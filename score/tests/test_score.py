import os
from unittest import TestCase
from score import Score

dir_path = os.path.dirname(os.path.realpath(__file__))


class TestCriteria(TestCase):
    def test_file(self):
        with open(os.path.join(dir_path, 'criteria.yml')) as f:
            data = Score(f)
        self.assertEqual(data.mark, 4.0)
        self.assertEqual(data.points.got, 4.0)
        self.assertEqual(data.points.total, 5.0)
        self.assertEqual(data.points.bonus, 1.0)
        self.assertTrue(data.success)