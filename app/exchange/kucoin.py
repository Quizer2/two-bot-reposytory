"""
Adapter dla giełdy KuCoin
"""

import asyncio
import base64
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode
import websockets

from .base_exchange import BaseExchange
import logging
from utils.net_wrappers import net_guard
from utils.http_logging import log_request
logger = logging.getLogger(__name__)

class KuCoinExchange(BaseExchange):
    """
    Adapter dla giełdy KuCoin
    
    Implementuje interfejs dla handlu na KuCoin
    poprzez REST API i WebSocket.
    """
    
    def __init__(self, api_key: str, api_secret: str, passphrase: str, testnet: bool = False):
        super().__init__(api_key, api_secret, testnet)
        
        self.passphrase = passphrase
        
        if testnet:
            self.base_url = "https://openapi-sandbox.kucoin.com"
            self.ws_url = "wss://ws-api-sandbox.kucoin.com"
        else:
            self.base_url = "https://api.kucoin.com"
            self.ws_url = "wss://ws-api-spot.kucoin.com"
        
        # KuCoin specific settings
        self.min_request_interval = 0.1  # 100ms
        
        # API version
        self.api_version = "v1"
        
        # WebSocket token
        self.ws_token = None
        self.ws_endpoint = None
    
    async def test_connection(self) -> bool:
        """Test połączenia z KuCoin API"""
        try:
            response = await self.make_request('GET', f'/api/{self.api_version}/timestamp')
            return response is not None and 'data' in response
            
        except Exception as e:
            raise Exception(f"Test połączenia KuCoin nieudany: {e}")
    
    async def load_exchange_info(self):
        """Wczytanie informacji o giełdzie KuCoin"""
        try:
            response = await self.make_request('GET', f'/api/{self.api_version}/symbols')
            
            if response and response.get('code') == '200000':
                self.exchange_info = response
                
                # Cache symbol information
                for symbol in response.get('data', []):
                    symbol_name = symbol['symbol']
                    
                    self.symbols_info[symbol_name] = {
                        'base_asset': symbol['baseCurrency'],
                        'quote_asset': symbol['quoteCurrency'],
                        'status': 'TRADING' if symbol['enableTrading'] else 'DISABLED',
                        'lot_size': float(symbol.get('baseIncrement', '0.001')),
                        'tick_size': float(symbol.get('priceIncrement', '0.01')),
                        'min_order_qty': float(symbol.get('baseMinSize', '0.001')),
                        'max_order_qty': float(symbol.get('baseMaxSize', '1000000')),
                        'min_order_amt': float(symbol.get('quoteMinSize', '1')),
                        'max_order_amt': float(symbol.get('quoteMaxSize', '1000000')),
                        'fee_currency': symbol.get('feeCurrency', symbol['quoteCurrency']),
                        'market': symbol.get('market', 'SPOT')
                    }
                    
        except Exception as e:
            raise Exception(f"Błąd podczas wczytywania informacji o giełdzie KuCoin: {e}")
    
    def generate_signature(self, timestamp: str, method: str, endpoint: str, body: str = '') -> str:
        """Generowanie podpisu HMAC SHA256 dla KuCoin"""
        message = timestamp + method.upper() + endpoint + body
        signature = base64.b64encode(
            hmac.new(
                self.api_secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
        return signature
    
    def generate_passphrase_signature(self) -> str:
        """Generowanie podpisu passphrase dla KuCoin"""
        return base64.b64encode(
            hmac.new(
                self.api_secret.encode('utf-8'),
                self.passphrase.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
    
    def normalize_pair(self, pair: str) -> str:
        """Normalizacja pary dla KuCoin (BTC-USDT)"""
        return pair.replace('/', '-').upper()
    
    def denormalize_pair(self, pair: str) -> str:
        """Denormalizacja pary z KuCoin do formatu standardowego"""
        if '/' in pair:
            return pair
        
        # Znajdź podział na base/quote używając exchange info
        if pair in self.symbols_info:
            symbol_info = self.symbols_info[pair]
            return f"{symbol_info['base_asset']}/{symbol_info['quote_asset']}"
        
        # Fallback - zamień - na /
        return pair.replace('-', '/')
    
    @net_guard('exchange:get_balance')
    async def get_balance(self, currency: Optional[str] = None) -> Dict:
        """Pobranie salda z KuCoin"""
        try:
            response = await self.make_request('GET', f'/api/{self.api_version}/accounts', signed=True)
            
            if not response or response.get('code') != '200000':
                return {}
            
            balances = {}
            
            for account in response.get('data', []):
                if account['type'] == 'trade':  # Tylko konto spot trading
                    asset = account['currency']
                    available = float(account.get('available', '0'))
                    holds = float(account.get('holds', '0'))
                    
                    if available > 0 or holds > 0:  # Tylko niezerowe salda
                        balances[asset] = {
                            'free': available,
                            'locked': holds,
                            'total': available + holds
                        }
            
            if currency:
                return balances.get(currency.upper(), {'free': 0.0, 'locked': 0.0, 'total': 0.0})
            
            return balances
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania salda KuCoin: {e}", exc_info=True)
            return {}
    
    @net_guard('exchange:get_current_price')
    async def get_current_price(self, pair: str) -> Optional[float]:
        """Pobranie aktualnej ceny z KuCoin"""
        try:
            symbol = self.normalize_pair(pair)
            params = {'symbol': symbol}
            response = await self.make_request('GET', f'/api/{self.api_version}/market/orderbook/level1', params=params)
            if response and response.get('code') == '200000':
                data = response.get('data', {})
                return float(data.get('price', 0))
            return None
        except Exception as e:
            logger.error(f"Błąd podczas pobierania ceny KuCoin {pair}: {e}", exc_info=True)
            return None
    
    @net_guard('exchange:get_order_book')
    async def get_order_book(self, pair: str, limit: int = 100) -> Dict:
        """Pobranie księgi zleceń z KuCoin"""
        try:
            symbol = self.normalize_pair(pair)
            # KuCoin ma różne endpointy dla różnych poziomów głębokości
            if limit <= 20:
                endpoint = f'/api/{self.api_version}/market/orderbook/level2_20'
            elif limit <= 100:
                endpoint = f'/api/{self.api_version}/market/orderbook/level2_100'
            else:
                endpoint = f'/api/{self.api_version}/market/orderbook/level2'
            params = {'symbol': symbol}
            response = await self.make_request('GET', endpoint, params=params)
            if response and response.get('code') == '200000':
                data = response.get('data', {})
                return {
                    'bids': [[float(price), float(amount)] for price, amount in data.get('bids', [])],
                    'asks': [[float(price), float(amount)] for price, amount in data.get('asks', [])],
                    'timestamp': data.get('time')
                }
            return {'bids': [], 'asks': [], 'timestamp': None}
        except Exception as e:
            logger.error(f"Błąd podczas pobierania księgi zleceń KuCoin {pair}: {e}", exc_info=True)
            return {'bids': [], 'asks': [], 'timestamp': None}
    
    @net_guard('exchange:create_order')
    async def create_order(self, pair: str, side: str, amount: float,
                           price: Optional[float] = None, order_type: str = 'market',
                           **kwargs) -> Optional[Dict]:
        """Utworzenie zlecenia na KuCoin"""
        try:
            symbol = self.normalize_pair(pair)
            formatted_amount = self.format_amount(pair, amount)

            order_data = {
                'clientOid': str(uuid.uuid4()),
                'symbol': symbol,
                'side': side.lower(),
                'type': order_type.lower()
            }

            # KuCoin używa różnych pól dla market i limit orders
            if order_type.lower() == 'market':
                if side.lower() == 'buy':
                    # Market buy - specify quote currency amount
                    if price:
                        order_data['funds'] = str(formatted_amount * price)
                    else:
                        # Get current price for funds calculation
                        current_price = await self.get_current_price(pair)
                        if current_price:
                            order_data['funds'] = str(formatted_amount * current_price)
                        else:
                            raise ValueError("Nie można określić ceny dla zlecenia market buy")
                else:
                    # Market sell - specify base currency amount
                    order_data['size'] = str(formatted_amount)
            else:
                # Limit order
                if price is None:
                    raise ValueError("Cena jest wymagana dla zlecenia limit")
                formatted_price = self.format_price(pair, price)
                order_data['price'] = str(formatted_price)
                order_data['size'] = str(formatted_amount)
                # Add time in force for limit orders
                order_data['timeInForce'] = kwargs.get('time_in_force', 'GTC')

            response = await self.make_request('POST', f'/api/{self.api_version}/orders',
                                               data=order_data, signed=True)

            if response and response.get('code') == '200000':
                data = response.get('data', {})
                return {
                    'id': data.get('orderId'),
                    'symbol': self.denormalize_pair(symbol),
                    'side': side.lower(),
                    'amount': float(formatted_amount),
                    'price': float(price) if price else 0,
                    'type': order_type.lower(),
                    'status': 'new',
                    'timestamp': int(time.time() * 1000),
                    'client_order_id': order_data['clientOid'],
                    'raw': response
                }

            return None
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia zlecenia KuCoin {pair}: {e}", exc_info=True)
            return None
    
    @net_guard('exchange:cancel_order')
    async def cancel_order(self, order_id: str, pair: str) -> bool:
        """Anulowanie zlecenia na KuCoin"""
        try:
            response = await self.make_request('DELETE', f'/api/{self.api_version}/orders/{order_id}', signed=True)
            return response is not None and response.get('code') == '200000'
        except Exception as e:
            logger.error(f"Błąd podczas anulowania zlecenia KuCoin {order_id}: {e}", exc_info=True)
            return False
    
    async def get_order_status(self, order_id: str, pair: str) -> Optional[Dict]:
        """Sprawdzenie statusu zlecenia na KuCoin"""
        try:
            response = await self.make_request('GET', f'/api/{self.api_version}/orders/{order_id}', 
                                             signed=True)
            
            if response and response.get('code') == '200000':
                order = response.get('data', {})
                return {
                    'id': order.get('id'),
                    'symbol': self.denormalize_pair(order.get('symbol')),
                    'side': order.get('side', '').lower(),
                    'amount': float(order.get('size', 0)),
                    'filled': float(order.get('dealSize', 0)),
                    'price': float(order.get('price', 0)),
                    'average_price': float(order.get('dealFunds', 0)) / float(order.get('dealSize', 1)) if float(order.get('dealSize', 0)) > 0 else 0,
                    'type': order.get('type', '').lower(),
                    'status': self._normalize_order_status(order.get('isActive'), order.get('cancelExist')),
                    'timestamp': int(order.get('createdAt', 0)),
                    'update_time': int(order.get('createdAt', 0)),
                    'client_order_id': order.get('clientOid'),
                    'raw': order
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania statusu zlecenia KuCoin {order_id}: {e}", exc_info=True)
            return None
    
    def _normalize_order_status(self, is_active: bool, cancel_exist: bool) -> str:
        """Normalizacja statusu zlecenia KuCoin"""
        if cancel_exist:
            return 'canceled'
        elif is_active:
            return 'open'
        else:
            return 'filled'
    
    @net_guard('exchange:get_open_orders')
    async def get_open_orders(self, pair: Optional[str] = None) -> List[Dict]:
        """Pobranie otwartych zleceń z KuCoin"""
        try:
            params = {'status': 'active'}
            if pair:
                params['symbol'] = self.normalize_pair(pair)
            response = await self.make_request('GET', f'/api/{self.api_version}/orders', params=params, signed=True)
            if response and response.get('code') == '200000':
                orders = []
                for order in response.get('data', {}).get('items', []):
                    orders.append({
                        'id': order.get('id'),
                        'symbol': self.denormalize_pair(order.get('symbol')),
                        'side': order.get('side', '').lower(),
                        'amount': float(order.get('size', 0)),
                        'filled': float(order.get('dealSize', 0)),
                        'price': float(order.get('price', 0)),
                        'type': order.get('type', '').lower(),
                        'status': 'open',
                        'timestamp': int(order.get('createdAt', 0)),
                        'client_order_id': order.get('clientOid'),
                        'raw': order
                    })
                return orders
            return []
        except Exception as e:
            logger.error(f"Błąd podczas pobierania otwartych zleceń KuCoin: {e}", exc_info=True)
            return []
    
    @net_guard('exchange:get_trade_history')
    async def get_trade_history(self, pair: str, limit: int = 100,
                               start_time: Optional[int] = None,
                               end_time: Optional[int] = None) -> List[Dict]:
        """Pobranie historii transakcji z KuCoin"""
        try:
            symbol = self.normalize_pair(pair)
            params = {
                'symbol': symbol,
                'pageSize': min(limit, 500)
            }
            if start_time:
                params['startAt'] = start_time
            if end_time:
                params['endAt'] = end_time
            response = await self.make_request('GET', f'/api/{self.api_version}/fills', params=params, signed=True)
            if response and response.get('code') == '200000':
                trades = []
                for trade in response.get('data', {}).get('items', []):
                    trades.append({
                        'id': trade.get('tradeId'),
                        'order_id': trade.get('orderId'),
                        'symbol': self.denormalize_pair(trade.get('symbol')),
                        'side': trade.get('side', '').lower(),
                        'amount': float(trade.get('size', 0)),
                        'price': float(trade.get('price', 0)),
                        'fee': float(trade.get('fee', 0)),
                        'fee_asset': trade.get('feeCurrency', ''),
                        'timestamp': int(trade.get('createdAt', 0)),
                        'is_maker': trade.get('liquidity') == 'maker',
                        'raw': trade
                    })
                return trades
            return []
        except Exception as e:
            logger.error(f"Błąd podczas pobierania historii transakcji KuCoin {pair}: {e}", exc_info=True)
            return []
    
    @net_guard('exchange:get_klines')
    async def get_klines(self, pair: str, interval: str = '1min', limit: int = 100,
                        start_time: Optional[int] = None,
                        end_time: Optional[int] = None) -> List[Dict]:
        """Pobranie danych OHLCV z KuCoin"""
        try:
            symbol = self.normalize_pair(pair)
            params = {
                'symbol': symbol,
                'type': interval
            }
            if start_time:
                params['startAt'] = start_time // 1000
            if end_time:
                params['endAt'] = end_time // 1000
            response = await self.make_request('GET', f'/api/{self.api_version}/market/candles', params=params)
            if response and response.get('code') == '200000':
                klines = []
                for kline in response.get('data', []):
                    klines.append({
                        'timestamp': int(kline[0]) * 1000,
                        'open': float(kline[1]),
                        'close': float(kline[2]),
                        'high': float(kline[3]),
                        'low': float(kline[4]),
                        'volume': float(kline[5]),
                        'turnover': float(kline[6])
                    })
                return klines
            return []
        except Exception as e:
            logger.error(f"Błąd podczas pobierania klines KuCoin {pair}: {e}", exc_info=True)
            return []
    async def _get_ws_token(self) -> bool:
        """Pobranie tokenu WebSocket z KuCoin"""
        try:
            response = await self.make_request('POST', f'/api/{self.api_version}/bullet-public')
            if response and response.get('code') == '200000':
                data = response.get('data', {})
                self.ws_token = data.get('token')
                servers = data.get('instanceServers', [])
                if servers:
                    server = servers[0]
                    self.ws_endpoint = f"{server['endpoint']}?token={self.ws_token}&[connectId={uuid.uuid4()}]"
                    return True
            return False
        except Exception as e:
            logger.error(f"Błąd podczas pobierania tokenu WebSocket KuCoin: {e}", exc_info=True)
            return False
    async def subscribe_ticker(self, pair: str, callback) -> bool:
        """Subskrypcja ticker WebSocket na KuCoin"""
        try:
            if not self.ws_token:
                if not await self._get_ws_token():
                    return False
            symbol = self.normalize_pair(pair)
            topic = f"/market/ticker:{symbol}"
            return await self._subscribe_websocket(topic, callback, 'ticker', pair)
        except Exception as e:
            logger.error(f"Błąd podczas subskrypcji ticker KuCoin {pair}: {e}", exc_info=True)
            return False
    
        try:
            if not self.ws_token:
                if not await self._get_ws_token():
                    return False
            symbol = self.normalize_pair(pair)
            topic = f"/market/match:{symbol}"
            return await self._subscribe_websocket(topic, callback, 'trades', pair)
        except Exception as e:
            logger.error(f"Błąd podczas subskrypcji trades KuCoin {pair}: {e}", exc_info=True)
            return False
    
    async def subscribe_order_book(self, pair: str, callback) -> bool:
        """Subskrypcja księgi zleceń WebSocket na KuCoin"""
        try:
            if not self.ws_token:
                if not await self._get_ws_token():
                    return False
            symbol = self.normalize_pair(pair)
            topic = f"/market/level2:{symbol}"
            return await self._subscribe_websocket(topic, callback, 'orderbook', pair)
        except Exception as e:
            logger.error(f"Błąd podczas subskrypcji orderbook KuCoin {pair}: {e}", exc_info=True)
            return False
    
        try:
            if topic in self.ws_connections:
                await self.ws_connections[topic].close()
            websocket = await websockets.connect(self.ws_endpoint, open_timeout=10, ping_interval=20, ping_timeout=10)
            self.ws_connections[topic] = websocket
            subscribe_msg = {
                "id": str(int(time.time() * 1000)),
                "type": "subscribe",
                "topic": topic,
                "privateChannel": False,
                "response": True
            }
            await websocket.send(json.dumps(subscribe_msg))
            callback_key = f"{pair}_{stream_type}"
            self.ws_callbacks[callback_key] = callback
            asyncio.create_task(self._websocket_listener(websocket, topic, stream_type, pair))
            return True
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia połączenia WebSocket KuCoin: {e}", exc_info=True)
            return False
    
        try:
            async for message in websocket:
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
            logger.info(f"Połączenie WebSocket zamknięte dla {topic}")
        except Exception as e:
            logger.error(f"Błąd w WebSocket listener: {e}", exc_info=True)
        finally:
            if topic in self.ws_connections:
                del self.ws_connections[topic]
    
    async def unsubscribe(self, pair: str, stream_type: str) -> bool:
        """Anulowanie subskrypcji WebSocket na KuCoin"""
        try:
            symbol = self.normalize_pair(pair)
            
            if stream_type == 'ticker':
                topic = f"/market/ticker:{symbol}"
            elif stream_type == 'trades':
                topic = f"/market/match:{symbol}"
            elif stream_type == 'orderbook':
                topic = f"/market/level2:{symbol}"
            else:
                return False
            
            # Wyślij unsubscribe jeśli połączenie istnieje
            if topic in self.ws_connections:
                websocket = self.ws_connections[topic]
                if not websocket.closed:
                    unsubscribe_msg = {
                        "id": str(int(time.time() * 1000)),
                        "type": "unsubscribe",
                        "topic": topic,
                        "privateChannel": False,
                        "response": True
                    }
                    await websocket.send(json.dumps(unsubscribe_msg))
                    await websocket.close()
                
                del self.ws_connections[topic]
            
            # Usuń callback
            callback_key = f"{pair}_{stream_type}"
            if callback_key in self.ws_callbacks:
                del self.ws_callbacks[callback_key]
            
            return True
        except Exception as e:
            logger.error(f"Błąd podczas anulowania subskrypcji KuCoin {pair}: {e}", exc_info=True)
            return False
    
    async def make_request(self, method: str, endpoint: str, params: Dict = None,
                          signed: bool = False, data: Dict = None) -> Optional[Dict]:
        """Wykonanie requestu HTTP do KuCoin API"""
        try:
            await self.rate_limit()
            if not self.session:
                raise Exception("Brak aktywnej sesji HTTP")
            url = f"{self.base_url}{endpoint}"
            headers = {'Content-Type': 'application/json'}
            if signed and self.api_key:
                timestamp = str(int(time.time() * 1000))
                body = ''
                if data:
                    body = json.dumps(data, separators=(',', ':'))
                elif method.upper() == 'GET' and params:
                    query_string = urlencode(sorted(params.items()))
                    endpoint = f"{endpoint}?{query_string}"
                signature = self.generate_signature(timestamp, method, endpoint, body)
                passphrase_sig = self.generate_passphrase_signature()
                headers.update({
                    'KC-API-KEY': self.api_key,
                    'KC-API-SIGN': signature,
                    'KC-API-TIMESTAMP': timestamp,
                    'KC-API-PASSPHRASE': passphrase_sig,
                    'KC-API-KEY-VERSION': '2'
                })
            request_params = params if method.upper() == 'GET' and not signed else None
            request_data = data if method.upper() != 'GET' else None
            # Zaktualizuj URL po ewentualnym modyfikowaniu endpointu (np. dodaniu query string)
            url = f"{self.base_url}{endpoint}"
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
                    try:
                        error_data = json.loads(error_text)
                        error_msg = error_data.get('msg', error_text)
                        error_code = error_data.get('code', response.status)
                        raise Exception(f"KuCoin API Error {error_code}: {error_msg}")
                    except json.JSONDecodeError:
                        raise Exception(f"HTTP {response.status}: {error_text}")
        except Exception as e:
            logger.error(f"Błąd requestu KuCoin {method} {endpoint}: {e}", exc_info=True)
            return None
    
    async def get_exchange_name(self) -> str:
        return "KuCoin"
    
    async def get_symbol_info(self, pair: str) -> Dict:
        try:
            symbol = self.normalize_pair(pair)
            if not hasattr(self, 'symbols_info'):
                self.symbols_info = {}
            if symbol in self.symbols_info:
                return self.symbols_info[symbol]
            # Attempt to load exchange info if missing
            await self.load_exchange_info()
            return self.symbols_info.get(symbol, {
                'base_asset': pair.split('/')[0].upper() if '/' in pair else symbol.split('-')[0],
                'quote_asset': pair.split('/')[1].upper() if '/' in pair else symbol.split('-')[1],
                'status': 'UNKNOWN'
            })
        except Exception as e:
            logger.error(f"Błąd podczas pobierania informacji o symbolu KuCoin {pair}: {e}", exc_info=True)
            return {}
    
    async def get_websocket_statistics(self) -> Dict:
        try:
            return {
                'connections': len(self.ws_connections),
                'topics': list(self.ws_connections.keys()),
                'callbacks': len(self.ws_callbacks)
            }
        except Exception:
            return {'connections': 0, 'topics': [], 'callbacks': 0}
    
    async def place_order(self, pair: str, side: str, order_type: str, quantity: float, price: Optional[float] = None) -> Dict:
        try:
            result = await self.create_order(pair=pair, side=side, amount=quantity, price=price, order_type=order_type)
            return result or {}
        except Exception as e:
            logger.error(f"Błąd podczas składania zlecenia KuCoin {pair}: {e}", exc_info=True)
            return {}