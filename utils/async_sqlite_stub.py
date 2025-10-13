"""Lekki stub modułu aiosqlite na potrzeby środowisk bez tej biblioteki."""
from __future__ import annotations

import asyncio
import sqlite3
import sys
import types
from typing import Any, Iterable, Optional


class _AsyncCursor:
    def __init__(self, cursor: sqlite3.Cursor):
        self._cursor = cursor

    @property
    def lastrowid(self) -> int:
        return self._cursor.lastrowid

    async def fetchone(self):
        return await asyncio.to_thread(self._cursor.fetchone)

    async def fetchall(self):
        return await asyncio.to_thread(self._cursor.fetchall)

    async def fetchmany(self, size: Optional[int] = None):
        if size is None:
            return await asyncio.to_thread(self._cursor.fetchmany)
        return await asyncio.to_thread(self._cursor.fetchmany, size)

    async def close(self) -> None:
        await asyncio.to_thread(self._cursor.close)

    def __aiter__(self):
        return self

    async def __anext__(self):
        row = await self.fetchone()
        if row is None:
            raise StopAsyncIteration
        return row

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()


class _AsyncConnection:
    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection

    @property
    def row_factory(self):
        return self._connection.row_factory

    @row_factory.setter
    def row_factory(self, factory):
        self._connection.row_factory = factory

    async def execute(self, sql: str, parameters: Iterable[Any] | None = None) -> _AsyncCursor:
        params = tuple(parameters or ())

        def _exec():
            cur = self._connection.execute(sql, params)
            return _AsyncCursor(cur)

        return await asyncio.to_thread(_exec)

    async def executemany(self, sql: str, seq_of_parameters: Iterable[Iterable[Any]]):
        def _exec():
            cur = self._connection.executemany(sql, list(seq_of_parameters))
            return _AsyncCursor(cur)

        return await asyncio.to_thread(_exec)

    async def executescript(self, script: str):
        return await asyncio.to_thread(self._connection.executescript, script)

    async def cursor(self) -> _AsyncCursor:
        def _cursor():
            return _AsyncCursor(self._connection.cursor())

        return await asyncio.to_thread(_cursor)

    async def commit(self) -> None:
        await asyncio.to_thread(self._connection.commit)

    async def close(self) -> None:
        await asyncio.to_thread(self._connection.close)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()


async def _connect(path: str, **kwargs) -> _AsyncConnection:
    kwargs.setdefault("check_same_thread", False)

    def _open():
        conn = sqlite3.connect(path, **kwargs)
        conn.row_factory = sqlite3.Row
        return conn

    connection = await asyncio.to_thread(_open)
    return _AsyncConnection(connection)


def install_aiosqlite_stub():
    """Instaluje moduł ``aiosqlite`` w sys.modules, jeśli brakuje zależności."""

    if "aiosqlite" in sys.modules:
        return sys.modules["aiosqlite"]

    module = types.ModuleType("aiosqlite")
    module.connect = _connect
    module.Connection = _AsyncConnection
    module.Cursor = _AsyncCursor
    module.Row = sqlite3.Row
    sys.modules["aiosqlite"] = module
    return module


__all__ = ["install_aiosqlite_stub"]
