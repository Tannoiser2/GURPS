import unittest

from App.pdf_structure_extractor import extract_pdf_structure
from App.preservation_policy import build_preservation_policy


class PreservationPolicyTests(unittest.TestCase):
    def test_pdf_dungeon_policy_forbids_compression(self):
        structure = extract_pdf_structure("\n".join(f"{i}. Room {i}" for i in range(1, 5)))
        policy = build_preservation_policy("pdf_import", structure)

        self.assertTrue(policy["preserve_rooms"])
        self.assertTrue(policy["forbid_structural_compression"])

    def test_ai_generated_policy_does_not_preserve_original_structure(self):
        policy = build_preservation_policy("ai_generated", {})

        self.assertFalse(policy["preserve_original_structure"])
        self.assertFalse(policy["forbid_structural_compression"])


if __name__ == "__main__":
    unittest.main()
