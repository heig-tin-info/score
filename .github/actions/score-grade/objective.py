#!/usr/bin/env python
"""Turn build/test outcomes into a StudentScore results.json fragment.

Reads JUnit XML (``report.xml``) and the surrounding step outcomes from the
environment, and emits ``{criterion.id: {awarded_points, rationale}}`` on stdout.
Only the objective, deterministic criteria are filled here — the subjective ones
are left untouched and graded later by the LLM tier.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from xml.etree import ElementTree


def _read_criterion_max(criteria_path: str, dotted_id: str) -> float | None:
    """Best-effort lookup of a criterion's max_points from the YAML file."""
    try:
        import yaml  # PyYAML ships with StudentScore
    except ModuleNotFoundError:
        return None
    try:
        data = yaml.safe_load(Path(criteria_path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    node = data.get("criteria", {}) if isinstance(data, dict) else {}
    for part in dotted_id.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part, {})
    if isinstance(node, dict):
        value = node.get("max_points")
        if isinstance(value, (int, float)):
            return float(value)
        pair = node.get("$points")
        if isinstance(pair, list) and len(pair) == 2:
            return float(pair[1])
    return None


def _test_ratio(report: Path) -> tuple[float, str]:
    """Return (pass_ratio, summary) parsed from a JUnit XML report."""
    if not report.exists():
        return 0.0, "no test report produced"
    tree = ElementTree.parse(report)
    root = tree.getroot()
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    total = failures = errors = skipped = 0
    for suite in suites:
        total += int(suite.get("tests", 0))
        failures += int(suite.get("failures", 0))
        errors += int(suite.get("errors", 0))
        skipped += int(suite.get("skipped", 0))
    effective = total - skipped
    if effective <= 0:
        return 0.0, "no tests were executed"
    passed = effective - failures - errors
    ratio = max(0.0, passed / effective)
    return ratio, f"{passed}/{effective} tests passed"


def main() -> None:
    criteria_file = os.environ.get("CRITERIA_FILE", "criteria.yml")
    tests_criterion = os.environ.get("TESTS_CRITERION", "binary.all-tests-passed")
    build_criterion = os.environ.get("BUILD_ERRORS_CRITERION", "").strip()
    build_ok = os.environ.get("BUILD_OUTCOME", "success") == "success"

    results: dict[str, dict[str, object]] = {}

    if build_criterion:
        results[build_criterion] = {
            "awarded_points": 0 if build_ok else -999,  # clamped to the penalty
            "rationale": "builds cleanly" if build_ok else "build failed",
        }

    if build_ok:
        ratio, summary = _test_ratio(Path("report.xml"))
    else:
        ratio, summary = 0.0, "build failed, tests not run"

    max_points = _read_criterion_max(criteria_file, tests_criterion) or 0.0
    results[tests_criterion] = {
        "awarded_points": round(ratio * max_points, 2),
        "rationale": summary,
    }

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
