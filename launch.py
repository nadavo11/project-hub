#!/usr/bin/env python3
"""Open the dashboard, starting its user service if necessary."""

import json
import subprocess
import sys
import time
import webbrowser
from urllib.request import ProxyHandler, build_opener


URL = "http://127.0.0.1:8765/"
HTTP = build_opener(ProxyHandler({}))


def ready():
    try:
        with HTTP.open(URL + "api/health", timeout=1) as response:
            return json.load(response).get("app") == "project-hub"
    except (OSError, ValueError):
        return False


def main():
    if not ready():
        subprocess.run(
            ["systemctl", "--user", "start", "project-hub.service"], check=True
        )
        for _ in range(40):
            if ready():
                break
            time.sleep(0.25)
        else:
            print(
                "Project Hub could not start. Run: journalctl --user -u project-hub",
                file=sys.stderr,
            )
            return 1
    webbrowser.open(URL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
