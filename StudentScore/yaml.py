"""Runtime wrapper ensuring PyYAML is available before parsing files."""

from __future__ import annotations

from importlib import import_module
from typing import IO, Any


try:
    _yaml = import_module("yaml")
except ModuleNotFoundError as exc:  # pragma: no cover - import side effect
    raise ImportError("PyYAML is required to parse grading criteria files.") from exc

FullLoader = _yaml.FullLoader
SafeDumper = _yaml.SafeDumper


def load(stream: IO[str] | str, *, Loader: Any | None = None) -> Any:
    """Proxy to ``yaml.load`` ensuring the ``FullLoader`` is used by default."""
    loader = Loader or FullLoader
    return _yaml.load(stream, Loader=loader)


def dump(
    data: Any,
    stream: IO[str] | None = None,
    *,
    Dumper: Any | None = None,
    **kwargs: Any,
) -> str | None:
    """Proxy to ``yaml.dump`` ensuring the ``SafeDumper`` is used by default."""
    dumper = Dumper or SafeDumper
    return _yaml.dump(data, stream=stream, Dumper=dumper, **kwargs)


__all__ = ["FullLoader", "SafeDumper", "dump", "load"]
