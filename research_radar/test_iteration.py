import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from . import iteration
from . import mechanism_campaign
from .archive import Archive, Reference


class IterationTests(unittest.TestCase):
    def test_fetch_preserves_response_and_refuses_duplicate_name(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(iteration, "DEFAULT_HOME", Path(tmp)):
            response = io.BytesIO(b"explicit synthetic public-source fixture")
            response.status, response.url, response.headers = 200, "https://example.org/source", {"Content-Type": "text/plain"}
            with patch.object(iteration, "urlopen", return_value=response):
                result = iteration.fetch(response.url, "fixture.txt")
            self.assertEqual(Archive(Path(tmp) / "archive").read(Reference(**result["archive"])),
                             b"explicit synthetic public-source fixture")
            with self.assertRaises(ValueError):
                iteration.fetch("https://example.org/source", "fixture.txt")
            self.assertEqual(len((Path(tmp) / "iteration-sources/requests.jsonl").read_text().splitlines()), 1)

    def test_budget_and_truncation_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(iteration, "DEFAULT_HOME", Path(tmp)):
            response = io.BytesIO(b"too long")
            response.status, response.url, response.headers = 200, "https://example.org", {}
            with patch.object(iteration, "urlopen", return_value=response), self.assertRaises(ValueError):
                iteration.fetch(response.url, "oversize", limit=3)
            log = Path(tmp) / "iteration-sources/requests.jsonl"
            row = json.loads(log.read_text())
            self.assertTrue(row["truncated"])
            self.assertNotIn("archive", row)
            log.write_text("".join(json.dumps({"bytes": 0}) + "\n" for _ in range(25)))
            with patch.object(iteration, "urlopen") as network, self.assertRaises(ValueError):
                iteration.fetch("https://example.org", "blocked")
            network.assert_not_called()

    def test_frozen_artifacts_cannot_be_replaced(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(iteration, "DIRECTORY", Path(tmp)):
            iteration.save("key.json", {"expected": "distinct"})
            iteration.save("key.json", {"expected": "distinct"})
            with self.assertRaises(ValueError):
                iteration.save("key.json", {"expected": "overlap"})

    def test_pdf_form_feeds_do_not_shift_newline_citation_ranges(self):
        text = "heading\n\fchart ticks\nactual supporting claim\nlast"
        start, quote = mechanism_campaign.newline_excerpt(text, 3, 3)
        self.assertEqual(quote, "actual supporting claim")
        self.assertEqual(text[start:start + len(quote)], quote)
        with self.assertRaises(ValueError):
            mechanism_campaign.newline_excerpt(text, 0, 3)

    def test_shortlist_recovers_saved_receipt_without_overwriting_prompt_or_recalling_model(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(mechanism_campaign, "DIRECTORY", Path(tmp)), \
                patch.object(mechanism_campaign, "campaign", return_value="fixture"), \
                patch.object(mechanism_campaign, "Store") as store_type, \
                patch.object(mechanism_campaign, "run") as model:
            ids = [f"M{i:02}" for i in range(1, 13)]
            mechanism_campaign.persist("candidates.json", [{"id": i} for i in ids])
            mechanism_campaign.persist("shortlist-freeze.json", {"sha256": "synthetic-prompt-hash"})
            mechanism_campaign.persist("shortlist.json", {
                "job_id": "fixture-job", "completed_at": "fixture-time",
                "result": {"screening": [{"id": i} for i in ids], "shortlist_ids": ids[:3]},
            })
            store_type.return_value.find_record.side_effect = lambda kind, i, cid: {
                "id": i, "assessment_history": [{"job_id": "fixture-job"}]}
            mechanism_campaign.shortlist()
            model.assert_not_called()
            self.assertEqual(mechanism_campaign.load("shortlist-freeze.json"), {"sha256": "synthetic-prompt-hash"})
            self.assertEqual(mechanism_campaign.load("shortlist-selection.json")["ids"], ids[:3])
            for call in store_type.return_value.put.call_args_list:
                self.assertEqual(len(call.args[2]["assessment_history"]), 1)
            mechanism_campaign.shortlist()
            self.assertEqual(store_type.return_value.put.call_count, 12)
