
from utils.notifications import get_notifier_from_config
_notifier = None
try:
    from utils.config_manager import ConfigManager
    _cfg = ConfigManager()
    _notifier = get_notifier_from_config(_cfg)
except Exception:
    _notifier = get_notifier_from_config(None)

import logging
from pathlib import Path
import asyncio
import threading, time as _t
from utils.yaml_loader import safe_load

from utils.logging_config import setup_logging
from utils.config_validation import validate_app_config
from utils.db_migrations import apply_migrations
from utils.net_wrappers import get_guard  # preload buckets
from utils.metrics_exporter import start_metrics_server, on_event
from utils.event_bus import get_event_bus, subscribe as global_subscribe
from utils.event_bus import register_on_cleared_hook
from utils import runtime_metrics as rt
from utils.runtime_metrics import record_fill, mark_price
from utils.metrics_persistence import save_snapshot
from utils.helpers import get_or_create_event_loop, schedule_coro_safely


def run_startup_checks():
    # metrics exporter
    start_metrics_server(8000)
    setup_logging()
    problems = validate_app_config()
    if problems:
        logging.getLogger(__name__).warning(f"Config issues: {problems}")
        # Highlight missing API credentials for enabled exchanges
        missing = [p for p in problems if isinstance(p, str) and p.startswith("missing_credentials:")]
        if missing:
            by_ex = {}
            for p in missing:
                try:
                    _, ex, key = p.split(":", 2)
                except Exception:
                    continue
                by_ex.setdefault(ex, []).append(key)
            # Provide guidance without exposing secrets
            for ex, keys in by_ex.items():
                logging.getLogger(__name__).warning(
                    f"Exchange '{ex}' missing credentials: {keys}. "
                    f"Set environment variables CRYPTOBOT_{ex.upper()}_API_KEY / CRYPTOBOT_{ex.upper()}_API_SECRET"
                    + (" / CRYPTOBOT_" + ex.upper() + "_PASSPHRASE" if "passphrase" in keys else "")
                    + " or fill config.exchanges." + ex + " and consider secure storage."
                )
    # DB migrate
    cfg = safe_load((Path(__file__).resolve().parents[1]/'config'/'app_config.yaml').read_text(encoding='utf-8'))
    db_rel = cfg.get('database', {}).get('path', 'data/database.db')
    db_path = Path(__file__).resolve().parents[1] / db_rel
    db_path.parent.mkdir(parents=True, exist_ok=True)
    apply_migrations(db_path)
    # Preload some rate limiters
    for key in ['binance:rest', 'binance:ws', 'okx:rest', 'bybit:rest']:
        try:
            get_guard(key)
        except Exception:
            pass

    # Validate API credentials for enabled exchanges without exposing secrets
    try:
        from app.api_config_manager import APIConfigManager
        import os as _os
        _api = APIConfigManager()
        _master = _os.getenv("CRYPTOBOT_MASTER_PASSWORD") or ""
        if _master:
            try:
                if _api.initialize_encryption(_master):
                    _api.load_api_config()
            except Exception:
                pass
        # Iterate over exchanges that are marked as enabled in encrypted config
        for _ex, _cfg in (_api.api_config or {}).items():
            if not isinstance(_cfg, dict) or not _cfg.get("enabled", False):
                continue
            _missing = []
            if not (_cfg.get("api_key") or "").strip():
                _missing.append("api_key")
            if not (_cfg.get("secret") or "").strip():
                _missing.append("api_secret")
            if _ex in ("kucoin", "coinbase") and not (_cfg.get("passphrase") or "").strip():
                _missing.append("passphrase")
            if _missing:
                logging.getLogger(__name__).warning(
                    f"Exchange '{_ex}' enabled but missing credentials: {_missing}. "
                    f"Set environment variables CRYPTOBOT_{_ex.upper()}_API_KEY / CRYPTOBOT_{_ex.upper()}_API_SECRET"
                    + (f" / CRYPTOBOT_{_ex.upper()}_PASSPHRASE" if "passphrase" in _missing else "")
                    + " or update encrypted API config (config/api_keys.encrypted)."
                )
    except Exception as _e:
        logging.getLogger(__name__).warning(f"Startup: API config validation skipped: {_e}")
# Ensure EventBus is initialized and subscribe metrics hooks for expected events
bus = get_event_bus()
_expected = ["TradeFilled", "OrderExecuted", "MarketDataUpdate", "Retry", "ReconnectAttempt"]

def _install_default_subscribers():
    for _ev in _expected:
        try:
            bus.subscribe(_ev, lambda p, ev=_ev: (on_event(ev, p), rt.record_event_name(ev)))
        except Exception:
            logging.getLogger(__name__).warning(f"Startup: failed to subscribe metrics hooks for {_ev}")
    # Verify and fallback subscribe via convenience function if needed
    try:
        for _ev in _expected:
            cnt = 0
            try:
                cnt = bus.get_listeners_count(_ev)
            except Exception:
                cnt = 0
            if cnt < 1:
                # fallback using convenience global subscribe
                global_subscribe(_ev, lambda p, ev=_ev: (on_event(ev, p), rt.record_event_name(ev)))
    except Exception:
        logging.getLogger(__name__).warning("Startup: metrics hooks verification failed")

# Core functional handlers (idempotent across clear: reinstalled by hook)

def _on_order_ev(p):
    try:
        ex = (p.get("exchange") if isinstance(p, dict) else None) or "na"
        sym = (p.get("symbol") if isinstance(p, dict) else None) or "NA"
        side = (p.get("side") if isinstance(p, dict) else None) or "NA"
        rt.record_order_event(ex, sym, side)
    except Exception:
        pass

def _on_order_filled(p):
    try:
        ex = (p.get("exchange") if isinstance(p, dict) else None) or "na"
        sym = p.get("symbol") or "NA"
        side = p.get("side") or "NA"
        price = float(p.get("price") or 0.0)
        qty = float(p.get("qty") or 0.0)
        record_fill(ex, sym, side, price, qty, p.get("bot_id"), p.get("strategy"))
        rt.record_order_event(ex, sym, side)
    except Exception:
        pass


def _on_market_tick(p):
    try:
        sym = p.get("symbol") or "NA"
        price = p.get("price") or p.get("bid") or p.get("ask")
        if price is not None:
            mark_price(sym, float(price))
    except Exception:
        pass


def _install_core_handlers():
    try:
        bus.subscribe('OrderSubmitted', _on_order_ev)
    except Exception:
        logging.getLogger(__name__).warning("Startup: failed to subscribe OrderSubmitted handler")
    try:
        bus.subscribe('ORDER_FILLED', _on_order_filled)
        bus.subscribe('TradeFilled', _on_order_filled)
        bus.subscribe('OrderExecuted', _on_order_filled)
        bus.subscribe('MarketDataUpdate', _on_market_tick)
        bus.subscribe('Retry', lambda p, _ev='Retry': rt.record_event_name(_ev))
        bus.subscribe('ReconnectAttempt', lambda p, _ev='ReconnectAttempt': rt.record_event_name(_ev))
    except Exception:
        logging.getLogger(__name__).warning("Startup: failed to subscribe core event handlers")

# Initial install
_install_default_subscribers()
_install_core_handlers()
# Reinstall after clear()
register_on_cleared_hook(lambda _bus: (_install_default_subscribers(), _install_core_handlers()))


def _persist_loop():
    while True:
        try:
            save_snapshot()
        except Exception:
            pass
        _t.sleep(5)
try:
    t = threading.Thread(target=_persist_loop, daemon=True)
    t.start()
except Exception:
    pass

# Telegram notifier for ORDER_FILLED
try:
    def _notify_order_filled(p):
        if _notifier is None:
            return None
        # Use unified scheduler with factory; do not create coro if no loop
        schedule_coro_safely(lambda: _notifier.send(f"ORDER_FILLED {p}"), run_in_thread_if_no_loop=False)
    bus.subscribe('ORDER_FILLED', _notify_order_filled)
except Exception:
    logging.getLogger(__name__).info("Startup: notifier for ORDER_FILLED disabled")
