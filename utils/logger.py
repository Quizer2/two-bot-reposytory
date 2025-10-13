"""
Central logging utilities for CryptoBotDesktop.
Provides rotating file logging, console logging and optional DB logging.
"""

from __future__ import annotations

import logging
import logging.handlers
import asyncio
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timedelta, timezone
from utils.helpers import schedule_coro_safely

# --- added: sanitizer ---
import re
SENSITIVE_PAT = re.compile(r"(api[_-]?key|secret|token|password|passphrase|signature)\s*[:=]?\s*([A-Za-z0-9+/=._-]{6,})", re.I)

def _mask_str(s: str) -> str:
    try:
        def _mask_val(m):
            val = m.group(2)
            if len(val) >= 6:
                return m.group(0).replace(val, val[:2] + "***" + val[-2:])
            return m.group(0).replace(val, "***")
        return SENSITIVE_PAT.sub(_mask_val, s)
    except Exception:
        return s

class SanitizingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        try:
            msg = super().format(record)
            return _mask_str(msg)
        except Exception:
            return super().format(record)


class LogType(Enum):
    SYSTEM = "system"
    ERROR = "error"
    TRADE = "trade"
    NETWORK = "network"
    DEBUG = "debug"
    USER = "user"
    BOT = "bot"
    SECURITY = "security"


class LogLevel(Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class DatabaseLogHandler(logging.Handler):
    """Async-friendly handler that writes logs to an async database manager (if provided)."""
    def __init__(self, database_manager=None):
        super().__init__()
        self.database_manager = database_manager
        self.log_queue: List[Dict] = []
        self.max_queue_size = 100

    def emit(self, record: logging.LogRecord) -> None:
        try:
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "message": self.format(record),
            }
            self.log_queue.append(entry)
            if len(self.log_queue) >= self.max_queue_size:
                try:
                    # Schedule flush safely: in running loop create task, otherwise run in background thread
                    schedule_coro_safely(lambda: self._flush_to_db(), run_in_thread_if_no_loop=True)
                except Exception:
                    # best-effort, swallow
                    pass
        except Exception:
            # Never let logging crash the app
            pass

    async def _flush_to_db(self) -> None:
        if not self.database_manager or not self.log_queue:
            return
        try:
            items = list(self.log_queue)
            self.log_queue.clear()
            for it in items:
                try:
                    await self.database_manager.add_log(
                        message=it.get("message", ""),
                        log_type="system",
                        level=it.get("level", "INFO"),
                        timestamp=it.get("timestamp"),
                    )
                except Exception:
                    # isolate single row failure
                    continue
        except Exception:
            # swallow handler internal errors
            pass

    def close(self) -> None:
        try:
            if self.log_queue and self.database_manager:
                try:
                    # If a loop is running, avoid scheduling flush during close to prevent interference
                    asyncio.get_running_loop()
                    # can't await here safely; drop on close
                    pass
                except RuntimeError:
                    try:
                        # No running loop: perform flush in background thread using safe scheduler
                        schedule_coro_safely(lambda: self._flush_to_db(), run_in_thread_if_no_loop=True)
                    except Exception:
                        pass
        except Exception:
            pass
        finally:
            super().close()


class LoggerManager:
    """Sets up application-wide logging sinks and exposes helpers."""
    def __init__(self, log_dir: Path | str = "logs", level: int = logging.INFO, database_manager=None):
        self.log_dir = Path(log_dir)
        self.level = level
        self.database_manager = database_manager
        self._configured = False

    def setup(self) -> logging.Logger:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger()
        logger.setLevel(self.level)

        # Remove existing handlers to avoid duplicates in repeated setup() calls
        for h in list(logger.handlers):
            logger.removeHandler(h)

        fmt = SanitizingFormatter('[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

        # Console
        ch = logging.StreamHandler()
        ch.setLevel(self.level)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

        # Rotating file
        fh = logging.handlers.RotatingFileHandler(self.log_dir / "main.log", maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
        fh.setLevel(self.level)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

        # Optional DB
        if self.database_manager is not None:
            dh = DatabaseLogHandler(self.database_manager)
            dh.setLevel(self.level)
            dh.setFormatter(fmt)
            logger.addHandler(dh)

        self._configured = True
        logging.getLogger(__name__).info("Logger configured.")
        return logger

    def get_recent_logs(self, log_type: Optional[LogType] = None, limit: int = 100) -> List[Dict]:
        """Return last 'limit' lines from log files."""
        out: List[Dict] = []
        try:
            patterns = [f"{log_type.value}_*.log"] if log_type else ["*.log"]
            files: List[Path] = []
            for pat in patterns:
                files.extend(self.log_dir.glob(pat))
            for lf in files:
                if not lf.exists():
                    continue
                try:
                    with lf.open("r", encoding="utf-8") as f:
                        lines = f.readlines()
                        for line in lines[-limit:]:
                            out.append({"file": lf.name, "line": line.strip()})
                except Exception:
                    continue
        except Exception:
            pass
        return out[-limit:]

    def cleanup_old_logs(self, days_to_keep: int = 30) -> None:
        """Remove rotated log files older than days_to_keep."""
        try:
            cutoff = datetime.now() - timedelta(days=days_to_keep)
            for lf in self.log_dir.glob("*.log*"):
                try:
                    if lf.is_file():
                        ts = datetime.fromtimestamp(lf.stat().st_mtime)
                        if ts < cutoff:
                            lf.unlink()
                            logging.getLogger(__name__).info(f"Deleted old log file: {lf.name}")
                except Exception:
                    continue
        except Exception:
            pass


def get_logger(name: str | None = None, log_type: 'LogType' | None = None, level: 'LogLevel' | int | None = None):
    logger = logging.getLogger(name or __name__)
    # Optionally set level if provided
    if level is not None:
        try:
            logger.setLevel(level.value if hasattr(level, 'value') else int(level))
        except Exception:
            pass
    # Attach log_type as an attribute for consumers that might read it
    try:
        setattr(logger, 'log_type', log_type.value if hasattr(log_type, 'value') else (log_type or None))
    except Exception:
        pass
    return logger
