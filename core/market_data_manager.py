"""Market Data Manager - zarządzanie danymi rynkowymi.

Wersja produkcyjna automatycznie próbuje korzystać z prawdziwych danych
giełdowych, jeżeli konfiguracja zawiera aktywne klucze API lub użytkownik
włącza odpowiednią opcję w panelu.  Fallback do danych symulowanych
pozostaje dostępny na potrzeby testów offline.
"""

from __future__ import annotations

import asyncio
import logging
import json
import os
import random
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Tuple, Set
from dataclasses import dataclass

try:  # pragma: no cover - optional dependency in CI
    import websocket  # type: ignore
except Exception:  # pragma: no cover - fallback used in tests
    websocket = None  # type: ignore

try:  # pragma: no cover - optional dependency
    import requests  # type: ignore
except Exception:  # pragma: no cover - handled by mock helpers
    requests = None

from app.exchange.adapter_factory import create_exchange_adapter
from app.exchange.live_ccxt_adapter import LiveCCXTAdapter
from utils.config_manager import get_config_manager
from utils.helpers import get_or_create_event_loop, schedule_coro_safely

try:  # pragma: no cover - opcjonalny moduł (może nie istnieć w środowisku CI)
    from app.api_config_manager import get_api_config_manager
except Exception:  # pragma: no cover - brak managera API w środowisku testowym
    get_api_config_manager = None  # type: ignore

from .websocket_callback_manager import WebSocketCallbackManager, WebSocketEventType, StandardizedTickerData

logger = logging.getLogger(__name__)

@dataclass
class PriceData:
    """Dane cenowe"""
    symbol: str
    price: float
    bid: float
    ask: float
    volume_24h: float
    change_24h: float
    change_24h_percent: float
    timestamp: datetime

@dataclass
class OrderBookData:
    """Dane order book"""
    symbol: str
    bids: List[Tuple[float, float]]  # [(price, quantity), ...]
    asks: List[Tuple[float, float]]  # [(price, quantity), ...]
    timestamp: datetime

@dataclass
class TradeData:
    """Dane transakcji"""
    symbol: str
    price: float
    quantity: float
    side: str  # 'buy' or 'sell'
    timestamp: datetime

class MarketDataManager:
    """Manager danych rynkowych - subskrybuje ceny, orderbook, dane z giełd"""
    
    def __init__(self):
        self.subscriptions: Dict[str, List[Callable]] = {}
        self.price_cache: Dict[str, PriceData] = {}
        self.orderbook_cache: Dict[str, OrderBookData] = {}
        self.candle_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.websocket_connections: Dict[str, Any] = {}
        self._websocket_threads: Dict[str, threading.Thread] = {}
        self.running = False
        self.update_interval = 1.0  # sekundy

        # Symbole do śledzenia
        self.tracked_symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']

        # WebSocket callback manager
        self.ws_callback_manager = WebSocketCallbackManager()
        self._setup_websocket_callbacks()

        self.enable_live = self._determine_live_mode()
        logger.info("MarketDataManager live market data %s", "ENABLED" if self.enable_live else "DISABLED")

        # Konfiguracja giełd
        self.exchanges = {
            'binance': {
                'rest_url': 'https://api.binance.com/api/v3',
                'ws_url': 'wss://stream.binance.com:9443/ws',
                'enabled': self.enable_live
            },
            'bybit': {
                'rest_url': 'https://api.bybit.com/v2/public',
                'ws_url': 'wss://stream.bybit.com/realtime',
                'enabled': self.enable_live
            }
        }

        self._live_price_adapter: Optional[LiveCCXTAdapter] = None
        if self.enable_live:
            try:
                loop = get_or_create_event_loop()
                adapter = create_exchange_adapter(
                    'binance',
                    mode='live',
                    event_loop=loop,
                    intent='market_data',
                )
                if isinstance(adapter, LiveCCXTAdapter):
                    self._live_price_adapter = adapter
                else:
                    logger.warning("Live adapter request returned simulated implementation – disabling live feed")
                    self._live_price_adapter = None
            except Exception as exc:
                logger.warning("Live price adapter initialisation failed: %s", exc)
                self._live_price_adapter = None
        
        # Symbole do śledzenia - pojedyncza inicjalizacja
        # self.tracked_symbols już ustawione wcześniej; zapewnij spójność
        # Pozostaw bez ponownej inicjalizacji, użyj metody set_tracked_symbols aby modyfikować
        # (patrz definicja metody poniżej)
        # self.tracked_symbols = self.tracked_symbols
    
    def _determine_live_mode(self) -> bool:
        env_flag = os.environ.get('ENABLE_REAL_MARKET_DATA')
        if env_flag is not None:
            return env_flag.lower() in ('1', 'true', 'yes', 'on')

        try:
            config_manager = get_config_manager()
            offline_mode = bool(config_manager.get_setting('app', 'app.offline_mode', False))
            if offline_mode:
                return False
            trading_mode = str(config_manager.get_setting('app', 'trading.mode', 'auto')).lower()
            if trading_mode == 'paper':
                return False
            if bool(config_manager.get_setting('trading', 'paper_trading', False)):
                return False
        except Exception:
            trading_mode = 'auto'

        if get_api_config_manager is not None:
            try:
                manager = get_api_config_manager()
                for exchange in manager.get_available_exchanges():
                    cfg = manager.get_exchange_config(exchange) or {}
                    if cfg.get('enabled') and (cfg.get('api_key') or cfg.get('secret')):
                        return True
            except Exception as exc:
                logger.debug("APIConfigManager live mode probe failed: %s", exc)

        credentials_file = Path('config/exchange_credentials.json')
        if credentials_file.exists():
            try:
                with credentials_file.open('r', encoding='utf-8') as handle:
                    payload = json.load(handle)
                if isinstance(payload, dict):
                    for cfg in payload.values():
                        if not isinstance(cfg, dict):
                            continue
                        if bool(cfg.get('enabled', True)) and (cfg.get('api_key') or cfg.get('secret')):
                            return True
            except Exception as exc:
                logger.debug("Credential file live mode probe failed: %s", exc)

        return trading_mode == 'live'

    def _setup_websocket_callbacks(self):
        """Konfiguruje callbacki WebSocket (idempotentnie)."""
        exchanges = ['binance', 'bybit', 'kucoin', 'coinbase']

        def _ensure_registered(event_type: WebSocketEventType, symbol: str, exchange: str, func: Callable):
            """Rejestruje callback tylko gdy nie istnieje dla danego eventu/symbolu/giełdy/funkcji."""
            exists = False
            try:
                for cid in self.ws_callback_manager.callbacks_by_type.get(event_type, []):
                    info = self.ws_callback_manager.callbacks.get(cid)
                    if info and info.symbol == symbol and info.exchange == exchange and info.callback_function == func:
                        exists = True
                        break
            except Exception:
                exists = False
            if not exists:
                self.ws_callback_manager.register_callback(event_type, symbol, exchange, func)

        for exchange in exchanges:
            for symbol in self.tracked_symbols:
                _ensure_registered(WebSocketEventType.TICKER, symbol, exchange, self._handle_ticker_update)
                _ensure_registered(WebSocketEventType.TRADES, symbol, exchange, self._handle_trade_update)
                _ensure_registered(WebSocketEventType.ORDER_BOOK, symbol, exchange, self._handle_orderbook_update)

    def set_tracked_symbols(self, symbols: List[str]) -> None:
        """Ustawia listę śledzonych symboli i zapewnia rejestrację callbacków WS bez duplikacji."""
        # Zachowaj kolejność i unikalność
        unique: List[str] = []
        for s in symbols:
            if s not in unique:
                unique.append(s)
        self.tracked_symbols = unique
        # Zapewnij rejestrację WS callbacków dla aktualnej listy symboli
        self._setup_websocket_callbacks()

    def add_tracked_symbol(self, symbol: str) -> None:
        """Dodaje symbol do śledzenia i zapewnia rejestrację WS callbacków w sposób idempotentny."""
        if symbol not in self.tracked_symbols:
            self.tracked_symbols.append(symbol)
        # Zapewnij rejestrację WS callbacków (idempotentnie)
        self._setup_websocket_callbacks()

    def remove_tracked_symbol(self, symbol: str) -> None:
        """Usuwa symbol ze śledzenia i wyrejestrowuje powiązane callbacki WS."""
        try:
            if symbol in self.tracked_symbols:
                self.tracked_symbols.remove(symbol)
            # Wyrejestruj istniejące callbacki WS dla tego symbolu
            for event_type in (WebSocketEventType.TICKER, WebSocketEventType.TRADES, WebSocketEventType.ORDER_BOOK):
                # Kopia listy, bo będziemy modyfikować podczas iteracji
                for cid in list(self.ws_callback_manager.callbacks_by_type.get(event_type, [])):
                    info = self.ws_callback_manager.callbacks.get(cid)
                    if info and info.symbol == symbol:
                        try:
                            self.ws_callback_manager.unregister_callback(cid)
                        except Exception as e:
                            logger.error(f"Błąd wyrejestrowania callbacku {cid} dla {symbol} ({event_type.value}): {e}")
        except Exception:
            pass
    
    def _handle_ticker_update(self, ticker_data: StandardizedTickerData):
        """Obsługuje aktualizacje ticker z WebSocket"""
        try:
            # Konwertuj StandardizedTickerData na PriceData
            price_data = PriceData(
                symbol=ticker_data.symbol,
                price=ticker_data.price,
                bid=getattr(ticker_data, 'bid', ticker_data.price * 0.999),  # Fallback jeśli brak bid
                ask=getattr(ticker_data, 'ask', ticker_data.price * 1.001),  # Fallback jeśli brak ask
                volume_24h=ticker_data.volume_24h,
                change_24h=ticker_data.price_change,
                change_24h_percent=ticker_data.price_change_percent,
                timestamp=ticker_data.timestamp
            )
            
            # Aktualizuj cache
            self.price_cache[ticker_data.symbol] = price_data
            
            # Powiadom subskrybentów
            if ticker_data.symbol in self.subscriptions:
                for callback in self.subscriptions[ticker_data.symbol]:
                    try:
                        callback(price_data)
                    except Exception as e:
                        logger.error(f"Error in ticker callback for {ticker_data.symbol}: {e}")
            
            logger.debug(f"Updated ticker data for {ticker_data.symbol}: {ticker_data.price}")
            
        except Exception as e:
            logger.error(f"Error handling ticker update: {e}")
    
    def _handle_trade_update(self, trade_data):
        """Obsługuje aktualizacje trades z WebSocket"""
        try:
            # Implementacja dla przyszłych potrzeb
            logger.debug(f"Received trade update for {trade_data.symbol}")
        except Exception as e:
            logger.error(f"Error handling trade update: {e}")
    
    def _handle_orderbook_update(self, orderbook_data):
        """Obsługuje aktualizacje order book z WebSocket"""
        try:
            # Implementacja dla przyszłych potrzeb
            logger.debug(f"Received orderbook update for {orderbook_data.symbol}")
        except Exception as e:
            logger.error(f"Error handling orderbook update: {e}")

    async def _ingest_websocket_ticker(self, payload: Dict[str, Any]):
        try:
            symbol = str(payload.get('s') or payload.get('symbol') or '').upper()
            if not symbol:
                return

            price = float(payload.get('c') or payload.get('C') or payload.get('p') or 0.0)
            bid = float(payload.get('b') or payload.get('B') or price)
            ask = float(payload.get('a') or payload.get('A') or price)
            volume = float(payload.get('v') or payload.get('V') or 0.0)
            change = float(payload.get('p') or payload.get('P') or 0.0)
            change_percent = float(payload.get('P') or payload.get('p') or 0.0)
            event_time = payload.get('E') or payload.get('eventTime')
            if event_time:
                timestamp = datetime.utcfromtimestamp(float(event_time) / 1000.0)
            else:
                timestamp = datetime.utcnow()

            price_data = PriceData(
                symbol=symbol,
                price=price,
                bid=bid,
                ask=ask,
                volume_24h=volume,
                change_24h=change,
                change_24h_percent=change_percent,
                timestamp=timestamp,
            )
            await self.update_price_data(symbol, price_data)
        except Exception as exc:
            logger.error(f"Error ingesting websocket ticker: {exc}")
        
    async def start(self):
        """Uruchamia manager danych rynkowych"""
        try:
            self.running = True
            logger.info("Starting MarketDataManager...")
            
            # Uruchom aktualizacje cen
            schedule_coro_safely(lambda: self._price_update_loop())
            
            # Uruchom WebSocket dla Binance jeśli włączone
            if self.exchanges['binance']['enabled']:
                await self._start_binance_websocket()
            
            logger.info("MarketDataManager started successfully")
            
        except Exception as e:
            logger.error(f"Error starting MarketDataManager: {e}")
    
    async def initialize(self):
        """Inicjalizuje MarketDataManager - alias dla start()"""
        try:
            await self.start()
            logger.info("MarketDataManager initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing MarketDataManager: {e}")
            return False
    
    async def update_price_data(self, symbol: str, price_data: PriceData):
        """Aktualizuje dane cenowe dla symbolu"""
        try:
            # Zapisz w cache
            self.price_cache[symbol] = price_data
            
            # Powiadom subskrybentów
            if symbol in self.subscriptions:
                for callback in self.subscriptions[symbol]:
                    try:
                        callback(price_data)
                    except Exception as e:
                        logger.error(f"Error in price callback for {symbol}: {e}")
            
            logger.debug(f"Updated price data for {symbol}: {price_data.price}")
            
        except Exception as e:
            logger.error(f"Error updating price data for {symbol}: {e}")
    
    async def stop(self):
        """Zatrzymuje manager danych rynkowych"""
        try:
            self.running = False
            
            # Zamknij WebSocket połączenia
            for exchange, ws in self.websocket_connections.items():
                if ws:
                    ws.close()
                thread = self._websocket_threads.get(exchange)
                if thread and thread.is_alive():  # pragma: no cover - requires live ws
                    thread.join(timeout=2.0)

            logger.info("MarketDataManager stopped")

        except Exception as e:
            logger.error(f"Error stopping MarketDataManager: {e}")
    
    def subscribe_to_price(self, symbol: str, callback: Callable[[PriceData], None]):
        """Subskrybuje aktualizacje cen dla symbolu bez duplikacji callbacków"""
        if symbol not in self.subscriptions:
            self.subscriptions[symbol] = []
        # Dodaj callback tylko jeśli nie istnieje
        if callback not in self.subscriptions[symbol]:
            self.subscriptions[symbol].append(callback)
            logger.info(f"Subscribed to price updates for {symbol}")
        else:
            logger.debug(f"Callback dla {symbol} już istnieje, pomijam duplikat")
        # Dodaj symbol do śledzonych jeśli nie ma i zarejestruj WS callbacki
        if symbol not in self.tracked_symbols:
            self.add_tracked_symbol(symbol)

    def subscribe_to_ticker(self, symbol: str, callback: Callable[[Dict[str, Any]], None]):
        """Alias wymagany przez testy UI – deleguje do :meth:`subscribe_to_price`."""

        def _wrapper(price_data: PriceData) -> None:
            ticker = {
                'symbol': price_data.symbol,
                'price': price_data.price,
                'bid': price_data.bid,
                'ask': price_data.ask,
                'volume_24h': price_data.volume_24h,
                'change_24h': price_data.change_24h,
                'change_24h_percent': price_data.change_24h_percent,
                'timestamp': price_data.timestamp.isoformat(),
            }
            callback(ticker)

        self.subscribe_to_price(symbol, _wrapper)
    
    def set_integrated_data_manager(self, integrated_data_manager):
        """Ustawia referencję do IntegratedDataManager dla propagacji danych"""
        self.integrated_data_manager = integrated_data_manager
        
        # Subskrybuj wszystkie symbole do propagacji
        for symbol in self.tracked_symbols:
            self.subscribe_to_price(symbol, self._propagate_to_integrated_manager)
    
    def _propagate_to_integrated_manager(self, price_data: PriceData):
        """Propaguje dane cenowe do IntegratedDataManager"""
        try:
            if hasattr(self, 'integrated_data_manager') and self.integrated_data_manager:
                # Uruchom asynchronicznie callback
                schedule_coro_safely(lambda: self.integrated_data_manager._handle_price_update(
                    price_data.symbol, price_data
                ))
        except Exception as e:
            logger.error(f"Error propagating price data to IntegratedDataManager: {e}")
    
    def unsubscribe_from_price(self, symbol: str, callback: Callable[[PriceData], None]):
        """Anuluje subskrypcję aktualizacji cen"""
        if symbol in self.subscriptions and callback in self.subscriptions[symbol]:
            self.subscriptions[symbol].remove(callback)

            if not self.subscriptions[symbol]:
                del self.subscriptions[symbol]

        logger.info(f"Unsubscribed from price updates for {symbol}")

    async def get_price(self, symbol: str) -> Optional[float]:
        """Zwraca jedynie wartość ceny dla wygody testów."""

        price_data = await self.get_current_price(symbol)
        return price_data.price if price_data else None

    async def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Zwraca uproszczony ticker w formacie przyjaznym dla UI."""

        price_data = await self.get_current_price(symbol)
        if not price_data:
            return None
        return {
            'symbol': price_data.symbol,
            'price': price_data.price,
            'bid': price_data.bid,
            'ask': price_data.ask,
            'volume_24h': price_data.volume_24h,
            'change_24h': price_data.change_24h,
            'change_24h_percent': price_data.change_24h_percent,
            'timestamp': price_data.timestamp.isoformat(),
        }

    async def get_current_price(self, symbol: str) -> Optional[PriceData]:
        """Pobiera aktualną cenę symbolu"""
        try:
            # Sprawdź cache
            if symbol in self.price_cache:
                cached_data = self.price_cache[symbol]
                # Sprawdź czy dane nie są starsze niż 30 sekund
                if datetime.now() - cached_data.timestamp < timedelta(seconds=30):
                    return cached_data
            
            # Pobierz z API
            price_data = await self._fetch_price_from_api(symbol)
            if price_data:
                self.price_cache[symbol] = price_data
                return price_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return None
    
    async def get_orderbook(self, symbol: str, depth: int = 10) -> Optional[OrderBookData]:
        """Pobiera order book dla symbolu"""
        try:
            # Sprawdź cache
            if symbol in self.orderbook_cache:
                cached_data = self.orderbook_cache[symbol]
                if datetime.now() - cached_data.timestamp < timedelta(seconds=5):
                    return cached_data

            # Pobierz z API
            orderbook_data = await self._fetch_orderbook_from_api(symbol, depth)
            if orderbook_data:
                self.orderbook_cache[symbol] = orderbook_data
                return orderbook_data

            return None

        except Exception as e:
            logger.error(f"Error getting orderbook for {symbol}: {e}")
            return None

    async def fetch_candles(
        self,
        symbol: str,
        *,
        timeframe: str = "1m",
        limit: int = 120,
    ) -> List[Dict[str, Any]]:
        """Pobiera dane świecowe dla wskazanego symbolu.

        Preferuje połączenie CCXT, następnie publiczne REST API Binance, a na
        końcu generuje stabilny fallback na podstawie lokalnego cache'u.
        """

        cache_key = f"{symbol}:{timeframe}:{limit}"
        cached = self.candle_cache.get(cache_key)
        if cached and cached and (
            datetime.now() - cached[-1]["timestamp"] < timedelta(seconds=30)
        ):
            return cached

        candles: List[Dict[str, Any]] = []

        # 1. Spróbuj użyć adaptera CCXT jeżeli jest dostępny
        if self._live_price_adapter and hasattr(self._live_price_adapter, "fetch_ohlcv"):
            ccxt_symbol = self._normalise_symbol_for_ccxt(symbol)
            try:
                raw = await self._live_price_adapter.fetch_ohlcv(
                    ccxt_symbol, timeframe=timeframe, limit=limit
                )
                candles = [
                    {
                        "symbol": symbol,
                        "timestamp": datetime.fromtimestamp(entry["timestamp"] / 1000.0),
                        "open": entry["open"],
                        "high": entry["high"],
                        "low": entry["low"],
                        "close": entry["close"],
                        "volume": entry["volume"],
                    }
                    for entry in raw
                ]
            except Exception as exc:
                logger.debug("CCXT fetch_ohlcv failed for %s: %s", symbol, exc)

        # 2. Publiczne REST API Binance jako fallback
        if not candles and self.exchanges.get("binance", {}).get("enabled") and requests:
            try:
                url = f"{self.exchanges['binance']['rest_url']}/klines"
                params = {"symbol": symbol, "interval": timeframe, "limit": limit}
                response = requests.get(url, params=params, timeout=5)  # type: ignore[operator]
                if response.status_code == 200:
                    data = response.json()
                    candles = [
                        {
                            "symbol": symbol,
                            "timestamp": datetime.fromtimestamp(int(item[0]) / 1000.0),
                            "open": float(item[1]),
                            "high": float(item[2]),
                            "low": float(item[3]),
                            "close": float(item[4]),
                            "volume": float(item[5]),
                        }
                        for item in data
                    ]
                else:
                    logger.debug(
                        "Binance klines request failed (%s): %s",
                        response.status_code,
                        response.text[:200],
                    )
            except Exception as exc:
                logger.debug("Binance klines fetch failed for %s: %s", symbol, exc)

        # 3. Generuj fallback gdy brak zewnętrznych danych
        if not candles:
            candles = self._generate_mock_candles(symbol, limit)

        self.candle_cache[cache_key] = candles
        return candles
    
    async def _price_update_loop(self):
        """Pętla aktualizacji cen"""
        while self.running:
            try:
                # Aktualizuj ceny dla wszystkich śledzonych symboli
                for symbol in self.tracked_symbols:
                    price_data = await self._fetch_price_from_api(symbol)
                    if price_data:
                        self.price_cache[symbol] = price_data
                        
                        # Powiadom subskrybentów
                        if symbol in self.subscriptions:
                            for callback in self.subscriptions[symbol]:
                                try:
                                    callback(price_data)
                                except Exception as e:
                                    logger.error(f"Error in price callback for {symbol}: {e}")
                
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error in price update loop: {e}")
                await asyncio.sleep(5)  # Czekaj dłużej przy błędzie
    
    async def _fetch_price_from_api(self, symbol: str) -> Optional[PriceData]:
        """Pobiera cenę z API Binance"""
        try:
            if self._live_price_adapter:
                ticker = await self._live_price_adapter.fetch_ticker(symbol)
                return PriceData(
                    symbol=symbol,
                    price=float(ticker.get('last') or ticker.get('close') or ticker.get('ask') or 0.0),
                    bid=float(ticker.get('bid') or ticker.get('ask') or 0.0),
                    ask=float(ticker.get('ask') or ticker.get('bid') or 0.0),
                    volume_24h=float(ticker.get('baseVolume') or ticker.get('quoteVolume') or 0.0),
                    change_24h=float(ticker.get('change') or ticker.get('percentage', 0.0) * 0.01),
                    change_24h_percent=float(ticker.get('percentage') or 0.0),
                    timestamp=datetime.now(),
                )

            if not self.exchanges.get('binance', {}).get('enabled') or not requests:
                return self._get_mock_price_data(symbol)

            url = f"{self.exchanges['binance']['rest_url']}/ticker/24hr"
            params = {'symbol': symbol}

            response = requests.get(url, params=params, timeout=5)  # type: ignore[operator]
            if response.status_code == 200:
                data = response.json()

                return PriceData(
                    symbol=symbol,
                    price=float(data['lastPrice']),
                    bid=float(data['bidPrice']),
                    ask=float(data['askPrice']),
                    volume_24h=float(data['volume']),
                    change_24h=float(data['priceChange']),
                    change_24h_percent=float(data['priceChangePercent']),
                    timestamp=datetime.now()
                )
            else:
                logger.warning(f"API request failed for {symbol}: {response.status_code}")
                return self._get_mock_price_data(symbol)
                
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return self._get_mock_price_data(symbol)
    
    async def _fetch_orderbook_from_api(self, symbol: str, depth: int) -> Optional[OrderBookData]:
        """Pobiera order book z API"""
        try:
            if self._live_price_adapter:
                book = await self._live_price_adapter.fetch_order_book(symbol, depth)
                bids = [(float(b[0]), float(b[1])) for b in book.get('bids', [])[:depth]]
                asks = [(float(a[0]), float(a[1])) for a in book.get('asks', [])[:depth]]
                return OrderBookData(
                    symbol=symbol,
                    bids=bids,
                    asks=asks,
                    timestamp=datetime.now(),
                )

            if not self.exchanges.get('binance', {}).get('enabled') or not requests:
                return self._get_mock_orderbook_data(symbol)

            url = f"{self.exchanges['binance']['rest_url']}/depth"
            params = {'symbol': symbol, 'limit': depth}

            response = requests.get(url, params=params, timeout=5)  # type: ignore[operator]
            if response.status_code == 200:
                data = response.json()
                
                bids = [(float(bid[0]), float(bid[1])) for bid in data['bids']]
                asks = [(float(ask[0]), float(ask[1])) for ask in data['asks']]
                
                return OrderBookData(
                    symbol=symbol,
                    bids=bids,
                    asks=asks,
                    timestamp=datetime.now()
                )
            else:
                return self._get_mock_orderbook_data(symbol)
                
        except Exception as e:
            logger.error(f"Error fetching orderbook for {symbol}: {e}")
            return self._get_mock_orderbook_data(symbol)
    
    async def _start_binance_websocket(self):
        """Uruchamia WebSocket dla Binance"""
        try:
            if not self.exchanges.get('binance', {}).get('enabled'):
                logger.debug("Binance WebSocket disabled - offline mode")
                return
            if websocket is None:
                logger.warning("WebSocket library not available, falling back to mock data")
                return

            symbols = [symbol.lower() for symbol in self.tracked_symbols]
            if not symbols:
                logger.debug("No symbols tracked – skipping Binance WebSocket initialisation")
                return

            stream = "/".join(f"{symbol}@ticker" for symbol in symbols)
            url = f"{self.exchanges['binance']['ws_url']}/{stream}"

            def _on_message(ws, message):
                try:
                    payload = json.loads(message)
                except Exception as exc:  # pragma: no cover - defensive
                    logger.error("Failed to decode Binance WS payload: %s", exc)
                    return

                data = payload.get('data') if isinstance(payload, dict) else payload
                if isinstance(data, dict) and data.get('s'):
                    schedule_coro_safely(lambda: self._ingest_websocket_ticker(data))

            def _on_error(ws, error):  # pragma: no cover - requires live WS
                logger.error("Binance WS error: %s", error)

            def _on_close(ws, *_):  # pragma: no cover - requires live WS
                logger.info("Binance WS closed")

            def _on_open(ws):  # pragma: no cover - requires live WS
                logger.info("Binance WS connection opened for symbols: %s", ", ".join(self.tracked_symbols))

            ws_app = websocket.WebSocketApp(
                url,
                on_message=_on_message,
                on_error=_on_error,
                on_close=_on_close,
                on_open=_on_open,
            )

            thread = threading.Thread(target=ws_app.run_forever, daemon=True)
            thread.start()
            self.websocket_connections['binance'] = ws_app
            self._websocket_threads['binance'] = thread
            logger.info("Binance WebSocket started in background thread")

        except Exception as e:
            logger.error(f"Error starting Binance WebSocket: {e}")
    
    def _normalise_symbol_for_ccxt(self, symbol: str) -> str:
        if "/" in symbol:
            return symbol
        if symbol.endswith("USDT"):
            return f"{symbol[:-4]}/USDT"
        if symbol.endswith("USD"):
            return f"{symbol[:-3]}/USD"
        if symbol.endswith("USDC"):
            return f"{symbol[:-4]}/USDC"
        return symbol

    def _get_mock_price_data(self, symbol: str) -> PriceData:
        """Zwraca przykładowe dane cenowe"""
        mock_prices = {
            'BTCUSDT': 43000.0,
            'ETHUSDT': 2600.0,
            'ADAUSDT': 0.5,
            'DOTUSDT': 6.5
        }
        
        base_price = mock_prices.get(symbol, 100.0)
        
        return PriceData(
            symbol=symbol,
            price=base_price,
            bid=base_price * 0.999,
            ask=base_price * 1.001,
            volume_24h=1000000.0,
            change_24h=base_price * 0.02,
            change_24h_percent=2.0,
            timestamp=datetime.now()
        )
    
    def _get_mock_orderbook_data(self, symbol: str) -> OrderBookData:
        """Zwraca przykładowe dane order book"""
        price_data = self._get_mock_price_data(symbol)
        base_price = price_data.price
        
        # Generuj przykładowe bids i asks
        bids = []
        asks = []
        
        for i in range(10):
            bid_price = base_price * (1 - (i + 1) * 0.001)
            ask_price = base_price * (1 + (i + 1) * 0.001)
            quantity = 100.0 / (i + 1)
            
            bids.append((bid_price, quantity))
            asks.append((ask_price, quantity))
        
        return OrderBookData(
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=datetime.now()
        )

    def _generate_mock_candles(self, symbol: str, limit: int) -> List[Dict[str, Any]]:
        cached = self.price_cache.get(symbol)
        last_price = cached.price if cached else self._get_mock_price_data(symbol).price
        candles: List[Dict[str, Any]] = []
        base_time = datetime.now()
        for idx in range(limit):
            ts = base_time - timedelta(minutes=(limit - idx))
            open_price = last_price
            high = open_price * (1 + random.uniform(0.0, 0.004))
            low = open_price * (1 - random.uniform(0.0, 0.004))
            close = random.uniform(low, high)
            volume = random.uniform(25.0, 250.0)
            candles.append(
                {
                    "symbol": symbol,
                    "timestamp": ts,
                    "open": round(open_price, 4),
                    "high": round(high, 4),
                    "low": round(low, 4),
                    "close": round(close, 4),
                    "volume": round(volume, 4),
                }
            )
            last_price = close
        return candles


# Singleton instance
_market_data_manager_instance = None

def get_market_data_manager() -> MarketDataManager:
    """Zwraca singleton instancję MarketDataManager"""
    global _market_data_manager_instance
    if _market_data_manager_instance is None:
        _market_data_manager_instance = MarketDataManager()
    return _market_data_manager_instance


__all__ = ['MarketDataManager', 'PriceData', 'OrderBookData', 'TradeData', 'get_market_data_manager']
