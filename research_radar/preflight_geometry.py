"""CPU-only annotation consistency check; no learned model or scientific treatment."""

import hashlib
import io
import math
import struct
import time
import zipfile
import ast

from .core import DEFAULT_HOME
from .iteration import save


def array(blob):
    file = io.BytesIO(blob)
    magic = file.read(8)
    if magic[:6] != b"\x93NUMPY":
        raise ValueError("Invalid NPY")
    size = struct.unpack("<H" if magic[6] == 1 else "<I", file.read(2 if magic[6] == 1 else 4))[0]
    header = ast.literal_eval(file.read(size).decode())
    if header["fortran_order"] or header["descr"] != "<f4":
        raise ValueError("Only C-order float32 geometry accepted; never unpickle data")
    return header["shape"], memoryview(blob)[file.tell():]


def matrix(package, name, count):
    _, data = array(package.read(name + ".npy"))
    return struct.unpack("<" + "f" * count, data)


def inspect(path):
    with zipfile.ZipFile(path) as package:
        shape, points = array(package.read("point_map.npy"))
        height, width, channels = shape
        if channels != 3:
            raise ValueError("Expected three-dimensional point map")
        intrinsics = matrix(package, "intrinsics", 9)
        output = {}
        for field in ["extrinsics", "extrinsics_refined"]:
            pose = matrix(package, field, 12)
            errors, invalid = [], 0
            for gy in range(6):
                y = min(height - 1, (2 * gy + 1) * height // 12)
                for gx in range(8):
                    x = min(width - 1, (2 * gx + 1) * width // 16)
                    point = struct.unpack_from("<fff", points, (y * width + x) * 12)
                    if not all(map(math.isfinite, point)):
                        invalid += 1
                        continue
                    camera = [sum(pose[i * 4 + j] * point[j] for j in range(3)) + pose[i * 4 + 3] for i in range(3)]
                    image = [sum(intrinsics[i * 3 + j] * camera[j] for j in range(3)) for i in range(3)]
                    if not all(map(math.isfinite, image)) or image[2] <= 0:
                        invalid += 1
                        continue
                    errors.append(math.hypot(image[0] / image[2] - x, image[1] / image[2] - y))
            errors.sort()
            output[field] = {
                "attempted": 48, "valid": len(errors), "invalid_or_nonpositive_depth": invalid,
                "median_pixel_error": errors[len(errors) // 2] if errors else None,
                "p95_pixel_error": errors[min(len(errors) - 1, math.ceil(.95 * len(errors)) - 1)] if errors else None,
                "errors": errors,
            }
    original = output["extrinsics"]
    return {"file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "poses": output, "nominal_consistency_passed": original["valid"] >= 30 and
            original["median_pixel_error"] <= 2 and original["p95_pixel_error"] <= 5}


def main():
    start = time.monotonic()
    root = DEFAULT_HOME / "iteration-sources"
    samples = [inspect(root / name) for name in ["ortholoc-crossdomain.npz", "ortholoc-samedomain.npz"]]
    value = {
        "id": "annotation-consistency", "expected": "At least 30/48 fixed-grid valid points, median <=2px and p95 <=5px using the nominal pose; refined pose reported separately, never selected post hoc.",
        "method": "Read numeric arrays without NumPy/pickle; project provided world point map through provided world-to-query extrinsics and intrinsics onto its own pixel grid.",
        "samples": samples, "passed": all(s["nominal_consistency_passed"] for s in samples),
        "elapsed_seconds": time.monotonic() - start, "gpu_hours": 0,
        "limitation": "Within-source camera/pointmap consistency only. Not independent ground truth, DSM correctness, matcher performance, a hypothesis experiment or generalization evidence.",
    }
    save("geometry-preflight.json", value)
    print({"passed": value["passed"], "elapsed_seconds": value["elapsed_seconds"],
           "nominal": [s["poses"]["extrinsics"] for s in samples]})


if __name__ == "__main__":
    main()
