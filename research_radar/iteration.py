"""Bounded, receipt-producing operations for the ITERATE experiment, not a crawler."""

import argparse
import fcntl
import hashlib
import json
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .core import DEFAULT_HOME, ROOT, Store, dumps, now
from .worker import Worker
from .archive import Archive


DIRECTORY = ROOT / "pilot" / "iteration"


def save(name, value, directory=None):
    directory = Path(directory) if directory is not None else DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    data = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
    if path.exists() and path.read_bytes() != data:
        raise ValueError(f"Refusing to overwrite an experiment artifact: {path}")
    if not path.exists():
        with path.open("xb") as file:
            file.write(data)
    return path


def fetch(url, name, limit=20_000_000, method="GET", source_directory=None):
    """Preserve each bounded HTTP response, including failures; never run fetched code."""
    DEFAULT_HOME.mkdir(parents=True, exist_ok=True)
    with (DEFAULT_HOME / "iteration-fetch.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _fetch(url, name, limit, method, source_directory)


def _fetch(url, name, limit, method, source_directory=None):
    directory = Path(source_directory) if source_directory is not None else DEFAULT_HOME / "iteration-sources"
    directory.mkdir(parents=True, exist_ok=True)
    log = directory / "requests.jsonl"
    rows = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    if len(rows) >= 25 or sum(r["bytes"] for r in rows) >= 120_000_000:
        raise ValueError("Frozen public-request or byte budget exhausted")
    if (directory / name).exists():
        raise ValueError("Source name already used; inspect the retained response instead")
    start = time.monotonic()
    row = {"url": url, "method": method, "at": now(), "bytes": 0}
    try:
        try:
            response = urlopen(Request(url, method=method, headers={"User-Agent": "ResearchRadar/0.2 bounded prerequisite verification"}), timeout=30)
        except HTTPError as error:
            response = error
        with response:
            cap = min(limit, 120_000_000 - sum(r["bytes"] for r in rows))
            raw = response.read(cap + 1)
            row.update(status=response.status, final_url=response.url, headers=dict(response.headers), bytes=len(raw))
        path = directory / name
        with path.open("xb") as file:
            file.write(raw)
        row.update(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), truncated=len(raw) > cap)
        if row["truncated"]:
            raise ValueError("Response exceeded bound; preserved prefix is NOT a complete source")
        reference = Archive(DEFAULT_HOME / "archive").store_bytes(
            raw, url=url, media_type=row["headers"].get("Content-Type", "application/octet-stream"),
            retrieved_at=row["at"], provenance={"http_status": row["status"], "method": method})
        row["archive"] = reference.to_dict()
        if method == "GET" and raw.startswith(b"%PDF"):
            subprocess.run(["pdftotext", str(path), str(path.with_suffix(".txt"))], check=True, capture_output=True)
            row["text_path"] = str(path.with_suffix(".txt"))
        return row
    except Exception as error:
        row["error"] = str(error)
        raise
    finally:
        row["elapsed_seconds"] = round(time.monotonic() - start, 3)
        with log.open("a") as file:
            file.write(dumps(row) + "\n")


def campaign():
    path = DIRECTORY / "campaign.json"
    if path.exists():
        return json.loads(path.read_text())["id"]
    store = Store()
    value = store.create({
        "name": "ITERATE | discrimination, preservation and opportunity quality",
        "field": "Existing drone-to-satellite corpus only; no expanded literature search",
        "config": {"queries": [], "max_papers": 25, "max_requests": 25,
                   "time_budget_seconds": 3600, "agent_timeout_seconds": 600,
                   "question": "Can the system distinguish overlap from distinct contribution and produce a defensible opportunity?"},
    })
    save("campaign.json", {"id": value["id"], "created_at": value["created_at"]})
    return value["id"]


def call(label, prompt, role="novelty", directory=None, campaign_id=None, call_limit=5):
    """Run one frozen prompt in a fresh tool-free context, retaining actual CLI receipts."""
    DEFAULT_HOME.mkdir(parents=True, exist_ok=True)
    with (DEFAULT_HOME / "iteration-model.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _call(label, prompt, role, directory, campaign_id, call_limit)


def _call(label, prompt, role, directory=None, campaign_id=None, call_limit=5):
    store = Store()
    directory = Path(directory) if directory is not None else DIRECTORY
    cid = campaign_id or campaign()
    if store.campaign(cid)["status"] == "cancelled":
        raise ValueError("Cancelled iteration cannot be revived")
    result_path = directory / (label + ".json")
    if result_path.exists():
        raise ValueError("Result already frozen; do not silently rerun or select a better answer")
    with store.db() as db:
        count = db.execute("SELECT COUNT(*) FROM jobs WHERE campaign_id=?", (cid,)).fetchone()[0]
        if count >= call_limit:
            raise ValueError("Frozen model-call budget exhausted, including failures")
        if db.execute("SELECT 1 FROM jobs WHERE campaign_id=? AND status='running'", (cid,)).fetchone():
            raise ValueError("Another bounded iteration call is active")
    job = store.enqueue(cid, role, "analysis", {"protocol": "externally driven frozen iteration prompt",
                                             "label": label, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()})
    # Reserve before making the campaign runnable, so the background worker cannot steal the job.
    with store.db() as db:
        db.execute("UPDATE jobs SET status='running' WHERE id=?", (job["id"],))
        db.execute("UPDATE campaigns SET status='running',stage=? WHERE id=?", (label, cid))
    job = store.job(job["id"])
    try:
        result = Worker(store).run_agent(job, prompt)
        save(label + ".json", {"job_id": job["id"], "completed_at": now(), "result": result}, directory=directory)
        store.finish(job, "completed", result)
        return result
    except Exception as error:
        store.finish(job, "failed", error=str(error))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    get = sub.add_parser("fetch")
    get.add_argument("url")
    get.add_argument("name")
    get.add_argument("--method", choices=["GET", "HEAD"], default="GET")
    run = sub.add_parser("call")
    run.add_argument("label")
    run.add_argument("prompt", type=Path)
    run.add_argument("--role", default="novelty", choices=["novelty", "generator", "reviewer"])
    args = parser.parse_args()
    result = fetch(args.url, args.name, method=args.method) if args.action == "fetch" else call(args.label, args.prompt.read_text(), args.role)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
