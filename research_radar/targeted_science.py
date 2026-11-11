"""Bounded CPU research measurements on preserved real OrthoLoC imagery."""

import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "pilot/targeted-science"
DATA = ROOT.parent / "data/research-radar/iteration-sources"
cv2.setNumThreads(1)


def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    content = json.dumps(value, indent=2, allow_nan=False) + "\n"
    if path.exists() and path.read_text() != content:
        raise ValueError(f"Refusing to overwrite {path}")
    path.write_text(content)


def center(rvec, tvec):
    rotation = cv2.Rodrigues(rvec)[0]
    return (-rotation.T @ tvec.reshape(3, 1)).ravel()


def solve(points, pixels, camera, seed=731, fixed=None):
    cv2.setRNGSeed(int(seed))
    if len(points) < 6:
        return None
    if fixed is None:
        ok, r, t, inliers = cv2.solvePnPRansac(
            np.ascontiguousarray(points, dtype=np.float64),
            np.ascontiguousarray(pixels, dtype=np.float64), camera, None,
            iterationsCount=1000, reprojectionError=4.0, confidence=.999,
            flags=cv2.SOLVEPNP_EPNP)
        if not ok or inliers is None or len(inliers) < 6:
            return None
        indices = inliers.ravel()
    else:
        indices, r, t = fixed
        r, t = r.copy(), t.copy()
    r, t = cv2.solvePnPRefineLM(points[indices], pixels[indices], camera, None, r, t)
    projected = cv2.projectPoints(points, r, t, camera, None)[0].reshape(-1, 2)
    residuals = np.linalg.norm(projected - pixels, axis=1)
    return {"r": r, "t": t, "center": center(r, t), "inliers": indices,
            "residuals": residuals}


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "real-matching.json").exists():
        return
    start = time.process_time()
    rows = []
    for domain in ["samedomain", "crossdomain"]:
        path = DATA / f"ortholoc-{domain}.npz"
        with np.load(path, allow_pickle=False) as data:
            query, reference = data["image_query"], data["image_dop"]
            dsm, camera, truth = data["dsm"], data["intrinsics"].astype(float), data["extrinsics"].astype(float)
            sample_id = str(data["sample_id"])
        sift = cv2.SIFT_create(nfeatures=4000)
        qk, qd = sift.detectAndCompute(cv2.cvtColor(query, cv2.COLOR_RGB2GRAY), None)
        rk, rd = sift.detectAndCompute(cv2.cvtColor(reference, cv2.COLOR_RGB2GRAY), None)
        pairs = cv2.BFMatcher().knnMatch(qd, rd, k=2)
        accepted = [a for a, b in pairs if a.distance < .8 * b.distance]
        pixels = np.array([qk[m.queryIdx].pt for m in accepted], dtype=float)
        ref_pixels = np.array([rk[m.trainIdx].pt for m in accepted], dtype=float)
        xy = np.rint(ref_pixels).astype(int)
        points = dsm[xy[:, 1], xy[:, 0]].astype(float)
        finite = np.isfinite(points).all(axis=1)
        pixels, ref_pixels, points = pixels[finite], ref_pixels[finite], points[finite]
        solution = solve(points, pixels, camera)
        true_center = -truth[:, :3].T @ truth[:, 3]
        gt_projection = cv2.projectPoints(points, cv2.Rodrigues(truth[:, :3])[0], truth[:, 3], camera, None)[0].reshape(-1, 2)
        gt_residual = np.linalg.norm(gt_projection - pixels, axis=1)
        cache = OUT / f"matches-{domain}.npz"
        if cache.exists():
            raise ValueError("Existing correspondence cache; inspect before recovery")
        np.savez_compressed(cache, points=points, pixels=pixels, reference_pixels=ref_pixels,
                            camera=camera, truth=truth, gt_residual=gt_residual)
        rows.append({
            "domain": domain, "sample_id": sample_id, "input": str(path),
            "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "matches_sha256": hashlib.sha256(cache.read_bytes()).hexdigest(),
            "query_features": len(qk), "reference_features": len(rk),
            "ratio_matches": len(accepted), "finite_geometry_matches": len(points),
            "geometry_consistent_within_4px": int((gt_residual <= 4).sum()),
            "gt_pixel_residual_median": float(np.median(gt_residual)),
            "pose_solved": solution is not None,
            "inliers": len(solution["inliers"]) if solution else 0,
            "translation_error_m": float(np.linalg.norm(solution["center"] - true_center)) if solution else None,
            "inlier_reprojection_median_px": float(np.median(solution["residuals"][solution["inliers"]])) if solution else None,
        })
    save("real-matching.json", {
        "method": "Actual CPU SIFT nfeatures4000, one-way Lowe ratio0.8; nearest DSM grid lift; EPNP-RANSAC1000 iterations,4px,.999 then LM on consensus. No GT filtering.",
        "opencv": cv2.__version__, "numpy": np.__version__, "rows": rows,
        "cpu_seconds": time.process_time() - start, "gpu": False,
        "ground_truth_limit": "Nominal reconstruction-derived poses, not independent surveyed truth; true geometry used only to score retained matches/poses.",
    })
    print(json.dumps(rows, indent=2))


def modes(reference_pixels):
    x, y = (2 * reference_pixels / 1024 - 1).T
    raw = np.column_stack([np.ones(len(x)), x, y, x*x, x*y, y*y, np.sin(np.pi*x), np.sin(np.pi*y)])
    if np.linalg.matrix_rank(raw) < 8:
        raise ValueError("Perturbation basis is rank deficient")
    q, r = np.linalg.qr(raw)
    return q * np.sign(np.diag(r))[None, :] * np.sqrt(len(x))


def analytic(points, pixels, camera, current, basis):
    ids = current["inliers"]
    r, t = current["r"], current["t"]
    _, jac = cv2.projectPoints(points[ids], r, t, camera, None)
    j_pose = jac[:, :6]
    rotation = cv2.Rodrigues(r)[0]
    pc = points[ids] @ rotation.T + t.ravel()
    fx, fy = camera[0, 0], camera[1, 1]
    jz = np.column_stack([
        fx * (rotation[0, 2]*pc[:, 2] - pc[:, 0]*rotation[2, 2]) / pc[:, 2]**2,
        fy * (rotation[1, 2]*pc[:, 2] - pc[:, 1]*rotation[2, 2]) / pc[:, 2]**2])
    j_modes = (jz[:, :, None] * basis[ids, None, :]).reshape(-1, 8)
    pose_response = -np.linalg.lstsq(j_pose, j_modes, rcond=None)[0]
    theta = np.r_[r.ravel(), t.ravel()]
    dc = []
    for k in range(6):
        hi, lo = theta.copy(), theta.copy()
        hi[k] += 1e-6
        lo[k] -= 1e-6
        dc.append((center(hi[:3], hi[3:]) - center(lo[:3], lo[3:])) / 2e-6)
    return np.column_stack(dc) @ pose_response


def shifted(points, basis, coefficients):
    value = points.copy()
    value[:, 2] += basis @ coefficients
    return value


def experiment():
    resource.setrlimit(resource.RLIMIT_CPU, (600, 605))
    protocol = OUT / "m09-v2-protocol.json"
    if (OUT / "experiment-rows.jsonl").exists():
        raise ValueError("Existing experiment rows; do not overwrite or rerun selectively")
    start, wall = time.process_time(), time.monotonic()
    save("experiment-freeze.json", {
        "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(),
        "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "baseline_matching_sha256": hashlib.sha256((OUT / "real-matching.json").read_bytes()).hexdigest(),
        "started_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    })
    with np.load(OUT / "matches-samedomain.npz", allow_pickle=False) as data:
        points, pixels, camera, truth, rp = [data[k] for k in ("points", "pixels", "camera", "truth", "reference_pixels")]
    true_center = -truth[:, :3].T @ truth[:, 3]
    supports = {
        "all": np.arange(len(points)),
        "random55": np.sort(np.random.default_rng(17).choice(len(points), 55, replace=False)),
        "concentrated55": np.sort(np.argsort(np.linalg.norm(pixels - pixels.mean(axis=0), axis=1), kind="stable")[:55]),
    }
    derivative_checks = []
    for name, ids in supports.items():
        p, q, b = points[ids], pixels[ids], modes(rp[ids])
        current = solve(p, q, camera)
        if current is None:
            raise ValueError("Nominal support has no pose; protocol requires explicit revision, not silent replacement")
        repeated = solve(p, q, camera)
        assert np.allclose(current["center"], repeated["center"], atol=1e-10)
        predicted = analytic(p, q, camera, current, b)
        actual = []
        fixed = (current["inliers"], current["r"], current["t"])
        for k in range(8):
            step = np.eye(8)[k] * .001
            hi, lo = solve(shifted(p, b, step), q, camera, fixed=fixed), solve(shifted(p, b, -step), q, camera, fixed=fixed)
            actual.append((hi["center"] - lo["center"]) / .002)
        actual = np.column_stack(actual)
        rel = float(np.linalg.norm(actual - predicted) / max(np.linalg.norm(actual), 1e-12))
        derivative_checks.append({"support": name, "relative_derivative_difference": rel,
                                  "maximum_absolute_difference": float(abs(actual - predicted).max())})
    save("derivative-checks.json", {"checks": derivative_checks,
                                   "limit": "Gauss-Newton derivative omits residual-weighted second derivatives; discrepancy is retained, not silently retuned."})
    rows = []
    for draw in range(8):
        z = np.random.default_rng(9100 + draw).normal(size=8)
        mc = np.random.default_rng(4200 + draw).normal(size=(16, 8))
        mc /= np.linalg.norm(mc, axis=1, keepdims=True)
        for name, ids in supports.items():
            p, q, b = points[ids], pixels[ids], modes(rp[ids])
            for amplitude in [0, .25, .5, 1, 2]:
                if time.process_time() - start > 480:
                    save("experiment-stop.json", {"reason": "Soft CPU cap", "completed": len(rows)})
                    return
                p_current = shifted(p, b, amplitude * z / np.sqrt(8))
                current = solve(p_current, q, camera)
                row = {"draw": draw, "support": name, "amplitude": amplitude, "solved": current is not None}
                if current is None:
                    row.update(failure=True, translation_error_m=None, scores=None)
                else:
                    fixed = (current["inliers"], current["r"], current["t"])
                    score_a = float(np.linalg.norm(analytic(p_current, q, camera, current, b), axis=0).max())
                    scores = {"analytic": score_a, "negative_inlier_fraction": -len(current["inliers"])/len(p),
                              "residual": float(np.median(current["residuals"][current["inliers"]]))}
                    displacements = {"finite_fixed": [], "finite_full": [], "switch_excess": [], "monte_carlo": [], "seed_spread": []}
                    fails = {k: 0 for k in displacements}
                    switches, no_switch_excess = [], []
                    for k in range(8):
                        for sign in [-1, 1]:
                            new_points = shifted(p_current, b, sign * np.eye(8)[k])
                            full, constrained = solve(new_points, q, camera), solve(new_points, q, camera, fixed=fixed)
                            for key, result in [("finite_full", full), ("finite_fixed", constrained)]:
                                if result is None:
                                    fails[key] += 1
                                else:
                                    displacements[key].append(float(np.linalg.norm(result["center"] - current["center"])))
                            if full is None or constrained is None:
                                fails["switch_excess"] += 1
                            else:
                                a, c = set(current["inliers"]), set(full["inliers"])
                                switching = 1 - len(a & c)/len(a | c)
                                excess = float(np.linalg.norm(full["center"] - constrained["center"]))
                                switches.append(switching)
                                displacements["switch_excess"].append(excess)
                                if switching == 0:
                                    no_switch_excess.append(excess)
                    for direction in mc:
                        result = solve(shifted(p_current, b, direction), q, camera)
                        if result is None:
                            fails["monte_carlo"] += 1
                        else:
                            displacements["monte_carlo"].append(float(np.linalg.norm(result["center"] - current["center"])))
                    for seed in [732, 733]:
                        result = solve(p_current, q, camera, seed=seed)
                        if result is None:
                            fails["seed_spread"] += 1
                        else:
                            displacements["seed_spread"].append(float(np.linalg.norm(result["center"] - current["center"])))
                    for key in displacements:
                        scores[key] = None if fails[key] else max(displacements[key], default=0.0)
                    te = float(np.linalg.norm(current["center"] - true_center))
                    rot = cv2.Rodrigues(current["r"])[0]
                    re = float(np.degrees(np.arccos(np.clip((np.trace(rot @ truth[:, :3].T)-1)/2, -1, 1))))
                    depth = (p_current @ rot.T + current["t"].ravel())[:, 2]
                    row.update(failure=te > 1, translation_error_m=te, rotation_error_deg=re,
                               scores=scores, probe_failures=fails, mean_consensus_change=float(np.mean(switches)) if switches else None,
                               max_zero_switch_excess=max(no_switch_excess, default=None),
                               positive_depth_fraction=float(np.mean(depth > 0)))
                rows.append(row)
                with (OUT / "experiment-rows.jsonl").open("a") as stream:
                    stream.write(json.dumps(row, allow_nan=False) + "\n")
        print("Completed draw", draw, "trials", len(rows), flush=True)
    save("experiment-execution.json", {
        "completed_trials": len(rows), "cpu_seconds": time.process_time() - start,
        "wall_seconds": time.monotonic() - wall, "gpu": False, "training": False,
        "full_solver_probe_attempts": sum(r["solved"] for r in rows) * 34,
        "scope": "Actual real-image correspondences; controlled synthetic map corruption; one solvable scene. Failed cross-domain baseline remains excluded explicitly.",
    })


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "experiment":
        experiment()
    else:
        prepare()
