import json
from pathlib import Path

import pytest

from app.exchange import adapter_factory
from app.exchange.base_simulated_adapter import SimulatedExchangeAdapter
from app.strategy.ai_trading_bot import AITradingBot
from core import market_data_manager


def test_paper_mode_returns_simulated_adapter(monkeypatch):
    class DummyLiveAdapter:
        def __init__(self, *args, **kwargs):
            pass

        @staticmethod
        def is_supported():
            return True

    monkeypatch.setattr(adapter_factory, "LiveCCXTAdapter", DummyLiveAdapter)

    adapter = adapter_factory.create_exchange_adapter("binance", mode="paper", intent="market_data")

    assert isinstance(adapter, SimulatedExchangeAdapter)


def test_market_data_manager_disables_live_when_paper(monkeypatch):
    class DummyConfig:
        def get_setting(self, config_type, path, default=None):
            if (config_type, path) == ("app", "app.offline_mode"):
                return False
            if (config_type, path) == ("app", "trading.mode"):
                return "paper"
            if (config_type, path) == ("trading", "paper_trading"):
                return True
            return default

    monkeypatch.setattr(market_data_manager, "get_config_manager", lambda: DummyConfig())

    manager = market_data_manager.MarketDataManager()

    assert manager.enable_live is False


@pytest.mark.asyncio
async def test_ai_bot_separates_training_profiles(monkeypatch, tmp_path):
    storage_root = tmp_path / "models"
    monkeypatch.setenv("AI_BOT_STORAGE_DIR", str(storage_root))

    from app.strategy import ai_trading_bot as module

    class DummyJoblib:
        @staticmethod
        def dump(obj, path):
            Path(path).write_text("model", encoding="utf-8")

        @staticmethod
        def load(path):
            return {
                'model': object(),
                'scaler': object(),
                'feature_columns': []
            }

    monkeypatch.setattr(module, "joblib", DummyJoblib, raising=False)
    monkeypatch.setattr(module, "ML_AVAILABLE", True)
    class DummyScaler:
        def fit_transform(self, data):
            return data

        def transform(self, data):
            return data

    monkeypatch.setattr(module, "StandardScaler", DummyScaler, raising=False)

    bot = AITradingBot("bot-profile", {"pair": "BTC/USDT", "trading_mode": "paper"})
    bot._sync_training_profile(initial=True)
    bot.ml_model = object()
    bot.scaler = object()
    bot.feature_columns = ["volatility"]

    await bot._save_model()

    paper_model_path = bot._get_model_path()
    assert "paper" in paper_model_path.parts
    assert paper_model_path.exists()

    paper_metadata = json.loads(paper_model_path.with_suffix(".json").read_text(encoding="utf-8"))
    assert paper_metadata["profile"] == "paper"

    bot.parameters["trading_mode"] = "live"
    bot.ml_model = object()

    await bot._save_model()

    live_model_path = bot._get_model_path()
    assert "live" in live_model_path.parts
    assert live_model_path.exists()
    assert live_model_path != paper_model_path

    live_metadata = json.loads(live_model_path.with_suffix(".json").read_text(encoding="utf-8"))
    assert live_metadata["profile"] == "live"
