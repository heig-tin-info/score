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
# Same rule as the heig-classroom platform: the tag doubles as a CLI argument
# (`score grade --milestone <name>`) and must stay shell- and YAML-friendly.
_MILESTONE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,49}$")
_MISSING = object()
# Version 3: a criterion name is one segment of a dotted id.
_NAME_PATTERN = re.compile(r"^[^.\s]+$")
_WILDCARD_PATTERN = re.compile(r"[*?\[]")
_MAX_COMMAND_ARGS = 20


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


def _validate_milestone(
    value: Any,
    errors: List[Dict[str, Any]],
    path: Sequence[Any],
) -> str | None:
    """Validate a per-criterion milestone tag (intermediate review marker)."""
    if isinstance(value, str) and _MILESTONE_PATTERN.fullmatch(value):
        return value
    _add_error(
        errors,
        path,
        "milestone must match [a-z0-9][a-z0-9_-]* (max 50 characters)",
    )
    return None


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
        "$milestone",
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
            continue

        if key == "$milestone":
            tag = _validate_milestone(raw_value, errors, _extend_path(path, key))
            if tag is not None:
                result[key] = tag

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
        "milestone",
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

        if key == "milestone":
            tag = _validate_milestone(raw_value, errors, _extend_path(path, key))
            if tag is not None:
                result["$milestone"] = tag
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


# ---------------------------------------------------------------------------
# Schema version 3 (the Quiz platform's criteria-3 contract).
# ---------------------------------------------------------------------------

_V3_LEAF_FIELDS = {
    "description",
    "desc",
    "max_points",
    "bonus_points",
    "awarded_points",
    "prompt",
    "command",
    "milestone",
    # StudentScore extension: `score apply` / `score grade --llm` write it.
    "rationale",
}
# A mapping carrying one of these keys is a leaf, never a section.
_V3_LEAF_MARKERS = _V3_LEAF_FIELDS - {"description"}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _v3_amount(
    value: Any,
    errors: List[Dict[str, Any]],
    path: Sequence[Any],
    *,
    bonus: bool,
) -> float | None:
    """Validate a ``max_points``/``bonus_points`` value: a number only."""
    if isinstance(value, str) and _PERCENT_PATTERN.fullmatch(value.strip()):
        _add_error(
            errors,
            path,
            "percentages are not accepted in schema version 3: give a number",
        )
        return None
    if not _is_number(value):
        _add_error(errors, path, "points must be a number")
        return None
    amount = float(value)
    if amount == 0:
        _add_error(errors, path, "No points given to this criteria.")
        return None
    if bonus and amount < 0:
        _add_error(errors, path, "bonus_points must be positive")
        return None
    return amount


def _validate_v3_command(
    value: Any,
    errors: List[Dict[str, Any]],
    path: Sequence[Any],
) -> List[str] | None:
    """A command is an argv list of 1 to 20 strings, never a shell string."""
    if (
        not isinstance(value, list)
        or not 1 <= len(value) <= _MAX_COMMAND_ARGS
        or not all(isinstance(item, str) for item in value)
        or not value[0]
    ):
        _add_error(
            errors,
            path,
            f"command must be a list of 1 to {_MAX_COMMAND_ARGS} strings "
            "(argv, no shell), the first one non-empty",
        )
        return None
    return list(value)


def _validate_v3_item(
    value: Dict[Any, Any],
    errors: List[Dict[str, Any]],
    path: Sequence[Any],
) -> Dict[str, Any]:
    """Validate a version 3 leaf and normalize it to the internal layout."""
    result: Dict[str, Any] = {}
    fields: Dict[str, Any] = {}
    for raw_key, raw_value in value.items():
        key = str(raw_key)
        if key not in _V3_LEAF_FIELDS:
            message = "unrecognized criteria field"
            if key == "test":
                message += " (`test` is version 2 only: use `command` or `prompt`)"
            _add_error(errors, _extend_path(path, key), message)
            continue
        fields[key] = raw_value

    if "description" in fields and "desc" in fields:
        _add_error(errors, path, "use either description or desc, not both")
    text = fields.get("description", fields.get("desc", _MISSING))
    if text is _MISSING:
        _add_error(errors, path, "description must be provided for each criterion")
    elif not isinstance(text, str):
        _add_error(
            errors,
            _extend_path(path, "description" if "description" in fields else "desc"),
            "value must be a string",
        )
    else:
        result["$description"] = text

    if "rationale" in fields:
        rationale = _ensure_text_or_text_list(
            fields["rationale"], errors, _extend_path(path, "rationale")
        )
        if rationale is not None:
            result["$rationale"] = rationale

    if "prompt" in fields:
        if isinstance(fields["prompt"], str):
            result["$test"] = fields["prompt"]
        else:
            _add_error(errors, _extend_path(path, "prompt"), "value must be a string")

    if "command" in fields:
        command = _validate_v3_command(
            fields["command"], errors, _extend_path(path, "command")
        )
        if command is not None:
            result["$command"] = command

    if "milestone" in fields:
        tag = _validate_milestone(
            fields["milestone"], errors, _extend_path(path, "milestone")
        )
        if tag is not None:
            result["$milestone"] = tag

    awarded: float = 0.0
    if "awarded_points" in fields:
        if _is_number(fields["awarded_points"]):
            awarded = float(fields["awarded_points"])
        else:
            _add_error(
                errors,
                _extend_path(path, "awarded_points"),
                "awarded_points must be a number",
            )

    if "max_points" in fields and "bonus_points" in fields:
        _add_error(errors, path, "use either max_points or bonus_points, not both")
    elif "max_points" in fields:
        total = _v3_amount(
            fields["max_points"], errors, _extend_path(path, "max_points"), bonus=False
        )
        if total is not None:
            result["$points"] = [awarded, total]
    elif "bonus_points" in fields:
        total = _v3_amount(
            fields["bonus_points"],
            errors,
            _extend_path(path, "bonus_points"),
            bonus=True,
        )
        if total is not None:
            result["$bonus"] = [awarded, total]
    else:
        _add_error(errors, path, "either max_points or bonus_points must be provided")

    return result


def _validate_v3_section(
    value: Any,
    errors: List[Dict[str, Any]],
    path: Sequence[Any],
) -> Dict[str, Any]:
    """Validate a version 3 section: an optional description and children."""
    if not isinstance(value, dict):
        _add_error(errors, path, "criteria entries must be mappings")
        return {}

    result: Dict[str, Any] = {}
    for raw_key, raw_value in value.items():
        key = str(raw_key)
        if key == "description":
            text_value = _ensure_section_text(
                raw_value, errors, _extend_path(path, key)
            )
            if text_value is not None:
                result["$description"] = text_value
            continue
        child_path = _extend_path(path, key)
        if not _NAME_PATTERN.fullmatch(key):
            _add_error(
                errors, child_path, "a name may contain neither a dot nor a space"
            )
            continue
        if not isinstance(raw_value, dict):
            _add_error(errors, child_path, "criteria entries must be mappings")
            continue
        if {str(k) for k in raw_value} & _V3_LEAF_MARKERS:
            result[key] = _validate_v3_item(raw_value, errors, child_path)
        else:
            result[key] = _validate_v3_section(raw_value, errors, child_path)
    return result


def _iter_normalized_leaves(
    node: Dict[str, Any],
    prefix: Tuple[str, ...] = (),
) -> Iterable[Tuple[Tuple[str, ...], Dict[str, Any]]]:
    """Yield ``(path, leaf)`` for every normalized leaf of a criteria tree."""
    for key, value in node.items():
        if key.startswith("$") or not isinstance(value, dict):
            continue
        if "$points" in value or "$bonus" in value:
            yield prefix + (key,), value
        else:
            yield from _iter_normalized_leaves(value, prefix + (key,))


def _validate_v3_criteria(
    value: Any,
    errors: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Validate a version 3 tree and the range of its awarded points."""
    root = ("criteria",)
    result = _validate_v3_section(value, errors, root)
    for path, leaf in _iter_normalized_leaves(result):
        key = "$points" if "$points" in leaf else "$bonus"
        awarded, total = leaf[key]
        low, high = (0.0, total) if total > 0 else (total, 0.0)
        if not low <= awarded <= high:
            _add_error(
                errors,
                root + path + ("awarded_points",),
                "awarded_points ({awarded}) must lie between {low} and {high}",
                ctx={"awarded": awarded, "low": low, "high": high},
            )
            continue
        leaf[key] = [awarded, int(total) if total.is_integer() else total]
    return result


def iter_leaves(
    data: Dict[str, Any],
) -> Iterable[Tuple[str, Dict[str, Any]]]:
    """Yield ``(dotted_id, leaf)`` for every leaf of normalized criteria data."""
    for path, leaf in _iter_normalized_leaves(data.get("criteria") or {}):
        yield ".".join(path), leaf


def _validate_student(
    value: Any,
    errors: List[Dict[str, Any]],
    path: Sequence[Any],
) -> Dict[str, Any] | None:
    """Validate the structured student profile used for LLM-assisted grading."""
    if not isinstance(value, dict):
        _add_error(errors, path, "student must be a mapping")
        return None

    allowed_fields = {"level", "knows", "learning"}
    result: Dict[str, Any] = {}
    for raw_key, raw_value in value.items():
        key = str(raw_key)
        if key not in allowed_fields:
            _add_error(errors, _extend_path(path, key), "unrecognized student field")
            continue

        if key == "level":
            if not isinstance(raw_value, str):
                _add_error(errors, _extend_path(path, key), "level must be a string")
            else:
                result[key] = raw_value
            continue

        # "knows" and "learning" are lists of short strings.
        if isinstance(raw_value, list) and all(
            isinstance(item, str) for item in raw_value
        ):
            result[key] = raw_value
        else:
            _add_error(
                errors,
                _extend_path(path, key),
                f"{key} must be a list of strings",
            )

    return result


def _validate_grading(
    value: Any,
    errors: List[Dict[str, Any]],
    path: Sequence[Any],
    *,
    plain_sources: bool = False,
) -> Dict[str, Any]:
    """Validate the top-level ``grading`` block guiding LLM-assisted grading."""
    if not isinstance(value, dict):
        _add_error(errors, path, "grading must be a mapping")
        return {}

    allowed_fields = {"context", "student", "sources"}
    result: Dict[str, Any] = {}
    for raw_key, raw_value in value.items():
        key = str(raw_key)
        if key not in allowed_fields:
            _add_error(errors, _extend_path(path, key), "unrecognized grading field")
            continue

        if key == "context":
            text_value = _ensure_text_or_text_list(
                raw_value, errors, _extend_path(path, key), allow_none=False
            )
            if text_value is not None:
                result[key] = text_value
            continue

        if key == "sources":
            if isinstance(raw_value, list) and all(
                isinstance(item, str) for item in raw_value
            ):
                if plain_sources and any(
                    _WILDCARD_PATTERN.search(item) for item in raw_value
                ):
                    _add_error(
                        errors,
                        _extend_path(path, key),
                        "sources are plain paths (a directory ends with /), "
                        "no wildcard",
                    )
                else:
                    result[key] = raw_value
            else:
                _add_error(
                    errors,
                    _extend_path(path, key),
                    "sources must be a list of file globs (strings)",
                )
            continue

        if key == "student":
            student = _validate_student(raw_value, errors, _extend_path(path, key))
            if student is not None:
                result[key] = student

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
            if schema_version not in {1, 2, 3}:
                _add_error(
                    errors,
                    ("schema_version",),
                    "schema_version must be 1, 2 or 3",
                )

    criteria_value = normalized.get("criteria")
    if criteria_value is None:
        _add_error(errors, ("criteria",), "missing criteria definition")
        validated_criteria: Dict[str, Any] = {}
    elif schema_version == 3:
        validated_criteria = _validate_v3_criteria(criteria_value, errors)
    elif schema_version == 2:
        validated_criteria = _validate_v2_section(criteria_value, errors, ("criteria",))
    else:
        validated_criteria = _validate_section(criteria_value, errors, ("criteria",))

    grading_value = normalized.get("grading")
    validated_grading: Dict[str, Any] | None = None
    if grading_value is not None:
        if schema_version not in {2, 3}:
            _add_error(
                errors,
                ("grading",),
                "grading requires schema_version 2 or 3",
            )
        else:
            validated_grading = _validate_grading(
                grading_value,
                errors,
                ("grading",),
                plain_sources=schema_version == 3,
            )

    if errors:
        message = _format_validation_errors(errors)
        raise CriteriaValidationError(message, errors=errors)

    result = {"criteria": validated_criteria}
    if "schema_version" in normalized or schema_version >= 2:
        result["schema_version"] = schema_version
    if validated_grading is not None:
        result["grading"] = validated_grading

    return result


Criteria = _criteria

__all__ = ["Criteria", "CriteriaValidationError", "iter_leaves"]
