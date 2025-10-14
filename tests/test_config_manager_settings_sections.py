import json
from pathlib import Path

from utils.config_manager import ConfigManager


def _create_manager(tmp_path) -> ConfigManager:
    cfg_dir = Path(tmp_path) / "config"
    manager = ConfigManager(config_dir=str(cfg_dir))
    manager.load_config("both")
    return manager


def test_update_risk_settings_roundtrip(tmp_path):
    manager = _create_manager(tmp_path)

    updated = manager.update_risk_settings({
        "max_daily_loss": 12.5,
        "max_drawdown": 21.0,
        "max_position_size": 7.5,
    })

    assert updated["max_daily_loss"] == 12.5
    assert updated["max_drawdown"] == 21.0
    assert updated["max_position_size"] == 7.5

    # Reload to confirm persistence
    reloaded = _create_manager(tmp_path)
    stored = reloaded.get_risk_settings()
    assert stored["max_daily_loss"] == 12.5
    assert stored["max_drawdown"] == 21.0
    assert stored["max_position_size"] == 7.5


def test_update_notification_settings_merges_channels(tmp_path):
    manager = _create_manager(tmp_path)

    manager.update_notification_settings({
        "enabled": False,
        "channels": {
            "email": {"enabled": True, "address": "alerts@example.com"},
            "telegram": {"enabled": True, "token": "token", "chat_id": "chat"},
        },
    })

    reloaded = _create_manager(tmp_path)
    settings = reloaded.get_notification_settings()

    assert settings["enabled"] is False
    assert settings["channels"]["email"]["address"] == "alerts@example.com"
    assert settings["channels"]["telegram"]["enabled"] is True
    assert settings["channels"]["discord"]["enabled"] is False  # default preserved


def test_update_general_settings_affects_app_and_ui(tmp_path):
    manager = _create_manager(tmp_path)

    payload = {
        "ui": {
            "theme": "light",
            "language": "en",
            "minimize_to_tray": False,
            "start_minimized": True,
        },
        "startup": {
            "start_with_system": True,
            "auto_start_bots": True,
            "auto_connect_exchanges": False,
        },
        "security": {
            "encrypt_config": False,
            "require_password": False,
            "auto_logout": False,
            "logout_timeout": 15,
        },
        "updates": {
            "auto_check": False,
            "beta_updates": True,
        },
    }

    manager.update_general_settings(payload)

    reloaded = _create_manager(tmp_path)
    general = reloaded.get_general_settings()

    assert general["ui"]["theme"] == "light"
    assert general["ui"]["language"] == "en"
    assert general["ui"]["minimize_to_tray"] is False
    assert general["ui"]["start_minimized"] is True
    assert general["startup"]["start_with_system"] is True
    assert general["startup"]["auto_start_bots"] is True
    assert general["startup"]["auto_connect_exchanges"] is False
    assert general["security"]["encrypt_config"] is False
    assert general["security"]["require_password"] is False
    assert general["security"]["auto_logout"] is False
    assert general["security"]["logout_timeout"] == 0
    assert general["updates"]["auto_check"] is False
    assert general["updates"]["beta_updates"] is True

    app_config_path = Path(tmp_path) / "config" / "app_config.json"
    with app_config_path.open("r", encoding="utf-8") as fh:
        app_cfg = json.load(fh)
    assert app_cfg["security"]["encryption_algorithm"] == "none"
    assert app_cfg["security"]["auto_lock_minutes"] == 0
