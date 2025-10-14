"""
Adapter dla giełdy Coinbase Pro (Advanced Trade)
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

class CoinbaseExchange(BaseExchange):
    """
    Adapter dla giełdy Coinbase Pro (Advanced Trade)
    
    Implementuje interfejs dla handlu na Coinbase Pro
    poprzez REST API i WebSocket.
    """
    
    def __init__(self, api_key: str, api_secret: str, passphrase: Optional[str] = None, testnet: bool = False):
        super().__init__(api_key, api_secret, testnet)
        self.passphrase = passphrase or ''
        if testnet:
            self.base_url = "https://api-public.sandbox.exchange.coinbase.com"
            self.ws_url = "wss://ws-feed-public.sandbox.exchange.coinbase.com"
        else:
            self.base_url = "https://api.exchange.coinbase.com"
            self.ws_url = "wss://ws-feed.exchange.coinbase.com"
        self.min_request_interval = 0.1
        self.api_version = ""

    async def test_connection(self) -> bool:
        """Test połączenia z Coinbase API"""
        try:
            response = await self.make_request('GET', '/time')
            return response is not None and 'iso' in response
            
        except Exception as e:
            raise Exception(f"Test połączenia Coinbase nieudany: {e}")
    
    async def load_exchange_info(self):
        """Wczytanie informacji o giełdzie Coinbase"""
        try:
            response = await self.make_request('GET', '/products')
            
            if response and isinstance(response, list):
                self.exchange_info = {'products': response}
                
                # Cache symbol information
                for product in response:
                    symbol_name = product['id']
                    
                    self.symbols_info[symbol_name] = {
                        'base_asset': product['base_currency'],
                        'quote_asset': product['quote_currency'],
                        'status': product.get('status', 'online'),
                        'lot_size': float(product.get('base_increment', '0.001')),
                        'tick_size': float(product.get('quote_increment', '0.01')),
                        'min_order_qty': float(product.get('min_market_funds', '1')),
                        'max_order_qty': float(product.get('max_market_funds', '1000000')),
                        'min_order_amt': float(product.get('min_market_funds', '1')),
                        'max_order_amt': float(product.get('max_market_funds', '1000000')),
                        'post_only': product.get('post_only', False),
                        'limit_only': product.get('limit_only', False),
                        'cancel_only': product.get('cancel_only', False)
                    }
                    
        except Exception as e:
            raise Exception(f"Błąd podczas wczytywania informacji o giełdzie Coinbase: {e}")
    
    def generate_signature(self, timestamp: str, method: str, path: str, body: str = '') -> str:
        """Generowanie podpisu HMAC SHA256 dla Coinbase"""
        message = timestamp + method.upper() + path + body
        signature = base64.b64encode(
            hmac.new(
                base64.b64decode(self.api_secret),
                message.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
        return signature
    
    def normalize_pair(self, pair: str) -> str:
        """Normalizacja pary dla Coinbase (BTC-USD)"""
        return pair.replace('/', '-').upper()
    
    def denormalize_pair(self, pair: str) -> str:
        """Denormalizacja pary z Coinbase do formatu standardowego"""
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
        """Pobranie salda z Coinbase"""
        try:
            response = await self.make_request('GET', '/accounts', signed=True)
            
            if not response or not isinstance(response, list):
                return {}
            
            balances = {}
            
            for account in response:
                asset = account['currency']
                available = float(account.get('available', '0') or 0)
                hold = float(account.get('hold', '0') or 0)
                if available > 0 or hold > 0:
                    balances[asset] = {
                        'free': available,
                        'locked': hold,
                        'total': available + hold,
                    }
            if currency:
                return balances.get(currency.upper(), {'free': 0.0, 'locked': 0.0, 'total': 0.0})
            return balances
        except Exception as e:
            logger.error(f"Błąd podczas pobierania salda Coinbase: {e}", exc_info=True)
            return {}

    @net_guard('exchange:get_current_price')
    async def get_current_price(self, pair: str) -> Optional[float]:
        try:
            symbol = self.normalize_pair(pair)
            response = await self.make_request('GET', f'/products/{symbol}/ticker')
            if response and 'price' in response:
                return float(response['price'])
            return None
        except Exception as e:
            logger.error(f"Błąd podczas pobierania ceny Coinbase {pair}: {e}", exc_info=True)
            return None

    @net_guard('exchange:get_order_book')
    async def get_order_book(self, pair: str, limit: int = 100) -> Dict:
        try:
            symbol = self.normalize_pair(pair)
            level = 2 if limit <= 50 else 3
            params = {'level': level}
            response = await self.make_request('GET', f'/products/{symbol}/book', params=params)
            if response and 'bids' in response and 'asks' in response:
                return {
                    'bids': [[float(price), float(amount)] for price, amount, *_ in response['bids'][:limit]],
                    'asks': [[float(price), float(amount)] for price, amount, *_ in response['asks'][:limit]],
                    'timestamp': response.get('time')
                }
            return {'bids': [], 'asks': [], 'timestamp': None}
        except Exception as e:
            logger.error(f"Błąd podczas pobierania księgi zleceń Coinbase {pair}: {e}", exc_info=True)
            return {'bids': [], 'asks': [], 'timestamp': None}

    @net_guard('exchange:create_order')
    async def create_order(self, pair: str, side: str, amount: float,
                           price: Optional[float] = None, order_type: str = 'market',
                           **kwargs) -> Optional[Dict]:
        try:
            symbol = self.normalize_pair(pair)
            formatted_amount = self.format_amount(pair, amount)
            order_data: Dict[str, Any] = {
                'product_id': symbol,
                'side': side.lower(),
                'type': order_type.lower(),
            }
            if order_type.lower() == 'market':
                if side.lower() == 'buy':
                    if price:
                        order_data['funds'] = str(self.format_price(pair, price) * formatted_amount)
                    else:
                        current_price = await self.get_current_price(pair)
                        if current_price:
                            order_data['funds'] = str(current_price * formatted_amount)
                        else:
                            raise ValueError("Nie można określić ceny dla zlecenia market buy")
                else:
                    order_data['size'] = str(formatted_amount)
            else:
                if price is None:
                    raise ValueError("Cena jest wymagana dla zlecenia limit")
                formatted_price = self.format_price(pair, price)
                order_data['price'] = str(formatted_price)
                order_data['size'] = str(formatted_amount)
                order_data['time_in_force'] = kwargs.get('time_in_force', 'GTC')
                if kwargs.get('post_only', False):
                    order_data['post_only'] = True
            response = await self.make_request('POST', '/orders', data=order_data, signed=True)
            if response and 'id' in response:
                return {
                    'id': response.get('id'),
                    'symbol': self.denormalize_pair(symbol),
                    'side': side.lower(),
                    'amount': float(formatted_amount),
                    'price': float(price) if price else 0,
                    'type': order_type.lower(),
                    'status': response.get('status', 'pending').lower(),
                    'timestamp': int(time.time() * 1000),
                    'raw': response
                }
            return None
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia zlecenia Coinbase {pair}: {e}", exc_info=True)
            return None

    @net_guard('exchange:cancel_order')
    async def cancel_order(self, order_id: str, pair: str) -> bool:
        try:
            response = await self.make_request('DELETE', f'/orders/{order_id}', signed=True)
            return response is not None and (response == order_id or 'id' in response)
        except Exception as e:
            logger.error(f"Błąd podczas anulowania zlecenia Coinbase {order_id}: {e}", exc_info=True)
            return False

    @net_guard('exchange:get_order_status')
    async def get_order_status(self, order_id: str, pair: str) -> Optional[Dict]:
        try:
            response = await self.make_request('GET', f'/orders/{order_id}', signed=True)
            if response and 'id' in response:
                filled_size = float(response.get('filled_size', 0) or 0)
                executed_value = float(response.get('executed_value', 0) or 0)
                avg_price = executed_value / filled_size if filled_size > 0 else 0
                return {
                    'id': response.get('id'),
                    'symbol': self.denormalize_pair(response.get('product_id', '')),
                    'side': response.get('side', '').lower(),
                    'amount': float(response.get('size', 0) or 0),
                    'filled': filled_size,
                    'price': float(response.get('price', 0) or 0),
                    'average_price': avg_price,
                    'type': response.get('type', '').lower(),
                    'status': response.get('status', '').lower(),
                    'timestamp': self._parse_coinbase_time(response.get('created_at')),
                    'update_time': self._parse_coinbase_time(response.get('done_at', response.get('created_at'))),
                    'raw': response,
                }
            return None
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania statusu zlecenia Coinbase {order_id}: {e}", exc_info=True)
            return None

    def _parse_coinbase_time(self, time_str: Optional[str]) -> int:
        try:
            if time_str:
                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                return int(dt.timestamp() * 1000)
            return 0
        except Exception:
            return 0

    @net_guard('exchange:get_open_orders')
    async def get_open_orders(self, pair: Optional[str] = None) -> List[Dict]:
        try:
            params: Dict[str, Any] = {'status': ['open', 'pending']}
            if pair:
                params['product_id'] = self.normalize_pair(pair)
            response = await self.make_request('GET', '/orders', params=params, signed=True)
            if response and isinstance(response, list):
                orders: List[Dict] = []
                for order in response:
                    orders.append({
                        'id': order.get('id'),
                        'symbol': self.denormalize_pair(order.get('product_id', '')),
                        'side': order.get('side', '').lower(),
                        'amount': float(order.get('size', 0) or 0),
                        'filled': float(order.get('filled_size', 0) or 0),
                        'price': float(order.get('price', 0) or 0),
                        'type': order.get('type', '').lower(),
                        'status': order.get('status', '').lower(),
                        'timestamp': self._parse_coinbase_time(order.get('created_at')),
                        'raw': order,
                    })
                return orders
            return []
        except Exception as e:
            logger.error(f"Błąd podczas pobierania otwartych zleceń Coinbase: {e}", exc_info=True)
            return []

    @net_guard('exchange:get_trade_history')
    async def get_trade_history(self, pair: str, limit: int = 100,
                                start_time: Optional[int] = None,
                                end_time: Optional[int] = None) -> List[Dict]:
        try:
            symbol = self.normalize_pair(pair)
            params: Dict[str, Any] = {
                'product_id': symbol,
                'limit': min(limit, 1000)
            }
            if start_time:
                params['start_date'] = datetime.fromtimestamp(start_time / 1000).isoformat()
            if end_time:
                params['end_date'] = datetime.fromtimestamp(end_time / 1000).isoformat()
            response = await self.make_request('GET', '/fills', params=params, signed=True)
            if response and isinstance(response, list):
                trades: List[Dict] = []
                for trade in response:
                    trades.append({
                        'id': trade.get('trade_id'),
                        'order_id': trade.get('order_id'),
                        'symbol': self.denormalize_pair(trade.get('product_id', '')),
                        'side': trade.get('side', '').lower(),
                        'amount': float(trade.get('size', 0) or 0),
                        'price': float(trade.get('price', 0) or 0),
                        'fee': float(trade.get('fee', 0) or 0),
                        'fee_asset': trade.get('fee_currency', ''),
                        'timestamp': self._parse_coinbase_time(trade.get('created_at')),
                        'is_maker': trade.get('liquidity') == 'M',
                        'raw': trade,
                    })
                return trades
            return []
        except Exception as e:
            logger.error(f"Błąd podczas pobierania historii transakcji Coinbase {pair}: {e}", exc_info=True)
            return []

    @net_guard('exchange:get_klines')
    async def get_klines(self, pair: str, interval: str = '60', limit: int = 100,
                         start_time: Optional[int] = None,
                         end_time: Optional[int] = None) -> List[Dict]:
        try:
            symbol = self.normalize_pair(pair)
            granularity = self._convert_interval_to_granularity(interval)
            params: Dict[str, Any] = {
                'granularity': granularity
            }
            if start_time:
                params['start'] = datetime.fromtimestamp(start_time / 1000).isoformat()
            if end_time:
                params['end'] = datetime.fromtimestamp(end_time / 1000).isoformat()
            response = await self.make_request('GET', f'/products/{symbol}/candles', params=params)
            if response and isinstance(response, list):
                klines: List[Dict] = []
                for kline in response:
                    klines.append({
                        'timestamp': int(kline[0]) * 1000,
                        'low': float(kline[1]),
                        'high': float(kline[2]),
                        'open': float(kline[3]),
                        'close': float(kline[4]),
                        'volume': float(kline[5]),
                    })
                return list(reversed(klines))[:limit]
            return []
        except Exception as e:
            logger.error(f"Błąd podczas pobierania klines Coinbase {pair}: {e}", exc_info=True)
            return []

    def _convert_interval_to_granularity(self, interval: str) -> int:
        interval_map = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '1h': 3600,
            '6h': 21600,
            '1d': 86400,
        }
        return interval_map.get(interval, 60)

    async def subscribe_ticker(self, pair: str, callback) -> bool:
        try:
            symbol = self.normalize_pair(pair)
            channel = "ticker"
            return await self._subscribe_websocket(channel, [symbol], callback, 'ticker', pair)
        except Exception as e:
            logger.error(f"Błąd podczas subskrypcji ticker Coinbase {pair}: {e}", exc_info=True)
            return False

    async def subscribe_trades(self, pair: str, callback) -> bool:
        try:
            symbol = self.normalize_pair(pair)
            channel = "matches"
            return await self._subscribe_websocket(channel, [symbol], callback, 'trades', pair)
        except Exception as e:
            logger.error(f"Błąd podczas subskrypcji trades Coinbase {pair}: {e}", exc_info=True)
            return False

    async def subscribe_order_book(self, pair: str, callback) -> bool:
        try:
            symbol = self.normalize_pair(pair)
            channel = "level2"
            return await self._subscribe_websocket(channel, [symbol], callback, 'orderbook', pair)
        except Exception as e:
            logger.error(f"Błąd podczas subskrypcji orderbook Coinbase {pair}: {e}", exc_info=True)
            return False

    async def _subscribe_websocket(self, channel: str, product_ids: List[str],
                                   callback, stream_type: str, pair: str) -> bool:
        try:
            topic = f"{channel}_{product_ids[0]}"
            if topic in self.ws_connections:
                await self.ws_connections[topic].close()
            websocket = await websockets.connect(self.ws_url, open_timeout=10, ping_interval=20, ping_timeout=10)
            self.ws_connections[topic] = websocket
            subscribe_msg = {
                "type": "subscribe",
                "channels": [
                    {
                        "name": channel,
                        "product_ids": product_ids
                    }
                ]
            }
            await websocket.send(json.dumps(subscribe_msg))
            callback_key = f"{pair}_{stream_type}"
            self.ws_callbacks[callback_key] = callback
            asyncio.create_task(self._websocket_listener(websocket, topic, stream_type, pair))
            return True
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia połączenia WebSocket Coinbase: {e}", exc_info=True)
            return False

    async def _websocket_listener(self, websocket, topic: str, stream_type: str, pair: str):
        try:
            async for message in websocket:
                from core.websocket_callback_manager import WebSocketEventType
                event_type_map = {
                    'ticker': WebSocketEventType.TICKER,
                    'trades': WebSocketEventType.TRADES,
                    'orderbook': WebSocketEventType.ORDER_BOOK,
                    'kline': WebSocketEventType.KLINE,
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
        try:
            symbol = self.normalize_pair(pair)
            if stream_type == 'ticker':
                channel = "ticker"
            elif stream_type == 'trades':
                channel = "matches"
            elif stream_type == 'orderbook':
                channel = "level2"
            else:
                return False
            topic = f"{channel}_{symbol}"
            if topic in self.ws_connections:
                websocket = self.ws_connections[topic]
                if not websocket.closed:
                    unsubscribe_msg = {
                        "type": "unsubscribe",
                        "channels": [
                            {
                                "name": channel,
                                "product_ids": [symbol]
                            }
                        ]
                    }
                    await websocket.send(json.dumps(unsubscribe_msg))
                    await websocket.close()
                del self.ws_connections[topic]
            callback_key = f"{pair}_{stream_type}"
            if callback_key in self.ws_callbacks:
                del self.ws_callbacks[callback_key]
            return True
        except Exception as e:
            logger.error(f"Błąd podczas anulowania subskrypcji Coinbase {pair}: {e}", exc_info=True)
            return False

    async def make_request(self, method: str, endpoint: str, params: Dict = None,
                          signed: bool = False, data: Dict = None) -> Optional[Dict]:
        try:
            await self.rate_limit()
            if not self.session:
                raise Exception("Brak aktywnej sesji HTTP")
            url = f"{self.base_url}{endpoint}"
            headers = {'Content-Type': 'application/json'}
            if signed and self.api_key:
                timestamp = str(time.time())
                path = endpoint
                if method.upper() == 'GET' and params:
                    query_string = urlencode(sorted(params.items()))
                    path = f"{endpoint}?{query_string}"
                body = ''
                if data:
                    body = json.dumps(data, separators=(',', ':'))
                signature = self.generate_signature(timestamp, method, path, body)
                headers.update({
                    'CB-ACCESS-KEY': self.api_key,
                    'CB-ACCESS-SIGN': signature,
                    'CB-ACCESS-TIMESTAMP': timestamp,
                    'CB-ACCESS-PASSPHRASE': self.passphrase if hasattr(self, 'passphrase') else ''
                })
            request_params = params if method.upper() == 'GET' else None
            request_data = data if method.upper() != 'GET' else None
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
                        error_msg = error_data.get('message', error_text)
                        raise Exception(f"Coinbase API Error {response.status}: {error_msg}")
                    except json.JSONDecodeError:
                        raise Exception(f"HTTP {response.status}: {error_text}")
        except Exception as e:
            logger.error(f"Błąd requestu Coinbase {method} {endpoint}: {e}", exc_info=True)
            return None

    # Dodatkowe metody wymagane przez BaseExchange
    async def get_exchange_name(self) -> str:
        return "coinbase"

    async def get_symbol_info(self, pair: str) -> Dict:
        symbol = self.normalize_pair(pair)
        if symbol not in self.symbols_info:
            await self.load_exchange_info()
        return self.symbols_info.get(symbol, {})

    async def get_websocket_statistics(self) -> Dict:
        connections = list(self.ws_connections.values())
        connected = any(getattr(ws, 'open', False) and not getattr(ws, 'closed', False) for ws in connections)
        return {
            'connections_count': len(self.ws_connections),
            'callbacks_count': len(self.ws_callbacks),
            'connected': connected,
        }

    async def place_order(self, pair: str, side: str, order_type: str, quantity: float, price: Optional[float] = None) -> Dict:
        order = await self.create_order(pair, side, quantity, price, order_type)
        return order or {}