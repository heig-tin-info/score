"""Assemble an LLM-ready grading prompt from a normalized criteria definition.

The prompt gathers three sources of guidance carried by a version 2 criteria
file: the global ``grading.context`` (the corrector's role and rules), the
``grading.student`` profile (level and known/learning topics), and the per
criterion ``prompt`` instructions describing how each point should be awarded.
No LLM call happens here; :func:`build_prompt` only renders the text.
"""

from __future__ import annotations

from typing import Any, Iterator, List, Mapping, Tuple


def _as_text(value: Any) -> str:
    """Render a string or list-of-strings value as a single block of text."""
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    return str(value)


def _iter_leaves(
    node: Mapping[str, Any],
    prefix: Tuple[str, ...] = (),
) -> Iterator[Tuple[Tuple[str, ...], Mapping[str, Any]]]:
    """Yield ``(path, item)`` pairs for every leaf criterion in the tree."""
    for key, value in node.items():
        if not isinstance(key, str) or key.startswith("$"):
            continue
        if not isinstance(value, Mapping):
            continue
        child_keys = {str(k) for k in value.keys()}
        if "$points" in child_keys or "$bonus" in child_keys:
            yield prefix + (key,), value
        else:
            yield from _iter_leaves(value, prefix + (key,))


def _student_block(student: Mapping[str, Any]) -> str:
    """Render the student profile section from its structured fields."""
    lines: List[str] = ["# Profil de l'étudiant"]
    level = student.get("level")
    if level:
        lines.append(f"\nNiveau : {level}")
    knows = student.get("knows")
    if knows:
        lines.append("\nAcquis :")
        lines.extend(f"- {item}" for item in knows)
    learning = student.get("learning")
    if learning:
        lines.append("\nEn cours d'apprentissage (à ne pas pénaliser durement) :")
        lines.extend(f"- {item}" for item in learning)
    return "\n".join(lines)


def _criterion_block(path: Tuple[str, ...], item: Mapping[str, Any]) -> str:
    """Render a single criterion, its scale, and its analysis instructions."""
    lines: List[str] = [f"## {'.'.join(path)}"]
    description = _as_text(item.get("$description", "")).strip()
    if description:
        lines.append(description)

    if "$points" in item:
        _, total = item["$points"]
        if total >= 0:
            lines.append(f"Barème : 0 à {total} point(s).")
        else:
            lines.append(f"Pénalité : {total} à 0 point(s).")
    elif "$bonus" in item:
        _, total = item["$bonus"]
        lines.append(f"Bonus : 0 à {total} point(s).")

    test = item.get("$test")
    if test:
        lines.append("Instructions : " + _as_text(test))
    else:
        lines.append(
            "Instructions : (aucune consigne spécifique — juge selon la description.)"
        )
    return "\n".join(lines)


def build_prompt(data: Mapping[str, Any]) -> str:
    """Return the full grading prompt rendered from normalized criteria data."""
    grading = data.get("grading") or {}
    criteria = data.get("criteria") or {}
    blocks: List[str] = []

    context = grading.get("context")
    if context:
        blocks.append("# Rôle et contexte de correction\n\n" + _as_text(context))

    student = grading.get("student")
    if student:
        blocks.append(_student_block(student))

    leaves = list(_iter_leaves(criteria))
    criterion_texts = [_criterion_block(path, item) for path, item in leaves]
    blocks.append("# Critères à évaluer\n\n" + "\n\n".join(criterion_texts))

    identifiers = [".".join(path) for path, _ in leaves]
    response = [
        "# Réponse attendue",
        "",
        "Pour chaque critère ci-dessus, renvoie un objet JSON de la forme :",
        "",
        "```json",
        "{",
        '  "<identifiant_du_critère>": {',
        '    "awarded_points": <nombre>,',
        '    "rationale": "<justification concise et factuelle>"',
        "  }",
        "}",
        "```",
        "",
        f"Critères à noter : {', '.join(identifiers)}.",
        "Respecte les bornes de chaque barème et justifie chaque dotation "
        "à partir des preuves présentes dans le rendu.",
    ]
    blocks.append("\n".join(response))

    return "\n\n".join(blocks) + "\n"


__all__ = ["build_prompt"]
