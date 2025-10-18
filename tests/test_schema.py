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

    def test_negative_penalty_bounds(self):
        with self.assertRaises(CriteriaValidationError) as exc:
            Criteria(
                {
                    "criteria": {
                        "test": {
                            "$description": "Description",
                            "$points": [-4, -2],
                        }
                    }
                }
            )
        self.assertIn(
            "cannot be smaller than available penalty",
            str(exc.exception),
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
        with self.assertRaises(CriteriaValidationError) as exc:
            Criteria(
                {
                    "criteria": {
                        "test": {"$description": "Description", "$points": [0, 0]}
                    }
                }
            )
        message = str(exc.exception)
        self.assertIn("criteria/test/$points", message)
        self.assertIn("No points given to this criteria.", message)

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

    def test_negative_obtained_with_positive_total(self):
        with self.assertRaises(CriteriaValidationError) as exc:
            Criteria(
                {
                    "criteria": {
                        "test": {
                            "$description": "Description",
                            "$points": [-1, 5],
                        }
                    }
                }
            )
        self.assertIn(
            "cannot be smaller than zero",
            str(exc.exception),
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
        self.assertIn(
            "points must be provided as a two-item sequence", str(exc.exception)
        )

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
            {"criteria": {"test": {"$description": "Description", "$points": (1, 5)}}}
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

    def test_points_must_be_numeric(self):
        with self.assertRaises(CriteriaValidationError) as exc:
            Criteria(
                {
                    "criteria": {
                        "test": {
                            "$description": "Description",
                            "$points": [object(), 5],
                        }
                    }
                }
            )
        self.assertIn("points must be numeric", str(exc.exception))

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

    def test_description_list_must_be_text(self):
        with self.assertRaises(CriteriaValidationError):
            Criteria(
                {
                    "criteria": {
                        "test": {
                            "$description": ["Valid", 3],
                            "$points": [1, 5],
                        }
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
        self.assertIn(
            "either $description or $desc must be provided", str(exc.exception)
        )

    def test_item_requires_points_or_bonus(self):
        with self.assertRaises(CriteriaValidationError) as exc:
            Criteria({"criteria": {"test": {"$description": "Description"}}})
        self.assertIn("either $points or $bonus must be provided", str(exc.exception))

    def test_nested_sections_roundtrip(self):
        data = Criteria(
            {
                "criteria": {
                    "parent": {
                        "$description": "Parent",
                        "child": {
                            "$desc": "Child",
                            "$rationale": ["Line one", "Line two"],
                            "$bonus": [1, 1],
                        },
                    }
                }
            }
        )
        nested = data["criteria"]["parent"]["child"]
        self.assertEqual(nested["$desc"], "Child")
        self.assertEqual(nested["$rationale"], ["Line one", "Line two"])
        self.assertEqual(nested["$bonus"], [1.0, 1])

    def test_section_entries_must_be_mappings(self):
        with self.assertRaises(CriteriaValidationError):
            Criteria({"criteria": ["not", "a", "mapping"]})

    def test_rationale_allows_none(self):
        data = Criteria(
            {
                "criteria": {
                    "test": {
                        "$description": "Description",
                        "$points": [1, 5],
                        "$rationale": None,
                    }
                }
            }
        )
        self.assertNotIn("$rationale", data["criteria"]["test"])

    def test_section_description_none(self):
        data = Criteria(
            {
                "criteria": {
                    "section": {
                        "$description": None,
                        "test": {"$description": "Desc", "$points": [1, 5]},
                    }
                }
            }
        )
        self.assertNotIn("$description", data["criteria"]["section"])

    def test_total_points_must_be_integer(self):
        with self.assertRaises(CriteriaValidationError) as exc:
            Criteria(
                {
                    "criteria": {
                        "test": {"$description": "Desc", "$points": [1, "five"]}
                    }
                }
            )
        self.assertIn("total points must be an integer", str(exc.exception))

    def test_unrecognized_field(self):
        with self.assertRaises(CriteriaValidationError) as exc:
            Criteria(
                {
                    "criteria": {
                        "test": {
                            "$description": "Desc",
                            "$points": [1, 5],
                            "$unexpected": "value",
                        }
                    }
                }
            )
        self.assertIn("unrecognized criteria field", str(exc.exception))

    def test_test_field_accepts_string(self):
        data = Criteria(
            {
                "criteria": {
                    "test": {
                        "$description": "Desc",
                        "$points": [1, 5],
                        "$test": "pytest -k something",
                    }
                }
            }
        )
        self.assertEqual(
            data["criteria"]["test"]["$test"],
            "pytest -k something",
        )

    def test_test_field_requires_string(self):
        with self.assertRaises(CriteriaValidationError) as exc:
            Criteria(
                {
                    "criteria": {
                        "test": {
                            "$description": "Desc",
                            "$points": [1, 5],
                            "$test": ["not", "a", "string"],
                        }
                    }
                }
            )
        self.assertIn("value must be a string", str(exc.exception))

    def test_entry_requires_mapping(self):
        with self.assertRaises(CriteriaValidationError) as exc:
            Criteria(
                {
                    "criteria": {
                        "test": [
                            {"$description": "Desc", "$points": [1, 5]},
                        ]
                    }
                }
            )
        self.assertIn("criteria entries must be mappings", str(exc.exception))

    def test_section_desc_alias(self):
        data = Criteria(
            {
                "criteria": {
                    "section": {
                        "$desc": "Alias",
                        "test": {"$description": "Desc", "$points": [1, 5]},
                    }
                }
            }
        )
        self.assertEqual(data["criteria"]["section"]["$desc"], "Alias")

    def test_section_description_choice_error(self):
        with self.assertRaises(CriteriaValidationError) as exc:
            Criteria(
                {
                    "criteria": {
                        "section": {
                            "$description": "Desc",
                            "$desc": "Duplicate",
                            "test": {"$description": "Desc", "$points": [1, 5]},
                        }
                    }
                }
            )
        self.assertIn("use either $description or $desc, not both", str(exc.exception))

    def test_root_must_be_mapping(self):
        with self.assertRaises(CriteriaValidationError) as exc:
            Criteria(["not", "a", "mapping"])  # type: ignore[arg-type]
        self.assertIn("criteria definition must be a mapping", str(exc.exception))

    def test_missing_criteria_definition(self):
        with self.assertRaises(CriteriaValidationError) as exc:
            Criteria({})
        self.assertIn("missing criteria definition", str(exc.exception))
