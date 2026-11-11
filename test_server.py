import http.client
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from server import (
    HubServer, Launcher, LaunchError, ManagedApp, VideoApp, Workspace, WorkspaceConflict,
)


def unused_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.app = ManagedApp(
            self.root,
            "test",
            "Test app",
            "Isolated test service",
            unused_port(),
            "health.json",
            {"app": "test", "status": "ok"},
        )
        self.app.logs = self.root / "logs"
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.app.close)

    def test_reuses_existing_service_without_owning_or_stopping_it(self):
        with patch.object(self.app, "healthy", return_value=True):
            self.assertEqual(self.app.launch()["state"], "ready")
            self.assertIsNone(self.app.process)
            self.app.close()
            self.assertIsNone(self.app.process)

    def test_duplicate_launches_share_one_startup(self):
        release = threading.Event()
        with (
            patch.object(self.app, "healthy", return_value=False),
            patch.object(self.app, "port_busy", return_value=False),
            patch.object(
                self.app, "_start", side_effect=lambda: release.wait(3)
            ) as start,
        ):
            try:
                self.assertEqual(self.app.launch()["state"], "starting")
                worker = self.app.worker
                self.assertEqual(self.app.launch()["state"], "starting")
                self.assertIs(self.app.worker, worker)
            finally:
                release.set()
                self.app.worker.join(3)
            start.assert_called_once()

    def test_port_conflict_and_missing_project_are_not_launched(self):
        with (
            patch.object(self.app, "healthy", return_value=False),
            patch.object(self.app, "port_busy", return_value=True),
        ):
            with self.assertRaisesRegex(LaunchError, "another service"):
                self.app.launch()
            self.app.project = self.root / "missing"
            with self.assertRaisesRegex(LaunchError, "not found"):
                self.app.launch()
            self.assertIsNone(self.app.worker)

    def test_cold_start_setup_readiness_retry_reuse_and_shutdown(self):
        setup = [
            sys.executable,
            "-c",
            "from pathlib import Path; "
            'Path(\'health.json\').write_text(\'{"app":"test","status":"ok"}\')',
        ]
        command = [
            sys.executable,
            "-m",
            "http.server",
            str(self.app.port),
            "--bind",
            "127.0.0.1",
        ]
        with (
            patch.object(self.app, "setup_commands", return_value=[setup]),
            patch.object(
                self.app,
                "start_command",
                return_value=["/nonexistent/project-hub-test"],
            ) as start,
        ):
            self.app.launch()
            self.app.worker.join(5)
            self.assertEqual(self.app.state, "error")
            start.return_value = command
            self.app.launch()
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and self.app.state == "starting":
                time.sleep(0.1)
            self.assertEqual(self.app.status()["state"], "ready", self.app.message)
            process = self.app.process
            self.assertEqual(self.app.launch()["state"], "ready")
            self.assertIs(self.app.process, process)
            self.app.close()
            self.assertIsNotNone(process.poll())

    def test_failed_dependency_probe_triggers_localization_bootstrap(self):
        python = self.root / ".venv/bin/python"
        python.parent.mkdir(parents=True)
        python.symlink_to(sys.executable)
        dist = self.root / "apps/web/dist/index.html"
        dist.parent.mkdir(parents=True)
        dist.touch()
        bootstrap = self.root / "scripts/bootstrap.sh"
        bootstrap.parent.mkdir()
        bootstrap.touch()
        with patch(
            "server.subprocess.run", return_value=subprocess.CompletedProcess([], 1)
        ):
            self.assertEqual(self.app.setup_commands(), [["bash", str(bootstrap)]])
        with patch(
            "server.subprocess.run", return_value=subprocess.CompletedProcess([], 0)
        ):
            self.assertEqual(self.app.setup_commands(), [])

    def test_video_missing_environment_has_automatic_setup(self):
        (self.root / "requirements-vision.txt").touch()
        app = VideoApp(self.root, "video-agents", "Video", "", 8000, "", {})
        commands = app.setup_commands()
        self.assertEqual(commands[0], [sys.executable, "-m", "venv", ".venv"])
        self.assertEqual(
            commands[1][-2:], ["-r", str(self.root / "requirements-vision.txt")]
        )


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "workspace.json"
        self.workspace = Workspace(self.path)

    def test_legacy_migration_preserves_content_and_backup(self):
        legacy = {
            "notes": [{"id": 7, "ts": 1, "title": "Research", "body": "Keep me"}],
            "chat": [{"id": 8, "ts": 2, "text": "Hi", "author": "Alex"}],
            "todos": [{"id": 9, "ts": 3, "text": "Read"}],
        }
        self.path.write_text(json.dumps(legacy))
        workspace = Workspace(self.path)
        self.assertEqual(workspace.list("notes")[0]["body"], "Keep me")
        self.assertEqual(workspace.list("notes")[0]["revision"], 1)
        self.assertEqual(
            workspace.list("chat")[0]["channel"], workspace.list("channels")[0]["id"]
        )
        self.assertEqual(json.loads(Path(str(self.path) + ".bak").read_text()), legacy)
        self.assertEqual(Workspace(self.path).snapshot(), workspace.snapshot())

    def test_corrupt_storage_is_not_replaced(self):
        for invalid in ('{"notes":[', '{"notes": "wrong"}', '{"notes":[{"id":1}]}'):
            with self.subTest(invalid=invalid):
                self.path.write_text(invalid)
                backup = Path(str(self.path) + ".bak")
                backup.write_text("recoverable backup")
                with self.assertRaises(RuntimeError):
                    Workspace(self.path)
                self.assertEqual(self.path.read_text(), invalid)
                self.assertEqual(backup.read_text(), "recoverable backup")

    def test_failed_write_rolls_back_memory_and_preserves_disk(self):
        note = self.workspace.add("notes", {"title": "Research", "body": "Original"})
        before = self.path.read_bytes()
        with patch.object(self.workspace, "_atomic_write", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.workspace.update(
                    "notes", note["id"], {"body": "Changed", "revision": note["revision"]}
                )
            with self.assertRaises(OSError):
                self.workspace.create({"kind": "todos", "name": "Checklist", "items": ["A", "B"]})
        self.assertEqual(self.workspace.list("notes")[0], note)
        self.assertEqual(len(self.workspace.list("lists")), 1)
        self.assertEqual(self.path.read_bytes(), before)

    def test_note_revision_prevents_stale_and_unversioned_overwrite(self):
        note = self.workspace.add("notes", {"title": "Research", "body": "Original"})
        changed = self.workspace.update(
            "notes", note["id"], {"body": "First editor", "revision": note["revision"]}
        )
        for payload in ({"body": "Second editor", "revision": note["revision"]},
                        {"body": "Old client"}):
            with self.assertRaises(WorkspaceConflict) as raised:
                self.workspace.update("notes", note["id"], payload)
            self.assertEqual(raised.exception.current, changed)
        self.assertEqual(Workspace(self.path).list("notes")[0]["body"], "First editor")

    def test_project_pairing_is_validated_and_survives_restart(self):
        legacy = self.workspace.add("lists", {"name": "Plain"})
        self.assertNotIn("project", legacy)
        for kind, name in (("lists", "name"), ("channels", "name"), ("notes", "title")):
            item = self.workspace.add(kind, {name: "Paired", "project": "sample4geo"})
            self.assertEqual(item["project"], "sample4geo")
            with self.assertRaises(ValueError):
                self.workspace.update(kind, item["id"], {"project": "../etc", "revision": item["revision"]})
        self.assertEqual(Workspace(self.path).list("lists")[-1]["project"], "sample4geo")

    def test_server_loads_custom_projects_before_workspace(self):
        root = Path(self.temp.name)
        data = root / "data"
        data.mkdir()
        path = data / "workspace.json"
        workspace = Workspace(path)
        workspace.add("channels", {"name": "Custom", "project": "sample4geo"})
        stored = json.loads(path.read_text())
        stored["channels"][0]["project"] = "test-custom"
        path.write_text(json.dumps(stored))
        (data / "projects.json").write_text(json.dumps([{
            "id": "test-custom", "name": "Test", "directory": str(root),
        }]))
        launcher = Launcher(
            project=root,
            prior_art=root / "review.html",
            video_project=root,
            prior_art_root=root,
            sample4geo_project=root,
        )
        server = None
        try:
            with patch("server.ROOT", root):
                server = HubServer(("127.0.0.1", 0), launcher)
            self.assertEqual(server.workspace.list("channels")[0]["project"], "test-custom")
        finally:
            if server:
                server.server_close()
            launcher.close()

    def test_template_creation_is_atomic_and_reusable(self):
        template = self.workspace.add("templates", {
            "kind": "todos", "name": "Review", "items": ["Read", "Summarize"],
        })
        created = self.workspace.create(template)
        self.assertEqual([i["text"] for i in created["children"]], ["Read", "Summarize"])
        self.assertTrue(all(i["list"] == created["item"]["id"] for i in created["children"]))
        before = self.workspace.snapshot()
        with patch.object(self.workspace, "MAX_ITEMS", 3):
            with self.assertRaises(ValueError):
                self.workspace.create({"kind": "todos", "name": "Too many", "items": ["A", "B"]})
        self.assertEqual(self.workspace.snapshot(), before)
        with self.assertRaises(ValueError):
            self.workspace.create({"kind": "chat", "name": "x" * 61})
        self.assertEqual(self.workspace.snapshot(), before)

    def test_trash_restores_parent_and_children_after_restart(self):
        created = self.workspace.create({
            "kind": "todos", "name": "Review", "items": ["Read", "Summarize"],
        })
        deletion = self.workspace.delete("lists", created["item"]["id"])
        self.assertFalse(self.workspace.list("todos"))
        workspace = Workspace(self.path)
        restored = workspace.restore(deletion["undo_id"])
        self.assertEqual(restored["item"]["id"], created["item"]["id"])
        self.assertEqual(len(workspace.list("todos")), 2)
        self.assertFalse(workspace.snapshot()["trash"])
        self.assertGreater(restored["item"]["revision"], created["item"]["revision"])
        self.assertIsNone(workspace.restore(deletion["undo_id"]))

    def test_restore_child_requires_parent_and_deleted_ids_are_not_reused(self):
        created = self.workspace.create({"kind": "chat", "name": "Review", "intro": "Hello"})
        message = created["children"][0]
        deleted_message = self.workspace.delete("chat", message["id"])
        deleted_channel = self.workspace.delete("channels", created["item"]["id"])
        workspace = Workspace(self.path)
        with self.assertRaises(WorkspaceConflict):
            workspace.restore(deleted_message["undo_id"])
        workspace.restore(deleted_channel["undo_id"])
        workspace.restore(deleted_message["undo_id"])
        new_note = workspace.add("notes", {"title": "New"})
        self.assertGreater(new_note["id"], deleted_channel["undo_id"])
        workspace.list("notes")[0]["title"] = "Client mutation"
        self.assertEqual(workspace.list("notes")[0]["title"], "New")

    def test_completed_tasks_clear_and_restore_as_one_operation(self):
        created = self.workspace.create({
            "kind": "todos", "name": "Review", "items": ["Read", "Summarize", "Publish"],
        })
        for task in created["children"][:2]:
            self.workspace.update("todos", task["id"], {"done": True})
        result = self.workspace.clear_completed({"list": created["item"]["id"]})
        self.assertEqual(result["count"], 2)
        self.assertEqual([i["text"] for i in self.workspace.list("todos")], ["Publish"])
        self.workspace.restore(result["undo_id"])
        self.assertEqual(len(self.workspace.list("todos")), 3)
        self.assertEqual(len(self.workspace.snapshot()["trash"]), 0)


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prior = self.root / "review.html"
        self.prior.write_text("<html><body>Research review</body></html>")
        (self.root / "index.html").write_text("<html>Both surveys</html>")
        survey = self.root / "coarse-geo-localization-survey"
        survey.mkdir()
        (survey / "index.html").write_text("<html>Coarse survey</html>")
        (survey / "research-appendix.html").write_text("<html>Sources</html>")
        (survey / "benchmarks.csv").write_text("Method,Metric\n")
        (survey / "evidence.json").write_text('{"methods": 13}')
        (survey / "assets").mkdir()
        (survey / "assets/diagram.svg").write_text("<svg></svg>")
        (survey / "build.py").write_text("private implementation")
        (survey / "assets/outside.txt").symlink_to(self.prior)
        self.launcher = Launcher(
            project=self.root,
            prior_art=self.prior,
            video_project=self.root,
            prior_art_root=self.root,
            sample4geo_project=self.root,
        )
        self.server = HubServer(
            ("127.0.0.1", 0), self.launcher, Workspace(self.root / "ws.json")
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_port
        self.host = f"127.0.0.1:{self.port}"
        self.addCleanup(self.cleanup)
        self.log_patch = patch("server.Handler.log_message")
        self.log_patch.start()

    def cleanup(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
        self.launcher.close()
        self.log_patch.stop()
        self.temp.cleanup()

    def request(self, path, method="GET", headers=None, body=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def test_only_allowlisted_files_are_served(self):
        for path in [
            "/",
            "/app.js",
            "/styles.css",
            "/prior-art/",
            "/prior-art/visual-localization-review.html",
            "/prior-art/coarse-geo-localization-survey/",
            "/prior-art/coarse-geo-localization-survey/research-appendix.html",
            "/prior-art/coarse-geo-localization-survey/benchmarks.csv",
            "/prior-art/coarse-geo-localization-survey/assets/diagram.svg",
        ]:
            with self.subTest(path=path):
                status, body = self.request(path)
                self.assertEqual(status, 200)
                self.assertTrue(body)
        for path in [
            "/server.py",
            "/.env",
            "/logs/localization.log",
            "/../server.py",
            "/%2e%2e/server.py",
            "/prior-art/coarse-geo-localization-survey/build.py",
            "/prior-art/coarse-geo-localization-survey/../index.html",
            "/prior-art/coarse-geo-localization-survey/assets/outside.txt",
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)

    def test_host_and_origin_validation_blocks_foreign_launches(self):
        self.assertEqual(self.request("/", headers={"Host": "attacker.test"})[0], 403)
        for headers in [
            {},
            {"Origin": "https://attacker.test"},
            {"Origin": f"http://{self.host}", "Host": "attacker.test"},
        ]:
            with self.subTest(headers=headers):
                self.assertEqual(
                    self.request("/api/projects/prior-art/launch", "POST", headers)[0],
                    403,
                )
        status, body = self.request(
            "/api/projects/prior-art/launch",
            "POST",
            {"Origin": f"http://{self.host}"},
        )
        self.assertEqual(status, 202)
        self.assertEqual(json.loads(body)["state"], "ready")
        self.assertEqual(json.loads(body)["url"], "/prior-art/")

    def test_workspace_crud_validation_and_persistence(self):
        origin = {"Origin": f"http://{self.host}"}

        def call(path, method="GET", payload=None, headers=origin):
            body = json.dumps(payload) if payload is not None else None
            status, data = self.request(path, method, headers, body)
            return status, json.loads(data)

        self.assertEqual(
            call("/api/workspace/todos", "POST", {"text": "x"}, {})[0], 403
        )
        _, channels = call("/api/workspace/channels")
        _, lists = call("/api/workspace/lists")
        self.assertEqual((len(channels["items"]), len(lists["items"])), (1, 1))
        general = channels["items"][0]["id"]
        status, todo = call("/api/workspace/todos", "POST", {"text": " Ship it "})
        self.assertEqual((status, todo["text"], todo["list"]), (201, "Ship it", lists["items"][0]["id"]))
        self.assertEqual(call("/api/workspace/todos", "POST", {"text": ""})[0], 400)
        self.assertEqual(call("/api/workspace/todos", "POST", {"text": 5})[0], 400)
        self.assertEqual(
            call("/api/workspace/todos", "POST", {"text": "a", "list": 999})[0], 400
        )
        _, todo = call(f"/api/workspace/todos/{todo['id']}", "PATCH", {"done": True, "starred": True})
        self.assertTrue(todo["done"] and todo["starred"])
        _, room = call("/api/workspace/channels", "POST", {"name": "Bugs", "icon": "🐞"})
        call("/api/workspace/chat", "POST", {"author": "", "text": "hi"})
        _, second = call(
            "/api/workspace/chat", "POST", {"author": "Ann", "text": "yo", "channel": room["id"]}
        )
        _, chat = call("/api/workspace/chat?since=" + str(second["id"] - 1))
        self.assertEqual([m["text"] for m in chat["items"]], ["yo"])
        call("/api/workspace/notes", "POST", {"title": "T", "body": "B", "pinned": True})
        reloaded = Workspace(self.root / "ws.json")
        self.assertEqual(reloaded.list("chat")[0]["author"], "Anonymous")
        self.assertEqual(reloaded.list("chat")[0]["channel"], general)
        self.assertEqual(len(reloaded.list("notes")), 1)
        self.assertEqual(call(f"/api/workspace/channels/{room['id']}", "DELETE")[0], 200)
        _, chat = call("/api/workspace/chat")
        self.assertEqual([m["text"] for m in chat["items"]], ["hi"])
        self.assertEqual(call(f"/api/workspace/todos/{todo['id']}", "DELETE")[0], 200)
        self.assertEqual(call(f"/api/workspace/todos/{todo['id']}", "DELETE")[0], 404)
        self.assertEqual(call("/api/workspace/bogus")[0], 404)

    def test_workspace_snapshot_conflicts_atomic_creation_and_restore_routes(self):
        headers = {"Origin": f"http://{self.host}", "Content-Type": "application/json"}

        def call(path, method="GET", body=None):
            status, data = self.request(
                "/api/workspace/" + path, method, headers,
                json.dumps(body) if body is not None else None,
            )
            return status, json.loads(data)

        status, created = call(
            "create", "POST", {"kind": "notes", "name": "Meeting", "body": "Original"}
        )
        self.assertEqual(status, 201)
        note = created["item"]
        path = f"notes/{note['id']}"
        status, changed = call(path, "PATCH", {"revision": 1, "body": "First editor"})
        self.assertEqual(status, 200)
        status, conflict = call(path, "PATCH", {"revision": 1, "body": "Second editor"})
        self.assertEqual(status, 409)
        self.assertEqual(conflict["current"], changed)
        with patch.object(self.server.workspace, "_save", side_effect=OSError):
            status, failure = call(path, "PATCH", {"revision": 2, "body": "Disk full"})
            self.assertEqual(status, 503)
            self.assertIn("not saved", failure["error"])
        status, deleted = call(path, "DELETE")
        self.assertEqual(status, 200)
        status, snapshot = call("snapshot")
        self.assertEqual(status, 200)
        self.assertFalse(snapshot["notes"])
        self.assertNotIn("items", snapshot["trash"][0])
        status, restored = call(f"trash/{deleted['undo_id']}/restore", "POST")
        self.assertEqual(status, 200)
        self.assertEqual(restored["item"]["body"], "First editor")
        self.assertEqual(call("extra/notes")[0], 404)

    def test_research_json_is_served_without_double_encoding(self):
        status, body = self.request(
            "/prior-art/coarse-geo-localization-survey/evidence.json"
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"methods": 13})

    def test_unknown_project_cannot_execute_commands(self):
        status, _ = self.request(
            "/api/projects/unknown/launch",
            "POST",
            {"Origin": f"http://{self.host}"},
        )
        self.assertEqual(status, 404)
        with self.assertRaises(LaunchError):
            self.launcher.launch("unknown")

    def test_sample4geo_launch_uses_existing_service_and_route(self):
        app = self.launcher.apps["sample4geo"]
        with patch.object(app, "healthy", return_value=True):
            status, body = self.request(
                "/api/projects/sample4geo/launch",
                "POST",
                {"Origin": f"http://{self.host}"},
            )
        self.assertEqual(status, 202)
        self.assertEqual(json.loads(body)["url"], "http://127.0.0.1:8025/")
        self.assertIsNone(app.process)

    def test_sample4geo_starts_service_and_allows_retry_after_failure(self):
        app = self.launcher.apps["sample4geo"]
        with (
            patch.object(app, "healthy", return_value=False),
            patch.object(app, "port_busy", return_value=False),
            patch("server.subprocess.run", side_effect=OSError("service failure")),
        ):
            app.launch()
            app.worker.join(3)
        self.assertEqual(app.state, "error")
        with (
            patch.object(app, "healthy", side_effect=[False, True]),
            patch.object(app, "port_busy", return_value=False),
            patch("server.subprocess.run") as run,
        ):
            app.launch()
            app.worker.join(3)
        self.assertEqual(app.state, "ready")
        self.assertEqual(
            run.call_args.args[0],
            ["systemctl", "--user", "start", "sample4geo-atlas.service"],
        )
        self.assertIsNone(app.process)
        app.close()
        self.assertEqual(run.call_count, 1)

    def test_crossview_launch_reuses_the_explorer_service(self):
        app = self.launcher.apps["crossview"]
        with patch.object(app, "healthy", return_value=True):
            status, body = self.request(
                "/api/projects/crossview/launch", "POST",
                {"Origin": f"http://{self.host}"},
            )
        self.assertEqual(status, 202)
        self.assertEqual(json.loads(body)["url"], "http://127.0.0.1:8012/")
        self.assertIsNone(app.process)

    def test_crossview_start_does_not_spawn_or_own_another_server(self):
        app = self.launcher.apps["crossview"]
        with (
            patch.object(app, "healthy", side_effect=[False, True]),
            patch.object(app, "port_busy", return_value=False),
            patch("server.subprocess.run") as run,
        ):
            app.launch()
            app.worker.join(3)
            self.assertEqual(app.state, "ready")
            self.assertEqual(
                run.call_args.args[0],
                ["systemctl", "--user", "start", "atlas-crossview.service"],
            )
            app.close()
            self.assertEqual(run.call_count, 1)
        self.assertIsNone(app.process)

    def test_missing_prior_art_reports_unavailable(self):
        self.prior.unlink()
        with (
            patch.object(
                self.launcher.apps["localization"], "healthy", return_value=False
            ),
            patch.object(
                self.launcher.apps["video-agents"], "healthy", return_value=False
            ),
            patch.object(
                self.launcher.apps["sample4geo"], "healthy", return_value=False
            ),
        ):
            status, body = self.request("/api/projects")
        self.assertEqual(status, 200)
        project = json.loads(body)["projects"][0]
        self.assertEqual(project["state"], "unavailable")
        status, _ = self.request(
            "/api/projects/prior-art/launch",
            "POST",
            {"Origin": f"http://{self.host}"},
        )
        self.assertEqual(status, 409)

    def test_issue_lifecycle_validation_and_persistence(self):
        headers = {"Origin": f"http://{self.host}", "Content-Type": "application/json"}

        def call(path, method="GET", body=None, head=headers):
            status, data = self.request(
                "/api/issues" + path, method, head,
                json.dumps(body) if body is not None else None,
            )
            return status, json.loads(data)

        actor = {"actor": "Dana"}
        self.assertEqual(call("", "POST", {"title": "x"}, {"Content-Type": "application/json"})[0], 403)
        self.assertEqual(call("", "POST", {"title": "  ", **actor})[0], 400)
        self.assertEqual(call("", "POST", {"title": "x"})[0], 400)
        self.assertEqual(call("", "POST", {"title": "x", "priority": "urgent", **actor})[0], 400)
        status, issue = call("", "POST", {
            "title": "Crash on save", "type": "bug", "priority": "high",
            "labels": ["ui", "UI", " "], **actor,
        })
        self.assertEqual((status, issue["number"], issue["reporter"]), (201, 1, "Dana"))
        self.assertEqual(issue["labels"], ["ui"])
        path = f"/{issue['number']}"
        status, moved = call(path, "PATCH", {"status": "in_progress", "assignee": "Sam", "rev": 1, **actor})
        self.assertEqual((status, moved["rev"], moved["closed_at"]), (200, 2, None))
        status, conflict = call(path, "PATCH", {"title": "Stale", "rev": 1, **actor})
        self.assertEqual((status, conflict["current"]["status"]), (409, "in_progress"))
        status, done = call(path, "PATCH", {"status": "done", **actor})
        self.assertTrue(done["closed_at"])
        status, reopened = call(path, "PATCH", {"status": "open", **actor})
        self.assertIsNone(reopened["closed_at"])
        status, comment = call(path + "/comments", "POST", {"text": "Repro attached", **actor})
        self.assertEqual(status, 201)
        self.assertEqual(call(path + "/comments", "POST", {"text": " ", **actor})[0], 400)
        status, edited = call(f"{path}/comments/{comment['id']}", "PATCH", {"text": "Fixed", **actor})
        self.assertTrue(edited["edited_at"])
        status, full = call(path)
        self.assertEqual(len(full["comments"]), 1)
        self.assertEqual(
            [entry["type"] for entry in full["activity"]],
            ["created", "status", "assignee", "status", "status"],
        )
        status, listing = call("")
        self.assertEqual(listing["issues"][0]["comment_count"], 1)
        self.assertNotIn("comments", listing["issues"][0])
        self.assertEqual(call(f"{path}/comments/{comment['id']}", "DELETE")[0], 200)
        self.assertEqual(call(f"{path}/comments/{comment['id']}", "DELETE")[0], 404)
        self.assertEqual(call("/99")[0], 404)
        self.assertEqual(call(path, "DELETE")[0], 200)
        self.assertEqual(call(path)[0], 404)
        self.assertEqual(call("", "POST", {"title": "Next", **actor})[1]["number"], 2)

    def test_ai_report_is_applied_to_its_issue(self):
        issue = self.server.issues.create({"title": "raw words", "body": "raw words", "labels": ["ai-triage"], "actor": "Dana"})
        report = 'Done.\n```issue-json\n{"title": "Crash on save", "body": "## Summary\\nx", "type": "bug", "priority": "high", "labels": ["ui"]}\n```'
        agents = self.server.agents
        state = {"thread": 7, "channel": 1, "state": "done", "pending": True, "agent": "0a1b2c3d"}
        with (
            patch.object(agents, "task_states", return_value={-issue["number"]: state}),
            patch.object(agents, "last_reply", return_value=report),
            patch.object(agents, "mark_applied") as applied,
        ):
            status, body = self.request("/api/issues")
        data = json.loads(body)
        self.assertEqual(status, 200)
        applied.assert_called_once_with(-issue["number"])
        self.assertEqual((data["issues"][0]["title"], data["issues"][0]["priority"]), ("Crash on save", "high"))
        self.assertEqual(data["issues"][0]["labels"], ["ui", "ai-triaged"])
        self.assertEqual(data["ai"]["1"]["thread"], 7)
        self.assertEqual(data["ai"]["1"]["agent"], "0a1b2c3d")
        self.assertEqual(self.server.issues.get(issue["number"])["activity"][-1]["actor"], "agent-0a1b2c3d")

    def test_ai_report_may_only_promote_to_in_review(self):
        from issues import parse_ai_report
        block = '```issue-json\n{"title": "t", "status": "%s"}\n```'
        self.assertEqual(parse_ai_report(block % "in_review")["status"], "in_review")
        for status in ("done", "closed", "bogus"):
            self.assertNotIn("status", parse_ai_report(block % status))

    def test_workspace_sync_does_not_consume_issue_reports(self):
        agents = self.server.agents
        state = {"thread": 7, "channel": 1, "state": "done", "pending": True, "agent": "0a1b2c3d"}
        with (
            patch.object(agents, "task_states", return_value={-1: state}),
            patch.object(agents, "mark_applied") as applied,
        ):
            status, _ = self.request("/api/workspace/snapshot")
        self.assertEqual(status, 200)
        applied.assert_not_called()


if __name__ == "__main__":
    unittest.main()
