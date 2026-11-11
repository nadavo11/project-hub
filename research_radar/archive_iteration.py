"""Verify and preserve the bounded iteration's source passages and local receipts."""

import hashlib
import json
from pathlib import Path

from .archive import Archive, Reference
from .core import DEFAULT_HOME, ROOT
from .iteration import DIRECTORY, save


def preserve_inputs():
    archive = Archive(DEFAULT_HOME / "archive")
    packet = json.loads((DIRECTORY / "benchmark-input.json").read_text())
    key = json.loads((DIRECTORY / "benchmark-key.json").read_text())
    preflight = json.loads((DIRECTORY / "prerequisites.json").read_text())
    sources = {r["url"]: r for r in preflight["sources"]}
    claims = []
    for source in packet["sources"]:
        entry = sources[source["url"]]
        raw, text = Reference(**entry["source"]), Reference(**entry["text"])
        extracted = archive.read(text).decode()
        for excerpt in source["excerpts"]:
            quote = excerpt["quote"]
            start = extracted.index(quote)
            digest = archive.record_claim(
                claim=f"Discrimination control {source['id']}: exact reference passage, not a global novelty claim",
                source=raw, text=text, quote=quote, start=start, end=start + len(quote),
                location=excerpt["location"], provenance={"scope": "benchmark reference", "cutoff": source["examined_version_date"]})
            archive.verify_manifest(digest)
            claims.append({"source_id": source["id"], "manifest": digest})
    retrievals = json.loads((ROOT / "sources/retrieval-log.json").read_text())
    for case in key["cases"]:
        if case["expected"] != "distinct":
            continue
        target = case["later_published_target"]
        path = Path(target["text_path"])
        matching = [r for r in retrievals if r.get("text_cache") == str(path.relative_to(ROOT))]
        if not matching and path.name.endswith(".full.txt"):
            html_path = str(path.with_suffix(".html").relative_to(ROOT))
            matching = [r for r in retrievals if r.get("cache") == html_path and r.get("status") == "ok"]
        if not matching:
            raise ValueError(f"No original raw response link for {path}")
        row = matching[-1]
        raw_bytes = (ROOT / row["cache"]).read_bytes()
        if hashlib.sha256(raw_bytes).hexdigest() != row["sha256"]:
            raise ValueError("Original target source hash mismatch")
        raw = archive.store_bytes(raw_bytes, url=row["url"], media_type=row.get("content_type", "application/octet-stream"),
                                  retrieved_at=row["accessed_at"])
        text = archive.store_text(path.read_text(), raw=raw, extraction="Retained pilot extraction; exact bytes linked to original retrieval log",
                                  provenance={"limitation": "Extraction transformation is recorded, not independently reproduced here"})
        extracted = archive.read(text).decode()
        for excerpt in target["excerpts"]:
            quote = excerpt["quote"]
            start = extracted.index(quote)
            digest = archive.record_claim(claim=f"{case['id']}: later published mechanism control, not proof of global historical novelty",
                source=raw, text=text, quote=quote, start=start, end=start + len(quote), location=excerpt["location"])
            archive.verify_manifest(digest)
            claims.append({"case": case["id"], "target": target["url"], "manifest": digest})
    artifacts = []
    for name in ["protocol.json", "benchmark-input.json", "benchmark-key.json", "benchmark-freeze.json",
                 "benchmark-ground-truth-audit.json", "candidate-diagnosis.json", "prerequisites.json",
                 "review-instructions.txt", "prompt-freeze.json"]:
        path = DIRECTORY / name
        reference = archive.store_bytes(path.read_bytes(), url=path.as_uri(), media_type="application/json" if path.suffix == ".json" else "text/plain",
                                         retrieved_at=None, representation="artifact")
        archive.verify_manifest(reference.manifest_sha256)
        artifacts.append({"path": str(path), "reference": reference.to_dict()})
    save("input-preservation.json", {"passed": True, "claims": claims, "artifacts": artifacts,
                                   "scope": "Integrity and exact quotation provenance, not semantic truth or global novelty"})
    return len(claims)


if __name__ == "__main__":
    print(f"Preserved and verified {preserve_inputs()} benchmark source passages.")
