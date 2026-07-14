from unittest import TestCase

from StudentScore.apply import apply_results, filter_milestone
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


class TestFilterMilestone(TestCase):
    def _v2(self):
        return {
            "schema_version": 2,
            "grading": {"context": "Be fair."},
            "criteria": {
                "structure": {
                    "description": "Program structure",
                    "prototypes": {
                        "description": "Prototypes are declared",
                        "awarded_points": 0,
                        "max_points": 2,
                        "milestone": "mid-review",
                    },
                    "style": {
                        "description": "Consistent style",
                        "awarded_points": 0,
                        "max_points": 1,
                    },
                },
                "final": {
                    "description": "Final behaviour",
                    "output": {
                        "description": "Correct output",
                        "awarded_points": 0,
                        "max_points": 4,
                    },
                },
            },
        }

    def test_keeps_only_tagged_leaves(self):
        filtered, kept = filter_milestone(self._v2(), "mid-review")
        self.assertEqual(kept, 1)
        self.assertIn("prototypes", filtered["criteria"]["structure"])
        self.assertNotIn("style", filtered["criteria"]["structure"])
        # A section left without any leaf disappears entirely.
        self.assertNotIn("final", filtered["criteria"])
        # Section descriptions and the grading block survive the filter.
        self.assertEqual(
            filtered["criteria"]["structure"]["description"], "Program structure"
        )
        self.assertEqual(filtered["grading"], {"context": "Be fair."})

    def test_filtered_result_validates(self):
        filtered, _ = filter_milestone(self._v2(), "mid-review")
        Criteria(filtered)  # should not raise

    def test_unknown_milestone_keeps_nothing(self):
        filtered, kept = filter_milestone(self._v2(), "nope")
        self.assertEqual(kept, 0)
        self.assertEqual(
            [k for k, v in filtered["criteria"].items() if isinstance(v, dict)], []
        )

    def test_v1_dollar_milestone(self):
        raw = {
            "criteria": {
                "tagged": {
                    "$description": "Tagged",
                    "$points": [0, 2],
                    "$milestone": "mid-review",
                },
                "plain": {"$description": "Plain", "$points": [0, 2]},
            }
        }
        filtered, kept = filter_milestone(raw, "mid-review")
        self.assertEqual(kept, 1)
        self.assertIn("tagged", filtered["criteria"])
        self.assertNotIn("plain", filtered["criteria"])
