from utils.logger import get_logger
logger = get_logger(__name__)

import logging, re
from typing import Mapping, Any, Tuple

SENSITIVE_KEYS = re.compile(r"(api|secret|token|key|password|passphrase|signature)", re.I)

def _mask_value(v: Any) -> Any:
    if v is None:
        return None
    s = str(v)
    if len(s) >= 6:
        return s[:2] + "***" + s[-2:]
    return "***"

def sanitize_mapping(d: Mapping[str, Any]) -> dict:
    out = {}
    for k, v in (d or {}).items():
        if SENSITIVE_KEYS.search(str(k)):
            out[k] = _mask_value(v)
        else:
            out[k] = v
    return out

def log_request(logger: logging.Logger, method: str, url: str, *, headers: Mapping[str, Any] | None=None, params: Mapping[str, Any] | None=None, json_body: Any=None):
    try:
        h = sanitize_mapping(headers or {})
        p = sanitize_mapping(params or {})
        jb = json_body
        if isinstance(jb, dict):
            jb = sanitize_mapping(jb)
        logger.debug("HTTP %s %s headers=%s params=%s body=%s", method, url, h, p, jb)
    except Exception:
        logger.debug("HTTP %s %s (log sanitize failed)", method, url)