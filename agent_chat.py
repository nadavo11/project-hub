"""Private, durable agent threads. Shared workspace content is never agent input."""

from contextlib import contextmanager
import hashlib
import hmac
import json
import os
import re
from pathlib import Path
import secrets
import sqlite3
import time
import uuid


class AgentConflict(ValueError):
    pass


STATUS_LINE = re.compile(r"^\s*TASK_STATUS:\s*(DONE|NEEDS_INPUT|IN_PROGRESS)\s*$", re.M)


class AgentStore:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.path = self.directory / "agents.sqlite3"
        self.key_path = self.directory / "operator.key"
        try:
            fd = os.open(self.key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, "w") as stream:
                stream.write(secrets.token_urlsafe(48) + "\n")
        self.key = self.key_path.read_text().strip()
        if len(self.key) < 32:
            raise RuntimeError("Invalid operator key; refusing to enable agent access.")
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS threads (
                    id INTEGER PRIMARY KEY, channel INTEGER NOT NULL, title TEXT NOT NULL,
                    session_id TEXT NOT NULL UNIQUE, closed INTEGER NOT NULL DEFAULT 0,
                    created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY, thread INTEGER NOT NULL REFERENCES threads(id),
                    role TEXT NOT NULL, text TEXT NOT NULL, created REAL NOT NULL,
                    nonce TEXT UNIQUE, job INTEGER);
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY, thread INTEGER NOT NULL REFERENCES threads(id),
                    message INTEGER NOT NULL UNIQUE REFERENCES messages(id),
                    status TEXT NOT NULL, created REAL NOT NULL, finished REAL,
                    error TEXT NOT NULL DEFAULT '');
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY, thread INTEGER NOT NULL REFERENCES threads(id),
                    job INTEGER NOT NULL REFERENCES jobs(id), kind TEXT NOT NULL,
                    text TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS task_links (
                    task INTEGER PRIMARY KEY, thread INTEGER NOT NULL REFERENCES threads(id),
                    outcome TEXT NOT NULL DEFAULT 'working', applied INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS service (
                    id INTEGER PRIMARY KEY CHECK(id=1), heartbeat REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS messages_thread ON messages(thread, id);
                CREATE INDEX IF NOT EXISTS jobs_status ON jobs(status, id);
                CREATE INDEX IF NOT EXISTS events_thread ON events(thread, id);
            """)
        os.chmod(self.path, 0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    @contextmanager
    def transaction(self):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            yield db

    def authenticate(self, key):
        return isinstance(key, str) and hmac.compare_digest(key.encode(), self.key.encode())

    def cookie(self):
        payload = f"{int(time.time() + 12 * 3600)}.{secrets.token_hex(16)}"
        signature = hmac.new(self.key.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return payload + "." + signature

    def valid_cookie(self, value):
        try:
            payload, signature = value.rsplit(".", 1)
            expiry, _nonce = payload.split(".")
            expected = hmac.new(self.key.encode(), payload.encode(), hashlib.sha256).hexdigest()
            return int(expiry) > time.time() and hmac.compare_digest(signature, expected)
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def string(body, key, limit):
        value = body.get(key) if isinstance(body, dict) else None
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError(f"{key} must contain 1 to {limit} characters.")
        return value.strip()

    @staticmethod
    def _thread(db, thread_id):
        row = db.execute("SELECT * FROM threads WHERE id=?", (thread_id,)).fetchone()
        if not row:
            raise ValueError("Thread not found.")
        return dict(row)

    @staticmethod
    def _event(db, job, kind, text):
        db.execute(
            "INSERT INTO events(thread,job,kind,text,created) VALUES(?,?,?,?,?)",
            (job["thread"], job["id"], kind, text, time.time()),
        )

    @staticmethod
    def _cancel(db, where, params, reason):
        jobs = db.execute(
            f"SELECT * FROM jobs WHERE {where} AND status IN ('queued','running')", params
        ).fetchall()
        for job in jobs:
            status = "cancelling" if job["status"] == "running" else "cancelled"
            db.execute("UPDATE jobs SET status=?,error=? WHERE id=?", (status, reason, job["id"]))
            AgentStore._event(db, job, "status", reason)

    def set_enabled(self, channel, enabled):
        if type(enabled) is not bool:
            raise ValueError("enabled must be true or false.")
        with self.transaction() as db:
            db.execute(
                "INSERT INTO channels(id,enabled) VALUES(?,?) "
                "ON CONFLICT(id) DO UPDATE SET enabled=excluded.enabled", (channel, enabled),
            )
            if not enabled:
                self._cancel(db, "thread IN (SELECT id FROM threads WHERE channel=?)",
                             (channel,), "AI disabled. Pending requests cancelled; running work is stopping.")
        return {"enabled": enabled}

    def reconcile_channels(self, ids):
        with self.connect() as db:
            stale = [row["id"] for row in db.execute("SELECT id FROM channels WHERE enabled=1")
                     if row["id"] not in ids]
        for channel in stale:
            self.set_enabled(channel, False)

    def channel(self, channel):
        with self.connect() as db:
            row = db.execute("SELECT enabled FROM channels WHERE id=?", (channel,)).fetchone()
            threads = db.execute("""
                SELECT t.*, COALESCE((SELECT status FROM jobs WHERE thread=t.id
                    ORDER BY id DESC LIMIT 1), 'idle') AS status
                FROM threads t WHERE channel=? ORDER BY id DESC
            """, (channel,)).fetchall()
            beat = db.execute("SELECT heartbeat FROM service WHERE id=1").fetchone()
            return {
                "enabled": bool(row and row["enabled"]),
                "online": bool(beat and time.time() - beat["heartbeat"] < 15),
                "threads": [dict(row) for row in threads],
            }

    def create_thread(self, channel, body):
        title = self.string(body, "title", 120)
        with self.transaction() as db:
            if db.execute("SELECT count(*) FROM threads WHERE channel=?", (channel,)).fetchone()[0] >= 500:
                raise ValueError("This channel has reached its 500-thread limit.")
            cursor = db.execute(
                "INSERT INTO threads(channel,title,session_id,created) VALUES(?,?,?,?)",
                (channel, title, str(uuid.uuid4()), time.time()),
            )
            return self._thread(db, cursor.lastrowid)

    def thread(self, thread_id, before=None):
        with self.connect() as db:
            thread = self._thread(db, thread_id)
            messages = db.execute("SELECT * FROM messages WHERE thread=? ORDER BY id", (thread_id,))
            bound = before or 2**63 - 1
            events = list(db.execute(
                "SELECT * FROM events WHERE thread=? AND id<? ORDER BY id DESC LIMIT 201",
                (thread_id, bound),
            ))
            return {
                "thread": thread, "messages": [dict(row) for row in messages],
                "events": [dict(row) for row in reversed(events[:200])],
                "has_older_events": len(events) > 200,
                "jobs": [dict(row) for row in db.execute(
                    "SELECT * FROM jobs WHERE thread=? ORDER BY id", (thread_id,)
                )],
            }

    def set_closed(self, thread_id, closed):
        if type(closed) is not bool:
            raise ValueError("closed must be true or false.")
        with self.transaction() as db:
            self._thread(db, thread_id)
            db.execute("UPDATE threads SET closed=? WHERE id=?", (closed, thread_id))
            if closed:
                self._cancel(db, "thread=?", (thread_id,), "Thread closed. Stopping pending work.")
        return {"closed": closed}

    def submit(self, thread_id, body):
        content = self.string(body, "text", 16000)
        nonce = self.string(body, "nonce", 100)
        with self.transaction() as db:
            previous = db.execute("SELECT * FROM messages WHERE nonce=?", (nonce,)).fetchone()
            if previous:
                if previous["thread"] != thread_id or previous["text"] != content:
                    raise AgentConflict("This request ID was already used for a different message.")
                return dict(previous)
            thread = self._thread(db, thread_id)
            channel = db.execute("SELECT enabled FROM channels WHERE id=?", (thread["channel"],)).fetchone()
            if thread["closed"] or not channel or not channel["enabled"]:
                raise AgentConflict("Enable AI and reopen this thread before sending.")
            if db.execute("SELECT count(*) FROM messages WHERE thread=?", (thread_id,)).fetchone()[0] >= 1000:
                raise ValueError("This thread is full. Start a new thread.")
            cursor = db.execute(
                "INSERT INTO messages(thread,role,text,created,nonce) VALUES(?,?,?,?,?)",
                (thread_id, "user", content, time.time(), nonce),
            )
            message_id = cursor.lastrowid
            job = db.execute(
                "INSERT INTO jobs(thread,message,status,created) VALUES(?,?,'queued',?)",
                (thread_id, message_id, time.time()),
            ).lastrowid
            db.execute("UPDATE messages SET job=? WHERE id=?", (job, message_id))
            return dict(db.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone())

    def start_task(self, task, channel, title, text):
        """Open (or reuse) the one dedicated thread for a task and queue its first request."""
        with self.transaction() as db:
            enabled = db.execute("SELECT enabled FROM channels WHERE id=?", (channel,)).fetchone()
            if not enabled or not enabled["enabled"]:
                raise AgentConflict("Turn on AI in this channel's Agent chat first.")
            link = db.execute("SELECT * FROM task_links WHERE task=?", (task,)).fetchone()
            if link:
                thread = self._thread(db, link["thread"])
                active = db.execute(
                    "SELECT 1 FROM jobs WHERE thread=? AND status IN ('queued','running','cancelling')",
                    (thread["id"],)).fetchone()
                if active or (not thread["closed"] and link["outcome"] == "needs_input"):
                    return {"thread": thread["id"], "channel": thread["channel"], "reused": True}
            if db.execute("SELECT count(*) FROM threads WHERE channel=?", (channel,)).fetchone()[0] >= 500:
                raise ValueError("This channel has reached its 500-thread limit.")
            thread_id = db.execute(
                "INSERT INTO threads(channel,title,session_id,created) VALUES(?,?,?,?)",
                (channel, title[:120], str(uuid.uuid4()), time.time()),
            ).lastrowid
            message = db.execute(
                "INSERT INTO messages(thread,role,text,created,nonce) VALUES(?,'user',?,?,?)",
                (thread_id, text[:16000], time.time(), str(uuid.uuid4())),
            ).lastrowid
            job = db.execute(
                "INSERT INTO jobs(thread,message,status,created) VALUES(?,?,'queued',?)",
                (thread_id, message, time.time()),
            ).lastrowid
            db.execute("UPDATE messages SET job=? WHERE id=?", (job, message))
            db.execute(
                "INSERT INTO task_links(task,thread,outcome,applied) VALUES(?,?,'working',0) "
                "ON CONFLICT(task) DO UPDATE SET thread=excluded.thread,outcome='working',applied=0",
                (task, thread_id),
            )
            return {"thread": thread_id, "channel": channel, "reused": False}

    def task_states(self):
        with self.connect() as db:
            rows = db.execute("""
                SELECT l.task, l.thread, l.outcome, l.applied, t.channel, t.closed,
                    EXISTS (SELECT 1 FROM jobs j WHERE j.thread=l.thread
                        AND j.status IN ('queued','running','cancelling')) AS active
                FROM task_links l JOIN threads t ON t.id=l.thread
            """).fetchall()
            return {
                row["task"]: {
                    "thread": row["thread"], "channel": row["channel"],
                    "state": "working" if row["active"] else row["outcome"],
                    "pending": row["outcome"] == "done" and not row["applied"],
                } for row in rows
            }

    def mark_applied(self, task):
        with self.connect() as db:
            db.execute("UPDATE task_links SET applied=1 WHERE task=? AND outcome='done'", (task,))

    def hosting_channel(self, valid):
        with self.connect() as db:
            for row in db.execute("SELECT id FROM channels WHERE enabled=1 ORDER BY id"):
                if row["id"] in valid:
                    return row["id"]
        return None

    def claim(self):
        with self.transaction() as db:
            job = db.execute("""
                SELECT j.*, t.session_id, t.title, t.channel, m.text
                FROM jobs j JOIN threads t ON t.id=j.thread
                JOIN channels c ON c.id=t.channel JOIN messages m ON m.id=j.message
                WHERE j.status='queued' AND c.enabled=1 AND t.closed=0
                AND NOT EXISTS (SELECT 1 FROM jobs active WHERE active.thread=j.thread
                    AND active.status IN ('running','cancelling'))
                ORDER BY j.id LIMIT 1
            """).fetchone()
            if not job:
                return None
            db.execute("UPDATE jobs SET status='running' WHERE id=?", (job["id"],))
            self._event(db, job, "status", "Matched to Copilot session " + job["session_id"])
            return dict(job)

    def cancelled(self, job_id):
        with self.connect() as db:
            row = db.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
            return not row or row["status"] != "running"

    def stop(self, thread_id):
        with self.transaction() as db:
            self._thread(db, thread_id)
            self._cancel(db, "thread=?", (thread_id,), "Stop requested. Changes already made are not undone.")
        return {"ok": True}

    def event(self, job, kind, text):
        if not text:
            return
        if len(text) > 16000:
            text = text[:16000] + "\n[Report truncated; full details remain in the Copilot session.]"
        # Never echo the operator credential even if a command prints it.
        text = text.replace(self.key, "[operator key redacted]")
        with self.connect() as db:
            self._event(db, job, kind, text)

    def finish(self, job, status, response="", error=""):
        error = error.replace(self.key, "[operator key redacted]")[:16000]
        with self.transaction() as db:
            current = db.execute("SELECT status FROM jobs WHERE id=?", (job["id"],)).fetchone()
            if not current or current["status"] not in ("running", "cancelling"):
                return
            if current["status"] == "cancelling":
                status, response = "cancelled", ""
                error = "Stopped. Review activity before continuing; prior changes are not undone."
            db.execute("UPDATE jobs SET status=?,finished=?,error=? WHERE id=?",
                       (status, time.time(), error, job["id"]))
            link = db.execute("SELECT task FROM task_links WHERE thread=?", (job["thread"],)).fetchone()
            if link:
                found = STATUS_LINE.findall(response)
                outcome = "needs_input" if status == "done" else "failed" if status == "failed" else "stopped"
                if status == "done" and found and found[-1] == "DONE":
                    outcome = "done"
                elif status == "done" and found and found[-1] == "IN_PROGRESS":
                    outcome = "working"
                db.execute("UPDATE task_links SET outcome=?,applied=0 WHERE task=?", (outcome, link["task"]))
                response = STATUS_LINE.sub("", response).rstrip()
            if response:
                response = response.replace(self.key, "[operator key redacted]")
                if len(response) > 64000:
                    response = response[:64000] + "\n[Reply truncated; see Copilot session.]"
                db.execute(
                    "INSERT INTO messages(thread,role,text,created,job) VALUES(?,'assistant',?,?,?)",
                    (job["thread"], response, time.time(), job["id"]),
                )
            self._event(db, job, "status", error or "Completed.")
            if status != "done":
                self._cancel(db, "thread=?", (job["thread"],),
                             "Not run after an interrupted or failed turn. Review activity and send a new request.")

    def recover(self):
        with self.transaction() as db:
            for job in db.execute("SELECT * FROM jobs WHERE status IN ('running','cancelling')").fetchall():
                reason = "Coordinator restarted during this turn. Not replayed: review activity before continuing."
                db.execute("UPDATE jobs SET status='interrupted',finished=?,error=? WHERE id=?",
                           (time.time(), reason, job["id"]))
                self._event(db, job, "status", reason)
                self._cancel(db, "thread=?", (job["thread"],), reason)

    def heartbeat(self):
        with self.connect() as db:
            db.execute("INSERT INTO service(id,heartbeat) VALUES(1,?) "
                       "ON CONFLICT(id) DO UPDATE SET heartbeat=excluded.heartbeat", (time.time(),))

    def summary(self):
        with self.connect() as db:
            return {
                "channels": [dict(row) for row in db.execute("SELECT * FROM channels")],
                "threads": [dict(row) for row in db.execute("SELECT * FROM threads")],
                "jobs": [dict(row) for row in db.execute(
                    "SELECT id,thread,status,error FROM jobs ORDER BY id DESC LIMIT 30"
                )],
            }


if __name__ == "__main__":
    store = AgentStore(Path(__file__).parent / "data/agents")
    print(json.dumps(store.summary(), indent=2))
