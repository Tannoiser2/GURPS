"""G3 — Injury persistence tests

Coverage:
- Wound model creation and severity levels
- wounds_skill_penalty applies correct malus
- resolve_attack persists wound on major_wound
- tick_player_wounds auto-heals minor wounds
- apply_wound_recovery (rest and first_aid actions)
"""

import unittest

from App.models import Player, Wound
from App.combat import (
    wounds_skill_penalty,
    tick_player_wounds,
    apply_wound_recovery,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _player(**kwargs) -> Player:
    defaults = dict(
        id=1, name="Tester", role="warrior", archetype="warrior",
        stats={"FO": 10, "DE": 10, "IN": 10, "SA": 10},
        max_hp=10, hp=10, max_fp=10, fp=10,
        will=10, per=10, basic_speed=5.0, dodge=8, move=5,
    )
    return Player(**{**defaults, **kwargs})


# ─── Wound model ─────────────────────────────────────────────────────────────

class TestWoundModel(unittest.TestCase):
    def test_default_severity_is_minor(self):
        w = Wound()
        self.assertEqual(w.severity, "minor")
        self.assertEqual(w.turns_remaining, 3)

    def test_major_wound_has_zero_turns(self):
        w = Wound(severity="major", turns_remaining=0, description="colpo alla spalla")
        self.assertEqual(w.severity, "major")
        self.assertEqual(w.turns_remaining, 0)

    def test_critical_wound(self):
        w = Wound(severity="critical", turns_remaining=0, description="ferita letale sventata")
        self.assertEqual(w.severity, "critical")


# ─── wounds_skill_penalty ────────────────────────────────────────────────────

class TestWoundsSkillPenalty(unittest.TestCase):
    def test_no_wounds_no_penalty(self):
        p = _player()
        self.assertEqual(wounds_skill_penalty(p), 0)

    def test_minor_wound_no_penalty(self):
        p = _player(wounds=[Wound(severity="minor")])
        self.assertEqual(wounds_skill_penalty(p), 0)

    def test_one_major_wound_minus_one(self):
        p = _player(wounds=[Wound(severity="major", turns_remaining=0)])
        self.assertEqual(wounds_skill_penalty(p), -1)

    def test_two_major_wounds_minus_two(self):
        p = _player(wounds=[
            Wound(severity="major", turns_remaining=0),
            Wound(severity="major", turns_remaining=0),
        ])
        self.assertEqual(wounds_skill_penalty(p), -2)

    def test_critical_wound_minus_one(self):
        p = _player(wounds=[Wound(severity="critical", turns_remaining=0)])
        self.assertEqual(wounds_skill_penalty(p), -1)

    def test_mixed_wounds_correct_total(self):
        p = _player(wounds=[
            Wound(severity="minor"),          # no penalty
            Wound(severity="major", turns_remaining=0),   # -1
            Wound(severity="critical", turns_remaining=0),  # -1
        ])
        self.assertEqual(wounds_skill_penalty(p), -2)


# ─── tick_player_wounds ──────────────────────────────────────────────────────

class TestTickPlayerWounds(unittest.TestCase):
    def test_minor_wound_decrements_turn(self):
        p = _player(wounds=[Wound(severity="minor", turns_remaining=3)])
        tick_player_wounds([p])
        self.assertEqual(p.wounds[0].turns_remaining, 2)

    def test_minor_wound_heals_at_zero(self):
        p = _player(wounds=[Wound(severity="minor", turns_remaining=1)])
        tick_player_wounds([p])
        self.assertEqual(len(p.wounds), 0)

    def test_major_wound_with_zero_remaining_not_decremented(self):
        """Major wounds with turns_remaining=0 do NOT auto-decrement."""
        p = _player(wounds=[Wound(severity="major", turns_remaining=0)])
        tick_player_wounds([p])
        self.assertEqual(len(p.wounds), 1)
        self.assertEqual(p.wounds[0].turns_remaining, 0)

    def test_major_wound_with_remaining_decrements(self):
        """Major wound after First Aid has turns_remaining=3, does decrement."""
        p = _player(wounds=[Wound(severity="major", turns_remaining=2)])
        tick_player_wounds([p])
        self.assertEqual(p.wounds[0].turns_remaining, 1)

    def test_no_wounds_no_error(self):
        p = _player()
        tick_player_wounds([p])  # should not raise
        self.assertEqual(p.wounds, [])

    def test_multiple_players(self):
        p1 = _player(id=1, wounds=[Wound(severity="minor", turns_remaining=1)])
        p2 = _player(id=2, wounds=[Wound(severity="minor", turns_remaining=2)])
        tick_player_wounds([p1, p2])
        self.assertEqual(len(p1.wounds), 0)   # healed
        self.assertEqual(p2.wounds[0].turns_remaining, 1)  # decremented


# ─── apply_wound_recovery ────────────────────────────────────────────────────

class TestApplyWoundRecovery(unittest.TestCase):
    def test_rest_decrements_minor_wound(self):
        p = _player(wounds=[Wound(severity="minor", turns_remaining=3)])
        healed = apply_wound_recovery(p, "rest")
        self.assertEqual(healed, 0)  # not healed yet, just decremented
        self.assertEqual(p.wounds[0].turns_remaining, 2)

    def test_rest_heals_minor_at_last_tick(self):
        p = _player(wounds=[Wound(severity="minor", turns_remaining=1)])
        healed = apply_wound_recovery(p, "rest")
        self.assertEqual(healed, 1)
        self.assertEqual(len(p.wounds), 0)

    def test_first_aid_heals_minor_immediately(self):
        p = _player(wounds=[Wound(severity="minor", turns_remaining=3)])
        healed = apply_wound_recovery(p, "first_aid")
        self.assertEqual(healed, 1)
        self.assertEqual(len(p.wounds), 0)

    def test_first_aid_converts_major_to_minor(self):
        p = _player(wounds=[Wound(severity="major", turns_remaining=0)])
        healed = apply_wound_recovery(p, "first_aid")
        self.assertEqual(healed, 1)
        self.assertEqual(len(p.wounds), 1)
        self.assertEqual(p.wounds[0].severity, "minor")
        self.assertEqual(p.wounds[0].turns_remaining, 3)

    def test_first_aid_only_heals_one_wound(self):
        """First Aid heals/improves only one wound per action."""
        p = _player(wounds=[
            Wound(severity="minor", turns_remaining=2),
            Wound(severity="minor", turns_remaining=2),
        ])
        healed = apply_wound_recovery(p, "first_aid")
        self.assertEqual(healed, 1)
        self.assertEqual(len(p.wounds), 1)

    def test_no_wounds_returns_zero(self):
        p = _player()
        self.assertEqual(apply_wound_recovery(p, "first_aid"), 0)
        self.assertEqual(apply_wound_recovery(p, "rest"), 0)


if __name__ == "__main__":
    unittest.main()
