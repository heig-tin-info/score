import json
from pathlib import Path
import sys
import tempfile
from unittest import TestCase
from unittest.mock import patch

from typer.testing import CliRunner

from StudentScore.__main__ import app, cli


class TestHelp(TestCase):
    def test_usage(self):
        runner = CliRunner()
        result = runner.invoke(app)

        self.assertEqual(result.exit_code, 2)
        self.assertIn("Usage", result.output)
        self.assertIn("Invalid value for '[FILE]'", result.output)


class TestCli(TestCase):
    @property
    def directory(self):
        return Path(__file__).resolve(strict=True).parent

    def test_success_default_output(self):
        runner = CliRunner()
        path = self.directory.joinpath("criteria.yml")
        result = runner.invoke(app, [str(path)])
        print(f"Path: {path}")
        print(result.output)

        self.assertEqual(result.exit_code, 0)
        self.assertEqual("4.5", result.output.strip())

    def test_success_verbose_output(self):
        runner = CliRunner()
        path = self.directory.joinpath("criteria.yml")
        result = runner.invoke(app, [str(path), "--verbose"])
        print(f"Path: {path}")
        print(result.output)

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Got 9 points + 2 points out of 13 points", result.output.strip())

    def test_json_output(self):
        runner = CliRunner()
        path = self.directory.joinpath("criteria.yml")
        result = runner.invoke(app, ["json", str(path)])

        self.assertEqual(result.exit_code, 0)
        payload = json.loads(result.output)
        self.assertEqual(payload["mark"], 4.5)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["points"]["got"], 9)
        self.assertEqual(payload["points"]["total"], 13)
        self.assertEqual(payload["points"]["bonus"], 2)

    def test_schema_output(self):
        runner = CliRunner()
        result = runner.invoke(app, ["schema"])

        self.assertEqual(result.exit_code, 0)
        schema = json.loads(result.output)
        self.assertEqual(schema["type"], "object")
        self.assertIn("properties", schema)

    def test_grade_milestone_filters_prompt(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "criteria.yml"
            path.write_text(
                "schema_version: 2\n"
                "criteria:\n"
                "  tagged:\n"
                "    description: Tagged criterion\n"
                "    awarded_points: 0\n"
                "    max_points: 2\n"
                "    milestone: mid-review\n"
                "  plain:\n"
                "    description: Plain criterion\n"
                "    awarded_points: 0\n"
                "    max_points: 3\n",
                encoding="utf-8",
            )

            result = runner.invoke(
                app, ["grade", str(path), "--milestone", "mid-review"]
            )
            self.assertEqual(result.exit_code, 0)
            self.assertIn("## tagged", result.output)
            self.assertNotIn("## plain", result.output)

    def test_grade_unknown_milestone_fails(self):
        runner = CliRunner()
        path = self.directory.joinpath("criteria.yml")
        result = runner.invoke(app, ["grade", str(path), "--milestone", "nope"])
        self.assertEqual(result.exit_code, 1)

    def test_entry_point_propagates_exit_code(self):
        # Through the real entry point (`score` / `python -m`), a typer.Exit
        # raised inside a command must reach the shell: click returns the
        # code with standalone_mode=False instead of raising (CI relies on it).
        path = self.directory.joinpath("criteria.yml")
        argv = ["score", "grade", str(path), "--milestone", "nope"]
        with patch.object(sys, "argv", argv):
            with self.assertRaises(SystemExit) as exc:
                cli()
        self.assertEqual(exc.exception.code, 1)

    def test_update_command(self):
        runner = CliRunner()
        source = self.directory.joinpath("criteria.yml")

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "criteria.yml"
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

            result = runner.invoke(app, ["update", str(target)])

            self.assertEqual(result.exit_code, 0)
            self.assertIn("schema version 2", result.output)

            content = target.read_text(encoding="utf-8")
            self.assertIn("schema_version: 2", content)
            self.assertIn("max_points: -4", content)
            self.assertIn("awarded_points: -2", content)
