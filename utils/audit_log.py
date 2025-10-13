from pathlib import Path
import json, time
from typing import Any, Dict

from utils.http_logging import sanitize_mapping
from utils.logger import get_logger, LogType
logger = get_logger(__name__, LogType.SECURITY)

LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "events.jsonl"


def _sanitize_deep(obj: Any) -> Any:
    try:
        if isinstance(obj, dict):
            # Najpierw zsanityzuj klucze na tym poziomie
            sanitized = sanitize_mapping(obj)
            # Następnie rekurencyjnie zsanityzuj wartości
            for k, v in list(sanitized.items()):
                sanitized[k] = _sanitize_deep(v)
            return sanitized
        if isinstance(obj, (list, tuple)):
            return type(obj)(_sanitize_deep(it) for it in obj)
        return obj
    except Exception as e:
        # W razie problemów zwróć bezpieczną reprezentację
        logger.debug(f"Sanitize deep failed: {e}", exc_info=True)
        try:
            return str(obj)
        except Exception as se:
            logger.debug(f"Stringify failed in sanitize: {se}", exc_info=True)
            return None


def log_event(event: str, payload: Dict[str, Any]) -> None:
    try:
        safe_payload = _sanitize_deep(payload or {})
        rec = {"ts": int(time.time()*1000), "event": event, "payload": safe_payload}
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        # Never let audit logging crash the app
        logger.debug(f"Audit log write failed: {e}", exc_info=True)
        try:
            rec = {"ts": int(time.time()*1000), "event": str(event), "payload": {"_log_error": True}}
            with LOG_FILE.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception as se:
            # swallow ultimate failure but log
            logger.debug(f"Audit log ultimate failure: {se}", exc_info=True)
