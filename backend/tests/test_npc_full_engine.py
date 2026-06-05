"""Il turno NPC usa il motore di combattimento completo (combat.resolve_attack).

Prima usava una logica inline semplificata: niente moltiplicatore di ferita,
Major Wound/Knockdown/Tiro morte senza veri check HT, difesa del bersaglio
finta. Ora gli NPC passano dallo stesso motore del giocatore.
"""
import random
import unittest

from App.models import Player, SceneEntity, SceneState
from App.engine import npc_combat_turn, empty_game_state, _choose_npc_maneuver
from App.combat import _defense_value


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


class TestNpcManeuverAI(unittest.TestCase):
    def test_moved_implies_move_attack(self):
        m = _choose_npc_maneuver(_enemy(), _player(), moved=True,
                                 attack_range=1, outnumber=0)
        self.assertEqual(m, "move_attack")

    def test_fanatic_goes_all_out_attack_in_melee(self):
        m = _choose_npc_maneuver(_enemy(morale="fanatico"), _player(), moved=False,
                                 attack_range=1, outnumber=0)
        self.assertEqual(m, "all_out_attack")

    def test_ranged_never_all_out_attack(self):
        # A distanza il +4 piatto non si applica → mai Attacco Totale.
        for _ in range(20):
            m = _choose_npc_maneuver(_enemy(morale="fanatico"), _player(), moved=False,
                                     attack_range=6, outnumber=5)
            self.assertNotEqual(m, "all_out_attack")

    def test_all_out_attack_flag_strips_npc_defense(self):
        # Fanatico in mischia → Attacco Totale → l'entità resta senza difesa.
        gs = _gs(_player(), _enemy(morale="fanatico"))
        log = npc_combat_turn(gs)["npc_logs"][-1]
        self.assertEqual(log["maneuver"], "all_out_attack")
        enemy = gs.scene.entities[0]
        self.assertTrue(enemy.no_active_defense)
        # Il giocatore che ora lo attacca non incontra difesa attiva.
        self.assertEqual(_defense_value(None, enemy, None), 0)

    def test_defense_bonus_applied(self):
        e = _enemy(active_defense=8, defense_bonus=2)
        self.assertEqual(_defense_value(None, e, None), 10)


if __name__ == "__main__":
    unittest.main()
