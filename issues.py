"""Issue tracker storage: reporting through completion, with comments and history."""

import json
import re
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

from projects import check_project, project_context

STATUSES = ("open", "in_progress", "in_review", "done", "closed")
CLOSED_STATUSES = ("done", "closed")
AGENT_STATUSES = ("in_review",)
PRIORITIES = ("low", "medium", "high", "critical")
TYPES = ("bug", "feature", "task", "question")
MAX_ISSUES = 5000
MAX_COMMENTS = 500
MAX_ACTIVITY = 500
MAX_LABELS = 10


AI_BLOCK = re.compile(r"```issue-json\s*(\{.*?\})\s*```", re.S)


def parse_ai_report(text):
    """Extract the structured issue fields an agent reports in an issue-json block."""
    match = AI_BLOCK.search(text or "")
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except ValueError:
        return None
    fields = {key: data[key] for key in ("title", "body", "type", "priority", "labels") if key in data}
    if data.get("status") in AGENT_STATUSES:
        fields["status"] = data["status"]
    if isinstance(fields.get("labels"), list):
        fields["labels"] = [str(label)[:30] for label in fields["labels"]][:MAX_LABELS - 1]
    return fields


def issue_request(issue, others=(), projects=(), hub=""):
    """Fixed template so every AI add-issue thread starts with the same context and rules."""
    known = "\n".join(
        f"- #{o['number']} [{o['status']}] {o['title'][:100]}" for o in others[-40:] if o["number"] != issue["number"]
    ) or "- (none)"
    where = "\n".join(f"- {p}" for p in projects) or "- (none)"
    return f"""AI ADD ISSUE #{issue['number']}

You are a senior engineer and expert issue author/triager. Your deliverable is ONE issue so complete that a developer who has never seen this conversation can understand, locate, reproduce and fix it without asking anything.

THE OPERATOR'S REPORT (verbatim, their own words; may be vague or short)
{issue['body']}

{project_context(issue.get('project', '')) or ''}CONTEXT
- Project Hub (this dashboard) lives in: {hub or 'unknown'}  (server.py, issues.py, agent_chat.py, static/*.js|css, test_*.py, logs/, data/)
- Projects launched from the hub (paths, for locating code and logs):
{where}
- Existing issues (check for duplicates; if this duplicates one, say so and link its number in the body instead of restating it):
{known}

HOW THIS WORKS (follow exactly)
1. This thread is the dedicated discussion for this one issue. The operator reads everything you write here.
2. First reply: a short plan (3-5 bullets), then start investigating immediately.
3. INVESTIGATE before writing. Work read-only: never modify, create or delete project files, never restart services. You may read code, docs, git history (git log/blame/diff), logs, configs, and run harmless read-only commands (grep, ls, curl on localhost GET endpoints, running existing tests is fine only if they do not write to real data).
   - Identify which project/component the report is about, and find the exact files, functions and line numbers involved.
   - For bugs: try to reproduce or find the cause (error in logs, failing code path). Capture exact error messages and log excerpts (trim to the relevant lines, never include secrets, keys or tokens).
   - For features: find where it would hook in, the closest existing pattern to copy, and what could break.
   - Check recent git history for related changes.
4. Do not invent facts. Mark anything you could not verify as "Unverified" and say what you checked. Separate observed facts from hypotheses.
5. Only ask a question if the report is impossible to interpret, as ONE clear question ending with TASK_STATUS: NEEDS_INPUT. Otherwise make reasonable assumptions and list them.
6. Do not edit the issue yourself. The hub applies your issue-json block to issue #{issue['number']} automatically when your final line is TASK_STATUS: DONE.

ISSUE QUALITY BAR (the body must contain every applicable section, in markdown)
## Summary  - 1-3 sentences: what and why it matters (impact, who is affected, severity).
## Context  - project/component, environment (paths, ports, versions, branch/commit), when it started if known.
## Steps to reproduce  (bugs) numbered, exact and minimal; or ## Motivation and proposal (features).
## Expected behaviour / ## Actual behaviour  - with exact error text or log excerpts in code fences.
## Where to look  - bullet list of file paths with line numbers/functions, log files, endpoints, related commits, related issues (#N). Say why each matters.
## Root cause analysis  - verified cause, or ranked hypotheses with the evidence for each and how to confirm.
## Suggested approach  - concrete implementation direction, pitfalls, and tests to add.
## Acceptance criteria  - checklist (- [ ]) of verifiable outcomes.
## Notes  - assumptions, open questions, things you could not verify, workarounds.
The title must be specific and searchable (component + symptom/goal, max 120 chars), never generic like "Bug" or a copy of the report. Priority: critical = data loss/security/outage, high = main feature broken, medium = noticeable defect or valuable feature, low = polish. Labels: 2-4 short lowercase labels naming the component and kind (e.g. "hub-ui", "localization", "regression").

FINAL REPORT TEMPLATE (use for every final reply)
## Issue #{issue['number']}: <title>
**Status:** Done | Needs your input
**Summary:** <1-3 sentences, including your confidence in the diagnosis>
**Investigated:** <files, logs, commands you actually looked at>
**Open risks:** <or "none">
```issue-json
{{"title": "<title>", "body": "<full markdown body as one JSON string; escape newlines as \\n and quotes as \\\"; sections above>", "type": "bug | feature | task | question", "priority": "low | medium | high | critical", "labels": ["..."], "status": "in_review"}}
```
TASK_STATUS: DONE | NEEDS_INPUT | IN_PROGRESS

Include "status": "in_review" in the issue-json block when the issue is complete and ready for the operator to review (the only status you may set).
The last line must be exactly one of those TASK_STATUS values. Use DONE only when the issue-json block is complete and valid JSON.
"""


class IssueConflict(ValueError):
    def __init__(self, message, current=None):
        super().__init__(message)
        self.current = current


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def valid_date(value):
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


class IssueStore:
    """Revisioned issues persisted atomically to one JSON file."""

    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()
        self.issues = []
        self.next_number = 1
        self.next_comment = 1
        if self.path.exists():
            data = json.loads(self.path.read_text())
            self.issues = data.get("issues", [])
            self.next_number = int(data.get("next_number", 1))
            self.next_comment = int(data.get("next_comment", 1))

    @staticmethod
    def _atomic_write(path, content):
        fd, name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def _save(self):
        self.path.parent.mkdir(exist_ok=True, mode=0o700)
        content = json.dumps({
            "issues": self.issues,
            "next_number": self.next_number,
            "next_comment": self.next_comment,
        }).encode()
        if self.path.exists():
            self._atomic_write(Path(str(self.path) + ".bak"), self.path.read_bytes())
        self._atomic_write(self.path, content)

    def _find(self, number):
        return next((issue for issue in self.issues if issue["number"] == number), None)

    @staticmethod
    def _text(body, key, limit, required=False):
        value = body[key]
        if not isinstance(value, str):
            raise ValueError(f"{key} must be text.")
        value = value.strip() if key != "body" else value
        if required and not value:
            raise ValueError(f"{key} is required.")
        if len(value) > limit:
            raise ValueError(f"{key} must be at most {limit} characters.")
        return value

    def _clean(self, body, creating):
        if not isinstance(body, dict):
            raise ValueError("Invalid request.")
        clean = {}
        if "title" in body or creating:
            if "title" not in body:
                raise ValueError("title is required.")
            clean["title"] = self._text(body, "title", 200, required=True)
        if "body" in body:
            clean["body"] = self._text(body, "body", 20000)
        for key, allowed in (("status", STATUSES), ("priority", PRIORITIES), ("type", TYPES)):
            if key in body:
                if body[key] not in allowed:
                    raise ValueError(f"{key} must be one of: {', '.join(allowed)}.")
                clean[key] = body[key]
        if "project" in body:
            clean["project"] = check_project(body["project"])
        if "assignee" in body:
            clean["assignee"] = self._text(body, "assignee", 40)
        if "due" in body:
            due = body["due"]
            if due in (None, ""):
                clean["due"] = ""
            elif isinstance(due, str) and valid_date(due):
                clean["due"] = due
            else:
                raise ValueError("due must be a date as YYYY-MM-DD.")
        if "labels" in body:
            labels = body["labels"]
            if not isinstance(labels, list) or len(labels) > MAX_LABELS:
                raise ValueError(f"labels must be a list of at most {MAX_LABELS} items.")
            seen = []
            for label in labels:
                if not isinstance(label, str):
                    raise ValueError("labels must be text.")
                label = label.strip()
                if len(label) > 30:
                    raise ValueError("A label must be at most 30 characters.")
                if label and label.lower() not in [item.lower() for item in seen]:
                    seen.append(label)
            clean["labels"] = seen
        return clean

    @staticmethod
    def _actor(body):
        actor = body.get("actor", "") if isinstance(body, dict) else ""
        if not isinstance(actor, str) or not actor.strip() or len(actor) > 40:
            raise ValueError("actor is required (at most 40 characters).")
        return actor.strip()

    @staticmethod
    def _log(issue, actor, kind, **details):
        issue["activity"].append({"at": now(), "actor": actor, "type": kind, **details})
        del issue["activity"][:-MAX_ACTIVITY]

    @staticmethod
    def summary(issue):
        return {
            key: value for key, value in issue.items() if key not in ("comments", "activity")
        } | {"comment_count": len(issue["comments"])}

    def list(self):
        with self.lock:
            return [self.summary(issue) for issue in self.issues]

    def get(self, number):
        with self.lock:
            issue = self._find(number)
            return json.loads(json.dumps(issue)) if issue else None

    def create(self, body):
        with self.lock:
            clean = self._clean(body, creating=True)
            actor = self._actor(body)
            reporter = actor
            if len(self.issues) >= MAX_ISSUES:
                raise ValueError("The issue limit has been reached.")
            stamp = now()
            issue = {
                "number": self.next_number,
                "title": clean["title"],
                "body": clean.get("body", ""),
                "status": clean.get("status", "open"),
                "priority": clean.get("priority", "medium"),
                "type": clean.get("type", "bug"),
                "assignee": clean.get("assignee", ""),
                "project": clean.get("project", ""),
                "reporter": reporter,
                "labels": clean.get("labels", []),
                "due": clean.get("due", ""),
                "created_at": stamp,
                "updated_at": stamp,
                "closed_at": stamp if clean.get("status") in CLOSED_STATUSES else None,
                "rev": 1,
                "comments": [],
                "activity": [],
            }
            self._log(issue, actor, "created")
            self.issues.append(issue)
            self.next_number += 1
            self._save()
            return json.loads(json.dumps(issue))

    def update(self, number, body):
        with self.lock:
            issue = self._find(number)
            if issue is None:
                return None
            clean = self._clean(body, creating=False)
            actor = self._actor(body)
            rev = body.get("rev")
            if rev is not None and rev != issue["rev"]:
                raise IssueConflict(
                    "This issue changed since you opened it. Review the latest version.",
                    self.summary(issue),
                )
            before = json.loads(json.dumps(issue))
            for key, value in clean.items():
                if issue.get(key, "") == value:
                    continue
                if key == "body":
                    self._log(issue, actor, "edited", field="description")
                elif key == "title":
                    self._log(issue, actor, "renamed", **{"from": issue[key], "to": value})
                elif key == "labels":
                    self._log(issue, actor, "labels", **{"from": issue[key], "to": value})
                else:
                    self._log(issue, actor, key, **{"from": issue.get(key, ""), "to": value})
                issue[key] = value
            if issue == before:
                return json.loads(json.dumps(issue))
            if issue["status"] in CLOSED_STATUSES:
                if before["status"] not in CLOSED_STATUSES:
                    issue["closed_at"] = now()
            else:
                issue["closed_at"] = None
            issue["updated_at"] = now()
            issue["rev"] += 1
            self._save()
            return json.loads(json.dumps(issue))

    def delete(self, number):
        with self.lock:
            issue = self._find(number)
            if issue is None:
                return False
            self.issues.remove(issue)
            self._save()
            return True

    def add_comment(self, number, body):
        with self.lock:
            issue = self._find(number)
            if issue is None:
                return None
            actor = self._actor(body)
            if not isinstance(body.get("text"), str) or not body["text"].strip():
                raise ValueError("text is required.")
            if len(body["text"]) > 10000:
                raise ValueError("text must be at most 10000 characters.")
            if len(issue["comments"]) >= MAX_COMMENTS:
                raise ValueError("The comment limit for this issue has been reached.")
            comment = {
                "id": self.next_comment,
                "author": actor,
                "text": body["text"].strip(),
                "created_at": now(),
                "edited_at": None,
            }
            self.next_comment += 1
            issue["comments"].append(comment)
            issue["updated_at"] = now()
            self._save()
            return comment

    def edit_comment(self, number, comment_id, body):
        with self.lock:
            issue = self._find(number)
            comment = next(
                (item for item in (issue or {}).get("comments", []) if item["id"] == comment_id),
                None,
            )
            if comment is None:
                return None
            self._actor(body)
            if not isinstance(body.get("text"), str) or not body["text"].strip():
                raise ValueError("text is required.")
            if len(body["text"]) > 10000:
                raise ValueError("text must be at most 10000 characters.")
            comment["text"] = body["text"].strip()
            comment["edited_at"] = now()
            issue["updated_at"] = now()
            self._save()
            return comment

    def delete_comment(self, number, comment_id):
        with self.lock:
            issue = self._find(number)
            comment = next(
                (item for item in (issue or {}).get("comments", []) if item["id"] == comment_id),
                None,
            )
            if comment is None:
                return False
            issue["comments"].remove(comment)
            issue["updated_at"] = now()
            self._save()
            return True
