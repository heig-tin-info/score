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
```

## Criteria file format

Each assignment has a description files that looks like the one below. One can add criteria with positive or negative points. Also bonus point can be set.

```yaml
---
criteria:
  testing:
    tests:
      build:
        $description: The program builds correctly
        $points: [-2, -4]
      unit-testing:
        foo: 
          $description: Foo function works
          $points: [3, 3]          
        bar:
          $description: Bar function works
          $points: [1, 3]        
  code:
    implementation:
      smart-pointer: 
        $description: Smart pointers are used correcly
        $points: [4, 4]
    overall:
      dry:
        $description: No repeated code
        $points: [0, -5]
      kiss:
        $description: No unnecessary code
        $points: [-1, -5]
      ssot:
        $description: No redundant information
        $points: [0, -5]
      indentation:
        $description: Indentation is correct
        $points: [0, -3]
  bonus:
    test_framework:
      $description: Use a test framework
      $bonus: [2, 2]
    extension:
      $description: Program goes beyond the scope of the assignment
      $bonus: [0, 3]
```      
