"""Runtime wrapper ensuring PyYAML is available before parsing files."""

from __future__ import annotations

from importlib import import_module
from typing import IO, Any


try:
    _yaml = import_module("yaml")
except ModuleNotFoundError as exc:  # pragma: no cover - import side effect
    raise ImportError("PyYAML is required to parse grading criteria files.") from exc

FullLoader = _yaml.FullLoader


def load(stream: IO[str] | str, *, Loader: Any | None = None) -> Any:
    """Proxy to ``yaml.load`` ensuring the ``FullLoader`` is used by default."""
    loader = Loader or FullLoader
    return _yaml.load(stream, Loader=loader)


__all__ = ["FullLoader", "load"]
