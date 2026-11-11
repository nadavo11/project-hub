"""Publish the bounded PointMatch attribution measurements, without starting agents."""

import argparse
import hashlib
import json
import mimetypes
from pathlib import Path

from .archive import Archive
from .core import DEFAULT_HOME, ROOT, Store
from .iteration import save


CAMPAIGN = "campaign-16abc539e9ed"
POINTMATCH = Path("/home/nadavo/pointmatch-atlas")
RESULTS = POINTMATCH / "results/radar-attribution"
REPORT = ROOT / "pilot/attribution/scientific-report.md"


def read(path):
    return json.loads(path.read_text())


def publish(documentation):
    store = Store()
    campaign = store.campaign(CAMPAIGN)
    if campaign["status"] != "paused" or campaign["config"]["agent_enabled"]:
        raise ValueError("The scientific-generation pause must remain in force")
    if store.find_record("opportunities", "M09", CAMPAIGN)["status"] != "rejected":
        raise ValueError("M09 must remain stopped")
    result, protocol = read(RESULTS / "results.json"), read(RESULTS / "protocol.json")
    packet = read(RESULTS / "review-packet.json")
    for name in ("numeric-verification.json", "browser-render-verification.json"):
        if not read(RESULTS / name)["passed"]:
            raise ValueError("Verification has not passed")
    files = [p for p in RESULTS.rglob("*") if p.is_file()]
    files += [
        REPORT, Path(__file__), POINTMATCH / "atlas/campaigns/radar_attribution.py",
        POINTMATCH / "scripts/verify_radar_attribution.py",
        POINTMATCH / "tests/test_radar_attribution.py", POINTMATCH / "frontend/app.js",
        ROOT / "static/app.js", ROOT / "test_ui.py",
    ]
    files += [Path(row["path"]) for row in protocol["sources"]]
    wanted = {row["pair_id"] for row in packet["pairs"]}
    pairs = [p for p in read(POINTMATCH / "data/custom_pairs.json") if p["id"] in wanted]
    if len(pairs) != 12:
        raise ValueError("PointMatch review cohort is incomplete")
    for pair in pairs:
        files += [Path(pair["image0"]), Path(pair["image1"])]
    save("pointmatch-pairs.json", pairs, directory=REPORT.parent)
    files.append(REPORT.parent / "pointmatch-pairs.json")
    documentation_urls = {
        "pose-rejection-opencv411.md":
            "https://raw.githubusercontent.com/opencv/opencv/4.11.0/modules/calib3d/doc/solvePnP.markdown",
        "pose-rejection-usac411.md":
            "https://raw.githubusercontent.com/opencv/opencv/4.11.0/doc/tutorials/calib3d/usac.markdown",
    }
    files += [documentation / name for name in documentation_urls]
    archive, references = Archive(DEFAULT_HOME / "archive"), []
    for path in sorted(set(files)):
        content = path.read_bytes()
        reference = archive.store_bytes(
            content, url=documentation_urls.get(path.name, path.as_uri()),
            media_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            retrieved_at=None, representation="artifact",
            provenance={"study": protocol["id"], "integrity_is_not_scientific_validation": True},
        )
        archive.verify_manifest(reference.manifest_sha256)
        references.append({"path": str(path), **reference.to_dict()})
    preservation = {
        "files": references, "artifact_count": len(references),
        "total_bytes": sum(row["size"] for row in references),
    }
    save("preservation.json", preservation, directory=REPORT.parent)
    cases = []
    for pair in packet["pairs"]:
        identifier = pair["case_id"]
        cases.append({
            "title": identifier, "status": "measured; annotations blocked",
            "expected": "Distinguish accepted pose from <=10m horizontal accuracy; "
                        "independent landmark review required before matcher attribution.",
            "observed": {
                name: metrics["errors_m"][identifier]
                for name, metrics in result["solver_comparison"].items()
            },
            "evidence": {"url": pair["url"], "label": "Open original pair in PointMatch Atlas"},
        })
    record = store.put(CAMPAIGN, "validations", {
        "id": "pointmatch-attribution-v1", "title": "Attribution gate: frozen matches, honest rejection",
        "verdict": "ITERATE",
        "summary": "Fixed P3P/USAC-MAGSAC agreement rejects9/10 wrong primary poses and retains1/1 "
                   "<=10m case; one935.82m false acceptance remains. Independent labels and "
                   "prospective scene validation are still missing.",
        "expected": "Independent correspondence truth, scene-held-out rejection, and evidence "
                    "distinguishing matching, overlap, geometry and estimator failures.",
        "observed": result, "cases": cases,
        "evidence": {
            "PointMatch measurements": str(RESULTS),
            "scientific_report": str(REPORT),
            "report_sha256": hashlib.sha256(REPORT.read_bytes()).hexdigest(),
            "preservation": str(REPORT.parent / "preservation.json"),
            "artifacts_verified": len(references),
        },
        "failures": [
            "No independently checked landmarks or overlap labels: confidence correctness unmeasured.",
            "Holding out Scene_19 leaves zero accurate accepted training cases; calibration abstains.",
            "No fixed check rejects all10 wrong poses while retaining the accurate case.",
        ],
        "limitations": [
            "12 pairs, three previously inspected scenes; no prospective/generalization claim.",
            "Self-consistency and solver agreement are not correspondence ground truth.",
            "Physical-plausibility inspection is post-outcome; no post-hoc rule promoted.",
            "Source-coordinate checks do not independently validate real calibration or vertical datum.",
            "No independent human scientific adjudication is claimed.",
        ],
    })
    store.put(CAMPAIGN, "decisions", {
        "id": "decision-pointmatch-attribution-v1", "action": "iterate",
        "reason": record["summary"], "validation_id": record["id"],
        "generation_paused": True, "m09_stopped": True,
        "next_evidence": "Two-reviewer PointMatch overlap/landmark annotations and new eligible scenes "
                         "containing both accurate and inaccurate poses; no speculative mechanism batch.",
    })
    remaining = next(pair for pair in packet["pairs"]
                     if pair["case_id"] == "any-l06_1274-satellite")
    store.put(CAMPAIGN, "tensions", {
        "id": "attribution-shared-wrong-consensus",
        "title": "Different estimators can agree on a geographically wrong, implausible pose",
        "observation": "L06_1274: P3P error935.82m; EPNP estimated-XY disagreement0.0654m; "
                       "USAC-MAGSAC disagreement5.1437m. Inlier hull minimum0.337%. "
                       "Post-outcome inspection places the estimated camera4.11m below the "
                       "provider DSM with an upward optical axis.",
        "evidence": [{
            "observation": "Frozen-match CPU measurements and original-image review packet",
            "record_type": "experimental_observation", "level": "reproduced; point GT unavailable",
            "source_url": remaining["url"], "location": str(RESULTS / "geometry-diagnostics.json"),
        }],
        "explanations": [
            "Incorrect correspondences or absent visible overlap produce a shared false consensus.",
            "Weak spatial support permits a physically implausible fitted pose.",
            "Physical camera/map assumptions remain wrong despite source-coordinate consistency.",
        ],
        "unresolved": "Two-reviewer landmarks/overlap, independent camera constraints and new-scene "
                      "validation are required to distinguish these causes. No new method claimed.",
        "directions": [], "opportunity_ids": [],
    })
    save("published.json", {"campaign": CAMPAIGN, "validation": record["id"]}, directory=REPORT.parent)
    print("Published ITERATE:", len(references), "preserved artifacts;", preservation["total_bytes"], "bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--documentation", type=Path, required=True)
    args = parser.parse_args()
    publish(args.documentation)
