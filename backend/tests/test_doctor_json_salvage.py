import unittest

from App.adventure_doctor import _json_from_llm


class DoctorJsonSalvageTests(unittest.TestCase):
    def test_valid_object(self):
        self.assertEqual(_json_from_llm('{"a": 1, "b": [1, 2]}'), {"a": 1, "b": [1, 2]})

    def test_valid_array(self):
        self.assertEqual(_json_from_llm('[{"id": "n1"}, {"id": "n2"}]'), [{"id": "n1"}, {"id": "n2"}])

    def test_markdown_fence(self):
        self.assertEqual(_json_from_llm('```json\n{"x": 5}\n```'), {"x": 5})

    def test_truncated_object_recovered(self):
        # Stringa non terminata (max_tokens raggiunto): scarta l'elemento incompleto,
        # chiude le parentesi e recupera il resto.
        raw = '{"clues": [{"id": "c1", "text": "ok"}, {"id": "c2", "text": "tronc'
        out = _json_from_llm(raw)
        self.assertIn("clues", out)
        self.assertEqual(out["clues"][0], {"id": "c1", "text": "ok"})

    def test_truncated_array_recovered(self):
        raw = '[{"id": "n1", "name": "Aldric"}, {"id": "n2", "name": "inc'
        out = _json_from_llm(raw)
        self.assertIsInstance(out, list)
        self.assertEqual(out[0], {"id": "n1", "name": "Aldric"})


if __name__ == "__main__":
    unittest.main()
