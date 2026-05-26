"""SQLite persistence for CS notes.

Schema is small and intentionally Postgres-compatible. We keep one connection
per call to stay thread-safe under Bolt's async dispatcher.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator, Literal

NoteKind = Literal["note", "todo"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    slug         TEXT PRIMARY KEY,
    display_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_slug TEXT NOT NULL REFERENCES customers(slug),
    kind         TEXT NOT NULL CHECK (kind IN ('note', 'todo')),
    body         TEXT NOT NULL,
    author       TEXT NOT NULL,
    channel      TEXT,
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    done         INTEGER NOT NULL DEFAULT 0  -- only meaningful for todos
);

CREATE INDEX IF NOT EXISTS idx_notes_customer_created
    ON notes(customer_slug, created_at DESC);
"""


@dataclass
class Note:
    id: int
    customer_slug: str
    kind: NoteKind
    body: str
    author: str
    channel: str | None
    created_at: datetime
    done: bool


def db_path() -> str:
    return os.environ.get("CSNOTES_DB_PATH", "csnotes.db")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    path = db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def upsert_customer(slug: str, display_name: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO customers(slug, display_name) VALUES (?, ?) "
            "ON CONFLICT(slug) DO UPDATE SET display_name = excluded.display_name",
            (slug, display_name),
        )


def list_customer_slugs() -> list[str]:
    with connect() as conn:
        return [r["slug"] for r in conn.execute("SELECT slug FROM customers")]


def lookup_customer(slug: str) -> str | None:
    """Return display_name or None if slug isn't a known customer."""
    with connect() as conn:
        row = conn.execute("SELECT display_name FROM customers WHERE slug = ?", (slug,)).fetchone()
        return row["display_name"] if row else None


def insert_note(
    *,
    customer_slug: str,
    kind: NoteKind,
    body: str,
    author: str,
    channel: str | None,
) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO notes(customer_slug, kind, body, author, channel) "
            "VALUES (?, ?, ?, ?, ?)",
            (customer_slug, kind, body, author, channel),
        )
        return cur.lastrowid


def _row_to_note(row: sqlite3.Row) -> Note:
    return Note(
        id=row["id"],
        customer_slug=row["customer_slug"],
        kind=row["kind"],
        body=row["body"],
        author=row["author"],
        channel=row["channel"],
        created_at=datetime.fromisoformat(row["created_at"]),
        done=bool(row["done"]),
    )


def recent_notes(customer_slug: str, limit: int = 5) -> list[Note]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM notes WHERE customer_slug = ? "
            "ORDER BY created_at DESC, id DESC LIMIT ?",
            (customer_slug, limit),
        ).fetchall()
        return [_row_to_note(r) for r in rows]


def all_notes_for_ask(customer_slug: str, limit: int = 100) -> list[Note]:
    """Notes used as context for /csnote ask. Newest first, capped to avoid
    blowing up the prompt on customers with a long history."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM notes WHERE customer_slug = ? "
            "ORDER BY created_at DESC, id DESC LIMIT ?",
            (customer_slug, limit),
        ).fetchall()
        return [_row_to_note(r) for r in rows]
