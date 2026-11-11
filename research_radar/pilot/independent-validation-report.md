# Research Radar pilot — independent validation report

**Final verdict: ITERATE**, 9 November 2026, following the final software and browser receipts. **Operational checks pass; scientific readiness and full archival reliability do not.** This report does not authorize experiments or a broader campaign.

**Operating URL:** <http://127.0.0.1:8776/?campaign=campaign-0919931353d1>  
**README:** `/home/nadavo/project-hub/research_radar/README.md`  
The service is loopback-only; this is not an authenticated public multi-user deployment.

## 1. Scope and independence

Three different activities must not be conflated:

1. **Literature investigation:** `literature.json` contains 21 domain/adjacent papers, 10 tensions, exactly three proposed opportunities and five methodology foundations. The published workbench separately labels three subsequent independent audit references. **The original corpus remains 21, not 24.** Reading was selective, not cover-to-cover or exhaustive.
2. **Actual runtime execution:** the original smoke completed search and six roles but admitted eight unrelated records and produced an infeasible sampling plan. It is now quarantined as failed scientific evidence. A separate, post-fix live browser campaign completed all six roles with eight papers, three tensions and one still-unvalidated candidate. Neither run automatically reproduces the larger 21-paper full-text investigation.
3. **Independent validation:** the five-description blind overlap audit, later candidate critique, and subsequently authorized independent candidate searches. The original candidate critique inspected shared primary-text caches; the later search phase independently obtained new public responses and PDFs.

The blind result was persisted before examining candidate material. Its SHA-256 remains `9f3479e269327854b343347004a612a6277cac2c335473a357f607a0009d6484`. The candidate critique also retains the pre-revision input snapshot. Literature revisions responding to the critique are explicitly recorded under `audit_updates`; they are not retroactively part of the original blinded generation.

All independent candidate research was completed before reading the scored overlap and coordinator verification artifacts for this report. **No benchmark-key file was read.** No new subagents, paid external APIs, scientific experiments or GPU runs were used by this auditor. Finalization inspected existing receipts and read the canonical campaign state; it ran no new tests or scholarly requests and changed only this report.

## 2. Expected versus observed

| Check | Expected | Observed evidence | Outcome and limitation |
|---|---|---|---|
| Bounded substantive corpus | Approximately 20 relevant papers with source-grounded claims, not invented titles | 21 domain/adjacent papers; 56 short evidence entries across domain papers and five foundations; selective reading and source limitations recorded in `literature.json` | Bounded corpus delivered. Coverage completeness and every scientific claim are not independently certified by a count or quotation match. |
| Independent problem inventory | At least eight independently reasoned tensions | `blind-audit.json` contains 11 tensions, with observed/inferred distinctions; literature investigator separately produced 10 | Requirement met procedurally. These are hypotheses and documented trade-offs, not experimentally validated opportunities. |
| Seeded overlap detection | At least four of five substantive overlaps, supported by independent mechanism checks | `overlap-results.json`: **5/5**, threshold **4/5**; `seed-source-verification.json` records five coordinator primary-PDF inspections | Passed this positive-case smoke test. Not a population accuracy, specificity or false-rejection estimate. |
| Source identity discipline | Wrong provisional citations rejected before use | Three coordinator provisional arXiv locators were unrelated and rejected; the blind investigator separately rejected one wrong locator. Final offline integrity receipt: **134 checks passed**, zero failures | Hash/title/quote/reference checks passed for retained evidence. They do not prove semantic interpretation, completeness or original snapshot preservation. |
| Reproducible source evidence | Exact inspected response bytes and provenance retained | Original blind PDFs/text were deleted; later five decisive PDFs were freshly fetched and retained by the coordinator. Candidate follow-up caches and three independently fetched PDFs are retained with hashes | Partial repair, not original snapshot recovery. See Section 4. |
| Independent candidate search | A new bounded search for each of O1–O3, outside shared-cache inspection | Exactly three new arXiv searches and three full-paper GETs; raw HTML, PDFs, text, URL/hash ledger retained | Six-request allowance met. Strong additional threats found; novelty still uncertain. |
| Candidate quality | A specific contribution distinguishable from closest prior art | O1 remains narrowly unresolved; O2 has direct uncertainty-propagation threats; O3 remains held | Not established. No candidate becomes publishable or “promising” merely because the pipeline completed. |
| Experimental feasibility | Accessible data/truth, comparable baselines, actual results | Three bounded plans with falsification rules; all remain planned, unauthorized and result-free. Data/license/checkpoint preflight is incomplete | Not validated. Planning estimates are not execution receipts. |
| Real pipeline execution | Retrieval, separate roles, durable structured output and cost receipts | Original runtime execution completed but failed topical/scientific checks. Separate corrected browser run: **8 papers, 3 tensions, 1 candidate**, all six roles completed; targeted assessments persisted | Functional execution demonstrated. Neither accepted records nor generated plans establish semantic relevance or novelty. |
| Backend/HTTP/validation behavior | Persistent state, controls, evidence safeguards, bounded requests, date guards and missing-judgment handling | Earlier auditor run: 45 passed. **Final receipt: 109 test executions, zero skipped, exit 0, 35.0725 s wrapper elapsed**, including ten real-server browser tests | Final receipt/log inspected, not rerun at finalization. Counts include inherited cases and synthetic fixtures, not independent scientific validations. |
| Existing Hub compatibility | Existing regression suite remains passing | Final combined command includes `test_server` and `test_agents`, with all selected tests passing; the earlier 43-pass Hub receipt is superseded by this combined run | No additional independent Hub rerun at finalization. |
| Browser/frontend journey | Actual researcher interaction in a browser, including active pause/resume | `live-ui-journey.json`: **14/14 functional PASS**, with original partial attempt retained and active-task UI-only retest | Functional journey passed. Initial attempt had two partial step entries; see Section 7 for the discrepancy with an earlier 13/1 progress summary. |
| Real-service restart persistence | Research records and task history survive a clean restart | `persistence-restart-check.json`: all three real campaigns have identical before/after SHA-256 values across papers, tensions, opportunities, validations, decisions and jobs | Restart persistence passed for the recorded snapshots. This cannot recover previously deleted raw source files. |
| Historical validation | Date-correct sources and meaningful protection against hindsight | Synthetic date/version guard test passes; no practical model-blinded historical retrospective was completed | Guard validated, historical scientific backtest not established. |
| Overall promotion | Mandatory scientific and engineering criteria supported | Candidate quality and feasibility unresolved. Operational checks pass, but original blind source snapshot loss prevents full archival reliability | **ITERATE.** No automatic GO; no demonstrated basis for a terminal NO-GO either. |

### Required six-criterion decision table

The canonical `pilot-go-no-go` validation was read from the main campaign after final receipts were published. It contains **20 cases: five seeded overlaps, one combined software case and 14 UI cases**. All those case outcomes are successful; this does not force the higher-level criteria to pass.

| Mandatory criterion | Final flag | Expected evidence | Observed basis and remaining failure |
|---|---|---|---|
| Citation reliability | **PASS** | Retained source identity, hashes, cited passages and explicit failure reporting | 134 offline integrity checks and five freshly restored decisive PDFs; rejected provisional identifiers retained. Not a guarantee of every interpretation or experiment. |
| Literature coverage | **PASS, bounded scope only** | Approximately 20 relevant domain papers across the stated problem | Original 21 papers plus three separately attributed subsequent audit references; five foundations separate. Selective, non-exhaustive reading remains a limitation. |
| Novelty detection | **PASS, seeded smoke only** | Detect substantive seeded overlap with independent primary evidence | 5/5 positive overlaps, independently source-checked. No specificity, false-rejection, memorization-free or general-discovery estimate. |
| Opportunity quality | **NOT ESTABLISHED / `passed=false`** | A sufficiently distinct technical contribution after adversarial comparison | O1 narrowly unresolved; O2 faces direct propagation/confidence threats; O3 held. No candidate has established defensible novelty or publication readiness. |
| Experimental feasibility | **NOT ESTABLISHED / `passed=false`** | Released annotations, licenses, usable caches and actual compute/resource preflight | Plans exist, but required annotations, licensing, pose caches and resource budgets have not been independently preflighted. No candidate experiment was executed. |
| System reliability | **NOT PASSED**; `operational_checks_passed=true` | Working controls/persistence **and** preserved original source evidence | Final software and functional UI checks pass. The original blind PDF/text snapshot was irrecoverably deleted. Five fresh downloads restore access, not original archival identity; this criterion remains `passed=false`. |

**Decision rule:** these are recorded evidence flags, not model self-ratings. Three mandatory criteria are false or unestablished, so **GO is unsupported**. No fatal citation/novelty/system flag requiring a terminal NO-GO is established. **ITERATE** accurately preserves the operational successes and outstanding scientific/archival failures.

## 3. Seeded overlap results and their meaning

The independently produced descriptions matched the following mechanisms:

| Case | Established work identified | Decisive overlap | Required qualification |
|---|---|---|---|
| B1 | *Each Part Matters: Local Patterns Facilitate Cross-view Geo-localization* | Square-ring partition, separate pooled parts and summed part cross-entropy | First preprint 2020; later journal publication. Do not equate square rings with exact arbitrary-angle rotation invariance. |
| B2 | *Sample4Geo: Hard Negative Sampling For Cross-View Geo-Localisation* | Geographic-neighbor initialization followed by dynamic feature-similarity mining, shared encoder | **Section 3.3 says geographic initialization was not possible on University-1652; shuffling was used there.** |
| B3 | *University-1652: A Multi-view Multi-source Benchmark for Drone-based Geo-localization* | University buildings, three platforms and both named retrieval directions | Main drone data are simulated. Publication is ACM Multimedia 2020; “navigation” here is retrieval, not demonstrated closed-loop control. |
| B4 | *TransGeo: Transformer Is All You Need for Cross-View Image Geo-Localization* | No polar transform; transformer attention drives non-uniform cropping and zoom-in | Inspected original evidence is street-to-aerial, not a drone-specific adaptation. |
| B5 | *RoMa: Robust Dense Feature Matching* | Frozen DINOv2 coarse features, classification anchors, separate fine features and robust refinement | General dense matching is not a guarantee of drone-to-satellite success. |

`validation.py::score_overlaps` requires a matching citation, a substantive overlap classification, and independent identity/mechanism flags. `test_overlap_requires_independent_evidence` demonstrates that matching titles alone do not pass and that an “uncertain” classification is not scored as a detected substantive overlap.

The scorer consumes human/coordinator verification flags; it is **not** an automated semantic verifier. For this report, the auditor separately checked the retained fresh PDF/text SHA-256 values and the quoted passages for all five cases. The coordinator's mechanism-inspection notes remain attributable to the coordinator.

All five cases were intentionally overlapping positives. There are no negative cases here from which to estimate specificity, false rejection, or discovery precision. Familiar methods may be present in model training. Procedural blinding does not establish memorization-free retrieval.

## 4. Citation and preservation failures

### Incorrect provisional locators

`operator-verification-log.json` records:

- `2107.14068` returned *On Charon's Far-Ultraviolet Surface Reflectance*, not LPN.
- `2303.11845` returned an unrelated Frobenius-algebra paper, not Sample4Geo.
- `2011.14506` returned an unrelated walled-Brauer-algebra paper, not LPN.

All three were rejected before accepted evidence was formed. One OpenAlex request returned HTTP 429; a previously successful response was reused rather than fabricated. A CVF page extraction yielded only boilerplate and was not treated as mechanism verification.

Separately, this blind investigator initially tried `2008.11613`, which returned an agricultural-robot pruning paper. That was rejected and the correct LPN record was found. The original audit also records an unsuccessful title formulation and local `python`/optional-parser failures; these are not hidden as successful research.

### Lost original blind source snapshot

The auditor deleted the original nine downloaded PDFs and associated extracted text during cleanup. This was a **source-preservation failure**. The unchanged blind audit and its retrieval log survived, but original PDF hashes had not been retained.

The coordinator subsequently performed **five fresh primary-source downloads** for B1–B5. Their original response bytes and extracted texts now exist under:

`/home/nadavo/project-hub/data/research-radar/sources/seed-verification/`

`seed-source-verification.json` records each exact path, source URL, PDF hash, text hash, timestamp, quote and inspection note. The auditor verified all five files against those hashes. Initial two-column extraction produced three quotation false negatives; re-extraction of the same downloaded PDFs in natural reading order repaired them without extra HTTP requests.

**This repairs access to the five decisive sources, not the original snapshot.** Byte identity with the original deleted downloads cannot be established, nor were all other original tension-source snapshots recovered. `sources/blind/manifest.json` correctly retains null original-source hashes rather than pretending recovery.

The subsequent candidate critique preserved six shared-cache primary texts and an exact candidate-input snapshot under `sources/candidate-audit/`. The independent search now preserves three new original PDFs and all three search responses under `sources/candidate-independent-search/`; these must not be deleted as scratch files.

The final `source-integrity.json` independently reports **134 offline hash/title/quotation/reference checks, all passing, no failures**. This verifies retained evidence within those check definitions. It does not undo the missing original snapshot, establish every interpretation, or reproduce a paper's experiment.

## 5. Candidate critique and independent search

### Shared-cache critique, before the new search

The first critique independently read primary text but used the literature investigator's downloads. It found additional substantive issues:

- RIC-Loc already reports **full-set behavior**, including ineligible queries, and includes common-mode scale uncertainty and residual-consistency inflation. Neither all-query evaluation nor generic inflation is an adequate O1 distinction.
- SkyReg already predicts **per-pixel confidence** and uses confidence-weighted regression. O2 must compare against that, not only residuals.
- OrthoLoC documents point maps, meshes and external geodata. Same-domain map/truth share reconstruction provenance; external DSM and local-coordinate release details matter for geodetic claims.
- HF-Net already clusters references by **3D covisibility**, strengthening O3's overlap beyond generic hierarchical localization.

The literature investigator incorporated these corrections with an explicit post-persistence boundary. That is a correction history, not proof that the original candidates were independently sound.

### New independent public retrieval

Each candidate received one new search plus one full-paper request. Exact search URLs, response bytes, hashes, durations and selected versions are in:

- `independent-candidate-audit.json::independent_search`
- `sources/candidate-independent-search/retrieval-log.json`

| Candidate | Exact query and screening | Independently retrieved primary paper | What it establishes—and does not |
|---|---|---|---|
| O1 | `covariance intersection`, title search; 24 returned titles screened | [*Overlapping Covariance Intersection: Fusion with Partial Structural Knowledge of Correlation from Multiple Sources*](https://arxiv.org/pdf/2603.16768), inspected v2, 1 Oct 2026 | Section II explicitly formalizes fusion with partial correlation structure. Dependence-aware fusion is established. Known linear models, zero-mean errors and covariance information are required; a geographic footprint proxy or biased wrong-building consensus does not automatically satisfy them. |
| O2 | `photogrammetry uncertainty propagation`, all-fields search; three titles screened | [*Uncertainty Quantification Framework for Aerial and UAV Photogrammetry through Error Propagation*](https://arxiv.org/pdf/2507.13486), first posted 2025, current PDF fetched | Pages 5–6 propagate camera/SfM and disparity/MVS error into point covariance and describe cross-covariance for anchor points. Generic per-anchor propagation is not new. Selective validity under erroneous external DSMs is not shown equivalent to this reconstruction task. |
| O3 | `view selection visual localization`, all-fields search; first 50 of 170 titles screened | [*OASIS: Optimal Arrangements for Sensing in SLAM*](https://arxiv.org/pdf/2309.10698), inspected v2, 21 Mar 2024 | Budgeted subset selection under E-optimal Fisher information, greedy optimization and convex verification are established. Physical sensor placement with independent known measurement models differs from reference selection with uncertain associations. |

The retained search responses also contain older correlated-estimation and sensor-coverage leads; those were abstract-only and were not promoted into full-paper claims. Searches were noisy, particularly O3; 120 O3 results were not retrieved. All six HTTP requests succeeded. One PDF extractor emitted a font warning but produced text; the PDF remains available for checking.

**Partial search remains uncertainty, not novelty.** The current evidence supports:

- **O1:** a narrowly defined footprint-dependence statistic might be testable, but it must improve on complete fusion, common-mode treatment, support counts and pose dispersion. Consistently wrong aliases can remain stable under leave-one-cluster-out tests.
- **O2:** compare finite-difference sensitivity with analytic ray/height derivatives, propagated covariance, incidence/relief covariates and existing point confidence. A constant-height sensitivity can reduce to `tan(off-nadir angle)`. Separate fixed-correspondence propagation from full matching failures and independent map-error truth.
- **O3:** maintain hold. A fixed matching budget is not a new selection principle. Compare against NMS, covisibility grouping and information/conditioning baselines; charge every support probe and cached full match. Diversity can waste budget when only one region is correct.

None has executed results, demonstrated a contribution beyond these threats, or earned a publication-readiness claim.

## 6. Real runtime failures, quarantine and corrected rerun

`runtime-smoke-observations.json` records campaign `campaign-b9637d19b9c4`:

- Two initial public search results expanded to ten papers during adversarial retrieval.
- Seven tasks completed: search, cartographer, failure investigator, generator, novelty investigator with further retrieval, reviewer and experiment architect.
- Two tensions and one unverified opportunity survived copying the database and reopening the application store.
- Real retrieval and CLI usage receipts were recorded; no GPU experiment ran.

The generated experiment nevertheless proposed a **geographic-neighbor warm-up on University-1652 without verifying the required metadata**. This contradicts the applicability caveat in Sample4Geo Section 3.3. The proposal therefore **fails feasibility validation as written**, despite successful orchestration.

A further concrete failure was discovered in the actual browser library: **eight admitted records were unrelated astronomy/physics papers**. The original arXiv fallback used unconjoined query words; successful HTTP retrieval and a requested domain label had been mistaken for relevant discovery. This is a real relevance failure, not a hypothetical risk or successful eight-paper search.

The original campaign is preserved and renamed **“FAILED relevance smoke | retained execution evidence”**. Its candidate is deferred and its agent is disabled. Neither the irrelevant records nor the rejected plan are included in the original 21-paper evidence corpus or silently deleted from history.

The recorded remediation:

- ArXiv queries now conjoin individually quoted non-stopword terms.
- A deterministic lexical relevance screen rejects unrelated provider records and records exclusions.
- Automatically retrieved metadata begins **task-unclassified**, rather than inheriting the requested domain as a demonstrated property.
- Regressions cover explicit query conjunction and rejection of the unrelated ATLAS-style result.

The novelty response also remained uncertain and did not use all newly retrieved competitors in its own summary. Separate processes plus fresh retrieval are useful controls, not assurance of complete comparison. The adapter receives abstracts and bounded excerpts, not a guarantee of full-paper comprehension.

On the fixed service, a **separate actual browser campaign**, `campaign-0dcdb4a15629`, completed all six roles and retained **eight papers, three tensions and one candidate**. A targeted follow-up changed assessment history **3→4**; the later active-work pause/resume retest changed it **4→5**, with reload persistence. These are execution observations, **not validation of a novel candidate**.

A keyword-like provider title—“Cross-view geo-localization, Image retrieval, Multiscale geometric modeling, Frequency domain enhancement”—remains explicitly **unverified bibliographic metadata**. The lexical repair is not expert semantic relevance or citation-quality validation. The eight-paper count must not be presented as eight independently verified scientific papers.

These failures remain visible alongside the corrected execution trace. The manual literature bundle, imported records, original failed smoke and corrected live run remain separately attributed.

## 7. Engineering checks and limits

The auditor's earlier bounded rerun remains recorded:

```text
python3 -m unittest research_radar.test_core research_radar.test_validation -v
Ran 45 tests in 11.917s
OK
```

Its full log remains `independent-backend-tests.log`; it is not the final suite count. The final coordinator receipt, `software-validation.json`, and exact `software-tests.log` report:

```text
/usr/bin/python3 -m unittest -v research_radar.test_core
  research_radar.test_validation research_radar.test_ui test_server test_agents

109 test executions; return code 0; zero skipped
Wrapper elapsed: 35.07248683999933 seconds
Runner log: Ran 109 tests in 34.965s — OK
```

The slight timing difference is wrapper versus unittest-runner elapsed, not conflicting pass counts. Finalization inspected these receipts and **did not rerun tests**. The final count supersedes earlier 45-, 100- or other intermediate counts; they must not be added together.

The log contains **ten** passing `ResearchRadarBrowserTests`:

1. `test_p0_campaign_creation_controls_and_persistence`
2. `test_p0_evidence_to_decision_and_authorization`
3. `test_p1_error_recovery_safe_links_and_campaign_switch`
4. `test_p1_external_feedback_is_scoped_unverified_and_does_not_execute`
5. `test_p1_failed_task_retry_redirect_and_polling_preserves_draft`
6. `test_p1_filters_comparison_validation_and_mobile`
7. `test_p1_foundations_serial_execution_and_default_validation`
8. `test_p1_method_landscape_uses_actual_families_and_opens_evidence`
9. `test_p1_revisions_priorities_challenges_and_form_errors`
10. `test_p1_structured_access_and_priority_do_not_imply_verification`

The software receipt's single `expected` sentence still says “eight” browser tests; the exact final test log lists ten. This report uses the executed cases, not that stale descriptive count. Automated browser scientific records are explicitly synthetic fixtures, unlike the separate live journey.

Scratch databases in the earlier auditor run were confined to the project and cleaned; public retrieval was mocked in relevant tests, and HTTP tests used loopback servers. The final software receipt likewise distinguishes fixture tests from real scientific evidence.

Direct source inspection of `core.py`, `validation.py`, `test_core.py`, `test_validation.py` and `ranking.py` supports the following limited engineering conclusions:

- Campaign pause/resume/cancel, interrupted-job recovery, failure blocking and retry paths have tests.
- Rejection history, hypothesis revision, targeted challenges, persistence and multi-campaign record handling are exercised.
- Paper deduplication retains stronger full-paper evidence rather than blindly replacing it with metadata.
- Fabricated paper identifiers and unknown evidence references are rejected in worker tests; agent-supplied “verified” evidence is demoted rather than accepted as self-verification.
- Authorization records manual execution intent; it does not launch GPU work. Result submission requires an artifact reference and observations, records results as independently unverified, and queues reviewer assessment.
- Budget validation, explicit provider failure, import-cost idempotence, HTTP create/control/export and selected HTTP boundary checks pass.
- Ranking leaves missing judgments unscored and explicitly labels complete weighted scores as subjective ordinal prioritization, not calibrated acceptance probabilities.
- `validation.py::verdict` requires all six mandatory criteria for GO and does not promote missing or false criteria. Its synthetic tests validate rule behavior, not the truth of supplied scientific judgments.

The final suite additionally records passing regressions for `test_arxiv_query_explicitly_conjoins_terms`, `test_completed_campaign_does_not_fake_running_on_resume`, and `test_date_boundaries_exclude_future_and_unknown_sources`. A completed campaign can no longer be made to look running simply by resuming with no work left. Publication-date form constraints now actively filter retrieved sources.

These are not a comprehensive security review, production reliability certification, load test, or demonstration that source-linked claims are scientifically correct. The final combined run includes the existing Hub suites. It was not independently repeated during finalization. Ruff and Node were unavailable; the receipt records Python compile checks and real Playwright JavaScript/CSP execution, not a linter/build pass.

### Final actual browser journey: 14/14 functional PASS

`live-ui-journey.json` records the following actual, non-fixture journey and its explicit active-work retest. All 14 current step verdicts are **PASS**:

| UI case | Expected behavior | Observed |
|---|---|---|
| UI-1 | Create a bounded real campaign | `campaign-0dcdb4a15629`; ten-paper/eight-request/900-second caps, real agent enabled, zero paid API/GPU allowance. |
| UI-2 | Start research | Real retrieval plus six role jobs queued. |
| UI-3 | Observe genuine work | Persisted events showed a completed search, running cartographer and queued dependent roles. |
| UI-4 | Inspect retrieved sources | Canonical links and honest abstract-access labels were available. Metadata-quality caveat remains; this is not full-paper verification. |
| UI-5 | Complete six roles | All six role executions completed; final state held eight papers, three tensions and one candidate. |
| UI-6 | Inspect a tension | The actual bundled-modifications tension exposed observation, explanations and source IDs. |
| UI-7 | Inspect hypothesis and novelty assessment | Generated attribution hypothesis and competing-work assessment were visible without claiming novelty proved. |
| UI-8 | Request targeted investigation | UI queued a real Sample4Geo search and linked novelty job. |
| UI-9 | Observe changed assessment | Completed follow-up changed assessment history **3→4**, tied to the actual job. |
| UI-10 | Inspect plan without execution | Dataset/baseline/metric/falsification planning was visible; no experiment/GPU authorization occurred. Plan feasibility is not certified by visibility. |
| UI-11 | Inspect separate main-pilot validation | Main campaign and its expected/observed/evidence records were distinguished from the fresh campaign. |
| UI-12 | Pause while work is active | UI interrupted running `job-e41e518b4ff8`; persisted campaign state became paused and job state interrupted. |
| UI-13 | Resume that same task | UI restarted the same task and it completed; assessment history **4→5**. No API-mutation fallback. |
| UI-14 | Reload and preserve results | Reload retained completed tasks and five assessments, then returned to the separately paused main campaign. |

The decisive retest sequence is **`job-e41e518b4ff8`: running → interrupted → running → completed**. `active_control_retest` records `api_mutation_fallback=false`, no application-code change during the retest, and no JavaScript, HTTP or request failures. Its snapshots, mutation receipts and screenshot paths are retained. The main scientific records were unchanged within the initial journey and within the retest.

**Initial failure is retained, not overwritten:** the first attempt tried Pause after the campaign had already completed, resorted to a same-origin status-only API call, and then observed a misleading running state on Resume. The completed-work behavior was repaired, and the final pass depends on the later UI-only active-work sequence—not on that initial attempt.

An earlier progress summary described the initial attempt as 13 PASS/1 PARTIAL. The **actual retained `initial_attempt.steps` currently contains 12 PASS/2 PARTIAL**, at steps 12 and 13, with overall `PARTIAL`. The report preserves the artifact's exact observations rather than repeating the earlier summary. The current top-level steps contain 14 PASS/0 PARTIAL.

The final functional UI pass closes the prior pending item. It does **not** close semantic metadata quality, scientific novelty, experiment feasibility, archival preservation or historical-leakage questions.

### Real-service restart persistence

`persistence-restart-check.json` records a clean service restart, with all three compared research-record/job snapshots unchanged:

| Campaign | Recorded state | Preserved counts: papers / tensions / opportunities / validations / decisions / jobs | Before/after SHA-256 |
|---|---|---|---|
| Main `campaign-0919931353d1` | Paused | **24 / 10 / 3 / 4 / 0 / 0**; the 24 papers are 21 original + 3 separately attributed audit references | Identical: `8254841dd774d9fbe9ae108dd826f8bf9d35fc7063e829b7fc2a117f92127b85` |
| Corrected live run `campaign-0dcdb4a15629` | Completed | **8 / 3 / 1 / 0 / 0 / 11** | Identical: `358b89375a9e4b50a4d055938072c46b9119ba3c7b77230da12c3fc68532f8eb` |
| Quarantined smoke `campaign-b9637d19b9c4` | Paused | **10 / 2 / 1 / 1 / 1 / 7**; failed relevance evidence remains retained | Identical: `d58c39ee8a8ae532c0749cb0b3bb143a6f0023c32cd6010b0e07ccaeeee69b96` |

The coordinator additionally reports the restarted service healthy and final actual-browser views checked: the 24-paper library, default go/no-go view and methodology, with no JavaScript errors. The canonical validation now includes a plain-language summary rather than relying on a JSON preview; its **ITERATE verdict and 20 cases are unchanged**. This auditor read the restart receipt and did not restart, re-probe or rerun the tests during finalization.

## 8. Historical/date validation

`cutoff_corpus` checks both first publication date and the **examined version date**. Missing/invalid dates and either post-cutoff date are excluded. The synthetic test includes one eligible source, a later revision, an unknown examined date and a future publication; only the eligible source remains.

This is a tested document/version guard. A historical model-blinded retrospective was **not practical/completed**, and no leakage-free backtest is claimed. Modern model training may contain later work even if documents are filtered. Contemporary downloaded revisions must not be treated as the original historical versions.

The final application's `date_range` constraints now hard-filter **publication dates**, with the final boundary regression passing. That operational filter is distinct from the separate examined-version guard and is **not** a historical-version or model-hindsight guarantee.

The independent O2 PDF lacks an extracted arXiv version marker; its source record states that limitation instead of inventing a version number.

## 9. Costs and accounting

The final authoritative aggregate is `cost-ledger.json`, covering the original pilot, quarantined smoke and corrected live run:

| Measured quantity | Final recorded value |
|---|---:|
| Public request operations | **103** |
| Downloaded bytes, measured lower bound | **398,821,269** |
| Recorded work seconds, partial | **1,082.03** |
| CLI usage-receipt requests | **14** |
| Raw nano-AIU | **89,994,880,000** |
| Input tokens including cache categories | **468,084** |
| Output tokens | **18,155** |
| Paid external API calls | **0** |
| GPU hours | **0** |
| Total monetary cost | **Unknown / `null`** |

The 103 operations comprise **93 main-pilot**, **3 original-smoke** and **7 corrected-live-run** operations. This is not a complete monetary bill: outer coordinating/research/browser agents' dollar costs are unavailable. Nine operator checks have counts but no byte/time measurements, so downloaded bytes are a **lower bound**. Tool-internal redirects are not separately measurable. Work seconds combine different measured intervals and are not a single non-overlapping wall-clock campaign duration.

The following phase provenance remains useful, but must not be added again to the aggregate. Some elapsed values are work time, others bounded wall-time snapshots; stages may overlap. Reused responses should not be charged as fresh downloads.

| Phase | Public HTTP requests | Downloaded response bytes | Recorded elapsed | Evidence |
|---|---:|---:|---:|---|
| Literature investigation | 56 | 267,027,628 | 619 s snapshot | `literature.json::costs`; includes discarded oversized response bytes and initial probe |
| Original blind investigation | 17 | 89,136,845 | 161.146 s evidence-freeze window | `blind-audit.json::costs` |
| First candidate critique | 0 | 0 new network bytes | Not separately timed | Shared primary-cache inspection, now snapshotted |
| Independent candidate searches | **6** | **8,229,036** | **90.831 s** evidence-freeze window | Retained six-entry URL/hash ledger |
| Coordinator source-identity checks | 9 reported | Unknown | Unknown | `operator-verification-log.json`; includes explicit failed/inconclusive checks |
| Fresh five-source mechanism verification | 5 | 32,796,809 | 11.0478 s | `seed-source-verification.json` |
| Actual runtime smoke | 3 | 1,260,804 | 80.69 s work time | `runtime-smoke-observations.json` |
| Corrected live UI run and targeted follow-ups | 7 | 370,147 | 119.32 s work time | `cost-ledger.json`, separate `campaign-0dcdb4a15629` |

The original smoke accounts for six CLI receipts and 34,385,450,000 nano-AIU; the corrected run adds eight receipts and 55,609,430,000 nano-AIU. Raw credits are reported without inventing a dollar conversion. **USD model cost is unknown (`null`), not zero.** A terminated process may lack a usage receipt; the ledger distinguishes process starts and observed receipts. Software fixture-test CPU time is in `software-validation.json`, not this public research ledger.

## 10. Decision boundary and remaining evidence

The seeded positive-overlap smoke, final software suite, 14-step functional browser journey, source-integrity checks and real-service restart check passed their stated checks. They do **not** establish candidate novelty, experiment feasibility, autonomous scientific correctness, complete original archival preservation or publication value.

Before any scientific promotion:

1. Incorporate the newly retrieved independent threats into each candidate's exact prior-art delta; do not broaden the search campaign under this report.
2. Verify data/license/annotation access and independent truth for any later, separately authorized experiment.
3. Keep the original University-1652 metadata/sampling error and eight-record relevance failure quarantined; no later functional pass retroactively validates that plan or source set.
4. Treat the completed browser/restart evidence as operational acceptance only; retain the initial partial attempt and the still-unverified provider metadata caveat.
5. Preserve all original and subsequent source/raw outputs going forward. The original blind snapshot loss is irreversible; fresh downloads must not be relabeled as original preservation.

**Final verdict: ITERATE.** Citation checks, bounded coverage and the seeded-overlap criterion pass. Opportunity quality and annotation/compute preflight remain unestablished. System operational checks pass, but its archival-reliability criterion remains false. These facts block GO; they do not establish the fatal condition needed for a terminal NO-GO. O3 remains held. No experiment or broader campaign is authorized, and no numerical model self-rating or acceptance probability is supplied.

## Evidence index

- `literature.json` — corpus, tensions, candidates, post-persistence audit updates and literature costs.
- `blind-audit.json` — unchanged independent five-case output and 11 tensions.
- `independent-candidate-audit.json` — source-grounded reviewer critiques and separately labeled independent search.
- `overlap-results.json` — coordinator-scored 5/5 result and scoring limitations.
- `seed-source-verification.json` — fresh replacement PDF/text paths, hashes and mechanism checks.
- `runtime-smoke-observations.json` — actual successful execution and unacceptable scientific proposal.
- `operator-verification-log.json` — three rejected provisional locators and other source-check failures.
- `independent-backend-tests.log` — this auditor's earlier 45-test run, retained rather than substituted for final receipts.
- `software-validation.json`, `software-tests.log` — final 109 executions, zero skips, ten real-server browser tests and combined Hub regressions.
- `live-ui-journey.json` — final 14/14 functional PASS, retained initial partial attempt, active UI-only pause/resume retest and metadata-quality caveat.
- `persistence-restart-check.json` — unchanged before/after hashes for all three real campaigns' recorded research data and jobs.
- `source-integrity.json` — 134 offline checks, all passed, with explicit semantic limitations.
- `cost-ledger.json` — final 103-operation aggregate, measured byte lower bound, partial work time and raw usage receipts.
- Main canonical campaign state — six-criterion `pilot-go-no-go`, ITERATE, 20 cases; `system_reliability.operational_checks_passed=true` while `system_reliability.passed=false`.
- `sources/blind/manifest.json` — explicit record of unavailable original blind source bytes.
- `sources/candidate-audit/manifest.json` — exact original candidate-input/shared-text snapshot hashes.
- `sources/candidate-independent-search/retrieval-log.json` — exact queries/URLs, raw responses, original PDFs, text hashes, request measurements.
- `../core.py`, `../validation.py`, `../test_core.py`, `../test_validation.py`, `../ranking.py` — inspected implementation and test definitions.
