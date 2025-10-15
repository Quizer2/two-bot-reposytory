import copy
from types import SimpleNamespace

import pytest

from app.trading_mode_manager import TradingModeManager, TradingMode
from utils.config_manager import ConfigManager


class DummyAPIConfigManager:
    def __init__(self, enabled=None, valid=None):
        self._enabled = list(enabled or [])
        self._valid = set(valid or [])
        self.loaded = False

    def load_api_config(self):
        self.loaded = True
        return True

    def get_enabled_exchanges(self):
        return list(self._enabled)

    def validate_exchange_config(self, exchange: str) -> bool:
        return exchange in self._valid


class FailingDataManager:
    def __init__(self):
        self.called = False

    async def get_real_balance(self):  # pragma: no cover - should not be invoked
        self.called = True
        raise AssertionError("Live balance should not be requested without credentials")


class StubLiveDataManager:
    async def get_real_balance(self):
        return {
            'USDT': {
                'free': 100.0,
                'used': 0.0,
                'total': 100.0,
            }
        }

    async def get_real_price(self, symbol: str):
        return 1.0

    async def get_portfolio_widget_data(self):
        return {
            'summary': {
                'total_value': 100.0,
                'unrealized_pnl': 5.0,
            }
        }

    async def test_connections(self):
        return True


class SnapshotDataManager:
    def __init__(self):
        self.snapshot = {
            'summary': {
                'total_value': 1234.56,
                'daily_change': 12.34,
                'daily_change_percent': 1.0,
                'available_balance': 200.0,
                'invested_amount': 1034.56,
                'total_profit_loss': 50.0,
                'total_profit_loss_percent': 4.2,
                'positions': [
                    {
                        'symbol': 'BTC',
                        'amount': 0.5,
                        'value': 800.0,
                        'average_price': 30000.0,
                        'current_price': 32000.0,
                        'profit_loss': 20.0,
                        'profit_loss_percent': 2.5,
                    }
                ],
            },
            'balances': [
                {
                    'symbol': 'BTC',
                    'balance': 0.5,
                    'free': 0.4,
                    'locked': 0.1,
                    'usd_value': 800.0,
                },
            ],
        }
        self.trades = [
            {'id': 't1', 'symbol': 'BTC/USDT', 'amount': 0.1, 'price': 30000.0},
        ]
        self.snapshot_calls = 0
        self.trade_calls = 0

    async def get_portfolio_widget_data(self):
        self.snapshot_calls += 1
        return copy.deepcopy(self.snapshot)

    async def get_recent_trades(self, limit=100):
        self.trade_calls += 1
        return list(self.trades)


@pytest.fixture()
def config_manager(tmp_path):
    cfg_dir = tmp_path / "config"
    manager = ConfigManager(str(cfg_dir))
    manager.load_config("app")
    return manager


@pytest.mark.asyncio
async def test_live_mode_blocked_without_keys(config_manager):
    config_manager.set_setting('app', 'trading.default_mode', 'live')
    api_manager = DummyAPIConfigManager()

    trading_manager = TradingModeManager(
        config_manager,
        data_manager=SimpleNamespace(),
        api_config_manager=api_manager,
    )

    assert not trading_manager.live_trading_available()

    switched = await trading_manager.switch_mode(TradingMode.LIVE)

    assert switched is False
    assert trading_manager.get_current_mode() == TradingMode.PAPER
    reason = trading_manager.get_live_trading_block_reason()
    assert reason
    assert "klucz" in reason.lower()


@pytest.mark.asyncio
async def test_live_balances_not_requested_without_credentials(config_manager):
    api_manager = DummyAPIConfigManager()
    data_manager = FailingDataManager()

    trading_manager = TradingModeManager(
        config_manager,
        data_manager=data_manager,
        api_config_manager=api_manager,
    )

    trading_manager.refresh_live_trading_status()
    trading_manager.current_mode = TradingMode.LIVE

    balances = await trading_manager.get_current_balances()

    assert balances == {}
    assert data_manager.called is False


@pytest.mark.asyncio
async def test_live_mode_enables_after_credentials(config_manager):
    api_manager = DummyAPIConfigManager(enabled=['binance'], valid={'binance'})
    data_manager = StubLiveDataManager()

    trading_manager = TradingModeManager(
        config_manager,
        data_manager=data_manager,
        api_config_manager=api_manager,
    )

    assert trading_manager.refresh_live_trading_status() is True

    switched = await trading_manager.switch_mode(TradingMode.LIVE)
    assert switched is True
    assert trading_manager.get_current_mode() == TradingMode.LIVE

    balances = await trading_manager.get_current_balances()
    assert 'USDT' in balances
    assert balances['USDT']['balance'] == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_zeroed_live_view_preserves_snapshot(config_manager):
    api_manager = DummyAPIConfigManager()
    data_manager = SnapshotDataManager()

    trading_manager = TradingModeManager(
        config_manager,
        data_manager=data_manager,
        api_config_manager=api_manager,
    )

    zero_view = await trading_manager.get_zeroed_live_view()

    assert zero_view['meta']['source'] == 'live_disabled'
    assert data_manager.snapshot_calls == 1
    assert data_manager.trade_calls == 1

    balances = zero_view['balances']
    assert balances
    for entry in balances:
        assert entry['balance'] == 0.0
        assert entry['usd_value'] == 0.0
        assert entry.get('meta', {}).get('original_total', 0.0) > 0.0

    # Historia w widoku jest wyzerowana, ale zachowujemy oryginalne transakcje w metadanych
    assert zero_view['transactions'] == []
    assert zero_view['original_transactions'] == data_manager.trades

    # Oryginalne dane w migawce nie zostały zmodyfikowane
    assert data_manager.snapshot['summary']['total_value'] == pytest.approx(1234.56)
    assert data_manager.snapshot['balances'][0]['balance'] == pytest.approx(0.5)
