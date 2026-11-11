"""Publish real research artifacts without pretending imported work ran live in the UI."""

from copy import deepcopy
import json

from .core import ROOT, Store, now
from .validation import cutoff_corpus, verdict


PILOT = ROOT / "pilot"


def load(name, fallback=None):
    path = PILOT / name
    return json.loads(path.read_text()) if path.exists() else fallback


def browser_receipt(raw):
    steps = raw.get("steps", [])
    passed = len(steps) == 14 and all(s.get("verdict") == "PASS" for s in steps)
    passed = passed and not any(raw.get(key) for key in ("javascript_errors", "http_failures", "request_failures"))
    return {
        **raw, "passed": passed,
        "cases": [{"id": f"UI-{step['step']}", "title": step["name"],
                   "expected": step["expected"], "observed": step["observed"],
                   "status": step["verdict"], "evidence": {"job_ids": step.get("job_ids", []), "recorded_at": step.get("recorded_at")}}
                  for step in steps],
    }


def build():
    bundle = deepcopy(load("literature.json"))
    audit = load("independent-candidate-audit.json", {})
    assessments = {entry["id"]: entry for entry in audit.get("candidates", [])}
    independent = audit.get("independent_search", {})
    threats = independent.get("primary_findings", [])
    for paper in bundle["papers"]:
        details = paper.get("verification")
        if isinstance(details, dict):
            paper["verification_details"] = details
            levels = {e.get("level") for e in paper.get("evidence", [])}
            paper["verification"] = "full paper" if "full paper" in levels else "abstract"
        paper["examination_note"] = "Selected passages examined; not cover-to-cover or an independent reproduction."
    for tension in bundle["tensions"]:
        tension["opportunity_ids"] = [o["id"] for o in bundle["opportunities"] if tension["id"] in o["tension_ids"]]
    for opportunity in bundle["opportunities"]:
        original_priority = opportunity["priority"]
        opportunity["priority_assessment"] = original_priority
        opportunity["priority"] = 4 - original_priority["rank"]
        opportunity["venue_assessment"] = opportunity["venue"]
        opportunity["venue"] = opportunity["venue"]["candidate"]
        opportunity["status"] = "deferred" if opportunity["id"] == "O3" else "awaiting evidence"
        opportunity["review"] = assessments.get(opportunity["id"], opportunity["review"])
        for threat in threats:
            if threat["candidate"] != opportunity["id"]:
                continue
            source_id = "independent-" + opportunity["id"]
            opportunity["prior_art"].append({
                "paper_id": source_id, "title": threat["title"], "url": threat["url"],
                "overlap": threat["mechanism_threat"], "difference": threat["non_equivalence"],
                "source_layer": "subsequent independent candidate search",
            })
            if isinstance(opportunity["review"], dict):
                opportunity["review"]["independently_retrieved_threat"] = threat
            bundle["papers"].append({
                "id": source_id, "title": threat["title"], "authors": [],
                "year": threat["first_posting_year"], "url": threat["url"],
                "venue": "Not independently checked", "family": "adjacent adversarial prior art",
                "task": "candidate mechanism comparison", "datasets": [],
                "relevance": "independent novelty threat", "verification": "full paper",
                "verification_details": {"read": threat["evidence_location"], "version": threat["inspected_version"],
                                         "sha256": threat["sha256"], "metadata_limit": "Author list and final publication venue not independently checked"},
                "contribution": threat["observed"], "mechanism": threat["mechanism_threat"],
                "limitations": threat["non_equivalence"], "evaluation": "Only decisive mechanism/assumption passages examined; no performance claim extracted",
                "source_layer": "Three-reference independent audit, separate from the original 21-paper landscape",
                "evidence": [{"claim": threat["observed"], "quote": threat["quote"], "location": threat["evidence_location"],
                              "source_url": threat["url"], "level": "full paper", "verified": True}],
            })
        if opportunity["id"] == "O3":
            opportunity["rejections"] = [{
                "at": "2026-11-09", "scope": "Broad contribution claim, not every possible narrower method",
                "reason": "Generic diversity/support selection is already anticipated; HF-Net covisibility and RIC-Loc geometry-aware reference selection defeat the broad novelty claim. A specific distinct estimator has not been supplied.",
                "by": "independent novelty/reviewer audit",
            }]
    overlap = load("overlap-results.json")
    integrity = load("source-integrity.json")
    software = load("software-validation.json", {"passed": False, "cases": [], "status": "pending final checks"})
    journey = browser_receipt(load("live-ui-journey.json", {"steps": [], "status": "pending actual browser journey"}))
    criteria = {
        "citation_reliability": {"passed": integrity["passed"] and overlap["passed"],
            "evidence": "134 offline hash/title/quotation/reference checks plus five freshly refetched decisive PDFs. Rejected incorrect provisional identifiers are retained in the failure log.",
            "limitations": "Identity and cited-passage checks do not independently reproduce paper experiments or validate every interpretation."},
        "literature_coverage": {"passed": len(bundle["papers"]) >= 20,
            "evidence": "21 initial papers spanning retrieval, partial/off-nadir matching, sparse/dense correspondences, metric pose, geometry, joint systems and selective localization; three subsequent independent audit references. Five foundations separate.",
            "limitations": "Bounded selective reading; not exhaustive. Classical uncertainty/selection coverage remains limited."},
        "novelty_detection": {"passed": overlap["passed"],
            "evidence": f"{overlap['detected']}/{overlap['total']} blinded seeded overlaps found with correct prior art, independently checked against full primary sources.",
            "limitations": "Five positive cases do not measure specificity, false rejections, memorization-free reasoning or general accuracy."},
        "opportunity_quality": {"passed": False,
            "evidence": "All three candidates underwent independent criticism. O1 remains a conditional diagnostic, O2 faces classical propagation and dense confidence overlap, O3's broad claim is rejected/deferred.",
            "limitations": "No candidate yet has a defensible, sufficiently distinct technical contribution. No paper-acceptance claim."},
        "experimental_feasibility": {"passed": False,
            "evidence": "Concrete 1-3-day CPU-first falsification plans exist with datasets, baselines, metrics, confounders and stop rules.",
            "limitations": "Required released annotations/cached pose outputs, licensing and actual resource budgets have not been independently preflighted. No GPU experiment was launched."},
        "system_reliability": {"passed": False,
            "operational_checks_passed": software.get("passed") is True and journey.get("passed") is True,
            "evidence": {"software": software, "actual_browser_journey": journey},
            "limitations": "Operational persistence/control checks pass when shown above, but archival reproducibility is partial: the original blind PDF cache was prematurely removed. Five decisive sources were freshly restored and hashed; this is recovery, not preservation of the original retrieval snapshot."},
    }
    summary = {
        "id": "pilot-go-no-go", "title": "Minimal end-to-end engineering validation",
        "verdict": verdict(criteria), "criteria": criteria,
        "summary": (
            f"{verdict(criteria)}: {overlap['detected']}/{overlap['total']} seeded overlaps detected; "
            + ("all 14 functional browser steps passed. " if journey["passed"] else "browser acceptance incomplete. ")
            + "No candidate yet has a defensible distinct contribution. Experiment preflight and original-source archival completeness remain unresolved."
        ),
        "cases": overlap["cases"] + software.get("cases", []) + journey.get("cases", []),
        "failures": [
            "No candidate satisfies the credible distinct opportunity gate.",
            "Dataset/annotation/compute preflight remains incomplete.",
            "Model-memory provisional citation locators were wrong and rejected before acceptance.",
            "The live abstract-only smoke proposed an invalid University-1652 GPS initialization; it was not accepted as a viable experiment.",
            "The original runtime fallback admitted unrelated astronomy records. Query conjunction and topical screening were corrected and the real browser run repeated; the contaminated smoke is retained separately and disabled.",
            "Original blind source-cache loss required fresh re-verification of all five decisive papers.",
        ],
        "limitations": [
            "Acceptance thresholds are engineering criteria, not validated predictors of conference acceptance.",
            "No absence of retrieved prior art is treated as proof of novelty.",
            "Role separation and fresh retrieval do not guarantee adequate scientific comparison.",
            "Document date/version filters cannot remove pretrained-model temporal leakage.",
            "USD billing for the coordinating and research agents is unavailable; measured counts and partial usage receipts are disclosed.",
        ],
    }
    historical = cutoff_corpus([
        {"id": "University-1652-v2", "date": "2020-02-27", "examined_version_date": "2020-08-16"},
        {"id": "RoMa-v2", "date": "2023-05-24", "examined_version_date": "2023-12-11"},
        {"id": "SkyReg-current-metadata-unknown-version", "date": next(p["date"] for p in bundle["papers"] if p["id"] == "skyreg")},
    ], "2023-06-01")
    bundle["validations"] = [summary, {
        "id": "candidate-independent-search", "title": "Three independent candidate searches",
        "verdict": "ITERATE", "expected": "Independent adversarial search and primary evidence for all three candidates",
        "observed": independent, "cases": [{"id": t["candidate"], "expected": "Find the strongest overlap and specify any actual distinction",
                                            "observed": t["verdict_update"], "evidence": t} for t in threats],
        "limitations": "Three searches plus three full-paper GETs, not an exhaustive novelty proof. Research questions remain uncertain.",
    }, {
        "id": "historical-cutoff", "title": "Historical calibration: document leakage guard only",
        "verdict": "ITERATE", "expected": "Include University-1652 v2; exclude RoMa v2 after cutoff and undated examined SkyReg version",
        "observed": historical, "passed": [p["id"] for p in historical["included"]] == ["University-1652-v2"],
        "limitations": "Not a blinded retrospective research evaluation. No claim of pretraining-leakage prevention or historical predictive validity.",
    }, {"id": "runtime-smoke", **load("runtime-smoke-observations.json")}]
    cost_sources = [bundle["costs"], load("blind-audit.json")["costs"],
                    load("seed-source-verification.json")["costs"], load("operator-verification-log.json")["costs"]]
    if isinstance(independent.get("costs"), dict):
        cost_sources.append(independent["costs"])
    bundle["costs"] = {
        "http_requests": sum(c.get("http_requests") or 0 for c in cost_sources),
        "download_bytes": sum(c.get("download_bytes") or 0 for c in cost_sources),
        "elapsed_seconds": sum(c.get("elapsed_seconds") or 0 for c in cost_sources),
        "api_cost_usd": None, "gpu_hours": 0,
        "measurement": "Partial aggregate: operator web-fetch byte/time measurements and model billing are unavailable. Runtime smoke is a separately costed campaign.",
    }
    bundle["independent_tensions"] = load("blind-audit.json")["independent_tensions"]
    return bundle


def publish():
    bundle = build()
    store = Store()
    name = "Drone-to-satellite reliability | bounded evidence pilot"
    question = "When does correct drone-to-satellite retrieval fail to support reliable metric localization, and is there a distinct, affordable way to diagnose that failure?"
    campaign = next((c for c in store.state()["campaigns"] if c["name"] == name), None)
    if not campaign:
        campaign = store.create({
            "name": name, "field": bundle["scope"] if isinstance(bundle["scope"], str) else "Drone-to-satellite retrieval versus reliable metric/geometric refinement",
            "config": {"max_papers": 25, "max_requests": 100, "time_budget_seconds": 3600,
                       "queries": ["drone satellite localization geographic reliability"], "question": question, "agent_enabled": True},
        })
    cid = campaign["id"]
    if store.records(cid, "decisions"):
        raise ValueError("This published pilot has researcher decisions. Refusing to overwrite them; import updated artifacts into a new campaign.")
    if not campaign["config"].get("question") and campaign["status"] != "running":
        store.control(cid, "configure", {"config": {"question": question}})
    # Re-publishing validation corrections must not charge the same source work twice.
    cost = bundle.pop("costs")
    store.import_bundle(cid, bundle, "pilot/literature.json + independently recorded validation artifacts")
    with store.db() as db:
        prior = db.execute("SELECT id FROM events WHERE campaign_id=? AND kind='cost' AND message='Bounded pilot measured research cost.'", (cid,)).fetchone()
        if prior:
            db.execute("UPDATE events SET data=? WHERE id=?", (json.dumps(cost), prior["id"]))
        else:
            db.execute("INSERT INTO events(campaign_id,job_id,kind,message,data,created_at) VALUES (?,NULL,'cost',?,?,?)",
                       (cid, "Bounded pilot measured research cost.", json.dumps(cost), now()))
        if campaign["status"] == "waiting":
            db.execute("UPDATE campaigns SET stage='human decision: ITERATE',updated_at=? WHERE id=?", (now(), cid))
    (PILOT / "published-campaign.json").write_text(json.dumps({"campaign_id": cid, "url": "http://127.0.0.1:8776/",
                                                             "verdict": bundle["validations"][0]["verdict"], "costs": cost}, indent=2))
    print(cid, bundle["validations"][0]["verdict"])


if __name__ == "__main__":
    publish()
