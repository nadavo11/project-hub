"""Offline integrity and citation-location checks for the bounded pilot artifacts."""

import hashlib
import html
import json
import re

from .core import ROOT
from .validation import normalized_title


def compact(value):
    return re.sub(r"\W", "", html.unescape(value)).lower()


def check():
    bundle = json.loads((ROOT / "pilot/literature.json").read_text())
    manifest = json.loads((ROOT / "sources/retrieval-log.json").read_text())
    sources = {entry["url"]: entry for entry in manifest}
    checks = []
    for entry in manifest:
        if entry.get("sha256") and entry.get("cache"):
            path = ROOT / entry["cache"]
            checks.append({"id": "hash:" + entry["cache"], "expected": entry["sha256"],
                           "observed": hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "missing",
                           "passed": path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]})
    for paper in bundle["papers"]:
        metadata = ROOT / "sources" / (paper["arxiv_id"] + ".html")
        raw = metadata.read_text()
        match = re.search(r'<meta name="citation_title" content="([^"]+)"', raw)
        title = html.unescape(match[1]) if match else ""
        checks.append({"id": "title:" + paper["id"], "expected": paper["title"], "observed": title,
                       "passed": normalized_title(title) == normalized_title(paper["title"])})
    for paper in bundle["papers"] + bundle["foundations"]:
        for index, evidence in enumerate(paper.get("evidence", [])):
            entry = sources.get(evidence["source_url"], {})
            path = ROOT / entry.get("text_cache", entry.get("cache", "missing"))
            text = path.read_text(errors="replace") if path.is_file() else ""
            plain = text if entry.get("text_cache") else html.unescape(re.sub(r"<[^>]*>", " ", text))
            checks.append({"id": f"quote:{paper['id']}:{index}", "expected": evidence["quote"],
                           "observed": "Located in cached primary text" if compact(evidence["quote"]) in compact(plain) else "Not mechanically located",
                           "passed": bool(evidence["quote"]) and compact(evidence["quote"]) in compact(plain),
                           "source": evidence["source_url"], "location": evidence["location"]})
    known = {p["id"] for p in bundle["papers"]}
    for idea in bundle["opportunities"]:
        references = {p["paper_id"] for p in idea["prior_art"]}
        checks.append({"id": "references:" + idea["id"], "expected": "At least three existing competing paper records",
                       "observed": sorted(references), "passed": len(references) >= 3 and references <= known})
    return {"title": "Offline source integrity and citation checks", "checks": checks,
            "passed": all(c["passed"] for c in checks), "count": len(checks),
            "failures": [c for c in checks if not c["passed"]],
            "limitations": ["Exact title, hash and quotation checks do not prove every interpretation or reproduce any experiment.",
                            "Latest metadata and earlier manuscript versions can differ; SkyReg is explicitly documented."]}


if __name__ == "__main__":
    result = check()
    (ROOT / "pilot/source-integrity.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({"count": result["count"], "passed": result["passed"], "failures": result["failures"]}, indent=2))
