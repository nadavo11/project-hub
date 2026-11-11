"""Offline, append-only evidence archive. No retrieval or model execution."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import re
import uuid


class ArchiveError(ValueError):
    """Missing, corrupt, or incorrectly linked archival evidence."""


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _json(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _hash(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ArchiveError("Expected a lowercase SHA-256 digest")
    return value


def _sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _mkdir(path):
    if not path.exists():
        _mkdir(path.parent)
        try:
            path.mkdir()
        except FileExistsError:
            pass
        _sync_directory(path.parent)


def _read_checked(path, expected):
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "rb") as stream:
            data = stream.read()
    except OSError as error:
        raise ArchiveError(f"Cannot read preserved evidence: {path}") from error
    if _digest(data) != expected:
        raise ArchiveError(f"SHA-256 mismatch: {path}")
    return data


def _first_write(path, data):
    """Publish a fully fsynced file with link(2), never replace existing bytes."""
    _mkdir(path.parent)
    expected = _digest(data)
    if path.exists():
        _read_checked(path, expected)
        _sync_directory(path.parent)
        return
    pending = path.parent / (".pending-" + uuid.uuid4().hex)
    descriptor = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(pending, path)
        except FileExistsError:
            _read_checked(path, expected)
        _sync_directory(path.parent)
    finally:
        # Only this invocation's explicitly named staging file may be removed.
        pending.unlink(missing_ok=True)
        _sync_directory(path.parent)


@dataclass(frozen=True)
class Reference:
    sha256: str
    size: int
    manifest_sha256: str

    def to_dict(self):
        return asdict(self)


class Archive:
    """Immutable content and provenance; verification raises ArchiveError on failure.

    Hashes establish byte integrity and declared provenance, not author identity,
    scientific truth, or that a caller's extraction actually came from its raw PDF.
    """

    def __init__(self, root):
        self.root = Path(root)
        for directory in ("objects", "manifests"):
            _mkdir(self.root / directory)

    def _path(self, kind, digest):
        return self.root / kind / _hash(digest)

    def _manifest(self, record):
        data = _json(record)
        digest = _digest(data)
        _first_write(self._path("manifests", digest), data)
        return digest

    def store_bytes(self, data, *, url, media_type, retrieved_at,
                    representation="raw", provenance=None, provenance_refs=()):
        """Deposit caller-supplied response bytes (or local provenance artifacts).

        retrieved_at=None means unknown, never the time of this archival deposit.
        For extracted text use store_text, which requires a verified raw reference.
        """
        if not isinstance(data, bytes):
            raise TypeError("data must be bytes")
        if representation not in ("raw", "artifact"):
            raise ArchiveError("store_bytes accepts raw or artifact representations")
        if not isinstance(url, str) or not url or not isinstance(media_type, str) or not media_type:
            raise ArchiveError("url and media_type are required")
        if retrieved_at is not None and (not isinstance(retrieved_at, str) or not retrieved_at):
            raise ArchiveError("retrieved_at must be a recorded timestamp or None")
        record = {"schema": 1, "kind": "blob", "representation": representation,
                  "sha256": _digest(data), "size": len(data), "url": url,
                  "media_type": media_type, "retrieved_at": retrieved_at,
                  "provenance": provenance or {}, "provenance_refs": list(provenance_refs)}
        for digest in record["provenance_refs"]:
            self.verify_manifest(digest)
        _first_write(self._path("objects", record["sha256"]), data)
        digest = self._manifest(record)
        self.verify_manifest(digest)
        return Reference(record["sha256"], len(data), digest)

    def store_text(self, text, *, raw, extraction, provenance=None, provenance_refs=()):
        """Preserve UTF-8 text with an explicit extraction attestation and raw link."""
        source = self._reference(raw)
        if source["representation"] != "raw" or not isinstance(text, str) or not extraction:
            raise ArchiveError("Text needs a raw source and a nonempty extraction description")
        data = text.encode("utf-8")
        record = {"schema": 1, "kind": "blob", "representation": "text",
                  "sha256": _digest(data), "size": len(data), "url": source["url"],
                  "media_type": "text/plain; charset=utf-8",
                  "retrieved_at": source["retrieved_at"], "raw": raw.to_dict(),
                  "extraction": extraction, "provenance": provenance or {},
                  "provenance_refs": list(provenance_refs)}
        for digest in record["provenance_refs"]:
            self.verify_manifest(digest)
        _first_write(self._path("objects", record["sha256"]), data)
        digest = self._manifest(record)
        self.verify_manifest(digest)
        return Reference(record["sha256"], len(data), digest)

    def _reference(self, reference, seen=None):
        if not isinstance(reference, Reference):
            raise ArchiveError("Expected an immutable Reference")
        record = self.verify_manifest(reference.manifest_sha256, _seen=seen)
        if (record.get("kind"), record.get("sha256"), record.get("size")) != (
                "blob", reference.sha256, reference.size):
            raise ArchiveError("Reference disagrees with its preserved manifest")
        return record

    def read(self, reference):
        """Verify manifest, linked evidence and object bytes before returning bytes."""
        self._reference(reference)
        return _read_checked(self._path("objects", reference.sha256), reference.sha256)

    def record_claim(self, *, claim, source, text, quote, start, end, location,
                     provenance=None, provenance_refs=()):
        """Record an exact UTF-8-decoded character span (zero-based, end-exclusive).

        location is the human page/section label; offsets are the mechanical
        location. A caller must distinguish interpretations from source statements.
        """
        record = {"schema": 1, "kind": "claim", "claim": claim,
                  "source": source.to_dict(), "text": text.to_dict(),
                  "quote": quote, "start": start, "end": end, "location": location,
                  "provenance": provenance or {}, "provenance_refs": list(provenance_refs)}
        self._verify_record(record, set())
        digest = self._manifest(record)
        self.verify_manifest(digest)
        return digest

    def verify_manifest(self, digest, *, _seen=None):
        """Return the verified record; missing/tampered/raw-unlinked claims raise."""
        seen = set() if _seen is None else set(_seen)
        if digest in seen:
            raise ArchiveError("Cyclic provenance")
        seen.add(digest)
        data = _read_checked(self._path("manifests", digest), digest)
        try:
            record = json.loads(data)
            self._verify_record(record, seen)
        except (KeyError, TypeError, UnicodeError, json.JSONDecodeError) as error:
            raise ArchiveError("Malformed evidence manifest") from error
        return record

    def _verify_record(self, record, seen):
        if record["schema"] != 1 or not isinstance(record.get("provenance"), dict):
            raise ArchiveError("Unsupported manifest schema or provenance")
        if not isinstance(record.get("provenance_refs"), list):
            raise ArchiveError("Missing provenance links")
        for digest in record["provenance_refs"]:
            self.verify_manifest(digest, _seen=seen)
        if record["kind"] == "blob":
            data = _read_checked(self._path("objects", record["sha256"]), record["sha256"])
            if type(record["size"]) is not int or len(data) != record["size"]:
                raise ArchiveError("Object size mismatch")
            if not isinstance(record["url"], str) or not record["url"] or not record["media_type"]:
                raise ArchiveError("Missing source identity")
            timestamp = record["retrieved_at"]
            if timestamp is not None and (not isinstance(timestamp, str) or not timestamp):
                raise ArchiveError("Invalid retrieval timestamp")
            representation = record["representation"]
            if representation == "text":
                raw = self._reference(Reference(**record["raw"]), seen)
                if (raw["representation"] != "raw" or record["url"] != raw["url"]
                        or record["retrieved_at"] != raw["retrieved_at"] or not record["extraction"]):
                    raise ArchiveError("Text is not linked to its declared raw source")
                data.decode("utf-8")
            elif representation not in ("raw", "artifact"):
                raise ArchiveError("Unknown representation")
        elif record["kind"] == "claim":
            source = self._reference(Reference(**record["source"]), seen)
            text = self._reference(Reference(**record["text"]), seen)
            if (source["representation"] != "raw" or text["representation"] != "text"
                    or text["raw"] != record["source"]):
                raise ArchiveError("Claim must link the exact raw source of its text")
            content = _read_checked(self._path("objects", text["sha256"]),
                                    text["sha256"]).decode("utf-8")
            start, end = record["start"], record["end"]
            if (type(start) is not int or type(end) is not int
                    or not 0 <= start < end <= len(content)
                    or not isinstance(record["quote"], str) or not record["quote"]
                    or content[start:end] != record["quote"]):
                raise ArchiveError("Claim quote does not match the exact stored text span")
            if not record["claim"] or not record["location"]:
                raise ArchiveError("Claim and page/section description are required")
        else:
            raise ArchiveError("Unknown manifest kind")


def _locate(text, quote):
    start = text.find(quote)
    if start >= 0:
        return start, start + len(quote), "exact"
    # Historical quotations wrap PDF lines, sometimes with a hyphen. The
    # normalized lookup selects a span; only the unchanged actual span is signed.
    positions = [i for i, character in enumerate(text) if character.isalnum()]
    compact = "".join(text[i].lower() for i in positions)
    needle = "".join(character.lower() for character in quote if character.isalnum())
    start = compact.find(needle) if needle else -1
    if start < 0:
        raise ArchiveError("Historical quotation not located in retained text")
    return positions[start], positions[start + len(needle) - 1] + 1, "alphanumeric-location-only"


def preserve_existing(project, *, refresh=False):
    """Bounded migration of named pilot evidence only, with no network access."""
    project = Path(project).resolve()
    radar = project / "research_radar"
    root = project / "data/research-radar/archive"
    archive = Archive(root)
    report_path = radar / "pilot/iteration/source-preservation.json"
    if report_path.exists() and not refresh:
        return verify_preservation_report(project)
    previous_reports = []
    if report_path.exists():
        previous = verify_preservation_report(project)
        previous_ref = archive.store_bytes(
            report_path.read_bytes(), url="local:source-preservation-report-previous",
            media_type="application/json", retrieved_at=None, representation="artifact",
            provenance={"role": "exact prior report projection, retained before refresh"},
            provenance_refs=[previous["immutable_report"]["manifest_sha256"]])
        previous_reports.append(previous_ref.to_dict())
    documents = {}
    artifacts = {}
    names = {
        "literature": "pilot/literature.json",
        "retrieval": "sources/retrieval-log.json",
        "audit": "pilot/independent-candidate-audit.json",
        "candidate": "pilot/sources/candidate-audit/manifest.json",
        "candidate_input": "pilot/sources/candidate-audit/literature-input.json",
        "independent": "pilot/sources/candidate-independent-search/retrieval-log.json",
        "seed": "pilot/seed-source-verification.json",
        "blind": "pilot/sources/blind/manifest.json",
        "blind_log": "pilot/sources/blind/retrieval-log.json",
    }
    for key, name in names.items():
        data = (radar / name).read_bytes()
        if key == "candidate_input" and _digest(data) != documents["candidate"]["input"]["sha256"]:
            raise ArchiveError("Candidate input snapshot fails its historical hash")
        documents[key] = json.loads(data)
        artifacts[key] = archive.store_bytes(
            data, url="local:research_radar/" + name, media_type="application/json",
            retrieved_at=None, representation="artifact",
            provenance={"original_path": "research_radar/" + name,
                        "role": "retained local provenance, not an HTTP response"})

    report = {
        "schema": 1, "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Offline archival migration of 56 literature, 11 candidate-audit, "
                 "3 independent-search and 5 seed-verification quotations; no benchmark keys read.",
        "network_requests": 0, "model_invocations": 0, "gpu_jobs": 0,
        "archive_root": "data/research-radar/archive",
        "previous_reports": previous_reports,
        "provenance_artifacts": {key: value.to_dict() for key, value in artifacts.items()},
        "sources": [], "claims": [], "exceptions": [], "past_missing_lineage": [],
        "limitations": [
            "Verified means preserved-byte integrity, raw/text linkage and an exact located "
            "quotation; it does not certify scientific truth, novelty, or semantic entailment.",
            "Extraction is an explicit provenance attestation, not a re-extraction test.",
            "Original reviewer location labels are retained, not independently page-validated; "
            "character offsets are mechanically verified.",
            "Normalized historical quotation searches retain both the original asserted quote "
            "and the exact source span; normalization alone is never the verification result.",
            "Unquoted hypotheses, interpretations and candidate verdicts are not promoted "
            "to verified claims. The full input artifacts are retained for context.",
            "Later seed verification does not restore deleted original blind-audit responses.",
            "Unknown retrieval timestamps remain null; archive creation time is separate.",
        ],
    }
    sources = {}
    retrieval = {entry["url"]: entry for entry in documents["retrieval"]
                 if entry.get("cache")}
    candidate = {entry["url"]: entry for entry in documents["candidate"]["sources"]}
    independent = {entry["url"]: entry for entry in documents["independent"]}

    def preserve(url, entry, base, provenance_key, *, text_path=None, text_hash=None,
                 text_provenance=None):
        raw_path = base / (entry.get("cache") or entry.get("filename"))
        raw_data = raw_path.read_bytes()
        expected = entry.get("sha256")
        if not expected or _digest(raw_data) != expected:
            raise ArchiveError(f"Retained raw bytes fail original hash: {raw_path}")
        provenance = {"original_path": str(raw_path.relative_to(project)),
                      "recorded_raw_sha256": expected,
                      "migration": "existing local bytes only"}
        refs = [artifacts[provenance_key].manifest_sha256]
        raw = archive.store_bytes(
            raw_data, url=url,
            media_type=entry.get("content_type") or (
                "application/pdf" if raw_path.suffix == ".pdf" else "text/html"),
            retrieved_at=entry.get("accessed_at") or entry.get("checked_at"),
            provenance=provenance, provenance_refs=refs)
        if text_path is None:
            name = entry.get("text_cache") or entry.get("text_filename")
            if name:
                text_path = base / name
            elif raw_path.name in ("2608.28891.full.html", "anthropic-research.html"):
                text_path = raw_path.with_suffix(".txt")
        generated = text_path is None
        if generated and raw_path.suffix != ".html":
            raise ArchiveError(f"No retained text snapshot for {raw_path}")
        text_data = (html.unescape(re.sub(r"<[^>]*>", " ", raw_data.decode("utf-8"))).encode("utf-8")
                     if generated else text_path.read_bytes())
        expected_text = text_hash or entry.get("text_sha256")
        if expected_text and _digest(text_data) != expected_text:
            raise ArchiveError(f"Retained text fails original hash: {text_path}")
        if text_provenance:
            refs.append(artifacts[text_provenance].manifest_sha256)
        text = archive.store_text(
            text_data.decode("utf-8"), raw=raw,
            extraction=("Offline HTML tag removal and html.unescape from preserved raw bytes"
                        if generated else "Previously retained HTML text extraction"
                        if raw_path.suffix == ".html"
                        else "Previously retained pdftotext extraction; not re-extracted"),
            provenance={"original_path": None if generated else str(text_path.relative_to(project)),
                        "generated_offline_at_archival_deposit": generated,
                        "recorded_text_sha256": expected_text,
                        "historical_text_hash_available": bool(expected_text)},
            provenance_refs=refs)
        report["sources"].append({"url": url, "raw": raw.to_dict(), "text": text.to_dict(),
                                  "original_raw_path": str(raw_path.relative_to(project)),
                                  "original_text_path": None if generated else str(text_path.relative_to(project)),
                                  "generated_offline_at_archival_deposit": generated,
                                  "historical_text_hash_available": bool(expected_text)})
        return raw, text

    def claim(identifier, evidence, group, pair, input_path):
        try:
            if isinstance(pair, Exception):
                raise pair
            raw, text = pair
            content = archive.read(text).decode("utf-8")
            asserted = evidence["quote"]
            start, end, method = _locate(content, asserted)
            location = evidence.get("location") or evidence.get("evidence_location")
            statement = (evidence.get("claim") or evidence.get("observed")
                         or evidence.get("review_status") or evidence.get("status")
                         or "Recorded source quotation")
            digest = archive.record_claim(
                claim=statement, source=raw, text=text, quote=content[start:end],
                start=start, end=end, location=location,
                provenance={"input_json_pointer": input_path, "original_asserted_quote": asserted,
                            "location_method": method, "group": group,
                            "interpretation_not_independently_validated": True},
                provenance_refs=[artifacts[group].manifest_sha256])
            report["claims"].append({"id": identifier, "status": "verified",
                                     "manifest_sha256": digest, "source_url": evidence.get(
                                         "source_url", evidence.get("url")),
                                     "quote_match": method})
        except (ArchiveError, OSError, UnicodeError) as error:
            report["claims"].append({"id": identifier, "status": "blocked", "reason": str(error)})
            report["exceptions"].append({"id": identifier, "reason": str(error)})

    def pair_for(key, action):
        if key not in sources:
            try:
                sources[key] = action()
            except (ArchiveError, OSError, KeyError, TypeError, UnicodeError) as error:
                sources[key] = ArchiveError(str(error))
        return sources[key]

    for collection in ("papers", "foundations"):
        for number, paper in enumerate(documents["literature"][collection]):
            for index, evidence in enumerate(paper.get("evidence", [])):
                url = evidence["source_url"]
                pair = pair_for(("literature", url), lambda: preserve(
                    url, retrieval[url], radar, "retrieval"))
                claim(f"literature:{paper['id']}:{index}", evidence, "literature", pair,
                      f"/{collection}/{number}/evidence/{index}")
    for index, evidence in enumerate(documents["audit"]["evidence"]):
        url = evidence["url"]
        pair = pair_for(("audit", url), lambda: preserve(
            url, retrieval[url], radar, "retrieval",
            text_path=radar / "pilot" / evidence["cache"],
            text_hash=candidate[url]["sha256"], text_provenance="candidate"))
        claim("candidate:" + evidence["id"], evidence, "audit", pair, f"/evidence/{index}")
    for index, evidence in enumerate(documents["audit"]["independent_search"]["primary_findings"]):
        url = evidence["url"]
        pair = pair_for(("independent", url), lambda: preserve(
            url, independent[url], radar / "pilot/sources/candidate-independent-search",
            "independent"))
        claim("independent:" + evidence["candidate"], evidence, "audit", pair,
              f"/independent_search/primary_findings/{index}")
    for index, evidence in enumerate(documents["seed"]["cases"]):
        url = evidence["source_url"]
        pair = pair_for(("seed", evidence["id"]), lambda: preserve(
            url, evidence, project, "seed"))
        claim("seed:" + evidence["id"], evidence, "seed", pair, f"/cases/{index}")

    # Historical loss remains a separate ledger, even where another later copy exists.
    blind = documents["blind"]
    for entry in documents["blind_log"]:
        report["past_missing_lineage"].append({
            "phase": "original_blind_audit", "url": entry["url"],
            "status": "original_response_unavailable", "historical_sha256": None,
            "retrieval_log_manifest": artifacts["blind_log"].manifest_sha256,
            "later_independent_copy_preserved": any(
                source["url"] == entry["url"] for source in report["sources"]),
            "historical_lineage_restored": False})
    report["past_missing_lineage"].append({
        "phase": "original_blind_audit", "status": "original_texts_unavailable",
        "detail": blind["missing_extracted_texts"],
        "manifest_sha256": artifacts["blind"].manifest_sha256,
        "historical_lineage_restored": False})
    for entry in documents["retrieval"]:
        if not entry.get("cache"):
            report["past_missing_lineage"].append({
                "phase": "original_literature_retrieval", "url": entry["url"],
                "status": entry["status"], "bytes_observed": entry.get("bytes"),
                "detail": entry.get("error") or entry.get("note"),
                "historical_lineage_restored": False,
                "retrieval_log_manifest": artifacts["retrieval"].manifest_sha256})
    report["current_claims_verified"] = all(item["status"] == "verified" for item in report["claims"])
    report["verified_claim_count"] = sum(item["status"] == "verified" for item in report["claims"])
    report["historical_lineage_complete"] = False
    report["status"] = ("current_quoted_evidence_preserved_with_historical_losses"
                        if report["current_claims_verified"] else "blocked_current_evidence")
    report_ref = archive.store_bytes(
        _json(report), url="local:source-preservation-report", media_type="application/json",
        retrieved_at=None, representation="artifact",
        provenance={"role": "immutable migration report"},
        provenance_refs=[item["manifest_sha256"] for item in report["claims"]
                         if item["status"] == "verified"]
        + [item["manifest_sha256"] for item in previous_reports])
    report["immutable_report"] = report_ref.to_dict()
    projection = json.dumps(report, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    snapshot = root / "reports" / (_digest(projection) + ".json")
    _first_write(snapshot, projection)
    if previous_reports:
        # This is a current-report projection, not evidence. Its exact old bytes
        # have already been durably preserved above; all source records are immutable.
        pending = report_path.parent / (".pending-" + uuid.uuid4().hex)
        try:
            os.link(snapshot, pending)
            os.replace(pending, report_path)
            _sync_directory(report_path.parent)
        finally:
            pending.unlink(missing_ok=True)
    else:
        _first_write(report_path, projection)
    return report


def verify_preservation_report(project):
    """Recheck the immutable report and every referenced claim without retrieval."""
    project = Path(project)
    report = json.loads((project / "research_radar/pilot/iteration/source-preservation.json").read_bytes())
    immutable = dict(report)
    reference = Reference(**immutable.pop("immutable_report"))
    archive = Archive(project / "data/research-radar/archive")
    if archive.read(reference) != _json(immutable):
        raise ArchiveError("Report disagrees with its immutable archival snapshot")
    for reference in report["provenance_artifacts"].values():
        archive.read(Reference(**reference))
    for reference in report.get("previous_reports", []):
        archive.read(Reference(**reference))
    for source in report["sources"]:
        archive.read(Reference(**source["raw"]))
        archive.read(Reference(**source["text"]))
    for claim in report["claims"]:
        if claim["status"] == "verified":
            archive.verify_manifest(claim["manifest_sha256"])
    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preserve-existing", type=Path, required=True, metavar="PROJECT")
    parser.add_argument("--refresh", action="store_true",
                        help="Publish a new report while preserving the previous report unchanged")
    arguments = parser.parse_args()
    result = preserve_existing(arguments.preserve_existing, refresh=arguments.refresh)
    print(json.dumps({key: result[key] for key in
                      ("status", "verified_claim_count", "current_claims_verified",
                       "historical_lineage_complete", "exceptions")}, indent=2))
