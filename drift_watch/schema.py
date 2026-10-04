"""Infer a compact structural schema from JSON values.

A schema node is a dict: {"types": [sorted type names], "fields": {...}, "items": node,
"optional": bool}. Objects get "fields", arrays get "items". Merging many samples
marks fields missing in some samples as optional and unions their types.
"""
from __future__ import annotations

from typing import Any


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def infer_schema(value: Any) -> dict:
    """Infer the schema of a single JSON value."""
    t = _type_name(value)
    node: dict = {"types": [t]}
    if isinstance(value, dict):
        node["fields"] = {k: infer_schema(v) for k, v in value.items()}
    elif isinstance(value, list):
        items = None
        for el in value:
            s = infer_schema(el)
            items = s if items is None else merge_schemas(items, s)
        if items is not None:
            node["items"] = items
    return node


def merge_schemas(a: dict, b: dict) -> dict:
    """Union two schemas (used to fold many samples into one)."""
    out: dict = {"types": sorted(set(a["types"]) | set(b["types"]))}
    fa, fb = a.get("fields"), b.get("fields")
    if fa is not None or fb is not None:
        fa, fb = fa or {}, fb or {}
        fields = {}
        for k in sorted(set(fa) | set(fb)):
            if k in fa and k in fb:
                fields[k] = merge_schemas(fa[k], fb[k])
            else:
                fields[k] = dict(fa.get(k) or fb[k])
                fields[k]["optional"] = True
            if (k in fa and fa[k].get("optional")) or (k in fb and fb[k].get("optional")):
                fields[k]["optional"] = True
        out["fields"] = fields
    ia, ib = a.get("items"), b.get("items")
    if ia is not None or ib is not None:
        out["items"] = merge_schemas(ia, ib) if ia and ib else (ia or ib)
    return out
