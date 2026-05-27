from contextlib import asynccontextmanager
import sqlite3
from typing import Any, AsyncIterator, List, Optional

from .config import DB_PATH


class AsyncCursor:
    def __init__(self, cursor: sqlite3.Cursor):
        self._cursor = cursor

    @property
    def lastrowid(self) -> int | None:
        return self._cursor.lastrowid

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    async def fetchall(self) -> list[sqlite3.Row]:
        return self._cursor.fetchall()

    async def fetchone(self) -> sqlite3.Row | None:
        return self._cursor.fetchone()


class AsyncConnection:
    def __init__(self, path: str):
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row

    @property
    def row_factory(self) -> Any:
        return self._conn.row_factory

    @row_factory.setter
    def row_factory(self, value: Any) -> None:
        self._conn.row_factory = value

    async def execute(self, sql: str, params: tuple = ()) -> AsyncCursor:
        return AsyncCursor(self._conn.execute(sql, params))

    async def executescript(self, sql: str) -> None:
        self._conn.executescript(sql)

    async def commit(self) -> None:
        self._conn.commit()

    async def close(self) -> None:
        self._conn.close()


@asynccontextmanager
async def db_connect() -> AsyncIterator[AsyncConnection]:
    """Create a DB connection with foreign keys enabled and row factory set.

    This intentionally uses sqlite3 behind an async-compatible shim. The previous
    aiosqlite worker-thread connection can hang in the current Python/sandbox
    test environment before startup completes.
    """
    db = AsyncConnection(DB_PATH)
    try:
        await db.execute("PRAGMA foreign_keys=ON")
        db.row_factory = sqlite3.Row
        yield db
    finally:
        await db.close()


async def db_exec(sql: str, params: tuple = ()) -> None:
    async with db_connect() as db:
        await db.execute(sql, params)
        await db.commit()


async def db_fetchall(sql: str, params: tuple = ()) -> List[sqlite3.Row]:
    async with db_connect() as db:
        cur = await db.execute(sql, params)
        return await cur.fetchall()


async def db_fetchone(sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
    rows = await db_fetchall(sql, params)
    return rows[0] if rows else None
