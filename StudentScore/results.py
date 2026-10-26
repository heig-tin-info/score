"""Run the ``command`` leaves of a version 3 criteria file and score them.

The contract is the Quiz platform's (``results-1.json``):

- a command is an argv list run without a shell, with a timeout, in the
  directory of the criteria file;
- its result is the last non-empty stdout line when it reads ``n/m``
  (``n`` may be decimal, ``m > 0``); otherwise the exit code: ``0`` gives
  ``1/1``, anything else ``0/1``;
- its ``log`` is the combined stdout and stderr, tail-capped to 8 KiB;
- ``results.json`` maps each command leaf's dotted id to
  ``{"score": "n/m", "log": "..."}`` and stays under 256 KiB.

Points from a fraction ``f = n/m`` (``n`` clamped to ``[0, m]``): a positive
leaf earns ``max * f``, a penalty (negative max) ``max * (1 - f)``, a bonus
``bonus * f``; rounded to 0.01.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import threading
from typing import Any, Dict, Iterable, List, Mapping, Tuple

from .schema import iter_leaves


RESULTS_SCHEMA_URL = "https://quiz.chevallier.io/schemas/results-1.json"
DEFAULT_TIMEOUT = 120.0
LOG_CAP = 8 * 1024
FILE_CAP = 256 * 1024

_FRACTION = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*$")
_TRUNCATED = "[... truncated]\n"


class InvalidFraction(ValueError):
    """Raised when a score is not a valid ``n/m`` with ``m > 0``."""


def parse_fraction(text: str) -> Tuple[float, float]:
    """Return ``(n, m)`` from ``"n/m"``; raise :class:`InvalidFraction` otherwise."""
    match = _FRACTION.fullmatch(text)
    if match is None:
        raise InvalidFraction(f"not a fraction n/m: {text!r}")
    n, m = float(match.group(1)), float(match.group(2))
    if m <= 0:
        raise InvalidFraction(f"the denominator must be positive: {text!r}")
    return n, m


def round_points(value: float) -> float:
    """Round to 0.01, half away from zero (no half-point rounding)."""
    rounded = float(Decimal(repr(value)).quantize(Decimal("0.01"), ROUND_HALF_UP))
    return rounded + 0.0  # no -0.0


def format_points(value: float) -> str:
    """Render points with at most two decimals, never in exponent form."""
    text = f"{round_points(value):.2f}".rstrip("0").rstrip(".")
    return "0" if text == "-0" else text


def leaf_points(leaf: Mapping[str, Any], n: float, m: float) -> float:
    """Points of a normalized leaf (``$points`` or ``$bonus``) for ``n/m``."""
    ratio = max(0.0, min(n, m)) / m
    if "$bonus" in leaf:
        return round_points(float(leaf["$bonus"][1]) * ratio)
    maximum = float(leaf["$points"][1])
    if maximum < 0:
        return round_points(maximum * (1.0 - ratio))
    return round_points(maximum * ratio)


def fraction_from_output(stdout: str, returncode: int) -> Tuple[str, str | None]:
    """Return ``(score, note)`` from a command's stdout and exit code.

    ``note`` explains a fallback worth a line in the log (a last line that
    looks like a fraction but has ``m = 0``).
    """
    lines = [line for line in stdout.splitlines() if line.strip()]
    note = None
    if lines:
        last = lines[-1]
        try:
            parse_fraction(last)
        except InvalidFraction as exc:
            if _FRACTION.fullmatch(last):
                note = f"[score] ignored {exc}; using the exit code"
        else:
            return re.sub(r"\s+", "", last), None
    return ("1/1" if returncode == 0 else "0/1"), note


def tail_cap(text: str, cap: int = LOG_CAP) -> str:
    """Keep the end of ``text`` within ``cap`` UTF-8 bytes."""
    data = text.encode("utf-8")
    if len(data) <= cap:
        return text
    keep = cap - len(_TRUNCATED.encode("utf-8"))
    tail = data[len(data) - keep :].decode("utf-8", errors="ignore")
    return _TRUNCATED + tail


@dataclass
class CommandResult:
    """The outcome of one command leaf."""

    score: str
    log: str


def _pump(
    stream: Any, own: List[str], combined: List[str], lock: threading.Lock
) -> None:
    for raw in iter(stream.readline, b""):
        line = raw.decode("utf-8", errors="replace")
        own.append(line)
        with lock:
            combined.append(line)
    stream.close()


def _kill(process: subprocess.Popen) -> None:
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:  # pragma: no cover - Windows
            process.kill()
    except (ProcessLookupError, PermissionError):  # pragma: no cover - raced
        pass


def run_command(argv: List[str], cwd: Path, timeout: float) -> CommandResult:
    """Run one argv without a shell and turn its outcome into a score and a log."""
    try:
        process = subprocess.Popen(
            argv,
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=os.name == "posix",
        )
    except OSError as exc:
        return CommandResult("0/1", f"[score] cannot run {argv[0]!r}: {exc}\n")

    stdout: List[str] = []
    stderr: List[str] = []
    combined: List[str] = []
    lock = threading.Lock()
    pumps = [
        threading.Thread(target=_pump, args=(process.stdout, stdout, combined, lock)),
        threading.Thread(target=_pump, args=(process.stderr, stderr, combined, lock)),
    ]
    for pump in pumps:
        pump.daemon = True
        pump.start()

    timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill(process)
        process.wait()
    for pump in pumps:
        # A grandchild may keep a pipe open after a kill: do not wait forever.
        pump.join(timeout=5)

    with lock:
        log = "".join(combined)
    if timed_out:
        log += f"\n[score] timeout after {timeout:g} s\n"
        return CommandResult("0/1", tail_cap(log))

    score, note = fraction_from_output("".join(stdout), process.returncode)
    if note:
        log += f"\n{note}\n"
    return CommandResult(score, tail_cap(log))


def command_leaves(data: Mapping[str, Any]) -> Iterable[Tuple[str, Dict[str, Any]]]:
    """Yield ``(dotted_id, leaf)`` for every leaf carrying a ``command``."""
    for cid, leaf in iter_leaves(dict(data)):
        if "$command" in leaf:
            yield cid, leaf


def build_results(outcomes: Mapping[str, CommandResult]) -> Dict[str, Any]:
    """Return the ``results.json`` payload, its logs shrunk to fit 256 KiB."""
    cap = LOG_CAP
    while True:
        criteria: Dict[str, Any] = {}
        for cid, outcome in outcomes.items():
            entry: Dict[str, Any] = {"score": outcome.score}
            if outcome.log:
                entry["log"] = tail_cap(outcome.log, cap)
            criteria[cid] = entry
        payload = {"$schema": RESULTS_SCHEMA_URL, "criteria": criteria}
        size = len(json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"))
        if size <= FILE_CAP or cap <= 256:
            return payload
        cap //= 2


def load_results(path: Path) -> Dict[str, Tuple[float, float]]:
    """Read a ``results.json`` and return ``{id: (n, m)}`` of its valid scores.

    An entry whose score is not a valid fraction is left out, like an absent
    one: its leaf then earns 0 points.
    """
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    criteria = payload.get("criteria") if isinstance(payload, dict) else None
    if not isinstance(criteria, dict):
        raise ValueError(f"{path}: results must hold a `criteria` object")
    fractions: Dict[str, Tuple[float, float]] = {}
    for cid, entry in criteria.items():
        score = entry.get("score") if isinstance(entry, dict) else None
        if not isinstance(score, str):
            continue
        try:
            fractions[str(cid)] = parse_fraction(score)
        except InvalidFraction:
            continue
    return fractions


def command_totals(
    data: Mapping[str, Any],
    fractions: Mapping[str, Tuple[float, float]],
) -> Tuple[float, float]:
    """Return ``(points, max)`` over the command leaves only.

    ``max`` sums the positive maxima; ``points`` sums every command leaf's
    points (positive, penalty and bonus). A leaf without a result earns 0.
    """
    points = 0.0
    maximum = 0.0
    for cid, leaf in command_leaves(data):
        if "$points" in leaf and float(leaf["$points"][1]) > 0:
            maximum += float(leaf["$points"][1])
        if cid in fractions:
            points += leaf_points(leaf, *fractions[cid])
    return round_points(points), round_points(maximum)


__all__ = [
    "DEFAULT_TIMEOUT",
    "RESULTS_SCHEMA_URL",
    "CommandResult",
    "InvalidFraction",
    "build_results",
    "command_leaves",
    "command_totals",
    "format_points",
    "fraction_from_output",
    "leaf_points",
    "load_results",
    "parse_fraction",
    "round_points",
    "run_command",
    "tail_cap",
]
