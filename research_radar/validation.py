"""Reproducible engineering checks, never a self-assessed quality score."""

import argparse
from datetime import date
import json
from pathlib import Path
import re


def normalized_title(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def cutoff_corpus(papers, cutoff):
    """Require the examined version's date, not just its first publication date."""
    boundary = date.fromisoformat(cutoff)
    included, excluded = [], []
    for paper in papers:
        version_date = paper.get("examined_version_date")
        try:
            published = date.fromisoformat(str(paper["date"])[:10])
            examined = date.fromisoformat(str(version_date)[:10])
        except (ValueError, KeyError):
            excluded.append({"id": paper["id"], "reason": "Missing or invalid publication/examined-version date"})
            continue
        if published > boundary or examined > boundary:
            excluded.append({"id": paper["id"], "reason": "Publication or examined version postdates cutoff"})
        else:
            included.append(paper)
    return {"cutoff": cutoff, "included": included, "excluded": excluded,
            "limitation": "Document cutoff only; cannot establish absence of pretrained-model hindsight leakage"}


def score_overlaps(key, audit, verified):
    """A matching title alone cannot pass: independent mechanism verification is required."""
    observations = {case["id"]: case for case in audit["cases"]}
    checks = {case["id"]: case for case in verified["cases"]}
    cases = []
    for expected in key["cases"]:
        observation = observations.get(expected["id"], {})
        check = checks.get(expected["id"], {})
        candidates = observation.get("papers", [])
        citation_match = any(
            normalized_title(p.get("title")) == normalized_title(expected["title"])
            or any(fragment.lower() in p.get("url", "").lower() for fragment in expected["acceptable_url_fragments"])
            for p in candidates
        )
        substantive = observation.get("classification") in {"already established", "partially overlapping"}
        passed = citation_match and substantive and check.get("identity_verified") is True and check.get("mechanism_verified") is True
        cases.append({
            "id": expected["id"], "title": observation.get("idea", expected["mechanism"]),
            "expected": expected["title"] + ": " + expected["mechanism"],
            "observed": observation.get("observed", "No result"),
            "classification": observation.get("classification", "missing"),
            "status": "pass" if passed else "fail", "passed": passed,
            "evidence": candidates, "independent_verification": check,
        })
    count = sum(case["passed"] for case in cases)
    return {"id": "blind-overlap-test", "title": "Blinded seeded-overlap detection",
            "detected": count, "total": len(cases), "threshold": key["threshold"],
            "passed": count >= key["threshold"], "cases": cases,
            "limitations": key["limitations"], "ground_truth_corrections": key.get("ground_truth_corrections", [])}


def score_discrimination(key, audit):
    """Distinct is positive; abstentions reduce recall and cannot silently disappear."""
    expected = {case["id"]: case for case in key["cases"]}
    observations = audit.get("cases", [])
    ids = [row.get("id") for row in observations]
    if len(ids) != len(set(ids)) or set(ids) - set(expected):
        raise ValueError("Duplicate or unknown benchmark response identifiers")
    counts = dict(true_positive=0, true_negative=0, false_positive=0, false_negative=0, abstained=0)
    cases = []
    for cid, target in expected.items():
        row = next((r for r in observations if r["id"] == cid), {})
        label = row.get("classification", "uncertain")
        # A correct label without a source-grounded explanation is not a detection.
        grounded = bool(row.get("reason", "").strip()) and target["source_id"] in row.get("source_ids", [])
        observed = label if grounded and label in {"distinct", "overlap"} else "uncertain"
        truth = target["expected"]
        if truth not in {"distinct", "overlap"}:
            raise ValueError("Ground truth must distinguish overlap from distinct")
        metric = ("abstained" if observed == "uncertain" else
                  "true_positive" if truth == observed == "distinct" else
                  "true_negative" if truth == observed == "overlap" else
                  "false_positive" if observed == "distinct" else "false_negative")
        counts[metric] += 1
        cases.append({"id": cid, "expected": truth, "observed": observed, "metric": metric,
                      "passed": truth == observed, "response": row})
    positives = sum(c["expected"] == "distinct" for c in key["cases"])
    negatives = len(expected) - positives
    if not positives or not negatives:
        raise ValueError("Discrimination requires both classes")
    distinct_recall = counts["true_positive"] / positives
    overlap_recall = counts["true_negative"] / negatives
    return {
        "positive_class": "distinct contribution within the frozen evidence scope",
        "counts": counts, "cases": cases,
        "distinct_recall": distinct_recall, "overlap_recall": overlap_recall,
        "balanced_accuracy": (distinct_recall + overlap_recall) / 2,
        "coverage": 1 - counts["abstained"] / len(expected),
        "false_novelty_rate": counts["false_positive"] / negatives,
        "false_rejection_rate": counts["false_negative"] / positives,
        "passed": distinct_recall >= key["minimum_recall_per_class"] and overlap_recall >= key["minimum_recall_per_class"],
        "limitations": key["limitations"],
    }


def verdict(criteria):
    mandatory = {"citation_reliability", "literature_coverage", "novelty_detection",
                 "opportunity_quality", "experimental_feasibility", "system_reliability"}
    if not mandatory <= set(criteria):
        return "ITERATE"
    if any(criteria[name].get("fatal") is True for name in ("citation_reliability", "novelty_detection", "system_reliability")):
        return "NO-GO"
    if all(criteria[name].get("passed") is True for name in mandatory):
        return "GO"
    return "ITERATE"


def main():
    parser = argparse.ArgumentParser(description="Re-score fixed overlap cases using independent evidence checks")
    parser.add_argument("key", type=Path)
    parser.add_argument("audit", type=Path)
    parser.add_argument("verification", type=Path)
    args = parser.parse_args()
    result = score_overlaps(*(json.loads(path.read_text()) for path in (args.key, args.audit, args.verification)))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
