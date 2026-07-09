from unittest import TestCase

from StudentScore.apply import apply_results
from StudentScore.schema import Criteria


class TestApplyResults(TestCase):
    def _v2(self):
        return {
            "schema_version": 2,
            "criteria": {
                "binary": {
                    "description": "Binary",
                    "all-tests-passed": {
                        "description": "Tests",
                        "awarded_points": 0,
                        "max_points": 10,
                    },
                },
                "build": {
                    "description": "Build",
                    "with-no-warnings": {
                        "description": "Warnings",
                        "awarded_points": 0,
                        "max_points": -1,
                    },
                },
                "bonus": {
                    "description": "Bonus",
                    "creativity": {
                        "description": "Creative",
                        "awarded_points": 0,
                        "bonus_points": 1,
                    },
                },
            },
        }

    def test_applies_points_and_rationale(self):
        updated, applied, unknown = apply_results(
            self._v2(),
            {
                "binary.all-tests-passed": {
                    "awarded_points": 10,
                    "rationale": "all green",
                }
            },
        )
        item = updated["criteria"]["binary"]["all-tests-passed"]
        self.assertEqual(item["awarded_points"], 10)
        self.assertEqual(item["rationale"], "all green")
        self.assertEqual(applied, ["binary.all-tests-passed"])
        self.assertEqual(unknown, [])

    def test_clamps_out_of_range(self):
        updated, _, _ = apply_results(
            self._v2(), {"binary.all-tests-passed": {"awarded_points": 99}}
        )
        self.assertEqual(
            updated["criteria"]["binary"]["all-tests-passed"]["awarded_points"], 10
        )

    def test_clamps_penalty(self):
        updated, _, _ = apply_results(
            self._v2(), {"build.with-no-warnings": {"awarded_points": -5}}
        )
        self.assertEqual(
            updated["criteria"]["build"]["with-no-warnings"]["awarded_points"], -1
        )

    def test_bonus_criterion(self):
        updated, applied, _ = apply_results(
            self._v2(), {"bonus.creativity": {"awarded_points": 1}}
        )
        self.assertEqual(
            updated["criteria"]["bonus"]["creativity"]["awarded_points"], 1
        )
        self.assertIn("bonus.creativity", applied)

    def test_reports_unknown_criteria(self):
        _, applied, unknown = apply_results(
            self._v2(), {"does.not.exist": {"awarded_points": 1}}
        )
        self.assertEqual(applied, [])
        self.assertEqual(unknown, ["does.not.exist"])

    def test_result_validates(self):
        updated, _, _ = apply_results(
            self._v2(),
            {
                "binary.all-tests-passed": {"awarded_points": 8},
                "bonus.creativity": {"awarded_points": 1},
            },
        )
        # Should not raise.
        Criteria(updated)

    def test_v1_leaf(self):
        raw = {
            "criteria": {
                "item": {"$description": "Item", "$points": [0, 5]},
            }
        }
        updated, applied, _ = apply_results(
            raw, {"item": {"awarded_points": 3, "rationale": "ok"}}
        )
        self.assertEqual(updated["criteria"]["item"]["$points"], [3, 5])
        self.assertEqual(updated["criteria"]["item"]["$rationale"], "ok")
        self.assertEqual(applied, ["item"])
