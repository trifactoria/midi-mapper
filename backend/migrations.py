import sqlite3
from pathlib import Path

from .db import db_connect
from .paths import SCHEMA_PATH


def init_schema(db_path: Path) -> None:
    con = sqlite3.connect(db_path)
    try:
        con.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        row = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='bindings'"
        ).fetchone()
        if row is None:
            raise RuntimeError(f"DB schema initialization failed: {db_path} has no bindings table")
        con.commit()
    finally:
        con.close()


async def apply_migrations() -> None:
    """Apply database migrations if needed."""
    async with db_connect() as db:
        # Check if new columns exist
        cursor = await db.execute("PRAGMA table_info(bindings)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]

        # Apply migration 002 if needed
        if "notes" not in column_names:
            await db.execute("ALTER TABLE bindings ADD COLUMN notes TEXT DEFAULT ''")
            await db.execute("ALTER TABLE bindings ADD COLUMN notify_text TEXT DEFAULT ''")
            await db.execute("ALTER TABLE bindings ADD COLUMN notify_emoji TEXT DEFAULT ''")
            await db.commit()

        # Apply migration 003: Add context_labels table
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='context_labels'")
        if not await cursor.fetchone():
            await db.execute(
                """
                CREATE TABLE context_labels (
                    context_id INTEGER PRIMARY KEY REFERENCES contexts(id) ON DELETE CASCADE,
                    label TEXT NOT NULL
                )
                """
            )
            await db.commit()
