"""Helpers to migrate criteria definitions between schema versions."""

from __future__ import annotations

from typing import Any, Dict, Mapping


def _is_v1_item(entry: Any) -> bool:
    """Return True when the provided entry represents a V1 leaf criterion."""
    if not isinstance(entry, Mapping):
        return False
    keys = {str(key) for key in entry.keys()}
    return bool(keys) and all(key.startswith("$") for key in keys)


def _normalize_text(value: Any) -> Any:
    """Convert multi-line list content into a single string."""
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    return value


def _normalize_points(value: float | int) -> float | int:
    """Return integers when the provided numeric value is integral."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _convert_item_v1_to_v2(item: Mapping[str, Any]) -> Dict[str, Any]:
    """Convert a v1 item definition to the v2 structure."""
    result: Dict[str, Any] = {}
    description = item.get("$description", item.get("$desc"))
    if description is not None:
        result["description"] = _normalize_text(description)

    points = item.get("$points")
    bonus = item.get("$bonus")
    if points is not None:
        obtained, total = points
        result["awarded_points"] = _normalize_points(obtained)
        result["max_points"] = int(total)
    elif bonus is not None:
        obtained, total = bonus
        result["awarded_points"] = _normalize_points(obtained)
        result["bonus_points"] = int(total)

    rationale = item.get("$rationale")
    if rationale is not None:
        result["rationale"] = _normalize_text(rationale)

    prompt = item.get("$test")
    if prompt is not None:
        result["prompt"] = prompt

    return result


def _convert_section_v1_to_v2(section: Mapping[str, Any]) -> Dict[str, Any]:
    """Recursively convert a v1 criteria section into the v2 structure."""
    if not isinstance(section, Mapping):
        raise ValueError("criteria sections must be mappings")

    result: Dict[str, Any] = {}
    description = section.get("$description", section.get("$desc"))
    if description is not None:
        result["description"] = _normalize_text(description)

    for raw_key, raw_value in section.items():
        key = str(raw_key)
        if key in {"$description", "$desc"}:
            continue
        if _is_v1_item(raw_value):
            result[key] = _convert_item_v1_to_v2(raw_value)
        else:
            result[key] = _convert_section_v1_to_v2(raw_value)
    return result


def upgrade_to_v2(data: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a criteria definition converted to schema version 2."""
    criteria = data.get("criteria")
    if not isinstance(criteria, Mapping):
        raise ValueError("criteria definition must be a mapping")

    converted = _convert_section_v1_to_v2(criteria)
    return {
        "schema_version": 2,
        "criteria": converted,
    }


__all__ = ["upgrade_to_v2"]
