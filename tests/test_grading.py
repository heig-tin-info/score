from unittest import TestCase

from StudentScore.grading import build_prompt
from StudentScore.schema import Criteria


class TestBuildPrompt(TestCase):
    def _prompt(self):
        data = Criteria(
            {
                "schema_version": 2,
                "grading": {
                    "context": "Be a fair corrector.",
                    "student": {
                        "level": "Year 1",
                        "knows": ["loops"],
                        "learning": ["pointers"],
                    },
                },
                "criteria": {
                    "quadratic": {
                        "description": "Lab work",
                        "delta": {
                            "description": "Delta is correct",
                            "awarded_points": 0,
                            "max_points": 1,
                            "prompt": "Award 1 if delta = B*B - 4*A*C.",
                        },
                        "plain": {
                            "description": "No prompt here",
                            "awarded_points": 0,
                            "max_points": 2,
                        },
                    },
                    "creativity": {
                        "description": "Bonus",
                        "awarded_points": 0,
                        "bonus_points": 1,
                    },
                },
            }
        )
        return build_prompt(data)

    def test_includes_context_and_student(self):
        prompt = self._prompt()
        self.assertIn("Be a fair corrector.", prompt)
        self.assertIn("Niveau : Year 1", prompt)
        self.assertIn("- loops", prompt)
        self.assertIn("- pointers", prompt)

    def test_includes_criterion_prompt_and_scale(self):
        prompt = self._prompt()
        self.assertIn("## quadratic.delta", prompt)
        self.assertIn("Award 1 if delta = B*B - 4*A*C.", prompt)
        self.assertIn("Barème : 0 à 1 point(s).", prompt)
        self.assertIn("Bonus : 0 à 1 point(s).", prompt)

    def test_missing_prompt_has_placeholder(self):
        prompt = self._prompt()
        self.assertIn("## quadratic.plain", prompt)
        self.assertIn("aucune consigne spécifique", prompt)

    def test_lists_all_criteria_ids(self):
        prompt = self._prompt()
        self.assertIn(
            "quadratic.delta, quadratic.plain, creativity",
            prompt,
        )

    def test_works_without_grading_block(self):
        data = Criteria(
            {
                "criteria": {
                    "item": {"$description": "Item", "$points": [0, 1]},
                }
            }
        )
        prompt = build_prompt(data)
        self.assertIn("## item", prompt)
        self.assertNotIn("Profil de l'étudiant", prompt)
