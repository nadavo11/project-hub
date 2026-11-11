"""Browser regressions against an isolated, real RadarServer and SQLite store.

Run from project-hub: python3 -m unittest -v research_radar.test_ui
Requires Playwright and Chromium (RADAR_TEST_CHROME overrides its executable).
All scientific records below are explicitly labelled test fixtures, not findings.
No worker, external retrieval, model invocation, or GPU execution is started.
"""

import os
import base64
import json
from pathlib import Path
import shutil
import threading
import unittest
from unittest.mock import patch
import uuid

try:
    from playwright.sync_api import sync_playwright, expect
except ImportError:
    sync_playwright = None

from .core import Store
from .server import RadarServer


@unittest.skipIf(sync_playwright is None, "Playwright is required for browser tests")
class ResearchRadarBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = Path("research_radar") / f".ui-{uuid.uuid4().hex[:8]}"
        cls.scratch.mkdir(parents=True)
        cls.addClassCleanup(shutil.rmtree, cls.scratch)
        cls.env = patch.dict(os.environ, {"TMPDIR": str(cls.scratch.resolve())})
        cls.env.start()
        cls.addClassCleanup(cls.env.stop)
        cls.playwright = sync_playwright().start()
        cls.addClassCleanup(cls.playwright.stop)
        cls.browser = cls.playwright.chromium.launch(
            executable_path=os.environ.get("RADAR_TEST_CHROME", "/usr/bin/google-chrome"),
            args=["--no-sandbox"],
        )

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()

    def setUp(self):
        self.store = Store(self.scratch / uuid.uuid4().hex)
        self.server = RadarServer(("127.0.0.1", 0), self.store)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 1000})
        self.page = self.context.new_page()
        self.errors = []
        self.csp_errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.on("console", lambda msg: self.csp_errors.append(msg.text) if "Content Security Policy" in msg.text else None)
        self.page.set_default_timeout(7000)

    def tearDown(self):
        self.context.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.assertEqual(self.errors, [], "Frontend JavaScript errors")
        self.assertEqual(self.csp_errors, [], "Frontend must respect the backend CSP")

    def create_campaign(self, name="UI fixture campaign"):
        return self.store.create({
            "name": name, "field": "UI test fixtures, not scientific findings",
            "config": {"question": "Can the research workbench preserve provenance?",
                       "queries": ["fixture retrieval"], "agent_enabled": False},
        })

    def open(self, campaign=None, view="observatory"):
        query = f"?campaign={campaign['id']}" if campaign else ""
        self.page.goto(f"{self.url}/{query}#{view}")
        expect(self.page.locator("#connection")).to_have_text("State synchronized")

    def refresh(self):
        self.page.get_by_role("button", name="Refresh research state").click()

    def test_validation_links_open_pointmatch_without_trusting_html_or_schemes(self):
        campaign = self.create_campaign()
        url = "http://127.0.0.1:8013/?pair=fixture-only#annotations"
        self.store.put(campaign["id"], "validations", {
            "id": "review-links-fixture", "title": "Synthetic annotation handoff",
            "verdict": "ITERATE",
            "evidence": [
                {"url": url, "label": "Open PointMatch review"},
                {"url": "javascript:alert(1)", "label": "<img src=x onerror=alert(1)>"},
            ],
        })
        self.open(campaign, "validation")
        link = self.page.get_by_role("link", name="Open PointMatch review", exact=False)
        expect(link).to_have_attribute("href", url)
        expect(link).to_have_attribute("rel", "noopener noreferrer")
        expect(self.page.locator('a[href^="javascript:"]')).to_have_count(0)
        expect(self.page.locator("main img")).to_have_count(0)
        expect(self.page.get_by_text("<img src=x onerror=alert(1)>", exact=True)).to_be_visible()

    def test_failure_atlas_filters_measurements_without_inventing_pose(self):
        atlas = self.store.home / "failure-atlas"
        case_dir = atlas / "cases" / "any_fixture"
        case_dir.mkdir(parents=True)
        observation = {
            "count": 2, "counts": {"detected_query": 12, "detected_target": 15},
            "query_coverage": {"hull_fraction": .2, "occupied_grid_fraction": .3},
            "target_coverage": {"hull_fraction": .3},
            "homography": {"inliers": 2, "median_inlier_residual_px": .1},
            "pose": {"status": "unsupported", "horizontal_error_m": None, "reason": "Fixture has no DSM"},
            "controls": {}, "stage": "missing metric geometry",
            "causal_status": "Test fixture, not a finding", "confidence_semantics": "Not probability",
            "point_accuracy_reason": "No point GT", "device": "cpu", "cpu_seconds": .01, "wall_seconds": .02,
            "matches": [
                {"q": [10, 10], "t": [12, 12], "confidence": .8, "h_inlier": True, "h_residual": .1, "p_inlier": False, "p_residual": None},
                {"q": [20, 20], "t": [22, 22], "confidence": .3, "h_inlier": False, "h_residual": 10, "p_inlier": False, "p_residual": None},
            ],
        }
        case = {
            "id": "any_fixture", "dataset": "AnyVisLoc", "scene": "Fixture", "query_id": "Fixture query",
            "target_id": "Fixture target", "query_size": [40, 30], "target_size": [40, 40],
            "camera": {"metric_pose_supported": False},
            "geography": {"status": "scene verified; crop overlap unresolved", "evidence": "UI fixture"},
            "methods": {method: {k: v for k, v in observation.items() if k != "matches"} for method in ("sift", "roma-official")},
        }
        (atlas / "atlas.json").write_text(json.dumps({"complete": False, "cases": [case], "counts": {"AnyVisLoc/sift": {"missing metric geometry": 1}}}))
        (atlas / "protocol.json").write_text('{"scope":"UI fixture, not scientific evidence"}')
        (case_dir / "case.json").write_text(json.dumps(case))
        (case_dir / "sift.json").write_text(json.dumps(observation))
        (case_dir / "roma-official.json").write_text(json.dumps(observation))
        pixel = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6Bx8AAAAASUVORK5CYII=")
        for side in ("query", "target", "confidence"):
            (case_dir / f"{side}.png").write_bytes(pixel)
        self.page.goto(self.url + "/atlas.html")
        expect(self.page.get_by_text("This baseline has not completed")).to_be_visible()
        self.page.get_by_role("button", name="SIFT + mutual ratio", exact=True).click()
        expect(self.page.get_by_text("Metric pose unsupported", exact=True)).to_be_visible()
        expect(self.page.locator("#match-legend")).to_contain_text("2 / 2 matches")
        self.page.get_by_label("Minimum match confidence").focus()
        self.page.get_by_label("Minimum match confidence").press("End")
        expect(self.page.locator("#match-legend")).to_contain_text("0 / 2 matches")
        self.page.get_by_label("Minimum match confidence").press("Home")
        self.page.get_by_label("Homography inliers only").check()
        expect(self.page.locator("#match-legend")).to_contain_text("1 / 2 matches")
        self.page.get_by_label("Inspect match index").fill("0")
        expect(self.page.locator("#match-inspector")).to_contain_text("correctness unknown")
        self.page.get_by_label("Find a case").fill("no-such-fixture")
        expect(self.page.get_by_text("No cases match these filters.", exact=False)).to_be_visible()
        response = self.page.request.get(self.url + "/api/atlas/cases/any_fixture/sift")
        self.assertEqual(response.status, 200)
        self.assertIsNone(response.json()["pose"]["horizontal_error_m"])
        self.assertEqual(self.page.request.get(self.url + "/api/atlas/cases/any_fixture/unknown").status, 404)
        self.assertEqual(self.page.request.get(self.url + "/atlas-assets/any_fixture/../../radar.sqlite").status, 404)
        outside = self.store.home / "outside.png"
        outside.write_bytes(b"not an atlas asset")
        (case_dir / "query.png").unlink()
        (case_dir / "query.png").symlink_to(outside)
        self.assertEqual(self.page.request.get(self.url + "/atlas-assets/any_fixture/query.png").status, 404)
        (case_dir / "query.png").unlink()
        (case_dir / "query.png").write_bytes(pixel)
        self.page.get_by_role("button", name="RoMa · upstream sample", exact=True).click()
        self.page.get_by_label("Raw confidence map").check()
        expect(self.page.locator("#match-legend")).to_contain_text("No per-image renormalization")
        self.assertEqual(self.page.locator('#match-view image[href$="confidence.png"]').get_attribute("preserveAspectRatio"), "none")
        self.page.reload()
        expect(self.page.get_by_text("Metric pose unsupported", exact=True)).to_be_visible()
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), 391)

    def seed_scientific_fixtures(self):
        campaign = self.create_campaign()
        cid = campaign["id"]
        self.store.put(cid, "papers", {
            "id": "paper-fixture", "title": "Fixture paper: matched controls",
            "authors": ["Fixture Author"], "date": "2025-03-01", "year": 2025,
            "venue": "FixtureVenue", "task": "retrieval", "family": "contrastive",
            "datasets": ["FixtureDataset"], "relevance": "direct", "url": "https://example.org/fixture-paper",
            "verification": "abstract only", "contribution": "Fixture contribution, not a finding.",
            "mechanism": "Fixture mechanism", "limitations": ["Fixture evidence only"],
            "evidence": [{"claim": "Fixture claim", "source_url": "https://example.org/fixture-paper",
                          "location": "Abstract", "level": "abstract", "quote": "Fixture quotation",
                          "verified": False}],
        })
        self.store.put(cid, "papers", {
            "id": "paper-other", "title": "Fixture paper: distinct family",
            "url": "https://example.org/other", "year": 2022, "venue": "OtherVenue",
            "family": "geometry", "task": "pose", "datasets": ["OtherDataset"], "relevance": "indirect",
        })
        self.store.put(cid, "tensions", {
            "id": "tension-fixture", "title": "Fixture tension: unmatched protocols",
            "observation": "Fixture protocols differ.", "paper_ids": ["paper-fixture"],
            "explanations": ["Fixture confound"], "unresolved": "Matched controls are missing.",
            "opportunity_ids": ["idea-0"], "evidence": [],
        })
        for i in range(4):
            self.store.put(cid, "opportunities", {
                "id": f"idea-{i}", "title": f"Fixture hypothesis {i}",
                "status": "newly proposed", "priority": i,
                "hypothesis": f"Fixture testable prediction {i}.", "question": "Fixture question?",
                "contribution": "Fixture proposed control.", "significance": "Unassessed fixture.",
                "novelty": "Unverified fixture inference.",
                "prior_art": [{"paper_id": "paper-fixture", "overlap": "Fixture overlap",
                              "difference": "Fixture difference requiring evidence"}],
                "tension_ids": ["tension-fixture"], "review": {"concerns": ["Fixture evidence gap"]},
                "experiment": {"hypothesis": "Fixture prediction", "datasets": ["FixtureDataset"],
                               "baselines": ["Fixture baseline"], "metrics": ["Fixture metric"],
                               "success": "Fixture threshold", "falsification": "Fixture null result",
                               "compute": "Not estimated", "status": "plan only"},
                "comments": [], "gaps": ["No empirical execution"],
            })
        self.store.put(cid, "validations", {
            "id": "validation-fixture", "title": "Fixture validation record", "verdict": "inconclusive",
            "criteria": "Fixture criterion", "cases": [
                {"title": "Fixture provenance case", "expected": "Source location retained",
                 "observed": "Abstract location retained", "evidence": {"record": "paper-fixture"},
                 "verdict": "pass"}
            ], "failures": [], "limitations": ["Fixture does not establish scientific validity"],
            "additional_schema": {"custom_field": "Generic fallback retained"},
        })
        return campaign

    def test_p0_campaign_creation_controls_and_persistence(self):
        self.open()
        expect(self.page.get_by_text("Find the question worth")).to_be_visible()
        self.page.get_by_role("button", name="New campaign", exact=True).click()
        dialog = self.page.get_by_role("dialog")
        dialog.get_by_label("Campaign name").fill("Browser-created fixture")
        dialog.get_by_label("Research field").fill("UI regression testing")
        dialog.get_by_label("Scientific question").fill("Are campaign controls persisted?")
        dialog.get_by_label("Retrieval queries").fill("fixture query")
        dialog.get_by_label("Additional configuration").fill('{"agent_enabled": false}')
        dialog.get_by_role("button", name="Create campaign", exact=True).click()
        expect(dialog).not_to_be_visible()
        self.page.get_by_role("button", name="Start research").click()
        expect(self.page.locator("#campaign-status")).to_contain_text("running")
        expect(self.page.get_by_role("button", name="Configure", exact=True)).to_be_disabled()
        self.page.get_by_role("button", name="Pause", exact=False).first.click()
        expect(self.page.locator("#campaign-status")).to_contain_text("paused")
        self.page.get_by_role("button", name="Configure", exact=True).click()
        self.page.get_by_role("dialog").get_by_label("Campaign name").fill("Configured fixture")
        self.page.get_by_role("dialog").get_by_role("button", name="Save configuration").click()
        expect(self.page.locator("#campaign-status")).to_contain_text("Configured fixture")
        self.page.get_by_role("button", name="Resume", exact=False).first.click()
        expect(self.page.locator("#campaign-status")).to_contain_text("running")
        self.page.reload()
        expect(self.page.locator("#campaign-status")).to_contain_text("Configured fixture")
        self.page.get_by_role("button", name="Cancel", exact=True).click()
        self.page.get_by_role("dialog").get_by_role("button", name="Cancel campaign", exact=True).click()
        expect(self.page.locator("#campaign-status")).to_contain_text("cancelled")
        saved = self.store.state()
        self.assertEqual(saved["campaigns"][0]["name"], "Configured fixture")
        self.assertTrue(saved["jobs"])
        self.assertEqual(saved["costs"]["api_cost_usd"], None)
        expect(self.page.locator("#cost-summary")).to_contain_text("API not measured")
        expect(self.page.get_by_role("button", name="Start research")).to_have_count(0)

    def test_p0_evidence_to_decision_and_authorization(self):
        c = self.seed_scientific_fixtures()
        self.open(c, "tensions")
        self.page.get_by_role("button", name="Fixture tension: unmatched protocols", exact=False).click()
        self.page.get_by_role("button", name="Fixture hypothesis 0", exact=False).click()
        expect(self.page.get_by_role("heading", name="Fixture hypothesis 0")).to_be_visible()
        self.page.get_by_role("tab", name="Prior art", exact=True).click()
        expect(self.page.get_by_text("Fixture difference requiring evidence", exact=True)).to_be_visible()
        self.page.get_by_role("tab", name="Prior art", exact=True).press("ArrowRight")
        expect(self.page.get_by_role("tab", name="Review", exact=True)).to_be_focused()
        self.page.locator("#decision-action").select_option("reject")
        self.page.locator("#decision-dimension").select_option("insufficient_evidence")
        self.page.get_by_label("Reason / research note").fill("Fixture rejection: matched control missing.")
        self.page.get_by_role("button", name="Save research judgment").click()
        expect(self.page.locator(".detail-heading")).to_be_visible()
        expect(self.page.locator("#toast")).to_have_text("Research judgment saved.")
        self.assertEqual(self.store.find_record("opportunities", "idea-0")["status"], "rejected")
        self.page.locator("#decision-action").select_option("reopen")
        self.page.get_by_label("Reason / research note").fill("Fixture reopening: test the missing control.")
        self.page.get_by_role("button", name="Save research judgment").click()
        expect(self.page.locator("#decision-form textarea[name=reason]")).to_have_value("")
        self.page.get_by_role("tab", name="Experiment", exact=True).click()
        self.page.get_by_role("button", name="Record experiment authorization").click()
        self.page.get_by_role("dialog").get_by_label("Authorization reason").fill("Fixture permission only, no execution.")
        self.page.get_by_role("dialog").get_by_role("button", name="Record permission only").click()
        expect(self.page.get_by_role("dialog")).not_to_be_visible()
        record = self.store.find_record("opportunities", "idea-0")
        self.assertEqual(record["experiment"]["authorization"]["reason"], "Fixture permission only, no execution.")
        self.assertNotIn("results", record["experiment"])
        self.assertEqual(self.store.state(c["id"])["costs"]["gpu_hours"], 0)
        self.page.get_by_role("tab", name="Decisions", exact=True).click()
        expect(self.page.locator("#candidate-panel").get_by_text("Fixture rejection: matched control missing.", exact=True)).to_have_count(1)

    def test_p1_reason_dimension_persists_and_reopening_retains_history(self):
        c = self.seed_scientific_fixtures()
        self.open(c, "board")
        self.page.get_by_role("button", name="Fixture hypothesis 0", exact=True).click()
        form = self.page.locator("#decision-form")
        form.locator("#decision-action").select_option("reject")
        form.get_by_label("Reason / research note").fill("Fixture novelty blocker with <literal> text.")
        form.get_by_role("button", name="Save research judgment").click()
        self.assertTrue(form.locator("#decision-dimension").evaluate("(el) => el.validity.valueMissing"))
        self.assertEqual(self.store.find_record("opportunities", "idea-0")["status"], "newly proposed")
        form.locator("#decision-dimension").select_option("novelty")
        self.page.get_by_role("tab", name="Prior art", exact=True).click()
        expect(form.locator("#decision-dimension")).to_have_value("novelty")
        expect(self.page.locator("#candidate-panel").get_by_text("External publication", exact=True)).to_be_visible()
        expect(self.page.locator("#candidate-panel").get_by_text("Internal hypothesis · not prior art", exact=True)).to_be_visible()
        with self.page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/decision")) as sent:
            form.get_by_role("button", name="Save research judgment").click()
        self.assertEqual(sent.value.post_data_json["dimension"], "novelty")
        expect(form.locator("textarea[name=reason]")).to_have_value("")
        saved = self.store.find_record("opportunities", "idea-0")
        self.assertEqual(saved["elimination_reasons"][-1]["dimension"], "novelty")
        self.assertEqual(saved["rejections"][-1]["dimension"], "novelty")
        self.assertEqual(saved["record_type"], "internal_hypothesis")
        self.page.reload()
        expect(self.page.locator("#connection")).to_have_text("State synchronized")
        card = self.page.locator(".candidate").filter(has_text="Fixture hypothesis 0")
        expect(card).to_contain_text("History · Novelty")
        expect(card).to_contain_text("Internal hypothesis · not prior art")
        card.get_by_role("button", name="Fixture hypothesis 0", exact=True).click()
        form.locator("#decision-action").select_option("reopen")
        expect(form.locator("#decision-dimension")).to_be_disabled()
        form.get_by_label("Reason / research note").fill("Fixture reopened for a new control.")
        form.get_by_role("button", name="Save research judgment").click()
        expect(form.locator("textarea[name=reason]")).to_have_value("")
        history = self.page.locator('[data-preserve="elimination-history-idea-0"]')
        history.locator(":scope > summary").click()
        expect(history).to_contain_text("not necessarily current blockers")
        expect(history.get_by_text("Fixture novelty blocker with <literal> text.", exact=True)).to_be_visible()
        expect(history.get_by_text("Novelty", exact=True)).to_have_count(1)
        form.locator("#decision-action").select_option("defer")
        expect(form.locator("#decision-dimension")).to_have_attribute("required", "")
        form.locator("#decision-dimension").select_option("technical_feasibility")
        form.get_by_label("Reason / research note").fill("Fixture compute not available.")
        form.get_by_role("button", name="Save research judgment").click()
        expect(form.locator("textarea[name=reason]")).to_have_value("")
        self.assertEqual(self.store.find_record("opportunities", "idea-0")["elimination_reasons"][-1]["dimension"], "technical_feasibility")
        self.page.reload()
        card = self.page.locator(".candidate").filter(has_text="Fixture hypothesis 0")
        expect(card).to_contain_text("History · Novelty")
        expect(card).to_contain_text("History · Technical feasibility")
        self.page.locator('nav [data-view="library"]').click()
        expect(self.page.locator(".paper-row")).to_have_count(2)
        expect(self.page.locator(".paper-row").first).to_contain_text("External publication")
        expect(self.page.locator(".paper-row").filter(has_text="Fixture hypothesis")).to_have_count(0)

    def test_p1_reason_filter_legacy_categories_and_source_provenance(self):
        c = self.seed_scientific_fixtures()
        for i, dimension in enumerate(["novelty", "scientific_significance", "insufficient_evidence"]):
            idea = self.store.find_record("opportunities", f"idea-{i}")
            idea["elimination_reasons"] = [{
                "dimension": dimension, "reason": f"Fixture blocker {i}",
                "at": "2026-01-02T03:04:05Z", "by": "Fixture reviewer", "stage": "novelty audit",
                "paper_ids": ["paper-fixture"],
                "evidence": [{"claim": "Fixture evidence for blocker", "paper_id": "paper-fixture",
                              "source_url": "https://example.org/blocker", "location": "Fixture section",
                              "record_type": "external_publication"}],
            }]
            self.store.put(c["id"], "opportunities", idea)
        legacy = self.store.find_record("opportunities", "idea-3")
        legacy["status"] = "rejected"
        legacy["rejections"] = [{"reason": "Novelty and feasibility words do not establish a category."}]
        self.store.put(c["id"], "opportunities", legacy)
        self.open(c, "board")
        for i, dimension in enumerate(["novelty", "scientific_significance", "insufficient_evidence", "unclassified"]):
            self.page.locator("#board-dimension").select_option(dimension)
            expect(self.page.locator(".candidate")).to_have_count(1)
            expect(self.page.locator(".candidate")).to_contain_text(f"Fixture hypothesis {i}")
        expect(self.page.locator(".candidate")).to_contain_text("History · Unclassified")
        self.page.locator("#board-dimension").select_option("technical_feasibility")
        expect(self.page.locator(".candidate")).to_have_count(0)
        self.page.locator("#board-dimension").select_option("novelty")
        self.page.locator("#board-status").select_option("rejected")
        expect(self.page.locator(".candidate")).to_have_count(0)
        self.page.locator("#board-status").select_option("")
        self.page.get_by_role("button", name="Fixture hypothesis 0", exact=True).click()
        history = self.page.locator('[data-preserve="elimination-history-idea-0"]')
        history.locator(":scope > summary").focus()
        history.locator(":scope > summary").press("Enter")
        expect(history.get_by_text("Fixture blocker 0", exact=True)).to_be_visible()
        expect(history).to_contain_text("Fixture reviewer")
        expect(history.get_by_role("link", name="Open source")).to_have_attribute("href", "https://example.org/blocker")
        expect(history.get_by_text("External publication", exact=True).first).to_be_visible()
        expect(history.get_by_role("button", name="Fixture paper: matched controls", exact=False).first).to_be_visible()
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), 391)
        self.page.locator('[data-action="back-board"]').click()
        expect(self.page.locator("#board-dimension")).to_have_value("novelty")
        self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), 391)

    def test_p1_filters_comparison_validation_and_mobile(self):
        c = self.seed_scientific_fixtures()
        self.open(c, "library")
        self.page.get_by_label("Search the evidence store").fill("matched controls")
        expect(self.page.locator(".paper-row")).to_have_count(1)
        self.page.get_by_role("button", name="Clear filters").click()
        for field, value in [("venue", "FixtureVenue"), ("task", "retrieval"),
                             ("family", "contrastive"), ("datasets", "FixtureDataset"),
                             ("relevance", "direct")]:
            self.page.locator(f"#filter-{field}").select_option(value)
        self.page.locator("#filter-from").fill("2025-01-01")
        self.page.locator("#filter-to").fill("2025-12-31")
        expect(self.page.locator(".paper-row")).to_have_count(1)
        self.page.locator(".paper-row").click()
        expect(self.page.get_by_role("link", name="Read paper")).to_have_attribute("href", "https://example.org/fixture-paper")
        expect(self.page.get_by_text("Fixture quotation", exact=True)).to_be_visible()
        self.page.locator('[data-view="board"]').click()
        expect(self.page.locator(".board-lane")).to_have_count(9)
        for i in range(3):
            self.page.get_by_role("checkbox", name=f"Compare Fixture hypothesis {i}").check()
        self.page.get_by_role("checkbox", name="Compare Fixture hypothesis 3").click()
        expect(self.page.get_by_role("checkbox", name="Compare Fixture hypothesis 3")).not_to_be_checked()
        self.page.get_by_role("button", name="Compare candidates").click()
        expect(self.page.locator(".compare-grid > .panel")).to_have_count(3)
        self.page.locator('[data-view="validation"]').click()
        expect(self.page.get_by_text("Abstract location retained", exact=True)).to_be_visible()
        self.page.get_by_text("Inspect full validation record", exact=True).click()
        expect(self.page.locator("pre").filter(has_text="Generic fallback retained")).to_be_visible()
        self.page.locator('nav [data-view="methodology"]').click()
        self.page.locator('[data-method="novelty"]').click()
        expect(self.page.get_by_text("A literature search cannot prove", exact=False)).to_be_visible()
        self.page.set_viewport_size({"width": 390, "height": 844})
        for view in ["observatory", "library", "tensions", "board", "validation", "methodology"]:
            self.page.locator(f'nav [data-view="{view}"]').click()
            self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), 391, view)

    def test_p1_failed_task_retry_redirect_and_polling_preserves_draft(self):
        c = self.create_campaign()
        self.store.control(c["id"], "start")
        job = self.store.claim()
        self.store.finish(job, "failed", error="Fixture retrieval failure")
        self.open(c)
        self.page.get_by_role("button", name="cartographer", exact=True).first.click()
        expect(self.page.get_by_text("Fixture retrieval failure", exact=True).first).to_be_visible()
        self.page.get_by_role("button", name="Redirect", exact=True).first.click()
        self.page.get_by_label("New retrieval query").fill("fixture redirected query")
        self.page.get_by_role("button", name="Redirect task", exact=True).click()
        expect(self.page.get_by_role("dialog")).not_to_be_visible()
        self.assertEqual(self.store.job(job["id"])["input"]["query"], "fixture redirected query")
        claimed = self.store.claim()
        self.store.finish(claimed, "failed", error="Fixture second failure")
        self.refresh()
        self.page.get_by_role("button", name="Retry", exact=True).click()
        expect(self.page.locator("#toast")).to_have_text("Task retry requested.")
        self.assertEqual(self.store.job(job["id"])["status"], "queued")
        draft = self.page.get_by_label("Follow a specific lead")
        draft.fill("Unsaved scientific question")
        self.page.get_by_role("heading", name="Campaign observatory").click()
        self.store.event(c["id"], "fixture", "A real persisted fixture event arrived")
        self.page.wait_for_timeout(2200)
        expect(draft).to_have_value("Unsaved scientific question")
        draft.fill("fixture counterevidence search")
        self.page.get_by_role("button", name="Investigate this direction").click()
        expect(self.page.locator("#toast")).to_contain_text("Investigation queued")
        self.assertTrue(any(j["input"].get("query") == "fixture counterevidence search"
                            for j in self.store.state(c["id"])["jobs"]))

    def test_p1_revisions_priorities_challenges_and_form_errors(self):
        c = self.seed_scientific_fixtures()
        self.open(c, "board")
        self.page.get_by_role("button", name="Fixture hypothesis 0", exact=True).click()
        self.page.locator("#decision-action").select_option("revise")
        self.page.get_by_label("Revised hypothesis").fill("Revised fixture hypothesis with a falsification test.")
        self.page.get_by_label("Reason / research note").fill("Fixture revision: isolate the matched-control confound.")
        self.page.get_by_role("tab", name="Prior art", exact=True).click()
        expect(self.page.get_by_label("Reason / research note")).to_have_value("Fixture revision: isolate the matched-control confound.")
        expect(self.page.get_by_label("Revised hypothesis")).to_have_value("Revised fixture hypothesis with a falsification test.")
        self.page.get_by_role("button", name="Save research judgment").click()
        expect(self.page.locator("#toast")).to_have_text("Research judgment saved.")
        record = self.store.find_record("opportunities", "idea-0")
        self.assertEqual(record["hypothesis"], "Revised fixture hypothesis with a falsification test.")
        self.assertEqual(record["status"], "novelty audit")
        self.page.locator("#decision-action").select_option("prioritize")
        self.page.get_by_label("Reason / research note").fill("Fixture priority: cheapest decisive test.")
        self.page.locator("input[name=priority]").fill("8")
        self.page.get_by_role("button", name="Save research judgment").click()
        expect(self.page.locator("#decision-form textarea[name=reason]")).to_have_value("")
        self.assertEqual(self.store.find_record("opportunities", "idea-0")["priority"], 8)
        self.page.locator("#decision-action").select_option("challenge")
        self.page.get_by_label("Reason / research note").fill("Fixture challenge: search for prior matched controls")
        self.page.get_by_role("button", name="Save research judgment").click()
        expect(self.page.locator("#decision-form textarea[name=reason]")).to_have_value("")
        self.assertTrue(any(j["input"].get("query") == "Fixture challenge: search for prior matched controls"
                            for j in self.store.state(c["id"])["jobs"]))
        record = self.store.find_record("opportunities", "idea-0")
        record.pop("experiment")
        self.store.put(c["id"], "opportunities", record)
        self.refresh()
        self.page.locator("#decision-action").select_option("approve")
        self.page.get_by_label("Reason / research note").fill("Fixture approval without a concrete plan")
        self.page.get_by_role("button", name="Save research judgment").click()
        expect(self.page.locator("#decision-form .form-error")).to_contain_text("concrete experiment plan")
        expect(self.page.get_by_label("Reason / research note")).to_have_value("Fixture approval without a concrete plan")

    def test_p1_error_recovery_safe_links_and_campaign_switch(self):
        c = self.seed_scientific_fixtures()
        other = self.create_campaign("Second isolated fixture")
        self.store.put(c["id"], "papers", {
            "id": "unsafe-paper", "title": '<img src=x onerror="alert(1)"> literal fixture title',
            "url": "javascript:alert(1)", "evidence": [{"claim": "<script>fixture</script>",
                                                        "source_url": "javascript:alert(1)"}],
        })
        self.open(c, "library")
        self.page.get_by_role("button", name="literal fixture title", exact=False).click()
        expect(self.page.locator("#paper-inspector a")).to_have_count(0)
        expect(self.page.locator("#paper-inspector img, #paper-inspector script")).to_have_count(0)
        self.page.route("**/api/state?*", lambda route: route.fulfill(status=503, json={"error": "Fixture offline"}))
        self.refresh()
        expect(self.page.get_by_role("alert")).to_contain_text("Fixture offline")
        expect(self.page.locator(".paper-row")).to_have_count(3)
        self.page.unroute("**/api/state?*")
        self.refresh()
        expect(self.page.locator("#error")).not_to_be_visible()
        self.page.locator("#campaign-select").select_option(other["id"])
        expect(self.page.get_by_text("The evidence store is empty", exact=True)).to_be_visible()
        self.page.reload()
        expect(self.page.locator("#campaign-select")).to_have_value(other["id"])

    def test_p1_external_feedback_is_scoped_unverified_and_does_not_execute(self):
        c = self.seed_scientific_fixtures()
        other = self.create_campaign("Duplicated stable identifier fixture")
        self.store.put(other["id"], "opportunities", {
            "id": "idea-0", "title": "Untouched fixture in another campaign",
            "status": "newly proposed",
        })
        self.open(c, "board")
        self.page.get_by_role("button", name="Fixture hypothesis 0", exact=True).click()
        self.page.get_by_role("tab", name="Experiment", exact=True).click()
        self.page.get_by_role("button", name="Record external result", exact=True).click()
        dialog = self.page.get_by_role("dialog")
        expect(dialog.get_by_label("Measured observations")).to_have_value("")
        expect(dialog.get_by_text("independently unverified", exact=False)).to_be_visible()
        dialog.get_by_label("Artifact path or source URL").fill("https://example.org/explicit-ui-fixture")
        dialog.get_by_label("Measured observations").fill("Explicit browser fixture, not scientific measurements.")
        dialog.get_by_label("Interpretation and limitations").fill("Fixture validates persistence only.")
        dialog.get_by_role("button", name="Save external measurements").click()
        expect(dialog).not_to_be_visible()
        expect(self.page.locator("#candidate-panel").get_by_text("Experimental observation · not a publication", exact=True)).to_be_visible()
        result = self.store.find_record("opportunities", "idea-0", c["id"])
        self.assertIn("independently unverified", result["experiment"]["status"])
        self.assertEqual(len(result["experiment"]["result_history"]), 1)
        self.assertEqual(result["status"], "reviewer assessment")
        self.assertEqual(self.store.find_record("opportunities", "idea-0", other["id"])["status"], "newly proposed")
        self.assertEqual(self.store.state(c["id"])["costs"]["gpu_hours"], 0)
        self.assertTrue(any(j["role"] == "reviewer" and j["input"].get("opportunity_id") == "idea-0"
                            for j in self.store.state(c["id"])["jobs"]))

    def test_p1_structured_access_and_priority_do_not_imply_verification(self):
        c = self.seed_scientific_fixtures()
        paper = self.store.find_record("papers", "paper-fixture")
        paper["verification"] = {
            "metadata": {"source": "Fixture metadata, not a finding"},
            "read": "Abstract; selected passages on pages 1 and 4.",
            "venue_note": "Proceedings not independently checked.",
            "cache": "fixture/selected-passages.txt", "reproduced": False,
        }
        paper["evidence"][0]["verified"] = True
        self.store.put(c["id"], "papers", paper)
        for i, rank in enumerate([3, 2, 1, 4]):
            idea = self.store.find_record("opportunities", f"idea-{i}")
            idea["priority"] = {"rank": rank, "decision": "Fixture ordering only",
                                "basis": "Fixture ranking is not a scientific confidence estimate"}
            self.store.put(c["id"], "opportunities", idea)
        self.open(c, "library")
        self.page.locator('[data-action="inspect-paper"][data-id="paper-fixture"]').click()
        inspector = self.page.locator("#paper-inspector")
        expect(inspector.get_by_text("Read scope recorded", exact=True)).to_be_visible()
        expect(inspector.get_by_text("Abstract; selected passages on pages 1 and 4.", exact=True)).to_be_visible()
        expect(inspector.get_by_text("Proceedings not independently checked.", exact=True)).to_be_visible()
        expect(inspector.get_by_text("source checked", exact=True)).to_be_visible()
        self.assertNotIn("[object Object]", inspector.inner_text())
        self.assertNotIn("full paper verified", inspector.locator(".badge").all_text_contents())
        self.page.locator('nav [data-view="board"]').click()
        expect(self.page.locator('.candidate [data-action="open-opportunity"]').first).to_have_attribute("data-id", "idea-2")
        expect(self.page.locator(".candidate-footer").first).to_contain_text("Priority: rank 1")
        self.page.get_by_role("button", name="Fixture hypothesis 2", exact=True).click()
        expect(self.page.get_by_text("Fixture ranking is not a scientific confidence estimate", exact=True)).to_be_visible()
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), 391)

    def test_p1_foundations_serial_execution_and_default_validation(self):
        c = self.seed_scientific_fixtures()
        for number, name in [(1, "Scideator facet recombination"), (2, "Multi-agent research")]:
            self.store.put(c["id"], "foundations", {
                "id": f"F{number}", "title": f"Fixture {name}",
                "url": f"https://example.org/foundation-{number}", "authors": ["Fixture Author"],
                "validated_insights": ["Fixture insight, not scientific validation"],
                "adaptation": f"Fixture adaptation {number}: retain source-grounded disagreement",
                "limits": [f"Fixture limit {number}: not acceptance prediction"],
                "verification": {"read": "Fixture selective source passages", "reproduced": False},
                "evidence": [{"claim": "Fixture source claim", "source_url": "https://example.org/evidence",
                              "location": "Fixture section", "level": "secondary", "verified": False}],
            })
        self.store.put(c["id"], "validations", {"id": "historical-cutoff", "title": "Fixture historical check", "verdict": "ITERATE"})
        self.store.put(c["id"], "validations", {"id": "pilot-go-no-go", "title": "Fixture primary go/no-go", "verdict": "ITERATE"})
        self.open(c, "methodology")
        expect(self.page.get_by_text("Independent assessments, SERIAL built-in worker execution.", exact=True)).to_be_visible()
        expect(self.page.get_by_text("Independent assessments · serial worker", exact=True)).to_be_visible()
        inspector = self.page.locator("#foundation-inspector")
        expect(inspector.get_by_role("heading", name="Fixture Scideator facet recombination", exact=True)).to_be_visible()
        expect(inspector.get_by_text("Fixture adaptation 1: retain source-grounded disagreement", exact=True)).to_be_visible()
        self.page.locator('[data-foundation="F2"]').click()
        expect(inspector.get_by_text("Fixture limit 2: not acceptance prediction", exact=True)).to_be_visible()
        expect(inspector.get_by_role("link", name="Read foundation source")).to_have_attribute("href", "https://example.org/foundation-2")
        expect(inspector.get_by_text("Fixture selective source passages", exact=True)).to_be_visible()
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), 391)
        self.page.locator('nav [data-view="validation"]').click()
        expect(self.page.locator('.validation-row[aria-pressed="true"]')).to_have_attribute("data-id", "pilot-go-no-go")
        self.page.locator('[data-action="inspect-validation"][data-id="historical-cutoff"]').click()
        self.refresh()
        expect(self.page.locator('.validation-row[aria-pressed="true"]')).to_have_attribute("data-id", "historical-cutoff")

    def test_p1_method_landscape_uses_actual_families_and_opens_evidence(self):
        c = self.seed_scientific_fixtures()
        self.store.put(c["id"], "papers", {"id": "unclassified-fixture", "title": "Fixture without classification",
                                         "url": "https://example.org/unclassified"})
        self.open(c, "library")
        landscape = self.page.locator(".landscape")
        expect(landscape).not_to_have_attribute("open", "")
        landscape.locator("summary").click()
        expect(landscape.locator(".family-chip")).to_have_count(3)
        landscape.locator('.family-chip[data-family="contrastive"]').click()
        expect(self.page.locator("#filter-family")).to_have_value("contrastive")
        expect(self.page.locator(".paper-row")).to_have_count(1)
        expect(landscape).to_have_attribute("open", "")
        landscape.locator('.family-chip[data-family="Not classified"]').click()
        expect(self.page.locator(".paper-row")).to_have_count(1)
        expect(self.page.locator(".paper-row")).to_contain_text("Fixture without classification")
        landscape.locator('[data-action="landscape-paper"][data-id="paper-fixture"]').click()
        expect(self.page.locator("#paper-inspector").get_by_role("heading", name="Fixture paper: matched controls", exact=True)).to_be_visible()
        expect(landscape.get_by_text("Evaluation not recorded", exact=True).first).to_be_visible()
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), 391)
        self.assertGreater(landscape.locator(".landscape-table").evaluate("(el)=>el.scrollWidth"), 390)


if __name__ == "__main__":
    unittest.main()
