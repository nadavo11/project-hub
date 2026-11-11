"""python -m research_radar --help"""

import argparse
import json
from pathlib import Path

from .core import DEFAULT_HOME, Store, dumps
from .server import report, serve


def main():
    parser = argparse.ArgumentParser(description="Persistent evidence-first research campaigns. No GPU execution.")
    parser.add_argument("--home", type=Path, default=DEFAULT_HOME)
    sub = parser.add_subparsers(dest="command", required=True)
    web = sub.add_parser("serve")
    web.add_argument("--port", type=int, default=8776)
    create = sub.add_parser("create")
    create.add_argument("--name", required=True)
    create.add_argument("--field", required=True)
    create.add_argument("--query", action="append", default=[])
    create.add_argument("--config", type=Path)
    for name in ("start", "pause", "resume", "cancel", "inspect", "report", "export"):
        cmd = sub.add_parser(name)
        cmd.add_argument("campaign")
    ingest = sub.add_parser("import")
    ingest.add_argument("campaign")
    ingest.add_argument("file", type=Path)
    search = sub.add_parser("search")
    search.add_argument("campaign")
    search.add_argument("query")
    sub.add_parser("list")
    args = parser.parse_args()
    if args.command == "serve":
        return serve(args.home, args.port)
    store = Store(args.home)
    if args.command == "create":
        config = json.loads(args.config.read_text()) if args.config else {}
        if args.query:
            config["queries"] = args.query
        output = store.create({"name": args.name, "field": args.field, "config": config})
    elif args.command == "list":
        output = store.state()["campaigns"]
    elif args.command in {"start", "pause", "resume", "cancel"}:
        output = store.control(args.campaign, args.command)
    elif args.command == "import":
        output = {"sha256": store.import_bundle(args.campaign, json.loads(args.file.read_text()), str(args.file))}
    elif args.command == "search":
        output = store.investigate(args.campaign, {"query": args.query})
    else:
        output = store.state(args.campaign)
        if args.command == "report":
            print(report(output))
            return
    print(dumps(output))


if __name__ == "__main__":
    main()
