# Independent scientific adjudication — mechanism-first batch

## Decision

**ITERATE. Defensible as written: 0/3 frozen finalists. Experimentally supported: 0/3.**

This is not a claim that all twelve ideas are scientifically worthless, nor that established mathematics makes every application-level study unpublishable. M06 and M08 use established operators; M09's proposed nonlinear/inlier-switch distinction remains unresolved. Each has concrete specification or evaluation defects beyond the absence of performance measurements. All three retain possible diagnostic value. No repaired proposal receives retrospective credit.

The frozen shortlist is **M09, M08, M06**. The three fresh reviewers each returned **revise**, not validated survival. Their reasoning was checked rather than adopted by majority vote. No replacement finalists were selected.

## Audit scope and integrity

I read all twelve candidate definitions, the original screening and selection record, all three final reviews, four new external primary records and their preserved texts, the diagnostic protocol/results/implementation, prerequisites, citation checks and costs. No network request, model call, subagent, training or candidate-performance run was added.

Independent checks:

- All eight prompt hashes match their freezes; the generation-input/protocol hashes match `input-freeze.json`.
- `shortlist-selection.json` identifies the same three finalists and hashes the actual screening result. `shortlist-freeze.json` is the **screening prompt** freeze, not a selected-ID record. The filename collision is not counted as another model run.
- All ten acquisition response files match logged hashes; recorded bytes sum to **9,226,121**, with ten HTTP-200 responses.
- All four new PDFs re-extract byte-identically using default `pdftotext`; all seven final-review quotations occur in preserved primary text after whitespace normalization. The prior `independent-O2` PDF also re-extracts identically.
- Twenty linked manifests were hash/object/quote-slice checked in this stage: new primary claims and parents, corrected L1 and parents, and diagnostic protocol/implementation. Initial limitation manifests were checked separately in `grounding-audit.json`.
- Both diagnostic sample hashes match the retained packages.

Hashes and exact quotations establish traceability, not scientific truth or semantic equivalence. The diagnostic implementation was inspected; its persistent results are reported below, not misrepresented as independently rerun full experiments.

### Original grounding remains conditional

**L1:** OrthoLoC Figure 15 / section C.7 reports sharp errors below 20% overlap in a reference-cropping experiment. The original quotation was chart ticks; an append-only correction now preserves the actual supporting text. The correction arrived **after generation, before screening**; it cannot retroactively repair generator exposure. Spatial concentration and PnP underdetermination are authors' explanations, not separately isolated causes. The reported regime is neither a universal threshold nor evidence that OrthoLoC implements a 20%-rejection rule.

**L2:** Table 6's SP+LG values are real: DOP versus DOP+DSM matching error **2.5/2.5 px**, translation error **0.42/1.07 m**, and 1m–1° recall **71.3/42.3%**. Equal rounded aggregates do not imply identical pointwise matches or residual distributions. Table 3 gives potentially different test populations, **17/496 versus 17/423** in-place/out-place. Thus this contrast motivates, but does not identify, a DSM-only causal mechanism. Same-reconstruction poses/maps are not independent external-map error truth.

**L3:** OffNadirLoc Table 4 reports **62.29 → 72.64% R@1**, leaving a derived **27.36%** miss rate. Its viewpoints are Google Earth **renderings**. Correctness is patch retrieval under basemap/IoU criteria, not metric pose accuracy. An unknown residual cause is a legitimate subject for a falsifiable hypothesis—not a logical reason to reject one—but cannot be presented as an observed causal partition.

## Decisive external evidence

Paths below are relative to the repository. New texts/PDFs are in `data/research-radar/mechanism-first-sources/`. Line numbers count newline separators; PDF pages count file page order.

| Source ID | Verified passage | What it establishes—and does not |
|---|---|---|
| `mf-bundle` — Triggs et al., *Bundle Adjustment—A Modern Synthesis* | Section 3, `bundle.txt` line 329 onward, PDF p.8: “A MAP estimator would typically add cost terms giving certain structure or camera calibration parameters a bias towards their expected values.” Also inverse-Hessian dispersion. Section 6.1, line 1309 onward, PDF p.22, equations 16–18. | Prior-regularized estimation, local covariance and Schur/block-inverse identities are established. This is not a drone-performance result or direct proof of every DSM-sensitivity variant. |
| `mf-degeneracy` — Zhang et al., *On Degeneracy of Optimization-based State Estimation Problems* | Section III.B, `degeneracy.txt` line 492 onward, PDF p.4: “The solution is only updated in the well-conditioned directions … leaving xp in the degenerate directions unchanged.” | Established eigenvalue degeneracy detection and prediction retention. Hard remapping is related to, not universally identical to, finite-prior MAP shrinkage. |
| `mf-spectral` — *Spectral GS-SLAM*, retained 2026 preprint | Equation 8, `spectral.txt` line 418 onward, PDF p.4: “information injection with the prior into the degenerate subspace containing low information”. | Established directional prior injection in a different optimizer/application. Its gated prior is not literally M06's full-prior addition in every case. |
| `mf-metrology` — *Metrological Characterization of a Laser-Camera 3D Vision System…* | Section 2.3, `metrology.txt` lines 287 and 350 onward, PDF p.3: perturbed rotation/translation are used “to project the Laser points into the Image plane.” | Monte Carlo **pose-to-projection** propagation, not DSM perturbation followed by PnP-RANSAC re-solving. It cannot alone invalidate M09's nonlinear distinction. |
| `independent-O2` — *Uncertainty Quantification Framework for Aerial and UAV Photogrammetry through Error Propagation* | `research_radar/pilot/sources/candidate-independent-search/2507.13486.txt`, line 494, PDF p.6: “The uncertainty propagated from SfM captures the low-frequency, systematic errors that affect the entire model”. | Systematic reconstruction uncertainty and covariance propagation; not an exact publication of M09's external-DSM abstention mechanism. The inherited locator said PDF p.5; the quote is genuine but that locator is wrong. |

Primary PDF SHA-256:

```text
mf-bundle     3442e3563b909f9e61f0a5a201b9ff73f4789e0c30e9411116e93071382b44f2
mf-degeneracy 20856ea44857ae27c08af62b4832dfe808f75d6016b8ed9f55f8bb02aee222c7
mf-spectral   c165816f002572dc92f8674550ca94bf1e4d30de3cf27b7a910db08e6b68375a
mf-metrology  26fca8c177e2c19113d425a28e7d5ee7ebf6dd3efe46a9a720612cad40b0b11b
independent-O2 2825ed4de297f579c05fa8863dff4ff74b11a5de95deeff4162c03b015222ef5
```

Claim manifests for the decisive MAP and Schur passages are respectively `d4f56b117d2752c8da2af9428c0bac348cb2e77fd8a59d935f8dc14f077ad2b2` and `0e54357dd0dec7dcc36ce4e1017a30335f74cabfd725c5beae202aac47be31c2`. The other exact claim references remain in `external-prior-art.json`. These are actual publications, not generated internal ideas.

## Finalist adjudication

### M09 — finite DSM-mode perturbation and PnP sensitivity

**Disposition: revise; novelty unresolved beyond the standard linear limit.**

- **Novelty:** With fixed inliers and a differentiable solver, infinitesimal re-solving estimates the ordinary derivative of pose with respect to map parameters. However, none of the examined passages proves publication of this exact finite-DSM/PnP-RANSAC application. The finite-amplitude/nonlinear/inlier-switch claim must remain unresolved, not be converted to “novelty fail.” Conversely, failure to locate an exact paper is not a novelty pass.
- **Significance:** Height sensitivity could be informative, including a negative result showing analytic equivalence. But Table 6 does not establish that elevation errors cause its aggregate gap. A sensitivity score estimates response to chosen perturbations, not their probability or the real map error.
- **Technical completeness:** “Eight” modes are not specified: constant, two linear terms and the three quadratic monomials yield six. More importantly, the re-solve instruction does not specify rerunning RANSAC or its thresholds/seeds/inlier policy, although switching is the proposed separating mechanism. Re-solving on a fixed inlier set cannot establish a RANSAC-switch advantage. The title's “leave-one-out” wording also does not describe the actual one-mode-at-a-time addition.
- **Evidence:** D09 tests only the uniform offset, with analytically compensated pose. It is not a solve. No nonlinear/RANSAC advantage, Spearman improvement, AUROC or latency was measured. A constant world-z shift is compensated by camera translation for **any** view/relief, not only flat nadir scenes: `P'=P+h e_z`, `t'=t-R h e_z` leaves `RP+t` unchanged. The bias mode therefore supplies a unit camera-centre sensitivity floor; it does not necessarily dominate other modes or make the whole score constant.

The future separating test would need all modes and a deterministic switching policy, analytic derivatives on the **same** modes, a RANSAC-aware comparator/control, and scene-clustered uncertainty. That is a possible revision, not the frozen experiment already completed.

### M08 — focal-marginalized Fisher/Schur pose covariance

**Disposition: revise; established operator plus defective frozen test.**

- **Novelty:** For nonsingular information,
  `Cov_pose = (I_pp - I_pf I_ff^-1 I_fp)^-1 = (I^-1)_pp`.
  This is the `mf-bundle` block-inverse identity, not a new covariance operator. `mf-degeneracy` also establishes eigenvalue-based weak-direction detection. Application-specific diagnostic value remains an empirical question.
- **Significance:** The current baselines—overlap, count, hull area and hull×depth—omit the equivalent full joint covariance and the known-focal covariance ablation. Success against proxies cannot establish the value of the Schur construction itself. Partial correlation is not causal isolation.
- **Technical completeness:** The frozen success metric asks for **positive** partial Spearman ≥0.5 between `log(kappa)` and `log(translation error)`. Since kappa is minimum information, the stated hypothesis predicts the **opposite sign**. Neither an inverse nor a negation is specified. This must not be silently corrected and credited. “Scale rot rows” also fails to define a symmetric coordinate change; literally scaling rows alone can destroy symmetry. A six-dimensional pose eigenvector cannot directly name a focal component without a recovery rule.
- **Evidence:** D08 confirms the identity on 64 normalized SPD matrices, not rank-deficient pose geometry, unit scaling, matching or the proposed ≥2,000 trials. Gaussian synthetic correspondences can test a narrow numerical/model prediction, but cannot by themselves establish the real-image failure cause. They are not guaranteed to succeed.

A correctly specified covariance evaluation with focal ablation could remain useful. Wrong-match/DSM bias is a possible limitation, **not a measured dominant cause** in this record.

### M06 — prior-regularized directional observability

**Disposition: revise; established machinery and ambiguous update.**

- **Novelty:** MAP priors and inverse-Hessian dispersion are established in `mf-bundle`; directional prediction retention/information injection appear in `mf-degeneracy` and `mf-spectral`. This supports operator overlap, not an assertion that all three algorithms are exactly identical or every directional aerial evaluation is already published.
- **Significance:** Directional covariance can contain information absent from a trace. For example, `diag(9,1)` and `diag(5,5)` both have trace 10 but maximum directional standard deviations 3 and √5. Thus the review's blanket trace-monotonicity claim is false. A full matched covariance comparator is needed; predictive success/failure alone does not establish/refute concentration as the causal explanation.
- **Technical completeness:** With `r=y-J theta0`, a linear unit-noise prior-regularized step is
  `theta0 + H^-1[J^T r + P(theta_prior-theta0)]`.
  The candidate instead writes `theta_prior + H^-1 J^T r`, without defining the residual point, noise scaling or prior correction. D06 gives a counterexample under the conventional residual. A prior-centred residual in the tested linear/unit-noise case yields standard MAP—not a new update. The prior means, uncertainty rule and deployment availability also need specification; benchmark ground truth must not silently become the operational prior.
- **Evidence:** No AUROC, MAP translation-error comparison, matching run or bootstrap was performed. Repeated crops from two scenes are dependent observations. Confident biased matches are a possible counterexample, not a measured frequency.

The retained question is whether a fully specified directional diagnostic adds useful prediction beyond appropriately matched covariance baselines under independently specified priors.

## What actually ran

`research_radar/mechanism_diagnostics.py` was reviewed against `diagnostic-protocol.json`. It uses small pure-Python matrix calculations and reads two preserved numeric packages. Its full-candidate experiment count is explicitly **zero**.

| Case | Expected | Recorded observation | Valid conclusion |
|---|---|---|---|
| D06 | Current-residual formula differs from exact MAP; prior-residual formula agrees in the specified linear example. | Exact `[1.6,2.0]`; current-residual proposal `[0,0]`, max error **2.0**; prior-centred error **0**. | Conditional counterexample, not rejection of every M06 interpretation. |
| D08 | Schur inverse agrees with full inverse pose block within `1e-9`. | **64** SPD cases; max entry difference **3.3306690738754696e-16**. | Established identity confirmed; no research-performance gain. |
| D09 | Uniform-height compensation preserves projections within `1e-6` px and translation derivative within `1e-10`. | **96 attempted**, **92 valid**, **4 excluded** points; **552** controlled projections. Max difference **1.1368683772161603e-13 px**; derivative discrepancy **1.4210854715202004e-14**. | Coordinate identity confirmed. Exclusions are reported, not counted as candidate failures. No PnP/RANSAC/nonlinear advantage tested. |

Recorded runtime: **0.112040531 CPU seconds**, **0.11205963499378413 wall seconds**, zero GPU, no new dependencies and no matcher/model execution. These are the retained run's timings, not audit-overhead timings. All expected diagnostic outcomes occurred. None satisfies the candidates' performance gates.

Default-Python checks independently confirm `numpy`, `scipy`, `cv2`, and `torch` are absent. Two numeric sample packages and cameras are available. Missing modules do not prove installation impossible; unattempted benchmark/weight acquisition does not prove assets globally unavailable. No under-50ms PnP timing has been established.

## Screening and reviewer errors, separately counted

`independent-verdict.json` records **12 grouped issues**, not twelve independent statistical errors:

1. Unknown L3 cause was used to exclude falsifiable causal hypotheses rather than merely limit their evidentiary status.
2. Unverified datasets/weights were called unavailable without an acquisition result.
3. Screening rationale says all finalists novelty-fail although M09's novelty axis is unresolved.
4. Reported <20% degradation and focal/translation discussion were overpromoted to universal thresholds, implemented rejection or isolated causes.
5. M06 review incorrectly equates directional posterior standard deviation with covariance trace.
6. SIFT/matching availability and cheap solve throughput were asserted without a working default stack or timing.
7. M08 review declares bias dominant without a measured cause partition and overstates guaranteed synthetic success.
8. M09 framing/review infer more causality from aggregate Table 6 than its domain-cohort comparison supports.
9. Screening accepts M11's `N<=6 ⇒ P_perp=0`. With `J_pose` of size `2N×6`, even `N=4` leaves an eight-dimensional residual space that rank≤6 cannot span. Restricting perturbations through a DCT basis is not itself inconsistent with a per-point Jacobian.
10. M12's different diagnostic quantities are called a CSLS inconsistency without identifying the actual ranking problem. The query-neighborhood term omitted from its ranking score is constant across gallery choices for a fixed query; the undefined “A is large” condition and transductive setup are the real issues needing specification.
11. Both M08 reviews miss the frozen information/error correlation sign problem.
12. The inherited `independent-O2` quote has a wrong PDF-page locator, although the text is genuine.

Internal M01/M05/M09/M11 overlap and M02/M06/M07/M08 overlap may justify portfolio-diversity concerns. **Generated ideas are never external prior publications.** The current external decisions above rely on actual primary sources, not duplicate labels. No screening mistake is repaired by changing the shortlist after seeing the external search.

## Diversity and before/after

All twelve proposals were inspected. There are four per limitation:

- **L1:** M02 spatial-spread proxy; M06 prior-regularized spectrum; M07 scaled weak-direction statistic; M08 focal-marginal covariance.
- **L2:** M01 per-height derivative; M05 perturbation families; M09 finite-mode re-solving; M11 bias-to-visible-residual gain.
- **L3:** M03/M04 group-centroid/spread diagnostics; M10 azimuth/displacement intervention; M12 hubness/CSLS.

This is **three broad families**, or **five** if the L3 operations are separated. Neither taxonomy makes these twelve independent technical inventions. The finalists occupy two broad groups, with M06/M08 closely related. The screener's single L3 “duplicate group” obscures meaningful differences between centroid pooling, azimuth intervention and hubness analysis.

The previous iteration's independently audited baseline and revised arms each had **0/3 as-written survivors** and no candidate-performance support. This batch has **0/3 among twelve-generated/three-selected finalists**, not a comparable randomized treatment. Inputs, generation count, search evidence, selection and review differ. Consequently:

- No causal or statistical quality improvement is established.
- No empirical diversity improvement is established; family counts are descriptive and taxonomy-sensitive.
- More precise equations, explicit stop rules and better provenance are useful process observations, not measured opportunity-discovery gains.
- The nine unselected proposals were not externally adjudicated here; do not report 0/12 external survivors.

## Costs and engineering boundary

Verified ledger totals: **8/8 direct CLI calls** (4 generation, 1 screening, 3 finalist reviews); **10/25 public requests**; **9,226,121/120,000,000 bytes**; **4/6 new primaries**; **0 failed requests**; **0.112040531/300 diagnostic CPU seconds**; zero GPU and zero paid external API calls as recorded.

Top-level direct receipts sum to `totalNanoAiu=102646680000`, `totalPremiumRequestCost=8`, and `totalApiDurationMs=279951`. Nested/provider copies were not double-counted. These usage units and public-service quota headers are not a complete dollar invoice. **Dollar cost and enclosing coordinator/auditor billing remain unavailable, not zero.** Earlier campaigns are excluded.

Final engineering receipts were subsequently inspected:

- `final-checks/software-validation.json` and the test-log summary agree on **137 passing executions, zero skips**, exit 0. Automated browser scientific records are fixtures, not scientific experiments.
- `source-verification.json` reports **29 verified archive-chain roots**, explicitly preserving rather than legitimizing the old incorrect L1 quote. This broader coordinator receipt is distinct from this auditor's final-stage twenty-manifest check.
- `restart-before.json` and `restart-verification.json` agree on **166 persisted records** and digest `2dc4a26fa8e800397ae2f97f4bdb6d610a3ede0766d6b6a66cb37cb4e1fbe5bd`. The restart receipt reports HTTP **200**, **12 typed internal hypotheses** and **23 typed external publications**.

The current recorded URL is `http://127.0.0.1:8776/?campaign=campaign-16abc539e9ed#validation`. I did not rerun the tests or replay the live restart. The coordinator's post-publication reason-filter/source/diagnostic/reload UI journey was still planned when these receipts were reviewed. Software operation does not turn identity checks, review votes or conditional hypotheses into scientific performance evidence.

## Final interpretation

Keep **ITERATE**. Preserve all frozen candidates, reviews, corrections, diagnostics and the shortlist. The narrow studies may be worth revising and testing, but no current finalist has demonstrated a non-equivalent operational benefit, real failure-cause identification, or improved opportunity discovery. Future evidence would need the corrected, preregistered mechanism/test definitions and actual discriminating measurements—not another reviewer vote, an identity check or a retrospective change of finalists.
