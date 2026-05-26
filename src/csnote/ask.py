"""LLM-powered Q&A over a customer's note history.

The whole point of routing notes through this bot rather than scattered Google
Docs is so they accumulate into a queryable context layer. ``/csnote ask``
loads everything we have on a customer and lets Claude answer questions about
it — "what's the status of their SSO rollout?", "have they complained about
exports before?", etc.

The system prompt is marked for caching because the same CSM may ask several
questions in a session — the per-question cost drops to just the new notes +
question after the first turn.
"""
from __future__ import annotations

import os

from anthropic import Anthropic

from .db import Note

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You answer questions about a single customer based only on
the customer-success notes provided below. Be concise and specific.

Rules:
- Cite dates when referencing a note (e.g. "on 2026-05-12, …").
- If the notes don't contain the answer, say so plainly. Do not speculate.
- Distinguish "notes" (general updates) from "todos" (action items) when relevant.
- Keep responses to a few sentences unless the user asks for more detail.

Formatting: the response will be posted to Slack. Use Slack's mrkdwn syntax,
NOT standard Markdown — that means *single asterisks* for bold (never **double**),
_underscores_ for italic, and `backticks` for code/identifiers.
"""


def _format_notes(notes: list[Note]) -> str:
    if not notes:
        return "(no notes on file)"
    lines = []
    # Render oldest-first for natural narrative flow.
    for note in reversed(notes):
        date = note.created_at.strftime("%Y-%m-%d")
        kind = "TODO" if note.kind == "todo" else "NOTE"
        done = " [done]" if note.kind == "todo" and note.done else ""
        lines.append(f"[{date}] {kind}{done} by {note.author}: {note.body}")
    return "\n".join(lines)


def ask(customer_display: str, notes: list[Note], question: str) -> str:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    context = (
        f"Customer: {customer_display}\n"
        f"Notes ({len(notes)} entries, oldest first):\n\n"
        f"{_format_notes(notes)}"
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=[
            {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": context, "cache_control": {"type": "ephemeral"}},
        ],
        messages=[{"role": "user", "content": question}],
    )

    return "".join(block.text for block in response.content if block.type == "text").strip()
