# Independent scientific evaluation

## Decision

**No distinct, significant contribution is supported yet.** The experiment is substantive and informative, but M09-v2 fails its prospective incremental-discrimination gate. Preserve the negative result and the full-support lead; do not promote a favorable subgroup retrospectively. This does **not** show that every nonlinear regime is useless.

## Observed problem → mechanism

Three recorded failure patterns survive inspection:

- Tracking logs contain **293/1858** and **15/1001** frames meeting exploratory criteria of ≥100 inliers, <3 px reprojection residual and >5 m position error. These demonstrate residual/error disagreement, not its cause.
- Two selected InfoGeo **native DINOv2 patch descriptors**, not global descriptors, have cosine **0.93599** and the same target maximum. All three inspected query identities rank first. This supports retrieval-success/local-ambiguity coexistence; unreviewed point annotations prohibit formal PCK or correspondence-accuracy claims.
- The real cross-domain pair produces **62 SIFT matches**, only **one** consistent with nominal geometry, and **no pose**. This remains a pipeline failure, outside the coverage of post-pose sensitivity scoring.

Map bias, tracking drift and incorrect correspondence remain competing explanations. The original M09 motivation needs correction: OrthoLoC Table 6 reports unchanged *matching* error, 2.5/2.5 px, but reprojection error **3.4→9.0 px**. It does not demonstrate residual-invisible degradation.

The revised mechanism is narrower: compare full RANSAC re-solving against fixed-consensus refinement under identical height probes. Their camera-centre difference could expose instability beyond continuous local sensitivity.

## Experiment → result

The inspected implementation uses **actual image matches**, DSM lifting, EPNP-RANSAC and LM. This is not a pure identity check. Height corruptions are synthetic; pose truth is reconstruction-derived, **not independently surveyed DSM truth**.

I verified frozen protocol/implementation/matching/cache hashes, all 120 design cells and labels, and independently recomputed AUROCs by rank sums and the 2,000-replicate paired-block bootstrap. All **120 solve; 64 exceed 1 m**. No required probes fail.

| Predictor | AUROC |
|---|---:|
| GN analytic sensitivity | 0.6468 |
| Fixed-consensus finite sensitivity | 0.6643 |
| Full finite sensitivity, M09-style | 0.7796 |
| **New consensus-switch excess** | **0.7294** |
| Generic Monte Carlo / reprojection residual | **0.7838 / 0.7838** |
| Negative inlier fraction / seed spread | 0.7360 / 0.5000 |

The primary excess-minus-best gap is **−0.0544**, conditional eight-block 95% interval **[−0.1401, 0.0223]**. The gate fails; this interval does not establish significant inferiority either.

Mean consensus change is **0.0996**; maximum excess with unchanged consensus is **1.01×10⁻⁶ m**. Tested seed spread is exactly zero, but **cv2.setRNGSeed may not change PnPRansac’s internal sampling**: independent hypothesis streams were not established. Consensus association is supported, not exhaustive exclusion of randomness. Full and fixed solves also differ in initialization, preventing complete causal isolation.

Full 111-match support is a promising secondary result: excess **0.9023**, versus best ordinary **0.8308**. It falls to **0.7375** with random55 and **0.6347** with concentrated55. That interaction needs independent confirmation.

## Scientific limits and implementation omissions

- **One solvable scene and 99 unique input geometries**, not 120 independent examples. Eight blocks represent synthetic-error draws. Twenty-four zero-amplitude rows repeat three geometries/labels; Monte Carlo probes still vary. Bootstrap uncertainty is conditional, not scene generalization.
- Amplitude pooling matters: residual AUROC is 0.7838 pooled but **0.1944/0.1259** at amplitudes 0.25/0.5. At amplitude 2, excess reaches 0.9565 with **only one negative**. Neither pooled superiority nor a favorable stratum is universal.
- Each support gets a separately normalized QR basis. Shared coefficients therefore do not impose identical physical error fields; support comparisons do not isolate concentration alone.
- The analytic implementation is a **Gauss–Newton implicit camera-centre derivative**, not an exact-Hessian derivative or a complete propagated covariance score. Nominal fixed-consensus finite-difference discrepancies, **0.58%, 0.58%, 1.23%**, pass the declared check. Accuracy under every corrupted state is unverified.
- Monte Carlo uses 16 spherical probes and a maximum displacement, not calibrated uncertainty. There is **no implementation of Vakhitov’s covariance-weighted estimator or EProPnP**. No calibrated rejection operating point is tested.
- The original frozen M09’s 300-trial/Spearman criterion was not executed. This is an explicit v2 experiment, not retrospective completion of that original protocol.
- The bootstrap fixes the empirically strongest comparator; it is not simultaneous inference against all baselines. This does not rescue the failed gate.

No identified defect blocks the bounded negative verdict.

## Novelty and selection

Direct primary passages establish relevant prior art:

- **JCGM 101:2008, §§5.8–5.9:** nonlinear numerical propagation by repeated sampling and model evaluation is established.
- **Vakhitov et al., CVPR 2021, §3.5, Eq.21:** PnP refinement incorporates both 2D and 3D uncertainty.
- **Chen et al., CVPR 2022, §§3.1–3.2:** pose distributions address ambiguity beyond local Laplace approximations; Monte Carlo integrates the training objective.

These are not proofs that the exact full-minus-fixed diagnostic already exists. They do defeat broad novelty claims about nonlinear propagation or uncertainty-aware PnP. **Incremental practical value remains unsupported**, independently of exact novelty.

All nine unselected candidates were reviewed: retain M01 as control; revise M02/M03/M04/M05/M10/M11/M12; reject frozen M07. Deep-three corrections are substantive: M02 normalization/depth defects; M11’s **2N** residual dimension and valid DCT composition, but degenerate DC gain; M12’s ranking-invariant query-side CSLS omission, with unresolved exposure confounding. Missing experiments do not imply nonnovelty or an illegitimate question. M06/M08 remain rejected per the separate user instruction; original M09 stays unchanged and under investigation.

## Next scientific action

Freeze an independent-scene **M11-v2 absorbed-bias versus residual-visibility** test: separate DC, use common physical perturbation fields and count-matched supports, and prospectively test the full-support interaction against ordinary baselines. Keep M02 as a support control and M12 as a separate retrieval hypothesis. Do not promote M09 meanwhile.
