
import random
import re
from collections import Counter
from .models import (
    GameState,
    Player,
    Action,
    SceneEntity,
    SceneChallenge,
    SceneState,
    MissionState,
    PhaseState,
    TeamSetupState,
    StoryState,
    StoryThread,
    AdventureCanon,
    CanonClue,
    NPCAgenda,
    WorldNPC,
    MapState,
    MapNode,
    MapEdge,
    AttackResult,
    CombatDefenseRequest,
    ReactionResult,
)
from .combat import (
    resolve_attack,
    reset_action_type, attempt_stun_recovery, stand_up,
)
from .action_intent import select_best_skill as resolve_action_skill
from .data_skills import (
    LEGACY_EFFECT_TO_SKILL,
    SKILL_INFO,
    SKILL_TO_EFFECT_TYPE,
    SKILLS_BY_STAT,
    VALID_SKILLS,
    default_skill_for,
    skill_default_level,
    skill_stat,
    normalize_skill,
    normalize_stat,
)
from .data_advantages import (
    advantage_skill_bonus,
    advantage_effect_type_bonus,
    advantage_dodge_bonus,
    advantage_death_threshold_mult,
    has_morale_check,
    advantage_combat_penalty,
    advantage_breakdown,
    advantage_luck_rerolls,
    advantage_will_modifier,
    advantage_per_modifier,
    advantage_night_vision,
    advantage_reckless_bonus,
)
from .runtime_models import AdventureDefinition, AdventureRuntimeState
from .data_genres import GENRE_PACKS
from .claude_service import (
    generate_scene_package,
    generate_mission_ending,
    get_phase_blueprint,
    generate_candidate_pool,
    generate_actions_for_selected_team,
    generate_story_canon,
    generate_prologue,
    refine_story_canon_with_prologue,
    rename_map_nodes_with_canon,
    generate_initial_world_npcs,
    build_scene_seed_with_canon,
    generate_movement_transition_narrative,
)

# Distribuzione esatta di 3d6: probabilità (su 216 esiti) di ogni somma 3-18.
# Usata da preview_action_outcomes per stimare le probabilità degli esiti GURPS.
_3D6_OUTCOMES: dict[int, int] = {
    3: 1, 4: 3, 5: 6, 6: 10, 7: 15, 8: 21, 9: 25, 10: 27,
    11: 27, 12: 25, 13: 21, 14: 15, 15: 10, 16: 6, 17: 3, 18: 1,
}
_3D6_TOTAL = 216  # = sum(_3D6_OUTCOMES.values())
_SCENE_KEYWORD_STOPWORDS = {
    "alla", "allo", "alla", "agli", "alle", "anche", "ancora", "aprire", "arrivare",
    "attuale", "attorno", "attraverso", "avanzata", "avanti", "avere", "basso", "bene",
    "cerca", "cercare", "come", "con", "contro", "cosa", "dalla", "dalle", "dallo",
    "degli", "della", "delle", "dello", "dentro", "deve", "devono", "dopo", "dove",
    "essere", "fare", "forse", "forza", "gli", "gruppo", "hanno", "immediato", "insieme",
    "loro", "mentre", "molto", "nella", "nelle", "nello", "nostra", "nostro", "nulla",
    "obiettivo", "ogni", "oltre", "passo", "per", "pero", "piano", "poco", "poi",
    "posto", "prima", "problema", "punto", "quale", "quella", "quello", "questa",
    "questo", "scena", "squadra", "sulla", "sullo", "solo", "sono", "stesso", "subito",
    "sugli", "suggerito", "tempo", "trovare", "tutto", "verso", "zona",
}
_GENERIC_SCENE_KEYWORDS = {
    "ambient", "apert", "attiv", "chiav", "clue", "core", "dettagl", "effett", "element",
    "fals", "luog", "minacc", "mission", "narrat", "oggett", "press", "risch", "salv",
    "segnal", "situaz", "stanz", "thread", "trappol", "verit",
}
_EFFECT_TYPE_LABELS = {
    "investigare": "esaminare gli indizi sul posto",
    "rilevare": "osservare, scansionare o seguire tracce concrete",
    "decifrare": "interpretare codici, dati o simboli",
    "forzare": "aprire, sbloccare o alterare l'ostacolo materiale",
    "combattere": "neutralizzare la minaccia presente",
    "infiltrarsi": "aggirare il rischio o passare senza esporsi",
    "recuperare": "estrarre o mettere al sicuro l'elemento chiave",
    "negoziare": "ottenere cooperazione o informazioni da chi c'è",
    "difendere": "tenere la posizione e guadagnare tempo",
    "stabilizzare": "contenere danni, ferite o contaminazione",
    "ingannare": "depistare chi controlla la situazione",
    "evocare": "attivare un effetto anomalo in modo controllato",
}
_EFFECT_TYPE_TITLES = {
    "investigare": "Esaminare la scena",
    "rilevare": "Leggere i segnali",
    "decifrare": "Decifrare il pattern",
    "forzare": "Forzare il varco",
    "combattere": "Spezzare il blocco",
    "infiltrarsi": "Aggirare il rischio",
    "recuperare": "Mettere in sicurezza",
    "negoziare": "Ottenere cooperazione",
    "difendere": "Tenere la posizione",
    "stabilizzare": "Stabilizzare la zona",
    "ingannare": "Costruire un diversivo",
    "evocare": "Attivare il fenomeno",
}
_SCENE_ARCHETYPE_DEFS = {
    "accesso_sorvegliato": {
        "allowed": {"infiltrarsi", "ingannare", "negoziare", "rilevare", "forzare"},
        "support": {"difendere", "stabilizzare"},
        "blocked": {"combattere"},
        "summary": "Serve superare un accesso controllato senza consegnare l'iniziativa a chi osserva.",
        "obstacle": "L'ostacolo immediato e il varco controllato verso {target}.",
        "resolution": "la squadra ottiene un ingresso credibile, un passaggio secondario o una distrazione sufficiente ad attraversare",
        "false": [
            "alzare subito uno scontro aperto davanti al controllo",
            "girare a vuoto senza scegliere un pretesto o un varco",
            "forzare il passaggio senza prima leggere guardie, ritmi o coperture",
        ],
    },
    "identificare_bersaglio": {
        "allowed": {"investigare", "rilevare", "decifrare", "negoziare", "ingannare"},
        "support": {"difendere", "stabilizzare"},
        "blocked": {"combattere"},
        "summary": "Serve distinguere il bersaglio giusto da esche, nomi falsi o informazioni contraddittorie.",
        "obstacle": "L'ostacolo immediato e capire chi o cosa, tra {target}, conta davvero.",
        "resolution": "la squadra riconosce il bersaglio corretto, ottiene una prova o elimina un'identita falsa",
        "false": [
            "agire sul primo sospetto senza verificarlo",
            "saltare alle conclusioni senza prova o riscontro",
            "sprecare tempo su dettagli pittoreschi ma irrilevanti",
        ],
    },
    "negoziazione_tesa": {
        "allowed": {"negoziare", "ingannare", "rilevare", "investigare"},
        "support": {"difendere", "stabilizzare"},
        "blocked": {"forzare", "combattere"},
        "summary": "Serve spostare una decisione umana o politica prima che il tavolo si chiuda.",
        "obstacle": "L'ostacolo immediato e la volonta di {target}, che va letta e piegata nel momento giusto.",
        "resolution": "la squadra ottiene collaborazione, tempo o un impegno concreto da chi decide",
        "false": [
            "premere senza capire cosa vuole davvero l'interlocutore",
            "mostrare le carte troppo presto",
            "provare a intimidire quando la scena richiede credibilita",
        ],
    },
    "anomalia_da_decifrare": {
        "allowed": {"decifrare", "rilevare", "investigare", "forzare", "stabilizzare", "evocare"},
        "support": {"difendere", "stabilizzare"},
        "blocked": {"combattere"},
        "summary": "Serve capire la logica dell'anomalia prima che il fenomeno travolga la scena.",
        "obstacle": "L'ostacolo immediato e l'effetto instabile legato a {target}.",
        "resolution": "la squadra interpreta il fenomeno, ne isola il punto critico o lo stabilizza abbastanza da agire",
        "false": [
            "toccare o attivare tutto insieme senza una lettura preliminare",
            "ignorare segnali, simboli o parametri che spiegano il fenomeno",
            "cercare una soluzione solo fisica a un problema ancora incomprensibile",
        ],
    },
    "recupero_conteso": {
        "allowed": {"recuperare", "forzare", "rilevare", "infiltrarsi", "difendere"},
        "support": {"difendere", "stabilizzare"},
        "blocked": {"negoziare"},
        "summary": "Serve mettere le mani sull'elemento utile prima che il contesto lo renda irraggiungibile.",
        "obstacle": "L'ostacolo immediato e recuperare {target} mentre la scena resta instabile.",
        "resolution": "la squadra mette in sicurezza l'elemento chiave o apre la via per estrarlo subito dopo",
        "false": [
            "trattare l'oggetto come gia al sicuro quando e ancora esposto",
            "perdere tempo a ispezioni secondarie mentre la finestra si chiude",
            "muoversi senza copertura quando il recupero richiede tempismo",
        ],
    },
    "scorta_estrazione": {
        "allowed": {"difendere", "infiltrarsi", "recuperare", "negoziare", "rilevare"},
        "support": {"stabilizzare", "difendere"},
        "blocked": {"decifrare"},
        "summary": "Serve portare qualcuno o qualcosa fuori dalla zona viva senza consegnarlo ai inseguitori o al caos.",
        "obstacle": "L'ostacolo immediato e muovere {target} fino a un'uscita utile senza rompere la copertura.",
        "resolution": "la squadra apre una rotta credibile, mette il bersaglio sotto controllo e avvia l'estrazione",
        "false": [
            "esporre il bersaglio prima di avere una rotta o una copertura",
            "fermare la marcia per dettagli non essenziali",
            "dividere il gruppo senza motivo quando serve protezione concentrata",
        ],
    },
    "combattimento_bloccante": {
        "allowed": {"combattere", "difendere", "infiltrarsi", "forzare", "rilevare"},
        "support": {"stabilizzare", "difendere"},
        "blocked": {"negoziare"},
        "summary": "Serve rompere il blocco ostile prima che la minaccia occupi tutta la scena.",
        "obstacle": "L'ostacolo immediato e la pressione ostile legata a {target}.",
        "resolution": "la squadra spezza il blocco, apre spazio o costringe la minaccia a perdere terreno",
        "false": [
            "restare fermi sotto pressione aspettando che il rischio si risolva da solo",
            "sparpagliarsi senza una linea di copertura",
            "provare soluzioni diplomatiche quando la minaccia sta gia chiudendo il varco",
        ],
    },
    "pressione_locale": {
        "allowed": {"investigare", "rilevare", "forzare", "recuperare", "difendere"},
        "support": {"stabilizzare", "difendere"},
        "blocked": set(),
        "summary": "Serve capire rapidamente qual e la leva concreta della zona prima che la pressione salga.",
        "obstacle": "L'ostacolo immediato riguarda {target}.",
        "resolution": "la squadra individua il punto debole della scena e lo trasforma in avanzamento",
        "false": [
            "scrivere o dichiarare intenzioni senza un bersaglio concreto",
            "ripetere azioni generiche che non cambiano nulla sul posto",
            "ignorare l'elemento piu pressante della zona",
        ],
    },
}


def hp_to_status(hp: int, max_hp: int) -> str:
    if hp <= 0:
        return "fuori_combattimento"
    ratio = hp / max(max_hp, 1)
    if ratio <= 0.40:
        return "ferito_grave"
    if ratio <= 0.75:
        return "ferito"
    return "ok"


def build_players_from_dicts(
    player_dicts: list[dict],
    previous_players: list[Player] | None = None,
) -> list[Player]:
    """Costruisce i Player applicando le derivate GURPS Lite.

    Mapping nomi italiani ↔ attributi GURPS:
      forza = FO (PF, danno)
      agilita = DE (Movimento, Schivata)
      intelligenza = IN (Volontà, Percezione)
      empatia = SA (Punti Fatica, Movimento/Schivata via Velocità base)

    Derivate:
      max_hp (PF)     = forza
      max_fp          = empatia (SA)
      will            = intelligenza
      per             = intelligenza
      basic_speed     = (agilita + empatia) / 4   (non arrotondato)
      move            = floor(basic_speed)
      dodge           = floor(basic_speed) + 3
    """
    previous_by_id = {p.id: p for p in previous_players} if previous_players else {}
    players: list[Player] = []

    for p in player_dicts:
        previous = previous_by_id.get(p["id"])
        stats = {normalize_stat(k): v for k, v in (p.get("stats", {}) or {}).items()}
        forza = stats.get("forza", 10)
        agilita = stats.get("agilita", 10)
        intelligenza = stats.get("intelligenza", 10)
        empatia = stats.get("empatia", 10)

        advantages_list = list(p.get("advantages", []))
        disadvantages_list = list(p.get("disadvantages", []))
        all_adv = advantages_list + disadvantages_list

        max_hp_val = max(1, forza)
        max_fp_val = max(1, empatia)
        will_val = intelligenza + advantage_will_modifier(all_adv)
        per_val = intelligenza + advantage_per_modifier(all_adv)
        basic_speed_val = (agilita + empatia) / 4.0
        move_val = int(basic_speed_val)        # floor positivo
        dodge_val = move_val + 3 + advantage_dodge_bonus(all_adv)

        hp_val = previous.hp if previous else p.get("hp", max_hp_val)
        hp_val = max(0, min(hp_val, max_hp_val))
        fp_val = previous.fp if previous else p.get("fp", max_fp_val)
        fp_val = max(0, min(fp_val, max_fp_val))
        status = hp_to_status(hp_val, max_hp_val)

        players.append(
            Player(
                id=p["id"],
                name=p["name"],
                role=p["role"],
                archetype=p["archetype"],
                stats=stats,
                skills={normalize_skill(k): v for k, v in p.get("skills", {}).items()},
                advantages=advantages_list,
                disadvantages=disadvantages_list,
                status=status,
                max_hp=max_hp_val,
                hp=hp_val,
                max_fp=max_fp_val,
                fp=fp_val,
                will=will_val,
                per=per_val,
                basic_speed=basic_speed_val,
                dodge=dodge_val,
                move=move_val,
                dr=int(p.get("dr", 0)),
                items=p.get("items", []),
                backstory=p.get("backstory", ""),
                motivation=p.get("motivation", ""),
                actions=[
                    Action(
                        name=a["name"],
                        stat=a["stat"],
                        skill=a.get("skill", ""),
                        difficulty=a.get("difficulty", 0),
                        effect_type=a.get("effect_type", "generic"),
                        action_role=a.get("action_role", "core"),
                        requires_item=a.get("requires_item"),
                        source=a.get("source", "role"),
                        description=a.get("description", ""),
                    )
                    for a in p.get("actions", [])
                ],
            )
        )

    return players


def empty_game_state() -> GameState:
    return GameState(
        turn=1,
        log="Configura il team prima di iniziare.",
        scene_source="setup",
        in_setup=True,
        team_setup=TeamSetupState(),
        mission=None,
        phase=None,
        scene=None,
        story=None,
        map_state=None,
        players=[],
        mission_memory=[],
        selected_actions={},
    )


def prepare_team_setup(genre: str, provider: str = "claude") -> GameState:
    pack = GENRE_PACKS.get(genre) or GENRE_PACKS.get("action") or {}
    mission_type = (pack.get("obiettivi") or ["avventura"])[0]
    environment_type = (pack.get("ambienti") or ["zona iniziale"])[0]

    candidates = generate_candidate_pool(
        genre=genre,
        active_slots=8,
        mission_type=mission_type,
        environment_type=environment_type,
        theme_family="",
    )

    return GameState(
        turn=1,
        log="Seleziona i personaggi da portare in missione.",
        scene_source="setup",
        in_setup=True,
        team_setup=TeamSetupState(
            genre=genre,
            active_slots=0,
            setup_complete=False,
            selected_player_ids=[],
            candidate_pool=build_players_from_dicts(candidates),
            provider=provider,
        ),
        mission=None,
        phase=None,
        scene=None,
        story=None,
        map_state=None,
        players=[],
        mission_memory=[],
        selected_actions={},
    )


def _edge_key(a: str, b: str) -> str:
    return "|".join(sorted([a, b]))


def _connect_map_nodes(
    nodes: dict[str, MapNode],
    edges: dict[str, MapEdge],
    a: str,
    b: str,
    status: str = "open",
    label: str = "",
    note: str = "",
    discovered: bool = True,
) -> None:
    nodes[a].connections.append(b)
    nodes[b].connections.append(a)
    edges[_edge_key(a, b)] = MapEdge(
        from_id=a,
        to_id=b,
        status=status,
        label=label,
        note=note,
        discovered=discovered,
    )


def generate_map_from_bible_locations(locations: list[dict], genre: str) -> MapState:
    """Costruisce una MapState dalle location della bibbia dell'avventura.
    Le location sono ordinate: la prima è il punto di partenza, l'ultima
    (o quella con has_combat_potential=True più avanzata) è l'obiettivo.
    """
    if not locations:
        return None

    # Pulisce e deduplicazione
    locs = [l for l in locations if l.get("name")]
    if not locs:
        return None

    n_locs = len(locs)
    nodes: dict[str, MapNode] = {}
    edges: dict[str, MapEdge] = {}

    # Layout su griglia: max 3 colonne, righe quanto serve
    # Con ≤3 location: layout lineare orizzontale
    # Con 4-6: due righe (start in alto a sinistra, obiettivo in basso a destra)
    COLS = min(3, n_locs)
    rows_needed = (n_locs + COLS - 1) // COLS

    def _grid_pos(i):
        row = i // COLS
        col = i % COLS
        # alterna direzione ogni riga per effetto "snake" più leggibile
        if row % 2 == 1:
            col = COLS - 1 - col
        return col * 2, row * 2  # passo 2 per spaziatura

    # Identifica indice obiettivo: preferisce location con has_combat_potential=True,
    # altrimenti l'ultima
    obj_idx = n_locs - 1
    for i in range(n_locs - 1, -1, -1):
        if locs[i].get("has_combat_potential"):
            obj_idx = i
            break

    # Indice uscita: ultima location se diversa dall'obiettivo
    exit_idx = n_locs - 1 if obj_idx != n_locs - 1 else None

    start_id = "loc_0"
    obj_id = f"loc_{obj_idx}"
    exit_id = f"loc_{exit_idx}" if exit_idx is not None else None

    for i, loc in enumerate(locs):
        nid = f"loc_{i}"
        gx, gy = _grid_pos(i)
        is_obj = (i == obj_idx)
        is_final = (exit_idx is not None and i == exit_idx)
        tags = ["obiettivo"] if is_obj else (["uscita"] if is_final else ["accesso" if i == 0 else "clue"])
        if loc.get("has_combat_potential"):
            tags.append("pericolo")
        nodes[nid] = MapNode(
            id=nid,
            name=loc["name"],
            kind=loc.get("description", loc["name"])[:20].strip(),
            description=loc.get("description", loc["name"]),
            phase_gate=1 + (i * 2 // max(n_locs, 1)),
            connections=[],
            tags=tags,
            contains_clue=(i not in (0, obj_idx)),
            contains_enemy=bool(loc.get("has_combat_potential")),
            contains_loot=False,
            is_objective=is_obj,
            is_final=is_final,
            grid_x=gx,
            grid_y=gy,
            tactical_map=loc.get("tactical_map") or {},
        )

    # Connessioni: ogni nodo connesso al successivo (catena lineare)
    ids = [f"loc_{i}" for i in range(n_locs)]
    for i in range(len(ids) - 1):
        _connect_map_nodes(nodes, edges, ids[i], ids[i + 1], "open")

    # Il nodo di partenza è già visitato
    nodes[start_id].visited = True

    return MapState(
        map_type=genre,
        theme="avventura",
        nodes=nodes,
        connections_meta=edges,
        current_node_id=start_id,
        start_node_id=start_id,
        objective_node_id=obj_id,
        extraction_node_id=exit_id,
    )


def generate_map_from_adventure_definition(definition: AdventureDefinition) -> MapState:
    """Costruisce la mappa strategica reale dal runtime compilato.

    Questa e la mappa autoritativa per le avventure compilate: location, indizi,
    attori e zone tattiche arrivano da AdventureDefinition, non dal generatore legacy.
    """
    locations = list(definition.locations or [])
    if not locations:
        return generate_map_from_bible_locations(definition.legacy_adventure.get("locations", []), definition.genre)

    clue_locations = {}
    for clue in definition.clues:
        key = str(clue.source_location or "").lower()
        for loc in locations:
            if key and (key in loc.name.lower() or loc.name.lower() in key):
                clue_locations.setdefault(loc.id, []).append(clue.id)

    actor_locations = {}
    for actor in definition.actors:
        key = str(actor.location_id or "").lower()
        for loc in locations:
            if key and (key == loc.id.lower() or key in loc.name.lower() or loc.name.lower() in key):
                actor_locations.setdefault(loc.id, []).append(actor.id)

    hot_ids = {
        loc.id for loc in locations
        if bool(loc.tactical_map and loc.tactical_map.get("enabled", bool(loc.tactical_map)))
    }
    objective_id = None
    for loc in locations:
        tactical_role = str((loc.tactical_map or {}).get("role", "")).lower()
        if "final" in tactical_role:
            objective_id = loc.id
    if not objective_id:
        objective_id = locations[-1].id

    cols = min(4, max(2, int(len(locations) ** 0.5) + 1))

    def _pos(i: int) -> tuple[int, int]:
        row = i // cols
        col = i % cols
        if row % 2:
            col = cols - 1 - col
        return col * 2, row * 2

    nodes: dict[str, MapNode] = {}
    edges: dict[str, MapEdge] = {}
    for i, loc in enumerate(locations):
        gx, gy = _pos(i)
        has_clue = bool(clue_locations.get(loc.id) or loc.contains_clues)
        has_actor = bool(actor_locations.get(loc.id) or loc.contains_actors)
        tactical = dict(loc.tactical_map or {})
        tactical_enabled = bool(tactical.get("enabled", bool(tactical)))
        role = str(tactical.get("role") or "").lower()
        tags = []
        if i == 0:
            tags.append("start")
        if has_clue:
            tags.append("indizio")
        if has_actor:
            tags.append("png")
        if tactical_enabled:
            tags.append("zona_calda")
        if loc.id == objective_id:
            tags.append("finale")
        nodes[loc.id] = MapNode(
            id=loc.id,
            name=loc.name,
            kind=loc.type or "location",
            description=loc.description or loc.name,
            phase_gate=1,
            connections=[],
            visited=i == 0,
            blocked=loc.access_state in {"locked", "blocked", "hidden"},
            is_objective=loc.id == objective_id,
            is_final=loc.id == objective_id or "final" in role,
            tags=tags,
            contains_clue=has_clue,
            contains_enemy=tactical_enabled or any(
                a.role in {"antagonist", "red_herring"} for a in definition.actors if a.id in actor_locations.get(loc.id, [])
            ),
            grid_x=gx,
            grid_y=gy,
            tactical_map=tactical if tactical_enabled else {},
        )

    ids = [loc.id for loc in locations]
    # Connessioni esplicite da genre_runtime.scene_nodes, se presenti.
    scene_nodes = (definition.genre_runtime or {}).get("scene_nodes") or []
    explicit_edges = False
    for scene in scene_nodes:
        if not isinstance(scene, dict):
            continue
        from_id = scene.get("id") or scene.get("location_id")
        for choice in scene.get("choices") or []:
            to_id = choice.get("target_node") or choice.get("to") or choice.get("location_id")
            if from_id in nodes and to_id in nodes:
                _connect_map_nodes(nodes, edges, from_id, to_id, choice.get("status", "open"))
                explicit_edges = True
    if not explicit_edges:
        for i in range(len(ids) - 1):
            status = "open"
            target_loc = locations[i + 1]
            if target_loc.access_state in {"locked", "hidden", "blocked"}:
                status = target_loc.access_state
                # La mappa mostra il nodo, ma il bordo resta bloccato finche una pista non lo sblocca.
                nodes[target_loc.id].blocked = True
            _connect_map_nodes(nodes, edges, ids[i], ids[i + 1], status)
        # Le zone calde non finali devono essere percorsi laterali reali, non solo schede nel pannello.
        for hid in hot_ids:
            if hid in nodes and hid not in {ids[0], objective_id}:
                prev = ids[max(0, ids.index(hid) - 1)]
                _connect_map_nodes(nodes, edges, prev, hid, "open")

    return MapState(
        map_type=definition.genre or "compiled",
        theme=definition.tone or "compiled_adventure",
        nodes=nodes,
        connections_meta=edges,
        current_node_id=ids[0],
        start_node_id=ids[0],
        objective_node_id=objective_id,
        extraction_node_id=objective_id,
    )


def _compiled_location_for_actor(actor_location: str, map_state: MapState, fallback_ids: list[str], idx: int) -> str:
    key = str(actor_location or "").lower()
    if key:
        for nid, node in map_state.nodes.items():
            if key == nid.lower() or key in node.name.lower() or node.name.lower() in key:
                return nid
    non_start = [nid for nid in fallback_ids if nid != map_state.start_node_id]
    return (non_start or fallback_ids or [map_state.start_node_id])[idx % max(1, len(non_start or fallback_ids or [map_state.start_node_id]))]


def _world_npcs_from_definition(definition: AdventureDefinition, map_state: MapState) -> list[WorldNPC]:
    node_ids = list(map_state.nodes.keys())
    npcs: list[WorldNPC] = []
    for i, actor in enumerate(definition.actors[:12]):
        role = str(actor.role or "neutral")
        low = role.lower()
        threat = 3 if "antagon" in low or "boss" in low else 2 if "red" in low or "guard" in low else 1 if role != "ally" else 0
        node_id = _compiled_location_for_actor(actor.location_id, map_state, node_ids, i)
        npcs.append(WorldNPC(
            id=actor.id,
            name=actor.name,
            role=role,
            current_node_id=node_id,
            status="alive" if actor.status in {"unintroduced", "active", "exposed"} else actor.status,
            threat_to_player=threat,
            holds_clue_for="",
            description=actor.goal or actor.secret or role,
            secret=actor.secret,
        ))
    return npcs


def _story_state_from_definition(definition: AdventureDefinition) -> StoryState:
    canon = AdventureCanon(
        core_truth=definition.core_truths[0].statement if definition.core_truths else "",
        main_antagonist=next((a.name for a in definition.actors if "antagon" in a.role.lower()), ""),
        key_locations=[l.name for l in definition.locations],
        required_clues=[c.id for c in definition.clues if c.is_required],
        finale_conditions=[f.label for f in definition.finale_conditions],
    )
    valid_clue_types = {"physical_evidence", "testimony", "document", "behavior", "location_detail", "contradiction"}
    clues = [
        CanonClue(
            id=c.id,
            label=c.label,
            type=c.type if c.type in valid_clue_types else "physical_evidence",
            thread_id=c.thread_id or (definition.revelations[0].thread_id if definition.revelations else "T1"),
            source_location=c.source_location,
            reveals=c.reveals,
            payoff=c.payoff,
            is_required=c.is_required,
        )
        for c in definition.clues
    ]
    threads = []
    for i, rev in enumerate(definition.revelations, start=1):
        tid = rev.thread_id or f"T{i}"
        required = rev.required_clues or [c.id for c in definition.clues if rev.id in c.revelation_ids]
        threads.append(StoryThread(
            id=tid,
            title=rev.statement[:80],
            question=rev.statement if rev.statement.endswith("?") else f"Cosa significa: {rev.statement[:80]}?",
            true_answer=rev.statement,
            required_clues=required,
            minimum_clues_to_deduce=min(2, max(1, len(required) or 1)),
            payoff=rev.payoff,
            answer=rev.statement,
            status="hidden",
        ))
    agendas = [
        NPCAgenda(
            npc_id=a.id,
            role=a.role if a.role in {"ally", "antagonist", "witness", "red_herring", "victim", "patron", "neutral"} else "neutral",
            secret=a.secret,
            goal=a.goal,
            recurrence_priority="high" if "antagon" in a.role.lower() else "medium",
            arc_status=a.status if a.status in {"unintroduced", "active", "exposed", "resolved", "dead"} else "unintroduced",
        )
        for a in definition.actors
    ]
    return StoryState(
        narrative_mode="compiled_runtime",
        premise=definition.premise,
        adventure_canon=canon,
        hidden_truth=canon.core_truth,
        hidden_truth_clues=[c.id for c in definition.clues[:3]],
        hidden_truth_reveal_rule=definition.core_truths[0].reveal_rule if definition.core_truths else "",
        win_condition=definition.objectives[0].label if definition.objectives else "",
        active_threads=[t.question for t in threads[:3]],
        threads=threads,
        named_entities=[a.name for a in definition.actors],
        key_entities=[
            {"name": a.name, "ruolo": a.role, "dove": a.location_id, "segreto": a.secret, "rivelazione": a.goal}
            for a in definition.actors
        ],
        key_items=[
            {"name": c.label, "dove": c.source_location, "uso": c.payoff, "rivelazione": c.reveals}
            for c in definition.clues
        ],
        canonical_clues=clues,
        npc_agendas=agendas,
        event_log=["Avventura compilata: il runtime e la fonte autoritativa del mondo."],
    )


def start_compiled_game_from_selection(
    current_state: GameState,
    selected_player_ids: list[int],
    custom_names: dict[int, str] | None,
    adventure_bible: dict,
) -> GameState:
    """Avvia un'avventura compilata senza usare generatori legacy di missione/canon/scena."""
    definition = AdventureDefinition(**adventure_bible["adventure_definition"])
    runtime_state = AdventureRuntimeState(**adventure_bible.get("runtime_state", {"definition_id": definition.id}))
    selected_player_ids = selected_player_ids[:4]
    if not selected_player_ids:
        raise ValueError("Nessun personaggio selezionato.")
    custom_names = custom_names or {}
    map_state = generate_map_from_adventure_definition(definition)
    world_npcs = _world_npcs_from_definition(definition, map_state)
    story = _story_state_from_definition(definition)

    candidate_pool_dicts = [
        {
            "id": p.id,
            "name": custom_names.get(p.id, p.name),
            "role": p.role,
            "archetype": p.archetype,
            "stats": p.stats,
            "skills": dict(p.skills),
            "advantages": list(p.advantages),
            "disadvantages": list(p.disadvantages),
            "status": p.status,
            "hp": p.hp,
            "max_hp": p.max_hp,
            "items": p.items,
            "backstory": getattr(p, "backstory", ""),
            "motivation": getattr(p, "motivation", ""),
            "actions": [],
        }
        for p in current_state.team_setup.candidate_pool
    ]
    selected_candidates = [p for p in candidate_pool_dicts if p["id"] in selected_player_ids]
    hook = definition.initial_hook or definition.premise or "L'avventura compilata inizia."
    selected_candidates = generate_actions_for_selected_team(
        selected_candidates,
        scene_context=hook,
        scene_tags=["compiled_runtime", "inizio"],
        genre=definition.genre,
    )
    first_clock = definition.event_clocks[0] if definition.event_clocks else None
    objective = definition.objectives[0].label if definition.objectives else "Completare l'avventura."
    game = GameState(
        turn=1,
        log="Avventura compilata iniziata.",
        scene_source="compiled_runtime",
        in_setup=False,
        team_setup=TeamSetupState(
            genre=definition.genre or current_state.team_setup.genre,
            active_slots=len(selected_player_ids),
            setup_complete=True,
            selected_player_ids=selected_player_ids,
            candidate_pool=current_state.team_setup.candidate_pool,
            provider=current_state.team_setup.provider,
            image_provider=current_state.team_setup.image_provider,
        ),
        mission=MissionState(
            genre=definition.genre or current_state.team_setup.genre,
            theme_family="compiled",
            mission_type=(definition.runtime_profiles[0] if definition.runtime_profiles else "compiled_runtime"),
            title=definition.title,
            objective=objective,
            environment_type=definition.locations[0].type if definition.locations else "compiled_location",
            threat_type=first_clock.label if first_clock else "pressione narrativa",
            tone=definition.tone or definition.genre_profile.tone,
            twist="",
            mission_target=max(1, len(definition.objectives)),
            max_turns=first_clock.max_value if first_clock else 999,
        ),
        phase=PhaseState(
            phase_index=1,
            max_phases=max(1, min(5, len(definition.locations))),
            phase_name="Runtime",
            zone_type=definition.locations[0].type if definition.locations else "zona iniziale",
            zone_goal=objective,
            zone_tags=["compiled_runtime"],
            is_final_phase=False,
        ),
        scene=SceneState(
            scene_text=hook,
            scene_problem=objective,
            scene_resolution="Avanzare nel canovaccio compilato tramite indizi, luoghi, PNG e condizioni finali.",
            objective_progress=0,
            objective_target=max(1, len(definition.objectives)),
            threat_level=first_clock.value if first_clock else 0,
            time_left=first_clock.max_value if first_clock else 0,
            time_limit=first_clock.max_value if first_clock else 0,
            scene_tags=["compiled_runtime"],
        ),
        story=story,
        map_state=map_state,
        world_npcs=world_npcs,
        players=build_players_from_dicts(selected_candidates),
        mission_memory=[],
        selected_actions={},
        adventure_definition_id=definition.id,
        adventure_definition=definition,
        adventure_runtime_state=runtime_state,
        current_objective_ids=list(runtime_state.active_objective_ids),
        active_revelation_ids=list(runtime_state.active_revelation_ids),
        active_clock_ids=list(runtime_state.clock_runtime.keys()),
        active_pressure_ids=list(runtime_state.pressure_runtime.keys()),
        allowed_escalation_types=list(definition.genre_profile.allowed_escalations),
        forbidden_escalation_types=list(definition.genre_profile.forbidden_escalations),
        director_reason="compiled_runtime_start",
    )
    refresh_scene_state(game, claude_scene_actions=None)
    return game


def _extract_canon_locations(canon: dict) -> list[str]:
    """Estrae fino a 2 nomi di luogo dal canon, in ordine di priorità.
    Priorità: key_items[kind=luogo] e key_entities[kind=luogo], poi
    frasi 'nel/nella/al/alla/sul/sulla X' nella win_condition."""
    found: list[str] = []

    def _add(name: str):
        clean = (name or "").strip().strip(".,;:«»\"'()[]")
        if clean and len(clean) >= 4 and clean not in found:
            found.append(clean)

    for card in (canon.get("key_entities", []) or []):
        if isinstance(card, dict) and str(card.get("kind", "")).lower() == "luogo":
            _add(card.get("name", ""))
    for card in (canon.get("key_items", []) or []):
        if isinstance(card, dict) and str(card.get("kind", "")).lower() == "luogo":
            _add(card.get("name", ""))

    win = canon.get("win_condition", "") or ""
    # Estrazione di frasi "nel/nella/al/alla/all'/sul/sulla X" — match capture frase fino a virgola/punto/preposizione
    for match in re.finditer(
        r"\b(?:nel|nella|nello|nei|negli|nelle|al|allo|alla|all'|ai|agli|alle|sul|sulla|sullo|sui|sugli|sulle|in|a)\s+([A-Za-zÀ-ÿ][\wÀ-ÿ' \-]{3,40}?)(?=\s+(?:e|per|prima|dopo|durante|con|senza|che|chi|dove|quando|del|della|degli|dei|dalle|alla|verso)\b|[.,;:]|$)",
        win,
        flags=re.IGNORECASE,
    ):
        candidate = match.group(1).strip()
        # Scarta verbi/parole vuote tipiche
        if any(candidate.lower().startswith(skip) for skip in ("squadra", "missione", "obiettivo", "soluzione", "verità", "lettera ", "diario ")):
            continue
        _add(candidate)

    return found[:2]


def append_unique(target: list[str], values: list[str]) -> None:
    for value in values:
        clean = str(value).strip()
        if clean and clean not in target:
            target.append(clean)


def _is_duplicate_fact(new_fact: str, existing: list[str], threshold: float = 0.55) -> bool:
    """True if new_fact is semantically too close to any existing fact."""
    new_lower = new_fact.lower()
    new_words = set(w for w in new_lower.split() if len(w) > 3)
    for old in existing:
        old_lower = old.lower()
        # Substring containment
        if new_lower in old_lower or old_lower in new_lower:
            return True
        # Word-overlap ratio
        if len(new_words) > 2:
            old_words = set(w for w in old_lower.split() if len(w) > 3)
            if old_words:
                overlap = len(new_words & old_words) / min(len(new_words), len(old_words))
                if overlap >= threshold:
                    return True
    return False


def append_unique_facts(target: list[str], values: list[str], cap: int = 14) -> None:
    """Append facts with semantic deduplication and a hard cap."""
    for value in values:
        clean = str(value).strip()
        if not clean:
            continue
        if clean in target:
            continue
        if _is_duplicate_fact(clean, target):
            continue
        if len(target) >= cap:
            break
        target.append(clean)


def _advance_thread_progress(state: GameState, story_hints: list[str]) -> str | None:
    """Avanza il thread_progress del thread più pertinente quando arrivano scoperte.
    Ritorna il testo del thread avanzato (o None)."""
    if not state.story or not state.story.active_threads:
        return None
    discovery_hints = {
        "scoperta_cruciale", "verita_rivelata", "codice_decifrato",
        "fatto_scoperto", "accordo_vantaggioso", "inganno_perfetto",
        "indizio_parziale", "posizione_rilevata",
    }
    hints_set = set(story_hints or [])
    if not hints_set & discovery_hints:
        return None

    # Peso: scoperta_cruciale/verita_rivelata avanzano di 2, gli altri di 1
    advance = 2 if hints_set & {"scoperta_cruciale", "verita_rivelata", "codice_decifrato", "accordo_vantaggioso", "inganno_perfetto"} else 1

    # Scegli il thread con meno progresso (il più lontano dalla risoluzione = priorità più alta)
    prog = state.story.thread_progress
    # Inizializza thread mancanti
    for t in state.story.active_threads:
        if t not in prog:
            prog[t] = 0
    target_thread = min(state.story.active_threads, key=lambda t: prog.get(t, 0))
    prog[target_thread] = min(3, prog.get(target_thread, 0) + advance)
    return target_thread


MAX_ACTIVE_THREADS = 3


def _shortest_path_next_step(map_state, from_id: str, to_id: str) -> str | None:
    """BFS sul grafo dei nodi. Ritorna il prossimo nodo lungo il cammino, o None."""
    if not map_state or from_id == to_id or from_id not in map_state.nodes or to_id not in map_state.nodes:
        return None
    visited = {from_id}
    queue: list[tuple[str, list[str]]] = [(from_id, [])]
    while queue:
        current, path = queue.pop(0)
        node = map_state.nodes.get(current)
        if not node:
            continue
        for nxt in node.connections:
            if nxt in visited:
                continue
            target = map_state.nodes.get(nxt)
            if not target or target.destroyed:
                continue
            new_path = path + [nxt]
            if nxt == to_id:
                return new_path[0] if new_path else None
            visited.add(nxt)
            queue.append((nxt, new_path))
    return None


def move_world_npcs(state: GameState, scene_transition: str) -> list[str]:
    """Sposta gli NPC persistenti in base al loro ruolo e all'esito della scena.
    Modifica state.world_npcs in-place. Ritorna lista di note testuali per il log."""
    if not state.world_npcs or not state.map_state:
        return []
    notes: list[str] = []
    party_node = state.map_state.current_node_id
    objective_node = state.map_state.objective_node_id

    for npc in state.world_npcs:
        if npc.status in {"dead", "missing"}:
            continue

        # Modulazione probabilità in base all'esito
        antagonist_chance = 0.5
        ally_chance = 0.3
        witness_disappear = 0.3
        witness_move = 0.3
        neutral_move = 0.2
        if scene_transition == "crisis":
            antagonist_chance += 0.3
            witness_disappear += 0.2
        elif scene_transition == "timeout":
            antagonist_chance += 0.15
            witness_disappear += 0.1
        elif scene_transition == "success":
            witness_disappear -= 0.15

        if npc.role == "antagonista":
            if random.random() < antagonist_chance:
                step = _shortest_path_next_step(state.map_state, npc.current_node_id, objective_node)
                if step and step != npc.current_node_id:
                    old = state.map_state.nodes[npc.current_node_id].name
                    npc.current_node_id = step
                    new_name = state.map_state.nodes[step].name
                    notes.append(f"{npc.name} ({npc.role}) si è spostato da {old} verso {new_name}")
        elif npc.role == "alleato":
            if random.random() < ally_chance:
                step = _shortest_path_next_step(state.map_state, npc.current_node_id, party_node)
                if step and step != npc.current_node_id:
                    old = state.map_state.nodes[npc.current_node_id].name
                    npc.current_node_id = step
                    new_name = state.map_state.nodes[step].name
                    notes.append(f"{npc.name} (alleato) si è avvicinato: ora a {new_name}")
        elif npc.role == "testimone":
            r = random.random()
            if r < witness_disappear:
                npc.status = "missing"
                notes.append(f"{npc.name} (testimone) è SCOMPARSO da {state.map_state.nodes[npc.current_node_id].name}")
            elif r < witness_disappear + witness_move:
                connections = state.map_state.nodes[npc.current_node_id].connections
                viable = [c for c in connections if c in state.map_state.nodes and not state.map_state.nodes[c].destroyed]
                if viable:
                    new_id = random.choice(viable)
                    old = state.map_state.nodes[npc.current_node_id].name
                    npc.current_node_id = new_id
                    notes.append(f"{npc.name} (testimone) si è spostato da {old} a {state.map_state.nodes[new_id].name}")
        elif npc.role == "neutrale":
            if random.random() < neutral_move:
                connections = state.map_state.nodes[npc.current_node_id].connections
                viable = [c for c in connections if c in state.map_state.nodes and not state.map_state.nodes[c].destroyed]
                if viable:
                    new_id = random.choice(viable)
                    old = state.map_state.nodes[npc.current_node_id].name
                    npc.current_node_id = new_id
                    notes.append(f"{npc.name} si è spostato da {old} a {state.map_state.nodes[new_id].name}")

    return notes


# Effect_type considerati "dialogici/investigativi": un'azione di questi tipi contro un NPC
# che detiene la chiave di un thread può estrarre un indizio extra (clue bonus).
_NPC_CLUE_EFFECT_TYPES = {"negoziare", "investigare", "rilevare", "ingannare", "decifrare"}


def collect_npc_clue_bonuses(state: GameState, effect_type: str, outcome: str, player_name: str) -> list[dict]:
    """Se l'azione del giocatore è dialogico/investigativa, l'outcome non è fallimento,
    e nella zona corrente ci sono NPC vivi e non ancora consultati con holds_clue_for valido,
    ritorna una lista di fatti bonus da iniettare in discovered_facts.

    Ogni NPC consultato viene marcato (consulted=True) per non triggerare il bonus due volte.
    Una sola consultazione per chiamata: il primo NPC pertinente viene scelto, gli altri restano.
    """
    if not state.world_npcs or not state.map_state or not state.story:
        return []
    if effect_type not in _NPC_CLUE_EFFECT_TYPES:
        return []
    if outcome == "fallimento":
        return []

    current_node_id = state.map_state.current_node_id
    # Costruisci set thread ancora attivi (non risolti)
    active_thread_ids = {t.id for t in state.story.threads if t.status != "resolved"}

    for npc in state.world_npcs:
        if npc.consulted or npc.status not in {"alive", "hidden"}:
            continue
        if npc.current_node_id != current_node_id:
            continue
        if not npc.holds_clue_for or npc.holds_clue_for not in active_thread_ids:
            continue
        # Match: l'NPC è qui, vivo, non consultato, detiene la chiave di un thread attivo.
        npc.consulted = True
        clue_text = (
            f"{npc.name} fornisce un indizio rilevante a {player_name}: "
            f"frammento utile a chiarire il thread {npc.holds_clue_for}."
        )
        state.story.event_log.append(
            f"[NPC clue bonus] {npc.name} (in {state.map_state.nodes[current_node_id].name}) "
            f"contribuisce al thread {npc.holds_clue_for} via azione '{effect_type}' di {player_name}"
        )
        return [{"text": clue_text, "clue_for_thread": npc.holds_clue_for}]
    return []


def _find_thread_by_id(state: GameState, tid: str):
    if not state.story:
        return None
    for t in state.story.threads:
        if t.id == tid:
            return t
    return None


def _find_thread_by_question(state: GameState, question: str):
    if not state.story:
        return None
    q = question.strip().lower()
    for t in state.story.threads:
        tq = t.question.strip().lower()
        if tq == q or tq in q or q in tq:
            return t
    return None


def _normalize_discovered_facts(raw_facts) -> list[dict]:
    """Normalizza discovered_facts in [{text, clue_for_thread}]. Accetta sia lista di stringhe che di dict."""
    out: list[dict] = []
    if not isinstance(raw_facts, list):
        return out
    for item in raw_facts:
        if isinstance(item, dict):
            text = str(item.get("text", "") or "").strip()
            tid = str(item.get("clue_for_thread", "") or "").strip()
            if text:
                out.append({"text": text, "clue_for_thread": tid})
        elif isinstance(item, str):
            text = item.strip()
            if text:
                out.append({"text": text, "clue_for_thread": ""})
    return out


def _apply_thread_resolution_effect(state: GameState, thread) -> None:
    """Applica l'on_resolve_effect di un thread che si sta chiudendo."""
    if not state.story:
        return
    effect = thread.on_resolve_effect or {}
    etype = (effect.get("type") or "").strip().lower()
    payload = (effect.get("payload") or "").strip()
    if not etype:
        return
    log = state.story.event_log

    if etype == "unlock_node":
        if not state.map_state:
            log.append(f"[effetto thread {thread.id}] unlock_node: map_state assente")
            return
        target_key = payload.lower()
        for node in state.map_state.nodes.values():
            if node.blocked and (target_key in node.name.lower() or node.id.lower() in target_key):
                node.blocked = False
                log.append(f"[effetto thread {thread.id}] sbloccato nodo: {node.name}")
                return
        log.append(f"[effetto thread {thread.id}] unlock_node senza match: {payload}")
    elif etype == "remove_blocker":
        if not state.map_state:
            log.append(f"[effetto thread {thread.id}] remove_blocker: map_state assente")
            return
        # Rimuove un edge bloccato/locked che corrisponde a payload
        target_key = payload.lower()
        for edge in state.map_state.connections_meta.values():
            if edge.status in {"locked", "trap"} and (target_key in edge.label.lower() or target_key in edge.note.lower() or not target_key):
                edge.status = "open"
                log.append(f"[effetto thread {thread.id}] rimosso blocco su edge {edge.from_id}->{edge.to_id}")
                return
        log.append(f"[effetto thread {thread.id}] remove_blocker senza match: {payload}")
    elif etype == "spawn_child_thread":
        # Retrocompatibilita: i vecchi salvataggi possono contenere questo effetto,
        # ma il canovaccio ora e chiuso. Non generiamo piu thread a runtime.
        if payload:
            log.append(f"[effetto thread {thread.id}] thread figlio ignorato (canovaccio chiuso): {payload}")
        else:
            log.append(f"[effetto thread {thread.id}] thread figlio ignorato (canovaccio chiuso)")
    elif etype == "modify_objective" and state.mission:
        # Aggiunge un suffisso all'obiettivo (non sostituisce per non perdere il canon)
        if payload and payload not in state.mission.objective:
            state.mission.objective = f"{state.mission.objective} — {payload}"
            log.append(f"[effetto thread {thread.id}] obiettivo specificato: {payload}")
    elif etype == "add_action":
        # L'effetto narrativo "azione disponibile" viene comunicato a Claude via event_log;
        # le scene future vedranno questa nota nel CONTESTO.
        log.append(f"[effetto thread {thread.id}] nuova azione disponibile: {payload}")
    else:
        log.append(f"[effetto thread {thread.id}] tipo non riconosciuto: {etype}")


def _resolve_thread(state: GameState, thread, deduction_text: str = "") -> None:
    """Marca un thread come resolved, applica l'effetto, sincronizza active_threads e resolved_threads."""
    if not state.story or thread.status == "resolved":
        return
    # Verifica parent: se ci sono parent non risolti, passa solo a 'ready' (non chiude)
    if thread.parent_thread_ids:
        for pid in thread.parent_thread_ids:
            parent = _find_thread_by_id(state, pid)
            if parent and parent.status != "resolved":
                if thread.status not in {"ready", "ready_to_deduce"}:
                    thread.status = "ready_to_deduce"
                state.story.event_log.append(f"[thread {thread.id}] in attesa di parent {pid}")
                return
    thread.status = "resolved"
    thread.revealed = True
    if deduction_text:
        thread.resolution_text = deduction_text
    # Sincronizza active_threads (vista legacy)
    if thread.question in state.story.active_threads:
        state.story.active_threads.remove(thread.question)
    # Aggiungi a resolved_threads
    label = f"{thread.question} → {deduction_text}" if deduction_text else thread.question
    if label not in state.story.resolved_threads:
        state.story.resolved_threads.append(label)
    state.story.thread_progress.pop(thread.question, None)
    state.story.event_log.append(f"[thread risolto] {thread.id}: {thread.question}")
    _apply_thread_resolution_effect(state, thread)
    # Cascata: thread ready che dipendevano da questo possono ora chiudersi
    for other in state.story.threads:
        if other.status == "ready" and thread.id in other.parent_thread_ids:
            _resolve_thread(state, other, other.resolution_text)


def apply_story_updates(state: GameState, updates: dict, *, outcome: str = "successo pieno") -> None:
    """Apply narrator-proposed story updates, gated by the action outcome.

    The ``outcome`` parameter carries the GURPS roll result for the action
    that produced these updates (one of "critico", "successo pieno",
    "successo parziale", "fallimento", "fallimento critico"). The gate
    enforces PbtA-style consequences:

    - successo critico / successo pieno
        Both ``clues_found`` (full discovery) and ``clue_progress``
        (partial progress) are accepted as proposed by the narrator.
    - successo parziale
        Full discoveries are *demoted* to partial progress — the players
        learn something useful but the clue does not close yet.
    - fallimento / fallimento critico
        No clue advancement at all. ``clues_found`` and ``clue_progress``
        are dropped; ``discovered_facts`` entries that link to a thread
        are stripped. The narrator can still produce a cost, just not
        progress.

    Default ``outcome="successo pieno"`` keeps backward compatibility for
    any caller that doesn't pass a roll result.
    """
    if not state.story:
        return

    outcome_low = (outcome or "").strip().lower()
    is_failure = "fallimento" in outcome_low
    is_partial = (not is_failure) and ("parziale" in outcome_low or "stretta misura" in outcome_low)

    if is_failure:
        updates = dict(updates)
        dropped_found = updates.get("clues_found") or []
        dropped_progress = updates.get("clue_progress") or []
        if dropped_found or dropped_progress:
            print(
                f"[apply_story_updates] outcome={outcome!r}: scartati "
                f"{len(dropped_found)} clues_found, {len(dropped_progress)} clue_progress"
            )
        updates["clues_found"] = []
        updates["clue_progress"] = []
        filtered_facts: list = []
        for fact in updates.get("discovered_facts") or []:
            if isinstance(fact, dict) and fact.get("clue_for_thread"):
                continue
            filtered_facts.append(fact)
        updates["discovered_facts"] = filtered_facts
    elif is_partial:
        updates = dict(updates)
        demoted: list[dict] = []
        for cid in updates.get("clues_found") or []:
            demoted.append({
                "clue_id": str(cid),
                "note": "scoperta parziale (successo di stretta misura)",
            })
        if demoted:
            updates["clue_progress"] = list(updates.get("clue_progress") or []) + demoted
            updates["clues_found"] = []
            print(
                f"[apply_story_updates] outcome={outcome!r}: "
                f"demoted {len(demoted)} clues_found → clue_progress"
            )

    def _required_count(thread: StoryThread) -> int:
        required = thread.required_clues
        if isinstance(required, list):
            return max(1, min(3, len(required) or thread.minimum_clues_to_deduce or 1))
        return max(1, int(required or thread.minimum_clues_to_deduce or 1))

    valid_thread_ids = {t.id for t in state.story.threads}
    canonical_clues = {c.id: c for c in getattr(state.story, "canonical_clues", [])}
    valid_clue_ids = {
        cid for cid, clue in canonical_clues.items()
        if not getattr(clue, "thread_id", "") or clue.thread_id in valid_thread_ids
    }

    # ── 0. Aggiornamenti canonici espliciti: clues_found / clue_progress ──
    for cid in updates.get("clues_found", []) or []:
        cid = str(cid)
        if valid_clue_ids and cid not in valid_clue_ids:
            continue
        clue = canonical_clues.get(cid)
        tid = clue.thread_id if clue else ""
        thread = _find_thread_by_id(state, tid) if tid else None
        if clue:
            clue.is_discovered = True
            fact = clue.reveals or clue.label or cid
            append_unique_facts(state.story.discovered_facts, [fact])
        if thread and thread.status != "resolved":
            thread.revealed = True
            if cid not in thread.collected_clue_ids:
                thread.collected_clue_ids.append(cid)
            if len(thread.collected_clue_ids) >= _required_count(thread) and thread.status in {"hidden", "active"}:
                thread.status = "ready_to_deduce"
                state.story.event_log.append(f"[thread {thread.id}] READY_TO_DEDUCE ({len(thread.collected_clue_ids)}/{_required_count(thread)} indizi)")

    for progress in updates.get("clue_progress", []) or []:
        if not isinstance(progress, dict):
            continue
        cid = str(progress.get("clue_id") or progress.get("id") or "")
        if valid_clue_ids and cid not in valid_clue_ids:
            continue
        clue = canonical_clues.get(cid)
        tid = clue.thread_id if clue else ""
        thread = _find_thread_by_id(state, tid) if tid else None
        if thread and cid not in thread.partial_clues and cid not in thread.collected_clue_ids:
            thread.partial_clues.append(cid)
            thread.revealed = True
            if thread.status == "hidden":
                thread.status = "active"
        note = str(progress.get("note") or "").strip()
        if note:
            state.story.event_log.append(f"Progresso indizio {cid}: {note}")

    # ── 1. discovered_facts: normalizza, salva nel canon, aggancia clue ai thread ──
    facts = _normalize_discovered_facts(updates.get("discovered_facts", []))
    new_fact_texts = [f["text"] for f in facts]
    append_unique_facts(state.story.discovered_facts, new_fact_texts)
    for f in facts:
        tid = f["clue_for_thread"]
        if not tid:
            continue
        thread = _find_thread_by_id(state, tid)
        if not thread or thread.status == "resolved":
            continue
        thread.revealed = True
        clue_id = f["text"][:80]  # usiamo il testo (truncato) come id univoco
        if clue_id not in thread.collected_clue_ids:
            thread.collected_clue_ids.append(clue_id)
        # Soglia raggiunta → ready (la chiusura effettiva avviene quando Claude la narra,
        # oppure forziamo la chiusura nel ciclo successivo se il modello non lo fa)
        if len(thread.collected_clue_ids) >= _required_count(thread) and thread.status in {"hidden", "active"}:
            thread.status = "ready_to_deduce"
            state.story.event_log.append(f"[thread {thread.id}] READY_TO_DEDUCE ({len(thread.collected_clue_ids)}/{_required_count(thread)} indizi)")

    append_unique(state.story.destroyed_elements, updates.get("destroyed_elements", []))
    append_unique(state.story.removed_clues, updates.get("removed_clues", []))

    # ── 2. resolved_threads: prova prima a matchare un thread strutturato ──
    for resolved_label in updates.get("resolved_threads", []):
        if not isinstance(resolved_label, str):
            continue
        question, _, deduction = resolved_label.partition("→")
        question = question.strip()
        deduction = deduction.strip()
        thread = _find_thread_by_question(state, question)
        if thread and thread.status != "resolved":
            _resolve_thread(state, thread, deduction)
            continue
        # Nessun match strutturato: fallback al vecchio sistema (active_threads sciolti)
        if resolved_label not in state.story.resolved_threads:
            state.story.resolved_threads.append(resolved_label)
        if resolved_label in state.story.active_threads:
            state.story.active_threads.remove(resolved_label)
        elif question in state.story.active_threads:
            state.story.active_threads.remove(question)
        else:
            for t in state.story.active_threads[:]:
                if t in question or question in t:
                    state.story.active_threads.remove(t)
                    break
        state.story.thread_progress.pop(resolved_label, None)
        state.story.thread_progress.pop(question, None)

    # ── 3. Auto-close: se Claude non ha narrato la chiusura ma il thread è ready, forziamo ──
    for t in list(state.story.threads):
        if t.status in {"ready", "ready_to_deduce"}:
            # Solo se i parent sono già risolti — altrimenti resta ready in attesa
            parents_ok = all(
                (_find_thread_by_id(state, pid) and _find_thread_by_id(state, pid).status == "resolved")
                for pid in t.parent_thread_ids
            )
            # Auto-close dopo che è stato ready per due aggiornamenti consecutivi
            ready_age_key = f"_ready_age_{t.id}"
            age = state.story.thread_progress.get(ready_age_key, 0) + 1
            state.story.thread_progress[ready_age_key] = age
            if parents_ok and age >= 2:
                _resolve_thread(state, t, "deduzione automatica dai fatti raccolti")

    # ── 4. Canovaccio chiuso: ignora new_threads generati a runtime ──
    ignored_new_threads = [
        str(t).strip()
        for t in updates.get("new_threads", [])
        if isinstance(t, str) and str(t).strip()
    ]

    # Hard cap di sicurezza per vecchi salvataggi o dati legacy
    if len(state.story.active_threads) > MAX_ACTIVE_THREADS:
        state.story.active_threads = state.story.active_threads[-MAX_ACTIVE_THREADS:]
    for t in state.story.active_threads:
        if t not in state.story.thread_progress:
            state.story.thread_progress[t] = 0

    # ── 5. Event log ──
    if new_fact_texts:
        state.story.event_log.extend([f"Fatto scoperto: {x}" for x in new_fact_texts])
    if updates.get("destroyed_elements"):
        state.story.event_log.extend([f"Elemento distrutto: {x}" for x in updates["destroyed_elements"]])
    if ignored_new_threads:
        state.story.event_log.extend([f"Thread ignorato (canovaccio chiuso): {x}" for x in ignored_new_threads])

    # ── 6. Accessi/location dal runtime compiler ──
    if state.map_state and updates.get("location_access"):
        for raw in updates.get("location_access") or []:
            if isinstance(raw, dict):
                target = str(raw.get("id") or raw.get("node_id") or raw.get("location_id") or raw.get("name") or "").lower()
            else:
                target = str(raw).lower()
            if not target:
                continue
            for node in state.map_state.nodes.values():
                if target in node.id.lower() or target in node.name.lower() or node.id.lower() in target or node.name.lower() in target:
                    node.blocked = False
                    node.destroyed = False
                    state.story.event_log.append(f"Accesso sbloccato: {node.name}")
            for edge in state.map_state.connections_meta.values():
                if edge.status in {"locked", "hidden", "blocked"} and (
                    target in edge.from_id.lower() or target in edge.to_id.lower()
                    or target in edge.label.lower() or target in edge.note.lower()
                ):
                    edge.status = "open"
                    edge.discovered = True


def get_accessible_connections(state: GameState) -> list[str]:
    if not state.map_state or not state.phase:
        return []
    current = state.map_state.nodes[state.map_state.current_node_id]
    allowed = []
    for nid in current.connections:
        node = state.map_state.nodes.get(nid)
        if not node or node.destroyed or node.blocked:
            continue
        edge = state.map_state.connections_meta.get(_edge_key(current.id, nid))
        if edge:
            if edge.status in {"locked", "hidden"}:
                continue
            if edge.status == "one_way" and edge.from_id != current.id:
                continue
        if node.phase_gate > state.phase.phase_index:
            continue
        allowed.append(nid)
    return allowed


def move_to_best_next_node(state: GameState, scene_transition: str) -> None:
    if not state.map_state:
        return
    candidates = []
    for nid in get_accessible_connections(state):
        node = state.map_state.nodes[nid]
        score = 0
        if not node.visited:
            score += 3
        if node.is_objective:
            score += 4
        if node.is_final and state.phase and state.phase.is_final_phase:
            score += 5
        if node.contains_clue:
            score += 1
        if scene_transition == "timeout":
            score -= 1
        candidates.append((score, nid))
    if not candidates:
        return
    candidates.sort(key=lambda x: x[0], reverse=True)
    next_id = candidates[0][1]
    state.map_state.current_node_id = next_id
    state.map_state.nodes[next_id].visited = True


def apply_map_persistence_from_effects(state: GameState, effect_types: list[str], scene_transition: str) -> list[str]:
    if not state.map_state or not state.map_state.connections_meta:
        return []
    if scene_transition not in {"success", "continue"}:
        return []
    current = state.map_state.nodes.get(state.map_state.current_node_id)
    if not current:
        return []
    notes: list[str] = []
    effects = set(effect_types)
    for nid in current.connections:
        edge = state.map_state.connections_meta.get(_edge_key(current.id, nid))
        if not edge:
            continue
        target = state.map_state.nodes.get(nid)
        target_name = target.name if target else nid
        if edge.status == "hidden" and effects & {"investigare", "rilevare", "decifrare"}:
            edge.discovered = True
            edge.status = "open"
            notes.append(f"passaggio rivelato verso {target_name}")
        elif edge.status == "locked" and effects & {"forzare", "decifrare"}:
            edge.status = "open"
            edge.discovered = True
            notes.append(f"accesso aperto verso {target_name}")
        elif edge.status == "trap" and effects & {"rilevare", "investigare"}:
            edge.note = "La trappola è stata riconosciuta: attraversarla resta possibile, ma non è più una sorpresa."
            notes.append(f"trappola identificata su {target_name}")
    return notes


def start_game_from_selection(current_state: GameState, selected_player_ids: list[int], custom_names: dict[int, str] | None = None, adventure_bible: dict | None = None) -> GameState:
    if adventure_bible and adventure_bible.get("adventure_definition"):
        return start_compiled_game_from_selection(current_state, selected_player_ids, custom_names, adventure_bible)
    raise ValueError(
        "Avvio legacy rimosso: start_game_from_selection richiede adventure_bible.adventure_definition. "
        "Genera o importa l'avventura tramite compiler prima della selezione squadra."
    )


def threat_penalty(threat: int) -> int:
    if threat >= 8:
        return 2
    if threat >= 5:
        return 1
    return 0


SKILL_EFFECT_PROFILES: dict[str, dict[str, dict]] = {
    # Forza
    "combattere": {
        "critico": {"progress": 4, "threat": -2, "self_damage": 0, "heal": 0, "story_hint": "colpo_decisivo"},
        "full": {"progress": 3, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "nemico_respinto"},
        "partial": {"progress": 1, "threat": -1, "self_damage": 2, "heal": 0, "story_hint": "scambio_violento"},
        "fail": {"progress": 0, "threat": 2, "self_damage": 3, "heal": 0, "story_hint": "contrattacco_subito"},
    },
    "resistere": {
        "critico": {"progress": 2, "threat": -3, "self_damage": 0, "heal": 0, "story_hint": "tenuta_eroica"},
        "full": {"progress": 1, "threat": -2, "self_damage": 0, "heal": 0, "story_hint": "posizione_tenuta"},
        "partial": {"progress": 0, "threat": -1, "self_damage": 1, "heal": 0, "story_hint": "resistenza_costosa"},
        "fail": {"progress": 0, "threat": 1, "self_damage": 2, "heal": 0, "story_hint": "linea_ceduta"},
    },
    "forzare": {
        "critico": {"progress": 5, "threat": 0, "self_damage": 0, "heal": 0, "story_hint": "varco_aperto_di_netto"},
        "full": {"progress": 4, "threat": 1, "self_damage": 0, "heal": 0, "story_hint": "ostacolo_superato_con_rumore"},
        "partial": {"progress": 2, "threat": 2, "self_damage": 0, "heal": 0, "story_hint": "apertura_instabile"},
        "fail": {"progress": 0, "threat": 3, "self_damage": 1, "heal": 0, "story_hint": "forzatura_fallita"},
    },
    "proteggere": {
        "critico": {"progress": 2, "threat": -3, "self_damage": 0, "heal": 0, "story_hint": "protezione_perfetta"},
        "full": {"progress": 1, "threat": -2, "self_damage": 0, "heal": 0, "story_hint": "alleati_coperti"},
        "partial": {"progress": 0, "threat": -1, "self_damage": 1, "heal": 0, "story_hint": "copertura_parziale"},
        "fail": {"progress": 0, "threat": 0, "self_damage": 2, "heal": 0, "story_hint": "protezione_travolta"},
    },
    "trasportare": {
        "critico": {"progress": 4, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "carico_estratto"},
        "full": {"progress": 3, "threat": 0, "self_damage": 0, "heal": 0, "story_hint": "spostamento_riuscito"},
        "partial": {"progress": 1, "threat": 1, "self_damage": 1, "heal": 0, "story_hint": "trasporto_faticoso"},
        "fail": {"progress": 0, "threat": 2, "self_damage": 1, "heal": 0, "story_hint": "carico_bloccato"},
    },
    "intimidire": {
        "critico": {"progress": 4, "threat": -2, "self_damage": 0, "heal": 0, "story_hint": "volonta_spezzata"},
        "full": {"progress": 3, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "pressione_riuscita"},
        "partial": {"progress": 1, "threat": 1, "self_damage": 0, "heal": 0, "story_hint": "sfida_aperta"},
        "fail": {"progress": 0, "threat": 2, "self_damage": 0, "heal": 0, "story_hint": "minaccia_ribaltata"},
    },
    "lottare": {
        "critico": {"progress": 4, "threat": -2, "self_damage": 0, "heal": 0, "story_hint": "bersaglio_immobilizzato"},
        "full": {"progress": 3, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "presa_salda"},
        "partial": {"progress": 1, "threat": 0, "self_damage": 2, "heal": 0, "story_hint": "presa_contesa"},
        "fail": {"progress": 0, "threat": 2, "self_damage": 3, "heal": 0, "story_hint": "presa_rotta"},
    },
    "sopravvivere": {
        "critico": {"progress": 3, "threat": -2, "self_damage": 0, "heal": 1, "story_hint": "adattamento_perfetto"},
        "full": {"progress": 2, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "risorse_trovate"},
        "partial": {"progress": 1, "threat": 0, "self_damage": 1, "heal": 0, "story_hint": "sopravvivenza_precaria"},
        "fail": {"progress": 0, "threat": 1, "self_damage": 2, "heal": 0, "story_hint": "ambiente_ostile"},
    },
    # Agilita
    "schivare": {
        "critico": {"progress": 3, "threat": -2, "self_damage": 0, "heal": 0, "story_hint": "pericolo_evitato"},
        "full": {"progress": 2, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "schivata_pulita"},
        "partial": {"progress": 1, "threat": 0, "self_damage": 1, "heal": 0, "story_hint": "evitato_di_poco"},
        "fail": {"progress": 0, "threat": 1, "self_damage": 2, "heal": 0, "story_hint": "colpo_subito"},
    },
    "furtivita": {
        "critico": {"progress": 5, "threat": -2, "self_damage": 0, "heal": 0, "story_hint": "ombra_perfetta"},
        "full": {"progress": 4, "threat": 0, "self_damage": 0, "heal": 0, "story_hint": "passaggio_silenzioso"},
        "partial": {"progress": 2, "threat": 2, "self_damage": 0, "heal": 0, "story_hint": "quasi_scoperto"},
        "fail": {"progress": 0, "threat": 4, "self_damage": 0, "heal": 0, "story_hint": "allarme_scattato"},
    },
    "acrobazia": {
        "critico": {"progress": 4, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "manovra_spettacolare"},
        "full": {"progress": 3, "threat": 0, "self_damage": 0, "heal": 0, "story_hint": "ostacolo_superato"},
        "partial": {"progress": 1, "threat": 1, "self_damage": 1, "heal": 0, "story_hint": "atterraggio_duro"},
        "fail": {"progress": 0, "threat": 2, "self_damage": 2, "heal": 0, "story_hint": "caduta_pericolosa"},
    },
    "rapidita": {
        "critico": {"progress": 4, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "iniziativa_totale"},
        "full": {"progress": 3, "threat": 0, "self_damage": 0, "heal": 0, "story_hint": "tempo_guadagnato"},
        "partial": {"progress": 1, "threat": 1, "self_damage": 0, "heal": 0, "story_hint": "azione_affrettata"},
        "fail": {"progress": 0, "threat": 2, "self_damage": 0, "heal": 0, "story_hint": "ritardo_critico"},
    },
    "mira": {
        "critico": {"progress": 4, "threat": -3, "self_damage": 0, "heal": 0, "story_hint": "colpo_perfetto"},
        "full": {"progress": 3, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "bersaglio_colpito"},
        "partial": {"progress": 1, "threat": 0, "self_damage": 1, "heal": 0, "story_hint": "colpo_di_copertura"},
        "fail": {"progress": 0, "threat": 2, "self_damage": 0, "heal": 0, "story_hint": "munizioni_sprecate"},
    },
    "guidare": {
        "critico": {"progress": 5, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "manovra_impossibile"},
        "full": {"progress": 4, "threat": 0, "self_damage": 0, "heal": 0, "story_hint": "rotta_tenuta"},
        "partial": {"progress": 2, "threat": 2, "self_damage": 1, "heal": 0, "story_hint": "sbandata_controllata"},
        "fail": {"progress": 0, "threat": 3, "self_damage": 2, "heal": 0, "story_hint": "impatto_o_blocco"},
    },
    "manualita": {
        "critico": {"progress": 4, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "meccanismo_domato"},
        "full": {"progress": 3, "threat": 0, "self_damage": 0, "heal": 0, "story_hint": "manovra_precisa"},
        "partial": {"progress": 1, "threat": 1, "self_damage": 0, "heal": 0, "story_hint": "lavoro_imperfetto"},
        "fail": {"progress": 0, "threat": 2, "self_damage": 0, "heal": 0, "story_hint": "meccanismo_compromesso"},
    },
    "infiltrarsi": {
        "critico": {"progress": 5, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "accesso_invisibile"},
        "full": {"progress": 4, "threat": 0, "self_damage": 0, "heal": 0, "story_hint": "perimetro_superato"},
        "partial": {"progress": 2, "threat": 2, "self_damage": 0, "heal": 0, "story_hint": "traccia_lasciata"},
        "fail": {"progress": 0, "threat": 4, "self_damage": 1, "heal": 0, "story_hint": "intrusione_scoperta"},
    },
    # Intelligenza
    "investigare": {
        "critico": {"progress": 4, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "scoperta_cruciale"},
        "full": {"progress": 3, "threat": 0, "self_damage": 0, "heal": 0, "story_hint": "fatto_scoperto"},
        "partial": {"progress": 1, "threat": 0, "self_damage": 0, "heal": 0, "story_hint": "indizio_parziale"},
        "fail": {"progress": 0, "threat": 1, "self_damage": 0, "heal": 0, "story_hint": "falsa_pista"},
    },
    "analizzare": {
        "critico": {"progress": 4, "threat": -2, "self_damage": 0, "heal": 0, "story_hint": "schema_compreso"},
        "full": {"progress": 3, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "dato_interpretato"},
        "partial": {"progress": 1, "threat": 0, "self_damage": 0, "heal": 0, "story_hint": "ipotesi_incompleta"},
        "fail": {"progress": 0, "threat": 1, "self_damage": 0, "heal": 0, "story_hint": "analisi_errata"},
    },
    "tecnologia": {
        "critico": {"progress": 5, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "sistema_piegato"},
        "full": {"progress": 4, "threat": 0, "self_damage": 0, "heal": 0, "story_hint": "accesso_tecnico"},
        "partial": {"progress": 2, "threat": 2, "self_damage": 0, "heal": 0, "story_hint": "bypass_instabile"},
        "fail": {"progress": 0, "threat": 3, "self_damage": 0, "heal": 0, "story_hint": "sistema_in_allarme"},
    },
    "medicina": {
        "critico": {"progress": 1, "threat": -1, "self_damage": 0, "heal": 2, "story_hint": "diagnosi_salvifica"},
        "full": {"progress": 0, "threat": 0, "self_damage": 0, "heal": 2, "story_hint": "cura_effettiva"},
        "partial": {"progress": 0, "threat": 0, "self_damage": 0, "heal": 1, "story_hint": "cura_precaria"},
        "fail": {"progress": 0, "threat": 1, "self_damage": 0, "heal": 0, "story_hint": "complicazione_medica"},
    },
    "cultura": {
        "critico": {"progress": 4, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "contesto_rivelatore"},
        "full": {"progress": 3, "threat": 0, "self_damage": 0, "heal": 0, "story_hint": "riferimento_compreso"},
        "partial": {"progress": 1, "threat": 0, "self_damage": 0, "heal": 0, "story_hint": "sapere_frammentario"},
        "fail": {"progress": 0, "threat": 0, "self_damage": 0, "heal": 0, "story_hint": "memoria_insufficiente"},
    },
    "strategia": {
        "critico": {"progress": 3, "threat": -3, "self_damage": 0, "heal": 0, "story_hint": "piano_superiore"},
        "full": {"progress": 2, "threat": -2, "self_damage": 0, "heal": 0, "story_hint": "vantaggio_tattico"},
        "partial": {"progress": 1, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "piano_adattato"},
        "fail": {"progress": 0, "threat": 2, "self_damage": 0, "heal": 0, "story_hint": "piano_letto_dal_nemico"},
    },
    "decifrare": {
        "critico": {"progress": 4, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "verita_rivelata"},
        "full": {"progress": 3, "threat": 0, "self_damage": 0, "heal": 0, "story_hint": "codice_decifrato"},
        "partial": {"progress": 1, "threat": 0, "self_damage": 0, "heal": 0, "story_hint": "messaggio_parziale"},
        "fail": {"progress": 0, "threat": 0, "self_damage": 0, "heal": 0, "story_hint": "segno_incomprensibile"},
    },
    "osservare": {
        "critico": {"progress": 4, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "dettaglio_decisivo"},
        "full": {"progress": 3, "threat": 0, "self_damage": 0, "heal": 0, "story_hint": "traccia_notata"},
        "partial": {"progress": 1, "threat": 1, "self_damage": 0, "heal": 0, "story_hint": "notato_ma_esposto"},
        "fail": {"progress": 0, "threat": 2, "self_damage": 0, "heal": 0, "story_hint": "dettaglio_mancato"},
    },
    # Empatia
    "persuadere": {
        "critico": {"progress": 4, "threat": -2, "self_damage": 0, "heal": 0, "story_hint": "accordo_vantaggioso"},
        "full": {"progress": 3, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "consenso_ottenuto"},
        "partial": {"progress": 1, "threat": 0, "self_damage": 0, "heal": 0, "story_hint": "compromesso_fragile"},
        "fail": {"progress": 0, "threat": 2, "self_damage": 0, "heal": 0, "story_hint": "rifiuto_netto"},
    },
    "ingannare": {
        "critico": {"progress": 5, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "inganno_perfetto"},
        "full": {"progress": 4, "threat": 0, "self_damage": 0, "heal": 0, "story_hint": "menzogna_regge"},
        "partial": {"progress": 2, "threat": 2, "self_damage": 0, "heal": 0, "story_hint": "sospetto_acceso"},
        "fail": {"progress": 0, "threat": 4, "self_damage": 0, "heal": 0, "story_hint": "inganno_scoperto"},
    },
    "intuire": {
        "critico": {"progress": 4, "threat": -2, "self_damage": 0, "heal": 0, "story_hint": "intenzione_smascherata"},
        "full": {"progress": 3, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "emozione_letta"},
        "partial": {"progress": 1, "threat": 0, "self_damage": 0, "heal": 0, "story_hint": "sensazione_ambigua"},
        "fail": {"progress": 0, "threat": 1, "self_damage": 0, "heal": 0, "story_hint": "lettura_sbagliata"},
    },
    "calmare": {
        "critico": {"progress": 2, "threat": -3, "self_damage": 0, "heal": 1, "story_hint": "panico_spento"},
        "full": {"progress": 1, "threat": -2, "self_damage": 0, "heal": 0, "story_hint": "tensione_calata"},
        "partial": {"progress": 0, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "calma_precaria"},
        "fail": {"progress": 0, "threat": 1, "self_damage": 0, "heal": 0, "story_hint": "panico_contagioso"},
    },
    "ispirare": {
        "critico": {"progress": 3, "threat": -2, "self_damage": 0, "heal": 1, "story_hint": "coraggio_ritrovato"},
        "full": {"progress": 2, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "morale_alto"},
        "partial": {"progress": 1, "threat": 0, "self_damage": 0, "heal": 0, "story_hint": "incoraggiamento_fragile"},
        "fail": {"progress": 0, "threat": 1, "self_damage": 0, "heal": 0, "story_hint": "parole_vuote"},
    },
    "curare": {
        "critico": {"progress": 1, "threat": -1, "self_damage": 0, "heal": 2, "story_hint": "soccorso_perfetto"},
        "full": {"progress": 0, "threat": 0, "self_damage": 0, "heal": 1, "story_hint": "ferita_stabilizzata"},
        "partial": {"progress": 0, "threat": 0, "self_damage": 0, "heal": 1, "story_hint": "soccorso_precario"},
        "fail": {"progress": 0, "threat": 1, "self_damage": 0, "heal": 0, "story_hint": "soccorso_fallito"},
    },
    "comandare": {
        "critico": {"progress": 3, "threat": -3, "self_damage": 0, "heal": 0, "story_hint": "ordine_perfetto"},
        "full": {"progress": 2, "threat": -2, "self_damage": 0, "heal": 0, "story_hint": "squadra_coordinata"},
        "partial": {"progress": 1, "threat": 0, "self_damage": 0, "heal": 0, "story_hint": "ordine_confuso"},
        "fail": {"progress": 0, "threat": 2, "self_damage": 0, "heal": 0, "story_hint": "comando_ignorato"},
    },
    "comunicare": {
        "critico": {"progress": 4, "threat": -2, "self_damage": 0, "heal": 0, "story_hint": "messaggio_decisivo"},
        "full": {"progress": 3, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "canale_aperto"},
        "partial": {"progress": 1, "threat": 1, "self_damage": 0, "heal": 0, "story_hint": "messaggio_distorto"},
        "fail": {"progress": 0, "threat": 2, "self_damage": 0, "heal": 0, "story_hint": "comunicazione_intercettata"},
    },
}


def apply_effect(effect_type: str, total: int, difficulty: int, action_role: str = "core", skill: str | None = None) -> dict:
    """Restituisce un dict con: progress, threat, self_damage, heal, time_bonus, story_hint.

    `total` è il *margine* GURPS Lite (abilità effettiva − tiro 3d6).
    Positivo = successo, negativo = fallimento. Più alto = effetto migliore.

    action_role modifica l'effetto base:
      core    → effetto standard
      support → dimezza il progresso, potenzia la riduzione minaccia, recupera tempo al successo
      risk    → raddoppia il progresso al critico / +50% al pieno, aggrava il fallimento
    """
    # Soglie sul margine GURPS: ≥10 critico, ≥5 pieno, ≥0 parziale, <0 fail
    if total >= 10:
        tier = "critico"
    elif total >= 5:
        tier = "full"
    elif total >= 0:
        tier = "partial"
    else:
        tier = "fail"

    s = 1 + (difficulty // 2)  # scala difficoltà

    skill_key = skill if skill in SKILL_EFFECT_PROFILES else LEGACY_EFFECT_TO_SKILL.get(effect_type, "")
    if skill_key in SKILL_EFFECT_PROFILES:
        result = dict(SKILL_EFFECT_PROFILES[skill_key][tier])
        result["progress"] *= s
        result["time_bonus"] = 0
        result["skill"] = skill_key
        result["effect_type"] = SKILL_TO_EFFECT_TYPE.get(skill_key, effect_type)
        return _apply_action_role_modifiers(result, total, action_role)

    PROFILES: dict[str, dict] = {
        # ── INFORMAZIONE ────────────────────────────────────────────
        # Basso rischio, produce conoscenza e progresso moderato
        "investigare": {
            "critico":  {"progress": 3*s, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "scoperta_cruciale"},
            "full":     {"progress": 2*s, "threat":  0, "self_damage": 0, "heal": 0, "story_hint": "fatto_scoperto"},
            "partial":  {"progress": 1*s, "threat":  0, "self_damage": 0, "heal": 0, "story_hint": "indizio_parziale"},
            "fail":     {"progress":   0, "threat":  1, "self_damage": 0, "heal": 0, "story_hint": "vicolo_cieco"},
        },
        "rilevare": {
            # Più veloce dell'indagine ma ti espone al fallimento
            "critico":  {"progress": 3*s, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "area_mappata_completamente"},
            "full":     {"progress": 2*s, "threat":  0, "self_damage": 0, "heal": 0, "story_hint": "posizione_rilevata"},
            "partial":  {"progress": 1*s, "threat":  1, "self_damage": 0, "heal": 0, "story_hint": "rilevato_ma_esposto"},
            "fail":     {"progress":   0, "threat":  2, "self_damage": 0, "heal": 0, "story_hint": "scoperto_durante_ricognizione"},
        },
        "decifrare": {
            # Lento ma sblocca verità narrative — non aumenta la minaccia nemmeno al fallimento
            "critico":  {"progress": 2*s, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "verita_rivelata"},
            "full":     {"progress": 2*s, "threat":  0, "self_damage": 0, "heal": 0, "story_hint": "codice_decifrato"},
            "partial":  {"progress": 1*s, "threat":  0, "self_damage": 0, "heal": 0, "story_hint": "decifrato_parzialmente"},
            "fail":     {"progress":   0, "threat":  0, "self_damage": 0, "heal": 0, "story_hint": "testo_incomprensibile"},
        },
        # ── FISICO ──────────────────────────────────────────────────
        # Alto progresso, rischi diversi per tipo
        "forzare": {
            # Lascia tracce, fa rumore — progresso alto ma la minaccia può salire
            "critico":  {"progress": 4*s, "threat":  0, "self_damage": 0, "heal": 0, "story_hint": "varco_aperto_di_netto"},
            "full":     {"progress": 3*s, "threat":  1, "self_damage": 0, "heal": 0, "story_hint": "varco_aperto_con_rumore"},
            "partial":  {"progress": 2*s, "threat":  1, "self_damage": 0, "heal": 0, "story_hint": "passaggio_parziale"},
            "fail":     {"progress":   0, "threat":  2, "self_damage": 0, "heal": 0, "story_hint": "tentativo_fallito_allarme"},
        },
        "combattere": {
            # Riduce la minaccia; al parziale/fallimento HP damage narrativo (scambio di colpi)
            "critico":  {"progress": 3*s, "threat": -2, "self_damage": 0, "heal": 0, "story_hint": "nemico_abbattuto"},
            "full":     {"progress": 2*s, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "nemico_respinto"},
            "partial":  {"progress": 1*s, "threat": -1, "self_damage": 2, "heal": 0, "story_hint": "scambio_ferite"},
            "fail":     {"progress":   0, "threat":  1, "self_damage": 3, "heal": 0, "story_hint": "sconfitta_con_ferita"},
        },
        "infiltrarsi": {
            # Progresso silenzioso al successo, ma al fallimento la minaccia esplode
            "critico":  {"progress": 4*s, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "passaggio_invisibile"},
            "full":     {"progress": 3*s, "threat":  0, "self_damage": 0, "heal": 0, "story_hint": "avanzata_silenziosa"},
            "partial":  {"progress": 1*s, "threat":  2, "self_damage": 0, "heal": 0, "story_hint": "quasi_scoperto"},
            "fail":     {"progress":   0, "threat":  3, "self_damage": 0, "heal": 0, "story_hint": "infiltrazione_scoperta"},
        },
        # ── SUPPORTO ────────────────────────────────────────────────
        # Non produce molto progresso, ma mantiene il gruppo operativo
        "difendere": {
            "critico":  {"progress": 1*s, "threat": -2, "self_damage": 0, "heal": 0, "story_hint": "difesa_impenetrabile"},
            "full":     {"progress": 1*s, "threat": -2, "self_damage": 0, "heal": 0, "story_hint": "difesa_solida"},
            "partial":  {"progress":   0, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "difesa_parziale"},
            "fail":     {"progress":   0, "threat":  0, "self_damage": 0, "heal": 0, "story_hint": "difesa_ceduta"},
        },
        "stabilizzare": {
            # Cura ferite fisiche — unico tipo che produce guarigione diretta
            "critico":  {"progress": 0, "threat": -1, "self_damage": 0, "heal": 2, "story_hint": "guarigione_completa"},
            "full":     {"progress": 0, "threat":  0, "self_damage": 0, "heal": 1, "story_hint": "paziente_stabilizzato"},
            "partial":  {"progress": 0, "threat":  0, "self_damage": 0, "heal": 1, "story_hint": "stabilizzato_precariamente"},
            "fail":     {"progress": 0, "threat":  1, "self_damage": 0, "heal": 0, "story_hint": "stabilizzazione_fallita"},
        },
        "recuperare": {
            # Ripristina risorse/morale — progresso lieve, nessun rischio fisico
            "critico":  {"progress": 2*s, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "pieno_recupero_risorse"},
            "full":     {"progress": 1*s, "threat":  0, "self_damage": 0, "heal": 0, "story_hint": "risorsa_recuperata"},
            "partial":  {"progress": 1*s, "threat":  0, "self_damage": 0, "heal": 0, "story_hint": "recupero_parziale"},
            "fail":     {"progress":   0, "threat":  1, "self_damage": 0, "heal": 0, "story_hint": "recupero_fallito"},
        },
        # ── SOCIALE ─────────────────────────────────────────────────
        # Varianza alta — ingannare può dare molto o costare tutto
        "negoziare": {
            "critico":  {"progress": 3*s, "threat": -2, "self_damage": 0, "heal": 0, "story_hint": "accordo_vantaggioso"},
            "full":     {"progress": 2*s, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "negoziato_riuscito"},
            "partial":  {"progress": 1*s, "threat":  0, "self_damage": 0, "heal": 0, "story_hint": "accordo_precario"},
            "fail":     {"progress":   0, "threat":  1, "self_damage": 0, "heal": 0, "story_hint": "negoziato_rotto"},
        },
        "ingannare": {
            # Alto guadagno al critico, disastro se scoperto
            "critico":  {"progress": 4*s, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "inganno_perfetto"},
            "full":     {"progress": 3*s, "threat":  0, "self_damage": 0, "heal": 0, "story_hint": "inganno_riuscito"},
            "partial":  {"progress": 1*s, "threat":  2, "self_damage": 0, "heal": 0, "story_hint": "inganno_sospettato"},
            "fail":     {"progress":   0, "threat":  3, "self_damage": 0, "heal": 0, "story_hint": "inganno_scoperto"},
        },
        "evocare": {
            # Massima varianza — al parziale/fallimento danno HP da sovraccarico
            "critico":  {"progress": 4*s, "threat": -2, "self_damage": 0, "heal": 0, "story_hint": "evocazione_potente"},
            "full":     {"progress": 3*s, "threat": -1, "self_damage": 0, "heal": 0, "story_hint": "evocazione_riuscita"},
            "partial":  {"progress": 1*s, "threat":  2, "self_damage": 2, "heal": 0, "story_hint": "evocazione_instabile"},
            "fail":     {"progress":   0, "threat":  3, "self_damage": 4, "heal": 0, "story_hint": "evocazione_incontrollata"},
        },
    }

    # Compatibilità con i vecchi nomi
    LEGACY: dict[str, str] = {
        "analysis": "investigare", "scan": "rilevare",
        "breach": "forzare",       "defense": "difendere",
        "move": "infiltrarsi",     "stabilize": "stabilizzare",
        "diplomacy": "negoziare",  "generic": "forzare",
    }
    key = LEGACY.get(effect_type, effect_type)
    profile = PROFILES.get(key, PROFILES["investigare"])
    result = dict(profile[tier])
    result["time_bonus"] = 0
    result["skill"] = skill or LEGACY_EFFECT_TO_SKILL.get(key, key)
    result["effect_type"] = key

    return _apply_action_role_modifiers(result, total, action_role)


def _apply_action_role_modifiers(result: dict, total: int, action_role: str) -> dict:
    if action_role == "support":
        # SUP: progresso pieno + riduzione minaccia potenziata + recupero tempo
        # Non dimezza il progresso — il personaggio contribuisce normalmente
        # ma il suo punto di forza è abbassare la minaccia e comprare tempo
        result["threat"] = result["threat"] - 2          # -2 extra threat (era -1)
        result["self_damage"] = 0                         # nessun danno a sé stessi
        if total >= 11:                                   # critico
            result["time_bonus"] = 2
        elif total >= 9:                                  # pieno
            result["time_bonus"] = 1

    elif action_role == "risk":
        # RISK: upside enorme, downside con danno fisico diretto al personaggio agente
        if total >= 11:                                   # critico — grande ricompensa
            result["progress"] = round(result["progress"] * 2.5)
        elif total >= 9:                                  # pieno
            result["progress"] = round(result["progress"] * 1.5)
        elif total >= 6:                                  # parziale — minaccia + danno
            result["threat"] = result["threat"] + 1
            result["self_damage"] = max(result.get("self_damage", 0), 1)
        else:                                             # fallimento — minaccia pesante + danno grave
            result["threat"] = result["threat"] + 2
            result["self_damage"] = max(result.get("self_damage", 0), 2)

    return result


def status_penalty(status: str) -> int:
    if status == "fuori_combattimento":
        return 99
    if status == "ferito_grave":
        return 2
    if status == "ferito":
        return 1
    return 0


def format_action_effect(effect: dict) -> str:
    parts: list[str] = []
    p, t = effect["progress"], effect["threat"]
    parts.append(f"progresso {'+' if p >= 0 else ''}{p}")
    parts.append(f"minaccia {'+' if t >= 0 else ''}{t}")
    if effect["self_damage"] > 0:
        parts.append(f"danno HP: -{effect['self_damage']}")
    if effect["heal"] > 0:
        parts.append(f"guarigione: {effect['heal']}")
    parts.append(f"[{effect['story_hint']}]")
    return ", ".join(parts)


def explain_self_damage(skill: str, story_hint: str, scene_tags: list[str], damage: int) -> str:
    tags = {t.lower() for t in scene_tags}
    if "veleno" in tags or "gas" in tags or "nebbia" in tags:
        return f"respira la sostanza tossica mentre forza la manovra (-{damage} HP)."
    if "fuoco" in tags or "incendio" in tags:
        return f"si brucia attraversando il pericolo (-{damage} HP)."
    if "trappola" in tags:
        return f"innesca di striscio una trappola nascosta (-{damage} HP)."
    if "combattimento" in tags or "attacco" in tags or skill in {"combattere", "mira", "lottare"}:
        return f"viene colpito nel contrattacco o da schegge della mischia (-{damage} HP)."
    if skill in {"schivare", "acrobazia", "rapidita", "guidare"}:
        return f"evita il peggio ma cade male e si contunde (-{damage} HP)."
    if skill in {"furtivita", "infiltrarsi"}:
        return f"si graffia e urta contro l'ambiente mentre resta nascosto (-{damage} HP)."
    if skill in {"forzare", "manualita", "tecnologia"}:
        return f"subisce un ritorno di forza, scintille o schegge durante il tentativo (-{damage} HP)."
    if skill in {"medicina", "curare"}:
        return f"si espone troppo nel soccorso e paga il costo fisico (-{damage} HP)."
    if "evitato_di_poco" in story_hint:
        return f"evita il pericolo per un soffio, ma ne porta il segno (-{damage} HP)."
    return f"subisce una conseguenza fisica coerente con '{story_hint}' (-{damage} HP)."


def inflict_damage(players: list[Player], hp_per_target: int, num_targets: int = 1) -> None:
    if hp_per_target <= 0:
        return
    candidates = [p for p in players if p.hp > 0]
    random.shuffle(candidates)
    for p in candidates[:num_targets]:
        p.hp = max(0, p.hp - hp_per_target)
        p.status = hp_to_status(p.hp, p.max_hp)


def mission_should_fail(state: GameState) -> tuple[bool, str]:
    ko_count = sum(1 for p in state.players if p.hp <= 0)
    if ko_count >= max(1, len(state.players) - 1):
        return True, "Troppi membri della squadra sono fuori combattimento."
    return False, ""


def update_phase(state: GameState) -> None:
    progress = state.mission.mission_progress
    phase_index = 1 if progress == 0 else 2 if progress < max(2, state.mission.mission_target) else 3
    phase_cfg = get_phase_blueprint(phase_index, state.mission.environment_type, state.mission.mission_type)
    state.phase = PhaseState(**phase_cfg)


_ENTITY_STOPWORDS = {"di", "del", "della", "delle", "degli", "dei", "da", "dal", "dallo", "la", "il", "lo", "le", "gli", "un", "una", "uno"}
_DEDUP_ANCHORS = {"carovana", "convoglio", "nave", "navetta", "shuttle", "drone", "terminale", "foresta", "bosco", "nido", "stazione", "culto", "creatura"}


def _entity_tokens(name: str) -> set[str]:
    return {tok for tok in re.findall(r"[a-zA-Zàèéìòù]+", name.lower()) if tok not in _ENTITY_STOPWORDS}


def _same_scene_entity(left: str, right: str) -> bool:
    left_tokens = _entity_tokens(left)
    right_tokens = _entity_tokens(right)
    if not left_tokens or not right_tokens:
        return left.lower() == right.lower()
    overlap = left_tokens & right_tokens
    if left_tokens <= right_tokens or right_tokens <= left_tokens:
        return True
    if overlap & _DEDUP_ANCHORS:
        return True
    return len(overlap) >= 2


def _append_scene_entity(entities: list[SceneEntity], entity: SceneEntity) -> None:
    if any(existing.id == entity.id or _same_scene_entity(existing.name, entity.name) for existing in entities):
        return
    entities.append(entity)


def _cover_entity_for_scene(scene_text: str, environment_type: str) -> SceneEntity:
    text = f"{scene_text} {environment_type}".lower()
    if any(word in text for word in ["foresta", "alberi", "radici", "vegetazione", "bosco"]):
        return SceneEntity(id="cover", name="Radici e tronchi", type="obstacle", zone="copertura", tags=["copertura", "ambiente", "foresta"])
    if any(word in text for word in ["hangar", "casse", "condotti", "cargo"]):
        return SceneEntity(id="cover", name="Casse e condotti", type="obstacle", zone="copertura", tags=["copertura", "ambiente", "meccanico"])
    if any(word in text for word in ["rovine", "muro", "colonne", "pietre"]):
        return SceneEntity(id="cover", name="Muri e pietre", type="obstacle", zone="copertura", tags=["copertura", "ambiente", "rovine"])
    return SceneEntity(id="cover", name="", type="obstacle", zone="copertura", tags=["copertura", "ambiente"], interactable=False)


def _is_concrete_threat_name(name: str) -> bool:
    lname = name.lower()
    abstract_words = ["ambiente", "ostile", "planetario", "clima", "metamorfosi", "radiazione", "pressione", "instabilità", "anomalia"]
    concrete_words = ["drone", "soldat", "cult", "creatura", "mostro", "ombra", "predator", "nemic", "guardia", "bestia", "sciame"]
    return any(word in lname for word in concrete_words) and not any(word in lname for word in abstract_words[:3])


def _entity_is_contextual(name: str, scene_text: str, mission_objective: str) -> bool:
    lname = name.lower()
    context = f"{scene_text} {mission_objective}".lower()
    tokens = _entity_tokens(lname)
    if not tokens:
        return False
    if lname in context:
        return True
    return bool(tokens & _DEDUP_ANCHORS) and any(tok in context for tok in tokens)


def _add_narrative_scene_entities(state: GameState, entities: list[SceneEntity]) -> None:
    text = (state.scene.scene_text if state.scene else "").lower()
    env = (state.mission.environment_type if state.mission else "").lower()
    combined = f"{text} {env}"

    if any(word in combined for word in ["foresta", "alberi", "radici", "vegetazione", "bosco"]):
        name = "Foresta aliena" if any(word in combined for word in ["aliena", "simbion", "biologic", "spore"]) else "Foresta"
        _append_scene_entity(entities, SceneEntity(
            id="scene_forest",
            name=name,
            type="location",
            zone="ambiente",
            tags=["foresta", "ambiente", "biologico"],
        ))

    if any(word in combined for word in ["suono", "richiamo", "eco", "vibra", "sibilo", "segnale"]):
        _append_scene_entity(entities, SceneEntity(
            id="scene_sound",
            name="Richiamo tra gli alberi" if "alber" in combined else "Segnale anomalo",
            type="phenomenon",
            zone="ambiente",
            tags=["suono", "indizio", "anomalia"],
        ))

    if any(word in combined for word in ["drone", "sorvola", "sorveglianza"]):
        _append_scene_entity(entities, SceneEntity(
            id="scene_drone",
            name="Drone in sorvolo",
            type="enemy",
            zone="minaccia",
            hp=2,
            tags=["drone", "sorveglianza", "tecnologia"],
        ))

    if any(word in combined for word in ["terminale", "schermo", "dati biometrici", "comunicazioni", "scanner"]):
        _append_scene_entity(entities, SceneEntity(
            id="scene_terminal",
            name="Terminale dati",
            type="object",
            zone="centro",
            tags=["tecnologia", "analisi", "indizio"],
        ))

    if any(word in combined for word in ["shuttle", "navetta", "zona di atterraggio", "atterraggio"]):
        _append_scene_entity(entities, SceneEntity(
            id="scene_shuttle",
            name="Shuttle / navetta",
            type="object",
            zone="accesso",
            tags=["accesso", "veicolo", "estrazione"],
        ))

    if any(word in combined for word in ["massa organica", "gelatinosa", "membrane trasparenti", "traslucido e pulsante"]):
        _append_scene_entity(entities, SceneEntity(
            id="scene_biomass",
            name="Massa organica",
            type="obstacle",
            zone="accesso",
            tags=["biologico", "ostacolo", "contaminazione"],
        ))

    if any(word in combined for word in ["portello", "rampa d'accesso", "ingresso bloccato"]):
        _append_scene_entity(entities, SceneEntity(
            id="scene_hatch",
            name="Portello sigillato",
            type="obstacle",
            zone="accesso",
            tags=["varco", "ostacolo", "accesso"],
        ))

    if any(word in combined for word in ["bioreattore", "bioreattori"]):
        _append_scene_entity(entities, SceneEntity(
            id="scene_bioreactor",
            name="Bioreattore contaminato",
            type="object",
            zone="centro",
            tags=["reattore", "obiettivo", "contaminazione"],
        ))

    if any(word in combined for word in ["conduttura", "condutture", "griglie di ventilazione", "fognario"]):
        _append_scene_entity(entities, SceneEntity(
            id="scene_pipeline",
            name="Conduttura critica",
            type="object",
            zone="ambiente",
            tags=["conduttura", "diffusione", "rischio"],
        ))

    if any(word in combined for word in ["capsula", "capsule di salvataggio", "imbarco"]):
        _append_scene_entity(entities, SceneEntity(
            id="scene_capsules",
            name="Capsule di salvataggio",
            type="object",
            zone="accesso",
            tags=["estrazione", "civili", "imbarco"],
        ))

    if any(word in combined for word in ["radio", "gracchia", "trasmissione", "canale", "richiamo"]):
        _append_scene_entity(entities, SceneEntity(
            id="scene_radio",
            name="Canale radio disturbato",
            type="phenomenon",
            zone="centro",
            tags=["comunicazione", "segnale", "indizio"],
        ))


def populate_scene_entities(state: GameState) -> None:
    if not state.scene:
        return
    entities: list[SceneEntity] = []
    tags = {t.lower() for t in state.scene.scene_tags}
    current_node = state.map_state.nodes.get(state.map_state.current_node_id) if state.map_state else None

    if current_node:
        _append_scene_entity(entities, SceneEntity(
            id=f"loc_{current_node.id}",
            name=current_node.name,
            type="location",
            zone="centro",
            tags=current_node.tags,
        ))

    if (current_node and current_node.contains_enemy) or tags & {"combattimento", "attacco", "scontro", "nemico"}:
        threat_name = state.mission.threat_type if state.mission else "Minaccia"
        if _is_concrete_threat_name(threat_name):
            _append_scene_entity(entities, SceneEntity(id="enemy_primary", name=threat_name.capitalize(), type="enemy", zone="minaccia", hp=2 + state.scene.threat_level // 4, tags=["nemico", "minaccia"]))

    scene_text = state.scene.scene_text if state.scene else ""
    mission_objective = state.mission.objective if state.mission else ""
    for idx, entity_name in enumerate((state.story.named_entities if state.story else [])[:4], start=1):
        lname = entity_name.lower()
        if not _entity_is_contextual(entity_name, scene_text, mission_objective):
            continue
        if any(existing.name == entity_name for existing in entities):
            continue
        if any(word in lname for word in ["cult", "nemic", "capo", "ombra", "mostro", "soldat", "minaccia"]):
            etype, zone, tags_out = "enemy", "minaccia", ["nemico"]
        elif any(word in lname for word in ["mira", "keilor", "dottoressa", "alleat", "creatura", "guida", "veggente", "ostaggio"]):
            etype, zone, tags_out = "ally", "centro", ["alleato", "npc"]
        elif any(word in lname for word in ["foresta", "bosco", "nido", "zona", "radura", "monolite"]):
            etype, zone, tags_out = "location", "ambiente", ["luogo", "ambiente"]
        else:
            etype, zone, tags_out = "npc", "centro", ["npc"]
        _append_scene_entity(entities, SceneEntity(id=f"entity_{idx}", name=entity_name, type=etype, zone=zone, tags=tags_out))

    _add_narrative_scene_entities(state, entities)
    cover_entity = _cover_entity_for_scene(state.scene.scene_text, state.mission.environment_type if state.mission else "")
    if cover_entity.name:
        _append_scene_entity(entities, cover_entity)
    state.scene.entities = entities[:7]


def refresh_scene_state(state: GameState, claude_scene_actions: list | None = None) -> None:
    if not state.scene:
        return
    populate_scene_entities(state)
    state.scene.challenge = SceneChallenge()
    current_node = state.map_state.nodes.get(state.map_state.current_node_id) if state.map_state else None
    state.scene.challenge = _build_scene_challenge(state, current_node, claude_scene_actions=claude_scene_actions)


def _tokenize_intent(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Zàèéìòù]+", text.lower()))


def _keyword_root(token: str) -> str:
    token = token.lower().strip(" '")
    if len(token) <= 3:
        return ""
    for suffix in ("azioni", "zione", "zioni", "mente"):
        if token.endswith(suffix) and len(token) > len(suffix) + 2:
            token = token[: -len(suffix)]
            break
    if token.endswith(("are", "ere", "ire")) and len(token) > 6:
        token = token[:-3]
    elif token.endswith(("ale", "ile", "ica", "ico")) and len(token) > 6:
        token = token[:-1]
    elif token.endswith(("i", "o", "a", "e")) and len(token) > 5:
        token = token[:-1]
    return token[:8]


def _scene_keyword_roots(text: str) -> set[str]:
    roots: set[str] = set()
    for token in _tokenize_intent(text):
        if token in _SCENE_KEYWORD_STOPWORDS:
            continue
        root = _keyword_root(token)
        if len(root) < 4 or root in _GENERIC_SCENE_KEYWORDS:
            continue
        roots.add(root)
    return roots


def _matching_scene_keywords(intent_tokens: set[str], scene_keywords: set[str]) -> list[str]:
    matches: list[str] = []
    for keyword in sorted(scene_keywords):
        if any(token.startswith(keyword) or keyword.startswith(token) for token in intent_tokens):
            matches.append(keyword)
    return matches


def _unique_preserve(items: list[str], limit: int = 6) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in items:
        item = str(raw or "").strip()
        if not item:
            continue
        low = item.lower()
        if low in seen:
            continue
        seen.add(low)
        out.append(item)
        if len(out) >= limit:
            break
    return out


def _join_terms(items: list[str], fallback: str) -> str:
    clean = _unique_preserve(items, limit=3)
    if not clean:
        return fallback
    if len(clean) == 1:
        return clean[0]
    if len(clean) == 2:
        return f"{clean[0]} e {clean[1]}"
    return f"{clean[0]}, {clean[1]} e {clean[2]}"


def _context_text(state: GameState, current_node: MapNode | None) -> str:
    chunks = [
        current_node.name if current_node else "",
        current_node.kind if current_node else "",
        current_node.description if current_node else "",
        state.scene.scene_text if state.scene else "",
        " ".join(state.scene.scene_tags) if state.scene else "",
        state.mission.objective if state.mission else "",
        state.phase.zone_goal if state.phase else "",
        " ".join(state.story.active_threads[:3]) if state.story else "",
    ]
    return " ".join(x for x in chunks if x).lower()


def _contains_any(text: str, fragments: tuple[str, ...]) -> bool:
    return any(fragment in text for fragment in fragments)


def _scene_display_terms(state: GameState, current_node: MapNode | None) -> list[str]:
    terms: list[str] = []
    if current_node:
        if current_node.contains_clue:
            terms.append("gli indizi della zona")
        if current_node.contains_enemy:
            terms.append("la minaccia presente")
        if current_node.contains_loot:
            terms.append("le risorse esposte")
    for entity in (state.scene.entities if state.scene else [])[:8]:
        if current_node and entity.name.lower() == current_node.name.lower():
            continue
        if entity.type in {"enemy", "npc", "ally", "object", "phenomenon"}:
            terms.append(entity.name)
    if current_node and len(terms) < 2:
        terms.append(current_node.name)
    return _unique_preserve(terms, limit=6)


def _scene_stakes_text(state: GameState, current_node: MapNode | None) -> str:
    scene = state.scene
    if not scene:
        return "la situazione degeneri"
    if scene.time_limit > 0 and scene.time_left <= 1:
        return "la finestra utile si chiuda del tutto"
    if scene.time_limit > 0 and scene.time_left <= 2:
        return "il tempo rimasto non basti piu"
    if scene.threat_level >= 8:
        return "la zona precipiti nel caos"
    if current_node and current_node.contains_enemy:
        return "la minaccia prenda il controllo della zona"
    if current_node and current_node.contains_clue:
        return "gli indizi vengano compromessi o dispersi"
    if current_node and current_node.contains_loot:
        return "l'elemento utile venga perso o distrutto"
    return "la pressione della scena salga oltre il controllo"


def _scene_summary_text(state: GameState, current_node: MapNode | None, display_terms: list[str], allowed_effect_types: set[str]) -> str:
    target = _join_terms(display_terms[:3], "la zona")
    if current_node and current_node.contains_enemy and current_node.contains_clue:
        return "Contenere la pressione della zona e capire quali elementi della scena contano davvero prima che la situazione travolga la squadra."
    if current_node and current_node.contains_enemy:
        return "Aprire spazio contro la minaccia presente e impedire che blocchi ogni avanzata."
    if current_node and current_node.contains_clue:
        return "Capire cosa rivelano gli elementi chiave della zona e trasformare la scoperta in un vantaggio concreto."
    if current_node and current_node.contains_loot:
        return "Recuperare o mettere al sicuro l'elemento utile della zona prima che vada perduto."
    if "decifrare" in allowed_effect_types:
        return "Interpretare gli elementi chiave della scena per trovare la leva giusta."
    if "forzare" in allowed_effect_types:
        return "Sbloccare o alterare l'ostacolo materiale della zona per cambiare l'equilibrio della scena."
    if "infiltrarsi" in allowed_effect_types:
        return f"Aggirare {target} e conquistare una posizione utile senza esporsi troppo."
    if "rilevare" in allowed_effect_types or "investigare" in allowed_effect_types:
        return "Leggere bene la scena e capire dove intervenire davvero."
    return f"Trovare il punto debole di {target} e usarlo prima che la scena peggiori."


def _scene_problem_context(state: GameState, current_node: MapNode | None) -> str:
    # Priorità 1: testo narrativo generato da Claude — massima coerenza con la scena.
    if state.scene and state.scene.scene_problem:
        resolution_hint = f" Risoluzione: {state.scene.scene_resolution}." if state.scene.scene_resolution else ""
        node_prefix = f"Zona attuale: {current_node.name}. " if current_node else ""
        return f"{node_prefix}{state.scene.scene_problem}{resolution_hint}"

    # Priorità 2: challenge summary derivata meccanicamente.
    if current_node:
        challenge = state.scene.challenge if state.scene else None
        if challenge and challenge.summary:
            stakes_txt = f" Rischio: {challenge.stakes}." if challenge.stakes else ""
            return f"Zona attuale: {current_node.name}. {challenge.summary}{stakes_txt}"
        local_pressure = []
        if current_node.contains_enemy:
            local_pressure.append("presenza ostile nella zona")
        if current_node.contains_clue:
            local_pressure.append("indizi da interpretare sul posto")
        if current_node.contains_loot:
            local_pressure.append("risorse utili da recuperare")
        pressure_txt = f" Pressioni locali: {', '.join(local_pressure)}." if local_pressure else ""
        return f"Zona attuale: {current_node.name}. {current_node.description}{pressure_txt}"

    if state.phase and state.phase.zone_goal:
        return state.phase.zone_goal
    return ""


def _scene_resolution_handles(
    state: GameState,
    current_node: MapNode | None,
    display_terms: list[str],
    allowed_effect_types: set[str],
) -> dict[str, str]:
    """
    Ritorna un dict {effect_type: prompt} con testi contestuali.
    Fonte primaria: scene_problem + scene_resolution generati da Claude.
    Fallback: named_entities della storia + nodo corrente.
    Le entità aggiunte da keyword (Shuttle, Segnale anomalo, ecc.) vengono ignorate.
    """
    scene_problem = (state.scene.scene_problem if state.scene else "").strip()
    scene_resolution = (state.scene.scene_resolution if state.scene else "").strip()

    # Estrai focus, agente e luogo dalle fonti affidabili (non da entità keyword)
    obstacle, agent, location = _extract_focus_from_problem(state, current_node)
    node_name = current_node.name if current_node else location

    # Se scene_resolution è disponibile, ogni effect_type adatta quella frase al proprio verbo.
    # Altrimenti costruisce dal focus/agent estratti dalla storia.
    if scene_resolution:
        # Usa scene_resolution come base e costruisce varianti per ogni tipo di azione
        handles: dict[str, str] = {
            "investigare": scene_resolution,
            "rilevare": f"leggere come si può {scene_resolution.lower().lstrip('r')}",
            "decifrare": f"capire il meccanismo dietro: {scene_resolution}",
            "forzare": scene_resolution if any(w in scene_resolution.lower() for w in ("apri", "forza", "sblocca", "rimuovi", "sfonda")) else f"forzare l'accesso per poi: {scene_resolution}",
            "combattere": f"neutralizzare chi blocca la via per: {scene_resolution}",
            "infiltrarsi": f"raggiungere la posizione giusta per: {scene_resolution}",
            "recuperare": scene_resolution if any(w in scene_resolution.lower() for w in ("estrai", "recupera", "porta", "metti in salvo")) else f"recuperare l'elemento necessario per: {scene_resolution}",
            "negoziare": f"convincere {agent} a permettere: {scene_resolution}",
            "difendere": f"proteggere la posizione abbastanza a lungo per: {scene_resolution}",
            "stabilizzare": f"stabilizzare la situazione per poter: {scene_resolution}",
            "ingannare": f"creare il margine per: {scene_resolution}",
            "evocare": f"attivare il fenomeno per: {scene_resolution}",
        }
    else:
        # Nessun scene_resolution da Claude: costruisce dal contesto della storia
        handles = {
            "investigare": f"esaminare {obstacle} per trovare come superarlo",
            "rilevare": f"leggere i movimenti di {agent} attorno a {obstacle}",
            "decifrare": f"capire come funziona {obstacle} e cosa serve per aprirlo",
            "forzare": f"rimuovere o aprire {obstacle} prima che la situazione peggiori",
            "combattere": f"neutralizzare {agent} che blocca l'accesso a {obstacle}",
            "infiltrarsi": f"aggirare {agent} e raggiungere {obstacle} senza essere visti",
            "recuperare": f"estrarre da {obstacle} ciò che serve prima che sia troppo tardi",
            "negoziare": f"convincere {agent} a cedere su {obstacle}",
            "difendere": f"tenere {node_name} abbastanza a lungo da aprire una finestra su {obstacle}",
            "stabilizzare": f"contenere il danno su {obstacle} finché la situazione non si sblocca",
            "ingannare": f"distogliere {agent} da {obstacle} per creare una copertura",
            "evocare": f"attivare il fenomeno su {obstacle} nel momento giusto",
        }
    return {k: v for k, v in handles.items() if k in allowed_effect_types}


def _preferred_effect_order(archetype: str) -> list[str]:
    preferred = {
        "accesso_sorvegliato": ["infiltrarsi", "ingannare", "rilevare", "decifrare", "forzare", "negoziare", "difendere"],
        "identificare_bersaglio": ["rilevare", "investigare", "decifrare", "negoziare", "ingannare", "difendere"],
        "negoziazione_tesa": ["negoziare", "rilevare", "ingannare", "investigare", "difendere", "stabilizzare"],
        "anomalia_da_decifrare": ["decifrare", "rilevare", "investigare", "stabilizzare", "forzare", "evocare"],
        "recupero_conteso": ["recuperare", "rilevare", "forzare", "infiltrarsi", "difendere"],
        "scorta_estrazione": ["negoziare", "difendere", "rilevare", "infiltrarsi", "recuperare", "stabilizzare"],
        "combattimento_bloccante": ["combattere", "difendere", "infiltrarsi", "forzare", "rilevare", "stabilizzare"],
        "pressione_locale": ["rilevare", "investigare", "decifrare", "forzare", "recuperare", "difendere", "stabilizzare"],
    }
    return preferred.get(archetype, preferred["pressione_locale"])


def _get_prompt_for_effect(effect_type: str, handles: dict[str, str], used_prompts: set[str], focus: str) -> str:
    """Recupera il prompt per un effect_type dal dict handles. Se già usato, genera variante con focus."""
    prompt = handles.get(effect_type, "")
    if prompt and prompt not in used_prompts:
        return prompt
    # Variante di fallback minimale che usa sempre il focus concreto
    fallbacks = {
        "investigare": f"esaminare {focus} in cerca dell'indizio decisivo",
        "rilevare": f"leggere le tracce attorno a {focus}",
        "decifrare": f"interpretare {focus} per sbloccare il passo successivo",
        "forzare": f"forzare l'accesso bloccato verso {focus}",
        "combattere": f"abbattere chi impedisce l'accesso a {focus}",
        "infiltrarsi": f"aggirare il blocco e raggiungere {focus}",
        "recuperare": f"estrarre {focus} prima che la situazione peggiori",
        "negoziare": f"trattare con chi controlla {focus}",
        "difendere": f"tenere {focus} abbastanza a lungo da creare un'apertura",
        "stabilizzare": f"contenere il danno attorno a {focus}",
        "ingannare": f"distogliere l'attenzione da {focus}",
        "evocare": f"attivare {focus} al momento giusto",
    }
    return fallbacks.get(effect_type, _EFFECT_TYPE_LABELS.get(effect_type, f"agire su {focus}"))


def _scene_focus_terms(state: GameState, current_node: MapNode | None) -> list[str]:
    terms: list[str] = []
    for entity in (state.scene.entities if state.scene else []):
        if entity.type in {"object", "obstacle", "phenomenon", "npc", "ally"}:
            terms.append(entity.name.lower())
    if current_node:
        terms.append(current_node.name.lower())
        terms.append(current_node.kind.lower())
        terms.append(current_node.description.lower())
    if state.scene:
        terms.append(state.scene.scene_text.lower())
    return terms


def _extract_focus_from_problem(state: GameState, current_node: MapNode | None) -> tuple[str, str, str]:
    """
    Estrae (ostacolo, agente, luogo) direttamente dal scene_problem generato da Claude.
    Queste sono le entità su cui costruire i prompt delle action card.
    Fallback su named_entities della storia, poi sul nodo corrente.
    """
    scene_problem = (state.scene.scene_problem if state.scene else "").strip()
    named = list(state.story.named_entities if state.story else [])
    node_name = current_node.name if current_node else ""
    mission_obj = (state.mission.objective if state.mission else "").strip()

    # Entità esplicite dalla storia (canoniche, affidabili)
    # Prima persona/NPC che appare nell'obiettivo o nel problema
    obstacle_entity = ""
    agent_entity = ""
    location_entity = node_name

    for e in named:
        el = e.lower()
        # NPC/persona se ha nome proprio (maiuscola, breve)
        if len(e.split()) <= 3 and e[0].isupper() and not any(w in el for w in ("livello", "settore", "zona", "pozzo", "camera", "deposito")):
            if not agent_entity and (el in scene_problem.lower() or el in mission_obj.lower()):
                agent_entity = e
        # Luogo/oggetto fisico
        elif any(w in el for w in ("livello", "settore", "zona", "pozzo", "camera", "deposito", "ponte", "corridoio", "laboratorio")):
            if not obstacle_entity and (el in scene_problem.lower() or el in mission_obj.lower()):
                obstacle_entity = e

    # Se scene_problem contiene il nodo corrente come ostacolo, usalo
    if not obstacle_entity and node_name and node_name.lower() in scene_problem.lower():
        obstacle_entity = node_name

    # Fallback: primo named entity disponibile
    if not obstacle_entity and named:
        obstacle_entity = named[0]
    if not agent_entity and len(named) > 1:
        agent_entity = named[1]

    obstacle_entity = obstacle_entity or node_name or "l'obiettivo"
    agent_entity = agent_entity or (state.mission.threat_type if state.mission else "") or "la minaccia"

    return obstacle_entity, agent_entity, location_entity


def _scene_primary_entity(state: GameState, current_node: MapNode | None) -> str:
    """Entità principale: priorità a named_entities della storia, poi enemy/obstacle della scena, poi nodo."""
    named = list(state.story.named_entities if state.story else [])
    scene_problem = (state.scene.scene_problem if state.scene else "").lower()
    mission_obj = (state.mission.objective if state.mission else "").lower()
    # Preferisci named entity che appare nell'obiettivo o nel problema (evita entità generiche)
    for e in named:
        el = e.lower()
        if el in scene_problem or el in mission_obj:
            return e
    # Fallback: enemy/obstacle della scena che NON sia aggiunto da keyword generiche
    if state.scene:
        for entity in state.scene.entities:
            if entity.type in {"enemy", "obstacle"} and entity.interactable and entity.id not in {"scene_shuttle", "scene_sound", "scene_forest", "cover"}:
                return entity.name
    return current_node.name if current_node else ""


def _scene_object_entity(state: GameState, current_node: MapNode | None) -> str:
    """Oggetto/fenomeno concreto: priorità al nodo corrente, poi entità rilevanti."""
    node_name = current_node.name if current_node else ""
    if state.scene:
        # Escludi entità aggiunte da keyword generiche non contestuali
        for entity in state.scene.entities:
            if entity.type in {"object", "obstacle", "phenomenon"} and entity.id not in {"scene_shuttle", "scene_sound", "scene_forest", "cover"}:
                return entity.name
    return node_name


def _scene_npc_entity(state: GameState, current_node: MapNode | None) -> str:
    """NPC/persona nominata: priorità a named_entities che appaiono nel contesto, poi entità npc della scena."""
    named = list(state.story.named_entities if state.story else [])
    scene_problem = (state.scene.scene_problem if state.scene else "").lower()
    mission_obj = (state.mission.objective if state.mission else "").lower()
    skip_generic = {"creatura", "minaccia", "nemico", "entità", "presenza"}
    for e in named:
        el = e.lower()
        if any(g in el for g in skip_generic):
            continue
        # È una persona se ha nome proprio corto e appare nel contesto operativo
        if len(e.split()) <= 3 and e[0].isupper() and (el in scene_problem or el in mission_obj):
            return e
    if state.scene:
        for entity in state.scene.entities:
            if entity.type in {"npc", "ally", "enemy"} and entity.id not in {"scene_shuttle", "scene_sound", "cover"}:
                if not any(g in entity.name.lower() for g in skip_generic):
                    return entity.name
    return ""


def _fiction_action_title(effect_type: str, _prompt: str, state: GameState, current_node: MapNode | None) -> str:
    node_name = (current_node.name if current_node else "").strip()
    node_kind = (current_node.kind if current_node else "").strip().lower()

    # Entità contestuali estratte dalla scena corrente — usate per titoli dinamici
    primary = _scene_primary_entity(state, current_node)
    obj = _scene_object_entity(state, current_node)
    npc = _scene_npc_entity(state, current_node)
    threat = (state.mission.threat_type if state.mission else "").strip()

    # Costruisci titoli dinamici basandosi sul contesto reale della scena
    # Ogni ramificazione usa il nome concreto dell'entità invece di un testo fisso
    if effect_type == "investigare":
        if obj:
            return f"Esaminare {obj}"
        if npc:
            return f"Interrogare {npc}"
        return f"Esaminare {node_name}" if node_name else "Cercare indizi"

    if effect_type == "rilevare":
        if obj:
            return f"Leggere {obj}"
        if primary:
            return f"Leggere i segnali di {primary}"
        return f"Leggere la zona" if not node_name else f"Leggere {node_name}"

    if effect_type == "decifrare":
        if obj:
            return f"Decifrare {obj}"
        if primary:
            return f"Interpretare {primary}"
        return "Decifrare il sistema"

    if effect_type == "forzare":
        if obj:
            return f"Forzare {obj}"
        if primary and primary != threat:
            return f"Aprire il varco verso {primary}"
        return "Forzare il blocco"

    if effect_type == "combattere":
        if primary:
            return f"Neutralizzare {primary}"
        if threat:
            return f"Spezzare {threat}"
        return "Eliminare la minaccia"

    if effect_type == "infiltrarsi":
        if npc:
            return f"Aggirare {npc}"
        if primary and primary != threat:
            return f"Passare oltre {primary}"
        if "corridoio" in node_kind or "condotto" in node_kind:
            return f"Scivolare per {node_name}" if node_name else "Passare dal condotto"
        return f"Infiltrarsi in {node_name}" if node_name else "Aggirare la sorveglianza"

    if effect_type == "negoziare":
        if npc:
            return f"Negoziare con {npc}"
        if primary and primary != threat:
            return f"Convincere {primary}"
        return "Ottenere margine"

    if effect_type == "ingannare":
        if npc:
            return f"Depistare {npc}"
        if primary and primary != threat:
            return f"Distogliere {primary}"
        return "Creare un diversivo"

    if effect_type == "recuperare":
        if obj:
            return f"Recuperare {obj}"
        if primary and primary != threat:
            return f"Mettere in salvo {primary}"
        return "Estrarre l'elemento chiave"

    if effect_type == "stabilizzare":
        if obj:
            return f"Stabilizzare {obj}"
        if primary:
            return f"Contenere {primary}"
        return "Stabilizzare la situazione"

    if effect_type == "difendere":
        if primary:
            return f"Proteggere {primary}"
        return f"Tenere {node_name}" if node_name else "Tenere la posizione"

    if effect_type == "evocare":
        if obj:
            return f"Attivare {obj}"
        if primary:
            return f"Evocare tramite {primary}"
        return "Attivare il fenomeno"

    return _EFFECT_TYPE_TITLES.get(effect_type, "Agire sulla zona")


def _scene_obstacle_text(
    archetype: str,
    current_node: MapNode | None,
    display_terms: list[str],
) -> str:
    target = _join_terms(display_terms[:2], current_node.name if current_node else "la zona")
    text = " ".join(
        x for x in [
            current_node.name if current_node else "",
            current_node.kind if current_node else "",
            current_node.description if current_node else "",
        ] if x
    ).lower()
    if archetype == "accesso_sorvegliato":
        return f"Il passaggio verso {target} resta controllato e un approccio diretto espone subito la squadra."
    if archetype == "identificare_bersaglio":
        return f"Tra {target} ci sono tracce, segnali o identita che si confondono: serve capire qual e quella giusta."
    if archetype == "negoziazione_tesa":
        return f"Chi decide su {target} non si scopre facilmente e una mossa sbagliata puo chiudere ogni margine."
    if archetype == "anomalia_da_decifrare":
        return f"Attorno a {target} c'e un effetto instabile che confonde la lettura della scena e blocca l'avanzata."
    if archetype == "recupero_conteso":
        return f"L'elemento utile legato a {target} e esposto, conteso o difficile da estrarre in sicurezza."
    if archetype == "scorta_estrazione":
        if any(word in text for word in ["hangar", "atterraggio", "ponte", "porto", "molo", "rampa"]):
            return f"La folla, l'imbarco e il caos sul ponte rendono difficile portare la squadra o i civili verso {target} senza perdere il controllo."
        return f"Muovere {target} senza perderlo di vista o senza esporlo troppo e il vero collo di bottiglia della zona."
    if archetype == "combattimento_bloccante":
        return f"La pressione ostile attorno a {target} occupa lo spazio e impedisce di avanzare con calma."
    return f"La leva utile della zona e nascosta dentro {target}, ma la pressione locale non lascia molto margine."


def _scene_resolution_text(
    archetype: str,
    state: GameState,
    current_node: MapNode | None,
    display_terms: list[str],
    allowed_effect_types: set[str],
) -> str:
    handles = _scene_resolution_handles(state, current_node, display_terms, allowed_effect_types)
    handle_values = list(handles.values())
    primary = handle_values[0] if handle_values else "agganciare l'elemento davvero decisivo della zona"
    secondary = handle_values[1] if len(handle_values) > 1 else ""

    if archetype == "accesso_sorvegliato":
        return f"serve {primary}" + (f", oppure {secondary}" if secondary else "")
    if archetype == "identificare_bersaglio":
        return f"serve {primary}" + (f" e poi {secondary}" if secondary else "")
    if archetype == "negoziazione_tesa":
        return f"serve {primary}" + (f"; in alternativa {secondary}" if secondary else "")
    if archetype == "anomalia_da_decifrare":
        return f"serve {primary}" + (f", quindi {secondary}" if secondary else "")
    if archetype == "recupero_conteso":
        return f"serve {primary}" + (f" e creare spazio per {secondary}" if secondary else "")
    if archetype == "scorta_estrazione":
        return f"serve {primary}" + (f", poi {secondary}" if secondary else "")
    if archetype == "combattimento_bloccante":
        return f"serve {primary}" + (f", mentre qualcuno prova a {secondary}" if secondary else "")
    return f"serve {primary}" + (f", oppure {secondary}" if secondary else "")


def _classify_scene_archetype(state: GameState, current_node: MapNode | None, profile: dict) -> str:
    text = _context_text(state, current_node)
    tags = {str(t).lower() for t in (state.scene.scene_tags if state.scene else [])}
    mission_objective = (state.mission.objective if state.mission else "").lower()
    scene_problem = (state.scene.scene_problem if state.scene else "").lower()
    combined = f"{text} {scene_problem}"

    # Anomalie biologiche/organiche: hanno priorità alta perché "salvataggio" e "estraz"
    # sono spesso presenti anche in queste scene e farebbero scattare scorta_estrazione per errore.
    if _contains_any(combined, ("fungo", "micelio", "miceliale", "ife", "spore", "filament", "simbios",
                                "parassit", "contamin", "integraz", "neurali", "bioluminesc",
                                "radici pensanti", "organismo", "rete biologica", "fusione")):
        return "anomalia_da_decifrare"

    # Scorta/evacuazione con folla fisica: richiede presenza esplicita di persone da spostare
    if _contains_any(text, ("capsula", "imbarco", "famiglie", "civili")):
        return "scorta_estrazione"
    if _contains_any(text, ("evacu",)) and _contains_any(text, ("folla", "civili", "coloni", "passeggeri")):
        return "scorta_estrazione"

    if _contains_any(text, ("ingresso", "accesso", "varco", "gate", "checkpoint", "sorvegliat", "barriera", "blocco", "dogana")):
        return "accesso_sorvegliato"

    # "salvataggio" da solo non basta per scorta: serve anche un elemento di movimento di gruppo
    if _contains_any(mission_objective, ("scort", "estraz", "condurre fuori", "portare in salvo")):
        return "scorta_estrazione"
    if _contains_any(mission_objective, ("evacu",)) and _contains_any(mission_objective, ("civili", "coloni", "famiglie")):
        return "scorta_estrazione"

    if _contains_any(combined, ("trovare", "individuare", "riconosc", "identit", "sosia", "bersaglio", "ambasciatore")) and not (current_node and current_node.contains_enemy):
        return "identificare_bersaglio"
    if "negoziazione" in tags or _contains_any(combined, ("summit", "consiglio", "delegat", "ambasciat", "trattativa", "voto", "accordo", "negoziare con")):
        return "negoziazione_tesa"
    if "rituale" in tags or "possessione" in tags or _contains_any(combined, ("anomalia", "ritual", "simbol", "codice", "terminale", "fenomen", "eco", "campion")):
        return "anomalia_da_decifrare"
    if current_node and current_node.contains_loot:
        return "recupero_conteso"
    if current_node and current_node.contains_enemy:
        return "combattimento_bloccante"
    return "pressione_locale"


def _derive_scene_solution_profile(state: GameState, current_node: MapNode | None) -> dict:
    scene = state.scene
    if not scene:
        return {"keywords": set(), "allowed_effect_types": set(), "support_effect_types": {"difendere", "stabilizzare"}}
    if scene.challenge and scene.challenge.allowed_effect_types:
        return {
            "archetype": scene.challenge.archetype or "pressione_locale",
            "keywords": set(scene.challenge.keyword_roots or []),
            "display_terms": list(scene.challenge.key_terms or []),
            "allowed_effect_types": set(scene.challenge.allowed_effect_types or []),
            "support_effect_types": set(scene.challenge.support_effect_types or []),
            "blocked_effect_types": set(scene.challenge.blocked_effect_types or []),
        }

    keywords: set[str] = set()
    allowed_effect_types: set[str] = set()
    support_effect_types: set[str] = {"difendere", "stabilizzare"}
    blocked_effect_types: set[str] = set()
    display_terms: list[str] = []

    text_chunks = [
        current_node.name if current_node else "",
        current_node.kind if current_node else "",
        current_node.description if current_node else "",
        scene.scene_text,
        " ".join(scene.scene_tags),
    ]
    keywords |= _scene_keyword_roots(" ".join(text_chunks))

    for entity in scene.entities[:8]:
        if not entity.interactable and entity.type not in {"enemy", "phenomenon", "location"}:
            continue
        if entity.type in {"enemy", "npc", "ally", "object", "phenomenon"}:
            display_terms.append(entity.name)
        keywords |= _scene_keyword_roots(f"{entity.name} {' '.join(entity.tags)}")
        if entity.type == "enemy":
            allowed_effect_types |= {"combattere", "difendere", "infiltrarsi", "ingannare", "negoziare"}
        elif entity.type in {"object", "phenomenon", "location"}:
            allowed_effect_types |= {"investigare", "rilevare", "decifrare", "forzare", "recuperare"}
        elif entity.type in {"npc", "ally"}:
            allowed_effect_types |= {"negoziare", "rilevare", "investigare"}

    profile_text = " ".join(text_chunks).lower()
    if current_node:
        if current_node.contains_enemy:
            allowed_effect_types |= {"combattere", "difendere", "infiltrarsi", "ingannare"}
            keywords |= {"ostil", "guard", "creatur", "drone", "minacc"}
        if current_node.contains_clue:
            allowed_effect_types |= {"investigare", "rilevare", "decifrare"}
            keywords |= {"indizi", "tracci", "codic", "archiv", "terminal"}
        if current_node.contains_loot:
            allowed_effect_types |= {"recuperare", "forzare", "rilevare"}
            keywords |= {"cass", "scort", "risors", "equipag"}

    if any(word in profile_text for word in ["laboratorio", "lab", "ricerca", "esperiment", "campion"]):
        allowed_effect_types |= {"investigare", "rilevare", "decifrare", "forzare"}
        keywords |= {"labor", "campion", "analis", "scansi", "esperim", "provett", "terminal"}
    if any(word in profile_text for word in ["server", "mainframe", "datacenter", "rete", "dati", "comunic"]):
        allowed_effect_types |= {"rilevare", "decifrare", "forzare"}
        keywords |= {"server", "ret", "dati", "canal", "access", "codic"}
    if any(word in profile_text for word in ["reatt", "energia", "nucleo", "generat"]):
        allowed_effect_types |= {"forzare", "rilevare", "recuperare", "difendere"}
        keywords |= {"reatto", "energ", "nucle", "cella", "raffred"}
    if any(word in profile_text for word in ["infermer", "medic", "ibern", "cryo", "stasi"]):
        allowed_effect_types |= {"stabilizzare", "rilevare", "investigare", "recuperare"}
        keywords |= {"medic", "sier", "stasi", "capsul", "paramet"}
    if any(word in profile_text for word in ["corridoio", "passaggio", "ventil", "manutenz", "tunnel"]):
        allowed_effect_types |= {"infiltrarsi", "forzare", "rilevare", "difendere"}
        keywords |= {"corrido", "portell", "grata", "condott", "passagg"}

    if not allowed_effect_types:
        allowed_effect_types |= {"investigare", "rilevare", "forzare", "recuperare"}

    return {
        "archetype": "pressione_locale",
        "keywords": set(sorted(keywords)[:16]),
        "display_terms": _unique_preserve(_scene_display_terms(state, current_node) + display_terms, limit=6),
        "allowed_effect_types": allowed_effect_types,
        "support_effect_types": support_effect_types,
        "blocked_effect_types": blocked_effect_types,
    }


def _build_scene_challenge(state: GameState, current_node: MapNode | None, claude_scene_actions: list | None = None) -> SceneChallenge:
    profile = _derive_scene_solution_profile(state, current_node)
    display_terms = profile.get("display_terms") or _scene_display_terms(state, current_node)
    archetype = _classify_scene_archetype(state, current_node, profile)
    template = _SCENE_ARCHETYPE_DEFS.get(archetype, _SCENE_ARCHETYPE_DEFS["pressione_locale"])
    stakes = _scene_stakes_text(state, current_node)
    summary = template.get("summary") or _scene_summary_text(state, current_node, display_terms, profile["allowed_effect_types"])
    effective_allowed = set(profile["allowed_effect_types"]) | set(template.get("allowed", set()))
    effective_support = set(profile["support_effect_types"]) | set(template.get("support", set()))
    blocked_effects = set(profile.get("blocked_effect_types", set())) | set(template.get("blocked", set()))

    # Preferisce il testo narrativo generato da Claude (scene_problem/scene_resolution)
    # al testo template generico — garantisce coerenza tra narrativa e meccanica.
    narrative_obstacle = (state.scene.scene_problem if state.scene and state.scene.scene_problem else "").strip()
    narrative_resolution = (state.scene.scene_resolution if state.scene and state.scene.scene_resolution else "").strip()

    obstacle = narrative_obstacle or _scene_obstacle_text(archetype, current_node, display_terms)
    resolution_signal = narrative_resolution or _scene_resolution_text(archetype, state, current_node, display_terms, effective_allowed)

    # Se abbiamo testo narrativo, aggiorniamo il profilo dei keyword dal testo reale
    if narrative_obstacle:
        narrative_roots = _scene_keyword_roots(narrative_obstacle + " " + narrative_resolution)
        profile["keywords"] = set(sorted(profile["keywords"] | narrative_roots)[:16])

    return SceneChallenge(
        archetype=archetype.replace("_", " "),
        summary=summary,
        obstacle=obstacle,
        stakes=stakes,
        resolution_signal=resolution_signal,
        valid_approaches=[
            _EFFECT_TYPE_LABELS[effect_type]
            for effect_type in sorted(effective_allowed)
            if effect_type in _EFFECT_TYPE_LABELS
        ][:4],
        support_approaches=[
            _EFFECT_TYPE_LABELS[effect_type]
            for effect_type in sorted(effective_support)
            if effect_type in _EFFECT_TYPE_LABELS
        ][:3],
        false_approaches=_unique_preserve(template.get("false", []), limit=3),
        key_terms=_unique_preserve(display_terms, limit=5),
        allowed_effect_types=sorted(effective_allowed),
        support_effect_types=sorted(effective_support),
        blocked_effect_types=sorted(blocked_effects),
        keyword_roots=sorted(profile["keywords"])[:10],
        scene_actions=claude_scene_actions if claude_scene_actions else [],
    )


def _resolve_action_roll(
    state: GameState,
    player: Player,
    action: Action,
    intent: str,
    shared_context: str,
    current_node: MapNode | None,
    roll: int,                    # somma di 3d6 (3-18)
    coordination_bonus: int = 0,  # +2 se un altro personaggio ha già agito sullo stesso effect_type
) -> dict:
    """Risoluzione GURPS Lite 4ª ed.: 3d6 ≤ abilità effettiva.

    abilità_effettiva = livello_skill + item_bonus + coordination_bonus - difficulty - status_malus - threat_malus
      livello_skill = player.skills[skill] se conosciuta,
                      altrimenti (stat_cardine - default_penalty E/M/D)
    margine = abilità_effettiva - roll    (positivo → successo)

    Outcome:
      critico        : roll ≤ 4, oppure (roll==5 con skill≥15), oppure (roll==6 con skill≥16),
                       oppure margine ≥ 10
      fallimento crit: roll == 18, oppure (roll==17 con skill≤15),
                       oppure (-margine) ≥ 10
      successo pieno : margine ≥ 5
      successo parz. : 0 ≤ margine < 5
      fallimento     : margine < 0
    """
    scene_problem = _scene_problem_context(state, current_node)
    action_text_for_tags = " ".join(x for x in [intent, action.name, action.description] if x)
    semantic_tags = _infer_semantic_tags(
        " ".join(x for x in [shared_context, scene_problem, action_text_for_tags] if x)
    )

    skill_name = normalize_skill(action.skill) if action.skill else default_skill_for(action.stat, action.effect_type)

    # Livello base della skill: conosciuta → memorizzato; sconosciuta → default da attributo
    if skill_name in player.skills:
        base_skill_level = player.skills[skill_name]
        skill_known = True
    else:
        default_level = skill_default_level(skill_name, player.stats)
        if default_level is None:
            cardinal_stat = skill_stat(skill_name) if skill_name in SKILL_INFO else action.stat
            default_level = min(player.stats.get(cardinal_stat, 10), 20) - 10
        base_skill_level = default_level
        skill_known = False

    item_bonus = 1 if action.requires_item else 0
    status_malus = status_penalty(player.status)
    threat_malus = threat_penalty(state.scene.threat_level)
    difficulty = action.difficulty
    all_traits = player.advantages + player.disadvantages
    adv_detail = advantage_breakdown(all_traits, skill_name, action.effect_type)
    adv_bonus = sum(t["delta"] for t in adv_detail)
    environmental_trait_detail = []
    if any(t in {"buio", "oscurita", "oscurità"} for t in (state.scene.scene_tags or [])):
        nv_reduction = min(difficulty, advantage_night_vision(all_traits))
        if nv_reduction:
            difficulty -= nv_reduction
            environmental_trait_detail.append({"name": "Visione Notturna", "delta": nv_reduction})
    if any(root in action_text_for_tags.lower() for root in ("risch", "azzard", "spericol", "mi lancio", "carico")):
        reckless = advantage_reckless_bonus(all_traits)
        if reckless:
            adv_bonus += reckless
            adv_detail.append({"name": "Spericolato", "delta": reckless})

    effective_skill = base_skill_level + item_bonus + adv_bonus + coordination_bonus - difficulty - status_malus - threat_malus
    margin = effective_skill - roll
    luck_detail = None
    if advantage_luck_rerolls(player.advantages) > 0 and margin < 0:
        extra_rolls = [sum(random.randint(1, 6) for _ in range(3)) for _ in range(2)]
        best_roll = min([roll, *extra_rolls])
        if best_roll < roll:
            luck_detail = {"trait": "Fortuna", "original_roll": roll, "extra_rolls": extra_rolls, "chosen_roll": best_roll}
            roll = best_roll
            margin = effective_skill - roll

    if (
        roll <= 4
        or (roll == 5 and base_skill_level >= 15)
        or (roll == 6 and base_skill_level >= 16)
        or margin >= 10
    ):
        outcome = "critico"
        outcome_reason = f"successo critico (3d6={roll}, abilità eff. {effective_skill})"
    elif (
        roll == 18
        or (roll == 17 and base_skill_level <= 15)
        or (-margin) >= 10
    ):
        outcome = "fallimento critico"
        outcome_reason = f"fallimento critico (3d6={roll}, abilità eff. {effective_skill})"
    elif margin >= 5:
        outcome = "successo pieno"
        outcome_reason = f"test superato con largo margine (+{margin})"
    elif margin >= 0:
        outcome = "successo parziale"
        outcome_reason = f"test superato di stretta misura (+{margin})"
    else:
        outcome = "fallimento"
        outcome_reason = f"test mancato ({margin})"

    effect_type = SKILL_TO_EFFECT_TYPE.get(skill_name, action.effect_type)
    effect = apply_effect(
        effect_type, margin, difficulty,
        action_role=action.action_role, skill=skill_name,
    )
    effect = _apply_tag_modifiers(effect, semantic_tags, action.effect_type)
    effect, scene_gate_note = _apply_scene_solution_gate(effect, state, current_node, action, intent)

    return {
        "roll": roll,
        "margin": margin,
        "effective_skill": effective_skill,
        "base_skill_level": base_skill_level,
        "skill_known": skill_known,
        "outcome": outcome,
        "outcome_reason": outcome_reason,
        "skill": skill_name,
        "effect_type": effect_type,
        "effect": effect,
        "semantic_tags": semantic_tags,
        "stat_value": player.stats.get(action.stat, 0),  # retro-compat
        "status_malus": status_malus,
        "threat_malus": threat_malus,
        "difficulty": difficulty,
        "item_bonus": item_bonus,
        "adv_bonus": adv_bonus,
        "adv_breakdown": adv_detail,
        "environmental_trait_modifiers": environmental_trait_detail,
        "luck": luck_detail,
        "coordination_bonus": coordination_bonus,
        "scene_gate_note": scene_gate_note,
        "total": margin,
    }


COMBAT_SKILLS = {"combattere", "mira", "lottare", "lanciare"}
PASSIVE_INTENTS = {"investigation", "observation", "technical", "medical", "social", "stealth", "survival", "generic"}

INTENT_ALLOWED_SKILLS: dict[str, list[str]] = {
    "combat": ["combattere", "mira", "lottare", "lanciare", "proteggere", "schivare", "strategia", "intimidire"],
    "investigation": ["investigare", "osservare", "analizzare", "decifrare", "cultura", "scienze", "occultismo", "seguire_tracce", "intuire"],
    "observation": ["osservare", "investigare", "seguire_tracce", "intuire", "analizzare"],
    "technical": ["tecnologia", "meccanica", "elettronica", "informatica", "ingegneria", "scassinare", "manualita", "forzare", "decifrare"],
    "medical": ["curare", "medicina", "biologia", "calmare"],
    "social": ["persuadere", "comunicare", "interrogare", "ingannare", "intuire", "calmare", "intimidire", "etichetta"],
    "stealth": ["furtivita", "infiltrarsi", "mimetizzare", "pedinare", "rapidita", "acrobazia", "schivare"],
    "force": ["forzare", "demolire", "sollevare", "trasportare", "arrampicarsi", "manualita"],
    "survival": ["sopravvivere", "sopravvivenza_urbana", "navigare", "seguire_tracce", "resistere", "nuotare"],
    "generic": ["osservare", "investigare", "intuire", "sopravvivere"],
}

_INTENT_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("combat", ("attacc", "combatt", "spar", "colp", "uccid", "abbatt", "trafigg", "pugnal", "lott", "spara", "arco", "fucile")),
    ("medical", ("cur", "medic", "stabilizz", "soccorr", "ferit", "bend", "diagnos")),
    ("technical", ("hacker", "ripar", "computer", "serratur", "lucchett", "scassin", "grimald", "meccan", "elettron", "consol", "terminale", "disattiv")),
    ("stealth", ("furtiv", "nascond", "silenz", "ombra", "intrufol", "aggir", "evit", "scapp", "fugg", "ritirat")),
    ("social", ("parl", "convinc", "persuad", "interrog", "negozi", "ingann", "ment", "bluff", "calm", "intimid", "minacc")),
    ("force", ("sfond", "romp", "forz", "sping", "sollev", "trascin", "demol", "aprire a forza")),
    ("investigation", ("investig", "indizio", "cerc", "esamin", "analizz", "stud", "decifr", "leggo", "traduc", "capire", "ricostru")),
    ("observation", ("osserv", "guardo", "guard", "not", "ascolt", "ispezion", "sorvegli", "scrut")),
    ("survival", ("orient", "sopravviv", "tracce", "seguire tracce", "navig", "resist", "nuot")),
]


def roll_for_player_action(player_dict: dict, action_text: str, threat_level: int = 1, scene_tags: list[str] | None = None) -> dict:
    """Tiro GURPS 3d6 completo da dict personaggio + testo azione libera.
    Applica: skill (conosciuta o default), bonus vantaggi/svantaggi, malus stato,
    malus minaccia, bonus oggetto, difficoltà situazionale da tag scena.
    Usato da master_turn_bible_endpoint per popolare last_roll_details."""
    scene_tags = scene_tags or []
    skills: dict = player_dict.get("skills") or {}
    stats: dict = player_dict.get("stats") or {}
    advantages: list = player_dict.get("advantages") or []
    disadvantages: list = player_dict.get("disadvantages") or []
    items: list = player_dict.get("items") or []

    # ── Inferisci skill ──────────────────────────────────────────────────────
    resolver_context = {
        "scene_type": " ".join(str(t) for t in scene_tags),
        "location_tags": scene_tags,
        "genre": player_dict.get("genre") or player_dict.get("setting") or "",
        "target_type": "",
        "threat_level": threat_level,
        "combat_active": bool(player_dict.get("combat_active") or player_dict.get("in_combat")),
        "active_objective": player_dict.get("active_objective") or "",
        "npc_role": player_dict.get("target_npc_role") or "",
    }
    if isinstance(player_dict.get("action_context"), dict):
        resolver_context.update(player_dict["action_context"])
    action_resolution = resolve_action_skill(action_text, resolver_context, skills)
    chosen_skill = action_resolution["selected_skill"]
    semantic_intent = action_resolution.get("intent", "investigate")
    intent = "observation" if semantic_intent == "observe" else semantic_intent
    valid_candidates = [c for c in action_resolution.get("candidate_skills", []) if not c.get("rejected")]
    intent_info = {
        "intent": intent,
        "matched_intents": [
            k for k, v in sorted(
                (action_resolution.get("intent_data") or {}).get("intent_scores", {}).items(),
                key=lambda item: item[1],
                reverse=True,
            )
            if v > 0
        ][:5],
        "allowed_skills": [c["skill"] for c in valid_candidates] or [chosen_skill],
        "is_passive": semantic_intent not in {"combat_melee", "combat_ranged"},
        "interaction_mode": action_resolution.get("interaction_mode"),
        "target_type": action_resolution.get("target_type"),
        "confidence": action_resolution.get("confidence"),
    }

    skill_known = False
    fallback_reason = "semantic_low_confidence" if action_resolution.get("confidence", 1.0) < 0.45 else ""
    if chosen_skill and chosen_skill in skills:
        base_skill_level = skills[chosen_skill]
        skill_known = True
    elif chosen_skill:
        default_level = skill_default_level(chosen_skill, stats)
        if default_level is None:
            cardinal = skill_stat(chosen_skill) if chosen_skill in SKILL_INFO else "intelligenza"
            default_level = min(stats.get(cardinal, 10), 20) - 10
        base_skill_level = default_level
    else:
        chosen_skill = "investigare"
        fallback_reason = "fallback_sicuro"
        base_skill_level = skill_default_level(chosen_skill, stats) or (min(stats.get("intelligenza", 10), 20) - 5)

    # ── Bonus/malus vantaggi e svantaggi ─────────────────────────────────────
    effect_type = SKILL_TO_EFFECT_TYPE.get(chosen_skill, chosen_skill)
    all_traits = advantages + disadvantages
    adv_detail = advantage_breakdown(all_traits, chosen_skill, effect_type)
    adv_bonus = sum(t["delta"] for t in adv_detail)

    # ── Item bonus: +1 se l'azione menziona un oggetto dell'inventario ───────
    item_bonus = 0
    action_lower = action_text.lower()
    for it in items:
        it_words = it.lower().split()
        if any(w in action_lower for w in it_words if len(w) > 3):
            item_bonus = 1
            break

    # ── Difficoltà situazionale da tag scena ─────────────────────────────────
    # Tag come "buio", "pericolo", "affollato", "tempo_limitato" aggiungono malus
    difficulty = 0
    hard_tags = {"buio", "oscurita", "pioggia", "tempesta", "rumore", "caos", "folla", "pericolo_immediato"}
    medium_tags = {"stress", "fretta", "visibilità_ridotta", "terreno_difficile", "affollato"}
    if any(t in hard_tags for t in scene_tags):
        difficulty += 2
    if any(t in medium_tags for t in scene_tags):
        difficulty += 1
    environmental_trait_detail = []
    if any(t in {"buio", "oscurita", "oscurità"} for t in scene_tags):
        nv_reduction = min(difficulty, advantage_night_vision(all_traits))
        if nv_reduction:
            difficulty -= nv_reduction
            environmental_trait_detail.append({"name": "Visione Notturna", "delta": nv_reduction})
    if any(root in action_text.lower() for root in ("risch", "azzard", "spericol", "mi lancio", "carico")):
        reckless = advantage_reckless_bonus(all_traits)
        if reckless:
            adv_bonus += reckless
            adv_detail.append({"name": "Spericolato", "delta": reckless})

    # ── Malus stato personaggio e minaccia ───────────────────────────────────
    status_malus = status_penalty(player_dict.get("status", "ok"))
    threat_malus = threat_penalty(threat_level)

    # ── Calcolo finale ────────────────────────────────────────────────────────
    effective_skill = base_skill_level + item_bonus + adv_bonus - difficulty - status_malus - threat_malus
    roll = sum(random.randint(1, 6) for _ in range(3))
    margin = effective_skill - roll
    luck_detail = None

    # Fortuna: nel motore narrativo automatico la usiamo come rete di sicurezza
    # sul primo tiro fallito. La gestione "una volta per sessione" richiede
    # tracking persistente dedicato; qui esponiamo il dettaglio nel risultato.
    if advantage_luck_rerolls(advantages) > 0 and margin < 0:
        extra_rolls = [sum(random.randint(1, 6) for _ in range(3)) for _ in range(2)]
        best_roll = min([roll, *extra_rolls])
        if best_roll < roll:
            luck_detail = {"trait": "Fortuna", "original_roll": roll, "extra_rolls": extra_rolls, "chosen_roll": best_roll}
            roll = best_roll
            margin = effective_skill - roll

    # Outcome GURPS Lite (usa base_skill_level per soglie critiche, come RAW)
    if roll <= 4 or (roll == 5 and base_skill_level >= 15) or (roll == 6 and base_skill_level >= 16) or margin >= 10:
        outcome = "CRITICO"
        success = True
    elif roll == 18 or (roll == 17 and base_skill_level <= 15) or margin <= -10:
        outcome = "FALLIMENTO CRITICO"
        success = False
    elif margin >= 5:
        outcome = "SUCCESSO PIENO"
        success = True
    elif margin >= 0:
        outcome = "SUCCESSO PARZIALE"
        success = True
    else:
        outcome = "FALLIMENTO"
        success = False

    return {
        "name": player_dict.get("name", "?"),
        "action": action_text[:60],
        "outcome": outcome,
        "hint": "",
        "margin": margin,
        "rolled": roll,
        "skill": chosen_skill,
        "intent": intent,
        "action_resolution": action_resolution,
        "intent_classification": intent_info,
        "allowed_skills": list(intent_info["allowed_skills"]),
        "fallback_reason": fallback_reason,
        "non_combat_action": semantic_intent not in {"combat_melee", "combat_ranged"},
        "skill_confidence": action_resolution.get("confidence"),
        "candidate_skills": action_resolution.get("candidate_skills", []),
        "rejected_skill_candidates": action_resolution.get("rejected_candidates", []),
        "interaction_mode": action_resolution.get("interaction_mode"),
        "target_type": action_resolution.get("target_type"),
        "skill_known": skill_known,
        "base_skill": base_skill_level,
        "item_bonus": item_bonus,
        "adv_bonus": adv_bonus,
        "adv_breakdown": adv_detail,
        "environmental_trait_modifiers": environmental_trait_detail,
        "luck": luck_detail,
        "coord_bonus": 0,
        "difficulty": difficulty,
        "status_malus": status_malus,
        "threat_malus": threat_malus,
        "effective_skill": effective_skill,
        "success": success,
        "critical": "CRITICO" in outcome,
    }


# ─── PR2: Combattimento meccanico ─────────────────────────────────────────────

def initiate_combat_action(
    state: GameState,
    attacker_id: int,
    action: Action,
    target_entity_id: str | None = None,
    target_player_id: int | None = None,
    action_type: str = "normal",   # "normal" | "all_out_attack"
) -> GameState:
    """
    Prima metà dello scambio di combattimento: tira il dado dell'attaccante
    e mette l'attacco in stato 'pending' in attesa della dichiarazione di difesa.

    Se il bersaglio è una SceneEntity (nemico), il motore procede automaticamente
    con la difesa dell'entità (non interattiva).
    Se il bersaglio è un Player, sospende e attende declare_defense().
    action_type: "all_out_attack" → +4 attacco, nessuna difesa attiva questo turno.
    """
    attacker = next((p for p in state.players if p.id == attacker_id), None)
    if not attacker:
        state.log = f"Attaccante {attacker_id} non trovato."
        return state

    # Applica action_type al Player così combat.py lo legge
    attacker.action_type = action_type

    attack_skill_name = action.skill or "combattere"
    damage_formula = action.damage or "1d6"
    damage_type = action.damage_type or "cr"
    roll = sum(random.randint(1, 6) for _ in range(3))

    # Stordito: non può agire, prova recupero automatico
    if attacker.stunned:
        recovered, stun_roll = attempt_stun_recovery(attacker)
        if recovered:
            state.log = (
                f"{attacker.name} era stordito — si riprende! (SA check: {stun_roll}). "
                f"Può agire al prossimo turno."
            )
        else:
            state.log = (
                f"{attacker.name} è stordito e non può agire. (SA check fallito: {stun_roll})"
            )
        state.last_attack_result = {
            "attacker": attacker.name, "target": "", "skill": "", "skill_level": 0,
            "attack_roll": stun_roll, "damage_formula": "", "damage_type": "",
            "result": {"hit": False, "narrative_hint": "attaccante_stordito",
                       "defended": False, "raw_damage": 0, "dr_absorbed": 0, "net_damage": 0,
                       "attacker_margin": 0, "defense_margin": 0, "attacker_critical": False,
                       "defense_critical_fail": False, "wound_threshold": "",
                       "shock_applied": 0, "major_wound": False, "major_wound_check_passed": False,
                       "knockdown": False, "knockdown_check_passed": False,
                       "death_check": False, "death_check_passed": False,
                       "fp_cost": 0, "target_stunned": False, "target_prone": False},
            "advantages_active": [], "target_dr": 0,
            "attacker_stunned": True, "stun_recovered": recovered,
        }
        return state

    # Bersaglio entità → risolvi subito (difesa automatica)
    if target_entity_id:
        entity = next(
            (e for e in state.scene.entities if e.id == target_entity_id), None
        )
        if not entity:
            state.log = f"Entità {target_entity_id} non trovata nella scena."
            return state
        result = resolve_attack(
            attacker=attacker,
            attack_skill_name=attack_skill_name,
            damage_formula=damage_formula,
            damage_type=damage_type,
            target_entity=entity,
        )
        reset_action_type(attacker)
        attack_level = attacker.skills.get(attack_skill_name, 0)
        all_adv = attacker.advantages + attacker.disadvantages
        active_adv = [a for a in all_adv if any(k in a.lower() for k in ("riflessi","forza","sensi","duro","ambid"))]
        state.log = _combat_result_to_log(attacker.name, entity.name, result, roll)
        state.last_attack_result = {
            "attacker": attacker.name,
            "target": entity.name,
            "skill": attack_skill_name,
            "skill_level": attack_level,
            "attack_roll": roll,
            "damage_formula": damage_formula,
            "damage_type": damage_type,
            "result": result.model_dump(),
            "advantages_active": active_adv,
            "target_dr": entity.dr,
            "action_type": action_type,
        }
        return state

    # Bersaglio giocatore → sospendi in attesa di declare_defense
    if target_player_id is not None:
        state.pending_attack = {
            "attacker_id": attacker_id,
            "target_player_id": target_player_id,
            "attack_skill_name": attack_skill_name,
            "damage_formula": damage_formula,
            "damage_type": damage_type,
            "roll": roll,
            "action_type": action_type,
        }
        attack_level = attacker.skills.get(attack_skill_name, 0)
        aoa_tag = " [ATTACCO TOTALE +4]" if action_type == "all_out_attack" else ""
        state.log = (
            f"{attacker.name}{aoa_tag} attacca! (3d6={roll} vs abilità {attack_level}). "
            f"Il bersaglio deve dichiarare la difesa attiva."
        )
        return state

    state.log = "Nessun bersaglio specificato per l'azione di combattimento."
    return state


def declare_defense(
    state: GameState,
    defense_request: CombatDefenseRequest,
    defense_action_type: str = "normal",  # "normal" | "all_out_defense"
    cover_bonus: int = 0,
    rear_attack: bool = False,
) -> GameState:
    """
    Seconda metà: il giocatore bersaglio dichiara la sua difesa attiva.
    Recupera l'attacco pendente, risolve l'intera sequenza e svuota pending_attack.
    defense_action_type: "all_out_defense" → +2 difesa, nessun attacco questo turno.
    cover_bonus: +2 se il bersaglio è in copertura (calcolato dal frontend via terreno hex).
    rear_attack: True se l'attaccante era nella zona posteriore del bersaglio (hex geometria).
    """
    if not state.pending_attack:
        state.log = "Nessun attacco in sospeso da difendere."
        return state

    pa = state.pending_attack
    attacker = next((p for p in state.players if p.id == pa["attacker_id"]), None)
    target = next((p for p in state.players if p.id == pa["target_player_id"]), None)
    if not attacker or not target:
        state.log = "Attaccante o bersaglio non trovati."
        state.pending_attack = None
        return state

    # Applica action_type al difensore (combat.py lo legge per +2 difesa)
    target.action_type = defense_action_type

    result = resolve_attack(
        attacker=attacker,
        attack_skill_name=pa["attack_skill_name"],
        damage_formula=pa["damage_formula"],
        damage_type=pa["damage_type"],
        target_player=target,
        defense_request=defense_request,
        cover_bonus=cover_bonus,
        rear_attack=rear_attack,
    )
    state.pending_attack = None
    reset_action_type(attacker)
    reset_action_type(target)

    state.log = _combat_result_to_log(attacker.name, target.name, result, pa["roll"])
    attack_level = attacker.skills.get(pa["attack_skill_name"], 0)
    all_adv_att = attacker.advantages + attacker.disadvantages
    all_adv_def = target.advantages + target.disadvantages
    from .data_advantages import advantage_dodge_bonus
    dodge_bonus = advantage_dodge_bonus(all_adv_def)
    def_value = target.dodge + dodge_bonus
    if defense_action_type == "all_out_defense":
        def_value += 2
    if defense_request and defense_request.defense_type in ("parry", "block"):
        s = defense_request.defense_skill or pa["attack_skill_name"]
        def_value = target.skills.get(s, 0) // 2 + 3 + dodge_bonus
        if defense_action_type == "all_out_defense":
            def_value += 2
    state.last_attack_result = {
        "attacker": attacker.name,
        "target": target.name,
        "skill": pa["attack_skill_name"],
        "skill_level": attack_level,
        "attack_roll": pa["roll"],
        "damage_formula": pa["damage_formula"],
        "damage_type": pa["damage_type"],
        "defense_type": defense_request.defense_type if defense_request else "dodge",
        "defense_value": def_value,
        "defense_action_type": defense_action_type,
        "action_type": pa.get("action_type", "normal"),
        "advantages_attacker": [a for a in all_adv_att if a],
        "advantages_defender": [a for a in all_adv_def if a],
        "result": result.model_dump(),
        "target_dr": target.dr,
        "target_stunned": result.target_stunned,
        "target_prone": result.target_prone,
        "target_hp_after": target.hp,
        "target_fp_after": target.fp,
        "shock_applied": result.shock_applied,
        "major_wound": result.major_wound,
        "major_wound_check_passed": result.major_wound_check_passed,
        "knockdown": result.knockdown,
        "knockdown_check_passed": result.knockdown_check_passed,
        "death_check": result.death_check,
        "death_check_passed": result.death_check_passed,
        "cover_bonus": cover_bonus,
        "rear_attack": rear_attack,
    }
    return state


def _combat_result_to_log(attacker_name: str, target_name: str, result: AttackResult, roll: int) -> str:
    """Genera una riga di log narrativa dal risultato combattimento."""
    if not result.hit:
        if result.narrative_hint == "attaccante_stordito":
            return f"{attacker_name} è stordito e non può agire."
        if result.narrative_hint == "critico_fallimentare_attaccante":
            return f"{attacker_name}: fallimento critico! (3d6={roll}) — l'attacco si ritorce contro di lui."
        return f"{attacker_name} manca {target_name}. (3d6={roll}, margine {result.attacker_margin})"
    if result.defended:
        return (
            f"{attacker_name} colpisce ma {target_name} difende! "
            f"(attacco margine {result.attacker_margin}, difesa margine {result.defense_margin})"
        )
    crit_tag = " [CRITICO]" if result.attacker_critical else ""
    wound_tag = {
        "ferito": " — FERITO",
        "ferito_grave": " — FERITO GRAVE",
        "fuori_combattimento": " — ABBATTUTO",
        "morto": " — MORTO",
    }.get(result.wound_threshold, "")
    # Condizioni secondarie
    extras = []
    if result.shock_applied:
        extras.append(f"Shock −{result.shock_applied}")
    if result.major_wound:
        extras.append("Ferita Grave!" + (" SA OK" if result.major_wound_check_passed else " → STORDITO"))
    if result.knockdown:
        extras.append("Caduta!" + (" SA OK" if result.knockdown_check_passed else " → A TERRA"))
    if result.death_check:
        extras.append("Tiro morte!" + (" SA OK" if result.death_check_passed else " → MORTO"))
    extras_str = " [" + ", ".join(extras) + "]" if extras else ""
    return (
        f"{attacker_name}{crit_tag} colpisce {target_name}: "
        f"{result.raw_damage} danno grezzo − {result.dr_absorbed} DR = {result.net_damage} PF{wound_tag}{extras_str}."
    )


def _tactical_hex_distance(a: dict | None, b: dict | None) -> int:
    if not a or not b:
        return 999
    ax = int(a.get("col", 0))
    az = int(a.get("row", 0)) - (ax - (ax & 1)) // 2
    bx = int(b.get("col", 0))
    bz = int(b.get("row", 0)) - (bx - (bx & 1)) // 2
    ay = -ax - az
    by = -bx - bz
    return max(abs(ax - bx), abs(ay - by), abs(az - bz))


def _tactical_adjacent_hexes(pos: dict) -> list[dict]:
    col = int(pos.get("col", 0))
    row = int(pos.get("row", 0))
    if col % 2:
        offsets = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (0, -1)]
    else:
        offsets = [(1, -1), (1, 0), (0, 1), (-1, 0), (-1, -1), (0, -1)]
    return [{"col": col + dc, "row": row + dr} for dc, dr in offsets]


def _npc_attack_range(enemy: SceneEntity) -> int:
    text = " ".join([enemy.name, " ".join(enemy.tags or []), enemy.damage_type or "", enemy.damage_dice or ""]).lower()
    if any(w in text for w in ["fucile", "pistola", "arco", "balestra", "ranged", "laser", "blaster", "proiettile"]):
        return 6
    return 1


def _npc_move_toward(enemy_key: str, target_key: str, positions: dict, terrain: dict | None = None, cols: int = 15, rows: int = 10) -> dict | None:
    enemy_pos = positions.get(enemy_key)
    target_pos = positions.get(target_key)
    if not enemy_pos or not target_pos:
        return None
    terrain = terrain or {}
    occupied = {
        (int(p.get("col", 0)), int(p.get("row", 0)))
        for key, p in positions.items()
        if key != enemy_key
    }
    current_distance = _tactical_hex_distance(enemy_pos, target_pos)
    best = None
    best_distance = current_distance
    for candidate in _tactical_adjacent_hexes(enemy_pos):
        c = int(candidate["col"])
        r = int(candidate["row"])
        if c < 0 or c >= cols or r < 0 or r >= rows:
            continue
        if (c, r) in occupied:
            continue
        if int(terrain.get(f"{c},{r}", 0) or 0) == 3:
            continue
        distance = _tactical_hex_distance(candidate, target_pos)
        if distance < best_distance:
            best = {"col": c, "row": r}
            best_distance = distance
    return best


def npc_combat_turn(state: GameState, tactical_context: dict | None = None) -> dict:
    """
    Turno degli NPC: ogni entità nemica viva attacca il giocatore vivo con meno HP.
    Restituisce una lista di combat_log (uno per ogni NPC che ha agito).
    """
    if not state.scene:
        return {"npc_logs": []}

    alive_enemies = [e for e in state.scene.entities if e.type == "enemy" and e.hp > 0]
    alive_players = [p for p in state.players if p.hp > 0]
    if not alive_enemies or not alive_players:
        return {"npc_logs": []}

    npc_logs = []
    tactical_context = tactical_context or {}
    positions = dict(tactical_context.get("positions") or {})
    terrain = dict(tactical_context.get("terrain") or {})
    cols = int(tactical_context.get("cols") or 15)
    rows = int(tactical_context.get("rows") or 10)
    current_node = None
    try:
        current_node = state.map_state.nodes.get(state.map_state.current_node_id) if state.map_state else None
    except Exception:
        current_node = None
    tactical = getattr(current_node, "tactical_map", None) or {}
    role = str(tactical.get("role") or tactical.get("purpose") or "").lower()
    is_final = bool(getattr(current_node, "is_final", False) or getattr(current_node, "is_objective", False) or "final" in role)
    enemies_acting = alive_enemies if is_final else alive_enemies[:max(1, min(len(alive_enemies), len(alive_players)))]
    for enemy in enemies_acting:
        enemy_key = f"e_{enemy.id}"
        enemy_pos = positions.get(enemy_key)
        # Bersaglio tattico: il più vicino; a parità, quello con meno HP.
        # Senza snapshot mappa resta il comportamento precedente.
        if positions and enemy_pos:
            target = min(
                alive_players,
                key=lambda p: (
                    _tactical_hex_distance(enemy_pos, positions.get(f"p_{p.id}")),
                    p.hp,
                ),
            )
        else:
            target = min(alive_players, key=lambda p: p.hp)
        target_key = f"p_{target.id}"
        target_pos = positions.get(target_key)
        attack_range = _npc_attack_range(enemy)
        distance = _tactical_hex_distance(enemy_pos, target_pos) if positions else 1

        if positions and distance > attack_range:
            step = _npc_move_toward(enemy_key, target_key, positions, terrain, cols=cols, rows=rows)
            if step:
                old_pos = positions[enemy_key]
                positions[enemy_key] = {**old_pos, **step}
                distance = _tactical_hex_distance(positions[enemy_key], target_pos)
                combat_log = {
                    "attacker": enemy.name,
                    "target": target.name,
                    "skill": "movimento",
                    "skill_level": enemy.attack_skill or 10,
                    "attack_roll": 0,
                    "damage_formula": enemy.damage_dice,
                    "damage_type": enemy.damage_type,
                    "is_npc_turn": True,
                    "tactical_move": {
                        "entity_id": enemy.id,
                        "from": old_pos,
                        "to": positions[enemy_key],
                        "target_player_id": target.id,
                        "distance_after": distance,
                    },
                    "result": {
                        "hit": False, "defended": False, "raw_damage": 0, "dr_absorbed": 0,
                        "net_damage": 0, "attacker_margin": 0, "defense_margin": 0,
                        "attacker_critical": False, "defense_critical_fail": False,
                        "wound_threshold": "", "narrative_hint": "npc_si_avvicina",
                        "shock_applied": 0, "major_wound": False, "major_wound_check_passed": False,
                        "knockdown": False, "knockdown_check_passed": False,
                        "death_check": False, "death_check_passed": False,
                        "fp_cost": 0, "target_stunned": False, "target_prone": False,
                    },
                }
                npc_logs.append(combat_log)
                if distance > attack_range:
                    continue

        roll = sum(random.randint(1, 6) for _ in range(3))
        atk_skill = enemy.attack_skill or 10
        margin = atk_skill - roll
        hits = roll <= atk_skill and roll != 18 and not (roll == 17 and atk_skill <= 15)
        critical = roll <= 4 or (roll == 5 and atk_skill >= 15) or margin >= 10

        combat_log: dict = {
            "attacker": enemy.name,
            "target": target.name,
            "skill": "combattere",
            "skill_level": atk_skill,
            "attack_roll": roll,
            "damage_formula": enemy.damage_dice,
            "damage_type": enemy.damage_type,
            "is_npc_turn": True,
            "distance": distance,
            "attack_range": attack_range,
        }

        if not hits:
            combat_log["result"] = {
                "hit": False, "defended": False, "raw_damage": 0, "dr_absorbed": 0,
                "net_damage": 0, "attacker_margin": margin, "defense_margin": 0,
                "attacker_critical": critical, "defense_critical_fail": False,
                "wound_threshold": "", "narrative_hint": "",
                "shock_applied": 0, "major_wound": False, "major_wound_check_passed": False,
                "knockdown": False, "knockdown_check_passed": False,
                "death_check": False, "death_check_passed": False,
                "fp_cost": 0, "target_stunned": False, "target_prone": False,
            }
            npc_logs.append(combat_log)
            continue

        # Difesa automatica del giocatore (schivata passiva)
        dodge_val = target.dodge
        def_roll = sum(random.randint(1, 6) for _ in range(3))
        defended = def_roll <= dodge_val and not critical

        if defended:
            combat_log["result"] = {
                "hit": True, "defended": True, "raw_damage": 0, "dr_absorbed": 0,
                "net_damage": 0, "attacker_margin": margin, "defense_margin": dodge_val - def_roll,
                "attacker_critical": critical, "defense_critical_fail": False,
                "wound_threshold": "", "narrative_hint": "",
                "shock_applied": 0, "major_wound": False, "major_wound_check_passed": False,
                "knockdown": False, "knockdown_check_passed": False,
                "death_check": False, "death_check_passed": False,
                "fp_cost": 0, "target_stunned": False, "target_prone": False,
            }
            npc_logs.append(combat_log)
            continue

        # Colpo a segno — calcola danno
        dice_parts = re.match(r"(\d+)d(\d+)([+-]\d+)?", enemy.damage_dice or "1d6")
        if dice_parts:
            n, sides = int(dice_parts.group(1)), int(dice_parts.group(2))
            bonus = int(dice_parts.group(3) or 0)
            raw = sum(random.randint(1, sides) for _ in range(n)) + bonus
        else:
            raw = random.randint(1, 6)
        if critical:
            raw = max(raw, raw + random.randint(1, 6))
        net = max(0, raw - target.dr)
        target.hp -= net

        # Soglia danno
        wound_threshold = ""
        if target.hp <= -target.max_hp * 5:
            wound_threshold = "morto"
            target.status = "morto"
        elif target.hp <= 0:
            wound_threshold = "fuori_combattimento"
            target.status = "ferito_grave"
        elif target.hp <= target.max_hp // 3:
            wound_threshold = "ferito_grave"
            target.status = "ferito_grave"
        elif net > 0:
            wound_threshold = "ferito"
            if target.status == "ok":
                target.status = "ferito"

        shock = min(4, net) if net > 0 else 0
        target.shock_penalty = shock
        major_wound = net > target.max_hp // 2
        knockdown = target.hp <= 0

        combat_log["result"] = {
            "hit": True, "defended": False, "raw_damage": raw, "dr_absorbed": target.dr,
            "net_damage": net, "attacker_margin": margin, "defense_margin": dodge_val - def_roll,
            "attacker_critical": critical, "defense_critical_fail": False,
            "wound_threshold": wound_threshold, "narrative_hint": "",
            "shock_applied": shock, "major_wound": major_wound,
            "major_wound_check_passed": False, "knockdown": knockdown,
            "knockdown_check_passed": False,
            "death_check": target.hp < 0, "death_check_passed": target.hp >= -target.max_hp * 5,
            "fp_cost": 0, "target_stunned": False, "target_prone": knockdown,
        }
        combat_log["target_hp_after"] = target.hp
        npc_logs.append(combat_log)

    state.last_attack_result = npc_logs[-1] if npc_logs else None
    return {"npc_logs": npc_logs, "positions": positions}


# ─── PR4: Reazioni sociali ────────────────────────────────────────────────────

# Tabella reazione GURPS Lite (p.18)
_REACTION_TABLE: list[tuple[int, str, str]] = [
    # (soglia_minima, livello, descrizione)
    (17, "entusiasta",  "supporto pieno, possibile alleato duraturo"),
    (14, "amichevole",  "aiuta attivamente senza chiedere nulla in cambio"),
    (12, "favorevole",  "coopera se conveniente, aperto alla trattativa"),
    (9,  "neutro",      "né aiuta né ostacola, atteggiamento attendista"),
    (7,  "sfavorevole", "rifiuta aiuto, diffidente e sospettoso"),
    (0,  "ostile",      "ostruisce attivamente, può attaccare o tradire"),
]

_REACTION_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "ostile":      {"alleato": "tradisce la squadra al primo momento utile",
                    "antagonista": "attacca o porta rinforzi immediatamente",
                    "neutrale": "blocca ogni accesso e chiama aiuto",
                    "testimone": "nega tutto, ostacola le indagini"},
    "sfavorevole": {"alleato": "ritira temporaneamente il supporto",
                    "antagonista": "minaccia e alza la posta",
                    "neutrale": "ignora la squadra, rifiuta informazioni",
                    "testimone": "fornisce informazioni false o incomplete"},
    "neutro":      {"alleato": "mantiene gli accordi senza slancio",
                    "antagonista": "osserva e aspetta prima di agire",
                    "neutrale": "risponde solo a domande dirette",
                    "testimone": "racconta solo i fatti che conosce"},
    "favorevole":  {"alleato": "condivide risorse e informazioni rilevanti",
                    "antagonista": "apre a una trattativa o tregua",
                    "neutrale": "fornisce indicazioni utili",
                    "testimone": "racconta tutto ciò che ha visto"},
    "amichevole":  {"alleato": "si espone per proteggere la squadra",
                    "antagonista": "depone le armi se la trattativa è onesta",
                    "neutrale": "accompagna la squadra nella zona",
                    "testimone": "guida attivamente le indagini"},
    "entusiasta":  {"alleato": "si unisce alla missione come supporto attivo",
                    "antagonista": "cambia schieramento se trattato con rispetto",
                    "neutrale": "diventa una risorsa fissa per i turni successivi",
                    "testimone": "rivela dettagli nascosti e connessioni chiave"},
}


def resolve_reaction_roll(
    state: GameState,
    npc_id: str,
    interacting_player_id: int,
    social_skill_name: str = "persuadere",
) -> ReactionResult:
    """
    Tiro di reazione GURPS Lite per un WorldNPC.

    Modificatori al 3d6:
      + npc.reaction_modifier          (fisso per NPC, es. alleato +2, antagonista −2)
      + Carisma del personaggio        (advantage_skill_bonus per "persuadere")
      + bonus skill sociale            (+1 ogni 2 punti sopra 12)
      + consulted bonus                (+1 se il giocatore ha già parlato con l'NPC)
      − team_status_malus              (−1 per ferito, −2 per ferito_grave)

    Aggiorna npc.last_reaction_level e npc.last_reaction_roll in-place.
    Restituisce un ReactionResult completo.
    """
    npc = next((n for n in state.world_npcs if n.id == npc_id), None)
    if not npc:
        return ReactionResult(
            npc_id=npc_id, npc_name="???", roll=0, total=0,
            level="neutro", description="NPC non trovato",
        )

    player = next((p for p in state.players if p.id == interacting_player_id), None)

    roll = sum(random.randint(1, 6) for _ in range(3))

    # Modificatore NPC
    npc_mod = npc.reaction_modifier

    # Carisma del personaggio (bonus a persuadere da vantaggi)
    charisma_bonus = 0
    if player:
        from .data_advantages import advantage_skill_bonus
        charisma_bonus = advantage_skill_bonus(player.advantages, "persuadere")

    # Bonus skill sociale: +1 ogni 2 punti sopra 12
    skill_bonus = 0
    if player:
        skill_level = player.skills.get(social_skill_name, player.stats.get("empatia", 10))
        skill_bonus = max(0, (skill_level - 12) // 2)

    # Bonus consulted
    consulted_bonus = 1 if npc.consulted else 0

    # Malus stato della squadra (prende il peggio tra i giocatori)
    worst_status = "ok"
    status_order = {"ok": 0, "ferito": 1, "ferito_grave": 2, "fuori_combattimento": 3}
    for p in state.players:
        if status_order.get(p.status, 0) > status_order.get(worst_status, 0):
            worst_status = p.status
    team_status_malus = {"ferito": 1, "ferito_grave": 2, "fuori_combattimento": 3}.get(worst_status, 0)

    total = roll + npc_mod + charisma_bonus + skill_bonus + consulted_bonus - team_status_malus
    total = max(3, min(total, 24))  # clamp ragionevole

    # Lookup livello
    level = "ostile"
    for threshold, lvl, _ in _REACTION_TABLE:
        if total >= threshold:
            level = lvl
            break

    # Descrizione specifica per ruolo NPC
    npc_role_key = npc.role if npc.role in _REACTION_DESCRIPTIONS.get(level, {}) else "neutrale"
    description = _REACTION_DESCRIPTIONS.get(level, {}).get(npc_role_key, "reagisce in modo neutro")

    # Aggiorna NPC in-place
    npc.last_reaction_level = level
    npc.last_reaction_roll = total

    return ReactionResult(
        npc_id=npc_id,
        npc_name=npc.name,
        roll=roll,
        total=total,
        level=level,
        description=description,
        charisma_bonus=charisma_bonus,
        skill_bonus=skill_bonus,
        consulted_bonus=consulted_bonus,
        npc_modifier=npc_mod,
        team_status_malus=team_status_malus,
    )


def preview_action_outcomes(
    state: GameState,
    player_id: int,
    intent: str = "",
    structured_intent: dict | None = None,
    custom_intents: dict[int, str] | None = None,
) -> dict:
    if state.in_setup or not state.scene or not state.mission:
        return {"available": False, "reason": "game_not_ready"}
    player = next((p for p in state.players if p.id == player_id), None)
    if not player:
        return {"available": False, "reason": "player_not_found"}
    if player.hp <= 0:
        return {"available": False, "reason": "player_unavailable"}

    clean_intent = str(intent or "").strip()
    structured_intent = structured_intent or {}
    custom_intents = custom_intents or {}
    shared_context = " ".join(
        str(text or "").strip()
        for pid, text in custom_intents.items()
        if int(pid) != player_id and str(text or "").strip()
    )
    current_node = state.map_state.nodes.get(state.map_state.current_node_id) if state.map_state else None

    if structured_intent:
        action = _action_from_structured_intent(player, structured_intent, state)
    elif clean_intent:
        action = _infer_action_from_intent(
            player,
            clean_intent,
            state.scene.scene_tags,
            shared_context=shared_context,
            scene_problem=_scene_problem_context(state, current_node),
        )
    else:
        return {"available": False, "reason": "empty_intent"}

    if action.requires_item and action.requires_item not in player.items:
        return {"available": False, "reason": "missing_item", "required_item": action.requires_item}

    # Preview GURPS Lite: itera su tutti i 16 esiti possibili di 3d6 (3-18) e calcola
    # la probabilità di ciascun outcome usando la distribuzione esatta (216 combinazioni).
    outcomes = []
    for roll in range(3, 19):
        result = _resolve_action_roll(state, player, action, clean_intent, shared_context, current_node, roll)
        result["_weight"] = _3D6_OUTCOMES[roll]
        outcomes.append(result)

    # Aggrego "fallimento critico" sotto "fallimento" e "critico" resta a sé per il preview UX.
    grouped: dict[str, list[dict]] = {"critico": [], "successo pieno": [], "successo parziale": [], "fallimento": []}
    for outcome in outcomes:
        bucket_key = "fallimento" if outcome["outcome"] == "fallimento critico" else outcome["outcome"]
        grouped[bucket_key].append(outcome)

    rows = []
    for key in ("critico", "successo pieno", "successo parziale", "fallimento"):
        bucket = grouped[key]
        weights = [entry["_weight"] for entry in bucket] or [0]
        total_weight = sum(weights)
        progress_values = [entry["effect"].get("progress", 0) for entry in bucket] or [0]
        threat_values = [entry["effect"].get("threat", 0) for entry in bucket] or [0]
        time_values = []
        for entry in bucket:
            bonus = entry["effect"].get("time_bonus", 0)
            if bonus > 0:
                time_values.append(bonus)
            elif entry["effect"].get("progress", 0) <= 0:
                time_values.append(-1)
            else:
                time_values.append(0)
        if not time_values:
            time_values = [0]
        rows.append({
            "key": key,
            "label": key,
            "probability": round((total_weight / _3D6_TOTAL) * 100, 1),
            "rolls": [entry["roll"] for entry in bucket],
            "progress": {"min": min(progress_values), "max": max(progress_values)},
            "threat": {"min": min(threat_values), "max": max(threat_values)},
            "time": {"min": min(time_values), "max": max(time_values)},
            "notes": _unique_preserve([entry["scene_gate_note"] for entry in bucket if entry["scene_gate_note"]], limit=2),
        })

    semantic_tags = _infer_semantic_tags(" ".join(x for x in [shared_context, clean_intent, action.name, action.description] if x))
    return {
        "available": True,
        "player_id": player_id,
        "action": {
            "name": action.name,
            "stat": action.stat,
            "skill": action.skill or default_skill_for(action.stat, action.effect_type),
            "effect_type": SKILL_TO_EFFECT_TYPE.get(action.skill or "", action.effect_type),
            "difficulty": action.difficulty,
            "action_role": action.action_role,
            "requires_item": action.requires_item,
            "semantic_tags": semantic_tags,
        },
        "rows": rows,
    }


def _infer_semantic_tags(text: str) -> list[str]:
    tokens = _tokenize_intent(text)
    tag_roots = {
        "stealth": {"ombra", "furtiv", "silenz", "aggirar", "infiltr", "schivar"},
        "protezione": {"coprir", "difend", "protegger", "scud", "tener", "sostener"},
        "analisi": {"anal", "scansion", "decifr", "osserv", "capir", "traccia", "indizio", "campione"},
        "pressione": {"rapid", "subito", "ora", "forzar", "sfond", "assalt", "corr"},
        "forza": {"sping", "colpir", "bloccar", "trascin", "sfond", "forza"},
        "sociale": {"parlar", "convinc", "negozi", "calmar", "persuad", "mentir", "ingann"},
        "cura": {"curar", "stabil", "soccor", "medic", "salvar"},
        "recupero": {"recuper", "prender", "estrarr", "portar", "salvare"},
        "temporale": {"tempo", "frequenz", "sfera", "sincronizz", "ritual", "halstrom"},
        "prudenza": {"prud", "piano", "sicuro", "attent", "contener", "profilo"},
    }
    tags: list[str] = []
    for tag, roots in tag_roots.items():
        if any(any(tok.startswith(root) for tok in tokens) for root in roots):
            tags.append(tag)
    return tags


def _apply_tag_modifiers(effect: dict, tags: list[str], effect_type: str) -> dict:
    adjusted = dict(effect)
    tag_set = set(tags)
    can_gain_progress = adjusted.get("progress", 0) > 0

    if "stealth" in tag_set or "prudenza" in tag_set:
        adjusted["threat"] -= 1
    if "protezione" in tag_set or "cura" in tag_set:
        adjusted["threat"] -= 1
        adjusted["time_bonus"] = adjusted.get("time_bonus", 0) + 1
    if "pressione" in tag_set:
        if can_gain_progress:
            adjusted["progress"] += 1
        adjusted["threat"] += 1
    if can_gain_progress and "forza" in tag_set and effect_type in {"combattere", "forzare", "recuperare"}:
        adjusted["progress"] += 1
    if can_gain_progress and "analisi" in tag_set and effect_type in {"investigare", "rilevare", "decifrare"}:
        adjusted["progress"] += 1
    if "sociale" in tag_set and effect_type in {"negoziare", "ingannare"}:
        adjusted["threat"] -= 1
    if can_gain_progress and "temporale" in tag_set and effect_type in {"decifrare", "rilevare", "evocare"}:
        adjusted["progress"] += 1

    return adjusted


def _apply_scene_solution_gate(
    effect: dict,
    state: GameState,
    current_node: MapNode | None,
    action: Action,
    intent: str,
) -> tuple[dict, str]:
    profile = _derive_scene_solution_profile(state, current_node)
    action_text = " ".join(
        x for x in [intent, action.name, action.description, action.skill, action.effect_type] if x
    )
    action_tokens = _scene_keyword_roots(action_text)
    matched_keywords = _matching_scene_keywords(action_tokens, profile["keywords"])
    effect_allowed = action.effect_type in profile["allowed_effect_types"]
    effect_blocked = action.effect_type in profile.get("blocked_effect_types", set())
    support_move = action.action_role == "support" or action.effect_type in profile["support_effect_types"]
    adjusted = dict(effect)

    if effect_blocked and not support_move:
        adjusted["progress"] = 0
        adjusted["time_bonus"] = 0
        adjusted["story_hint"] = "approccio_sbagliato"
        adjusted["threat"] = max(adjusted.get("threat", 0), 1)
        note = "approccio sbagliato per questo tipo di problema"
        return adjusted, note

    if effect_allowed and matched_keywords:
        if adjusted.get("progress", 0) > 0 and len(matched_keywords) >= 2:
            adjusted["progress"] += 1
        note = "aggancio forte al problema locale"
        return adjusted, note

    if support_move and (matched_keywords or effect_allowed):
        adjusted["progress"] = 0
        adjusted["story_hint"] = "supporto_utile_ma_non_risolutivo"
        note = "azione utile di supporto, ma non risolve il problema locale"
        return adjusted, note

    if effect_allowed and not matched_keywords:
        adjusted["progress"] = min(adjusted.get("progress", 0), 1)
        adjusted["story_hint"] = "approccio_giusto_ma_vago"
        note = "approccio plausibile, ma mancano parole chiave o un bersaglio chiaro"
        return adjusted, note

    adjusted["progress"] = 0
    adjusted["time_bonus"] = 0
    adjusted["story_hint"] = "azione_fuori_contesto"
    adjusted["threat"] = max(adjusted.get("threat", 0), 1)
    note = "fuori contesto: non aggancia il problema della zona"
    return adjusted, note


def _infer_action_from_intent(
    player: Player,
    intent: str,
    scene_tags: list[str],
    shared_context: str = "",
    scene_problem: str = "",
) -> Action:
    combined_context = " ".join(x for x in [shared_context, scene_problem, intent] if x).strip()
    tokens = _tokenize_intent(combined_context)
    tags = {t.lower() for t in scene_tags}

    stat_keywords = {
        "forza": {"forza", "sping", "forzar", "sfond", "colpir", "bloccar", "trascin", "coprir", "difend", "tratten", "demol", "abbatter"},
        "agilita": {"agil", "scattar", "muover", "corr", "salt", "schivar", "furtiv", "ombra", "aggirar", "infiltr", "scassin", "pedin"},
        "intelligenza": {"anal", "capir", "stud", "scansion", "decifr", "hacker", "calibr", "osserv", "traccia", "indizio", "campione", "ingegner", "scient"},
        "empatia": {"parlar", "calmar", "convinc", "curar", "soccorr", "aiutar", "guidar", "protegger", "timar", "negozi", "intratten", "etichett"},
    }
    stat_scores: dict[str, int] = {}
    for stat, roots in stat_keywords.items():
        stat_scores[stat] = sum(2 for root in roots if any(tok.startswith(root) for tok in tokens))
        stat_scores[stat] += player.stats.get(stat, 0)
    stat = max(stat_scores, key=stat_scores.get)

    mechanical_target = any(tok.startswith(root) for root in (
        "lucchett", "serratur", "chiavistell", "pannell", "consolle", "console",
        "terminal", "boccaport", "porta", "rampa",
    ) for tok in tokens)
    if mechanical_target and any(tok.startswith(root) for root in ("sequenz", "codic", "cifr", "numer", "password", "led") for tok in tokens):
        effect_type = "decifrare"
    elif mechanical_target and any(tok.startswith(root) for root in ("colpir", "colpi", "sfond", "romp", "forzar", "apr", "sbloc", "scassin", "manomet", "smont") for tok in tokens):
        effect_type = "forzare"
    else:
        effect_type = "investigare"

    effect_map = [
        ("stabilizzare", {"curar", "stabil", "soccor", "medic", "salvar"}),
        ("difendere", {"coprir", "protegger", "difend", "scud", "tener"}),
        ("negoziare", {"parlar", "convinc", "negozi", "calmar", "persuad"}),
        ("decifrare", {"decifr", "tradur", "decritt"}),
        ("rilevare", {"scanner", "scansion", "traccia", "rilev", "monitor", "pedin", "scient"}),
        ("combattere", {"spar", "colpir", "attacc", "neutralizz", "abbatter"}),
        ("infiltrarsi", {"furtiv", "ombra", "aggirar", "infiltr", "schivar"}),
        ("forzare", {"forzar", "aprire", "sfond", "sbloccar", "manomet", "demol", "ripar", "ingegner", "scassin"}),
        ("recuperare", {"recuper", "prender", "portar", "salvare", "estrarr"}),
        ("investigare", {"anal", "capir", "osserv", "indizio", "cercar", "esamin"}),
        ("ingannare", {"ingann", "fing", "depistar", "bluff"}),
        ("evocare", {"attivar", "sincronizz", "sfera", "frequenz", "ritual"}),
    ]
    if effect_type == "investigare":
        for candidate, roots in effect_map:
            if any(any(tok.startswith(root) for tok in tokens) for root in roots):
                effect_type = candidate
                break
    skill_map = [
        ("combattere", {"combatt", "spar", "attacc", "colpir", "abbatter"}),
        ("resistere", {"resist", "tenere", "sopport", "regger"}),
        ("forzare", {"forzar", "sfond", "romper", "aprire"}),
        ("proteggere", {"protegger", "coprir", "scud", "difend"}),
        ("trasportare", {"trascin", "portar", "sollev", "spostar"}),
        ("intimidire", {"intimid", "minacc", "pression"}),
        ("lottare", {"lott", "bloccar", "immobilizz", "disarm"}),
        ("sopravvivere", {"sopravviv", "resister", "riparar", "risorsa"}),
        ("demolire", {"demol", "abbatter", "distrugg", "esplos"}),
        ("schivare", {"schiv", "evitar", "scansar"}),
        ("furtivita", {"furtiv", "silenz", "ombra", "nascost"}),
        ("acrobazia", {"salt", "arramp", "equilibr", "acrob"}),
        ("rapidita", {"rapid", "scattar", "subito", "veloc"}),
        ("mira", {"mir", "spar", "cecchin", "colpo"}),
        ("guidare", {"guid", "pilot", "veicol", "insegu"}),
        ("scassinare", {"scassin", "grimald", "serratur", "lucchett"}),
        ("manualita", {"manipol", "disinnesc"}),
        ("infiltrarsi", {"infiltr", "aggirar", "entrare", "superar"}),
        ("pedinare", {"pedin", "seguire", "sorvegli", "appostar"}),
        ("investigare", {"investig", "indizio", "cercar", "ricostru"}),
        ("analizzare", {"anal", "campione", "dato", "schema"}),
        ("tecnologia", {"hacker", "tecnolog", "sistema", "ripar", "computer"}),
        ("medicina", {"medic", "diagnos", "anatom", "farmac"}),
        ("scienze", {"scient", "scienza", "chimic", "fisic", "biolog", "laborator"}),
        ("cultura", {"storia", "occult", "sapere", "arcano"}),
        ("strategia", {"strateg", "piano", "tattic", "coordin"}),
        ("decifrare", {"decifr", "codice", "simbol", "lingua", "traduc"}),
        ("osservare", {"osserv", "notar", "veder", "traccia"}),
        ("ingegneria", {"ingegner", "ripar", "progettar", "costruir", "macchin"}),
        ("persuadere", {"persuad", "convinc", "negozi", "parlar"}),
        ("ingannare", {"ingann", "ment", "bluff", "fing"}),
        ("intuire", {"intuir", "capire", "emozion", "intenzion"}),
        ("calmare", {"calmar", "tranquill", "panico"}),
        ("ispirare", {"ispir", "coraggio", "motiv", "morale"}),
        ("curare", {"curar", "soccorr", "stabilizz", "ferita"}),
        ("comandare", {"comand", "ordine", "guidar", "leader"}),
        ("comunicare", {"comunic", "radio", "messaggio", "mediare"}),
        ("intrattenere", {"intratten", "recitar", "cant", "suonar", "distrarre"}),
        ("etichetta", {"etichett", "protocol", "cerimon", "corte", "formal"}),
    ]
    skill = default_skill_for(stat, effect_type)
    if mechanical_target and effect_type == "forzare":
        skill = "forzare"
        stat = "forza" if player.stats.get("forza", 0) >= player.stats.get("intelligenza", 0) else "intelligenza"
        if stat == "intelligenza":
            skill = "tecnologia"
    elif mechanical_target and effect_type == "decifrare":
        skill = "decifrare"
        stat = "intelligenza"
    else:
        matched_skills: list[str] = []
        for candidate, roots in skill_map:
            if candidate in VALID_SKILLS and any(any(tok.startswith(root) for tok in tokens) for root in roots):
                matched_skills.append(candidate)
        if matched_skills:
            # Preferisce la skill con livello più alto tra quelle possedute dal personaggio
            owned = [(s, player.skills.get(s, 0)) for s in matched_skills if s in player.skills]
            if owned:
                skill = max(owned, key=lambda x: x[1])[0]
            else:
                skill = matched_skills[0]
            effect_type = SKILL_TO_EFFECT_TYPE.get(skill, effect_type)

    action_role = "core"
    if effect_type in {"stabilizzare", "difendere", "negoziare"} or "supporto" in tags:
        action_role = "support"
    if effect_type in {"infiltrarsi", "ingannare", "evocare"} or any(tok.startswith(root) for root in ("disper", "azzard", "risch", "furtiv") for tok in tokens):
        action_role = "risk"

    # Difficoltà base: dipende da phase/scene/threat, non sempre 1
    scene_threat = state.scene.threat_level if state.scene else 1
    time_left = state.scene.time_left if state.scene else 4
    time_limit = state.scene.time_limit if state.scene else 4
    phase_idx = state.phase.phase_index if state.phase else 1

    # Base: 1 in fase 1, 2 in fase 2, 3 in fase finale
    difficulty = min(phase_idx, 3)

    # Pressione temporale: se rimane poco tempo aumenta di 1
    if time_limit > 0 and time_left <= time_limit // 2:
        difficulty = min(4, difficulty + 1)

    # Alta minaccia: ulteriore +1
    if scene_threat >= 3:
        difficulty = min(4, difficulty + 1)

    # Parole chiave nell'intento che indicano azione difficile
    if any(tok.startswith(root) for root in ("disper", "imposs", "estrem", "forzar", "sotto", "rapid") for tok in tokens):
        difficulty = min(4, difficulty + 1)

    # Crisi + azione fisica/rischiosa
    if "crisi" in tags and effect_type in {"combattere", "forzare", "infiltrarsi"}:
        difficulty = min(4, max(difficulty, 2))

    requires_item = None
    for item in player.items:
        item_tokens = _tokenize_intent(item)
        if tokens & item_tokens:
            requires_item = item
            break

    candidate_scores: list[tuple[int, Action]] = []
    for action in player.actions:
        score = 0
        action_tokens = _tokenize_intent(f"{action.name} {action.description} {action.skill} {action.effect_type} {action.stat}")
        score += len(tokens & action_tokens) * 3
        if action.stat == stat:
            score += 2
        if action.skill == skill:
            score += 3
        if action.effect_type == effect_type:
            score += 3
        if action.action_role == action_role:
            score += 1
        if action.requires_item and action.requires_item in player.items:
            score += 1
        candidate_scores.append((score, action))
    if candidate_scores:
        best_score, best_action = max(candidate_scores, key=lambda x: x[0])
        if best_score >= 3 and (not mechanical_target or best_action.effect_type == effect_type):
            return Action(
                name=intent.strip()[:60],
                stat=best_action.stat,
                skill=best_action.skill or default_skill_for(best_action.stat, best_action.effect_type),
                difficulty=max(difficulty, best_action.difficulty),
                effect_type=best_action.effect_type,
                action_role=best_action.action_role,
                requires_item=best_action.requires_item,
                source="intent",
                description=f"Piano libero: {intent.strip()[:100]}",
            )

    return Action(
        name=intent.strip()[:60] or "Agire sul problema",
        stat=stat,
        skill=skill,
        difficulty=difficulty,
        effect_type=effect_type,
        action_role=action_role,
        requires_item=requires_item,
        source="intent",
        description=f"Piano libero: {intent.strip()[:100]}",
    )


def _stat_for_skill(skill: str, fallback: str = "intelligenza") -> str:
    for stat, skills in SKILLS_BY_STAT.items():
        if skill in skills:
            return stat
    return fallback


def _action_from_structured_intent(player: Player, data: dict, state: GameState) -> Action:
    raw_skill = str(data.get("skill") or "").strip()
    skill = raw_skill if raw_skill in VALID_SKILLS else default_skill_for("intelligenza", "")
    stat = _stat_for_skill(skill)
    effect_type = SKILL_TO_EFFECT_TYPE.get(skill, "investigare")
    intent = str(data.get("intent") or "agire").strip()
    target_id = str(data.get("target_id") or "").strip()
    target_name = str(data.get("target_name") or "").strip()
    item = str(data.get("item") or "").strip() or None
    if item and item not in player.items:
        item = None

    target = next((e for e in (state.scene.entities if state.scene else []) if e.id == target_id), None)
    if target and not target_name:
        target_name = target.name
    target_label = target_name or "la situazione"

    lname = " ".join([intent, target_label, skill]).lower()
    if any(word in lname for word in ["protegg", "copr", "cur", "calm", "ispir", "aiut", "difend", "assist", "support", "sostien"]):
        action_role = "support"
    elif any(word in lname for word in ["uccid", "elimin", "risch", "disper", "furtiv", "ingann", "sacrific"]):
        action_role = "risk"
    else:
        action_role = "core"

    scene_threat = state.scene.threat_level if state.scene else 1
    time_left = state.scene.time_left if state.scene else 4
    time_limit = state.scene.time_limit if state.scene else 4
    phase_idx = state.phase.phase_index if state.phase else 1

    difficulty = min(phase_idx, 3)
    if time_limit > 0 and time_left <= time_limit // 2:
        difficulty = min(4, difficulty + 1)
    if scene_threat >= 3:
        difficulty = min(4, difficulty + 1)
    if target and target.type == "enemy":
        difficulty = min(4, max(difficulty, 2))
    if state.scene and state.scene.threat_level >= 8:
        difficulty = min(4, difficulty + 1)

    name = f"{intent.capitalize()} {target_label}"[:60]
    item_text = f" con {item}" if item else ""
    description = f"{player.name} prova a {intent} {target_label}{item_text} usando {skill}."
    return Action(
        name=name,
        stat=stat,
        skill=skill,
        difficulty=difficulty,
        effect_type=effect_type,
        action_role=action_role,
        requires_item=item,
        source="builder",
        description=description[:120],
    )


def resolve_actions(
    state: GameState,
    selected_actions: dict[int, str],
    custom_intents: dict[int, str] | None = None,
    structured_intents: dict[int, dict] | None = None,
) -> GameState:
    if state.in_setup:
        state.log = "Completa prima la selezione del team."
        return state
    if state.mission.completed or state.mission.failed:
        state.log = "La missione è già conclusa."
        state.selected_actions = {}
        return state

    log_lines = []
    chosen_action_names = {}
    used_actions = []
    used_effect_types = []
    effect_types_this_turn: dict[str, str] = {}  # effect_type → nome primo personaggio che l'ha usato
    story_hints_collected = []
    per_player_outcomes: list[dict] = []  # {name, action, outcome, hint} — vincolante per Claude
    npc_clue_bonuses: list[dict] = []  # discovered_facts da NPC consultati questo turno
    previous_scene_text = state.scene.scene_text
    previous_turn = state.turn
    total_progress = 0
    total_threat_change = 0
    total_time_bonus = 0
    custom_intents = custom_intents or {}
    structured_intents = structured_intents or {}
    shared_context = " ".join(
        str(custom_intents.get(player.id, "")).strip()
        for player in state.players
        if str(custom_intents.get(player.id, "")).strip()
    )
    current_node = state.map_state.nodes.get(state.map_state.current_node_id) if state.map_state else None
    scene_problem = _scene_problem_context(state, current_node)

    for player in state.players:
        chosen = selected_actions.get(player.id)
        intent = str(custom_intents.get(player.id, "")).strip()
        structured = structured_intents.get(player.id) or structured_intents.get(str(player.id))
        if not chosen and not structured:
            if not intent:
                continue
        if player.hp <= 0:
            log_lines.append(f"{player.name} è fuori combattimento e non può agire.")
            continue
        action = _action_from_structured_intent(player, structured, state) if structured else _infer_action_from_intent(
            player,
            intent,
            state.scene.scene_tags,
            shared_context=shared_context,
            scene_problem=scene_problem,
        ) if intent else next((a for a in player.actions if a.name == chosen), None)
        if not action:
            continue
        if action.requires_item and action.requires_item not in player.items:
            log_lines.append(f"{player.name} non può usare '{action.name}' perché non possiede {action.requires_item}.")
            continue

        shown_plan = intent or action.description or action.name
        chosen_action_names[player.name] = shown_plan
        used_actions.append(action.name)

        # Coordinamento: +2 se un altro personaggio ha già agito sullo stesso effect_type
        anticipated_effect_type = SKILL_TO_EFFECT_TYPE.get(
            normalize_skill(action.skill) if action.skill else default_skill_for(action.stat, action.effect_type),
            action.effect_type,
        )
        coord_bonus = 0
        coord_with = None
        if anticipated_effect_type in effect_types_this_turn:
            coord_bonus = 2
            coord_with = effect_types_this_turn[anticipated_effect_type]

        roll_3d6 = sum(random.randint(1, 6) for _ in range(3))
        roll_result = _resolve_action_roll(state, player, action, intent, shared_context, current_node, roll_3d6, coordination_bonus=coord_bonus)
        used_effect_types.append(roll_result["effect_type"])

        # Registra effect_type per eventuali personaggi successivi (solo il primo attiva il bonus)
        if roll_result["effect_type"] not in effect_types_this_turn:
            effect_types_this_turn[roll_result["effect_type"]] = player.name
        semantic_tags = roll_result["semantic_tags"]
        skill = roll_result["skill"]
        effect_type = roll_result["effect_type"]
        effect = roll_result["effect"]
        scene_gate_note = roll_result["scene_gate_note"]
        outcome = roll_result["outcome"]
        outcome_reason = roll_result["outcome_reason"]
        margin = roll_result["margin"]
        effective_skill = roll_result["effective_skill"]
        base_skill_level = roll_result["base_skill_level"]
        skill_known = roll_result["skill_known"]
        roll = roll_result["roll"]
        status_malus = roll_result["status_malus"]
        threat_malus = roll_result["threat_malus"]
        difficulty = roll_result["difficulty"]
        item_bonus = roll_result["item_bonus"]
        adv_bonus = roll_result["adv_bonus"]

        total_progress += effect["progress"]
        total_threat_change += effect["threat"]
        total_time_bonus += effect.get("time_bonus", 0)
        story_hints_collected.append(effect["story_hint"])
        # Bonus NPC: se l'azione è dialogica/investigativa e nel nodo c'è un NPC chiave non
        # ancora consultato, estrai un indizio extra agganciato al thread che l'NPC custodisce.
        bonus_facts = collect_npc_clue_bonuses(state, effect_type, outcome, player.name)
        if bonus_facts:
            npc_clue_bonuses.extend(bonus_facts)
            for bf in bonus_facts:
                log_lines.append(f"  ↳ NPC clue: indizio bonus per thread {bf['clue_for_thread']}")
        effect_text = format_action_effect(effect)

        verb = "tenta" if intent else "usa"
        item_text = f" | oggetto={action.requires_item}" if action.requires_item else ""
        item_formula = f" + oggetto({action.requires_item})=+{item_bonus}" if item_bonus else ""
        adv_formula = f" + vantaggi={adv_bonus:+d}" if adv_bonus != 0 else ""
        coord_formula = f" + coord.={coord_bonus:+d}" if coord_bonus else ""
        skill_label = f"{skill} {base_skill_level}" if skill_known else f"{skill}(default {base_skill_level})"
        log_lines.append(
            f"{player.name} {verb} '{action.name}' [{skill_label} | {effect_type} | {action.action_role}{item_text}] "
            f"(3d6={roll} vs abilità eff. {effective_skill} = base {base_skill_level}{item_formula}{adv_formula}{coord_formula} "
            f"- difficoltà={difficulty} - status/ferite={status_malus} - minaccia={threat_malus}; margine={margin:+d}) "
            f"→ {outcome} ({outcome_reason}) | effetto: {effect_text}"
        )
        if coord_bonus:
            log_lines.append(f"  ↳ coordinamento: {player.name} agisce in sinergia con {coord_with} (stesso approccio '{effect_type}') → +{coord_bonus} all'abilità effettiva")
        log_lines.append(
            f"  ↳ meccanica GURPS: 3d6 ≤ {effective_skill} → {'successo' if margin >= 0 else 'fallimento'} "
            f"con margine {margin:+d}; skill '{skill}' mappa su effetto '{effect_type}'."
        )

        # Accumula esito vincolante per personaggio (enforcement narrativo)
        outcome_label = {
            "critico": "SUCCESSO CRITICO",
            "successo pieno": "SUCCESSO PIENO",
            "successo parziale": "SUCCESSO PARZIALE",
            "fallimento": "FALLIMENTO",
            "fallimento critico": "FALLIMENTO CRITICO",
        }.get(outcome, outcome.upper())
        hint_desc = effect.get("story_hint", "")
        per_player_outcomes.append({
            "name": player.name,
            "action": shown_plan,
            "outcome": outcome_label,
            "hint": hint_desc,
            "margin": margin,
            # dati formula completa per il playtest
            "rolled": roll,
            "skill": skill,
            "skill_known": skill_known,
            "base_skill": base_skill_level,
            "item_bonus": item_bonus,
            "adv_bonus": adv_bonus,
            "adv_breakdown": roll_result.get("adv_breakdown", []),
            "environmental_trait_modifiers": roll_result.get("environmental_trait_modifiers", []),
            "luck": roll_result.get("luck"),
            "coord_bonus": coord_bonus,
            "difficulty": difficulty,
            "status_malus": status_malus,
            "threat_malus": threat_malus,
            "effective_skill": effective_skill,
            "success": margin >= 0,
            "critical": outcome in ("critico", "fallimento critico"),
        })
        if action.requires_item:
            log_lines.append(f"  ↳ oggetto: {action.requires_item} usato come requisito e bonus +{item_bonus} al tiro")
        if semantic_tags:
            log_lines.append(f"  ↳ tag letti: {', '.join(semantic_tags)}")
        if scene_gate_note:
            log_lines.append(f"  ↳ problema zona: {scene_gate_note}")

        # Danno HP al personaggio agente (combattere/evocare su parziale o fallimento)
        if effect["self_damage"] > 0:
            player.hp = max(0, player.hp - effect["self_damage"])
            player.status = hp_to_status(player.hp, player.max_hp)
            damage_fiction = explain_self_damage(skill, effect["story_hint"], state.scene.scene_tags, effect["self_damage"])
            log_lines.append(f"  ↳ danno fiction: {player.name} {damage_fiction} Stato: {player.status}.")

        # Guarigione (stabilizzare) — cura l'alleato più ferito, o sé stesso
        # heal=1 → +3 HP, heal=2 → +5 HP
        if effect["heal"] > 0:
            hp_restored = 3 if effect["heal"] == 1 else 5
            targets = sorted(
                [p for p in state.players if 0 < p.hp < p.max_hp],
                key=lambda p: p.hp / max(p.max_hp, 1)
            )
            if not targets:
                targets = [player]
            target = targets[0]
            target.hp = min(target.max_hp, target.hp + hp_restored)
            target.status = hp_to_status(target.hp, target.max_hp)
            log_lines.append(f"  ↳ {target.name} recupera {hp_restored} HP ({target.hp}/{target.max_hp} — {target.status})")

    # Azioni investigative avanzano i thread anche senza story_hint esplicito (se il dado ha prodotto progresso)
    investigative_effects = {"investigare", "rilevare", "decifrare"}
    if total_progress > 0 and any(e in investigative_effects for e in used_effect_types):
        if state.story and state.story.active_threads:
            for t in state.story.active_threads:
                if t not in state.story.thread_progress:
                    state.story.thread_progress[t] = 0
            # Avanza il thread con meno progresso di 1 punto
            least = min(state.story.active_threads, key=lambda t: state.story.thread_progress.get(t, 0))
            state.story.thread_progress[least] = min(3, state.story.thread_progress.get(least, 0) + 1)

    # Tempo: scende solo se il turno non ha prodotto alcun progresso (tutti fallimenti)
    # e solo se il timer è attivo (time_limit > 0)
    if state.scene.time_limit > 0:
        if total_progress <= 0:
            state.scene.time_left = max(0, state.scene.time_left - 1)
        if total_time_bonus > 0:
            state.scene.time_left = min(state.scene.time_limit, state.scene.time_left + total_time_bonus)
    state.scene.objective_progress += total_progress
    state.scene.threat_level += total_threat_change
    state.scene.objective_progress = max(0, min(state.scene.objective_progress, state.scene.objective_target))
    state.scene.threat_level = max(0, min(state.scene.threat_level, 10))

    if state.scene.objective_progress >= state.scene.objective_target:
        scene_result = "ESITO GLOBALE: obiettivo locale completato"
        scene_transition = "success"
    elif state.scene.time_limit > 0 and state.scene.time_left == 0:
        scene_result = "ESITO GLOBALE: tempo scaduto"
        scene_transition = "timeout"
    elif state.scene.threat_level >= 9:
        scene_result = "ESITO GLOBALE: minaccia critica"
        scene_transition = "crisis"
    else:
        scene_result = "ESITO GLOBALE: situazione ancora aperta"
        scene_transition = "continue"

    # Quality of outcome — distingue successo pulito da sporco e popola il nodo che si lascia
    encounter_outcome = ""
    clue_yield = 0
    time_bonus = 0
    if scene_transition == "success":
        if state.scene.threat_level <= 4:
            encounter_outcome = "success_clean"
            clue_yield = 2
            time_bonus = 1
        else:
            encounter_outcome = "success_dirty"
            clue_yield = 1
            time_bonus = 0
    elif scene_transition == "timeout":
        encounter_outcome = "timeout"
        clue_yield = 1
        time_bonus = -1
    elif scene_transition == "crisis":
        encounter_outcome = "crisis"
        clue_yield = 0
        time_bonus = -2

    if encounter_outcome and state.map_state:
        leaving_node = state.map_state.nodes.get(state.map_state.current_node_id)
        if leaving_node:
            leaving_node.outcome = encounter_outcome
            leaving_node.clue_yield = clue_yield
            leaving_node.time_bonus_for_next = time_bonus
            leaving_node.outcome_summary = {
                "success_clean": "zona risolta con margine",
                "success_dirty": "zona risolta a fatica",
                "timeout": "tempo scaduto, zona compromessa",
                "crisis": "zona collassata",
            }.get(encounter_outcome, "")

    # Movimento NPC persistenti su transizioni "forti" (la squadra ha appena chiuso un encounter)
    if scene_transition in {"success", "timeout", "crisis"}:
        npc_notes = move_world_npcs(state, scene_transition)
        for n in npc_notes:
            log_lines.append(f"  ↳ NPC: {n}.")

    map_notes = apply_map_persistence_from_effects(state, used_effect_types, scene_transition)
    for note in map_notes:
        log_lines.append(f"  ↳ mappa: {note}.")

    if scene_transition == "timeout":
        hp_hit = 2 if state.scene.threat_level < 6 else 3
        num_hit = 1 if state.scene.threat_level < 6 else 2
        inflict_damage(state.players, hp_hit, num_hit)
        log_lines.append(f"Conseguenza scena: tempo scaduto | -{hp_hit} HP a {num_hit} membro/i")
    if scene_transition == "crisis":
        inflict_damage(state.players, 3, 1)
        log_lines.append("Conseguenza scena: minaccia critica | -3 HP a 1 membro")

    technical_log = "\n".join(log_lines + ["", scene_result])
    state.log = technical_log  # log tecnico — visibile solo in debug

    # Progressione missione solo su nodo giusto
    current_node = state.map_state.nodes[state.map_state.current_node_id] if state.map_state else None
    if scene_transition == "success" and current_node:
        if current_node.phase_gate == state.phase.phase_index:
            state.mission.mission_progress += 1
        if current_node.is_objective:
            state.mission.goal_resolved = True
            append_unique(state.story.resolved_threads, [f"Obiettivo della missione → La squadra raggiunge {current_node.name} e può completare: {state.mission.objective}"])
        update_phase(state)

    fail_now, fail_reason = mission_should_fail(state)
    if fail_now:
        state.mission.failed = True
        summary = f"Missione: {state.mission.title}. Obiettivo non raggiunto. Motivo: {fail_reason}"
        story_ctx = {
            "resolved_threads": state.story.resolved_threads if state.story else [],
            "discovered_facts": state.story.discovered_facts if state.story else [],
            "named_entities": state.story.named_entities if state.story else [],
        }
        ending = generate_mission_ending(state.mission.title, state.mission.objective, False, summary, story_context=story_ctx)
        state.mission.ending_text = ending
        state.scene.scene_text = ending
        state.log = ending + "\n\n---\n" + technical_log
        state.selected_actions = {}
        return state

    # Finale vero solo sul nodo finale + goal risolto
    if current_node and current_node.is_final and state.mission.goal_resolved and scene_transition == "success":
        state.mission.completed = True
        summary = f"Missione: {state.mission.title}. Obiettivo: {state.mission.objective}. Completata in {state.turn} turni."
        story_ctx = {
            "resolved_threads": state.story.resolved_threads if state.story else [],
            "discovered_facts": state.story.discovered_facts if state.story else [],
            "named_entities": state.story.named_entities if state.story else [],
        }
        ending = generate_mission_ending(state.mission.title, state.mission.objective, True, summary, story_context=story_ctx)
        state.mission.ending_text = ending
        state.scene.scene_text = ending
        state.log = ending + "\n\n---\n" + technical_log
        state.selected_actions = {}
        return state

    memory_line = (
        f"Turno {previous_turn}: nodo={state.map_state.current_node_id if state.map_state else 'n/a'} | "
        f"scena='{previous_scene_text}' | azioni={chosen_action_names} | "
        f"mission_progress={state.mission.mission_progress}/{state.mission.mission_target} | "
        f"scene_progress={state.scene.objective_progress}/{state.scene.objective_target} | "
        f"threat={state.scene.threat_level} | time_left={state.scene.time_left} | esito={scene_result}"
    )
    state.mission_memory.append(memory_line)
    state.mission_memory = state.mission_memory[-6:]
    if state.story:
        state.story.event_log.append(memory_line)
        state.story.event_log = state.story.event_log[-20:]

    state.turn = previous_turn + 1
    recent_actions = ", ".join(used_actions) if used_actions else "nessuna"
    effect_counts = Counter(used_effect_types)
    effect_summary = "; ".join(f"{k}×{v}" for k, v in effect_counts.most_common())
    recent_memory = " || ".join(state.mission_memory)
    current_statuses = ", ".join([f"{p.name}:{p.status}" for p in state.players])
    current_wounds = ", ".join([f"{p.name}:{p.hp}/{p.max_hp}HP" for p in state.players])

    # Cattura il nodo precedente PRIMA dello spostamento
    previous_node_name = None
    previous_node_description = None
    if state.map_state:
        prev_node = state.map_state.nodes.get(state.map_state.current_node_id)
        if prev_node:
            previous_node_name = prev_node.name
            previous_node_description = prev_node.description

    # Movimento: se più destinazioni accessibili, il giocatore sceglie
    if scene_transition in ["success", "timeout", "crisis"] and state.map_state:
        accessible = get_accessible_connections(state)
        if len(accessible) > 1:
            state.pending_movement = True
            state.movement_options = accessible
            movement_options = [
                (state.map_state.nodes[nid].name, state.map_state.nodes[nid].description)
                for nid in accessible
            ]
            state.scene.scene_text = generate_movement_transition_narrative(
                mission_title=state.mission.title,
                mission_objective=state.mission.objective,
                scene_transition=scene_transition,
                current_node_name=previous_node_name or state.map_state.nodes[state.map_state.current_node_id].name,
                movement_options=movement_options,
                recent_actions=", ".join(used_actions) if used_actions else "nessuna",
                story_hints=story_hints_collected,
                premise=state.story.premise if state.story else "",
            )
            state.selected_actions = {}
            return state
        else:
            move_to_best_next_node(state, scene_transition)

    # Cattura il challenge corrente PRIMA di costruire il seed —
    # così Claude riceve il problema meccanico-narrativo già classificato
    # e può costruire la narrativa in modo coerente.
    current_challenge = state.scene.challenge if state.scene else None

    next_seed = build_scene_seed_with_canon(
        mission=state.mission,
        phase=state.phase,
        scene=state.scene,
        story=state.story,
        map_state=state.map_state,
        recent_actions=recent_actions,
        effect_summary=effect_summary,
        story_hints=story_hints_collected,
        recent_memory=recent_memory,
        current_statuses=current_statuses,
        current_wounds=current_wounds,
        scene_result=scene_result,
        scene_transition=scene_transition,
        previous_node_name=previous_node_name,
        previous_node_description=previous_node_description,
        scene_challenge=current_challenge,
        world_npcs=state.world_npcs,
    )

    # Costruisce gli esiti vincolanti per personaggio — Claude NON può ignorarli
    if per_player_outcomes:
        outcomes_block = "\n".join(
            f"  • {r['name']}: {r['action']} → [{r['outcome']}] (margine {r['margin']:+d}) hint='{r['hint']}'"
            for r in per_player_outcomes
        )
        coord_pairs = [
            f"{b} coordina con {effect_types_this_turn[et]}"
            for et, b in [(et, n) for et, n in effect_types_this_turn.items() if sum(1 for r in per_player_outcomes if r["hint"]) > 1]
        ]
        coord_note = f"\nAzioni coordinate: {'; '.join(coord_pairs)}" if coord_pairs else ""
    else:
        outcomes_block = "(nessuna azione)"
        coord_note = ""

    action_results_summary = (
        "══ ESITI DEI TIRI — VINCOLANTI PER LA NARRATIVA ══\n"
        "Ogni esito sotto è il risultato reale del dado 3d6 GURPS. "
        "NON puoi cambiare FALLIMENTO in successo né SUCCESSO in fallimento. "
        "Adatta la narrativa all'esito: un FALLIMENTO produce conseguenze negative concrete, "
        "un SUCCESSO PARZIALE produce il risultato atteso ma con un costo o complicazione.\n"
        f"{outcomes_block}{coord_note}\n"
        "══════════════════════════════════════════════════\n"
        "Tipi effetto: " + (effect_summary or "nessuno") + "\n"
        + "Esiti narrativi: " + (" | ".join(story_hints_collected) if story_hints_collected else "nessuno") + "\n"
        + "Esito globale: " + scene_result
    ) if chosen_action_names else ""

    package = generate_scene_package(next_seed, active_slots=len(state.players), action_results_summary=action_results_summary)
    state.scene_source = package.get("source", "unknown")
    # Inietta i bonus NPC nei discovered_facts della scena prossima, così entrano nel
    # normale flusso di apply_story_updates (che agganciano clue_for_thread).
    story_updates = package.get("story_updates", {}) or {}
    if npc_clue_bonuses:
        existing_facts = story_updates.get("discovered_facts", []) or []
        story_updates["discovered_facts"] = list(existing_facts) + npc_clue_bonuses
    apply_story_updates(state, story_updates)
    _advance_thread_progress(state, story_hints_collected)

    updated_players = generate_actions_for_selected_team(
        _player_context_dicts(state.players),
        scene_context=package.get("scene", {}).get("scene_text", "Nuova scena"),
        scene_tags=package.get("scene", {}).get("scene_tags", []),
        genre=state.mission.genre if state.mission else "",
    )
    state.players = build_players_from_dicts(updated_players, previous_players=state.players)

    scene_cfg = package.get("scene", {})
    new_scene_problem = scene_cfg.get("scene_problem", "")
    new_scene_resolution = scene_cfg.get("scene_resolution", "")
    claude_scene_actions = scene_cfg.get("scene_actions") or None

    if scene_transition in ["success", "timeout", "crisis"]:
        # Calcola bonus/malus al tempo dal nodo che la squadra ha appena lasciato.
        # Il nodo corrente è già il NUOVO (move_to_best_next_node l'ha aggiornato),
        # quindi cerco il bonus su tutti i nodi che hanno outcome non ancora consumato.
        time_adjustment = 0
        if state.map_state:
            for n in state.map_state.nodes.values():
                if n.outcome and n.time_bonus_for_next != 0:
                    time_adjustment += n.time_bonus_for_next
                    n.time_bonus_for_next = 0  # consumato
        base_time = scene_cfg.get("time_limit", 4)
        adjusted_time = max(3, base_time + time_adjustment) if state.scene and state.scene.time_limit > 0 else 0
        adjusted_threat = scene_cfg.get("starting_threat", 1)
        if scene_transition == "crisis":
            adjusted_threat = min(10, adjusted_threat + 1)
        state.scene = SceneState(
            scene_text=scene_cfg.get("scene_text", "Nuova scena."),
            scene_problem=new_scene_problem,
            scene_resolution=new_scene_resolution,
            objective_progress=0,
            objective_target=scene_cfg.get("objective_target", 4),
            threat_level=adjusted_threat,
            time_left=adjusted_time,
            time_limit=adjusted_time,
            scene_tags=scene_cfg.get("scene_tags", []),
        )
    else:
        state.scene.scene_text = scene_cfg.get("scene_text", state.scene.scene_text)
        state.scene.scene_tags = scene_cfg.get("scene_tags", state.scene.scene_tags)
        # Aggiorna problema/risoluzione anche nelle scene continue
        if new_scene_problem:
            state.scene.scene_problem = new_scene_problem
        if new_scene_resolution:
            state.scene.scene_resolution = new_scene_resolution
    refresh_scene_state(state, claude_scene_actions=claude_scene_actions)

    state.selected_actions = {}
    return state


def _player_context_dicts(players: list[Player]) -> list[dict]:
    return [
        {
            "id": p.id, "name": p.name, "role": p.role, "archetype": p.archetype,
            "stats": p.stats, "status": p.status,
            "skills": p.skills, "advantages": p.advantages, "disadvantages": p.disadvantages,
            "hp": p.hp, "max_hp": p.max_hp, "items": p.items, "actions": [],
            "backstory": p.backstory, "motivation": p.motivation,
        }
        for p in players
    ]

