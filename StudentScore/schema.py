from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Sequence, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


class CriteriaValidationError(ValueError):
    """Raised when the grading criteria definition is invalid."""

    def __init__(self, message: str, *, errors: List[Dict[str, Any]]):
        super().__init__(message)
        self.errors = errors


_PERCENT_PATTERN = re.compile(r"^(-?\d+(?:\.\d+)?)%$")


def _ensure_text_or_text_list(value: Any) -> Union[str, List[str]]:
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise TypeError("value must be a string or a list of strings")


def _validate_pair(value: Any) -> List[Union[int, float]]:
    if isinstance(value, tuple):
        value = list(value)

    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError("points must be provided as a two-item sequence")
    if len(value) != 2:
        raise ValueError("points must contain exactly two entries")

    obtained, total = value

    try:
        total_value = int(total)
    except (TypeError, ValueError):
        raise TypeError("total points must be an integer") from None

    if isinstance(obtained, str):
        match = _PERCENT_PATTERN.fullmatch(obtained.strip())
        if not match:
            raise ValueError("percentage must match the form '42%' or '-10.5%'")
        percent_value = float(match.group(1))
        if not -100 <= percent_value <= 100:
            raise ValueError("percentage must be between -100% and 100%")
        obtained_value = abs(percent_value / 100.0) * total_value
    else:
        try:
            obtained_value = float(obtained)
        except (TypeError, ValueError):
            raise TypeError("points must be numeric or a percentage string") from None

    if total_value == 0:
        raise ValueError("No points given to this criteria.")
    if obtained_value < total_value < 0:
        raise ValueError(
            (
                f"Given points ({obtained_value}) cannot be smaller "
                f"than available penalty ({total_value})."
            )
        )
    if total_value < 0 < obtained_value:
        raise ValueError(
            (
                f"Given points ({obtained_value}) cannot be bigger "
                f"than zero with penalty criteria ({total_value})."
            )
        )
    if total_value > 0 > obtained_value:
        raise ValueError(
            f"Given points ({obtained_value}) cannot be smaller than zero."
        )
    if obtained_value > total_value > 0:
        raise ValueError(
            (
                f"Given points ({obtained_value}) cannot be greater than "
                f"available points ({total_value})."
            )
        )

    return [float(obtained_value), total_value]


class ItemModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    description: Union[str, List[str]] | None = Field(default=None, alias="$description")
    desc: Union[str, List[str]] | None = Field(default=None, alias="$desc")
    points: List[Union[int, float]] | None = Field(default=None, alias="$points")
    bonus: List[Union[int, float]] | None = Field(default=None, alias="$bonus")
    rationale: Union[str, List[str]] | None = Field(default=None, alias="$rationale")
    test: str | None = Field(default=None, alias="$test")

    @field_validator("description", "desc", "rationale", mode="before")
    @classmethod
    def validate_text_block(cls, value: Any) -> Any:
        if value is None:
            return value
        return _ensure_text_or_text_list(value)

    @field_validator("points", "bonus", mode="before")
    @classmethod
    def validate_pair(cls, value: Any) -> Any:
        if value is None:
            return value
        return _validate_pair(value)

    @model_validator(mode="after")
    def ensure_required_fields(self) -> "ItemModel":
        if self.description is None and self.desc is None:
            raise ValueError("either $description or $desc must be provided")
        if self.points is None and self.bonus is None:
            raise ValueError("either $points or $bonus must be provided")
        return self

    def as_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        if self.description is not None:
            data["$description"] = self.description
        if self.desc is not None:
            data["$desc"] = self.desc
        if self.points is not None:
            data["$points"] = self.points
        if self.bonus is not None:
            data["$bonus"] = self.bonus
        if self.rationale is not None:
            data["$rationale"] = self.rationale
        if self.test is not None:
            data["$test"] = self.test
        return data


class SectionModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    description: str | None = Field(default=None, alias="$description")
    desc: str | None = Field(default=None, alias="$desc")
    items: Dict[str, Union["SectionModel", ItemModel]] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def restructure(cls, value: Any) -> Dict[str, Any]:
        if not isinstance(value, dict):
            raise TypeError("section entries must be mappings")

        items: Dict[str, Any] = {}
        data: Dict[str, Any] = {}
        for key, item in value.items():
            if key in {"$description", "$desc"}:
                data[key] = item
            else:
                items[str(key)] = item
        data["items"] = items
        return data

    @field_validator("description", "desc", mode="before")
    @classmethod
    def ensure_text(cls, value: Any) -> Any:
        if value is None or isinstance(value, str):
            return value
        raise TypeError("section descriptions must be strings")

    @field_validator("items", mode="before")
    @classmethod
    def ensure_mapping(cls, value: Any) -> Dict[str, Any]:
        if not isinstance(value, dict):
            raise TypeError("section items must be a mapping of criteria")
        return value

    @model_validator(mode="after")
    def ensure_description_choice(self) -> "SectionModel":
        if self.description is not None and self.desc is not None:
            raise ValueError("use either $description or $desc, not both")
        return self

    def as_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        if self.description is not None:
            data["$description"] = self.description
        if self.desc is not None:
            data["$desc"] = self.desc
        for key, value in self.items.items():
            if isinstance(value, SectionModel):
                data[key] = value.as_dict()
            else:
                data[key] = value.as_dict()
        return data


class CriteriaModel(BaseModel):
    criteria: SectionModel

    def as_dict(self) -> Dict[str, Any]:
        return {"criteria": self.criteria.as_dict()}


def _format_location(parts: Iterable[Any]) -> str:
    filtered = [str(part) for part in parts if part not in {"items"}]
    return "/".join(filtered) if filtered else "<root>"


def _format_validation_errors(errors: List[Dict[str, Any]]) -> str:
    lines = ["Invalid criteria definition detected:"]
    for error in errors:
        location = _format_location(error.get("loc", ()))
        message = error.get("msg", "unknown validation error")
        lines.append(f"- {location}: {message}")
    return "\n".join(lines)


def Criteria(data: Any) -> Dict[str, Any]:
    try:
        model = CriteriaModel.model_validate(data)
    except ValidationError as exc:
        message = _format_validation_errors(exc.errors())
        raise CriteriaValidationError(message, errors=exc.errors()) from exc
    return model.as_dict()


__all__ = ["Criteria", "CriteriaValidationError"]
