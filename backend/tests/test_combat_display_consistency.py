"""Combattimento: il dado MOSTRATO deve essere quello che decide l'esito, e il
livello mostrato deve includere TUTTI i modificatori (All-Out Attack, ecc.).

Regressione del bug 'pistola 5 ≤ 5 ✗ Mancato': prima resolve_attack tirava un
secondo 3d6 interno (diverso da quello mostrato) e l'engine ricalcolava il
livello DOPO aver azzerato l'action_type, perdendo il +4. Inoltre la skill
'pistola' non veniva normalizzata → livello di default assurdamente basso.
"""
import unittest

from App.models import Player, SceneEntity
from App.combat import resolve_attack


def _player(**kwargs) -> Player:
    defaults = dict(
        id=1, name="Vance", role="investigatore", archetype="investigator",
        stats={"forza": 10, "agilita": 12, "intelligenza": 12, "empatia": 10},
        max_hp=10, hp=10, max_fp=10, fp=10,
        will=10, per=10, basic_speed=5.0, dodge=8, move=5,
    )
    return Player(**{**defaults, **kwargs})


def _dummy() -> SceneEntity:
    return SceneEntity(id="rats", name="Branco di Ratti", type="enemy",
                       hp=20, max_hp=20, dr=0)


class TestCombatDisplayConsistency(unittest.TestCase):
    def test_prerolled_die_is_the_one_used(self):
        p = _player(skills={"mira": 12})
        res = resolve_attack(p, "pistola", "2d6", "pi", target_entity=_dummy(),
                             attack_kind="ranged", prerolled=10)
        # il dado restituito È quello passato (niente seconda tiratura nascosta)
        self.assertEqual(res.attack_roll, 10)
        self.assertEqual(res.effective_level, 12)  # skill 'mira' via alias 'pistola'
        self.assertTrue(res.hit)  # 10 <= 12

    def test_boundary_roll_equal_level_is_hit(self):
        p = _player(skills={"mira": 12})
        res = resolve_attack(p, "mira", "2d6", "pi", target_entity=_dummy(),
                             attack_kind="ranged", prerolled=12)
        self.assertTrue(res.hit)  # 12 <= 12 in GURPS è SUCCESSO

    def test_all_out_attack_bonus_in_effective_level(self):
        p = _player(skills={"mira": 12})
        p.action_type = "all_out_attack"
        res = resolve_attack(p, "pistola", "2d6", "pi", target_entity=_dummy(),
                             attack_kind="ranged", prerolled=15)
        self.assertEqual(res.effective_level, 16)  # 12 + 4
        self.assertTrue(res.hit)  # 15 <= 16

    def test_pistol_skill_normalized_not_absurdly_low(self):
        # Senza la skill 'mira', deve cadere sul default dello stat-cardine
        # (destrezza 12 − penalità), NON sul ramo rotto 'forza − 5'.
        p = _player(skills={})
        res = resolve_attack(p, "pistola", "2d6", "pi", target_entity=_dummy(),
                             attack_kind="ranged", prerolled=8)
        self.assertGreaterEqual(res.effective_level, 7)

    def test_miss_uses_shown_die(self):
        p = _player(skills={"mira": 10})
        res = resolve_attack(p, "pistola", "2d6", "pi", target_entity=_dummy(),
                             attack_kind="ranged", prerolled=14)
        self.assertFalse(res.hit)  # 14 > 10
        self.assertEqual(res.attack_roll, 14)
        self.assertEqual(res.effective_level, 10)


if __name__ == "__main__":
    unittest.main()
