from __future__ import annotations

import os
import tempfile

import pytest

from src.csnote import db


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch: pytest.MonkeyPatch):
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    monkeypatch.setenv("CSNOTES_DB_PATH", path)
    db.init_db()
    db.upsert_customer("acme", "ACME Corp")
    yield
    os.unlink(path)


def test_insert_and_recent_roundtrip():
    db.insert_note(customer_slug="acme", kind="note", body="Hi there", author="alex", channel="C1")
    db.insert_note(customer_slug="acme", kind="todo", body="Send invoice", author="alex", channel="C1")

    recent = db.recent_notes("acme")
    assert len(recent) == 2
    bodies = [n.body for n in recent]
    assert "Send invoice" in bodies
    assert "Hi there" in bodies


def test_recent_orders_newest_first():
    first = db.insert_note(customer_slug="acme", kind="note", body="first", author="alex", channel=None)
    second = db.insert_note(customer_slug="acme", kind="note", body="second", author="alex", channel=None)

    recent = db.recent_notes("acme")
    # Newest should come first; SQLite created_at granularity could equal so check IDs as fallback
    ids = [n.id for n in recent]
    assert ids == [second, first]
