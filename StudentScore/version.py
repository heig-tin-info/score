"""Expose the installed package version."""

from __future__ import annotations

from importlib import metadata


try:
    __version__ = metadata.version("StudentScore")
except metadata.PackageNotFoundError:
    __version__ = "0.0.0"

version = __version__
__version_tuple__ = tuple(__version__.split("."))
