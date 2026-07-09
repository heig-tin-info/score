"""Merge a results mapping into a raw criteria YAML structure.

Results are ``{ "dotted.criterion.id": {"awarded_points": N, "rationale": "..."} }``.
The same shape is produced both by objective test harnesses (tests passed ->
points) and by the LLM grader (``score grade --llm``), so a single ``score
apply`` command closes the loop for both grading tiers.

Applying mutates the *raw* YAML (before schema normalization) so the file keeps
its version 2 layout (``awarded_points`` / ``max_points`` / ``bonus_points``);
version 1 files (``$points`` / ``$bonus``) are supported too.
"""

from __future__ import annotations

import sys
from typing import Any, Dict, Iterator, List, Mapping, Tuple


def _is_raw_item(value: Any) -> bool:
    """Return True when a raw YAML node is a leaf criterion, not a section."""
    if not isinstance(value, dict):
        return False
    keys = {str(k) for k in value.keys()}
    if keys & {"awarded_points", "max_points", "bonus_points"}:
        return True
    return bool(keys) and all(k.startswith("$") for k in keys)


def _iter_raw_leaves(
    node: Mapping[str, Any],
    prefix: Tuple[str, ...] = (),
) -> Iterator[Tuple[Tuple[str, ...], Dict[str, Any]]]:
    """Yield ``(path, item)`` for every leaf criterion in a raw section."""
    for key, value in node.items():
        skey = str(key)
        if skey in {"description", "schema_version", "$description", "$desc"}:
            continue
        if not isinstance(value, dict):
            continue
        if _is_raw_item(value):
            yield prefix + (skey,), value
        else:
            yield from _iter_raw_leaves(value, prefix + (skey,))


def _clamp(points: float, item: Dict[str, Any]) -> Tuple[float, str | None]:
    """Clamp awarded points to the criterion's valid range; return a note if changed."""
    total: float | None = None
    if "max_points" in item:
        total = float(item["max_points"])
    elif "bonus_points" in item:
        total = float(item["bonus_points"])
    elif "$points" in item and isinstance(item["$points"], list):
        total = float(item["$points"][1])
    elif "$bonus" in item and isinstance(item["$bonus"], list):
        total = float(item["$bonus"][1])

    if total is None:
        return points, None

    low, high = (0.0, total) if total >= 0 else (total, 0.0)
    clamped = max(low, min(high, points))
    if clamped != points:
        return clamped, f"clamped {points:g} into [{low:g}, {high:g}]"
    return clamped, None


def _normalize_points(value: float) -> float | int:
    """Return an int when the numeric value is integral, else the float."""
    return int(value) if float(value).is_integer() else value


def _set_award(
    item: Dict[str, Any],
    points: float,
    rationale: Any,
) -> None:
    """Write awarded points (and optional rationale) into a raw leaf criterion."""
    points = _normalize_points(points)
    if {"max_points", "bonus_points", "awarded_points"} & set(item):
        item["awarded_points"] = points
        if rationale is not None:
            item["rationale"] = rationale
    else:  # version 1 leaf
        if "$points" in item and isinstance(item["$points"], list):
            item["$points"] = [points, item["$points"][1]]
        elif "$bonus" in item and isinstance(item["$bonus"], list):
            item["$bonus"] = [points, item["$bonus"][1]]
        if rationale is not None:
            item["$rationale"] = rationale


def apply_results(
    raw_criteria: Mapping[str, Any],
    results: Mapping[str, Any],
) -> Tuple[Dict[str, Any], List[str], List[str]]:
    """Return ``(updated, applied_ids, unknown_ids)`` after merging results.

    ``raw_criteria`` is the full parsed YAML mapping (``criteria``, and
    optionally ``grading`` / ``schema_version``). ``results`` maps dotted
    criterion ids to ``{"awarded_points": N, "rationale": "..."}``.
    """
    updated = dict(raw_criteria)
    section = updated.get("criteria")
    if not isinstance(section, dict):
        raise ValueError("criteria definition must be a mapping")

    by_id: Dict[str, Dict[str, Any]] = {
        ".".join(path): item for path, item in _iter_raw_leaves(section)
    }

    applied: List[str] = []
    unknown: List[str] = []
    for raw_id, payload in results.items():
        cid = str(raw_id)
        item = by_id.get(cid)
        if item is None:
            unknown.append(cid)
            continue
        if not isinstance(payload, Mapping) or "awarded_points" not in payload:
            unknown.append(cid)
            continue
        points = float(payload["awarded_points"])
        clamped, note = _clamp(points, item)
        if note is not None:
            print(f"warning: {cid}: {note}", file=sys.stderr)
        _set_award(item, clamped, payload.get("rationale"))
        applied.append(cid)

    return updated, applied, unknown


__all__ = ["apply_results"]
