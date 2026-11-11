import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .core import Conflict, Store
from .retrieval import BudgetExceeded, Retriever
from .server import RadarServer, report
from .worker import Worker, parse_response


class RadarTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(self.temp.name)
        self.campaign = self.store.create({"name": "Explicit synthetic fixture", "field": "test field", "config": {"agent_enabled": False}})
        self.cid = self.campaign["id"]

    def tearDown(self):
        self.temp.cleanup()

    def paper(self, **kwargs):
        return self.store.put(self.cid, "papers", {"id": "p1", "title": "A test paper", "url": "https://example.org/p1", **kwargs})

    def idea(self):
        return self.store.put(self.cid, "opportunities", {
            "id": "o1", "title": "Test hypothesis", "hypothesis": "X fails under Y",
            "status": "novelty audit", "experiment": {"hypothesis": "X", "results": None},
        })

    def test_persistence_restart_and_dedup(self):
        self.paper(doi="10.1/TEST", verification="full paper", evidence=[{"claim": "test", "verified": True}])
        self.paper(id="another", title="A TEST paper", doi="https://doi.org/10.1/test", verification="metadata")
        restored = Store(self.temp.name)
        papers = restored.records(self.cid, "papers")
        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0]["id"], "p1")
        self.assertEqual(papers[0]["verification"], "full paper")
        self.assertTrue(papers[0]["evidence"][0]["verified"])

    def test_campaign_pause_resume_cancel(self):
        self.store.control(self.cid, "start")
        self.assertEqual(len(self.store.state(self.cid)["jobs"]), 7)
        self.store.control(self.cid, "pause")
        self.assertIsNone(self.store.claim())
        self.store.control(self.cid, "resume")
        job = self.store.claim()
        self.assertIsNotNone(job)
        self.store.control(self.cid, "cancel")
        self.store.finish(job, "completed", {})
        self.assertEqual(self.store.job(job["id"])["status"], "cancelled")
        with self.assertRaises(Conflict):
            self.store.control(self.cid, "resume")

    def test_completed_campaign_does_not_fake_running_on_resume(self):
        self.store.control(self.cid, "start")
        while job := self.store.claim():
            self.store.finish(job, "completed", {})
        self.store.control(self.cid, "pause")
        result = self.store.control(self.cid, "resume")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["stage"], "human decision")

    def test_recovery_requires_resume(self):
        self.store.control(self.cid, "start")
        job = self.store.claim()
        Store(self.temp.name).recover()
        self.assertEqual(self.store.job(job["id"])["status"], "interrupted")
        self.assertEqual(self.store.campaign(self.cid)["status"], "paused")
        self.store.control(self.cid, "resume")
        self.assertEqual(self.store.claim()["id"], job["id"])

    def test_rejected_history_survives_reopen(self):
        self.idea()
        self.store.decide("o1", {"action": "reject", "reason": "Established in prior work"})
        self.store.decide("o1", {"action": "reopen", "reason": "Narrowed the hypothesis"})
        idea = self.store.find_record("opportunities", "o1")
        self.assertEqual(idea["status"], "awaiting evidence")
        self.assertEqual(idea["rejections"][0]["reason"], "Established in prior work")
        self.assertEqual(len(idea["comments"]), 2)

    def test_typed_hypotheses_never_become_publication_evidence(self):
        self.idea()
        with self.assertRaises(ValueError):
            self.store.put(self.cid, "papers", {"id": "o1", "title": "Internal proposal", "url": "https://example.org"})
        with self.assertRaises(ValueError):
            self.paper(record_type="internal_hypothesis")
        self.paper()
        job = self.store.enqueue(self.cid, "novelty", "analysis", {})
        with self.assertRaises(ValueError):
            Worker(self.store).apply_analysis(job, {"assessments": [{"opportunity_id": "o1",
                "classification": "already established", "fatal_overlap": True,
                "prior_art": [{"paper_id": "o1", "overlap": "Another generated idea"}]}]})
        self.assertEqual(self.store.find_record("opportunities", "o1")["record_type"], "internal_hypothesis")
        self.assertEqual(self.store.find_record("papers", "p1")["record_type"], "external_publication")

    def test_elimination_dimension_is_persisted_without_conflating_novelty(self):
        self.idea()
        self.store.decide("o1", {"action": "reject", "dimension": "technical_feasibility", "reason": "Required inputs unavailable"})
        idea = self.store.find_record("opportunities", "o1")
        self.assertEqual(idea["hypothesis_state"], "prior_rejected_hypothesis")
        self.assertEqual(idea["elimination_reasons"][0]["dimension"], "technical_feasibility")
        self.store.decide("o1", {"action": "reopen", "reason": "Inputs now available"})
        idea = Store(self.temp.name).find_record("opportunities", "o1")
        self.assertEqual(idea["hypothesis_state"], "internal_hypothesis")
        self.assertEqual(idea["elimination_reasons"][0]["reason"], "Required inputs unavailable")
        with self.assertRaises(ValueError):
            self.store.decide("o1", {"action": "reject", "reason": "Fixture", "dimension": "made up"})

    def test_challenge_enqueues_real_update(self):
        self.idea()
        self.store.decide("o1", {"action": "challenge", "reason": "Find adaptive confidence prior art"})
        jobs = self.store.state(self.cid)["jobs"]
        self.assertEqual([j["kind"] for j in jobs], ["search", "analysis"])
        self.assertEqual(jobs[1]["input"]["opportunity_id"], "o1")
        self.assertEqual(self.store.campaign(self.cid)["status"], "running")

    def test_authorization_never_launches_gpu(self):
        self.idea()
        self.store.decide("o1", {"action": "authorize", "reason": "Approve future manual CPU pilot"})
        self.assertEqual(self.store.state(self.cid)["jobs"], [])
        self.assertEqual(self.store.find_record("opportunities", "o1")["experiment"]["status"], "authorized; execution is manual")

    def test_experimental_feedback_is_unverified_and_retained(self):
        self.idea()
        self.store.decide("o1", {"action": "result", "reason": "Observed pilot failures",
                               "results": {"artifact": "local:results.csv", "observations": {"error_m": 42}}})
        record = self.store.find_record("opportunities", "o1")
        self.assertEqual(record["experiment"]["results"]["observations"]["error_m"], 42)
        self.assertIn("unverified", record["experiment"]["status"])
        self.assertEqual(self.store.state(self.cid)["jobs"][0]["role"], "reviewer")

    def test_config_budgets_and_validation(self):
        for config in ({"max_papers": 1000}, {"max_requests": True}, {"queries": "query"}, {"api_budget_usd": 1}):
            with self.assertRaises(ValueError):
                self.store.create({"name": "invalid", "field": "field", "config": config})

    def test_source_failures_remain_explicit(self):
        job = self.store.enqueue(self.cid, "cartographer", "search", {"query": "fixture"})
        retriever = Retriever(self.store, job)
        with patch.object(retriever, "openalex", side_effect=OSError("offline")), patch.object(retriever, "arxiv", side_effect=OSError("offline")), patch.object(retriever, "crossref", return_value=[]):
            with self.assertRaisesRegex(RuntimeError, "All public retrieval providers failed"):
                retriever.search("fixture")
        self.assertEqual(self.store.records(self.cid, "papers"), [])

    def test_budget_stops_before_network(self):
        self.store.event(self.cid, "retrieval", "fixture", {"http_requests": 40})
        job = self.store.enqueue(self.cid, "cartographer", "search", {"query": "fixture"})
        with patch("research_radar.retrieval.urlopen") as network:
            with self.assertRaises(BudgetExceeded):
                Retriever(self.store, job).fetch("https://api.openalex.org/works")
            network.assert_not_called()

    def test_irrelevant_results_never_become_domain_papers(self):
        job = self.store.enqueue(self.cid, "cartographer", "search", {"query": "hard negative cross view localization"})
        retriever = Retriever(self.store, job)
        unrelated = {"id": "noise", "title": "Expected Performance of the ATLAS Experiment", "abstract": "Particle physics and collider detection", "url": "https://example.org/noise"}
        relevant = {"id": "real", "title": "Hard Negative Sampling for Cross-View Localization", "abstract": "Image matching", "url": "https://example.org/relevant"}
        with patch.object(retriever, "openalex", return_value=[unrelated]), patch.object(retriever, "arxiv", return_value=[relevant]):
            result = retriever.search(job["input"]["query"])
        self.assertEqual(result["provider"], "arxiv")
        self.assertEqual([p["id"] for p in self.store.records(self.cid, "papers")], ["real"])
        self.assertEqual(result["excluded_by_relevance_screen"][0]["title"], unrelated["title"])

    def test_arxiv_query_explicitly_conjoins_terms(self):
        job = self.store.enqueue(self.cid, "cartographer", "search", {"query": "hard negative mining"})
        retriever = Retriever(self.store, job)
        with patch.object(retriever, "fetch", return_value=(b'<feed xmlns="http://www.w3.org/2005/Atom"></feed>', {})) as fetch:
            retriever.arxiv(job["input"]["query"], 2)
        from urllib.parse import parse_qs, urlsplit
        query = parse_qs(urlsplit(fetch.call_args.args[0]).query)["search_query"][0]
        self.assertEqual(query, 'all:"hard" AND all:"negative" AND all:"mining"')

    def test_date_boundaries_exclude_future_and_unknown_sources(self):
        self.store.control(self.cid, "configure", {"config": {"date_from": "2020-01-01", "date_to": "2023-06-01"}})
        job = self.store.enqueue(self.cid, "cartographer", "search", {"query": "localization"})
        retriever = Retriever(self.store, job)
        self.assertTrue(retriever.in_date_range({"date": "2022-01-03"}))
        self.assertFalse(retriever.in_date_range({"date": "2024-01-03"}))
        self.assertFalse(retriever.in_date_range({"date": ""}))

    def test_fabricated_paper_rejected(self):
        self.paper()
        worker = Worker(self.store)
        job = self.store.enqueue(self.cid, "cartographer", "analysis", {})
        with self.assertRaisesRegex(ValueError, "fabricate"):
            worker.apply_analysis(job, {"papers": [{"id": "fake", "title": "Invented"}]})

    def test_fabricated_evidence_rejected(self):
        self.paper()
        worker = Worker(self.store)
        job = self.store.enqueue(self.cid, "tensions", "analysis", {})
        with self.assertRaisesRegex(ValueError, "unknown"):
            worker.apply_analysis(job, {"tensions": [{"id": "t1", "title": "Test", "paper_ids": ["fake"]}]})
        self.assertEqual(self.store.records(self.cid, "tensions"), [])

    def test_agent_cannot_verify_own_claims(self):
        self.paper()
        worker = Worker(self.store)
        job = self.store.enqueue(self.cid, "tensions", "analysis", {})
        worker.apply_analysis(job, {"tensions": [{"id": "t1", "title": "Test", "paper_ids": ["p1"], "evidence": [{"claim": "Test", "verified": True, "level": "full paper"}]}]})
        evidence = self.store.records(self.cid, "tensions")[0]["evidence"][0]
        self.assertFalse(evidence["verified"])
        self.assertEqual(evidence["level"], "inference")

    def test_no_model_output_without_evidence(self):
        self.store.control(self.cid, "start")
        first = self.store.claim()
        self.store.finish(first, "completed", {})
        job = self.store.claim()
        worker = Worker(self.store, agent=lambda *_: {"papers": []})
        worker.execute(job)
        self.assertEqual(self.store.job(job["id"])["status"], "failed")
        self.assertIn("without retrieved papers", self.store.job(job["id"])["error"])

    def test_targeted_assessment_is_persisted(self):
        self.paper()
        self.idea()
        paper = self.store.find_record("papers", "p1")
        paper["evidence"] = [{"quote": "Existing mechanism", "location": "Fixture section"}]
        self.store.put(self.cid, "papers", paper)
        job = self.store.enqueue(self.cid, "novelty", "analysis", {"opportunity_id": "o1"})
        Worker(self.store).apply_analysis(job, {"assessments": [{"opportunity_id": "o1", "classification": "partially overlapping",
            "summary": "Existing mechanism; evaluation may differ", "prior_art": [{"paper_id": "p1", "overlap": "mechanism"}],
            "fatal_overlap": True, "rejection_basis": "prior_art_overlap",
            "overlap_evidence": [{"paper_id": "p1", "location": "Fixture section", "quote": "Existing mechanism"}]}]})
        idea = Store(self.temp.name).find_record("opportunities", "o1")
        self.assertEqual(idea["status"], "rejected")
        self.assertEqual(idea["assessment_history"][0]["job_id"], job["id"])

    def test_missing_experiments_cannot_be_a_fatal_novelty_rejection(self):
        self.paper()
        self.idea()
        job = self.store.enqueue(self.cid, "novelty", "analysis", {})
        assessment = {"opportunity_id": "o1", "classification": "uncertain",
                      "fatal_overlap": True, "rejection_basis": "missing experiments",
                      "summary": "Data unavailable"}
        with self.assertRaises(ValueError):
            Worker(self.store).apply_analysis(job, {"assessments": [assessment]})
        self.assertNotEqual(self.store.find_record("opportunities", "o1")["status"], "rejected")
        assessment["fatal_overlap"] = "false"
        with self.assertRaises(ValueError):
            Worker(self.store).apply_analysis(job, {"assessments": [assessment]})
        assessment["fatal_overlap"] = False
        Worker(self.store).apply_analysis(job, {"assessments": [assessment]})
        self.assertEqual(self.store.find_record("opportunities", "o1")["status"], "reviewer assessment")

    def test_failed_task_retry_blocks_downstream_until_repaired(self):
        self.store.control(self.cid, "start")
        job = self.store.claim()
        self.store.finish(job, "failed", error="Unavailable source")
        self.assertIsNone(self.store.claim())
        self.store.job_control(job["id"], "retry", {})
        self.assertEqual(self.store.claim()["id"], job["id"])

    def test_import_idempotent_cost_and_export(self):
        bundle = {"papers": [{"id": "p1", "title": "Fixture", "url": "https://example.org"}], "costs": {"http_requests": 2}}
        digest = self.store.import_bundle(self.cid, bundle, "fixture.json")
        self.assertEqual(self.store.import_bundle(self.cid, bundle, "fixture.json"), digest)
        self.assertEqual(self.store.costs(self.cid)["http_requests"], 2)
        self.assertIn("Fixture", report(self.store.state(self.cid)))
        self.assertIsNone(self.store.costs(self.cid)["api_cost_usd"])

    def test_unknown_cost_measurements_remain_explicit(self):
        self.store.event(self.cid, "cost", "Partially measured import",
                         {"http_requests": 2, "download_bytes": None, "elapsed_seconds": None,
                          "measurement": "Request count known; bytes and runtime unknown"})
        costs = self.store.costs(self.cid)
        self.assertEqual(costs["http_requests"], 2)
        self.assertEqual(costs["incomplete_measurement_records"], 1)
        self.assertIn("bytes and runtime unknown", costs["measurement_notes"][0])

    def test_parse_requires_structured_json(self):
        self.assertEqual(parse_response('```json\n{"papers":[]}\n```'), {"papers": []})
        with self.assertRaises(ValueError):
            parse_response("A convincing unstructured answer")

    def test_same_paper_in_multiple_campaigns_can_be_annotated(self):
        self.paper()
        other = self.store.create({"name": "Second field", "field": "another"})
        self.store.put(other["id"], "papers", {"id": "p1", "title": "A test paper", "url": "https://example.org/p1"})
        job = self.store.enqueue(self.cid, "cartographer", "analysis", {})
        Worker(self.store).apply_analysis(job, {"papers": [{"id": "p1", "family": "retrieval"}]})
        self.assertEqual(self.store.find_record("papers", "p1", self.cid)["family"], "retrieval")
        self.assertNotIn("family", self.store.find_record("papers", "p1", other["id"]))


class HTTPTests(RadarTests):
    def setUp(self):
        super().setUp()
        self.server = RadarServer(("127.0.0.1", 0), self.store)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        super().tearDown()

    def test_http_create_controls_export_persistence(self):
        request = Request(self.url + "/api/campaigns", data=json.dumps({"name": "Browser fixture", "field": "test"}).encode(),
                          headers={"Content-Type": "application/json"})
        with urlopen(request) as response:
            cid = json.load(response)["id"]
        with urlopen(Request(self.url + f"/api/campaigns/{cid}/start", data=b"{}", headers={"Content-Type": "application/json"})) as response:
            self.assertEqual(json.load(response)["status"], "running")
        with urlopen(self.url + f"/api/export?campaign={cid}") as response:
            state = json.load(response)
        self.assertEqual(len(state["jobs"]), 7)
        self.assertEqual(Store(self.temp.name).campaign(cid)["status"], "running")

    def test_cross_origin_mutation_rejected(self):
        req = Request(self.url + "/api/campaigns", data=b"{}", headers={"Content-Type": "application/json", "Origin": "https://untrusted.example"})
        with self.assertRaises(HTTPError) as error:
            urlopen(req)
        self.assertEqual(error.exception.code, 403)

    def test_paths_not_exposed(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(self.url + "/../core.py")
        self.assertEqual(error.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
