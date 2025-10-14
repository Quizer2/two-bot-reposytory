import types

import pytest

from ui import bot_config


@pytest.fixture
def bot_config_fakes(monkeypatch):
    class DummyComboBox:
        def __init__(self, text="", data=None):
            self._text = text
            self._data = data

        def currentText(self):
            return self._text

        def currentData(self, role=None):
            return self._data

    class DummyLineEdit:
        def __init__(self, text=""):
            self._text = text

        def text(self):
            return self._text

    class DummyDoubleSpinBox:
        def __init__(self, value=0.0):
            self._value = value

        def value(self):
            return self._value

    class DummySpinBox:
        def __init__(self, value=0):
            self._value = value

        def value(self):
            return self._value

    class DummyMessageBox:
        calls = []

        @classmethod
        def information(cls, *args, **kwargs):
            cls.calls.append((args, kwargs))

    monkeypatch.setattr(bot_config, "QComboBox", DummyComboBox)
    monkeypatch.setattr(bot_config, "QLineEdit", DummyLineEdit)
    monkeypatch.setattr(bot_config, "QDoubleSpinBox", DummyDoubleSpinBox)
    monkeypatch.setattr(bot_config, "QSpinBox", DummySpinBox)
    monkeypatch.setattr(bot_config, "QMessageBox", DummyMessageBox)

    return types.SimpleNamespace(
        Combo=DummyComboBox,
        LineEdit=DummyLineEdit,
        DoubleSpin=DummyDoubleSpinBox,
        Spin=DummySpinBox,
        message_box=DummyMessageBox,
    )


def test_extract_strategy_key_falls_back_to_text(bot_config_fakes):
    widget = object.__new__(bot_config.BotConfigWidget)
    combo = bot_config_fakes.Combo("Momentum", data=None)

    assert widget._extract_strategy_key(combo) == "momentum"


def test_normalise_pair_value_uses_combo_text(bot_config_fakes):
    widget = object.__new__(bot_config.BotConfigWidget)
    combo = bot_config_fakes.Combo("eth/usdt", data="grid")

    assert widget._normalise_pair_value(combo) == "ETH/USDT"


def test_save_bot_config_persists_with_combobox_pair(bot_config_fakes):
    widget = object.__new__(bot_config.BotConfigWidget)
    widget.bots_data = []
    widget.logger = None

    widget._collect_strategy_field_values = lambda state: {"grid_size": 8}
    captured = {}

    def fake_compose(strategy_key, strategy_settings, trading_settings, pair):
        captured["compose_args"] = (strategy_key, strategy_settings, trading_settings, pair)
        return {"composed": True}

    def fake_persist(payload):
        captured["payload"] = payload
        return True

    widget._compose_parameters = fake_compose
    widget._persist_bot_config = fake_persist
    widget.reload_backend_state = lambda: captured.setdefault("reloaded", True)
    widget.cancel_bot_edit = lambda: captured.setdefault("cancelled", True)

    form_state = {
        "name": bot_config_fakes.LineEdit("Nowy Bot"),
        "pair": bot_config_fakes.Combo("eth/usdt", data="grid"),
        "strategy_combo": bot_config_fakes.Combo("Grid", data="grid"),
        "strategy_state": {},
        "amount": bot_config_fakes.DoubleSpin(250.0),
        "take_profit": bot_config_fakes.DoubleSpin(3.5),
        "stop_loss": bot_config_fakes.DoubleSpin(1.25),
        "max_orders": bot_config_fakes.Spin(12),
        "interval": bot_config_fakes.Combo("5m"),
    }

    bot_data = {
        "id": None,
        "name": "",
        "strategy": "",
        "parameters": {},
        "trading_settings": {},
    }

    widget.save_bot_config(bot_data, form_state)

    assert captured["payload"]["symbol"] == "ETH/USDT"
    assert captured["payload"]["strategy"] == "grid"
    assert captured["compose_args"][3] == "ETH/USDT"
    assert bot_config_fakes.message_box.calls, "Expected success message to be emitted"
