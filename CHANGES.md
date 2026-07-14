# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.4] - 2026-07-14

### Changed

- The `grade-final` review now writes the awarded points and LLM rationales
  directly INTO the criteria file (in place) instead of a separate
  GRADING.yml, and the review commit message carries the mark
  (`grading: 5.9/6 (grade-final)`). Milestone reviews keep their own
  `GRADING-<name>.yml`: their filter prunes the untagged criteria, so an
  in-place write would destroy the barème (`.github/workflows/grading.yml`).
- The "no grade on infrastructure failure" gate now keys on the grading
  step's outcome rather than the review file's existence (the in-place
  target always exists).

## [0.7.3] - 2026-07-14

### Added

- Per-criterion `milestone: <name>` tag (schema v1: `$milestone`) marking the
  subset graded at an intermediate milestone; validated against
  `[a-z0-9][a-z0-9_-]*` so the name stays shell- and YAML-safe
  (`StudentScore/schema.py`, `StudentScore/conversion.py`).
- `score grade --milestone <name>`: keeps only the tagged criteria (empty
  sections pruned) for the prompt and the graded output; fails when no
  criterion carries the tag (`StudentScore/apply.py` `filter_milestone`,
  `StudentScore/__main__.py`).
- The reusable grading workflow's `llm-review` job reads
  `client_payload.milestone` (heig-classroom `grade-milestone` dispatch),
  grades with `--milestone` and commits the review as `GRADING-<name>.yml`, so
  the final `GRADING.yml` never overwrites an intermediate review
  (`.github/workflows/grading.yml`).

### Fixed

- The `score` entry point now propagates the exit code of a `typer.Exit`
  raised inside a command: click returns the code with
  `standalone_mode=False` instead of raising, so `score check` on an invalid
  file (and `score grade --milestone` with an unknown tag) exited 0 in CI
  (`StudentScore/__main__.py`).

## [0.7.1] - 2026-07-10

### Added

- The reusable grading workflow's `objective` job now also runs on
  `workflow_dispatch`, so heig-classroom's "grade now" button can trigger an
  on-demand objective grade of the student's head commit
  (`.github/workflows/grading.yml`).

## [0.7.0] - 2026-07-10

### Added

- Schema version 2 now accepts an optional top-level `grading` block carrying an
  LLM correction `context` and a structured `student` profile (`level`, `knows`,
  `learning`) to guide assisted grading (`StudentScore/schema.py`).
- New `score grade` command that assembles an LLM grading prompt from the
  `grading` block and each criterion's `prompt` instructions, without calling any
  LLM (`StudentScore/grading.py`, `StudentScore/__main__.py`).
- `grading.sources` field (list of file globs) telling the LLM tier which files
  to attach to the grading prompt (`StudentScore/schema.py`).
- New `score apply` command that merges a `{criterion.id: {awarded_points,
  rationale}}` results file into a criteria file, clamping out-of-range points;
  the single ingestion path for both the objective and LLM grading tiers
  (`StudentScore/apply.py`, `StudentScore/__main__.py`).
- `score grade --llm` grades a submission with Claude (Opus 4.8, strict JSON
  output) using the optional `anthropic` extra — `pip install StudentScore[llm]`
  (`StudentScore/llm.py`).
- `score-grade` composite GitHub Action computing the objective mark (build +
  tests) and publishing it as a heig-classroom `GRADE` annotation
  (`.github/actions/score-grade/`).
- Reusable two-tier grading workflow (`workflow_call`) so student repositories
  only carry a thin shim: `objective` job on push, `llm-review` job on
  `repository_dispatch` from heig-classroom (`.github/workflows/grading.yml`).

### Fixed

- Default-command forwarding (`score criteria.yml`) now works with click ≥ 8.2:
  the group inserts the hidden default command in `parse_args` instead of
  relying on the removed `Context.protected_args` (`StudentScore/__main__.py`).
- CLI tests no longer use `CliRunner.isolated_filesystem`, removed in click 8.3
  (`tests/test_cli.py`).

### Changed

- CI: bump `.github/workflows/ci.yml` to use `actions/download-artifact@v4.1.7` for artifact handling.
- Replaced tox-based automation with `nox` sessions and modernised the CI release pipeline (`noxfile.py`, `.github/workflows/ci.yml`, `pyproject.toml`).
- Moved packaging configuration to Poetry package mode with dynamic versioning and an `importlib.metadata`-based version helper (`pyproject.toml`, `StudentScore/version.py`).

### Removed

- Dropped support for Python 3.6–3.9 in favour of a Python 3.10+ baseline aligned with the current build tooling (`pyproject.toml`, `.github/workflows/ci.yml`).

## [0.3.1] - 2022-11-15

### Fixed

- Ensure marks are rounded up to the nearest tenth so borderline grades are not rounded down (`StudentScore/score.py`).
- Emit marks with a single decimal place in the CLI to match the new rounding rules (`StudentScore/__main__.py`).

### Added

- Regression coverage for fractional scores, zero-total checks, and bonus aggregation (`tests/test_score.py`).

## [0.3.0] - 2022-11-14

### Added

- Extended schema validation to accept percentage-based point definitions and reject inconsistent pairs via the new `ValidPoints` checks (`StudentScore/schema.py`, `tests/test_schema.py`).
- Comprehensive CLI, file, and schema tests along with coverage tooling configuration (`tests/`, `.coveragerc`, `.editorconfig`).

### Changed

- `Score.mark` now raises an explicit `ValueError` when total available points are zero and reads criteria files as UTF-8 text (`StudentScore/score.py`).
- Consolidated tests under a top-level `tests` package to integrate with `pytest` and coverage workflows.

### Fixed

- Moved the responsibility for rejecting impossible point allocations from runtime scoring to schema validation, preventing silent misconfigurations (`StudentScore/score.py`, `StudentScore/schema.py`).

## [0.2.0] - 2022-06-26

### Added

- Configured `setuptools_scm` via `pyproject.toml` to generate package versions automatically (`pyproject.toml`, `StudentScore/version.py`).
- Introduced a YAML validation helper that surfaces precise line and column information on schema errors (`StudentScore/schema.py`).

### Changed

- Renamed the Python package to `StudentScore` and updated the console entry point and metadata accordingly (`setup.cfg`, `StudentScore/__main__.py`).
- Updated bundled criteria examples and tests to the new namespace and scoring baseline (`StudentScore/tests/`).

## [0.1.2] - 2022-02-17

### Added

- Negative-criteria fixtures and regression tests to capture grading behaviour at the lower bound (`score/tests/`).

### Changed

- Clamp computed marks within the 1.0–6.0 grading scale to avoid returning scores below the minimum (`score/score.py`).
- Switched the PyPI publishing workflow to the maintained action and secret naming (`.github/workflows/ci.yml`).
- Returned the published package name to `Score` to match the existing distribution (`setup.cfg`).

## [0.1.1] - 2022-02-06

### Changed

- Updated distribution metadata to publish under the `StudentScore` name (`setup.cfg`).

## [0.1.0] - 2022-02-06

### Added

- Initial release with the `score` CLI for computing grades from YAML criteria files (`score/__main__.py`).
- YAML schema validation for nested criteria, points, and bonuses (`score/schema.py`).
- Core scoring engine that aggregates earned, total, and bonus points and flags pass/fail thresholds (`score/score.py`).

<!-- Links -->
[Unreleased]: https://github.com/heig-tin-info/score/compare/0.3.1...HEAD
[0.3.1]: https://github.com/heig-tin-info/score/compare/0.3.0...0.3.1
[0.3.0]: https://github.com/heig-tin-info/score/compare/0.2.0...0.3.0
[0.2.0]: https://github.com/heig-tin-info/score/compare/0.1.2...0.2.0
[0.1.2]: https://github.com/heig-tin-info/score/compare/0.1.1...0.1.2
[0.1.1]: https://github.com/heig-tin-info/score/compare/0.1.0...0.1.1
[0.1.0]: https://github.com/heig-tin-info/score/releases/tag/0.1.0
