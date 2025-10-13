"""
Production Data Manager - Zarządzanie prawdziwymi danymi z API giełd

Zastępuje fikcyjne dane demo prawdziwymi danymi pobieranymi z API giełd
w trybie produkcyjnym aplikacji.
"""

import asyncio
import json
import threading
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from contextlib import asynccontextmanager

try:
    import ccxt
    import ccxt.async_support as ccxt_async
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False

from utils.logger import get_logger
from utils.config_manager import ConfigManager, get_config_manager
from app.exchange import get_exchange_adapter, AVAILABLE_EXCHANGES


class ProductionDataManager:
    """Manager do pobierania prawdziwych danych z API giełd"""
    
    def __init__(self, config_manager: ConfigManager = None):
        self.logger = get_logger("ProductionDataManager")
        self.config = config_manager or get_config_manager()
        self.exchanges = {}
        self.ccxt_exchanges = {}  # Async CCXT exchanges
        self.sync_ccxt_exchanges = {}  # Sync CCXT exchanges
        
        # Cache dla danych
        self.price_cache = {}
        self.ohlcv_cache = {}
        self.balance_cache = {}
        self.ticker_cache = {}
        
        # Ustawienia cache
        self.cache_ttl = 30  # sekundy
        self.last_update = {}
        
        # Synchronizacja
        self._lock = threading.RLock()
        self._initialized = False
        self._initialization_lock = asyncio.Lock()
        
        # Zarządzanie połączeniami
        self._connection_pool = {}
        self._max_retries = 3
        self._retry_delay = 1.0
        
    async def initialize(self):
        """Inicjalizacja managera danych produkcyjnych"""
        async with self._initialization_lock:
            if self._initialized:
                return True
                
            try:
                self.logger.info("Inicjalizacja Production Data Manager...")
                
                # Sprawdź czy CCXT jest dostępne
                if not CCXT_AVAILABLE:
                    self.logger.error("CCXT nie jest zainstalowane - nie można używać danych produkcyjnych")
                    return False
                
                # Sprawdź czy tryb produkcyjny jest włączony
                production_mode = self.config.get_setting('app', 'production_mode', False)
                if not production_mode:
                    self.logger.warning("Tryb produkcyjny wyłączony - używanie danych demo")
                    return False
                
                # Inicjalizuj połączenia z giełdami
                success = await self.setup_exchanges()
                if not success:
                    self.logger.error("Nie udało się skonfigurować połączeń z giełdami")
                    return False
                
                self._initialized = True
                self.logger.info("Production Data Manager zainicjalizowany pomyślnie")
                return True
                
            except Exception as e:
                self.logger.error(f"Błąd inicjalizacji Production Data Manager: {e}")
                return False
    
    async def setup_exchanges(self):
        """Konfiguruje połączenia z giełdami"""
        try:
            # Pobierz konfigurację giełd
            exchanges_config = self.config.get_setting('app', 'exchanges', {})
            self.logger.info(f"Konfiguracja giełd: {list(exchanges_config.keys())}")
            
            success_count = 0
            
            for exchange_name in AVAILABLE_EXCHANGES.keys():
                try:
                    self.logger.info(f"Konfigurowanie giełdy: {exchange_name}")
                    
                    # Sprawdź czy są skonfigurowane klucze API
                    api_config = exchanges_config.get(exchange_name, {})
                    
                    if CCXT_AVAILABLE:
                        # Mapowanie nazw giełd na klasy CCXT
                        ccxt_class_names = {
                            'binance': 'binance',
                            'bybit': 'bybit',
                            'kucoin': 'kucoin',
                            'coinbase': 'coinbaseadvanced'
                        }
                        
                        ccxt_class_name = ccxt_class_names.get(exchange_name)
                        
                        # Utwórz async exchange dla operacji asynchronicznych
                        if ccxt_class_name and hasattr(ccxt.async_support, ccxt_class_name):
                            async_exchange_class = getattr(ccxt.async_support, ccxt_class_name)
                            
                            config = {
                                'sandbox': False,  # Tryb produkcyjny
                                'enableRateLimit': True,
                                'timeout': 30000,  # 30 sekund timeout
                                'rateLimit': 1200,  # Rate limit w ms
                            }
                            
                            # Dodaj klucze API jeśli są dostępne
                            if api_config.get('api_key') and api_config.get('api_secret'):
                                config.update({
                                    'apiKey': api_config['api_key'],
                                    'secret': api_config['api_secret'],
                                })
                                if api_config.get('passphrase'):
                                    config['password'] = api_config['passphrase']
                            
                            self.ccxt_exchanges[exchange_name] = async_exchange_class(config)
                            self.logger.info(f"✅ Połączono z {exchange_name} (async)")
                            success_count += 1
                        
                        # Utwórz sync exchange dla operacji synchronicznych
                        if ccxt_class_name and hasattr(ccxt, ccxt_class_name):
                            sync_exchange_class = getattr(ccxt, ccxt_class_name)
                            
                            config = {
                                'sandbox': False,  # Tryb produkcyjny
                                'enableRateLimit': True,
                                'timeout': 30000,  # 30 sekund timeout
                                'rateLimit': 1200,  # Rate limit w ms
                            }
                            
                            # Dodaj klucze API jeśli są dostępne
                            if api_config.get('api_key') and api_config.get('api_secret'):
                                config.update({
                                    'apiKey': api_config['api_key'],
                                    'secret': api_config['api_secret'],
                                })
                                if api_config.get('passphrase'):
                                    config['password'] = api_config['passphrase']
                            
                            self.sync_ccxt_exchanges[exchange_name] = sync_exchange_class(config)
                            self.logger.info(f"✅ Połączono z {exchange_name} (sync)")
                        
                except Exception as e:
                    self.logger.warning(f"Nie udało się połączyć z {exchange_name}: {e}")
                    
            self.logger.info(f"Utworzone połączenia CCXT async: {list(self.ccxt_exchanges.keys())}")
            self.logger.info(f"Utworzone połączenia CCXT sync: {list(self.sync_ccxt_exchanges.keys())}")
            
            return success_count > 0
                    
        except Exception as e:
            self.logger.error(f"Błąd konfiguracji giełd: {e}")
            return False
    
    async def _execute_with_retry(self, func, *args, **kwargs):
        """Wykonuje funkcję z mechanizmem retry"""
        last_exception = None
        
        for attempt in range(self._max_retries):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self._max_retries - 1:
                    wait_time = self._retry_delay * (2 ** attempt)
                    self.logger.warning(f"Próba {attempt + 1} nieudana: {e}. Ponowna próba za {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"Wszystkie próby nieudane: {e}")
        
        raise last_exception
    
    def _validate_symbol(self, symbol: str) -> bool:
        """Waliduje format symbolu"""
        if not symbol or not isinstance(symbol, str):
            return False
        
        # Podstawowa walidacja formatu (np. BTC/USDT)
        if '/' not in symbol:
            return False
        
        parts = symbol.split('/')
        if len(parts) != 2:
            return False
        
        # Sprawdź czy części nie są puste
        return all(part.strip() for part in parts)
    
    def _validate_exchange(self, exchange: str) -> bool:
        """Waliduje nazwę giełdy"""
        return exchange in AVAILABLE_EXCHANGES
    
    async def get_real_price(self, symbol: str, exchange: str = 'binance') -> Optional[float]:
        """Pobiera prawdziwą cenę z API giełdy"""
        try:
            # Walidacja parametrów
            if not self._validate_symbol(symbol):
                self.logger.error(f"Nieprawidłowy symbol: {symbol}")
                return None
            
            if not self._validate_exchange(exchange):
                self.logger.error(f"Nieprawidłowa giełda: {exchange}")
                return None
            
            cache_key = f"{exchange}_{symbol}_price"
            
            # Sprawdź cache
            with self._lock:
                if self._is_cache_valid(cache_key):
                    return self.price_cache[cache_key]
            
            if exchange in self.ccxt_exchanges:
                ticker = await self._execute_with_retry(
                    self.ccxt_exchanges[exchange].fetch_ticker, symbol
                )
                price = float(ticker['last'])
                
                # Zapisz w cache
                with self._lock:
                    self.price_cache[cache_key] = price
                    self.last_update[cache_key] = datetime.now()
                
                return price
            else:
                self.logger.warning(f"Giełda {exchange} niedostępna - używanie danych demo")
                return None
                
        except Exception as e:
            self.logger.error(f"Błąd pobierania ceny {symbol} z {exchange}: {e}")
            return None
    
    async def get_real_ohlcv(self, symbol: str, timeframe: str = '1h', 
                           limit: int = 100, exchange: str = 'binance') -> Optional[pd.DataFrame]:
        """Pobiera prawdziwe dane OHLCV z API giełdy"""
        try:
            # Walidacja parametrów
            if not self._validate_symbol(symbol):
                self.logger.error(f"Nieprawidłowy symbol: {symbol}")
                return None
            
            if not self._validate_exchange(exchange):
                self.logger.error(f"Nieprawidłowa giełda: {exchange}")
                return None
            
            if limit <= 0 or limit > 1000:
                self.logger.error(f"Nieprawidłowy limit: {limit}")
                return None
            
            cache_key = f"{exchange}_{symbol}_{timeframe}_ohlcv"
            
            # Sprawdź cache
            with self._lock:
                if self._is_cache_valid(cache_key):
                    return self.ohlcv_cache[cache_key]
            
            if exchange in self.ccxt_exchanges:
                ohlcv = await self._execute_with_retry(
                    self.ccxt_exchanges[exchange].fetch_ohlcv,
                    symbol, timeframe, limit=limit
                )
                
                if not ohlcv:
                    return None
                
                # Konwertuj na DataFrame
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                # Zapisz w cache
                with self._lock:
                    self.ohlcv_cache[cache_key] = df
                    self.last_update[cache_key] = datetime.now()
                
                return df
            else:
                self.logger.warning(f"Giełda {exchange} niedostępna - używanie danych demo")
                return None
                
        except Exception as e:
            self.logger.error(f"Błąd pobierania OHLCV {symbol} z {exchange}: {e}")
            return None
    
    async def get_real_balance(self, exchange: str = 'binance') -> Optional[Dict]:
        """Pobiera prawdziwe saldo z API giełdy"""
        try:
            if not self._validate_exchange(exchange):
                self.logger.error(f"Nieprawidłowa giełda: {exchange}")
                return None
            
            cache_key = f"{exchange}_balance"
            
            # Sprawdź cache
            with self._lock:
                if self._is_cache_valid(cache_key):
                    return self.balance_cache[cache_key]
            
            if exchange in self.ccxt_exchanges:
                # Sprawdź czy mamy klucze API
                exchange_obj = self.ccxt_exchanges[exchange]
                if not (exchange_obj.apiKey and exchange_obj.secret):
                    self.logger.warning(f"Brak kluczy API dla {exchange} - nie można pobrać salda")
                    return None
                
                balance = await self._execute_with_retry(
                    exchange_obj.fetch_balance
                )
                
                # Zapisz w cache
                with self._lock:
                    self.balance_cache[cache_key] = balance
                    self.last_update[cache_key] = datetime.now()
                
                return balance
            else:
                self.logger.warning(f"Giełda {exchange} niedostępna - używanie danych demo")
                return None
                
        except Exception as e:
            self.logger.error(f"Błąd pobierania salda z {exchange}: {e}")
            return None
    
    async def get_real_ticker(self, symbol: str, exchange: str = 'binance') -> Optional[Dict]:
        """Pobiera prawdziwy ticker z API giełdy"""
        try:
            if not self._validate_symbol(symbol):
                self.logger.error(f"Nieprawidłowy symbol: {symbol}")
                return None
            
            if not self._validate_exchange(exchange):
                self.logger.error(f"Nieprawidłowa giełda: {exchange}")
                return None
            
            cache_key = f"{exchange}_{symbol}_ticker"
            
            # Sprawdź cache
            with self._lock:
                if self._is_cache_valid(cache_key):
                    return self.ticker_cache[cache_key]
            
            if exchange in self.ccxt_exchanges:
                ticker = await self._execute_with_retry(
                    self.ccxt_exchanges[exchange].fetch_ticker, symbol
                )
                
                # Zapisz w cache
                with self._lock:
                    self.ticker_cache[cache_key] = ticker
                    self.last_update[cache_key] = datetime.now()
                
                return ticker
            else:
                self.logger.warning(f"Giełda {exchange} niedostępna - używanie danych demo")
                return None
                
        except Exception as e:
            self.logger.error(f"Błąd pobierania ticker {symbol} z {exchange}: {e}")
            return None
    
    async def get_real_tickers(self, exchange: str = 'binance') -> Optional[Dict]:
        """Pobiera wszystkie tickery z API giełdy"""
        try:
            if not self._validate_exchange(exchange):
                self.logger.error(f"Nieprawidłowa giełda: {exchange}")
                return None
            
            cache_key = f"{exchange}_all_tickers"
            
            # Sprawdź cache
            with self._lock:
                if self._is_cache_valid(cache_key):
                    return self.ticker_cache[cache_key]
            
            if exchange in self.ccxt_exchanges:
                tickers = await self._execute_with_retry(
                    self.ccxt_exchanges[exchange].fetch_tickers
                )
                
                # Zapisz w cache
                with self._lock:
                    self.ticker_cache[cache_key] = tickers
                    self.last_update[cache_key] = datetime.now()
                
                return tickers
            else:
                self.logger.warning(f"Giełda {exchange} niedostępna - używanie danych demo")
                return None
                
        except Exception as e:
            self.logger.error(f"Błąd pobierania tickerów z {exchange}: {e}")
            return None
    
    async def get_market_summary(self, exchange: str = 'binance') -> Dict[str, Any]:
        """Pobiera podsumowanie rynku z API giełdy"""
        try:
            if not self._validate_exchange(exchange):
                return {'error': f'Nieprawidłowa giełda: {exchange}'}
            
            if exchange in self.ccxt_exchanges:
                # Pobierz top pary handlowe
                markets = await self._execute_with_retry(
                    self.ccxt_exchanges[exchange].load_markets
                )
                top_symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'DOT/USDT']
                
                summary = {
                    'exchange': exchange,
                    'timestamp': datetime.now(),
                    'markets_count': len(markets),
                    'top_pairs': {}
                }
                
                for symbol in top_symbols:
                    if symbol in markets:
                        ticker = await self.get_real_ticker(symbol, exchange)
                        if ticker:
                            summary['top_pairs'][symbol] = {
                                'price': ticker.get('last'),
                                'change_24h': ticker.get('percentage'),
                                'volume_24h': ticker.get('quoteVolume')
                            }
                
                return summary
            else:
                return {'error': f'Giełda {exchange} niedostępna'}
                
        except Exception as e:
            self.logger.error(f"Błąd pobierania podsumowania rynku z {exchange}: {e}")
            return {'error': str(e)}
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Sprawdza czy dane w cache są aktualne"""
        if cache_key not in self.last_update:
            return False
        
        time_diff = (datetime.now() - self.last_update[cache_key]).total_seconds()
        return time_diff < self.cache_ttl
    
    def clear_cache(self):
        """Czyści cache danych"""
        with self._lock:
            self.price_cache.clear()
            self.ohlcv_cache.clear()
            self.balance_cache.clear()
            self.ticker_cache.clear()
            self.last_update.clear()
        self.logger.info("Cache danych wyczyszczony")
    
    async def test_connections(self) -> Dict[str, bool]:
        """Testuje połączenia z giełdami"""
        results = {}
        
        for exchange_name in AVAILABLE_EXCHANGES.keys():
            try:
                if exchange_name in self.ccxt_exchanges:
                    # Test publicznego API
                    try:
                        ticker = await self._execute_with_retry(
                            self.ccxt_exchanges[exchange_name].fetch_ticker, 'BTC/USDT'
                        )
                        results[f"{exchange_name}_public"] = ticker is not None
                    except:
                        results[f"{exchange_name}_public"] = False
                else:
                    results[f"{exchange_name}_public"] = False
                
                if exchange_name in self.ccxt_exchanges:
                    # Test prywatnego API (jeśli są klucze)
                    exchange_obj = self.ccxt_exchanges[exchange_name]
                    if exchange_obj.apiKey and exchange_obj.secret:
                        try:
                            balance = await self._execute_with_retry(
                                exchange_obj.fetch_balance
                            )
                            results[f"{exchange_name}_private"] = balance is not None
                        except:
                            results[f"{exchange_name}_private"] = False
                    else:
                        results[f"{exchange_name}_private"] = False
                else:
                    results[f"{exchange_name}_private"] = False
                    
            except Exception as e:
                self.logger.error(f"Test połączenia z {exchange_name} nieudany: {e}")
                results[f"{exchange_name}_public"] = False
                results[f"{exchange_name}_private"] = False
        
        return results
    
    def test_connection(self) -> bool:
        """Testuje podstawowe połączenie z giełdą (synchroniczna wersja)"""
        try:
            # Sprawdź czy mamy jakiekolwiek połączenia
            if not self.sync_ccxt_exchanges:
                return False
            
            # Testuj pierwsze dostępne połączenie
            for exchange_name, exchange in self.sync_ccxt_exchanges.items():
                try:
                    ticker = exchange.fetch_ticker('BTC/USDT')
                    if ticker and 'last' in ticker:
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.error(f"Błąd testu połączenia: {e}")
            return False
    
    def get_tickers(self, symbols: list = None) -> dict:
        """Pobiera tickery dla podanych symboli"""
        try:
            if not self.sync_ccxt_exchanges:
                return {}
            
            tickers = {}
            for exchange_name, exchange in self.sync_ccxt_exchanges.items():
                try:
                    if symbols:
                        exchange_tickers = {}
                        for symbol in symbols:
                            try:
                                if self._validate_symbol(symbol):
                                    ticker = exchange.fetch_ticker(symbol)
                                    exchange_tickers[symbol] = ticker
                            except:
                                continue
                        tickers[exchange_name] = exchange_tickers
                    else:
                        # Pobierz wszystkie dostępne tickery
                        tickers[exchange_name] = exchange.fetch_tickers()
                except Exception as e:
                    self.logger.error(f"Błąd pobierania tickerów z {exchange_name}: {e}")
                    continue
            
            return tickers
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania tickerów: {e}")
            return {}
    
    async def test_connection_async(self) -> bool:
        """Testuje podstawowe połączenie z giełdą (asynchroniczna wersja)"""
        try:
            # Sprawdź czy mamy jakiekolwiek połączenia
            if not self.ccxt_exchanges:
                return False
            
            # Testuj pierwsze dostępne połączenie
            for exchange_name, exchange in self.ccxt_exchanges.items():
                try:
                    ticker = await self._execute_with_retry(
                        exchange.fetch_ticker, 'BTC/USDT'
                    )
                    if ticker and 'last' in ticker:
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.error(f"Błąd testu połączenia: {e}")
            return False
    
    async def close(self):
        """Zamyka połączenia z giełdami"""
        try:
            # Zamknij async exchanges
            for exchange in self.ccxt_exchanges.values():
                if hasattr(exchange, 'close'):
                    try:
                        await exchange.close()
                    except Exception as e:
                        self.logger.warning(f"Błąd zamykania połączenia async: {e}")
            
            # Zamknij sync exchanges (jeśli mają metodę close)
            for exchange in self.sync_ccxt_exchanges.values():
                if hasattr(exchange, 'close'):
                    try:
                        exchange.close()
                    except Exception as e:
                        self.logger.warning(f"Błąd zamykania połączenia sync: {e}")
            
            # Wyczyść cache
            self.clear_cache()
            
            # Reset flag
            self._initialized = False
            
            self.logger.info("Połączenia z giełdami zamknięte")
            
        except Exception as e:
            self.logger.error(f"Błąd zamykania połączeń: {e}")


# Singleton instance
_production_data_manager = None
_production_data_manager_lock = threading.Lock()


def get_production_data_manager() -> ProductionDataManager:
    """Zwraca singleton instance ProductionDataManager"""
    global _production_data_manager
    
    if _production_data_manager is None:
        with _production_data_manager_lock:
            if _production_data_manager is None:
                _production_data_manager = ProductionDataManager()
    
    return _production_data_manager