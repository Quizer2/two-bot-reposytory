import logging
import re
from typing import Iterable

SENSITIVE_KEYS = re.compile(r"(api|secret|token|key|password)", re.I)

class SensitiveFilter(logging.Filter):
    def __init__(self, keys: Iterable[str] | None=None):
        super().__init__()
        self.keys = set(k.lower() for k in (keys or []))

    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.getMessage())
        # mask values following key-like patterns: key=..., 'api_key': '...'
        msg = re.sub(r"(?P<k>[\w-]*?(api|secret|token|key|password)[\w-]*?)\s*[:=]\s*['\"]?([^'\"\s]+)", r"\g<k>=***", msg, flags=re.I)
        # generic 32+ char tokens
        msg = re.sub(r"(?<!\*)\b[A-Za-z0-9_\-]{32,}\b", "***", msg)
        record.msg = msg
        return True

def setup_logging(level: int = logging.INFO):
    logger = logging.getLogger()
    if logger.handlers:
        return  # already configured
    logger.setLevel(level)
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.addFilter(SensitiveFilter())
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    # Optional: reduce noisy libs
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    return logger
