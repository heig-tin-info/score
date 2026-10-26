"""Schema version 3, the command runner, the points arithmetic, results.json."""

import json
import sys

import pytest
from typer.testing import CliRunner

from StudentScore import Score
from StudentScore.__main__ import app
from StudentScore.results import (
    RESULTS_SCHEMA_URL,
    CommandResult,
    InvalidFraction,
    build_results,
    format_points,
    fraction_from_output,
    leaf_points,
    load_results,
    parse_fraction,
    round_points,
    run_command,
    tail_cap,
)
from StudentScore.schema import Criteria, CriteriaValidationError


PY = sys.executable


def v3(criteria, **extra):
    return {"schema_version": 3, "criteria": criteria, **extra}


def errors_of(data):
    with pytest.raises(CriteriaValidationError) as exc:
        Criteria(data)
    return str(exc.value)


# --------------------------------------------------------------------------
# Schema version 3
# --------------------------------------------------------------------------


class TestSchemaV3:
    def test_full_leaf(self):
        data = Criteria(
            v3(
                {
                    "code": {
                        "description": "Code",
                        "format": {
                            "desc": "Formatted",
                            "max_points": 2,
                            "command": ["make", "format-check"],
                            "prompt": "ignored for the kind",
                            "milestone": "m1",
                            "awarded_points": 1.5,
                        },
                    }
                },
                grading={"context": "c", "sources": ["src/", "main.c"]},
            )
        )
        leaf = data["criteria"]["code"]["format"]
        assert data["schema_version"] == 3
        assert leaf["$command"] == ["make", "format-check"]
        assert leaf["$points"] == [1.5, 2]
        assert leaf["$milestone"] == "m1"
        assert leaf["$test"] == "ignored for the kind"
        assert data["criteria"]["code"]["$description"] == "Code"

    def test_awarded_points_optional(self):
        data = Criteria(v3({"a": {"description": "A", "max_points": 3}}))
        assert data["criteria"]["a"]["$points"] == [0.0, 3]

    def test_decimal_max(self):
        data = Criteria(v3({"a": {"description": "A", "max_points": 2.5}}))
        assert data["criteria"]["a"]["$points"] == [0.0, 2.5]

    @pytest.mark.parametrize("field", ["max_points", "bonus_points"])
    @pytest.mark.parametrize("value", ["50%", "-20%", "150%"])
    def test_percentages_refused(self, field, value):
        message = errors_of(
            v3(
                {
                    "a": {"description": "A", "max_points": 6},
                    "p": {"description": "P", field: value},
                }
            )
        )
        assert "percentages are not accepted in schema version 3" in message

    @pytest.mark.parametrize(
        "leaf, expected",
        [
            ({"description": "A", "max_points": 1, "test": "x"}, "version 2 only"),
            ({"description": "A", "max_points": 1, "foo": 1}, "unrecognized"),
            ({"description": "A", "max_points": 1, "command": "make"}, "argv"),
            ({"description": "A", "max_points": 1, "command": []}, "argv"),
            ({"description": "A", "max_points": 1, "command": ["x"] * 21}, "argv"),
            ({"description": "A", "max_points": 1, "command": ["make", 3]}, "argv"),
            ({"description": "A", "max_points": 1, "command": [""]}, "argv"),
            (
                {"description": "A", "max_points": 1, "milestone": "Bad Tag"},
                "milestone",
            ),
            ({"description": "A", "max_points": 0}, "No points"),
            ({"description": "A", "max_points": "abc"}, "must be a number"),
            ({"description": "A", "max_points": True}, "must be a number"),
            ({"description": "A", "bonus_points": -2}, "bonus_points must be positive"),
            ({"description": "A", "max_points": 1, "bonus_points": 1}, "not both"),
            ({"description": "A", "command": ["make"]}, "either max_points"),
            ({"max_points": 1}, "description must be provided"),
            ({"description": "A", "desc": "B", "max_points": 1}, "not both"),
            ({"description": "A", "max_points": 2, "awarded_points": 3}, "between"),
            ({"description": "A", "max_points": -2, "awarded_points": 1}, "between"),
            ({"description": "A", "max_points": 2, "awarded_points": "1"}, "number"),
        ],
    )
    def test_leaf_errors(self, leaf, expected):
        assert expected in errors_of(v3({"leaf": leaf}))

    @pytest.mark.parametrize("name", ["a.b", "a b"])
    def test_names(self, name):
        message = errors_of(v3({name: {"description": "A", "max_points": 1}}))
        assert "neither a dot nor a space" in message

    def test_sources_without_wildcard(self):
        message = errors_of(
            v3(
                {"a": {"description": "A", "max_points": 1}},
                grading={"sources": ["src/*.c"]},
            )
        )
        assert "no wildcard" in message

    def test_v2_still_valid(self):
        data = Criteria(
            {
                "schema_version": 2,
                "criteria": {
                    "a": {"description": "A", "max_points": 2, "awarded_points": 1}
                },
            }
        )
        assert data["schema_version"] == 2


# --------------------------------------------------------------------------
# Fractions and the command runner
# --------------------------------------------------------------------------


class TestFraction:
    def test_parse(self):
        assert parse_fraction(" 7.5 / 10 ") == (7.5, 10.0)

    @pytest.mark.parametrize("text", ["1/0", "a/b", "-1/2", "1/2/3", "", "3"])
    def test_invalid(self, text):
        with pytest.raises(InvalidFraction):
            parse_fraction(text)

    def test_last_non_empty_line(self):
        assert fraction_from_output("ran 10 tests\n7/10\n\n  \n", 1) == ("7/10", None)

    def test_decimal(self):
        assert fraction_from_output("7.5 / 10\n", 0) == ("7.5/10", None)

    def test_exit_code_fallback(self):
        assert fraction_from_output("all good\n", 0) == ("1/1", None)
        assert fraction_from_output("", 2) == ("0/1", None)
        # Only the LAST line counts.
        assert fraction_from_output("3/4\ndone\n", 0) == ("1/1", None)

    def test_zero_denominator_falls_back(self):
        score, note = fraction_from_output("5/0\n", 0)
        assert score == "1/1"
        assert "denominator" in note

    def test_run_fraction_and_log(self, tmp_path):
        code = "import sys; print('x'); print('err', file=sys.stderr); print('3/4')"
        result = run_command([PY, "-c", code], tmp_path, timeout=30)
        assert result.score == "3/4"
        assert "x\n" in result.log and "err\n" in result.log

    def test_run_exit_codes(self, tmp_path):
        assert run_command([PY, "-c", "pass"], tmp_path, 30).score == "1/1"
        assert (
            run_command([PY, "-c", "raise SystemExit(3)"], tmp_path, 30).score == "0/1"
        )

    def test_run_cwd(self, tmp_path):
        (tmp_path / "marker").write_text("1/2\n")
        code = "print(open('marker').read())"
        assert run_command([PY, "-c", code], tmp_path, 30).score == "1/2"

    def test_run_no_shell(self, tmp_path):
        result = run_command(
            [PY, "-c", "import sys; print(sys.argv[1])", "$HOME; 1/1"], tmp_path, 30
        )
        assert "$HOME; 1/1" in result.log

    def test_timeout(self, tmp_path):
        code = "import time; print('1/1', flush=True); time.sleep(30)"
        result = run_command([PY, "-c", code], tmp_path, timeout=1)
        assert result.score == "0/1"
        assert "[score] timeout after 1 s" in result.log

    def test_missing_binary(self, tmp_path):
        result = run_command(["no-such-binary-for-score"], tmp_path, 30)
        assert result.score == "0/1"
        assert "cannot run" in result.log

    def test_tail_cap(self):
        text = "a" * 10_000 + "END"
        capped = tail_cap(text)
        assert len(capped.encode()) <= 8192
        assert capped.endswith("END")
        assert capped.startswith("[... truncated]")
        assert tail_cap("short") == "short"


# --------------------------------------------------------------------------
# Points arithmetic
# --------------------------------------------------------------------------


class TestArithmetic:
    def test_positive(self):
        assert leaf_points({"$points": [0, 4]}, 3, 4) == 3
        assert leaf_points({"$points": [0, 10]}, 7.5, 10) == 7.5

    def test_penalty(self):
        # max × (1 − n/m): a full pass costs nothing, a failure the full penalty.
        assert leaf_points({"$points": [0, -4]}, 1, 1) == 0
        assert leaf_points({"$points": [0, -4]}, 0, 1) == -4
        assert leaf_points({"$points": [0, -4]}, 3, 4) == -1

    def test_bonus(self):
        assert leaf_points({"$bonus": [0, 2]}, 1, 2) == 1

    def test_clamped(self):
        assert leaf_points({"$points": [0, 4]}, 12, 10) == 4
        assert leaf_points({"$points": [0, -4]}, 12, 10) == 0

    def test_rounding(self):
        assert leaf_points({"$points": [0, 1]}, 1, 3) == 0.33
        assert leaf_points({"$points": [0, 2]}, 1, 3) == 0.67
        assert round_points(0.125) == 0.13
        assert round_points(-0.125) == -0.13
        assert format_points(1234567) == "1234567"
        assert format_points(-0.001) == "0"

    def test_penalty_and_bonus_leaves(self):
        data = Score(
            v3(
                {
                    "t": {"description": "T", "max_points": 8, "command": ["t"]},
                    "p": {"description": "P", "max_points": -2, "command": ["p"]},
                    "b": {"description": "B", "bonus_points": 4, "command": ["b"]},
                }
            ),
            results={"t": (1, 2), "p": (0, 1), "b": (1, 1)},
        )
        # t: 8 × 1/2 = 4; p: −2 × (1 − 0) = −2; b: 4 × 1 = 4.
        assert data.points.got == 6
        assert data.points.total == 8
        assert data.points.bonus == 4

    def test_score_with_and_without_results(self):
        criteria = v3(
            {
                "auto": {
                    "description": "A",
                    "max_points": 4,
                    "command": ["x"],
                    "awarded_points": 1,
                },
                "manual": {"description": "M", "max_points": 6, "awarded_points": 6},
                "absent": {"description": "N", "max_points": 2, "command": ["y"]},
            }
        )
        assert Score(criteria).points.got == 7
        with_results = Score(criteria, results={"auto": (3, 4)})
        assert with_results.points.got == 9  # 3 + 6 + 0 (no result)
        assert with_results.points.total == 12


# --------------------------------------------------------------------------
# results.json and the CLI
# --------------------------------------------------------------------------


CRITERIA = f"""\
schema_version: 3
criteria:
  code:
    description: Code
    tests:
      description: Tests
      max_points: 10
      command: [{json.dumps(PY)}, -c, "print('7.5/10')"]
    warnings:
      description: No warnings
      max_points: -2
      command: [{json.dumps(PY)}, -c, "raise SystemExit(1)"]
    extra:
      description: Extra
      bonus_points: 4
      command: [{json.dumps(PY)}, -c, "print('ok')"]
    review:
      description: Review
      max_points: 5
      prompt: Read the code
"""


class TestResultsFile:
    def test_shape(self):
        payload = build_results(
            {
                "a.b": CommandResult("1/1", "log\n"),
                "c": CommandResult("0/1", ""),
            }
        )
        assert payload == {
            "$schema": RESULTS_SCHEMA_URL,
            "criteria": {
                "a.b": {"score": "1/1", "log": "log\n"},
                "c": {"score": "0/1"},
            },
        }

    def test_file_cap(self):
        outcomes = {f"c{i}": CommandResult("1/1", "x" * 8000) for i in range(64)}
        payload = build_results(outcomes)
        assert len(json.dumps(payload, indent=2).encode()) <= 256 * 1024

    def test_load_results_skips_invalid(self, tmp_path):
        path = tmp_path / "results.json"
        path.write_text(
            json.dumps(
                {"criteria": {"a": {"score": "1/2"}, "b": {"score": "1/0"}, "c": {}}}
            )
        )
        assert load_results(path) == {"a": (1.0, 2.0)}

    def test_cli_run_then_score(self, tmp_path):
        criteria = tmp_path / "criteria.yml"
        criteria.write_text(CRITERIA)
        output = tmp_path / "out" / "results.json"
        output.parent.mkdir()
        runner = CliRunner()
        result = runner.invoke(
            app, ["run", str(criteria), "-o", str(output), "--points"]
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(output.read_text())
        assert payload["$schema"] == RESULTS_SCHEMA_URL
        assert list(payload["criteria"]) == [
            "code.tests",
            "code.warnings",
            "code.extra",
        ]
        assert payload["criteria"]["code.tests"]["score"] == "7.5/10"
        assert payload["criteria"]["code.warnings"]["score"] == "0/1"
        assert payload["criteria"]["code.extra"]["score"] == "1/1"
        # 7.5 − 2 + 4 over the positive command max (10).
        assert result.stdout.strip().splitlines()[-1] == "9.5/10"

        scored = runner.invoke(app, ["json", str(criteria), "--results", str(output)])
        assert scored.exit_code == 0, scored.output
        points = json.loads(scored.stdout)["points"]
        assert points == {"got": 9.5, "total": 15.0, "bonus": 4.0}

    def test_cli_check_v3(self, tmp_path):
        criteria = tmp_path / "criteria.yml"
        criteria.write_text(CRITERIA)
        result = CliRunner().invoke(app, ["check", str(criteria)])
        assert result.exit_code == 0
        assert "schema version 3" in result.output

    def test_update_v2_to_v3(self, tmp_path):
        criteria = tmp_path / "criteria.yml"
        criteria.write_text(
            "schema_version: 2\n"
            "grading:\n  context: Be fair\n"
            "criteria:\n"
            "  a:\n    description: A\n    max_points: 4\n    awarded_points: 2\n"
            "    prompt: Look\n"
        )
        result = CliRunner().invoke(app, ["update", str(criteria)])
        assert result.exit_code == 0, result.output
        data = Criteria(__import__("yaml").safe_load(criteria.read_text()))
        assert data["schema_version"] == 3
        assert data["grading"]["context"] == "Be fair"
        assert data["criteria"]["a"]["$points"] == [2.0, 4]

    def test_update_refuses_unmigratable(self, tmp_path):
        criteria = tmp_path / "criteria.yml"
        criteria.write_text(
            "schema_version: 2\n"
            "grading:\n  sources: ['src/*.c']\n"
            "criteria:\n  a:\n    description: A\n"
            "    max_points: 4\n    awarded_points: 0\n"
        )
        result = CliRunner().invoke(app, ["update", str(criteria)])
        assert result.exit_code == 1
        assert "schema_version: 2" in criteria.read_text()

    @pytest.mark.parametrize(
        "content",
        [
            "schema_version: 2\ncriteria:\n  a:\n    description: A\n"
            "    max_points: 4\n    awarded_points: '50%'\n",
            "criteria:\n  a:\n    $description: A\n    $points: ['50%', 4]\n",
        ],
    )
    def test_update_refuses_percentages(self, tmp_path, content):
        criteria = tmp_path / "criteria.yml"
        criteria.write_text(content)
        result = CliRunner().invoke(app, ["update", str(criteria)])
        assert result.exit_code == 1
        assert "not percentages" in result.output
        assert "criteria.a." in result.output
        assert criteria.read_text() == content
