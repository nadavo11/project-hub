"""Loopback research workbench; never launches experiment commands."""

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

from .core import Conflict, DEFAULT_HOME, ROOT, Store, dumps
from .worker import Worker


def report(state):
    campaign = next((c for c in state["campaigns"] if c["id"] == state["campaign"]), {})
    lines = [f"# Research Radar: {campaign.get('name', 'No campaign')}", "",
             "Evidence labels are part of the findings. No absence-of-prior-art claim proves novelty.", "",
             f"State: {campaign.get('status', 'waiting')}", "",
             "## Literature"]
    for paper in state["papers"]:
        lines += [f"### {paper['title']}", f"Source: {paper['url']}", f"Access: {paper.get('verification', 'unverified')}",
                  f"Contribution: {paper.get('contribution', 'Unexamined')}", f"Mechanism: {paper.get('mechanism', 'Unexamined')}",
                  f"Evaluation: {paper.get('evaluation', 'Unexamined')}", f"Limitations: {paper.get('limitations', 'Unknown')}", ""]
    lines += ["## Research tensions", ""]
    for tension in state["tensions"]:
        lines += [f"### {tension['title']}", str(tension.get("observation", "")), f"Evidence: {dumps(tension.get('evidence', []))}", ""]
    lines += ["## Opportunity board", ""]
    for idea in state["opportunities"]:
        lines += [f"### {idea['id']}: {idea['title']}", f"State: {idea.get('status')}",
                  f"Hypothesis: {idea.get('hypothesis')}", f"Contribution: {idea.get('contribution')}",
                  f"Novelty: {dumps(idea.get('novelty'))}", f"Prior art: {dumps(idea.get('prior_art', []))}",
                  f"Review: {dumps(idea.get('review'))}", f"Falsification: {dumps(idea.get('experiment'))}",
                  f"Decision history: {dumps(idea.get('comments', []))}", ""]
    lines += ["## System validation", "", "```json", dumps(state["validations"]), "```", "",
              "## Measured costs", "", "```json", dumps(state["costs"]), "```"]
    return "\n".join(lines)


class RadarServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, store, worker=None):
        self.store, self.worker = store, worker
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send(self, status, body, content_type="application/json; charset=utf-8"):
        payload = dumps(body).encode() if content_type.startswith("application/json") else body
        if isinstance(payload, str):
            payload = payload.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(payload)

    def trusted(self, mutation=False):
        host = self.headers.get("Host", "")
        allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        if host not in allowed:
            self.send(403, {"error": "Use the loopback address; reverse proxy access is not configured"})
            return False
        origin = self.headers.get("Origin")
        if origin and origin not in {f"http://{h}" for h in allowed}:
            self.send(403, {"error": "Cross-origin requests are not allowed"})
            return False
        if mutation and self.headers.get("Sec-Fetch-Site") == "cross-site":
            self.send(403, {"error": "Cross-site actions are not allowed"})
            return False
        return True

    def do_GET(self):
        if not self.trusted():
            return
        path = urlsplit(self.path)
        campaign_id = parse_qs(path.query).get("campaign", [None])[0]
        try:
            if path.path == "/api/health":
                return self.send(200, {"status": "ok", "app": "research-radar", "gpu_execution": False})
            if path.path == "/api/atlas" or path.path.startswith(("/api/atlas/", "/atlas-assets/")):
                base = (self.server.store.home / "failure-atlas").resolve()
                relative = ""
                if path.path in {"/api/atlas", "/api/atlas/export"}:
                    relative = "atlas.json"
                elif path.path == "/api/atlas/protocol":
                    relative = "protocol.json"
                else:
                    match = re.fullmatch(r"/api/atlas/cases/([a-z0-9_-]+)(?:/(sift|orb|roma|roma-005|roma-official))?", path.path)
                    asset = re.fullmatch(r"/atlas-assets/([a-z0-9_-]+)/(query|target|confidence)\.png", path.path)
                    if match:
                        relative = f"cases/{match[1]}/{match[2] or 'case'}.json"
                    elif asset:
                        relative = f"cases/{asset[1]}/{asset[2]}.png"
                if not relative:
                    return self.send(404, {"error": "Unknown atlas artifact"})
                file = (base / relative).resolve()
                if not file.is_relative_to(base) or not file.is_file():
                    return self.send(404, {"error": "Atlas artifact not available; no result is fabricated"})
                if file.suffix == ".png":
                    return self.send(200, file.read_bytes(), "image/png")
                return self.send(200, json.loads(file.read_text()))
            if path.path in {"/api/state", "/api/export", "/api/report"}:
                if campaign_id:
                    self.server.store.campaign(campaign_id)
                state = self.server.store.state(campaign_id)
                if path.path == "/api/report":
                    return self.send(200, report(state), "text/markdown; charset=utf-8")
                return self.send(200, state)
            if path.path.startswith("/api/"):
                return self.send(404, {"error": "Unknown API"})
            name = path.path.strip("/") or "index.html"
            if name not in {"index.html", "styles.css", "app.js", "atlas.html", "atlas.css", "atlas.js"}:
                return self.send(404, {"error": "Not found"})
            file = ROOT / "static" / name
            return self.send(200, file.read_bytes(), mimetypes.guess_type(name)[0] or "application/octet-stream")
        except KeyError as error:
            self.send(404, {"error": str(error)})
        except OSError:
            self.send(503, {"error": "Interface asset unavailable"})

    def do_POST(self):
        if not self.trusted(mutation=True):
            return
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.send(415, {"error": "Use application/json"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 100_000:
                return self.send(413, {"error": "JSON request must be 1-100000 bytes"})
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError("JSON object required")
            path = urlsplit(self.path).path
            store = self.server.store
            if path == "/api/campaigns":
                return self.send(201, store.create(data))
            match = re.fullmatch(r"/api/(campaigns|jobs|opportunities)/([a-zA-Z0-9_-]+)/([a-z]+)", path)
            if not match:
                return self.send(404, {"error": "Unknown operation"})
            kind, record_id, action = match.groups()
            if kind == "campaigns":
                result = store.investigate(record_id, data) if action == "investigate" else store.control(record_id, action, data)
            elif kind == "jobs":
                result = store.job_control(record_id, action, data)
            elif action == "decision":
                result = store.decide(record_id, data)
            else:
                raise ValueError("Unknown opportunity operation")
            self.send(200, result)
        except Conflict as error:
            self.send(409, {"error": str(error)})
        except (ValueError, TypeError) as error:
            self.send(400, {"error": str(error)})
        except KeyError as error:
            self.send(404, {"error": str(error)})


def serve(home=DEFAULT_HOME, port=8776):
    store = Store(home)
    worker = Worker(store)
    server = RadarServer(("127.0.0.1", port), store, worker)
    worker.start()
    print(f"Research Radar: http://127.0.0.1:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        worker.close()
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path, default=DEFAULT_HOME)
    parser.add_argument("--port", type=int, default=8776)
    args = parser.parse_args()
    serve(args.home, args.port)
