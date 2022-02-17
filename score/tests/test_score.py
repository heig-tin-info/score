import os
from unittest import TestCase
from score import Score

dir_path = os.path.dirname(os.path.realpath(__file__))


class TestCriteria(TestCase):
    def test_file(self):
        with open(os.path.join(dir_path, 'criteria.yml')) as f:
            data = Score(f)
        print(f'{data.points.got}/{data.points.total}')
        self.assertEqual(data.mark, 4.5)
        self.assertEqual(data.points.got, 7)
        self.assertEqual(data.points.total, 10)
        self.assertEqual(data.points.bonus, 2)
        self.assertTrue(data.success)

    def test_neg_file(self):
        with open(os.path.join(dir_path, 'criteria-neg.yml')) as f:
            data = Score(f)
        print(f'{data.points.got}/{data.points.total}')
        self.assertEqual(data.mark, 1.0)
        self.assertEqual(data.points.got, -8)
        self.assertEqual(data.points.total, 10)
        self.assertEqual(data.points.bonus, 0)
        self.assertFalse(data.success)
