"""Resolve the target customer from a slash-command invocation.

Order of precedence:
1. Explicit ``customer <slug>`` prefix in the command text.
2. Channel name → customer slug (strip optional ``-channel`` suffix and look
   up in the ``customers`` table).
"""
from __future__ import annotations

from dataclasses import dataclass

from . import db


@dataclass
class Resolved:
    slug: str
    display_name: str
    remaining_text: str


@dataclass
class Unresolved:
    reason: str


Resolution = Resolved | Unresolved


def _strip_channel_suffix(channel_name: str) -> str:
    if channel_name.endswith("-channel"):
        return channel_name[: -len("-channel")]
    return channel_name


def resolve(channel_name: str | None, tokens: list[str]) -> Resolution:
    # 1. Explicit override
    if len(tokens) >= 2 and tokens[0].lower() == "customer":
        slug = tokens[1].lower()
        display = db.lookup_customer(slug)
        if display is None:
            return Unresolved(
                reason=f"I don't have a customer with slug `{slug}`. "
                f"Known customers: {', '.join(db.list_customer_slugs()) or '(none)'}."
            )
        return Resolved(slug=slug, display_name=display, remaining_text=" ".join(tokens[2:]))

    # 2. Channel-based resolution
    if channel_name:
        slug = _strip_channel_suffix(channel_name).lower()
        display = db.lookup_customer(slug)
        if display is not None:
            return Resolved(slug=slug, display_name=display, remaining_text=" ".join(tokens))

    return Unresolved(
        reason="I couldn't figure out which customer this is for. Use it inside a "
        "customer channel, or prefix with `customer <slug>`."
    )
