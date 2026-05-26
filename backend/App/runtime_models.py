from pydantic import BaseModel
from typing import Any, Dict, List, Literal, Optional


SourceMode = Literal["ai_generated", "pdf_import", "pdf_import_fallback", "raw_text", "manual_json"]
SourceStatus = Literal["explicit", "inferred", "suggested", "generated"]


class SourceRef(BaseModel):
    page: Optional[int] = None
    section: str = ""
    paragraph: Optional[int] = None
    snippet_hash: str = ""
    quote: str = ""


class HiddenTruth(BaseModel):
    id: str
    statement: str = ""
    reveal_clues: List[str] = []
    reveal_rule: str = ""
    revealed: bool = False


class Objective(BaseModel):
    id: str
    label: str
    status: Literal["hidden", "inactive", "available", "active", "complete", "failed"] = "active"
    unlocks: List[str] = []
    success_conditions: List[str] = []


class LocationState(BaseModel):
    id: str
    name: str
    description: str = ""
    status: Literal["hidden", "unknown", "known", "visited", "locked", "changed", "compromised", "secured", "destroyed"] = "known"
    contains_clues: List[str] = []
    contains_actors: List[str] = []
    tactical_map: Dict = {}
    access_requirements: List[str] = []
    type: str = "location"
    access_state: Literal["open", "locked", "hidden", "blocked", "restricted", "unlocked", "sealed"] = "open"
    visual_identity: str = ""
    gameplay_function: str = ""
    concrete_features: List[str] = []
    hazards: List[str] = []
    exits: List[str] = []
    locked_paths: List[str] = []
    clue_slots: List[str] = []
    tactical_features: List[str] = []
    source_ref: Dict[str, Any] = {}
    source_status: SourceStatus = "generated"
    original_room_number: str = ""
    original_section: str = ""
    is_preserved_from_pdf: bool = False
    inferred_runtime_fields: List[str] = []
    confidence: float = 1.0


class ActorState(BaseModel):
    id: str
    name: str
    role: str = "neutral"
    location_id: str = ""
    status: Literal["unintroduced", "introduced", "active", "exposed", "allied", "hostile", "captured", "resolved", "dead", "missing"] = "unintroduced"
    goal: str = ""
    secret: str = ""
    agenda_pressure: int = 0
    fear: str = ""
    current_plan: str = ""
    fallback_plan: str = ""
    resources: List[str] = []
    knows: List[str] = []
    wants: List[str] = []
    avoids: List[str] = []
    pressure_response: Dict = {}
    reaction_table: Dict = {}
    relationships: List[Dict[str, Any]] = []
    source_ref: Dict[str, Any] = {}
    source_status: SourceStatus = "generated"
    is_preserved_from_pdf: bool = False
    inferred_agenda: bool = False
    confidence: float = 1.0
    llm_enriched: bool = False


class FactionState(BaseModel):
    id: str
    name: str
    agenda: str = ""
    pressure: int = 0
    status: Literal["quiet", "watching", "active", "escalating", "dominant", "weakened", "broken"] = "quiet"
    source_ref: Dict[str, Any] = {}
    source_status: SourceStatus = "generated"
    confidence: float = 1.0


class Revelation(BaseModel):
    id: str
    thread_id: str = ""
    statement: str
    required_clues: List[str] = []
    required_evidence_kinds: List[str] = []
    minimum_independent_kinds: int = 1
    red_herring_clues: List[str] = []
    status: Literal["hidden", "seeded", "available", "revealed", "resolved"] = "hidden"
    payoff: str = ""
    conditions: List[str] = []
    llm_generated: bool = False


class RuntimeClue(BaseModel):
    id: str
    label: str = ""
    type: str = "physical_evidence"
    thread_id: str = ""
    source_location: str = ""
    reveals: str = ""
    payoff: str = ""
    state: Literal["hidden", "seeded", "partial", "available", "discovered", "spent"] = "hidden"
    progress_ticks: int = 0
    is_required: bool = True
    revelation_ids: List[str] = []
    immediate_information: str = ""
    hidden_implication: str = ""
    unlocks: List[str] = []
    possible_actions: List[str] = []
    wrong_interpretations: List[str] = []
    source_ref: Dict[str, Any] = {}
    source_status: SourceStatus = "generated"
    is_preserved_from_pdf: bool = False
    inferred_payoff: bool = False
    confidence: float = 1.0
    llm_extracted: bool = False


class EventClock(BaseModel):
    id: str
    label: str
    value: int = 0
    max_value: int = 8
    consequence: str = ""
    active: bool = True
    on_complete: str = ""
    steps: List[Dict] = []
    # Tipo: determina cosa succede quando il clock completa
    clock_type: str = "narrative"
    # "narrative"        → il mondo cambia (NPC fugge, documento bruciato, ecc.) ma l'avventura continua
    # "terminal_defeat"  → story_over=true, victory=false
    # "terminal_victory" → story_over=true, victory=true
    # "escalation"       → aumento massiccio threat_level, non termina
    # Risoluzione: come i giocatori fermano questo clock
    resolution_clues: List[str] = []    # ID indizi che, trovati tutti, fermano/pausano il clock
    resolution_condition: str = ""      # descrizione leggibile di come fermarlo
    resolved: bool = False              # True = giocatori l'hanno fermato in tempo
    # Auto-bilanciamento: max_value >= len(resolution_clues) + buffer
    auto_balance: bool = True
    _balance_buffer: int = 2            # turni extra oltre il percorso minimo
    # Discovery: il clock esiste dal turno 1 ma è visibile ai giocatori solo dopo scoperta
    discovered: bool = False            # True = i giocatori sanno che esiste
    discovery_clue_id: str = ""         # id dell'indizio che rivela questo clock
    discovery_hint: str = ""            # cosa il GM può narrare prima (ambiguo)
    ticks_per_failure: int = 1
    ticks_per_partial: int = 0   # parziale = hai agito, ma con complicazioni → non avanza il pericolo
    ticks_per_success: int = 0
    source_ref: Dict[str, Any] = {}
    source_status: SourceStatus = "generated"
    is_explicit_from_source: bool = False
    is_inferred: bool = False
    confidence: float = 1.0


class PressureSystem(BaseModel):
    id: str
    label: str
    value: int = 0
    max_value: int = 10
    description: str = ""


class ResourceState(BaseModel):
    id: str
    label: str
    value: int = 0
    max_value: int = 0


class FinaleCondition(BaseModel):
    id: str
    label: str
    required_threads: List[str] = []
    required_clues: List[str] = []
    status: Literal["locked", "seeded", "available", "satisfied", "failed"] = "locked"
    depends_on: List[str] = []
    method: str = ""
    concrete_choice: str = ""


class GenreRuntime(BaseModel):
    rules: Dict = {}


class GenreProfile(BaseModel):
    id: str = "generic"
    tone: str = ""
    allowed_escalations: List[str] = []
    forbidden_escalations: List[str] = []
    terminal_events_require: List[str] = []
    max_default_tier: int = 4


class AdventureRuntime(BaseModel):
    id: str = "runtime"
    title: str = ""
    genre: str = ""
    runtime_profile: Literal[
        "investigation_graph",
        "guided_sandbox",
        "ritual_dungeon",
        "pursuit_thriller",
        "escalating_horror",
        "mythic_quest",
        "heist",
        "survival_escape",
        "faction_crisis",
        "journey",
        "branching_node_graph",
        "room_keyed_dungeon",
    ] = "investigation_graph"
    tone: str = ""
    premise: str = ""
    initial_hook: str = ""
    hidden_truths: List[HiddenTruth] = []
    objective_stack: List[Objective] = []
    locations: List[LocationState] = []
    actors: List[ActorState] = []
    factions: List[FactionState] = []
    revelations: List[Revelation] = []
    clues: List[RuntimeClue] = []
    event_clocks: List[EventClock] = []
    pressure_systems: List[PressureSystem] = []
    resources: List[ResourceState] = []
    finale_conditions: List[FinaleCondition] = []
    genre_runtime: GenreRuntime = GenreRuntime()
    genre_profile: GenreProfile = GenreProfile()
    source_mode: SourceMode = "raw_text"
    archetype_profile: Dict[str, Any] = {}
    preservation_policy: Dict[str, Any] = {}
    allow_runtime_expansion: bool = False


class _MappingCompatibleBase(BaseModel):
    """Mixin che rende ``**model`` valido per le entrate richiamate dalle API
    legacy in ``main.py`` (``AdventureDefinition(**compiled[...])``). Pydantic
    v2 BaseModel non implementa ``keys`` / ``__getitem__``, quindi l'unpack
    fallisce con "argument after ** must be a mapping".
    """

    def keys(self):  # pragma: no cover - delegata a Pydantic
        return self.__class__.model_fields.keys()

    def __getitem__(self, key):
        return getattr(self, key)


class AdventureDefinition(_MappingCompatibleBase):
    id: str = "definition"
    title: str = ""
    source_type: Literal["pdf_text", "markdown", "raw_text", "manual_json"] = "raw_text"
    source_mode: SourceMode = "raw_text"
    source_structure: Dict[str, Any] = {}
    archetype_profile: Dict[str, Any] = {}
    preservation_policy: Dict[str, Any] = {}
    original_structure_map: Dict[str, Any] = {}
    source_cards: List[Dict[str, Any]] = []
    inferred_elements: List[Dict[str, Any]] = []
    preserved_elements: List[Dict[str, Any]] = []
    genre: str = ""
    runtime_profiles: List[Literal[
        "investigation_graph",
        "guided_sandbox",
        "ritual_dungeon",
        "pursuit_thriller",
        "escalating_horror",
        "mythic_quest",
        "heist",
        "survival_escape",
        "faction_crisis",
        "journey",
        "branching_node_graph",
        "room_keyed_dungeon",
    ]] = ["investigation_graph"]
    tone: str = ""
    premise: str = ""
    initial_hook: str = ""
    core_truths: List[HiddenTruth] = []
    objectives: List[Objective] = []
    revelations: List[Revelation] = []
    clues: List[RuntimeClue] = []
    actors: List[ActorState] = []
    factions: List[FactionState] = []
    locations: List[LocationState] = []
    event_clocks: List[EventClock] = []
    pressure_systems: List[PressureSystem] = []
    resources: List[ResourceState] = []
    finale_conditions: List[FinaleCondition] = []
    story_threads: List[Dict[str, Any]] = []
    genre_runtime: Dict = {}
    genre_profile: GenreProfile = GenreProfile()
    legacy_adventure: Dict = {}
    suggestions: List[str] = []


class AdventureRuntimeState(_MappingCompatibleBase):
    definition_id: str
    current_scene_id: Optional[str] = None
    active_objective_ids: List[str] = []
    completed_objective_ids: List[str] = []
    failed_objective_ids: List[str] = []
    revealed_truth_ids: List[str] = []
    discovered_clue_ids: List[str] = []
    partial_clue_ids: List[str] = []
    active_revelation_ids: List[str] = []
    ready_revelation_ids: List[str] = []
    resolved_revelation_ids: List[str] = []
    actor_runtime: Dict = {}
    faction_runtime: Dict = {}
    location_runtime: Dict = {}
    clock_runtime: Dict = {}
    pressure_runtime: Dict = {}
    resource_runtime: Dict = {}
    finale_runtime: Dict = {}
    truth_runtime: Dict = {}
    clue_to_revelation_ids: Dict[str, List[str]] = {}
    thread_to_revelation_ids: Dict[str, List[str]] = {}
    revelation_to_thread_id: Dict[str, str] = {}
    flags: Dict = {}
    history: List[str] = []
