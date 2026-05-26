"""Populate the local SQLite DB with fictional customers + a few months of
notes, so /csnote ask has real history to draw on for the demo.

Usage:
    python -m scripts.seed_db
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

from src.csnote import db  # noqa: E402

CUSTOMERS = [
    ("northwind", "Northwind Logistics"),
    ("helix", "Helix Biosciences"),
    ("atlas", "Atlas Freight"),
]

# (customer_slug, kind, body, author, days_ago)
SEED_NOTES = [
    # Northwind — an SSO-heavy account
    ("northwind", "note", "Kickoff call w/ ops team. They want to roll out to 200 users by EOQ. Main concern is Okta SSO.", "alex", 90),
    ("northwind", "note", "SSO config done. They're on Okta, RelayState format is the hash-fragment style.", "alex", 75),
    ("northwind", "todo", "Send them the SAML attribute mapping doc.", "alex", 75),
    ("northwind", "note", "Pilot group (20 users) live. Positive feedback on the dashboard speed.", "alex", 60),
    ("northwind", "note", "Expansion conversation — they want to add a second team next quarter. Champion is the ops director.", "alex", 30),
    ("northwind", "note", "Hit by the redirect-loop bug this morning. Engineering says ENG-1421 is the fix. Customer was understanding.", "alex", 1),
    ("northwind", "todo", "Follow up with ops director on the SSO incident once ENG-1421 ships.", "alex", 1),

    # Helix — reporting / Snowflake focus
    ("helix", "note", "Finance team uses our monthly usage reports for billing reconciliation. CSV export is critical for them.", "alex", 80),
    ("helix", "note", "They're on the Snowflake-backed reporting tier, ~250k rows/month.", "alex", 80),
    ("helix", "todo", "Get them onto the new dashboard before next renewal.", "alex", 45),
    ("helix", "note", "Renewal discussion went well. They want a 15% discount for a 2-year commit.", "alex", 20),
    ("helix", "note", "CSV export issue — only 100k rows downloading. Filed under ENG-1602. Finance unblocked via manual extract.", "alex", 0),

    # Atlas — integrations-heavy
    ("atlas", "note", "Atlas integrates webhooks into their sync pipeline. Latency-sensitive.", "alex", 100),
    ("atlas", "note", "Onboarding complete. They're sending ~50k events/day.", "alex", 70),
    ("atlas", "todo", "Set up monthly health-check call.", "alex", 70),
    ("atlas", "note", "Champion left for another company last month. New POC is the head of engineering, less hands-on with our tool.", "alex", 25),
    ("atlas", "note", "Webhook delivery delays today. ENG-1518 in review. They were unhappy but appreciated the quick update.", "alex", 0),
]


def main() -> None:
    db.init_db()
    for slug, display in CUSTOMERS:
        db.upsert_customer(slug, display)

    # Wipe existing seeded notes so re-running is idempotent
    with db.connect() as conn:
        conn.execute("DELETE FROM notes")

    now = datetime.now(timezone.utc)
    with db.connect() as conn:
        for slug, kind, body, author, days_ago in SEED_NOTES:
            created = (now - timedelta(days=days_ago)).isoformat(sep=" ", timespec="seconds")
            conn.execute(
                "INSERT INTO notes(customer_slug, kind, body, author, channel, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (slug, kind, body, author, None, created),
            )

    print(f"Seeded {len(CUSTOMERS)} customers and {len(SEED_NOTES)} notes into {db.db_path()}")


if __name__ == "__main__":
    main()
