import sys
import types
import asyncio
import sqlite3
import pytest
from pathlib import Path

# Ensure project root is importable when running tests directly
ROOT_DIR = Path(__file__).resolve().parents[1]
root_str = str(ROOT_DIR)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

# Teraz możemy importować stub PyQt6
from utils.pyqt_stubs import install_pyqt_stubs

# Install PyQt6 stubs if moduł nie jest dostępny (np. brak libGL)
install_pyqt_stubs()

# Optional dependency shims -------------------------------------------------

if "aiosqlite" not in sys.modules:
    try:
        import aiosqlite  # type: ignore  # pragma: no cover - prefer real dependency
    except Exception:  # pragma: no cover - dependency unavailable in CI
        aiosqlite_stub = types.ModuleType("aiosqlite")

        class Cursor:
            def __init__(self, cursor: sqlite3.Cursor):
                self._cursor = cursor

            @property
            def lastrowid(self):
                return self._cursor.lastrowid

            async def fetchone(self):
                return await asyncio.to_thread(self._cursor.fetchone)

            async def fetchall(self):
                return await asyncio.to_thread(self._cursor.fetchall)

            async def fetchmany(self, size=None):
                if size is None:
                    return await asyncio.to_thread(self._cursor.fetchmany)
                return await asyncio.to_thread(self._cursor.fetchmany, size)

            async def close(self):
                await asyncio.to_thread(self._cursor.close)

            def __aiter__(self):
                return self

            async def __anext__(self):
                row = await self.fetchone()
                if row is None:
                    raise StopAsyncIteration
                return row

        class Connection:
            def __init__(self, connection: sqlite3.Connection):
                self._connection = connection

            @property
            def row_factory(self):
                return self._connection.row_factory

            @row_factory.setter
            def row_factory(self, factory):
                self._connection.row_factory = factory

            async def execute(self, sql, parameters=None):
                params = parameters if parameters is not None else ()

                def _exec():
                    cur = self._connection.execute(sql, tuple(params))
                    return Cursor(cur)

                return await asyncio.to_thread(_exec)

            async def commit(self):
                await asyncio.to_thread(self._connection.commit)

            async def close(self):
                await asyncio.to_thread(self._connection.close)

        async def connect(path, **kwargs):
            def _connect():
                conn = sqlite3.connect(path, check_same_thread=False, **kwargs)
                return Connection(conn)

            return await asyncio.to_thread(_connect)

        aiosqlite_stub.connect = connect
        aiosqlite_stub.Connection = Connection
        aiosqlite_stub.Cursor = Cursor
        sys.modules["aiosqlite"] = aiosqlite_stub

if "websockets" not in sys.modules:
    try:
        import websockets  # type: ignore  # pragma: no cover - prefer real dependency
    except Exception:  # pragma: no cover - dependency unavailable in CI
        websockets_stub = types.ModuleType("websockets")

        class _ConnectionClosed(Exception):
            pass

        class exceptions:  # pragma: no cover - attribute namespace
            ConnectionClosed = _ConnectionClosed

        class FakeWebSocket:
            def __init__(self):
                self._queue: asyncio.Queue[str] = asyncio.Queue()

            async def send(self, message: str) -> None:  # pragma: no cover - trivial
                await asyncio.sleep(0)

            async def recv(self) -> str:  # pragma: no cover - trivial
                return await self._queue.get()

            async def close(self) -> None:  # pragma: no cover - trivial
                await asyncio.sleep(0)

        async def connect(*args, **kwargs):
            raise _ConnectionClosed(
                "websockets.connect is unavailable in the lightweight test environment"
            )

        websockets_stub.connect = connect
        websockets_stub.exceptions = exceptions
        websockets_stub.FakeWebSocket = FakeWebSocket
        sys.modules["websockets"] = websockets_stub

@pytest.fixture(autouse=True)
def ensure_event_loop():
    """Ensure there's an event loop available for tests that use asyncio.get_event_loop()."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    yield
    # Do not close the loop here; tests may schedule tasks across modules.
    # Leaving it managed by pytest process avoids dangling loop issues.
