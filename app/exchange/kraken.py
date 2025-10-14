"""
Adapter dla giełdy Kraken
"""

import asyncio
import base64
import hashlib
import hmac
import json
import time
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional, Any
import websockets

from .base_exchange import BaseExchange
import logging
from utils.net_wrappers import net_guard
from utils.http_logging import log_request
logger = logging.getLogger(__name__)


class KrakenExchange(BaseExchange):
    """
    Adapter dla giełdy Kraken
    
    Implementuje pełny interfejs dla handlu na Kraken
    poprzez REST API i WebSocket.
    """
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False, sandbox: bool = None):
        # Map sandbox -> testnet for compatibility
        if sandbox is not None:
            testnet = bool(sandbox)
        super().__init__(api_key, api_secret, testnet)
        
        # Nazwa giełdy
        self.name = 'kraken'
        
        # Kraken nie ma oficjalnej sieci testowej
        self.base_url = "https://api.kraken.com"
        self.ws_url = "wss://ws.kraken.com"
        
        # Kraken specific settings
        self.min_request_interval = 0.5  # 500ms - Kraken ma niższe limity
        self.api_version = "0"
        
        # Kraken używa innych nazw par
        self.pair_mapping = {
            'BTC/USD': 'XXBTZUSD',
            'BTC/USDT': 'XBTUSDT',
            'ETH/USD': 'XETHZUSD',
            'ETH/USDT': 'ETHUSDT',
            'ETH/BTC': 'XETHXXBT',
            'LTC/USD': 'XLTCZUSD',
            'LTC/BTC': 'XLTCXXBT',
            'XRP/USD': 'XXRPZUSD',
            'XRP/BTC': 'XXRPXXBT',
            'ADA/USD': 'ADAUSD',
            'ADA/BTC': 'ADAXXBT',
            'DOT/USD': 'DOTUSD',
            'DOT/BTC': 'DOTXXBT'
        }
        
        # Reverse mapping
        self.reverse_pair_mapping = {v: k for k, v in self.pair_mapping.items()}
        
        # WebSocket token
        self.ws_token = None
    
    async def test_connection(self) -> bool:
        """Test połączenia z Kraken API"""
        try:
            response = await self.make_request('GET', '/0/public/SystemStatus')
            return response and response.get('error') == []
            
        except Exception as e:
            raise Exception(f"Test połączenia Kraken nieudany: {e}")
    
    async def load_exchange_info(self):
        """Wczytanie informacji o giełdzie Kraken"""
        try:
            response = await self.make_request('GET', '/0/public/AssetPairs')
            
            if response and response.get('error') == []:
                result = response.get('result', {})
                self.exchange_info = result
                
                # Cache symbol information
                for pair_name, pair_info in result.items():
                    # Kraken używa różnych nazw dla par
                    base = pair_info.get('base', '')
                    quote = pair_info.get('quote', '')
                    
                    # Normalizuj nazwy assetów
                    base = self._normalize_asset_name(base)
                    quote = self._normalize_asset_name(quote)
                    
                    normalized_pair = f"{base}/{quote}"
                    
                    self.symbols_info[pair_name] = {
                        'base_asset': base,
                        'quote_asset': quote,
                        'normalized_pair': normalized_pair,
                        'status': 'TRADING',  # Kraken nie ma statusu jak Binance
                        'lot_decimals': pair_info.get('lot_decimals', 8),
                        'pair_decimals': pair_info.get('pair_decimals', 5),
                        'lot_multiplier': pair_info.get('lot_multiplier', 1),
                        'ordermin': float(pair_info.get('ordermin', '0')),
                        'costmin': float(pair_info.get('costmin', '0')),
                        'tick_size': 10 ** (-pair_info.get('pair_decimals', 5)),
                        'lot_size': 10 ** (-pair_info.get('lot_decimals', 8)),
                        'fees': pair_info.get('fees', []),
                        'fees_maker': pair_info.get('fees_maker', [])
                    }
                    
        except Exception as e:
            raise Exception(f"Błąd podczas wczytywania informacji o giełdzie: {e}")
    
    def _normalize_asset_name(self, asset: str) -> str:
        """Normalizacja nazw assetów Kraken"""
        # Kraken używa prefiksów X i Z
        asset_mapping = {
            'XXBT': 'BTC',
            'XETH': 'ETH',
            'XLTC': 'LTC',
            'XXRP': 'XRP',
            'ZUSD': 'USD',
            'ZEUR': 'EUR',
            'ZGBP': 'GBP',
            'ZJPY': 'JPY'
        }
        
        return asset_mapping.get(asset, asset)
    
    def generate_signature(self, endpoint: str, data: str, nonce: str) -> str:
        """Generowanie podpisu dla Kraken API"""
        # Kraken używa specjalnego sposobu generowania podpisu
        postdata = urllib.parse.urlencode(data) if isinstance(data, dict) else data
        encoded = (nonce + postdata).encode()
        message = endpoint.encode() + hashlib.sha256(encoded).digest()
        
        signature = hmac.new(
            base64.b64decode(self.api_secret),
            message,
            hashlib.sha512
        )
        
        return base64.b64encode(signature.digest()).decode()
    
    def normalize_pair(self, pair: str) -> str:
        """Normalizacja pary dla Kraken"""
        # Sprawdź czy para jest w mapowaniu
        if pair in self.pair_mapping:
            return self.pair_mapping[pair]
        
        # Jeśli nie, spróbuj znaleźć w symbols_info
        for kraken_pair, info in self.symbols_info.items():
            if info.get('normalized_pair') == pair:
                return kraken_pair
        
        # Ostatnia próba - usuń / i zamień na wielkie litery
        return pair.replace('/', '').upper()
    
    def denormalize_pair(self, kraken_pair: str) -> str:
        """Konwersja pary Kraken na standardowy format"""
        if kraken_pair in self.reverse_pair_mapping:
            return self.reverse_pair_mapping[kraken_pair]
        
        # Sprawdź w symbols_info
        if kraken_pair in self.symbols_info:
            return self.symbols_info[kraken_pair].get('normalized_pair', kraken_pair)
        
        return kraken_pair
    
    async def _make_request(self, method: str, endpoint: str, params: Dict = None, signed: bool = False) -> Optional[Dict]:
        """Alias do make_request używany przez testy do patchowania"""
        return await self.make_request(method, endpoint, params, signed)
    async def make_request(self, method: str, endpoint: str, params: Dict = None, signed: bool = False) -> Optional[Dict]:
        """Wykonanie zapytania HTTP do Kraken API"""
        try:
            # Rate limiting
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.min_request_interval:
                await asyncio.sleep(self.min_request_interval - time_since_last)
            
            if not self.session:
                import aiohttp
                self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
            
            url = f"{self.base_url}{endpoint}"
            headers = {
                'User-Agent': 'Kraken Trading Bot 1.0'
            }
            
            if signed:
                if not params:
                    params = {}
                
                # Dodaj nonce
                nonce = str(int(time.time() * 1000000))
                params['nonce'] = nonce
                
                # Generuj podpis
                signature = self.generate_signature(endpoint, params, nonce)
                
                headers.update({
                    'API-Key': self.api_key,
                    'API-Sign': signature
                })
            
            self.last_request_time = time.time()
            # BEFORE any HTTP call, apply global rate limiter
            await self.rate_limit()
            if method == 'GET':
                if params:
                    import urllib.parse
                    url += '?' + urllib.parse.urlencode(params)
                # Sanityzowane logowanie żądania HTTP
                log_request(logger, method, url, headers=headers, params=params, json_body=None)
                async with self.session.get(url, headers=headers) as response:
                    return await response.json()
            elif method == 'POST':
                # Sanityzowane logowanie żądania HTTP
                log_request(logger, method, url, headers=headers, params=None, json_body=params)
                async with self.session.post(url, data=params, headers=headers) as response:
                    return await response.json()

        except Exception as e:
            self.logger.error(f"Błąd zapytania Kraken API: {e}", exc_info=True)
            return None
    
    @net_guard('exchange:get_current_price')
    async def get_current_price(self, pair: str) -> Optional[float]:
        """Pobranie aktualnej ceny"""
        kraken_pair = self.normalize_pair(pair)
        response = await self._make_request('GET', '/0/public/Ticker', {'pair': kraken_pair})
        
        if response and response.get('error') == []:
            result = response.get('result', {})
            if kraken_pair in result:
                ticker_data = result[kraken_pair]
                return float(ticker_data['c'][0])  # Last trade price
        
        return None

    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Pobierz ticker dla symbolu"""
        try:
            kraken_pair = self.normalize_pair(symbol)
            response = await self.make_request('GET', '/0/public/Ticker', {'pair': kraken_pair})
            
            if response and response.get('error') == []:
                result = response.get('result', {})
                if kraken_pair in result:
                    ticker_data = result[kraken_pair]
                    
                    return {
                        'symbol': symbol,
                        'price': float(ticker_data['c'][0]),  # Last trade price
                        'bid': float(ticker_data['b'][0]),    # Best bid
                        'ask': float(ticker_data['a'][0]),    # Best ask
                        'volume': float(ticker_data['v'][1]), # 24h volume
                        'high': float(ticker_data['h'][1]),   # 24h high
                        'low': float(ticker_data['l'][1]),    # 24h low
                        'change': float(ticker_data['c'][0]) - float(ticker_data['o']),  # Price change
                        'change_percent': ((float(ticker_data['c'][0]) - float(ticker_data['o'])) / float(ticker_data['o'])) * 100,
                        'timestamp': datetime.now()
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania ticker Kraken: {e}", exc_info=True)
            return None

    async def get_order_book(self, symbol: str, limit: int = 100) -> Optional[Dict]:
        """Pobierz księgę zleceń"""
        try:
            kraken_pair = self.normalize_pair(symbol)
            params = {'pair': kraken_pair, 'count': min(limit, 500)}  # Kraken max 500
            
            response = await self.make_request('GET', '/0/public/Depth', params)
            
            if response and response.get('error') == []:
                result = response.get('result', {})
                if kraken_pair in result:
                    order_book = result[kraken_pair]
                    
                    return {
                        'symbol': symbol,
                        'bids': [[float(price), float(volume)] for price, volume, _ in order_book.get('bids', [])],
                        'asks': [[float(price), float(volume)] for price, volume, _ in order_book.get('asks', [])],
                        'timestamp': datetime.now()
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania order book Kraken: {e}", exc_info=True)
            return None
    @net_guard('exchange:get_klines')
    async def get_klines(self, pair: str, interval: str = '1m', 
                        limit: int = 100, start_time: Optional[int] = None,
                        end_time: Optional[int] = None) -> List[Dict]:
        """Pobranie danych OHLCV (świece) - implementacja metody abstrakcyjnej"""
        result = await self.get_ohlcv(pair, interval, limit)
        return result if result else []

    async def get_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> Optional[List[Dict]]:
        """Pobierz dane OHLCV"""
        try:
            kraken_pair = self.normalize_pair(symbol)
            
            # Mapowanie timeframe
            timeframe_mapping = {
                '1m': 1,
                '5m': 5,
                '15m': 15,
                '30m': 30,
                '1h': 60,
                '4h': 240,
                '1d': 1440,
                '1w': 10080
            }
            
            interval = timeframe_mapping.get(timeframe, 60)
            params = {
                'pair': kraken_pair,
                'interval': interval
            }
            
            response = await self.make_request('GET', '/0/public/OHLC', params)
            
            if response and response.get('error') == []:
                result = response.get('result', {})
                if kraken_pair in result:
                    ohlc_data = result[kraken_pair]
                    
                    candles = []
                    for candle in ohlc_data[-limit:]:  # Ostatnie 'limit' świec
                        candles.append({
                            'timestamp': int(candle[0]),
                            'open': float(candle[1]),
                            'high': float(candle[2]),
                            'low': float(candle[3]),
                            'close': float(candle[4]),
                            'volume': float(candle[6])
                        })
                    
                    return candles
            
            return None
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania OHLCV Kraken: {e}", exc_info=True)
            return None

    @net_guard('exchange:get_balance')
    async def get_balance(self, currency: Optional[str] = None) -> Optional[Dict]:
        """Pobierz saldo konta. Jeśli podano currency, zwraca słownik z kluczami free/used/total dla tej waluty."""
        response = await self._make_request('POST', '/0/private/Balance', signed=True)
        
        if response and response.get('error') == []:
            result = response.get('result', {})
            
            normalized_balance: Dict[str, Dict[str, float]] = {}
            for asset, balance in result.items():
                normalized_asset = self._normalize_asset_name(asset)
                bal = float(balance)
                normalized_balance[normalized_asset] = {
                    'free': bal,
                    'used': 0.0,  # Kraken nie rozróżnia free/locked w tym endpoint
                    'total': bal
                }
            
            if currency:
                cur = currency.upper()
                if cur in normalized_balance:
                    return normalized_balance[cur]
                return {'free': 0.0, 'used': 0.0, 'total': 0.0}
            
            # Jeśli nie podano currency, zwróć pełny słownik z walutami
            return normalized_balance
        
        return None

    async def create_order(
        self,
        pair: Optional[str] = None,
        side: Optional[str] = None,
        amount: Optional[float] = None,
        price: Optional[float] = None,
        order_type: str = 'market',
        **kwargs
    ) -> Optional[Dict]:
        """Utworzenie zlecenia (implementacja metody abstrakcyjnej). Obsługuje symbol/type z kwargs."""
        if pair is None:
            pair = kwargs.get('symbol')
        if 'type' in kwargs:
            order_type = kwargs.get('type') or order_type
        return await self.place_order(pair, side, amount, price, order_type)

    @net_guard('exchange:place_order')
    async def place_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float = None,
        order_type: str = 'market'
    ) -> Optional[Dict]:
        """Złóż zlecenie"""
        try:
            kraken_pair = self.normalize_pair(symbol)
            
            params = {
                'pair': kraken_pair,
                'type': side.lower(),  # buy/sell
                'ordertype': 'market' if order_type == 'market' else 'limit',
                'volume': str(amount)
            }
            
            if order_type == 'limit' and price:
                params['price'] = str(price)
            
            response = await self._make_request('POST', '/0/private/AddOrder', params, signed=True)
            
            if response and response.get('error') == []:
                result = response.get('result', {})
                order_id = result.get('txid', [''])[0]
                
                return {
                    'success': True,
                    'id': order_id,
                    'order_id': order_id,
                    'symbol': symbol,
                    'side': side,
                    'amount': amount,
                    'price': price,
                    'type': order_type,
                    'status': 'pending',
                    'timestamp': datetime.now()
                }
            else:
                errors = response.get('error', []) if isinstance(response, dict) else []
                return {
                    'success': False,
                    'error': ', '.join(errors) if errors else 'Unknown error'
                }
            
        except Exception as e:
            self.logger.error(f"Błąd składania zlecenia Kraken: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    @net_guard('exchange:cancel_order')
    async def cancel_order(self, order_id: str, pair: str) -> bool:
        """Anuluj zlecenie"""
        try:
            params = {'txid': order_id}
            response = await self.make_request('POST', '/0/private/CancelOrder', params, signed=True)
            
            return response and response.get('error') == []
            
        except Exception as e:
            self.logger.error(f"Błąd anulowania zlecenia Kraken: {e}", exc_info=True)
            return False

    @net_guard('exchange:get_order_status')
    async def get_order_status(self, order_id: str, pair: str) -> Optional[Dict]:
        """Sprawdź status zlecenia"""
        try:
            params = {'txid': order_id}
            response = await self.make_request('POST', '/0/private/QueryOrders', params, signed=True)
            
            if response and response.get('error') == []:
                result = response.get('result', {})
                if order_id in result:
                    order_data = result[order_id]
                    
                    # Mapowanie statusów Kraken
                    status_mapping = {
                        'pending': 'pending',
                        'open': 'open',
                        'closed': 'filled',
                        'canceled': 'canceled',
                        'expired': 'expired'
                    }
                    
                    status = status_mapping.get(order_data.get('status', ''), 'unknown')
                    
                    return {
                        'order_id': order_id,
                        'symbol': self.denormalize_pair(order_data.get('descr', {}).get('pair', '')),
                        'side': order_data.get('descr', {}).get('type', ''),
                        'amount': float(order_data.get('vol', 0)),
                        'filled': float(order_data.get('vol_exec', 0)),
                        'remaining': float(order_data.get('vol', 0)) - float(order_data.get('vol_exec', 0)),
                        'price': float(order_data.get('descr', {}).get('price', 0)),
                        'avg_price': float(order_data.get('price', 0)) if order_data.get('price') else None,
                        'status': status,
                        'timestamp': datetime.fromtimestamp(float(order_data.get('opentm', 0)))
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Błąd sprawdzania statusu zlecenia Kraken: {e}", exc_info=True)
            return None
    
    @net_guard('exchange:get_open_orders')
    async def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """Pobierz otwarte zlecenia"""
        try:
            response = await self.make_request('POST', '/0/private/OpenOrders', signed=True)
            
            if response and response.get('error') == []:
                result = response.get('result', {})
                open_orders = result.get('open', {})
                
                orders = []
                for order_id, order_data in open_orders.items():
                    order_symbol = self.denormalize_pair(order_data.get('descr', {}).get('pair', ''))
                    
                    # Filtruj po symbolu jeśli podano
                    if symbol and order_symbol != symbol:
                        continue
                    
                    orders.append({
                        'order_id': order_id,
                        'symbol': order_symbol,
                        'side': order_data.get('descr', {}).get('type', ''),
                        'amount': float(order_data.get('vol', 0)),
                        'filled': float(order_data.get('vol_exec', 0)),
                        'remaining': float(order_data.get('vol', 0)) - float(order_data.get('vol_exec', 0)),
                        'price': float(order_data.get('descr', {}).get('price', 0)),
                        'status': 'open',
                        'timestamp': datetime.fromtimestamp(float(order_data.get('opentm', 0)))
                    })
                
                return orders
            
            return []
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania otwartych zleceń Kraken: {e}", exc_info=True)
            return []
    
    @net_guard('exchange:get_trade_history')
    async def get_trade_history(self, symbol: str = None, limit: int = 100) -> List[Dict]:
        """Pobierz historię transakcji"""
        try:
            params = {}
            if limit:
                params['count'] = min(limit, 50)  # Kraken limit
            
            response = await self.make_request('POST', '/0/private/TradesHistory', params, signed=True)
            
            if response and response.get('error') == []:
                result = response.get('result', {})
                trades = result.get('trades', {})
                
                trade_list = []
                for trade_id, trade_data in trades.items():
                    trade_symbol = self.denormalize_pair(trade_data.get('pair', ''))
                    
                    # Filtruj po symbolu jeśli podano
                    if symbol and trade_symbol != symbol:
                        continue
                    
                    trade_list.append({
                        'trade_id': trade_id,
                        'order_id': trade_data.get('ordertxid', ''),
                        'symbol': trade_symbol,
                        'side': trade_data.get('type', ''),
                        'amount': float(trade_data.get('vol', 0)),
                        'price': float(trade_data.get('price', 0)),
                        'fee': float(trade_data.get('fee', 0)),
                        'timestamp': datetime.fromtimestamp(float(trade_data.get('time', 0)))
                    })
                
                # Sortuj po czasie (najnowsze pierwsze)
                trade_list.sort(key=lambda x: x['timestamp'], reverse=True)
                
                return trade_list[:limit] if limit else trade_list
            
            return []
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania historii transakcji Kraken: {e}", exc_info=True)
            return []

    @net_guard('exchange:get_trading_fees')
    async def get_trading_fees(self, symbol: str = None) -> Dict:
        try:
            # Kraken zwraca opłaty na poziomie rynku w dokumentacji, ale brak prostego endpointu do pobrania
            return {
                'maker': 0.0016,  # 0.16%
                'taker': 0.0026   # 0.26%
            }
        except Exception:
            return {'maker': 0.0016, 'taker': 0.0026}

    async def get_symbol_info(self, pair: str) -> Dict:
        """Zwróć podstawowe informacje o symbolu z cache lub mapowania"""
        try:
            # Spróbuj znaleźć w cache symboli
            for kraken_pair, info in getattr(self, 'symbols_info', {}).items():
                if info.get('normalized_pair') == pair:
                    return {
                        'symbol': pair,
                        'exchange_symbol': kraken_pair,
                        'base_asset': info.get('base_asset'),
                        'quote_asset': info.get('quote_asset'),
                        'status': info.get('status', 'TRADING'),
                        'tick_size': info.get('tick_size'),
                        'lot_size': info.get('lot_size')
                    }
            # Jeśli nie znaleziono, użyj mapowania
            exchange_symbol = self.pair_mapping.get(pair)
            base, quote = pair.split('/') if '/' in pair else (pair, '')
            return {
                'symbol': pair,
                'exchange_symbol': exchange_symbol or pair,
                'base_asset': base,
                'quote_asset': quote,
                'status': 'TRADING'
            }
        except Exception:
            return {'symbol': pair, 'status': 'UNKNOWN'}

    async def get_websocket_statistics(self) -> Dict:
        """Podstawowe statystyki WebSocket dla Kraken"""
        try:
            return {
                'connected': self.is_connected,
                'connections': len(self.ws_connections),
                'subscriptions': len(self.ws_callbacks) if hasattr(self, 'ws_callbacks') else 0
            }
        except Exception:
            return {'connected': False, 'connections': 0, 'subscriptions': 0}

    async def get_exchange_name(self) -> str:
        """Zwróć nazwę giełdy"""
        return self.name
    
    async def start_websocket(self, symbols: List[str], callback: callable):
        """Uruchom WebSocket dla subskrypcji danych"""
        try:
            # Kraken WebSocket wymaga tokena dla prywatnych danych
            if not self.ws_token:
                await self._get_ws_token()
            
            # Normalizuj symbole
            kraken_pairs = [self.normalize_pair(symbol) for symbol in symbols]
            
            # Subskrypcje
            subscriptions = [
                {
                    "name": "ticker",
                    "pair": kraken_pairs
                },
                {
                    "name": "book",
                    "pair": kraken_pairs,
                    "depth": 10
                }
            ]
            
            async with websockets.connect(self.ws_url, open_timeout=10, ping_interval=20, ping_timeout=10) as websocket:
                # Subskrybuj kanały
                for subscription in subscriptions:
                    subscribe_msg = {
                        "event": "subscribe",
                        "subscription": subscription
                    }
                    await websocket.send(json.dumps(subscribe_msg))
                
                # Słuchaj wiadomości
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        await self._handle_ws_message(data, callback)
                    except Exception as e:
                        self.logger.error(f"Błąd przetwarzania wiadomości WS: {e}")
                        
        except Exception as e:
            self.logger.error(f"Błąd WebSocket Kraken: {e}")
    
    async def _get_ws_token(self):
        """Pobierz token WebSocket"""
        try:
            response = await self.make_request('POST', '/0/private/GetWebSocketsToken', signed=True)
            
            if response and response.get('error') == []:
                result = response.get('result', {})
                self.ws_token = result.get('token')
                
        except Exception as e:
            self.logger.error(f"Błąd pobierania tokena WS: {e}")
    
    async def _handle_ws_message(self, data: Dict, callback: callable):
        """Obsłuż wiadomość WebSocket"""
        try:
            if isinstance(data, list) and len(data) >= 3:
                channel_data = data[1]
                channel_name = data[2]
                pair = data[3] if len(data) > 3 else None
                
                if 'ticker' in channel_name:
                    # Przetwórz dane ticker
                    ticker_info = {
                        'symbol': self.denormalize_pair(pair) if pair else '',
                        'price': float(channel_data.get('c', [0])[0]),
                        'bid': float(channel_data.get('b', [0])[0]),
                        'ask': float(channel_data.get('a', [0])[0]),
                        'volume': float(channel_data.get('v', [0])[1]),
                        'timestamp': datetime.now()
                    }
                    await callback('ticker', ticker_info)
                
                elif 'book' in channel_name:
                    # Przetwórz dane order book
                    book_data = {
                        'symbol': self.denormalize_pair(pair) if pair else '',
                        'bids': [[float(p), float(v)] for p, v, _ in channel_data.get('b', [])],
                        'asks': [[float(p), float(v)] for p, v, _ in channel_data.get('a', [])],
                        'timestamp': datetime.now()
                    }
                    await callback('orderbook', book_data)
                    
        except Exception as e:
            self.logger.error(f"Błąd obsługi wiadomości WS: {e}")
    
    async def subscribe_ticker(self, pair: str, callback) -> bool:
        """Subskrypcja ticker WebSocket"""
        try:
            kraken_pair = self.normalize_pair(pair)
            
            # Implementacja subskrypcji ticker dla Kraken
            subscription = {
                "event": "subscribe",
                "pair": [kraken_pair],
                "subscription": {"name": "ticker"}
            }
            
            # Tutaj byłaby implementacja WebSocket
            self.logger.info(f"Subskrypcja ticker dla {pair}")
            return True
            
        except Exception as e:
            self.logger.error(f"Błąd subskrypcji ticker Kraken: {e}")
            return False

    async def subscribe_trades(self, pair: str, callback) -> bool:
        """Subskrypcja transakcji WebSocket"""
        try:
            kraken_pair = self.normalize_pair(pair)
            
            # Implementacja subskrypcji trades dla Kraken
            subscription = {
                "event": "subscribe",
                "pair": [kraken_pair],
                "subscription": {"name": "trade"}
            }
            
            self.logger.info(f"Subskrypcja trades dla {pair}")
            return True
            
        except Exception as e:
            self.logger.error(f"Błąd subskrypcji trades Kraken: {e}")
            return False

    async def subscribe_order_book(self, pair: str, callback) -> bool:
        """Subskrypcja księgi zleceń WebSocket"""
        try:
            kraken_pair = self.normalize_pair(pair)
            
            # Implementacja subskrypcji order book dla Kraken
            subscription = {
                "event": "subscribe",
                "pair": [kraken_pair],
                "subscription": {"name": "book", "depth": 10}
            }
            
            self.logger.info(f"Subskrypcja order book dla {pair}")
            return True
            
        except Exception as e:
            self.logger.error(f"Błąd subskrypcji order book Kraken: {e}")
            return False

    async def unsubscribe(self, pair: str, stream_type: str) -> bool:
        """Anulowanie subskrypcji WebSocket"""
        try:
            kraken_pair = self.normalize_pair(pair)
            
            # Implementacja anulowania subskrypcji dla Kraken
            unsubscription = {
                "event": "unsubscribe",
                "pair": [kraken_pair],
                "subscription": {"name": stream_type}
            }
            
            self.logger.info(f"Anulowanie subskrypcji {stream_type} dla {pair}")
            return True
            
        except Exception as e:
            self.logger.error(f"Błąd anulowania subskrypcji Kraken: {e}")
            return False

    async def close(self):
        """Zamknij połączenia"""
        try:
            if self.session:
                await self.session.close()
                
            # Zamknij WebSocket connections
            for ws in self.ws_connections.values():
                if not ws.closed:
                    await ws.close()
                    
        except Exception as e:
            self.logger.error(f"Błąd zamykania połączeń Kraken: {e}")
    
    def __del__(self):
        """Destruktor"""
        if hasattr(self, 'session') and self.session:
            try:
                asyncio.create_task(self.session.close())
            except Exception as e:
                logger.exception('Unhandled error', exc_info=True)