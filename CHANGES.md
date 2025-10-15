# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- CI: bump `.github/workflows/ci.yml` to use `actions/download-artifact@v4.1.7` for artifact handling.
- Replaced tox-based automation with `nox` sessions and modernised the CI release pipeline (`noxfile.py`, `.github/workflows/ci.yml`, `pyproject.toml`).

### Removed

- Dropped support for Python 3.6 and 3.7 in favour of a Python 3.8+ baseline aligned with the current build tooling (`pyproject.toml`, `.github/workflows/ci.yml`).

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
