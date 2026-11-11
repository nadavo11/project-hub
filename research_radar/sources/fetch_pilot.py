"""Bounded public-source retrieval cache; no model APIs or experiments."""
import concurrent.futures
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import time
import urllib.request
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
IDS = [
    "2002.12186", "2201.09201", "2303.11851", "2309.16020",
    "2405.11936", "2409.16925", "2607.19951", "2607.20116",
    "2605.07099", "2608.28891", "2505.07622", "2308.16906",
    "2305.15404", "2406.09756", "2503.11651", "1812.03506",
    "2306.13643", "2011.12172", "2607.04722", "2509.18350",
    "2409.14634", "2409.04109", "2506.22026", "2504.08066",
]


class Metadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}
        self.capture = False
        self.abstract = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "meta" and d.get("name", "").startswith("citation_"):
            self.meta.setdefault(d["name"], []).append(d.get("content", ""))
        if tag == "blockquote" and "abstract" in d.get("class", ""):
            self.capture = True

    def handle_endtag(self, tag):
        if tag == "blockquote":
            self.capture = False

    def handle_data(self, data):
        if self.capture:
            self.abstract.append(data)


def fetch(url, name, query):
    start = time.monotonic()
    entry = dict(url=url, query=query, accessed_at=datetime.now(timezone.utc).isoformat())
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "ResearchRadarPilot/1.0 (public academic reading)"})
        with urllib.request.urlopen(request, timeout=70) as response:
            data = response.read(40_000_001)
            entry["http_status"] = response.status
            entry["content_type"] = response.headers.get("Content-Type")
            entry["final_url"] = response.url
            entry["bytes"] = len(data)
        if len(data) > 40_000_000:
            entry.update(status="budget_limited", cache=None,
                         error="40 MB per-response research budget exceeded")
        else:
            (ROOT / name).write_bytes(data)
            entry.update(status="ok", cache="sources/" + name,
                         sha256=hashlib.sha256(data).hexdigest())
    except Exception as exc:
        entry.update(status="error", error=str(exc))
        entry.setdefault("bytes", 0)
    entry["seconds"] = round(time.monotonic() - start, 3)
    return entry


def one(identifier):
    entries = []
    entry = fetch("https://arxiv.org/abs/" + identifier, identifier + ".html",
                  "Resolve discovery candidate identifier; verify title/authors/date/abstract")
    entries.append(entry)
    if entry["status"] != "ok":
        return entries
    parser = Metadata()
    parser.feed((ROOT / (identifier + ".html")).read_text(errors="replace"))
    metadata = dict(arxiv_id=identifier, **parser.meta,
                    abstract=" ".join(" ".join(parser.abstract).split()))
    (ROOT / (identifier + ".metadata.json")).write_text(json.dumps(metadata, indent=2))
    if not metadata.get("citation_title"):
        entries[-1]["status"] = "metadata_missing"
        return entries
    entry = fetch("https://arxiv.org/pdf/" + identifier, identifier + ".pdf",
                  "Retrieve full paper for bounded selective examination")
    entries.append(entry)
    if entry["status"] == "ok":
        result = subprocess.run(["pdftotext", "-layout", str(ROOT / (identifier + ".pdf")),
                                 str(ROOT / (identifier + ".txt"))], capture_output=True, text=True)
        entry["text_extraction"] = "ok" if result.returncode == 0 else result.stderr[:1000]
        entry["text_cache"] = "sources/" + identifier + ".txt"
    return entries


if __name__ == "__main__":
    start = time.monotonic()
    log = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for entries in pool.map(one, IDS):
            log.extend(entries)
            print(entries[0]["url"], [(e["status"], e["bytes"]) for e in entries], flush=True)
    log.append(fetch("https://www.anthropic.com/research/multi-agent-research-system",
                     "anthropic-research.html", "Read supplied multi-agent research engineering foundation"))
    (ROOT / "retrieval-log.json").write_text(json.dumps(log, indent=2))
    (ROOT / "retrieval-costs.json").write_text(json.dumps(dict(
        http_requests=len(log), download_bytes=sum(e["bytes"] for e in log),
        elapsed_seconds=round(time.monotonic() - start, 3),
        api_cost_usd=None, gpu_hours=0), indent=2))
