"""Paired depth-provider intervention; never changes satellite images or matches."""

import argparse
import hashlib
import time

import cv2
import numpy as np

from .failure_atlas_run import OUT, HOME, read, save, solve, digest


def prepare():
    if (OUT / "depth-protocol.json").exists():
        raise RuntimeError("Depth intervention already frozen")
    root = HOME / "crossview/datasets/anyvisloc-expanded"
    manifest = read(root / "manifest.json")
    sources = []
    for row in manifest["maps"]:
        path = root / row["dsm"]["path"]
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        assert actual == row["dsm"]["sha256"]
        sources.append({"map": row["id"], "path": str(path), "sha256": actual,
                        "spacing_m": row["dsm"]["resolution"], "bytes": path.stat().st_size})
    save(OUT / "depth-protocol.json", {
        "hypothesis": "Coarse satellite depth, rather than only 2D matching, contributes to some AnyVisLoc pose failures. Finer aerial depth at the SAME local XY may change accepted pose and horizontal error.",
        "status": "Exploratory causal follow-up, frozen before depth-control outcomes; not a new method or novelty claim",
        "cases": [i for i in read(OUT / "protocol.json")["cases"] if i.startswith("any-")],
        "methods": ["roma", "sift", "orb"],
        "controls": "For each method, use identical q/map XY, K/dist and common valid DSM support. Cross satellite/aerial heights with P3P/EPNP. Never choose solver/depth by GT score.",
        "endpoint": "Counts accepted within10m, accepted above10m and unsolved; paired transitions by scene. No scene-generalization p-value.",
        "limits": ["Released SfM camera XY is not surveyed independent truth",
                   "Changing DSM changes provider, resolution and possibly acquisition epoch; improvement does not isolate resolution alone",
                   "No pixel correspondence GT; bad matches and missing view overlap remain competing explanations"],
        "sources": sources, "expanded_manifest_sha256": digest(root / "manifest.json"),
        "implementation_sha256": digest(__file__),
    })
    print("Depth intervention frozen; all six DSM source hashes verified.")


def run():
    from drone_loc.crossview_map_pose import _geometry, _lift

    protocol = read(OUT / "depth-protocol.json")
    if (OUT / "depth-controls.json").exists():
        raise RuntimeError("Depth results already retained; no silent rerun")
    assert digest(__file__) == protocol["implementation_sha256"]
    started, cpu = time.monotonic(), time.process_time()
    root = HOME / "crossview/datasets/anyvisloc-expanded"
    manifest = read(root / "manifest.json")
    assert digest(root / "manifest.json") == protocol["expanded_manifest_sha256"]
    output = []
    for identifier in protocol["cases"]:
        folder = OUT / "cases" / identifier
        case = read(folder / "case.json")
        original_root = HOME / "crossview/datasets/anyvisloc"
        satellite = _geometry(original_root, read(case["manifest"]), case["query"], case["map"])
        aerial_row = next(row for row in manifest["maps"] if row["scene_id"] == case["scene"] and row["reference_mode"] == "aerial")
        aerial = _geometry(root, manifest, case["query"], aerial_row)
        for method in protocol["methods"]:
            baseline = read(folder / f"{method}.json")
            q = np.array([m["q"] for m in baseline["matches"]]).reshape(-1, 2)
            t = np.array([m["t"] for m in baseline["matches"]]).reshape(-1, 2)
            xyz, valid_sat, _ = _lift(t + np.array(case["target"]["box"][:2]) + .5, satellite)
            aerial_pixels = (xyz[:, :2] - aerial["origin"]) / aerial["resolution"] + .5
            fine, valid_air, _ = _lift(aerial_pixels, aerial)
            valid = valid_sat & valid_air
            assert np.allclose(xyz[valid, :2], fine[valid, :2], rtol=0, atol=1e-8)
            results = {}
            for name, points in (("satellite", xyz[valid]), ("aerial", fine[valid])):
                for solver, flag in (("p3p", cv2.SOLVEPNP_P3P), ("epnp", cv2.SOLVEPNP_EPNP)):
                    results[f"{name}_{solver}"] = solve(
                        np.ascontiguousarray(points * [1, -1, 1]), np.ascontiguousarray(q[valid]),
                        satellite["K"], satellite["dist"], satellite["truth_xyz"], flag)[0]
            row = {"case_id": identifier, "method": method, "scene": case["scene"],
                   "original_matches": len(q), "common_valid_matches": int(valid.sum()),
                   "height_delta_quantiles_m": np.quantile(fine[valid, 2] - xyz[valid, 2], [0, .25, .5, .75, 1]).tolist() if valid.any() else [],
                   "satellite_height_range_m": float(np.ptp(xyz[valid, 2])) if valid.any() else None,
                   "aerial_height_range_m": float(np.ptp(fine[valid, 2])) if valid.any() else None,
                   "results": results, "baseline_sha256": digest(folder / f"{method}.json")}
            np.savez_compressed(folder / f"{method}-depth-inputs.npz", q=q[valid], satellite_xyz=xyz[valid],
                                aerial_xyz=fine[valid], K=satellite["K"], dist=satellite["dist"], truth=satellite["truth_xyz"])
            row["inputs_sha256"] = digest(folder / f"{method}-depth-inputs.npz")
            output.append(row)
            save(OUT / "depth-partial.json", output)
    save(OUT / "depth-controls.json", {"protocol": protocol, "observations": output,
                                     "cpu_seconds": time.process_time() - cpu, "wall_seconds": time.monotonic() - started,
                                     "gpu_hours": 0, "implementation_sha256": digest(__file__)})
    atlas = read(OUT / "atlas.json")
    atlas["depth_controls"] = output
    save(OUT / "atlas.json", atlas)
    print("Retained", len(output), "paired match sets, four depth/solver cells each.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "run"])
    args = parser.parse_args()
    prepare() if args.command == "prepare" else run()
