import os
import pytest

from utils.config_validation import validate_app_config


def test_validate_app_config_reports_missing_passphrase_for_enabled_kucoin(monkeypatch):
    # Enable KuCoin in app config with per-exchange settings
    config = {
        "exchanges": {
            "kucoin": {
                "enabled": True,
                "sandbox": False,
            }
        }
    }

    # Provide partial credentials via ENV (missing passphrase)
    monkeypatch.setenv("CRYPTOBOT_KUCOIN_API_KEY", "KEY")
    monkeypatch.setenv("CRYPTOBOT_KUCOIN_API_SECRET", "SECRET")
    if "CRYPTOBOT_KUCOIN_PASSPHRASE" in os.environ:
        monkeypatch.delenv("CRYPTOBOT_KUCOIN_PASSPHRASE", raising=False)

    issues = validate_app_config(config)

    assert isinstance(issues, list)
    # Expect at least one issue related to KuCoin passphrase missing
    assert any(("kucoin" in i.lower()) and ("passphrase" in i.lower()) for i in issues)