from pathlib import Path
from unittest import TestCase

from StudentScore import Score

dir_path = Path(__file__).resolve(strict=True).parent


class TestCriteria(TestCase):
    def test_file(self):
        with open(dir_path.joinpath('criteria.yml'), encoding='utf8') as f:
            data = Score(f)
        self.assertEqual(data.mark, 4.5)
        self.assertEqual(data.points.got, 9)
        self.assertEqual(data.points.total, 13)
        self.assertEqual(data.points.bonus, 2)
        self.assertTrue(data.success)

    def test_neg_file(self):
        with open(dir_path.joinpath('criteria-neg.yml'),
                  encoding='utf8') as f:
            data = Score(f)
        print(f'{data.points.got}/{data.points.total}')
        self.assertEqual(data.mark, 1.0)
        self.assertEqual(data.points.got, -8)
        self.assertEqual(data.points.total, 10)
        self.assertEqual(data.points.bonus, 0)
        self.assertFalse(data.success)

    def test_percent_file(self):
        with open(dir_path.joinpath('criteria-percent.yml'),
                  encoding='utf8') as f:
            data = Score(f)
        print(f'{data.points.got}/{data.points.total}')
        self.assertEqual(data.mark, 4.8)
        self.assertEqual(data.points.got, 7.5)
        self.assertEqual(data.points.total, 10)
        self.assertEqual(data.points.bonus, 2)
        self.assertTrue(data.success)
