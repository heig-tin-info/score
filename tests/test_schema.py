from unittest import TestCase

from voluptuous.error import MultipleInvalid

from StudentScore.schema import Criteria


class TestCriteria(TestCase):
    def test_valid(self):
        Criteria({
            "criteria": {
                "test": {
                    "$description": "Description",
                    "$points": [1, 5]
                }
            }
        })

    def test_max(self):
        with self.assertRaises(MultipleInvalid):
            Criteria({
                "criteria": {
                    "test": {
                        "$description": "Description",
                        "$points": [6, 5]
                    }
                }
            })

    def test_below(self):
        with self.assertRaises(MultipleInvalid):
            Criteria({
                "criteria": {
                    "test": {
                        "$description": "Description",
                        "$points": [-2, 5]
                    }
                }
            })

    def test_min(self):
        with self.assertRaises(MultipleInvalid):
            Criteria({
                "criteria": {
                    "test": {
                        "$description": "Description",
                        "$points": [-6, -5]
                    }
                }
            })

    def test_zero(self):
        with self.assertRaises(MultipleInvalid):
            Criteria({
                "criteria": {
                    "test": {
                        "$description": "Description",
                        "$points": [0, 0]
                    }
                }
            })

    def test_percent(self):
        Criteria({
            "criteria": {
                "test": {
                    "$description": "Description",
                    "$points": ['100%', 2]
                }
            }
        })

    def test_smaller(self):
        with self.assertRaises(MultipleInvalid):
            Criteria({
                "criteria": {
                    "test": {
                        "$description": "Description",
                        "$points": [2, -2]
                    }
                }
            })
