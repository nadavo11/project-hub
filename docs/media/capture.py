"""Regenerate README screenshots and tour.gif from a fictional demo workspace.

Needs Playwright, Pillow and Chrome (HUB_TEST_CHROME to override). Run: python3 docs/media/capture.py
Uses a temporary data folder; your real workspace is never read.
"""
import os, sys, tempfile, threading
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from PIL import Image
from playwright.sync_api import sync_playwright
from server import HubServer, Workspace

OUT = Path(__file__).resolve().parent
CHROME = os.environ.get("HUB_TEST_CHROME", "/usr/bin/google-chrome")


class Launcher:
    apps = {}

    def __init__(self, root):
        self.prior_art_root = root
        self.prior_art = root / "missing.html"

    def launch(self, _id):
        return {"state": "ready", "url": "/", "message": "Ready to open."}

    def projects(self):
        items = [
            ("prior-art", "Atlas Notebook", "Interactive notebook for exploring experiment results.", "ready"),
            ("localization", "Data Pipeline", "Nightly ingestion and validation jobs.", "ready"),
            ("video-agents", "Vision Lab", "Model evaluation dashboards and visual diffs.", "stopped"),
            ("sample4geo", "Docs Site", "Public documentation, built locally.", "stopped"),
        ]
        return [{"id": i, "name": n, "description": d, "state": s,
                 "message": "Running and ready to open." if s == "ready" else "Starts on demand.",
                 "url": "/"} for i, n, d, s in items]


tmp = tempfile.TemporaryDirectory()
root = Path(tmp.name)
ws = Workspace(root / "workspace.json")
general = ws.list("channels")[0]
dev = ws.add("channels", {"name": "Experiments"})
for author, text, ch in [
    ("Maya", "Baseline run finished: **top-1 = 71.4%**, up from 68.9%.", general["id"]),
    ("Leo", "Nice. Can you post the ablation table?", general["id"]),
    ("Maya", "| Variant | Top-1 |\n| --- | --- |\n| baseline | 68.9 |\n| + augment | 70.2 |\n| + augment + tuned lr | 71.4 |", general["id"]),
    ("Leo", "The loss is $L = -\\sum_i y_i \\log p_i$, so the gain is plausible.", general["id"]),
    ("Maya", "Shipping the report today. Notes are in the *Findings* note.", general["id"]),
]:
    ws.add("chat", {"author": author, "text": text, "channel": ch})
n1 = ws.add("notes", {"title": "Findings", "body": "# Findings\n\nThe tuned learning rate gives the **largest single gain**.\n\n- Baseline: 68.9%\n- Augmentation: +1.3\n- Tuned lr: +1.2\n\n```python\nlr = 3e-4\n```\n\nNext: repeat on the held-out split."})
ws.add("notes", {"title": "Meeting notes", "body": "Agenda\n\n- Review results\n- Plan next sprint"})
tl = ws.list("lists")[0]
for t, d in [("Re-run baseline with 3 seeds", True), ("Write ablation section", True),
             ("Review held-out split", False), ("Publish report", False)]:
    ws.add("todos", {"list": tl["id"], "text": t, "done": d})

with patch("server.Handler.log_message"):
    srv = HubServer(("127.0.0.1", 0), Launcher(root), ws)
threading.Thread(target=srv.serve_forever, daemon=True).start()
for t, ty, st, pr, lab in [
    ("Search page is slow on large result sets", "bug", "in_progress", "high", ["performance"]),
    ("Add CSV export to the results table", "feature", "open", "medium", ["export"]),
    ("Document the backup procedure", "task", "in_review", "low", ["docs"]),
    ("Dark mode contrast on charts", "bug", "open", "medium", ["ui"]),
    ("Evaluate a smaller model", "question", "done", "low", ["research"]),
]:
    srv.issues.create({"title": t, "type": ty, "status": st, "priority": pr, "labels": lab,
                       "assignee": "Maya", "body": "Steps, context and acceptance criteria go here.", "actor": "Maya"})
url = f"http://127.0.0.1:{srv.server_port}"

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
    pg = b.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1).new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))

    def shot(name, hash_, wait):
        pg.goto(f"{url}/#{hash_}")
        pg.locator(wait).first.wait_for()
        pg.wait_for_timeout(700)
        pg.screenshot(path=str(OUT / f"{name}.png"))

    shot("projects", "projects", ".card:not(.skeleton)")
    shot("chat", f"chat/{general['id']}", ".ws")
    shot("notes", f"notes/{n1['id']}", "#noteBody")
    pg.get_by_role("button", name="Preview", exact=True).click()
    pg.wait_for_timeout(500)
    pg.screenshot(path=str(OUT / "notes.png"))
    shot("tasks", f"tasks/{tl['id']}", ".ws")
    shot("issues", "issues", "#tab-issues *")
    print("errors:", errs)
    b.close()
srv.shutdown()
tmp.cleanup()

names = ["projects", "chat", "notes", "tasks", "issues"]
frames = [Image.open(OUT / f"{n}.png").convert("RGB").resize((960, 600), Image.LANCZOS).quantize(128) for n in names]
frames[0].save(OUT / "tour.gif", save_all=True, append_images=frames[1:], duration=1800, loop=0, optimize=True)
