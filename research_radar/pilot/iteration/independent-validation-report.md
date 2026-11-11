# Independent final ITERATE validation

**Verdict: ITERATE — not GO for research-novelty discrimination or a paper-worthy discovery.**  
**Campaign:** `campaign-0ea39fd68d9c`  
**Operating URL:** <http://127.0.0.1:8776/?campaign=campaign-0ea39fd68d9c>  
The campaign ID is from `campaign.json`; the local origin and `?campaign=` routing are documented in the retained prior report/application. No HTTP availability check was made in this audit.

## Bottom line

Both policies correctly classify **5/5 overlap and 5/5 distinct controls**, with no false labels or abstentions. This passes the frozen **assigned-source** diagnostic, not broad historical novelty discrimination. It provides **no measured classification improvement**: both are at the ceiling.

The blind reviewer reports scientific survival of **1/3 baseline versus 2/3 revised** candidates. That comparison is unreliable: a new candidate was treated as prior art for another candidate, and underspecified contributions were promoted despite the review's explicit specification requirement. Applying that same requirement independently gives **0/3 versus 0/3 eligible as written**, **0/3 versus 0/3 established distinct contributions**, and **0/3 versus 0/3 experiment-ready**. This does **not** establish that all six are unoriginal, worthless, or incapable of repair. Several retain worthwhile questions.

There is real progress in source preservation and prerequisite inspection. It does not substitute for candidate evidence. The cheapest next step is a **manual operational-definition/equivalence screen of the shared geometric-disagreement idea**, not another generation run, literature expansion, or GPU experiment.

## Independence, frozen evidence and scope

The earlier `benchmark-ground-truth-audit.json` was completed without reading outcomes. Its ten labels remain unchanged. This final audit read both benchmark responses, scores, both generations, the blind review and unblinding key, diagnosis, prerequisite, preservation, software, cost and annotation-preflight receipts, and relevant retained primary methods.

The final auditor is **not blind to policy labels** and was explicitly alerted to suspected reviewer errors. I independently checked those objections against candidate text and primary sources; I did not treat the suggestions or raw votes as ground truth. The before-outcome ground-truth audit provides a separate protection against benchmark relabeling, not full independence from shared evidence or model training.

The final `comparison.json` agrees with the raw counts below and explicitly withholds validated-survivor status. Its distinct-and-experiment-ready count is **0→0**. Final evidence inspection includes the post-clarification software receipt dated 2026-11-10T07:58:08Z; the measured scientific outputs remain unchanged.

Verified locally:

- Input/key hashes still match `benchmark-freeze.json`; all four measured prompts match `prompt-freeze.json`; the measured review prompt matches `review-freeze.json`.
- Both benchmark prompt JSON payloads equal `benchmark-input.json`, without expected labels or later-target fields.
- Both generation prompts contain identical JSON evidence/prerequisite payloads, hash `bc2fd4f622e79eef4370b931434c1cdff97d4842f314443f4a2ea3ef51866c19`.
- The review payload removes policy and original-index labels. Candidate wording can still reveal stylistic clues; this is label blinding, not guaranteed condition concealment.
- The five campaign jobs and five direct CLI cost events exist in the local database, inspected read-only. Receipts identify **Claude Sonnet 5.5 for all five**: the generator and judge are separate calls, not independent model families.

No new network requests, agents, model runs, training, candidate experiments or software suites were executed by this auditor. Local hashes, archive quotation integrity and recorded-result arithmetic were checked. Raw outputs were not rewritten.

The parent reports a **post-measurement production-prompt clarification** that another generated proposal is not published prior art. That is a reasonable prospective correction, but was **not rerun or demonstrated effective**. It is not credited to the frozen results.

## 1. Balanced benchmark: label success, bounded meaning

The frozen minimum is 0.8 recall **in each class**. Both achieve 1.0; coverage is 1.0. Positive means “distinct within the assigned source,” not historically novel. There are five correlated source pairs, not ten independent validation settings.

| Case | Expected / both outputs | Independent semantic finding |
|---|---|---|
| C01 | overlap | DenseUAV already supplies dense real-UAV sampling, siamese transformer retrieval, neighbor-search and SDM. Both responses appropriately flag acquisition detail missing from excerpts. |
| C02 | overlap | LPN's square rings, pooling and part-wise classification match. Rotation robustness is not exact rotation invariance. |
| C03 | distinct | Token confidence/matchability gates inside a pairwise transformer differ from HF-Net retrieval, covisibility and distilled features. HF-Net itself already stops after finding a valid pose; “early stop” alone is not the distinction. |
| C04 | distinct | Geographic coverage and within-tile offset regression distinguish the proposal. **Baseline's claim that University-1652 uses one-to-one retrieval is wrong**: the source already has multiple true-matched viewpoints and AP. Revised uses the more defensible identity-versus-coordinate distinction. Label remains correct. |
| C05 | overlap | The full University-1652 source supports the shared identity-training baseline. Baseline asserts training detail absent from its packet; revised acknowledges that gap. This is not a completely source-supported rationale from the evaluator's limited view. |
| C06 | overlap | Single-network distillation, retrieval, covisibility grouping and local PnP/RANSAC reproduce HF-Net. |
| C07 | distinct | Geography-initialized, embedding-refreshed negative sampling differs from LPN's representation partition. Generic contrastive training/shared weights alone are not new. |
| C08 | distinct | Dense per-pixel pointmap georegistration differs from DenseUAV image-location retrieval. “Every visible pixel” must not imply guaranteed success; the target evaluates valid pixels. |
| C09 | overlap | RoMa v1 contains frozen coarse features, classification anchors, decoupled refinement and robust loss. Both responses acknowledge missing anchor detail; the limited packet does not independently substantiate every mechanism detail. |
| C10 | distinct | Joint pointmap/descriptor learning differs from RoMa's 2D warp formulation. Revised's “combined with” wording should not be read as a mandatory fused 3D-plus-descriptor matching score. |

Thus **20/20 labels** are supportable, but not **20 flawless grounded explanations**. No new semantic score or threshold is invented after the fact. The specific C04/C05 improvements are qualitative observations, not a statistically supported policy effect.

### Why this does not meet the broader objective

Distinctness was tested against one assigned older source, often a clearly different module or output type. Several overlap cases closely paraphrase abstracts; C07/C10 explicitly state their intended contrast. Pairing and recognizable paper signatures offer shortcuts. The benchmark does not test discrimination against the nearest competing mechanisms, unknown prior art, generic reformulations, valuable new questions, or proposed opportunities' real evidence.

All five supplied source documents are genuinely retained **v1 texts before their cutoffs**, with matching hashes. No later-target material appears in the measured evaluator payloads. That controls document timing, **not pretrained-model hindsight**. Later publication is not proof of novelty. VIGOR's retained target is **v2, 2021-03-22**, despite the key's 2020-11-24 date; Sample4Geo is **v2, 2023-08-29**, not the key's earlier date. Both remain post-cutoff targets, but their v1 mechanism attribution is unverified. SkyReg's retained title is *Pixel-wise Geo-registration of Drone Images*; its flattened HTML excerpts should not be cited as verified PDF pages. These pre-outcome qualifications remain in force.

## 2. Candidate adjudication: separate four questions

1. **Published overlap:** does a retained primary source implement the submitted contribution?
2. **Within-batch redundancy:** does another generated idea repeat it? This is not prior art.
3. **Scientific eligibility:** is the question significant and the contribution precise, distinguishable and affordably falsifiable, as required by the frozen review instructions?
4. **Readiness/value:** are prerequisites verified, and is there evidence supporting a useful paper? Neither follows from eligibility.

“Uncertain” novelty does not automatically fail scientific eligibility. Here, failures are specific definition, equivalence, baseline or design problems—not absence of results, inaccessible software, or lack of a global novelty proof.

### R01 — revised G2: geometric disagreement

**Raw:** uncertain novelty; survives; not ready.  
**Audited:** uncertain novelty; **revise, not eligible as written**; not ready.

The question—detecting planar-model failure under relief/parallax—is meaningful. A disagreement diagnostic is not shown to be an implemented equivalent in OrthoLoC or SkyReg. However, the candidate inaccurately treats “both existing fits” as directly comparable pose outputs:

- **OrthoLoC §4.2–4.3 / Fig. 4**, `research_radar/sources/2509.18350.txt`, lines **489–534, 565–566**: DSM-lifted correspondences produce a pose. AdHoP estimates a **2D homography to warp the orthophoto**, then **rematches**, maps correspondences back, and performs DSM-based pose estimation again. It accepts refinement when reprojection error decreases.
- Consequently, comparing the original and refined pipeline poses does **not** isolate two scene models on identical matches. A homography is not already the alternative 6-DoF pose assumed by the proposal.

The submission does not define homography-to-pose conversion, common observable, units/gauge, per-anchor support or aggregation. A meaningful alternative could compare projected coordinates on held-out anchors, but supplying that now would repair, not validate, the frozen candidate. Its numeric success gate only requires beating residual/count baselines, despite naming analytic covariance and SkyReg confidence as important comparators; it therefore need not demonstrate the advertised superiority to the strongest baseline.

Additional counterexamples: coherent wrong correspondences can make both models agree on a wrong location; legitimate relief can cause disagreement despite a correct DSM-PnP estimate. Disagreement measures model discrepancy, not automatically pose error. These do not prove an empirical ranker cannot help; they show why the target and controls must be specified.

### R03 — baseline G2: the same geometric-disagreement family

**Raw:** overlap, rejected as a duplicate of R01.  
**Audited:** **uncertain published novelty**, within-batch duplicate of R01; revise, not eligible as written; not ready.

R01 is a newly generated proposal, not published prior art. The review explicitly admits that OrthoLoC does not use this disagreement score. Therefore its published-overlap classification is unsupported. Evaluate the shared mechanism once and apply the same substantive standard to both policies; deduplicate pooled opportunities separately.

R03 has R01's common-observable problem, weaker comparator commitments and a success criterion against inlier ratio rather than the strongest justified comparator. Its “at least 20% covisibility, as the source requires” is also too strong: OrthoLoC Appendix C.7, lines **1978–2051**, reports a performance cliff below 20%, not a universal eligibility requirement. Ground-truth covisibility filtering could make evaluation oracle-conditioned; report all-query performance and define any permissible observable filter.

This correction **does not promote R03** merely to offset the reviewer's asymmetry. Both versions require the same specification repair.

### R04 — revised G1: overlap-discounted agreement under map absence

**Raw:** uncertain; survives despite “statistic is under-specified”; not ready.  
**Audited:** uncertain; **revise, not eligible as written**; not ready.

Map-absence rejection is important. RIC-Loc already implements covariance/dispersion rejection and common-mode inflation, but neither that source nor OCI establishes an exact footprint-discounted map-absence detector. OCI's unbiased linear fusion assumptions are not a model for biased wrong-building aliases.

Nevertheless, no exact score, overlap grouping, empty-set behavior or normalization is supplied. Removing all references overlapping the top hypothesis may remove every useful candidate; different reasonable completions yield different algorithms. The review's survival vote contradicts its own finding and frozen precision requirement.

The stress design is also invalid as a general “no valid reference” label: **removing one true tile does not remove all geographically covering positives**. The assigned-source VIGOR evidence already illustrates multiple covering references. Removal may merely perturb the best match. Absent/present AUROC can reflect that manipulation rather than wrong-pose rejection; define geometric validity, all valid references, paired-query dependence and query/scene-grouped uncertainty before any such claim. The frozen wording does not do this.

### R05 — baseline G1: leave-one-footprint-out pose shift

**Raw:** uncertain; survives despite a generic-jackknife objection; not ready.  
**Audited:** uncertain; **revise, not eligible as written**; not ready.

The incremental logistic comparison and scene-grouped validation are useful design elements. The reviewer is not entitled to claim that a retained source implements this exact rule merely by invoking “standard jackknife.” But the rule is not operationally precise and may algebraically duplicate its proposed dispersion baseline.

For the admissible simple implementation with mean center `μ` and `K` reference centers, deleting one center gives:

`μ[-i] − μ = (μ − x[i]) / (K − 1)`.

The RMS leave-one-out shift is therefore exactly **RMS dispersion divided by K−1**. This is an analytical counterexample to assuming an automatically new signal, not an executed experiment or a proof for every robust/cluster-weighted estimator. The candidate must define footprint clusters, estimator recomputation and the scalar statistic, then identify what breaks this equivalence.

If every retained reference supports the same wrong building, leave-one-out shift can be zero despite large true error. Geographic overlap is also only a proxy for error dependence. “Common wrong alias” is not, by itself, a reason the statistic should become large. The proposed natural/stress tests have no results, and dropping a single true entry again does not guarantee map absence.

Strongest retained comparator: **RIC-Loc §3.4**, `2607.04722.txt`, lines **368–414**, already combines covariance with residual inflation, a common-mode scale term and dispersion using held-out normalization. Comparing only to a loose “RIC-Loc-style” dispersion proxy cannot establish incremental value over the complete method.

### R02 — baseline G3: budgeted footprint-complementarity selection

**Raw:** overlap, rejected.  
**Audited:** uncertain exact-method novelty with **established broad-principle overlap**; do not advance as written; not ready.

HF-Net implements covisibility grouping; RIC-Loc's geometry-aware selection is **future work**; OASIS implements budgeted information-based **sensor-placement** selection. They undermine broad claims that geometry/diversity or fixed-budget selection is new. They do not prove an exact equivalence to an unspecified satellite-reference selector. The reviewer's named MMR analogy is a plausible threat, not a newly verified primary citation in this bounded audit.

No marginal utility, redundancy penalty, uncertain-association treatment or pre-match cost accounting is defined. Footprint geometry may be unavailable from a bare gallery, and top-20 cached matcher results can hide work outside the proposed budget. Set Jaccard below 0.8 proves different selections on those inputs, not a different scientific contribution; conversely Jaccard above 0.9 does not prove universal algorithmic equivalence. There is no complete non-oracle gallery or matched-budget validation.

### R06 — revised G3: retrieval invariance versus local precision

**Raw:** uncertain, rejected; not ready.  
**Audited:** uncertain; retain only a **descriptive question requiring redesign**, not the submitted causal claim; not ready.

This changes the question beyond another confidence score. But comparing different frozen retrieval and matcher networks confounds objective, architecture, input resolution, feature stride, data and supervision. Altitude additionally changes ground sampling distance, field of view and content. “Equivariant comparator” is not a proved property of RoMa, whose coarse/refine feature specialization is already an important competing explanation.

The retained **RIM §2.1**, `2607.20116.txt`, lines **212–233**, freezes an adapted retrieval backbone and trains a local decoder on its token field. This contradicts a blanket premise that retrieval learning destroys usable locality, but does not prove raw frozen tokens solve matching or rule out a more specific loss. **InfoGeo Appendix C**, `2605.07099.txt`, lines **1240–1252, 1309–1318**, discusses noisy object relations and reduced gains at altitude, not a controlled demonstration of lost spatial equivariance. Its later failure analysis even shows some cases improving at higher altitude.

The candidate does not establish true within-tile correspondences or define a comparable feature-level measurement. The blind review's suggested matched-backbone **training** is outside the authorized no-training scope and is **not** the next action. Reframe any future frozen-feature study as descriptive, or defer the causal question.

## 3. Raw versus audited before/after

“Before” here means the **frozen baseline-policy arm of this iteration**, not the older three-candidate pilot. The older pilot's claims and incomplete lineage cannot be retrospectively turned into this experiment's baseline.

| Measure | Baseline raw | Revised raw | Baseline audited | Revised audited |
|---|---:|---:|---:|---:|
| Overlap controls correct | 5/5 | 5/5 | 5/5 | 5/5 |
| Distinct controls correct | 5/5 | 5/5 | 5/5 | 5/5 |
| False labels / abstentions | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Candidate novelty: distinct | 0 | 0 | 0 | 0 |
| Candidate novelty: overlap | 2 | 0 | 0 exact equivalences established | 0 exact equivalences established |
| Candidate novelty: uncertain | 1 | 3 | 3 | 3 |
| Scientific eligibility as written | 1/3 | 2/3 | **0/3** | **0/3** |
| Experiment ready | 0/3 | 0/3 | 0/3 | 0/3 |
| Empirically supported valuable paper | 0 | 0 | 0 | 0 |
| Primary coarse mechanism families | 3 | 3 | 2 | 3 |

The audited diversity count uses the review's five-category vocabulary but assigns R02's **post-retrieval selector** to `posthoc-score-or-selection`, not `acquisition-or-system-design`: it does not change sensor acquisition. R01/R03 remain `geometry-or-identifiability`; R04/R05 are posthoc scoring; R06 is representation analysis. This creates a descriptive 2→3 increase. Keeping the reviewer's R02 assignment leaves 3→3: **the diversity conclusion is taxonomy-sensitive**, not calibrated or causal.

At the specific-operation level each arm has three proposed operations. Two related themes persist across policies (dependence scoring; geometric disagreement); reference selection is replaced by representation analysis. Across six candidates there are five non-identical descriptions after merging the exact R01/R03 duplicate, and four broader shared themes. All baseline operations and two revised operations still consume existing pipeline outputs for scoring/selection; changing question labels alone is not escape from that concentration.

No worthwhile paper is demonstrated. An eligible hypothesis would still need evidence of importance and incremental value; these candidates have neither measurements nor a validated non-equivalent operational quantity. Conversely, no experiment is necessary merely to propose a valuable question: the zero eligibility count here rests on the frozen proposals' specific defects.

## 4. Prerequisites, annotation sanity and preservation

### Genuine prerequisite progress

`prerequisites.json` records actual same-domain/cross-domain OrthoLoC `.npz` samples with image, pointmap, DSM, scale, intrinsics/extrinsics and other geometry arrays; numerical calibration entries are finite. Both RIM checkpoint byte hashes match the released manifest. The held-out index lists **1,415 files across L08/L50/L51**, not 1,415 independently validated locations or downloaded test samples.

Remaining gaps: NumPy/environment and full baseline runtime, cached hypotheses/matches, complete external checkpoints, non-oracle galleries, independently certified truth/global transform, and licensing. OrthoLoC's retained license is CC BY-NC-SA 4.0; RIM states GPL-3.0-only with separate third-party terms; RIC-Loc permission and UAV-VisLoc data licensing remain unresolved. “No license found in the inspected tree” is narrower than proving no license exists anywhere.

The geometry receipt reports the predeclared nominal-pose gate: **≥30/48 valid fixed-grid samples, median ≤2 px, p95 ≤5 px**:

| Sample | Nominal valid | Nominal median / p95 px | Refined median / p95 px, separate |
|---|---:|---:|---:|
| cross-domain | 48/48 | 0.000174 / 0.000278 | 0.086966 / 0.110443 |
| same-domain | 44/48 | 0.000108 / 0.000207 | 0.160292 / 0.284797 |

Both pass the nominal gate; four invalid/nonpositive-depth same-domain points remain counted. No best-pose selection was used. This is **within-source pointmap/camera consistency**, potentially expected from how annotations were constructed—not independent truth, DSM correctness, matcher execution, candidate evidence or geographic generalization. I inspected the receipt and matching archived input hashes; I did not rerun this calculation. No candidate becomes ready because of it.

### Preservation

I independently traversed the content-addressed manifests and bytes for **75 existing quoted claims plus 29 benchmark source/target passages**. All **104** exact spans, raw/text links and referenced content hashes checked successfully, covering **83 distinct archived blobs**. This verifies preserved evidence, not scientific entailment or historical completeness.

**Twenty historical missing-response lineage records remain explicit.** Later copies do not recreate original blind snapshots, and extraction provenance is an attestation, not a fresh PDF re-extraction test. The current evidence is materially better preserved; the past loss remains a limitation.

### Software

The final retained execution log independently matches the post-clarification software receipt: **129 executions, all pass, zero skipped; 10 browser and 14 archive tests**. Some inherited tests repeat, and browser scientific data are synthetic fixtures. These tests establish software behavior within their coverage, not scientific novelty, semantic reviewer correctness, production-model independence or successful candidate experiments. No full-suite rerun was performed by this auditor.

## 5. Costs and bounds

The frozen caps are 25 public requests, 120,000,000 downloaded bytes and five direct model calls. Reported usage is **22 requests; 112,086,336 bytes; five direct CLI calls**. The five stored CLI cost events independently reconcile to:

- **220,622 input / 16,266 output tokens**;
- **54,992,020,000 raw nanoAIU**;
- **136.3048567 seconds** summed CLI elapsed work (ledger rounds to 136.3);
- zero recorded GPU hours and paid external API calls.

Public-request elapsed time is 42.485 seconds. Annotation sanity took about 0.104 seconds. These are different scopes, not a complete campaign wall-clock measurement. Input accounting includes cached token categories; nested provider/agent metrics must not be added again.

**USD remains unknown**, not zero. Coordinator/delegated-agent usage and billing are not included in the five direct-call receipts. No verified conversion from nanoAIU to dollars exists here. The ledger accurately acknowledges this incompleteness.

## 6. Failure causes and corrections

- **Established broad overlap, not universal non-novelty:** confidence/dispersion, uncertainty propagation and budgeted geometric selection already exist. Exact candidate equivalence often remains unresolved.
- **Search-space concentration:** repeated posthoc diagnostics and selectors are visible. One representation question broadens the revised set, but the single batch does not establish a causal diversity benefit.
- **Reviewer inconsistency:** R03 was rejected using another generated idea as prior art; R04 survived an explicitly missing statistic; R05's concrete equivalence threat was not resolved; R01's “two existing poses” premise was not checked.
- **Over-aggressiveness is not a general explanation:** correcting R03's and R02's unsupported overlap labels does not validate their methods. The same reviewer was permissive elsewhere.
- **Novelty/evidence/readiness conflation:** inaccessible data is not overlap, and missing results alone do not reject a hypothesis. Conversely, a numeric success gate is not a defined mechanism; downloadable weights are not a runnable baseline.
- **Baseline incompleteness:** several proposals name strong comparators without making success contingent on beating them. RIC-Loc-style proxies and weak residual-only wins do not establish incremental value over the strongest relevant mechanisms.

Apply the existing standard consistently. Preserve raw votes and display audited corrections separately. The production anti-duplicate clarification is prospective only. No thresholds were relaxed, no candidate was retroactively rewritten, and no extra generation or judge calls were made.

## 7. Cheapest decisive next step and stopping rule

**Stop this measured iteration at five calls.** If a further bounded step is authorized, spend **30–60 minutes of manual, no-network specification review** on **R01/R03 together**, using only retained OrthoLoC methods and the already acquired arrays:

1. Specify one common observable for homography and DSM-PnP—e.g. held-out image-plane projections—not an undefined difference between a 2D homography and a pose.
2. Freeze direction of the homography, coordinate gauge, calibration assumptions, anchor selection, units, aggregation, missing/degenerate behavior, and disjoint fitting/evaluation supports. Do not use query ground truth to construct the diagnostic.
3. Algebraically check whether the quantity merely reproduces inlier residual, relief/off-nadir sensitivity or the existing AdHoP reprojection acceptance test. Include coherent wrong-match and common-bias counterexamples.
4. Identify exact required cached matches and uncertainty inputs for the strongest comparator. Arrays and internally consistent pointmaps alone are not enough.

**Decisive stop:** if no non-equivalent observable and leakage-free target can be defined without new training, unavailable annotations or an oracle construction, reject the current diagnostic mechanism rather than generate more variants. If that screen succeeds, freeze a new, explicitly identified protocol before any subsequent empirical test; do not count the repaired proposal as a success of this run.

R05 additionally has a zero-compute mean/jackknife equivalence check already shown above. R04 needs a definition of *all* valid-reference absence before testing. R06's causal claim should remain deferred under the no-training constraint.

**Why ITERATE rather than NO-GO:** useful, separable questions and better preserved, inspectable inputs remain; the system is not shown incapable of improvement. **Why not GO:** broad novelty discrimination, consistent opportunity adjudication, a precise surviving contribution, experiment readiness and valuable-paper evidence have not been established. Confidence is high in this bounded verdict and the reviewer-category corrections, moderate in the strict as-written eligibility judgments, and low in any worldwide novelty or eventual-publication prediction.
