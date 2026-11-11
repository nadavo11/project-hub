import unittest

from .validation import cutoff_corpus, score_overlaps, score_discrimination, verdict
from .ranking import DIMENSIONS, rank
from .assemble_pilot import browser_receipt


class ValidationTests(unittest.TestCase):
    def test_constant_rejection_fails_balanced_benchmark(self):
        key = {"cases": [{"id": str(i), "source_id": "s", "expected": "overlap" if i < 5 else "distinct"}
                         for i in range(10)], "minimum_recall_per_class": .8, "limitations": []}
        audit = {"cases": [{"id": str(i), "classification": "overlap", "source_ids": ["s"], "reason": "Fixture"}
                           for i in range(10)]}
        result = score_discrimination(key, audit)
        self.assertFalse(result["passed"])
        self.assertEqual(result["overlap_recall"], 1)
        self.assertEqual(result["false_rejection_rate"], 1)
        self.assertEqual(result["balanced_accuracy"], .5)
        for row in audit["cases"]:
            row["classification"] = "distinct"
        self.assertEqual(score_discrimination(key, audit)["false_novelty_rate"], 1)
        self.assertEqual(score_discrimination(key, {"cases": []})["coverage"], 0)
        for row, target in zip(audit["cases"], key["cases"]):
            row["classification"] = target["expected"]
        self.assertTrue(score_discrimination(key, audit)["passed"])
        audit["cases"].append(audit["cases"][0])
        with self.assertRaises(ValueError):
            score_discrimination(key, audit)

    def test_browser_acceptance_requires_all_steps_and_no_errors(self):
        steps = [{"step": i, "name": "Fixture", "expected": "Control works",
                  "observed": "Persisted", "verdict": "PASS"} for i in range(1, 15)]
        self.assertFalse(browser_receipt({})["passed"])
        self.assertFalse(browser_receipt({"steps": steps[:13]})["passed"])
        self.assertTrue(browser_receipt({"steps": steps})["passed"])
        self.assertFalse(browser_receipt({"steps": steps, "javascript_errors": ["crash"]})["passed"])

    def test_future_revision_and_unknown_date_excluded(self):
        result = cutoff_corpus([
            {"id": "eligible", "date": "2020-02-27", "examined_version_date": "2020-08-16"},
            {"id": "leak", "date": "2020-02-27", "examined_version_date": "2024-01-01"},
            {"id": "unknown", "date": "2020-02-27"},
            {"id": "future", "date": "2023-01-01", "examined_version_date": "2023-01-01"},
        ], "2021-12-31")
        self.assertEqual([p["id"] for p in result["included"]], ["eligible"])
        self.assertEqual(len(result["excluded"]), 3)

    def test_overlap_requires_independent_evidence(self):
        key = {"cases": [{"id": "B1", "title": "Actual paper", "mechanism": "Mechanism",
                          "acceptable_url_fragments": ["example.org/actual"]}], "threshold": 1, "limitations": []}
        audit = {"cases": [{"id": "B1", "classification": "already established",
                            "papers": [{"title": "Actual paper", "url": "https://example.org/actual"}]}]}
        self.assertFalse(score_overlaps(key, audit, {"cases": []})["passed"])
        check = {"cases": [{"id": "B1", "identity_verified": True, "mechanism_verified": True}]}
        self.assertTrue(score_overlaps(key, audit, check)["passed"])
        audit["cases"][0]["classification"] = "uncertain"
        self.assertFalse(score_overlaps(key, audit, check)["passed"])

    def test_missing_criteria_never_go(self):
        self.assertEqual(verdict({}), "ITERATE")
        criteria = {name: {"passed": True} for name in [
            "citation_reliability", "literature_coverage", "novelty_detection",
            "opportunity_quality", "experimental_feasibility", "system_reliability",
        ]}
        self.assertEqual(verdict(criteria), "GO")
        criteria["opportunity_quality"]["passed"] = False
        self.assertEqual(verdict(criteria), "ITERATE")
        criteria["novelty_detection"]["fatal"] = True
        self.assertEqual(verdict(criteria), "NO-GO")

    def test_ranking_does_not_impute_missing_judgments(self):
        self.assertIsNone(rank([{"id": "untested"}], {})[0]["score"])
        dimensions = {key: {"score": 2, "reason": "Synthetic test judgment"} for key in DIMENSIONS}
        dimensions["novelty"]["score"] = 4
        result = rank([{"id": "scored", "assessment_dimensions": dimensions}], {"novelty": 3})[0]
        self.assertEqual(result["score"], 2.6)
        self.assertIn("not a calibrated", result["interpretation"])
