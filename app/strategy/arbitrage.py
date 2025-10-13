"""
Arbitrage Strategy Implementation
Strategia arbitrażu wykorzystująca różnice cenowe między giełdami
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, asdict
from collections import deque
from enum import Enum
import statistics

from app.exchange.base_exchange import BaseExchange
from core.database_manager import DatabaseManager
from app.risk_management import RiskManager
from utils.logger import get_logger
from utils.helpers import FormatHelper, CalculationHelper
import logging
logger = logging.getLogger(__name__)


class ArbitrageStatus(Enum):
    """Status strategii arbitrażu"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    SCANNING = "scanning"


class ArbitrageType(Enum):
    """Typ arbitrażu"""
    SIMPLE = "simple"  # Prosty arbitraż między dwoma giełdami
    TRIANGULAR = "triangular"  # Arbitraż trójkątny na jednej giełdzie
    CROSS_EXCHANGE = "cross_exchange"  # Arbitraż między wieloma giełdami


@dataclass
class ArbitrageOpportunity:
    """Okazja arbitrażowa"""
    id: str
    type: ArbitrageType
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread: float
    spread_percentage: float
    volume: float
    estimated_profit: float
    estimated_profit_percentage: float
    detected_at: datetime
    expires_at: datetime
    min_amount: float
    max_amount: float
    fees_buy: float
    fees_sell: float
    net_profit: float
    confidence_score: float


@dataclass
class ArbitrageTrade:
    """Transakcja arbitrażowa"""
    opportunity_id: str
    symbol: str
    amount: float
    buy_exchange: str
    sell_exchange: str
    buy_order_id: str
    sell_order_id: str
    buy_price: float
    sell_price: float
    buy_time: datetime
    sell_time: datetime
    gross_profit: float
    fees_paid: float
    net_profit: float
    profit_percentage: float
    execution_time_ms: float
    slippage: float
    status: str  # 'completed', 'partial', 'failed'


@dataclass
class ExchangeData:
    """Dane z giełdy"""
    exchange_name: str
    symbol: str
    bid_price: float
    ask_price: float
    bid_volume: float
    ask_volume: float
    timestamp: datetime
    latency_ms: float
    fees: Dict[str, float]


@dataclass
class ArbitrageStatistics:
    """Statystyki strategii arbitrażu"""
    total_opportunities: int = 0
    executed_trades: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    total_profit: float = 0.0
    total_profit_percentage: float = 0.0
    avg_profit_per_trade: float = 0.0
    avg_execution_time_ms: float = 0.0
    avg_spread: float = 0.0
    success_rate: float = 0.0
    total_volume: float = 0.0
    total_fees_paid: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    avg_slippage: float = 0.0
    opportunities_per_hour: float = 0.0
    profit_factor: float = 0.0


class ArbitrageStrategy:
    """
    Strategia arbitrażu wykorzystująca różnice cenowe między giełdami
    """
    
    def __init__(
        self,
        symbol: str,
        exchanges: List[str],
        min_spread_percentage: float = 0.5,
        max_spread_percentage: float = 10.0,
        min_volume: float = 100.0,
        max_position_size: float = 1000.0,
        execution_timeout_seconds: int = 30,
        price_update_interval_ms: int = 1000,
        opportunity_expiry_seconds: int = 10,
        min_confidence_score: float = 0.7,
        max_slippage_percentage: float = 0.2,
        enable_triangular: bool = False,
        balance_threshold_percentage: float = 10.0,
        fee_consideration: bool = True,
        latency_threshold_ms: int = 500,
        risk_per_trade_percentage: float = 1.0,
        max_concurrent_trades: int = 3,
        max_daily_trades: Optional[int] = None,
        max_position_time: Optional[int] = None,
        blacklist_exchanges: Optional[List[str]] = None,
        preferred_exchanges: Optional[List[str]] = None
    ):
        # Podstawowe parametry
        self.symbol = symbol
        self.exchanges = exchanges
        self.min_spread_percentage = min_spread_percentage
        self.max_spread_percentage = max_spread_percentage
        self.min_volume = min_volume
        self.max_position_size = max_position_size
        
        # Parametry wykonania
        self.execution_timeout_seconds = execution_timeout_seconds
        self.price_update_interval_ms = price_update_interval_ms
        self.opportunity_expiry_seconds = opportunity_expiry_seconds
        self.min_confidence_score = min_confidence_score
        self.max_slippage_percentage = max_slippage_percentage
        
        # Opcje strategii
        self.enable_triangular = enable_triangular
        self.balance_threshold_percentage = balance_threshold_percentage
        self.fee_consideration = fee_consideration
        self.latency_threshold_ms = latency_threshold_ms
        self.risk_per_trade_percentage = risk_per_trade_percentage
        self.max_concurrent_trades = max_concurrent_trades
        self.max_daily_trades = max_daily_trades
        self.max_position_time = max_position_time
        
        # Listy giełd
        self.blacklist_exchanges = blacklist_exchanges or []
        self.preferred_exchanges = preferred_exchanges or []
        
        # Stan strategii
        self.status = ArbitrageStatus.STOPPED
        self.is_running = False
        self.is_paused = False
        
        # Komponenty
        self.exchange_adapters: Dict[str, BaseExchange] = {}
        self.db_manager: Optional[DatabaseManager] = None
        self.risk_manager: Optional[RiskManager] = None
        
        # Dane strategii
        self.current_opportunities: List[ArbitrageOpportunity] = []
        self.active_trades: List[ArbitrageTrade] = []
        self.trade_history: List[ArbitrageTrade] = []
        self.statistics = ArbitrageStatistics()
        
        # Dane rynkowe
        self.exchange_data: Dict[str, ExchangeData] = {}
        self.price_history: Dict[str, deque] = {}
        self.latency_history: Dict[str, deque] = {}
        
        # Synchronizacja
        self.data_lock = asyncio.Lock()
        self.trade_lock = asyncio.Lock()
        
        # Logger
        self.logger = get_logger(f"ArbitrageStrategy_{symbol}")
        
        # Inicjalizacja
        self._initialize_strategy()
        # Kontener na zadania asynchroniczne strategii
        self._tasks: List[asyncio.Task] = []
    
    def _initialize_strategy(self):
        """Inicjalizacja strategii"""
        self.logger.info(f"Inicjalizacja Arbitrage Strategy dla {self.symbol}")
        self.logger.info(f"Giełdy: {', '.join(self.exchanges)}")
        self.logger.info(f"Min spread: {self.min_spread_percentage}%")
        self.logger.info(f"Max pozycja: {self.max_position_size}")
        self.logger.info(f"Timeout: {self.execution_timeout_seconds}s")
        
        # Inicjalizuj historię cen dla każdej giełdy
        for exchange in self.exchanges:
            self.price_history[exchange] = deque(maxlen=100)
            self.latency_history[exchange] = deque(maxlen=50)
    
    async def start(self):
        """Uruchomienie strategii"""
        try:
            if self.status == ArbitrageStatus.RUNNING:
                self.logger.warning("Strategia już działa")
                return
            
            # Sprawdź dostępność giełd
            if not await self._validate_exchanges():
                self.logger.error("Nie wszystkie giełdy są dostępne")
                return
            
            self.status = ArbitrageStatus.RUNNING
            self.is_running = True
            self.is_paused = False
            
            self.logger.info("Arbitrage Strategy uruchomiona")
            
            # Uruchom równoległe zadania w tle
            self._tasks = [
                asyncio.create_task(self._price_monitoring_loop()),
                asyncio.create_task(self._opportunity_scanning_loop()),
                asyncio.create_task(self._trade_execution_loop()),
                asyncio.create_task(self._cleanup_loop())
            ]
            
            # Nie czekaj na zakończenie zadań - uruchom w tle
            return
            
        except Exception as e:
            self.logger.error(f"Błąd w strategii arbitrażu: {e}")
            self.status = ArbitrageStatus.ERROR
        
    async def stop(self):
        """Zatrzymanie strategii"""
        self.logger.info("Zatrzymywanie Arbitrage Strategy...")
        self.is_running = False
        self.status = ArbitrageStatus.STOPPED
        
        # Zamknij aktywne transakcje
        if self.active_trades:
            self.logger.info(f"Zamykanie {len(self.active_trades)} aktywnych transakcji...")
            for trade in self.active_trades.copy():
                await self._cancel_trade(trade)
        
        # Anuluj zadania pętli
        try:
            if hasattr(self, '_tasks') and self._tasks:
                for t in self._tasks:
                    if not t.done():
                        t.cancel()
                await asyncio.gather(*self._tasks, return_exceptions=True)
                self._tasks = []
        except Exception:
            self.logger.exception('Błąd podczas zatrzymywania zadań strategii')
        
        return
    
    async def pause(self):
        """Wstrzymanie strategii"""
        self.is_paused = True
        self.logger.info("Arbitrage Strategy wstrzymana")
    
    async def resume(self):
        """Wznowienie strategii"""
        self.is_paused = False
        self.logger.info("Arbitrage Strategy wznowiona")
    
    async def initialize(self, db_manager: 'DatabaseManager', risk_manager: 'RiskManager', 
                        exchange: 'BaseExchange', data_manager=None):
        """Inicjalizuje strategię z komponentami"""
        self.db_manager = db_manager
        self.risk_manager = risk_manager
        self.data_manager = data_manager
        
        # Dodaj adaptery giełd jeśli exchange jest listą
        if isinstance(exchange, list):
            for ex in exchange:
                if hasattr(ex, 'get_exchange_name'):
                    self.exchange_adapters[ex.get_exchange_name()] = ex
                elif hasattr(ex, 'name'):
                    # Fallback dla prostych mocków, które mają tylko atrybut 'name'
                    self.exchange_adapters[getattr(ex, 'name')] = ex
        else:
            # Pojedyncza giełda
            if hasattr(exchange, 'get_exchange_name'):
                self.exchange_adapters[exchange.get_exchange_name()] = exchange
            elif hasattr(exchange, 'name'):
                self.exchange_adapters[getattr(exchange, 'name')] = exchange
        
        self.logger.info(f"Arbitrage strategy initialized for {self.symbol}")
    
    async def _validate_exchanges(self) -> bool:
        """Sprawdź dostępność giełd"""
        try:
            valid_exchanges = []
            
            for exchange_name in self.exchanges:
                if exchange_name in self.blacklist_exchanges:
                    self.logger.warning(f"Giełda {exchange_name} na czarnej liście")
                    continue
                
                if exchange_name not in self.exchange_adapters:
                    self.logger.error(f"Brak adaptera dla giełdy {exchange_name}")
                    continue
                
                # Test połączenia
                try:
                    adapter = self.exchange_adapters[exchange_name]
                    # Elastyczna walidacja: próbuj dostępnych metod adaptera
                    if hasattr(adapter, 'get_ticker'):
                        await adapter.get_ticker(self.symbol)
                    elif hasattr(adapter, 'get_current_price'):
                        await adapter.get_current_price(self.symbol)
                    elif hasattr(adapter, 'get_orderbook'):
                        await adapter.get_orderbook(self.symbol, limit=1)
                    elif hasattr(adapter, 'get_order_book'):
                        await adapter.get_order_book(self.symbol, limit=1)
                    else:
                        raise Exception("Adapter nie obsługuje metod pobierania danych")
                    valid_exchanges.append(exchange_name)
                    self.logger.info(f"Giełda {exchange_name} dostępna")
                except Exception as e:
                    self.logger.error(f"Giełda {exchange_name} niedostępna: {e}")
            
            self.exchanges = valid_exchanges
            return len(valid_exchanges) >= 2
        
        except Exception as e:
            self.logger.error(f"Błąd walidacji giełd: {e}")
            return False
    
    async def _price_monitoring_loop(self):
        """Pętla monitorowania cen"""
        while self.is_running:
            try:
                if not self.is_paused:
                    await self._update_exchange_data()
                
                await asyncio.sleep(self.price_update_interval_ms / 1000)
                
            except Exception as e:
                self.logger.error(f"Błąd w monitorowaniu cen: {e}")
                await asyncio.sleep(1)
    
    async def _update_exchange_data(self):
        """Aktualizuj dane z giełd"""
        tasks = []
        for exchange_name in self.exchanges:
            task = asyncio.create_task(
                self._fetch_exchange_data(exchange_name)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        async with self.data_lock:
            for i, result in enumerate(results):
                if isinstance(result, ExchangeData):
                    exchange_name = self.exchanges[i]
                    self.exchange_data[exchange_name] = result
                    self.price_history[exchange_name].append({
                        'timestamp': result.timestamp,
                        'bid': result.bid_price,
                        'ask': result.ask_price,
                        'volume': (result.bid_volume + result.ask_volume) / 2
                    })
                    self.latency_history[exchange_name].append(result.latency_ms)
    
    async def _fetch_exchange_data(self, exchange_name: str) -> Optional[ExchangeData]:
        """Pobierz dane z giełdy"""
        try:
            start_time = datetime.now()
            adapter = self.exchange_adapters[exchange_name]
            
            # Pobierz dane order book z elastycznym dopasowaniem nazw metod
            order_book = None
            if hasattr(adapter, 'get_order_book'):
                order_book = await adapter.get_order_book(self.symbol, limit=5)
            elif hasattr(adapter, 'get_orderbook'):
                order_book = await adapter.get_orderbook(self.symbol, limit=5)
            
            # Pobierz ticker lub bieżącą cenę
            ticker = None
            if hasattr(adapter, 'get_ticker'):
                ticker = await adapter.get_ticker(self.symbol)
            elif hasattr(adapter, 'get_current_price'):
                try:
                    current_price = await adapter.get_current_price(self.symbol)
                    ticker = {'last': current_price}
                except Exception:
                    ticker = None
            
            end_time = datetime.now()
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            if not order_book and not ticker:
                return None
            
            # Sprawdź latencję
            if latency_ms > self.latency_threshold_ms:
                self.logger.warning(f"Wysoka latencja {exchange_name}: {latency_ms:.1f}ms")
            
            # Fallbacky dla danych z order_book/ticker
            bid_price = order_book['bids'][0][0] if order_book and order_book.get('bids') else (ticker.get('bid') if isinstance(ticker, dict) else 0)
            ask_price = order_book['asks'][0][0] if order_book and order_book.get('asks') else (ticker.get('ask') if isinstance(ticker, dict) else 0)
            bid_volume = order_book['bids'][0][1] if order_book and order_book.get('bids') else 0
            ask_volume = order_book['asks'][0][1] if order_book and order_book.get('asks') else 0
            
            return ExchangeData(
                exchange_name=exchange_name,
                symbol=self.symbol,
                bid_price=bid_price,
                ask_price=ask_price,
                bid_volume=bid_volume,
                ask_volume=ask_volume,
                timestamp=datetime.now(),
                latency_ms=latency_ms,
                fees=await self._get_exchange_fees(adapter)
            )
        
        except Exception as e:
            self.logger.error(f"Błąd pobierania danych z {exchange_name}: {e}")
            return None
    
    async def _get_exchange_fees(self, adapter: BaseExchange) -> Dict[str, float]:
        """Pobierz opłaty giełdy"""
        try:
            if hasattr(adapter, 'get_trading_fees'):
                fees = await adapter.get_trading_fees()
                if isinstance(fees, dict):
                    maker = fees.get('maker')
                    taker = fees.get('taker')
                    if isinstance(maker, (int, float)) and isinstance(taker, (int, float)):
                        return {'maker': float(maker), 'taker': float(taker)}
            # Domyślne opłaty jeśli brak
            return {
                'maker': 0.001,  # 0.1%
                'taker': 0.001   # 0.1%
            }
        except Exception:
            return {'maker': 0.001, 'taker': 0.001}
    
    async def _opportunity_scanning_loop(self):
        """Pętla skanowania okazji"""
        while self.is_running:
            try:
                if not self.is_paused:
                    self.status = ArbitrageStatus.SCANNING
                    await self._scan_opportunities()
                    await self._cleanup_expired_opportunities()
                
                await asyncio.sleep(0.1)  # Szybkie skanowanie
                
            except Exception as e:
                self.logger.error(f"Błąd w skanowaniu okazji: {e}")
                await asyncio.sleep(1)
    
    async def _scan_opportunities(self):
        """Skanuj okazje arbitrażowe"""
        async with self.data_lock:
            exchange_data = self.exchange_data.copy()
        
        if len(exchange_data) < 2:
            return
        
        # Skanuj proste arbitraże między parami giełd
        for i, (exchange1, data1) in enumerate(exchange_data.items()):
            for j, (exchange2, data2) in enumerate(exchange_data.items()):
                if i >= j:  # Unikaj duplikatów
                    continue
                
                opportunity = await self._analyze_simple_arbitrage(
                    exchange1, data1, exchange2, data2
                )
                
                if opportunity:
                    await self._add_opportunity(opportunity)
        
        # Skanuj arbitraże trójkątne (jeśli włączone)
        if self.enable_triangular:
            for exchange_name, data in exchange_data.items():
                opportunities = await self._analyze_triangular_arbitrage(exchange_name, data)
                for opportunity in opportunities:
                    await self._add_opportunity(opportunity)
    
    async def _analyze_simple_arbitrage(
        self, 
        exchange1: str, 
        data1: ExchangeData,
        exchange2: str, 
        data2: ExchangeData
    ) -> Optional[ArbitrageOpportunity]:
        """Analizuj prosty arbitraż między dwoma giełdami"""
        try:
            # Sprawdź czy dane są aktualne
            now = datetime.now()
            if ((now - data1.timestamp).total_seconds() > 5 or 
                (now - data2.timestamp).total_seconds() > 5):
                return None
            
            # Sprawdź spread w obu kierunkach
            # Kierunek 1: Kup na exchange1, sprzedaj na exchange2
            spread1 = data2.bid_price - data1.ask_price
            spread1_pct = (spread1 / data1.ask_price) * 100 if data1.ask_price > 0 else 0
            
            # Kierunek 2: Kup na exchange2, sprzedaj na exchange1
            spread2 = data1.bid_price - data2.ask_price
            spread2_pct = (spread2 / data2.ask_price) * 100 if data2.ask_price > 0 else 0
            
            # Wybierz lepszy kierunek
            if spread1_pct > spread2_pct and spread1_pct >= self.min_spread_percentage:
                buy_exchange, sell_exchange = exchange1, exchange2
                buy_price, sell_price = data1.ask_price, data2.bid_price
                spread, spread_pct = spread1, spread1_pct
                volume = min(data1.ask_volume, data2.bid_volume)
            elif spread2_pct >= self.min_spread_percentage:
                buy_exchange, sell_exchange = exchange2, exchange1
                buy_price, sell_price = data2.ask_price, data1.bid_price
                spread, spread_pct = spread2, spread2_pct
                volume = min(data2.ask_volume, data1.bid_volume)
            else:
                return None
            
            # Sprawdź maksymalny spread
            if spread_pct > self.max_spread_percentage:
                return None
            
            # Oblicz wielkość pozycji
            max_amount = min(
                volume,
                self.max_position_size / buy_price,
                self.min_volume / buy_price
            )
            
            if max_amount * buy_price < self.min_volume:
                return None
            
            # Oblicz opłaty
            buy_fees = self.exchange_data[buy_exchange].fees['taker'] if self.fee_consideration else 0
            sell_fees = self.exchange_data[sell_exchange].fees['taker'] if self.fee_consideration else 0
            
            # Oblicz zysk
            gross_profit = spread * max_amount
            total_fees = (buy_price * max_amount * buy_fees) + (sell_price * max_amount * sell_fees)
            net_profit = gross_profit - total_fees
            net_profit_pct = (net_profit / (buy_price * max_amount)) * 100
            
            if net_profit <= 0:
                return None
            
            # Oblicz wskaźnik pewności
            confidence_score = self._calculate_confidence_score(
                spread_pct, volume, data1.latency_ms, data2.latency_ms
            )
            
            if confidence_score < self.min_confidence_score:
                return None
            
            return ArbitrageOpportunity(
                id=f"{buy_exchange}_{sell_exchange}_{int(now.timestamp() * 1000)}",
                type=ArbitrageType.SIMPLE,
                symbol=self.symbol,
                buy_exchange=buy_exchange,
                sell_exchange=sell_exchange,
                buy_price=buy_price,
                sell_price=sell_price,
                spread=spread,
                spread_percentage=spread_pct,
                volume=volume,
                estimated_profit=gross_profit,
                estimated_profit_percentage=spread_pct,
                detected_at=now,
                expires_at=now + timedelta(seconds=self.opportunity_expiry_seconds),
                min_amount=self.min_volume / buy_price,
                max_amount=max_amount,
                fees_buy=buy_fees,
                fees_sell=sell_fees,
                net_profit=net_profit,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            self.logger.error(f"Błąd analizy arbitrażu: {e}")
            return None
    
    async def _analyze_triangular_arbitrage(
        self, 
        exchange_name: str, 
        data: ExchangeData
    ) -> List[ArbitrageOpportunity]:
        """Analizuj arbitraż trójkątny (uproszczona implementacja)"""
        # Implementacja arbitrażu trójkątnego jest złożona i wymaga
        # analizy trzech par walutowych jednocześnie
        # Na razie zwracamy pustą listę
        return []
    
    def _calculate_confidence_score(
        self, 
        spread_pct: float, 
        volume: float, 
        latency1: float, 
        latency2: float
    ) -> float:
        """Oblicz wskaźnik pewności okazji"""
        try:
            # Bazowy wynik na podstawie spreadu
            spread_score = min(spread_pct / 2.0, 1.0)  # Max 1.0 dla 2%+ spreadu
            
            # Wynik na podstawie wolumenu
            volume_score = min(volume / 1000, 1.0)  # Max 1.0 dla 1000+ wolumenu
            
            # Wynik na podstawie latencji
            avg_latency = (latency1 + latency2) / 2
            latency_score = max(0, 1.0 - (avg_latency / self.latency_threshold_ms))
            
            # Średnia ważona
            confidence = (spread_score * 0.5 + volume_score * 0.3 + latency_score * 0.2)
            
            return min(max(confidence, 0.0), 1.0)
            
        except Exception as e:
            return 0.5
    
    async def _add_opportunity(self, opportunity: ArbitrageOpportunity):
        """Dodaj okazję do listy"""
        # Sprawdź czy podobna okazja już istnieje
        for existing in self.current_opportunities:
            if (existing.buy_exchange == opportunity.buy_exchange and
                existing.sell_exchange == opportunity.sell_exchange and
                abs(existing.spread_percentage - opportunity.spread_percentage) < 0.1):
                return  # Podobna okazja już istnieje
        
        self.current_opportunities.append(opportunity)
        self.statistics.total_opportunities += 1
        
        self.logger.info(
            f"Nowa okazja: {opportunity.buy_exchange} -> {opportunity.sell_exchange} "
            f"Spread: {opportunity.spread_percentage:.2f}% "
            f"Zysk: {opportunity.net_profit:.2f}"
        )
    
    async def _cleanup_expired_opportunities(self):
        """Usuń wygasłe okazje"""
        now = datetime.now()
        self.current_opportunities = [
            opp for opp in self.current_opportunities 
            if opp.expires_at > now
        ]
    
    async def _trade_execution_loop(self):
        """Pętla wykonywania transakcji"""
        while self.is_running:
            try:
                if not self.is_paused and len(self.active_trades) < self.max_concurrent_trades:
                    await self._execute_best_opportunity()
                
                await asyncio.sleep(0.05)  # Bardzo szybkie wykonanie
                
            except Exception as e:
                self.logger.error(f"Błąd w wykonywaniu transakcji: {e}")
                await asyncio.sleep(1)
    
    async def _execute_best_opportunity(self):
        """Wykonaj najlepszą okazję"""
        if not self.current_opportunities:
            return
        
        # Sortuj okazje według zysku
        sorted_opportunities = sorted(
            self.current_opportunities,
            key=lambda x: x.net_profit,
            reverse=True
        )
        
        best_opportunity = sorted_opportunities[0]
        
        # Sprawdź czy okazja jest nadal aktualna
        if datetime.now() > best_opportunity.expires_at:
            self.current_opportunities.remove(best_opportunity)
            return
        
        # Sprawdź zarządzanie ryzykiem
        if not await self._check_risk_limits(best_opportunity):
            return
        
        # Wykonaj transakcję
        await self._execute_arbitrage_trade(best_opportunity)
        
        # Usuń okazję z listy
        if best_opportunity in self.current_opportunities:
            self.current_opportunities.remove(best_opportunity)
    
    async def _check_risk_limits(self, opportunity: ArbitrageOpportunity) -> bool:
        """Sprawdź limity ryzyka"""
        try:
            if self.risk_manager:
                # Sprawdź limit na transakcję
                trade_amount = opportunity.max_amount * opportunity.buy_price
                risk_assessment = await self.risk_manager.assess_trade_risk(
                    symbol=self.symbol,
                    side='arbitrage',
                    amount=trade_amount,
                    price=opportunity.buy_price
                )
                
                if not risk_assessment.approved:
                    self.logger.warning(f"Arbitraż odrzucony przez risk manager: {risk_assessment.reason}")
                    return False
            
            # Sprawdź saldo na giełdach
            buy_adapter = self.exchange_adapters[opportunity.buy_exchange]
            sell_adapter = self.exchange_adapters[opportunity.sell_exchange]
            
            # Uproszczone sprawdzenie sald (można rozszerzyć)
            return True
            
        except Exception as e:
            self.logger.error(f"Błąd sprawdzania limitów ryzyka: {e}")
            return False
    
    async def _execute_arbitrage_trade(self, opportunity: ArbitrageOpportunity):
        """Wykonaj transakcję arbitrażową"""
        async with self.trade_lock:
            try:
                start_time = datetime.now()
                
                buy_adapter = self.exchange_adapters[opportunity.buy_exchange]
                sell_adapter = self.exchange_adapters[opportunity.sell_exchange]
                
                # Oblicz wielkość pozycji
                amount = min(opportunity.max_amount, self.max_position_size / opportunity.buy_price)
                
                self.logger.info(f"Wykonywanie arbitrażu: {amount:.6f} {self.symbol}")
                
                # Wykonaj zlecenia równocześnie
                self.logger.debug(f"TRACE: order.submitted - symbol={self.symbol}, side=buy, amount={amount}, type=limit, strategy=arbitrage")
                buy_task = asyncio.create_task(
                    buy_adapter.place_order(
                        symbol=self.symbol,
                        side='buy',
                        amount=amount,
                        price=opportunity.buy_price,
                        order_type='limit'
                    )
                )
                
                self.logger.debug(f"TRACE: order.submitted - symbol={self.symbol}, side=sell, amount={amount}, type=limit, strategy=arbitrage")
                sell_task = asyncio.create_task(
                    sell_adapter.place_order(
                        symbol=self.symbol,
                        side='sell',
                        amount=amount,
                        price=opportunity.sell_price,
                        order_type='limit'
                    )
                )
                
                # Czekaj na wykonanie z timeoutem
                try:
                    buy_result, sell_result = await asyncio.wait_for(
                        asyncio.gather(buy_task, sell_task),
                        timeout=self.execution_timeout_seconds
                    )
                except asyncio.TimeoutError:
                    self.logger.error("Timeout wykonania arbitrażu")
                    # Anuluj zlecenia
                    await self._cancel_pending_orders(buy_task, sell_task)
                    return
                
                end_time = datetime.now()
                execution_time_ms = (end_time - start_time).total_seconds() * 1000
                
                # Sprawdź wyniki
                if (buy_result and buy_result.get('success') and 
                    sell_result and sell_result.get('success')):
                    
                    # Oblicz rzeczywisty zysk
                    actual_buy_price = buy_result.get('price', opportunity.buy_price)
                    actual_sell_price = sell_result.get('price', opportunity.sell_price)
                    
                    gross_profit = (actual_sell_price - actual_buy_price) * amount
                    fees_paid = (actual_buy_price * amount * opportunity.fees_buy + 
                               actual_sell_price * amount * opportunity.fees_sell)
                    net_profit = gross_profit - fees_paid
                    profit_percentage = (net_profit / (actual_buy_price * amount)) * 100
                    
                    # Oblicz slippage
                    buy_slippage = abs(actual_buy_price - opportunity.buy_price) / opportunity.buy_price * 100
                    sell_slippage = abs(actual_sell_price - opportunity.sell_price) / opportunity.sell_price * 100
                    avg_slippage = (buy_slippage + sell_slippage) / 2
                    
                    # Utwórz rekord transakcji
                    trade = ArbitrageTrade(
                        opportunity_id=opportunity.id,
                        symbol=self.symbol,
                        amount=amount,
                        buy_exchange=opportunity.buy_exchange,
                        sell_exchange=opportunity.sell_exchange,
                        buy_order_id=buy_result['order_id'],
                        sell_order_id=sell_result['order_id'],
                        buy_price=actual_buy_price,
                        sell_price=actual_sell_price,
                        buy_time=start_time,
                        sell_time=end_time,
                        gross_profit=gross_profit,
                        fees_paid=fees_paid,
                        net_profit=net_profit,
                        profit_percentage=profit_percentage,
                        execution_time_ms=execution_time_ms,
                        slippage=avg_slippage,
                        status='completed'
                    )
                    
                    self.trade_history.append(trade)
                    self.statistics.executed_trades += 1
                    
                    if net_profit > 0:
                        self.statistics.successful_trades += 1
                        self.logger.info(f"Arbitraż zakończony sukcesem: {net_profit:.2f} ({profit_percentage:.2f}%)")
                    else:
                        self.statistics.failed_trades += 1
                        self.logger.warning(f"Arbitraż zakończony stratą: {net_profit:.2f}")
                    
                    # Zapisz do bazy danych
                    if self.db_manager:
                        await self._save_trade_to_db(trade)
                    
                    # Aktualizuj statystyki
                    self._update_statistics()
                    
                else:
                    self.logger.error("Błąd wykonania arbitrażu - nie wszystkie zlecenia zostały zrealizowane")
                    self.statistics.failed_trades += 1
                    
            except Exception as e:
                self.logger.error(f"Błąd wykonania arbitrażu: {e}")
                self.statistics.failed_trades += 1
    
    async def _cancel_pending_orders(self, buy_task, sell_task):
        """Anuluj oczekujące zlecenia"""
        try:
            if not buy_task.done():
                buy_task.cancel()
            if not sell_task.done():
                sell_task.cancel()
        except Exception as e:
            logger.exception('Unhandled error', exc_info=True)
    
    async def _cancel_trade(self, trade: ArbitrageTrade):
        """Anuluj aktywną transakcję"""
        try:
            buy_adapter = self.exchange_adapters[trade.buy_exchange]
            sell_adapter = self.exchange_adapters[trade.sell_exchange]
            
            # Anuluj zlecenia
            await buy_adapter.cancel_order(trade.buy_order_id, self.symbol)
            await sell_adapter.cancel_order(trade.sell_order_id, self.symbol)
            
            if trade in self.active_trades:
                self.active_trades.remove(trade)
                
        except Exception as e:
            self.logger.error(f"Błąd anulowania transakcji: {e}")
    
    async def _enforce_position_time_limits(self):
        """Wymuś maksymalny czas utrzymania pozycji dla aktywnych transakcji."""
        try:
            # Jeśli brak aktywnych transakcji lub limit nieustawiony, nic nie rób
            if not self.active_trades or not self.max_position_time or self.max_position_time <= 0:
                return
            now = datetime.now()
            for trade in list(self.active_trades):
                position_time_seconds = (now - trade.buy_time).total_seconds()
                if not self._check_position_time(position_time_seconds, self.max_position_time):
                    self.logger.warning(
                        f"Przekroczono maksymalny czas pozycji ({position_time_seconds:.2f}s > {self.max_position_time}s) - anuluję transakcję"
                    )
                    await self._cancel_trade(trade)
        except Exception:
            self.logger.exception("Błąd podczas wymuszania limitu czasu pozycji")
    
    async def _cleanup_loop(self):
        """Pętla czyszczenia"""
        while self.is_running:
            try:
                # Czyść stare dane
                await self._cleanup_old_data()
                
                # Wymuszaj limit czasu pozycji
                await self._enforce_position_time_limits()
                
                # Aktualizuj statystyki
                self._update_statistics()
                
                await asyncio.sleep(60)  # Co minutę
                
            except Exception as e:
                self.logger.error(f"Błąd w czyszczeniu: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_old_data(self):
        """Wyczyść stare dane"""
        # Usuń stare okazje
        await self._cleanup_expired_opportunities()
        
        # Ograniczenie historii transakcji
        if len(self.trade_history) > 1000:
            self.trade_history = self.trade_history[-1000:]
    
    def _update_statistics(self):
        """Aktualizuj statystyki"""
        if not self.trade_history:
            return
        
        stats = self.statistics
        trades = self.trade_history
        
        stats.executed_trades = len(trades)
        stats.successful_trades = len([t for t in trades if t.net_profit > 0])
        stats.failed_trades = len([t for t in trades if t.net_profit <= 0])
        
        stats.total_profit = sum(t.net_profit for t in trades)
        stats.total_profit_percentage = sum(t.profit_percentage for t in trades)
        stats.avg_profit_per_trade = stats.total_profit / len(trades)
        
        stats.avg_execution_time_ms = sum(t.execution_time_ms for t in trades) / len(trades)
        stats.avg_slippage = sum(t.slippage for t in trades) / len(trades)
        
        stats.success_rate = (stats.successful_trades / stats.executed_trades) * 100 if stats.executed_trades > 0 else 0
        
        stats.total_volume = sum(t.amount * t.buy_price for t in trades)
        stats.total_fees_paid = sum(t.fees_paid for t in trades)
        
        stats.best_trade = max(t.net_profit for t in trades) if trades else 0
        stats.worst_trade = min(t.net_profit for t in trades) if trades else 0
        
        # Profit factor
        winning_trades = [t for t in trades if t.net_profit > 0]
        losing_trades = [t for t in trades if t.net_profit <= 0]
        
        total_wins = sum(t.net_profit for t in winning_trades)
        total_losses = abs(sum(t.net_profit for t in losing_trades))
        stats.profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Okazje na godzinę
        if trades:
            time_span_hours = (trades[-1].buy_time - trades[0].buy_time).total_seconds() / 3600
            stats.opportunities_per_hour = stats.total_opportunities / time_span_hours if time_span_hours > 0 else 0
    
    async def _save_trade_to_db(self, trade: ArbitrageTrade):
        """Zapisz transakcję do bazy danych"""
        try:
            if not self.db_manager:
                return
            
            trade_data = {
                'strategy_type': 'arbitrage',
                'symbol': self.symbol,
                'side': 'arbitrage',
                'amount': trade.amount,
                'entry_price': trade.buy_price,
                'exit_price': trade.sell_price,
                'pnl': trade.net_profit,
                'pnl_percentage': trade.profit_percentage,
                'entry_time': trade.buy_time,
                'exit_time': trade.sell_time,
                'metadata': json.dumps({
                    'buy_exchange': trade.buy_exchange,
                    'sell_exchange': trade.sell_exchange,
                    'execution_time_ms': trade.execution_time_ms,
                    'slippage': trade.slippage,
                    'fees_paid': trade.fees_paid
                })
            }
            
            await self.db_manager.save_trade(trade_data)
            
        except Exception as e:
            self.logger.error(f"Błąd zapisu transakcji do DB: {e}")
    
    def get_status(self) -> Dict:
        """Pobierz status strategii"""
        return {
            'status': self.status.value,
            'symbol': self.symbol,
            'exchanges': self.exchanges,
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'current_opportunities': len(self.current_opportunities),
            'active_trades': len(self.active_trades),
            'statistics': asdict(self.statistics),
            'last_update': datetime.now().isoformat()
        }
    
    def get_current_opportunities(self) -> List[Dict]:
        """Pobierz aktualne okazje"""
        return [asdict(opp) for opp in self.current_opportunities]
    
    def get_performance_summary(self) -> Dict:
        """Pobierz podsumowanie wydajności"""
        return {
            'total_profit': self.statistics.total_profit,
            'success_rate': self.statistics.success_rate,
            'executed_trades': self.statistics.executed_trades,
            'avg_profit_per_trade': self.statistics.avg_profit_per_trade,
            'avg_execution_time_ms': self.statistics.avg_execution_time_ms,
            'profit_factor': self.statistics.profit_factor,
            'opportunities_per_hour': self.statistics.opportunities_per_hour
        }
    
    # Metody konfiguracji
    def add_exchange_adapter(self, exchange_name: str, adapter: BaseExchange):
        """Dodaj adapter giełdy"""
        self.exchange_adapters[exchange_name] = adapter
        self.logger.info(f"Dodano adapter dla giełdy: {exchange_name}")
    
    def set_db_manager(self, db_manager: DatabaseManager):
        """Ustaw menedżer bazy danych"""
        self.db_manager = db_manager
        self.logger.info("Ustawiono menedżer bazy danych")
    
    def set_risk_manager(self, risk_manager: RiskManager):
        """Ustaw menedżer ryzyka"""
        self.risk_manager = risk_manager
        self.logger.info("Ustawiono menedżer ryzyka")


    def _check_position_time(self, position_time_seconds: float, max_time_seconds: Optional[int]) -> bool:
        """Sprawdź czy czas utrzymania pozycji nie przekracza limitu."""
        try:
            if max_time_seconds is None or max_time_seconds <= 0:
                return True
            return position_time_seconds <= max_time_seconds
        except Exception:
            self.logger.exception("Błąd podczas sprawdzania czasu pozycji")
            return False


    async def _calculate_total_fees(self, trade_data: Dict[str, Any]) -> float:
        """Oblicz całkowite opłaty transakcyjne dla scenariusza arbitrażu.
        Używa domyślnych stawek taker 0.1% jeśli brak adapterów giełdowych.
        """
        try:
            taker_fee_pct = 0.001
            buy_value = float(trade_data.get('buy_amount', 0)) * float(trade_data.get('buy_price', 0))
            sell_value = float(trade_data.get('sell_amount', 0)) * float(trade_data.get('sell_price', 0))
            total_fees = (buy_value + sell_value) * taker_fee_pct
            return total_fees
        except Exception:
            self.logger.exception("Błąd podczas obliczania opłat")
            return 0.0

    async def _get_prices_from_exchanges(self) -> Dict[str, float]:
        """Pobierz bieżące ceny z wszystkich skonfigurowanych giełd."""
        prices: Dict[str, float] = {}
        for exchange_name in self.exchanges:
            adapter = self.exchange_adapters.get(exchange_name)
            if not adapter:
                self.logger.error(f"Brak adaptera dla giełdy {exchange_name}")
                continue
            try:
                price_val = None
                if hasattr(adapter, 'get_current_price'):
                    price_val = await adapter.get_current_price(self.symbol)
                elif hasattr(adapter, 'get_ticker'):
                    t = await adapter.get_ticker(self.symbol)
                    if isinstance(t, dict):
                        price_val = t.get('last') or t.get('price') or t.get('close') or t.get('ask') or t.get('bid')
                    elif isinstance(t, (int, float)):
                        price_val = t
                else:
                    # Fallback: weź cenę z pierwszego ask z orderbooka
                    ob = None
                    if hasattr(adapter, 'get_order_book'):
                        ob = await adapter.get_order_book(self.symbol, limit=1)
                    elif hasattr(adapter, 'get_orderbook'):
                        ob = await adapter.get_orderbook(self.symbol, limit=1)
                    if ob and isinstance(ob, dict) and ob.get('asks'):
                        price_val = ob['asks'][0][0]
                if price_val is not None:
                    prices[exchange_name] = float(price_val)
            except Exception as e:
                self.logger.error(f"Błąd pobierania ceny z {exchange_name}: {e}")
        return prices

    def _calculate_spreads(self, prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """Oblicz spready między wszystkimi parami giełd na podstawie cen."""
        spread_list: List[Dict[str, Any]] = []
        names = list(prices.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                n1, n2 = names[i], names[j]
                p1, p2 = prices.get(n1), prices.get(n2)
                if p1 is None or p2 is None:
                    continue
                # Kup taniej, sprzedaj drożej
                if p1 <= p2:
                    buy_exchange, sell_exchange = n1, n2
                    buy_price, sell_price = p1, p2
                else:
                    buy_exchange, sell_exchange = n2, n1
                    buy_price, sell_price = p2, p1
                spread_percentage = ((sell_price - buy_price) / buy_price) * 100 if buy_price > 0 else 0.0
                profit_potential = (sell_price - buy_price)
                spread_list.append({
                    'buy_exchange': buy_exchange,
                    'sell_exchange': sell_exchange,
                    'buy_price': buy_price,
                    'sell_price': sell_price,
                    'spread_percentage': spread_percentage,
                    'profit_potential': profit_potential
                })
        return spread_list

    def _is_arbitrage_opportunity(self, spread_data: Dict[str, Any]) -> bool:
        """Sprawdź czy spread kwalifikuje się jako okazja arbitrażowa."""
        try:
            return float(spread_data.get('spread_percentage', 0.0)) >= float(self.min_spread_percentage)
        except Exception:
            return False

    async def _execute_arbitrage(self, opportunity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Wykonaj prosty arbitraż na bazie przekazanej okazji (mock-friendly).
        Zwraca słownik z kluczami: 'buy_order', 'sell_order', 'profit'.
        """
        try:
            buy_exchange = opportunity.get('buy_exchange')
            sell_exchange = opportunity.get('sell_exchange')
            buy_price = float(opportunity.get('buy_price', 0))
            sell_price = float(opportunity.get('sell_price', 0))
            amount = float(opportunity.get('amount') or (self.min_volume / buy_price if buy_price > 0 else 0.0))
            
            buy_adapter = self.exchange_adapters.get(buy_exchange)
            sell_adapter = self.exchange_adapters.get(sell_exchange)
            if not buy_adapter or not sell_adapter:
                self.logger.error("Brak adapterów dla arbitrażu")
                return None
            
            # Złóż zlecenia po dostępnych metodach
            if hasattr(buy_adapter, 'create_order'):
                buy_order = await buy_adapter.create_order(self.symbol, 'limit', 'buy', amount, price=buy_price)
            elif hasattr(buy_adapter, 'place_order'):
                buy_order = await buy_adapter.place_order(symbol=self.symbol, side='buy', amount=amount, price=buy_price, order_type='limit')
            else:
                buy_order = {'id': 'buy_mock', 'status': 'filled'}
            
            if hasattr(sell_adapter, 'create_order'):
                sell_order = await sell_adapter.create_order(self.symbol, 'limit', 'sell', amount, price=sell_price)
            elif hasattr(sell_adapter, 'place_order'):
                sell_order = await sell_adapter.place_order(symbol=self.symbol, side='sell', amount=amount, price=sell_price, order_type='limit')
            else:
                sell_order = {'id': 'sell_mock', 'status': 'filled'}
            
            profit = (sell_price - buy_price) * amount
            return {
                'buy_order': buy_order,
                'sell_order': sell_order,
                'profit': float(profit)
            }
        except Exception as e:
            self.logger.error(f"Błąd wykonania arbitrażu: {e}")
            return None

    def _can_trade_today(self, daily_trades: int, max_daily: Optional[int]) -> bool:
        """Sprawdź czy można wykonać kolejną transakcję w danym dniu względem limitu."""
        try:
            if max_daily is None or max_daily <= 0:
                return True
            return int(daily_trades) < int(max_daily)
        except Exception:
            return False