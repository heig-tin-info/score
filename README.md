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

Use `score check` to validate a criteria file and `score update` to migrate an older version 1 definition to the version 2 schema.
