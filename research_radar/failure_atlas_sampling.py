"""Audit confidence gating against upstream RoMa sampling on the SAME saved warps."""

import argparse
from types import SimpleNamespace
import time
import sys

import numpy as np

from .failure_atlas_run import OUT, HOME, read, save, digest, analyze


def prepare():
    if (OUT / "sampling-protocol.json").exists():
        raise RuntimeError("Sampling controls already frozen")
    source = HOME / "runtimes/crossview-roma/source/romatch/models/matcher.py"
    save(OUT / "sampling-protocol.json", {
        "hypothesis": "Our inherited certainty>=0.2 filtering may be a bottleneck rather than absence of useful pretrained predictions.",
        "scope": "Exploratory follow-up after the 36-pair baseline. No new inference, no GT-based threshold tuning.",
        "cases": read(OUT / "protocol.json")["cases"],
        "controls": {
            "roma-005": "Change only certainty minimum from0.2 to0.05; identical strongest-per64x64-cell policy and cap2048",
            "roma-official": "Pinned upstream RegressionMatcher.sample, threshold_balanced, sample_thresh0.05, num2048, torch.manual_seed731. These are native predictions; scores displayed are ORIGINAL certainty, not upstream sampling weights.",
        },
        "endpoint": "Retained count, support and accepted pose/horizontal error with unchanged geometry and solver; no correspondence-accuracy claim",
        "source": str(source), "source_sha256": digest(source), "implementation_sha256": digest(__file__),
        "limits": "Official sampler capped at2048 for CPU comparison, not full published-system benchmark reproduction. The two controls isolate threshold versus sampling-policy effects separately.",
    })


def threshold_ids(warp, certainty, threshold):
    flat, scores = warp.reshape(-1, 4), certainty.ravel()
    valid = np.isfinite(flat).all(1) & np.isfinite(scores) & (scores >= threshold) & (scores <= 1) & (flat >= -1).all(1) & (flat <= 1).all(1)
    ids = np.flatnonzero(valid)
    ids = ids[np.argsort(-scores[ids], kind="stable")]
    xy = np.minimum(((flat[ids, :2] + 1) * 32).astype(int), 63)
    _, first = np.unique(xy[:, 1] * 64 + xy[:, 0], return_index=True)
    return ids[np.sort(first)[:2048]]


def run():
    import torch

    protocol = read(OUT / "sampling-protocol.json")
    assert digest(__file__) == protocol["implementation_sha256"]
    assert digest(protocol["source"]) == protocol["source_sha256"]
    sys.path.insert(0, str(HOME / "runtimes/crossview-roma/source"))
    from romatch.models.matcher import RegressionMatcher

    torch.set_num_threads(4)
    started, cpu = time.monotonic(), time.process_time()
    outcomes = []
    for identifier in protocol["cases"]:
        folder = OUT / "cases" / identifier
        case = read(folder / "case.json")
        with np.load(folder / "roma-native.npz", allow_pickle=False) as data:
            warp, certainty = data["warp"], data["certainty"]
        native = read(folder / "roma.json")
        assert digest(folder / "roma-native.npz") == native["counts"]["native_sha256"]
        for method in protocol["controls"]:
            destination = folder / f"{method}.json"
            if destination.exists():
                raise RuntimeError("Control result exists; refusing silent overwrite")
            wall, process = time.monotonic(), time.process_time()
            if method == "roma-005":
                ids = threshold_ids(warp, certainty, .05)
            else:
                torch.manual_seed(731)
                sampled, _ = RegressionMatcher.sample(
                    SimpleNamespace(sample_mode="threshold_balanced", sample_thresh=.05),
                    torch.from_numpy(warp), torch.from_numpy(certainty), num=2048)
                sample = sampled.numpy()
                x = np.clip(np.rint((sample[:, 0] + 1) * warp.shape[1] / 2 - .5).astype(int), 0, warp.shape[1] - 1)
                y = np.clip(np.rint((sample[:, 1] + 1) * warp.shape[0] / 2 - .5).astype(int), 0, warp.shape[0] - 1)
                ids = y * warp.shape[1] + x
                assert np.allclose(sample, warp.reshape(-1, 4)[ids], atol=1e-6)
            points = warp.reshape(-1, 4)[ids].astype(float)
            valid = np.isfinite(points).all(1) & (points >= -1).all(1) & (points <= 1).all(1)
            ids, points = ids[valid], points[valid]
            q = (points[:, :2] + 1) / 2 * [case["query"]["width"], case["query"]["height"]] - .5
            t = (points[:, 2:] + 1) / 2 * [case["target"]["width"], case["target"]["height"]] - .5
            result = analyze(case, q, t, certainty.ravel()[ids], {
                "dense_lattice": certainty.size, "detected_query": None, "detected_target": None,
                "native_sha256": digest(folder / "roma-native.npz"),
            })
            result.update(method=method, case_id=identifier, device="cpu", gpu_hours=0,
                          cpu_seconds=time.process_time() - process, wall_seconds=time.monotonic() - wall,
                          confidence_semantics="Original native certainty, not thresholded sampling weights or calibrated probability",
                          protocol_sha256=digest(OUT / "sampling-protocol.json"), implementation_sha256=digest(__file__),
                          provenance=native["provenance"])
            save(destination, result)
            outcomes.append({"case_id": identifier, "method": method, "count": result["count"], "stage": result["stage"], "pose": result["pose"]})
            save(OUT / "sampling-partial.json", outcomes)
            print(method, identifier, result["count"], result["stage"], flush=True)
    save(OUT / "sampling-controls.json", {"protocol": protocol, "observations": outcomes,
                                         "cpu_seconds": time.process_time() - cpu, "wall_seconds": time.monotonic() - started,
                                         "gpu_hours": 0})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "run"])
    args = parser.parse_args()
    prepare() if args.command == "prepare" else run()
