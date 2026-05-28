"""T4 — Escalation limiter edge cases

Coverage:
- Stallo 3+ turni → tier aumenta
- Clock completion → tier ≥5
- Finale condition + clock → tier 6
- Genre max_default_tier cap
- Passive intent capped at 3
- Combat intent bumped to min 4
- Critical failure → tier 4
"""

import unittest

from App.escalation_limiter import compute_allowed_escalation_tier, classify_event_tier


def _tier(outcome="successo pieno", intent="", profile="investigation_graph",
          clocks=None, ctx=None, progress=0, genre_profile=None):
    return compute_allowed_escalation_tier(
        outcome, intent, profile,
        active_clocks=clocks,
        scene_context=ctx,
        genre_profile=genre_profile,
        investigation_progress=progress,
    )


class TestBaseTierFromOutcome(unittest.TestCase):
    def test_success_gives_tier_2(self):
        self.assertEqual(_tier("successo pieno"), 2)

    def test_critical_success_gives_tier_2(self):
        self.assertEqual(_tier("critico"), 2)

    def test_partial_success_gives_tier_3(self):
        self.assertEqual(_tier("successo parziale"), 3)

    def test_failure_gives_tier_3(self):
        self.assertEqual(_tier("fallimento"), 3)

    def test_critical_failure_gives_tier_4(self):
        self.assertEqual(_tier("fallimento critico"), 4)


class TestInvestigationProgress(unittest.TestCase):
    def test_progress_reduces_tier_on_success(self):
        """Finding a clue lowers tier by 1 (min 1)."""
        tier_with = _tier("successo pieno", progress=1)
        tier_without = _tier("successo pieno", progress=0)
        self.assertLess(tier_with, tier_without)
        self.assertEqual(tier_with, 1)

    def test_stallo_3_turns_increases_tier(self):
        """3+ consecutive turns without progress → tier +1."""
        tier_stall = _tier("successo pieno", progress=-3)
        tier_normal = _tier("successo pieno", progress=0)
        self.assertGreater(tier_stall, tier_normal)

    def test_stallo_2_turns_no_change(self):
        """Only -3 or worse triggers the bump."""
        tier_2 = _tier("successo pieno", progress=-2)
        tier_0 = _tier("successo pieno", progress=0)
        self.assertEqual(tier_2, tier_0)


class TestClockAndFinale(unittest.TestCase):
    def test_clock_completion_raises_tier_to_5(self):
        tier = _tier("successo pieno", clocks=[{"completed": True, "tick": 1}])
        self.assertGreaterEqual(tier, 5)

    def test_completed_clock_in_context_raises_to_5(self):
        tier = _tier("fallimento", ctx={"completed_clock": True})
        self.assertGreaterEqual(tier, 5)

    def test_explicit_trigger_raises_to_5(self):
        tier = _tier("successo pieno", ctx={"explicit_trigger": True})
        self.assertGreaterEqual(tier, 5)

    def test_finale_plus_clock_gives_tier_6(self):
        tier = _tier(
            "successo pieno",
            clocks=[{"completed": True, "tick": 1}],
            ctx={"finale_condition_met": True, "completed_clock": True},
        )
        self.assertEqual(tier, 6)

    def test_finale_alone_no_tier_6(self):
        """Finale condition without clock or trigger cannot produce tier 6."""
        tier = _tier("successo pieno", ctx={"finale_condition_met": True})
        self.assertLess(tier, 6)

    def test_tier_6_without_finale_capped_at_5(self):
        """Safeguard: tier 6 is blocked without finale or clock."""
        tier = _tier("fallimento critico")
        self.assertLessEqual(tier, 4)


class TestGenreCap(unittest.TestCase):
    def test_max_default_tier_3_caps_failure(self):
        """Genre with max_default_tier=3 (e.g. detective_classico) caps at 3."""
        genre = {"max_default_tier": 3, "allowed_escalations": [], "forbidden_escalations": []}
        tier = _tier("fallimento critico", genre_profile=genre)
        self.assertLessEqual(tier, 3)

    def test_max_default_tier_5_allows_4(self):
        genre = {"max_default_tier": 5, "allowed_escalations": [], "forbidden_escalations": []}
        tier = _tier("fallimento critico", genre_profile=genre)
        self.assertEqual(tier, 4)

    def test_genre_cap_does_not_block_clock_events(self):
        """Clock completion bypasses max_default_tier cap."""
        genre = {"max_default_tier": 3, "allowed_escalations": [], "forbidden_escalations": []}
        tier = _tier("successo pieno", clocks=[{"completed": True}], genre_profile=genre)
        self.assertGreaterEqual(tier, 5)


class TestIntentModifiers(unittest.TestCase):
    def test_passive_investigation_capped_at_3(self):
        tier = _tier("fallimento", intent="investigation")
        self.assertLessEqual(tier, 3)

    def test_passive_observation_capped_at_3(self):
        tier = _tier("fallimento critico", intent="observation")
        self.assertLessEqual(tier, 3)

    def test_combat_intent_bumped_to_min_4(self):
        tier = _tier("successo pieno", intent="combat")
        self.assertGreaterEqual(tier, 4)

    def test_stealth_intent_capped_at_4(self):
        tier = _tier("fallimento critico", intent="stealth")
        self.assertLessEqual(tier, 4)

    def test_no_intent_uses_default(self):
        tier = _tier("fallimento", intent="")
        self.assertEqual(tier, 3)


class TestClassifyEventTier(unittest.TestCase):
    def test_story_over_is_tier_6(self):
        self.assertEqual(classify_event_tier({"story_over": True}), 6)

    def test_combat_is_tier_4(self):
        self.assertEqual(classify_event_tier({"activate_combat": True}), 4)

    def test_threat_increase_is_tier_3(self):
        self.assertEqual(classify_event_tier({"threat_increase": 1}), 3)

    def test_clue_progress_is_tier_2(self):
        self.assertEqual(classify_event_tier({"clue_progress": [{"clue_id": "c1"}]}), 2)

    def test_npc_update_is_tier_1(self):
        self.assertEqual(classify_event_tier({"npc_updates": [{"id": "npc1"}]}), 1)

    def test_empty_update_is_tier_0(self):
        self.assertEqual(classify_event_tier({}), 0)

    def test_string_event_with_murder_is_tier_5(self):
        self.assertEqual(classify_event_tier("murder"), 5)


if __name__ == "__main__":
    unittest.main()
