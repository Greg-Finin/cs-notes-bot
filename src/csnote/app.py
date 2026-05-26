"""Slack Bolt app — /csnote slash command.

Subcommands (parsed from the message text):
  /csnote <text>                       — save a note for the current channel's customer
  /csnote customer <slug> <text>       — save a note for an explicit customer
  /csnote todo <text>                  — save a todo (same resolution rules)
  /csnote todo customer <slug> <text>
  /csnote ask <question>               — Claude reads recent notes and answers
  /csnote ask customer <slug> <question>
  /csnote recent                       — list recent notes for the channel's customer
  /csnote recent customer <slug>
"""
from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from . import ask as ask_mod
from . import db
from .resolver import Resolved, Unresolved, resolve

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("csnote")

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

SUBCOMMANDS = {"todo", "ask", "recent"}


def _format_recent(notes) -> str:
    if not notes:
        return "_No notes on file._"
    lines = []
    for n in notes:
        if n.kind == "todo":
            marker = ":white_check_mark:" if n.done else ":pushpin:"
        else:
            marker = ":memo:"
        date = n.created_at.strftime("%Y-%m-%d")
        lines.append(f"{marker} *{date}* — {n.body}  _({n.author})_")
    return "\n".join(lines)


@app.command("/csnote")
def handle_csnote(ack, command, respond):
    ack()
    text = (command.get("text") or "").strip()
    channel_name = command.get("channel_name")
    user_name = command.get("user_name", "unknown")
    channel_id = command.get("channel_id")

    tokens = text.split()
    subcmd = tokens[0].lower() if tokens and tokens[0].lower() in SUBCOMMANDS else "note"
    if subcmd in SUBCOMMANDS:
        tokens = tokens[1:]

    resolution = resolve(channel_name, tokens)
    if isinstance(resolution, Unresolved):
        respond({"response_type": "ephemeral", "text": resolution.reason})
        return

    assert isinstance(resolution, Resolved)
    body = resolution.remaining_text.strip()

    if subcmd in ("note", "todo"):
        if not body:
            respond({"response_type": "ephemeral", "text": f"_(missing {subcmd} text)_"})
            return
        note_id = db.insert_note(
            customer_slug=resolution.slug,
            kind="todo" if subcmd == "todo" else "note",
            body=body,
            author=user_name,
            channel=channel_id,
        )
        marker = ":pushpin: *Todo*" if subcmd == "todo" else ":memo: *Note*"
        respond(
            {
                "response_type": "in_channel",
                "text": (
                    f"{marker} for *{resolution.display_name}* — _@{user_name}_  "
                    f"`#{note_id}`\n> {body}"
                ),
            }
        )
        return

    if subcmd == "recent":
        notes = db.recent_notes(resolution.slug, limit=5)
        respond(
            {
                "response_type": "in_channel",
                "text": (
                    f":books: *Recent notes — {resolution.display_name}*  "
                    f"_(requested by @{user_name})_\n{_format_recent(notes)}"
                ),
            }
        )
        return

    if subcmd == "ask":
        if not body:
            respond({"response_type": "ephemeral", "text": "_(ask what?)_"})
            return
        notes = db.all_notes_for_ask(resolution.slug)
        try:
            answer = ask_mod.ask(resolution.display_name, notes, body)
        except Exception as e:  # noqa: BLE001
            log.exception("ask failed")
            respond({"response_type": "ephemeral", "text": f":warning: ask failed: {e}"})
            return
        respond(
            {
                "response_type": "in_channel",
                "text": (
                    f":mag: _@{user_name} asked about *{resolution.display_name}*_\n"
                    f"*Q:* {body}\n*A:* {answer}"
                ),
            }
        )
        return


def main() -> None:
    db.init_db()
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    log.info("csnote bot starting (socket mode)")
    handler.start()


if __name__ == "__main__":
    main()
