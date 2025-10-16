from unittest import TestCase

from StudentScore.schema import Criteria, CriteriaValidationError


class TestCriteria(TestCase):
    def test_valid(self):
        Criteria(
            {"criteria": {"test": {"$description": "Description", "$points": [1, 5]}}}
        )

    def test_max(self):
        with self.assertRaises(CriteriaValidationError) as exc:
            Criteria(
                {
                    "criteria": {
                        "test": {"$description": "Description", "$points": [6, 5]}
                    }
                }
            )
        self.assertIn("criteria/test/$points", str(exc.exception))

    def test_below(self):
        with self.assertRaises(CriteriaValidationError):
            Criteria(
                {
                    "criteria": {
                        "test": {"$description": "Description", "$points": [-2, 5]}
                    }
                }
            )

    def test_min(self):
        with self.assertRaises(CriteriaValidationError):
            Criteria(
                {
                    "criteria": {
                        "test": {"$description": "Description", "$points": [-6, -5]}
                    }
                }
            )

    def test_zero(self):
        with self.assertRaises(CriteriaValidationError):
            Criteria(
                {
                    "criteria": {
                        "test": {"$description": "Description", "$points": [0, 0]}
                    }
                }
            )

    def test_percent(self):
        Criteria(
            {
                "criteria": {
                    "test": {"$description": "Description", "$points": ["100%", 2]}
                }
            }
        )

    def test_smaller(self):
        with self.assertRaises(CriteriaValidationError):
            Criteria(
                {
                    "criteria": {
                        "test": {"$description": "Description", "$points": [2, -2]}
                    }
                }
            )

    def test_sequence_type_error(self):
        with self.assertRaises(CriteriaValidationError) as exc:
            Criteria(
                {
                    "criteria": {
                        "test": {"$description": "Description", "$points": "invalid"}
                    }
                }
            )
        self.assertIn("points must be provided as a two-item sequence", str(exc.exception))

    def test_sequence_length_error(self):
        with self.assertRaises(CriteriaValidationError):
            Criteria(
                {
                    "criteria": {
                        "test": {"$description": "Description", "$points": [1, 2, 3]}
                    }
                }
            )

    def test_tuple_points_are_accepted(self):
        Criteria(
            {
                "criteria": {
                    "test": {"$description": "Description", "$points": (1, 5)}
                }
            }
        )

    def test_percentage_format_error(self):
        with self.assertRaises(CriteriaValidationError):
            Criteria(
                {
                    "criteria": {
                        "test": {"$description": "Description", "$points": ["bad", 5]}
                    }
                }
            )

    def test_percentage_bounds_error(self):
        with self.assertRaises(CriteriaValidationError):
            Criteria(
                {
                    "criteria": {
                        "test": {"$description": "Description", "$points": ["150%", 5]}
                    }
                }
            )

    def test_requires_textual_description(self):
        with self.assertRaises(CriteriaValidationError):
            Criteria(
                {
                    "criteria": {
                        "$description": ["not", "valid"],
                        "test": {"$description": "Description", "$points": [1, 5]},
                    }
                }
            )

    def test_description_choice(self):
        with self.assertRaises(CriteriaValidationError):
            Criteria(
                {
                    "criteria": {
                        "test": {
                            "$description": "Description",
                            "$desc": "Duplicate",
                            "$points": [1, 5],
                        }
                    }
                }
            )

    def test_item_requires_description_and_points(self):
        with self.assertRaises(CriteriaValidationError) as exc:
            Criteria({"criteria": {"test": {"$points": [1, 5]}}})
        self.assertIn("either $description or $desc must be provided", str(exc.exception))

    def test_item_requires_points_or_bonus(self):
        with self.assertRaises(CriteriaValidationError) as exc:
            Criteria({"criteria": {"test": {"$description": "Description"}}})
        self.assertIn("either $points or $bonus must be provided", str(exc.exception))

    def test_section_entries_must_be_mappings(self):
        with self.assertRaises(CriteriaValidationError):
            Criteria({"criteria": ["not", "a", "mapping"]})
