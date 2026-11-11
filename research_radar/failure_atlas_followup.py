"""Extend the frozen depth operator to the separately audited sampling controls."""

import shutil

from . import failure_atlas_depth as depth
from .failure_atlas_run import OUT, read, save, digest


def main():
    destination = OUT / "sampling-depth"
    if destination.exists():
        raise RuntimeError("Follow-up already exists; preserve its results")
    destination.mkdir()
    protocol = read(OUT / "depth-protocol.json")
    protocol["methods"] = ["roma-005", "roma-official"]
    protocol["status"] = "Secondary depth test after sampling controls; frozen before its own depth outcomes. The original depth experiment is unchanged."
    protocol["orchestrator_sha256"] = digest(__file__)
    save(destination / "depth-protocol.json", protocol)
    save(destination / "atlas.json", read(OUT / "atlas.json"))
    for identifier in protocol["cases"]:
        folder = destination / "cases" / identifier
        folder.mkdir(parents=True)
        for name in ("case.json", "roma-005.json", "roma-official.json"):
            shutil.copyfile(OUT / "cases" / identifier / name, folder / name)
    depth.OUT = destination
    depth.run()


if __name__ == "__main__":
    main()
