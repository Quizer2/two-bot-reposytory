"""
Silniki botów handlowych

Zawiera implementację różnych strategii handlowych
i silników do automatycznego handlu na giełdach.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)

try:
    import ccxt
    import ccxt.async_support as ccxt_async
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    logger.info("CCXT not available - trading engines will use simulation mode")


class OrderType(Enum):
    """Typy zleceń"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class OrderSide(Enum):
    """Strony zlecenia"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Statusy zleceń"""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """Klasa reprezentująca zlecenie"""
    id: str
    symbol: str
    side: OrderSide
    type: OrderType
    amount: float
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled: float = 0.0
    remaining: float = 0.0
    timestamp: datetime = None
    exchange_id: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.remaining == 0.0:
            self.remaining = self.amount


@dataclass
class Position:
    """Klasa reprezentująca pozycję"""
    symbol: str
    side: OrderSide
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class Balance:
    """Klasa reprezentująca saldo"""
    currency: str
    free: float
    used: float
    total: float


class ExchangeConnector:
    """Łącznik z giełdą"""
    
    def __init__(self, exchange_name: str, api_key: str = "", secret: str = "", 
                 sandbox: bool = True, passphrase: str = ""):
        self.exchange_name = exchange_name
        self.api_key = api_key
        self.secret = secret
        self.sandbox = sandbox
        self.passphrase = passphrase
        
        self.exchange = None
        self.async_exchange = None
        
        if CCXT_AVAILABLE:
            self.setup_exchange()
        else:
            logger.info(f"CCXT not available - {exchange_name} connector in simulation mode")
    
    def setup_exchange(self):
        """Konfiguruje połączenie z giełdą"""
        try:
            exchange_class = getattr(ccxt, self.exchange_name)
            async_exchange_class = getattr(ccxt_async, self.exchange_name)
            
            config = {
                'apiKey': self.api_key,
                'secret': self.secret,
                'sandbox': self.sandbox,
                'enableRateLimit': True,
            }
            
            if self.passphrase:
                config['passphrase'] = self.passphrase
            
            self.exchange = exchange_class(config)
            self.async_exchange = async_exchange_class(config)
            logger.info(f"✅ Połączono z giełdą {self.exchange_name}")
            
        except Exception as e:
            logger.info(f"❌ Błąd połączenia z giełdą {self.exchange_name}: {e}")
            self.exchange = None
            self.async_exchange = None
    
    async def get_balance(self) -> Dict[str, Balance]:
        """Pobiera saldo konta"""
        if not self.async_exchange:
            # Symulacja salda
            return {
                'USDT': Balance('USDT', 1000.0, 0.0, 1000.0),
                'BTC': Balance('BTC', 0.0, 0.0, 0.0),
                'ETH': Balance('ETH', 0.0, 0.0, 0.0)
            }
        
        try:
            balance_data = await self.async_exchange.fetch_balance()
            balances = {}
            
            for currency, data in balance_data.items():
                if isinstance(data, dict) and 'free' in data:
                    balances[currency] = Balance(
                        currency=currency,
                        free=data['free'],
                        used=data['used'],
                        total=data['total']
                    )
            
            return balances
            
        except Exception as e:
            logger.info(f"Błąd pobierania salda: {e}")
            return {}
    
    async def get_ticker(self, symbol: str) -> Dict:
        """Pobiera ticker dla symbolu"""
        if not self.async_exchange:
            # Symulacja tickera
            return {
                'symbol': symbol,
                'last': 45000.0,
                'bid': 44995.0,
                'ask': 45005.0,
                'volume': 1000.0
            }
        
        try:
            return await self.async_exchange.fetch_ticker(symbol)
        except Exception as e:
            logger.info(f"Błąd pobierania tickera {symbol}: {e}")
            return {}
    
    async def place_order(self, order: Order) -> Order:
        """Składa zlecenie na giełdzie"""
        logger.info(f"TRACE: order.submitted - symbol={order.symbol}, side={order.side.value}, amount={order.amount}, type={order.type.value}")
        
        if not self.async_exchange:
            # Symulacja zlecenia
            order.id = f"sim_{int(time.time())}"
            order.status = OrderStatus.FILLED
            order.filled = order.amount
            order.remaining = 0.0
            logger.info(f"🔄 Symulacja zlecenia: {order.side.value} {order.amount} {order.symbol} @ {order.price}")
            return order
        
        try:
            order_params = {
                'symbol': order.symbol,
                'type': order.type.value,
                'side': order.side.value,
                'amount': order.amount,
            }

            if order.price:
                order_params['price'] = order.price

            result = await self.async_exchange.create_order(**order_params)

            order.exchange_id = result['id']
            order.status = OrderStatus.OPEN
            logger.info(f"✅ Zlecenie złożone: {result['id']}")
            return order

        except Exception as e:
            logger.info(f"❌ Błąd składania zlecenia: {e}")
            order.status = OrderStatus.REJECTED
            return order
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Anuluje zlecenie"""
        if not self.async_exchange:
            logger.info(f"🔄 Symulacja anulowania zlecenia: {order_id}")
            return True
        
        try:
            await self.async_exchange.cancel_order(order_id, symbol)
            logger.info(f"✅ Zlecenie anulowane: {order_id}")
            return True
        except Exception as e:
            logger.info(f"❌ Błąd anulowania zlecenia: {e}")
            return False
    
    async def get_order_status(self, order_id: str, symbol: str) -> Dict:
        """Sprawdza status zlecenia"""
        if not self.async_exchange:
            return {'status': 'filled', 'filled': 1.0}
        
        try:
            return await self.async_exchange.fetch_order(order_id, symbol)
        except Exception as e:
            logger.info(f"Błąd sprawdzania statusu zlecenia: {e}")
            return {}


class TradingStrategy(ABC):
    """Abstrakcyjna klasa strategii handlowej"""
    
    def __init__(self, name: str):
        self.name = name
        self.parameters = {}
        self.positions = []
        self.orders = []
        self.pnl = 0.0
        
    @abstractmethod
    async def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analizuje dane i zwraca sygnały"""
        pass
    
    @abstractmethod
    async def generate_signals(self, analysis: Dict[str, Any]) -> List[Order]:
        """Generuje sygnały handlowe"""
        pass


class MovingAverageCrossStrategy(TradingStrategy):
    """Strategia przecięcia średnich kroczących"""
    
    def __init__(self, fast_period: int = 10, slow_period: int = 20, symbol: str = "BTC/USDT"):
        super().__init__("MA Cross")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.symbol = symbol
        self.position = None
        
    async def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analizuje dane i oblicza średnie kroczące"""
        if len(data) < self.slow_period:
            return {'signal': 'hold', 'reason': 'insufficient_data'}
        
        # Oblicz średnie kroczące
        fast_ma = data['close'].rolling(window=self.fast_period).mean()
        slow_ma = data['close'].rolling(window=self.slow_period).mean()
        
        current_fast = fast_ma.iloc[-1]
        current_slow = slow_ma.iloc[-1]
        prev_fast = fast_ma.iloc[-2]
        prev_slow = slow_ma.iloc[-2]
        
        # Sprawdź przecięcie
        signal = 'hold'
        if prev_fast <= prev_slow and current_fast > current_slow:
            signal = 'buy'
        elif prev_fast >= prev_slow and current_fast < current_slow:
            signal = 'sell'
        
        return {
            'signal': signal,
            'fast_ma': current_fast,
            'slow_ma': current_slow,
            'current_price': data['close'].iloc[-1],
            'reason': f'MA({self.fast_period}) vs MA({self.slow_period})'
        }
    
    async def generate_signals(self, analysis: Dict[str, Any]) -> List[Order]:
        """Generuje zlecenia na podstawie analizy"""
        orders = []
        signal = analysis['signal']
        current_price = analysis['current_price']
        
        if signal == 'buy' and not self.position:
            # Otwórz pozycję długą
            order = Order(
                id=f"ma_buy_{int(time.time())}",
                symbol=self.symbol,
                side=OrderSide.BUY,
                type=OrderType.MARKET,
                amount=0.01,  # 0.01 BTC
                price=current_price
            )
            orders.append(order)
            
        elif signal == 'sell' and self.position:
            # Zamknij pozycję
            order = Order(
                id=f"ma_sell_{int(time.time())}",
                symbol=self.symbol,
                side=OrderSide.SELL,
                type=OrderType.MARKET,
                amount=0.01,
                price=current_price
            )
            orders.append(order)
        
        return orders


class RSIStrategy(TradingStrategy):
    """Strategia oparta na RSI"""
    
    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70, 
                 symbol: str = "BTC/USDT"):
        super().__init__("RSI Strategy")
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.symbol = symbol
        self.position = None
    
    def calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """Oblicza RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    async def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analizuje RSI"""
        if len(data) < self.period + 1:
            return {'signal': 'hold', 'reason': 'insufficient_data'}
        
        rsi = self.calculate_rsi(data['close'])
        current_rsi = rsi.iloc[-1]
        current_price = data['close'].iloc[-1]
        
        signal = 'hold'
        if current_rsi < self.oversold:
            signal = 'buy'
        elif current_rsi > self.overbought:
            signal = 'sell'
        
        return {
            'signal': signal,
            'rsi': current_rsi,
            'current_price': current_price,
            'reason': f'RSI({self.period}): {current_rsi:.2f}'
        }
    
    async def generate_signals(self, analysis: Dict[str, Any]) -> List[Order]:
        """Generuje zlecenia na podstawie RSI"""
        orders = []
        signal = analysis['signal']
        current_price = analysis['current_price']
        
        if signal == 'buy' and not self.position:
            order = Order(
                id=f"rsi_buy_{int(time.time())}",
                symbol=self.symbol,
                side=OrderSide.BUY,
                type=OrderType.MARKET,
                amount=0.01,
                price=current_price
            )
            orders.append(order)
            
        elif signal == 'sell' and self.position:
            order = Order(
                id=f"rsi_sell_{int(time.time())}",
                symbol=self.symbol,
                side=OrderSide.SELL,
                type=OrderType.MARKET,
                amount=0.01,
                price=current_price
            )
            orders.append(order)
        
        return orders


class TradingBot:
    """Główny bot handlowy"""
    
    def __init__(self, name: str, exchange_connector: ExchangeConnector, 
                 strategy: TradingStrategy, symbol: str = "BTC/USDT"):
        self.name = name
        self.exchange = exchange_connector
        self.strategy = strategy
        self.symbol = symbol
        self.is_running = False
        self.positions = []
        self.orders = []
        self.balance = {}
        self.pnl = 0.0
        
        # Konfiguracja
        self.check_interval = 60  # sekundy
        self.max_position_size = 0.1  # maksymalny rozmiar pozycji
        self.stop_loss_pct = 0.02  # 2% stop loss
        self.take_profit_pct = 0.04  # 4% take profit
        
        # Logging
        self.logger = logging.getLogger(f"TradingBot_{name}")
        self.logger.setLevel(logging.INFO)
    
    async def start(self):
        """Uruchamia bota"""
        self.is_running = True
        self.logger.info(f"🚀 Uruchamianie bota {self.name}")
        
        while self.is_running:
            try:
                await self.trading_cycle()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                self.logger.error(f"Błąd w cyklu handlowym: {e}")
                await asyncio.sleep(5)
    
    async def stop(self):
        """Zatrzymuje bota"""
        self.is_running = False
        self.logger.info(f"🛑 Zatrzymywanie bota {self.name}")
    
    async def trading_cycle(self):
        """Jeden cykl handlowy"""
        # 1. Pobierz dane rynkowe
        market_data = await self.get_market_data()
        if market_data.empty:
            return
        
        # 2. Aktualizuj saldo
        await self.update_balance()
        
        # 3. Sprawdź otwarte zlecenia
        await self.check_orders()
        
        # 4. Analizuj rynek
        analysis = await self.strategy.analyze(market_data)
        
        # 5. Generuj sygnały
        signals = await self.strategy.generate_signals(analysis)
        
        # 6. Wykonaj zlecenia
        for signal in signals:
            await self.execute_order(signal)
        
        # 7. Zarządzaj ryzykiem
        await self.manage_risk()
        
        # 8. Loguj status
        await self.log_status(analysis)
    async def get_market_data(self) -> pd.DataFrame:
        """Pobiera dane rynkowe"""
        try:
            if self.exchange.exchange:
                ohlcv = self.exchange.exchange.fetch_ohlcv(self.symbol, '1m', limit=100)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                return df
            else:
                # Symulacja danych
                dates = pd.date_range(
                    start=datetime.now() - timedelta(hours=2),
                    end=datetime.now(),
                    freq='1min',
                )[:100]

                base_price = 45000.0
                prices: List[float] = []
                current_price = base_price

                for _ in range(len(dates)):
                    change = np.random.normal(0, 0.001)
                    current_price *= 1 + change
                    prices.append(current_price)

                data: List[List[float]] = []
                for price in prices:
                    open_price = price
                    high_price = price * (1 + abs(np.random.normal(0, 0.0005)))
                    low_price = price * (1 - abs(np.random.normal(0, 0.0005)))
                    close_price = price * (1 + np.random.normal(0, 0.0002))
                    volume = float(np.random.uniform(10, 100))

                    data.append([open_price, high_price, low_price, close_price, volume])

                df = pd.DataFrame(data, columns=['open', 'high', 'low', 'close', 'volume'], index=dates)
                return df

        except Exception as e:
            self.logger.error(f"Błąd pobierania danych rynkowych: {e}")
            return pd.DataFrame()
    
    async def update_balance(self):
        """Aktualizuje saldo"""
        self.balance = await self.exchange.get_balance()

    async def check_orders(self):
        """Sprawdza status otwartych zleceń"""
        for order in list(self.orders):
            if order.status == OrderStatus.OPEN:
                status = await self.exchange.get_order_status(order.exchange_id, order.symbol)
                if status.get('status') == 'filled':
                    order.status = OrderStatus.FILLED
                    order.filled = order.amount
                    order.remaining = 0.0
                    self.logger.info(f"✅ Zlecenie wypełnione: {order.id}")
    
    async def execute_order(self, order: Order):
        """Wykonuje zlecenie"""
        # Sprawdź saldo
        if not await self.check_balance_for_order(order):
            self.logger.warning(f"Niewystarczające saldo dla zlecenia: {order.id}")
            return

        # Składaj zlecenie
        executed_order = await self.exchange.place_order(order)
        self.orders.append(executed_order)
        
        self.logger.info(f"📋 Zlecenie złożone: {executed_order.side.value} {executed_order.amount} {executed_order.symbol}")
    
    async def check_balance_for_order(self, order: Order) -> bool:
        """Sprawdza czy saldo wystarczy na zlecenie"""
        if order.side == OrderSide.BUY:
            # Sprawdź USDT
            usdt_balance = self.balance.get('USDT')
            if usdt_balance and usdt_balance.free >= order.amount * order.price:
                return True
        else:
            # Sprawdź bazową walutę
            base_currency = order.symbol.split('/')[0]
            base_balance = self.balance.get(base_currency)
            if base_balance and base_balance.free >= order.amount:
                return True
        
        return False
    
    async def manage_risk(self):
        """Zarządzanie ryzykiem"""
        # Implementacja stop loss i take profit
        current_ticker = await self.exchange.get_ticker(self.symbol)
        current_price = current_ticker.get('last', 0)
        
        for position in self.positions:
            if position.side == OrderSide.BUY:
                # Long position
                pnl_pct = (current_price - position.entry_price) / position.entry_price
                
                if pnl_pct <= -self.stop_loss_pct:
                    # Stop loss
                    await self.close_position(position, "Stop Loss")
                elif pnl_pct >= self.take_profit_pct:
                    # Take profit
                    await self.close_position(position, "Take Profit")
    
    async def close_position(self, position: Position, reason: str):
        """Zamyka pozycję"""
        order = Order(
            id=f"close_{int(time.time())}",
            symbol=position.symbol,
            side=OrderSide.SELL if position.side == OrderSide.BUY else OrderSide.BUY,
            type=OrderType.MARKET,
            amount=position.size
        )
        
        await self.execute_order(order)
        self.positions.remove(position)

        self.logger.info(f"🔒 Pozycja zamknięta: {reason}")

    async def log_status(self, analysis: Dict[str, Any]):
        """Loguje status bota"""
        signal = analysis.get('signal', 'hold')
        current_price = analysis.get('current_price', 0)
        
        self.logger.info(f"📊 Status: {signal} | Cena: {current_price:.2f} | Pozycje: {len(self.positions)} | PnL: {self.pnl:.2f}")


class BotManager:
    """Menedżer botów handlowych"""
    
    def __init__(self):
        self.bots = {}
        self.is_running = False

    def add_bot(self, bot: TradingBot):
        """Dodaje bota do managera"""
        self.bots[bot.name] = bot
        logger.info(f"✅ Dodano bota: {bot.name}")
    
    def remove_bot(self, bot_name: str):
        """Usuwa bota z managera"""
        if bot_name in self.bots:
            del self.bots[bot_name]
            logger.info(f"🗑️ Usunięto bota: {bot_name}")
    
    async def start_all_bots(self):
        """Uruchamia wszystkie boty"""
        self.is_running = True
        tasks = []
        
        for bot in self.bots.values():
            task = asyncio.create_task(bot.start())
            tasks.append(task)
        
        logger.info(f"🚀 Uruchomiono {len(tasks)} botów")
        await asyncio.gather(*tasks)
    
    async def stop_all_bots(self):
        """Zatrzymuje wszystkie boty"""
        self.is_running = False
        
        for bot in self.bots.values():
            await bot.stop()
        
        logger.info("🛑 Wszystkie boty zatrzymane")
    
    def get_bots_status(self) -> Dict[str, Dict]:
        """Zwraca status wszystkich botów"""
        status = {}
        
        for name, bot in self.bots.items():
            status[name] = {
                'running': bot.is_running,
                'symbol': bot.symbol,
                'strategy': bot.strategy.name,
                'positions': len(bot.positions),
                'orders': len(bot.orders),
                'pnl': bot.pnl
            }
        
        return status


# Przykład użycia
async def main():
    """Przykład uruchomienia botów"""
    
    # Konfiguracja giełdy (sandbox)
    exchange = ExchangeConnector(
        exchange_name="binance",
        api_key="your_api_key",
        secret="your_secret",
        sandbox=True
    )
    
    # Strategia MA Cross
    ma_strategy = MovingAverageCrossStrategy(fast_period=10, slow_period=20)
    ma_bot = TradingBot("MA_Bot", exchange, ma_strategy)
    
    # Strategia RSI
    rsi_strategy = RSIStrategy(period=14, oversold=30, overbought=70)
    rsi_bot = TradingBot("RSI_Bot", exchange, rsi_strategy)
    
    # Menedżer botów
    manager = BotManager()
    manager.add_bot(ma_bot)
    manager.add_bot(rsi_bot)
    
    # Uruchom boty
    try:
        await manager.start_all_bots()
    except KeyboardInterrupt:
        logger.info("\n🛑 Zatrzymywanie botów...")
        await manager.stop_all_bots()


if __name__ == "__main__":
    asyncio.run(main())
