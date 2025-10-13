import time
from datetime import datetime

import pytest

from utils.config_manager import ConfigManager
from utils.event_bus import get_event_bus, EventTypes


def test_config_manager_publishes_config_updated_and_notifies_listeners(tmp_path):
    # Przygotuj tymczasowy katalog z plikami konfiguracyjnymi
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    # Minimalny app_config.json
    (cfg_dir / "app_config.json").write_text("{}", encoding="utf-8")
    (cfg_dir / "ui_config.json").write_text("{}", encoding="utf-8")

    cm = ConfigManager(config_dir=str(cfg_dir))
    bus = get_event_bus()

    received = []

    def on_config_updated(event_data):
        received.append(event_data)

    # Subskrybuj EventBus bezpośrednio i via API CM
    bus.subscribe(EventTypes.CONFIG_UPDATED, on_config_updated)
    cm.subscribe_to_config_changes(on_config_updated)

    # Zmień wartość w app config via set_setting (powinno publikować EventTypes.CONFIG_UPDATED)
    current = cm.get_app_config()
    current.update({
        "risk_management": {
            "max_drawdown_percent": 12.5
        }
    })

    cm.save_config("app", current)

    # Daj odrobinę czasu na propagację synchroniczną (teoretycznie zbędne)
    time.sleep(0.01)

    # Asercje: event został opublikowany i listener otrzymał dane
    assert len(received) >= 1
    last = received[-1]
    assert last.get("config_type") == "app"
    assert "new_config" in last and isinstance(last["new_config"], dict)

    # Dodatkowo sprawdź, że UI/słuchacze używający EventTypes.CONFIG_UPDATED mogą reagować
    # (Tu ograniczamy się do weryfikacji samej publikacji i payloadu)

    # Cleanup subskrypcji
    bus.unsubscribe(EventTypes.CONFIG_UPDATED, on_config_updated)
    cm.unsubscribe_from_config_changes(on_config_updated)