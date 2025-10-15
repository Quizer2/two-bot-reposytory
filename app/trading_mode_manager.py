"""
Trading Mode Manager - Zarządzanie trybami handlowymi (Paper Trading / Live Trading)
"""

import asyncio
import logging
import threading
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import json

# Importy lokalne
from utils.config_manager import ConfigManager
from core.integrated_data_manager import get_integrated_data_manager
from core.trading_engine import OrderRequest, OrderSide, OrderType, OrderStatus

try:
    from app.api_config_manager import APIConfigManager
except Exception:  # pragma: no cover - fallback when manager is unavailable
    APIConfigManager = None  # type: ignore


class TradingMode(Enum):
    """Tryby handlowe"""
    PAPER = "paper"
    LIVE = "live"


@dataclass
class PaperBalance:
    """Saldo w trybie Paper Trading"""
    symbol: str
    balance: float = 0.0
    locked: float = 0.0
    avg_price: float = 0.0
    
    @property
    def free(self) -> float:
        """Dostępne środki"""
        return max(0.0, self.balance - self.locked)
    
    def to_dict(self) -> Dict:
        """Konwertuje do słownika"""
        return {
            'symbol': self.symbol,
            'balance': self.balance,
            'locked': self.locked,
            'avg_price': self.avg_price,
            'free': self.free
        }


@dataclass
class TradingOrder:
    """Zlecenie handlowe"""
    id: str
    symbol: str
    side: str  # 'buy' lub 'sell'
    amount: float
    price: float
    order_type: str = 'market'  # 'market' lub 'limit'
    status: str = 'pending'  # 'pending', 'filled', 'cancelled'
    timestamp: datetime = field(default_factory=datetime.now)
    mode: TradingMode = TradingMode.PAPER
    exchange: str = 'binance'
    fee: float = 0.0
    filled_amount: float = 0.0
    
    def to_dict(self) -> Dict:
        """Konwertuje do słownika"""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'side': self.side,
            'amount': self.amount,
            'price': self.price,
            'order_type': self.order_type,
            'status': self.status,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            'mode': self.mode.value if isinstance(self.mode, TradingMode) else self.mode,
            'exchange': self.exchange,
            'fee': self.fee,
            'filled_amount': self.filled_amount
        }


@dataclass
class RiskLimits:
    """Limity ryzyka"""
    max_position_size: float = 0.0
    max_daily_loss: float = 0.0
    max_drawdown: float = 0.0
    stop_loss_percent: float = 0.0
    take_profit_percent: float = 0.0
    
    def to_dict(self) -> Dict:
        """Konwertuje do słownika"""
        return {
            'max_position_size': self.max_position_size,
            'max_daily_loss': self.max_daily_loss,
            'max_drawdown': self.max_drawdown,
            'stop_loss_percent': self.stop_loss_percent,
            'take_profit_percent': self.take_profit_percent
        }


class TradingModeManager:
    """Manager zarządzający trybami handlowymi"""
    
    def __init__(self, config: ConfigManager, data_manager=None, api_config_manager=None):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.data_manager = data_manager or get_integrated_data_manager()
        self.api_config_manager = api_config_manager or (APIConfigManager() if APIConfigManager else None)

        # Synchronizacja
        self._lock = threading.RLock()
        self._async_lock = asyncio.Lock()
        self._initialized = False
        
        # Tryb handlowy
        self.current_mode = TradingMode.PAPER
        
        # Paper Trading
        self.initial_paper_balance = 10000.0  # $10,000 USD
        self.paper_balances: Dict[str, PaperBalance] = {}
        self.paper_orders: List[TradingOrder] = []
        self.paper_trades: List[Dict] = []
        self.live_orders: List[TradingOrder] = []
        self.live_trades: List[Dict[str, Any]] = []

        # Managery
        self.risk_manager = None
        self.notification_manager = None

        # Cache
        self._cache = {}
        self._cache_ttl = 30  # 30 sekund
        self._last_cache_update = {}

        # Migawka danych live używana przy blokadzie kluczy API.
        # Przechowujemy ostatnie poprawne podsumowanie, listę sald oraz historię transakcji
        # wyłącznie w pamięci, aby móc wyzerować widok bez utraty danych w bazie.
        self._live_snapshot_cache: Dict[str, Any] = {
            'summary': None,
            'balances': None,
            'transactions': None,
            'timestamp': None,
        }

        # Stan poświadczeń dla handlu live
        self._live_state_initialized = False
        self._live_credentials_ready = False
        self._live_credential_exchanges: List[str] = []
        self._live_disabled_reason = "Brak zweryfikowanych kluczy API"

        self.logger.info("Trading Mode Manager utworzony")
    
    async def initialize(self) -> bool:
        """Inicjalizuje Trading Mode Manager"""
        try:
            async with self._async_lock:
                if self._initialized:
                    return True
                
                self.logger.info("Inicjalizacja Trading Mode Manager...")
                
                # Data Manager jest już zainicjalizowany w konstruktorze
                
                # Inicjalizuj Risk Manager (jeśli dostępny)
                try:
                    from app.risk_management import RiskManager
                    from core.database_manager import DatabaseManager
                    
                    db_manager = DatabaseManager()
                    await db_manager.initialize()
                    
                    self.risk_manager = RiskManager(db_manager)
                    await self.risk_manager.initialize()
                    self.logger.info("Risk Manager zainicjalizowany")
                except ImportError as e:
                    self.logger.warning(f"Risk Manager niedostępny: {e}")
                except Exception as e:
                    self.logger.warning(f"Nie udało się zainicjalizować Risk Manager: {e}")
                
                # Inicjalizuj Notification Manager (jeśli dostępny)
                try:
                    from app.notification_manager import NotificationManager
                    from utils.encryption import EncryptionManager
                    
                    encryption_manager = EncryptionManager()
                    self.notification_manager = NotificationManager(None, encryption_manager)
                    await self.notification_manager.initialize()
                    self.logger.info("Notification Manager zainicjalizowany")
                except ImportError as e:
                    self.logger.warning(f"Notification Manager niedostępny: {e}")
                except Exception as e:
                    self.logger.warning(f"Nie udało się zainicjalizować Notification Manager: {e}")
                
                # Wczytaj tryb z konfiguracji
                saved_mode = self.config.get_setting('app', 'trading.default_mode', 'paper')
                try:
                    self.current_mode = TradingMode(saved_mode)
                except ValueError:
                    self.current_mode = TradingMode.PAPER
                    self.logger.warning(f"Nieprawidłowy tryb w konfiguracji: {saved_mode}, używam Paper Trading")

                # Inicjalizuj Paper Trading
                await self.initialize_paper_trading()

                # Zsynchronizuj stan kluczy API – brak kluczy oznacza blokadę trybu live
                self.refresh_live_trading_status()

                self._initialized = True
                self.logger.info(f"Trading Mode Manager zainicjalizowany w trybie: {self.current_mode.value}")
                return True

        except Exception as e:
            self.logger.error(f"Błąd inicjalizacji Trading Mode Manager: {e}")
            return False
    
    async def initialize_paper_trading(self):
        """Inicjalizuje Paper Trading z początkowym saldem"""
        try:
            with self._lock:
                # Sprawdź czy już są salda
                if not self.paper_balances:
                    # Utwórz początkowe saldo USDT
                    self.paper_balances['USDT'] = PaperBalance(
                        symbol='USDT',
                        balance=self.initial_paper_balance,
                        locked=0.0,
                        avg_price=1.0
                    )
                    
                    self.logger.info(f"Utworzono początkowe saldo Paper Trading: ${self.initial_paper_balance} USDT")
                else:
                    self.logger.info(f"Wczytano salda Paper Trading: {len(self.paper_balances)} walut")
                    
        except Exception as e:
            self.logger.error(f"Błąd inicjalizacji Paper Trading: {e}")
    
    async def switch_mode(self, new_mode: TradingMode) -> bool:
        """Przełącza tryb handlowy"""
        try:
            if not isinstance(new_mode, TradingMode):
                self.logger.error(f"Nieprawidłowy tryb: {new_mode}")
                return False
            
            if new_mode == self.current_mode:
                self.logger.info(f"Tryb już ustawiony na: {new_mode.value}")
                return True
            
            old_mode = self.current_mode
            
            # Jeśli przełączamy na Live Trading, sprawdź konfigurację
            if new_mode == TradingMode.LIVE:
                if not self.refresh_live_trading_status():
                    self.logger.error("Live Trading niedostępny – brak aktywnych kluczy API")
                    return False

                if not await self.verify_live_trading_setup():
                    self.logger.error("Live Trading nie jest poprawnie skonfigurowany")
                    return False

            with self._lock:
                self.current_mode = new_mode
            
            # Zapisz nowy tryb do konfiguracji
            self.config.set_setting('app', 'trading.default_mode', new_mode.value)
            
            self.logger.info(f"Przełączono tryb z {old_mode.value} na {new_mode.value}")
            
            # Wyślij powiadomienie o zmianie trybu
            await self._send_mode_change_notification(old_mode, new_mode)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Błąd przełączania trybu: {e}")
            return False
    
    async def _send_mode_change_notification(self, old_mode: TradingMode, new_mode: TradingMode):
        """Wysyła powiadomienie o zmianie trybu handlowego"""
        try:
            if not self.notification_manager:
                return
            
            mode_names = {
                TradingMode.PAPER: "Paper Trading",
                TradingMode.LIVE: "Live Trading"
            }
            
            old_name = mode_names.get(old_mode, old_mode.value)
            new_name = mode_names.get(new_mode, new_mode.value)
            
            # Wyślij powiadomienie
            await self.notification_manager.send_notification(
                title="Zmiana trybu handlowego",
                message=f"Tryb handlowy został zmieniony z {old_name} na {new_name}",
                metadata={
                    "old_mode": old_mode.value,
                    "new_mode": new_mode.value,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            self.logger.info(f"Wysłano powiadomienie o zmianie trybu: {old_name} → {new_name}")
            
        except Exception as e:
            self.logger.error(f"Błąd wysyłania powiadomienia o zmianie trybu: {e}")
    
    async def verify_live_trading_setup(self) -> bool:
        """Sprawdza czy Live Trading jest poprawnie skonfigurowany"""
        try:
            if not self.live_trading_available():
                self.logger.error(self._live_disabled_reason)
                return False

            # Sprawdź połączenie z Data Manager
            if hasattr(self.data_manager, 'test_connections'):
                test_result = await self.data_manager.test_connections()
                if not test_result:
                    self.logger.error("Nie można nawiązać połączenia z giełdami")
                    return False
            
            self.logger.info(
                "Live Trading skonfigurowany dla giełd: %s",
                ', '.join(self._live_credential_exchanges)
            )
            return True

        except Exception as e:
            self.logger.error(f"Błąd weryfikacji Live Trading: {e}")
            return False
    
    async def get_current_balances(self) -> Dict[str, Dict]:
        """Pobiera aktualne salda w zależności od trybu"""
        try:
            if self.current_mode == TradingMode.PAPER:
                return await self.get_paper_balances()
            else:
                if not self.live_trading_available():
                    self.logger.warning("Live Trading wyłączony – zwracam puste salda")
                    return {}
                return await self.get_live_balances()
                
        except Exception as e:
            self.logger.error(f"Błąd pobierania sald: {e}")
            return {}

    async def get_zeroed_live_view(self) -> Dict[str, Any]:
        """Zwraca wyzerowaną migawkę portfela na potrzeby UI bez modyfikowania bazy danych."""
        try:
            snapshot = await self._load_live_snapshot_from_sources()
            if snapshot:
                self._cache_live_snapshot(
                    summary=snapshot.get('summary'),
                    balances=snapshot.get('balances'),
                    transactions=snapshot.get('transactions'),
                )

            summary = self._live_snapshot_cache.get('summary')
            balances = self._live_snapshot_cache.get('balances')
            transactions = self._live_snapshot_cache.get('transactions') or []

            zero_summary = self._zero_summary_clone(summary)
            zero_balances = self._zero_balances_clone(balances)

            return {
                'summary': zero_summary,
                'balances': zero_balances,
                'transactions': [],  # Historia ma być pusta w widoku, ale nie jest kasowana z DB
                'original_transactions': transactions,
                'meta': {
                    'cached_at': self._live_snapshot_cache.get('timestamp'),
                    'source': 'live_disabled',
                },
            }
        except Exception as exc:
            self.logger.error("Nie udało się przygotować wyzerowanej migawki live: %s", exc)
            return {
                'summary': self._zero_summary_clone(None),
                'balances': [],
                'transactions': [],
                'meta': {'source': 'live_disabled'},
            }
    
    async def get_paper_balances(self) -> Dict[str, Dict]:
        """Pobiera salda Paper Trading"""
        try:
            balances = {}
            
            with self._lock:
                for symbol, paper_balance in self.paper_balances.items():
                    # Pobierz aktualną cenę
                    current_price = 1.0
                    if symbol != 'USDT' and self.production_data_manager:
                        try:
                            price_data = await self.production_data_manager.get_real_price(f"{symbol}/USDT")
                            if price_data:
                                current_price = float(price_data)
                            else:
                                current_price = paper_balance.avg_price if paper_balance.avg_price > 0 else 1.0
                        except Exception:
                            current_price = paper_balance.avg_price if paper_balance.avg_price > 0 else 1.0
                    
                    # Oblicz wartość USD
                    usd_value = paper_balance.balance * current_price
                    
                    # Oblicz zmianę 24h
                    change_24h = await self.calculate_24h_change(symbol, current_price)
                    
                    balances[symbol] = {
                        'balance': paper_balance.balance,
                        'locked': paper_balance.locked,
                        'free': paper_balance.free,
                        'usd_value': usd_value,
                        'price': current_price,
                        'change_24h': change_24h,
                        'avg_price': paper_balance.avg_price,
                        'mode': 'paper'
                    }
            
            return balances
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania sald Paper Trading: {e}")
            return {}
    
    async def get_live_balances(self) -> Dict[str, Dict]:
        """Pobiera prawdziwe salda z API giełd"""
        try:
            if not self.live_trading_available():
                self.logger.debug("Pominięto pobieranie sald live – brak aktywnych kluczy API")
                return {}

            if not hasattr(self.data_manager, 'get_real_balance'):
                self.logger.warning("Data Manager nie obsługuje prawdziwych sald")
                return {}

            # Pobierz prawdziwe saldo
            raw_balance = await self.data_manager.get_real_balance()

            if not raw_balance:
                self.logger.warning("Nie można pobrać sald z API")
                return {}

            balances = {}

            # Przetwórz dane z API giełdy
            for symbol, balance_data in raw_balance.items():
                if isinstance(balance_data, dict):
                    free_balance = float(balance_data.get('free', 0))
                    locked_balance = float(balance_data.get('used', 0))
                    total_balance = float(balance_data.get('total', free_balance + locked_balance))
                    
                    # Pomiń waluty z zerowym saldem
                    if total_balance > 0:
                        # Pobierz aktualną cenę
                        current_price = 1.0
                        if symbol != 'USDT':
                            try:
                                price_data = await self.data_manager.get_real_price(f"{symbol}/USDT")
                                if price_data:
                                    current_price = float(price_data)
                            except Exception:
                                pass
                        
                        # Oblicz wartość USD
                        usd_value = total_balance * current_price
                        
                        # Oblicz zmianę 24h
                        change_24h = await self.calculate_24h_change(symbol, current_price)
                        
                        balances[symbol] = {
                            'balance': total_balance,
                            'locked': locked_balance,
                            'free': free_balance,
                            'usd_value': usd_value,
                            'price': current_price,
                            'change_24h': change_24h,
                            'mode': 'live'
                        }

            if balances:
                self._cache_live_snapshot(balances=balances)

            return balances

        except Exception as e:
            self.logger.error(f"Błąd pobierania prawdziwych sald: {e}")
            return {}
    
    async def calculate_24h_change(self, symbol: str, current_price: float) -> float:
        """Oblicza zmianę ceny w ciągu 24h"""
        try:
            if symbol == 'USDT' or not self.production_data_manager:
                return 0.0
            
            # Pobierz ticker z danymi 24h
            ticker = await self.production_data_manager.get_real_ticker(f"{symbol}/USDT")
            if ticker and isinstance(ticker, dict) and 'percentage' in ticker:
                return float(ticker['percentage'])
            
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Błąd obliczania zmiany 24h dla {symbol}: {e}")
            return 0.0
    
    async def place_order(self, symbol: str, side: str, amount: float, 
                         price: Optional[float] = None, order_type: str = 'market') -> Optional[TradingOrder]:
        """Składa zlecenie w odpowiednim trybie"""
        try:
            # Dodaj trace log przed składaniem zlecenia
            self.logger.debug(f"TRACE: order.submitted - symbol={symbol}, side={side}, amount={amount}, type={order_type}, mode={self.current_mode.value}")
            
            # Walidacja parametrów
            if not self._validate_order_params(symbol, side, amount, price, order_type):
                return None
            
            if self.current_mode == TradingMode.PAPER:
                return await self.place_paper_order(symbol, side, amount, price, order_type)
            else:
                return await self.place_live_order(symbol, side, amount, price, order_type)
                
        except Exception as e:
            self.logger.error(f"Błąd składania zlecenia: {e}")
            return None
    
    def _validate_order_params(self, symbol: str, side: str, amount: float, 
                              price: Optional[float], order_type: str) -> bool:
        """Waliduje parametry zlecenia"""
        try:
            # Sprawdź symbol
            if not symbol or '/' not in symbol:
                self.logger.error(f"Nieprawidłowy symbol: {symbol}")
                return False
            
            # Sprawdź stronę
            if side not in ['buy', 'sell']:
                self.logger.error(f"Nieprawidłowa strona zlecenia: {side}")
                return False
            
            # Sprawdź ilość
            if amount <= 0:
                self.logger.error(f"Nieprawidłowa ilość: {amount}")
                return False
            
            # Sprawdź typ zlecenia
            if order_type not in ['market', 'limit']:
                self.logger.error(f"Nieprawidłowy typ zlecenia: {order_type}")
                return False
            
            # Sprawdź cenę dla zleceń limit
            if order_type == 'limit' and (price is None or price <= 0):
                self.logger.error(f"Nieprawidłowa cena dla zlecenia limit: {price}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Błąd walidacji parametrów zlecenia: {e}")
            return False
    
    async def place_paper_order(self, symbol: str, side: str, amount: float, 
                               price: Optional[float] = None, order_type: str = 'market') -> Optional[TradingOrder]:
        """Składa zlecenie w trybie Paper Trading"""
        try:
            # Pobierz aktualną cenę rynkową
            if not self.production_data_manager:
                self.logger.error("Production Data Manager nie jest dostępny")
                return None
            
            market_price = await self.production_data_manager.get_real_price(symbol)
            if market_price is None:
                self.logger.error(f"Nie można pobrać ceny dla {symbol}")
                return None
            
            market_price = float(market_price)
            
            # Ustaw cenę zlecenia
            order_price = price if price and order_type == 'limit' else market_price
            
            # Sprawdź czy mamy wystarczające środki
            if not await self.check_paper_balance(symbol, side, amount, order_price):
                self.logger.error("Niewystarczające środki dla zlecenia Paper Trading")
                return None
            
            # Sprawdź limity ryzyka
            if self.risk_manager:
                try:
                    risk_check = await self.risk_manager.check_order_risk(
                        bot_id=0,  # Paper trading bot ID
                        symbol=symbol,
                        side=side,
                        amount=amount,
                        price=order_price
                    )
                    if not risk_check:
                        self.logger.warning(f"Zlecenie odrzucone przez system zarządzania ryzykiem: {symbol}")
                        return None
                except Exception as e:
                    self.logger.warning(f"Błąd sprawdzania ryzyka: {e}")
            
            # Utwórz zlecenie
            order = TradingOrder(
                id=f"paper_{int(datetime.now().timestamp() * 1000)}",
                symbol=symbol,
                side=side,
                amount=amount,
                price=order_price,
                order_type=order_type,
                status='filled',  # W Paper Trading zlecenia są od razu wypełniane
                timestamp=datetime.now(),
                mode=TradingMode.PAPER,
                fee=amount * order_price * 0.001  # 0.1% fee
            )
            
            # Wykonaj zlecenie
            await self.execute_paper_order(order)
            
            with self._lock:
                self.paper_orders.append(order)
            
            self.logger.info(f"Zlecenie Paper Trading wykonane: {side} {amount} {symbol} @ ${order_price}")
            
            return order
            
        except Exception as e:
            self.logger.error(f"Błąd zlecenia Paper Trading: {e}")
            return None
    
    async def place_live_order(self, symbol: str, side: str, amount: float,
                              price: Optional[float] = None, order_type: str = 'market') -> Optional[TradingOrder]:
        """Składa prawdziwe zlecenie przez API"""
        try:
            self.logger.info(f"Składanie prawdziwego zlecenia: {side} {amount} {symbol} ({order_type})")

            if not self.live_trading_available():
                self.logger.error("Zlecenia Live są zablokowane – brak aktywnych kluczy API")
                return None

            if not hasattr(self.data_manager, 'get_real_balance'):
                self.logger.error("Data Manager nie obsługuje prawdziwych sald")
                return None
            
            # Sprawdź saldo przed złożeniem zlecenia
            balance = await self.data_manager.get_real_balance()
            if not balance:
                self.logger.error("Nie można pobrać salda - anulowanie zlecenia")
                return None
            
            # Walidacja salda
            if not await self.check_live_balance(symbol, side, amount, price, balance):
                self.logger.error("Niewystarczające środki na koncie")
                return None

            trading_engine = getattr(self.data_manager, 'trading_engine', None)
            if trading_engine is None:
                self.logger.error("Trading engine nie jest dostępny - nie mogę złożyć zlecenia live")
                return None

            try:
                side_enum = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
                order_type_enum = OrderType.MARKET if order_type.lower() == 'market' else OrderType.LIMIT
            except Exception:
                self.logger.error(f"Nieobsługiwany typ zlecenia: {order_type}")
                return None

            request = OrderRequest(
                symbol=symbol,
                side=side_enum,
                order_type=order_type_enum,
                quantity=amount,
                price=price,
                client_order_id=f"live_{int(datetime.now().timestamp() * 1000)}"
            )

            if self.risk_manager:
                try:
                    risk_ok = await self.risk_manager.check_order_risk(
                        bot_id=0,
                        symbol=symbol,
                        side=side,
                        amount=amount,
                        price=price
                    )
                    if not risk_ok:
                        self.logger.warning("Zlecenie odrzucone przez system zarządzania ryzykiem")
                        return None
                except Exception as exc:
                    self.logger.warning(f"Błąd walidacji ryzyka dla zlecenia live: {exc}")
                    return None

            response = await trading_engine.place_order(request)

            status_map = {
                OrderStatus.FILLED: 'filled',
                OrderStatus.PARTIALLY_FILLED: 'partially_filled',
                OrderStatus.NEW: 'pending',
                OrderStatus.CANCELED: 'cancelled',
                OrderStatus.REJECTED: 'rejected',
                OrderStatus.EXPIRED: 'expired',
            }
            status = status_map.get(response.status, 'pending')
            executed_price = response.average_price or response.price or price or 0.0

            order = TradingOrder(
                id=response.order_id,
                symbol=response.symbol,
                side=side.lower(),
                amount=response.quantity,
                price=executed_price,
                order_type=order_type.lower(),
                status=status,
                timestamp=response.timestamp,
                mode=TradingMode.LIVE,
                exchange=(response.metadata or {}).get('adapter', 'live'),
                fee=response.commission or 0.0,
                filled_amount=response.filled_quantity or 0.0
            )

            with self._lock:
                self.live_orders.append(order)
                if order.status in ('filled', 'partially_filled'):
                    trade_entry = {
                        'id': order.id,
                        'timestamp': order.timestamp.isoformat() if isinstance(order.timestamp, datetime) else order.timestamp,
                        'symbol': order.symbol,
                        'side': order.side,
                        'amount': order.filled_amount or order.amount,
                        'price': order.price,
                        'fee': order.fee,
                        'mode': 'live'
                    }
                    self.live_trades.append(trade_entry)

            self.logger.info(
                f"Zlecenie Live złożone: {order.side} {order.amount} {order.symbol} @ {order.price} (status: {order.status})"
            )

            return order

        except Exception as e:
            self.logger.error(f"Błąd prawdziwego zlecenia: {e}")
            return None
    
    async def check_paper_balance(self, symbol: str, side: str, amount: float, price: float) -> bool:
        """Sprawdza czy są wystarczające środki w Paper Trading"""
        try:
            parts = symbol.split('/')
            if len(parts) != 2:
                return False
            
            base_symbol, quote_symbol = parts
            
            with self._lock:
                if side == 'buy':
                    # Sprawdź saldo waluty kwotowej (np. USDT)
                    required_amount = amount * price
                    quote_balance = self.paper_balances.get(quote_symbol)
                    
                    if not quote_balance or quote_balance.free < required_amount:
                        return False
                        
                else:  # sell
                    # Sprawdź saldo waluty bazowej (np. BTC)
                    base_balance = self.paper_balances.get(base_symbol)
                    
                    if not base_balance or base_balance.free < amount:
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Błąd sprawdzania salda Paper Trading: {e}")
            return False
    
    async def check_live_balance(self, symbol: str, side: str, amount: float, 
                                price: Optional[float], balance: Dict) -> bool:
        """Sprawdza czy są wystarczające środki w Live Trading"""
        try:
            parts = symbol.split('/')
            if len(parts) != 2:
                return False
            
            base_symbol, quote_symbol = parts
            
            if not balance:
                return False
            
            if side == 'buy':
                # Sprawdź saldo waluty kwotowej (np. USDT)
                if price is None:
                    # Dla zleceń market pobierz aktualną cenę
                    if not self.production_data_manager:
                        return False
                    price_data = await self.production_data_manager.get_real_price(symbol)
                    if not price_data:
                        return False
                    price = float(price_data)
                
                required_amount = amount * price
                quote_balance_data = balance.get(quote_symbol, {})
                
                if isinstance(quote_balance_data, dict):
                    free_balance = float(quote_balance_data.get('free', 0))
                    if free_balance < required_amount:
                        self.logger.warning(f"Niewystarczające środki {quote_symbol}: {free_balance} < {required_amount}")
                        return False
                else:
                    return False
                    
            else:  # sell
                # Sprawdź saldo waluty bazowej (np. BTC)
                base_balance_data = balance.get(base_symbol, {})
                
                if isinstance(base_balance_data, dict):
                    free_balance = float(base_balance_data.get('free', 0))
                    if free_balance < amount:
                        self.logger.warning(f"Niewystarczające środki {base_symbol}: {free_balance} < {amount}")
                        return False
                else:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Błąd sprawdzania salda Live Trading: {e}")
            return False
    
    async def execute_paper_order(self, order: TradingOrder):
        """Wykonuje zlecenie Paper Trading"""
        try:
            parts = order.symbol.split('/')
            if len(parts) != 2:
                raise ValueError(f"Nieprawidłowy symbol: {order.symbol}")
            
            base_symbol, quote_symbol = parts
            
            with self._lock:
                # Upewnij się, że salda istnieją
                if base_symbol not in self.paper_balances:
                    self.paper_balances[base_symbol] = PaperBalance(base_symbol, 0.0)
                if quote_symbol not in self.paper_balances:
                    self.paper_balances[quote_symbol] = PaperBalance(quote_symbol, 0.0)
                
                if order.side == 'buy':
                    # Kup: zmniejsz saldo quote, zwiększ saldo base
                    cost = order.amount * order.price + order.fee
                    
                    self.paper_balances[quote_symbol].balance -= cost
                    self.paper_balances[base_symbol].balance += order.amount
                    
                    # Aktualizuj średnią cenę
                    old_balance = self.paper_balances[base_symbol].balance - order.amount
                    if old_balance > 0:
                        old_value = old_balance * self.paper_balances[base_symbol].avg_price
                        new_value = order.amount * order.price
                        total_value = old_value + new_value
                        total_balance = self.paper_balances[base_symbol].balance
                        self.paper_balances[base_symbol].avg_price = total_value / total_balance
                    else:
                        self.paper_balances[base_symbol].avg_price = order.price
                        
                else:  # sell
                    # Sprzedaj: zmniejsz saldo base, zwiększ saldo quote
                    revenue = order.amount * order.price - order.fee
                    
                    self.paper_balances[base_symbol].balance -= order.amount
                    self.paper_balances[quote_symbol].balance += revenue
                
                # Dodaj do historii transakcji
                trade = {
                    'timestamp': order.timestamp.isoformat() if isinstance(order.timestamp, datetime) else order.timestamp,
                    'symbol': order.symbol,
                    'side': order.side,
                    'amount': order.amount,
                    'price': order.price,
                    'fee': order.fee,
                    'mode': 'paper'
                }
                self.paper_trades.append(trade)
            
        except Exception as e:
            self.logger.error(f"Błąd wykonywania zlecenia Paper Trading: {e}")
    
    def get_current_mode(self) -> TradingMode:
        """Zwraca aktualny tryb handlowy"""
        return self.current_mode
    
    def is_paper_mode(self) -> bool:
        """Sprawdza czy aktywny jest tryb Paper Trading"""
        return self.current_mode == TradingMode.PAPER
    
    def is_live_mode(self) -> bool:
        """Sprawdza czy aktywny jest tryb Live Trading"""
        return self.current_mode == TradingMode.LIVE
    
    async def get_trading_statistics(self) -> Dict[str, Any]:
        """Pobiera statystyki handlowe"""
        try:
            if self.current_mode == TradingMode.PAPER:
                return await self.get_paper_statistics()
            else:
                return await self.get_live_statistics()
                
        except Exception as e:
            self.logger.error(f"Błąd pobierania statystyk: {e}")
            return {}
    
    async def get_paper_statistics(self) -> Dict[str, Any]:
        """Pobiera statystyki Paper Trading"""
        try:
            total_value = 0.0
            total_pnl = 0.0
            
            with self._lock:
                for symbol, balance in self.paper_balances.items():
                    if balance.balance > 0:
                        current_price = 1.0
                        if symbol != 'USDT' and self.production_data_manager:
                            try:
                                price_data = await self.production_data_manager.get_real_price(f"{symbol}/USDT")
                                if price_data:
                                    current_price = float(price_data)
                                else:
                                    current_price = balance.avg_price if balance.avg_price > 0 else 1.0
                            except Exception:
                                current_price = balance.avg_price if balance.avg_price > 0 else 1.0
                        
                        value = balance.balance * current_price
                        total_value += value
                        
                        if symbol != 'USDT' and balance.avg_price > 0:
                            pnl = (current_price - balance.avg_price) * balance.balance
                            total_pnl += pnl
            
            return {
                'mode': 'paper',
                'total_value': total_value,
                'total_pnl': total_pnl,
                'initial_balance': self.initial_paper_balance,
                'total_return': ((total_value - self.initial_paper_balance) / self.initial_paper_balance) * 100 if self.initial_paper_balance > 0 else 0,
                'trades_count': len(self.paper_trades),
                'orders_count': len(self.paper_orders)
            }
            
        except Exception as e:
            self.logger.error(f"Błąd statystyk Paper Trading: {e}")
            return {}
    
    async def get_live_statistics(self) -> Dict[str, Any]:
        """Pobiera statystyki Live Trading"""
        try:
            if not self.live_trading_available():
                return {
                    'mode': 'live_disabled',
                    'total_value': 0.0,
                    'total_pnl': 0.0,
                    'trades_count': 0,
                    'orders_count': len(self.live_orders)
                }

            total_value = 0.0
            total_pnl = 0.0
            try:
                portfolio_snapshot = await self.data_manager.get_portfolio_widget_data()
                if isinstance(portfolio_snapshot, dict):
                    summary = portfolio_snapshot.get('summary') or {}
                    total_value = float(summary.get('total_value', 0.0) or 0.0)
                    total_pnl = float(summary.get('unrealized_pnl', 0.0) or 0.0)
                    balances = portfolio_snapshot.get('balances')
                    transactions = portfolio_snapshot.get('transactions')
                    self._cache_live_snapshot(
                        summary=summary,
                        balances=balances,
                        transactions=transactions,
                    )
            except Exception as exc:
                self.logger.debug(f"Nie udało się pobrać danych portfela: {exc}")

            return {
                'mode': 'live',
                'total_value': total_value,
                'total_pnl': total_pnl,
                'trades_count': len(self.live_trades),
                'orders_count': len(self.live_orders)
            }

        except Exception as e:
            self.logger.error(f"Błąd statystyk Live Trading: {e}")
            return {}

    async def _load_live_snapshot_from_sources(self) -> Dict[str, Any]:
        """Ładuje ostatnią migawkę portfela z dostępnych źródeł bez modyfikacji bazy."""
        snapshot: Dict[str, Any] = {}

        if self.data_manager and hasattr(self.data_manager, 'get_portfolio_widget_data'):
            try:
                snapshot = await self.data_manager.get_portfolio_widget_data() or {}
            except Exception as exc:
                self.logger.debug("Nie udało się pobrać migawki portfela: %s", exc)
                snapshot = {}

        # Dla historii spróbuj pobrać transakcje – tylko do cache, nie do wyświetlenia
        if self.data_manager and hasattr(self.data_manager, 'get_recent_trades'):
            try:
                trades = await self.data_manager.get_recent_trades(limit=100)
                if snapshot is not None:
                    snapshot = dict(snapshot)
                    snapshot['transactions'] = trades
            except Exception as exc:
                self.logger.debug("Nie udało się pobrać historii transakcji: %s", exc)

        return snapshot

    def _cache_live_snapshot(self, summary=None, balances=None, transactions=None):
        """Zapamiętuje ostatni znany stan live na potrzeby zerowania widoku."""
        if summary is not None:
            self._live_snapshot_cache['summary'] = summary
        if balances is not None:
            self._live_snapshot_cache['balances'] = balances
        if transactions is not None:
            self._live_snapshot_cache['transactions'] = transactions
        if any(value is not None for value in (summary, balances, transactions)):
            self._live_snapshot_cache['timestamp'] = datetime.now()

    def _zero_summary_clone(self, summary):
        """Zwraca kopię podsumowania z wyzerowanymi wartościami."""
        from core.portfolio_manager import PortfolioSummary, AssetPosition

        if summary is None:
            return PortfolioSummary(
                total_value=0.0,
                available_balance=0.0,
                invested_amount=0.0,
                total_profit_loss=0.0,
                total_profit_loss_percent=0.0,
                daily_change=0.0,
                daily_change_percent=0.0,
                positions=[],
                last_updated=datetime.now(),
            )

        if isinstance(summary, PortfolioSummary):
            base_summary = PortfolioSummary(
                total_value=summary.total_value,
                available_balance=summary.available_balance,
                invested_amount=summary.invested_amount,
                total_profit_loss=summary.total_profit_loss,
                total_profit_loss_percent=summary.total_profit_loss_percent,
                daily_change=summary.daily_change,
                daily_change_percent=summary.daily_change_percent,
                positions=list(summary.positions or []),
                last_updated=datetime.now(),
            )
        elif isinstance(summary, dict):
            positions_raw = summary.get('positions') or []
            positions: List[AssetPosition] = []
            for position in positions_raw:
                if isinstance(position, AssetPosition):
                    positions.append(position)
                elif isinstance(position, dict):
                    positions.append(
                        AssetPosition(
                            symbol=str(position.get('symbol', 'UNKNOWN')),
                            amount=float(position.get('amount', 0.0) or 0.0),
                            average_price=float(position.get('average_price', 0.0) or 0.0),
                            current_price=float(position.get('current_price', 0.0) or 0.0),
                            value=float(position.get('value', 0.0) or 0.0),
                            profit_loss=float(position.get('profit_loss', 0.0) or 0.0),
                            profit_loss_percent=float(position.get('profit_loss_percent', 0.0) or 0.0),
                            last_updated=datetime.now(),
                        )
                    )
            base_summary = PortfolioSummary(
                total_value=float(summary.get('total_value', 0.0) or 0.0),
                available_balance=float(summary.get('available_balance', 0.0) or 0.0),
                invested_amount=float(summary.get('invested_amount', 0.0) or 0.0),
                total_profit_loss=float(summary.get('total_profit_loss', 0.0) or 0.0),
                total_profit_loss_percent=float(summary.get('total_profit_loss_percent', 0.0) or 0.0),
                daily_change=float(summary.get('daily_change', 0.0) or 0.0),
                daily_change_percent=float(summary.get('daily_change_percent', 0.0) or 0.0),
                positions=positions,
                last_updated=datetime.now(),
            )
        else:
            # Nieznany format – utwórz pusty obiekt
            return PortfolioSummary(
                total_value=0.0,
                available_balance=0.0,
                invested_amount=0.0,
                total_profit_loss=0.0,
                total_profit_loss_percent=0.0,
                daily_change=0.0,
                daily_change_percent=0.0,
                positions=[],
                last_updated=datetime.now(),
            )

        zero_positions: List[AssetPosition] = []
        for position in base_summary.positions:
            if isinstance(position, AssetPosition):
                zero_positions.append(
                    AssetPosition(
                        symbol=position.symbol,
                        amount=0.0,
                        average_price=position.average_price,
                        current_price=0.0,
                        value=0.0,
                        profit_loss=0.0,
                        profit_loss_percent=0.0,
                        last_updated=datetime.now(),
                    )
                )

        base_summary.total_value = 0.0
        base_summary.available_balance = 0.0
        base_summary.invested_amount = 0.0
        base_summary.total_profit_loss = 0.0
        base_summary.total_profit_loss_percent = 0.0
        base_summary.daily_change = 0.0
        base_summary.daily_change_percent = 0.0
        base_summary.positions = zero_positions
        base_summary.last_updated = datetime.now()

        return base_summary

    def _zero_balances_clone(self, balances):
        """Zwraca listę słowników z wyzerowanymi saldami i metadanymi oryginalnych wartości."""
        zeroed: List[Dict[str, Any]] = []

        if isinstance(balances, dict):
            iterable = balances.items()
        elif isinstance(balances, list):
            iterable = enumerate(balances)
        else:
            iterable = []

        for key, entry in iterable:
            if hasattr(entry, 'asset') and hasattr(entry, 'free'):
                symbol = getattr(entry, 'asset', str(key))
                free_amount = float(getattr(entry, 'free', 0.0) or 0.0)
                locked_amount = float(getattr(entry, 'locked', 0.0) or 0.0)
                total_amount = free_amount + locked_amount
                zeroed.append({
                    'symbol': symbol,
                    'balance': 0.0,
                    'free': 0.0,
                    'locked': 0.0,
                    'usd_value': 0.0,
                    'mode': 'live_disabled',
                    'meta': {
                        'original_free': free_amount,
                        'original_locked': locked_amount,
                        'original_total': total_amount,
                    }
                })
            elif isinstance(entry, dict):
                symbol = str(entry.get('symbol') or entry.get('asset') or key)
                original_balance = float(entry.get('balance', entry.get('amount', 0.0)) or 0.0)
                original_free = float(entry.get('free', 0.0) or 0.0)
                original_locked = float(entry.get('locked', entry.get('hold', 0.0)) or 0.0)
                zeroed.append({
                    **{k: v for k, v in entry.items() if k not in {'balance', 'amount', 'free', 'locked', 'usd_value'}},
                    'symbol': symbol,
                    'balance': 0.0,
                    'free': 0.0,
                    'locked': 0.0,
                    'usd_value': 0.0,
                    'mode': 'live_disabled',
                    'meta': {
                        'original_free': original_free,
                        'original_locked': original_locked,
                        'original_total': original_balance if original_balance else original_free + original_locked,
                    }
                })

        return zeroed

    # ------------------------------------------------------------------
    # Obsługa stanu poświadczeń Live Trading
    # ------------------------------------------------------------------
    def refresh_live_trading_status(self) -> bool:
        """Odświeża stan poświadczeń Live Trading i zwraca czy handel live jest dostępny."""
        try:
            if not self.api_config_manager:
                self._live_state_initialized = True
                self._live_credentials_ready = False
                self._live_credential_exchanges = []
                self._live_disabled_reason = "Manager konfiguracji API nie jest dostępny"
                return False

            self.api_config_manager.load_api_config()
            enabled = self.api_config_manager.get_enabled_exchanges()
            valid = [
                exchange
                for exchange in enabled
                if self.api_config_manager.validate_exchange_config(exchange)
            ]

            self._live_state_initialized = True
            self._live_credentials_ready = bool(valid)
            self._live_credential_exchanges = valid

            if not self._live_credentials_ready:
                self._live_disabled_reason = (
                    "Brak aktywnych kluczy API i tajnych kluczy dla trybu Live Trading"
                )
            else:
                self._live_disabled_reason = ""

            if not self._live_credentials_ready and self.current_mode == TradingMode.LIVE:
                with self._lock:
                    self.current_mode = TradingMode.PAPER
                try:
                    self.config.set_setting(
                        'app',
                        'trading.default_mode',
                        'paper',
                        meta={'source': 'trading_mode_manager', 'reason': 'missing_api_keys'}
                    )
                except Exception as exc:
                    self.logger.debug("Nie udało się zapisać wymuszonego trybu paper: %s", exc)

            return self._live_credentials_ready

        except Exception as exc:
            self._live_state_initialized = True
            self._live_credentials_ready = False
            self._live_credential_exchanges = []
            self._live_disabled_reason = f"Błąd weryfikacji kluczy API: {exc}"
            self.logger.error("Błąd podczas odświeżania stanu kluczy API: %s", exc)
            return False

    def live_trading_available(self) -> bool:
        """Zwraca informację czy dostępne są poprawne klucze dla handlu live."""
        if not self._live_state_initialized:
            self.refresh_live_trading_status()
        return self._live_credentials_ready

    def get_live_trading_block_reason(self) -> str:
        """Zwraca powód blokady trybu live (lub pusty string gdy dostępny)."""
        if not self._live_state_initialized:
            self.refresh_live_trading_status()
        return self._live_disabled_reason

    def get_configured_live_exchanges(self) -> List[str]:
        """Zwraca listę giełd z kompletnymi poświadczeniami live."""
        if not self._live_state_initialized:
            self.refresh_live_trading_status()
        return list(self._live_credential_exchanges)
    
    async def get_total_balance_usd(self) -> float:
        """Pobiera całkowitą wartość portfela w USD"""
        try:
            balances = await self.get_current_balances()
            total = sum(balance.get('usd_value', 0) for balance in balances.values())
            return total
        except Exception as e:
            self.logger.error(f"Błąd pobierania całkowitego salda: {e}")
            return 0.0
    
    async def close(self):
        """Zamyka Trading Mode Manager"""
        try:
            self.logger.info("Zamykanie Trading Mode Manager...")
            
            # Data Manager jest zarządzany przez IntegratedDataManager
            
            if self.notification_manager:
                await self.notification_manager.stop()
            
            with self._lock:
                self._cache.clear()
                self._last_cache_update.clear()
            
            self.logger.info("Trading Mode Manager zamknięty")
            
        except Exception as e:
            self.logger.error(f"Błąd zamykania Trading Mode Manager: {e}")


# Singleton instance
_trading_mode_manager = None
_trading_mode_manager_lock = threading.Lock()


def get_trading_mode_manager(config: ConfigManager = None, data_manager=None) -> TradingModeManager:
    """Pobiera singleton instance Trading Mode Manager"""
    global _trading_mode_manager
    
    with _trading_mode_manager_lock:
        if _trading_mode_manager is None:
            if config is None or data_manager is None:
                raise ValueError("Config Manager i Data Manager są wymagane przy pierwszym wywołaniu")
            _trading_mode_manager = TradingModeManager(config, data_manager)
        
        return _trading_mode_manager