# Research Radar: bounded literature pilot

**Date:** 2026-11-09  
**Decision:** **ITERATE. No candidate is presently defensibly novel or publication-ready.**  
**Scope:** 21 domain/adjacent papers, five separate methodological foundations, ten evidence-backed tensions, exactly three prospective experiments.

The useful near-term outcome is a falsifiable diagnosis of reliability failures—not a claim that adding geometry or uncertainty to retrieval is new. All experiment results are `null`; all experiments remain **not authorized**.

## What was actually done

Local survey inventories supplied candidate identifiers, not trusted conclusions. Fresh public arXiv pages verified titles, author lists and first-posting dates. Twenty domain PDFs and four foundation PDFs were downloaded and converted with `pdftotext`; a further domain paper, SkyReg, was examined through full-text HTML after its PDF exceeded the response-size budget. The supplied Anthropic engineering page was fetched directly.

Reading was **selective**, concentrating on task definitions, mechanisms, evaluation protocols and decisive limitations. “Full paper” in the JSON identifies the source of a passage, not a claim of cover-to-cover reading. No paper experiment was reproduced. Author claims remain author claims.

Three new arXiv searches supplemented identifier discovery:

- `drone satellite uncertainty localization`: surfaced **PAUL**, subsequently read.
- `cross view selective localization`: noisy; the first fourteen titles were screened. This is not a negative novelty result.
- `drone satellite correspondence benchmark`: reinforced PAUL and surfaced a day/night benchmark outside this bounded pass.

The complete records are in [`literature.json`](literature.json). Each paper has short supporting quotations, URLs, full-text locations, examination limits and a cache path. Raw retrieval records include timestamps, response sizes, durations and SHA-256 hashes in [`../sources/retrieval-log.json`](../sources/retrieval-log.json). Full texts are local research caches, not content intended for republication.

**Blinding:** The initial tensions and candidates were developed without inspecting any `pilot/benchmark*` artifact or independent-auditor output. After they were persisted, a correction message arrived from the independent auditor. The corrections below were checked against existing primary-text caches; no audit artifact or benchmark file was opened.

## Landscape and source map

First-posting years below are **not publication years**. Independently unverified venues/DOIs are null in the structured record; author-reported venues are labeled separately.

| Family | Examined source | What it establishes—and does not |
|---|---|---|
| Drone retrieval | [University-1652](https://arxiv.org/abs/2002.12186) | Building-identity retrieval with synthetic drone views; not corner accuracy or 6-DoF pose. |
| Real UAV retrieval | [DenseUAV](https://arxiv.org/abs/2201.09201) | Dense, down-looking self-positioning data and distance-sensitive retrieval; not unrestricted oblique geometry. |
| Contrastive retrieval | [Sample4Geo](https://arxiv.org/abs/2303.11851) | Strong simple hard-negative retrieval control; local correspondence is a different target. |
| Adjacent worldwide geolocation | [GeoCLIP](https://arxiv.org/abs/2309.16020) | Image-to-GPS encoding evaluated at kilometer scales; do not conflate with UAV satellite matching. |
| Real map data | [UAV-VisLoc](https://arxiv.org/abs/2405.11936) | Multi-location/platform/terrain map localization data; annotation availability still needs experiment preflight. |
| Partial overlap | [Game4Loc](https://arxiv.org/abs/2409.16925) | GTA-UAV partial matches and overlap-weighted contrastive learning; generic partial-overlap formulation is established. |
| Extreme views | [OffNadirLoc](https://arxiv.org/abs/2607.19951) | Large-off-nadir rendered retrieval and structure-aware weighting; core metrics are still recall/AP. |
| Retrieval plus metric pose | [RIM](https://arxiv.org/abs/2607.20116) | Shared backbone, local descriptor distillation, geometric reranking and PnP; confidence fusion is explicitly proposed as future work. |
| Object-centric retrieval | [InfoGeo](https://arxiv.org/abs/2605.07099) | Structural invariance through slots/information constraints; appendix identifies altitude/concept-scalability limitations. |
| Dense georegistration | [SkyReg](https://arxiv.org/abs/2608.28891) | Pixelwise geodetic supervision and a 3D-aware registration method; a dense-registration task is not a new gap. |
| Joint coarse/fine learning | [UnifyGeo](https://arxiv.org/abs/2505.07622) | Retrieval, metric localization and reranking in one framework; terrestrial evidence is not automatically UAV evidence. |
| Geometric alignment | [Correlation-aware homography](https://arxiv.org/abs/2308.16906) | Ground-to-aerial transformation/alignment; scene assumptions matter for oblique UAV imagery. |
| Dense matching | [RoMa](https://arxiv.org/abs/2305.15404) | Coarse multimodality and fine localization already addressed; geographic calibration remains separate. |
| 3D-grounded matching | [MASt3R](https://arxiv.org/abs/2406.09756) | Geometric context plus local descriptors/reciprocal matching; not an external geographic datum. |
| Feed-forward geometry | [VGGT](https://arxiv.org/abs/2503.11651) | Cameras, pointmaps, depth and tracks; manuscript discloses extreme-rotation/input-model limitations. |
| Hierarchical localization | [HF-Net](https://arxiv.org/abs/1812.03506) | Global/local sharing and retrieval-to-PnP predate the recent UAV literature. |
| Adaptive sparse matching | [LightGlue](https://arxiv.org/abs/2306.13643) | Difficulty-adaptive local matching; match confidence is not calibrated geographic pose risk. |
| Non-centered retrieval | [VIGOR](https://arxiv.org/abs/2011.12172) | Multiple covering references and within-image offset calibration; one-to-one assumptions were challenged years ago. |
| Selective pose | [RIC-Loc](https://arxiv.org/abs/2607.04722) | Consensus, covariance/dispersion scores and risk–coverage; correlated hypotheses and calibration limits are explicitly acknowledged. |
| Metric orthographic localization | [OrthoLoC](https://arxiv.org/abs/2509.18350) | DSM-backed UAV 6-DoF localization and AdHoP; paired references do not test large-area retrieval. |
| Noisy correspondence | [PAUL](https://arxiv.org/abs/2508.20066) | Uncertainty-aware partitioning/co-augmentation for misaligned training pairs; distinct from test-time pose abstention. |

### Decisive recent evidence

1. **RIM is much closer than generic retrieval baselines.** Its full text describes shared retrieval/local tokens (p.6), geographic-map requirements and excluded construction frames (p.27), and the absence of a calibrated reject option. Appendix E distinguishes finite solver return from correct pose (p.51). However, p.28 already proposes fusing retrieval margins, correspondence support, geometric statistics and temporal consistency. Merely implementing that list is not a new scientific contribution.
2. **RIC-Loc already does selective localization.** Its limitations state that hypotheses share a VGGT pass yet are aggregated under an independence approximation (p.15); p.20 explicitly treats covariance as a ranking score rather than a calibrated posterior. It also suggests geometry-aware reference selection. **The audit correction is important:** p.9 already reports full-set treatment of ineligible queries, and p.8 already adds common-mode scale and residual-consistency inflation. Neither all-query evaluation nor generic covariance inflation differentiates O1.
3. **SkyReg already does dense UAV georegistration.** [Full-text §5.1](https://arxiv.org/html/2608.28891v1) distinguishes pixelwise error from image-level median GPS. Its per-image dense statistic is a median, which does not certify every corner. Section 5.2 reports homography difficulties with urban relief/parallax. **Section 3.4 also predicts per-pixel confidence and trains with confidence-weighted regression**: this is a required O2 baseline, not a missing capability.
4. **OrthoLoC separates matching from search.** Its limitations (p.10) identify covisibility, raster scalability, camera-calibration ambiguity and inability to recover completely corrupted matches. Success on paired references cannot be presented as end-to-end cold-start localization. Pages 4–5 also show that same-domain rasters and query truth share a reconstruction; external DOP/DSM transfer is a separate test. Released geometric elements use a privacy-preserving local frame, so local metric accuracy is not automatically global GPS accuracy.

**Version/access warning:** SkyReg's current abstract title is *Pixel-wise Geo-registration of Drone and Satellite Images*; the retrieved v1 HTML manuscript is titled *Pixel-wise Geo-registration of Drone Images*. The distinction is retained rather than silently normalized. The large PDF was discarded after 40,000,001 bytes; the recovered HTML is the source of the full-text claims.

## Ten research tensions

These are supported task/assumption mismatches or open empirical questions, **not manufactured head-to-head contradictions**.

| ID | Tension | Evidence anchor | What remains unproved |
|---|---|---|---|
| T01 | Retrieval success versus metric correctness | University-1652 p.4; DenseUAV p.2; RIM p.51 | Failure frequency on the user's actual subset. |
| T02 | Positive overlap versus unique correspondence | VIGOR p.2; Game4Loc pp.2,4; SkyReg §5.1 | Benefit of retaining multiple geographic hypotheses. |
| T03 | Oblique identity versus observable map surface | OffNadirLoc pp.3,6; OrthoLoC p.10; SkyReg §5.2 | A controlled separation of recognition and observability. |
| T04 | Retrieval invariance versus local precision | InfoGeo pp.3,21; RoMa Fig.2; MASt3R p.2 | A causal loss of precision in any specific learned representation. |
| T05 | Useful homographies versus nonplanar relief | Homography §3.1; OrthoLoC pp.2,10; SkyReg §5.2 | Whether cheap sensitivity beats residual-based diagnostics. |
| T06 | Predicted geometry versus geographic anchoring | VGGT abstract; RIC-Loc p.4; OrthoLoC pp.4,7 | Effects of datum, elevation and camera errors in deployment. |
| T07 | Closed-gallery success versus missing-map rejection | RIM pp.27–28; Game4Loc paired protocol | Performance on natural temporal/map absence. |
| T08 | Failure ranking versus calibrated transferred risk | RIC-Loc pp.15,20; PAUL p.2; LightGlue protocol | Risk control under real geographic shift. |
| T09 | Candidate count versus independent evidence | RIC-Loc p.15; RoMa Fig.2; MASt3R p.2 | Whether footprint overlap is a useful dependence proxy. |
| T10 | Established integration versus new contribution | HF-Net pp.2–3; UnifyGeo pp.2,6; RIM pp.6,28 | A distinction beyond familiar system composition. |

## Ranked candidate board

Every candidate has at least four explicit closest-prior-art comparisons and a complete experiment object in `literature.json`. Ranking is subjective triage, **not an acceptance probability**.

| Rank | Direction | Cheapest test | Principal threat | Current decision |
|---|---|---|---|---|
| 1 | **O1: Dependence-aware abstention** | Two-day CPU analysis of pose hypotheses, spatial overlap and failure ranking | RIC-Loc already exposes dependence; RIM already proposes confidence fusion | Audit first; potentially useful diagnostic, novelty uncertain |
| 2 | **O2: Geometry-sensitivity anchor gating** | Up to three days perturbing DSM heights and measuring geodetic sensitivity | Classical photogrammetric error propagation, SkyReg and OrthoLoC | Conditional on actual dense truth and a distinct mechanism |
| 3 | **O3: Fixed-budget geometric-support selection** | Two-day comparison of top-K, geographic NMS and support selection | RIC-Loc already suggests geometric reference selection; classical active localization | Hold; likely an engineering baseline rather than a paper |

### O1 — Dependence-aware abstention

**Thesis to test:** overlapping map candidates can agree on the wrong structure, so multiple similar hypotheses should not automatically increase confidence.

Use at most 400 queries, five candidates each, with non-overlapping geographic calibration/test partitions. Compare footprint-cluster support and leave-one-cluster-out pose displacement against retrieval margin, inlier statistics, spatial support, residual, dispersion, and a fitted combination of **all** those conventional signals. Evaluate all attempted queries, not just covariance-eligible or successfully solved examples.

Primary endpoints: risk–coverage/AURC, large-error rate at matched coverage, accepted-query p95 error and no-pose fraction. A prospective go rule is at least 10% relative AURC improvement over full conventional fusion while retaining at least 50% coverage; clustered uncertainty must not contradict the improvement. These numbers are screening criteria, not results.

**Kill it** if the proxy is redundant, gains depend only on artificial removal of correct tiles, or useful coverage collapses. Geography-aware splitting does not create distribution-free protection against arbitrary shift.

**Closest work:** RIC-Loc, RIM, PAUL and RoMa. The proposed difference is geographic evidence dependence, not consensus or abstention themselves. An actual contribution would require real cross-geography evidence and a mechanism beyond relabeling correlated uncertainty.

### O2 — Geometry-sensitivity gating

**Thesis to test:** a small reprojection residual can coexist with a large geographic error when oblique rays intersect uncertain-height surfaces.

Use up to 200 OrthoLoC queries and 100 anchors per query. Keep observed matches fixed; compare homography and DSM-lifted PnP under symmetric height perturbations of 1/3/5 m. Rank anchors by geodetic displacement sensitivity and model disagreement. Ground-truth camera/depth information is for evaluation and stratification only—not an input to the score.

Compare residual/confidence, homography, PnP, AdHoP where usable, **analytic ray/first-order covariance propagation**, and **existing SkyReg/MASt3R point confidence**. Report per-anchor p95 error **and coverage**. Use local metric errors for anonymized OrthoLoC coordinates; report global geodetic errors only when the transform is verified. A prospective screen requires 20% lower p95 error at 50% or greater coverage beyond the strongest of these baselines, with held-out geography, relief strata and separately reported external-DSM transfer.

**Kill it** if simple off-nadir/relief covariates explain the gain, ground truth is needed to compute the score, or dense truth cannot be obtained. Do not invent facade/visibility labels. Existing SkyReg data are a possible transfer test, subject to access and annotation verification.

**Closest work:** SkyReg, OrthoLoC, correlation-aware homography and MASt3R. The largest unsearched threat is classical photogrammetric uncertainty propagation. A negative result would still clarify whether matching or map geometry dominates the user's precision problem.

### O3 — Fixed-budget support selection

**Thesis to test:** at a fixed expensive-matching budget, a diverse supported reference set can outperform several near-duplicate high-score candidates.

For at most 300 queries, select two or five references from a top-20 pool. Compare top-K, random selection, geographic nonmaximum suppression, cheap inlier ranking and a support-based greedy selector. Charge every low-resolution probe and every expensive match to the ledger. Do not claim a selection benefit after spending more matching compute than the baseline.

Require at least five percentage points of metric-success improvement over top-K **and** improvement beyond simple geographic NMS before further investment. Use a genuine gallery and non-oracle retrieval, not paired references selected by truth.

**Kill it** if NMS suffices, probe overhead removes the benefit, or gains only appear in oracle-paired evaluation.

**Closest work:** RIC-Loc, RIM, UnifyGeo and HF-Net. RIC-Loc already proposes the broad direction. **HF-Net p.3 already clusters candidate frames by shared 3D covisibility**, making footprint grouping an especially weak novelty claim; add covisibility grouping as a baseline where supported. There is currently no basis for a top-tier paper recommendation.

### Compute and authorization

These plans assume public data and compatible existing outputs. CPU ORB/RANSAC/PnP can cheaply screen a mechanism if learned outputs are unavailable, but **cannot be mislabeled as a RoMa/RIM/MASt3R replication**. Individual screens budget roughly 8–12 CPU-hours and 16 GB RAM. Learned feature extraction, dataset licensing, model access and any GPU budget require a separate preflight and approval.

No experiment has run. No model/API cost, result, speedup or performance improvement is fabricated.

## The five supplied methodological foundations

Actual titles were verified rather than copied from informal labels:

1. [**Human-LLM Compound System for Scientific Ideation through Facet Recombination and Novelty Evaluation**](https://arxiv.org/abs/2409.14634), Scideator. Keep purpose, mechanism and evaluation separate; the user remains responsible for pursuing an idea. Creativity-support studies and top-10 novelty retrieval do not establish scientific truth.
2. [**Can LLMs Generate Novel Research Ideas? A Large-Scale Human Study with 100+ NLP Researchers**](https://arxiv.org/abs/2409.04109). Human judgment, feasibility and model self-ranking differ. Its limits on diversity/self-evaluation argue for separate criticism and real tests, not self-certified novelty.
3. [**Literature-Grounded Novelty Assessment of Scientific Ideas**](https://arxiv.org/abs/2506.22026). Adopt retrieve/filter/facet-rerank/source-grounded comparison. Its §8 acknowledges restricted retrieved context and shared annotators between exemplars and test labels. Benchmark agreement is not exhaustive novelty validation.
4. [**The AI Scientist-v2: Workshop-Level Automated Scientific Discovery via Agentic Tree Search**](https://arxiv.org/abs/2504.08066). Persistent experiment trees, negative results and budgeted execution are useful engineering patterns. Manuscript inaccuracies and limited consistency preclude using this report to predict publication outcomes.
5. [**How we built our multi-agent research system**](https://www.anthropic.com/research/multi-agent-research-system). Use bounded ownership, checkpoints, retries, tracing and source attribution. It is a first-party engineering account with internal evaluations, not independent evidence that agents reliably discover scientific truths.

## Post-persistence independent-audit corrections

The independent auditor identified four substantive omissions in the initial pilot: RIC-Loc's full-set evaluation and existing covariance corrections; SkyReg's predicted pixel confidence; OrthoLoC's shared reconstruction/local-coordinate constraints; and HF-Net's explicit covisibility clustering. All four were verified directly in cached primary text and incorporated above and in `literature.json` under `audit_updates`.

This narrows rather than strengthens the novelty claims. **O1 remains only narrowly unresolved; O2 needs stronger classical and learned-confidence controls; O3 remains held.** No new source requests or experiments were required. The initial blind generation and this subsequent correction phase are explicitly distinct.

## Cost, uncertainty and next decision

- **56 HTTP requests**, including the initial partial connectivity probe.
- **267,027,628 response bytes read**, including the discarded oversized PDF prefix.
- Instrumented request durations total **80.855 seconds**; overlapping requests mean this is not wall time.
- The JSON records a **619-second research/validation snapshot**, excluding subsequent report finalization.
- **GPU hours: 0. Paid APIs: none.** API/CLI dollar cost is null because billing was not available.

Important unfinished work: publisher/DOI validation; exhaustive citation expansion; code/data licensing and availability; current-version reconciliation; full dataset/appendix audits; classical uncertainty and active-localization prior art. No claims are based on absent search results. The user's preliminary DenseUAV experience remains motivation, not a verified gap.

**Recommended checkpoint:** adjudicate the independently raised prior-art objections before any experiment authorization. Prefer a truthful **ITERATE / no surviving novel hypothesis** result over manufacturing a promising research direction. If O1 remains worth testing, authorize only its bounded falsification after data preflight—not a new training campaign.
