import unittest

from App.claude_service import _extract_json_object


class TruncatedJsonRecoveryTests(unittest.TestCase):
    def test_recovers_truncated_array_of_objects(self):
        truncated = """```json
{
  "clues": [
    {"label": "Mirror", "text": "Karl Vayne's stage mirror"},
    {"label": "Letters", "text": "Hungarian occult letters"},
    {"label": "Ledger", "text": "
"""
        parsed = _extract_json_object(truncated)
        self.assertIn("clues", parsed)
        # The last truncated object is dropped; the first two complete ones
        # remain accessible.
        labels = [c.get("label") for c in parsed["clues"]]
        self.assertIn("Mirror", labels)
        self.assertIn("Letters", labels)

    def test_recovers_truncated_nested_array(self):
        truncated = """{
  "actors": [
    {
      "name": "Tockman",
      "knows": ["orari", "punti ciechi"],
      "wants": ["denaro
"""
        parsed = _extract_json_object(truncated)
        self.assertIn("actors", parsed)
        self.assertEqual(parsed["actors"][0]["name"], "Tockman")
        self.assertIn("orari", parsed["actors"][0]["knows"])


if __name__ == "__main__":
    unittest.main()
