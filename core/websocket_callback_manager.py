"""
WebSocket Callback Manager - Zunifikowany system callbacków dla wszystkich giełd

Standardizuje obsługę callbacków websocketów między różnymi giełdami,
zapewniając spójny interfejs i format danych.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum

from utils.logger import get_logger


class WebSocketEventType(Enum):
    """Typy wydarzeń WebSocket"""
    TICKER = "ticker"
    TRADES = "trades"
    ORDER_BOOK = "order_book"
    KLINE = "kline"
    USER_DATA = "user_data"
    ERROR = "error"
    CONNECTION = "connection"


@dataclass
class StandardizedTickerData:
    """Standardowy format danych ticker"""
    symbol: str
    price: float
    price_change: float
    price_change_percent: float
    high_24h: float
    low_24h: float
    volume_24h: float
    timestamp: datetime
    exchange: str
    raw_data: Dict[str, Any]


@dataclass
class StandardizedTradeData:
    """Standardowy format danych transakcji"""
    symbol: str
    price: float
    quantity: float
    side: str  # 'buy' lub 'sell'
    timestamp: datetime
    trade_id: str
    exchange: str
    raw_data: Dict[str, Any]


@dataclass
class StandardizedOrderBookData:
    """Standardowy format danych księgi zleceń"""
    symbol: str
    bids: List[List[float]]  # [[price, quantity], ...]
    asks: List[List[float]]  # [[price, quantity], ...]
    timestamp: datetime
    exchange: str
    raw_data: Dict[str, Any]


@dataclass
class StandardizedKlineData:
    """Standardowy format danych świec"""
    symbol: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    open_time: datetime
    close_time: datetime
    interval: str
    exchange: str
    raw_data: Dict[str, Any]


@dataclass
class WebSocketCallbackInfo:
    """Informacje o callbacku WebSocket"""
    callback_id: str
    event_type: WebSocketEventType
    symbol: str
    exchange: str
    callback_function: Callable
    created_at: datetime
    last_called: Optional[datetime] = None
    call_count: int = 0
    error_count: int = 0


class WebSocketCallbackManager:
    """
    Manager callbacków WebSocket - centralizuje i standardizuje obsługę
    callbacków dla wszystkich giełd
    """
    
    def __init__(self):
        self.logger = get_logger("websocket_callback_manager")
        
        # Rejestr callbacków
        self.callbacks: Dict[str, WebSocketCallbackInfo] = {}
        
        # Callbacki pogrupowane według typu
        self.callbacks_by_type: Dict[WebSocketEventType, List[str]] = {
            event_type: [] for event_type in WebSocketEventType
        }
        
        # Callbacki pogrupowane według giełdy
        self.callbacks_by_exchange: Dict[str, List[str]] = {}
        
        # Callbacki pogrupowane według symbolu
        self.callbacks_by_symbol: Dict[str, List[str]] = {}
        
        # Statystyki
        self.total_messages_processed = 0
        self.messages_by_exchange: Dict[str, int] = {}
        self.messages_by_type: Dict[WebSocketEventType, int] = {
            event_type: 0 for event_type in WebSocketEventType
        }
        
        # Parsery dla różnych giełd
        self.exchange_parsers = {
            'binance': self._parse_binance_data,
            'bybit': self._parse_bybit_data,
            'kucoin': self._parse_kucoin_data,
            'coinbase': self._parse_coinbase_data,
            'bitfinex': self._parse_bitfinex_data,
            'kraken': self._parse_kraken_data
        }
    
    def register_callback(self, 
                         event_type: WebSocketEventType,
                         symbol: str,
                         exchange: str,
                         callback_function: Callable) -> str:
        """
        Rejestruje callback dla określonego typu wydarzenia
        
        Args:
            event_type: Typ wydarzenia
            symbol: Symbol handlowy
            exchange: Nazwa giełdy
            callback_function: Funkcja callback
            
        Returns:
            ID callbacku
        """
        try:
            callback_id = f"{exchange}_{event_type.value}_{symbol}_{datetime.now().timestamp()}"
            
            callback_info = WebSocketCallbackInfo(
                callback_id=callback_id,
                event_type=event_type,
                symbol=symbol,
                exchange=exchange,
                callback_function=callback_function,
                created_at=datetime.now()
            )
            
            # Zapisz callback
            self.callbacks[callback_id] = callback_info
            
            # Dodaj do indeksów
            self.callbacks_by_type[event_type].append(callback_id)
            
            if exchange not in self.callbacks_by_exchange:
                self.callbacks_by_exchange[exchange] = []
            self.callbacks_by_exchange[exchange].append(callback_id)
            
            if symbol not in self.callbacks_by_symbol:
                self.callbacks_by_symbol[symbol] = []
            self.callbacks_by_symbol[symbol].append(callback_id)
            
            self.logger.info(f"Zarejestrowano callback {callback_id} dla {exchange} {symbol} {event_type.value}")
            return callback_id
            
        except Exception as e:
            self.logger.error(f"Błąd rejestracji callbacku: {e}")
            raise
    
    def unregister_callback(self, callback_id: str):
        """Wyrejestrowuje callback"""
        try:
            if callback_id not in self.callbacks:
                self.logger.warning(f"Callback {callback_id} nie istnieje")
                return
            
            callback_info = self.callbacks[callback_id]
            
            # Usuń z indeksów
            self.callbacks_by_type[callback_info.event_type].remove(callback_id)
            self.callbacks_by_exchange[callback_info.exchange].remove(callback_id)
            self.callbacks_by_symbol[callback_info.symbol].remove(callback_id)
            
            # Usuń callback
            del self.callbacks[callback_id]
            
            self.logger.info(f"Wyrejestrowano callback {callback_id}")
            
        except Exception as e:
            self.logger.error(f"Błąd wyrejestrowania callbacku {callback_id}: {e}")
    
    async def process_websocket_message(self, 
                                      exchange: str,
                                      raw_message: Union[str, Dict[str, Any]],
                                      event_type: WebSocketEventType,
                                      symbol: str = None):
        """
        Przetwarza wiadomość WebSocket i wywołuje odpowiednie callbacki
        
        Args:
            exchange: Nazwa giełdy
            raw_message: Surowa wiadomość
            event_type: Typ wydarzenia
            symbol: Symbol (jeśli znany)
        """
        try:
            # Parsuj wiadomość
            if isinstance(raw_message, str):
                try:
                    message_data = json.loads(raw_message)
                except json.JSONDecodeError:
                    self.logger.error(f"Błąd parsowania JSON: {raw_message}")
                    return
            else:
                message_data = raw_message
            
            # Użyj parsera specyficznego dla giełdy
            if exchange in self.exchange_parsers:
                standardized_data = await self.exchange_parsers[exchange](
                    message_data, event_type, symbol
                )
            else:
                self.logger.warning(f"Brak parsera dla giełdy {exchange}")
                return
            
            if standardized_data is None:
                return
            
            # Aktualizuj statystyki
            self.total_messages_processed += 1
            self.messages_by_exchange[exchange] = self.messages_by_exchange.get(exchange, 0) + 1
            self.messages_by_type[event_type] += 1
            
            # Znajdź i wywołaj odpowiednie callbacki
            await self._invoke_callbacks(event_type, standardized_data.symbol, standardized_data)
            
        except Exception as e:
            self.logger.error(f"Błąd przetwarzania wiadomości WebSocket {exchange}: {e}")
    
    async def _invoke_callbacks(self, 
                              event_type: WebSocketEventType,
                              symbol: str,
                              data: Any):
        """Wywołuje wszystkie pasujące callbacki"""
        try:
            # Znajdź callbacki dla tego typu wydarzenia i symbolu
            matching_callbacks = []
            
            for callback_id in self.callbacks_by_type[event_type]:
                callback_info = self.callbacks[callback_id]
                if callback_info.symbol == symbol or callback_info.symbol == "*":
                    matching_callbacks.append(callback_info)
            
            # Wywołaj callbacki
            for callback_info in matching_callbacks:
                try:
                    # Aktualizuj statystyki callbacku
                    callback_info.last_called = datetime.now()
                    callback_info.call_count += 1
                    
                    # Wywołaj callback
                    if asyncio.iscoroutinefunction(callback_info.callback_function):
                        await callback_info.callback_function(data)
                    else:
                        callback_info.callback_function(data)
                        
                except Exception as e:
                    callback_info.error_count += 1
                    self.logger.error(f"Błąd w callbacku {callback_info.callback_id}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Błąd wywołania callbacków: {e}")
    
    # === PARSERY DLA RÓŻNYCH GIEŁD ===
    
    async def _parse_binance_data(self, 
                                data: Dict[str, Any],
                                event_type: WebSocketEventType,
                                symbol: str = None) -> Optional[Any]:
        """Parser dla danych Binance"""
        try:
            if event_type == WebSocketEventType.TICKER:
                if 'c' in data:  # 24hr ticker
                    return StandardizedTickerData(
                        symbol=data.get('s', symbol),
                        price=float(data.get('c', 0)),
                        price_change=float(data.get('p', 0)),
                        price_change_percent=float(data.get('P', 0)),
                        high_24h=float(data.get('h', 0)),
                        low_24h=float(data.get('l', 0)),
                        volume_24h=float(data.get('v', 0)),
                        timestamp=datetime.now(),
                        exchange='binance',
                        raw_data=data
                    )
            
            elif event_type == WebSocketEventType.TRADES:
                if 'p' in data and 'q' in data:
                    return StandardizedTradeData(
                        symbol=data.get('s', symbol),
                        price=float(data.get('p', 0)),
                        quantity=float(data.get('q', 0)),
                        side='buy' if data.get('m', False) else 'sell',
                        timestamp=datetime.fromtimestamp(data.get('T', 0) / 1000),
                        trade_id=str(data.get('t', '')),
                        exchange='binance',
                        raw_data=data
                    )
            
            elif event_type == WebSocketEventType.KLINE:
                if 'k' in data:
                    kline = data['k']
                    return StandardizedKlineData(
                        symbol=kline.get('s', symbol),
                        open_price=float(kline.get('o', 0)),
                        high_price=float(kline.get('h', 0)),
                        low_price=float(kline.get('l', 0)),
                        close_price=float(kline.get('c', 0)),
                        volume=float(kline.get('v', 0)),
                        open_time=datetime.fromtimestamp(kline.get('t', 0) / 1000),
                        close_time=datetime.fromtimestamp(kline.get('T', 0) / 1000),
                        interval=kline.get('i', ''),
                        exchange='binance',
                        raw_data=data
                    )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Błąd parsowania danych Binance: {e}")
            return None
    
    async def _parse_bybit_data(self, 
                              data: Dict[str, Any],
                              event_type: WebSocketEventType,
                              symbol: str = None) -> Optional[Any]:
        """Parser dla danych Bybit"""
        try:
            if event_type == WebSocketEventType.TICKER:
                if 'data' in data and isinstance(data['data'], dict):
                    ticker_data = data['data']
                    return StandardizedTickerData(
                        symbol=ticker_data.get('symbol', symbol),
                        price=float(ticker_data.get('lastPrice', 0)),
                        price_change=float(ticker_data.get('price24hPcnt', 0)) * float(ticker_data.get('lastPrice', 0)) / 100,
                        price_change_percent=float(ticker_data.get('price24hPcnt', 0)),
                        high_24h=float(ticker_data.get('highPrice24h', 0)),
                        low_24h=float(ticker_data.get('lowPrice24h', 0)),
                        volume_24h=float(ticker_data.get('volume24h', 0)),
                        timestamp=datetime.now(),
                        exchange='bybit',
                        raw_data=data
                    )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Błąd parsowania danych Bybit: {e}")
            return None
    
    async def _parse_kucoin_data(self, 
                               data: Dict[str, Any],
                               event_type: WebSocketEventType,
                               symbol: str = None) -> Optional[Any]:
        """Parser dla danych KuCoin"""
        try:
            if event_type == WebSocketEventType.TICKER:
                if 'data' in data:
                    ticker_data = data['data']
                    return StandardizedTickerData(
                        symbol=ticker_data.get('symbol', symbol),
                        price=float(ticker_data.get('price', 0)),
                        price_change=float(ticker_data.get('changePrice', 0)),
                        price_change_percent=float(ticker_data.get('changeRate', 0)) * 100,
                        high_24h=float(ticker_data.get('high', 0)),
                        low_24h=float(ticker_data.get('low', 0)),
                        volume_24h=float(ticker_data.get('vol', 0)),
                        timestamp=datetime.now(),
                        exchange='kucoin',
                        raw_data=data
                    )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Błąd parsowania danych KuCoin: {e}")
            return None
    
    async def _parse_coinbase_data(self, 
                                 data: Dict[str, Any],
                                 event_type: WebSocketEventType,
                                 symbol: str = None) -> Optional[Any]:
        """Parser dla danych Coinbase"""
        try:
            if event_type == WebSocketEventType.TICKER:
                if data.get('type') == 'ticker':
                    return StandardizedTickerData(
                        symbol=data.get('product_id', symbol),
                        price=float(data.get('price', 0)),
                        price_change=0,  # Coinbase nie dostarcza bezpośrednio
                        price_change_percent=0,  # Coinbase nie dostarcza bezpośrednio
                        high_24h=float(data.get('high_24h', 0)),
                        low_24h=float(data.get('low_24h', 0)),
                        volume_24h=float(data.get('volume_24h', 0)),
                        timestamp=datetime.now(),
                        exchange='coinbase',
                        raw_data=data
                    )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Błąd parsowania danych Coinbase: {e}")
            return None
    
    async def _parse_bitfinex_data(self, 
                                 data: Dict[str, Any],
                                 event_type: WebSocketEventType,
                                 symbol: str = None) -> Optional[Any]:
        """Parser dla danych Bitfinex"""
        try:
            if event_type == WebSocketEventType.TICKER:
                if isinstance(data, list) and len(data) >= 10:
                    return StandardizedTickerData(
                        symbol=symbol,
                        price=float(data[6]),  # LAST_PRICE
                        price_change=float(data[4]),  # DAILY_CHANGE
                        price_change_percent=float(data[5]) * 100,  # DAILY_CHANGE_RELATIVE
                        high_24h=float(data[8]),  # HIGH
                        low_24h=float(data[9]),  # LOW
                        volume_24h=float(data[7]),  # VOLUME
                        timestamp=datetime.now(),
                        exchange='bitfinex',
                        raw_data=data
                    )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Błąd parsowania danych Bitfinex: {e}")
            return None
    
    async def _parse_kraken_data(self, 
                               data: Dict[str, Any],
                               event_type: WebSocketEventType,
                               symbol: str = None) -> Optional[Any]:
        """Parser dla danych Kraken"""
        try:
            if event_type == WebSocketEventType.TICKER:
                if isinstance(data, list) and len(data) >= 2:
                    ticker_data = data[1]
                    if 'c' in ticker_data:  # Current price
                        return StandardizedTickerData(
                            symbol=symbol,
                            price=float(ticker_data['c'][0]),
                            price_change=0,  # Kraken nie dostarcza bezpośrednio
                            price_change_percent=0,  # Kraken nie dostarcza bezpośrednio
                            high_24h=float(ticker_data.get('h', [0, 0])[1]),  # 24h high
                            low_24h=float(ticker_data.get('l', [0, 0])[1]),   # 24h low
                            volume_24h=float(ticker_data.get('v', [0, 0])[1]), # 24h volume
                            timestamp=datetime.now(),
                            exchange='kraken',
                            raw_data=data
                        )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Błąd parsowania danych Kraken: {e}")
            return None
    
    def get_callback_statistics(self) -> Dict[str, Any]:
        """Zwraca statystyki callbacków"""
        return {
            'total_callbacks': len(self.callbacks),
            'callbacks_by_type': {
                event_type.value: len(callback_ids) 
                for event_type, callback_ids in self.callbacks_by_type.items()
            },
            'callbacks_by_exchange': {
                exchange: len(callback_ids)
                for exchange, callback_ids in self.callbacks_by_exchange.items()
            },
            'total_messages_processed': self.total_messages_processed,
            'messages_by_exchange': self.messages_by_exchange,
            'messages_by_type': {
                event_type.value: count
                for event_type, count in self.messages_by_type.items()
            }
        }
    
    def get_callback_info(self, callback_id: str) -> Optional[Dict[str, Any]]:
        """Zwraca informacje o callbacku"""
        if callback_id not in self.callbacks:
            return None
        
        callback_info = self.callbacks[callback_id]
        return {
            'callback_id': callback_info.callback_id,
            'event_type': callback_info.event_type.value,
            'symbol': callback_info.symbol,
            'exchange': callback_info.exchange,
            'created_at': callback_info.created_at.isoformat(),
            'last_called': callback_info.last_called.isoformat() if callback_info.last_called else None,
            'call_count': callback_info.call_count,
            'error_count': callback_info.error_count
        }