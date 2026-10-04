"""Render drift results as text, JSON or Markdown."""
from __future__ import annotations

import json

from .diff import Change, summarize

ICON = {"breaking": "BREAKING", "warning": "WARNING ", "info": "INFO    "}


def as_text(name: str, changes: list[Change]) -> str:
    if not changes:
        return f"[{name}] no drift detected"
    s = summarize(changes)
    lines = [f"[{name}] {s['breaking']} breaking, {s['warning']} warning, {s['info']} info"]
    order = {"breaking": 0, "warning": 1, "info": 2}
    for c in sorted(changes, key=lambda c: (order[c.severity], c.path)):
        lines.append(f"  {ICON[c.severity]} {c.path}  {c.kind}: {c.detail}")
    return "\n".join(lines)


def as_json(name: str, changes: list[Change]) -> str:
    return json.dumps({"endpoint": name, "summary": summarize(changes),
                       "changes": [c.to_dict() for c in changes]}, indent=2)


def as_markdown(name: str, changes: list[Change]) -> str:
    if not changes:
        return f"### {name}\n\nNo drift detected."
    rows = ["| Severity | Path | Change | Detail |", "|---|---|---|---|"]
    for c in changes:
        rows.append(f"| {c.severity} | `{c.path}` | {c.kind} | {c.detail} |")
    return f"### {name}\n\n" + "\n".join(rows)
