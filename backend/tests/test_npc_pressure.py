"""T2 — Unit tests for npc_state_machine.py

Coverage:
- Pressure threshold crossing (4 tests)
- Idempotency — same event does not re-fire (4 tests)
- Side-effect correctness: destroy_clue, eliminate_npc (2 tests)
"""

import unittest

from App.runtime_models import (
    AdventureDefinition,
    AdventureRuntimeState,
    ActorState,
    RuntimeClue,
)
from App.npc_state_machine import (
    increment_pressure,
    fire_pressure_events,
    _pressure_band,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _rt() -> AdventureRuntimeState:
    return AdventureRuntimeState(definition_id="test")


def _actor(**kwargs) -> ActorState:
    defaults = dict(id="villain", name="Il Villain", agenda_pressure=0)
    return ActorState(**{**defaults, **kwargs})


def _defn(actors=None, clues=None) -> AdventureDefinition:
    return AdventureDefinition(
        id="test", title="Test",
        actors=actors or [],
        clues=clues or [],
    )


# ─── Pressure band helper ─────────────────────────────────────────────────────

class TestPressureBand(unittest.TestCase):
    def test_low(self):
        self.assertEqual(_pressure_band(0), "low")
        self.assertEqual(_pressure_band(2), "low")

    def test_medium(self):
        self.assertEqual(_pressure_band(3), "medium")
        self.assertEqual(_pressure_band(5), "medium")

    def test_high(self):
        self.assertEqual(_pressure_band(6), "high")
        self.assertEqual(_pressure_band(8), "high")

    def test_extreme(self):
        self.assertEqual(_pressure_band(9), "extreme")
        self.assertEqual(_pressure_band(10), "extreme")


# ─── Threshold crossing ───────────────────────────────────────────────────────

class TestThresholdCrossing(unittest.TestCase):
    def _actor_with_events(self):
        return _actor(
            pressure_events=[
                {"at_pressure": 3, "action": "destroy_clue", "clue_id": "clue_1"},
                {"at_pressure": 6, "action": "destroy_clue", "clue_id": "clue_2"},
                {"at_pressure": 9, "action": "destroy_clue", "clue_id": "clue_3"},
            ]
        )

    def test_crossing_3_fires_event(self):
        actor = self._actor_with_events()
        rt = _rt()
        defn = _defn(actors=[actor])
        _, fired = increment_pressure("villain", 3, defn, rt)
        self.assertEqual(len(fired), 1)
        self.assertEqual(fired[0]["action"], "destroy_clue")
        self.assertIn("clue_1", rt.destroyed_clue_ids)

    def test_crossing_6_fires_event(self):
        actor = self._actor_with_events()
        rt = _rt()
        defn = _defn(actors=[actor])
        increment_pressure("villain", 3, defn, rt)  # → 3, fires clue_1
        _, fired = increment_pressure("villain", 3, defn, rt)  # → 6, fires clue_2
        clue_ids = [f["destroyed_clue_id"] for f in fired]
        self.assertIn("clue_2", clue_ids)
        self.assertNotIn("clue_1", clue_ids)  # already fired, idempotency guaranteed

    def test_crossing_9_fires_event(self):
        actor = self._actor_with_events()
        rt = _rt()
        defn = _defn(actors=[actor])
        increment_pressure("villain", 3, defn, rt)
        increment_pressure("villain", 3, defn, rt)
        _, fired = increment_pressure("villain", 3, defn, rt)  # → 9
        clue_ids = [f["destroyed_clue_id"] for f in fired]
        self.assertIn("clue_3", clue_ids)

    def test_large_jump_crosses_multiple_thresholds(self):
        """A single large delta crossing multiple thresholds fires all of them."""
        actor = _actor(
            pressure_events=[
                {"at_pressure": 3, "action": "destroy_clue", "clue_id": "c1"},
                {"at_pressure": 6, "action": "destroy_clue", "clue_id": "c2"},
            ]
        )
        rt = _rt()
        defn = _defn(actors=[actor])
        _, fired = increment_pressure("villain", 7, defn, rt)  # 0→7
        self.assertEqual(len(fired), 2)
        destroyed = {f["destroyed_clue_id"] for f in fired}
        self.assertEqual(destroyed, {"c1", "c2"})


# ─── Idempotency ─────────────────────────────────────────────────────────────

class TestIdempotency(unittest.TestCase):
    def _actor_single_event(self) -> ActorState:
        return _actor(
            pressure_events=[{"at_pressure": 3, "action": "destroy_clue", "clue_id": "clue_x"}]
        )

    def test_event_not_refired_on_next_increment(self):
        actor = self._actor_single_event()
        rt = _rt()
        defn = _defn(actors=[actor])
        _, fired_first = increment_pressure("villain", 3, defn, rt)
        self.assertEqual(len(fired_first), 1)
        _, fired_second = increment_pressure("villain", 1, defn, rt)  # 3→4, no new threshold
        self.assertEqual(len(fired_second), 0)

    def test_event_not_refired_when_pressure_drops_and_recrosses(self):
        """Simulate scenario where pressure is incremented past threshold again."""
        actor = self._actor_single_event()
        rt = _rt()
        defn = _defn(actors=[actor])
        increment_pressure("villain", 3, defn, rt)  # fires at 3
        # Manually reset pressure to 2 (simulating decrement, not in API but testing flag guard)
        rt.actor_runtime["villain"]["pressure"] = 2
        fired = fire_pressure_events("villain", 2, 4, defn, rt)
        # Threshold 3 was already triggered — must NOT fire again
        self.assertEqual(len(fired), 0)

    def test_different_actors_independent(self):
        """Events on actor A do not affect actor B and vice versa."""
        actor_a = _actor(id="a", name="A", pressure_events=[{"at_pressure": 3, "action": "destroy_clue", "clue_id": "ca"}])
        actor_b = _actor(id="b", name="B", pressure_events=[{"at_pressure": 3, "action": "destroy_clue", "clue_id": "cb"}])
        rt = _rt()
        defn = _defn(actors=[actor_a, actor_b])
        _, fired_a = increment_pressure("a", 3, defn, rt)
        _, fired_b = increment_pressure("b", 3, defn, rt)
        self.assertEqual(len(fired_a), 1)
        self.assertEqual(len(fired_b), 1)
        self.assertEqual(fired_a[0]["destroyed_clue_id"], "ca")
        self.assertEqual(fired_b[0]["destroyed_clue_id"], "cb")

    def test_no_events_defined_no_fire(self):
        actor = _actor(pressure_events=[])
        rt = _rt()
        defn = _defn(actors=[actor])
        _, fired = increment_pressure("villain", 10, defn, rt)
        self.assertEqual(fired, [])


# ─── Side-effect correctness ──────────────────────────────────────────────────

class TestSideEffects(unittest.TestCase):
    def test_destroy_clue_adds_to_destroyed_ids(self):
        actor = _actor(
            pressure_events=[{"at_pressure": 1, "action": "destroy_clue", "clue_id": "evidence_key"}]
        )
        rt = _rt()
        defn = _defn(actors=[actor])
        _, fired = increment_pressure("villain", 1, defn, rt)
        self.assertIn("evidence_key", rt.destroyed_clue_ids)
        self.assertEqual(fired[0]["action"], "destroy_clue")
        self.assertEqual(fired[0]["destroyed_clue_id"], "evidence_key")

    def test_eliminate_npc_sets_dead_status(self):
        villain = _actor(
            id="villain", name="Villain",
            pressure_events=[{
                "at_pressure": 5,
                "action": "eliminate_npc",
                "target_id": "witness_npc",
                "new_status": "dead",
            }]
        )
        rt = _rt()
        defn = _defn(actors=[villain])
        _, fired = increment_pressure("villain", 5, defn, rt)
        self.assertEqual(len(fired), 1)
        self.assertEqual(fired[0]["eliminated_npc_id"], "witness_npc")
        self.assertEqual(fired[0]["new_status"], "dead")
        # Runtime state reflects the change
        npc_entry = rt.actor_runtime.get("witness_npc", {})
        self.assertEqual(npc_entry.get("status"), "dead")


if __name__ == "__main__":
    unittest.main()
