# Score

[![PyPI version](https://img.shields.io/pypi/v/StudentScore.svg)](https://pypi.org/project/StudentScore/)
[![PyPI downloads](https://img.shields.io/pypi/dm/StudentScore.svg)](https://pypi.org/project/StudentScore/)
[![Python](https://img.shields.io/pypi/pyversions/StudentScore)](https://pypi.org/project/StudentScore/)
[![CI](https://github.com/heig-tin-info/score/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/heig-tin-info/score/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/heig-tin-info/score/branch/master/graph/badge.svg)](https://codecov.io/gh/heig-tin-info/score)
[![License](https://img.shields.io/github/license/heig-tin-info/score.svg)](https://github.com/heig-tin-info/score/blob/master/LICENSE.txt)
[![GitHub repo size](https://img.shields.io/github/repo-size/heig-tin-info/score.svg)](https://github.com/heig-tin-info/score)
[![GitHub issues](https://img.shields.io/github/issues/heig-tin-info/score.svg)](https://github.com/heig-tin-info/score/issues)
[![GitHub last commit](https://img.shields.io/github/last-commit/heig-tin-info/score.svg)](https://github.com/heig-tin-info/score/commits/master)

Compute the final score of an assignment based on the `criteria.yml` file.

This small package is an helper to sum the points of programming assignments.

## Usage

Simply use `score` inside an assignment folder

```console
$ score -v
Got 7 points + 2 points out of 10 points
4.5
$ score
4.5
$ score check criteria.yml
OK, schema version 2
```

You can use the porcelain command `score json` to get the detailed score report in JSON format:

```console
$ score json [file]
```

## Criteria file format

Criteria files now use the version 2 schema which is more explicit and easier to validate. The root object must contain a `schema_version: 2` field and a `criteria` mapping. Each section can provide an optional `description` and nested criteria items. A leaf item uses descriptive keys such as `description`, `awarded_points`, and either `max_points` (regular points) or `bonus_points` (bonus points).

```yaml
---
schema_version: 2
criteria:
  testing:
    description: Automated testing
    build:
      description: The program builds correctly
      awarded_points: -2
      max_points: -4
    unit:
      description: Unit test suite covers the critical paths
      awarded_points: 4
      max_points: 4
  code:
    description: Code quality
    implementation:
      description: Smart pointers are used correctly
      awarded_points: 4
      max_points: 4
    duplication:
      description: No repeated code
      awarded_points: -1
      max_points: -5
  bonus:
    description: Extra credit
    extension:
      description: Program goes beyond the scope of the assignment
      awarded_points: 2
      bonus_points: 3
```

Use `score check` to validate a criteria file (versions 1, 2 and 3) and `score update` to migrate a version 1 or 2 definition to the version 3 schema.

## Schema v3, commands and results.json

Version 3 is the criteria format of the [Quiz](https://quiz.chevallier.io) platform, which publishes its JSON Schemas; StudentScore is one implementation. A leaf keeps the version 2 keys and gains `command`:

```yaml
schema_version: 3
grading:                 # optional, for the LLM reviewer
  context: You grade a first-year C lab.
  sources: [src/, Makefile]   # plain paths, a directory ends with /, no wildcard
criteria:
  code:
    description: Code
    format:
      description: The code is formatted
      max_points: 2
      command: [make, format-check]   # argv, 1 to 20 strings, no shell
    tests:
      desc: Functional tests          # `desc` is an alias of `description`
      max_points: 10
      command: [python3, tests/run.py]
      milestone: mid                  # [a-z0-9][a-z0-9_-]{0,49}
    warnings:
      description: No compiler warning
      max_points: -2                  # a penalty
      command: [make, CFLAGS=-Werror]
    readability:
      description: The code reads well
      max_points: 4
      prompt: Judge the names and the structure.
  bonus:
    extension:
      description: Goes beyond the assignment
      bonus_points: 2
```

- The kind of a leaf: `command` makes it automatic (even with a `prompt`); else `prompt` makes it reviewed by the LLM; else the teacher grades it.
- `max_points` (negative for a penalty) or `bonus_points` (positive): numbers only. `awarded_points` is a number too; `score update` turns a version 1 or 2 percentage (`"50%"`) into its points.
- `awarded_points` is optional (StudentScore's output, 0 when absent). `rationale` is also accepted: `score apply` and `score grade --llm` write it.
- A name contains neither a dot nor a space; unknown keys are errors; `test:` exists in version 2 only.

### `score run`

```console
$ score run [criteria.yml] [-o results.json] [--timeout 120] [--points]
```

Runs the `command` of every leaf, in the directory of the criteria file, without a shell, each with a wall-clock limit (120 s by default). A command's result is a fraction `n/m`:

- the last non-empty line of its standard output when it reads `n/m` (`n` may be decimal, `m > 0`), so a test runner can print `7/10`;
- otherwise its exit code: `0` gives `1/1`, anything else `0/1`;
- a timeout, or a program that cannot start, gives `0/1` with a line in the log.

A readable summary goes to stderr; `--points` also prints `points/max` of the command criteria on stdout. Students can run it locally before pushing. The file it writes:

```json
{
  "$schema": "https://quiz.chevallier.io/schemas/results-1.json",
  "criteria": {
    "code.format": { "score": "1/1", "log": "..." },
    "code.tests": { "score": "7.5/10" }
  }
}
```

Each `log` is the combined stdout and stderr, cut to its last 8 KiB; the file stays under 256 KiB.

### Points

With `f = n/m` (`n` clamped to `[0, m]`): a positive leaf earns `max × f`, a penalty `max × (1 − f)` (a full pass costs nothing), a bonus `bonus × f`; each rounded to 0.01. `score --results results.json` and `score json --results results.json` compute the mark with these points for the command leaves (a command leaf missing from the file earns 0); without `--results` they use `awarded_points` as before.

### GitHub Actions

`.github/workflows/run.yml` is the reusable workflow. The lab repository's `.github/workflows/grading.yml` stays a constant shim, pinned by sha:

```yaml
name: grading
on:
  push:
  workflow_dispatch:
  repository_dispatch:
    types: [quiz-grade]
run-name: grading ${{ github.event.client_payload.nonce || github.sha }}
jobs:
  grading:
    uses: heig-tin-info/score/.github/workflows/run.yml@<sha of 1.0.0>
    # with: { apt-packages: build-essential, python-version: "3.12" }
```

It checks out `client_payload.sha` (or the pushed commit), installs StudentScore from the workflow's own commit, runs `score run`, uploads one artifact named `results` holding `results.json` (kept 30 days) and prints `::notice title=GRADE::<points>/<max>` over the command criteria: points, never a mark, the points capped at the max. The 0.7.x pipeline (`grading.yml`) is unchanged.
