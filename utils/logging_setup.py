import logging, re, os

SECRET_PATTERNS = [
    r"api[_-]?key\s*[:=]\s*['\"]?([A-Za-z0-9-_]{8,})['\"]?" ,
    r"secret\s*[:=]\s*['\"]?([A-Za-z0-9-_]{6,})['\"]?" ,
    r"token\s*[:=]\s*['\"]?([A-Za-z0-9-_.]{10,})['\"]?" ,
]

class SecretMaskFilter(logging.Filter):
    def __init__(self, patterns=None):
        super().__init__()
        self.regexes = [re.compile(pat, re.I) for pat in (patterns or SECRET_PATTERNS)]
    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.getMessage())
        for rx in self.regexes:
            msg = rx.sub(lambda m: m.group(0).replace(m.group(1), "***MASKED***"), msg)
        record.msg = msg
        return True

def setup_logging(level: str|int = None):
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    level = level or os.environ.get("APP_LOG_LEVEL", "INFO")
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s"
    )
    root_logger = logging.getLogger()
    root_logger.addFilter(SecretMaskFilter())
    return root_logger
