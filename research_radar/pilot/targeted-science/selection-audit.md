# Selection audit: recover scientific questions, not novelty claims

**Decision:** retain one comparator, revise seven questions explicitly, reject one frozen standalone proposal. This does **not** establish that the shortlist was optimal, validate any candidate, or replace M09/M08/M06 retrospectively.

The nine unselected candidates were screened independently. The deeper sample **M02/L1, M11/L2, M12/L3** was fixed before this audit because it spans limitations and suspected reviewer overreach. It is purposive, not an unbiased sample for estimating a screening-error rate. No network, model spawning, training, GPU, candidate-performance experiment, parent experimental output inspection, or code change occurred. Only these two reports were written.

## What survives scientifically?

1. **M11-v2 is the most useful complement to M09.** Ask whether a height error is absorbed as camera bias or remains visible in image residuals. But remove the universal constant-height gauge from any proposed discriminating score: otherwise the frozen maximum gain is generally infinite.
2. **M02-v2 is the most direct competing explanation/control for real-match failure.** Ask whether concentrated support matters after controlling match count and residual, or whether broad-support failures instead implicate incorrect correspondences/map mismatch. A cheap established proxy can be useful without being novel.
3. **M12-v2 offers a legitimate retrieval hypothesis, not a direct PnP explanation.** Hubness is known; whether it explains these particular misses is unmeasured. Its relevance to M09 requires an actual retrieval/descriptor-assignment link.

These are proposed studies, **not findings that height bias, concentration or hubness caused the failures**.

## Evidence boundary and a material source correction

The sources below are existing local documents, not generated ideas:

- **[C]** `research_radar/pilot/mechanism-first/candidates.json`, objects by ID: frozen proposals.
- **[S]** `research_radar/pilot/mechanism-first/shortlist.json`, `result.screening` and selection rationale.
- **[A]** `research_radar/pilot/mechanism-first/independent-validation-report.md`, grounding, reviewer-error items 1/2/9/10, and M09 adjudication. This supplied allegations; their mathematical validity was checked rather than adopted by vote.
- **[O]** `research_radar/pilot/sources/candidate-audit/2509.18350.txt` — OrthoLoC. Table 3, lines 1129–1134; Table 6, lines 1840–1854; C.7, lines 1978–1983 and 2046–2053; A.5, lines 1098–1116.
- **[ON]** `research_radar/sources/2607.19951.txt` — OffNadirLoc. Table 4/§5.5, lines 501–543; rendering, lines 183–188; patch evaluation near line 393.
- **[O2]** `research_radar/pilot/sources/candidate-independent-search/2507.13486.txt`, §3.1/equation 1, lines 455–515. Established photogrammetric covariance propagation, including “low-frequency, systematic errors” at lines 494–498.
- **[O3]** `research_radar/pilot/sources/candidate-independent-search/2309.10698.txt`, §III.D, lines 394–420. Established E-optimal minimum-information-eigenvalue sensor arrangement.
- **[BA]** `data/research-radar/mechanism-first-sources/bundle.txt`, §3 near line 329 and §6.1 near line 1309. Established local covariance and block elimination; retained quoted passages also appear in `mechanism-first/external-prior-art.json`.

**Equal matching error is not equal reprojection error.** Table 6's SP+LG DOP versus DOP+DSM entries are:

| Metric | DOP | DOP+DSM |
|---|---:|---:|
| Matching error | 2.5 px | 2.5 px |
| Translation error | 0.42 m | 1.07 m |
| **Reprojection error** | **3.4 px** | **9.0 px** |
| 1m–1° recall | 71.3% | 42.3% |

Thus the broad claim that image residuals did not reveal this aggregate degradation is unsupported even by the same table. Equal rounded ME does not identify a residual-nullspace mechanism. Different test populations, 17/496 versus 17/423 in-place/out-place, further prevent a paired DSM-only interpretation. A residual-invisible height gauge nevertheless exists mathematically; that is a different claim. [O]

**L1 was already a cropping experiment.** C.7 explicitly says “by cropping the reference raster.” The screener's contrast between M02 cropping and the authors' supposedly natural covisibility data is inaccurate. Masking a query still differs from cropping a reference, and neither isolates concentration from match quality. [O]

**L3 has an unknown cause, not an illegitimate question.** ONLoc's 72.64% R@1 leaves 27.36% misses in rendered patch retrieval. This motivates hypotheses; it does not establish any proposed cause partition or metric-pose claim. [ON]

## All-nine screening audit

Here **retain** means retain a scientific role, **revise** means a new version only, and **reject** means reject the frozen standalone proposal. No decision certifies an unrun protocol.

| ID / disposition | Novelty | Scientific significance | Technical specification | Feasibility / available evidence | Was exclusion premature? |
|---|---|---|---|---|---|
| **M01 — retain as analytic control** | First-order propagation is established, not an invention. [O2] | Necessary comparator for M09; numerical/approximation failure is informative. | With fixed geometry and fixed noise scale, predicted RMS is constant across iid trials; per-trial Pearson correlation can be undefined. **M01-v2-control** must compare moments or paired responses across varying geometry. | Small CPU calculations plausible; no real DSM attribution established. | Portfolio exclusion as a new method is reasonable. “Synthetic checks cannot falsify anything” is too strong. |
| **M02 — revise** | Established support/conditioning proxy; OASIS does not prove exact equivalence to image-coordinate covariance. [O3] | Cheap support-versus-bias alternative/control. | Wrong normalization/range; pose-dependent depth used before pose exists. See deep audit. | Cheap after matches exist; no demonstrated predictive gain. | Yes if rejected for being untested. Specification objections are real. |
| **M03 — revise** | Pooling/margin analysis established; exact diagnostic novelty unresolved. | Spread versus gallery confusion is testable. | `1−cos` does not obey the invoked metric triangle inequality; mean spread cannot bound every view. `s/m` is problematic at zero/negative margin. Oracle truth enters the diagnostic, not just the intervention. | ONLoc-specific assets unverified, not proved globally unavailable; aggregate evidence only. | Unknown cause is not a rejection reason. **M03-v2** must drop the claimed universal 0.5 theorem and use explicit per-view margins/leave-one-view-out oracle pooling. The screener mentions a random-group control absent from M03; it is in M04. |
| **M04 — revise** | Multi-view averaging is not new. | Oracle pooling can measure recoverability. | A/B/C overlap without a tie rule; cross-modality similarities are not calibrated cause labels. Pooling can reduce noise or aliasing too, so it does not uniquely “isolate” spread. | Conditional on target descriptors and groups; no intervention evidence. | “Hypothesis test only” is not a scientific defect. **M04-v2** reports multi-label associations and recoverability, with matched random groups, not a causal partition. |
| **M05 — revise as control** | Numerical propagation is established. [O2] | Mode/amplitude controls can separate M09 nonlinearity from ordinary propagation. | A vector outer product `S sigma² Sᵀ` is valid for one scalar mode; the review overstates that objection. Multiple modes need a matrix and coefficient covariance; metre/degree norms remain undefined. | CPU re-solves plausible; no certified error truth or measured effect. | Low novelty does not remove its control role. **M05-v2-control** explicitly defines modes/covariance and separates translation/rotation units. |
| **M07 — reject frozen standalone proposal** | E-optimality established; internal overlap is not external prior art. [O3] | Underlying observability question survives, but this score adds no justified physical interpretation. | Mixed pose/focal scaling cannot yield metres from the minimum eigenvalue alone; needs eigenvector/coordinate projection. “Equal count” example then adds points to one set. | Matrix computation feasible; invalid units are not computational infeasibility. No separating evidence. | Rejection on these technical grounds is defensible. Synthetic success is not guaranteed, so that argument is unnecessary. No repaired M07 is credited. |
| **M10 — revise/defer** | No new retrieval operator claimed; exact intervention novelty unresolved. | Azimuth-rotating displacement versus fixed alias is falsifiable. | Removing top-1 only measures rank-2 recoverability. Re-rendering also changes visibility; rotating errors do not uniquely identify projective offset. | Cannot run the original intervention in this offline audit; access remains unverified. Proxy cannot explain ONLoc residuals. | Deferral is justified, dismissal of “invented hypotheses” is not. **M10-v2-deferred** requires matched-location multi-azimuth data and explicit visibility/permutation controls. |
| **M11 — revise** | Bias/error propagation established; exact gain novelty unresolved. [O2] | Best complement to M09: absorbed bias versus visible residual. | Review is wrong about both sample count and DCT restriction. Frozen gain also has a universal DC-gauge problem. See below. | CPU linear algebra plausible; only formal/source evidence here. | Yes: two review errors. Correcting them does not validate the frozen gain or establish real causality. |
| **M12 — revise** | CSLS/hubness is known and conceded. No archived primary CSLS paper was located in the searched source-text directories; no exact prior-art citation is invented. | Whether hubness explains these misses remains testable. | Query-only CSLS omission preserves ranking. Undefined A cutoff, pool policy and exposure null are real defects. | Cheap given descriptors; target descriptors not demonstrated by this audit. | Known mechanism and unknown cause are different issues; neither invalidates a diagnostic question. |

The detailed JSON preserves each candidate's separate reasons and explicit version changes. No original hypothesis was edited.

## Deep audit 1 — M02: normalization is wrong; the question is not thereby answered

Let image dimensions be `W,H`, diagonal `d=√(W²+H²)`, and original normalized coordinates `(u−c)/(d/2)`. For uniform support:

```text
C_uniform = diag(W²,H²) / [3(W²+H²)].
```

For a square, both eigenvalues are **1/6**, not 1/12. At constant depth the original score is therefore **√2**, not a value bounded by one; four equally weighted image corners give **√6**. The depth multiplier can increase it further. These scalar checks were executed independently.

This is a genuine range/normalization defect, **not proof that its ranking is useless**. For fixed image geometry, multiplying all scores by a positive constant leaves AUROC unchanged, and cancels in both a quantile gate and `S0/S`. Variable aspect ratios and depth factors need separate treatment.

The depth construction is less cosmetic: `r3` requires pose, and camera depth is `r3·P+t_z`, not merely `r3·P`. The latter depends on the world origin. Full lifted coordinates and a pose are not supplied consistently with the claimed pre-PnP stage. Optional “inflation” can also become deflation when `S>S0`.

The scientific premise is not equivalent to covariance trace: `diag(a,a)` and `diag(2a−ε,ε)` have equal trace but different minimum eigenvalues. This is a separating algebraic example, not evidence that the score beats hull area/full pose covariance. OASIS studies a Fisher matrix, not this exact coordinate covariance. [C:M02, S:M02, O3]

### Explicit new proposal: M02-v2

- **Remove** the depth multiplier, covariance inflation and `[0,1]` claim.
- Normalize coordinates by width and height independently. Compute weighted covariance with nonnegative weights and positive total weight; report `S2=√(12 λmin(C))` and effective sample count separately. Insufficient/invalid matches produce an explicit abstention.
- Test count-matched support subsets within fixed query/map cases. Compare count, residual, confidence, trace, hull area, full pose covariance and M09 sensitivity. Separate correctness-controlled subsets, where available for evaluation, from actual matcher failures.
- An incremental predictive null or absent paired support effect weakens this proxy/operational hypothesis; it does not disprove every geometric concentration mechanism.

This is an established cheap **control**. No corrected score or causal effect has been measured here. [O C.7]

## Deep audit 2 — M11: two reviewer errors and a more serious gain degeneracy

### 1. The residual space has 2N dimensions

For `J=J_pose ∈ R^(2N×6)`:

```text
P_perp = I − J J⁺
rank(P_perp) = 2N − rank(J).
```

`P_perp=0` requires full **row** rank. It can occur only if `2N≤6`, and is not guaranteed even then. For **N=4**, its rank is at least two; for N=6, at least six. The candidate's `N≤6` statement and the screener's endorsement are false.

An independent exact-rational pinhole calculation used `R=I,t=0,f=1,c=0` and points `(1,0,4),(0,1,5),(-1,-1,6),(2,-1,7)`. The 8×6 pose Jacobian has rank **6**; the residual projector has trace/rank **2**. Exact checks gave `P_perp²=P_perp` and `P_perp J=0`. This is a mathematical counterexample, not a dataset experiment.

### 2. A DCT restriction is ordinary composition

For sampled basis `B ∈ R^(N×K)` and coefficients `a`:

```text
dz = B a
db = −J⁺ J_z B a
r_remaining = P_perp J_z B a.
```

The per-point 6×N sensitivity becomes a 6×K mode sensitivity. There is no dimensional contradiction. The basis must still be normalized and checked for rank at the sampled locations. [C:M11, S:M11]

### 3. Constant height is a gauge for any scene/view

For world-vertical `e_z`:

```text
P_i' = P_i + h e_z
t'   = t − R h e_z
R P_i' + t' = R P_i + t
C' = −Rᵀ t' = C + h e_z.
```

Thus a uniform height offset can produce **h metres of camera-centre shift with zero residual**, not only on a flat nadir scene. For a full-rank unconstrained pose fit, a DCT basis containing DC generally makes the maximum bias-to-residual gain **infinite**. The result is a genuine non-identifiability, but not a scene-discriminating predictor. Rank deficiency, priors or fixed pose coordinates change the chosen solution/penalty and must be specified.

This independently confirms and extends the uniform-height reasoning in [A]. It also prevents treating a successful constant-offset test as evidence of a practically useful M11 score.

### Explicit new proposal: M11-v2

Fix inliers and a pose convention. **Separate DC as a gauge control.** For nonconstant modes report:

```text
A = −D_C J⁺ J_z B       # camera-centre response in metres
V = P_perp J_z B        # residual response in pixels
```

`D_C` differentiates camera centre with respect to the chosen pose coordinates; this avoids taking a meaningless norm across metres and degrees. If weighted fitting is used, whiten both Jacobians and residuals consistently.

Instead of an unbounded quotient, report per-mode bias/visibility and a declared bound:

```text
max ||A a|| subject to RMS(B a) ≤ h
                       ||V a||/√(2N) ≤ epsilon.
```

Fix `h,epsilon` before evaluation, report any exact null directions, and never disguise them with an unexplained denominator floor. DC is separately an `h`-metre gauge response.

**Useful M09 control:** at equal height RMS, compare modes with similar pose response but different residual visibility. Compare analytic and finite responses on the same modes, with fixed-inlier versus switching regimes separate. Horizontal map offsets, incorrect correspondences and concentrated support are competing controls—not presumed height errors.

Finite nonlinear solves can falsify the first-order approximation; identical linear simulations merely verify algebra. Supplying the injected error to the predictor tests **conditional response**, not a blind prediction of unknown real error. If only DC succeeds, the result is a gauge demonstration. No novelty or real-error attribution follows. [O2; O Table 6]

## Deep audit 3 — M12: ranking is valid; the causal test needs better controls

### 1. The omitted query-side CSLS term cannot change this ranking

```text
CSLS(q,g) = 2 cos(q,g) − r_q(q) − r_g(g).
```

For fixed `q`, `r_q(q)` is constant in `g`. Omitting it leaves gallery ordering unchanged. Example scores `[1.0,1.3,0.4]` become `[0.25,0.55,−0.35]` after subtracting 0.75: both rank `g2,g1,g3`. This is an algebra illustration, not observed descriptor evidence.

This argument does not justify shortened scores for cross-query thresholds or reverse rankings, where the omitted term may vary. The frozen proposal's reverse cosine rank is a separate diagnostic and is not inherently incompatible with tile hubness.

### 2. Uniform counts do not imply uniform correction

`N_k` counts neighborhood membership; `r_g` averages similarities. Uniform `N_k` does not imply constant `r_g`, so the proposed degenerate case “uniform hubness ⇒ unchanged CSLS ranking” is unsupported. Constant `r_g` would suffice. The undefined condition “A is large,” joint flag rule, tie handling and reference pool are genuine specification gaps.

### 3. Ten percent of tiles is not ten percent of query exposure

If the top-decile tiles receive **80% of all top-1 assignments**, and every assignment has the same 20% error probability, they also receive **80% of misses** without excess conditional failure risk. Hence the proposed 25% miss concentration against a 10% gallery baseline can pass for a trivial exposure reason.

Repeated views, true-location frequency, angle mix and gallery coverage can also inflate occurrence counts. Unlabeled test queries constitute **transduction**, not automatically label leakage; pool access must match the intended use.

### Explicit new proposal: M12-v2

- Use a declared unlabeled query reference pool; cross-fit/leave locations out where possible, and report a separate all-test-pool transductive arm.
- Fix `k`, pool composition, tie handling, and either define `A`'s cutoff or drop it.
- Compare cosine, true tile penalties, and **permuted tile penalties with the same marginal distribution**.
- Evaluate exposure-adjusted conditional miss risk and paired recall change, controlling location/view/angle multiplicity. Bootstrap by location.
- No exposure-adjusted risk and no advantage above matched penalty controls fails to support this operational explanation. A CSLS gain alone does not uniquely establish repetitive texture as the cause; a null CSLS gain alone does not disprove all forms of hubness.

The correction is known. The target-specific explanation remains testable and unknown. A different model/dataset is a different test, not ONLoc residual validation. [C:M12, S:M12, ON]

## Bottom line

The original review sometimes demanded an already-known cause before allowing a cause-discovery experiment, confused missing evidence with scientific insignificance, and accepted or introduced mathematical errors. It also correctly identified genuine specification and access problems.

**Keep the questions, not the unsupported claims:** M11-v2 for absorbed bias versus visible residual, M02-v2 for support versus correspondence/map failure, M12-v2 for exposure-adjusted retrieval hubness. Preserve the original shortlist and versions. None currently demonstrates valuable novelty, predictive benefit, or the cause of real-match failure.

Validation in this audit was limited to direct primary-passage checks, independently derived mathematics and standard-library exact/scalar calculations. No exhaustive novelty search, full archive-hash audit, current asset survey, or performance experiment was performed.
