"""Reconcile and verify empirical atlas artifacts; optional replay on fresh output."""

import argparse
from collections import Counter
from pathlib import Path
import shutil
import time

import numpy as np
from PIL import Image

from .failure_atlas_run import OUT, read, save, digest, analyze

METHODS = ["sift", "orb", "roma", "roma-005", "roma-official"]


def publish():
    atlas = read(OUT / "atlas.json")
    counts = {}
    for case in atlas["cases"]:
        folder = OUT / "cases" / case["id"]
        case["methods"] = {}
        for method in METHODS:
            row = read(folder / f"{method}.json")
            case["methods"][method] = {k: v for k, v in row.items() if k != "matches"}
            counts.setdefault(case["dataset"] + "/" + method, Counter())[row["stage"]] += 1
        with np.load(folder / "roma-native.npz", allow_pickle=False) as archive:
            confidence = archive["certainty"]
        rgba = np.zeros((*confidence.shape, 4), dtype=np.uint8)
        rgba[:] = [243, 165, 175, 110]
        rgba[confidence >= .05] = [232, 195, 139, 110]
        rgba[confidence >= .20] = [131, 217, 224, 110]
        Image.fromarray(rgba).save(folder / "confidence.png")
    costs = []
    for name in ("execution-sift-orb.json", "execution-roma.json", "sampling-controls.json",
                 "depth-controls.json", "sampling-depth/depth-controls.json"):
        row = read(OUT / name)
        costs.append({"artifact": name, "cpu_seconds": row["cpu_seconds"], "wall_seconds": row["wall_seconds"]})
    atlas.update(counts=counts, complete=True, method_count=len(METHODS),
                 depth_controls=read(OUT / "depth-controls.json")["observations"] + read(OUT / "sampling-depth/depth-controls.json")["observations"],
                 supplemental_protocols={"sampling": read(OUT / "sampling-protocol.json"), "depth": read(OUT / "depth-protocol.json"),
                                         "sampling_depth": read(OUT / "sampling-depth/depth-protocol.json")},
                 costs={"timed_stages": costs, "cpu_seconds": sum(r["cpu_seconds"] for r in costs),
                        "wall_seconds": sum(r["wall_seconds"] for r in costs), "gpu_hours": 0,
                        "network_requests": 0, "new_dependencies": 0, "model_billing_usd": None,
                        "limit": "Measured experiment stages only; preparation, review, UI, verification and coordinator model usage are not included."},
                 updated_at=time.time())
    improved = next(c for c in atlas["cases"] if c["id"] == "any-l06_0425-satellite")
    old, new = improved["methods"]["roma"], improved["methods"]["roma-005"]
    wrong = counts["AnyVisLoc/roma-official"]["pose error above 10m"]
    atlas["findings"] = [
        {"title": "The confidence gate is a measured bottleneck",
         "observation": f"One unchanged pair goes from {old['count']} matches / no accepted pose to {new['count']} matches / {new['pose']['horizontal_error_m']:.2f} m XY error when the gate changes from0.20 to0.05. Not a cohort-wide fix.",
         "case_id": improved["id"], "method": "roma-005"},
        {"title": "An accepted pose can still be very wrong",
         "observation": f"Upstream RoMa sampling produces {wrong} accepted poses above10m error among12 AnyVisLoc pairs. More matches and RANSAC consensus are not accuracy certificates.",
         "case_id": "any-l04_0959-satellite", "method": "roma-official"},
        {"title": "Correct region is not metric localization",
         "observation": "All24 selected DenseUAV pairs retrieve the official matching identity, but none has verified metric depth and camera calibration in this subset.",
         "case_id": "dense-002385", "method": "roma"},
    ]
    save(OUT / "atlas.json", atlas)
    print("Published five conditions on36 pairs; paired depth outcomes and measured costs included.")


def verify():
    from .failure_atlas_sampling import threshold_ids

    atlas = read(OUT / "atlas.json")
    assert len(atlas["cases"]) == 36 and all(len(c["methods"]) == 5 for c in atlas["cases"])
    verified = 0
    for case in atlas["cases"]:
        folder = OUT / "cases" / case["id"]
        source = read(folder / "case.json")
        for side in ("query", "target"):
            assert digest(folder / f"{side}.png") == source[side + "_sha256"]
        with np.load(folder / "roma-native.npz", allow_pickle=False) as native:
            warp, certainty = native["warp"], native["certainty"]
        primary = read(folder / "roma.json")
        assert digest(folder / "roma-native.npz") == primary["counts"]["native_sha256"]
        ids = threshold_ids(warp, certainty, .2)
        points = warp.reshape(-1, 4)[ids].astype(float)
        q = (points[:, :2] + 1) / 2 * source["query"]["width"] - .5
        # Height has its own normalization for non-square original images.
        q[:, 1] = (points[:, 1] + 1) / 2 * source["query"]["height"] - .5
        recorded = np.array([m["q"] for m in primary["matches"]]).reshape(-1, 2)
        assert np.allclose(q, recorded, atol=1e-8), case["id"]
        for method in METHODS:
            result = read(folder / f"{method}.json")
            assert result["count"] == len(result["matches"])
            assert all(0 <= m["confidence"] <= 1 for m in result["matches"])
            assert result["point_accuracy"] is None
            assert result["gpu_hours"] == 0
            if not source["camera"]["metric_pose_supported"]:
                assert result["pose"]["horizontal_error_m"] is None
                assert result["pose"]["status"] == "unsupported"
            verified += 1
    reproduced = []
    for identifier in ("any-l06_0425-satellite", "any-l19_0001-satellite", "any-l04_0959-satellite"):
        folder = OUT / "cases" / identifier
        case = read(folder / "case.json")
        for method in ("roma", "roma-005", "roma-official"):
            recorded = read(folder / f"{method}.json")
            q = np.array([m["q"] for m in recorded["matches"]]).reshape(-1, 2)
            t = np.array([m["t"] for m in recorded["matches"]]).reshape(-1, 2)
            confidence = np.array([m["confidence"] for m in recorded["matches"]])
            repeated = analyze(case, q, t, confidence, recorded["counts"])
            assert repeated["pose"]["status"] == recorded["pose"]["status"]
            assert repeated["pose"]["inliers"] == recorded["pose"]["inliers"]
            a, b = repeated["pose"]["horizontal_error_m"], recorded["pose"]["horizontal_error_m"]
            assert a is None and b is None or a is not None and b is not None and abs(a - b) < 1e-8
            reproduced.append({"case": identifier, "method": method, "pose_status": repeated["pose"]["status"], "horizontal_error_m": a})
    receipt = {"passed": True, "method_case_records": verified, "source_pairs_verified": 36,
               "threshold_operator_reproduced": 36, "pose_outcomes_reproduced": reproduced,
               "scope": "Verification is not a new held-out experiment or proof of correspondence accuracy."}
    save(OUT / "verification.json", receipt)
    print("Verified180 records,36 frozen image pairs and36 threshold operators; reproduced9 successful/failed/wrong pose outcomes.")


def replay(destination):
    from . import failure_atlas_run as baseline, failure_atlas_sampling as sampling
    from . import failure_atlas_depth as depth, failure_atlas_followup as followup

    destination = destination.resolve()
    if destination.exists():
        raise RuntimeError("Replay requires a new output directory; original results are never overwritten")
    destination.mkdir(parents=True)
    shutil.copyfile(OUT / "protocol.json", destination / "protocol.json")
    for identifier in read(OUT / "protocol.json")["cases"]:
        folder = destination / "cases" / identifier
        folder.mkdir(parents=True)
        for name in ("case.json", "query.png", "target.png"):
            shutil.copyfile(OUT / "cases" / identifier / name, folder / name)
    for module in (baseline, sampling, depth, followup):
        module.OUT = destination
    baseline.summarize()
    baseline.run(["sift", "orb", "roma"])
    sampling.prepare()
    sampling.run()
    depth.prepare()
    depth.run()
    followup.main()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["publish", "verify", "replay"])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "replay":
        if not args.output:
            parser.error("replay requires --output pointing to a new directory")
        replay(args.output)
    else:
        publish() if args.command == "publish" else verify()
