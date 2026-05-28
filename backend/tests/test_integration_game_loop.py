"""
T1: Integration tests for the full game loop (pure logic layer — no LLM calls).

Covers:
- simulate_world_state returns expected keys
- narrative_phase is "investigation" at turn 0 with no clues found
- tick_clocks advances clock progress on failure outcomes
- canonical_log passthrough via simulate_world_state
- director_prompt_context includes canonical log entries
- narrative_phase transitions to "extraction" when 70%+ required clues found
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from App.world_simulator import simulate_world_state
from App.clock_engine import tick_clocks
from App.narrative_director import director_prompt_context, make_director_decision
from App.runtime_models import (
    AdventureDefinition,
    AdventureRuntimeState,
    AdventureRuntime,
    ActorState,
    RuntimeClue,
    EventClock,
    Revelation,
    FinaleCondition,
    GenreProfile,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_runtime(clues=None, actors=None, event_clocks=None, revelations=None,
                  finale_conditions=None) -> AdventureRuntime:
    """Build a minimal AdventureRuntime for testing."""
    return AdventureRuntime(
        id="test_runtime",
        title="Test Adventure",
        genre="investigation",
        runtime_profile="investigation_graph",
        clues=clues or [],
        actors=actors or [],
        event_clocks=event_clocks or [],
        revelations=revelations or [],
        finale_conditions=finale_conditions or [],
        genre_profile=GenreProfile(
            id="investigation",
            tone="noir",
            allowed_escalations=["reveal_clue", "npc_pressure"],
            forbidden_escalations=["mass_casualty"],
            max_default_tier=4,
        ),
    )


def _make_definition(event_clocks=None) -> AdventureDefinition:
    """Build a minimal AdventureDefinition for tick_clocks tests."""
    return AdventureDefinition(
        id="test_def",
        genre="investigation",
        event_clocks=event_clocks or [],
    )


def _make_runtime_state(clock_runtime=None) -> AdventureRuntimeState:
    """Build a minimal AdventureRuntimeState for tick_clocks tests."""
    return AdventureRuntimeState(
        definition_id="test_def",
        clock_runtime=clock_runtime or {},
    )


def _base_clues():
    """Return 4 required clues all located in 'biblioteca'."""
    return [
        RuntimeClue(id="c1", label="Lettera anonima", source_location="biblioteca",
                    is_required=True, progress_ticks=1),
        RuntimeClue(id="c2", label="Registro prestiti", source_location="biblioteca",
                    is_required=True, progress_ticks=1),
        RuntimeClue(id="c3", label="Firma sospetta", source_location="biblioteca",
                    is_required=True, progress_ticks=1),
        RuntimeClue(id="c4", label="Mappa annotata", source_location="biblioteca",
                    is_required=True, progress_ticks=1),
    ]


def _base_actors():
    """Return 2 NPCs: a witness (available) and a villain."""
    return [
        ActorState(id="npc_1", name="Sofia Moretti", role="witness",
                   status="active", agenda_pressure=2),
        ActorState(id="npc_2", name="Marco Ferrini", role="antagonist",
                   status="unintroduced", agenda_pressure=3),
    ]


def _base_clock():
    """Return a single terminal_defeat clock with max_value=4."""
    return EventClock(
        id="clock_1",
        label="Distruzione prove",
        max_value=4,
        clock_type="terminal_defeat",
        active=True,
        consequence="Le prove vengono distrutte e il caso è irrecuperabile.",
        ticks_per_failure=1,
        ticks_per_success=0,
    )


def _base_revelation():
    """Return a story thread requiring c1+c2+c3 with minimum_clues_to_deduce=2."""
    return Revelation(
        id="rev_1",
        thread_id="thread_main",
        statement="Marco Ferrini ha falsificato i registri per nascondere il furto.",
        required_clues=["c1", "c2", "c3"],
        status="seeded",
    )


def _base_game_state(clues_found=None, canonical_log=None, turn=0,
                     clock_value=0) -> dict:
    """Build a minimal game_state_data dict."""
    return {
        "clues_found": clues_found or [],
        "canonical_log": canonical_log or [],
        "turn": turn,
        "threat_level": 0,
        "clue_progress": {},
        "npc_runtime": {},
        "clock_runtime": {"clock_1": {"value": clock_value}},
    }


def _base_runtime_and_state():
    """Return (runtime, game_state_data) built from all base fixtures."""
    runtime = _make_runtime(
        clues=_base_clues(),
        actors=_base_actors(),
        event_clocks=[_base_clock()],
        revelations=[_base_revelation()],
        finale_conditions=[],
    )
    game_state_data = _base_game_state()
    return runtime, game_state_data


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSimulateWorldStateKeys(unittest.TestCase):
    """T1.1 — simulate_world_state returns all expected top-level keys."""

    def test_result_has_required_keys(self):
        runtime, game_state_data = _base_runtime_and_state()

        result = simulate_world_state(
            runtime,
            player_action="esamina la biblioteca",
            prerolled={"success": True, "margin": 2, "critical": False, "outcome": "successo"},
            game_state_data=game_state_data,
        )

        for key in ("narrative_phase", "fail_tier", "canonical_log",
                    "current_turn", "next_best_actions", "witness_updates"):
            with self.subTest(key=key):
                self.assertIn(key, result, f"Missing key: {key}")


class TestPhaseInvestigationAtStart(unittest.TestCase):
    """T1.2 — narrative_phase is 'investigation' when no clues are found."""

    def test_phase_is_investigation_at_turn_zero(self):
        runtime, game_state_data = _base_runtime_and_state()
        # Ensure no clues found
        game_state_data["clues_found"] = []

        result = simulate_world_state(
            runtime,
            player_action="osserva l'ambiente",
            prerolled={"success": True, "margin": 1, "critical": False},
            game_state_data=game_state_data,
        )

        self.assertEqual(result["narrative_phase"], "investigation")

    def test_current_turn_matches_game_state(self):
        runtime, game_state_data = _base_runtime_and_state()
        game_state_data["turn"] = 0

        result = simulate_world_state(
            runtime,
            player_action="cerco indizi",
            prerolled={"success": True},
            game_state_data=game_state_data,
        )

        self.assertEqual(result["current_turn"], 0)


class TestClockTicking(unittest.TestCase):
    """T1.3 — tick_clocks advances clock progress on failure outcomes."""

    def test_failure_outcome_advances_clock(self):
        clock = _base_clock()
        definition = _make_definition(event_clocks=[clock])
        runtime_state = _make_runtime_state(
            clock_runtime={"clock_1": {"value": 0, "active": True}}
        )

        clock_events, updates = tick_clocks(
            outcome="fallimento",
            definition=definition,
            runtime_state=runtime_state,
        )

        # At least one clock event should have been produced
        self.assertTrue(len(clock_events) > 0, "Expected at least one clock event on failure")
        new_value = runtime_state.clock_runtime.get("clock_1", {}).get("value", 0)
        self.assertGreater(new_value, 0, "Clock value should have advanced from 0")

    def test_success_outcome_does_not_advance_clock(self):
        """ticks_per_success=0 → success does not move the clock."""
        clock = _base_clock()  # ticks_per_success=0
        definition = _make_definition(event_clocks=[clock])
        runtime_state = _make_runtime_state(
            clock_runtime={"clock_1": {"value": 0, "active": True}}
        )

        clock_events, updates = tick_clocks(
            outcome="successo",
            definition=definition,
            runtime_state=runtime_state,
        )

        new_value = runtime_state.clock_runtime.get("clock_1", {}).get("value", 0)
        self.assertEqual(new_value, 0, "Success should not advance the clock (ticks_per_success=0)")
        self.assertEqual(len(clock_events), 0, "No events expected on success with ticks_per_success=0")

    def test_failure_clock_value_equals_ticks_per_failure(self):
        """After one failure tick, value should equal ticks_per_failure (1)."""
        clock = EventClock(
            id="clock_1", label="Test", max_value=10,
            clock_type="terminal_defeat", active=True,
            ticks_per_failure=1, ticks_per_success=0,
        )
        definition = _make_definition(event_clocks=[clock])
        runtime_state = _make_runtime_state(
            clock_runtime={"clock_1": {"value": 0, "active": True}}
        )

        tick_clocks(outcome="fallimento", definition=definition, runtime_state=runtime_state)

        new_value = runtime_state.clock_runtime["clock_1"]["value"]
        self.assertEqual(new_value, 1)


class TestCanonicalLogPassthrough(unittest.TestCase):
    """T1.4 — canonical_log entries are passed through unchanged."""

    def test_canonical_log_preserved_in_result(self):
        runtime, game_state_data = _base_runtime_and_state()
        pre_existing_log = [
            {"turn": 1, "type": "clue_revealed", "clue_id": "c1",
             "summary": "trovata lettera anonima"},
            {"turn": 2, "type": "clue_partial", "clue_id": "c2",
             "summary": "iniziato esame registro"},
        ]
        game_state_data["canonical_log"] = pre_existing_log

        result = simulate_world_state(
            runtime,
            player_action="cerco indizi",
            prerolled={"success": True},
            game_state_data=game_state_data,
        )

        returned_log = result["canonical_log"]
        self.assertEqual(len(returned_log), len(pre_existing_log),
                         "canonical_log should have the same number of entries")
        for original_entry in pre_existing_log:
            self.assertIn(original_entry, returned_log,
                          f"Entry missing from returned log: {original_entry}")

    def test_empty_canonical_log_returns_empty_list(self):
        runtime, game_state_data = _base_runtime_and_state()
        game_state_data["canonical_log"] = []

        result = simulate_world_state(
            runtime,
            player_action="cerco indizi",
            prerolled={"success": True},
            game_state_data=game_state_data,
        )

        self.assertIsInstance(result["canonical_log"], list)
        self.assertEqual(len(result["canonical_log"]), 0)


class TestDirectorPromptContextCanonicalLog(unittest.TestCase):
    """T1.5 — director_prompt_context includes content from canonical_log."""

    def test_prompt_contains_log_clue_id(self):
        fake_log = [
            {"turn": 1, "type": "clue_revealed", "clue_id": "c1",
             "summary": "trovata lettera"},
            {"turn": 2, "type": "clue_revealed", "clue_id": "c2",
             "summary": "trovato registro"},
            {"turn": 3, "type": "clue_revealed", "clue_id": "c3",
             "summary": "trovata firma sospetta"},
        ]

        # Build a minimal decision dict (no LLM needed)
        decision = {
            "scene_directive": "Muovi la scena",
            "director_notes": [],
            "state_updates_required": {},
            "allowed_escalation_tier": 3,
            "allowed_escalation_types": [],
            "forbidden_escalation_types": [],
            "selected_clue_id": None,
            "npcs_to_introduce": [],
            "clock_tick": 0,
            "clock_triggers": [],
            "ready_threads": [],
            "narrative_phase": "investigation",
            "fail_tier": "none",
            "urgency_warnings": [],
            "next_best_actions": [],
            "witness_updates": [],
            "red_herring_candidate": None,
            "revelation_pacing": {"score": 0.0, "label": "slow",
                                  "recent_revelations": 0, "this_turn_revelations": 0},
            "revelation_timing": "now",
            "finale_near": False,
            "reason": "test",
        }

        prompt = director_prompt_context(decision=decision, canonical_log=fake_log)

        # The prompt should contain the canonical log section header
        self.assertIn("FATTI", prompt,
                      "director_prompt_context should emit a 'FATTI' section when canonical_log is provided")

        # At least one of our clue ids should appear in the prompt
        has_clue_reference = any(cid in prompt for cid in ("c1", "c2", "c3"))
        self.assertTrue(has_clue_reference,
                        "Prompt should reference at least one clue id from the canonical log")

    def test_prompt_contains_log_summary_text(self):
        """The summary text 'trovata lettera' should appear (or be reconstructed) in the prompt."""
        fake_log = [
            {"turn": 1, "type": "clue_revealed", "clue_id": "c1",
             "summary": "trovata lettera"},
        ]
        decision = {
            "scene_directive": "Test",
            "director_notes": [],
            "state_updates_required": {},
            "allowed_escalation_tier": 3,
            "allowed_escalation_types": [],
            "forbidden_escalation_types": [],
            "narrative_phase": "investigation",
            "fail_tier": "none",
            "urgency_warnings": [],
            "next_best_actions": [],
            "witness_updates": [],
            "red_herring_candidate": None,
            "revelation_timing": "now",
            "finale_near": False,
            "reason": "test",
        }

        prompt = director_prompt_context(decision=decision, canonical_log=fake_log)

        # The FATTI section should mention [c1] clue id (log entry for type=clue_revealed uses clue_id)
        self.assertIn("c1", prompt)

    def test_empty_canonical_log_no_fatti_section(self):
        """When canonical_log is empty, the 'FATTI GIÀ STABILITI' section is absent."""
        decision = {
            "scene_directive": "Test",
            "director_notes": [],
            "state_updates_required": {},
            "allowed_escalation_tier": 3,
            "allowed_escalation_types": [],
            "forbidden_escalation_types": [],
            "narrative_phase": "investigation",
            "fail_tier": "none",
            "urgency_warnings": [],
            "next_best_actions": [],
            "witness_updates": [],
            "red_herring_candidate": None,
            "revelation_timing": "now",
            "finale_near": False,
            "reason": "test",
        }

        prompt = director_prompt_context(decision=decision, canonical_log=[])
        self.assertNotIn("FATTI GIÀ STABILITI", prompt)


class TestPhaseTransitionToExtraction(unittest.TestCase):
    """T1.6 — narrative_phase transitions to 'extraction' when 70%+ required clues found."""

    def test_75_pct_clues_found_gives_extraction(self):
        """3 of 4 required clues found = 75% → extraction."""
        runtime, game_state_data = _base_runtime_and_state()
        game_state_data["clues_found"] = ["c1", "c2", "c3"]  # 3/4 = 75%

        result = simulate_world_state(
            runtime,
            player_action="cerco indizi",
            prerolled={"success": True},
            game_state_data=game_state_data,
        )

        self.assertEqual(result["narrative_phase"], "extraction",
                         f"Expected 'extraction' with 3/4 clues found, got {result['narrative_phase']!r}")

    def test_100_pct_clues_found_gives_extraction(self):
        """All 4 required clues found = 100% → extraction."""
        runtime, game_state_data = _base_runtime_and_state()
        game_state_data["clues_found"] = ["c1", "c2", "c3", "c4"]  # 4/4 = 100%

        result = simulate_world_state(
            runtime,
            player_action="cerco indizi",
            prerolled={"success": True},
            game_state_data=game_state_data,
        )

        self.assertIn(result["narrative_phase"], ("extraction", "delivery"),
                      f"Expected 'extraction' or 'delivery' with all clues found, "
                      f"got {result['narrative_phase']!r}")

    def test_0_clues_found_stays_investigation(self):
        """0 of 4 required clues found = 0% → investigation (far below 70% threshold)."""
        runtime, game_state_data = _base_runtime_and_state()
        game_state_data["clues_found"] = []  # 0/4 = 0%

        result = simulate_world_state(
            runtime,
            player_action="cerco indizi",
            prerolled={"success": True},
            game_state_data=game_state_data,
        )

        self.assertEqual(result["narrative_phase"], "investigation",
                         f"Expected 'investigation' with 0/4 clues found, "
                         f"got {result['narrative_phase']!r}")


class TestNextBestActions(unittest.TestCase):
    """T1.7 — next_best_actions is a non-empty list during investigation phase."""

    def test_investigation_phase_has_actions(self):
        runtime, game_state_data = _base_runtime_and_state()

        result = simulate_world_state(
            runtime,
            player_action="cerco indizi",
            prerolled={"success": True},
            game_state_data=game_state_data,
        )

        self.assertIsInstance(result["next_best_actions"], list)
        self.assertGreater(len(result["next_best_actions"]), 0,
                           "next_best_actions should not be empty in investigation phase")

    def test_extraction_phase_actions_include_protection(self):
        """In extraction phase, next_best_actions should include protection-related actions."""
        runtime, game_state_data = _base_runtime_and_state()
        game_state_data["clues_found"] = ["c1", "c2", "c3"]  # triggers extraction

        result = simulate_world_state(
            runtime,
            player_action="cerco indizi",
            prerolled={"success": True},
            game_state_data=game_state_data,
        )

        if result["narrative_phase"] == "extraction":
            actions_text = " ".join(result["next_best_actions"])
            has_protection = any(
                word in actions_text
                for word in ("proteggere", "raggiungere", "luogo", "contattare", "consegnare")
            )
            self.assertTrue(has_protection,
                            f"Expected extraction-phase actions, got: {result['next_best_actions']}")


if __name__ == "__main__":
    unittest.main()
