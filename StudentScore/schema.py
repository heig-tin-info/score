"""Validation logic for StudentScore grading criteria definitions."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Sequence, Tuple


class CriteriaValidationError(ValueError):
    """Raised when the grading criteria definition is invalid."""

    def __init__(self, message: str, *, errors: List[Dict[str, Any]]):
        super().__init__(message)
        self.errors = errors


_PERCENT_PATTERN = re.compile(r"^(-?\d+(?:\.\d+)?)%$")
_MISSING = object()


def _add_error(
    errors: List[Dict[str, Any]],
    path: Sequence[Any],
    message: str,
    *,
    ctx: Dict[str, Any] | None = None,
) -> None:
    """Collect a validation error entry with contextual information."""
    error: Dict[str, Any] = {"loc": tuple(path), "msg": message}
    if ctx:
        error["ctx"] = ctx
    errors.append(error)


def _ensure_text_or_text_list(
    value: Any,
    errors: List[Dict[str, Any]],
    path: Sequence[Any],
    *,
    allow_none: bool = True,
) -> str | List[str] | None:
    """Return text or list of text values, recording validation errors when required."""
    if value is None and allow_none:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    _add_error(errors, path, "value must be a string or a list of strings")
    return None


def _ensure_section_text(
    value: Any,
    errors: List[Dict[str, Any]],
    path: Sequence[Any],
) -> str | None:
    """Return a section description when valid, otherwise add a validation error."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    _add_error(errors, path, "section descriptions must be strings")
    return None


def _validate_pair(
    value: Any,
    errors: List[Dict[str, Any]],
    path: Sequence[Any],
) -> List[float | int] | None:
    """Validate a tuple or list of points and return a normalized list when valid."""
    if isinstance(value, tuple):
        value = list(value)

    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        _add_error(
            errors,
            path,
            "points must be provided as a two-item sequence",
        )
        return None
    if len(value) != 2:
        _add_error(errors, path, "points must contain exactly two entries")
        return None

    obtained, total = value

    try:
        total_value = int(total)
    except (TypeError, ValueError):
        _add_error(errors, path, "total points must be an integer")
        return None

    if isinstance(obtained, str):
        match = _PERCENT_PATTERN.fullmatch(obtained.strip())
        if not match:
            _add_error(
                errors,
                path,
                "percentage must match the form '42%' or '-10.5%'",
            )
            return None
        percent_value = float(match.group(1))
        if not -100 <= percent_value <= 100:
            _add_error(
                errors,
                path,
                "percentage must be between -100% and 100%",
            )
            return None
        obtained_value = abs(percent_value / 100.0) * total_value
    else:
        try:
            obtained_value = float(obtained)
        except (TypeError, ValueError):
            _add_error(
                errors,
                path,
                "points must be numeric or a percentage string",
            )
            return None

    if total_value == 0:
        _add_error(errors, path, "No points given to this criteria.")
        return None
    if obtained_value < total_value < 0:
        _add_error(
            errors,
            path,
            (
                "Given points ({obtained}) cannot be smaller "
                "than available penalty ({total})."
            ),
            ctx={"obtained": obtained_value, "total": total_value},
        )
        return None
    if total_value < 0 < obtained_value:
        _add_error(
            errors,
            path,
            (
                "Given points ({obtained}) cannot be bigger "
                "than zero with penalty criteria ({total})."
            ),
            ctx={"obtained": obtained_value, "total": total_value},
        )
        return None
    if total_value > 0 > obtained_value:
        _add_error(
            errors,
            path,
            "Given points ({obtained}) cannot be smaller than zero.",
            ctx={"obtained": obtained_value},
        )
        return None
    if obtained_value > total_value > 0:
        _add_error(
            errors,
            path,
            (
                "Given points ({obtained}) cannot be greater than "
                "available points ({total})."
            ),
            ctx={"obtained": obtained_value, "total": total_value},
        )
        return None

    return [float(obtained_value), total_value]


def _format_location(parts: Iterable[Any]) -> str:
    """Return a slash separated string describing where an error occurred."""
    filtered = [str(part) for part in parts if part not in {"items"}]
    return "/".join(filtered) if filtered else "<root>"


def _format_validation_errors(errors: List[Dict[str, Any]]) -> str:
    """Build a human readable message from collected validation errors."""
    lines = ["Invalid criteria definition detected:"]
    for error in errors:
        location = _format_location(error.get("loc", ()))
        message = error.get("msg", "unknown validation error")
        context = error.get("ctx")
        if isinstance(message, str) and "{" in message and isinstance(context, dict):
            try:
                message = message.format(**context)
            except (IndexError, KeyError, ValueError):  # pragma: no cover - defensive
                pass
        lines.append(f"- {location}: {message}")
    return "\n".join(lines)


def _extend_path(path: Sequence[Any], *suffix: Any) -> Tuple[Any, ...]:
    """Return a tuple that extends the provided path with the
    given suffix components."""
    return tuple(path) + suffix


def _validate_item(
    value: Dict[Any, Any],
    errors: List[Dict[str, Any]],
    path: Sequence[Any],
) -> Dict[str, Any]:
    """Validate a criteria item definition and return a normalized mapping."""
    allowed_fields = {
        "$description",
        "$desc",
        "$points",
        "$bonus",
        "$rationale",
        "$test",
    }
    result: Dict[str, Any] = {}
    has_description = False
    has_desc = False
    has_points = False
    has_bonus = False

    for raw_key, raw_value in value.items():
        key = str(raw_key)
        if key not in allowed_fields:
            _add_error(errors, _extend_path(path, key), "unrecognized criteria field")
            continue

        if key in {"$description", "$desc"}:
            text_value = _ensure_text_or_text_list(
                raw_value, errors, _extend_path(path, key), allow_none=False
            )
            if text_value is not None:
                result[key] = text_value
                if key == "$description":
                    has_description = True
                else:
                    has_desc = True
            continue

        if key == "$rationale":
            text_value = _ensure_text_or_text_list(
                raw_value, errors, _extend_path(path, key), allow_none=True
            )
            if text_value is not None:
                result[key] = text_value
            continue

        if key in {"$points", "$bonus"}:
            pair = _validate_pair(raw_value, errors, _extend_path(path, key))
            if pair is not None:
                result[key] = pair
                if key == "$points":
                    has_points = True
                else:
                    has_bonus = True
            continue

        if key == "$test":
            if not isinstance(raw_value, str):
                _add_error(errors, _extend_path(path, key), "value must be a string")
            else:
                result[key] = raw_value

    if has_description and has_desc:
        _add_error(
            errors,
            path,
            "use either $description or $desc, not both",
        )
    if not has_description and not has_desc:
        _add_error(
            errors,
            path,
            "either $description or $desc must be provided",
        )
    if not has_points and not has_bonus:
        _add_error(
            errors,
            path,
            "either $points or $bonus must be provided",
        )

    return result


def _validate_entry(
    value: Any,
    errors: List[Dict[str, Any]],
    path: Sequence[Any],
) -> Dict[str, Any]:
    """Choose between item or section validation based on the provided value."""
    if not isinstance(value, dict):
        _add_error(errors, path, "criteria entries must be mappings")
        return {}

    keys = {str(k) for k in value.keys()}
    if keys and all(key.startswith("$") for key in keys):
        return _validate_item(value, errors, path)
    return _validate_section(value, errors, path)


def _validate_section(
    value: Dict[Any, Any],
    errors: List[Dict[str, Any]],
    path: Sequence[Any],
) -> Dict[str, Any]:
    """Validate a criteria section definition and normalize all nested entries."""
    if not isinstance(value, dict):
        _add_error(errors, path, "section entries must be mappings")
        return {}

    result: Dict[str, Any] = {}
    has_description = False
    has_desc = False

    for raw_key, raw_value in value.items():
        key = str(raw_key)
        if key in {"$description", "$desc"}:
            text_value = _ensure_section_text(
                raw_value, errors, _extend_path(path, key)
            )
            if text_value is not None:
                result[key] = text_value
                if key == "$description":
                    has_description = True
                else:
                    has_desc = True
            continue

        result[key] = _validate_entry(raw_value, errors, _extend_path(path, key))

    if has_description and has_desc:
        _add_error(
            errors,
            path,
            "use either $description or $desc, not both",
        )

    return result


def _validate_v2_entry(
    value: Any,
    errors: List[Dict[str, Any]],
    path: Sequence[Any],
) -> Dict[str, Any]:
    """Dispatch version 2 entries to either section or item validators."""
    if not isinstance(value, dict):
        _add_error(errors, path, "criteria entries must be mappings")
        return {}

    keys = {str(k) for k in value.keys()}
    if {"awarded_points", "max_points", "bonus_points"} & keys:
        return _validate_v2_item(value, errors, path)
    return _validate_v2_section(value, errors, path)


def _validate_v2_section(
    value: Dict[Any, Any],
    errors: List[Dict[str, Any]],
    path: Sequence[Any],
) -> Dict[str, Any]:
    """Validate a version 2 section definition."""
    if not isinstance(value, dict):
        _add_error(errors, path, "section entries must be mappings")
        return {}

    result: Dict[str, Any] = {}
    description_value = value.get("description")
    if description_value is not None:
        text_value = _ensure_section_text(
            description_value, errors, _extend_path(path, "description")
        )
        if text_value is not None:
            result["$description"] = text_value

    for raw_key, raw_value in value.items():
        key = str(raw_key)
        if key == "description":
            continue
        result[key] = _validate_v2_entry(raw_value, errors, _extend_path(path, key))

    return result


def _validate_v2_item(
    value: Dict[Any, Any],
    errors: List[Dict[str, Any]],
    path: Sequence[Any],
) -> Dict[str, Any]:
    """Validate a version 2 item definition and normalize it."""
    allowed_fields = {
        "description",
        "max_points",
        "bonus_points",
        "awarded_points",
        "rationale",
        "prompt",
    }
    result: Dict[str, Any] = {}
    has_description = False
    awarded_points: Any = _MISSING
    max_points: Any = _MISSING
    bonus_points: Any = _MISSING

    for raw_key, raw_value in value.items():
        key = str(raw_key)
        if key not in allowed_fields:
            _add_error(errors, _extend_path(path, key), "unrecognized criteria field")
            continue

        if key == "description":
            text_value = _ensure_text_or_text_list(
                raw_value, errors, _extend_path(path, key), allow_none=False
            )
            if text_value is not None:
                result["$description"] = text_value
                has_description = True
            continue

        if key == "rationale":
            text_value = _ensure_text_or_text_list(
                raw_value, errors, _extend_path(path, key), allow_none=True
            )
            if text_value is not None:
                result["$rationale"] = text_value
            continue

        if key == "prompt":
            if not isinstance(raw_value, str):
                _add_error(errors, _extend_path(path, key), "value must be a string")
            else:
                result["$test"] = raw_value
            continue

        if key == "awarded_points":
            awarded_points = raw_value
            continue

        if key == "max_points":
            max_points = raw_value
            continue

        if key == "bonus_points":
            bonus_points = raw_value
            continue

    if not has_description:
        _add_error(
            errors,
            path,
            "description must be provided for each criterion",
        )

    if awarded_points is _MISSING:
        _add_error(
            errors,
            _extend_path(path, "awarded_points"),
            "awarded_points must be provided",
        )

    if max_points is not _MISSING and bonus_points is not _MISSING:
        _add_error(
            errors,
            path,
            "use either max_points or bonus_points, not both",
        )

    pair: List[float | int] | None = None
    if max_points is not _MISSING:
        if awarded_points is not _MISSING:
            pair = _validate_pair(
                [awarded_points, max_points],
                errors,
                _extend_path(path, "max_points"),
            )
            if pair is not None:
                result["$points"] = pair
    elif bonus_points is not _MISSING:
        if awarded_points is not _MISSING:
            pair = _validate_pair(
                [awarded_points, bonus_points],
                errors,
                _extend_path(path, "bonus_points"),
            )
            if pair is not None:
                result["$bonus"] = pair
    else:
        _add_error(
            errors,
            path,
            "either max_points or bonus_points must be provided",
        )

    return result


def _criteria(data: Any) -> Dict[str, Any]:
    """Normalize a criteria definition and raise if the structure is invalid."""
    errors: List[Dict[str, Any]] = []

    if not isinstance(data, dict):
        _add_error(errors, (), "criteria definition must be a mapping")
        normalized: Dict[str, Any] = {}
    else:
        normalized = {str(key): value for key, value in data.items()}

    schema_version = 1
    if "schema_version" in normalized:
        try:
            schema_version = int(normalized["schema_version"])
        except (TypeError, ValueError):
            _add_error(
                errors,
                ("schema_version",),
                "schema_version must be an integer",
            )
        else:
            if schema_version not in {1, 2}:
                _add_error(
                    errors,
                    ("schema_version",),
                    "schema_version must be either 1 or 2",
                )

    criteria_value = normalized.get("criteria")
    if criteria_value is None:
        _add_error(errors, ("criteria",), "missing criteria definition")
        validated_criteria: Dict[str, Any] = {}
    elif schema_version == 2:
        validated_criteria = _validate_v2_section(criteria_value, errors, ("criteria",))
    else:
        validated_criteria = _validate_section(criteria_value, errors, ("criteria",))

    if errors:
        message = _format_validation_errors(errors)
        raise CriteriaValidationError(message, errors=errors)

    result = {"criteria": validated_criteria}
    if "schema_version" in normalized or schema_version == 2:
        result["schema_version"] = schema_version

    return result


Criteria = _criteria

__all__ = ["Criteria", "CriteriaValidationError"]
