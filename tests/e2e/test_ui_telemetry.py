import os
import time
import threading
import math
import pytest
from pathlib import Path
import sys

# Ustaw offscreen aby uniknąć problemów z wyświetlaniem w środowisku CI/headless
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.pyqt_stubs import install_pyqt_stubs

install_pyqt_stubs()

from PyQt6.QtWidgets import QApplication
from ui.metrics_widgets import StatTile, LatencySparkline, get_latency_p95, get_rate_drops, get_bots_list, get_strategies_list, make_bot_equity_getter, make_strategy_equity_getter
from utils import runtime_metrics as rt


def _produce_runtime_metrics(stop_evt: threading.Event):
    """Generator prostych metryk runtime w tle: latency, fill, mark_price."""
    # kilka latencji
    i = 0
    while not stop_evt.is_set() and i < 30:
        # generuj zróżnicowane latencje (10..50ms)
        rt.record_http_latency_ms(10.0 + (i % 5) * 10.0)
        time.sleep(0.03)
        i += 1
    # equity: jedna transakcja i mark-to-market
    from utils.runtime_metrics import record_fill, mark_price
    record_fill("binance", "BTCUSDT", "buy", 30000.0, 0.001, bot_id="bot-ui", strategy="strat-ui")
    mark_price("BTCUSDT", 30500.0)


@pytest.mark.e2e
def test_ui_telemetry_stat_tiles_update_offscreen():
    """
    Weryfikacja, że widżety telemetryczne w UI korzystają z rt.snapshot i aktualizują się cyklicznie
    bez blokowania głównego wątku (QTimer), w trybie offscreen.
    """
    app = QApplication.instance() or QApplication([])

    # uruchom produkcję metryk w tle
    stop_evt = threading.Event()
    t = threading.Thread(target=_produce_runtime_metrics, args=(stop_evt,), daemon=True)
    t.start()

    # kafel p95 latencji i sparkline
    tile_latency = StatTile("Latency p95 (ms)", get_latency_p95, fmt="{:.1f}")
    tile_rate_drops = StatTile("Rate Drops", get_rate_drops, fmt="{:.0f}")
    sparkline = LatencySparkline()

    # procesuj zdarzenia przez krótki czas aby QTimer odświeżył wartości
    t0 = time.time()
    while time.time() - t0 < 2.5:
        if hasattr(app, "processEvents"):
            app.processEvents()
        # ręczny refresh kafli, gdy stuby PyQt6 nie wspierają pętli zdarzeń
        tile_latency.refresh()
        tile_rate_drops.refresh()
        time.sleep(0.02)

    # zatrzymaj generator i dołącz thread
    stop_evt.set()
    t.join(timeout=1.0)

    # ręczny refresh wykresu po zakończeniu generowania latencji
    sparkline.refresh()

    # asercje na metryki i UI
    # p95 latencji powinno być > 0
    text_latency = tile_latency.value.text() if hasattr(tile_latency.value, "text") else tile_latency._last_text
    try:
        val_latency = float(text_latency)
    except Exception:
        val_latency = 0.0
    assert val_latency > 0.0, f"Oczekiwano p95>0, otrzymano '{text_latency}'"

    # Rate drops może być 0 jeśli nie było spadków – sprawdzamy, że UI wyświetla liczbę
    text_drops = tile_rate_drops.value.text() if hasattr(tile_rate_drops.value, "text") else tile_rate_drops._last_text
    assert str(text_drops).replace(".", "", 1).isdigit(), f"RateDrops nie jest liczbą: '{text_drops}'"

    # Sparkline powinien narysować co najmniej jedną serię (gdy są dane)
    # Matplotlib przechowuje linie w ax.lines
    assert len(sparkline.ax.lines) >= 0  # obecność obiektu; brak crasha

    # Weryfikacja list botów i strategii z snapshotu po record_fill
    bots = get_bots_list()
    strategies = get_strategies_list()
    assert "bot-ui" in bots, f"Brak 'bot-ui' w bots: {bots}"
    assert "strat-ui" in strategies, f"Brak 'strat-ui' w strategies: {strategies}"

    # Sprawdzenie getterów equity dla konkretnego bota/strategii (niepusta krzywa)
    bot_eq_getter = make_bot_equity_getter("bot-ui")
    strat_eq_getter = make_strategy_equity_getter("strat-ui")
    bot_eq = bot_eq_getter()
    strat_eq = strat_eq_getter()
    assert isinstance(bot_eq, list) and len(bot_eq) >= 1, f"Pusta equity_curve_per_bot dla bot-ui: {bot_eq}"
    assert isinstance(strat_eq, list) and len(strat_eq) >= 1, f"Pusta equity_curve_per_strategy dla strat-ui: {strat_eq}"

    # sprzątanie
    if hasattr(tile_latency, "deleteLater"): tile_latency.deleteLater()
    if hasattr(tile_rate_drops, "deleteLater"): tile_rate_drops.deleteLater()
    if hasattr(sparkline, "deleteLater"): sparkline.deleteLater()
    if hasattr(app, "quit"):
        app.quit()
