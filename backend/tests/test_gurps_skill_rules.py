import unittest

from App.character_creation import skill_cost
from App.data_skills import skill_default_level, skill_is_tech_level


class GurpsSkillRulesTests(unittest.TestCase):
    def test_skill_cost_table_easy(self):
        stats = {"agilita": 12}
        self.assertEqual(skill_cost("lanciare", 12, stats), 1)
        self.assertEqual(skill_cost("lanciare", 13, stats), 2)
        self.assertEqual(skill_cost("lanciare", 14, stats), 4)
        self.assertEqual(skill_cost("lanciare", 15, stats), 8)
        self.assertEqual(skill_cost("lanciare", 16, stats), 12)

    def test_skill_cost_table_average(self):
        stats = {"agilita": 12}
        self.assertEqual(skill_cost("furtivita", 11, stats), 1)
        self.assertEqual(skill_cost("furtivita", 12, stats), 2)
        self.assertEqual(skill_cost("furtivita", 13, stats), 4)
        self.assertEqual(skill_cost("furtivita", 14, stats), 8)
        self.assertEqual(skill_cost("furtivita", 15, stats), 12)

    def test_skill_cost_table_hard(self):
        stats = {"agilita": 12}
        self.assertEqual(skill_cost("acrobazia", 10, stats), 1)
        self.assertEqual(skill_cost("acrobazia", 11, stats), 2)
        self.assertEqual(skill_cost("acrobazia", 12, stats), 4)
        self.assertEqual(skill_cost("acrobazia", 13, stats), 8)
        self.assertEqual(skill_cost("acrobazia", 14, stats), 12)

    def test_default_level_uses_difficulty_penalty(self):
        stats = {"agilita": 12, "intelligenza": 11}
        self.assertEqual(skill_default_level("lanciare", stats), 8)
        self.assertEqual(skill_default_level("furtivita", stats), 7)
        self.assertEqual(skill_default_level("acrobazia", stats), 6)
        self.assertEqual(skill_default_level("investigare", stats), 6)

    def test_rule_of_20_caps_default_attribute(self):
        stats = {"agilita": 25}
        self.assertEqual(skill_default_level("lanciare", stats), 16)
        self.assertEqual(skill_default_level("furtivita", stats), 15)
        self.assertEqual(skill_default_level("acrobazia", stats), 14)

    def test_current_macro_tech_skills_are_flagged(self):
        self.assertTrue(skill_is_tech_level("meccanica"))
        self.assertTrue(skill_is_tech_level("medicina"))
        self.assertTrue(skill_is_tech_level("informatica"))
        self.assertFalse(skill_is_tech_level("persuadere"))


if __name__ == "__main__":
    unittest.main()
