"""Il turno NPC usa il motore di combattimento completo (combat.resolve_attack).

Prima usava una logica inline semplificata: niente moltiplicatore di ferita,
Major Wound/Knockdown/Tiro morte senza veri check HT, difesa del bersaglio
finta. Ora gli NPC passano dallo stesso motore del giocatore.
"""
import random
import unittest

from App.models import Player, SceneEntity, SceneState
from App.engine import npc_combat_turn, empty_game_state


def _gs(player, enemy):
    gs = empty_game_state()
    gs.players = [player]
    gs.scene = SceneState(scene_text="x", entities=[enemy])
    return gs


def _player(**kw) -> Player:
    d = dict(id=1, name="Vance", role="inv", archetype="investigator",
             stats={"forza": 10, "agilita": 12, "intelligenza": 12, "empatia": 10},
             max_hp=12, hp=12, max_fp=10, fp=10, will=10, per=10,
             basic_speed=5.0, dodge=9, move=5)
    return Player(**{**d, **kw})


def _enemy(**kw) -> SceneEntity:
    d = dict(id="rats", name="Branco di Ratti", type="enemy", hp=8, max_hp=8,
             dr=0, attack_skill=12, damage_dice="1d6", damage_type="cr")
    return SceneEntity(**{**d, **kw})


class TestNpcFullEngine(unittest.TestCase):
    def test_display_roll_matches_outcome_and_level(self):
        random.seed(7)
        gs = _gs(_player(), _enemy())
        log = npc_combat_turn(gs)["npc_logs"][-1]
        r = log["result"]
        # il dado/livello MOSTRATI sono quelli usati per l'esito (no doppia tiratura)
        self.assertEqual(log["attack_roll"], r["attack_roll"])
        self.assertEqual(log["skill_level"], r["effective_level"])
        self.assertEqual(r["effective_level"], 12)  # attack_skill dell'entità

    def test_target_gets_active_defense(self):
        # Con dodge altissimo il bersaglio deve poter schivare → niente auto-hit.
        random.seed(1)
        any_defended = False
        for _ in range(40):
            p = _player(dodge=20)
            gs = _gs(p, _enemy())
            r = npc_combat_turn(gs)["npc_logs"][-1]["result"]
            if r["hit"] and r["defended"]:
                any_defended = True
                break
        self.assertTrue(any_defended, "il bersaglio non ottiene mai la difesa attiva")

    def test_impaling_wounding_multiplier(self):
        # Danno impalante = ×2 (regola GURPS applicata dal motore completo).
        random.seed(3)
        got_double = False
        for _ in range(60):
            p = _player(dr=0, max_hp=50, hp=50, dodge=0)  # niente difesa, niente morte
            enemy = _enemy(attack_skill=20, damage_dice="1d6", damage_type="imp")
            gs = _gs(p, enemy)
            r = npc_combat_turn(gs)["npc_logs"][-1]["result"]
            if r["hit"] and not r["defended"] and r["net_damage"] == r["raw_damage"] * 2:
                got_double = True
                break
        self.assertTrue(got_double, "il moltiplicatore di ferita impalante non è applicato")


if __name__ == "__main__":
    unittest.main()
