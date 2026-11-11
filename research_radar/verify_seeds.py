"""Re-fetch the five blind-test primary sources and verify identity/quoted passages."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .core import DEFAULT_HOME, ROOT, now
from .validation import normalized_title


def compact(value):
    return re.sub(r"\W", "", value).lower()


def verify(audit_path, home):
    audit = json.loads(audit_path.read_text())
    directory = Path(home) / "sources" / "seed-verification"
    directory.mkdir(parents=True, exist_ok=True)
    cases, requests = [], []
    start = time.monotonic()
    for case in audit["cases"]:
        paper = case["papers"][0]
        url = re.search(r"https://\S+", paper["access_level"]).group()
        if urlsplit(url).hostname not in {"arxiv.org", "openaccess.thecvf.com"}:
            raise ValueError("Only the expected primary source hosts are supported")
        began = time.monotonic()
        body = b""
        check = {"id": case["id"], "source_url": url, "checked_at": now(),
                 "mechanism_verified": False, "review_status": "operator must examine the recorded primary passages"}
        try:
            request = Request(url, headers={"User-Agent": "ResearchRadar/0.1 bounded citation verification"})
            with urlopen(request, timeout=40) as response:
                body = response.read(30_000_001)
            if len(body) > 30_000_000 or not body.startswith(b"%PDF"):
                raise ValueError("Expected a PDF no larger than 30 MB")
            pdf = directory / (case["id"] + ".pdf")
            text = pdf.with_suffix(".txt")
            pdf.write_bytes(body)
            subprocess.run(["pdftotext", str(pdf), str(text)], check=True, timeout=30, capture_output=True)
            content = text.read_text()
            check.update({
                "sha256": hashlib.sha256(body).hexdigest(),
                "text_sha256": hashlib.sha256(content.encode()).hexdigest(),
                "cache": str(pdf), "text_cache": str(text),
                "identity_verified": normalized_title(paper["title"]) in normalized_title(content[:12000]),
                "quote_verified": compact(paper["quote"]) in compact(content),
                "quote": paper["quote"], "location": paper["evidence_location"],
                "bytes": len(body),
            })
            requests.append({"url": url, "status": "retrieved", "bytes": len(body), "seconds": time.monotonic() - began})
        except Exception as error:
            check.update(identity_verified=False, quote_verified=False, error=str(error))
            requests.append({"url": url, "status": "failed", "error": str(error), "bytes": len(body), "seconds": time.monotonic() - began})
        cases.append(check)
    return {
        "protocol": "Fresh primary-source verification independent of the investigator. Mechanical identity and quotation matching is not a substitute for mechanism examination.",
        "cases": cases, "retrieval_log": requests,
        "costs": {"http_requests": len(requests), "download_bytes": sum(r["bytes"] for r in requests),
                  "elapsed_seconds": time.monotonic() - start, "api_cost_usd": None, "gpu_hours": 0},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, default=ROOT / "pilot" / "blind-audit.json")
    parser.add_argument("--home", type=Path, default=DEFAULT_HOME)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.audit, args.home)
    args.output.write_text(json.dumps(result, indent=2))
    for case in result["cases"]:
        print(case["id"], "identity:", case["identity_verified"], "quote:", case["quote_verified"], case.get("error", ""))


if __name__ == "__main__":
    main()
