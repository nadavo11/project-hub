"""Browser regressions against an ephemeral hub, never the shared workspace.

Run with a Python environment containing Playwright and a Chromium installation:
    python -m unittest -v test_ui
HUB_TEST_CHROME can override the browser executable.
"""

import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

from server import HubServer, Workspace


class FixtureLauncher:
    apps = {}

    def __init__(self, root):
        self.prior_art_root = root
        self.prior_art = root / "missing.html"
        (root / "index.html").write_text("<html><title>Research fixture</title>Research</html>")

    def launch(self, _project_id):
        return {"state": "ready", "url": "/prior-art/", "message": "Ready to open."}

    def projects(self):
        return [
            {
                "id": key, "name": name, "description": "An isolated project fixture.",
                "state": "ready", "message": "Running and ready to open.",
                "url": "/prior-art/",
            }
            for key, name in (
                ("prior-art", "Research library"), ("localization", "Localization"),
                ("video-agents", "Video Agents"), ("sample4geo", "Sample4Geo Atlas"),
            )
        ]


@unittest.skipIf(sync_playwright is None, "Install Playwright to run browser regressions.")
class WorkspaceBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            executable_path=os.environ.get("HUB_TEST_CHROME", "/usr/bin/google-chrome"),
            args=["--no-sandbox"],
        )

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workspace = Workspace(self.root / "workspace.json")
        self.note = self.workspace.add("notes", {"title": "Experiment findings", "body": "Original"})
        self.workspace.add("notes", {"title": "Meeting notes", "body": "Agenda"})
        self.general = self.workspace.list("channels")[0]
        self.channel = self.workspace.add("channels", {"name": "Experiments"})
        self.task_list = self.workspace.list("lists")[0]
        self.workspace.add("todos", {"list": self.task_list["id"], "text": "Compare the baseline"})
        self.workspace.add("todos", {"list": self.task_list["id"], "text": "Publish findings"})
        self.workspace.add("chat", {"author": "Alex", "text": "Results are ready."})
        self.log_patch = patch("server.Handler.log_message")
        self.log_patch.start()
        self.server = HubServer(("127.0.0.1", 0), FixtureLauncher(self.root), self.workspace)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 900})
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))

    def tearDown(self):
        self.context.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.log_patch.stop()
        self.temp.cleanup()
        self.assertEqual(self.errors, [], "Unexpected browser runtime errors")

    def wait_until(self, predicate, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            self.page.wait_for_timeout(100)
        self.fail("Timed out waiting for workspace state")

    def open_note(self):
        self.page.goto(f"{self.url}/#notes/{self.note['id']}")
        self.page.locator("#noteBody").wait_for()

    def saved_note(self):
        return next(n for n in self.workspace.list("notes") if n["id"] == self.note["id"])

    def test_project_open_still_launches_the_expected_page(self):
        self.page.goto(self.url + "/#projects")
        self.page.locator(".card:not(.skeleton)").first.wait_for()
        with self.page.expect_popup() as popup_info:
            self.page.locator("[data-project-id='prior-art']").get_by_role(
                "button", name="Open Research library in a new tab", exact=True
            ).click()
        popup = popup_info.value
        popup.wait_for_url(self.url + "/prior-art/")
        self.assertEqual(popup.title(), "Research fixture")

    def test_chat_drafts_survive_navigation_reload_and_keyboard_poll(self):
        self.page.goto(f"{self.url}/#chat/{self.general['id']}")
        self.page.locator(".composer textarea").wait_for()
        self.page.fill(".composer textarea", "Unsent draft")
        self.page.locator(".side-item", has_text="Experiments").click()
        self.page.locator(".side-item", has_text="General").click()
        self.assertEqual(self.page.input_value(".composer textarea"), "Unsent draft")
        self.page.reload()
        self.page.locator(".composer textarea").wait_for()
        self.assertEqual(self.page.input_value(".composer textarea"), "Unsent draft")
        self.page.wait_for_timeout(200)
        self.page.locator(".side-item").first.focus()
        self.page.wait_for_timeout(5500)
        self.assertTrue(self.page.evaluate(
            "document.activeElement.classList.contains('side-item')"
        ))

    def test_note_autosave_survives_reload(self):
        self.open_note()
        self.page.fill("#noteBody", "A saved revision")
        self.wait_until(lambda: self.saved_note()["body"] == "A saved revision")
        self.page.reload()
        self.page.locator("#noteBody").wait_for()
        self.assertEqual(self.page.input_value("#noteBody"), "A saved revision")

    def test_icon_picker_and_emoji_buttons(self):
        self.open_note()
        self.page.locator(".pane-head .icon-pick").click()
        self.page.locator(".emoji-opt", has_text="🚀").click()
        self.wait_until(lambda: self.saved_note().get("icon") == "🚀")
        self.page.fill("#noteBody", "Ship ")
        self.page.locator(".emoji-field.multiline .emoji-add").click()
        self.page.locator(".emoji-opt", has_text="🎉").click()
        self.wait_until(lambda: self.saved_note()["body"] == "Ship 🎉")
        self.page.goto(f"{self.url}/#chat/{self.general['id']}")
        self.page.locator(".composer textarea").wait_for()
        self.page.locator(".pane-head .icon-pick").click()
        self.page.locator(".emoji-opt", has_text="🔥").click()
        self.wait_until(lambda: self.workspace.list("channels")[0]["icon"] == "🔥")
        self.page.locator(".composer .emoji-add").click()
        self.page.keyboard.press("Escape")
        self.assertEqual(self.page.locator(".emoji-pop").count(), 0)
        self.page.goto(f"{self.url}/#tasks/{self.task_list['id']}")
        self.page.locator(".add-task input").wait_for()
        self.page.locator(".add-task .emoji-add").click()
        self.page.locator(".emoji-opt", has_text="✅").click()
        self.assertEqual(self.page.input_value(".add-task input"), "✅")

    def test_typing_during_note_save_keeps_newest_revision(self):
        self.open_note()
        held = []

        def delay_first_save(route):
            if route.request.method == "PATCH" and not held:
                held.append(route)
            else:
                route.continue_()

        self.page.route("**/api/workspace/notes/*", delay_first_save)
        self.page.fill("#noteBody", "First revision")
        self.wait_until(lambda: bool(held))
        self.page.fill("#noteBody", "Newer revision typed while saving")
        self.page.wait_for_timeout(900)
        held[0].continue_()
        self.wait_until(lambda: self.saved_note()["body"] == "Newer revision typed while saving")
        self.page.reload()
        self.page.locator("#noteBody").wait_for()
        self.assertEqual(self.page.input_value("#noteBody"), "Newer revision typed while saving")

    def test_failed_chat_send_does_not_replace_newer_draft(self):
        self.page.goto(f"{self.url}/#chat/{self.general['id']}")
        self.page.locator(".composer textarea").wait_for()
        held = []

        def hold_send(route):
            if route.request.method == "POST":
                held.append(route)
            else:
                route.continue_()

        self.page.route("**/api/workspace/chat", hold_send)
        self.page.fill(".composer textarea", "Message in flight")
        self.page.locator(".composer textarea").press("Enter")
        self.wait_until(lambda: bool(held))
        self.page.fill(".composer textarea", "A new draft")
        held[0].fulfill(status=503, content_type="application/json",
                        body='{"error":"Simulated send failure"}')
        self.page.locator(".outbox-item").wait_for()
        self.assertEqual(self.page.input_value(".composer textarea"), "A new draft")
        self.assertIn("Message in flight", self.page.locator(".outbox").inner_text())
        self.page.reload()
        self.page.locator(".composer textarea").wait_for()
        self.assertEqual(self.page.input_value(".composer textarea"), "A new draft")
        self.assertIn("Message in flight", self.page.locator(".outbox").inner_text())

    def test_failed_note_save_retains_draft_across_poll_navigation_and_reload(self):
        self.open_note()

        def fail_save(route):
            if route.request.method == "PATCH":
                route.fulfill(status=503, content_type="application/json",
                              body=json.dumps({"error": "Simulated save failure"}))
            else:
                route.continue_()

        self.page.route("**/api/workspace/notes/*", fail_save)
        self.page.fill("#noteBody", "Important unsaved revision")
        self.page.wait_for_timeout(6500)
        self.assertEqual(self.saved_note()["body"], "Original")
        self.page.click("#nav-chat")
        self.page.click("#nav-notes")
        self.page.locator(".side-item", has_text="Experiment findings").click()
        self.assertEqual(self.page.input_value("#noteBody"), "Important unsaved revision")
        self.page.reload()
        self.page.locator("#noteBody").wait_for()
        self.assertEqual(self.page.input_value("#noteBody"), "Important unsaved revision")

    def test_conflicting_note_does_not_overwrite_remote_revision(self):
        self.open_note()
        self.workspace.update("notes", self.note["id"], {"body": "Remote edit", "revision": 1})
        self.page.fill("#noteBody", "My local edit")
        self.page.wait_for_timeout(1500)
        self.assertEqual(self.saved_note()["body"], "Remote edit")
        self.assertEqual(self.page.input_value("#noteBody"), "My local edit")
        self.page.reload()
        self.page.locator("#noteBody").wait_for()
        self.assertEqual(self.page.input_value("#noteBody"), "My local edit")

    def test_template_dialog_contains_focus_and_restores_trigger(self):
        self.page.goto(f"{self.url}/#chat/{self.general['id']}")
        self.page.locator(".composer textarea").wait_for()
        self.page.click("#sideTemplates")
        self.assertTrue(self.page.evaluate("document.getElementById('modal').open"))
        for _ in range(20):
            self.page.keyboard.press("Tab")
            self.assertTrue(self.page.evaluate(
                "document.activeElement === document.body || "
                "!!document.activeElement.closest('dialog')"
            ))
        self.page.keyboard.press("Escape")
        self.assertFalse(self.page.evaluate("document.getElementById('modal').open"))
        self.assertTrue(self.page.evaluate("document.activeElement.id === 'sideTemplates'"))

    def test_template_preview_failure_retry_and_reusable_template(self):
        self.page.goto(f"{self.url}/#tasks/{self.task_list['id']}")
        self.page.locator(".add-task input").wait_for()
        self.page.click("#sideTemplates")
        self.page.locator(".template", has_text="Experiment checklist").click()
        self.page.locator("#modal input").fill("My experiment")
        submitted = []

        def fail_create(route):
            submitted.append(route.request.post_data_json)
            route.fulfill(status=503, content_type="application/json",
                          body='{"error":"Simulated create failure"}')

        self.page.route("**/api/workspace/create", fail_create)
        self.page.get_by_role("button", name="Create", exact=True).click()
        self.wait_until(lambda: bool(submitted))
        self.assertTrue(self.page.evaluate("document.getElementById('modal').open"))
        self.assertEqual(len(self.workspace.list("lists")), 1)
        self.page.unroute("**/api/workspace/create", fail_create)
        self.page.get_by_role("button", name="Create", exact=True).click()
        self.wait_until(lambda: len(self.workspace.list("lists")) == 2)
        created = next(i for i in self.workspace.list("lists") if i["name"] == "My experiment")
        children = [i for i in self.workspace.list("todos") if i["list"] == created["id"]]
        self.assertEqual([i["text"] for i in children], submitted[0]["items"])
        self.page.get_by_role("button", name="Save as template", exact=True).click()
        self.page.locator("#modal input").fill("My reusable checklist")
        self.page.get_by_role("button", name="Save template", exact=True).click()
        self.wait_until(lambda: len(self.workspace.list("templates")) == 1)
        self.page.click("#sideTemplates")
        self.page.locator(".template", has_text="My reusable checklist").wait_for()

    def test_task_delete_has_undo_and_trash_survives_reload(self):
        self.page.goto(f"{self.url}/#tasks/{self.task_list['id']}")
        self.page.locator(".add-task input").wait_for()
        original_ids = {i["id"] for i in self.workspace.list("todos")}
        self.page.locator(".task .danger").first.click()
        self.wait_until(lambda: len(self.workspace.list("todos")) == 1)
        self.page.get_by_role("button", name="Undo", exact=True).click()
        self.wait_until(lambda: len(self.workspace.list("todos")) == 2)
        self.assertEqual({i["id"] for i in self.workspace.list("todos")}, original_ids)
        self.page.locator(".task .danger").first.click()
        self.wait_until(lambda: len(self.workspace.list("todos")) == 1)
        self.page.reload()
        self.page.locator(".add-task input").wait_for()
        self.page.click("#workspaceTrash")
        self.page.get_by_role("button", name="Restore", exact=True).click()
        self.wait_until(lambda: len(self.workspace.list("todos")) == 2)
        self.assertEqual({i["id"] for i in self.workspace.list("todos")}, original_ids)

    def test_mobile_detail_composer_has_space_and_back_returns_to_list(self):
        self.context.close()
        self.context = self.browser.new_context(
            viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
        )
        self.page = self.context.new_page()
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.goto(f"{self.url}/#chat/{self.general['id']}")
        self.page.locator(".composer textarea").wait_for()
        self.page.wait_for_timeout(200)
        text = self.page.locator(".composer textarea").bounding_box()
        self.assertGreater(text["width"], 200)
        self.assertLessEqual(text["y"] + text["height"], 844)
        self.assertFalse(self.page.evaluate("document.activeElement.tagName === 'TEXTAREA'"))
        self.page.locator(".pane-back").click()
        self.assertTrue(self.page.locator(".ws-side").is_visible())
        self.assertFalse(self.page.locator("#wsMain").is_visible())
        self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), 390)

    def test_navigation_motion_settles_and_task_progress_tracks_completion(self):
        self.page.goto(self.url + "/#projects")
        self.page.locator(".card:not(.skeleton)").first.wait_for()
        self.page.wait_for_timeout(300)
        moving = self.page.evaluate("""async () => {
            document.getElementById('nav-chat').click();
            await new Promise(requestAnimationFrame);
            return document.querySelector('.nav-highlight').getAnimations().length;
        }""")
        self.assertGreater(moving, 0)
        self.page.evaluate("document.getElementById('nav-todos').click()")
        self.page.locator(".task").first.wait_for()
        self.page.wait_for_timeout(300)
        indicator = self.page.locator(".nav-highlight").bounding_box()
        selected = self.page.locator("#nav-todos").bounding_box()
        for dimension in ("x", "y", "width", "height"):
            self.assertAlmostEqual(indicator[dimension], selected[dimension], delta=1)
        self.page.locator(".task-check").first.click()
        self.page.locator(".task.done").wait_for()
        self.page.wait_for_timeout(300)
        progress = self.page.locator("#progressBar").bounding_box()
        track = self.page.locator(".progress").bounding_box()
        self.assertAlmostEqual(progress["width"], track["width"] / 2, delta=1)

    def test_reduced_motion_and_keyboard_navigation_are_immediate(self):
        self.page.emulate_media(reduced_motion="reduce")
        self.page.goto(f"{self.url}/#chat/{self.general['id']}")
        self.page.locator(".composer textarea").wait_for()
        self.page.click("#nav-notes")
        self.page.locator("#noteBody").wait_for()
        self.assertEqual(self.page.evaluate("document.getAnimations().length"), 0)
        self.page.emulate_media(reduced_motion="no-preference")
        self.page.evaluate("document.getElementById('nav-chat').click()")
        self.page.wait_for_function(
            "document.querySelector('.nav-highlight').getAnimations().length > 0"
        )
        self.page.evaluate("""() => {
            window.motionPreferenceChanged = false;
            matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', () => {
                window.motionPreferenceChanged = true;
            }, {once: true});
        }""")
        self.page.emulate_media(reduced_motion="reduce")
        self.page.wait_for_function("window.motionPreferenceChanged")
        self.assertEqual(self.page.evaluate("document.getAnimations().length"), 0)
        self.page.emulate_media(reduced_motion="no-preference")
        self.page.locator("#nav-notes").focus()
        self.page.keyboard.press("Enter")
        self.page.locator("#noteBody").wait_for()
        self.assertEqual(self.page.evaluate("document.getAnimations().length"), 0)

    def open_agents(self):
        self.page.goto(f"{self.url}/#chat/{self.general['id']}")
        self.page.get_by_role("button", name="+ New", exact=True).click()
        self.page.get_by_label("Operator key", exact=True).fill(self.server.agents.key)
        self.page.get_by_role("button", name="Unlock Agent chat", exact=True).click()
        self.page.get_by_role("switch", name="AI for this channel").wait_for()

    def test_operator_key_entry_survives_background_session_poll(self):
        self.page.goto(f"{self.url}/#chat/{self.general['id']}")
        self.page.get_by_role("button", name="+ New", exact=True).click()
        key = self.page.get_by_label("Operator key", exact=True)
        key.fill(self.server.agents.key)
        self.page.wait_for_timeout(2300)
        self.assertEqual(key.input_value(), self.server.agents.key)
        self.page.get_by_role("button", name="Unlock Agent chat", exact=True).click()
        self.page.get_by_role("switch", name="AI for this channel").wait_for()

    def test_private_agents_toggle_thread_routing_reports_and_lock(self):
        self.open_agents()
        self.page.get_by_role("switch", name="AI for this channel").click()
        self.page.get_by_role("button", name="+ New", exact=True).click()
        self.page.get_by_label("New thread title").fill("Baseline review")
        self.page.get_by_role("button", name="Create thread", exact=True).click()
        message = self.page.get_by_role("textbox", name="Message agent", exact=True)
        self.wait_until(lambda: message.is_enabled())
        message.fill("Review the baseline")
        self.page.locator(".agent-composer").get_by_role("button", name="Send", exact=True).click()
        self.wait_until(lambda: len(self.server.agents.summary()["jobs"]) == 1)
        first = self.server.agents.claim()
        self.server.agents.event(first, "tool.execution_start", '{"toolName":"view","path":"baseline.py"}')
        self.server.agents.finish(first, "done", response="The baseline review is ready.")
        self.page.locator(".agent-message.assistant").wait_for()
        self.assertIn("The baseline review is ready.", self.page.locator(".agent-messages").inner_text())
        self.page.locator(".agent-activity > summary").click()
        self.assertIn("Tool start", self.page.locator(".agent-activity").inner_text())
        self.page.get_by_role("button", name="+ New", exact=True).click()
        self.page.get_by_label("New thread title").fill("Separate experiment")
        self.page.get_by_role("button", name="Create thread", exact=True).click()
        self.wait_until(lambda: len(self.server.agents.channel(self.general["id"])["threads"]) == 2)
        self.wait_until(lambda: self.page.locator(".agent-message").count() == 0)
        message.fill("Draft for another agent")
        self.page.get_by_role("tab", name="Baseline review", exact=True).click()
        self.page.locator(".agent-message.assistant").wait_for()
        self.assertEqual(message.input_value(), "")
        self.page.reload()
        self.page.locator(".agent-message.assistant").wait_for()
        self.assertEqual(self.page.locator(".agent-unlock").is_visible(), False)
        self.page.get_by_role("switch", name="AI for this channel").click()
        self.wait_until(lambda: message.is_disabled())
        self.page.get_by_label("More options").click()
        self.page.get_by_role("button", name="Lock", exact=True).click()
        self.page.get_by_label("Operator key", exact=True).wait_for()
        self.assertEqual(self.page.locator(".agent-message").count(), 0)
        self.assertEqual(self.page.get_by_role("tab").all_text_contents(), ["Shared"])
        snapshot = self.workspace.snapshot()
        self.assertNotIn("Review the baseline", json.dumps(snapshot))
        self.assertIsNone(self.page.evaluate("sessionStorage.getItem('operator.key')"))

    def test_flat_chat_tabs_discover_threads_and_preserve_drafts_and_focus(self):
        self.open_agents()
        store = self.server.agents
        store.set_enabled(self.general["id"], True)
        first = store.create_thread(self.general["id"], {"title": "First private chat"})
        second = store.create_thread(self.general["id"], {"title": "Second private chat"})
        store.create_thread(self.channel["id"], {"title": "Other channel private chat"})
        self.page.reload()
        shared = self.page.get_by_role("tab", name="Shared", exact=True)
        first_tab = self.page.get_by_role("tab", name="First private chat", exact=True)
        second_tab = self.page.get_by_role("tab", name="Second private chat", exact=True)
        first_tab.wait_for()
        self.assertEqual(shared.get_attribute("aria-selected"), "true")
        self.assertEqual(self.page.get_by_role("tab").count(), 3)
        self.assertEqual(self.page.locator(".agent-thread-picker").count(), 0)
        self.page.locator(".composer textarea").fill("Shared draft")
        first_tab.click()
        message = self.page.get_by_role("textbox", name="Message agent", exact=True)
        self.wait_until(lambda: message.is_enabled())
        message.fill("First private draft")
        first_tab.focus()
        self.page.keyboard.press("ArrowLeft")
        self.wait_until(lambda: message.is_enabled())
        self.assertEqual(second_tab.get_attribute("aria-selected"), "true")
        self.assertTrue(self.page.url.endswith(f"/thread/{second['id']}"))
        message.fill("Second private draft")
        second_tab.focus()
        self.page.wait_for_timeout(2300)
        self.assertTrue(second_tab.evaluate("(tab) => tab === document.activeElement"))
        self.page.keyboard.press("Home")
        self.assertEqual(shared.get_attribute("aria-selected"), "true")
        self.assertEqual(self.page.input_value(".composer textarea"), "Shared draft")
        self.assertFalse(self.page.locator(".agent-panel").is_visible())
        self.page.keyboard.press("End")
        self.wait_until(lambda: message.is_enabled())
        self.assertEqual(message.input_value(), "First private draft")
        self.assertTrue(self.page.url.endswith(f"/thread/{first['id']}"))
        self.page.get_by_label("More options").click()
        self.page.get_by_role("button", name="Close thread", exact=True).click()
        closed_tab = self.page.get_by_role("tab", name="First private chat (closed)", exact=True)
        closed_tab.wait_for()
        self.wait_until(lambda: message.is_disabled())
        second_tab.click()
        self.wait_until(lambda: message.is_enabled())
        self.assertEqual(message.input_value(), "Second private draft")
        self.page.get_by_role("button", name="+ New", exact=True).click()
        self.assertTrue(self.page.get_by_label("New thread title").is_visible())
        self.assertFalse(message.is_visible())
        shared.click()
        self.assertEqual(self.page.input_value(".composer textarea"), "Shared draft")

    def test_agent_delivery_retry_is_idempotent_after_lost_response(self):
        self.open_agents()
        self.server.agents.set_enabled(self.general["id"], True)
        thread = self.server.agents.create_thread(self.general["id"], {"title": "Retry request"})
        self.page.reload()
        self.page.get_by_role("tab", name="Retry request", exact=True).click()
        message = self.page.get_by_role("textbox", name="Message agent", exact=True)
        self.wait_until(lambda: message.is_enabled())
        delivered = []

        def lose_reply(route):
            payload = route.request.post_data_json
            delivered.append(payload)
            self.server.agents.submit(thread["id"], payload)
            route.abort()

        self.page.route("**/api/agents/threads/*/messages", lose_reply)
        message.fill("Run exactly once")
        self.page.locator(".agent-composer").get_by_role("button", name="Send", exact=True).click()
        self.wait_until(lambda: bool(delivered))
        self.page.unroute("**/api/agents/threads/*/messages", lose_reply)
        self.wait_until(lambda: message.input_value() == "")
        self.assertEqual(len(self.server.agents.thread(thread["id"])["jobs"]), 1)

    def test_agent_mobile_composer_and_thread_history_remain_usable(self):
        self.page.set_viewport_size({"width": 320, "height": 568})
        self.open_agents()
        self.server.agents.set_enabled(self.general["id"], True)
        thread = self.server.agents.create_thread(self.general["id"], {"title": "Small screen"})
        self.server.agents.submit(thread["id"], {"text": "A task", "nonce": "mobile"})
        job = self.server.agents.claim()
        self.server.agents.finish(job, "done", response="Ready for your next message.")
        for index in range(8):
            self.server.agents.create_thread(self.general["id"], {"title": f"Another long private chat {index}"})
        self.page.goto(f"{self.url}/#chat/{self.general['id']}/thread/{thread['id']}")
        self.page.locator(".agent-message.assistant").wait_for()
        self.page.wait_for_timeout(300)
        self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), 320)
        composer = self.page.locator(".agent-composer").bounding_box()
        self.assertLessEqual(composer["y"] + composer["height"], 568)
        self.assertGreater(self.page.locator(".agent-log").bounding_box()["height"], 80)
        self.assertTrue(self.page.locator(".chat-tabs").evaluate("(tabs) => tabs.scrollWidth > tabs.clientWidth"))
        active_tab = self.page.get_by_role("tab", name="Small screen", exact=True).bounding_box()
        tab_bar = self.page.locator(".chat-tabs").bounding_box()
        self.assertGreaterEqual(active_tab["x"], tab_bar["x"])
        self.assertLessEqual(active_tab["x"] + active_tab["width"], tab_bar["x"] + tab_bar["width"] + 1)
        new_button = self.page.get_by_role("button", name="+ New", exact=True).bounding_box()
        self.assertLessEqual(new_button["x"] + new_button["width"], 320)
        self.page.get_by_role("tab", name="Shared", exact=True).click()
        self.assertTrue(self.page.locator(".composer textarea").is_visible())
        self.assertFalse(self.page.locator(".agent-panel").is_visible())

    def test_earlier_agent_activity_remains_reachable_after_poll(self):
        self.open_agents()
        store = self.server.agents
        store.set_enabled(self.general["id"], True)
        thread = store.create_thread(self.general["id"], {"title": "Long activity history"})
        store.submit(thread["id"], {"text": "A task", "nonce": "history"})
        job = store.claim()
        for index in range(410):
            store.event(job, "status", f"Activity {index}")
        store.finish(job, "done", response="Complete.")
        self.page.goto(f"{self.url}/#chat/{self.general['id']}/thread/{thread['id']}")
        self.page.locator(".agent-message.assistant").wait_for()
        self.page.locator(".agent-activity > summary").click()
        earlier = self.page.get_by_role("button", name="Load earlier activity")
        earlier.click()
        self.page.wait_for_timeout(2200)
        self.assertTrue(earlier.is_visible())
        earlier.click()
        self.wait_until(lambda: not earlier.is_visible())
        self.assertEqual(self.page.locator(".agent-event").count(), 412)


if __name__ == "__main__":
    unittest.main()
