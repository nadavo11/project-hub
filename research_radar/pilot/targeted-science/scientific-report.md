# Targeted discovery: M09 reached an experiment, not a supported contribution

**Decision: no-go for the tested contribution claim; retain M09 as an unresolved diagnostic lead.** This iteration completed an observed-problem → specified mechanism → real-correspondence experiment → independently checked decision cycle. It did not demonstrate a publishable invention.

## What the actual failures establish

| Inspected failure | Evidence | Mechanism question and boundary |
|---|---|---|
| Retrieval success does not ensure local discrimination | Three inspected InfoGeo queries have identity rank 1. Two selected native patch descriptors have cosine 0.936 and the same target maximum. | Semantic similarity, target-side hubs and physical ambiguity are competing explanations. Unreviewed point labels cannot support formal PCK. |
| A post-pose diagnostic cannot cover missing poses | Actual CPU SIFT produces 62 matches on the cross-domain OrthoLoC pair; only one agrees with nominal geometry within 4 px, and RANSAC returns no pose. | Correspondence errors, map mismatch and calibration remain competing explanations. M09 does not repair this upstream failure. |
| Low residual need not imply low reported position error | Two existing tracking sequences contain 293/1858 and 15/1001 frames with >=100 inliers, <3 px reprojection residual and >5 m position error. Stored position errors were independently recomputed from coordinates. | Map bias, tracking drift and correspondence errors compete. The logs do not isolate DSM error as the cause. |

These are local measurements, not literature-summary inventions. A previous motivation was also corrected: OrthoLoC's equal **matching** errors of 2.5/2.5 px accompany **reprojection** errors of 3.4/9.0 px, not equal residuals.

## Fully specified M09-v2

The original proposal remains frozen. The explicit revision uses eight QR-normalized height modes:
`1, x, y, x², xy, y², sin(pi*x), sin(pi*y)`.
Coordinates, units, distributions, rank checks, solver settings, seeds, missing-result handling and stopping rules are in [`m09-v2-protocol.json`](m09-v2-protocol.json).

For each identical +/-1 m mode probe, compare a full EPNP-RANSAC/LM re-solve with LM holding the current consensus fixed:

`S_X = max_probe ||C_full - C_fixed||`, where `C = -R^T t`.

Consensus change is one minus inlier-set Jaccard similarity. The falsifiable claim was that this excess predicts >1 m pose failures better than established analytic sensitivity, fixed/full finite re-solving, generic Monte Carlo, residual and inlier-count predictors. This is a proposed diagnostic, not a new pose estimator.

Nonlinear propagation is established in JCGM 101:2008; Vakhitov et al. (CVPR 2021) incorporate 2D/3D uncertainty in PnP refinement; EPro-PnP (CVPR 2022) models pose distributions. None of the examined passages proves exact prior publication of this diagnostic. Absence of such a match does not establish novelty.

## Decisive experiment and both outcomes

Actual SIFT matches on one solvable real image pair were tested under controlled, synthetic height corruption and three support sets. All **120 trials** solved; **64** exceeded 1 m. There were **99 unique input geometries from one scene**, not 120 independent scenes. Labels are reconstruction-derived, not surveyed external-map truth.

| Predictor | Failure AUROC |
|---|---:|
| Analytic sensitivity | 0.647 |
| Fixed-consensus finite sensitivity | 0.664 |
| Original-style full re-solving | 0.780 |
| **M09-v2 consensus-switch excess** | **0.729** |
| Generic Monte Carlo / reprojection residual | **0.784 / 0.784** |

The revised score missed its predeclared +0.05 incremental gate: difference **-0.054**, conditional paired-block 95% interval **[-0.140, 0.022]**. This fails the improvement claim; it does not prove significant inferiority.

**Positive lead:** on full 111-match support, excess reached **0.902**, versus the strongest ordinary predictor's **0.831**. It fell to **0.738** and **0.635** on the two 55-match supports. This interaction is retained, not promoted retrospectively. Separately normalized mode bases confound a causal support comparison.

Consensus change averaged 0.100; excess with unchanged consensus was at most 1.01e-6 m. This supports a link to consensus changes, but initialization also differs. Changing OpenCV's global RNG left outputs unchanged; independent internal RANSAC streams were not established.

## Selection audit and decision

All nine unselected proposals were reviewed, with independent deep checks of M02, M11 and M12: **one retained as a control, seven requiring revision, one rejected as written**. These are not eight novel survivors. Important premature objections were corrected: M11 has a 2N-dimensional residual space, its DCT restriction is valid, and M12's query-only CSLS term does not affect gallery ranking. M11 nevertheless has a constant-height gauge that can make its proposed maximum gain infinite.

The independent evaluator reproduced the statistics and found no blocking defect for the bounded negative conclusion. The study does not implement all published uncertainty-aware estimators, estimate calibrated rejection risk, or establish scene generalization.

**Change the discovery strategy toward measured failures, not another broad generation batch.** The next discriminating study would use independent scenes, common physical perturbation fields and matched supports, testing absorbed bias versus visible residual. The main cross-domain failure also needs an upstream correspondence investigation; M09 cannot help before a pose exists.

Evidence: [independent evaluation](independent-evaluation.md), [selection audit](selection-audit.md), protocol, raw trial rows and primary-source packet alongside this report. Actual experiment: **2.58 CPU seconds**, no GPU/training or dependency installation; six targeted public requests, three primary sources. Total model billing is unavailable.
