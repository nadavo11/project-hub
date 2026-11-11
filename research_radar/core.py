"""Transactional campaign state. No model response is evidence by itself."""

from contextlib import contextmanager
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import uuid

from .ranking import DIMENSIONS, rank


ROOT = Path(__file__).resolve().parent
DEFAULT_HOME = ROOT.parent / "data" / "research-radar"
STATUSES = {
    "newly proposed", "awaiting evidence", "novelty audit", "reviewer assessment",
    "experiment ready", "experimenting", "promising", "rejected", "deferred",
}
RECORD_TYPES = {"papers": "external_publication", "opportunities": "internal_hypothesis",
                "tensions": "internal_research_observation", "decisions": "research_decision",
                "validations": "validation_record"}
ELIMINATION_DIMENSIONS = {"novelty", "scientific_significance", "technical_feasibility",
                          "insufficient_evidence", "unclassified"}
ROLES = [
    ("cartographer", "Literature Cartographer", "Map contributions and evaluations", "papers", "paper annotations"),
    ("tensions", "Failure Investigator", "Separate observations from unresolved explanations", "paper evidence", "tensions"),
    ("generator", "Opportunity Generator", "Form falsifiable hypotheses, not novelty assertions", "tensions and evidence", "opportunities"),
    ("novelty", "Novelty Investigator", "Distinguish substantive overlap from a defensible difference", "candidate facets and independent retrieval", "overlap and distinction audit"),
    ("reviewer", "Skeptical Area Chair", "Ground objections in competing evidence", "audits and proposals", "review"),
    ("experiment", "Experiment Architect", "Design the cheapest decisive falsification", "surviving hypotheses and objections", "experiment plans"),
]


def now():
    return datetime.now(timezone.utc).isoformat()


def uid(prefix):
    return prefix + "-" + uuid.uuid4().hex[:12]


def dumps(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def paper_key(paper):
    doi = str(paper.get("doi") or "").lower().removeprefix("https://doi.org/").strip()
    arxiv = re.sub(r"v\d+$", "", str(paper.get("arxiv_id") or ""))
    title = re.sub(r"[^a-z0-9]", "", str(paper.get("title", "")).lower())
    return doi or arxiv or title


class Conflict(ValueError):
    pass


class Store:
    def __init__(self, home=DEFAULT_HOME):
        self.home = Path(home)
        self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.home / "radar.sqlite"
        with self.db() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS campaigns (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, field TEXT NOT NULL,
                    status TEXT NOT NULL, stage TEXT NOT NULL, config TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS records (
                    campaign_id TEXT NOT NULL REFERENCES campaigns(id),
                    kind TEXT NOT NULL, id TEXT NOT NULL, body TEXT NOT NULL,
                    PRIMARY KEY(campaign_id,kind,id)
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL REFERENCES campaigns(id),
                    role TEXT NOT NULL, kind TEXT NOT NULL, status TEXT NOT NULL,
                    input TEXT NOT NULL, output TEXT, error TEXT,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, campaign_id TEXT NOT NULL,
                    job_id TEXT, kind TEXT NOT NULL, message TEXT NOT NULL,
                    data TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS jobs_queue ON jobs(status,created_at);
            """)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def decode(row):
        result = dict(row)
        for key in ("config", "input", "output", "data"):
            if key in result and result[key] is not None:
                result[key] = json.loads(result[key])
        return result

    def campaign(self, campaign_id):
        with self.db() as db:
            row = db.execute("SELECT * FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        if not row:
            raise KeyError("Campaign not found")
        return self.decode(row)

    def event(self, campaign_id, kind, message, data=None, job_id=None):
        with self.db() as db:
            db.execute("INSERT INTO events(campaign_id,job_id,kind,message,data,created_at) VALUES (?,?,?,?,?,?)",
                       (campaign_id, job_id, kind, message, dumps(data or {}), now()))

    @staticmethod
    def config(value):
        defaults = {
            "queries": [], "max_papers": 20, "max_requests": 40,
            "time_budget_seconds": 600, "api_budget_usd": 0,
            "compute_budget_hours": 0, "venues": ["CVPR", "ICCV", "ECCV"],
            "agent_enabled": True, "agent_timeout_seconds": 180,
            "search_depth": 1, "question": "",
            "ranking_weights": {key: 1 for key in DIMENSIONS},
        }
        if not isinstance(value, dict):
            raise ValueError("config must be an object")
        defaults.update(value)
        for key, low, high in [
            ("max_papers", 1, 25), ("max_requests", 1, 100),
            ("time_budget_seconds", 10, 3600), ("agent_timeout_seconds", 10, 600),
            ("search_depth", 1, 2),
        ]:
            if type(defaults[key]) is not int or not low <= defaults[key] <= high:
                raise ValueError(f"{key} must be an integer in [{low}, {high}] for the pilot")
        if not isinstance(defaults["queries"], list) or not all(
            isinstance(q, str) and 0 < len(q) <= 500 for q in defaults["queries"]
        ) or len(defaults["queries"]) > 10:
            raise ValueError("Provide at most ten nonempty search queries (500 characters each)")
        if type(defaults["agent_enabled"]) is not bool:
            raise ValueError("agent_enabled must be boolean")
        if not isinstance(defaults["venues"], list) or not all(isinstance(v, str) and len(v) <= 100 for v in defaults["venues"]):
            raise ValueError("venues must be a list of short conference names")
        if not isinstance(defaults["question"], str) or len(defaults["question"]) > 3000:
            raise ValueError("Research question must be at most 3000 characters")
        for key in ("date_from", "date_to"):
            if defaults.get(key):
                try:
                    date.fromisoformat(defaults[key])
                except (TypeError, ValueError):
                    raise ValueError(f"{key} must be an ISO calendar date") from None
        if defaults.get("date_from") and defaults.get("date_to") and defaults["date_from"] > defaults["date_to"]:
            raise ValueError("Publication date range is reversed")
        weights = defaults["ranking_weights"]
        if not isinstance(weights, dict) or set(weights) - set(DIMENSIONS) or not all(
            type(v) in (int, float) and 0 <= v <= 10 for v in weights.values()
        ):
            raise ValueError("Ranking weights must use the documented dimensions with values from zero to ten")
        if defaults["api_budget_usd"] != 0:
            raise ValueError("Paid external APIs are not supported; API budget must be zero")
        if not isinstance(defaults["compute_budget_hours"], (int, float)) or not 0 <= defaults["compute_budget_hours"] <= 72:
            raise ValueError("Compute planning budget must be between zero and 72 hours")
        return defaults

    def create(self, data):
        name, field = str(data.get("name", "")).strip(), str(data.get("field", "")).strip()
        if not name or not field or len(name) > 200 or len(field) > 1000:
            raise ValueError("A campaign name and bounded research field are required")
        config = self.config(data.get("config", {}))
        campaign_id = uid("campaign")
        stamp = now()
        with self.db() as db:
            db.execute("INSERT INTO campaigns VALUES (?,?,?,?,?,?,?,?)",
                       (campaign_id, name, field, "waiting", "field definition", dumps(config), stamp, stamp))
        self.event(campaign_id, "decision", "Field defined; waiting for researcher to start.", {"config": config})
        return self.campaign(campaign_id)

    def records(self, campaign_id, kind):
        with self.db() as db:
            rows = db.execute("SELECT body FROM records WHERE campaign_id=? AND kind=? ORDER BY id",
                              (campaign_id, kind)).fetchall()
        return [self.typed_record(kind, json.loads(row[0])) for row in rows]

    @staticmethod
    def typed_record(kind, record):
        record = dict(record)
        if kind in RECORD_TYPES:
            expected = RECORD_TYPES[kind]
            if record.get("record_type", expected) != expected:
                raise ValueError("Knowledge type conflicts with its collection")
            record["record_type"] = expected
        if kind == "opportunities":
            record["hypothesis_state"] = "prior_rejected_hypothesis" if record.get("status") == "rejected" else "internal_hypothesis"
        return record

    def put(self, campaign_id, kind, record):
        record = self.typed_record(kind, dict(record, campaign_id=campaign_id))
        record.setdefault("id", uid(kind.rstrip("s")))
        if kind == "papers":
            with self.db() as db:
                if db.execute("SELECT 1 FROM records WHERE campaign_id=? AND kind='opportunities' AND id=?",
                              (campaign_id, record["id"])).fetchone():
                    raise ValueError("An internal hypothesis cannot be reclassified as a publication")
            if not record.get("title") or not record.get("url"):
                raise ValueError("A paper requires a title and source URL")
            for existing in self.records(campaign_id, kind):
                same_title = re.sub(r"\W", "", existing["title"].lower()) == re.sub(r"\W", "", record["title"].lower())
                if paper_key(existing) == paper_key(record) or same_title:
                    old_sources = existing.get("sources", [])
                    sources = old_sources + [record["url"]]
                    # Incremental metadata must not overwrite independently examined evidence.
                    if existing.get("verification") == "full paper" and record.get("verification") != "full paper":
                        record = dict(existing, sources=list(dict.fromkeys(sources)))
                    else:
                        record = {**existing, **record, "id": existing["id"], "sources": list(dict.fromkeys(sources))}
                    break
        if kind == "opportunities" and record.get("status", "newly proposed") not in STATUSES:
            raise ValueError("Unknown opportunity state")
        if kind == "opportunities":
            with self.db() as db:
                if db.execute("SELECT 1 FROM records WHERE campaign_id=? AND kind='papers' AND id=?",
                              (campaign_id, record["id"])).fetchone():
                    raise ValueError("A publication ID cannot also identify an internal hypothesis")
        for reason in record.get("elimination_reasons", []):
            if not isinstance(reason, dict) or reason.get("dimension") not in ELIMINATION_DIMENSIONS or not str(reason.get("reason", "")).strip():
                raise ValueError("Elimination reasons require a valid dimension and an explanation")
        with self.db() as db:
            db.execute("INSERT INTO records VALUES (?,?,?,?) ON CONFLICT(campaign_id,kind,id) DO UPDATE SET body=excluded.body",
                       (campaign_id, kind, record["id"], dumps(record)))
        return record

    def find_record(self, kind, record_id, campaign_id=None):
        with self.db() as db:
            if campaign_id:
                rows = db.execute("SELECT body FROM records WHERE kind=? AND id=? AND campaign_id=?", (kind, record_id, campaign_id)).fetchall()
            else:
                rows = db.execute("SELECT body FROM records WHERE kind=? AND id=?", (kind, record_id)).fetchall()
        if len(rows) != 1:
            raise KeyError("Record missing or ambiguous")
        return self.typed_record(kind, json.loads(rows[0][0]))

    def enqueue(self, campaign_id, role, kind, inputs):
        job_id, stamp = uid("job"), now()
        with self.db() as db:
            db.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (job_id, campaign_id, role, kind, "queued", dumps(inputs), None, None, stamp, stamp))
        self.event(campaign_id, "queued", f"{role}: {kind} queued.", inputs, job_id)
        return self.job(job_id)

    def job(self, job_id):
        with self.db() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise KeyError("Job not found")
        return self.decode(row)

    def control(self, campaign_id, action, data=None):
        campaign = self.campaign(campaign_id)
        data = data or {}
        current = campaign["status"]
        if action == "configure":
            if current == "running":
                raise Conflict("Pause the campaign before changing its configuration")
            config = self.config(dict(campaign["config"], **data.get("config", {})))
            name, field = data.get("name", campaign["name"]), data.get("field", campaign["field"])
            if not isinstance(name, str) or not name.strip() or len(name) > 200:
                raise ValueError("Campaign name must be 1-200 characters")
            if not isinstance(field, str) or not field.strip() or len(field) > 1000:
                raise ValueError("Research field must be 1-1000 characters")
            with self.db() as db:
                db.execute("UPDATE campaigns SET config=?,name=?,field=?,updated_at=? WHERE id=?",
                           (dumps(config), name, field, now(), campaign_id))
        elif action in {"start", "resume"}:
            if current == "cancelled":
                raise Conflict("Cancelled campaigns are immutable; create a new campaign")
            if current == "running":
                return campaign
            with self.db() as db:
                count = db.execute("SELECT count(*) FROM jobs WHERE campaign_id=?", (campaign_id,)).fetchone()[0]
            if count == 0:
                queries = campaign["config"]["queries"] or [campaign["field"]]
                for query in queries:
                    self.enqueue(campaign_id, "cartographer", "search", {"query": query})
                for role, *_ in ROLES:
                    self.enqueue(campaign_id, role, "analysis", {})
            with self.db() as db:
                db.execute("UPDATE jobs SET status='queued',updated_at=? WHERE campaign_id=? AND status='interrupted'", (now(), campaign_id))
                pending = db.execute("SELECT count(*) FROM jobs WHERE campaign_id=? AND status NOT IN ('completed','cancelled')", (campaign_id,)).fetchone()[0]
                db.execute("UPDATE campaigns SET status=?,stage=?,updated_at=? WHERE id=?",
                           ("running" if pending else "completed", "investigation" if pending else "human decision", now(), campaign_id))
        elif action in {"pause", "cancel"}:
            if current == "cancelled":
                raise Conflict("Campaign already cancelled")
            with self.db() as db:
                db.execute("UPDATE campaigns SET status=?,updated_at=? WHERE id=?", ("paused" if action == "pause" else "cancelled", now(), campaign_id))
                if action == "cancel":
                    db.execute("UPDATE jobs SET status='cancelled',updated_at=? WHERE campaign_id=? AND status IN ('queued','running','paused','interrupted')", (now(), campaign_id))
        else:
            raise ValueError("Unknown campaign action")
        self.event(campaign_id, "control", f"Researcher requested {action}.", data)
        return self.campaign(campaign_id)

    def investigate(self, campaign_id, data):
        campaign = self.campaign(campaign_id)
        if campaign["status"] == "cancelled":
            raise Conflict("Cannot add work to a cancelled campaign")
        query = str(data.get("query") or data.get("note") or "").strip()
        if not query or len(query) > 1000:
            raise ValueError("A targeted query of at most 1000 characters is required")
        opportunity_id = data.get("opportunity_id")
        if opportunity_id:
            opportunity = self.find_record("opportunities", opportunity_id, campaign_id)
            if opportunity["campaign_id"] != campaign_id:
                raise ValueError("Opportunity belongs to another campaign")
        job = self.enqueue(campaign_id, "novelty", "search", dict(data, query=query[:500]))
        self.enqueue(campaign_id, "novelty", "analysis", {"opportunity_id": opportunity_id, "challenge": query})
        if campaign["status"] in {"completed", "waiting", "failed"}:
            with self.db() as db:
                db.execute("UPDATE campaigns SET status='running',stage='targeted investigation',updated_at=? WHERE id=?", (now(), campaign_id))
        return job

    def job_control(self, job_id, action, data):
        job = self.job(job_id)
        if self.campaign(job["campaign_id"])["status"] == "cancelled":
            raise Conflict("Campaign cancelled")
        if action == "pause" and job["status"] in {"queued", "running"}:
            target = "paused"
        elif action in {"resume", "retry", "redirect"} and job["status"] in {"failed", "paused", "interrupted", "waiting"}:
            target = "queued"
        else:
            raise Conflict("Action is not valid for this task state")
        inputs = job["input"]
        if action == "redirect":
            query = str(data.get("query", "")).strip()
            if not query:
                raise ValueError("A redirect query is required")
            inputs = dict(inputs, query=query[:500], challenge=query)
        with self.db() as db:
            db.execute("UPDATE jobs SET status=?,input=?,error=NULL,updated_at=? WHERE id=?", (target, dumps(inputs), now(), job_id))
            if target == "queued":
                db.execute("UPDATE campaigns SET status='running',updated_at=? WHERE id=? AND status IN ('failed','waiting','completed')", (now(), job["campaign_id"]))
        self.event(job["campaign_id"], "control", f"Task {action}.", data, job_id)
        return self.job(job_id)

    def decide(self, record_id, data):
        record = self.find_record("opportunities", record_id, data.get("campaign_id"))
        action, reason = data.get("action"), str(data.get("reason", "")).strip()
        if not reason:
            raise ValueError("Record the reason, comment, or challenge")
        if self.campaign(record["campaign_id"])["status"] == "cancelled":
            raise Conflict("Campaign cancelled")
        mapping = {"reject": "rejected", "reopen": "awaiting evidence", "defer": "deferred", "approve": "experiment ready"}
        if action in mapping:
            dimension = data.get("dimension", "unclassified")
            if action in {"reject", "defer"} and dimension not in ELIMINATION_DIMENSIONS:
                raise ValueError("Unknown elimination dimension")
            if action == "approve" and not record.get("experiment"):
                raise Conflict("A concrete experiment plan is required before approval")
            record["status"] = mapping[action]
            if action == "reject":
                record.setdefault("rejections", []).append({"reason": reason, "dimension": dimension, "at": now()})
            if action in {"reject", "defer"}:
                record.setdefault("elimination_reasons", []).append(
                    {"dimension": dimension, "reason": reason, "action": action, "at": now(),
                     "by": "local operator", "stage": "research decision"})
        elif action == "revise":
            hypothesis = str(data.get("hypothesis") or reason)
            record.setdefault("hypothesis_history", []).append({"hypothesis": record.get("hypothesis"), "at": now()})
            record["hypothesis"] = hypothesis
            record["status"] = "novelty audit"
            record["novelty"] = "uncertain after researcher revision; audit required"
        elif action == "prioritize":
            priority = data.get("priority", 0)
            if type(priority) is not int or not 0 <= priority <= 10:
                raise ValueError("Priority must be an integer between zero and ten")
            record["priority"] = priority
        elif action == "authorize":
            if not record.get("experiment"):
                raise Conflict("No experiment plan to authorize")
            record["experiment"]["authorization"] = {"by": "local operator", "at": now(), "reason": reason}
            record["experiment"]["status"] = "authorized; execution is manual"
        elif action == "result":
            experiment = record.get("experiment")
            results = data.get("results")
            if not experiment or not isinstance(results, dict) or not results.get("artifact") or not results.get("observations"):
                raise ValueError("An existing plan, result artifact location and observed measurements are required")
            experiment.setdefault("result_history", []).append({"results": results, "at": now(), "reason": reason})
            experiment["results"] = dict(results, record_type="experimental_observation",
                                          verification="operator-reported; independently unverified")
            experiment["status"] = "results recorded; independently unverified"
            record["status"] = "reviewer assessment"
        elif action not in {"comment", "challenge"}:
            raise ValueError("Unknown decision")
        record.setdefault("comments", []).append({"action": action, "text": reason, "at": now()})
        record = self.put(record["campaign_id"], "opportunities", record)
        self.put(record["campaign_id"], "decisions", {"id": uid("decision"), "opportunity_id": record_id, **data, "at": now()})
        self.event(record["campaign_id"], "decision", f"{action}: {record['title']}", data)
        if action in {"challenge", "revise"}:
            self.investigate(record["campaign_id"], {"query": reason, "opportunity_id": record_id})
        elif action == "result":
            self.enqueue(record["campaign_id"], "reviewer", "analysis", {"opportunity_id": record_id, "experimental_feedback": reason})
        return record

    def recover(self):
        with self.db() as db:
            rows = db.execute("SELECT id,campaign_id FROM jobs WHERE status='running'").fetchall()
            db.execute("UPDATE jobs SET status='interrupted',error='Worker interrupted; resume to retry safely',updated_at=? WHERE status='running'", (now(),))
            for row in rows:
                db.execute("UPDATE campaigns SET status='paused',updated_at=? WHERE id=? AND status='running'", (now(), row["campaign_id"]))
        for row in rows:
            self.event(row["campaign_id"], "recovery", "Interrupted task recovered; explicit resume required.", job_id=row["id"])

    def claim(self):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("""
                SELECT j.* FROM jobs j JOIN campaigns c ON c.id=j.campaign_id
                WHERE j.status='queued' AND c.status='running'
                  AND NOT EXISTS (SELECT 1 FROM jobs earlier WHERE earlier.campaign_id=j.campaign_id
                    AND earlier.rowid<j.rowid AND earlier.status NOT IN ('completed','cancelled'))
                ORDER BY j.rowid LIMIT 1
            """).fetchone()
            if not row:
                return None
            db.execute("UPDATE jobs SET status='running',updated_at=? WHERE id=?", (now(), row["id"]))
        return self.job(row["id"])

    def finish(self, job, status, output=None, error=None):
        with self.db() as db:
            row = db.execute("SELECT status FROM jobs WHERE id=?", (job["id"],)).fetchone()
            if row["status"] != "running":
                return
            db.execute("UPDATE jobs SET status=?,output=?,error=?,updated_at=? WHERE id=?",
                       (status, dumps(output), error, now(), job["id"]))
            if status in {"failed", "waiting"}:
                db.execute("UPDATE campaigns SET status=?,updated_at=? WHERE id=? AND status='running'",
                           (status, now(), job["campaign_id"]))
            pending = db.execute("SELECT count(*) FROM jobs WHERE campaign_id=? AND status NOT IN ('completed','cancelled')", (job["campaign_id"],)).fetchone()[0]
            if not pending:
                db.execute("UPDATE campaigns SET status='completed',stage='human decision',updated_at=? WHERE id=? AND status='running'", (now(), job["campaign_id"]))
        self.event(job["campaign_id"], status, error or f"{job['role']} finished; outputs retain their evidence labels.", output, job["id"])

    def costs(self, campaign_id):
        with self.db() as db:
            rows = db.execute("SELECT data FROM events WHERE campaign_id=? AND kind IN ('retrieval','cost')", (campaign_id,)).fetchall()
        values = [json.loads(row[0]) for row in rows]
        usage = [v["usage"] for v in values if isinstance(v.get("usage"), dict)]
        return {
            "http_requests": sum(v.get("http_requests") or 0 for v in values),
            "download_bytes": sum(v.get("download_bytes") or 0 for v in values),
            "elapsed_seconds": round(sum(v.get("elapsed_seconds") or 0 for v in values), 2),
            "api_cost_usd": None, "external_api_cost_usd": 0, "gpu_hours": 0,
            "cli_requests": sum(v.get("totalUserRequests", 0) for v in usage) if usage else None,
            "cli_nano_aiu": sum(v.get("totalNanoAiu", 0) for v in usage) if usage else None,
            "model_input_tokens": sum(sum(v.get("tokenDetails", {}).get(k, {}).get("tokenCount", 0)
                                           for k in ("input", "cache_read", "cache_write")) for v in usage) if usage else None,
            "model_output_tokens": sum(v.get("tokenDetails", {}).get("output", {}).get("tokenCount", 0) for v in usage) if usage else None,
            "measurement_notes": [v["measurement"] for v in values if v.get("measurement")],
            "incomplete_measurement_records": sum(any(k in v and v[k] is None for k in ("http_requests", "download_bytes", "elapsed_seconds")) for v in values),
            "note": "Elapsed work time, not wall-clock campaign time. CLI credits are recorded when available; USD conversion is unavailable.",
        }

    def state(self, campaign_id=None):
        with self.db() as db:
            campaigns = [self.decode(r) for r in db.execute("SELECT * FROM campaigns ORDER BY created_at DESC")]
        campaign_id = campaign_id or (campaigns[0]["id"] if campaigns else None)
        state = {"campaigns": campaigns, "campaign": campaign_id, "methodology": [
            {"id": role, "name": name, "purpose": purpose, "inputs": inputs, "outputs": outputs,
             "operations": "Source-grounded structured analysis in a fresh role context.",
             "validation": "Schema and source-link checks; independent audit; no model-only verification.",
             "state": "not started"} for role, name, purpose, inputs, outputs in ROLES
        ]}
        for kind in ("papers", "tensions", "opportunities", "validations", "decisions", "foundations"):
            state[kind] = self.records(campaign_id, kind) if campaign_id else []
        with self.db() as db:
            state["jobs"] = [self.decode(r) for r in db.execute("SELECT * FROM jobs WHERE campaign_id=? ORDER BY rowid", (campaign_id,))]
            state["events"] = [self.decode(r) for r in db.execute("SELECT * FROM events WHERE campaign_id=? ORDER BY id DESC LIMIT 500", (campaign_id,))]
        for role in state["methodology"]:
            jobs = [j for j in state["jobs"] if j["role"] == role["id"]]
            if jobs:
                role["state"] = jobs[-1]["status"]
        state["costs"] = self.costs(campaign_id)
        current = next((c for c in campaigns if c["id"] == campaign_id), {})
        state["ranking"] = rank(state["opportunities"], current.get("config", {}).get("ranking_weights", {}))
        return state

    def import_bundle(self, campaign_id, bundle, source):
        self.campaign(campaign_id)
        for kind in ("papers", "tensions", "opportunities", "validations", "foundations"):
            for record in bundle.get(kind, []):
                self.put(campaign_id, kind, record)
        digest = hashlib.sha256(dumps(bundle).encode()).hexdigest()
        previous = [e for e in self.state(campaign_id)["events"] if e["kind"] == "import" and e["data"].get("sha256") == digest]
        if not previous:
            self.event(campaign_id, "import", "Research artifacts imported; not a replay of live execution.", {"source": source, "sha256": digest})
            if bundle.get("costs"):
                self.event(campaign_id, "cost", "Imported measured research cost; model USD cost may be unknown.", bundle["costs"])
        return digest
