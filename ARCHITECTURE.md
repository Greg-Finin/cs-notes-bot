# Architecture

## Intended deployment shape

```
   ┌────────────────────┐
   │  Slack workspace   │
   │  /csnote slash cmd │
   └─────────┬──────────┘
             │ Socket Mode (WebSocket out)
             ▼
   ┌────────────────────┐         ┌──────────────────┐
   │   Bolt app         │────────▶│   Anthropic API  │
   │  (container task)  │◀────────│   (/csnote ask)  │
   └─────────┬──────────┘         └──────────────────┘
             │
             ▼
   ┌────────────────────┐
   │   Postgres         │
   └────────────────────┘
```

## Demo shape (this repo)

| Component | Real integration | Demo |
| --- | --- | --- |
| Slack | Real workspace, paid plan | Free workspace, same Socket Mode setup |
| Transport | Socket Mode | Socket Mode (same) |
| App runtime | Long-running container task | `python -m src.csnote.app` locally |
| Persistence | Postgres-compatible database | SQLite file (`csnotes.db`) |
| Seed data | Representative customer history | `scripts/seed_db.py` — 3 fictional customers, ~3 months of notes |

The application code is identical between the two paths — only the DB driver
and the deploy target differ.

## Why these choices

**Socket Mode** rather than HTTP endpoints with API Gateway: the bot is
workspace-only, never needs to be reachable from the public internet, and
Socket Mode means no inbound NAT/load balancer to maintain. Bolt opens the
WebSocket outbound, so a private container task works without any
ingress configuration.

**Channel-based customer resolution** rather than requiring an explicit
customer in every command: most notes are written in the customer's dedicated
Slack channel, so the channel name *is* the context. The explicit
`customer <slug>` override exists for the minority case of notes written in a
team-wide or cross-customer channel.

**LLM Q&A over the full note history** rather than just full-text search:
notes are short, contextual, and often reference team shorthand ("ENG-1421",
"the SSO rollout"). A keyword search misses the question *"what's the latest
on their SSO issues?"* unless someone literally wrote "SSO" in every note.
Claude resolves the references and produces a usable answer.

**SQLite for the demo, Postgres-compatible schema**: schema avoids
SQLite-specific column types and uses standard SQL idioms, so swapping to
`psycopg`/Postgres in a deployed environment is a connection-string change.
