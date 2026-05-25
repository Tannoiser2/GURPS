import unittest

from App.action_intent import select_best_skill, validate_skill_against_context
from App.engine import roll_for_player_action


class ActionSkillResolutionTests(unittest.TestCase):
    def assert_skill_in(self, action, expected, context=None, skills=None):
        result = select_best_skill(action, context or {}, skills or {})
        self.assertIn(
            result["selected_skill"],
            expected,
            f"{action!r} -> {result['selected_skill']} ({result})",
        )
        return result

    def assert_not_absurd(self, action, forbidden, context=None, skills=None):
        result = select_best_skill(action, context or {}, skills or {})
        self.assertNotIn(
            result["selected_skill"],
            forbidden,
            f"{action!r} picked absurd skill {result['selected_skill']} ({result})",
        )
        return result

    def test_cross_genre_skill_resolution_table(self):
        cases = [
            ("Examine crime scene", {"investigare", "analizzare", "osservare"}, {"genre": "noir investigation"}),
            ("Inspect the blood pattern on the wall", {"investigare", "analizzare", "osservare"}, {"genre": "horror"}),
            ("Examine the corpse in the alley", {"investigare", "analizzare", "medicina"}, {"genre": "noir"}),
            ("Search the victim's room", {"investigare", "osservare", "seguire_tracce"}, {"genre": "noir"}),
            ("Look for fingerprints around the safe", {"investigare", "osservare"}, {"genre": "detective"}),
            ("Analyze the ash residue", {"investigare", "analizzare", "scienze"}, {"genre": "supernatural investigation"}),
            ("Question the bartender while observing his reactions", {"interrogare", "intuire", "persuadere"}, {"genre": "noir"}),
            ("Talk to the witness calmly", {"persuadere", "comunicare", "interrogare"}, {"genre": "noir"}),
            ("Convince the guard to open the gate", {"persuadere", "comunicare", "etichetta"}, {"genre": "fantasy"}),
            ("Threaten the guard with consequences", {"intimidire", "interrogare"}, {"genre": "military"}),
            ("Lie about my identity at the checkpoint", {"ingannare", "recitazione", "seduzione"}, {"genre": "cyberpunk"}),
            ("Understand the child's emotional state", {"intuire", "calmare", "persuadere"}, {"genre": "horror"}),
            ("Calm the terrified child", {"calmare", "persuadere", "comunicare"}, {"genre": "horror"}),
            ("Negotiate a ceasefire with the militia", {"persuadere", "etichetta", "politica", "comunicare"}, {"genre": "military"}),
            ("Interrogate the prisoner about the convoy", {"interrogare", "intuire", "persuadere", "intimidire"}, {"genre": "military"}),
            ("Study the ancient tome", {"cultura", "decifrare", "storia", "linguistica", "occultismo", "teologia"}, {"genre": "fantasy"}),
            ("Read the cult diary", {"cultura", "decifrare", "storia", "linguistica", "occultismo", "teologia"}, {"genre": "horror"}),
            ("Translate the runes on the altar", {"cultura", "decifrare", "storia", "linguistica", "occultismo", "teologia"}, {"genre": "fantasy supernatural"}),
            ("Research the noble family archive", {"cultura", "decifrare", "storia", "linguistica", "occultismo", "teologia"}, {"genre": "fantasy investigation"}),
            ("Study the alien manuscript", {"cultura", "decifrare", "storia", "linguistica", "occultismo", "teologia"}, {"genre": "sci-fi"}),
            ("Repair the engine before takeoff", {"tecnologia", "meccanica", "elettronica", "informatica", "ingegneria", "scassinare"}, {"genre": "sci-fi"}),
            ("Hack the corporate terminal", {"tecnologia", "meccanica", "elettronica", "informatica", "ingegneria", "scassinare"}, {"genre": "cyberpunk"}),
            ("Inspect the damaged machine", {"tecnologia", "meccanica", "elettronica", "informatica", "ingegneria", "scassinare"}, {"genre": "sci-fi"}),
            ("Disable the security console", {"tecnologia", "meccanica", "elettronica", "informatica", "ingegneria", "scassinare"}, {"genre": "cyberpunk"}),
            ("Repair the generator in the bunker", {"tecnologia", "meccanica", "elettronica", "informatica", "ingegneria", "scassinare"}, {"genre": "survival"}),
            ("Treat the wound with bandages", {"medicina", "curare", "biologia", "chimica"}, {"genre": "military"}),
            ("Diagnose the poison in the cup", {"medicina", "curare", "biologia", "chimica"}, {"genre": "fantasy"}),
            ("Heal the wounded scout", {"medicina", "curare", "biologia", "chimica"}, {"genre": "fantasy"}),
            ("Analyze the poison sample", {"medicina", "curare", "biologia", "chimica"}, {"genre": "noir"}),
            ("Stabilize the injured pilot", {"medicina", "curare", "biologia", "chimica"}, {"genre": "sci-fi"}),
            ("Hide from the patrol", {"furtivita", "mimetizzare", "infiltrarsi"}, {"genre": "military"}),
            ("Sneak past the sleeping guards", {"furtivita", "mimetizzare", "infiltrarsi"}, {"genre": "fantasy"}),
            ("Follow the suspect secretly", {"pedinare", "furtivita", "seguire_tracce"}, {"genre": "noir"}),
            ("Infiltrate the corporate lab silently", {"furtivita", "mimetizzare", "infiltrarsi"}, {"genre": "cyberpunk"}),
            ("Tail the courier without being seen", {"pedinare", "furtivita", "seguire_tracce"}, {"genre": "noir"}),
            ("Shoot the cultist", {"mira", "lanciare"}, {"genre": "horror", "combat_active": True}),
            ("Fire the rifle at the drone", {"mira", "lanciare"}, {"genre": "sci-fi", "combat_active": True}),
            ("Attack the orc with my sword", {"combattere", "lottare"}, {"genre": "fantasy", "combat_active": True}),
            ("Stab the vampire with the stake", {"combattere", "lottare"}, {"genre": "horror", "combat_active": True}),
            ("Charge the barricade and tackle the soldier", {"combattere", "lottare"}, {"genre": "military", "combat_active": True}),
            ("Break the locked door", {"forzare", "demolire", "sollevare", "scassinare", "manualita"}, {"genre": "survival"}),
            ("Force open the rusted gate", {"forzare", "demolire", "sollevare", "scassinare", "manualita"}, {"genre": "fantasy"}),
            ("Smash the padlock with a hammer", {"forzare", "demolire", "sollevare", "scassinare", "manualita"}, {"genre": "military"}),
            ("Pick the lock quietly", {"forzare", "demolire", "sollevare", "scassinare", "manualita"}, {"genre": "noir"}),
            ("Lift the fallen beam", {"forzare", "demolire", "sollevare", "scassinare", "manualita"}, {"genre": "survival"}),
            ("Navigate through the blizzard", {"sopravvivere", "sopravvivenza_urbana", "navigare", "seguire_tracce"}, {"genre": "survival"}),
            ("Forage for food in the wasteland", {"sopravvivere", "sopravvivenza_urbana", "navigare", "seguire_tracce"}, {"genre": "survival"}),
            ("Track the wolf prints through snow", {"investigare", "osservare", "seguire_tracce", "sopravvivere"}, {"genre": "survival"}),
            ("Climb the broken tower", {"acrobazia", "rapidita", "arrampicarsi", "saltare", "nuotare"}, {"genre": "fantasy"}),
            ("Swim across the flooded tunnel", {"acrobazia", "rapidita", "arrampicarsi", "saltare", "nuotare"}, {"genre": "survival"}),
            ("Coordinate the squad under fire", {"comandare", "ispirare", "strategia"}, {"genre": "military", "combat_active": True}),
            ("Command the villagers to form a bucket line", {"comandare", "ispirare", "strategia"}, {"genre": "fantasy"}),
            ("Protect the witness from the blast", {"schivare", "proteggere", "resistere", "strategia"}, {"genre": "noir", "combat_active": True}),
            ("Approach the suspect", {"interrogare", "persuadere", "intuire"}, {"genre": "noir investigation", "target_type": "suspect"}),
            ("Approach the suspect", {"furtivita", "mimetizzare", "infiltrarsi", "pedinare", "seguire_tracce"}, {"genre": "stealth mission", "scene_type": "infiltration", "target_type": "suspect"}),
            ("Approach the suspect", {"osservare", "investigare", "intuire", "sopravvivere"}, {"genre": "horror", "target_type": "suspect"}),
        ]
        self.assertGreaterEqual(len(cases), 50)
        for action, expected, context in cases:
            with self.subTest(action=action, context=context):
                self.assert_skill_in(action, expected, context)

    def test_absurd_pairings_are_rejected(self):
        absurd_cases = [
            ("examine corpse", {"intimidire", "combattere", "mira", "furtivita"}),
            ("read diary", {"combattere", "mira", "furtivita"}),
            ("search library", {"furtivita", "combattere", "mira"}),
            ("calm child", {"combattere", "mira", "intimidire"}),
            ("inspect machine", {"seduzione", "intimidire", "combattere"}),
            ("talk to witness", {"furtivita", "combattere", "mira"}),
            ("study manuscript", {"combattere", "mira", "intimidire"}),
            ("search room", {"persuadere", "intimidire", "combattere"}),
        ]
        for action, forbidden in absurd_cases:
            with self.subTest(action=action):
                self.assert_not_absurd(action, forbidden, {"genre": "investigation"})

    def test_combat_requires_attack_or_active_context(self):
        passive = [
            "investigate the battlefield",
            "search the cultist's pocket",
            "inspect the rifle serial number",
            "ask the soldier what happened",
            "study the tactical map",
            "observe the monster tracks",
        ]
        for action in passive:
            with self.subTest(action=action):
                result = select_best_skill(action, {"genre": "military", "combat_active": False})
                self.assertNotIn(result["selected_skill"], {"combattere", "mira", "lottare", "lanciare"})

        attack = select_best_skill("shoot the guard", {"genre": "military", "combat_active": False})
        self.assertIn(attack["selected_skill"], {"mira", "lanciare"})

    def test_stealth_requires_avoidance_or_infiltration(self):
        normal_search = select_best_skill("search the office", {"genre": "noir"})
        self.assertNotIn(normal_search["selected_skill"], {"furtivita", "infiltrarsi", "mimetizzare", "pedinare"})

        covert = select_best_skill("search the office silently while avoiding patrols", {"genre": "stealth mission"})
        self.assertIn(covert["selected_skill"], {"furtivita", "mimetizzare", "infiltrarsi"})

    def test_validation_api_rejects_bad_context(self):
        intent_data = {
            "intent": "investigate",
            "target_type": "corpse",
            "interaction_mode": "exploratory",
        }
        self.assertFalse(validate_skill_against_context("intimidire", intent_data, {"action_text": "examine corpse"}))
        self.assertFalse(validate_skill_against_context("combattere", intent_data, {"action_text": "examine corpse"}))
        self.assertTrue(validate_skill_against_context("investigare", intent_data, {"action_text": "examine corpse"}))

    def test_roll_for_player_action_uses_semantic_resolver_not_best_skill(self):
        player = {
            "name": "Tester",
            "stats": {"forza": 14, "agilita": 12, "intelligenza": 11, "empatia": 10},
            "skills": {"combattere": 18, "intimidire": 17, "investigare": 9, "osservare": 10},
            "advantages": [],
            "disadvantages": [],
            "items": [],
            "status": "ok",
            "genre": "noir investigation",
        }
        result = roll_for_player_action(player, "examine the corpse for clues", 0, ["crime_scene"])
        self.assertNotIn(result["skill"], {"combattere", "mira", "intimidire"})
        self.assertIn(result["intent"], {"investigate", "medical", "observe"})
        self.assertIn("action_resolution", result)
        self.assertGreaterEqual(result["skill_confidence"], 0.45)

    def test_low_confidence_uses_safe_fallback(self):
        result = select_best_skill("do something careful", {"genre": "generic"})
        self.assertIn(result["selected_skill"], {"investigare", "osservare", "persuadere", "acrobazia", "sopravvivere", "cultura"})
        self.assertNotIn(result["selected_skill"], {"combattere", "mira", "intimidire", "furtivita"})


if __name__ == "__main__":
    unittest.main()
