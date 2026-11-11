"""Small CPU identity/counterexample checks against frozen finalist operations."""

import hashlib
import math
import random
import struct
import time
import zipfile
from pathlib import Path

from .archive import Archive
from .core import DEFAULT_HOME
from .mechanism_campaign import DIRECTORY, load, persist
from .preflight_geometry import array, matrix


def inverse(a):
    n = len(a)
    m = [list(row) + [float(i == j) for j in range(n)] for i, row in enumerate(a)]
    for k in range(n):
        pivot = max(range(k, n), key=lambda i: abs(m[i][k]))
        m[k], m[pivot] = m[pivot], m[k]
        if abs(m[k][k]) < 1e-12:
            raise ValueError("Singular diagnostic matrix")
        divisor = m[k][k]
        m[k] = [v / divisor for v in m[k]]
        for i in range(n):
            if i != k:
                multiplier = m[i][k]
                m[i] = [a - multiplier * b for a, b in zip(m[i], m[k])]
    return [row[n:] for row in m]


def map_counterexample():
    jacobian, y, prior, theta0 = [[2.0, 0.0], [0.0, 1.0]], [4.0, 4.0], [0.0, 0.0], [2.0, 4.0]
    hessian = [[sum(row[i] * row[j] for row in jacobian) + (i == j) for j in range(2)] for i in range(2)]
    covariance = inverse(hessian)

    def apply(a, x):
        return [sum(v * w for v, w in zip(row, x)) for row in a]

    transposed = list(zip(*jacobian))
    rhs = [a + b for a, b in zip(apply(transposed, y), prior)]
    exact = apply(covariance, rhs)

    def proposal(at):
        residual = [a - b for a, b in zip(y, apply(jacobian, at))]
        return [a + b for a, b in zip(prior, apply(covariance, apply(transposed, residual)))]

    current_residual_proposal = proposal(theta0)
    prior_residual_proposal = proposal(prior)
    current_error = max(abs(a - b) for a, b in zip(exact, current_residual_proposal))
    prior_error = max(abs(a - b) for a, b in zip(exact, prior_residual_proposal))
    assert all(math.isclose(a, b) for a, b in zip(exact, [1.6, 2.0]))
    assert current_error > 1e-10 and prior_error <= 1e-10
    return {
        "id": "D06", "candidate_id": "M06", "record_type": "experimental_observation",
        "expected": load("diagnostic-protocol.json")["cases"][0]["expected"],
        "observed": {"exact_map": exact, "current_residual_proposal": current_residual_proposal,
                     "current_residual_max_error": current_error,
                     "prior_residual_proposal": prior_residual_proposal, "prior_residual_max_error": prior_error},
        "conclusion": "Counterexample under the conventional current-iterate residual; under a prior-centred residual the operation is standard MAP. Residual definition is missing, so this is not an unconditional invalidity verdict.",
    }


def schur_identity():
    rng = random.Random(731)
    errors = []
    for _ in range(64):
        a = [[rng.uniform(-1, 1) for _ in range(7)] for _ in range(10)]
        information = [[sum(row[i] * row[j] for row in a) + (i == j) for j in range(7)] for i in range(7)]
        full = inverse(information)
        schur = [[information[i][j] - information[i][6] * information[6][j] / information[6][6]
                  for j in range(6)] for i in range(6)]
        marginal = inverse(schur)
        errors.append(max(abs(marginal[i][j] - full[i][j]) for i in range(6) for j in range(6)))
    assert max(errors) <= 1e-9
    return {
        "id": "D08", "candidate_id": "M08", "record_type": "experimental_observation",
        "expected": load("diagnostic-protocol.json")["cases"][1]["expected"],
        "observed": {"cases": len(errors), "max_entry_difference": max(errors), "errors": errors},
        "conclusion": "Numerically confirms the standard block-inverse identity. No new covariance operator; no claim about real-data utility.",
    }


def uniform_height(path):
    def project(p, pose, intrinsics):
        camera = [sum(pose[i * 4 + j] * p[j] for j in range(3)) + pose[i * 4 + 3] for i in range(3)]
        image = [sum(intrinsics[i * 3 + j] * camera[j] for j in range(3)) for i in range(3)]
        return [image[0] / image[2], image[1] / image[2]] if image[2] > 0 else None

    errors, derivative_errors, valid, invalid = [], [], 0, 0
    with zipfile.ZipFile(path) as package:
        (height, width, channels), points = array(package.read("point_map.npy"))
        assert channels == 3
        pose = matrix(package, "extrinsics", 12)
        intrinsics = matrix(package, "intrinsics", 9)
        for gy in range(6):
            y = min(height - 1, (2 * gy + 1) * height // 12)
            for gx in range(8):
                x = min(width - 1, (2 * gx + 1) * width // 16)
                point = struct.unpack_from("<fff", points, (y * width + x) * 12)
                if not all(map(math.isfinite, point)):
                    invalid += 1
                    continue
                original = project(point, pose, intrinsics)
                if original is None:
                    invalid += 1
                    continue
                valid += 1
                for shift in [-3.0, -1.0, -0.1, 0.1, 1.0, 3.0]:
                    perturbed = list(point)
                    perturbed[2] += shift
                    compensation = list(pose)
                    for i in range(3):
                        compensation[i * 4 + 3] -= pose[i * 4 + 2] * shift
                        derivative_errors.append(abs((compensation[i * 4 + 3] - pose[i * 4 + 3]) / shift + pose[i * 4 + 2]))
                    actual = project(perturbed, compensation, intrinsics)
                    errors.append(math.dist(original, actual))
    assert valid >= 30 and max(errors) <= 1e-6 and max(derivative_errors) <= 1e-10
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "attempted": 48, "valid": valid, "invalid": invalid, "controlled_projections": len(errors),
            "max_projection_difference_px": max(errors),
            "max_translation_derivative_difference": max(derivative_errors)}


def main():
    archive = Archive(DEFAULT_HOME / "archive")
    protocol = DIRECTORY / "diagnostic-protocol.json"
    reference = archive.store_bytes(protocol.read_bytes(), url=protocol.as_uri(),
                                    media_type="application/json", retrieved_at=None, representation="artifact")
    source = Path(__file__).resolve()
    implementation = archive.store_bytes(source.read_bytes(), url=source.as_uri(),
                                         media_type="text/x-python", retrieved_at=None, representation="artifact")
    start = time.process_time()
    wall = time.monotonic()
    results = [map_counterexample(), schur_identity()]
    samples = [uniform_height(DEFAULT_HOME / "iteration-sources" / name)
               for name in ["ortholoc-crossdomain.npz", "ortholoc-samedomain.npz"]]
    results.append({
        "id": "D09", "candidate_id": "M09", "record_type": "experimental_observation",
        "expected": load("diagnostic-protocol.json")["cases"][2]["expected"], "observed": samples,
        "conclusion": "Uniform-height mode is exactly compensated by camera translation. No advantage over analytic sensitivity on this mode. Nonlinear/inlier-switch advantage remains untested, not disproved.",
    })
    cpu = time.process_time() - start
    assert cpu <= 300
    persist("diagnostic-results.json", {
        "protocol": reference.to_dict(), "implementation": implementation.to_dict(), "results": results,
        "cpu_seconds": cpu, "wall_seconds": time.monotonic() - wall, "gpu_hours": 0,
        "new_dependencies": [], "matcher_or_model_execution": False, "full_candidate_experiments_run": 0,
        "experimentally_supported_hypotheses": 0,
        "limit": "Conditional counterexample, standard algebra identity and controlled coordinate transformation only. No scientific-performance gate satisfied.",
    })
    print({"diagnostics": len(results), "cpu_seconds": cpu, "full_candidate_experiments_run": 0})


if __name__ == "__main__":
    main()
