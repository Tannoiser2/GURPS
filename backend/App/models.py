
from pydantic import BaseModel
from typing import Dict, List, Optional
from typing import Literal
from .runtime_models import AdventureDefinition, AdventureRuntime, AdventureRuntimeState


class Action(BaseModel):
    name: str
    stat: str               # attributo cardine GURPS: "FO" | "DE" | "IN" | "SA"
    skill: str = ""
    difficulty: int = 0     # modificatore situazionale (positivo = malus al target)
    effect_type: str = "generic"
    action_role: str = "core"   # "core" | "support" | "risk"
    requires_item: Optional[str] = None
    source: str = "role"
    description: str = ""
    # Combattimento meccanico PR2
    attack_kind: Optional[str] = None   # "melee" | "ranged" | None
    damage: Optional[str] = None        # formula dado, es. "2d6", "1d6+2"
    damage_type: Optional[str] = None   # "cut" | "imp" | "cr" | "burn" | "pi" | "pi+" | "pi-" | "tox"
    # Arma a distanza (ranged)
    acc: int = 0                        # bonus Accuratezza (arco 2, pistola 2, fucile 4, ecc.)
    range_half: int = 0                 # gittata ½D in yard/esagoni (−3 oltre questa)
    range_max: int = 0                  # gittata massima in yard/esagoni (−6 oltre questa, impossibile oltre il doppio)
    bulk: int = 0                       # penalità Bulk (solo distanza; solitamente negativo)
    ammo: int = 0                       # capacità caricatore (0 = non applicabile)
    ammo_current: int = 0              # munizioni rimanenti nel caricatore corrente
    rcl: int = 1                        # rinculo per colpo extra (burst); 1 = nessuno
    reload: int = 0                     # turni per ricaricare (0 = istantaneo)
    weapon_id: str = ""                 # id in WEAPON_TABLE (es. "pistola_9mm")
    weapon_notes: str = ""              # note regole speciali


class EquipmentItem(BaseModel):
    """Oggetto fisico nell'inventario di un PG o NPC."""
    id: str = ""                   # slug univoco, es. "pistola_9mm_1", "frecce_30"
    name: str
    category: str = "misc"         # "weapon" | "armor" | "ammo" | "misc" | "consumable" | "quest_item" | "key_item"
    weapon_id: str = ""            # se weapon, link a WEAPON_TABLE (es. "pistola_9mm")
    quantity: int = 1              # per ammo/consumabili: numero di pezzi/pacchi
    ammo_per_pack: int = 0         # per category=="ammo": munizioni per unità (es. 20 cartucce/pacco)
    ammo_type: str = ""            # tipo di munizioni: abbinato al weapon_id dell'arma corrispondente
    armor_dr: int = 0              # per category=="armor": DR fornita
    armor_location: str = ""       # "torso" | "testa" | "totale" | …
    equipped: bool = True          # True = in mano / indosso
    weight: float = 0.0            # kg (approssimato)
    cost: int = 0                  # valore/costo in moneta di gioco
    notes: str = ""
    # ── Bonus/malus alle abilità ─────────────────────────────────────────────
    # Mappa skill → modificatore (positivo = bonus, negativo = malus).
    # Applicato automaticamente quando il PG usa quella skill con l'oggetto equipaggiato.
    # Es. scanner: {"ricerca": 2, "percezione": 1}
    # Es. armatura pesante: {"furtivita": -2, "acrobazia": -1}
    skill_bonuses: Dict[str, int] = {}
    # Bonus condizionali: applicati solo in specifici contesti
    # Es. [{"skill": "ricerca", "bonus": 3, "tags": ["tecnologico", "laboratorio"]}]
    conditional_bonuses: List[Dict] = []
    # Tracciabilità narrativa
    source_npc_id: str = ""        # id del WorldNPC o SceneEntity da cui è stato ottenuto
    source_location: str = ""      # nome della location in cui è stato trovato
    found_at_turn: int = 0         # turno in cui è stato raccolto


class LootEntry(BaseModel):
    """Oggetto disponibile per la raccolta nella scena corrente."""
    item: "EquipmentItem"
    source_type: str = "scene"     # "npc_defeat" | "scene" | "chest" | "clue" | "quest"
    source_id: str = ""            # id NPC/entità di origine
    source_name: str = ""          # nome leggibile (es. "Guardia Nord")
    collected_by: int = 0          # player_id che l'ha raccolto (0 = ancora disponibile)
    visible: bool = True           # False = nascosto finché non scoperto


class SceneEntity(BaseModel):
    id: str
    name: str
    type: str = "object"  # enemy | npc | ally | object | obstacle | location | phenomenon
    zone: str = "centro"
    status: str = "attivo"
    hp: int = 1
    max_hp: int = 1
    dr: int = 0                         # Resistenza al Danno
    tags: List[str] = []
    interactable: bool = True
    # Combattimento meccanico PR2
    attack_skill: int = 0               # livello skill di attacco (0 = non combattente)
    active_defense: int = 0             # valore base schivata/parata
    damage_dice: str = "1d6"            # formula danno, es. "2d6", "1d6+2"
    damage_type: str = "cr"             # "cut" | "imp" | "cr" | "burn"


class SceneChallenge(BaseModel):
    archetype: str = ""
    summary: str = ""
    obstacle: str = ""
    stakes: str = ""
    resolution_signal: str = ""
    valid_approaches: List[str] = []
    support_approaches: List[str] = []
    false_approaches: List[str] = []
    key_terms: List[str] = []
    allowed_effect_types: List[str] = []
    support_effect_types: List[str] = []
    blocked_effect_types: List[str] = []
    keyword_roots: List[str] = []
    scene_actions: List[Dict[str, str]] = []


class Player(BaseModel):
    id: int
    name: str
    role: str
    archetype: str
    stats: Dict[str, int]              # GURPS: {"FO": int, "DE": int, "IN": int, "SA": int}
    skills: Dict[str, int] = {}        # nome abilità → livello effettivo (es. {"Fucile": 14})
    advantages: List[str] = []         # nomi GURPS (es. "Carisma 2", "Riflessi da Combattimento")
    disadvantages: List[str] = []
    status: str = "ok"
    max_hp: int = 10                   # PF: punti ferita (= FO)
    hp: int = 10
    max_fp: int = 10                   # Punti Fatica (= SA)
    fp: int = 10
    will: int = 10                     # Volontà (= IN, modificabile da vantaggi)
    per: int = 10                      # Percezione (= IN)
    basic_speed: float = 5.0           # Velocità base (= (DE+SA)/4, NON arrotondato)
    dodge: int = 8                     # Schivata (= floor(basic_speed) + 3)
    move: int = 5                      # Movimento (= floor(basic_speed))
    dr: int = 0                        # Resistenza al Danno totale (da armatura/vantaggi)
    items: List[str] = []
    equipment: List["EquipmentItem"] = []   # inventario strutturato
    actions: List[Action] = []
    backstory: str = ""
    motivation: str = ""
    # ── Stato condizioni GURPS ────────────────────────────────────────────────
    shock_penalty: int = 0             # −X ai prossimi tiri attacco/difesa (max −4), azzera a fine turno
    stunned: bool = False              # stordito: niente azioni attive, −4 difesa, si recupera con SA
    prone: bool = False                # a terra: −3 attacco, −3 difesa melee, +1 difesa ranged
    posture: str = "standing"          # "standing" | "kneeling" | "prone"  (sincronizzato con prone)
    action_type: str = "normal"        # "normal" | "all_out_attack" | "all_out_defense" | "aim"
    death_check_pending: bool = False  # True se è appena sceso sotto 0 PF e deve tiro SA
    aimed: bool = False                # True se ha usato l'azione Aim il turno precedente (+Acc al prossimo tiro)
    aimed_turns: int = 0              # turni consecutivi di mira (max +Acc dell'arma)
    # ── Manovre GURPS ────────────────────────────────────────────────────────
    evaluate_bonus: int = 0            # bonus cumulativo dalla manovra Valuta (max +3, vs stesso bersaglio)
    evaluate_target: str = ""          # ID bersaglio corrente della manovra Valuta
    all_out_defense_active: bool = False  # True → +2 a tutte le difese questo turno, no attacco
    last_maneuver: str = ""            # ultima manovra usata (per UI e log)


class CharacterDraft(BaseModel):
    """Input utente per la creazione manuale di un personaggio (PR5)."""
    name: str
    role: str
    archetype: str = "custom"
    genre: str = "sci_fi"
    stats: Dict[str, int] = {}          # forza/agilita/intelligenza/empatia, base 10
    skills: Dict[str, int] = {}         # nome → livello assoluto
    advantages: List[str] = []
    disadvantages: List[str] = []
    dr: int = 0
    items: List[str] = []
    backstory: str = ""
    motivation: str = ""


class CharacterValidation(BaseModel):
    """Risultato validazione + anteprima derivate per un CharacterDraft (PR5)."""
    valid: bool
    point_total: int
    point_budget: int = 100
    points_remaining: int = 0
    errors: List[str] = []
    warnings: List[str] = []
    # Derivate calcolate
    max_hp: int = 10
    max_fp: int = 10
    will: int = 10
    per: int = 10
    basic_speed: float = 5.0
    dodge: int = 8
    move: int = 5
    # Breakdown costi
    stat_cost: int = 0
    skill_cost: int = 0
    advantage_cost: int = 0
    disadvantage_refund: int = 0


class CombatDefenseRequest(BaseModel):
    """Dichiarazione di difesa attiva del giocatore (PR2)."""
    player_id: int
    defense_type: str           # "dodge" | "parry" | "block"
    defense_skill: str = ""     # skill usata per parata (vuoto = usa dodge del Player)

class AttackResult(BaseModel):
    """Risultato completo di una sequenza attacco-difesa-danno GURPS."""
    hit: bool
    defended: bool = False
    raw_damage: int = 0
    dr_absorbed: int = 0
    net_damage: int = 0
    attacker_margin: int = 0
    defense_margin: int = 0
    attacker_critical: bool = False
    defense_critical_fail: bool = False
    wound_threshold: str = ""   # "" | "ferito" | "ferito_grave" | "fuori_combattimento" | "morto"
    narrative_hint: str = ""
    # ── Effetti secondari GURPS ───────────────────────────────────────────────
    shock_applied: int = 0             # valore shock applicato al bersaglio (0 = nessuno)
    major_wound: bool = False          # danno singolo > max_hp/2 → tiro SA stordimento
    major_wound_check_passed: bool = False  # esito tiro SA vs major wound
    knockdown: bool = False            # HP ≤ 0 → tiro SA o prone
    knockdown_check_passed: bool = False
    death_check: bool = False          # HP < 0 → tiro SA o morte
    death_check_passed: bool = False
    fp_cost: int = 0                   # punti fatica consumati dall'attaccante
    target_stunned: bool = False       # bersaglio è ora stordito
    target_prone: bool = False         # bersaglio è ora a terra


class TeamSetupState(BaseModel):
    genre: str = "sci_fi"
    active_slots: int = 3
    setup_complete: bool = False
    selected_player_ids: List[int] = []
    candidate_pool: List[Player] = []
    provider: str = "claude"       # "claude" | "openai" — AI testuale
    image_provider: str = "auto"   # "auto" | "openai" | "gemini" | "none"


class MissionState(BaseModel):
    genre: str
    theme_family: str = "base"
    mission_type: str
    title: str
    objective: str
    environment_type: str
    threat_type: str
    tone: str
    twist: str
    forbidden_elements: List[str] = []
    narrative_blacklist: List[str] = []

    mission_progress: int = 0
    mission_target: int = 3
    max_turns: int = 9
    goal_resolved: bool = False
    completed: bool = False
    failed: bool = False
    ending_text: str = ""


class PhaseState(BaseModel):
    phase_index: int = 1
    max_phases: int = 3
    phase_name: str = "Ingresso"
    zone_type: str = "zona esterna"
    zone_goal: str = "aprire la via"
    zone_tags: List[str] = []
    zone_modifier: str = ""
    is_final_phase: bool = False


class SceneState(BaseModel):
    scene_text: str
    scene_problem: str = ""
    scene_resolution: str = ""
    objective_progress: int = 0
    objective_target: int = 4
    threat_level: int = 1
    time_left: int = 4
    time_limit: int = 4
    scene_tags: List[str] = []
    entities: List[SceneEntity] = []
    challenge: SceneChallenge = SceneChallenge()


class MapEdge(BaseModel):
    from_id: str
    to_id: str
    status: str = "open"  # open | locked | hidden | trap | one_way
    label: str = ""
    discovered: bool = True
    note: str = ""


class MapNode(BaseModel):
    id: str
    name: str
    kind: str
    description: str
    phase_gate: int = 1
    connections: List[str] = []
    visited: bool = False
    blocked: bool = False
    destroyed: bool = False
    is_objective: bool = False
    is_final: bool = False
    tags: List[str] = []
    contains_clue: bool = False
    contains_enemy: bool = False
    contains_loot: bool = False
    special_event: Optional[str] = None
    grid_x: int = 0
    grid_y: int = 0
    # Encounter outcome — popolato quando la squadra lascia il nodo
    outcome: str = ""           # "" | "success_clean" | "success_dirty" | "timeout" | "crisis"
    outcome_summary: str = ""   # 1 frase: cosa è rimasto della zona dopo la partenza
    clue_yield: int = 0         # 0 = niente, 1 = indizio minore, 2 = indizio maggiore
    time_bonus_for_next: int = 0  # +/- al time_limit della prossima scena (consumato una volta)
    tactical_map: Dict = {}     # scheda tattica canonica per zone calde/finali


class MapState(BaseModel):
    map_type: str
    theme: str
    nodes: Dict[str, MapNode]
    connections_meta: Dict[str, MapEdge] = {}
    current_node_id: str
    start_node_id: str
    objective_node_id: str
    extraction_node_id: Optional[str] = None


class WorldNPC(BaseModel):
    id: str
    name: str
    role: str               # "alleato" | "antagonista" | "neutrale" | "testimone"
    current_node_id: str    # dove si trova ora
    status: str = "alive"   # "alive" | "missing" | "dead" | "hidden"
    threat_to_player: int = 0   # 0-3, peso della pressione che esercita
    holds_clue_for: str = ""    # thread_id se è la chiave di un thread
    description: str = ""       # 1 frase per il prompt: chi è e cosa vuole
    consulted: bool = False     # True dopo che il giocatore ha estratto un indizio da questo NPC
    # PR4 — reazioni sociali
    reaction_modifier: int = 0          # modificatore fisso al tiro di reazione (+/−)
    last_reaction_level: str = ""       # ultimo livello di reazione: "ostile".."entusiasta"
    last_reaction_roll: int = 0         # ultimo roll 3d6 + modificatori
    # Stat GURPS complete — pre-generate per NPC importanti (threat>=2)
    gurps_fo: Optional[int] = None    # Forza
    gurps_de: Optional[int] = None    # Destrezza/Agilità
    gurps_in: Optional[int] = None    # Intelligenza
    gurps_sa: Optional[int] = None    # Salute/Empatia
    gurps_skills: dict = {}           # {"combattere": 13, "intimidire": 12, ...}
    gurps_advantages: list[str] = []  # ["Riflessi da Combattimento", "Duro da Uccidere"]
    gurps_disadvantages: list[str] = []
    # Stat GURPS — generate al primo ingresso in combattimento e poi persistenti
    combat_hp: Optional[int] = None
    combat_max_hp: Optional[int] = None
    combat_dr: int = 0
    combat_attack_skill: Optional[int] = None
    combat_active_defense: Optional[int] = None
    combat_damage_dice: str = ""
    combat_damage_type: str = "cr"
    # Equipaggiamento e azioni (come i Player — usato in combattimento tattico)
    actions: List[Action] = []
    equipment: List["EquipmentItem"] = []


class ReactionResult(BaseModel):
    """Risultato di un tiro di reazione GURPS (PR4)."""
    npc_id: str
    npc_name: str
    roll: int                   # dado grezzo 3-18
    total: int                  # roll + tutti i modificatori
    level: str                  # "ostile" | "sfavorevole" | "neutro" | "favorevole" | "amichevole" | "entusiasta"
    description: str            # frase narrativa
    charisma_bonus: int = 0
    skill_bonus: int = 0
    consulted_bonus: int = 0
    npc_modifier: int = 0
    team_status_malus: int = 0


class AdventureCanon(BaseModel):
    core_truth: str = ""
    main_antagonist: str = ""
    false_leads: List[str] = []
    key_locations: List[str] = []
    required_clues: List[str] = []
    optional_events: List[str] = []
    finale_conditions: List[str] = []


class CanonClue(BaseModel):
    id: str
    label: str = ""
    type: Literal[
        "physical_evidence",
        "testimony",
        "document",
        "behavior",
        "location_detail",
        "contradiction",
    ] = "physical_evidence"
    thread_id: str
    source_location: str = ""
    reveals: str = ""
    payoff: str = ""
    is_required: bool = True
    is_discovered: bool = False


class NPCAgenda(BaseModel):
    npc_id: str
    role: Literal["ally", "antagonist", "witness", "red_herring", "victim", "patron", "neutral"] = "neutral"
    secret: str = ""
    goal: str = ""
    methods: List[str] = []
    recurrence_priority: Literal["low", "medium", "high"] = "medium"
    arc_status: Literal["unintroduced", "active", "exposed", "resolved", "dead"] = "unintroduced"


class StoryThread(BaseModel):
    id: str
    title: str = ""
    question: str
    true_answer: str = ""
    partial_clues: List[str] = []
    minimum_clues_to_deduce: int = 2
    payoff: str = ""
    linked_npcs: List[str] = []
    linked_locations: List[str] = []
    purpose: str = ""           # quale pezzo della soluzione finale sblocca
    required_clues: int | List[str] = 2
    answer: str = ""            # risposta canonica nascosta al tavolo, visibile al facilitatore
    clue_plan: List[str] = []    # indizi previsti che spiegano come arrivare alla risposta
    reveal_rule: str = ""        # quando/come la risposta puo essere narrata
    revealed: bool = False       # True quando almeno un indizio lo ha fatto emergere al tavolo
    collected_clue_ids: List[str] = []
    # active = ancora in raccolta; ready = soglia raggiunta, deve essere narrata e risolta; resolved = chiusa
    status: str = "active"
    # effetto da applicare al momento della risoluzione: tipo + payload
    # tipi supportati: "unlock_node" {node_id}, "remove_blocker" {edge_key},
    #                  "modify_objective" {note}, "add_action" {label}
    on_resolve_effect: Dict[str, str] = {}
    # se non vuoto, questo thread può chiudersi solo quando i parent sono risolti
    parent_thread_ids: List[str] = []
    resolution_text: str = ""  # popolato a chiusura: la deduzione narrativa


class StoryState(BaseModel):
    narrative_mode: str = "emergent_mission"  # "fixed_mystery" | "emergent_mission"
    premise: str = ""
    adventure_canon: Optional[AdventureCanon] = None
    hidden_truth: str = ""
    hidden_truth_clues: List[str] = []
    hidden_truth_reveal_rule: str = ""
    win_condition: str = ""
    discovered_facts: List[str] = []
    destroyed_elements: List[str] = []
    removed_clues: List[str] = []
    active_threads: List[str] = []
    thread_progress: Dict[str, int] = {}   # thread_text -> indizi raccolti (0-3, 3 = risolto) [legacy]
    threads: List[StoryThread] = []         # thread strutturati con dipendenze ed effetti
    resolved_threads: List[str] = []
    named_entities: List[str] = []
    key_entities: List[Dict[str, str | List[str]]] = []  # schede canoniche: nome, ruolo, dove, segreto, indizi, rivelazione
    key_items: List[Dict[str, str | List[str]]] = []     # oggetti/luoghi-chiave: nome, dove, uso, requisiti, indizi, rivelazione
    canonical_clues: List[CanonClue] = []
    npc_agendas: List[NPCAgenda] = []
    event_log: List[str] = []


class GameState(BaseModel):
    turn: int
    log: str
    scene_source: str = "unknown"
    in_setup: bool = True
    team_setup: TeamSetupState
    mission: Optional[MissionState] = None
    phase: Optional[PhaseState] = None
    scene: Optional[SceneState] = None
    story: Optional[StoryState] = None
    adventure_runtime: Optional[AdventureRuntime] = None
    adventure_definition_id: str = ""
    adventure_definition: Optional[AdventureDefinition] = None
    adventure_runtime_state: Optional[AdventureRuntimeState] = None
    current_objective_ids: List[str] = []
    active_revelation_ids: List[str] = []
    active_clock_ids: List[str] = []
    active_pressure_ids: List[str] = []
    allowed_escalation_tier: int = 3
    allowed_escalation_types: List[str] = []
    forbidden_escalation_types: List[str] = []
    blocked_major_events: List[str] = []
    downgraded_events: List[Dict] = []
    director_reason: str = ""
    map_state: Optional[MapState] = None
    world_npcs: List[WorldNPC] = []
    players: List[Player] = []
    mission_memory: List[str] = []
    selected_actions: Dict[int, str] = {}
    pending_movement: bool = False
    movement_options: List[str] = []
    # Combattimento meccanico PR2: attacco in attesa di difesa dichiarata
    pending_attack: Optional[Dict] = None  # payload attacco (player_id, action, target_id, roll)
    last_attack_result: Optional[Dict] = None  # AttackResult dettagliato dell'ultimo scambio
    last_roll_details: List[Dict] = []  # per_player_outcomes dell'ultimo resolve_actions (playtest)
    personal_victories: Dict[int, bool] = {}  # player_id → obiettivo personale raggiunto
    flags: Dict = {}  # runtime flags: pending_npc_events, pe_triggered_*, etc.
    locked_context: List[str] = []  # fatti pilastro bloccati — iniettati in ogni turno, non troncabili
    consecutive_no_progress_turns: int = 0  # turni consecutivi senza indizi trovati — usato dal soft escalation
    turn_id: str = ""                           # UUID del turno corrente — per sync client/server
    # Inventario persistente: oggetti disponibili per la raccolta nella scena corrente
    loot_pool: List["LootEntry"] = []          # bottino visibile/raccoglibile ora
    scene_items_given: List[str] = []          # item_id già distribuiti (evita duplicati)
