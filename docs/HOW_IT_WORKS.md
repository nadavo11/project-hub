# How Project Hub works

## Overview

```
browser (static/*.js) ──HTTP/JSON──▶ server.py ──▶ data/workspace.json
                                        │
                                        └──▶ data/agents/agents.sqlite3 ◀── agent_worker.py ──▶ copilot CLI
```

One process (`server.py`, `ThreadingHTTPServer`) serves the static files and a JSON API. There is no framework and no build step.

## Workspace store

`Workspace` keeps everything in memory and persists to `data/workspace.json` with an atomic write (temp file + rename) and a `.bak` copy. Kinds: `channels`, `lists`, `chat`, `notes`, `todos`, `templates`, plus `trash`.

- Each item has `id`, `revision`, `updated`. Fields are validated against a table (`Workspace.FIELDS`) of type and maximum length — for example `icon` is a string of at most 8 characters (one emoji).
- **Optimistic concurrency:** `PATCH` with a `revision`; if it no longer matches the server returns `409` with the current item. Notes always require it. The UI keeps your draft and offers to review the newer version rather than overwriting.
- **Delete is soft:** the item (and children — a channel's messages, a list's tasks) moves to `trash` and can be restored.
- Every change runs in a transaction that rolls back in-memory state on failure.

## API (under `/api/workspace/`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `snapshot` | All current data, polled every 5 s and on tab focus |
| GET | `trash` | Deleted items |
| POST | `channels` `lists` `notes` `todos` `chat` `templates` | Create |
| PATCH | `<kind>/<id>` | Update (include `revision`) |
| DELETE | `<kind>/<id>` | Move to trash |
| POST | `create` | Create from a template (item plus children) |
| POST | `trash/<id>/restore` | Restore a deleted item |
| POST | `clear-completed` | Remove completed tasks of a list |

Also `GET /api/health` and `GET /api/projects`, `POST /api/projects/<id>/launch`.

## Frontend

`workspace.js` is a single IIFE. State `S` mirrors the snapshot; `render()` patches the DOM in place so focus and scroll survive polling. Drafts (chat text, unsent messages, note edits) are stored in `localStorage`, so a reload or an outage loses nothing. The emoji button (`withEmoji`) wraps any input/textarea; the icon square (`iconButton`) saves `icon` through the same `PATCH` flow (notes via autosave).

## Project launcher

Each card is a `ManagedApp`: it health-checks a local port, and on click starts the project (optionally via a systemd user unit), waits for it to be healthy, then returns its URL. It never stops a process it did not start.

## Private AI threads

`agent_chat.AgentStore` holds threads and messages in SQLite, unlocked by an operator key (cookie, `SameSite=Strict`). `agent_worker.py` is a separate service that claims queued jobs and runs the Copilot CLI per thread in its own process group, then posts the reply. A reply ending in `TASK_STATUS: DONE | NEEDS_INPUT | IN_PROGRESS` sets the thread state. Shared workspace content is never fed to agents.
