"""
Adapter dla giełdy Binance
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

class BinanceExchange(BaseExchange):
    """
    Adapter dla giełdy Binance
    
    Implementuje pełny interfejs dla handlu na Binance
    poprzez REST API i WebSocket.
    """
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        super().__init__(api_key, api_secret, testnet)
        
        if testnet:
            self.base_url = "https://testnet.binance.vision/api/v3"
            self.ws_url = "wss://testnet.binance.vision/ws"
        else:
            self.base_url = "https://api.binance.com/api/v3"
            self.ws_url = "wss://stream.binance.com:9443/ws"
        
        # Binance specific settings
        self.min_request_interval = 0.1  # 100ms
        self.recv_window = 5000  # 5 seconds
        
        # WebSocket stream names
        self.ws_streams = {}
    
    async def test_connection(self) -> bool:
        """Test połączenia z Binance API"""
        try:
            response = await self.make_request('GET', '/ping')
            return response is not None
            
        except Exception as e:
            raise Exception(f"Test połączenia Binance nieudany: {e}")
    
    async def load_exchange_info(self):
        """Wczytanie informacji o giełdzie Binance"""
        try:
            response = await self.make_request('GET', '/exchangeInfo')
            
            if response:
                self.exchange_info = response
                
                # Cache symbol information
                for symbol in response.get('symbols', []):
                    symbol_name = symbol['symbol']
                    
                    # Extract lot size and tick size
                    lot_size = None
                    tick_size = None
                    min_notional = None
                    
                    for filter_info in symbol.get('filters', []):
                        if filter_info['filterType'] == 'LOT_SIZE':
                            lot_size = float(filter_info['stepSize'])
                        elif filter_info['filterType'] == 'PRICE_FILTER':
                            tick_size = float(filter_info['tickSize'])
                        elif filter_info['filterType'] == 'MIN_NOTIONAL':
                            min_notional = float(filter_info['minNotional'])
                    
                    self.symbols_info[symbol_name] = {
                        'base_asset': symbol['baseAsset'],
                        'quote_asset': symbol['quoteAsset'],
                        'status': symbol['status'],
                        'lot_size': lot_size,
                        'tick_size': tick_size,
                        'min_notional': min_notional,
                        'is_spot_trading_allowed': symbol.get('isSpotTradingAllowed', False),
                        'permissions': symbol.get('permissions', [])
                    }
                    
        except Exception as e:
            raise Exception(f"Błąd podczas wczytywania informacji o giełdzie: {e}")
    
    def generate_signature(self, params: str) -> str:
        """Generowanie podpisu HMAC SHA256 dla Binance"""
        return hmac.new(
            self.api_secret.encode('utf-8'),
            params.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def normalize_pair(self, pair: str) -> str:
        """Normalizacja pary dla Binance (BTCUSDT)"""
        return pair.replace('/', '').upper()
    
    def denormalize_pair(self, pair: str) -> str:
        """Denormalizacja pary z Binance do formatu standardowego"""
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
        """Pobranie salda z Binance"""
        try:
            params = {
                'timestamp': int(time.time() * 1000),
                'recvWindow': self.recv_window
            }
            query_string = urlencode(params)
            signature = self.generate_signature(query_string)
            params['signature'] = signature

            log_request(logger, 'GET', f"{self.base_url}/account", params=params)
            response = await self.make_request('GET', '/account', params=params, signed=True)
            if not response:
                return {}

            balances: Dict[str, Dict[str, float]] = {}
            for balance in response.get('balances', []):
                asset = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])
                if free > 0 or locked > 0:
                    balances[asset] = {
                        'free': free,
                        'locked': locked,
                        'total': free + locked
                    }
            if currency:
                return balances.get(currency.upper(), {'free': 0.0, 'locked': 0.0, 'total': 0.0})
            return balances
        except Exception as e:
            logger.error(f"Błąd podczas pobierania salda Binance: {e}")
            return {}

    @net_guard('exchange:get_current_price')
    async def get_current_price(self, pair: str) -> Optional[float]:
        """Pobranie aktualnej ceny z Binance"""
        try:
            symbol = self.normalize_pair(pair)
            params = {'symbol': symbol}
            log_request(logger, 'GET', f"{self.base_url}/ticker/price", params=params)
            response = await self.make_request('GET', '/ticker/price', params=params)
            if response and 'price' in response:
                return float(response['price'])
            return None
        except Exception as e:
            logger.error(f"Błąd podczas pobierania ceny Binance {pair}: {e}")
            return None

    @net_guard('exchange:get_order_book')
    async def get_order_book(self, pair: str, limit: int = 100) -> Dict:
        """Pobranie księgi zleceń z Binance"""
        try:
            symbol = self.normalize_pair(pair)
            params = {
                'symbol': symbol,
                'limit': min(limit, 5000)
            }
            log_request(logger, 'GET', f"{self.base_url}/depth", params=params)
            response = await self.make_request('GET', '/depth', params=params)
            if response:
                return {
                    'bids': [[float(price), float(amount)] for price, amount in response.get('bids', [])],
                    'asks': [[float(price), float(amount)] for price, amount in response.get('asks', [])],
                    'timestamp': response.get('lastUpdateId')
                }
            return {'bids': [], 'asks': [], 'timestamp': None}
        except Exception as e:
            logger.error(f"Błąd podczas pobierania księgi zleceń Binance {pair}: {e}")
            return {'bids': [], 'asks': [], 'timestamp': None}

    @net_guard('exchange:create_order')
    async def create_order(self, pair: str, side: str, amount: float,
                      price: Optional[float] = None, order_type: str = 'market',
                      **kwargs) -> Optional[Dict]:
        """Utworzenie zlecenia na Binance"""
        try:
            symbol = self.normalize_pair(pair)
            formatted_amount = self.format_amount(pair, amount)
            params = {
                'symbol': symbol,
                'side': side.upper(),
                'type': order_type.upper(),
                'quantity': str(formatted_amount),
                'timestamp': int(time.time() * 1000),
                'recvWindow': self.recv_window
            }
            if order_type.lower() in ['limit', 'stop_loss_limit', 'take_profit_limit']:
                if price is None:
                    raise ValueError(f"Cena jest wymagana dla zlecenia {order_type}")
                formatted_price = self.format_price(pair, price)
                params['price'] = str(formatted_price)
            if order_type.lower() == 'limit':
                params['timeInForce'] = kwargs.get('time_in_force', 'GTC')
            if 'stop' in order_type.lower():
                stop_price = kwargs.get('stop_price', price)
                if stop_price is not None:
                    formatted_stop_price = self.format_price(pair, stop_price)
                    params['stopPrice'] = str(formatted_stop_price)
            query_string = urlencode(params)
            signature = self.generate_signature(query_string)
            params['signature'] = signature
            response = await self.make_request('POST', '/order', params=params, signed=True)
            if response:
                return {
                    'id': str(response['orderId']),
                    'symbol': self.denormalize_pair(response['symbol']),
                    'side': response['side'].lower(),
                    'amount': float(response['origQty']),
                    'price': float(response.get('price', 0)),
                    'type': response['type'].lower(),
                    'status': response['status'].lower(),
                    'timestamp': response['transactTime'],
                    'fills': response.get('fills', []),
                    'raw': response
                }
            return None
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia zlecenia Binance {pair}: {e}")
            return None

    @net_guard('exchange:cancel_order')
    async def cancel_order(self, order_id: str, pair: str) -> bool:
        """Anulowanie zlecenia na Binance"""
        try:
            symbol = self.normalize_pair(pair)
            params = {
                'symbol': symbol,
                'orderId': order_id,
                'timestamp': int(time.time() * 1000),
                'recvWindow': self.recv_window
            }
            query_string = urlencode(params)
            signature = self.generate_signature(query_string)
            params['signature'] = signature
            response = await self.make_request('DELETE', '/order', params=params, signed=True)
            return response is not None
        except Exception as e:
            logger.error(f"Błąd podczas anulowania zlecenia Binance {order_id}: {e}")
            return False

    @net_guard('exchange:get_order_status')
    async def get_order_status(self, order_id: str, pair: str) -> Optional[Dict]:
        """Sprawdzenie statusu zlecenia na Binance"""
        try:
            symbol = self.normalize_pair(pair)
            params = {
                'symbol': symbol,
                'orderId': order_id,
                'timestamp': int(time.time() * 1000),
                'recvWindow': self.recv_window
            }
            query_string = urlencode(params)
            signature = self.generate_signature(query_string)
            params['signature'] = signature
            response = await self.make_request('GET', '/order', params=params, signed=True)
            if response:
                return {
                    'id': str(response['orderId']),
                    'symbol': self.denormalize_pair(response['symbol']),
                    'side': response['side'].lower(),
                    'amount': float(response['origQty']),
                    'filled': float(response['executedQty']),
                    'price': float(response.get('price', 0)),
                    'average_price': float(response.get('cummulativeQuoteQty', 0)) / float(response['executedQty']) if float(response['executedQty']) > 0 else 0,
                    'type': response['type'].lower(),
                    'status': response['status'].lower(),
                    'timestamp': response['time'],
                    'update_time': response['updateTime'],
                    'raw': response
                }
            return None
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania statusu zlecenia Binance {order_id}: {e}")
            return None

    @net_guard('exchange:get_open_orders')
    async def get_open_orders(self, pair: Optional[str] = None) -> List[Dict]:
        """Pobranie otwartych zleceń z Binance"""
        try:
            params = {
                'timestamp': int(time.time() * 1000),
                'recvWindow': self.recv_window
            }
            if pair:
                params['symbol'] = self.normalize_pair(pair)
            query_string = urlencode(params)
            signature = self.generate_signature(query_string)
            params['signature'] = signature
            response = await self.make_request('GET', '/openOrders', params=params, signed=True)
            if response:
                orders = []
                for order in response:
                    orders.append({
                        'id': str(order['orderId']),
                        'symbol': self.denormalize_pair(order['symbol']),
                        'side': order['side'].lower(),
                        'amount': float(order['origQty']),
                        'filled': float(order['executedQty']),
                        'price': float(order.get('price', 0)),
                        'type': order['type'].lower(),
                        'status': order['status'].lower(),
                        'timestamp': order['time'],
                        'raw': order
                    })
                return orders
            return []
        except Exception as e:
            logger.error(f"Błąd podczas pobierania otwartych zleceń Binance: {e}")
            return []

    @net_guard('exchange:get_trade_history')
    async def get_trade_history(self, pair: str, limit: int = 100,
                           start_time: Optional[int] = None,
                           end_time: Optional[int] = None) -> List[Dict]:
        """Pobranie historii transakcji z Binance"""
        try:
            symbol = self.normalize_pair(pair)
            params = {
                'symbol': symbol,
                'limit': min(limit, 1000),  # Binance limit
                'timestamp': int(time.time() * 1000),
                'recvWindow': self.recv_window
            }
            if start_time:
                params['startTime'] = start_time
            if end_time:
                params['endTime'] = end_time
    
            query_string = urlencode(params)
            signature = self.generate_signature(query_string)
            params['signature'] = signature
    
            response = await self.make_request('GET', '/myTrades', params=params, signed=True)
            if response:
                trades = []
                for trade in response:
                    trades.append({
                        'id': str(trade['id']),
                        'order_id': str(trade['orderId']),
                        'symbol': self.denormalize_pair(trade['symbol']),
                        'side': 'buy' if trade['isBuyer'] else 'sell',
                        'amount': float(trade['qty']),
                        'price': float(trade['price']),
                        'fee': float(trade['commission']),
                        'fee_asset': trade['commissionAsset'],
                        'timestamp': trade['time'],
                        'is_maker': trade['isMaker'],
                        'raw': trade
                    })
                return trades
            return []
        except Exception as e:
            logger.error(f"Błąd podczas pobierania historii transakcji Binance {pair}: {e}")
            return []
    
    @net_guard('exchange:get_klines')
    async def get_klines(self, pair: str, interval: str = '1m', limit: int = 100,
                     start_time: Optional[int] = None,
                     end_time: Optional[int] = None) -> List[Dict]:
        """Pobranie danych OHLCV z Binance"""
        try:
            symbol = self.normalize_pair(pair)
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': min(limit, 1000)  # Binance limit
            }
            if start_time:
                params['startTime'] = start_time
            if end_time:
                params['endTime'] = end_time
    
            response = await self.make_request('GET', '/klines', params=params)
            if response:
                klines = []
                for kline in response:
                    klines.append({
                        'timestamp': kline[0],
                        'open': float(kline[1]),
                        'high': float(kline[2]),
                        'low': float(kline[3]),
                        'close': float(kline[4]),
                        'volume': float(kline[5]),
                        'close_time': kline[6],
                        'quote_volume': float(kline[7]),
                        'trades_count': kline[8],
                        'taker_buy_base_volume': float(kline[9]),
                        'taker_buy_quote_volume': float(kline[10])
                    })
                return klines
            return []
        except Exception as e:
            logger.error(f"Błąd podczas pobierania klines Binance {pair}: {e}")
            return []
    
    async def subscribe_ticker(self, pair: str, callback) -> bool:
        """Subskrypcja ticker WebSocket na Binance"""
        try:
            symbol = self.normalize_pair(pair).lower()
            stream = f"{symbol}@ticker"
            return await self._subscribe_websocket(stream, callback, 'ticker', pair)
        except Exception as e:
            logger.error(f"Błąd podczas subskrypcji ticker Binance {pair}: {e}")
            return False
    
    async def subscribe_trades(self, pair: str, callback) -> bool:
        """Subskrypcja transakcji WebSocket na Binance"""
        try:
            symbol = self.normalize_pair(pair).lower()
            stream = f"{symbol}@trade"
            return await self._subscribe_websocket(stream, callback, 'trades', pair)
        except Exception as e:
            logger.error(f"Błąd podczas subskrypcji trades Binance {pair}: {e}")
            return False
    
    async def subscribe_order_book(self, pair: str, callback) -> bool:
        """Subskrypcja księgi zleceń WebSocket na Binance"""
        try:
            symbol = self.normalize_pair(pair).lower()
            stream = f"{symbol}@depth"
            return await self._subscribe_websocket(stream, callback, 'orderbook', pair)
        except Exception as e:
            logger.error(f"Błąd podczas subskrypcji orderbook Binance {pair}: {e}")
            return False
    
    async def _subscribe_websocket(self, stream: str, callback, stream_type: str, pair: str) -> bool:
        """Wewnętrzna metoda subskrypcji WebSocket"""
        try:
            ws_url = f"{self.ws_url}/{stream}"
            # Zamknij istniejące połączenie jeśli istnieje
            if stream in self.ws_connections:
                await self.ws_connections[stream].close()
            # Utwórz nowe połączenie
            websocket = await websockets.connect(ws_url, open_timeout=10, ping_interval=20, ping_timeout=10)
            self.ws_connections[stream] = websocket
            # Zapisz callback
            callback_key = f"{pair}_{stream_type}"
            self.ws_callbacks[callback_key] = callback
            # Uruchom listener w tle
            asyncio.create_task(self._websocket_listener(websocket, stream, stream_type, pair))
            return True
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia połączenia WebSocket: {e}")
            return False
    
    async def _websocket_listener(self, websocket, stream: str, stream_type: str, pair: str):
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
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Połączenie WebSocket zamknięte dla {stream}")
        except Exception as e:
            logger.error(f"Błąd w WebSocket listener: {e}")
        finally:
            # Cleanup
            if stream in self.ws_connections:
                del self.ws_connections[stream]
    
    async def unsubscribe(self, pair: str, stream_type: str) -> bool:
        """Anulowanie subskrypcji WebSocket na Binance"""
        try:
            symbol = self.normalize_pair(pair).lower()
            
            if stream_type == 'ticker':
                stream = f"{symbol}@ticker"
            elif stream_type == 'trades':
                stream = f"{symbol}@trade"
            elif stream_type == 'orderbook':
                stream = f"{symbol}@depth"
            else:
                return False
            # Zamknij połączenie WebSocket
            if stream in self.ws_connections:
                await self.ws_connections[stream].close()
                del self.ws_connections[stream]
            # Usuń callback
            callback_key = f"{pair}_{stream_type}"
            if callback_key in self.ws_callbacks:
                del self.ws_callbacks[callback_key]
            return True
        except Exception as e:
            logger.error(f"Błąd podczas anulowania subskrypcji Binance {pair}: {e}")
            return False
    async def make_request(self, method: str, endpoint: str, params: Dict = None,
                          signed: bool = False, data: Dict = None) -> Optional[Dict]:
        """Wykonanie requestu HTTP do Binance API"""
        try:
            await self.rate_limit()
            
            if not self.session:
                raise Exception("Brak aktywnej sesji HTTP")
            
            url = f"{self.base_url}{endpoint}"
            headers = {}
            
            if signed and self.api_key:
                headers['X-MBX-APIKEY'] = self.api_key
            
            # Dla Binance, parametry są zawsze w query string
            if params:
                if signed:
                    # Dodaj signature dla signed requests
                    query_string = urlencode(params)
                    if 'signature' not in params:
                        signature = self.generate_signature(query_string)
                        params['signature'] = signature
            
            # Sanityzowane logowanie żądania HTTP
            log_request(logger, method, url, headers=headers, params=params, json_body=data)
            async with self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=headers
            ) as response:
                
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    
                    # Parse Binance error
                    try:
                        error_data = json.loads(error_text)
                        error_msg = error_data.get('msg', error_text)
                        error_code = error_data.get('code', response.status)
                        raise Exception(f"Binance API Error {error_code}: {error_msg}")
                    except json.JSONDecodeError:
                        raise Exception(f"HTTP {response.status}: {error_text}")
        except Exception as e:
            logger.error(f"Błąd requestu Binance {method} {endpoint}: {e}")
            return None