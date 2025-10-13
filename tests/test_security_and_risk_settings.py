import asyncio

import app.api_config_manager as api_cfg
from app.risk_management import RiskManager, RiskLimits
from utils.config_manager import ConfigManager
from utils.event_bus import EventTypes, get_event_bus


def test_api_config_manager_syncs_trading_mode(tmp_path, monkeypatch):
    temp_config_dir = tmp_path / "cfg"
    temp_config_dir.mkdir()
    temp_manager = ConfigManager(config_dir=str(temp_config_dir))

    monkeypatch.setattr(api_cfg, "get_config_manager", lambda: temp_manager)
    monkeypatch.setattr(api_cfg, "CREDENTIALS_FILE", tmp_path / "exchange_credentials.json")

    manager = api_cfg.APIConfigManager()
    manager.config_dir = tmp_path
    manager.api_config_file = tmp_path / "api_keys.encrypted"
    manager.api_config = {ex: cfg.copy() for ex, cfg in manager.default_config.items()}

    for cfg in manager.api_config.values():
        cfg.update({"api_key": "", "secret": "", "enabled": False})

    manager.save_api_config()

    assert temp_manager.get_setting("app", "trading.paper_trading", False) is True
    assert temp_manager.get_setting("app", "trading.default_mode", "live") == "paper"

    temp_manager.set_setting("app", "trading.paper_trading", False, meta={"source": "test"})
    temp_manager.set_setting("app", "trading.default_mode", "live", meta={"source": "test"})

    cfg = manager.api_config["binance"]
    cfg.update({"api_key": "key", "secret": "secret", "enabled": True, "sandbox": False})
    manager.save_api_config()

    assert temp_manager.get_setting("app", "trading.default_mode", "paper") == "live"
    assert temp_manager.get_setting("app", "trading.paper_trading", True) is False


def test_risk_manager_update_settings_emits_event(monkeypatch):
    manager = RiskManager(db_manager=None)
    captured = {}
    monkeypatch.setattr(
        manager,
        "_persist_limits_to_file",
        lambda bot_id, limits: captured.update({"bot_id": bot_id, "limits": limits}),
    )

    events = []
    bus = get_event_bus()

    def listener(payload):
        events.append(payload)

    bus.subscribe(EventTypes.CONFIG_RISK_UPDATED, listener)
    try:
        manager.update_settings(
            {
                "max_daily_loss": 4.5,
                "max_drawdown": 12.0,
                "max_position_size": 7.5,
                "max_open_positions": 3,
            }
        )
    finally:
        bus.unsubscribe(EventTypes.CONFIG_RISK_UPDATED, listener)

    assert captured["bot_id"] is None
    assert isinstance(captured["limits"], RiskLimits)
    assert abs(captured["limits"].daily_loss_limit - 4.5) < 1e-9
    assert events, "Expected CONFIG_RISK_UPDATED event"
    last = events[-1]
    assert last.get("meta", {}).get("scope") == "default"
    assert abs(last.get("limits", {}).get("daily_loss_limit", 0.0) - 4.5) < 1e-9


def test_risk_manager_update_limits_emits_event(monkeypatch):
    manager = RiskManager(db_manager=None)
    captured = {}
    monkeypatch.setattr(
        manager,
        "_persist_limits_to_file",
        lambda bot_id, limits: captured.update({"bot_id": bot_id, "limits": limits}),
    )

    events = []
    bus = get_event_bus()

    def listener(payload):
        events.append(payload)

    bus.subscribe(EventTypes.CONFIG_RISK_UPDATED, listener)
    try:
        limits = RiskLimits(daily_loss_limit=2.0, position_size_limit=1500.0)
        asyncio.run(manager.update_risk_limits(7, limits))
    finally:
        bus.unsubscribe(EventTypes.CONFIG_RISK_UPDATED, listener)

    assert captured["bot_id"] == 7
    assert captured["limits"].daily_loss_limit == 2.0
    assert any(evt.get("meta", {}).get("bot_id") == 7 for evt in events)
