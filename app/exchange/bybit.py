"""
Adapter dla giełdy Bybit
"""

import asyncio
import hashlib
import hmac
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode
import websockets

from .base_exchange import BaseExchange
import logging
from utils.net_wrappers import net_guard
from utils.http_logging import log_request
logger = logging.getLogger(__name__)

class BybitExchange(BaseExchange):
    """
    Adapter dla giełdy Bybit
    
    Implementuje interfejs dla handlu na Bybit
    poprzez REST API i WebSocket.
    """
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        super().__init__(api_key, api_secret, testnet)
        
        if testnet:
            self.base_url = "https://api-testnet.bybit.com"
            self.ws_url = "wss://stream-testnet.bybit.com/v5/public/spot"
        else:
            self.base_url = "https://api.bybit.com"
            self.ws_url = "wss://stream.bybit.com/v5/public/spot"
        
        # Bybit specific settings
        self.min_request_interval = 0.1  # 100ms
        self.recv_window = 5000  # 5 seconds
        
        # API version
        self.api_version = "v5"
    
    async def test_connection(self) -> bool:
        """Test połączenia z Bybit API"""
        try:
            response = await self.make_request('GET', f'/{self.api_version}/market/time')
            return response is not None and response.get('retCode') == 0
            
        except Exception as e:
            raise Exception(f"Test połączenia Bybit nieudany: {e}")
    
    async def load_exchange_info(self):
        """Wczytanie informacji o giełdzie Bybit"""
        try:
            response = await self.make_request('GET', f'/{self.api_version}/market/instruments-info', 
                                             params={'category': 'spot'})
            
            if response and response.get('retCode') == 0:
                self.exchange_info = response
                
                # Cache symbol information
                for symbol in response.get('result', {}).get('list', []):
                    symbol_name = symbol['symbol']
                    
                    self.symbols_info[symbol_name] = {
                        'base_asset': symbol['baseCoin'],
                        'quote_asset': symbol['quoteCoin'],
                        'status': symbol['status'],
                        'lot_size': float(symbol.get('lotSizeFilter', {}).get('qtyStep', '0.001')),
                        'tick_size': float(symbol.get('priceFilter', {}).get('tickSize', '0.01')),
                        'min_order_qty': float(symbol.get('lotSizeFilter', {}).get('minOrderQty', '0.001')),
                        'max_order_qty': float(symbol.get('lotSizeFilter', {}).get('maxOrderQty', '1000000')),
                        'min_order_amt': float(symbol.get('lotSizeFilter', {}).get('minOrderAmt', '1')),
                        'max_order_amt': float(symbol.get('lotSizeFilter', {}).get('maxOrderAmt', '1000000')),
                        'innovation': symbol.get('innovation', '0') == '1'
                    }
                    
        except Exception as e:
            raise Exception(f"Błąd podczas wczytywania informacji o giełdzie Bybit: {e}")
    
    def generate_signature(self, params: str) -> str:
        """Generowanie podpisu HMAC SHA256 dla Bybit"""
        return hmac.new(
            self.api_secret.encode('utf-8'),
            params.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def normalize_pair(self, pair: str) -> str:
        """Normalizacja pary dla Bybit (BTCUSDT)"""
        return pair.replace('/', '').upper()
    
    def denormalize_pair(self, pair: str) -> str:
        """Denormalizacja pary z Bybit do formatu standardowego"""
        if '/' in pair:
            return pair
        
        # Znajdź podział na base/quote używając exchange info
        if pair in self.symbols_info:
            symbol_info = self.symbols_info[pair]
            return f"{symbol_info['base_asset']}/{symbol_info['quote_asset']}"
        
        # Fallback - próba automatycznego podziału
        return super().denormalize_pair(pair)
    
    @net_guard('exchange:get_balance')
    async def get_balance(self, currency: Optional[str] = None) -> Dict:
        """Pobranie salda z Bybit"""
        try:
            timestamp = str(int(time.time() * 1000))
            params = {
                'accountType': 'SPOT',
                'api_key': self.api_key,
                'timestamp': timestamp,
                'recv_window': str(self.recv_window)
            }
            
            # Generate signature
            param_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = self.generate_signature(param_str)
            params['sign'] = signature
            
            response = await self.make_request('GET', f'/{self.api_version}/account/wallet-balance', 
                                             params=params, signed=True)
            
            if not response or response.get('retCode') != 0:
                return {}
            
            balances = {}
            wallet_balance = response.get('result', {}).get('list', [])
            
            if wallet_balance:
                for coin in wallet_balance[0].get('coin', []):
                    asset = coin['coin']
                    free = float(coin.get('availableToWithdraw', '0'))
                    locked = float(coin.get('locked', '0'))
                    
                    if free > 0 or locked > 0:  # Tylko niezerowe salda
                        balances[asset] = {
                            'free': free,
                            'locked': locked,
                            'total': free + locked
                        }
            
            if currency:
                return balances.get(currency.upper(), {'free': 0.0, 'locked': 0.0, 'total': 0.0})
            
            return balances
            
        except Exception as e:
            logger.error(f"Błąd Bybit API podczas pobierania salda: {e}", exc_info=True)
            return {}

    @net_guard('exchange:get_current_price')
    async def get_current_price(self, pair: str) -> Optional[float]:
        """Pobranie aktualnej ceny z Bybit"""
        try:
            symbol = self.normalize_pair(pair)
            params = {
                'category': 'spot',
                'symbol': symbol
            }
            
            response = await self.make_request('GET', f'/{self.api_version}/market/tickers', params=params)
            
            if response and response.get('retCode') == 0:
                tickers = response.get('result', {}).get('list', [])
                if tickers:
                    return float(tickers[0]['lastPrice'])
            
            return None
            
        except Exception as e:
            logger.error(f"Błąd Bybit API podczas pobierania ceny {pair}: {e}", exc_info=True)
            return None
    
    @net_guard('exchange:get_order_book')
    async def get_order_book(self, pair: str, limit: int = 50) -> Dict:
        """Pobranie księgi zleceń z Bybit"""
        try:
            symbol = self.normalize_pair(pair)
            params = {
                'category': 'spot',
                'symbol': symbol,
                'limit': min(limit, 500)
            }
            response = await self.make_request('GET', f'/{self.api_version}/market/orderbook', params=params)
            if response and response.get('retCode') == 0:
                result = response.get('result', {})
                return {
                    'bids': [[float(price), float(amount)] for price, amount in result.get('b', [])],
                    'asks': [[float(price), float(amount)] for price, amount in result.get('a', [])],
                    'timestamp': result.get('ts')
                }
            return {'bids': [], 'asks': [], 'timestamp': None}
        except Exception as e:
            logger.error(f"Błąd podczas pobierania księgi zleceń Bybit {pair}: {e}", exc_info=True)
            return {'bids': [], 'asks': [], 'timestamp': None}
    
    @net_guard('exchange:create_order')
    async def create_order(self, pair: str, side: str, amount: float,
                          price: Optional[float] = None, order_type: str = 'market',
                          **kwargs) -> Optional[Dict]:
        """Utworzenie zlecenia na Bybit"""
        try:
            symbol = self.normalize_pair(pair)
            
            # Format amount and price
            formatted_amount = self.format_amount(pair, amount)
            
            timestamp = str(int(time.time() * 1000))
            params = {
                'category': 'spot',
                'symbol': symbol,
                'side': side.title(),  # Buy/Sell
                'orderType': order_type.title(),  # Market/Limit
                'qty': str(formatted_amount),
                'api_key': self.api_key,
                'timestamp': timestamp,
                'recv_window': str(self.recv_window)
            }
            
            # Add price for limit orders
            if order_type.lower() == 'limit':
                if price is None:
                    raise ValueError(f"Cena jest wymagana dla zlecenia limit")
                formatted_price = self.format_price(pair, price)
                params['price'] = str(formatted_price)
            
            # Add time in force
            params['timeInForce'] = kwargs.get('time_in_force', 'GTC')
            
            # Generate signature
            param_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = self.generate_signature(param_str)
            params['sign'] = signature
            
            response = await self.make_request('POST', f'/{self.api_version}/order/create', 
                                             data=params, signed=True)
            
            if response and response.get('retCode') == 0:
                result = response.get('result', {})
                return {
                    'id': result.get('orderId'),
                    'symbol': self.denormalize_pair(symbol),
                    'side': side.lower(),
                    'amount': float(formatted_amount),
                    'price': float(price) if price else 0,
                    'type': order_type.lower(),
                    'status': 'new',
                    'timestamp': int(timestamp),
                    'raw': response
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Błąd Bybit API podczas tworzenia zlecenia {pair}: {e}", exc_info=True)
            return None
    
    @net_guard('exchange:cancel_order')
    async def cancel_order(self, order_id: str, pair: str) -> bool:
        """Anulowanie zlecenia na Bybit"""
        try:
            symbol = self.normalize_pair(pair)
            
            timestamp = str(int(time.time() * 1000))
            params = {
                'category': 'spot',
                'symbol': symbol,
                'orderId': order_id,
                'api_key': self.api_key,
                'timestamp': timestamp,
                'recv_window': str(self.recv_window)
            }
            
            # Generate signature
            param_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = self.generate_signature(param_str)
            params['sign'] = signature
            
            response = await self.make_request('POST', f'/{self.api_version}/order/cancel', 
                                             data=params, signed=True)
            return response is not None and response.get('retCode') == 0
        except Exception as e:
            logger.error(f"Błąd Bybit API podczas anulowania zlecenia {order_id}: {e}", exc_info=True)
            return False
    
    @net_guard('exchange:get_order_status')
    async def get_order_status(self, order_id: str, pair: str) -> Optional[Dict]:
        """Sprawdzenie statusu zlecenia na Bybit"""
        try:
            symbol = self.normalize_pair(pair)
            
            timestamp = str(int(time.time() * 1000))
            params = {
                'category': 'spot',
                'symbol': symbol,
                'orderId': order_id,
                'api_key': self.api_key,
                'timestamp': timestamp,
                'recv_window': str(self.recv_window)
            }
            # Generate signature
            param_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = self.generate_signature(param_str)
            params['sign'] = signature
            
            response = await self.make_request('GET', f'/{self.api_version}/order/realtime', 
                                             params=params, signed=True)
            
            if response and response.get('retCode') == 0:
                orders = response.get('result', {}).get('list', [])
                if orders:
                    order = orders[0]
                    return {
                        'id': order.get('orderId'),
                        'symbol': self.denormalize_pair(order.get('symbol')),
                        'side': order.get('side', '').lower(),
                        'amount': float(order.get('qty', 0)),
                        'filled': float(order.get('cumExecQty', 0)),
                        'price': float(order.get('price', 0)),
                        'average_price': float(order.get('avgPrice', 0)),
                        'type': order.get('orderType', '').lower(),
                        'status': order.get('orderStatus', '').lower(),
                        'timestamp': int(order.get('createdTime', 0)),
                        'update_time': int(order.get('updatedTime', 0)),
                        'raw': order
                    }
            
            return None
        except Exception as e:
            logger.error(f"Błąd Bybit API podczas sprawdzania statusu zlecenia {order_id}: {e}", exc_info=True)
            return None
    

    @net_guard('exchange:get_open_orders')
    async def get_open_orders(self, pair: Optional[str] = None) -> List[Dict]:
        """Pobranie otwartych zleceń z Bybit"""
        try:
            timestamp = str(int(time.time() * 1000))
            params = {
                'category': 'spot',
                'api_key': self.api_key,
                'timestamp': timestamp,
                'recv_window': str(self.recv_window)
            }
            if pair:
                params['symbol'] = self.normalize_pair(pair)
            # Generate signature
            param_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = self.generate_signature(param_str)
            params['sign'] = signature
            response = await self.make_request('GET', f'/{self.api_version}/order/realtime', 
                                             params=params, signed=True)
            if response and response.get('retCode') == 0:
                orders = []
                for order in response.get('result', {}).get('list', []):
                    orders.append({
                        'id': order.get('orderId'),
                        'symbol': self.denormalize_pair(order.get('symbol')),
                        'side': order.get('side', '').lower(),
                        'amount': float(order.get('qty', 0)),
                        'filled': float(order.get('cumExecQty', 0)),
                        'price': float(order.get('price', 0)),
                        'type': order.get('orderType', '').lower(),
                        'status': order.get('orderStatus', '').lower(),
                        'timestamp': int(order.get('createdTime', 0)),
                        'raw': order
                    })
                return orders
            return []
        except Exception as e:
            logger.error(f"Błąd Bybit API podczas pobierania otwartych zleceń: {e}", exc_info=True)
            return []
    
    @net_guard('exchange:get_trade_history')
    async def get_trade_history(self, pair: str, limit: int = 100,
                               start_time: Optional[int] = None,
                               end_time: Optional[int] = None) -> List[Dict]:
        """Pobranie historii transakcji z Bybit"""
        try:
            symbol = self.normalize_pair(pair)
            timestamp = str(int(time.time() * 1000))
            params = {
                'category': 'spot',
                'symbol': symbol,
                'limit': str(min(limit, 100)),  # Bybit limit
                'api_key': self.api_key,
                'timestamp': timestamp,
                'recv_window': str(self.recv_window)
            }
            if start_time:
                params['startTime'] = str(start_time)
            if end_time:
                params['endTime'] = str(end_time)
            # Generate signature
            param_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = self.generate_signature(param_str)
            params['sign'] = signature
            response = await self.make_request('GET', f'/{self.api_version}/execution/list', 
                                             params=params, signed=True)
            if response and response.get('retCode') == 0:
                trades = []
                for trade in response.get('result', {}).get('list', []):
                    trades.append({
                        'id': trade.get('execId'),
                        'order_id': trade.get('orderId'),
                        'symbol': self.denormalize_pair(trade.get('symbol')),
                        'side': trade.get('side', '').lower(),
                        'amount': float(trade.get('execQty', 0)),
                        'price': float(trade.get('execPrice', 0)),
                        'fee': float(trade.get('execFee', 0)),
                        'fee_asset': trade.get('feeTokenId', ''),
                        'timestamp': int(trade.get('execTime', 0)),
                        'is_maker': trade.get('isMaker', False),
                        'raw': trade
                    })
                return trades
            return []
        except Exception as e:
            logger.error(f"Błąd Bybit API podczas pobierania historii transakcji {pair}: {e}", exc_info=True)
            return []
    
    @net_guard('exchange:get_klines')
    async def get_klines(self, pair: str, interval: str = '1m', limit: int = 1000,
                         start_time: Optional[int] = None, end_time: Optional[int] = None) -> List[Dict]:
        try:
            symbol = self.normalize_pair(pair)
            params = {
                'category': 'spot',
                'symbol': symbol,
                'interval': interval,  # Bybit uses different interval format
                'limit': str(min(limit, 1000))
            }
            if start_time:
                params['start'] = str(start_time)
            if end_time:
                params['end'] = str(end_time)
            response = await self.make_request('GET', f'/{self.api_version}/market/kline', params=params)
            if response and response.get('retCode') == 0:
                klines = []
                for kline in response.get('result', {}).get('list', []):
                    klines.append({
                        'timestamp': int(kline[0]),
                        'open': float(kline[1]),
                        'high': float(kline[2]),
                        'low': float(kline[3]),
                        'close': float(kline[4]),
                        'volume': float(kline[5]),
                        'turnover': float(kline[6]) if len(kline) > 6 else 0
                    })
                return klines
            return []
        except Exception as e:
            logger.error(f"Błąd Bybit API podczas pobierania klines {pair}: {e}", exc_info=True)
            return []

    async def subscribe_ticker(self, pair: str, callback) -> bool:
        """Subskrypcja ticker WebSocket na Bybit"""
        try:
            symbol = self.normalize_pair(pair)
            topic = f"tickers.{symbol}"
            
            return await self._subscribe_websocket(topic, callback, 'ticker', pair)
            
        except Exception as e:
            logger.error(f"Błąd podczas subskrypcji ticker Bybit {pair}: {e}", exc_info=True)
            return False
    
    async def subscribe_trades(self, pair: str, callback) -> bool:
        """Subskrypcja transakcji WebSocket na Bybit"""
        try:
            symbol = self.normalize_pair(pair)
            topic = f"publicTrade.{symbol}"
            
            return await self._subscribe_websocket(topic, callback, 'trades', pair)
            
        except Exception as e:
            logger.error(f"Błąd podczas subskrypcji trades Bybit {pair}: {e}", exc_info=True)
            return False
    
    async def subscribe_order_book(self, pair: str, callback) -> bool:
        """Subskrypcja księgi zleceń WebSocket na Bybit"""
        try:
            symbol = self.normalize_pair(pair)
            topic = f"orderbook.1.{symbol}"
            
            return await self._subscribe_websocket(topic, callback, 'orderbook', pair)
            
        except Exception as e:
            logger.error(f"Błąd podczas subskrypcji orderbook Bybit {pair}: {e}", exc_info=True)
            return False
    
    async def _subscribe_websocket(self, topic: str, callback, stream_type: str, pair: str) -> bool:
        """Wewnętrzna metoda subskrypcji WebSocket"""
        try:
            # Zamknij istniejące połączenie jeśli istnieje
            if topic in self.ws_connections:
                await self.ws_connections[topic].close()
            
            # Utwórz nowe połączenie
            websocket = await websockets.connect(self.ws_url, open_timeout=10, ping_interval=20, ping_timeout=10)
            self.ws_connections[topic] = websocket
            
            # Wyślij subskrypcję
            subscribe_msg = {
                "op": "subscribe",
                "args": [topic]
            }
            await websocket.send(json.dumps(subscribe_msg))
            
            # Zapisz callback
            callback_key = f"{pair}_{stream_type}"
            self.ws_callbacks[callback_key] = callback
            
            # Uruchom listener w tle
            asyncio.create_task(self._websocket_listener(websocket, topic, stream_type, pair))
            
            return True
            
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia połączenia WebSocket Bybit: {e}", exc_info=True)
            return False
    
    async def _websocket_listener(self, websocket, topic: str, stream_type: str, pair: str):
        """Listener dla wiadomości WebSocket"""
        try:
            async for message in websocket:
                # Mapuj stream_type na WebSocketEventType
                from core.websocket_callback_manager import WebSocketEventType
                
                event_type_map = {
                    'ticker': WebSocketEventType.TICKER,
                    'trades': WebSocketEventType.TRADES,
                    'orderbook': WebSocketEventType.ORDER_BOOK,
                    'kline': WebSocketEventType.KLINE
                }
                
                event_type = event_type_map.get(stream_type, WebSocketEventType.TICKER)
                await self.handle_websocket_message(message, event_type, pair)
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Połączenie WebSocket zamknięte dla {topic}: {e}")
        except Exception as e:
            logger.error(f"Błąd w WebSocket listener: {e}", exc_info=True)
        finally:
            # Zamknij połączenie i wyczyść struktury
            try:
                await websocket.close()
            except Exception as close_err:
                logger.warning(f"Nie udało się zamknąć połączenia WebSocket dla {topic}: {close_err}")
            if topic in self.ws_connections:
                del self.ws_connections[topic]
            callback_key = f"{pair}_{stream_type}"
            if callback_key in self.ws_callbacks:
                del self.ws_callbacks[callback_key]
            
            return True
    async def make_request(self, method: str, endpoint: str, params: Dict = None,
                          signed: bool = False, data: Dict = None) -> Optional[Dict]:
        """Wykonanie requestu HTTP do Bybit API"""
        try:
            await self.rate_limit()
            
            if not self.session:
                raise Exception("Brak aktywnej sesji HTTP")
            
            url = f"{self.base_url}{endpoint}"
            headers = {'Content-Type': 'application/json'}
            
            if signed and self.api_key:
                headers['X-BAPI-API-KEY'] = self.api_key
            
            # Dla Bybit, POST requests używają JSON body, GET używa query params
            request_params = None
            request_data = None
            
            if method.upper() == 'GET':
                request_params = params
            else:
                request_data = data or params
            
            # Sanityzowane logowanie żądania HTTP
            log_request(logger, method, url, headers=headers, params=request_params, json_body=request_data)
            async with self.session.request(
                method=method,
                url=url,
                params=request_params,
                json=request_data,
                headers=headers
            ) as response:
                
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    
                    # Parse Bybit error
                    try:
                        error_data = json.loads(error_text)
                        error_msg = error_data.get('retMsg', error_text)
                        error_code = error_data.get('retCode', response.status)
                        raise Exception(f"Bybit API Error {error_code}: {error_msg}")
                    except json.JSONDecodeError:
                        raise Exception(f"HTTP {response.status}: {error_text}")
                        
        except Exception as e:
            logger.error(f"Błąd requestu Bybit {method} {endpoint}: {e}", exc_info=True)