"""Compare a baseline schema with a current schema and classify changes."""
from __future__ import annotations

from dataclasses import dataclass

BREAKING = "breaking"
WARNING = "warning"
INFO = "info"


@dataclass(frozen=True)
class Change:
    path: str
    kind: str       # removed | added | type_changed | became_optional | became_required
    severity: str   # breaking | warning | info
    detail: str

    def to_dict(self) -> dict:
        return {"path": self.path, "kind": self.kind, "severity": self.severity, "detail": self.detail}


def diff_schemas(old: dict, new: dict, path: str = "$") -> list[Change]:
    changes: list[Change] = []
    ot, nt = set(old["types"]), set(new["types"])
    if ot != nt:
        lost, gained = ot - nt, nt - ot
        # widening to include null is a warning; losing/replacing types is breaking
        sev = BREAKING if lost or (gained - {"null"}) else WARNING
        changes.append(Change(path, "type_changed", sev,
                              f"{'/'.join(sorted(ot))} -> {'/'.join(sorted(nt))}"))
    of, nf = old.get("fields"), new.get("fields")
    if of is not None and nf is not None:
        for k in sorted(set(of) | set(nf)):
            p = f"{path}.{k}"
            if k in of and k not in nf:
                sev = WARNING if of[k].get("optional") else BREAKING
                changes.append(Change(p, "removed", sev, "field no longer present"))
            elif k in nf and k not in of:
                changes.append(Change(p, "added", INFO, f"new field ({'/'.join(nf[k]['types'])})"))
            else:
                if nf[k].get("optional") and not of[k].get("optional"):
                    changes.append(Change(p, "became_optional", WARNING, "field now sometimes missing"))
                elif of[k].get("optional") and not nf[k].get("optional"):
                    changes.append(Change(p, "became_required", INFO, "field now always present"))
                changes.extend(diff_schemas(of[k], nf[k], p))
    oi, ni = old.get("items"), new.get("items")
    if oi is not None and ni is not None:
        changes.extend(diff_schemas(oi, ni, path + "[]"))
    return changes


def summarize(changes: list[Change]) -> dict:
    out = {BREAKING: 0, WARNING: 0, INFO: 0}
    for c in changes:
        out[c.severity] += 1
    return out
