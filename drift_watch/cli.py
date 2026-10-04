"""Command line interface.

  drift-watch snapshot URL_OR_FILE [--name N] [--store DIR] [--header K:V]
  drift-watch check    URL_OR_FILE [--name N] [--store DIR] [--format text|json|markdown]
                                    [--fail-on breaking|warning|never] [--update]
  drift-watch list     [--store DIR]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

from . import report
from .diff import diff_schemas
from .schema import infer_schema, merge_schemas

DEFAULT_STORE = ".drift-watch"


def load_json(source: str, headers: list[str] | None = None, timeout: int = 15):
    if source.startswith(("http://", "https://")):
        req = urllib.request.Request(source, headers={"Accept": "application/json",
                                                       "User-Agent": "api-schema-drift-watch/1.0"})
        for h in headers or []:
            k, _, v = h.partition(":")
            req.add_header(k.strip(), v.strip())
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            return json.loads(r.read().decode("utf-8"))
    return json.loads(Path(source).read_text(encoding="utf-8"))


def slug(source: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", re.sub(r"^https?://", "", source)).strip("-").lower()[:80] or "endpoint"


def schema_path(store: str, name: str) -> Path:
    return Path(store) / f"{name}.schema.json"


def sample_schema(sources: list[str], headers):
    schema = None
    for s in sources:
        sc = infer_schema(load_json(s, headers))
        schema = sc if schema is None else merge_schemas(schema, sc)
    return schema


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="drift-watch", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for cmd in ("snapshot", "check"):
        sp = sub.add_parser(cmd)
        sp.add_argument("source", nargs="+", help="URL(s) or JSON file(s); several samples are merged")
        sp.add_argument("--name")
        sp.add_argument("--store", default=DEFAULT_STORE)
        sp.add_argument("--header", action="append", default=[], help="e.g. 'Authorization: Bearer X'")
        if cmd == "check":
            sp.add_argument("--format", choices=["text", "json", "markdown"], default="text")
            sp.add_argument("--fail-on", choices=["breaking", "warning", "never"], default="breaking")
            sp.add_argument("--update", action="store_true", help="accept current schema as new baseline")
    ls = sub.add_parser("list")
    ls.add_argument("--store", default=DEFAULT_STORE)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "list":
        for f in sorted(Path(args.store).glob("*.schema.json")):
            print(f.name.removesuffix(".schema.json"))
        return 0
    name = args.name or slug(args.source[0])
    path = schema_path(args.store, name)
    try:
        current = sample_schema(args.source, args.header)
    except Exception as exc:  # network / parse errors
        print(f"error: could not load source: {exc}", file=sys.stderr)
        return 3
    if args.cmd == "snapshot":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(current, indent=2, sort_keys=True), encoding="utf-8")
        print(f"baseline saved: {path}")
        return 0
    if not path.exists():
        print(f"error: no baseline for '{name}'. Run `drift-watch snapshot` first.", file=sys.stderr)
        return 3
    baseline = json.loads(path.read_text(encoding="utf-8"))
    changes = diff_schemas(baseline, current)
    render = {"text": report.as_text, "json": report.as_json, "markdown": report.as_markdown}[args.format]
    print(render(name, changes))
    if args.update:
        path.write_text(json.dumps(current, indent=2, sort_keys=True), encoding="utf-8")
    sev = {c.severity for c in changes}
    if args.fail_on == "breaking" and "breaking" in sev:
        return 1
    if args.fail_on == "warning" and sev & {"breaking", "warning"}:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
