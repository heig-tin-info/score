from unittest import TestCase
from pathlib import Path

from click.testing import CliRunner
from StudentScore.__main__ import cli


class TestHelp(TestCase):
    def test_usage(self):
        runner = CliRunner()
        result = runner.invoke(cli)

        self.assertEqual(result.exit_code, 2)
        self.assertIn('Usage', result.output)
        self.assertIn('Invalid value for', result.output)


class TestCli(TestCase):
    @property
    def directory(self):
        return Path(__file__).resolve(strict=True).parent

    def test_success(self):
        runner = CliRunner()
        path = self.directory.joinpath('criteria.yml')
        result = runner.invoke(cli, [str(path)])
        print(f"Path: {path}")
        print(result.output)

        self.assertEqual(result.exit_code, 0)
        self.assertEqual('4.5', result.output.strip())

    def test_success(self):
        runner = CliRunner()
        path = self.directory.joinpath('criteria.yml')
        result = runner.invoke(cli, [str(path), '--verbose'])
        print(f"Path: {path}")
        print(result.output)

        self.assertEqual(result.exit_code, 0)
        self.assertIn('Got 9 points + 2 points out of 13 points', result.output.strip())
