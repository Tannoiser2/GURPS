from dotenv import load_dotenv
load_dotenv(override=True)
from datetime import datetime, timezone
import json
import os
import random
import re
import uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import io
from .engine import (
    empty_game_state, prepare_team_setup, start_game_from_selection,
    preview_action_outcomes, initiate_combat_action, declare_defense,
    resolve_reaction_roll, roll_for_player_action, npc_combat_turn,
    build_players_from_dicts, apply_story_updates,
    reload_weapon, add_weapon_to_player, remove_weapon_from_player, remove_equipment_item,
    collect_loot, give_item_to_player, _extract_found_items_from_narrative,
)
from .combat import stand_up
from .character_creation import validate_draft, build_custom_player
from .claude_service import (
    generate_scene_image, generate_character_avatar, generate_npc_avatar,
    generate_tactical_map_image, generate_location_map_image, narrate_combat_result,
    set_active_provider,
    get_session_token_stats, reset_session_token_stats,
    reset_last_request_tokens, get_last_request_tokens,
    master_turn_with_bible, create_adventure,
    generate_character_from_description, enrich_character_with_backstory,
    evaluate_personal_victories,
    _GOOGLE_GENAI_AVAILABLE, _GOOGLE_GENAI_IMPORT_ERROR,
    _OPENAI_AVAILABLE, _OPENAI_IMPORT_ERROR, OPENAI_API_KEY,
    compile_adventure_to_runtime,
    generate_opening_scene,
    compress_history, _COMPRESS_THRESHOLD,
)
from . import claude_service
from .data_genres import GENRE_PACKS
from .models import GameState, CombatDefenseRequest, CharacterDraft, SceneEntity, SceneState, MapNode, MapEdge, MapState, WorldNPC
from .runtime_models import AdventureDefinition, AdventureRuntimeState
from .adventure_runtime_store import list_runtimes, load_runtime, save_runtime, update_runtime
from .adventure_compiler import compile_from_raw_structure, compile_pdf_pages_to_runtime
from .adventure_validator import check_raw_compilation_quality
from .scene_context import actions_for_scene
from .adventure_doctor import run_doctor, audit as doctor_audit, score as doctor_score
from .clock_engine import tick_clocks, format_clock_event_narrative
from .npc_state_machine import update_pressure_from_clues, build_npc_pressure_context
from .deadlock_guard import check_and_fix_deadlocks

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
game_state: GameState = empty_game_state()
tactical_map_image_cache: dict[str, str] = {}
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PDF_COMPILATION_EXPORT_DIR = PROJECT_ROOT / "data" / "compiled_adventures" / "_debug_pdf"


def _ensure_runtime_scene(scene_text: str = "") -> None:
    if game_state.scene is None:
        game_state.scene = SceneState(scene_text=scene_text or "Scena in corso.")
    elif scene_text:
        game_state.scene.scene_text = scene_text


def _build_map_from_definition(definition: AdventureDefinition) -> "MapState | None":
    """Costruisce un MapState dal grafo di locazioni dell'AdventureDefinition.

    Assegna automaticamente posizioni griglia con BFS partendo dalla prima
    locazione, risolve gli exit-name → location-id e crea gli archi.
    """
    locs = definition.locations or []
    if not locs:
        return None

    name_to_id = {loc.name.lower(): loc.id for loc in locs}
    id_set = {loc.id for loc in locs}

    nodes: dict[str, MapNode] = {}
    adj: dict[str, list[str]] = {}

    _FINAL_KEYWORDS = {"finale", "final", "confronto finale", "boss", "scontro finale",
                       "ultimo scontro", "resa dei conti", "epilogo", "restituzione", "risoluzione"}
    _COMBAT_KEYWORDS = {"confronto", "combattimento", "scontro", "guardie", "nemici",
                        "bunker", "prigione", "infiltrazione", "assalto", "attacco"}

    for loc in locs:
        connections: list[str] = []
        for ex in (loc.exits or []):
            en = ex.strip().lower()
            if en in name_to_id:
                connections.append(name_to_id[en])
            elif ex.strip() in id_set:
                connections.append(ex.strip())
        adj[loc.id] = connections

        gf = (loc.gameplay_function or "").lower()
        hazards = loc.hazards or []
        tac_feats = loc.tactical_features or []
        existing_tac = dict(loc.tactical_map or {})

        is_final = any(kw in gf for kw in _FINAL_KEYWORDS)
        has_combat = any(kw in gf for kw in _COMBAT_KEYWORDS) or len(hazards) >= 2

        # Build minimal tactical_map if missing but combat/final is implied
        if (is_final or has_combat) and not existing_tac.get("enabled"):
            role = "finale" if is_final else "hot_zone"
            existing_tac = {
                "enabled": True,
                "role": existing_tac.get("role") or role,
                "trigger": existing_tac.get("trigger") or gf[:80] or f"Il confronto a {loc.name} non può più essere evitato.",
                "layout": existing_tac.get("layout") or "room",
                "features": existing_tac.get("features") or list(tac_feats[:3]),
                "hazards": existing_tac.get("hazards") or list(hazards[:3]),
            }

        nodes[loc.id] = MapNode(
            id=loc.id,
            name=loc.name,
            kind="location",
            description=(loc.description or "")[:200],
            connections=connections,
            visited=False,
            is_final=is_final,
            contains_enemy=has_combat,
            tactical_map=existing_tac,
        )

    # BFS from start to assign grid_x (depth) and grid_y (sibling index)
    start_id = locs[0].id
    depth_of: dict[str, int] = {start_id: 0}
    queue = [start_id]
    while queue:
        curr = queue.pop(0)
        for nb in adj.get(curr, []):
            if nb not in depth_of and nb in nodes:
                depth_of[nb] = depth_of[curr] + 1
                queue.append(nb)
    max_depth = max(depth_of.values(), default=0) if depth_of else 0
    for nid in nodes:
        if nid not in depth_of:
            depth_of[nid] = max_depth + 1

    depth_groups: dict[int, list[str]] = {}
    for nid, d in depth_of.items():
        depth_groups.setdefault(d, []).append(nid)
    for d, group in depth_groups.items():
        for i, nid in enumerate(group):
            nodes[nid].grid_x = d
            nodes[nid].grid_y = i

    # Build undirected edges (deduplicated by sorted pair)
    edges: dict[str, MapEdge] = {}
    for nid, conns in adj.items():
        for to_id in conns:
            if to_id in nodes:
                key = "-".join(sorted([nid, to_id]))
                if key not in edges:
                    edges[key] = MapEdge(from_id=nid, to_id=to_id, status="open")

    nodes[start_id].visited = True
    obj_id = locs[-1].id

    return MapState(
        map_type="adventure_location_graph",
        theme=definition.genre or "fantasy",
        nodes=nodes,
        connections_meta=edges,
        current_node_id=start_id,
        start_node_id=start_id,
        objective_node_id=obj_id,
    )


def _update_map_position(player_action: str) -> None:
    """Aggiorna current_node_id e visited se il player si sposta."""
    if not game_state.map_state or not game_state.adventure_definition:
        return
    import re as _re
    # Match many movement patterns: "spostarsi verso X", "vai a X", "andare a X",
    # "raggiungere X", "dirigersi a X", "recarsi a X", "entrare in X", "tornare a X"
    patterns = [
        r"[Ss]postar[si]* (?:verso|a|al|alla|allo|agli|alle)\s+(.+)",
        r"[Vv]a(?:i|do|)? (?:a|al|alla|allo|agli|alle)\s+(.+)",
        r"[Aa]ndar[ei]? (?:a|al|alla|allo|agli|alle)\s+(.+)",
        r"[Rr]aggiungere\s+(.+)",
        r"[Dd]irigers[i]* (?:a|al|alla|verso)\s+(.+)",
        r"[Rr]ecars[i]* (?:a|al|alla)\s+(.+)",
        r"[Ee]ntrare (?:in|nel|nella|nello|nei|negli|nelle)\s+(.+)",
        r"[Tt]ornare (?:a|al|alla|allo)\s+(.+)",
        r"[Mm]uovers[i]* (?:verso|a|al)\s+(.+)",
    ]
    dest_name = None
    for pat in patterns:
        m = _re.search(pat, player_action or "")
        if m:
            dest_name = m.group(1).strip().rstrip(".!?,;")
            break
    if not dest_name:
        return
    dest_name_l = dest_name.lower()
    nodes = game_state.map_state.nodes
    match_id = None
    for nid, node in nodes.items():
        if node.name.lower() == dest_name_l or nid.lower() == dest_name_l:
            match_id = nid
            break
    if not match_id:
        for nid, node in nodes.items():
            if dest_name_l in node.name.lower() or node.name.lower() in dest_name_l:
                match_id = nid
                break
    if match_id:
        game_state.map_state.current_node_id = match_id
        nodes[match_id].visited = True


def _safe_file_stem(value: str, fallback: str = "avventura") -> str:
    stem = Path(value or fallback).stem or fallback
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-._")
    return stem[:80] or fallback


def _without_embedded_images(value):
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if key in {"map_image_b64", "image_b64", "image_base64"}:
                cleaned[key] = f"<omessa: base64 {len(item) if isinstance(item, str) else 0} caratteri>"
            else:
                cleaned[key] = _without_embedded_images(item)
        return cleaned
    if isinstance(value, list):
        return [_without_embedded_images(item) for item in value]
    return value


def _save_pdf_compilation_json(
    *,
    source_filename: str,
    requested_genre: str,
    provider: str,
    map_page: str,
    total_pages: int,
    text_pages: list[str],
    raw_chars: int,
    cleaned_pdf_text: str,
    compiled_result: dict,
) -> dict:
    """Salva un export locale per audit PDF -> runtime. Best effort: non blocca il gioco."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    runtime_id = (
        compiled_result.get("runtime_id")
        or (compiled_result.get("adventure_definition") or {}).get("id")
        or "runtime"
    )
    filename = f"{timestamp}-{_safe_file_stem(source_filename)}-{_safe_file_stem(runtime_id)}.json"
    payload = {
        "export_type": "gurps_pdf_compilation_debug",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_pdf_filename": source_filename,
        "requested_genre": requested_genre,
        "provider": provider,
        "map_page_requested": map_page,
        "pdf_total_pages": total_pages,
        "pdf_pages_read": len(text_pages),
        "pdf_raw_extracted_chars": raw_chars,
        "pdf_cleaned_chars": len(cleaned_pdf_text),
        "pdf_cleaned_text": cleaned_pdf_text,
        "compiled_adventure": _without_embedded_images(compiled_result),
    }
    PDF_COMPILATION_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = PDF_COMPILATION_EXPORT_DIR / filename
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "saved_json_path": str(path),
        "saved_json_filename": filename,
        "saved_json_relative_path": str(path.relative_to(PROJECT_ROOT)),
    }


def _sync_players_from_payload(players: list[dict]) -> None:
    """Sincronizza i PG del flusso bibbia nel GameState usato dal combattimento."""
    normalized = []
    for p in players or []:
        q = dict(p)
        q.setdefault("id", len(normalized) + 1)
        q.setdefault("name", f"Personaggio {q['id']}")
        q.setdefault("role", "Avventuriero")
        q.setdefault("archetype", q.get("role", "custom"))
        q.setdefault("stats", {})
        q.setdefault("skills", {})
        q.setdefault("advantages", [])
        q.setdefault("disadvantages", [])
        q.setdefault("items", [])
        q.setdefault("actions", [])
        normalized.append(q)
    if normalized:
        game_state.players = build_players_from_dicts(normalized, previous_players=game_state.players)
        game_state.in_setup = False


def _npc_name_match(npc_name: str, entity_name: str) -> bool:
    """True se i nomi si sovrappongono abbastanza (case-insensitive, almeno 4 caratteri comuni)."""
    a = npc_name.lower().strip()
    b = entity_name.lower().strip()
    if a == b:
        return True
    # partial: uno contiene l'altro, o condividono il primo token
    if a in b or b in a:
        return True
    tok_a = a.split()[0] if a.split() else a
    tok_b = b.split()[0] if b.split() else b
    return len(tok_a) >= 4 and tok_a == tok_b


def _generate_npc_combat_stats(npc_role: str, threat: int) -> dict:
    """
    Genera stat GURPS coerenti per un WorldNPC al primo ingresso in combattimento.
    threat 0-3: 0=civile, 1=guardia, 2=veterano, 3=boss
    """
    role_lower = npc_role.lower()
    is_boss = threat >= 3 or any(w in role_lower for w in ["boss", "capo", "generale", "comandante", "antagonista"])
    is_veteran = threat >= 2 or any(w in role_lower for w in ["guardia", "soldat", "veteran", "operativo", "agente"])

    if is_boss:
        hp = random.randint(14, 18)
        attack = random.randint(13, 15)
        defense = random.randint(10, 12)
        dr = random.randint(2, 4)
        dmg = "2d6"
    elif is_veteran:
        hp = random.randint(10, 14)
        attack = random.randint(11, 13)
        defense = random.randint(9, 11)
        dr = random.randint(1, 2)
        dmg = "1d6+2"
    else:
        hp = random.randint(8, 11)
        attack = random.randint(9, 11)
        defense = random.randint(8, 10)
        dr = 0
        dmg = "1d6"

    # tipo danno da ruolo
    if any(w in role_lower for w in ["pistola", "fucile", "tiratore", "cecchino", "ranged"]):
        dmg_type = "cr"
    elif any(w in role_lower for w in ["lama", "spada", "coltello", "tagliente"]):
        dmg_type = "cut"
    else:
        dmg_type = "cr"

    return {
        "hp": hp, "max_hp": hp, "dr": dr,
        "attack_skill": attack, "active_defense": defense,
        "damage_dice": dmg, "damage_type": dmg_type,
    }


def _seed_world_npcs_from_actors(definition) -> None:
    """Pre-popola game_state.world_npcs dagli attori dell'avventura.

    Gli antagonisti/villain ricevono stat GURPS complete; gli altri NPC
    hanno solo dati narrativi. Viene saltato se world_npcs è già popolato
    (evita doppio seed su restart).
    """
    if not definition:
        return
    actors = getattr(definition, "actors", None) or []
    if not actors:
        return
    # Skip se già popolato
    if game_state.world_npcs:
        return

    first_location_id = ""
    locations = getattr(definition, "locations", None) or []
    if locations:
        first_location_id = getattr(locations[0], "id", "") or ""

    for actor in actors:
        actor_id = getattr(actor, "id", "") or ""
        actor_name = getattr(actor, "name", "") or actor_id
        if not actor_id or not actor_name:
            continue

        role_raw = str(getattr(actor, "role", "") or "").lower()
        location_id = getattr(actor, "location_id", "") or first_location_id
        goal = getattr(actor, "goal", "") or ""
        secret = getattr(actor, "secret", "") or ""
        current_plan = getattr(actor, "current_plan", "") or ""

        # Descrizione compatta per il prompt.
        # Il segreto NON viene incluso per antagonisti/villain:
        # viene rivelato nel prompt solo quando l'NPC è marcato [ESPOSTO].
        # Per alleati/neutrali (non combattivi) il segreto è meno critico e può restare.
        desc_parts = []
        if goal:
            desc_parts.append(f"Obiettivo: {goal[:80]}")
        if current_plan:
            desc_parts.append(f"Piano: {current_plan[:60]}")
        description = " | ".join(desc_parts)[:200]

        # Ruolo canonico e threat level
        if role_raw in ("villain", "antagonista principale", "main antagonist"):
            npc_role = "antagonista"
            threat = 3
        elif role_raw in ("antagonist", "antagonista", "enemy", "nemico", "hostile"):
            npc_role = "antagonista"
            threat = 2
        elif role_raw in ("neutral", "neutrale", "witness", "testimone"):
            npc_role = "neutrale"
            threat = 0
        elif role_raw in ("ally", "alleato", "friend", "amico"):
            npc_role = "alleato"
            threat = 0
        else:
            npc_role = "neutrale"
            threat = 0

        # Stat GURPS per NPC combattivi
        combat_stats = _generate_npc_combat_stats(role_raw, threat) if threat >= 2 else None

        npc = WorldNPC(
            id=actor_id,
            name=actor_name,
            role=npc_role,
            current_node_id=location_id,
            status="alive",
            threat_to_player=threat,
            description=description,
            # GURPS combat stats (solo per threat >= 2)
            combat_hp=combat_stats["hp"] if combat_stats else None,
            combat_max_hp=combat_stats["max_hp"] if combat_stats else None,
            combat_dr=combat_stats["dr"] if combat_stats else 0,
            combat_attack_skill=combat_stats["attack_skill"] if combat_stats else None,
            combat_active_defense=combat_stats["active_defense"] if combat_stats else None,
            combat_damage_dice=combat_stats["damage_dice"] if combat_stats else "",
            combat_damage_type=combat_stats["damage_type"] if combat_stats else "cr",
        )
        # Auto-equip armi per NPC combattivi
        from .engine import _assign_npc_weapons
        _assign_npc_weapons(npc, game_state.team_setup.genre if game_state.team_setup else "")
        game_state.world_npcs.append(npc)

    print(f"[seed_npcs] Pre-seeded {len(game_state.world_npcs)} NPC da {len(actors)} attori dell'avventura.")


def _current_tactical_is_final() -> bool:
    node = None
    try:
        node = game_state.map_state.nodes.get(game_state.map_state.current_node_id) if game_state.map_state else None
    except Exception:
        node = None
    if not node:
        return False
    tactical = getattr(node, "tactical_map", None) or {}
    role = str(tactical.get("role") or tactical.get("purpose") or "").lower()
    return bool(getattr(node, "is_final", False) or getattr(node, "is_objective", False) or "final" in role)


def _runtime_location_accessible(node_id: str) -> bool:
    rt = getattr(game_state, "adventure_runtime_state", None)
    if not rt or not node_id:
        return True
    entry = dict((rt.location_runtime or {}).get(node_id) or {})
    access_state = str(entry.get("access_state") or "open").lower()
    status = str(entry.get("status") or "known").lower()
    if access_state in {"locked", "hidden", "blocked", "sealed", "restricted"}:
        return False
    if status in {"hidden", "locked"}:
        return False
    return True


def _runtime_finale_available() -> bool:
    rt = getattr(game_state, "adventure_runtime_state", None)
    if not rt:
        return True
    statuses = [
        str((entry or {}).get("status") or "locked").lower()
        for entry in (rt.finale_runtime or {}).values()
        if isinstance(entry, dict)
    ]
    if not statuses:
        return True
    return any(status in {"available", "satisfied"} for status in statuses)


def _current_hot_node():
    try:
        node = game_state.map_state.nodes.get(game_state.map_state.current_node_id) if game_state.map_state else None
    except Exception:
        return None
    if not node:
        return None
    if not _runtime_location_accessible(node.id):
        return None
    tactical = getattr(node, "tactical_map", None) or {}
    enabled = bool(tactical.get("enabled") or getattr(node, "contains_enemy", False) or getattr(node, "is_final", False) or getattr(node, "is_objective", False))
    role = str(tactical.get("role") or tactical.get("purpose") or "").lower()
    if enabled and (getattr(node, "is_final", False) or getattr(node, "is_objective", False) or "final" in role) and not _runtime_finale_available():
        return None
    return node if enabled else None


def _action_triggers_tactical_combat(action_text: str, node) -> bool:
    if not node:
        return False
    tactical = getattr(node, "tactical_map", None) or {}
    role = str(tactical.get("role") or "").lower()
    text = str(action_text or "").lower()
    trigger = str(tactical.get("trigger") or "").lower()
    trigger_words = {
        "attacco", "attacca", "combatto", "scontro", "confronto", "assalto",
        "entro", "entra", "avanza", "avanzo", "sposta", "raggiunge", "verso",
        "forzo", "sfondo", "inseguo", "fuga", "scappo", "irrompo", "apro",
    }
    text_hit = any(word in text for word in trigger_words)
    trigger_hit = any(word in trigger for word in ["scontro", "confronto", "assalto", "fuga", "agguato", "combatt"])
    final_or_enemy = bool(getattr(node, "is_final", False) or getattr(node, "contains_enemy", False) or "final" in role or role in {"hot_zone", "boss", "combat"})
    if final_or_enemy and (getattr(node, "is_final", False) or getattr(node, "is_objective", False) or "final" in role) and not _runtime_finale_available():
        return False
    return bool(final_or_enemy and (text_hit or trigger_hit))


def _forced_combat_entities_for_node(node) -> list[dict]:
    npcs_here = [
        npc for npc in game_state.world_npcs
        if npc.status == "alive"
        and npc.current_node_id == node.id
        and (
            npc.threat_to_player > 0
            or any(word in npc.role.lower() for word in ["antagon", "ostile", "guard", "soldat", "nemic"])
        )
    ]
    if not npcs_here:
        npcs_here = [
            npc for npc in game_state.world_npcs
            if npc.status == "alive"
            and (
                npc.threat_to_player >= 2
                or any(word in npc.role.lower() for word in ["antagon", "ostile", "guard", "soldat", "nemic"])
            )
        ][:2]

    entities = []
    for idx, npc in enumerate(npcs_here[:3], start=1):
        stats = _generate_npc_combat_stats(npc.role, npc.threat_to_player)
        entities.append({
            "id": npc.id or f"enemy_{idx}",
            "name": npc.name,
            "type": "enemy",
            "zone": "centro",
            **stats,
        })
    if not entities:
        tactical = getattr(node, "tactical_map", None) or {}
        role = str(tactical.get("role") or "").lower()
        name = "Guardia della zona calda" if "final" not in role else "Difensore finale"
        stats = _generate_npc_combat_stats("guardia veterana" if "final" in role else "guardia", 2 if "final" in role else 1)
        entities.append({
            "id": f"enemy_{node.id}",
            "name": name,
            "type": "enemy",
            "zone": "centro",
            **stats,
        })
    return entities


_ROUTINE_MOVE_RE = re.compile(
    r"^\s*(spostar[si]*|andare|camminare|dirigers[i]*|avvicinar[si]*|allontan[si]*|tornare|raggiungere|uscire|entrare|seguire il sentiero|seguire la strada|procedere)\b",
    re.IGNORECASE,
)
_ROUTINE_MOVE_KEYWORDS = {
    "spostarsi", "andare a", "camminare verso", "dirigersi", "avvicinarsi verso",
    "seguire il sentiero", "seguire la strada", "raggiungere", "tornare al",
    "uscire dalla", "entrare nel", "entrare nella", "allontanarsi",
}


def _needs_roll(action_text: str, threat_level: int, in_combat: bool) -> bool:
    """Restituisce False per azioni di routine che non richiedono tiro GURPS.

    Regola base GURPS: se l'azione è banale (nessuna difficoltà reale, nessuna
    opposizione, threat_level basso) il Master non chiede un tiro.
    """
    if in_combat:
        return True  # in combattimento si tira sempre
    if threat_level >= 3:
        return True  # alta tensione: anche il movimento può nascondere pericoli
    text_lower = action_text.strip().lower()
    # Movimento semplice senza specificare ostacoli o azioni aggiuntive
    if _ROUTINE_MOVE_RE.match(text_lower):
        # Eccezioni: se l'azione contiene un obiettivo secondario (es. "spostarsi e cercare")
        secondary_keywords = ("cerca", "osserv", "nascond", "furtiv", "combatt",
                              "attacc", "scappa", "sfuggi", "investiga", "esamina",
                              "ascolt", "spia", "intercett")
        if not any(k in text_lower for k in secondary_keywords):
            return False
    return True


def _force_hot_zone_combat_update(updates: dict, player_action: str) -> dict:
    su = dict(updates or {})
    if su.get("activate_combat") or su.get("combat_over") or su.get("story_over"):
        return su
    node = _current_hot_node()
    if not _action_triggers_tactical_combat(player_action, node):
        return su
    tactical = getattr(node, "tactical_map", None) or {}
    entities = _forced_combat_entities_for_node(node)
    su["activate_combat"] = True
    su["combat_scene"] = {
        "location_id": node.id,
        "location_name": node.name,
        "location_type": node.kind or "zona tattica",
        "scene_text": (
            f"La zona calda di {node.name} scatta: {tactical.get('trigger') or 'il confronto diretto non puo piu essere evitato'}."
        ),
        "role": tactical.get("role") or ("finale" if getattr(node, "is_final", False) else "hot_zone"),
        "layout": tactical.get("layout") or "room",
        "features": list(tactical.get("features") or []),
        "hazards": list(tactical.get("hazards") or []),
        "entities": entities,
        "forced_by_hot_zone": True,
    }
    su["threat_increase"] = max(0, int(su.get("threat_increase") or 0))
    su.setdefault("flags", {})
    if isinstance(su["flags"], dict):
        su["flags"]["hot_zone_triggered"] = node.id
    return su


def _safe_int(value, fallback: int) -> int:
    try:
        return int(value)
    except Exception:
        return fallback


def _balance_combat_entities(entities: list[dict], combat_scene: dict | None = None) -> list[dict]:
    """Applica un paracadute agli scontri non finali: pochi nemici, leggibili, con via d'uscita."""
    if not entities:
        return entities
    player_count = max(1, len([p for p in game_state.players if getattr(p, "hp", 1) > 0]) or len(game_state.players) or 1)
    is_final = _current_tactical_is_final()
    max_enemies = player_count + 2 if is_final else max(1, min(3, player_count))
    balanced: list[dict] = []
    for raw in entities[:max_enemies]:
        entity = dict(raw)
        if not is_final:
            hp = min(_safe_int(entity.get("hp", entity.get("max_hp", 10)), 10), 11)
            max_hp = min(_safe_int(entity.get("max_hp", hp), hp), 11)
            entity["hp"] = min(hp, max_hp)
            entity["max_hp"] = max_hp
            entity["dr"] = min(_safe_int(entity.get("dr", 0), 0), 1)
            entity["attack_skill"] = min(_safe_int(entity.get("attack_skill", 10), 10), 11)
            entity["active_defense"] = min(_safe_int(entity.get("active_defense", 8), 8), 9)
            dmg = str(entity.get("damage_dice") or "1d6")
            if dmg.startswith("2d") or dmg.startswith("3d"):
                entity["damage_dice"] = "1d6"
            entity.setdefault("morale", "si ritira se ferito o se il gruppo apre una via di fuga")
        balanced.append(entity)
    return balanced


def _enrich_combat_scene(combat_scene: dict | None) -> dict | None:
    """
    Arricchisce combat_scene con stat GURPS persistenti dai WorldNPC.
    Cerca match per nome: se il WorldNPC ha già stat le riusa, altrimenti le genera e salva.

    IMPORTANTE: preserva l'HP corrente dall'entità live (game_state.scene.entities) se esiste.
    Questo evita il reset dell'HP dopo ogni turno narrativo durante un combattimento attivo.
    """
    if not combat_scene or not isinstance(combat_scene.get("entities"), list):
        return combat_scene

    # Indice delle entità live: preserva HP corrente, non resettare a max
    live_by_id: dict = {}
    live_by_name: dict = {}
    if game_state.scene and game_state.scene.entities:
        for le in game_state.scene.entities:
            if le.id:
                live_by_id[le.id] = le
            if le.name:
                live_by_name[le.name.lower()] = le

    enriched = []
    for entity in combat_scene["entities"]:
        name = entity.get("name", "")
        entity_id = entity.get("id", "")
        matched_npc = None
        for npc in game_state.world_npcs:
            if _npc_name_match(npc.name, name):
                matched_npc = npc
                break

        # Cerca entità live per id poi per nome
        live_entity = live_by_id.get(entity_id) or live_by_name.get(name.lower())

        if matched_npc is not None:
            if matched_npc.combat_hp is not None:
                # Riusa stat già generate — ma preserva HP corrente se l'entità è già in gioco
                if live_entity is not None:
                    current_hp = live_entity.hp  # preserva danno già applicato
                else:
                    current_hp = matched_npc.combat_hp  # prima apparizione: HP pieno
                entity = {
                    **entity,
                    "hp": current_hp,
                    "max_hp": matched_npc.combat_max_hp,
                    "dr": matched_npc.combat_dr,
                    "attack_skill": matched_npc.combat_attack_skill,
                    "active_defense": matched_npc.combat_active_defense,
                    "damage_dice": matched_npc.combat_damage_dice or entity.get("damage_dice", "1d6"),
                    "damage_type": matched_npc.combat_damage_type or entity.get("damage_type", "cr"),
                }
            else:
                # Prima volta in combattimento: genera e persisti
                stats = _generate_npc_combat_stats(matched_npc.role, matched_npc.threat_to_player)
                matched_npc.combat_hp = stats["hp"]
                matched_npc.combat_max_hp = stats["max_hp"]
                matched_npc.combat_dr = stats["dr"]
                matched_npc.combat_attack_skill = stats["attack_skill"]
                matched_npc.combat_active_defense = stats["active_defense"]
                matched_npc.combat_damage_dice = stats["damage_dice"]
                matched_npc.combat_damage_type = stats["damage_type"]
                # Prima volta: usa HP dalle stat (max)
                entity = {**entity, **stats}
        elif live_entity is not None:
            # Nessun WorldNPC corrispondente, ma l'entità è già in gioco: preserva HP corrente
            entity = {**entity, "hp": live_entity.hp}

        # Se non c'è match in world_npcs lascia le stat di Claude (o i default del modello)
        enriched.append(entity)

    enriched = _balance_combat_entities(enriched, combat_scene)
    next_scene = {**combat_scene, "entities": enriched}
    if not _current_tactical_is_final():
        next_scene.setdefault("escape_routes", ["ritirata ordinata verso la stanza precedente", "forzare un varco laterale con un costo di minaccia"])
    return next_scene


def _persist_combat_scene(combat_scene: dict | None, preserve_live_hp: bool = False) -> None:
    """
    Salva i nemici della combat_scene nello stato backend usato dagli endpoint tattici.

    preserve_live_hp=True: se un'entità esiste già in game_state.scene.entities con un HP
    inferiore al valore in combat_scene, usa l'HP corrente (evita reset HP durante combattimento).
    """
    if not combat_scene or not isinstance(combat_scene.get("entities"), list):
        return
    _ensure_runtime_scene()

    # Indice entità live per id e nome (per preservare HP corrente)
    live_hp: dict = {}
    if preserve_live_hp and game_state.scene and game_state.scene.entities:
        for le in game_state.scene.entities:
            if le.id:
                live_hp[le.id] = le.hp
            if le.name:
                live_hp[f"name:{le.name.lower()}"] = le.hp

    entities: list[SceneEntity] = []
    for idx, raw in enumerate(combat_scene.get("entities") or [], start=1):
        if not isinstance(raw, dict):
            continue
        entity = dict(raw)
        entity.setdefault("id", f"enemy_{idx}")
        entity.setdefault("name", f"Nemico {idx}")
        entity.setdefault("type", "enemy")
        entity.setdefault("zone", "centro")
        entity.setdefault("max_hp", entity.get("hp", 10))
        # Usa HP corrente se disponibile (preserve_live_hp mode)
        if preserve_live_hp:
            eid = entity.get("id", "")
            ename = entity.get("name", "")
            current_hp = live_hp.get(eid) or live_hp.get(f"name:{ename.lower()}")
            if current_hp is not None:
                entity["hp"] = current_hp
            else:
                entity.setdefault("hp", entity.get("max_hp", 10))
        else:
            entity.setdefault("hp", entity.get("max_hp", 10))
        entity.setdefault("dr", 0)
        entity.setdefault("attack_skill", 10)
        entity.setdefault("active_defense", 8)
        entity.setdefault("damage_dice", "1d6")
        entity.setdefault("damage_type", "cr")
        # Propaga l'id generato (es. "enemy_1") al dict originale nella combat_scene,
        # così il frontend riceve lo stesso id che sarà usato dal backend per trovare l'entità.
        raw["id"] = entity["id"]
        try:
            entities.append(SceneEntity(**entity))
        except Exception:
            continue

    if entities:
        game_state.scene.entities = entities
        game_state.pending_attack = None
        game_state.last_attack_result = None


def _image_provider_available(provider: str) -> bool:
    if provider == "openai":
        return bool(OPENAI_API_KEY) and _OPENAI_AVAILABLE
    return bool(os.getenv("GOOGLE_AI_STUDIO_KEY")) and _GOOGLE_GENAI_AVAILABLE

def _resolve_image_provider() -> str | None:
    """Restituisce il provider immagini da usare o None se disabilitato.
    Rispetta game_state.team_setup.image_provider:
      'none'  → None (nessuna grafica)
      'openai'→ openai se disponibile, else None
      'gemini'→ gemini se disponibile, else None
      'auto'  → primo disponibile tra openai e gemini
    """
    ip = getattr(game_state.team_setup, "image_provider", "auto") or "auto"
    if ip == "none":
        return None
    if ip in ("openai", "gemini"):
        return ip if _image_provider_available(ip) else None
    # auto: preferisce openai, poi gemini
    for p in ("openai", "gemini"):
        if _image_provider_available(p):
            return p
    return None

class PreviewActionPayload(BaseModel):
    player_id: int
    intent: str = ""
    custom_intents: dict[int, str] = {}
    structured_intent: dict = {}

class SetupPayload(BaseModel):
    genre: str
    provider: str = "claude"        # "claude" | "openai" — AI testuale
    image_provider: str = "auto"    # "auto" | "openai" | "gemini" | "none"

class TeamSelectionPayload(BaseModel):
    selected_player_ids: list[int]
    custom_names: dict[int, str] = {}
    adventure_bible: dict | None = None

class AvatarGenPayload(BaseModel):
    photo_b64: str = ""
    genre: str
    role: str
    archetype: str
    name: str = ""
    description: str = ""

class CombatAttackPayload(BaseModel):
    attacker_id: int
    action_name: str                    # nome dell'Action nel player.actions
    target_entity_id: str | None = None
    target_player_id: int | None = None
    action_type: str = "normal"         # "normal" | "all_out_attack" | "aim"
    distance: int = 0                   # distanza in esagoni/yard (mappa tattica)

class CombatAimPayload(BaseModel):
    attacker_id: int
    action_name: str                    # nome dell'Action da mirare

class CombatDefendPayload(BaseModel):
    """Estende CombatDefenseRequest con il tipo di azione difensiva."""
    player_id: int
    defense_type: str                   # "dodge" | "parry" | "block"
    defense_skill: str = ""
    defense_action_type: str = "normal" # "normal" | "all_out_defense"
    cover_bonus: int = 0                # +2 se il bersaglio è in copertura (dal frontend)
    rear_attack: bool = False           # True se attaccante era nella zona posteriore

class CombatStandUpPayload(BaseModel):
    player_id: int

class ReactionPayload(BaseModel):
    npc_id: str
    player_id: int
    social_skill: str = "persuadere"

class ImageGenPayload(BaseModel):
    scene_text: str
    genre: str
    environment_type: str
    player_photos_b64: list[str] = []
    player_names: list[str] = []

class AdventureCreatePayload(BaseModel):
    genre: str
    players: list[dict]

class AdventureCompilePayload(BaseModel):
    source_type: str = "raw_text"
    title: str = ""
    content: str
    genre_hint: str | None = None
    runtime_profile_hint: str | None = None

class RuntimeUpdatePayload(BaseModel):
    adventure_definition: dict | None = None
    runtime_state: dict | None = None
    validation_report: dict | None = None

class RuntimeStartPayload(BaseModel):
    selected_player_ids: list[int] = []
    custom_names: dict[int, str] = {}

class MasterStartBiblePayload(BaseModel):
    genre: str
    players: list[dict]
    adventure: dict

class MasterTurnBiblePayload(BaseModel):
    genre: str
    players: list[dict]
    history: list[dict] = []
    player_action: str
    active_player_id: int
    adventure: dict
    game_state_data: dict = {}

@app.post("/game/adventure/create")
def adventure_create(payload: AdventureCreatePayload):
    """Genera un'avventura, la ricompila nel runtime e la corregge automaticamente col Doctor."""
    raw = create_adventure(payload.genre, payload.players)
    if raw.get("error"):
        return raw
    raw["source_mode"] = "ai_generated"
    compiled = compile_from_raw_structure(
        raw,
        source_type="raw_text",
        title=raw.get("title", "Avventura generata"),
        genre_hint=payload.genre,
    )
    definition = compiled["adventure_definition"]
    definition.legacy_adventure = definition.legacy_adventure or {}
    runtime_state = compiled["runtime_state"]
    saved = save_runtime(definition, runtime_state, compiled["validation_report"])

    # ── Doctor: audit + fix automatico ──────────────────────────────────────
    defn_dict = saved["adventure_definition"]
    doctor_result = {"score": 10.0, "findings": [], "score_after": 10.0}
    try:
        doctor_result = run_doctor(defn_dict, do_enrich=True)
        enriched = doctor_result.get("enriched_definition")
        if enriched:
            # Risalva il runtime con la definizione arricchita
            enr_def = AdventureDefinition(**{
                k: v for k, v in enriched.items()
                if k in AdventureDefinition.model_fields
            })
            enr_def.id = definition.id  # mantieni lo stesso id
            saved = save_runtime(enr_def, runtime_state, compiled["validation_report"])
            defn_dict = saved["adventure_definition"]
            print(f"[doctor/create] score {doctor_result['score']} → {doctor_result.get('score_after', '?')}/10"
                  f" ({len(doctor_result['findings'])} findings corretti)")
    except Exception as de:
        print(f"[doctor/create] errore (non bloccante): {de}")

    result = dict(definition.legacy_adventure or {})
    result.update({
        "from_runtime_compiler": True,
        "runtime_id": definition.id,
        "adventure_definition": defn_dict,
        "runtime_state": saved["runtime_state"],
        "validation_report": saved["validation_report"],
        "doctor": {
            "score":        doctor_result.get("score", 10.0),
            "score_after":  doctor_result.get("score_after"),
            "findings":     doctor_result.get("findings", []),
            "auto_fixed":   bool(doctor_result.get("enriched_definition")),
        },
    })
    return result

@app.post("/game/adventure/compile")
def adventure_compile(payload: AdventureCompilePayload):
    compiled = compile_adventure_to_runtime(
        payload.content,
        genre_hint=payload.genre_hint,
        runtime_profile_hint=payload.runtime_profile_hint,
        source_type=payload.source_type,
        title=payload.title,
    )
    definition = AdventureDefinition(**compiled["adventure_definition"])
    runtime_state = AdventureRuntimeState(**compiled["runtime_state"])
    saved = save_runtime(definition, runtime_state, compiled["validation_report"])
    return saved

@app.get("/game/adventure/runtime")
def adventure_runtime_list(genre: str | None = None):
    return {"items": list_runtimes(genre_filter=genre)}

@app.get("/game/adventure/runtime/{runtime_id}")
def adventure_runtime_get(runtime_id: str):
    data = load_runtime(runtime_id)
    if not data:
        return {"error": "runtime non trovato"}
    return data

@app.get("/game/adventure/runtime/{runtime_id}/live-state")
def adventure_live_state(runtime_id: str):
    """Restituisce lo stato world salvato dell'ultima sessione di gioco."""
    data = load_runtime(runtime_id)
    if not data:
        return {"live_game_state": None}
    return {"live_game_state": data.get("live_game_state")}

@app.post("/game/adventure/runtime/{runtime_id}/update")
def adventure_runtime_update(runtime_id: str, payload: RuntimeUpdatePayload):
    patch = {}
    if payload.adventure_definition is not None:
        patch["adventure_definition"] = payload.adventure_definition
    if payload.runtime_state is not None:
        patch["runtime_state"] = payload.runtime_state
    if payload.validation_report is not None:
        patch["validation_report"] = payload.validation_report
    data = update_runtime(runtime_id, patch)
    if not data:
        return {"error": "runtime non trovato"}
    return data

@app.post("/game/adventure/runtime/{runtime_id}/start")
def adventure_runtime_start(runtime_id: str, payload: RuntimeStartPayload | None = None):
    global game_state, tactical_map_image_cache
    data = load_runtime(runtime_id)
    if not data:
        return {"error": "runtime non trovato"}
    definition = AdventureDefinition(**data["adventure_definition"])
    runtime_state = AdventureRuntimeState(**data["runtime_state"])
    legacy_adventure = definition.legacy_adventure or {}
    if payload and payload.selected_player_ids:
        compiled_payload = {
            **legacy_adventure,
            "adventure_definition": definition.model_dump(),
            "runtime_state": runtime_state.model_dump(),
        }
        game_state = start_game_from_selection(game_state, payload.selected_player_ids, payload.custom_names, compiled_payload)
    game_state.adventure_definition_id = definition.id
    game_state.adventure_definition = definition
    game_state.adventure_runtime_state = runtime_state
    game_state.current_objective_ids = list(runtime_state.active_objective_ids)
    game_state.active_revelation_ids = list(runtime_state.active_revelation_ids)
    game_state.active_clock_ids = list(runtime_state.clock_runtime.keys())
    game_state.active_pressure_ids = list(runtime_state.pressure_runtime.keys())
    tactical_map_image_cache = {}
    return {
        "game_state": game_state.model_dump(),
        "adventure": legacy_adventure,
        "adventure_definition": definition.model_dump(),
        "runtime_state": runtime_state.model_dump(),
    }

class DoctorPayload(BaseModel):
    adventure_definition: dict
    enrich: bool = False


@app.post("/game/adventure/doctor")
def adventure_doctor(payload: DoctorPayload):
    """Audit (and optionally enrich) an adventure definition."""
    try:
        result = run_doctor(payload.adventure_definition, do_enrich=payload.enrich)
        return result
    except Exception as e:
        print(f"[doctor endpoint] error: {e}")
        return {"error": str(e), "score": 0, "findings": [], "enriched_definition": None}


def _merge_game_state(current: dict, updates: dict) -> dict:
    """Replica applyStateUpdates del frontend — produce lo stato world dopo un turno."""
    new_clues = list({*(current.get("clues_found") or []), *(updates.get("clues_found") or [])})

    progress = dict(current.get("clue_progress") or {})
    for p in updates.get("clue_progress") or []:
        cid = p.get("clue_id") or p.get("id")
        if not cid or cid in new_clues:
            continue
        prev = progress.get(cid) or {"ticks": 0}
        progress[cid] = {
            "ticks": min(2, (prev.get("ticks") or 0) + (p.get("ticks") or 1)),
            "note": p.get("note") or prev.get("note") or "",
        }
    for cid in new_clues:
        progress.pop(cid, None)

    npc_statuses = dict(current.get("npc_statuses") or {})
    for u in updates.get("npc_updates") or []:
        nid = u.get("id") or u.get("npc_id")
        if nid:
            npc_statuses[nid] = {**(npc_statuses.get(nid) or {}), **u, "id": nid}

    resolved = list({
        *(current.get("resolved_threads") or []),
        *(updates.get("closed_threads") or []),
        *(updates.get("thread_resolved") or []),
    })
    existing_threads = [
        t for t in (current.get("open_threads") or [])
        if t not in (updates.get("closed_threads") or [])
    ]
    in_combat = bool(updates.get("activate_combat")) or (
        current.get("in_combat", False) and not updates.get("combat_over")
    )
    return {
        **current,
        "clues_found": new_clues,
        "clue_progress": progress,
        "npc_statuses": npc_statuses,
        "threat_level": (current.get("threat_level") or 0) + (updates.get("threat_increase") or 0),
        "open_threads": existing_threads,
        "resolved_threads": resolved,
        "turn": (current.get("turn") or 1) + 1,
        "turns_played": (current.get("turns_played") or 0) + 1,
        "in_combat": in_combat,
    }


def _adventure_id(adventure: dict) -> str | None:
    return (adventure or {}).get("id") or (adventure or {}).get("adventure_definition_id") or None


def _build_clocks_data(runtime, runtime_state) -> list[dict]:
    """Costruisce la lista clock da inviare al frontend, rispettando la visibilità."""
    clocks = []
    clock_rt = {}
    if runtime_state:
        clock_rt = dict(runtime_state.clock_runtime or {})
    # Prefer adventure_runtime.event_clocks, fall back to adventure_definition.event_clocks
    clock_source = getattr(runtime, "event_clocks", None) or []
    if not clock_source and game_state.adventure_definition:
        clock_source = game_state.adventure_definition.event_clocks or []
    for clock in clock_source:
        entry = dict(clock_rt.get(clock.id) or {})
        current_value = int(entry.get("value") or 0)
        is_discovered = clock.discovered or bool(entry.get("discovered", False))
        is_resolved = getattr(clock, "resolved", False) or bool(entry.get("resolved", False))
        clocks.append({
            "id": clock.id,
            "label": clock.label,
            "value": current_value,
            "max_value": clock.max_value,
            "consequence": clock.consequence,
            "clock_type": getattr(clock, "clock_type", "narrative") or "narrative",
            "resolved": is_resolved,
            "resolution_condition": getattr(clock, "resolution_condition", "") or "",
            "discovered": is_discovered,
            "discovery_hint": getattr(clock, "discovery_hint", "") or "",
            "active": bool(entry.get("active", clock.active)),
            "steps": [
                {
                    "step": s.get("step"),
                    "scene_prompt": s.get("scene_prompt") or "",
                    "world_state_change": s.get("world_state_change") or "",
                }
                for s in (clock.steps or [])
            ],
        })
    return clocks


_ENGLISH_MARKERS = {
    " the ", " through ", " from ", " are ", " is ", " a ", " an ", " to ", " with ",
    "recover", "bring", "hidden", "located", "castle", "tunnels", "jewels", "safety",
}


def _compact_text(value: str, limit: int = 220) -> str:
    text = " ".join(str(value or "").replace("\n", " ").split())
    return text[:limit].strip()


def _looks_english(value: str) -> bool:
    text = f" {str(value or '').lower()} "
    if not text.strip():
        return False
    hits = sum(1 for marker in _ENGLISH_MARKERS if marker in text)
    return hits >= 2


def _italianize_common_text(value: str, fallback: str = "") -> str:
    text = _compact_text(value, 260)
    if not text:
        return fallback
    replacements = [
        ("The PCs are fleeing from a crime boss through secret tunnels.", "I personaggi stanno fuggendo da un boss criminale attraverso una rete di tunnel segreti."),
        ("Recover the Irish Crown Jewels", "Recuperare i Gioielli della Corona Irlandese"),
        ("Bring the Jewels to Safety", "Portare i gioielli al sicuro"),
        ("The Irish Crown Jewels are hidden on Speirling Island, located in an eternal fog bank.", "I Gioielli della Corona Irlandese sono nascosti sull'isola di Speirling, avvolta da un banco di nebbia eterno."),
        ("The PCs", "I personaggi"),
        ("PCs", "personaggi"),
        ("are fleeing", "stanno fuggendo"),
        ("from a crime boss", "da un boss criminale"),
        ("through secret tunnels", "attraverso tunnel segreti"),
        ("Recover", "Recuperare"),
        ("Bring", "Portare"),
        ("to Safety", "al sicuro"),
        ("hidden on", "nascosti su"),
        ("located in", "situata in"),
        ("eternal fog bank", "banco di nebbia eterno"),
        ("Castle Tunnels", "Tunnel del castello"),
        ("University of Vienna", "Università di Vienna"),
    ]
    for src, dst in replacements:
        text = text.replace(src, dst)
    if _looks_english(text) and fallback:
        return fallback
    return text


def _skill_for_option(text: str) -> str:
    blob = text.lower()
    if any(w in blob for w in ["parlare", "negoziare", "convincere", "interrogare", "testimone", "png"]):
        return "negoziare"
    if any(w in blob for w in ["forzare", "correre", "fuggire", "inseguire", "tunnel", "uscita"]):
        return "atletica"
    if any(w in blob for w in ["nascond", "silenz", "sorvegl", "passare inosservati"]):
        return "furtività"
    if any(w in blob for w in ["mappa", "rotta", "orient", "percorso", "isola"]):
        return "sopravvivenza"
    return "osservare"


def _best_player_for_skill(players: list[dict], skill: str) -> tuple[int, int]:
    best_id = players[0].get("id", 0) if players else 0
    best_level = 0
    for player in players or []:
        level = int((player.get("skills") or {}).get(skill, 0) or 0)
        if level > best_level:
            best_id = player.get("id", best_id)
            best_level = level
    return best_id, best_level


def _opening_context_from_definition(definition: AdventureDefinition) -> dict:
    first_location = definition.locations[0] if definition.locations else None
    second_location = definition.locations[1] if len(definition.locations) > 1 else None
    first_clue = definition.clues[0] if definition.clues else None
    first_actor = definition.actors[0] if definition.actors else None
    objective = definition.objectives[0].label if definition.objectives else "Completare l'avventura"
    premise = _italianize_common_text(definition.premise, "")
    hook = _italianize_common_text(definition.initial_hook, "")
    if not hook or len(hook) < 80:
        loc_name = first_location.name if first_location else "la prima scena"
        loc_desc = _italianize_common_text(first_location.description, "") if first_location else ""
        clue_text = first_clue.label if first_clue else ""
        actor_text = f" {first_actor.name} è già una presenza da tenere d'occhio." if first_actor else ""
        hook = (
            f"L'avventura si apre a {loc_name}. "
            f"{loc_desc + ' ' if loc_desc else ''}"
            f"La squadra ha un obiettivo concreto: {_italianize_common_text(objective, objective)}. "
            f"Il primo appiglio è {clue_text}, ma va conquistato in scena prima che diventi una prova utile."
            f"{actor_text}"
        )
    if premise and premise != hook:
        opening = f"{premise} {hook}"
    else:
        opening = hook
    if len(opening.split(".")) < 4:
        next_place = second_location.name if second_location else (first_location.name if first_location else "il luogo iniziale")
        opening += f" Da qui la pista punta verso {next_place}, ma la pressione del canovaccio è già in movimento."
    return {
        "narrative": _compact_text(opening, 900),
        "objective": _italianize_common_text(objective, objective),
        "first_location": first_location,
        "second_location": second_location,
        "first_clue": first_clue,
        "first_actor": first_actor,
    }


_SKILL_HINT_MAP: dict[str, str] = {
    "Observation": "osservare",
    "Research": "osservare",
    "Diplomacy": "negoziare",
    "Intimidation": "negoziare",
    "Forensics": "osservare",
    "Detect Lies": "negoziare",
}


def _skill_hint_to_italian(hint: str) -> str:
    return _SKILL_HINT_MAP.get(hint, "")


def _initial_runtime_options(definition: AdventureDefinition, players: list[dict]) -> list[dict]:
    opening_scene_id = definition.locations[0].id if definition.locations else None
    scene_actions = actions_for_scene(None, definition, opening_scene_id, max_actions=4)
    options: list[dict] = []
    for action in scene_actions:
        label = action["label"]
        skill_hint = action.get("skill_hint") or ""
        skill = _skill_hint_to_italian(skill_hint) or _skill_for_option(label)
        player_id, skill_level = _best_player_for_skill(players, skill)
        options.append({
            "text": label,
            "skill": skill,
            "skill_level": skill_level,
            "stat": "intelligenza" if skill in {"osservare", "sopravvivenza"} else ("empatia" if skill == "negoziare" else "agilita"),
            "player_id": player_id,
        })
        if len(options) >= 2:
            break
    options.append({"text": "Azione custom", "skill": "", "skill_level": 0, "stat": "", "player_id": players[0]["id"] if players else 0})
    return options[:3]


def _runtime_revelation_ids_for_token(rt: AdventureRuntimeState, token: str) -> list[str]:
    token = str(token or "").strip()
    if not token:
        return []
    ids: list[str] = []
    if token in (rt.revelation_to_thread_id or {}):
        ids.append(token)
    ids.extend((rt.thread_to_revelation_ids or {}).get(token, []))
    if token.startswith("rev_") and token not in ids:
        ids.append(token)
    return list(dict.fromkeys([rid for rid in ids if rid]))


def _runtime_thread_tokens_for_revelation_ids(rt: AdventureRuntimeState, revelation_ids: list[str]) -> list[str]:
    tokens = []
    for rid in revelation_ids:
        thread_id = (rt.revelation_to_thread_id or {}).get(rid)
        if thread_id:
            tokens.append(thread_id)
        tokens.append(rid)
    return list(dict.fromkeys([t for t in tokens if t]))


def _refresh_runtime_derived_state(rt: AdventureRuntimeState) -> None:
    discovered = set(rt.discovered_clue_ids or [])
    active = set(rt.active_revelation_ids or [])
    ready = set(rt.ready_revelation_ids or [])
    resolved = set(rt.resolved_revelation_ids or [])

    definition = game_state.adventure_definition
    if definition:
        for revelation in definition.revelations:
            if revelation.id in resolved:
                active.discard(revelation.id)
                ready.discard(revelation.id)
                continue
            required = list(revelation.required_clues or [])
            if required:
                minimum = min(2, max(1, len(required)))
                if len([cid for cid in required if cid in discovered]) >= minimum:
                    ready.add(revelation.id)
                    active.add(revelation.id)
            elif revelation.status in {"hidden", "seeded", "available", "revealed"}:
                active.add(revelation.id)

        for finale in definition.finale_conditions:
            entry = dict((rt.finale_runtime or {}).get(finale.id) or {})
            if entry.get("status") in {"satisfied", "failed"}:
                rt.finale_runtime[finale.id] = entry
                continue
            required_clues = set(entry.get("required_clues") or finale.required_clues or [])
            required_threads = set(entry.get("required_threads") or finale.required_threads or [])
            if not required_threads:
                required_threads = {
                    definition_thread
                    for rid in (finale.depends_on or [])
                    for definition_thread in [(rt.revelation_to_thread_id or {}).get(rid, "")]
                    if definition_thread
                }
            clues_ok = not required_clues or required_clues.issubset(discovered)
            threads_ok = not required_threads or required_threads.issubset(set(_runtime_thread_tokens_for_revelation_ids(rt, list(resolved))))
            if clues_ok and threads_ok:
                entry["status"] = "available"
            elif entry.get("status") not in {"seeded", "available"}:
                entry["status"] = entry.get("status") or "locked"
            rt.finale_runtime[finale.id] = entry

    rt.active_revelation_ids = [rid for rid in rt.active_revelation_ids if rid not in resolved]
    for rid in sorted(active):
        if rid not in rt.active_revelation_ids and rid not in resolved:
            rt.active_revelation_ids.append(rid)
    rt.ready_revelation_ids = [rid for rid in rt.ready_revelation_ids if rid not in resolved]
    for rid in sorted(ready):
        if rid not in rt.ready_revelation_ids and rid not in resolved:
            rt.ready_revelation_ids.append(rid)


def _update_locked_context(updates: dict, narrative: str = "") -> None:
    """Aggiorna game_state.locked_context con i fatti pilastro appena emersi.

    locked_context è una lista corta (max 12 voci) di fatti che vengono iniettati
    in ogni turno — indipendentemente da quanti turni fa sono stati scoperti.
    Non viene mai troncata dalla finestra di contesto della storia recente.

    Criteri di inclusione (solo fatti ad alto valore narrativo):
    - Thread chiusi (la verità di una pista risolta)
    - NPC smascherati (nome + ruolo già pubblico)
    - Indizi trovati che contengono una rivelazione chiave (revelations resolved)
    - Verità nascoste ora rivelate
    """
    if not game_state.adventure_definition:
        return

    defn = game_state.adventure_definition
    rt = getattr(game_state, "adventure_runtime_state", None)
    locked = game_state.locked_context

    def _add(fact: str) -> None:
        if fact and fact not in locked:
            locked.append(fact)
            # Mantieni max 12 voci — rimuovi le più vecchie se necessario
            if len(locked) > 12:
                locked.pop(0)

    # 1. Thread/rivelazioni chiuse → aggiungi la risposta canonica
    for closed in (updates.get("closed_threads") or []) + (updates.get("thread_resolved") or []):
        token = str(closed).split("→", 1)[0].strip()
        # Cerca la rivelazione corrispondente
        for rev in (defn.revelations or []):
            if token and (token == rev.id or token in rev.statement):
                _add(f"RISOLTO: {rev.statement[:120]}")
                break
        # Cerca nei story_threads
        for t in (defn.story_threads or []):
            if token and (token == t.get("id") or token in t.get("question", "")):
                answer = t.get("true_answer") or t.get("payoff") or t.get("question", "")
                _add(f"PISTA CHIUSA: {answer[:120]}")
                break

    # 2. NPC smascherati → aggiungi identità pubblica
    for update in (updates.get("actor_updates") or []) + (updates.get("npc_updates") or []):
        if not isinstance(update, dict):
            continue
        status = str(update.get("arc_status") or update.get("status") or "")
        if status in ("exposed", "captured"):
            aid = str(update.get("id") or update.get("actor_id") or update.get("npc_id") or "").strip()
            actor = next((a for a in (defn.actors or []) if a.id == aid), None)
            if actor:
                role = actor.role or "sconosciuto"
                goal = (actor.goal or "")[:80]
                _add(f"SMASCHERATO: {actor.name} ({role}) — {goal}")

    # 3. Indizi trovati che corrispondono a una revelation risolta
    for cid in (updates.get("clues_found") or []):
        clue = next((c for c in (defn.clues or []) if c.id == cid), None)
        if not clue:
            continue
        # Aggiungi solo se l'indizio ha revelation_ids (alto valore narrativo)
        if getattr(clue, "revelation_ids", None):
            reveals = clue.reveals or clue.label or cid
            _add(f"PROVA OTTENUTA: {reveals[:120]}")

    # 4. Verità nascoste rivelate
    for update in (updates.get("truth_updates") or []):
        if isinstance(update, dict) and update.get("revealed"):
            tid = str(update.get("id") or update.get("truth_id") or "").strip()
            truth = next((h for h in (defn.core_truths or []) if h.id == tid), None)
            if truth and truth.statement:
                _add(f"VERITÀ RIVELATA: {truth.statement[:120]}")


def _sync_runtime_state_from_updates(updates: dict, narrative: str = "") -> None:
    """Mantiene AdventureRuntimeState come stato autoritativo lato backend."""
    if not game_state.adventure_runtime_state:
        return
    rt = game_state.adventure_runtime_state
    newly_found = [cid for cid in (updates.get("clues_found") or []) if cid not in rt.discovered_clue_ids]
    for cid in newly_found:
        rt.discovered_clue_ids.append(cid)
        if cid in rt.partial_clue_ids:
            rt.partial_clue_ids.remove(cid)
    # NPC pressure: increment for each newly discovered clue
    if newly_found and game_state.adventure_definition:
        fired_events = []
        try:
            changed, fired_events = update_pressure_from_clues(
                newly_found, game_state.adventure_definition, rt
            )
            for actor_id, new_pressure in changed:
                print(f"[npc_state] {actor_id}: pressione → {new_pressure}/10")
            if fired_events:
                existing = game_state.flags.get("pending_npc_events") or []
                game_state.flags["pending_npc_events"] = existing + fired_events
        except Exception as npc_e:
            print(f"[npc_state] errore (non bloccante): {npc_e}")
        # Anti-deadlock: if pressure_events destroyed clues, ensure revelations stay reachable
        if fired_events and game_state.adventure_definition:
            try:
                fixed = check_and_fix_deadlocks(game_state.adventure_definition, rt)
                if fixed:
                    existing_npc = game_state.flags.get("pending_npc_events") or []
                    for clue in fixed:
                        existing_npc.append({
                            "actor_id": "system",
                            "actor_name": "Sistema",
                            "action": "failforward_clue",
                            "narration": f"[Anti-deadlock] Pista alternativa iniettata: '{clue['label']}'",
                            "clue_id": clue["id"],
                        })
                    game_state.flags["pending_npc_events"] = existing_npc
            except Exception as dl_e:
                print(f"[deadlock_guard] errore (non bloccante): {dl_e}")
    for progress in updates.get("clue_progress") or []:
        cid = progress.get("clue_id") or progress.get("id")
        if cid and cid not in rt.partial_clue_ids and cid not in rt.discovered_clue_ids:
            rt.partial_clue_ids.append(cid)
    for closed in (updates.get("closed_threads") or []) + (updates.get("thread_resolved") or []):
        token = str(closed).split("→", 1)[0].strip()
        for rid in _runtime_revelation_ids_for_token(rt, token):
            if rid not in rt.resolved_revelation_ids:
                rt.resolved_revelation_ids.append(rid)
            if rid in rt.ready_revelation_ids:
                rt.ready_revelation_ids.remove(rid)
            if rid in rt.active_revelation_ids:
                rt.active_revelation_ids.remove(rid)
    for update in updates.get("revelation_updates") or []:
        if not isinstance(update, dict):
            continue
        tokens = [update.get("id"), update.get("revelation_id"), update.get("thread_id")]
        target_ids = []
        for token in tokens:
            target_ids.extend(_runtime_revelation_ids_for_token(rt, str(token or "")))
        status = str(update.get("status") or "").strip()
        for rid in list(dict.fromkeys(target_ids)):
            if status in {"resolved", "revealed"} and rid not in rt.resolved_revelation_ids:
                rt.resolved_revelation_ids.append(rid)
            elif status in {"available", "ready", "ready_to_deduce"} and rid not in rt.ready_revelation_ids:
                rt.ready_revelation_ids.append(rid)
            if status in {"hidden", "seeded", "available", "revealed"} and rid not in rt.active_revelation_ids:
                rt.active_revelation_ids.append(rid)
    for update in updates.get("objective_updates") or []:
        if not isinstance(update, dict):
            continue
        oid = str(update.get("id") or update.get("objective_id") or "").strip()
        status = str(update.get("status") or "").strip()
        if not oid:
            continue
        if status in {"complete", "completed"}:
            if oid not in rt.completed_objective_ids:
                rt.completed_objective_ids.append(oid)
            if oid in rt.active_objective_ids:
                rt.active_objective_ids.remove(oid)
        elif status == "failed":
            if oid not in rt.failed_objective_ids:
                rt.failed_objective_ids.append(oid)
            if oid in rt.active_objective_ids:
                rt.active_objective_ids.remove(oid)
        elif status in {"active", "available"} and oid not in rt.active_objective_ids:
            rt.active_objective_ids.append(oid)
    for update in (updates.get("actor_updates") or []) + (updates.get("npc_updates") or []):
        if not isinstance(update, dict):
            continue
        aid = str(update.get("id") or update.get("actor_id") or update.get("npc_id") or "").strip()
        if aid:
            entry = dict((rt.actor_runtime or {}).get(aid) or {})
            if update.get("status") or update.get("arc_status"):
                entry["status"] = update.get("arc_status") or update.get("status")
            if update.get("location") or update.get("location_id"):
                entry["location_id"] = update.get("location_id") or update.get("location")
            if update.get("attitude"):
                entry["attitude"] = update.get("attitude")
            # N5: witness state changes from player actions (reassure/protect)
            if update.get("witness_state"):
                entry["witness_state"] = update["witness_state"]
                entry["fearful_turns_ignored"] = 0  # reset counter on interaction
            rt.actor_runtime[aid] = entry
    for update in updates.get("faction_updates") or []:
        if not isinstance(update, dict):
            continue
        fid = str(update.get("id") or update.get("faction_id") or "").strip()
        if fid:
            entry = dict((rt.faction_runtime or {}).get(fid) or {})
            if update.get("status"):
                entry["status"] = update.get("status")
            if update.get("pressure") is not None:
                entry["pressure"] = int(update.get("pressure") or 0)
            rt.faction_runtime[fid] = entry
    for update in updates.get("location_updates") or []:
        if not isinstance(update, dict):
            continue
        lid = str(update.get("id") or update.get("location_id") or update.get("node_id") or "").strip()
        if lid:
            entry = dict((rt.location_runtime or {}).get(lid) or {})
            if update.get("status"):
                entry["status"] = update.get("status")
            if update.get("access_state"):
                entry["access_state"] = update.get("access_state")
            rt.location_runtime[lid] = entry
    for raw in updates.get("location_access") or []:
        if isinstance(raw, dict):
            lid = str(raw.get("id") or raw.get("location_id") or raw.get("node_id") or raw.get("name") or "").strip()
            access_state = str(raw.get("access_state") or "open")
        else:
            lid = str(raw or "").strip()
            access_state = "open"
        if lid:
            entry = dict((rt.location_runtime or {}).get(lid) or {})
            entry["access_state"] = access_state
            if entry.get("status") in {None, "", "hidden", "unknown", "locked"}:
                entry["status"] = "known"
            rt.location_runtime[lid] = entry
    # I clock NON avanzano più con threat_increase globale:
    # ogni clock ha il proprio delta in clock_updates (gestito dal world_simulator per-clock).
    for update in updates.get("clock_updates") or []:
        if not isinstance(update, dict):
            continue
        cid = str(update.get("id") or update.get("clock_id") or "").strip()
        if cid:
            entry = dict((rt.clock_runtime or {}).get(cid) or {})
            if update.get("value") is not None:
                entry["value"] = int(update.get("value") or 0)
            if update.get("delta") is not None:
                new_val = int(entry.get("value") or 0) + int(update.get("delta") or 0)
                # Trova max_value dalla definizione del clock (sta su AdventureDefinition, non su RuntimeState)
                _defn = game_state.adventure_definition
                _defn_clocks = _defn.event_clocks if _defn else []
                clock_def = next((c for c in (_defn_clocks or []) if c.id == cid), None)
                max_v = clock_def.max_value if clock_def else 999
                entry["value"] = min(new_val, max_v)
            if update.get("active") is not None:
                entry["active"] = bool(update.get("active"))
            if update.get("discovered") is True:
                entry["discovered"] = True
            if update.get("resolved") is True:
                entry["resolved"] = True
            rt.clock_runtime[cid] = entry
    for key, value in list(rt.pressure_runtime.items()):
        entry = dict(value or {})
        entry["value"] = int(entry.get("value") or 0) + int(updates.get("threat_increase") or 0)
        rt.pressure_runtime[key] = entry
    for runtime_key, update_key in [("pressure_runtime", "pressure_updates"), ("resource_runtime", "resource_updates")]:
        container = dict(getattr(rt, runtime_key) or {})
        for update in updates.get(update_key) or []:
            if not isinstance(update, dict):
                continue
            uid = str(update.get("id") or update.get("pressure_id") or update.get("resource_id") or "").strip()
            if uid:
                entry = dict(container.get(uid) or {})
                if update.get("value") is not None:
                    entry["value"] = int(update.get("value") or 0)
                if update.get("delta") is not None:
                    entry["value"] = int(entry.get("value") or 0) + int(update.get("delta") or 0)
                container[uid] = entry
        setattr(rt, runtime_key, container)
    for update in updates.get("finale_updates") or []:
        if not isinstance(update, dict):
            continue
        fid = str(update.get("id") or update.get("finale_id") or "").strip()
        if fid:
            entry = dict((rt.finale_runtime or {}).get(fid) or {})
            if update.get("status"):
                entry["status"] = update.get("status")
            rt.finale_runtime[fid] = entry
    for update in updates.get("truth_updates") or []:
        if not isinstance(update, dict):
            continue
        tid = str(update.get("id") or update.get("truth_id") or "").strip()
        if tid:
            entry = dict((rt.truth_runtime or {}).get(tid) or {})
            if update.get("revealed") is not None:
                entry["revealed"] = bool(update.get("revealed"))
                if entry["revealed"] and tid not in rt.revealed_truth_ids:
                    rt.revealed_truth_ids.append(tid)
            rt.truth_runtime[tid] = entry
    if isinstance(updates.get("flags"), dict):
        rt.flags = {**(rt.flags or {}), **updates["flags"]}
    if game_state.map_state:
        rt.current_scene_id = game_state.map_state.current_node_id
        if rt.current_scene_id:
            entry = dict((rt.location_runtime or {}).get(rt.current_scene_id) or {})
            entry.setdefault("access_state", "open")
            entry["status"] = "visited"
            rt.location_runtime[rt.current_scene_id] = entry
    if narrative:
        rt.history = [*rt.history, narrative[:300]][-20:]
    _refresh_runtime_derived_state(rt)
    game_state.current_objective_ids = list(rt.active_objective_ids)
    game_state.active_revelation_ids = list(rt.active_revelation_ids)
    game_state.active_clock_ids = list((rt.clock_runtime or {}).keys())
    game_state.active_pressure_ids = list((rt.pressure_runtime or {}).keys())
    _update_locked_context(updates, narrative)

    # ── Soft escalation: aggiorna stall counter ───────────────────────────────
    clues_found_now = list(updates.get("clues_found") or [])
    threads_closed_now = list((updates.get("closed_threads") or []) + (updates.get("thread_resolved") or []))
    if clues_found_now or threads_closed_now:
        game_state.consecutive_no_progress_turns = 0
    else:
        game_state.consecutive_no_progress_turns += 1


@app.post("/game/master/start-bible")
def master_start_bible_endpoint(payload: MasterStartBiblePayload):
    """Scena d'apertura runtime-first.

    Il vecchio avvio "bibbia senza runtime" e stato rimosso: ogni partita deve
    avere un AdventureDefinition compilato prima di entrare in gioco.
    """
    _sync_players_from_payload(payload.players)
    if not game_state.adventure_definition and payload.adventure:
        try:
            defn_data = payload.adventure.get("adventure_definition") or payload.adventure
            game_state.adventure_definition = AdventureDefinition(**defn_data)
            game_state.adventure_definition_id = game_state.adventure_definition.id
        except Exception:
            pass
    if not game_state.adventure_definition:
        raise HTTPException(
            status_code=409,
            detail="Avventura non compilata: crea o importa un AdventureDefinition prima di avviare il Master.",
        )
    if not game_state.map_state:
        game_state.map_state = _build_map_from_definition(game_state.adventure_definition)
    _seed_world_npcs_from_actors(game_state.adventure_definition)
    opening = _opening_context_from_definition(game_state.adventure_definition)
    opening_narrative = generate_opening_scene(game_state.adventure_definition, payload.players)
    _ensure_runtime_scene(opening_narrative)
    if game_state.story:
        game_state.story.premise = opening_narrative
    if game_state.mission:
        game_state.mission.objective = opening["objective"]
    options = _initial_runtime_options(game_state.adventure_definition, payload.players)
    resp: dict = {
        "narrative": opening_narrative,
        "roll": None,
        "options": options,
        "state_updates": {
            "clue_progress": [], "clues_found": [], "npc_updates": [], "new_threads": [],
            "closed_threads": [], "threat_increase": 0, "activate_combat": False,
            "combat_scene": None, "combat_over": False, "story_over": False, "victory": False,
            "allowed_escalation_tier": game_state.allowed_escalation_tier,
            "allowed_escalation_types": game_state.allowed_escalation_types,
            "forbidden_escalation_types": game_state.forbidden_escalation_types,
            "director_reason": "compiled_runtime_start",
        },
    }
    if game_state.map_state:
        resp["map_state"] = game_state.map_state.model_dump()
    if game_state.adventure_definition or game_state.adventure_runtime:
        resp["clocks_data"] = _build_clocks_data(game_state.adventure_runtime, game_state.adventure_runtime_state)
    return resp

@app.post("/game/master/turn-bible")
def master_turn_bible_endpoint(payload: MasterTurnBiblePayload):
    """Turno Master con bibbia e tracking stato."""
    # R1: genera un turn_id univoco per questo turno
    _turn_id = str(uuid.uuid4())[:8]
    game_state.turn_id = _turn_id

    _sync_players_from_payload(payload.players)
    _ensure_runtime_scene()
    if not game_state.adventure_definition and payload.adventure:
        try:
            defn_data = payload.adventure.get("adventure_definition") or payload.adventure
            game_state.adventure_definition = AdventureDefinition(**defn_data)
            game_state.adventure_definition_id = game_state.adventure_definition.id
        except Exception:
            pass
    if not game_state.adventure_definition:
        raise HTTPException(
            status_code=409,
            detail="Turno bloccato: manca AdventureDefinition compilato nel GameState.",
        )
    _seed_world_npcs_from_actors(game_state.adventure_definition)
    reset_last_request_tokens()
    # Tiro GURPS reale prima di chiamare Claude — vincolante per la narrativa
    active_player = next((p for p in payload.players if p["id"] == payload.active_player_id), payload.players[0] if payload.players else None)
    roll_detail = None
    if active_player:
        threat_level = payload.game_state_data.get("threat_level", 1)
        in_combat = bool(payload.game_state_data.get("in_combat"))
        scene_tags = list(game_state.scene.scene_tags) if game_state.scene else []
        if _needs_roll(payload.player_action, threat_level, in_combat):
            roll_detail = roll_for_player_action(active_player, payload.player_action, threat_level, scene_tags)
            game_state.last_roll_details = [roll_detail]
        else:
            game_state.last_roll_details = []

    # Inject NPC pressure context and runtime-created clues into adventure dict
    adventure_with_npc_state = dict(payload.adventure or {})
    if game_state.adventure_definition and game_state.adventure_runtime_state:
        try:
            npc_ctx = build_npc_pressure_context(
                game_state.adventure_definition,
                game_state.adventure_runtime_state,
            )
            if npc_ctx:
                adventure_with_npc_state["npc_pressure_context"] = npc_ctx
            # Inject runtime-created clues so the LLM knows they exist
            rt_state = game_state.adventure_runtime_state
            injected = list(rt_state.injected_clues or [])
            destroyed = list(rt_state.destroyed_clue_ids or [])
            if injected or destroyed:
                adventure_with_npc_state["injected_clues"] = injected
                adventure_with_npc_state["destroyed_clue_ids"] = destroyed
        except Exception as npc_ctx_e:
            print(f"[npc_state] context build error (non bloccante): {npc_ctx_e}")
    # Inject locked_context — fatti pilastro che non devono mai sparire dal prompt
    if game_state.locked_context:
        adventure_with_npc_state["locked_context"] = list(game_state.locked_context)

    # Inject soft escalation data nel game_state_data
    _gsd = dict(payload.game_state_data or {})
    # N5: inietta npc_runtime persistente (witness_state + fearful_turns_ignored)
    if game_state.adventure_runtime_state and game_state.adventure_runtime_state.actor_runtime:
        _merged_npc_rt = dict(_gsd.get("npc_runtime") or {})
        for _aid, _adata in game_state.adventure_runtime_state.actor_runtime.items():
            _existing = dict(_merged_npc_rt.get(_aid) or {})
            for _k in ("witness_state", "fearful_turns_ignored"):
                if _k in _adata:
                    _existing[_k] = _adata[_k]
            _merged_npc_rt[_aid] = _existing
        _gsd["npc_runtime"] = _merged_npc_rt
    _gsd["consecutive_no_progress_turns"] = game_state.consecutive_no_progress_turns
    # clues_found_this_turn: indizi trovati nell'ultimo turno (per progress awareness)
    # Derivati dal runtime state: quelli trovati dall'ultimo sync
    _prev_found = set(payload.game_state_data.get("clues_found") or [])
    _curr_found = set((game_state.adventure_runtime_state.discovered_clue_ids or []) if game_state.adventure_runtime_state else [])
    _gsd["clues_found_this_turn"] = list(_curr_found - _prev_found)
    # Inietta stato combattimento live: HP corrente entità, ultimo esito round, stato giocatori
    if payload.game_state_data.get("in_combat") and game_state.scene and game_state.scene.entities:
        _gsd["live_combat_entities"] = [
            {
                "id": e.id, "name": e.name, "type": e.type,
                "hp": e.hp, "max_hp": e.max_hp,
                "status": getattr(e, "status", "") or ("eliminato" if e.hp <= 0 else "vivo"),
            }
            for e in game_state.scene.entities if e.type == "enemy"
        ]
    if game_state.last_attack_result:
        _gsd["last_combat_round"] = game_state.last_attack_result

    # L2: comprimi la history se è cresciuta troppo — risparmia token e mantiene coerenza
    _history_for_turn = payload.history
    _history_was_compressed = False
    if len(payload.history) > _COMPRESS_THRESHOLD:
        _compressed = compress_history(payload.history)
        if len(_compressed) < len(payload.history):
            _history_for_turn = _compressed
            _history_was_compressed = True

    result = master_turn_with_bible(
        payload.genre, payload.players, _history_for_turn,
        payload.player_action, payload.active_player_id,
        adventure_with_npc_state, _gsd,
        prerolled=roll_detail,
    )
    # Arricchisce combat_scene con stat GURPS persistenti dai WorldNPC
    su = result.get("state_updates") or {}
    if not payload.game_state_data.get("in_combat"):
        su = _force_hot_zone_combat_update(su, payload.player_action)
        result["state_updates"] = su
    # ── Soft escalation post-processing: frena threat_increase se ci sono progressi
    _clues_just_found = list(su.get("clues_found") or [])
    _threads_just_closed = list((su.get("closed_threads") or []) + (su.get("thread_resolved") or []))
    _clue_progress_made = bool(su.get("clue_progress"))
    _current_threat_increase = int(su.get("threat_increase") or 0)
    if (_clues_just_found or _threads_just_closed) and _current_threat_increase > 0:
        # Indizio trovato o thread chiuso → nessuna pressione aggiuntiva questo turno
        su["threat_increase"] = 0
        print(f"[soft_escalation] threat_increase azzerato: indizio/thread trovato ({_clues_just_found or _threads_just_closed})")
    elif _clue_progress_made and _current_threat_increase > 1:
        # Progresso parziale → cap a 1
        su["threat_increase"] = 1
        print(f"[soft_escalation] threat_increase limitato a 1: progresso parziale registrato")
    elif game_state.consecutive_no_progress_turns >= 3 and _current_threat_increase == 0 and not (su.get("activate_combat") or su.get("story_over")):
        # Stallo prolungato + nessuna pressione → aggiungi 1 per spingere la storia
        su["threat_increase"] = 1
        print(f"[soft_escalation] threat_increase +1: stallo da {game_state.consecutive_no_progress_turns} turni")
    result["state_updates"] = su

    print(f"[turn-bible] activate_combat={su.get('activate_combat')} combat_over={su.get('combat_over')} combat_scene={'presente' if su.get('combat_scene') else 'assente'}")
    if su.get("activate_combat") and su.get("combat_scene"):
        _already_in_combat = bool(payload.game_state_data.get("in_combat"))
        su["combat_scene"] = _enrich_combat_scene(su["combat_scene"])
        # Se già in combattimento, preserva HP corrente delle entità live
        _persist_combat_scene(su["combat_scene"], preserve_live_hp=_already_in_combat)
        result["state_updates"] = su
    if su.get("combat_over"):
        game_state.pending_attack = None
        if game_state.scene:
            game_state.scene.entities = []
    game_state.allowed_escalation_tier = int(su.get("allowed_escalation_tier", game_state.allowed_escalation_tier or 3) or 3)
    game_state.allowed_escalation_types = list(su.get("allowed_escalation_types") or game_state.allowed_escalation_types or [])
    game_state.forbidden_escalation_types = list(su.get("forbidden_escalation_types") or game_state.forbidden_escalation_types or [])
    game_state.blocked_major_events = list(su.get("blocked_major_events") or su.get("blocked_state_updates") or [])
    game_state.downgraded_events = list(su.get("downgraded_events") or [])
    game_state.director_reason = str(su.get("director_reason") or "")
    apply_story_updates(
        game_state,
        su,
        outcome=str((roll_detail or {}).get("outcome") or "successo pieno"),
    )
    if game_state.scene:
        game_state.scene.threat_level += int(su.get("threat_increase") or 0)

    # ── Clock engine: tick basato sull'outcome del tiro ──
    clock_events = []
    if (
        game_state.adventure_definition
        and game_state.adventure_runtime_state
        and roll_detail
    ):
        outcome_str = str((roll_detail or {}).get("outcome") or "successo pieno")
        try:
            clock_events, _ = tick_clocks(
                outcome_str,
                game_state.adventure_definition,
                game_state.adventure_runtime_state,
            )
            if clock_events:
                for ev in clock_events:
                    print(f"[clock_engine] {format_clock_event_narrative(ev)}")
        except Exception as ce:
            print(f"[clock_engine] errore (non bloccante): {ce}")
    if clock_events:
        result["clock_events"] = clock_events

    # Flush pending NPC pressure events to the response
    pending_npc_events = (game_state.flags or {}).pop("pending_npc_events", [])
    if pending_npc_events:
        result["npc_events"] = pending_npc_events

    # 1. Regex fallback: sposta il giocatore se l'azione testo corrisponde a un pattern di movimento
    _update_map_position(payload.player_action)

    # 2. Override esplicito: l'AI ha compilato new_location_id in state_updates
    _ai_new_loc = str(su.get("new_location_id") or "").strip()
    if _ai_new_loc and game_state.map_state and _ai_new_loc in game_state.map_state.nodes:
        game_state.map_state.current_node_id = _ai_new_loc
        game_state.map_state.nodes[_ai_new_loc].visited = True
        print(f"[map] AI ha spostato il gruppo → {_ai_new_loc}")
    elif _ai_new_loc and game_state.map_state:
        # Fallback: cerca per nome parziale se l'id non corrisponde esattamente
        _ai_loc_low = _ai_new_loc.lower()
        for nid, node in game_state.map_state.nodes.items():
            if nid.lower() == _ai_loc_low or node.name.lower() == _ai_loc_low or _ai_loc_low in node.name.lower():
                game_state.map_state.current_node_id = nid
                node.visited = True
                print(f"[map] AI ha spostato il gruppo (fuzzy) → {nid} ({node.name})")
                break

    if not game_state.map_state and game_state.adventure_definition:
        game_state.map_state = _build_map_from_definition(game_state.adventure_definition)
    if game_state.map_state:
        result["map_state"] = game_state.map_state.model_dump()
    # Invia stato clock aggiornato al frontend
    if game_state.adventure_runtime:
        result["clocks_data"] = _build_clocks_data(game_state.adventure_runtime, game_state.adventure_runtime_state)
    _sync_runtime_state_from_updates(su, result.get("narrative", ""))

    # Valutazione vittorie personali quando la storia finisce
    if su.get("story_over"):
        final_narrative = result.get("narrative", "")
        group_victory = bool(su.get("victory", False))
        personal = evaluate_personal_victories(payload.players, payload.adventure, final_narrative, group_victory)
        game_state.personal_victories = personal
        su["personal_victories"] = personal
        result["state_updates"] = su

    # Persiste lo stato world sul disco dopo ogni turno
    adv_id = _adventure_id(payload.adventure)
    if adv_id:
        merged = _merge_game_state(payload.game_state_data, result.get("state_updates") or {})
        patch = {"live_game_state": merged}
        if game_state.adventure_runtime_state:
            patch["runtime_state"] = game_state.adventure_runtime_state.model_dump()
        update_runtime(adv_id, patch)

    # N5: applica witness_updates al runtime actor_runtime per persistenza tra turni
    _witness_updates = result.get("witness_updates") or []
    if _witness_updates and game_state.adventure_runtime_state:
        _art = game_state.adventure_runtime_state
        _touched_witness_ids = set()
        for wu in _witness_updates:
            wid = wu.get("npc_id") or ""
            if not wid:
                continue
            _entry = dict((_art.actor_runtime or {}).get(wid) or {})
            new_ws = wu.get("witness_state") or wu.get("previous_witness_state") or "available"
            _entry["witness_state"] = new_ws
            # Incrementa fearful_turns_ignored se il witness è ancora fearful
            if new_ws == "fearful":
                _entry["fearful_turns_ignored"] = int(_entry.get("fearful_turns_ignored") or 0) + 1
            else:
                _entry["fearful_turns_ignored"] = 0
            _art.actor_runtime[wid] = _entry
            _touched_witness_ids.add(wid)
        # Esponi il npc_runtime aggiornato nella risposta per sync frontend
        result["npc_runtime"] = {k: dict(v) for k, v in (_art.actor_runtime or {}).items()}

    result["call_tokens"] = get_last_request_tokens()
    result["turn_id"] = _turn_id
    if _history_was_compressed:
        result["compressed_history"] = _history_for_turn

    # ── Auto-rilevamento oggetti dalla narrativa AI ───────────────────────────
    # Analizza il testo prodotto dall'AI GM: se menziona oggetti trovati
    # (diario, chiave, scanner, ecc.) li aggiunge automaticamente al loot_pool.
    _narrative_text = result.get("narrative", "") or ""
    if _narrative_text and game_state.scene:
        _cur_location = ""
        if game_state.map_state and game_state.map_state.current_node_id:
            _cur_node = game_state.map_state.nodes.get(game_state.map_state.current_node_id)
            _cur_location = _cur_node.name if _cur_node else ""
        _new_loot = _extract_found_items_from_narrative(_narrative_text, game_state, scene_location=_cur_location)
        if _new_loot:
            game_state.loot_pool.extend(_new_loot)
            result["loot_pool"] = [e.model_dump() for e in game_state.loot_pool if e.collected_by == 0]
            print(f"[loot] auto-detected {len(_new_loot)} item/i dalla narrativa AI: {[e.item.name for e in _new_loot]}")

    return result

class CharacterAIPayload(BaseModel):
    genre: str
    description: str

@app.post("/game/character/generate-ai")
def character_generate_ai(payload: CharacterAIPayload):
    """Genera un CharacterDraft da descrizione in linguaggio libero, poi lo valida."""
    draft_dict = generate_character_from_description(payload.genre, payload.description)
    if "error" in draft_dict:
        return draft_dict
    try:
        draft = CharacterDraft(**{k: v for k, v in draft_dict.items() if k in CharacterDraft.model_fields})
        validation = validate_draft(draft)
        return {"draft": draft_dict, "validation": validation}
    except Exception as e:
        return {"draft": draft_dict, "validation": None, "error": str(e)}

class BackstoryPayload(BaseModel):
    characters: list[dict]
    adventure: dict
    genre: str

@app.post("/game/character/enrich-backstory")
def enrich_backstory(payload: BackstoryPayload):
    """Genera backstory + vantaggi/svantaggi contestuali per un pool di personaggi in parallelo."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    results = list(payload.characters)
    def _enrich(args):
        idx, ch = args
        return idx, enrich_character_with_backstory(ch, payload.adventure, payload.genre)
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_enrich, (i, ch)): i for i, ch in enumerate(payload.characters)}
        for future in as_completed(futures):
            try:
                idx, enriched = future.result()
                results[idx] = enriched
            except Exception as e:
                print(f"[enrich-backstory] errore slot {futures[future]}: {e}")
    return {"characters": results}


@app.get("/game/state")
def get_game_state():
    snapshot = game_state.model_copy(deep=False)
    data = snapshot.model_dump()
    data["in_combat"] = bool(
        game_state.pending_attack
        or (
            game_state.scene
            and any(e.type == "enemy" and e.hp > 0 for e in game_state.scene.entities)
        )
    )
    game_state.last_roll_details = []   # consuma i dettagli dopo la prima lettura
    return data

@app.get("/game/state/sync")
def get_game_state_sync():
    """Sync rapido: restituisce turn_id + campi essenziali per riallineare il client.
    Usato dal frontend quando sospetta di avere uno stato stale (es. dopo reconnect).
    """
    clocks: list[dict] = []
    if game_state.adventure_runtime and game_state.adventure_runtime_state:
        try:
            clocks = _build_clocks_data(game_state.adventure_runtime, game_state.adventure_runtime_state)
        except Exception:
            pass
    map_dump = game_state.map_state.model_dump() if game_state.map_state else None
    rt_state = game_state.adventure_runtime_state
    return {
        "turn_id": game_state.turn_id,
        "turn": game_state.turn,
        "clocks_data": clocks,
        "map_state": map_dump,
        "game_state_snapshot": {
            "threat_level": game_state.scene.threat_level if game_state.scene else 0,
            "in_combat": bool(
                game_state.pending_attack
                or (game_state.scene and any(e.type == "enemy" and e.hp > 0 for e in game_state.scene.entities))
            ),
            "discovered_clue_ids": list(rt_state.discovered_clue_ids) if rt_state else [],
            "active_objective_ids": list(rt_state.active_objective_ids) if rt_state else [],
            "locked_context": list(game_state.locked_context),
        },
    }


@app.get("/game/genres")
def get_genres():
    return {"genres": list(GENRE_PACKS.keys())}

@app.get("/game/debug-world")
def get_debug_world():
    return {"story": game_state.story, "map_state": game_state.map_state}

@app.post("/game/setup")
def setup_game(payload: SetupPayload):
    global game_state, tactical_map_image_cache
    set_active_provider(payload.provider)
    game_state = prepare_team_setup(payload.genre, provider=payload.provider)
    game_state.team_setup.image_provider = payload.image_provider
    tactical_map_image_cache = {}
    return game_state

@app.post("/game/select-team")
def select_team(payload: TeamSelectionPayload):
    global game_state, tactical_map_image_cache
    if not payload.adventure_bible or not payload.adventure_bible.get("adventure_definition"):
        raise HTTPException(
            status_code=400,
            detail="Selezione squadra bloccata: il vecchio avvio procedurale e stato rimosso. Compila prima un'avventura.",
        )
    game_state = start_game_from_selection(game_state, payload.selected_player_ids, payload.custom_names, payload.adventure_bible)
    if payload.adventure_bible:
        definition_data = payload.adventure_bible.get("adventure_definition")
        runtime_data = payload.adventure_bible.get("runtime_state")
        try:
            if definition_data:
                definition = AdventureDefinition(**definition_data)
                game_state.adventure_definition_id = definition.id
                game_state.adventure_definition = definition
            if runtime_data:
                runtime_state = AdventureRuntimeState(**runtime_data)
                game_state.adventure_runtime_state = runtime_state
                game_state.current_objective_ids = list(runtime_state.active_objective_ids)
                game_state.active_revelation_ids = list(runtime_state.active_revelation_ids)
                game_state.active_clock_ids = list(runtime_state.clock_runtime.keys())
                game_state.active_pressure_ids = list(runtime_state.pressure_runtime.keys())
        except Exception as e:
            print(f"[select-team] runtime bridge non applicato: {type(e).__name__}: {e}")
    tactical_map_image_cache = {}
    return game_state

@app.post("/game/generate-avatar")
def gen_avatar(payload: AvatarGenPayload):
    provider = _resolve_image_provider()
    if not provider:
        return {"avatar_b64": None, "available": False, "provider": "none", "error": "Generazione grafica disabilitata o nessun provider configurato"}
    set_active_provider(provider)
    if payload.photo_b64:
        avatar = generate_character_avatar(payload.photo_b64, payload.genre, payload.role, payload.archetype)
    else:
        # Nessuna foto — genera da descrizione testuale; usa nome+descrizione per unicità
        display_name = payload.name or payload.archetype or payload.role
        desc = payload.description or f"{payload.role} ({payload.archetype})"
        avatar = generate_npc_avatar(display_name, desc, "npc", payload.genre)
    return {
        "avatar_b64": avatar,
        "available": bool(avatar),
        "provider": provider,
        "error": None if avatar else (claude_service.LAST_IMAGE_ERROR or "Nessuna immagine restituita dal provider"),
    }

class NpcAvatarGenPayload(BaseModel):
    entities: list[dict]   # [{id, name, description, type}]
    genre: str

@app.post("/game/generate-npc-avatars")
def gen_npc_avatars(payload: NpcAvatarGenPayload):
    """Genera ritratti per tutti gli NPC/nemici passati, in parallelo."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    provider = _resolve_image_provider()
    if not provider:
        return {"avatars": {}}
    set_active_provider(provider)

    results = {}
    def _gen(e):
        img = generate_npc_avatar(e["name"], e.get("description", ""), e.get("type", "npc"), payload.genre)
        return e["id"], img

    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(_gen, e): e["id"] for e in payload.entities}
        for fut in as_completed(futures):
            eid, img = fut.result()
            if img:
                results[eid] = img

    return {"avatars": results}


@app.post("/game/abort-mission")
def abort_mission():
    """Termina manualmente la missione corrente come fallita.
    Usato per uscire da partite incartate dove la condizione di vittoria non si attiva."""
    global game_state
    if game_state and game_state.mission and not game_state.mission.completed and not game_state.mission.failed:
        game_state.mission.failed = True
        ending_text = (
            f"Missione interrotta manualmente. {game_state.mission.title} si chiude senza esito ufficiale: "
            f"la squadra abbandona l'operazione. Obiettivo originario: {game_state.mission.objective}"
        )
        game_state.mission.ending_text = ending_text
        if game_state.scene:
            game_state.scene.scene_text = ending_text
        game_state.selected_actions = {}
    return game_state


@app.post("/game/preview-action")
def preview_action(payload: PreviewActionPayload):
    return preview_action_outcomes(
        game_state,
        payload.player_id,
        intent=payload.intent,
        structured_intent=payload.structured_intent,
        custom_intents=payload.custom_intents,
    )

@app.post("/game/combat/attack")
def combat_attack(payload: CombatAttackPayload):
    global game_state
    attacker = next((p for p in game_state.players if p.id == payload.attacker_id), None)
    if not attacker:
        return {"error": f"Player {payload.attacker_id} non trovato"}
    action = next((a for a in attacker.actions if a.name == payload.action_name), None)
    if not action:
        # Fallback: costruisce azione di combattimento sintetica con le skill del personaggio
        from .models import Action as ActionModel
        combat_skill = attacker.skills.get("combattere", attacker.stats.get("agilita", 10))
        action = ActionModel(
            name="combattere",
            stat="DE",
            skill="combattere",
            difficulty=0,
            effect_type="combattere",
            action_role="core",
            attack_kind="melee",
            damage=f"1d6+{max(0, (attacker.stats.get('forza', 10) - 10) // 2)}",
            damage_type="cr",
        )
    game_state = initiate_combat_action(
        game_state,
        attacker_id=payload.attacker_id,
        action=action,
        target_entity_id=payload.target_entity_id,
        target_player_id=payload.target_player_id,
        action_type=payload.action_type,
        distance=payload.distance,
    )
    resp = game_state.model_dump()
    resp["combat_log"] = game_state.last_attack_result
    # Includi loot_pool aggiornato (potrebbe avere nuovi oggetti se NPC abbattuto)
    resp["loot_pool"] = [e.model_dump() for e in game_state.loot_pool if e.collected_by == 0]
    return resp


@app.post("/game/combat/aim")
def combat_aim(payload: CombatAimPayload):
    """Azione Aim: il giocatore mira per un turno senza sparare.
    Accumula bonus Acc (max +Acc dell'arma). Al turno successivo può sparare con il bonus.
    """
    global game_state
    attacker = next((p for p in game_state.players if p.id == payload.attacker_id), None)
    if not attacker:
        return {"error": f"Player {payload.attacker_id} non trovato"}
    action = next((a for a in attacker.actions if a.name == payload.action_name), None)
    if not action:
        return {"error": f"Azione '{payload.action_name}' non trovata per il giocatore"}
    if getattr(action, "attack_kind", None) != "ranged":
        return {"error": "L'azione Aim è disponibile solo per armi a distanza"}
    game_state = initiate_combat_action(
        game_state,
        attacker_id=payload.attacker_id,
        action=action,
        action_type="aim",
    )
    resp = game_state.model_dump()
    resp["combat_log"] = game_state.last_attack_result
    return resp


@app.get("/game/combat/weapons")
def get_combat_weapons(genre: str | None = None):
    """Ritorna le armi disponibili per il genere corrente (o tutte se non specificato)."""
    from .data_weapons import get_weapons_for_genre, WEAPON_TABLE
    g = genre or (game_state.genre if game_state else None) or "fantasy"
    weapons = get_weapons_for_genre(g)
    return {
        "genre": g,
        "weapons": weapons,
        "melee": [w for w in weapons if w["attack_kind"] == "melee"],
        "ranged": [w for w in weapons if w["attack_kind"] == "ranged"],
    }


class CombatReloadPayload(BaseModel):
    player_id: int
    action_name: str   # nome dell'Action da ricaricare


@app.post("/game/combat/reload")
def combat_reload(payload: CombatReloadPayload):
    """Ricarica un'arma consumando 1 unità di munizioni dall'inventario del PG."""
    global game_state
    from .engine import reload_weapon
    result = reload_weapon(game_state, payload.player_id, payload.action_name)
    if result.get("error"):
        return {"error": result["error"]}
    return {
        "log": result.get("log", ""),
        "players": [p.model_dump() for p in game_state.players],
    }


class EquipmentUpdatePayload(BaseModel):
    equipment: list   # lista di EquipmentItem come dict


@app.put("/game/player/{player_id}/equipment")
def update_player_equipment(player_id: int, payload: EquipmentUpdatePayload):
    """Aggiorna l'inventario strutturato di un PG."""
    global game_state
    from .models import EquipmentItem
    player = next((p for p in game_state.players if p.id == player_id), None)
    if not player:
        return {"error": f"Personaggio {player_id} non trovato."}
    player.equipment = [EquipmentItem(**it) if isinstance(it, dict) else it
                        for it in payload.equipment]
    return {"players": [p.model_dump() for p in game_state.players]}


@app.get("/game/player/{player_id}/equipment")
def get_player_equipment(player_id: int):
    """Ritorna l'inventario strutturato di un PG."""
    player = next((p for p in game_state.players if p.id == player_id), None)
    if not player:
        return {"error": f"Personaggio {player_id} non trovato."}
    return {
        "player_id": player_id,
        "equipment": [it.model_dump() for it in player.equipment],
        "actions": [a.model_dump() for a in player.actions],
    }


class AddWeaponPayload(BaseModel):
    weapon_id: str
    ammo_packs: int = 0


@app.post("/game/player/{player_id}/add-weapon")
def player_add_weapon(player_id: int, payload: AddWeaponPayload):
    """Aggiunge un'arma (+ eventuali munizioni) all'inventario di un PG."""
    global game_state
    result = add_weapon_to_player(game_state, player_id, payload.weapon_id, payload.ammo_packs)
    if result.get("error"):
        return {"error": result["error"]}
    return {
        "log": result.get("log", ""),
        "players": [p.model_dump() for p in game_state.players],
    }


@app.delete("/game/player/{player_id}/remove-weapon/{weapon_id}")
def player_remove_weapon(player_id: int, weapon_id: str):
    """Rimuove un'arma (e le sue munizioni) dall'inventario di un PG."""
    global game_state
    result = remove_weapon_from_player(game_state, player_id, weapon_id)
    if result.get("error"):
        return {"error": result["error"]}
    return {
        "log": result.get("log", ""),
        "players": [p.model_dump() for p in game_state.players],
    }


@app.delete("/game/player/{player_id}/equipment/{item_id}")
def player_remove_equipment_item(player_id: int, item_id: str):
    """Rimuove un singolo oggetto dall'inventario di un PG."""
    global game_state
    result = remove_equipment_item(game_state, player_id, item_id)
    if result.get("error"):
        return {"error": result["error"]}
    return {
        "log": result.get("log", ""),
        "players": [p.model_dump() for p in game_state.players],
    }


@app.get("/game/loot")
def get_loot_pool():
    """Ritorna gli oggetti disponibili per la raccolta nella scena corrente."""
    available = [e for e in game_state.loot_pool if e.collected_by == 0 and e.visible]
    return {
        "loot_pool": [e.model_dump() for e in available],
        "total": len(available),
    }


class CollectLootPayload(BaseModel):
    player_id: int
    item_id: str


@app.post("/game/loot/collect")
def loot_collect(payload: CollectLootPayload):
    """Un PG raccoglie un oggetto dal loot_pool."""
    global game_state
    result = collect_loot(game_state, payload.player_id, payload.item_id)
    if result.get("error"):
        return {"error": result["error"]}
    return {
        "log": result.get("log", ""),
        "players": [p.model_dump() for p in game_state.players],
        "loot_pool": [e.model_dump() for e in game_state.loot_pool if e.collected_by == 0],
    }


class GiveItemPayload(BaseModel):
    player_id: int
    item_name: str
    category: str = "misc"
    weapon_id: str = ""
    quantity: int = 1
    notes: str = ""


@app.post("/game/master/give-item")
def master_give_item(payload: GiveItemPayload):
    """Il Master assegna direttamente un oggetto a un PG (bypassa il loot_pool)."""
    global game_state
    result = give_item_to_player(
        game_state, payload.player_id, payload.item_name,
        payload.category, payload.weapon_id, payload.quantity, payload.notes,
    )
    if result.get("error"):
        return {"error": result["error"]}
    return {
        "log": result.get("log", ""),
        "players": [p.model_dump() for p in game_state.players],
    }


@app.post("/game/master/add-loot")
def master_add_loot(payload: GiveItemPayload):
    """Il Master aggiunge un oggetto al loot_pool della scena (visibile a tutti)."""
    global game_state
    from .models import EquipmentItem as EI
    from .engine import _add_item_to_loot_pool
    import uuid
    from .data_weapons import item_to_weapon_id, get_weapon
    wid = payload.weapon_id or item_to_weapon_id(payload.item_name) or ""
    wd = get_weapon(wid) if wid else None
    item = EI(
        id=f"loot_{uuid.uuid4().hex[:6]}",
        name=wd["name"] if wd else payload.item_name,
        category="weapon" if wd else payload.category,
        weapon_id=wid, quantity=payload.quantity,
        notes=payload.notes or (wd.get("notes","") if wd else ""),
    )
    _add_item_to_loot_pool(game_state, item, source_type="scene", source_name="master")
    return {
        "log": f"Oggetto '{item.name}' aggiunto al bottino della scena.",
        "loot_pool": [e.model_dump() for e in game_state.loot_pool if e.collected_by == 0],
    }


@app.post("/game/combat/defend")
def combat_defend(payload: CombatDefendPayload):
    global game_state
    from .models import CombatDefenseRequest as CDR
    dr = CDR(
        player_id=payload.player_id,
        defense_type=payload.defense_type,
        defense_skill=payload.defense_skill,
    )
    game_state = declare_defense(
        game_state, dr,
        defense_action_type=payload.defense_action_type,
        cover_bonus=payload.cover_bonus,
        rear_attack=payload.rear_attack,
    )
    resp = game_state.model_dump()
    resp["combat_log"] = game_state.last_attack_result
    return resp


@app.post("/game/combat/standup")
def combat_standup(payload: CombatStandUpPayload):
    """Il giocatore usa la sua azione per alzarsi da terra (prone)."""
    global game_state
    player = next((p for p in game_state.players if p.id == payload.player_id), None)
    if not player:
        return {"error": f"Player {payload.player_id} non trovato"}
    if not player.prone:
        return {"message": f"{player.name} non è a terra.", "players": [p.model_dump() for p in game_state.players]}
    stand_up(player)
    player.posture = "standing"
    return {"message": f"{player.name} si alza.", "players": [p.model_dump() for p in game_state.players]}


class CombatManeuverPayload(BaseModel):
    player_id: int
    maneuver: str           # "all_out_defense" | "evaluate" | "change_posture" | "do_nothing" | "concentrate" | "ready"
    posture: str = ""       # per change_posture: "standing" | "kneeling" | "prone"
    evaluate_target: str = ""  # ID bersaglio per manovra Valuta

@app.post("/game/combat/maneuver")
def combat_maneuver(payload: CombatManeuverPayload):
    """Esegue una manovra GURPS non-attacco (Difesa Totale, Valuta, Postura, Niente, ecc.)."""
    global game_state
    player = next((p for p in game_state.players if p.id == payload.player_id), None)
    if not player:
        return {"error": f"Player {payload.player_id} non trovato"}

    maneuver = payload.maneuver
    log_msg = ""

    if maneuver == "all_out_defense":
        # Marca difesa totale — +2 a tutte le difese fino al prossimo turno
        player.all_out_defense_active = True
        player.action_type = "all_out_defense"
        player.last_maneuver = "all_out_defense"
        log_msg = f"🛡 {player.name} — Difesa Totale (+2 a tutte le difese, nessun attacco questo turno)."

    elif maneuver == "evaluate":
        # Accumula bonus Valuta vs stesso bersaglio (max +3)
        tgt = payload.evaluate_target or ""
        if player.evaluate_target and player.evaluate_target != tgt:
            # Cambiato bersaglio → azzera bonus
            player.evaluate_bonus = 0
        player.evaluate_target = tgt
        player.evaluate_bonus = min(3, (player.evaluate_bonus or 0) + 1)
        player.last_maneuver = "evaluate"
        log_msg = f"🔍 {player.name} valuta il bersaglio. Bonus att. accumulato: +{player.evaluate_bonus}/3."

    elif maneuver == "change_posture":
        new_posture = payload.posture or "standing"
        old_posture = player.posture
        player.posture = new_posture
        player.prone = (new_posture == "prone")
        player.last_maneuver = "change_posture"
        posture_labels = {"standing": "in piedi", "kneeling": "in ginocchio", "prone": "a terra"}
        log_msg = (f"🧎 {player.name} cambia postura: "
                   f"{posture_labels.get(old_posture, old_posture)} → {posture_labels.get(new_posture, new_posture)}.")

    elif maneuver == "concentrate":
        player.last_maneuver = "concentrate"
        log_msg = f"🧠 {player.name} si concentra. Azione mentale o magica in corso."

    elif maneuver == "ready":
        player.last_maneuver = "ready"
        log_msg = f"🔄 {player.name} prepara / ricarica l'arma."

    elif maneuver == "do_nothing":
        player.last_maneuver = "do_nothing"
        log_msg = f"✋ {player.name} non fa nulla questo turno."

    else:
        return {"error": f"Manovra sconosciuta: {maneuver}"}

    return {
        "ok": True,
        "maneuver": maneuver,
        "log": log_msg,
        "players": [p.model_dump() for p in game_state.players],
    }


class WillCheckPayload(BaseModel):
    player_id: int
    modifier: int = 0          # penalità/bonus al tiro (es. −3 per paura intensa)
    reason: str = "paura"      # etichetta narrativa

@app.post("/game/combat/will-check")
def combat_will_check(payload: WillCheckPayload):
    """Tiro di Volontà (IN) per effetti narrativi di paura o stress. 3d6 ≤ Volontà+mod."""
    import random
    player = next((p for p in game_state.players if p.id == payload.player_id), None)
    if not player:
        return {"error": f"Player {payload.player_id} non trovato"}
    will = player.stats.get("IN", 10)  # Volontà = IN in GURPS Lite
    effective = max(3, will + payload.modifier)
    roll = sum(random.randint(1, 6) for _ in range(3))
    passed = roll <= effective
    margin = effective - roll
    return {
        "player_id": payload.player_id,
        "player_name": player.name,
        "will": will,
        "modifier": payload.modifier,
        "effective": effective,
        "roll": roll,
        "passed": passed,
        "margin": margin,
        "reason": payload.reason,
        "log": (
            f"{player.name} — Tiro di Volontà ({payload.reason}): "
            f"3d6={roll} vs {effective} → {'SUPERATO' if passed else 'FALLITO'} (margine {margin:+d})"
        ),
    }


class PlayerRenamePayload(BaseModel):
    player_id: int
    name: str

@app.post("/game/player/rename")
def player_rename(payload: PlayerRenamePayload):
    """Rinomina un personaggio nel pool o tra i giocatori attivi."""
    global game_state
    new_name = payload.name.strip()
    if not new_name:
        return {"error": "Il nome non può essere vuoto"}
    # Cerca prima tra i giocatori attivi
    player = next((p for p in game_state.players if p.id == payload.player_id), None)
    if player:
        player.name = new_name
        return {"ok": True, "players": [p.model_dump() for p in game_state.players]}
    # Poi nel candidate_pool
    pooled = next((p for p in game_state.team_setup.candidate_pool if p.id == payload.player_id), None)
    if pooled:
        pooled.name = new_name
        return {"ok": True, "pool": [p.model_dump() for p in game_state.team_setup.candidate_pool]}
    return {"error": f"Player {payload.player_id} non trovato"}


class CombatNarratePayload(BaseModel):
    combat_log: dict
    genre: str = "fantasy"
    adventure: dict = {}

@app.post("/game/combat/narrate")
def combat_narrate(payload: CombatNarratePayload):
    """Genera 1-2 frasi narrative in italiano sull'esito di uno scambio di combattimento."""
    text = narrate_combat_result(payload.combat_log, payload.genre, payload.adventure or None)
    return {"narrative": text}

class CombatNpcTurnPayload(BaseModel):
    positions: dict = {}
    terrain: dict = {}
    cols: int = 15
    rows: int = 10

@app.post("/game/combat/npc-turn")
def combat_npc_turn(payload: CombatNpcTurnPayload | None = None):
    """Fa agire tutti gli NPC nemici vivi — chiamato dal frontend dopo ogni azione del giocatore."""
    global game_state
    tactical_context = payload.model_dump() if payload else None
    result = npc_combat_turn(game_state, tactical_context=tactical_context)
    resp = game_state.model_dump()
    resp["npc_logs"] = result["npc_logs"]
    resp["positions"] = result.get("positions", {})
    return resp


@app.post("/game/combat/retreat")
def combat_retreat(payload: CombatNpcTurnPayload | None = None):
    """Chiude uno scontro non finale con un costo: la squadra ripiega e la storia torna alla chat."""
    global game_state
    _ensure_runtime_scene()
    if game_state.scene:
        game_state.scene.entities = []
        game_state.scene.threat_level = min(10, (game_state.scene.threat_level or 0) + 1)
    game_state.pending_attack = None
    game_state.last_attack_result = None
    resp = game_state.model_dump()
    resp["combat_over"] = True
    resp["retreat"] = True
    resp["message"] = "La squadra ripiega prima che lo scontro diventi una trappola. La minaccia avanza di 1."
    return resp


@app.post("/game/reaction")
def reaction_roll(payload: ReactionPayload):
    result = resolve_reaction_roll(game_state, payload.npc_id, payload.player_id, payload.social_skill)
    return result


@app.post("/game/character/validate")
def character_validate(draft: CharacterDraft):
    """Valida un CharacterDraft e restituisce derivate + breakdown costi senza modificare lo stato."""
    return validate_draft(draft)


@app.post("/game/character/create")
def character_create(draft: CharacterDraft):
    """
    Valida e crea un personaggio personalizzato, aggiungendolo al candidate_pool.
    Restituisce il GameState aggiornato con il nuovo Player nel pool.
    """
    global game_state
    validation = validate_draft(draft)
    if not validation.valid:
        return {"error": "Bozza non valida", "validation": validation}
    player = build_custom_player(draft)
    game_state.team_setup.candidate_pool.append(player)
    return {"player": player, "validation": validation}


@app.post("/game/new")
def new_game():
    global game_state, tactical_map_image_cache
    game_state = empty_game_state()
    tactical_map_image_cache = {}
    return game_state

@app.post("/game/generate-scene-image")
def generate_image(payload: ImageGenPayload):
    provider = _resolve_image_provider()
    if not provider:
        return {"image_base64": None, "available": False}
    reset_last_request_tokens()
    set_active_provider(provider)
    image_b64 = generate_scene_image(
        payload.scene_text, payload.genre, payload.environment_type,
        player_photos_b64=payload.player_photos_b64 or None,
        player_names=payload.player_names or None,
    )
    return {"image_base64": image_b64, "available": bool(image_b64), "call_tokens": get_last_request_tokens()}

class LocationImagePayload(BaseModel):
    location_id: str
    location_name: str
    location_description: str = ""
    genre: str = "fantasy"
    theme: str = ""

@app.post("/game/adventure/location-image")
def generate_location_image(payload: LocationImagePayload):
    """Genera un'immagine per una singola locazione dell'avventura."""
    provider = _resolve_image_provider()
    if not provider:
        return {"location_id": payload.location_id, "image_b64": None}
    reset_last_request_tokens()
    set_active_provider(provider)
    image_b64 = generate_location_map_image(payload.location_name, payload.location_description or "")
    return {"location_id": payload.location_id, "image_b64": image_b64, "call_tokens": get_last_request_tokens()}

class TacticalMapPayload(BaseModel):
    location_name: str = ""
    location_description: str = ""
    genre: str = "fantasy"
    environment_type: str = "indoor"
    scene_narrative: str = ""       # testo narrativo del turno in cui scatta il combattimento
    mission_environment: str = ""   # environment_type della missione (dal GameState)
    enemy_names: list[str] = []     # nomi dei nemici (per inferire il tipo di luogo)
    layout: str = "room"            # "room" | "narrow" | "open" — determina aspect ratio immagine

@app.post("/game/generate-tactical-map-image")
def generate_tactical_map(payload: TacticalMapPayload):
    global tactical_map_image_cache
    provider = _resolve_image_provider()
    if not provider:
        return {"image_b64": None, "available": False}
    cache_key = "|".join([
        payload.location_name.strip().lower(),
        payload.environment_type.strip().lower(),
        payload.genre.strip().lower(),
        ",".join(sorted(payload.enemy_names or [])),
    ])
    if cache_key in tactical_map_image_cache:
        return {"image_b64": tactical_map_image_cache[cache_key], "available": True, "cached": True}
    reset_last_request_tokens()
    set_active_provider(provider)
    # arricchisce location_description con dati dal GameState se non forniti dal frontend
    mission_env = payload.mission_environment or (
        game_state.mission.environment_type if game_state.mission else ""
    )
    scene_narrative = payload.scene_narrative or (
        game_state.scene.scene_text[:300] if game_state.scene else ""
    )
    image_b64 = generate_tactical_map_image(
        payload.location_name,
        payload.location_description,
        payload.genre,
        payload.environment_type or mission_env,
        scene_narrative=scene_narrative,
        mission_environment=mission_env,
        enemy_names=payload.enemy_names,
        layout=payload.layout or "room",
    )
    if image_b64:
        tactical_map_image_cache[cache_key] = image_b64
    return {"image_b64": image_b64, "available": bool(image_b64), "call_tokens": get_last_request_tokens()}

@app.get("/game/image-available")
def image_available():
    provider = game_state.team_setup.provider
    return {"available": _image_provider_available(provider), "provider": provider}

@app.get("/game/debug-image")
def debug_image():
    google_key = os.getenv("GOOGLE_AI_STUDIO_KEY", "")
    return {
        "provider": game_state.team_setup.provider,
        "google_key_len": len(google_key), "google_key_prefix": google_key[:8] if google_key else "",
        "genai_available": _GOOGLE_GENAI_AVAILABLE, "genai_import_error": _GOOGLE_GENAI_IMPORT_ERROR,
        "openai_key_len": len(OPENAI_API_KEY), "openai_key_prefix": OPENAI_API_KEY[:8] if OPENAI_API_KEY else "",
        "openai_available": _OPENAI_AVAILABLE, "openai_import_error": _OPENAI_IMPORT_ERROR,
        "last_image_error": claude_service.LAST_IMAGE_ERROR,
    }

@app.get("/game/token-stats")
def token_stats_endpoint():
    return get_session_token_stats()


@app.post("/game/token-stats/reset")
def token_stats_reset_endpoint():
    reset_session_token_stats()
    return {"ok": True}


@app.get("/game/providers-available")
def providers_available():
    return {
        "claude": bool(os.getenv("ANTHROPIC_API_KEY")),
        "openai": bool(OPENAI_API_KEY) and _OPENAI_AVAILABLE,
        "gemini": bool(os.getenv("GOOGLE_AI_STUDIO_KEY")) and _GOOGLE_GENAI_AVAILABLE,
    }

def _extract_title_from_pdf_pages(text_pages: list[str]) -> str | None:
    """Try to extract the adventure title from the first 1-2 pages of PDF text.

    Looks for the first short, letter-rich line that isn't a stat block or number.
    Returns None if nothing usable is found.
    """
    import re as _re
    # Match stat block fields with explicit separator (HP: 12, AC=5) OR multiple GURPS stats on one line
    _stat_explicit_re = _re.compile(r'\b(AC|HD|HP|MV|ST|DX|IQ|HT|FP|Move|Speed)\s*[:=]\s*\d', _re.IGNORECASE)
    _stat_abbr_re = _re.compile(r'\b(ST|DX|IQ|HT|HP|FP|Will|Per|Move|Speed|Dodge|Parry|Block)\b', _re.IGNORECASE)
    _num_only_re = _re.compile(r'^[\d\s\.\-\–\—\*\/\|\[\](),:;]+$')
    _sep_re = _re.compile(r'^[=\-_\.~\*]{3,}$')

    def _looks_like_stat_line(s: str) -> bool:
        if _stat_explicit_re.search(s):
            return True
        # GURPS format: multiple stat abbreviations on one line (ST 12 DX 11 IQ 10...)
        if len(_stat_abbr_re.findall(s)) >= 3:
            return True
        return False

    for page in (text_pages or [])[:2]:
        for line in (page or "").splitlines():
            stripped = line.strip()
            if not stripped or len(stripped) < 4 or len(stripped) > 90:
                continue
            if _num_only_re.match(stripped) or _sep_re.match(stripped):
                continue
            letters = sum(c.isalpha() for c in stripped)
            if letters < 4:
                continue
            if _looks_like_stat_line(stripped):
                continue
            # Skip all-caps single-word page labels ("INDICE", "COPYRIGHT", etc.)
            words = stripped.split()
            if len(words) == 1 and stripped.isupper():
                continue
            return stripped
    return None


def _clean_pdf_text(text: str) -> str:
    """Rimuove righe a bassa densità narrativa da testo PDF estratto.

    Elimina: righe di soli numeri/simboli, intestazioni di pagina brevi,
    separatori, righe con ratio numero/lettera troppo alto (stat block puri).
    Mantiene tutto il testo narrativo, descrittivo e dialogico.
    """
    import re
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned.append("")
            continue
        # Salta righe troppo corte che sono probabilmente header di pagina o numeri di pagina
        if len(stripped) <= 3:
            continue
        # Salta righe che sono solo numeri, punteggiatura e spazi (es. "12", "— 7 —", "* * *")
        if re.fullmatch(r'[\d\s\.\-\–\—\*\/\|\[\](),:;]+', stripped):
            continue
        # Salta righe con troppi numeri rispetto alle lettere (stat block densi)
        letters = sum(c.isalpha() for c in stripped)
        digits = sum(c.isdigit() for c in stripped)
        if letters < 4 and digits >= 2:
            continue
        # Salta linee che sembrano separatori (es. "====", "----", ".......")
        if re.fullmatch(r'[=\-_\.~\*]{3,}', stripped):
            continue
        cleaned.append(line)

    # Collassa blocchi di righe vuote consecutive in una sola
    result_lines = []
    prev_blank = False
    for line in cleaned:
        is_blank = not line.strip()
        if is_blank and prev_blank:
            continue
        result_lines.append(line)
        prev_blank = is_blank

    return "\n".join(result_lines)


@app.post("/game/adventure/from-pdf")
async def adventure_from_pdf(
    file: UploadFile = File(...),
    genre: str = Form(...),
    players: str = Form(...),
    provider: str = Form(default="claude"),
    map_page: str = Form(default=""),
):
    """Estrae testo dal PDF e genera la bibbia. map_page opzionale: numero pagina (1-based) da usare come mappa."""
    import base64
    try:
        import pdfplumber
        from PIL import Image
    except ImportError:
        return {"error": "pdfplumber/Pillow non installato sul server"}

    pdf_bytes = await file.read()
    raw_text_pages = []
    map_image_b64 = None

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        total_pages = len(pdf.pages)

        # Estrai immagine mappa se richiesta
        map_page_idx = None
        if map_page.strip():
            try:
                map_page_idx = int(map_page.strip()) - 1  # converti a 0-based
                if not (0 <= map_page_idx < total_pages):
                    map_page_idx = None
            except ValueError:
                pass

        if map_page_idx is not None:
            try:
                page = pdf.pages[map_page_idx]
                # Renderizza la pagina come immagine (150 DPI — bilanciato qualità/peso)
                page_img = page.to_image(resolution=150)
                buf = io.BytesIO()
                page_img.save(buf, format="JPEG", quality=82)
                map_image_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                print(f"[adventure/from-pdf] mappa estratta da pagina {map_page_idx+1} ({len(map_image_b64)//1024} KB)")
            except Exception as e:
                print(f"[adventure/from-pdf] errore estrazione mappa pag {map_page_idx+1}: {e}")

        for page in pdf.pages:
            t = page.extract_text()
            if t:
                raw_text_pages.append(t)

    pdf_text = "\n\n".join(raw_text_pages).strip()
    if not pdf_text:
        return {"error": "Impossibile estrarre testo dal PDF"}
    raw_chars = len(pdf_text)
    text_pages = [_clean_pdf_text(page) for page in raw_text_pages]
    text_pages = [page for page in text_pages if page.strip()]
    pdf_text = "\n\n".join(text_pages).strip()
    print(f"[adventure/from-pdf] estratte {len(text_pages)}/{total_pages} pagine, {raw_chars} caratteri → {len(pdf_text)} dopo pulizia ({100*len(pdf_text)//max(raw_chars,1)}%)")

    set_active_provider(provider)
    try:
        genre_hint = None if str(genre or "").lower() == "auto" else genre

        # Try to extract a real title from PDF content; fall back to cleaned filename
        extracted_title = _extract_title_from_pdf_pages(text_pages)
        if extracted_title:
            pdf_title = extracted_title
            print(f"[adventure/from-pdf] titolo estratto dal testo: '{pdf_title}'")
        else:
            raw_name = file.filename or "Avventura da PDF"
            # Strip .pdf extension and clean separators for a readable fallback
            import os as _os
            stem = _os.path.splitext(raw_name)[0]
            pdf_title = stem.replace("-", " ").replace("_", " ").strip() or "Avventura da PDF"
            print(f"[adventure/from-pdf] titolo non estratto, fallback da filename: '{pdf_title}'")

        compiled = compile_pdf_pages_to_runtime(
            text_pages,
            genre_hint=genre_hint,
            runtime_profile_hint=None,
            title=pdf_title,
        )

        # ── Quality gate: blocca se la compilazione è chiaramente fallita ──
        quality_gate = check_raw_compilation_quality(compiled.get("adventure_definition") or {})
        print(f"[adventure/from-pdf] quality gate: passed={quality_gate['passed']} score={quality_gate['score']} critical={quality_gate['critical']}")
        if not quality_gate["passed"]:
            issues = "; ".join(quality_gate["critical"])
            return {
                "error": f"Compilazione fallita: il PDF non ha prodotto un'avventura giocabile. Problemi rilevati: {issues}",
                "quality_gate": quality_gate,
                "compilation_failed": True,
            }

        if compiled.get("validation_report") is None:
            compiled["validation_report"] = {}
        compiled["validation_report"]["quality_gate"] = quality_gate

        definition = AdventureDefinition(**compiled["adventure_definition"])
        runtime_state = AdventureRuntimeState(**compiled["runtime_state"])
        saved = save_runtime(definition, runtime_state, compiled["validation_report"])

        # ── Doctor: audit + fix automatico ──────────────────────────────────
        defn_dict = saved["adventure_definition"]
        doctor_result = {"score": 10.0, "findings": [], "score_after": 10.0}
        try:
            doctor_result = run_doctor(defn_dict, do_enrich=True)
            enriched = doctor_result.get("enriched_definition")
            if enriched:
                enr_def = AdventureDefinition(**{
                    k: v for k, v in enriched.items()
                    if k in AdventureDefinition.model_fields
                })
                enr_def.id = definition.id
                saved = save_runtime(enr_def, runtime_state, compiled["validation_report"])
                defn_dict = saved["adventure_definition"]
                print(f"[doctor/from-pdf] score {doctor_result['score']} → {doctor_result.get('score_after','?')}/10"
                      f" ({len(doctor_result['findings'])} findings corretti)")
        except Exception as de:
            print(f"[doctor/from-pdf] errore (non bloccante): {de}")

        result = dict(definition.legacy_adventure or {})
        result.update({
            "from_pdf": True,
            "from_runtime_compiler": True,
            "runtime_id": definition.id,
            "adventure_definition": defn_dict,
            "runtime_state": saved["runtime_state"],
            "validation_report": saved["validation_report"],
            "pdf_pages_read": len(text_pages),
            "pdf_total_pages": total_pages,
            "doctor": {
                "score":       doctor_result.get("score", 10.0),
                "score_after": doctor_result.get("score_after"),
                "auto_fixed":  bool(doctor_result.get("enriched_definition")),
                "findings":    doctor_result.get("findings", []),
            },
        })
    except Exception as e:
        print(f"[adventure/from-pdf] errore compiler runtime: {type(e).__name__}: {e}")
        return {"error": f"Errore durante la compilazione runtime del PDF: {type(e).__name__}: {str(e)[:260]}"}
    if map_image_b64:
        result["map_image_b64"] = map_image_b64
    try:
        result.update(_save_pdf_compilation_json(
            source_filename=file.filename or "Avventura da PDF",
            requested_genre=genre,
            provider=provider,
            map_page=map_page,
            total_pages=total_pages,
            text_pages=text_pages,
            raw_chars=raw_chars,
            cleaned_pdf_text=pdf_text,
            compiled_result=result,
        ))
    except Exception as e:
        result["saved_json_error"] = f"{type(e).__name__}: {str(e)[:220]}"
        print(f"[adventure/from-pdf] impossibile salvare JSON debug: {result['saved_json_error']}")
    return result


# ─── DEBUG: avvia combattimento di test ───────────────────────────────────────

@app.post("/game/debug/start-combat")
def debug_start_combat():
    """Inietta un combattimento di test (con player di default se non esiste sessione)."""
    global game_state
    from .models import Player

    # Se non ci sono player, crea un guerriero di test
    if not game_state.players:
        from .models import Action as ActionModel
        test_player = Player(
            id=1, name="Guerriero", role="combattente", archetype="warrior",
            hp=14, max_hp=14, fp=10, max_fp=10,
            will=10, per=10, basic_speed=5.75, dodge=8, move=5, dr=0,
            stats={"forza": 13, "agilita": 12, "intelligenza": 10, "empatia": 9},
            skills={"spada": 13, "pistola": 11, "combattere": 12},
            actions=[
                ActionModel(name="spada", stat="DE", skill="spada", attack_kind="melee",
                            damage="1d6+2", damage_type="cut", weapon_id="spada_1"),
                ActionModel(name="pistola", stat="DE", skill="pistola", attack_kind="ranged",
                            damage="2d6", damage_type="pi", weapon_id="pistola_1",
                            ammo=12, ammo_current=12, acc=2, range_half=150, range_max=300),
            ],
            equipment=[], posture="standing", prone=False, stunned=False, status="attivo",
        )
        game_state.players.append(test_player)

    test_entities = [
        SceneEntity(
            id="guardia_1", name="Guardia di Sicurezza", type="enemy",
            hp=14, max_hp=14,
            description="Guardia robusta in uniforme scura, armata di manganello",
            stats={"forza": 13, "agilita": 11, "intelligenza": 9, "empatia": 8},
            actions=[{"name": "manganello", "attack_kind": "melee", "damage": "1d6+2",
                      "skill": 12, "weapon_id": "manganello_1", "ammo": None}],
            defense_value=9, speed=5,
        ),
        SceneEntity(
            id="guardia_2", name="Agente Moretti", type="enemy",
            hp=11, max_hp=11,
            description="Agente snello con coltello da combattimento",
            stats={"forza": 11, "agilita": 13, "intelligenza": 10, "empatia": 9},
            actions=[{"name": "coltello", "attack_kind": "melee", "damage": "1d6-1",
                      "skill": 13, "weapon_id": "coltello_1", "ammo": None}],
            defense_value=10, speed=6,
        ),
    ]

    game_state.scene = SceneState(
        scene_id="debug_combat", scene_type="combat",
        location="Corridoio di Sicurezza",
        scene_text="Le guardie vi sbarrano il passaggio — il combattimento è inevitabile!",
        description="Le guardie vi sbarrano il passaggio — il combattimento è inevitabile!",
        entities=test_entities, exits=[], items=[], npcs=[],
    )

    _persist_combat_scene(
        {"entities": [e.model_dump() for e in test_entities]},
        preserve_live_hp=False,
    )

    return {
        "ok": True,
        "message": "Combattimento di test avviato",
        "combat_scene": {
            "scene_id": "debug_combat",
            "location": "Corridoio di Sicurezza",
            "entities": [e.model_dump() for e in test_entities],
        },
        "activate_combat": True,
        "players": [p.model_dump() for p in game_state.players],
    }
