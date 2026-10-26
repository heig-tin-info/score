"""High-level helpers to compute grades from validated criteria data."""

from __future__ import annotations

from collections import namedtuple
import copy
from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping, TextIO, Tuple

from . import yaml
from .results import command_leaves, leaf_points
from .schema import Criteria


Points = namedtuple("Points", ["got", "total", "bonus"])


@dataclass
class _Accumulator:
    """Internal structure used while aggregating points."""

    got: float = 0.0
    total: float = 0.0
    bonus: float = 0.0


class Score:
    """Compute aggregate grade statistics from a criteria definition."""

    def __init__(
        self,
        data: str | TextIO | Mapping[str, Any],
        results: Mapping[str, Tuple[float, float]] | None = None,
    ) -> None:
        """Load YAML content, validate it, and store normalized data.

        ``results`` maps dotted ids to ``(n, m)`` fractions (from a
        ``results.json``): when given, every ``command`` leaf earns its points
        from its fraction, and 0 when it has none, instead of its
        ``awarded_points``.
        """
        normalized_data: Mapping[str, Any]

        if hasattr(data, "read"):
            normalized_data = Criteria(yaml.load(data, Loader=yaml.FullLoader))
        elif isinstance(data, str):
            with open(data, "rt", encoding="utf8") as file_handle:
                normalized_data = Criteria(
                    yaml.load(file_handle, Loader=yaml.FullLoader)
                )
        else:
            normalized_data = Criteria(data)

        if results is not None:
            normalized_data = copy.deepcopy(dict(normalized_data))
            for cid, leaf in command_leaves(normalized_data):
                key = "$points" if "$points" in leaf else "$bonus"
                fraction = results.get(cid)
                earned = leaf_points(leaf, *fraction) if fraction else 0.0
                leaf[key] = [earned, leaf[key][1]]

        self.data = normalized_data

    @property
    def mark(self) -> float:
        """Return the final mark on a 1.0 to 6.0 grading scale."""
        if self.total == 0:
            raise ValueError("Total is zero points")
        return max(1.0, min(6.0, round(5.0 * self.got / self.total + 1.0, 1)))

    @property
    def points(self) -> Points:
        """Return the aggregated points, bonus, and total values."""
        return self._get_points(self.data)

    @property
    def total(self) -> float:
        """Return the total number of available points."""
        return self.points.total

    @property
    def bonus(self) -> float:
        """Return the total bonus collected for the criteria tree."""
        return self.points.bonus

    @property
    def got(self) -> float:
        """Return the number of points obtained, including bonus."""
        return self.points.got

    @property
    def success(self) -> bool:
        """Return True when the final mark reaches the passing threshold."""
        return self.mark >= 4.0

    def _get_points(self, data: Mapping[str, Any]) -> Points:
        """Recursively aggregate points stored in a criteria mapping."""
        accumulator = _Accumulator()
        for key, value in data.items():
            if key in {"schema_version", "grading"}:
                continue
            if isinstance(value, MutableMapping):
                nested_points = self._get_points(value)
                accumulator.got += nested_points.got
                accumulator.total += nested_points.total
                accumulator.bonus += nested_points.bonus
            elif isinstance(value, list) and key in {"$points", "$pts"}:
                obtained, available = value
                obtained_value = float(obtained)
                available_value = float(available)
                accumulator.got += obtained_value
                accumulator.total += available_value if available_value > 0 else 0.0
            elif isinstance(value, list) and key == "$bonus":
                obtained, _ = value
                obtained_value = float(obtained)
                accumulator.bonus += obtained_value
                accumulator.got += obtained_value
        return Points(
            got=accumulator.got, total=accumulator.total, bonus=accumulator.bonus
        )
