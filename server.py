#!/usr/bin/env python3
"""A loopback-only landing page and allowlisted launcher for local projects."""

import argparse
from contextlib import contextmanager
from copy import deepcopy
import json
import mimetypes
import os
from pathlib import Path
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import CookieError, SimpleCookie
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import ProxyHandler, build_opener

from agent_chat import AgentConflict, AgentStore


ROOT = Path(__file__).resolve().parent
HOME = Path.home()
PRIOR_ART_ROOT = HOME / "Documents/prior-art"
PRIOR_ART = PRIOR_ART_ROOT / "visual-localization-review.html"
LOCALIZATION = HOME / "localization-models"
SAMPLE4GEO = HOME / "sample4geo-atlas"
VIDEO_AGENTS = (
    HOME
    / ".copilot/session-state/0bf05d14-ae18-4935-a27f-f7e87de03910"
    / "files/project/video-agents"
)
HTTP = build_opener(ProxyHandler({}))
BIND_HOST = os.environ.get("PROJECT_HUB_HOST", "0.0.0.0")


def local_names():
    names = {socket.gethostname(), socket.getfqdn()}
    try:
        out = subprocess.run(
            ["hostname", "-I"], capture_output=True, text=True, timeout=5
        ).stdout
        names.update(out.split())
    except (OSError, subprocess.SubprocessError):
        pass
    return sorted(n for n in names if n)


class LaunchError(Exception):
    pass


class ManagedApp:
    def __init__(
        self, project, app_id, name, description, port, health_path, signature
    ):
        self.project = Path(project)
        self.app_id = app_id
        self.name = name
        self.description = description
        self.health_path = health_path
        self.signature = signature
        self.port = port
        self.url = f"http://127.0.0.1:{port}/"
        self.lock = threading.Lock()
        self.state = "stopped"
        self.message = "Starts automatically when you open this project."
        self.process = None
        self.closed = False
        self.worker = None
        self.logs = ROOT / "logs"

    def healthy(self):
        try:
            with HTTP.open(self.url + self.health_path, timeout=1) as response:
                data = json.load(response)
            return isinstance(data, dict) and all(
                data.get(key) == value for key, value in self.signature.items()
            )
        except (OSError, ValueError, HTTPError, URLError):
            return False

    def port_busy(self):
        try:
            with socket.create_connection(("127.0.0.1", self.port), timeout=0.5):
                return True
        except OSError:
            return False

    def status(self):
        ready = self.healthy()
        with self.lock:
            state, message = self.state, self.message
            if ready:
                state, message = "ready", "Running and ready to open."
            elif state == "ready":
                state, message = (
                    "stopped",
                    "Starts automatically when you open this project.",
                )
            if not self.project.is_dir():
                state, message = "unavailable", f"Project not found at {self.project}."
        return {
            "id": self.app_id,
            "name": self.name,
            "description": self.description,
            "state": state,
            "message": message,
            "url": self.url if state == "ready" else None,
        }

    def launch(self):
        with self.lock:
            if self.closed:
                raise LaunchError("The dashboard is shutting down.")
            if self.state == "starting":
                return {"state": "starting", "url": None, "message": self.message}
            if self.healthy():
                self.state = "ready"
                return {"state": "ready", "url": self.url, "message": "Ready to open."}
            if not self.project.is_dir():
                raise LaunchError(f"Project not found at {self.project}.")
            if self.port_busy():
                raise LaunchError(
                    f"Port {self.port} is used by another service. "
                    "No existing process was stopped."
                )
            self.state = "starting"
            self.message = f"Preparing {self.name}..."
            self.worker = threading.Thread(target=self._start, daemon=True)
            self.worker.start()
            return {"state": "starting", "url": None, "message": self.message}

    def _spawn(self, command, log, env):
        with self.lock:
            if self.closed:
                raise LaunchError("The dashboard is shutting down.")
            self.process = subprocess.Popen(
                command,
                cwd=self.project,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            return self.process

    def _start(self):
        process = None
        try:
            self.logs.mkdir(exist_ok=True, mode=0o700)
            log_path = self.logs / f"{self.app_id}.log"
            if log_path.exists() and log_path.stat().st_size > 1_000_000:
                log_path.replace(self.logs / f"{self.app_id}.previous.log")
            env = dict(os.environ, PYTHONUNBUFFERED="1")
            if self.app_id == "localization":
                env["DRONE_LOC_HOME"] = str(self.project / "data/workbench")
                env["DRONE_LOC_HOST"] = BIND_HOST
                env["DRONE_LOC_ALLOWED_HOSTS"] = ",".join(
                    ["127.0.0.1", "localhost", "testserver", *local_names()]
                )
            with log_path.open("ab") as log:
                for command in self.setup_commands():
                    with self.lock:
                        self.message = "First-time setup is running. Downloads may take several minutes."
                    process = self._spawn(command, log, env)
                    try:
                        result = process.wait(timeout=1200)
                    except subprocess.TimeoutExpired:
                        raise LaunchError(
                            "First-time setup timed out. You can retry."
                        ) from None
                    if result:
                        raise LaunchError(
                            "First-time setup failed. See the local project log."
                        )
                with self.lock:
                    self.message = (
                        "Starting the project. It will open as soon as it is ready."
                    )
                process = self._spawn(
                    self.start_command(),
                    log,
                    env,
                )
                deadline = time.monotonic() + 120
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise LaunchError(
                            "Project startup failed. See the local project log."
                        )
                    if self.healthy():
                        with self.lock:
                            self.state = "ready"
                            self.message = "Running and ready to open."
                        return
                    if self.closed:
                        return
                    time.sleep(0.5)
                raise LaunchError(
                    "The project did not become ready in time. You can retry."
                )
        except (OSError, LaunchError, subprocess.SubprocessError) as error:
            self._stop_process(process)
            with self.lock:
                self.state = "error"
                self.message = f"{error} Log: {self.logs / (self.app_id + '.log')}"

    def setup_commands(self):
        python = self.project / ".venv/bin/python"
        needs_setup = (
            not python.is_file()
            or not (self.project / "apps/web/dist/index.html").is_file()
        )
        if not needs_setup:
            result = subprocess.run(
                [
                    str(python),
                    "-c",
                    "import fastapi, uvicorn, numpy, pyarrow, pydantic, yaml, PIL, multipart",
                ],
                cwd=self.project,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=60,
            )
            needs_setup = result.returncode != 0
        if needs_setup:
            bootstrap = self.project / "scripts/bootstrap.sh"
            if not bootstrap.is_file():
                raise LaunchError("The project's setup script is missing.")
            return [["bash", str(bootstrap)]]
        return []

    def start_command(self):
        return [
            str(self.project / ".venv/bin/python"),
            "-m",
            "drone_loc.cli",
            "--home",
            str(self.project / "data/workbench"),
            "serve",
            "--port",
            str(self.port),
        ]

    @staticmethod
    def _stop_process(process):
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    def close(self):
        with self.lock:
            self.closed = True
            process = self.process
        self._stop_process(process)


class Launcher:
    def __init__(
        self,
        project=LOCALIZATION,
        prior_art=PRIOR_ART,
        port=8010,
        video_project=VIDEO_AGENTS,
        prior_art_root=PRIOR_ART_ROOT,
        sample4geo_project=SAMPLE4GEO,
    ):
        self.prior_art = Path(prior_art)
        self.prior_art_root = Path(prior_art_root)
        self.apps = {
            "localization": ManagedApp(
                project,
                "localization",
                "Localization",
                "Open the localization workbench, datasets, and experiments.",
                port,
                "api/health",
                {"status": "ok", "research_only": True},
            ),
            "video-agents": VideoApp(
                video_project,
                "video-agents",
                "Video Agents",
                "Investigate video with visual search, evidence, and agent workflows.",
                8000,
                "openapi.json",
                {},
            ),
            "sample4geo": Sample4GeoApp(
                sample4geo_project,
                "sample4geo",
                "Sample4Geo Atlas",
                "Explore drone-to-satellite retrieval, image representations, and benchmarks.",
                8025,
                "openapi.json",
                {"info": {"title": "Sample4Geo Atlas", "version": "1.0.0"}},
            ),
            "crossview": CrossviewApp(
                project,
                "crossview",
                "Drone & Aerial Explorer",
                "Switch UAV datasets, search full reference maps, and inspect matches, landmarks and model evidence.",
                8012,
                "api/health",
                {"status": "ok", "research_only": True},
            ),
        }

    def projects(self):
        prior_ready = (
            self.prior_art.is_file() and (self.prior_art_root / "index.html").is_file()
        )
        return [
            {
                "id": "prior-art",
                "name": "Prior Art",
                "description": "Fine localization and coarse geo-localization: both research slideshows.",
                "state": "ready" if prior_ready else "unavailable",
                "message": "Two research presentations - ready to read."
                if prior_ready
                else "The research library files could not be found.",
                "url": "/prior-art/",
            },
            *(app.status() for app in self.apps.values()),
        ]

    def launch(self, project_id):
        if project_id == "prior-art":
            if (
                not self.prior_art.is_file()
                or not (self.prior_art_root / "index.html").is_file()
            ):
                raise LaunchError("The research review file could not be found.")
            return {
                "state": "ready",
                "url": "/prior-art/",
                "message": "Ready to read.",
            }
        if project_id not in self.apps:
            raise LaunchError("This project is not connected yet.")
        return self.apps[project_id].launch()

    def close(self):
        for app in self.apps.values():
            app.close()


class VideoApp(ManagedApp):
    def healthy(self):
        try:
            with HTTP.open(self.url + "openapi.json", timeout=1) as response:
                data = json.load(response)
            return (
                isinstance(data, dict)
                and isinstance(data.get("info"), dict)
                and data["info"].get("title") == "Video Reflexion Agent"
                and "/api/config" in data.get("paths", {})
                and "/api/investigations" in data.get("paths", {})
            )
        except (OSError, ValueError, HTTPError, URLError):
            return False

    def setup_commands(self):
        python = self.project / ".venv/bin/python"
        requirements = self.project / "requirements-vision.txt"
        if not requirements.is_file():
            raise LaunchError("The video's dependency manifest is missing.")
        install = [str(python), "-m", "pip", "install", "-r", str(requirements)]
        if not python.is_file():
            return [[sys.executable, "-m", "venv", ".venv"], install]
        result = subprocess.run(
            [
                str(python),
                "-c",
                "import fastapi, uvicorn, PIL, cv2, numpy, sklearn, av, torch, transformers",
            ],
            cwd=self.project,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60,
        )
        return [install] if result.returncode else []

    def start_command(self):
        return [
            str(self.project / ".venv/bin/python"),
            "-m",
            "uvicorn",
            "app:app",
            "--host",
            BIND_HOST,
            "--port",
            str(self.port),
        ]


class SystemdApp(ManagedApp):
    service_name = ""

    def _start(self):
        try:
            with self.lock:
                self.message = f"Starting {self.name}..."
            subprocess.run(
                ["systemctl", "--user", "start", self.service_name],
                check=True,
                timeout=60,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                if self.closed:
                    return
                if self.healthy():
                    with self.lock:
                        self.state = "ready"
                        self.message = "Interface ready. Model and gallery readiness are shown inside."
                    return
                time.sleep(0.5)
            raise LaunchError("The interface did not become ready in time.")
        except (OSError, LaunchError, subprocess.SubprocessError):
            with self.lock:
                self.state = "error"
                self.message = (
                    f"{self.name} could not start. Retry, or inspect its service log: "
                    f"journalctl --user -u {self.service_name}"
                )


class Sample4GeoApp(SystemdApp):
    service_name = "sample4geo-atlas.service"


class CrossviewApp(SystemdApp):
    service_name = "atlas-crossview.service"


def task_request(task, lst, siblings):
    """Fixed template so every AI-complete thread starts with the same context and rules."""
    others = "\n".join(
        f"- [{'x' if item['done'] else ' '}] {item['text'][:120]}" for item in siblings if item["id"] != task["id"]
    ) or "- (none)"
    return f"""AI-COMPLETE TASK #{task['id']}

TASK
{task['text']}

CONTEXT
- List: {lst['name'] if lst else 'Unknown'}
- Priority: {'starred (high)' if task.get('starred') else 'normal'}
- Other tasks in this list (context only, do not work on them):
{others}

HOW THIS WORKS (follow exactly)
1. This thread is the dedicated discussion for this one task. The operator reads everything you write here.
2. First reply: a short plan (3-6 bullets), then start working immediately.
3. Keep going until the task is fully complete and verified. Do not stop at partial progress.
4. If you are blocked or need a decision, ask ONE clear question and stop with TASK_STATUS: NEEDS_INPUT. The operator will answer in this thread.
5. Do not tick the task yourself. The hub ticks it automatically when your final line is TASK_STATUS: DONE.

FINAL REPORT TEMPLATE (use for every final reply)
## Task #{task['id']}: <task text>
**Status:** Done | Needs your input
**Summary:** <1-3 sentences>
**Changes:** <files, commands, or "none">
**Verification:** <how you confirmed it works>
**Open risks:** <or "none">
TASK_STATUS: DONE | NEEDS_INPUT | IN_PROGRESS

The last line must be exactly one of those TASK_STATUS values. Use DONE only when finished and verified.
"""


class WorkspaceConflict(ValueError):
    def __init__(self, message, current=None):
        super().__init__(message)
        self.current = current


class Workspace:
    """Revisioned shared content, with atomic writes and recoverable deletion."""

    # field -> (type, max length); the first field of REQUIRED is mandatory on create.
    FIELDS = {
        "channels": {"name": (str, 60), "icon": (str, 8)},
        "lists": {"name": (str, 100), "icon": (str, 8)},
        "chat": {"author": (str, 40), "text": (str, 4000), "channel": (int, 0)},
        "notes": {
            "title": (str, 200),
            "body": (str, 50000),
            "icon": (str, 8),
            "pinned": (bool, 0),
        },
        "todos": {
            "text": (str, 500),
            "done": (bool, 0),
            "starred": (bool, 0),
            "list": (int, 0),
        },
        "templates": {
            "name": (str, 200),
            "kind": (str, 10),
            "icon": (str, 8),
            "body": (str, 50000),
            "intro": (str, 4000),
            "items": (list, 200),
        },
    }
    REQUIRED = {
        "channels": "name",
        "lists": "name",
        "chat": "text",
        "notes": "title",
        "todos": "text",
        "templates": "name",
    }
    KINDS = tuple(FIELDS)
    MAX_ITEMS = 5000

    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()
        self.data = {kind: [] for kind in (*self.KINDS, "trash")}
        loaded = {}
        existed = False
        try:
            loaded = json.loads(self.path.read_text())
            existed = True
            if not isinstance(loaded, dict):
                raise ValueError("Expected a workspace object.")
            for kind in self.KINDS:
                items = loaded.get(kind, [])
                if not isinstance(items, list):
                    raise ValueError(f"Invalid {kind} collection.")
                for item in items:
                    self._validate_stored_item(kind, item)
                self.data[kind] = items
            trash = loaded.get("trash", [])
            if not isinstance(trash, list):
                raise ValueError("Invalid trash collection.")
            for entry in trash:
                if (
                    not isinstance(entry, dict)
                    or type(entry.get("id")) is not int
                    or entry.get("kind") not in self.KINDS
                    or not isinstance(entry.get("items"), dict)
                    or not isinstance(entry.get("label"), str)
                    or not isinstance(entry.get("ts"), (int, float))
                ):
                    raise ValueError("Invalid trash entry.")
                if not entry["items"].get(entry["kind"]):
                    raise ValueError("Missing deleted item.")
                for kind, items in entry["items"].items():
                    if kind not in self.KINDS or not isinstance(items, list):
                        raise ValueError("Invalid deleted content.")
                    for item in items:
                        self._validate_stored_item(kind, item)
            self.data["trash"] = trash
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError) as error:
            raise RuntimeError(
                f"Workspace could not be loaded: {self.path}. "
                f"The original file was preserved. Check {self.path}.bak "
                "before restoring a backup."
            ) from error
        ids = [i["id"] for items in self.data.values() for i in items]
        for entry in self.data["trash"]:
            ids.extend(i["id"] for items in entry["items"].values() for i in items)
        saved_next = loaded.get("_next_id", loaded.get("next_id", 1))
        if type(saved_next) is not int or saved_next < 1:
            raise RuntimeError("Invalid workspace ID counter. Original file preserved.")
        self.next_id = max([saved_next, *[i + 1 for i in ids]])
        original = deepcopy(self.data)
        if not existed or "channels" not in loaded:
            self._make("channels", name="General", icon="💬")
        if not existed or "lists" not in loaded:
            self._make("lists", name="My tasks", icon="✅")
        for kind, parent, field in (
            ("chat", "channels", "channel"), ("todos", "lists", "list")
        ):
            for item in self.data[kind]:
                if field not in item:
                    if not self.data[parent]:
                        raise RuntimeError("Orphaned content. Original file preserved.")
                    item[field] = self.data[parent][0]["id"]
        for kind in self.KINDS:
            for item in self.data[kind]:
                item.setdefault("revision", 1)
        if not existed or self.data != original or "_next_id" not in loaded:
            self._save()

    def _validate_stored_item(self, kind, item):
        if (
            not isinstance(item, dict)
            or type(item.get("id")) is not int
            or item["id"] < 1
            or not isinstance(item.get("ts"), (int, float))
            or type(item.get("revision", 1)) is not int
            or item.get("revision", 1) < 1
        ):
            raise ValueError("Invalid workspace item.")
        self._clean(kind, item, False)

    def _make(self, collection, **fields):
        if len(self.data[collection]) >= self.MAX_ITEMS:
            raise ValueError("This collection is full. Move unused items to Trash first.")
        item = {"id": self.next_id, "ts": time.time(), "revision": 1, **fields}
        self.next_id += 1
        self.data[collection].append(item)
        return item

    @contextmanager
    def _transaction(self):
        with self.lock:
            previous, counter = deepcopy(self.data), self.next_id
            try:
                yield
                if previous != self.data or counter != self.next_id:
                    self._save()
            except BaseException:
                self.data, self.next_id = previous, counter
                raise

    @staticmethod
    def _atomic_write(path, content):
        fd, name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def _save(self):
        self.path.parent.mkdir(exist_ok=True, mode=0o700)
        content = json.dumps({**self.data, "_next_id": self.next_id}).encode()
        if self.path.exists():
            self._atomic_write(Path(str(self.path) + ".bak"), self.path.read_bytes())
        self._atomic_write(self.path, content)

    def _clean(self, kind, body, partial):
        if not isinstance(body, dict):
            raise ValueError("Expected a JSON object.")
        clean = {}
        for key, (kind_type, limit) in self.FIELDS[kind].items():
            if key not in body:
                continue
            value = body[key]
            if kind_type is bool:
                if not isinstance(value, bool):
                    raise ValueError(f"{key} must be true or false.")
            elif kind_type is int:
                if not isinstance(value, int) or isinstance(value, bool):
                    raise ValueError(f"{key} must be a number.")
            elif kind_type is list:
                if not isinstance(value, list) or len(value) > limit:
                    raise ValueError(f"{key} must contain at most {limit} tasks.")
                if any(
                    not isinstance(text, str) or not text.strip() or len(text) > 500
                    for text in value
                ):
                    raise ValueError("Every template task must contain 1 to 500 characters.")
                value = [text.strip() for text in value]
            elif not isinstance(value, str) or len(value) > limit:
                raise ValueError(f"{key} must be text of at most {limit} characters.")
            elif key != "body":
                value = value.strip()
            clean[key] = value
        required = self.REQUIRED[kind]
        if (not partial and not clean.get(required)) or (
            partial and required in clean and not clean[required]
        ):
            raise ValueError(f"{required} is required.")
        if kind == "templates":
            template_kind = clean.get("kind")
            if (not partial or "kind" in clean) and template_kind not in (
                "chat", "notes", "todos"
            ):
                raise ValueError("Choose a chat, notes, or todos template.")
        return clean

    def list(self, kind, since=0):
        with self.lock:
            return deepcopy([i for i in self.data[kind] if i["id"] > since])

    def snapshot(self):
        with self.lock:
            return deepcopy({
                **{kind: self.data[kind] for kind in self.KINDS},
                "trash": [
                    {key: entry[key] for key in ("id", "kind", "label", "ts")}
                    for entry in self.data["trash"]
                ],
            })

    def _ids(self, kind):
        return {i["id"] for i in self.data[kind]}

    def _check_refs(self, kind, clean):
        for field, target in (("chat", "channels"), ("todos", "lists")):
            ref = "channel" if kind == "chat" else "list"
            if kind == field and ref in clean and clean[ref] not in self._ids(target):
                raise ValueError(f"Unknown {ref}.")

    def add(self, kind, body):
        clean = self._clean(kind, body, False)
        with self._transaction():
            if kind == "chat":
                clean.setdefault("channel", self.data["channels"][0]["id"] if self.data["channels"] else 0)
                clean["author"] = clean.get("author") or "Anonymous"
            if kind == "todos":
                clean.setdefault("list", self.data["lists"][0]["id"] if self.data["lists"] else 0)
                clean.setdefault("done", False)
            if kind == "notes":
                clean.setdefault("body", "")
            self._check_refs(kind, clean)
            item = self._make(kind, **clean)
            return deepcopy(item)

    def create(self, body):
        """Create a template's parent and children in one durable transaction."""
        template = self._clean("templates", body, False)
        kind = template["kind"]
        parent_kind = {"chat": "channels", "notes": "notes", "todos": "lists"}[kind]
        fields = {
            "title" if kind == "notes" else "name": template["name"],
            "icon": template.get("icon", ""),
        }
        if kind == "notes":
            fields["body"] = template.get("body", "")
        fields = self._clean(parent_kind, fields, False)
        with self._transaction():
            item = self._make(parent_kind, **fields)
            children = []
            if kind == "todos":
                for text in template.get("items", []):
                    children.append(self._make(
                        "todos", text=text, list=item["id"], done=False, starred=False
                    ))
            elif kind == "chat" and template.get("intro", "").strip():
                children.append(self._make(
                    "chat", channel=item["id"], author="Project Hub",
                    text=template["intro"].strip(),
                ))
            return deepcopy({"kind": parent_kind, "item": item, "children": children})

    def update(self, kind, item_id, body):
        clean = self._clean(kind, body, True)
        with self._transaction():
            self._check_refs(kind, clean)
            for item in self.data[kind]:
                if item["id"] == item_id:
                    revision = body.get("revision")
                    if revision is not None and type(revision) is not int:
                        raise ValueError("revision must be an integer.")
                    if (kind == "notes" or revision is not None) and revision != item["revision"]:
                        raise WorkspaceConflict(
                            "This item changed. Review the latest version before saving.",
                            deepcopy(item),
                        )
                    item.update(clean)
                    item["updated"] = time.time()
                    item["revision"] += 1
                    return deepcopy(item)
        return None

    def delete(self, kind, item_id):
        with self._transaction():
            item = next((i for i in self.data[kind] if i["id"] == item_id), None)
            if item is None:
                return None
            deleted = {kind: [item]}
            self.data[kind] = [i for i in self.data[kind] if i["id"] != item_id]
            child, field = {"channels": ("chat", "channel"), "lists": ("todos", "list")}.get(
                kind, (None, None)
            )
            if child:
                deleted[child] = [i for i in self.data[child] if i[field] == item_id]
                self.data[child] = [i for i in self.data[child] if i[field] != item_id]
            entry = {
                "id": self.next_id, "kind": kind, "label": item[self.REQUIRED[kind]],
                "ts": time.time(), "items": deleted,
            }
            self.next_id += 1
            self.data["trash"].append(entry)
            return {"ok": True, "undo_id": entry["id"]}

    def restore(self, undo_id):
        with self._transaction():
            entry = next((i for i in self.data["trash"] if i["id"] == undo_id), None)
            if entry is None:
                return None
            for kind, items in entry["items"].items():
                if len(self.data[kind]) + len(items) > self.MAX_ITEMS:
                    raise ValueError("Not enough room to restore this item.")
                for item in items:
                    self._check_refs_for_restore(kind, item, entry)
                    restored = deepcopy(item)
                    restored["revision"] = restored.get("revision", 1) + 1
                    restored["updated"] = time.time()
                    self.data[kind].append(restored)
            self.data["trash"] = [i for i in self.data["trash"] if i["id"] != undo_id]
            parent_id = entry["items"][entry["kind"]][0]["id"]
            restored = next(i for i in self.data[entry["kind"]] if i["id"] == parent_id)
            return deepcopy({"ok": True, "kind": entry["kind"], "item": restored})

    def clear_completed(self, body):
        if not isinstance(body, dict) or type(body.get("list")) is not int:
            raise ValueError("Choose a task list.")
        list_id = body["list"]
        with self._transaction():
            if list_id not in self._ids("lists"):
                raise ValueError("This task list no longer exists.")
            completed = [
                i for i in self.data["todos"] if i["list"] == list_id and i.get("done")
            ]
            if not completed:
                return {"ok": True, "count": 0}
            ids = {i["id"] for i in completed}
            self.data["todos"] = [i for i in self.data["todos"] if i["id"] not in ids]
            entry = {
                "id": self.next_id, "kind": "todos",
                "label": f"{len(completed)} completed tasks", "ts": time.time(),
                "items": {"todos": completed},
            }
            self.next_id += 1
            self.data["trash"].append(entry)
            return {"ok": True, "undo_id": entry["id"], "count": len(completed)}

    def _check_refs_for_restore(self, kind, item, entry):
        for child, parent, field in (
            ("chat", "channels", "channel"), ("todos", "lists", "list")
        ):
            if kind == child:
                available = self._ids(parent) | {
                    i["id"] for i in entry["items"].get(parent, [])
                }
                if item[field] not in available:
                    raise WorkspaceConflict(
                        "Restore the containing channel or task list first."
                    )


class HubServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, launcher, workspace=None):
        super().__init__(address, Handler)
        self.launcher = launcher
        self.workspace = workspace or Workspace(ROOT / "data/workspace.json")
        self.agents = AgentStore(self.workspace.path.parent / "agents")
        self.agent_login_lock = threading.Lock()
        self.agent_login_failures = {}


class Handler(BaseHTTPRequestHandler):
    def _allowed_host(self):
        port = self.server.server_port
        host = self.headers.get("Host") or ""
        name, _, host_port = host.rpartition(":")
        allowed = {"127.0.0.1", "localhost", *local_names()}
        return host_port == str(port) and name.strip("[]") in allowed

    def _send(self, status, content, content_type="application/json", headers=None):
        body = (
            json.dumps(content).encode()
            if content_type == "application/json" and not isinstance(content, bytes)
            else content
        )
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if not self._allowed_host():
            self._send(403, {"error": "Only local dashboard addresses are allowed."})
            return
        path = urlsplit(self.path).path
        if self._agent_route("GET"):
            return
        if path == "/api/health":
            self._send(200, {"status": "ok", "app": "project-hub"})
        elif path == "/api/projects":
            self._send(200, {"projects": self.server.launcher.projects()})
        elif path == "/api/workspace/snapshot":
            try:
                ai_tasks = self._sync_ai_tasks()
            except sqlite3.Error:
                ai_tasks = {}
            try:
                chat_states = {str(k): v for k, v in self.server.agents.indicators().items()}
            except sqlite3.Error:
                chat_states = {}
            self._send(200, {**self.server.workspace.snapshot(), "ai_tasks": ai_tasks, "chat_states": chat_states})
        elif path == "/api/workspace/trash":
            self._send(200, {"items": self.server.workspace.snapshot()["trash"]})
        elif path.startswith("/api/workspace/"):
            parts = path.strip("/").split("/")
            kind = parts[-1]
            if len(parts) != 3 or kind not in Workspace.KINDS:
                self._send(404, {"error": "Not found."})
                return
            try:
                since = int(parse_qs(urlsplit(self.path).query).get("since", ["0"])[0])
            except ValueError:
                since = 0
            items = self.server.workspace.list(kind, since if kind == "chat" else 0)
            self._send(200, {"items": items})
        else:
            files = {
                "/": (ROOT / "static/index.html", "text/html; charset=utf-8"),
                "/app.js": (ROOT / "static/app.js", "text/javascript; charset=utf-8"),
                "/workspace.js": (
                    ROOT / "static/workspace.js",
                    "text/javascript; charset=utf-8",
                ),
                "/markdown.js": (
                    ROOT / "static/markdown.js", "text/javascript; charset=utf-8",
                ),
                "/agent-chat.js": (
                    ROOT / "static/agent-chat.js", "text/javascript; charset=utf-8",
                ),
                "/styles.css": (ROOT / "static/styles.css", "text/css; charset=utf-8"),
                "/agent-chat.css": (ROOT / "static/agent-chat.css", "text/css; charset=utf-8"),
                "/prior-art/": (
                    self.server.launcher.prior_art_root / "index.html",
                    "text/html; charset=utf-8",
                ),
                "/prior-art/visual-localization-review.html": (
                    self.server.launcher.prior_art,
                    "text/html; charset=utf-8",
                ),
            }
            survey = (
                self.server.launcher.prior_art_root / "coarse-geo-localization-survey"
            )
            prefix = "/prior-art/coarse-geo-localization-survey/"
            files[prefix] = (survey / "index.html", "text/html; charset=utf-8")
            public_files = [
                survey / name
                for name in (
                    "index.html",
                    "coarse-geo-localization-survey.html",
                    "research-appendix.html",
                    "benchmarks.csv",
                    "evidence.json",
                    "survey-context.json",
                    "diagram-index.json",
                    "slide-manifest.json",
                )
            ]
            public_files.extend(
                file
                for file in (survey / "assets").rglob("*")
                if file.is_file()
                and file.suffix in {".svg", ".jpg", ".css", ".js", ".txt", ".json"}
            )
            for file in public_files:
                if not file.resolve().is_relative_to(survey.resolve()):
                    continue
                content_type = (
                    mimetypes.guess_type(file.name)[0] or "application/octet-stream"
                )
                files[prefix + file.relative_to(survey).as_posix()] = (
                    file,
                    content_type + "; charset=utf-8"
                    if content_type.startswith("text/")
                    else content_type,
                )
            if path not in files:
                self._send(404, {"error": "Not found."})
                return
            file, content_type = files[path]
            try:
                self._send(200, file.read_bytes(), content_type)
            except OSError:
                self._send(404, {"error": "The requested file is unavailable."})

    def _guard_write(self):
        origin = self.headers.get("Origin")
        expected_origin = f"http://{self.headers.get('Host')}"
        if not self._allowed_host() or origin != expected_origin:
            self._send(
                403, {"error": "Requests must come from the local dashboard."}
            )
            return False
        return True

    def _json_body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length < 0 or length > 1_000_000:
                self.close_connection = True
                raise ValueError
            return json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return None

    def _agent_authenticated(self):
        bearer = self.headers.get("Authorization", "")
        if bearer.startswith("Bearer ") and self.server.agents.authenticate(bearer[7:]):
            return True
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
            return self.server.agents.valid_cookie(cookie["hub_operator"].value)
        except (KeyError, ValueError, CookieError):
            return False

    def _sync_ai_tasks(self):
        """Tick tasks whose agent reported DONE; the hub server is the only workspace writer."""
        states = self.server.agents.task_states()
        for task_id, state in states.items():
            if state["pending"]:
                try:
                    self.server.workspace.update("todos", task_id, {"done": True})
                except ValueError:
                    pass
                self.server.agents.mark_applied(task_id)
        ids = {row["id"] for row in self.server.workspace.list("todos")}
        return {
            str(task): {key: state[key] for key in ("thread", "channel", "state")}
            for task, state in states.items() if task in ids
        }

    def _agent_route(self, method):
        parts = urlsplit(self.path).path.strip("/").split("/")
        if parts[:2] != ["api", "agents"]:
            return False
        store = self.server.agents
        try:
            if parts == ["api", "agents", "session"]:
                if method == "GET":
                    self._send(200, {"authenticated": self._agent_authenticated()})
                    return True
                if method == "DELETE":
                    self._send(200, {"ok": True}, headers={
                        "Set-Cookie": "hub_operator=; Path=/api/agents; HttpOnly; SameSite=Strict; Max-Age=0",
                    })
                    return True
                if method == "POST":
                    body = self._json_body()
                    peer = self.client_address[0]
                    with self.server.agent_login_lock:
                        failures = self.server.agent_login_failures
                        now = time.time()
                        for address in list(failures):
                            if now - failures[address][1] > 60:
                                del failures[address]
                        count, _ = failures.get(peer, (0, now))
                        if count >= 5:
                            self._send(429, {"error": "Too many unlock attempts. Wait one minute."})
                            return True
                        if not isinstance(body, dict) or not store.authenticate(body.get("key")):
                            if len(failures) < 1000 or peer in failures:
                                failures[peer] = (count + 1, now)
                            self._send(401, {"error": "Incorrect operator key."})
                            return True
                        failures.pop(peer, None)
                    self._send(200, {"authenticated": True}, headers={
                        "Set-Cookie": "hub_operator=" + store.cookie()
                        + "; Path=/api/agents; HttpOnly; SameSite=Strict; Max-Age=43200",
                    })
                    return True
            if not self._agent_authenticated():
                self._send(401, {"error": "Unlock Agent chat with the operator key first."})
                return True
            if len(parts) < 4 or not parts[3].isdigit():
                self._send(404, {"error": "Not found."})
                return True
            item_id = int(parts[3])
            if parts[2] == "tasks" and parts[4:] == ["ai-complete"] and method == "POST":
                workspace = self.server.workspace
                task = next((row for row in workspace.list("todos") if row["id"] == item_id), None)
                if not task:
                    self._send(404, {"error": "Task not found."})
                    return True
                if task.get("done"):
                    self._send(400, {"error": "This task is already complete. Reopen it to use AI complete."})
                    return True
                channel = store.hosting_channel({row["id"] for row in workspace.list("channels")})
                if channel is None:
                    self._send(409, {"error": "Turn on AI in a channel's Agent chat first (the heart channel)."})
                    return True
                lst = next((row for row in workspace.list("lists") if row["id"] == task["list"]), None)
                siblings = [row for row in workspace.list("todos") if row["list"] == task["list"]][:20]
                title = "✨ Task: " + task["text"]
                self._send(200, store.start_task(item_id, channel, title, task_request(task, lst, siblings)))
                return True
            if parts[2] == "channels":
                if item_id not in {row["id"] for row in self.server.workspace.list("channels")}:
                    self._send(404, {"error": "Channel not found."})
                    return True
                if len(parts) == 4 and method == "GET":
                    self._send(200, store.channel(item_id))
                    return True
                if len(parts) == 4 and method == "PATCH":
                    body = self._json_body()
                    self._send(200, store.set_enabled(item_id, (body or {}).get("enabled")))
                    return True
                if parts[4:] == ["threads"] and method == "POST":
                    self._send(201, store.create_thread(item_id, self._json_body()))
                    return True
            if parts[2] == "threads":
                if len(parts) == 4 and method == "GET":
                    before = parse_qs(urlsplit(self.path).query).get("before", [None])[0]
                    self._send(200, store.thread(item_id, int(before) if before else None))
                    return True
                if len(parts) == 4 and method == "PATCH":
                    body = self._json_body() or {}
                    if "archived" in body:
                        self._send(200, store.set_archived(item_id, body["archived"]))
                    else:
                        self._send(200, store.set_closed(item_id, body.get("closed")))
                    return True
                if parts[4:] == ["messages"] and method == "POST":
                    self._send(201, store.submit(item_id, self._json_body()))
                    return True
                if parts[4:] == ["stop"] and method == "POST":
                    self._send(200, store.stop(item_id))
                    return True
            self._send(404, {"error": "Not found."})
        except AgentConflict as error:
            self._send(409, {"error": str(error)})
        except (ValueError, TypeError, AttributeError) as error:
            self._send(400, {"error": str(error)})
        except (OSError, sqlite3.Error):
            self._send(503, {"error": "Agent storage unavailable. Your request was not confirmed."})
        return True

    def _workspace_route(self, method):
        parts = urlsplit(self.path).path.strip("/").split("/")
        if len(parts) < 3 or parts[:2] != ["api", "workspace"]:
            return False
        try:
            return self._workspace_write(parts, method)
        except WorkspaceConflict as error:
            self._send(409, {"error": str(error), "current": error.current})
        except ValueError as error:
            self._send(400, {"error": str(error)})
        except OSError:
            self.log_error("Workspace write failed; retaining unsaved changes in client.")
            self._send(503, {
                "error": "The server could not save this change. Your draft is not saved. Retry."
            })
        return True

    def _workspace_write(self, parts, method):
        workspace = self.server.workspace
        kind = parts[2]
        if kind == "create" and len(parts) == 3 and method == "POST":
            self._send(201, workspace.create(self._json_body()))
            return True
        if kind == "clear-completed" and len(parts) == 3 and method == "POST":
            self._send(200, workspace.clear_completed(self._json_body()))
            return True
        if (
            kind == "trash" and len(parts) == 5 and parts[3].isdigit()
            and parts[4] == "restore" and method == "POST"
        ):
            result = workspace.restore(int(parts[3]))
            self._send(200 if result else 404, result or {"error": "Item not found in Trash."})
            return True
        if kind not in Workspace.KINDS:
            self._send(404, {"error": "Not found."})
            return True
        item_id = None
        if len(parts) == 4 and parts[3].isdigit():
            item_id = int(parts[3])
        elif len(parts) != 3:
            self._send(404, {"error": "Not found."})
            return True
        if (method == "POST") != (item_id is None):
            self._send(405, {"error": "Method not allowed."})
            return True
        if method == "DELETE":
            if kind == "channels":
                self.server.agents.set_enabled(item_id, False)
            result = workspace.delete(kind, item_id)
            self._send(200 if result else 404, result or {"error": "Item not found."})
            return True
        body = self._json_body()
        if body is None:
            self._send(400, {"error": "Invalid JSON."})
            return True
        item = (
            workspace.add(kind, body)
            if method == "POST"
            else workspace.update(kind, item_id, body)
        )
        if item is None:
            self._send(404, {"error": "Not found."})
        else:
            if kind == "todos" and method != "POST" and isinstance(body.get("done"), bool):
                self.server.agents.archive_for_task(item_id, body["done"])
            self._send(201 if method == "POST" else 200, item)
        return True

    def do_PATCH(self):
        if self._guard_write():
            if self._agent_route("PATCH"):
                return
            if not self._workspace_route("PATCH"):
                self._send(404, {"error": "Not found."})

    def do_DELETE(self):
        if self._guard_write():
            if self._agent_route("DELETE"):
                return
            if not self._workspace_route("DELETE"):
                self._send(404, {"error": "Not found."})

    def do_POST(self):
        if not self._guard_write():
            return
        if self._agent_route("POST"):
            return
        if self._workspace_route("POST"):
            return
        path = urlsplit(self.path).path
        routes = {
            f"/api/projects/{key}/launch": key
            for key in ("prior-art", *self.server.launcher.apps)
        }
        if path not in routes:
            self._send(404, {"error": "Unknown project."})
            return
        try:
            result = self.server.launcher.launch(routes[path])
            self._send(202, result)
        except LaunchError as error:
            self._send(409, {"error": str(error)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    launcher = Launcher()
    server = HubServer((BIND_HOST, args.port), launcher)

    def stop(_signum, _frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print(f"Project Hub: http://127.0.0.1:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    finally:
        launcher.close()
        server.server_close()


if __name__ == "__main__":
    main()
