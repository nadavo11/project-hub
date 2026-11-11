"""Bounded, CPU-only failure analysis. No training or opportunity generation."""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
import time

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

import cv2
import numpy as np
from PIL import Image

from .core import DEFAULT_HOME

LOCAL = Path("/home/nadavo/localization-models")
HOME = LOCAL / "data/workbench"
OUT = DEFAULT_HOME / "failure-atlas"
sys.path.insert(0, str(LOCAL))
cv2.setNumThreads(1)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def prepare():
    from drone_loc.crossview_map_pair import map_candidate

    if (OUT / "protocol.json").exists():
        raise RuntimeError("Cohort already frozen; use run to resume it")
    cases = []
    root = HOME / "crossview/datasets/denseuav-eval"
    manifest = read(root / "manifest.json")
    images = {r["id"]: r for r in manifest["images"]}
    retrieval_path = LOCAL / "data/validation/crossview/denseuav-48-review/infogeo-pass-1.json"
    retrieval = {r["id"]: r for r in read(retrieval_path)["result"]["queries"]}
    identities = manifest["protocol"]["selected_identities"][::2]
    for i, identity in enumerate(identities):
        query = images[f"drone-{identity}-H{[80, 90, 100][i % 3]}"]
        result = retrieval[query["id"]]
        target = images[result["candidates"][0]["id"]]
        cases.append({
            "id": f"dense-{identity}", "dataset": "DenseUAV", "group": "retrieved",
            "scene": identity, "query": query, "target": target,
            "query_path": str(root / query["path"]), "target_path": str(root / target["path"]),
            "geography": {
                "status": "identity verified" if query["identity"] == target["identity"] else "retrieval mismatch",
                "evidence": "Official same-identity relevance labels, original member paths and image SHA256",
                "gt_rank": result["gt_rank"], "retrieval_source": str(retrieval_path),
                "retrieval_sha256": digest(retrieval_path),
                "pixel_ground_truth": False,
            },
            "camera": {"metric_pose_supported": False, "reason": "No verified intrinsics, distortion, depth/DSM or metric pixel-to-world transform in this captured subset. Altitude labels are not depth."},
            "manifest": str(root / "manifest.json"), "manifest_sha256": digest(root / "manifest.json"),
        })
    root = HOME / "crossview/datasets/anyvisloc"
    manifest = read(root / "manifest.json")
    images = {r["id"]: r for r in manifest["images"]}
    jobs = {}
    for path in sorted((HOME / "crossview/jobs").glob("*/job.json")):
        job = read(path)
        config = job.get("config", {})
        if (job["status"] == "completed" and config.get("dataset_id") == "anyvisloc"
                and config.get("method") == "infogeo" and config.get("mode") == "map"
                and len(config.get("query_ids", [])) == 16):
            jobs.setdefault(config["map_id"], path.parent)
    for map_row in manifest["maps"]:
        if map_row["reference_mode"] != "satellite":
            continue
        job_root = jobs[map_row["id"]]
        queries = sorted(read(job_root / "result.json")["queries"], key=lambda r: r["id"])
        for index in (0, 5, 10, 15):
            result = queries[index]
            query = images[result["id"]]
            config = {"dataset_id": "anyvisloc", "query_id": query["id"],
                      "candidate_id": result["candidates"][0]["id"], "map_job_id": job_root.name}
            target, path, _ = map_candidate(HOME, config)
            cases.append({
                "id": "any-" + query["id"].lower(), "dataset": "AnyVisLoc", "group": "retrieved",
                "scene": query["scene_id"], "query": query, "target": target,
                "query_path": str(root / query["path"]), "target_path": str(path),
                "geography": {
                    "status": "scene verified; crop overlap unresolved",
                    "evidence": "Same released scene/map, exact retrieved crop and source hashes. Camera position inside a crop is NOT proof of view overlap.",
                    "gt_rank": result["gt_rank"], "retrieval_source": str(job_root / "result.json"),
                    "retrieval_sha256": digest(job_root / "result.json"),
                    "pixel_ground_truth": False,
                },
                "camera": {"metric_pose_supported": True, **query["camera"]},
                "map": map_row, "config": config,
                "manifest": str(root / "manifest.json"), "manifest_sha256": digest(root / "manifest.json"),
            })
    for case in cases:
        folder = OUT / "cases" / case["id"]
        folder.mkdir(parents=True, exist_ok=True)
        for side in ("query", "target"):
            source = Path(case[side + "_path"])
            assert digest(source) == case[side]["sha256"], source
            with Image.open(source) as image:
                image.convert("RGB").save(folder / f"{side}.png")
            case[side + "_sha256"] = digest(folder / f"{side}.png")
        case["point_ground_truth"] = "Unavailable. Homography/PnP inliers measure self-consistency, not correct correspondences."
        save(folder / "case.json", case)
    protocol = {
        "id": "failure-first-v1", "cases": [c["id"] for c in cases],
        "selection": "24 of 48 sorted DenseUAV identities, every second identity, cyclic H80/H90/H100; actual InfoGeo top1. AnyVisLoc satellite: four sorted queries at indices 0,5,10,15 in each of three scenes; actual InfoGeo top1. No matching-outcome selection.",
        "scope": "36 pairs, 24 DenseUAV identities and 12 AnyVisLoc frames from 3 scenes; not a population or held-out SOTA benchmark. No pixel GT.",
        "methods": ["sift", "orb", "roma"],
        "sparse": {"features": 4000, "ratio": 0.8, "mutual": True, "resolution": "original"},
        "roma": {"coarse_res": 560, "upsample_res": 640, "symmetric": False,
                 "use_custom_corr": False, "upsample_preds": True, "with_padding": False,
                 "do_compile": False, "min_certainty": 0.2, "sampling": "strongest per 64x64 source cell, cap2048"},
        "homography": {"threshold_target_px": 4, "iterations": 2000, "confidence": 0.999},
        "pnp": {"threshold_query_px": 8, "iterations": 2000, "confidence": 0.999,
                "min_positive_depth_inliers": 12, "default": "P3P", "seed": 731,
                "world": "AnyVisLoc [local_x,-local_y,local_z]; image pixel-index centers"},
        "controls": ["EPNP on identical matches", "zero distortion", "focal length times0.8", "focal length times1.2", "constant median DSM height"],
        "interpretation": "Control interventions measure sensitivity, not which camera assumption is true. Do not select the best assumption by GT error.",
        "compute": {"device": "cpu", "torch_threads": 4, "max_wall_seconds": 3600, "max_cpu_seconds": 7200, "network_requests": 0},
    }
    save(OUT / "protocol.json", protocol)
    summarize()
    print("Frozen", len(cases), "real pairs", flush=True)


def coverage(points, size):
    if not len(points):
        return {"hull_fraction": 0.0, "occupied_grid_fraction": 0.0, "axis_ratio": 0.0}
    normalized = np.asarray(points, np.float32) / np.asarray(size)
    hull = cv2.contourArea(cv2.convexHull(normalized.astype(np.float32))) if len(points) >= 3 else 0
    cells = np.clip((normalized * 8).astype(int), 0, 7)
    s = np.linalg.svd(normalized - normalized.mean(0), compute_uv=False)
    return {"hull_fraction": float(hull), "occupied_grid_fraction": len(np.unique(cells, axis=0)) / 64,
            "axis_ratio": float(s[-1] / s[0]) if s[0] > 0 else 0.0}


def sparse(query, target, method):
    detector = cv2.SIFT_create(nfeatures=4000) if method == "sift" else cv2.ORB_create(nfeatures=4000)
    a, da = detector.detectAndCompute(cv2.cvtColor(query, cv2.COLOR_RGB2GRAY), None)
    b, db = detector.detectAndCompute(cv2.cvtColor(target, cv2.COLOR_RGB2GRAY), None)
    if da is None or db is None or min(len(a), len(b)) < 2:
        return np.empty((0, 2)), np.empty((0, 2)), np.empty(0), {"detected_query": len(a), "detected_target": len(b), "ratio_pass": 0}
    matcher = cv2.BFMatcher(cv2.NORM_L2 if method == "sift" else cv2.NORM_HAMMING)
    forward = matcher.knnMatch(da, db, k=2)
    reverse = matcher.match(db, da)
    passed = [m[0] for m in forward if len(m) == 2 and m[0].distance < 0.8 * m[1].distance]
    selected = [m for m in passed if reverse[m.trainIdx].trainIdx == m.queryIdx]
    confidence = {m[0].queryIdx: 1 - m[0].distance / max(m[1].distance, 1e-12) for m in forward if len(m) == 2}
    return (np.array([a[m.queryIdx].pt for m in selected]).reshape(-1, 2),
            np.array([b[m.trainIdx].pt for m in selected]).reshape(-1, 2),
            np.array([confidence[m.queryIdx] for m in selected]),
            {"detected_query": len(a), "detected_target": len(b), "ratio_pass": len(passed)})


def solve(points, pixels, K, dist, truth, flag=cv2.SOLVEPNP_P3P):
    result = {"status": "unsolved", "inliers": 0, "horizontal_error_m": None,
              "residual_median_px": None, "center": None}
    if len(points) < 12:
        return result, np.zeros(len(points), bool), np.full(len(points), np.nan)
    cv2.setRNGSeed(731)
    try:
        ok, r, t, ids = cv2.solvePnPRansac(
            np.ascontiguousarray(points, dtype=np.float64), np.ascontiguousarray(pixels, dtype=np.float64),
            K, dist, flags=flag, iterationsCount=2000, reprojectionError=8, confidence=0.999)
        if not ok or ids is None:
            return result, np.zeros(len(points), bool), np.full(len(points), np.nan)
        projected = cv2.projectPoints(points, r, t, K, dist)[0].reshape(-1, 2)
        errors = np.linalg.norm(projected - pixels, axis=1)
        R = cv2.Rodrigues(r)[0]
        positive = ((R @ points.T).T + t.ravel())[:, 2] > 1e-8
        mask = (errors <= 8) & positive & np.isfinite(errors)
        center = (-R.T @ t).ravel() * [1, -1, 1]
        result.update(status="estimated" if mask.sum() >= 12 else "insufficient inliers",
                      inliers=int(mask.sum()), ransac_inliers=len(ids), positive_depth_fraction=float(positive.mean()),
                      center=center.tolist(), rvec=r.ravel().tolist(), tvec=t.ravel().tolist(),
                      residual_median_px=float(np.median(errors[mask])) if mask.any() else None)
        if result["status"] == "estimated" and truth is not None:
            result["horizontal_error_m"] = float(np.linalg.norm(center[:2] - truth[:2]))
        return result, mask, errors
    except cv2.error as error:
        result["error"] = str(error)
        return result, np.zeros(len(points), bool), np.full(len(points), np.nan)


def analyze(case, q, t, confidence, counts):
    from drone_loc.crossview_map_pose import _geometry, _lift

    n = len(q)
    result = {"count": n, "counts": counts, "query_coverage": coverage(q, [case["query"]["width"], case["query"]["height"]]),
              "target_coverage": coverage(t, [case["target"]["width"], case["target"]["height"]]),
              "confidence_quantiles": np.quantile(confidence, [0, .25, .5, .75, 1]).tolist() if n else [],
              "point_accuracy": None, "point_accuracy_reason": case["point_ground_truth"]}
    hmask = np.zeros(n, bool)
    herror = np.full(n, np.nan)
    result["homography"] = {"status": "insufficient matches", "inliers": 0}
    if n >= 4:
        cv2.setRNGSeed(731)
        H, mask = cv2.findHomography(q, t, cv2.RANSAC, 4, maxIters=2000, confidence=.999)
        if H is not None:
            prediction = cv2.perspectiveTransform(q.reshape(-1, 1, 2), H).reshape(-1, 2)
            herror = np.linalg.norm(prediction - t, axis=1)
            hmask = np.isfinite(herror) & (herror <= 4)
            result["homography"] = {"status": "estimated", "inliers": int(hmask.sum()),
                                    "inlier_fraction": float(hmask.mean()), "matrix": H.tolist(),
                                    "median_inlier_residual_px": float(np.median(herror[hmask])) if hmask.any() else None,
                                    "meaning": "Target-pixel self-consistency, not correspondence GT or metric pose"}
    pmask = np.zeros(n, bool)
    perror = np.full(n, np.nan)
    result["pose"] = {"status": "unsupported", "horizontal_error_m": None,
                      "reason": case["camera"].get("reason")}
    result["controls"] = {}
    if case["camera"]["metric_pose_supported"]:
        root = Path(case["manifest"]).parent
        geometry = _geometry(root, read(case["manifest"]), case["query"], case["map"])
        world, valid, lift_counts = _lift(t + np.array(case["target"]["box"][:2]) + .5, geometry)
        result["depth"] = {"valid": int(valid.sum()), **lift_counts, "dsm_resolution_m": geometry["dsm_resolution"].tolist()}
        points = np.ascontiguousarray(world[valid] * [1, -1, 1])
        pixels = np.ascontiguousarray(q[valid])
        if len(points) >= 3:
            singular = np.linalg.svd(points - points.mean(0), compute_uv=False)
            result["geometry"] = {"singular_values_m": singular.tolist(),
                                  "axis_ratio": float(singular[1] / max(singular[0], 1e-12)),
                                  "planarity_ratio": float(singular[-1] / max(singular[0], 1e-12)),
                                  "note": "Planarity alone does not make calibrated PnP impossible"}
        K, dist, truth = geometry["K"], geometry["dist"], geometry["truth_xyz"]
        result["pose"], local_mask, local_error = solve(points, pixels, K, dist, truth)
        pmask[valid], perror[valid] = local_mask, local_error
        for name in ("epnp", "zero_distortion", "focal_0.8", "focal_1.2", "flat_dsm"):
            k, d, p = K.copy(), dist.copy(), points.copy()
            if name == "zero_distortion":
                d *= 0
            if name.startswith("focal_"):
                k[0, 0] *= float(name.split("_")[1])
                k[1, 1] *= float(name.split("_")[1])
            if name == "flat_dsm" and len(p):
                p[:, 2] = np.median(p[:, 2])
            result["controls"][name] = solve(p, pixels, k, d, truth, cv2.SOLVEPNP_EPNP if name == "epnp" else cv2.SOLVEPNP_P3P)[0]
    if case["geography"]["status"] == "retrieval mismatch":
        stage = "retrieval mismatch"
    elif n < 12:
        stage = "insufficient matches"
    elif result["query_coverage"]["axis_ratio"] < .001 or result["target_coverage"]["axis_ratio"] < .001:
        stage = "spatial degeneracy"
    elif result["pose"]["status"] == "unsupported":
        stage = "missing metric geometry"
    elif result["pose"]["status"] != "estimated":
        stage = "pose unsolved"
    elif result["pose"]["horizontal_error_m"] is None:
        stage = "pose accuracy unknown"
    elif result["pose"]["horizontal_error_m"] > 10:
        stage = "pose error above 10m"
    else:
        stage = "horizontal error within 10m"
    result["stage"] = stage
    result["causal_status"] = "Observed stage, not a unique causal attribution. Missing point GT prevents identifying wrong matches from residuals alone."
    result["matches"] = [{"q": a.tolist(), "t": b.tolist(), "confidence": float(c),
                          "h_inlier": bool(hi), "h_residual": float(he) if np.isfinite(he) else None,
                          "p_inlier": bool(pi), "p_residual": float(pe) if np.isfinite(pe) else None}
                         for a, b, c, hi, he, pi, pe in zip(q, t, confidence, hmask, herror, pmask, perror)]
    return result


def roma_model():
    import torch
    from drone_loc.crossview_roma import _runtime, PROCESSING

    root, provenance = _runtime(HOME)
    sys.path.insert(0, str(root / "source"))
    import romatch

    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.manual_seed(731)
    weights = torch.load(root / "checkpoints/roma_outdoor.pth", map_location="cpu", weights_only=True)
    backbone = torch.load(root / "checkpoints/dinov2_vitl14_pretrain.pth", map_location="cpu", weights_only=True)
    model = romatch.roma_outdoor(device="cpu", weights=weights, dinov2_weights=backbone, **PROCESSING).eval()
    return model, {"source_commit": provenance["source_commit"], "checkpoint_sha256": provenance["checkpoint_sha256"],
                   "backbone_sha256": provenance["backbone_sha256"], "torch": torch.__version__, "processing": PROCESSING}


def run(methods):
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (7200, 7210))
    protocol = read(OUT / "protocol.json")
    started, cpu = time.monotonic(), time.process_time()
    model = None
    provenance = {}
    for method in methods:
        for identifier in protocol["cases"]:
            folder = OUT / "cases" / identifier
            destination = folder / f"{method}.json"
            if destination.exists():
                continue
            if time.monotonic() - started > 3600:
                raise TimeoutError("Frozen wall budget exhausted; retained results are resumable")
            case = read(folder / "case.json")
            for side in ("query", "target"):
                assert digest(folder / f"{side}.png") == case[side + "_sha256"]
            query, target = np.array(Image.open(folder / "query.png")), np.array(Image.open(folder / "target.png"))
            wall, process = time.monotonic(), time.process_time()
            try:
                if method != "roma":
                    q, t, confidence, counts = sparse(query, target, method)
                else:
                    import torch
                    from drone_loc.crossview_map_pose import _select
                    if model is None:
                        model, provenance = roma_model()
                    with torch.inference_mode():
                        warp, cert = model.match(Image.fromarray(query), Image.fromarray(target), device="cpu")
                    warp, cert = warp[0].float().cpu().numpy(), cert[0].float().cpu().numpy()
                    np.savez_compressed(folder / "roma-native.npz", warp=warp, certainty=cert)
                    ids, eligible = _select(warp, cert)
                    points = warp.reshape(-1, 4)[ids]
                    q = (points[:, :2].astype(float) + 1) / 2 * [query.shape[1], query.shape[0]] - .5
                    t = (points[:, 2:].astype(float) + 1) / 2 * [target.shape[1], target.shape[0]] - .5
                    confidence = cert.reshape(-1)[ids]
                    counts = {"dense_lattice": cert.size, "certainty_eligible": eligible,
                              "detected_query": None, "detected_target": None, "native_sha256": digest(folder / "roma-native.npz")}
                result = analyze(case, q, t, confidence, counts)
                result.update(method=method, case_id=identifier, device="cpu", gpu_hours=0,
                              cpu_seconds=time.process_time() - process, wall_seconds=time.monotonic() - wall,
                              opencv=cv2.__version__, numpy=np.__version__, provenance=provenance if method == "roma" else {},
                              implementation_sha256=digest(__file__), protocol_sha256=digest(OUT / "protocol.json"),
                              confidence_semantics="Native RoMa certainty, not calibrated probability" if method == "roma" else "1 - nearest/second descriptor distance ratio; not calibrated probability")
                save(destination, result)
            except Exception as error:
                save(folder / f"{method}-error.json", {"error": repr(error), "cpu_seconds": time.process_time() - process,
                                                      "wall_seconds": time.monotonic() - wall, "implementation_sha256": digest(__file__)})
                raise
            summarize()
            print(method, identifier, result["count"], result["stage"], flush=True)
    save(OUT / ("execution-" + "-".join(methods) + ".json"),
         {"cpu_seconds": time.process_time() - cpu, "wall_seconds": time.monotonic() - started,
          "device": "cpu", "gpu_hours": 0, "methods": methods, "implementation_sha256": digest(__file__)})


def summarize():
    protocol = read(OUT / "protocol.json")
    rows = []
    groups = {}
    for identifier in protocol["cases"]:
        folder = OUT / "cases" / identifier
        case = read(folder / "case.json")
        methods = {}
        for method in protocol["methods"]:
            if (folder / f"{method}.json").exists():
                result = read(folder / f"{method}.json")
                methods[method] = {k: v for k, v in result.items() if k != "matches"}
                key = case["dataset"] + "/" + method
                groups.setdefault(key, Counter())[result["stage"]] += 1
        rows.append({"id": identifier, "dataset": case["dataset"], "scene": case["scene"],
                     "query_id": case["query"]["id"], "target_id": case["target"]["id"],
                     "query_size": [case["query"]["width"], case["query"]["height"]],
                     "target_size": [case["target"]["width"], case["target"]["height"]],
                     "geography": case["geography"], "camera": case["camera"], "methods": methods})
    save(OUT / "atlas.json", {"protocol": protocol, "cases": rows, "counts": groups,
                             "complete": all(len(r["methods"]) == 3 for r in rows),
                             "updated_at": time.time(),
                             "warning": "Inliers are model self-consistency, not correspondence ground truth. Report frequencies by dataset and method; no scene-generalization claim."})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "run", "summarize"])
    parser.add_argument("--methods", nargs="+", choices=["sift", "orb", "roma"], default=["sift", "orb", "roma"])
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    OUT = args.output.resolve()
    if args.command == "prepare":
        prepare()
    elif args.command == "run":
        run(args.methods)
    else:
        summarize()
