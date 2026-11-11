"""Publish the bounded mechanism experiment without converting review votes into findings."""

import json
import hashlib
from pathlib import Path

from .archive import Archive
from .core import DEFAULT_HOME, ROOT, Store
from .mechanism_campaign import DIRECTORY, SOURCES, campaign, load, persist


def publish():
    if (DIRECTORY / "published.json").exists():
        return
    verdict = load("independent-verdict.json")
    if verdict.get("verdict") not in {"GO", "ITERATE", "NO-GO"}:
        raise ValueError("Independent verdict missing")
    store = Store()
    cid = campaign()
    if store.records(cid, "decisions"):
        raise ValueError("Researcher decisions exist; do not overwrite this campaign")
    diagnostics = load("diagnostic-results.json")
    dispositions = {row["id"]: row for row in verdict["finalist_dispositions"]}
    selected = load("shortlist-selection.json")["ids"]
    if set(dispositions) != set(selected):
        raise ValueError("Independent disposition missing or unexpected")
    records = []
    for identifier in selected:
        record = store.find_record("opportunities", identifier, cid)
        receipt = load(f"review-{identifier}.json")
        raw = receipt["result"]
        finding = dispositions[identifier]
        status = "awaiting evidence" if finding["status"].startswith("revise") else {
            "reject": "rejected", "defer": "deferred"}.get(finding["status"], finding["status"])
        if status not in {"rejected", "awaiting evidence", "deferred", "experiment ready"}:
            raise ValueError("Unsupported scientific disposition")
        record["status"] = status
        record["review"] = {"independent_adjudication": finding, "raw_model_review": raw,
                            "review_errors": verdict["review_errors"],
                            "authority": "Independent source/diagnostic audit overrides provisional screening and model votes"}
        record["novelty"] = {"assessment": finding, "limit": "No exhaustive novelty proof; internal ideas are not publications"}
        record["analysis_status"] = "Independently adjudicated as written; no full candidate performance experiment"
        for reason in record.get("elimination_reasons", []):
            reason["stage"] = "Provisional screening; see independent adjudication"
        for reason in finding["elimination_reasons"]:
            record["elimination_reasons"].append(dict(reason, by="Independent mechanism audit", stage="Final adjudication"))
        for prior in raw["closest_prior_art"]:
            if not any(p.get("paper_id") == prior["paper_id"] for p in record["prior_art"]):
                record["prior_art"].append({"paper_id": prior["paper_id"], "overlap": prior["equivalence"],
                                           "difference": prior["remaining_difference"],
                                           "verification": "Model comparison; consult independent adjudication and preserved primary text"})
        if not any(h.get("job_id") == receipt["job_id"] for h in record["assessment_history"]):
            record["assessment_history"].append({"role": "novelty", "job_id": receipt["job_id"],
                                                 "at": receipt["completed_at"], "assessment": raw})
        record["experiment"]["results"] = {
            "record_type": "experimental_observation", "scope": "Necessary-condition diagnostic only; not the planned experiment",
            "observation": next(r for r in diagnostics["results"] if r["candidate_id"] == identifier),
            "protocol": str(DIRECTORY / "diagnostic-protocol.json"), "full_performance_experiment_run": False,
            "experimentally_supported_hypothesis": False,
        }
        record["gaps"] = [r["reason"] for r in finding["elimination_reasons"]]
        records.append(record)
    software = load("final-checks/software-validation.json")
    costs = load("cost-ledger.json")
    cases = [{"id": r["id"], "title": f"{r['candidate_id']}: necessary-condition diagnostic",
              "expected": r["expected"], "observed": r["observed"], "status": "DIAGNOSTIC ONLY",
              "evidence": r["conclusion"]} for r in diagnostics["results"]]
    validations = [
        {"id": "pilot-go-no-go", "title": "Mechanism-first discovery: independent verdict",
         "verdict": verdict["verdict"], "summary": verdict["summary"],
         "expected": "At least one independently defensible mechanism, with experimental support before claiming discovery improvement",
         "observed": {"summary": verdict["summary"], "generated": 12, "independently_reviewed": 3,
                      "defensible_as_written": verdict["defensible_as_written"],
                      "experimentally_supported": verdict["experimentally_supported"],
                      "before_after": verdict["before_after"]},
         "evidence": {"report": str(DIRECTORY / "independent-validation-report.md"),
                      "costs": {k: costs[k] for k in ("direct_cli_calls", "public_requests", "response_bytes",
                                                     "cpu_diagnostic_seconds", "gpu_hours", "dollar_cost")}},
         "independent_report": verdict, "cost_ledger": costs,
         "limitations": verdict["methodology_limits"]},
        {"id": "mechanism-diagnostics", "title": "Three frozen CPU diagnostics, not performance validation",
         "verdict": "LIMITED", "cases": cases, "observed": diagnostics,
         "summary": "Conditional MAP counterexample, Schur identity, and uniform-height gauge check; zero full hypothesis experiments."},
        {"id": "generation-screening", "title": "Twelve original mechanisms and elimination history",
         "verdict": "RECORDED", "observed": load("shortlist.json")["result"],
         "evidence": {"original_candidates": load("candidates.json"), "selection": load("shortlist-selection.json")},
         "failures": verdict["review_errors"], "limitations": ["Screening is provisional; not all twelve received external novelty audits."]},
        {"id": "source-and-prerequisites", "title": "Primary source correction and practical prerequisites",
         "verdict": "PARTIAL", "observed": load("prerequisite-status.json"),
         "evidence": {"correction": load("grounding-correction.json"), "citation_checks": load("review-citation-checks.json")},
         "failures": ["A byte-valid original L1 quotation did not support its claim; appended correction retained the defective input."]},
        {"id": "mechanism-software", "title": "Engineering regression and restart persistence",
         "verdict": "PASS" if software["passed"] else "FAIL", "observed": software,
         "cases": software["cases"], "evidence": load("restart-verification.json")},
    ]
    store.import_bundle(cid, {"opportunities": records, "validations": validations},
                        "Actual bounded mechanism-first artifacts; not simulated live activity")
    requests = [json.loads(line) for line in (SOURCES / "requests.jsonl").read_text().splitlines()]
    if not any(e["kind"] == "cost" and e["data"].get("receipt") == "mechanism-public-requests" for e in store.state(cid)["events"]):
        store.event(cid, "cost", "Measured targeted primary-source requests", {
            "receipt": "mechanism-public-requests", "http_requests": len(requests),
            "download_bytes": sum(r["bytes"] for r in requests),
            "elapsed_seconds": sum(r["elapsed_seconds"] for r in requests)})
    persist("published.json", {"campaign_id": cid, "url": f"http://127.0.0.1:8776/?campaign={cid}#validation",
                              "verdict": verdict["verdict"]})
    print(cid, verdict["verdict"])


def finalize():
    if (DIRECTORY / "final-preservation.json").exists():
        return
    store = Store()
    cid = campaign()
    live = load("live-ui-verification.json")
    if not live["passed"]:
        raise ValueError("Final real-data UI verification did not pass")
    engineering = store.find_record("validations", "mechanism-software", cid)
    engineering["evidence"] = {"restart": load("restart-verification.json"), "live_ui": live}
    store.put(cid, "validations", engineering)
    sources = store.find_record("validations", "source-and-prerequisites", cid)
    sources["evidence"]["final_locator_correction"] = load("final-source-correction.json")
    store.put(cid, "validations", sources)
    for identifier in ("mf-bundle", "mf-degeneracy", "mf-spectral", "mf-metrology"):
        paper = store.find_record("papers", identifier, cid)
        paper["family"] = "Estimation theory and uncertainty"
        paper["verification"] = {
            "read": "Title, abstract and selected method passages; not a full evaluation review",
            "source": "Full PDF preserved; identities and decisive quoted passages independently checked",
            "limit": "Not independent experimental reproduction",
        }
        for evidence in paper["evidence"]:
            evidence.update(level="primary method passage", verified=True)
        store.put(cid, "papers", paper)
    archive = Archive(DEFAULT_HOME / "archive")
    paths = [p for p in DIRECTORY.rglob("*") if p.is_file()]
    paths.append(SOURCES / "requests.jsonl")
    paths.extend(Path(p) for p in live["screenshots"])
    paths.append(Path(live["screenshots"][0]).parent / "mechanism-live-check.py")
    for receipt in load("cost-ledger.json")["cli_receipts"]:
        paths.extend(p for p in (DEFAULT_HOME / "runs" / receipt["job"]["id"]).iterdir() if p.is_file())
    paths.extend(ROOT / name for name in [
        "mechanism_campaign.py", "mechanism_evidence.py", "mechanism_diagnostics.py", "publish_mechanism.py",
        "core.py", "worker.py", "static/app.js", "test_core.py", "test_ui.py", "test_iteration.py"])
    artifacts = []
    for path in sorted(set(paths)):
        reference = archive.store_bytes(path.read_bytes(), url=path.as_uri(), media_type="application/octet-stream",
                                         retrieved_at=None, representation="artifact")
        archive.verify_manifest(reference.manifest_sha256)
        artifacts.append({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                          "reference": reference.to_dict()})
    snapshot = store.state(cid)
    persist("final-preservation.json", {
        "passed": True, "artifacts": artifacts, "campaign_id": cid,
        "published_records": {kind: len(snapshot[kind]) for kind in ("papers", "opportunities", "validations")},
        "final_source_correction": load("final-source-correction.json"),
        "scope": "Independent report, original hypotheses, failures, sources, exact model traces, usage and engineering receipts retained. Hash integrity is not scientific support.",
    })
    print("Final evidence archive verified:", len(artifacts), "artifacts")


if __name__ == "__main__":
    publish()
    if (DIRECTORY / "live-ui-verification.json").exists():
        finalize()
