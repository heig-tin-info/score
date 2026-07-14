#!/usr/bin/env python
from __future__ import annotations

from functools import lru_cache
import importlib.resources as resources
import json as json_module
from pathlib import Path
import sys
from typing import Any

import click
import typer
from typer.main import TyperGroup

from . import yaml
from .apply import apply_results, filter_milestone
from .conversion import upgrade_to_v2
from .grading import build_prompt
from .schema import Criteria, CriteriaValidationError
from .score import Score


DEFAULT_CRITERIA_FILE = Path("criteria.yml")
DEFAULT_COMMAND_NAME = "__default__"
_DEBUG_ENABLED = False


class _DefaultCommandGroup(TyperGroup):
    """Typer group that forwards to a predefined command when none is provided."""

    default_command_name: str | None = None

    def parse_args(self, ctx: typer.Context, args: list[str]) -> list[str]:
        # Insert the default command when the invocation does not start with a
        # known subcommand (e.g. `score criteria.yml` or bare `score`).
        if self.default_command_name is not None:
            head = next((arg for arg in args if not arg.startswith("-")), None)
            if head is None or self.get_command(ctx, head) is None:
                args = [self.default_command_name, *args]
        return super().parse_args(ctx, args)


class _ScoreCommandGroup(_DefaultCommandGroup):
    default_command_name = DEFAULT_COMMAND_NAME


app = typer.Typer(
    add_completion=False,
    help="Student Score.",
    cls=_ScoreCommandGroup,
    pretty_exceptions_show_locals=False,
)


def _compute_score(path: Path) -> Score:
    """Instantiate Score with the provided path."""
    return Score(str(path))


@lru_cache(maxsize=1)
def _load_result_schema() -> dict[str, Any]:
    """Load the JSON schema definition stored in the package."""
    schema_path = resources.files(__package__) / "result_schema.json"
    with schema_path.open("r", encoding="utf-8") as schema_file:
        return json_module.load(schema_file)


def _format_payload(score: Score) -> dict[str, Any]:
    """Return a serializable payload describing the score analysis."""
    return {
        "mark": score.mark,
        "success": score.success,
        "points": {
            "got": score.points.got,
            "total": score.points.total,
            "bonus": score.points.bonus,
        },
        "criteria": score.data,
    }


def _print_score(score: Score, *, verbose: bool) -> None:
    """Render the score information on stdout."""
    if verbose:
        typer.echo(
            (
                f"Got {score.got:g} points + {score.bonus:g} "
                f"points out of {score.total:g} points"
            )
        )

    typer.secho(f"{score.mark:g}", fg="green" if score.success else "red")


@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Display detailed points before the final mark.",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Show full traceback for unexpected errors.",
    ),
) -> None:
    """Store global CLI options for later use."""
    global _DEBUG_ENABLED
    ctx.obj = ctx.obj or {}
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug
    _DEBUG_ENABLED = debug


def _handle_unexpected(exception: Exception) -> None:
    """Gracefully handle unexpected exceptions."""
    if isinstance(exception, (typer.Exit, click.ClickException)):
        raise exception

    debug = _DEBUG_ENABLED
    if debug:
        raise exception

    message = str(exception).strip() or exception.__class__.__name__
    typer.secho(message, fg="red", err=True)
    raise SystemExit(1)


def _invoke_cli() -> None:
    """Execute the Typer application with controlled error handling."""
    try:
        result = app(standalone_mode=False)
    except typer.Exit as exc:
        raise SystemExit(exc.exit_code)
    except click.ClickException as exc:
        exc.show(file=sys.stderr)
        raise SystemExit(exc.exit_code)
    except Exception as exc:  # noqa: BLE001
        _handle_unexpected(exc)
    else:
        # click's standalone_mode=False RETURNS the exit code of a
        # typer.Exit raised inside a command instead of raising it; without
        # this, `score check` on an invalid file exited 0 in CI.
        if isinstance(result, int) and result != 0:
            raise SystemExit(result)


@app.command(name=DEFAULT_COMMAND_NAME, hidden=True)
def _default_command(
    ctx: typer.Context,
    file: Path = typer.Argument(
        DEFAULT_CRITERIA_FILE,
        exists=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the criteria file.",
    ),
    verbose_flag: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Display detailed points before the final mark.",
    ),
) -> None:
    """Compute the score from a criteria file."""
    verbose = bool((ctx.obj or {}).get("verbose"))
    score = _compute_score(file)
    _print_score(score, verbose=verbose or verbose_flag)


@app.command()
def json(
    file: Path = typer.Argument(
        DEFAULT_CRITERIA_FILE,
        exists=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the criteria file.",
    ),
) -> None:
    """Emit the score analysis as JSON."""
    score = _compute_score(file)
    typer.echo(json_module.dumps(_format_payload(score), indent=2, sort_keys=True))


@app.command()
def check(
    file: Path = typer.Argument(
        DEFAULT_CRITERIA_FILE,
        exists=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the criteria file to validate.",
    ),
) -> None:
    """Validate a criteria file and report its schema version."""
    try:
        with file.open("r", encoding="utf-8") as handle:
            raw_criteria = yaml.load(handle, Loader=yaml.FullLoader)
    except Exception as exc:  # noqa: BLE001
        message = str(exc).strip() or "Unable to parse criteria file."
        typer.secho("BAD", fg="red")
        typer.echo(message)
        raise typer.Exit(code=1)

    try:
        normalized = Criteria(raw_criteria)
    except CriteriaValidationError as exc:
        typer.secho("BAD", fg="red")
        typer.echo(str(exc).strip() or "Invalid criteria definition.")
        raise typer.Exit(code=1)

    schema_version = int(normalized.get("schema_version", 1))
    typer.secho(f"OK, schema version {schema_version}", fg="green")


@app.command()
def apply(
    results: Path = typer.Argument(
        ...,
        exists=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="JSON results file: {criterion.id: {awarded_points, rationale}}.",
    ),
    file: Path = typer.Argument(
        DEFAULT_CRITERIA_FILE,
        exists=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the criteria file to update.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        dir_okay=False,
        writable=True,
        resolve_path=True,
        help="Destination file. Defaults to updating the criteria file in place.",
    ),
) -> None:
    """Merge awarded points/rationale from a results file into the criteria."""
    with results.open("r", encoding="utf-8") as handle:
        payload = json_module.load(handle)
    if not isinstance(payload, dict):
        typer.secho("Results file must be a JSON object.", fg="red", err=True)
        raise typer.Exit(code=1)

    with file.open("r", encoding="utf-8") as handle:
        raw_criteria = yaml.load(handle, Loader=yaml.FullLoader)

    updated, applied, unknown = apply_results(raw_criteria, payload)

    # Fail fast on a typo/mismatch rather than silently dropping a grade.
    for cid in unknown:
        typer.secho(f"Unknown criterion in results: {cid}", fg="red", err=True)
    if unknown:
        raise typer.Exit(code=1)

    # Validate the merged result before persisting it.
    Criteria(updated)

    destination = output or file
    with destination.open("w", encoding="utf-8") as handle:
        yaml.dump(
            updated,
            stream=handle,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )
    typer.secho(
        f"Applied {len(applied)} criteria to {destination}", fg="green"
    )


@app.command()
def grade(
    file: Path = typer.Argument(
        DEFAULT_CRITERIA_FILE,
        exists=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the criteria file.",
    ),
    use_llm: bool = typer.Option(
        False,
        "--llm",
        help="Call Claude to grade the submission (needs ANTHROPIC_API_KEY).",
    ),
    source: list[str] = typer.Option(
        [],
        "--source",
        "-s",
        help="Glob of source files to send to the model (repeatable).",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        dir_okay=False,
        writable=True,
        resolve_path=True,
        help="With --llm: write the graded criteria file here.",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Override the grading model (default: claude-opus-4-8).",
    ),
    milestone: str | None = typer.Option(
        None,
        "--milestone",
        help=(
            "Intermediate review: grade only the criteria tagged "
            "`milestone: <name>` in the criteria file."
        ),
    ),
) -> None:
    """Assemble the grading prompt, or grade with Claude when --llm is set."""
    with file.open("r", encoding="utf-8") as handle:
        raw_criteria = yaml.load(handle, Loader=yaml.FullLoader)

    if milestone is not None:
        raw_criteria, kept = filter_milestone(raw_criteria, milestone)
        if kept == 0:
            typer.secho(
                f"No criteria tagged with milestone '{milestone}'.",
                fg="red",
                err=True,
            )
            raise typer.Exit(code=1)

    normalized = Criteria(raw_criteria)

    if not use_llm:
        typer.echo(build_prompt(normalized))
        return

    from .llm import DEFAULT_MODEL, collect_sources, grade_with_llm

    patterns = list(source)
    grading = normalized.get("grading") or {}
    patterns.extend(grading.get("sources", []))
    sources = collect_sources(patterns) if patterns else {}

    results = grade_with_llm(
        normalized, sources, model=model or DEFAULT_MODEL
    )

    updated, applied, _ = apply_results(raw_criteria, results)
    Criteria(updated)

    destination = output or file
    with destination.open("w", encoding="utf-8") as handle:
        yaml.dump(
            updated,
            stream=handle,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )
    typer.secho(
        f"Graded {len(applied)} criteria with {model or DEFAULT_MODEL} "
        f"-> {destination}",
        fg="green",
    )


@app.command()
def schema() -> None:
    """Display the JSON schema for the analysis payload."""
    typer.echo(json_module.dumps(_load_result_schema(), indent=2, sort_keys=True))


@app.command()
def update(
    file: Path = typer.Argument(
        DEFAULT_CRITERIA_FILE,
        exists=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the criteria file to migrate.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        dir_okay=False,
        writable=True,
        resolve_path=True,
        help="Optional destination file. Defaults to in-place upgrade.",
    ),
) -> None:
    """Migrate a criteria file from schema version 1 to version 2."""
    with file.open("r", encoding="utf-8") as handle:
        raw_criteria = yaml.load(handle, Loader=yaml.FullLoader)

    normalized = Criteria(raw_criteria)
    schema_version = normalized.get("schema_version", 1)

    if schema_version == 2 and output is None:
        typer.secho(
            "Criteria already use schema version 2; no changes written.",
            fg="yellow",
        )
        return

    converted = upgrade_to_v2(normalized)
    destination = output or file
    with destination.open("w", encoding="utf-8") as handle:
        yaml.dump(
            converted,
            stream=handle,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )

    typer.secho(
        f"Criteria upgraded to schema version 2 and written to {destination}",
        fg="green",
    )


def cli() -> None:
    """Entry point compatible wrapper."""
    _invoke_cli()


if __name__ == "__main__":
    cli()
