# Research Radar

A persistent, evidence-first scientific workbench in Project Hub. Python standard
library backend, SQLite/WAL, and a dependency-free browser interface. No database
server, frontend build, external paid API, or GPU runner.

## Run

From `project-hub`:

```bash
python3 -m research_radar serve --port 8776
# http://127.0.0.1:8776/
```

The Project Hub launcher also has a Research Radar card on its next normal restart.
Existing shared applications do not need to be stopped. Radar binds to loopback
only; use an SSH tunnel for remote access. The API trusts local users and is not
an authenticated multi-user deployment. Do not expose it directly on a network.

Persistent state: `project-hub/data/research-radar/`. Back up this directory with
the server stopped, or use SQLite's backup API. It contains the database,
content-addressed public retrieval responses, per-job prompts, raw CLI traces and
usage receipts. UI JSON exports include research records, controls and recent
events; the database retains the complete event history.

## Failure Atlas

Open `http://127.0.0.1:8776/atlas.html`, or select **Failure Atlas** in the
workbench. The empirical cohort contains 36 real retrieved pairs, five measured
matching/sampling conditions, and paired depth/solver controls. Select a case,
inspect its original images, confidence map and correspondences, filter the
display, and export the exact evidence. Display filters do not rerun inference.

The atlas separates geographic identity, correspondence self-consistency,
metric geometry prerequisites and pose accuracy. Missing point ground truth is
explicit; a homography or RANSAC consensus is not labelled localization success.
Data persists in `data/research-radar/failure-atlas/`. The web server is read-only
for these experiments and does not launch model or GPU work.

See [the empirical scientific report](pilot/failure-first/scientific-report.md)
for measured findings, limitations and replay commands. General opportunity
generation is paused and M09 is stopped as a paper direction.

## New campaign

Create a campaign in the interface, set its question, field, queries, paper/request
limits and target venues, then start. The pilot hard limit is 25 papers and 100
public HTTP requests. Paid external API budget is always zero. Compute budget is
a planning constraint, never permission to execute a command.

```bash
python3 -m research_radar create \
  --name "Drone correspondence pilot" \
  --field "Drone-to-satellite retrieval and geometric localization" \
  --config research_radar/configs/drone-pilot.json
python3 -m research_radar start CAMPAIGN_ID
python3 -m research_radar inspect CAMPAIGN_ID
python3 -m research_radar pause CAMPAIGN_ID
python3 -m research_radar resume CAMPAIGN_ID
python3 -m research_radar search CAMPAIGN_ID "specific competing mechanism"
python3 -m research_radar report CAMPAIGN_ID > report.md
python3 -m research_radar export CAMPAIGN_ID > campaign.json
```

The server must be running to process queued work. CLI controls and browser
controls share the same database. `--home PATH` before the subcommand selects an
isolated store. To change fields, create a new campaign with different queries;
there is no drone-specific assumption in the scheduler or schema.

Pause stops further processing at the next checkpoint, aborts an active model
call, and preserves fetched evidence. Resume retries interrupted work. Cancel
preserves the full audit trail but makes the campaign terminal. A failed stage
blocks dependent stages; inspect the error and retry or redirect it. Restarting
recovers running jobs as interrupted and requires explicit resume.

## Roles and evidence flow

Public retrieval feeds the shared evidence store. Six fresh role contexts perform
cartography, failure investigation, hypothesis generation, adversarial novelty
assessment, reviewer criticism and falsification planning. The novelty stage
performs a separate competing-work search. Researcher challenges enqueue a real
search and a new novelty assessment; comments and revised hypotheses are supplied
to subsequent roles. All assessment history and rejection reasons remain stored.

The installed runtime is **GitHub Copilot CLI**, using existing configured access.
Claude Code is not assumed to be installed. Equivalent reusable profiles are in
`.claude/agents/` for use with Claude Code, but Claude Agent Teams execution is not
claimed or required. The runtime adapter gives models **no tools**: they can only
analyze supplied source records, return structured JSON and receive schema checks.
The backend, not a model-generated shell command, performs public retrieval.
This intentionally prevents an external paper from authorizing actions.

OpenAlex is the primary discovery integration; arXiv and Crossref are fallbacks.
Search depth two performs a bounded reference expansion when OpenAlex supplies
references. Queries, responses, errors, byte counts and elapsed time are recorded.
DOI, arXiv identifiers and normalized titles support incremental deduplication.
An unavailable source or exhausted budget becomes an explicit waiting/failed task.

Automated retrieval examines metadata/abstracts, **not full papers**. Full-paper
pilot examinations are imported with source locations and access labels. Model
annotations are always unverified inferences. Schema checks and paper-ID checks
prevent certain fabrications but do not establish claim truth. There is no
automatic scientific GO, experiment launch, or publication-acceptance prediction.

## Research decisions and experiments

Reject, reopen, defer, prioritize, revise and challenge actions persist their
reasons. Approval means a researcher is selecting a direction, not independently
certifying novelty. Experiment authorization records explicit permission; actual
execution remains manual. This pilot never starts GPU jobs. No result is shown
unless it has been recorded as an actual result.

The validation screen shows imported, reproducible test artifacts, including blind
test expectations, observed overlaps, failures and limitations. The five seeded
positives do not measure specificity or calibrated novelty accuracy. Historical
date filtering cannot remove model pretraining leakage.

## Cost interpretation

Public requests, retrieved bytes and work-time seconds are measured. CLI usage
receipts are retained when emitted by the installed version. Dollar conversion of
configured Copilot access is unknown, not zero. External paid API calls and GPU
hours are zero by construction. Discovery and agent failures also consume and
record budget. This is a bounded engineering pilot, not a large scan.

## Verification

```bash
python3 -m unittest -v research_radar.test_core
python3 -m unittest -v research_radar.test_ui
python3 -m unittest -v test_server test_agents
python3 -m research_radar.run_checks
python3 -m research_radar.check_pilot
```

Browser tests require the already-used Project Hub Playwright/Chrome setup. Test
fixtures are explicitly synthetic and isolated from the shared workspace. The
pilot files record real retrieval and independent investigation results separately
from software test fixtures.

The actual pilot verdict and failure history are in
`pilot/independent-validation-report.md`, with machine-readable cases in
`pilot/overlap-results.json`, `pilot/source-integrity.json`,
`pilot/software-validation.json`, and `pilot/live-ui-journey.json`. The original
21-paper investigation and the three subsequent independent audit references are
separately attributed. Primary-document caches remain local and are intentionally
excluded from version control rather than republished.

To re-score the seeded overlap benchmark without another model call:

```bash
python3 -m research_radar.validation \
  research_radar/pilot/benchmark-key.json \
  research_radar/pilot/blind-audit.json \
  research_radar/pilot/seed-source-verification.json
```

`python3 -m research_radar.assemble_pilot` publishes the recorded pilot into the
workbench. It refuses to overwrite a pilot that has researcher decision records.
This publication step is an explicitly labelled artifact import, not live agent
execution. Re-running verification that fetches primary sources incurs additional
public requests; do not confuse it with offline re-scoring.

## Import and extension

`python3 -m research_radar import CAMPAIGN_ID bundle.json` imports structured
`papers`, `tensions`, `opportunities`, `validations` and `foundations` collections.
An import is labelled as an import, never fabricated live agent activity.
Content hashes identify repeat imports; duplicate imports do not double count cost.

`core.py` defines persistence and controls; `retrieval.py` implements public
retrieval; `worker.py` defines role contracts and execution; `server.py` serves the
API and Markdown export. All external evidence is untrusted. Never grant a model
shell access to "fix" research retrieval or silently turn inferred claims into
verified evidence. New retrieval providers should preserve the same budget,
provenance and failure semantics.

## Bounded ITERATE campaign

The follow-up campaign is available at
`http://127.0.0.1:8776/?campaign=campaign-0ea39fd68d9c#validation`.
It reuses the existing corpus; it is not an expanded literature campaign.
Evidence, frozen inputs, actual model responses, before/after scores, prerequisite
checks and the independent report live in `pilot/iteration/`.

The balanced benchmark has five overlapping and five source-distinct controls.
Both policies are evaluated against the same frozen inputs; an independent
before-outcome audit checks the expected mechanisms. A perfect score means
assigned-source discrimination, **not global novelty**, clean historical
backtesting or valuable-opportunity discovery. False novelty, false rejection,
abstention and coverage are reported separately. Raw reviewer survival votes
are not the independent final decision.

`prerequisites.json` records actual data/checkpoint downloads and checks;
`geometry-preflight.json` is a CPU-only annotation self-consistency check,
not independent ground-truth validation or a research result. No downloaded
checkpoint or external project code was executed. Full learned-pipeline
feasibility remains a separate gate.

The iteration scripts preserve inputs and refuse silent replacement or
best-of-many reruns. `iteration.py` limits this recorded experiment to 25 public
requests, 120 MB of response data and five tool-free model invocations.
`cost-ledger.json` distinguishes measured requests/tokens from unavailable
coordinator/agent billing and unknown dollar conversion. Do not rerun acquisition
or model commands just to inspect the results.

Run the combined checks without replacing the original pilot receipt:

```bash
python3 -m research_radar.run_checks --output-dir research_radar/pilot/iteration
```

## Mechanism-first follow-up

The bounded follow-up is at
`http://127.0.0.1:8776/?campaign=campaign-16abc539e9ed#validation`.
Its frozen inputs, twelve original hypotheses, three-finalist selection, external
source comparisons, CPU diagnostics and independent verdict are in
`pilot/mechanism-first/`. Four isolated generator contexts each proposed one
mechanism for each of three reported limitations. Selection preceded six targeted
queries and examination of four new primary papers; no general scan was started.

Open **Opportunity board** and use **Reason dimension** to distinguish novelty,
scientific significance, technical feasibility and insufficient evidence. Open a
candidate's **Elimination & deferral history**, **Prior art**, **Review**, and
**Experiment** tabs for the original reasons, source comparisons, independent
adjudication and diagnostic limitations. Reopening retains earlier reasons.
Provisional screening reasons are not automatically verified scientific findings.
Publications, internal hypotheses and experimental observations have distinct
types; generated or rejected hypotheses cannot be cited as external publications.

The three CPU checks are a conditional MAP counterexample, a Schur-complement
identity check and a controlled uniform-height transformation on two preserved
samples. They are **not full candidate performance experiments** or evidence of
improved discovery. The run used eight direct CLI calls, ten public requests
(9,226,121 response bytes), and about 0.112 CPU seconds for diagnostics; no GPU,
training or new dependencies. Dollar cost and enclosing-agent billing are unknown.

One preserved quotation contained chart ticks rather than the supporting
statement. Independent inspection caught it; an append-only correction links the
actual prose while retaining the defective original. A valid hash is not proof
that a source supports a claim. Final artifact integrity and live UI receipts
accompany the independent report. Do not rerun acquisition or generation to view
results.

## Source preservation

`archive.py` provides an offline, standard-library, content-addressed archive at
`data/research-radar/archive/`. Back up this directory with the other persistent
state; ignored local evidence is not protected by a Git commit. Never delete
source caches or archive objects during cleanup.

```python
from research_radar.archive import Archive, Reference

archive = Archive("data/research-radar/archive")
raw = archive.store_bytes(response_bytes, url=source_url,
                          media_type="application/pdf", retrieved_at=recorded_timestamp)
text = archive.store_text(extracted_text, raw=raw, extraction="pdftotext -layout")
start = extracted_text.index(exact_quote)
claim_hash = archive.record_claim(
    claim=source_statement, source=raw, text=text, quote=exact_quote,
    start=start, end=start + len(exact_quote), location="PDF page 4, Section 3")
archive.verify_manifest(claim_hash)  # raises ArchiveError on missing/tampered evidence
serialized_reference = raw.to_dict()
verified_bytes = archive.read(Reference(**serialized_reference))
```

The caller supplies bytes/text; the archive performs no HTTP, model, or GPU calls.
Use `retrieved_at=None` when unknown, never the archival deposit time. Optional
`provenance` dictionaries retain extraction/access qualifications;
`provenance_refs=[manifest_sha256, ...]` adds recursively verified artifact links.
`store_bytes(..., representation="artifact")` preserves local logs/input snapshots,
not purported HTTP originals. References are frozen dataclasses with `sha256`,
`size`, and `manifest_sha256`. Offsets count decoded Unicode characters, zero-based
and end-exclusive. A text snapshot must link its actual preserved raw reference.

Writes fsync staged bytes and atomically link them into place without replacing
existing evidence. Reuse and reads recheck SHA-256, including provenance links.
Interrupted staging files are ignored; retry the deposit. Do not sweep orphan
files: the implementation removes only its own explicitly named staging file.
Hash verification establishes integrity and an exact quotation, **not** scientific
truth, author authentication, extraction correctness, or semantic entailment.

```bash
python3 -m unittest -v research_radar.test_archive
python3 -m research_radar.archive --preserve-existing .
```

The second command verifies an existing report or creates the bounded local-only
migration. `--refresh` produces a new report while preserving the previous report's
exact bytes; only the current-report projection changes, never archived evidence.
`verify_preservation_report(project)` verifies that projection against its immutable
snapshot and rechecks every linked claim. Synthetic negative-test fixtures remain
under separate `archive/test-*` directories and are not research evidence.

`pilot/iteration/source-preservation.json` distinguishes current verified quotation
chains from permanently missing historical blind-audit responses/extractions,
the discarded oversized PDF prefix, and the initial partial probe. Later copies
do not retroactively restore that lineage. It also labels newly generated offline
HTML text and historical normalized-quote lookups; each claim stores the actual
exact substring and offsets alongside the original asserted quotation.
