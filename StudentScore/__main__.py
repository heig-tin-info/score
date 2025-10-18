#!/usr/bin/env python
from __future__ import annotations

import importlib.resources as resources
import json as json_module
from functools import lru_cache
from pathlib import Path
from typing import Any

import click
import typer
from typer.main import TyperGroup

from .score import Score


DEFAULT_CRITERIA_FILE = Path("criteria.yml")
DEFAULT_COMMAND_NAME = "__default__"


class _DefaultCommandGroup(TyperGroup):
    """Typer group that forwards to a predefined command when none is provided."""

    default_command_name: str | None = None

    def invoke(self, ctx: typer.Context) -> Any:
        if (
            self.default_command_name
            and not ctx._protected_args
            and not ctx.resilient_parsing
        ):
            ctx._protected_args = [self.default_command_name]
        return super().invoke(ctx)

    def resolve_command(  # type: ignore[override]
        self,
        ctx: typer.Context,
        args: list[str],
    ) -> tuple[str, click.Command, list[str]]:
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError as exc:
            if self.default_command_name:
                command = self.get_command(ctx, self.default_command_name)
                if command is not None:
                    return self.default_command_name, command, args
            raise exc


class _ScoreCommandGroup(_DefaultCommandGroup):
    default_command_name = DEFAULT_COMMAND_NAME


app = typer.Typer(
    add_completion=False,
    help="Student Score.",
    cls=_ScoreCommandGroup,
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
) -> None:
    """Store global CLI options for later use."""
    ctx.obj = ctx.obj or {}
    ctx.obj["verbose"] = verbose


@app.command(name=DEFAULT_COMMAND_NAME, hidden=True)
def _default_command(
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
    ctx = click.get_current_context()
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
def schema() -> None:
    """Display the JSON schema for the analysis payload."""
    typer.echo(
        json_module.dumps(_load_result_schema(), indent=2, sort_keys=True)
    )


def cli() -> None:
    """Entry point compatible wrapper."""
    app()


if __name__ == "__main__":
    cli()
