"""Canonical registry of the projects that hub content can be paired with."""

import json
import os
import re
from pathlib import Path
import threading

HOME = Path.home()

# id -> (display name, directory). Ids are the only thing the client may send.
PROJECTS = {
    "localization": ("Localization", HOME / "localization-models"),
    "crossview": ("Drone & Aerial Explorer", HOME / "localization-models"),
    "video-agents": (
        "Video Agents",
        HOME / ".copilot/session-state/0bf05d14-ae18-4935-a27f-f7e87de03910"
        / "files/project/video-agents",
    ),
    "sample4geo": ("Sample4Geo Atlas", HOME / "sample4geo-atlas"),
    "research-radar": ("Research Radar", Path(__file__).resolve().parent / "research_radar"),
}


BUILTIN = frozenset(PROJECTS)
DESCRIPTIONS = {}
_lock = threading.Lock()
_store = None


def load_custom(path):
    """Merge operator-created badges from a JSON file into the registry."""
    global _store
    _store = Path(path)
    try:
        rows = json.loads(_store.read_text())
    except (OSError, ValueError):
        return
    for row in rows if isinstance(rows, list) else []:
        try:
            key, name, directory = row["id"], row["name"], Path(row["directory"])
        except (KeyError, TypeError):
            continue
        if isinstance(key, str) and isinstance(name, str) and key not in BUILTIN:
            PROJECTS[key] = (name, directory)
            DESCRIPTIONS[key] = str(row.get("description", ""))


def add_project(name, directory, description=""):
    """Create a badge. The id is server-generated; the directory must already exist."""
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 40:
        raise ValueError("Badge name is required (up to 40 characters).")
    if not isinstance(directory, str) or not os.path.isabs(directory):
        raise ValueError("Directory must be an absolute path.")
    folder = Path(directory).resolve()
    if not folder.is_dir():
        raise ValueError("Directory does not exist.")
    if not isinstance(description, str) or len(description) > 2000:
        raise ValueError("Description is too long.")
    name = name.strip()
    with _lock:
        if any(existing.lower() == name.lower() for existing, _ in PROJECTS.values()):
            raise ValueError("A badge with that name already exists.")
        base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:24] or "project"
        key, count = base, 2
        while key in PROJECTS:
            key, count = f"{base}-{count}", count + 1
        PROJECTS[key] = (name, folder)
        DESCRIPTIONS[key] = description.strip()
        if _store:
            rows = [{"id": k, "name": PROJECTS[k][0], "directory": str(PROJECTS[k][1]),
                     "description": DESCRIPTIONS.get(k, "")} for k in PROJECTS if k not in BUILTIN]
            temporary = _store.with_suffix(".tmp")
            temporary.write_text(json.dumps(rows, indent=2))
            os.replace(temporary, _store)
    return key


def valid_project(value):
    return value == "" or value in PROJECTS


def check_project(value):
    if not isinstance(value, str) or not valid_project(value):
        raise ValueError("Unknown project.")
    return value


def project_directory(project):
    """Working directory for a project id, or None when unset, unknown or missing."""
    entry = PROJECTS.get(project)
    return entry[1] if entry and entry[1].is_dir() else None


def project_context(project):
    """Text block telling an agent which project it is working in."""
    entry = PROJECTS.get(project)
    if not entry:
        return ""
    about = DESCRIPTIONS.get(project)
    extra = f"- Description: {about}\n" if about else ""
    return f"PROJECT\n- Id: {project}\n- Name: {entry[0]}\n- Directory: {entry[1]}\n{extra}\n"


def registry():
    return [{"id": key, "name": name} for key, (name, _path) in list(PROJECTS.items())]
