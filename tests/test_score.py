from pathlib import Path
from unittest import TestCase

from StudentScore import Score

dir_path = Path(__file__).resolve(strict=True).parent


class TestScore(TestCase):
    def test_score(self):
        data = Score({
            "criteria": {
                "test": {
                    "$description": "Description",
                    "$points": [2, 2]
                }
            }
        })
        print(f'{data.points.got}/{data.points.total}')
        self.assertEqual(data.mark, 6.0)
        self.assertEqual(data.points.got, 2)
        self.assertEqual(data.points.total, 2)
        self.assertEqual(data.points.bonus, 0)
        self.assertTrue(data.success)

    def test_score(self):
        data = Score(str(
            Path(__file__)
            .resolve(strict=True).parent
            .joinpath('criteria.yml'))
        )
        print(f'{data.points.got}/{data.points.total}')
        self.assertEqual(data.mark, 4.5)
        self.assertEqual(data.points.got, 9)
        self.assertEqual(data.points.total, 13)
        self.assertEqual(data.points.bonus, 2)
        self.assertTrue(data.success)

    def test_zero_total(self):
        with self.assertRaises(ValueError):
            data = Score({
                "criteria": {
                    "test": {
                        "$description": "Description",
                        "$bonus": [2, 2]
                    }
                }
            })
            mark = data.mark

    def test_frac(self):
        data = Score({
            "criteria": {
                "test": {
                    "$description": "Description",
                    "$points": [970, 1000]
                }
            }
        })
        self.assertEqual(data.mark, 5.9)

    def test_bonus(self):

        data = Score({
            "criteria": {
                "experiment": {
                    "$description": "Description",
                    "$points": [2, 2]
                },
                "test": {
                    "$description": "Description",
                    "$bonus": [2, 2]
                }
            }
        })
        print(f'{data.points.got}/{data.points.total}')
        self.assertEqual(data.mark, 6.0)
        self.assertEqual(data.points.got, 4)
        self.assertEqual(data.points.total, 2)
        self.assertEqual(data.points.bonus, 2)
        self.assertTrue(data.success)
