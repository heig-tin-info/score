import json
from pathlib import Path
from unittest import TestCase

from typer.testing import CliRunner

from StudentScore.__main__ import app


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
