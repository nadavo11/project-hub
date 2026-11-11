"""Reproduce the software acceptance receipt; fixtures never count as research findings."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time

from .core import ROOT, now


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "pilot")
    output = parser.parse_args().output_dir
    output.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-m", "unittest", "-v",
               "research_radar.test_core", "research_radar.test_validation",
               "research_radar.test_archive", "research_radar.test_iteration",
               "research_radar.test_ui", "test_server", "test_agents"]
    start = time.monotonic()
    result = subprocess.run(command, cwd=ROOT.parent, capture_output=True, text=True, timeout=180)
    log = result.stdout + result.stderr
    (output / "software-tests.log").write_text(log)
    count = re.search(r"Ran (\d+) tests", log)
    skipped = re.search(r"skipped=(\d+)", log)
    receipt = {
        "id": "software-acceptance", "title": "Real backend and isolated browser regression execution",
        "at": now(), "passed": result.returncode == 0 and not skipped,
        "command": command, "returncode": result.returncode,
        "test_executions": int(count[1]) if count else None,
        "skipped": int(skipped[1]) if skipped else 0,
        "elapsed_seconds": time.monotonic() - start,
        "log": str(output / "software-tests.log"),
        "cases": [{
            "id": "software-regressions", "title": "Persistence, controls, recovery, provenance, isolation, browser and Hub regressions",
            "expected": "All selected tests pass, including real-server browser tests, with no skipped browser tests",
            "observed": f"{count[1] if count else 'Unknown count'} test executions; exit {result.returncode}; " + ("no skipped tests" if not skipped else skipped[0]),
            "passed": result.returncode == 0 and not skipped,
            "evidence": "Exact test names and results in software-tests.log; behavioral expectations are executable in test_core.py, test_validation.py and test_ui.py.",
        }],
        "limitations": [
            "Scientific records in automated browser tests are explicitly synthetic fixtures; real research is evaluated in separate artifacts.",
            "HTTPTests also executes inherited store tests, so execution count is not a count of independent scientific or behavioral claims.",
            "Ruff and Node executables were unavailable. No repository linter/build is configured for this stdlib/static application; Python compile checks and actual Playwright JavaScript/CSP execution were used instead.",
        ],
    }
    (output / "software-validation.json").write_text(json.dumps(receipt, indent=2))
    print(json.dumps({key: receipt[key] for key in ("passed", "test_executions", "skipped", "elapsed_seconds")}))
    if result.returncode:
        print(log[-10000:])
    raise SystemExit(0 if receipt["passed"] else 1)


if __name__ == "__main__":
    main()
