"""LLM-assisted grading: send the grading prompt to Claude and get points back.

Kept optional: the ``anthropic`` SDK is imported lazily so the base package
installs without it. Install the extra with ``pip install StudentScore[llm]``.
The model returns a strict JSON object keyed by criterion id, so no free-form
parsing is needed. Used by ``score grade --llm`` for the deadline / milestone
grading tier; the per-commit CI tier stays deterministic and never calls this.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Tuple

from .grading import _iter_leaves, build_prompt

DEFAULT_MODEL = "claude-opus-4-8"

_DEFAULT_CONTEXT = (
    "You are an impartial, benevolent grader. Award points strictly from the "
    "evidence in the submitted files, following each criterion's instructions."
)


def _criteria_ids(data: Mapping[str, Any]) -> List[str]:
    """Return the dotted ids of every leaf criterion, in document order."""
    criteria = data.get("criteria") or {}
    return [".".join(path) for path, _ in _iter_leaves(criteria)]


def _results_schema(ids: List[str]) -> Dict[str, Any]:
    """Build a strict JSON schema forcing one graded entry per criterion."""
    properties = {
        cid: {
            "type": "object",
            "properties": {
                "awarded_points": {"type": "number"},
                "rationale": {"type": "string"},
            },
            "required": ["awarded_points", "rationale"],
            "additionalProperties": False,
        }
        for cid in ids
    }
    return {
        "type": "object",
        "properties": properties,
        "required": ids,
        "additionalProperties": False,
    }


def _render_sources(sources: Mapping[str, str]) -> str:
    """Render the collected source files as one delimited text block."""
    if not sources:
        return "(No source files were provided.)"
    blocks = []
    for name, text in sources.items():
        blocks.append(f"### File: {name}\n```\n{text}\n```")
    return "\n\n".join(blocks)


def grade_with_llm(
    data: Mapping[str, Any],
    sources: Mapping[str, str],
    *,
    model: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    """Grade a submission with Claude and return a results mapping.

    ``data`` is normalized criteria (from ``Criteria``); ``sources`` maps file
    names to their text. Returns ``{criterion_id: {awarded_points, rationale}}``,
    ready to feed to :func:`StudentScore.apply.apply_results`.
    """
    try:
        import anthropic
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "LLM grading requires the 'anthropic' package. "
            "Install it with: pip install 'StudentScore[llm]'"
        ) from exc

    ids = _criteria_ids(data)
    if not ids:
        return {}

    grading = data.get("grading") or {}
    context = grading.get("context") or _DEFAULT_CONTEXT
    if isinstance(context, list):
        context = "\n".join(str(item) for item in context)

    prompt = build_prompt(data)
    user_content = (
        f"{prompt}\n\n"
        "# Submitted files\n\n"
        f"{_render_sources(sources)}\n\n"
        "Grade every criterion listed above using the required JSON object."
    )

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=16000,
        system=context,
        thinking={"type": "adaptive"},
        output_config={
            "effort": "high",
            "format": {"type": "json_schema", "schema": _results_schema(ids)},
        },
        messages=[{"role": "user", "content": user_content}],
    )

    if response.stop_reason == "refusal":  # pragma: no cover - safety path
        raise RuntimeError("The model refused to grade this submission.")

    text = next((b.text for b in response.content if b.type == "text"), "")
    return json.loads(text)


def collect_sources(patterns: List[str], root: str = ".") -> Dict[str, str]:
    """Read files matching the given globs (relative to ``root``) into a mapping."""
    from pathlib import Path

    base = Path(root)
    collected: Dict[str, str] = {}
    for pattern in patterns:
        for path in sorted(base.glob(pattern)):
            if path.is_file():
                try:
                    collected[str(path.relative_to(base))] = path.read_text(
                        encoding="utf-8"
                    )
                except (OSError, UnicodeDecodeError):
                    continue
    return collected


__all__ = ["grade_with_llm", "collect_sources", "DEFAULT_MODEL"]
