import asyncio
from datetime import datetime
from typing import Any, Dict, List

import pytest

from core.updated_bot_manager import UpdatedBotManager, BotType


class DummyStatus:
    def __init__(self, value: str):
        self.value = value


class DummyOrderResponse:
    def __init__(self, price: float):
        self.status = DummyStatus('FILLED')
        self.average_price = price


class DummyPriceData:
    def __init__(self, symbol: str, price: float):
        self.symbol = symbol
        self.price = price
        self.timestamp = datetime.utcnow()


class DummyRiskManager:
    async def validate_bot_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return {'valid': True}

    async def validate_order(self, order_request, bot_id: str) -> bool:
        return True


class DummyDataManager:
    def __init__(self, price: float = 100.0):
        self._price = price
        self.status_updates: List[Dict[str, Any]] = []
        self.config_manager = None
        self.database_manager = None
        self.trading_engine = None
        self.market_data_manager = None

    async def update_bot_status(self, bot_id: str, status: str, is_active: bool) -> None:
        self.status_updates.append({'bot_id': bot_id, 'status': status, 'active': is_active})

    async def execute_trade_order(self, bot_id: str, order_request) -> DummyOrderResponse:
        price = order_request.price or self._price
        return DummyOrderResponse(price)

    async def get_market_data_for_bot(self, bot_id: str, symbol: str) -> DummyPriceData:
        return DummyPriceData(symbol, self._price)


@pytest.mark.asyncio
async def test_updated_bot_manager_handles_multiple_strategies(monkeypatch):
    monkeypatch.setattr('core.updated_bot_manager.AI_COMPONENTS_AVAILABLE', False)

    data_manager = DummyDataManager()
    risk_manager = DummyRiskManager()

    manager = UpdatedBotManager(
        risk_manager=risk_manager,
        data_manager=data_manager,
        db_manager=None,
        notification_manager=None,
    )

    ai_bot_one = await manager.create_bot(
        name='AI Bot 1',
        bot_type=BotType.AI,
        symbol='BTCUSDT',
        parameters={'budget': 1000},
        risk_settings={},
    )

    grid_bot = await manager.create_bot(
        name='Grid Bot',
        bot_type=BotType.GRID,
        symbol='ETHUSDT',
        parameters={'grid_size': 3, 'grid_spacing': 0.01},
        risk_settings={},
    )

    arbitrage_bot = await manager.create_bot(
        name='Arb Bot',
        bot_type=BotType.ARBITRAGE,
        symbol='BTCUSDT',
        parameters={'exchanges': ['binance', 'kraken'], 'min_spread_percentage': 0.5},
        risk_settings={},
    )

    ai_bot_two = await manager.create_bot(
        name='AI Bot 2',
        bot_type=BotType.AI,
        symbol='ETHUSDT',
        parameters={'budget': 2000},
        risk_settings={},
    )

    momentum_bot = await manager.create_bot(
        name='Momentum Bot',
        bot_type=BotType.MOMENTUM,
        symbol='BTC/EUR',
        parameters={'short_window': 5, 'long_window': 20, 'trade_amount': 150.0},
        risk_settings={},
    )

    mean_reversion_bot = await manager.create_bot(
        name='Reversion Bot',
        bot_type=BotType.MEAN_REVERSION,
        symbol='ETH/EUR',
        parameters={'lookback_window': 18, 'deviation_threshold': 0.7, 'trade_amount': 120.0},
        risk_settings={},
    )

    breakout_bot = await manager.create_bot(
        name='Breakout Bot',
        bot_type=BotType.BREAKOUT,
        symbol='ADA/USDT',
        parameters={'lookback_window': 25, 'breakout_buffer': 0.6, 'trailing_stop_percentage': 0.9},
        risk_settings={},
    )

    assert await manager.start_bot(ai_bot_one)
    assert await manager.start_bot(grid_bot)
    assert await manager.start_bot(arbitrage_bot)
    assert await manager.start_bot(ai_bot_two)
    assert await manager.start_bot(momentum_bot)
    assert await manager.start_bot(mean_reversion_bot)
    assert await manager.start_bot(breakout_bot)

    running_ids = set(manager.get_running_bot_ids())
    expected_ids = {
        ai_bot_one,
        grid_bot,
        arbitrage_bot,
        ai_bot_two,
        momentum_bot,
        mean_reversion_bot,
        breakout_bot,
    }
    assert expected_ids.issubset(running_ids)

    # Pozwól pętlom strategii wykonać co najmniej jedną iterację
    await asyncio.sleep(0.05)

    for bot_id in expected_ids:
        assert await manager.stop_bot(bot_id)

    await manager.shutdown()

    running_after = set(manager.get_running_bot_ids())
    assert running_after == set()

    status_types = {entry['status'] for entry in data_manager.status_updates}
    assert {'running', 'stopped'}.issubset(status_types)


@pytest.mark.asyncio
async def test_updated_bot_manager_strategy_pair_matrix(monkeypatch):
    """Weryfikuje możliwość równoległej obsługi wszystkich strategii i wielu par."""

    monkeypatch.setattr('core.updated_bot_manager.AI_COMPONENTS_AVAILABLE', False)
    monkeypatch.setattr('core.updated_bot_manager.ARBITRAGE_COMPONENTS_AVAILABLE', False)
    monkeypatch.setattr('core.updated_bot_manager.AdvancedArbitrageStrategy', None)
    monkeypatch.setattr('core.updated_bot_manager.SWING_COMPONENTS_AVAILABLE', False)
    monkeypatch.setattr('core.updated_bot_manager.AdvancedSwingStrategy', None)

    data_manager = DummyDataManager(price=250.0)
    risk_manager = DummyRiskManager()

    manager = UpdatedBotManager(
        risk_manager=risk_manager,
        data_manager=data_manager,
        db_manager=None,
        notification_manager=None,
    )

    supported_pairs = [
        'BTC/USDT',
        'ETH/EUR',
        'SOL/USDT',
        'BTC/GBP',
        'ADA/EUR',
        'AVAX/USDT',
        'MATIC/USDT',
    ]

    parameter_matrix = {
        BotType.DCA: {'buy_amount': 180.0, 'interval_minutes': 15},
        BotType.GRID: {'grid_size': 5, 'grid_spacing': 0.02},
        BotType.SCALPING: {'profit_target': 0.006, 'stop_loss': 0.003},
        BotType.AI: {'budget': 1200.0},
        BotType.ARBITRAGE: {
            'exchanges': ['binance', 'kraken', 'coinbase'],
            'min_spread_percentage': 0.4,
            'trade_amount': 150.0,
        },
        BotType.SWING: {
            'amount': 220.0,
            'short_window': 6,
            'long_window': 18,
            'trend_buffer': 0.002,
        },
        BotType.MOMENTUM: {
            'short_window': 7,
            'long_window': 21,
            'momentum_threshold': 0.3,
            'trade_amount': 200.0,
            'cooldown_seconds': 5,
        },
        BotType.MEAN_REVERSION: {
            'lookback_window': 24,
            'deviation_threshold': 0.9,
            'trade_amount': 180.0,
            'position_scaling': True,
        },
        BotType.BREAKOUT: {
            'lookback_window': 28,
            'breakout_buffer': 0.5,
            'trailing_stop_percentage': 0.8,
            'trade_amount': 210.0,
            'confirmation_candles': 2,
        },
    }

    created_ids = []
    iterable_bot_types = [bot_type for bot_type in BotType if bot_type is not BotType.CUSTOM]

    for index, bot_type in enumerate(iterable_bot_types):
        symbol = supported_pairs[index % len(supported_pairs)]
        parameters = parameter_matrix[bot_type]
        bot_id = await manager.create_bot(
            name=f"{bot_type.value.title()} Bot #{index+1}",
            bot_type=bot_type,
            symbol=symbol,
            parameters=parameters,
            risk_settings={'max_drawdown': 10.0, 'max_position_size': 500.0},
        )
        created_ids.append(bot_id)

    for bot_id in created_ids:
        assert await manager.start_bot(bot_id)

    await asyncio.sleep(0.1)

    running_ids = set(manager.get_running_bot_ids())
    assert set(created_ids) == running_ids

    for bot_id in reversed(created_ids):
        assert await manager.stop_bot(bot_id)

    await manager.shutdown()

    status_by_bot = {}
    for entry in data_manager.status_updates:
        status_by_bot.setdefault(entry['bot_id'], set()).add(entry['status'])

    for bot_id in created_ids:
        assert {'starting', 'running', 'stopping', 'stopped'}.issubset(status_by_bot.get(bot_id, set()))

    assert manager.get_running_bot_ids() == []
