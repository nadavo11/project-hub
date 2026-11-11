# Attribution gate: correspondence truth and pose rejection

**Decision: ITERATE. Experiment B is complete as a bounded retrospective study.
Experiment A remains blocked on independent human annotation. No new mechanism
batch was generated; M09 remains stopped.**

The strongest fixed rejection check removed **9/10 geographically wrong accepted
poses and retained the sole <=10 m case**. It did not remove the last catastrophic
false acceptance. Holding out its entire scene cannot resolve the broader
calibration problem: all accurate primary outcomes belong to Scene_19, leaving
zero accurate training examples when that scene is held out.

## What was actually measured

All 12 original AnyVisLoc satellite pairs, four per scene, were retained, including
the primary success, ten false acceptances and one failure. These are an
outcome-enriched convenience cohort, not an estimate of population prevalence.
Every pair uses its unchanged 2,048 upstream-sampled RoMa matches, original
certainty, camera calibration, crop transform and satellite DSM. No matcher was
rerun and no GPU was used.

The observable criterion and the reference label are separate:

- Pose acceptance: at least 12 positive-depth, <=8-original-pixel reprojection
  inliers. Additional checks use support, coverage or disagreement between
  estimated positions, **never distance to the reference position**.
- Accuracy label: horizontal error <=10 m relative to the released SfM-refined
  reference. This is neither surveyed ground truth nor complete 6-DoF accuracy.
- Estimators: legacy P3P-RANSAC, EPNP-RANSAC and OpenCV USAC with MAGSAC scoring
  and inner local optimization; fixed 2,000-iteration cap, .999 confidence,
  seed 731. This bounded configuration is not a reproduction of a published
  full-system benchmark. Legacy P3P-RANSAC itself uses EPnP for its final
  nonminimal refit; these are not independent sensors or independent evidence.

The grids and fixed checks were frozen before the new measurements. The
coordinator had already seen the original errors: this is **retrospective
scene-blocked analysis**, not prospectively blinded validation.

## Experiment B: rejection results

Each row applies to the same 11 primary accepted poses. The twelfth pair remains
an original estimation failure; it is not counted as a successful rejection.

| Fixed check | Wrong poses rejected / 10 | <=10 m case retained / 1 | Wrong poses retained |
|---|---:|---:|---:|
| Accept all | 0 | 1 | 10 |
| Reject all, negative control | 10 | 0 | 0 |
| Inlier fraction >=0.10 | 10 | 0 | 0 |
| Minimum source/target inlier hull fraction >=0.10 | 9 | 0 | 1 |
| P3P/EPNP estimated-XY agreement <=10 m | 8 | 0 | 2 |
| P3P/USAC-MAGSAC estimated-XY agreement <=10 m | **9** | **1** | **1** |
| Spatial-half estimated-XY stability <=10 m | 10 | 0 | 0 |
| Spatial-half withheld-match support >=0.10 | 10 | 0 | 0 |

These are engineering operating points, not literature-validated thresholds.
Spatial checks use five seeded partitions of 8x8 source-image cells, fitting
both halves separately and measuring residuals on withheld matches. Any failed
half makes the score unavailable; missing scores fail closed in fixed rules.
The sole accurate case has one failed half-fit and therefore fails these checks.
Withheld matches from the same dense prediction remain correlated and are not
independent correspondence truth.

**Changing the robust estimator does not solve the accuracy problem:**

| Estimator, same frozen matches | Accepted <=10 m | Accepted >10 m | No accepted pose |
|---|---:|---:|---:|
| P3P-RANSAC | 1 | 10 | 1 |
| EPNP-RANSAC | 1 | 7 | 4 |
| USAC-MAGSAC | 1 | 11 | 0 |

The EPNP success is L06_0425, not the primary L19_0001 success. No oracle selects
the best estimator per query.

### Actual cases

All errors below are horizontal meters. Review links open the exact frozen
images in the existing PointMatch Atlas annotation workbench. **This table is
for investigators, not a blinded first-pass annotator packet.**

| Case / PointMatch review | P3P | EPNP | USAC-MAGSAC |
|---|---:|---:|---:|
| [L04_0001](http://127.0.0.1:8013/?pair=custom-8c41648abd0c4a7c#annotations) | 744.56 | No pose | 753.11 |
| [L04_0959](http://127.0.0.1:8013/?pair=custom-f9ea7f15ad4e4fc0#annotations) | 60.00 | 397.79 | 274.51 |
| [L04_1893](http://127.0.0.1:8013/?pair=custom-5dbff15891ca46b7#annotations) | 277.46 | No pose | 387.75 |
| [L04_2828](http://127.0.0.1:8013/?pair=custom-a307f9047db6418b#annotations) | 113.33 | 116.42 | 127.48 |
| [L06_0001](http://127.0.0.1:8013/?pair=custom-eb23810c9fc04f11#annotations) | 417.95 | 394.54 | 557.23 |
| [L06_0425](http://127.0.0.1:8013/?pair=custom-0440e343c6374fee#annotations) | 13.90 | **4.62** | 35.54 |
| [L06_0849](http://127.0.0.1:8013/?pair=custom-23913b68b69b45b0#annotations) | 357.44 | 301.32 | 211.96 |
| [L06_1274](http://127.0.0.1:8013/?pair=custom-eaf2deb569354793#annotations) | **935.82** | **935.82** | **939.73** |
| [L19_0001](http://127.0.0.1:8013/?pair=custom-2c4f776405584f52#annotations) | **8.35** | 22.18 | **4.21** |
| [L19_0081](http://127.0.0.1:8013/?pair=custom-cf274b4c70594158#annotations) | No pose | No pose | 300.10 |
| [L19_0161](http://127.0.0.1:8013/?pair=custom-52af723d0b4c44ce#annotations) | 306.72 | No pose | 469.63 |
| [L19_0241](http://127.0.0.1:8013/?pair=custom-af44fefd3d274ce7#annotations) | 534.95 | 458.18 | 508.12 |

### Held-out scenes, not held-out frames

For each feature, thresholds were selected only using the other two scenes,
minimizing false accepts while retaining every accurate accepted training case.
No accurate training example, or no feasible threshold, means **abstain**.
The held-out scene's reference labels never enter threshold selection.

| Feature | Wrong rejected in calibrated folds | Wrong retained | Accepted-pose abstentions |
|---|---:|---:|---:|
| Inlier fraction | 6 | 2 | 3 |
| Inlier hull coverage | 4 | 4 | 3 |
| Median inlier residual | 4 | 4 | 3 |
| EPNP disagreement | 5 | 3 | 3 |
| USAC-MAGSAC disagreement | 7 | 1 | 3 |
| Spatial-half stability | 0 | 0 | 11 |
| Spatial-half support | 0 | 0 | 11 |

The three accepted-pose abstentions in the first five rows are the Scene_19
fold, including the sole accurate case. Its fourth query is the original
no-pose case. **Accurate-case retention is not established by held-out
calibration.** The spatial rules have no feasible recall-preserving training
threshold in either remaining fold. Additional frames of these same scenes
would not constitute new-scene validation.

## The remaining false acceptance: a useful diagnostic, not a new method

L06_1274 remains 935.82 m wrong under P3P. EPNP's position differs by only
**0.0654 m**, and USAC-MAGSAC differs by **5.1437 m** while being 939.73 m wrong.
Their agreement is agreement on a wrong solution. The minimum normalized
source/target inlier hull covers only **0.337%**, versus **4.572%** for L19_0001.

A separately recorded **post-outcome** geometric inspection found that the
L06_1274 estimate puts the camera **4.11 m below the supplied DSM at its estimated
XY**, with an **upward-pointing optical axis**. The ground-viewing image instead
shows low-structure terrain. This motivates an ordinary pose-plausibility check
and targeted overlap/landmark review, not a new descriptor architecture.
Coarse DSM clearance is not measured AGL; missing terrain support stays missing.
No post-hoc combined rule is presented as an independently successful test.

This gives a falsifiable case-level hypothesis: geographically wrong consensus
can survive estimator changes when spatial support is weak and the fitted pose
violates the task's physical camera constraints. Independently reviewing its
visible overlap and inlier landmarks, then testing predeclared gravity/terrain
checks on new scenes, can distinguish this explanation from bad correspondences
or incorrect camera/map assumptions. It does **not** yet assign blame to RoMa.

## Experiment A: ready for review, not completed ground truth

Twelve neutral-ID pairs were imported through PointMatch's existing upload API.
All 24 decoded images were verified pixel-identical to the frozen inputs.
No predicted matches, pose-error labels or dummy landmark coordinates were
attached to those review pairs. There are **zero saved annotations** in this
cohort, no independently verified crop-overlap decisions and no qualified
correspondence labels. Accordingly, confidence-versus-correctness remains
**unmeasured**, not zero and not inferred from consensus.

The review packet supplies direct links, blank per-pair review forms and a
point-wise notes schema: physical landmark description, uncertainty radius in
each original image, ambiguity, reviewer identity, and second-review linkage.
Use PointMatch's existing zoom/click annotation interface and structured notes.
No-overlap/unmatchable cases use the review forms rather than fictitious points.
Drafts remain drafts; the generic single-reviewer "verified" checkbox alone does
not meet this study's two-reviewer gate. Human identity/independence cannot be
established merely by entering two different names.

Original K, distortion, image dimensions, crop offsets, map affines, DSM hashes
and nearest-DSM indexing were reproduced for every pair. This rules out a
disagreement with the frozen source conversion, **not physical miscalibration**.
Released camera heights are sanitized local heights, not AGL; their vertical
alignment with provider DSMs is unverified. A constant vertical shift of the
world points and camera leaves projections and horizontal position unchanged;
this was checked in camera coordinates and on finite inlier projections.
Absolute-height differences alone therefore cannot explain these XY errors.

## Gate and next evidence

| Required evidence | Observed outcome |
|---|---|
| Recurring consequential failure | Reproduced 10/11 accepted primary poses above10 m; limited to this cohort |
| Independently checked correspondence truth | **Blocked**: human landmark and overlap review not available |
| Cause isolated or competing causes distinguished | Estimator dependence and one physically implausible consensus identified; matching versus overlap versus calibration still unresolved |
| Established remedies compared | P3P, EPNP, USAC-MAGSAC and support/coverage/spatial-holdout checks executed |
| Reliable rejection of all ten while keeping the accurate case | **Not demonstrated** by fixed checks; scene-calibrated accurate-case recall unavailable |
| New-scene confirmation | **Blocked**: no frozen matches from genuinely unseen eligible scenes in this cohort |

Keep **ITERATE**, pause mechanism generation and preserve all negative checks.
The necessary next input is independent review of the prepared PointMatch pairs
and additional eligible scenes containing accurate as well as inaccurate poses.
Until that evidence exists, neither correspondence-confidence calibration nor a
scientific-contribution GO is justified.

## Reproducibility and evidence

PointMatch owns the inputs, measurements and annotation packet:
`/home/nadavo/pointmatch-atlas/results/radar-attribution/`.
Key artifacts are `protocol.json`, separate `labels.json`, `cases/*/input.npz`
(no geographic labels), `cases/*/measurement.json`, `results.json`,
`review-packet.json`, `review-forms/`, `geometry-diagnostics.json`,
`numeric-verification.json` and `browser-render-verification.json`.
Research Radar stores this report and the attribution validation/decision record.

Measured experiment cost: **5.070 CPU seconds / 5.071 wall seconds**, 156 fits,
zero new inference or GPU time. This excludes preparation, image imports,
verification, browser work and model/coordinator billing, which is unavailable.
Two small upstream documentation files were downloaded; no data, weights or
dependencies were downloaded. Three failed documentation lookups are recorded
in the execution notes.

All 156 fits, decisions and coordinate mappings were reproduced; 16 targeted
tests passed, and the actual PointMatch review links and rendered images were
checked on desktop/mobile. These checks do not substitute for scientific labels
or an independent human evaluation.

```bash
cd /home/nadavo/pointmatch-atlas
CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=1 \
  /home/nadavo/localization-models/.venv/bin/python \
  scripts/verify_radar_attribution.py numeric
python3 scripts/verify_radar_attribution.py browser
```

For a fresh replay, run `python -m atlas.campaigns.radar_attribution prepare`
and then `run`, both with the same unused `--output` directory and the scientific
interpreter above. Existing artifacts are immutable; completed case records
support resumption. No need to reimport images or rerun RoMa.

Method references: version-pinned OpenCV
[PnP documentation](https://github.com/opencv/opencv/blob/4.11.0/modules/calib3d/doc/solvePnP.markdown)
and [USAC documentation](https://github.com/opencv/opencv/blob/4.11.0/doc/tutorials/calib3d/usac.markdown),
plus the previously preserved
[AnyVisLoc coordinate/pose implementation](https://github.com/UAV-AVL/Benchmark/blob/6c8f7980f35defd0676d82e71b19fcd214da4033/avl_utils.py).
This is comparison with established machinery, not a novelty claim.
