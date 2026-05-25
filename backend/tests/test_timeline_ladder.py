import unittest

from App.pdf_structure_extractor import extract_timeline_events


class TimelineLadderTests(unittest.TestCase):
    def test_extracts_day_phase_round_headers(self):
        text = (
            "Day 1: The cult gathers at the docks.\n"
            "Day 2: A second victim is found.\n"
            "Hour 0: The ritual begins.\n"
            "Round 3: Reinforcements arrive.\n"
            "Phase II: The seal cracks.\n"
        )
        blocks = extract_timeline_events(text)
        labels = [b["label"] for b in blocks]
        self.assertTrue(any("Day 1" in l for l in labels))
        self.assertTrue(any("Day 2" in l for l in labels))
        self.assertTrue(any("Hour 0" in l for l in labels))
        self.assertTrue(any("Round 3" in l for l in labels))
        self.assertTrue(any("Phase II" in l for l in labels))

    def test_preserves_existing_prefixed_format(self):
        text = "Giorno 1: I PG arrivano\nEvento 2: Tradimento"
        blocks = extract_timeline_events(text)
        self.assertGreaterEqual(len(blocks), 2)

    def test_does_not_match_random_uppercase_with_number(self):
        text = "Stanza 3 contiene un teschio."
        blocks = extract_timeline_events(text)
        labels = [b["label"].lower() for b in blocks]
        self.assertFalse(any("stanza" in l for l in labels))


if __name__ == "__main__":
    unittest.main()
