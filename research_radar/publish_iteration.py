"""Publish recorded ITERATE evidence without promoting model votes into scientific facts."""

import hashlib
import json

from .archive import Archive
from .core import DEFAULT_HOME, Store, now
from .iteration import DIRECTORY, campaign, save


def load(name):
    return json.loads((DIRECTORY / name).read_text())


def comparison():
    mapping = {row["id"]: row for row in load("review-blinding-key.json")}
    review = load("candidate-blind-review.json")["result"]["assessments"]
    if {r["id"] for r in review} != set(mapping) or len(review) != 6:
        raise ValueError("Missing or repeated candidate review")
    policies = {}
    for policy in ["baseline", "revised"]:
        assessments = [r for r in review if mapping[r["id"]]["policy"] == policy]
        score = load("benchmark-" + policy + "-scores.json")
        policies[policy] = {
            "benchmark": {k: score[k] for k in ["counts", "overlap_recall", "distinct_recall", "balanced_accuracy", "coverage", "passed"]},
            "generated": 3,
            "raw_reviewer_survival_votes": sum(r.get("survives_scientific_audit") is True for r in assessments),
            "raw_reviewer_families": sorted(set(r["mechanism_family"] for r in assessments)),
            "distinct_and_experiment_ready": sum(r.get("novelty") == "distinct" and r.get("experiment_ready") is True for r in assessments),
            "candidate_ids": [r["id"] for r in assessments],
        }
    value = {
        "policies": policies,
        "interpretation": "Raw survival votes are inconsistent with some explanations and are NOT validated survivors. Independent adjudication is authoritative.",
        "observed_review_failure": "R03 was called overlapping because it duplicates generated R01, which is not published prior art. R04 was marked surviving despite an underspecified statistic.",
        "post_measurement_change": "Production prompt now explicitly separates within-campaign duplication from prior art. No retest or effectiveness claim for that added clarification.",
        "historical_baseline": "Original pilot: five overlapping controls only, no false-rejection estimate, zero validated opportunities. Baseline here is a fresh old-policy rerun on identical inputs, not retroactively the original run.",
        "scope": "Single paired-policy run; no causal improvement inference or paper acceptance prediction.",
    }
    save("comparison.json", value)
    return value


def publish():
    independent = load("independent-verdict.json")
    if independent.get("verdict") not in {"GO", "ITERATE", "NO-GO"}:
        raise ValueError("Independent verdict not ready")
    results = comparison()
    store = Store()
    cid = campaign()
    if store.records(cid, "decisions"):
        raise ValueError("Researcher decisions exist; do not overwrite this campaign")
    mapping = {r["id"]: r for r in load("review-blinding-key.json")}
    review_receipt = load("candidate-blind-review.json")
    records = []
    for audit in review_receipt["result"]["assessments"]:
        link = mapping[audit["id"]]
        finding = independent["candidate_findings"][audit["id"]]
        disposition = finding["recommended_disposition"]
        generated = load("generation-" + link["policy"] + ".json")
        original = generated["result"]["opportunities"][link["original_index"]]
        record = dict(original)
        record.update(id="iteration-" + link["policy"] + "-" + original["id"],
                      title=f"[{link['policy']}] {original['title']}",
                      status="rejected" if disposition == "reject" else "deferred" if disposition == "defer" else "awaiting evidence",
                      analysis_status="Unverified generated hypothesis; independent audit has not established scientific readiness",
                      policy=link["policy"], blinded_id=audit["id"],
                      novelty={"classification": finding["audited"]["novelty"], "scope": "Independent source-grounded adjudication; no global novelty proof"},
                      review={"raw_blinded_review": audit, "independent_adjudication": finding,
                              "source_locations": str(DIRECTORY / "independent-validation-report.md")},
                      gaps=original.get("evidence_gaps", []),
                      assessment_history=[
                          {"role": "generator", "job_id": generated["job_id"], "at": generated["completed_at"], "assessment": original},
                          {"role": "reviewer", "job_id": review_receipt["job_id"], "at": review_receipt["completed_at"], "assessment": audit},
                      ])
        record["experiment"].update(authorization="not authorized", status="planned", results=None)
        if disposition == "reject":
            record["rejections"] = [{"reason": finding["recommended_reason"],
                                    "scope": "Submitted proposal as written; not proof of exact published equivalence",
                                    "by": "Independent iteration audit", "at": independent["evidence_cutoff_utc"]}]
        records.append(record)
    cases = []
    for policy in ["baseline", "revised"]:
        for case in load("benchmark-" + policy + "-scores.json")["cases"]:
            cases.append({"id": policy + "-" + case["id"], "title": f"{policy}: {case['id']}",
                          "expected": case["expected"], "observed": case["response"],
                          "status": "PASS" if case["passed"] else "FAIL",
                          "evidence": "Frozen key, independently audited before outcomes; preserved source passages in input-preservation.json"})
    tests = load("software-validation.json")
    validations = [
        {"id": "pilot-go-no-go", "title": "Bounded ITERATE: independent before/after verdict",
         "verdict": independent["verdict"],
         "summary": f"{independent['verdict']}: both policies scored 10/10 on assigned-source controls. This does not establish global novelty discrimination or a valuable research opportunity.",
         "criteria": independent["criterion_flags"],
         "observed": {"raw_comparison": results, "independently_audited": independent["before_after"],
                      "summary": independent["summary"]},
         "evidence": {"report": str(DIRECTORY / "independent-validation-report.md"),
                                          "costs": load("cost-ledger.json")},
         "limitations": ["No expanded search or GPU experiment. No pipeline-level scientific result.",
                         "Prior original source loss remains historical; current iteration evidence is preserved.",
                         "Raw model reviewer votes are not the independent final decision."]},
        {"id": "balanced-discrimination", "title": "Balanced novelty discrimination: two policies, ten controls each",
         "verdict": "PASS (narrow scope)", "summary": "5 overlap and 5 source-distinct ideas; both policies made zero false labels or abstentions.",
         "criteria": load("protocol.json")["benchmark"], "cases": cases,
         "evidence": load("benchmark-ground-truth-audit.json"), "limitations": load("benchmark-key.json")["limitations"]},
        {"id": "current-source-preservation", "title": "Preserved raw sources and claim quotations",
         "verdict": "PASS (current evidence)", "summary": "75 migrated quotations plus 29 benchmark passages have hash-checked raw/text chains; missing historical originals remain explicitly listed.",
         "observed": {"existing_claims": load("source-preservation.json"), "benchmark": load("input-preservation.json")},
         "limitations": ["Integrity is not semantic entailment or independent experimental reproduction."]},
        {"id": "prerequisite-preflight", "title": "Real data, weights and annotation preflight",
         "verdict": "PARTIAL", "summary": "Two actual annotated samples and two released weights verified; full baseline execution and scientific experiment readiness remain blocked.",
         "observed": load("prerequisites.json"), "evidence": load("geometry-preflight.json")},
        {"id": "iteration-software", "title": "Iteration engineering regressions",
         "verdict": "PASS" if tests["passed"] else "FAIL", "summary": f"{tests['test_executions']} test executions, {tests['skipped']} skipped.",
         "cases": tests["cases"], "evidence": tests},
    ]
    store.import_bundle(cid, {"opportunities": records, "validations": validations}, "recorded bounded ITERATE, not a live replay")
    public = load("prerequisites.json")
    previous = [e for e in store.state(cid)["events"] if e["kind"] == "cost" and e["data"].get("receipt") == "iteration-public-requests"]
    if not previous:
        store.event(cid, "cost", "Measured public preflight requests, separate from actual model receipts",
                    {"receipt": "iteration-public-requests", "http_requests": public["public_requests"],
                     "download_bytes": public["download_bytes"], "elapsed_seconds": public["elapsed_seconds"]})
    save("published.json", {"campaign_id": cid, "url": f"http://127.0.0.1:8776/?campaign={cid}#validation",
                           "verdict": independent["verdict"]})
    archive = Archive(DEFAULT_HOME / "archive")
    artifacts = []
    for path in sorted(DIRECTORY.iterdir()):
        if path.is_file() and path.name != "final-preservation.json":
            reference = archive.store_bytes(path.read_bytes(), url=path.as_uri(), media_type="application/octet-stream",
                                             retrieved_at=None, representation="artifact")
            archive.verify_manifest(reference.manifest_sha256)
            artifacts.append({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                              "reference": reference.to_dict()})
    save("final-preservation.json", {"at": now(), "passed": True, "artifacts": artifacts})
    print(cid, independent["verdict"])


if __name__ == "__main__":
    publish()
