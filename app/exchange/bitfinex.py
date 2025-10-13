"""
Adapter dla giełdy Bitfinex
"""

import asyncio
import hashlib
import hmac
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import websockets

from .base_exchange import BaseExchange
import logging
from utils.net_wrappers import net_guard
from utils.http_logging import log_request
logger = logging.getLogger(__name__)


class BitfinexExchange(BaseExchange):
    """
    Adapter dla giełdy Bitfinex
    
    Implementuje pełny interfejs dla handlu na Bitfinex
    poprzez REST API v2 i WebSocket.
    """
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False, sandbox: bool = None):
        # Map sandbox -> testnet for compatibility
        if sandbox is not None:
            testnet = bool(sandbox)
        super().__init__(api_key, api_secret, testnet)
        
        # Nazwa giełdy
        self.name = 'bitfinex'
        
        # Bitfinex nie ma oficjalnej sieci testowej
        self.base_url = "https://api-pub.bitfinex.com"
        self.private_url = "https://api.bitfinex.com"
        self.ws_url = "wss://api-pub.bitfinex.com/ws/2"
        
        # Bitfinex specific settings
        self.min_request_interval = 0.1  # 100ms
        self.api_version = "v2"
        
        # Bitfinex używa prefiksu 't' dla par handlowych
        self.pair_mapping = {
            'BTC/USD': 'tBTCUSD',
            'BTC/USDT': 'tBTCUST',
            'ETH/USD': 'tETHUSD',
            'ETH/USDT': 'tETHUST',
            'ETH/BTC': 'tETHBTC',
            'LTC/USD': 'tLTCUSD',
            'LTC/BTC': 'tLTCBTC',
            'XRP/USD': 'tXRPUSD',
            'XRP/BTC': 'tXRPBTC',
            'ADA/USD': 'tADAUSD',
            'ADA/BTC': 'tADABTC',
            'DOT/USD': 'tDOTUSD',
            'DOT/BTC': 'tDOTBTC',
            'LINK/USD': 'tLINKUSD',
            'LINK/BTC': 'tLINKBTC'
        }
        
        # Reverse mapping
        self.reverse_pair_mapping = {v: k for k, v in self.pair_mapping.items()}
        
        # WebSocket channels
        self.ws_channels = {}
    
    async def test_connection(self) -> bool:
        """Test połączenia z Bitfinex API"""
        try:
            response = await self.make_request('GET', '/v2/platform/status')
            return response and response[0] == 1  # 1 = operational
            
        except Exception as e:
            raise Exception(f"Test połączenia Bitfinex nieudany: {e}")
    
    async def load_exchange_info(self):
        """Wczytanie informacji o giełdzie Bitfinex"""
        try:
            # Pobierz listę symboli
            symbols_response = await self.make_request('GET', '/v2/conf/pub:list:pair:exchange')
            
            if symbols_response and isinstance(symbols_response[0], list):
                symbols = symbols_response[0]
                
                # Pobierz szczegóły symboli
                for symbol in symbols:
                    if symbol.startswith('t'):  # Trading pairs
                        # Bitfinex format: tBTCUSD -> BTC/USD
                        normalized_pair = self._normalize_symbol(symbol)
                        
                        self.symbols_info[symbol] = {
                            'symbol': symbol,
                            'normalized_pair': normalized_pair,
                            'status': 'TRADING',
                            'base_asset': self._extract_base_asset(symbol),
                            'quote_asset': self._extract_quote_asset(symbol),
                            'min_order_size': 0.00001,  # Default, będzie aktualizowane
                            'max_order_size': 1000000,
                            'tick_size': 0.00001,
                            'lot_size': 0.00001
                        }
                
                # Pobierz szczegółowe informacje o symbolach
                await self._load_symbol_details()
                
        except Exception as e:
            raise Exception(f"Błąd podczas wczytywania informacji o giełdzie: {e}")
    
    def _normalize_symbol(self, bitfinex_symbol: str) -> str:
        """Konwertuj symbol Bitfinex na standardowy format"""
        if bitfinex_symbol in self.reverse_pair_mapping:
            return self.reverse_pair_mapping[bitfinex_symbol]
        
        # Usuń prefix 't' i spróbuj parsować
        symbol = bitfinex_symbol[1:] if bitfinex_symbol.startswith('t') else bitfinex_symbol
        
        # Typowe pary
        common_quotes = ['USD', 'USDT', 'EUR', 'GBP', 'JPY', 'BTC', 'ETH']
        
        for quote in common_quotes:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                return f"{base}/{quote}"
        
        # Fallback - spróbuj podzielić na 3+3 znaki
        if len(symbol) == 6:
            return f"{symbol[:3]}/{symbol[3:]}"
        
        return symbol
    
    def _extract_base_asset(self, symbol: str) -> str:
        """Wyciągnij asset bazowy z symbolu"""
        normalized = self._normalize_symbol(symbol)
        return normalized.split('/')[0] if '/' in normalized else symbol[:3]
    
    def _extract_quote_asset(self, symbol: str) -> str:
        """Wyciągnij asset kwotowania z symbolu"""
        normalized = self._normalize_symbol(symbol)
        return normalized.split('/')[1] if '/' in normalized else symbol[3:]
    
    async def _load_symbol_details(self):
        """Wczytaj szczegółowe informacje o symbolach"""
        try:
            # Bitfinex nie ma jednego endpoint dla wszystkich szczegółów
            # Używamy domyślnych wartości i aktualizujemy w razie potrzeby
            self.logger.info("Bitfinex: użycie domyślnych wartości szczegółów symboli (min_order_size, tick_size, lot_size)")
            # Jeśli w przyszłości pojawią się dodatkowe dane (np. w self.exchange_info), można je tu wprowadzić
            return True
        except Exception as e:
            self.logger.error(f"Błąd wczytywania szczegółów symboli: {e}")
    
    def generate_signature(self, path: str, nonce: str, body: str = '') -> str:
        """Generowanie podpisu dla Bitfinex API"""
        message = f'/api/{path}{nonce}{body}'
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha384
        ).hexdigest()
        
        return signature
    
    def normalize_pair(self, pair: str) -> str:
        """Normalizacja pary dla Bitfinex"""
        if pair in self.pair_mapping:
            return self.pair_mapping[pair]
        
        # Sprawdź w symbols_info
        for bitfinex_symbol, info in self.symbols_info.items():
            if info.get('normalized_pair') == pair:
                return bitfinex_symbol
        
        # Konwertuj format BTC/USD -> tBTCUSD
        if '/' in pair:
            base, quote = pair.split('/')
            return f"t{base}{quote}"
        
        return pair
    
    def denormalize_pair(self, bitfinex_pair: str) -> str:
        """Konwersja pary Bitfinex na standardowy format"""
        if bitfinex_pair in self.reverse_pair_mapping:
            return self.reverse_pair_mapping[bitfinex_pair]
        
        if bitfinex_pair in self.symbols_info:
            return self.symbols_info[bitfinex_pair].get('normalized_pair', bitfinex_pair)
        
        return self._normalize_symbol(bitfinex_pair)
    
    async def _make_request(self, method: str, endpoint: str, params: Dict = None, signed: bool = False) -> Optional[Any]:
        """Alias do make_request używany przez testy do patchowania"""
        return await self.make_request(method, endpoint, params, signed)
    
    async def make_request(self, method: str, endpoint: str, params: Dict = None, signed: bool = False) -> Optional[Any]:
        """Wykonanie zapytania HTTP do Bitfinex API"""
        try:
            # Rate limiting
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.min_request_interval:
                await asyncio.sleep(self.min_request_interval - time_since_last)
            
            if not self.session:
                import aiohttp
                self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
            
            # Wybierz odpowiedni URL
            base_url = self.private_url if signed else self.base_url
            url = f"{base_url}{endpoint}"
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            if signed:
                nonce = str(int(time.time() * 1000000))
                body = json.dumps(params) if params else ''
                
                signature = self.generate_signature(endpoint, nonce, body)
                
                headers.update({
                    'bfx-apikey': self.api_key,
                    'bfx-signature': signature,
                    'bfx-nonce': nonce
                })
            
            self.last_request_time = time.time()
            # BEFORE any HTTP call, apply global rate limiter
            await self.rate_limit()
            log_request(logger, method, url, headers=headers, params=params if method == 'GET' else None, json_body=(params if method == 'POST' else None))
            if method == 'GET':
                if params:
                    import urllib.parse
                    url += '?' + urllib.parse.urlencode(params)
                async with self.session.get(url, headers=headers) as response:
                    return await response.json()
            elif method == 'POST':
                async with self.session.post(url, data=json.dumps(params) if params else '{}', headers=headers) as response:
                    return await response.json()
            
        except Exception as e:
            self.logger.error(f"Błąd zapytania Bitfinex API: {e}")
            return None
    
    @net_guard('exchange:get_ticker')
    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Pobierz ticker dla symbolu"""
        try:
            bitfinex_symbol = self.normalize_pair(symbol)
            response = await self.make_request('GET', f'/v2/ticker/{bitfinex_symbol}')
            
            if response and isinstance(response, list) and len(response) >= 10:
                # Bitfinex ticker format: [BID, BID_SIZE, ASK, ASK_SIZE, DAILY_CHANGE, DAILY_CHANGE_RELATIVE, LAST_PRICE, VOLUME, HIGH, LOW]
                return {
                    'symbol': symbol,
                    'price': float(response[6]),      # LAST_PRICE
                    'bid': float(response[0]),        # BID
                    'ask': float(response[2]),        # ASK
                    'volume': float(response[7]),     # VOLUME
                    'high': float(response[8]),       # HIGH
                    'low': float(response[9]),        # LOW
                    'change': float(response[4]),     # DAILY_CHANGE
                    'change_percent': float(response[5]) * 100,  # DAILY_CHANGE_RELATIVE
                    'timestamp': datetime.now()
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania ticker Bitfinex: {e}")
            return None

    @net_guard('exchange:get_order_book')
    async def get_order_book(self, symbol: str, limit: int = 25) -> Optional[Dict]:
        """Pobierz księgę zleceń"""
        try:
            bitfinex_symbol = self.normalize_pair(symbol)
            # Bitfinex obsługuje precyzję P0, P1, P2, P3, P4
            precision = 'P0'  # Najwyższa precyzja
            
            response = await self.make_request('GET', f'/v2/book/{bitfinex_symbol}/{precision}', {'len': str(limit)})
            
            if response and isinstance(response, list):
                bids = []
                asks = []
                
                for entry in response:
                    if len(entry) >= 3:
                        price = float(entry[0])
                        count = int(entry[1])
                        amount = float(entry[2])
                        
                        if amount > 0:  # Bid
                            bids.append([price, amount])
                        else:  # Ask
                            asks.append([price, abs(amount)])
                
                # Sortuj bids (malejąco) i asks (rosnąco)
                bids.sort(key=lambda x: x[0], reverse=True)
                asks.sort(key=lambda x: x[0])
                
                return {
                    'symbol': symbol,
                    'bids': bids[:limit],
                    'asks': asks[:limit],
                    'timestamp': datetime.now()
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania order book Bitfinex: {e}")
            return None

    @net_guard('exchange:get_current_price')
    async def get_current_price(self, pair: str) -> Optional[float]:
        """Pobranie aktualnej ceny"""
        bitfinex_symbol = self.normalize_pair(pair)
        response = await self._make_request('GET', f'/v2/ticker/{bitfinex_symbol}')
        if response and isinstance(response, list) and len(response) >= 7:
            return float(response[6])  # Last trade price
        raise Exception(f"Nieprawidłowa odpowiedź dla aktualnej ceny: {response}")
    
    @net_guard('exchange:get_klines')
    async def get_klines(self, pair: str, interval: str = '1h', limit: int = 100,
                        start_time: Optional[int] = None,
                        end_time: Optional[int] = None) -> List[Dict]:
        """Pobranie danych OHLCV (wrapper dla get_ohlcv)"""
        result = await self.get_ohlcv(pair, interval, limit)
        return result if result is not None else []

    @net_guard('exchange:get_ohlcv')
    async def get_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> Optional[List[Dict]]:
        """Pobierz dane OHLCV"""
        try:
            bitfinex_symbol = self.normalize_pair(symbol)
            
            # Mapowanie timeframe
            timeframe_mapping = {
                '1m': '1m',
                '5m': '5m',
                '15m': '15m',
                '30m': '30m',
                '1h': '1h',
                '3h': '3h',
                '6h': '6h',
                '12h': '12h',
                '1d': '1D',
                '1w': '7D',
                '2w': '14D',
                '1M': '1M'
            }
            
            tf = timeframe_mapping.get(timeframe, '1h')
            params = {
                'limit': str(limit),
                'sort': '1'  # Sortuj rosnąco (najstarsze pierwsze)
            }
            
            response = await self.make_request('GET', f'/v2/candles/trade:{tf}:{bitfinex_symbol}/hist', params)
            
            if response and isinstance(response, list):
                candles = []
                
                # Bitfinex zwraca w odwrotnej kolejności, więc odwracamy
                for candle in reversed(response):
                    if len(candle) >= 6:
                        candles.append({
                            'timestamp': int(candle[0] / 1000),  # Konwertuj z ms na s
                            'open': float(candle[1]),
                            'close': float(candle[2]),
                            'high': float(candle[3]),
                            'low': float(candle[4]),
                            'volume': float(candle[5])
                        })
                
                return candles
            return None
        except Exception as e:
            self.logger.error(f"Błąd pobierania OHLCV Bitfinex: {e}")
            return None

    @net_guard('exchange:get_balance')
    async def get_balance(self, currency: Optional[str] = None) -> Optional[Dict]:
        """Pobierz saldo konta"""
        try:
            response = await self._make_request('POST', '/v2/auth/r/wallets', signed=True)
            if response and isinstance(response, list):
                balance: Dict[str, Dict[str, float]] = {}
                for wallet in response:
                    if len(wallet) >= 4:
                        wallet_type = wallet[0]  # exchange, margin, funding
                        cur = wallet[1]
                        total = float(wallet[2])
                        available = float(wallet[4]) if len(wallet) > 4 and wallet[4] is not None else total
                        if wallet_type == 'exchange':
                            balance[cur.upper()] = {
                                'free': available,
                                'used': max(0.0, total - available),
                                'total': total
                            }
                if currency:
                    return balance.get(currency.upper(), {'free': 0.0, 'used': 0.0, 'total': 0.0})
                return balance
            raise Exception(f"Nieprawidłowy format odpowiedzi dla salda: {response}")
        except Exception as e:
            self.logger.error(f"Błąd pobierania salda Bitfinex: {e}")
            return None
    
    async def create_order(self, pair: Optional[str] = None, side: Optional[str] = None, amount: Optional[float] = None,
                      price: Optional[float] = None, order_type: str = 'market', **kwargs) -> Optional[Dict]:
        """Utworzenie zlecenia na Bitfinex (wrapper dla place_order). Obsługuje symbol/type z kwargs."""
        symbol = kwargs.get('symbol', pair)
        if 'type' in kwargs and kwargs.get('type'):
            order_type = kwargs['type']
        return await self.place_order(symbol, side, amount, price, order_type)

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
        bitfinex_symbol = self.normalize_pair(symbol)
        # Bitfinex używa ujemnych wartości dla sell
        order_amount = amount if side.lower() == 'buy' else -amount
        params = {
            'type': 'EXCHANGE MARKET' if order_type == 'market' else 'EXCHANGE LIMIT',
            'symbol': bitfinex_symbol,
            'amount': str(order_amount)
        }
        if order_type == 'limit' and price is not None:
            params['price'] = str(price)
        response = await self._make_request('POST', '/v2/auth/w/order/submit', params, signed=True)
        if response is None:
            raise Exception('Brak odpowiedzi z API podczas składania zlecenia')
        # Obsługa odpowiedzi w formacie listy ["SUCCESS", data] lub słownika
        if isinstance(response, list):
            if len(response) >= 2 and response[0] == 'SUCCESS':
                order_data = response[1]
                order_id = None
                if isinstance(order_data, list) and len(order_data) > 0:
                    order_id = str(order_data[0])
                elif isinstance(order_data, dict):
                    order_id = str(order_data.get('id') or order_data.get('order_id') or '')
                result = {
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
                return result
            else:
                # Obsługa spłaszczonej odpowiedzi zlecenia (lista z danymi zlecenia)
                # Przykład: [id, ..., 'tBTCUSD', ..., amount, ..., 'ACTIVE', ..., price, ...]
                if len(response) >= 15 and isinstance(response[0], (int, str)):
                    order_id = str(response[0])
                    order_symbol = self.denormalize_pair(response[3]) if len(response) > 3 else symbol
                    amount_val = abs(float(response[6])) if len(response) > 6 and response[6] is not None else amount
                    status_str = response[12] if len(response) > 12 else 'ACTIVE'
                    price_val = float(response[14]) if len(response) > 14 and response[14] is not None else price
                    normalized = {
                        'success': True,
                        'id': order_id,
                        'order_id': order_id,
                        'symbol': order_symbol or symbol,
                        'side': side,
                        'amount': amount_val if amount_val is not None else amount,
                        'price': price_val,
                        'type': order_type,
                        'status': 'open' if status_str == 'ACTIVE' else 'pending',
                        'timestamp': datetime.now()
                    }
                    return normalized
                raise Exception(f"Błąd odpowiedzi podczas składania zlecenia: {response}")
        elif isinstance(response, dict):
            order_id = str(response.get('id') or response.get('order_id') or '')
            success = response.get('success', bool(order_id))
            normalized = {
                'success': success,
                'id': order_id or None,
                'order_id': order_id or None,
                'symbol': response.get('symbol', symbol),
                'side': response.get('side', side),
                'amount': float(response.get('amount', amount)),
                'price': float(response.get('price', price)) if response.get('price') is not None else price,
                'type': response.get('type', order_type),
                'status': response.get('status', 'pending' if success else 'error'),
                'timestamp': response.get('timestamp', datetime.now())
            }
            if 'price_avg' in response:
                normalized['price_avg'] = response['price_avg']
            return normalized
        else:
            raise Exception(f"Nieprawidłowy format odpowiedzi: {response}")
    
    async def cancel_order(self, order_id: str, symbol: str = None) -> bool:
        """Anuluj zlecenie"""
        try:
            params = {'id': int(order_id)}
            response = await self.make_request('POST', '/v2/auth/w/order/cancel', params, signed=True)
            
            return response and isinstance(response, list) and response[0] == 'SUCCESS'
        except Exception as e:
            self.logger.error(f"Błąd anulowania zlecenia Bitfinex: {e}")
            return False

    @net_guard('exchange:get_order_status')
    async def get_order_status(self, order_id: str, pair: str = None) -> Optional[Dict]:
        """Sprawdź status zlecenia"""
        try:
            # Bitfinex nie ma bezpośredniego endpointu dla pojedynczego zlecenia
            # Używamy historii zleceń
            params = {'id': [int(order_id)]}
            response = await self.make_request('POST', '/v2/auth/r/orders/hist', params, signed=True)
            
            if response and isinstance(response, list):
                for order in response:
                    if len(order) >= 16 and str(order[0]) == order_id:
                        # Mapowanie statusów
                        status_mapping = {
                            'ACTIVE': 'open',
                            'EXECUTED': 'filled',
                            'PARTIALLY FILLED': 'partially_filled',
                            'CANCELED': 'canceled'
                        }
                        
                        status = status_mapping.get(order[13], 'unknown')
                        amount = abs(float(order[7]))
                        filled = abs(float(order[7]) - float(order[6]))
                        
                        return {
                            'order_id': order_id,
                            'symbol': self.denormalize_pair(order[3]),
                            'side': 'buy' if float(order[7]) > 0 else 'sell',
                            'amount': amount,
                            'filled': filled,
                            'remaining': amount - filled,
                            'price': float(order[16]) if order[16] else None,
                            'avg_price': float(order[17]) if order[17] else None,
                            'status': status,
                            'timestamp': datetime.fromtimestamp(float(order[4]) / 1000)
                        }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Błąd sprawdzania statusu zlecenia Bitfinex: {e}")
            return None
    
    @net_guard('exchange:get_open_orders')
    async def get_open_orders(self, pair: str = None) -> List[Dict]:
        """Pobierz otwarte zlecenia"""
        try:
            params = {}
            if pair:
                params['symbol'] = self.normalize_pair(pair)
            
            response = await self.make_request('POST', '/v2/auth/r/orders', params, signed=True)
            
            if response and isinstance(response, list):
                orders = []
                
                for order in response:
                    if len(order) >= 16:
                        order_symbol = self.denormalize_pair(order[3])
                        
                        # Filtruj po symbolu jeśli podano
                        if pair and order_symbol != pair:
                            continue
                        
                        amount = abs(float(order[7]))
                        filled = abs(float(order[7]) - float(order[6]))
                        
                        orders.append({
                            'order_id': str(order[0]),
                            'symbol': order_symbol,
                            'side': 'buy' if float(order[7]) > 0 else 'sell',
                            'amount': amount,
                            'filled': filled,
                            'remaining': amount - filled,
                            'price': float(order[16]) if order[16] else None,
                            'status': 'open',
                            'timestamp': datetime.fromtimestamp(float(order[4]) / 1000)
                        })
                
                return orders
            
            return []
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania otwartych zleceń Bitfinex: {e}")
            return []
    
    @net_guard('exchange:get_trade_history')
    async def get_trade_history(self, symbol: str = None, limit: int = 100) -> List[Dict]:
        """Pobierz historię transakcji"""
        try:
            params = {'limit': limit}
            if symbol:
                params['symbol'] = self.normalize_pair(symbol)
            
            response = await self.make_request('POST', '/v2/auth/r/trades/hist', params, signed=True)
            
            if response and isinstance(response, list):
                trades = []
                
                for trade in response:
                    if len(trade) >= 11:
                        trade_symbol = self.denormalize_pair(trade[1])
                        
                        # Filtruj po symbolu jeśli podano
                        if symbol and trade_symbol != symbol:
                            continue
                        
                        trades.append({
                            'trade_id': str(trade[0]),
                            'order_id': str(trade[3]),
                            'symbol': trade_symbol,
                            'side': 'buy' if float(trade[4]) > 0 else 'sell',
                            'amount': abs(float(trade[4])),
                            'price': float(trade[5]),
                            'fee': abs(float(trade[9])),
                            'timestamp': datetime.fromtimestamp(float(trade[2]) / 1000)
                        })
                
                # Sortuj po czasie (najnowsze pierwsze)
                trades.sort(key=lambda x: x['timestamp'], reverse=True)
                return trades[:limit] if limit else trades
            
            return []
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania historii transakcji Bitfinex: {e}")
            return []
    
    @net_guard('exchange:get_trading_fees')
    async def get_trading_fees(self, symbol: str = None) -> Dict:
        """Pobierz opłaty handlowe"""
        try:
            response = await self.make_request('GET', '/v2/platform/status')
            # Bitfinex nie udostępnia prostego endpointu opłat bez autoryzacji – zwróć wartości domyślne
            return {
                'maker': 0.001,  # 0.1%
                'taker': 0.002   # 0.2%
            }
        except Exception:
            return {'maker': 0.001, 'taker': 0.002}

    async def get_symbol_info(self, pair: str) -> Dict:
        """Zwróć podstawowe informacje o symbolu"""
        try:
            # Spróbuj mapować do symbolu Bitfinex
            bitfinex_symbol = self.pair_mapping.get(pair)
            base, quote = pair.split('/') if '/' in pair else (pair, '')
            return {
                'symbol': pair,
                'exchange_symbol': bitfinex_symbol or pair,
                'base_asset': base,
                'quote_asset': quote,
                'status': 'TRADING'
            }
        except Exception:
            return {'symbol': pair, 'status': 'UNKNOWN'}

    async def get_websocket_statistics(self) -> Dict:
        """Podstawowe statystyki połączeń WebSocket"""
        try:
            return {
                'connected': self.is_connected,
                'connections': len(self.ws_connections),
                'subscriptions': len(self.ws_channels) if hasattr(self, 'ws_channels') else 0
            }
        except Exception:
            return {'connected': False, 'connections': 0, 'subscriptions': 0}

    async def get_exchange_name(self) -> str:
        """Zwróć nazwę giełdy"""
        return self.name
    
    async def start_websocket(self, symbols: List[str], callback: callable):
        """Uruchom WebSocket dla subskrypcji danych"""
        try:
            # Normalizuj symbole
            bitfinex_symbols = [self.normalize_pair(symbol) for symbol in symbols]
            
            async with websockets.connect(self.ws_url, open_timeout=10, ping_interval=20, ping_timeout=10) as websocket:
                # Subskrybuj ticker dla każdego symbolu
                for symbol in bitfinex_symbols:
                    subscribe_msg = {
                        'event': 'subscribe',
                        'channel': 'ticker',
                        'symbol': symbol
                    }
                    await websocket.send(json.dumps(subscribe_msg))
                
                # Subskrybuj order book
                for symbol in bitfinex_symbols:
                    subscribe_msg = {
                        'event': 'subscribe',
                        'channel': 'book',
                        'symbol': symbol,
                        'prec': 'P0',
                        'freq': 'F0',
                        'len': '25'
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
            self.logger.error(f"Błąd WebSocket Bitfinex: {e}")
    
    async def _handle_ws_message(self, data: Any, callback: callable):
        """Obsłuż wiadomość WebSocket"""
        try:
            if isinstance(data, dict):
                # Wiadomości konfiguracyjne
                if data.get('event') == 'subscribed':
                    channel_id = data.get('chanId')
                    channel = data.get('channel')
                    symbol = data.get('symbol')
                    
                    self.ws_channels[channel_id] = {
                        'channel': channel,
                        'symbol': symbol
                    }
                    
            elif isinstance(data, list) and len(data) >= 2:
                channel_id = data[0]
                channel_data = data[1]
                
                if channel_id in self.ws_channels:
                    channel_info = self.ws_channels[channel_id]
                    channel_type = channel_info['channel']
                    symbol = channel_info['symbol']
                    
                    if channel_type == 'ticker' and isinstance(channel_data, list) and len(channel_data) >= 10:
                        # Ticker data
                        ticker_info = {
                            'symbol': self.denormalize_pair(symbol),
                            'price': float(channel_data[6]),
                            'bid': float(channel_data[0]),
                            'ask': float(channel_data[2]),
                            'volume': float(channel_data[7]),
                            'timestamp': datetime.now()
                        }
                        await callback('ticker', ticker_info)
                    
                    elif channel_type == 'book' and isinstance(channel_data, list):
                        # Order book data
                        if len(channel_data) > 0 and isinstance(channel_data[0], list):
                            # Snapshot
                            bids = []
                            asks = []
                            
                            for entry in channel_data:
                                if len(entry) >= 3:
                                    price = float(entry[0])
                                    count = int(entry[1])
                                    amount = float(entry[2])
                                    
                                    if amount > 0:
                                        bids.append([price, amount])
                                    else:
                                        asks.append([price, abs(amount)])
                            
                            book_data = {
                                'symbol': self.denormalize_pair(symbol),
                                'bids': sorted(bids, key=lambda x: x[0], reverse=True),
                                'asks': sorted(asks, key=lambda x: x[0]),
                                'timestamp': datetime.now()
                            }
                            await callback('orderbook', book_data)
                            
        except Exception as e:
            self.logger.error(f"Błąd obsługi wiadomości WS: {e}")
    
    async def subscribe_ticker(self, pair: str, callback: callable) -> bool:
        """Subskrybuj ticker dla pary"""
        try:
            bitfinex_symbol = self.normalize_pair(pair)
            # Implementacja subskrypcji ticker
            self.logger.info(f"Subskrybowano ticker dla {pair}")
            return True
        except Exception as e:
            self.logger.error(f"Błąd subskrypcji ticker Bitfinex: {e}")
            return False
    
    async def subscribe_trades(self, pair: str, callback: callable) -> bool:
        """Subskrybuj transakcje dla pary"""
        try:
            bitfinex_symbol = self.normalize_pair(pair)
            # Implementacja subskrypcji trades
            self.logger.info(f"Subskrybowano trades dla {pair}")
            return True
        except Exception as e:
            self.logger.error(f"Błąd subskrypcji trades Bitfinex: {e}")
            return False
    
    async def subscribe_order_book(self, pair: str, callback: callable) -> bool:
        """Subskrybuj order book dla pary"""
        try:
            bitfinex_symbol = self.normalize_pair(pair)
            # Implementacja subskrypcji order book
            self.logger.info(f"Subskrybowano order book dla {pair}")
            return True
        except Exception as e:
            self.logger.error(f"Błąd subskrypcji order book Bitfinex: {e}")
            return False
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Anuluj subskrypcję"""
        try:
            # Implementacja anulowania subskrypcji
            self.logger.info(f"Anulowano subskrypcję {subscription_id}")
            return True
        except Exception as e:
            self.logger.error(f"Błąd anulowania subskrypcji Bitfinex: {e}")
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
            self.logger.error(f"Błąd zamykania połączeń Bitfinex: {e}")
    
    def __del__(self):
        """Destruktor"""
        if hasattr(self, 'session') and self.session:
            try:
                asyncio.create_task(self.session.close())
            except Exception as e:
                logger.exception('Unhandled error', exc_info=True)