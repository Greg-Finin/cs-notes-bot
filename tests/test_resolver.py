from __future__ import annotations

import os
import tempfile

import pytest

from src.csnote import db
from src.csnote.resolver import Resolved, Unresolved, resolve


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch: pytest.MonkeyPatch):
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    monkeypatch.setenv("CSNOTES_DB_PATH", path)
    db.init_db()
    db.upsert_customer("northwind", "Northwind Logistics")
    db.upsert_customer("helix", "Helix Biosciences")
    yield
    os.unlink(path)


def test_resolves_from_channel_with_suffix():
    r = resolve("northwind-channel", ["Spoke", "today"])
    assert isinstance(r, Resolved)
    assert r.slug == "northwind"
    assert r.remaining_text == "Spoke today"


def test_resolves_from_bare_channel_name():
    r = resolve("helix", ["Pricing", "call", "went", "well"])
    assert isinstance(r, Resolved)
    assert r.slug == "helix"
    assert r.remaining_text == "Pricing call went well"


def test_explicit_customer_overrides_channel():
    r = resolve("northwind-channel", ["customer", "helix", "Sent", "renewal", "quote"])
    assert isinstance(r, Resolved)
    assert r.slug == "helix"
    assert r.remaining_text == "Sent renewal quote"


def test_unknown_explicit_customer_returns_unresolved():
    r = resolve(None, ["customer", "nobody", "Hi"])
    assert isinstance(r, Unresolved)
    assert "nobody" in r.reason


def test_unknown_channel_returns_unresolved():
    r = resolve("random-water-cooler", ["just", "chatting"])
    assert isinstance(r, Unresolved)
