"""Unit tests for world_simulator private functions.

Tests cover:
- _fail_tier: graduated failure classification
- _compute_narrative_phase: narrative phase determination
- _witness_state_check: witness NPC state transitions
- _clock_urgency_warnings: urgency warning generation
"""
import unittest

from App.world_simulator import (
    _fail_tier,
    _compute_narrative_phase,
    _witness_state_check,
    _clock_urgency_warnings,
)
from App.runtime_models import (
    AdventureRuntime,
    EventClock,
    RuntimeClue,
    FinaleCondition,
    Revelation,
    ActorState,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _runtime(**kwargs) -> AdventureRuntime:
    return AdventureRuntime(**kwargs)


def _terminal_clock(
    id: str = "c",
    label: str = "Danger",
    max_value: int = 10,
    active: bool = True,
    consequence: str = "disaster",
    clock_type: str = "terminal_defeat",
) -> EventClock:
    return EventClock(
        id=id,
        label=label,
        max_value=max_value,
        clock_type=clock_type,
        active=active,
        consequence=consequence,
    )


def _clock_state(clock_id: str, value: int) -> dict:
    """Build a game_state_data dict with a clock_runtime entry."""
    return {"clock_runtime": {clock_id: {"value": value}}, "clues_found": []}


def _game_state(threat_level: int = 0, clues_found: list | None = None, **kwargs) -> dict:
    return {"threat_level": threat_level, "clues_found": clues_found or [], **kwargs}


# ---------------------------------------------------------------------------
# TestFailTier
# ---------------------------------------------------------------------------

class TestFailTier(unittest.TestCase):
    """Tests for _fail_tier(prerolled, game_state_data, runtime)."""

    def _rt_with_clock(self, max_value: int = 10) -> AdventureRuntime:
        clock = EventClock(id="c", label="Pressure", max_value=max_value, clock_type="narrative")
        return _runtime(event_clocks=[clock])

    # -- success always returns "none" --

    def test_success_returns_none(self):
        rt = _runtime()
        prerolled = {"success": True, "margin": 5, "critical": False}
        result = _fail_tier(prerolled, _game_state(threat_level=0), rt)
        self.assertEqual(result, "none")

    # -- soft failure --

    def test_failure_margin_minus1_low_threat_returns_soft(self):
        """margin -1, threat 20% of max → soft (below 60% and margin > -3)."""
        rt = self._rt_with_clock(max_value=10)
        prerolled = {"success": False, "margin": -1, "critical": False}
        # threat_level=2 / max_value=10 → 20%
        result = _fail_tier(prerolled, _game_state(threat_level=2), rt)
        self.assertEqual(result, "soft")

    # -- pressure failure: high threat --

    def test_failure_high_threat_returns_pressure(self):
        """threat >= 60% → pressure regardless of margin."""
        rt = self._rt_with_clock(max_value=10)
        prerolled = {"success": False, "margin": -1, "critical": False}
        # threat_level=6 / max_value=10 → 60%
        result = _fail_tier(prerolled, _game_state(threat_level=6), rt)
        self.assertEqual(result, "pressure")

    def test_failure_margin_minus4_high_threat_returns_pressure(self):
        """margin -4, threat 65% → pressure (margin -4 is between -3 and -5)."""
        rt = self._rt_with_clock(max_value=10)
        prerolled = {"success": False, "margin": -4, "critical": False}
        # threat_level=7 / max_value=10 → 70%
        result = _fail_tier(prerolled, _game_state(threat_level=7), rt)
        self.assertEqual(result, "pressure")

    # -- hard failure: critical --

    def test_critical_failure_returns_hard(self):
        """critical=True always returns hard."""
        rt = self._rt_with_clock(max_value=10)
        prerolled = {"success": False, "margin": -1, "critical": True}
        result = _fail_tier(prerolled, _game_state(threat_level=0), rt)
        self.assertEqual(result, "hard")

    # -- hard failure: margin <= -5 --

    def test_failure_margin_minus5_returns_hard(self):
        """margin <= -5 returns hard."""
        rt = self._rt_with_clock(max_value=10)
        prerolled = {"success": False, "margin": -5, "critical": False}
        result = _fail_tier(prerolled, _game_state(threat_level=0), rt)
        self.assertEqual(result, "hard")

    # -- pressure: margin <= -3 threshold --

    def test_failure_margin_minus3_low_threat_returns_pressure(self):
        """margin -3 alone (low threat) is enough to reach pressure tier."""
        rt = self._rt_with_clock(max_value=10)
        prerolled = {"success": False, "margin": -3, "critical": False}
        # threat_level=1 / max_value=10 → 10%  (well below 60%)
        result = _fail_tier(prerolled, _game_state(threat_level=1), rt)
        self.assertEqual(result, "pressure")


# ---------------------------------------------------------------------------
# TestComputeNarrativePhase
# ---------------------------------------------------------------------------

class TestComputeNarrativePhase(unittest.TestCase):
    """Tests for _compute_narrative_phase(runtime, game_state_data)."""

    def test_empty_runtime_returns_investigation(self):
        """No clues, no clocks, no conditions → default investigation."""
        rt = _runtime()
        result = _compute_narrative_phase(rt, _game_state())
        self.assertEqual(result, "investigation")

    def test_70_pct_required_clues_found_returns_extraction(self):
        """70% of required clues found → extraction."""
        clues = [
            RuntimeClue(id=f"c{i}", label=f"Clue {i}", is_required=True)
            for i in range(10)
        ]
        rt = _runtime(clues=clues)
        found = [f"c{i}" for i in range(7)]  # 7/10 = 70%
        result = _compute_narrative_phase(rt, _game_state(clues_found=found))
        self.assertEqual(result, "extraction")

    def test_69_pct_required_clues_stays_investigation(self):
        """69% of required clues found → investigation (below threshold)."""
        clues = [
            RuntimeClue(id=f"c{i}", label=f"Clue {i}", is_required=True)
            for i in range(100)
        ]
        rt = _runtime(clues=clues)
        found = [f"c{i}" for i in range(69)]  # 69/100 = 69%
        result = _compute_narrative_phase(rt, _game_state(clues_found=found))
        self.assertEqual(result, "investigation")

    def test_finale_condition_satisfied_returns_delivery(self):
        """A satisfied finale condition → delivery."""
        fc = FinaleCondition(id="f1", label="Goal", status="satisfied")
        rt = _runtime(finale_conditions=[fc])
        result = _compute_narrative_phase(rt, _game_state())
        self.assertEqual(result, "delivery")

    def test_terminal_defeat_clock_at_80pct_returns_escape(self):
        """terminal_defeat clock at 80% → escape mode."""
        clock = _terminal_clock(id="doom", max_value=10)
        rt = _runtime(event_clocks=[clock])
        # value=8 → 8/10 = 80%
        gsd = _clock_state("doom", 8)
        result = _compute_narrative_phase(rt, gsd)
        self.assertEqual(result, "escape")

    def test_terminal_defeat_clock_at_79pct_stays_investigation(self):
        """terminal_defeat clock at 79% → not yet escape (stays investigation)."""
        clock = _terminal_clock(id="doom", max_value=100)
        rt = _runtime(event_clocks=[clock])
        # value=79 → 79/100 = 79%
        gsd = {"clock_runtime": {"doom": {"value": 79}}, "clues_found": []}
        result = _compute_narrative_phase(rt, gsd)
        self.assertEqual(result, "investigation")

    def test_payload_object_clue_50pct_found_returns_extraction(self):
        """payload_object clues with >=50% found → extraction."""
        clues = [
            RuntimeClue(id="p1", label="Payload A", type="payload_object", is_required=False),
            RuntimeClue(id="p2", label="Payload B", type="payload_object", is_required=False),
        ]
        rt = _runtime(clues=clues)
        # 1/2 = 50% → max(1, 2//2) = 1, found_payload=1 >= 1
        result = _compute_narrative_phase(rt, _game_state(clues_found=["p1"]))
        self.assertEqual(result, "extraction")


# ---------------------------------------------------------------------------
# TestWitnessStateCheck
# ---------------------------------------------------------------------------

class TestWitnessStateCheck(unittest.TestCase):
    """Tests for _witness_state_check(runtime, game_state_data)."""

    def _actor(
        self,
        id: str = "w1",
        name: str = "Witness",
        role: str = "witness",
        status: str = "active",
    ) -> ActorState:
        return ActorState(id=id, name=name, role=role, status=status)

    def _rt_with_clock(self, max_value: int = 10) -> AdventureRuntime:
        clock = EventClock(id="c", label="Pressure", max_value=max_value, clock_type="narrative")
        return _runtime(event_clocks=[clock])

    # -- transitions --

    def test_witness_threat_70pct_transitions_to_fearful(self):
        """Witness with threat at 70% (>=65%) transitions from available to fearful."""
        actor = self._actor(status="active")
        rt = _runtime(
            actors=[actor],
            event_clocks=[EventClock(id="c", label="Pressure", max_value=10, clock_type="narrative")],
        )
        # threat_level=7 / max_value=10 → 70%
        gsd = _game_state(threat_level=7, npc_runtime={})
        updates = _witness_state_check(rt, gsd)
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["npc_id"], "w1")
        self.assertEqual(updates[0]["previous_witness_state"], "available")
        self.assertEqual(updates[0]["witness_state"], "fearful")

    def test_witness_threat_87pct_transitions_to_panicked(self):
        """Witness with threat at 87% (>=85%) transitions from available to panicked."""
        actor = self._actor(status="active")
        rt = _runtime(
            actors=[actor],
            event_clocks=[EventClock(id="c", label="Pressure", max_value=100, clock_type="narrative")],
        )
        # threat_level=87 / max_value=100 → 87%
        gsd = _game_state(threat_level=87, npc_runtime={})
        updates = _witness_state_check(rt, gsd)
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["witness_state"], "panicked")

    def test_witness_already_panicked_stays_panicked(self):
        """Witness already in panicked state at threat 90% → no duplicate update."""
        actor = self._actor(status="active")
        rt = _runtime(
            actors=[actor],
            event_clocks=[EventClock(id="c", label="Pressure", max_value=10, clock_type="narrative")],
        )
        # Override runtime state: witness_state already panicked
        npc_rt = {"w1": {"status": "active", "witness_state": "panicked"}}
        gsd = _game_state(threat_level=9, npc_runtime=npc_rt)
        updates = _witness_state_check(rt, gsd)
        self.assertEqual(len(updates), 0)

    def test_non_witness_actor_no_updates(self):
        """Non-witness actor (role=antagonist) produces no updates."""
        actor = self._actor(role="antagonist", status="active")
        rt = _runtime(
            actors=[actor],
            event_clocks=[EventClock(id="c", label="Pressure", max_value=10, clock_type="narrative")],
        )
        gsd = _game_state(threat_level=9, npc_runtime={})
        updates = _witness_state_check(rt, gsd)
        self.assertEqual(len(updates), 0)

    def test_witness_in_terminal_state_no_update(self):
        """Witness in terminal state (dead) → no update."""
        actor = self._actor(status="dead")
        rt = _runtime(
            actors=[actor],
            event_clocks=[EventClock(id="c", label="Pressure", max_value=10, clock_type="narrative")],
        )
        gsd = _game_state(threat_level=9, npc_runtime={})
        updates = _witness_state_check(rt, gsd)
        self.assertEqual(len(updates), 0)

    def test_threat_below_65pct_no_update(self):
        """Threat below 65% → witness stays available, no update."""
        actor = self._actor(status="active")
        rt = _runtime(
            actors=[actor],
            event_clocks=[EventClock(id="c", label="Pressure", max_value=10, clock_type="narrative")],
        )
        # threat_level=6 / max_value=10 → 60% (below 65%)
        gsd = _game_state(threat_level=6, npc_runtime={})
        updates = _witness_state_check(rt, gsd)
        self.assertEqual(len(updates), 0)


# ---------------------------------------------------------------------------
# TestClockUrgencyWarnings
# ---------------------------------------------------------------------------

class TestClockUrgencyWarnings(unittest.TestCase):
    """Tests for _clock_urgency_warnings(runtime, game_state_data)."""

    def _setup(self, value: int, max_value: int = 100, active: bool = True,
               clock_type: str = "terminal_defeat") -> tuple[AdventureRuntime, dict]:
        clock = EventClock(
            id="c",
            label="Danger",
            max_value=max_value,
            clock_type=clock_type,
            active=active,
            consequence="disaster",
        )
        rt = _runtime(event_clocks=[clock])
        gsd = {"clock_runtime": {"c": {"value": value}}, "clues_found": []}
        return rt, gsd

    def test_92pct_clock_returns_critica(self):
        """terminal_defeat clock at 92% → CRITICA urgency."""
        rt, gsd = self._setup(value=92, max_value=100)
        warnings = _clock_urgency_warnings(rt, gsd)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]["urgency"], "CRITICA")

    def test_75pct_clock_returns_alta(self):
        """terminal_defeat clock at 75% → ALTA urgency."""
        rt, gsd = self._setup(value=75, max_value=100)
        warnings = _clock_urgency_warnings(rt, gsd)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]["urgency"], "ALTA")

    def test_55pct_clock_returns_media(self):
        """terminal_defeat clock at 55% → MEDIA urgency."""
        rt, gsd = self._setup(value=55, max_value=100)
        warnings = _clock_urgency_warnings(rt, gsd)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]["urgency"], "MEDIA")

    def test_49pct_clock_returns_no_warning(self):
        """terminal_defeat clock at 49% → below threshold, no warning."""
        rt, gsd = self._setup(value=49, max_value=100)
        warnings = _clock_urgency_warnings(rt, gsd)
        self.assertEqual(len(warnings), 0)

    def test_non_terminal_clock_no_warning(self):
        """Non-terminal clock (narrative type) at 95% → no warning."""
        rt, gsd = self._setup(value=95, max_value=100, clock_type="narrative")
        warnings = _clock_urgency_warnings(rt, gsd)
        self.assertEqual(len(warnings), 0)

    def test_inactive_clock_no_warning(self):
        """Inactive terminal_defeat clock → no warning."""
        rt, gsd = self._setup(value=95, max_value=100, active=False)
        warnings = _clock_urgency_warnings(rt, gsd)
        self.assertEqual(len(warnings), 0)


if __name__ == "__main__":
    unittest.main()
