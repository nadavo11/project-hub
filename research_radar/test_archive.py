"""Focused offline tests; every test writes only inside the owned archive tree."""

import os
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import uuid

from .archive import (Archive, ArchiveError, Reference, _digest, _first_write,
                      _locate, preserve_existing, verify_preservation_report)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.root = (Path(__file__).resolve().parents[1] / "data/research-radar/archive"
                     / ("test-" + uuid.uuid4().hex))
        self.archive = Archive(self.root)

    def tearDown(self):
        # Test fixtures are deliberately retained: no recursive cleanup or deletion
        # of evidence in this shared environment.
        pass

    def raw(self, data=b"%PDF-local synthetic source", url="https://example.invalid/paper"):
        return self.archive.store_bytes(
            data, url=url, media_type="application/pdf", retrieved_at="2026-11-09",
            provenance={"fixture": True})

    def claim(self):
        raw = self.raw()
        text = self.archive.store_text("Before. Exact quotation. After.", raw=raw,
                                       extraction="Synthetic test fixture")
        digest = self.archive.record_claim(
            claim="Example source statement", source=raw, text=text, quote="Exact quotation",
            start=8, end=23, location="page 1")
        return raw, text, digest

    def corrupt(self, path, data):
        path.chmod(0o644)
        path.write_bytes(data)

    def test_roundtrip_exact_claim_and_immutable_reference(self):
        raw, text, digest = self.claim()
        self.assertEqual(self.archive.read(raw), b"%PDF-local synthetic source")
        record = self.archive.verify_manifest(digest)
        self.assertEqual(record["text"], text.to_dict())
        self.assertEqual(record["quote"], "Exact quotation")
        self.assertEqual(Reference(**raw.to_dict()), raw)
        with self.assertRaises(AttributeError):
            raw.sha256 = "changed"

    def test_duplicate_preserves_object_and_distinct_provenance(self):
        first = self.raw()
        path = self.archive._path("objects", first.sha256)
        inode = path.stat().st_ino
        self.assertEqual(self.raw(), first)
        other = self.raw(url="https://example.invalid/later-copy")
        self.assertEqual(first.sha256, other.sha256)
        self.assertNotEqual(first.manifest_sha256, other.manifest_sha256)
        self.assertEqual(path.stat().st_ino, inode)
        self.assertEqual(self.archive.verify_manifest(first.manifest_sha256)["url"],
                         "https://example.invalid/paper")

    def test_corrupt_existing_bytes_are_never_replaced_on_reuse(self):
        raw = self.raw()
        path = self.archive._path("objects", raw.sha256)
        self.corrupt(path, b"tampered")
        with self.assertRaises(ArchiveError):
            self.raw()
        self.assertEqual(path.read_bytes(), b"tampered")

    def test_missing_raw_cannot_validate_claim(self):
        raw, _, digest = self.claim()
        # Simulate unavailable evidence without deleting any retained file.
        path = self.archive._path("objects", raw.sha256)
        path.rename(path.with_suffix(".missing-fixture"))
        with self.assertRaises(ArchiveError):
            self.archive.verify_manifest(digest)

    def test_tampered_raw_text_and_manifest_fail(self):
        for target in ("raw", "text", "manifest"):
            with self.subTest(target=target):
                # Different response bytes prevent deliberate fixture damage from
                # interfering with the next subcase.
                archive = Archive(self.root / target)
                raw = archive.store_bytes(b"raw", url="local:fixture",
                                          media_type="text/plain", retrieved_at=None)
                text = archive.store_text("quote", raw=raw, extraction="fixture")
                digest = archive.record_claim(claim="claim", source=raw, text=text,
                                              quote="quote", start=0, end=5, location="line 1")
                path = (archive._path("manifests", digest) if target == "manifest"
                        else archive._path("objects", (raw if target == "raw" else text).sha256))
                self.corrupt(path, b"tampered")
                with self.assertRaises(ArchiveError):
                    archive.verify_manifest(digest)

    def test_unlinked_text_and_wrong_raw_cannot_pass(self):
        raw, text, _ = self.claim()
        other = self.raw(b"other raw bytes")
        for source, snapshot in ((other, text), (raw, raw)):
            with self.subTest(source=source, snapshot=snapshot):
                with self.assertRaises(ArchiveError):
                    self.archive.record_claim(claim="claim", source=source, text=snapshot,
                                              quote="Exact quotation", start=8, end=23,
                                              location="page 1")
        record = self.archive.verify_manifest(text.manifest_sha256)
        del record["raw"]
        forged = self.archive._manifest(record)
        with self.assertRaises(ArchiveError):
            self.archive.verify_manifest(forged)
        with self.assertRaises(ArchiveError):
            self.archive.store_bytes(b"text", url="local:bad", media_type="text/plain",
                                     retrieved_at=None, representation="text")

    def test_wrong_quote_or_offsets_cannot_pass(self):
        raw, text, _ = self.claim()
        for quote, start, end in (("invented", 8, 23), ("Exact quotation", -1, 23),
                                  ("", 8, 8), ("Exact quotation", True, 23)):
            with self.subTest(quote=quote, start=start):
                with self.assertRaises(ArchiveError):
                    self.archive.record_claim(claim="claim", source=raw, text=text,
                                              quote=quote, start=start, end=end, location="page 1")

    def test_provenance_corruption_and_reference_mismatch_fail(self):
        artifact = self.archive.store_bytes(b"original log", url="local:log",
                                             media_type="text/plain", retrieved_at=None,
                                             representation="artifact")
        raw = self.archive.store_bytes(b"raw", url="local:source", media_type="text/plain",
                                        retrieved_at=None,
                                        provenance_refs=[artifact.manifest_sha256])
        with self.assertRaises(ArchiveError):
            self.archive.read(Reference(raw.sha256, 999, raw.manifest_sha256))
        self.corrupt(self.archive._path("objects", artifact.sha256), b"changed log")
        with self.assertRaises(ArchiveError):
            self.archive.read(raw)

    def test_interrupted_publication_recovers_without_sweeping_orphans(self):
        orphan = self.root / "objects/.pending-interrupted-fixture"
        orphan.write_bytes(b"partial earlier write")
        with patch("research_radar.archive.os.link", side_effect=OSError("interruption")):
            with self.assertRaises(OSError):
                self.raw()
        self.assertEqual(orphan.read_bytes(), b"partial earlier write")
        raw = self.raw()
        self.assertEqual(self.archive.read(raw), b"%PDF-local synthetic source")
        self.assertEqual(orphan.read_bytes(), b"partial earlier write")
        self.assertEqual(list((self.root / "objects").glob(".pending-*")), [orphan])

    def test_publication_race_reuses_only_verified_winner(self):
        link = os.link
        calls = []

        def race(source, destination):
            calls.append(destination)
            link(source, destination)
            raise FileExistsError("another writer won")

        with patch("research_radar.archive.os.link", side_effect=race):
            raw = self.raw()
        self.assertTrue(calls)
        self.assertEqual(self.archive.read(raw), b"%PDF-local synthetic source")

    def test_interruption_after_publish_is_reusable(self):
        original = self.raw()
        path = self.root / "objects" / _digest(b"interrupted")
        real_sync = os.fsync
        count = 0

        def interrupt(descriptor):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError("directory sync interrupted")
            return real_sync(descriptor)

        with patch("research_radar.archive.os.fsync", side_effect=interrupt):
            with self.assertRaises(OSError):
                _first_write(path, b"interrupted")
        _first_write(path, b"interrupted")
        self.assertEqual(path.read_bytes(), b"interrupted")
        self.assertEqual(self.archive.read(original), b"%PDF-local synthetic source")

    def test_normalized_lookup_records_exact_original_span(self):
        text = "Before: a line-\nwrapped quotation; after."
        start, end, method = _locate(text, "a linewrapped quotation")
        self.assertEqual(text[start:end], "a line-\nwrapped quotation")
        self.assertEqual(method, "alphanumeric-location-only")
        with self.assertRaises(ArchiveError):
            _locate(text, "nonexistent statement")

    def test_invalid_digest_does_not_escape_archive(self):
        with self.assertRaises(ArchiveError):
            self.archive.verify_manifest("../outside")

    def test_html_migration_and_report_refresh_preserve_previous_evidence(self):
        project = self.root / "synthetic-project"
        radar = project / "research_radar"
        raw = b"<html><p>An exact &amp; decisive quotation.</p></html>"
        candidate_input = b"{}"
        evidence = {"quote": "exact & decisive quotation", "claim": "fixture",
                    "location": "paragraph 1", "source_url": "https://example.invalid/abstract"}
        documents = {
            "sources/retrieval-log.json": [{
                "url": evidence["source_url"], "cache": "sources/abstract.html",
                "sha256": _digest(raw), "accessed_at": None}],
            "pilot/literature.json": {"papers": [{"id": "fixture", "evidence": [evidence]}],
                                     "foundations": []},
            "pilot/independent-candidate-audit.json": {
                "evidence": [], "independent_search": {"primary_findings": []}},
            "pilot/sources/candidate-audit/manifest.json": {
                "sources": [], "input": {"sha256": _digest(candidate_input)}},
            "pilot/sources/candidate-independent-search/retrieval-log.json": [],
            "pilot/seed-source-verification.json": {"cases": []},
            "pilot/sources/blind/manifest.json": {"missing_extracted_texts": "fixture missing"},
            "pilot/sources/blind/retrieval-log.json": [],
        }
        for name, value in documents.items():
            path = radar / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value))
        (radar / "sources/abstract.html").write_bytes(raw)
        (radar / "pilot/sources/candidate-audit/literature-input.json").write_bytes(candidate_input)
        first = preserve_existing(project)
        self.assertTrue(first["current_claims_verified"])
        self.assertEqual(first["verified_claim_count"], 1)
        self.assertTrue(first["sources"][0]["generated_offline_at_archival_deposit"])
        self.assertEqual(verify_preservation_report(project), first)
        report_path = radar / "pilot/iteration/source-preservation.json"
        original_projection = report_path.read_bytes()
        second = preserve_existing(project, refresh=True)
        archive = Archive(project / "data/research-radar/archive")
        previous = Reference(**second["previous_reports"][0])
        self.assertEqual(archive.read(previous), original_projection)
        self.assertEqual(second["claims"], first["claims"])
        self.assertEqual(verify_preservation_report(project), second)
        changed = dict(second, verified_claim_count=500)
        self.corrupt(report_path, json.dumps(changed).encode())
        with self.assertRaises(ArchiveError):
            verify_preservation_report(project)


if __name__ == "__main__":
    unittest.main()
