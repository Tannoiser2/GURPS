"""Ogni NPC compilato riceve una scheda GURPS di base (attributi + combat).

Prima la scheda esisteva solo a runtime per i boss (threat>=2): nei dati
dell'avventura (e nell'editor) gli NPC non avevano alcuna scheda.
"""
import unittest

from App.adventure_compiler import definition_from_compiler_json
from App.npc_sheet import baseline_npc_gurps, threat_from_role


class TestNpcGurpsSheet(unittest.TestCase):
    def test_every_actor_gets_a_sheet(self):
        raw = {
            "title": "Test",
            "actors": [
                {"id": "npc_a", "name": "Guardia", "role": "antagonista"},
                {"id": "npc_b", "name": "Vedova", "role": "witness"},
                {"id": "npc_c", "name": "Medico", "role": "ally"},
            ],
        }
        d = definition_from_compiler_json(raw, source_type="manual_json")
        self.assertEqual(len(d.actors), 3)
        for a in d.actors:
            self.assertTrue(a.gurps_fo >= 8, f"{a.name} senza FO")
            self.assertTrue(a.combat_hp > 0, f"{a.name} senza PF")
            self.assertTrue(a.combat_attack_skill > 0, f"{a.name} senza attacco")
            self.assertTrue(a.combat_active_defense > 0, f"{a.name} senza difesa")
            self.assertTrue(len(a.gurps_skills) >= 1, f"{a.name} senza skill")

    def test_threat_scales_sheet(self):
        # L'antagonista (threat 3) deve essere più forte del civile (threat ~1).
        boss = baseline_npc_gurps("antagonista", threat_from_role("antagonista"))
        civ = baseline_npc_gurps("neutral", threat_from_role("neutral"))
        self.assertGreater(boss["combat_attack_skill"], civ["combat_attack_skill"])
        self.assertGreaterEqual(boss["gurps_fo"], civ["gurps_fo"])

    def test_existing_sheet_preserved(self):
        # Se l'actor porta già una scheda (es. editata), non viene sovrascritta.
        raw = {"title": "T", "actors": [
            {"id": "npc_x", "name": "Custom", "role": "neutral",
             "gurps_fo": 16, "combat_attack_skill": 18}]}
        d = definition_from_compiler_json(raw, source_type="manual_json")
        a = d.actors[0]
        self.assertEqual(a.gurps_fo, 16)
        self.assertEqual(a.combat_attack_skill, 18)


class TestSeedWorldNpcsSheet(unittest.TestCase):
    def test_seeded_world_npcs_all_have_sheet(self):
        # Il pannello GM legge game_state.world_npcs (seed da main): ogni NPC
        # deve avere la scheda GURPS, non solo i boss.
        import App.main as main
        from App.engine import empty_game_state
        raw = {"title": "T", "actors": [
            {"id": "n1", "name": "Civile", "role": "neutral"},
            {"id": "n2", "name": "Bandito", "role": "antagonista"},
        ]}
        defn = definition_from_compiler_json(raw, source_type="manual_json")
        main.game_state = empty_game_state()
        main._seed_world_npcs_from_actors(defn)
        self.assertEqual(len(main.game_state.world_npcs), 2)
        for npc in main.game_state.world_npcs:
            self.assertTrue(npc.gurps_fo and npc.gurps_fo >= 8, f"{npc.name} senza FO")
            self.assertTrue(npc.combat_hp and npc.combat_hp > 0, f"{npc.name} senza PF")
            self.assertTrue(npc.combat_attack_skill, f"{npc.name} senza attacco")


if __name__ == "__main__":
    unittest.main()
