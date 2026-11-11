# Failure-first localization analysis

**Result: a reproducible configuration bottleneck is established; the complete causal diagnosis remains partial.** M09 is stopped as a paper direction. General opportunity generation is paused. No new research mechanisms or novelty claims were generated.

Open the [interactive Failure Atlas](http://127.0.0.1:8776/atlas.html).

## Cohort and what is actually verified

The frozen cohort contains **36 real retrieved pairs**:

- **24 DenseUAV identities:** every second identity in the existing 48-identity subset, with H80/H90/H100 query labels cycled evenly. Actual saved InfoGeo top-one retrieval is used, not an oracle replacement. All 24 retrieved targets have the correct official identity. Original image members and hashes are checked. Geographic identity is not pixel ground truth.
- **12 AnyVisLoc frames:** four predetermined indices per satellite scene across Scenes 04, 06 and 19. Released pitch-from-nadir values span approximately **0.7–85.5 degrees**. The scenes include urban buildings and open terrain. Each uses the actual top-one InfoGeo crop. Scene identity and crop provenance are verified; **visual footprint overlap is not independently established for every crop**. Camera position inside a crop would not establish overlap for an oblique view.

These are 24 DenseUAV identities plus three correlated AnyVisLoc scenes, not 36 independent environments or a population-representative benchmark. DenseUAV altitude variation is not treated as measured viewpoint variation. Pixel correspondence GT is unavailable throughout.

## Baselines and instrumentation

Fresh CPU inference ran original **RoMa outdoor**, pinned to source commit `77f8d68803526dcddfd9b7a46bc76125bdc25f15`, with verified local RoMa and DINOv2 weights: 560-square coarse input, 640-square refinement, forward-only, no custom correlation. SIFT and ORB use original-resolution images, 4,000 features, mutual matching and a 0.8 ratio threshold.

Every case retains detected-feature or dense-lattice counts, original confidence, spatial coverage, homography residuals/inliers, DSM validity, 3D singular values, PnP consensus, post-fit positive-depth inliers, camera assumptions, pose outcome and source provenance. Homography residuals are in target pixels; PnP residuals are in query pixels.

Metric PnP is attempted only for AnyVisLoc, using released K/distortion, documented map coordinates and DSM. P3P-RANSAC uses 2,000 iterations, an 8-pixel threshold and at least 12 post-fit positive-depth inliers. Position errors use released **SfM-refined horizontal camera coordinates**, not independently surveyed 6-DoF truth.

The primary RoMa selection policy inherited from our application uses certainty >=0.20, strongest-per-64x64-source-cell selection and a 2,048 cap. After observing starvation, two separately frozen follow-ups reused the **identical native predictions**, without new inference:

1. Change only the gate to 0.05, retaining the same spatial selection.
2. Use pinned upstream `RegressionMatcher.sample` (`threshold_balanced`, threshold 0.05, seed 731), capped at 2,048. Displayed confidence remains the original certainty, not transformed sampling weights.

This compares an installed established baseline and its upstream sampling policy; it is not a full published-system or current-SOTA reproduction.

## Quantitative outcomes

**AnyVisLoc, denominator 12 pairs per condition:**

| Condition | Accepted poses | Horizontal error <=10 m | Accepted but >10 m | No accepted pose |
|---|---:|---:|---:|---:|
| SIFT | 0 | 0 | 0 | 12 |
| ORB | 0 | 0 | 0 | 12 |
| RoMa, gate 0.20 | 0 | 0 | 0 | 12 |
| RoMa, gate 0.05 | 3 | 1 | 2 | 9 |
| RoMa, upstream sampling | 11 | 1 | 10 | 1 |

At gate 0.20, **10/12** AnyVisLoc pairs retain fewer than 12 matches. Lowering the gate reduces that to **7/12**. Upstream sampling supplies 2,048 matches per pair, but its accepted-pose median horizontal error is **306.72 m**; the maximum is **935.82 m**. Acceptance is not localization correctness.

**Decisive paired case, L06_0425:** changing only the gate from 0.20 to 0.05 changes 13 retained matches and no accepted pose into 169 matches, 28 post-fit inliers and **8.75 m** horizontal error. This operational improvement was reproduced from retained inputs. It does not establish true point accuracy or make 0.05 a safe universal setting: the other two accepted low-gate poses err by **61.73 m and 930.61 m**.

**Estimator sensitivity:** on the same L06_0425 upstream-sampled matches and satellite DSM, P3P gives **13.90 m**, while EPNP gives **4.62 m**. This isolates an estimator-choice effect on that input; it does not establish general EPNP superiority.

**DenseUAV:** all 24 geographically correct retrieved pairs lack verified metric intrinsics/depth/map-scale prerequisites in this subset. RoMa at gate 0.20 has a median of 50 retained matches and median homography inlier fraction 0.759, but neither establishes point accuracy or metric pose. Three pairs retain fewer than 12 matches. Metric geometry remains missing for all 24, including the locally self-consistent cases.

## Depth intervention: negative result retained

Satellite DSM spacing is **30 m**; available aerial DSM spacing is approximately **0.25–0.65 m**. At identical local XY and common valid support, we crossed satellite/aerial heights with P3P/EPNP, holding satellite imagery, matches and K/dist fixed.

The initial 36 method-case sets and subsequent 24 sampling-control sets produced **240 depth/solver cells**. Finer-provider depth did **not** create an accepted <=10 m result in these cells. For L06_0425 at gate 0.05, replacing heights changes P3P error from 8.75 to **15.77 m**. Do not infer that finer DSMs are generally worse: provider, acquisition epoch, surface interpretation and vertical alignment are not independently controlled. The initial gate-starved cases offer little power to diagnose depth.

## Established versus unresolved

**Established:** the inherited confidence gate can obstruct pose formation; changing it alone alters measured localization outcomes. Metric prerequisites are absent in the DenseUAV subset despite correct retrieval. Solver acceptance and large correspondence counts are inadequate correctness checks.

**Unresolved:** incorrect matches versus incomplete crop overlap; repeated-structure confusion versus viewpoint/domain shift; camera/DSM error versus estimator behavior in each wrong pose. Self-fit residuals cannot settle these without point GT or additional independent constraints.

**Concrete next action:** obtain independently checked landmarks and geometry on a small matched subset, evaluate confidence/spatial-support operating points on held-out scenes, and validate pose rejection against independent errors. Do not deploy the lower gate globally or start another mechanism-generation batch.

## Reproducibility and bounds

The atlas exposes case selection, five matching/sampling conditions, confidence maps, filtered correspondences, exact point inspection, geometric residuals, depth/solver controls and JSON exports. All 180 method-case records, 36 input pairs and threshold operators were checked; nine successful, failed and wrong pose outcomes were numerically reproduced.

Artifacts: `data/research-radar/failure-atlas/` contains frozen protocols, input PNGs, native RoMa warps, all measurements, depth inputs, costs and verification receipts. The source scripts are `research_radar/failure_atlas_*.py`.

To recheck numerical outcomes without inference:

```bash
cd /home/nadavo/project-hub
/home/nadavo/localization-models/.venv/bin/python -m research_radar.failure_atlas_finalize verify
```

For a complete replay on copied frozen inputs, use the existing RoMa interpreter and a **new output directory**:

```bash
CUDA_VISIBLE_DEVICES='' /home/nadavo/localization-models/data/workbench/runtimes/crossview-roma/venv/bin/python \
  -m research_radar.failure_atlas_finalize replay --output /path/to/new/replay-directory
```

Timed experiment stages total **2,034.06 CPU seconds (33.90 CPU minutes)** and **611.23 wall seconds**. No GPU, training, new downloads or dependency installation was used. Preparation, UI work and coordinator billing are outside these timing totals; model billing is unavailable.
