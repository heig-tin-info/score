from pathlib import Path
from unittest import TestCase

from StudentScore import Score


dir_path = Path(__file__).resolve(strict=True).parent


class TestScore(TestCase):
    def test_score(self):
        data = Score(
            {"criteria": {"test": {"$description": "Description", "$points": [2, 2]}}}
        )
        print(f"{data.points.got}/{data.points.total}")
        self.assertEqual(data.mark, 6.0)
        self.assertEqual(data.points.got, 2)
        self.assertEqual(data.points.total, 2)
        self.assertEqual(data.points.bonus, 0)
        self.assertTrue(data.success)

    def test_score_from_file(self):
        data = Score(
            str(Path(__file__).resolve(strict=True).parent.joinpath("criteria.yml"))
        )
        print(f"{data.points.got}/{data.points.total}")
        self.assertEqual(data.mark, 4.5)
        self.assertEqual(data.points.got, 9)
        self.assertEqual(data.points.total, 13)
        self.assertEqual(data.points.bonus, 2)
        self.assertTrue(data.success)

    def test_zero_total(self):
        with self.assertRaises(ValueError):
            Score(
                {
                    "criteria": {
                        "test": {"$description": "Description", "$bonus": [2, 2]}
                    }
                }
            ).mark

    def test_bonus(self):
        data = Score(
            {
                "criteria": {
                    "experiment": {"$description": "Description", "$points": [2, 2]},
                    "test": {"$description": "Description", "$bonus": [2, 2]},
                }
            }
        )
        print(f"{data.points.got}/{data.points.total}")
        self.assertEqual(data.mark, 6.0)
        self.assertEqual(data.points.got, 4)
        self.assertEqual(data.points.total, 2)
        self.assertEqual(data.points.bonus, 2)
        self.assertTrue(data.success)

    def test_score_v2_format(self):
        data = Score(
            {
                "schema_version": 2,
                "criteria": {
                    "group": {
                        "description": "Group description",
                        "item": {
                            "description": "Item description",
                            "max_points": 4,
                            "awarded_points": 4,
                        },
                        "bonus": {
                            "description": "Bonus description",
                            "bonus_points": 2,
                            "awarded_points": 1,
                        },
                    }
                },
            }
        )
        self.assertEqual(data.mark, 6.0)
        self.assertEqual(data.points.got, 5)
        self.assertEqual(data.points.total, 4)
        self.assertEqual(data.points.bonus, 1)
