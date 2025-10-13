"""Market Data Manager - zarządzanie danymi rynkowymi.

This version prefers deterministic, offline-friendly behaviour so the
automated integration flows can execute without real exchange access or
heavy optional dependencies such as ``websocket``.  Real-time features
can still be enabled by setting the ``ENABLE_REAL_MARKET_DATA``
environment variable to a truthy value.
"""

from __future__ import annotations

import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
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

from utils.helpers import get_or_create_event_loop, schedule_coro_safely

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
        self.websocket_connections: Dict[str, Any] = {}
        self.running = False
        self.update_interval = 1.0  # sekundy
        
        # Symbole do śledzenia
        self.tracked_symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
        
        # WebSocket callback manager
        self.ws_callback_manager = WebSocketCallbackManager()
        self._setup_websocket_callbacks()
        
        enable_live = os.environ.get('ENABLE_REAL_MARKET_DATA', '0').lower() in ('1', 'true', 'yes')

        # Konfiguracja giełd (domyślnie tryb offline)
        self.exchanges = {
            'binance': {
                'rest_url': 'https://api.binance.com/api/v3',
                'ws_url': 'wss://stream.binance.com:9443/ws',
                'enabled': enable_live
            },
            'bybit': {
                'rest_url': 'https://api.bybit.com/v2/public',
                'ws_url': 'wss://stream.bybit.com/realtime',
                'enabled': False  # Wyłączone domyślnie
            }
        }
        
        # Symbole do śledzenia - pojedyncza inicjalizacja
        # self.tracked_symbols już ustawione wcześniej; zapewnij spójność
        # Pozostaw bez ponownej inicjalizacji, użyj metody set_tracked_symbols aby modyfikować
        # (patrz definicja metody poniżej)
        # self.tracked_symbols = self.tracked_symbols
    
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
            if not self.exchanges['binance']['enabled'] or not requests:
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
            if not self.exchanges['binance']['enabled'] or not requests:
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
            if not self.exchanges['binance']['enabled']:
                logger.debug("Binance WebSocket disabled - offline mode")
                return
            if websocket is None:
                logger.warning("WebSocket library not available, falling back to mock data")
                return

            logger.info("WebSocket for Binance will be implemented in future updates")

        except Exception as e:
            logger.error(f"Error starting Binance WebSocket: {e}")
    
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


# Singleton instance
_market_data_manager_instance = None

def get_market_data_manager() -> MarketDataManager:
    """Zwraca singleton instancję MarketDataManager"""
    global _market_data_manager_instance
    if _market_data_manager_instance is None:
        _market_data_manager_instance = MarketDataManager()
    return _market_data_manager_instance


__all__ = ['MarketDataManager', 'PriceData', 'OrderBookData', 'TradeData', 'get_market_data_manager']
