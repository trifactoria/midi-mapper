from contextlib import asynccontextmanager
from typing import AsyncIterator, List, Optional

import aiosqlite

from .config import DB_PATH


@asynccontextmanager
async def db_connect() -> AsyncIterator[aiosqlite.Connection]:
    """Create a DB connection with foreign keys enabled and row factory set."""
    db = await aiosqlite.connect(DB_PATH)
    try:
        await db.execute("PRAGMA foreign_keys=ON")
        db.row_factory = aiosqlite.Row
        yield db
    finally:
        await db.close()


async def db_exec(sql: str, params: tuple = ()) -> None:
    async with db_connect() as db:
        await db.execute(sql, params)
        await db.commit()


async def db_fetchall(sql: str, params: tuple = ()) -> List[aiosqlite.Row]:
    async with db_connect() as db:
        cur = await db.execute(sql, params)
        return await cur.fetchall()


async def db_fetchone(sql: str, params: tuple = ()) -> Optional[aiosqlite.Row]:
    rows = await db_fetchall(sql, params)
    return rows[0] if rows else None
