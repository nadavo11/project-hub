#!/usr/bin/env bash
# Install Project Hub as systemd user services. Python 3.9+ standard library only.
#   ./install.sh                 dashboard only, localhost
#   ./install.sh --agents        also enable the private AI-thread coordinator
#   ./install.sh --lan           listen on all interfaces (no authentication on the workspace!)
#   ./install.sh --no-start      write units without starting them
set -euo pipefail

agents=0 host=127.0.0.1 start=1
for arg in "$@"; do
  case "$arg" in
    --agents) agents=1 ;;
    --lan) host=0.0.0.0 ;;
    --no-start) start=0 ;;
    -h|--help) sed -n '2,6p' "$0"; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

dir=$(cd "$(dirname "$0")" && pwd)
python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' \
  || { echo "Python 3.9 or newer is required." >&2; exit 1; }
command -v systemctl >/dev/null \
  || { echo "systemd not found. Run it manually instead: python3 server.py" >&2; exit 1; }

units="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
mkdir -p "$units" "$dir/logs"
render() {
  sed -e "s|@PROJECT_DIR@|$dir|g" -e "s|@HOME@|$HOME|g" -e "s|@HOST@|$host|g" \
    "$dir/systemd/$1.service.in" > "$units/$1.service.tmp"
  rm -f "$units/$1.service"; mv "$units/$1.service.tmp" "$units/$1.service"
}
render project-hub
(( agents )) && render project-hub-agents
systemctl --user daemon-reload

if (( start )); then
  systemctl --user enable --now project-hub.service
  (( agents )) && systemctl --user enable --now project-hub-agents.service
  echo "Project Hub is running at http://127.0.0.1:8765/"
else
  echo "Units written to $units (not started)."
fi
