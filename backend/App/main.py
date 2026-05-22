from dotenv import load_dotenv
load_dotenv(override=True)
import os
import random
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import io
from .engine import empty_game_state, prepare_team_setup, start_game_from_selection, advance_to_node, preview_action_outcomes, initiate_combat_action, declare_defense, resolve_reaction_roll, roll_for_player_action, npc_combat_turn, build_players_from_dicts
from .combat import attempt_stun_recovery, stand_up
from .character_creation import validate_draft, build_custom_player
from .claude_service import (
    generate_scene_image, generate_character_avatar, generate_npc_avatar, generate_map_tile_image,
    generate_strategic_map_image, generate_tactical_map_image, narrate_combat_result,
    set_active_provider,
    master_turn_with_bible, master_start_with_bible, create_adventure,
    generate_character_from_description, enrich_character_with_backstory,
    evaluate_personal_victories,
    _GOOGLE_GENAI_AVAILABLE, _GOOGLE_GENAI_IMPORT_ERROR,
    _OPENAI_AVAILABLE, _OPENAI_IMPORT_ERROR, OPENAI_API_KEY,
)
from . import claude_service
from .claude_service import create_adventure_from_pdf_text
from .data_genres import GENRE_PACKS
from .models import GameState, CombatDefenseRequest, CharacterDraft, SceneEntity, SceneState

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
game_state: GameState = empty_game_state()
tile_image_cache: dict[str, str] = {}
strategic_map_image_cache: str | None = None


def _ensure_runtime_scene(scene_text: str = "") -> None:
    if game_state.scene is None:
        game_state.scene = SceneState(scene_text=scene_text or "Scena in corso.")
    elif scene_text:
        game_state.scene.scene_text = scene_text


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


def _enrich_combat_scene(combat_scene: dict | None) -> dict | None:
    """
    Arricchisce combat_scene con stat GURPS persistenti dai WorldNPC.
    Cerca match per nome: se il WorldNPC ha già stat le riusa, altrimenti le genera e salva.
    """
    if not combat_scene or not isinstance(combat_scene.get("entities"), list):
        return combat_scene

    enriched = []
    for entity in combat_scene["entities"]:
        name = entity.get("name", "")
        matched_npc = None
        for npc in game_state.world_npcs:
            if _npc_name_match(npc.name, name):
                matched_npc = npc
                break

        if matched_npc is not None:
            if matched_npc.combat_hp is not None:
                # Riusa stat già generate in precedenza
                entity = {
                    **entity,
                    "hp": matched_npc.combat_hp,
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
                entity = {**entity, **stats}
        # Se non c'è match in world_npcs lascia le stat di Claude (o i default del modello)
        enriched.append(entity)

    return {**combat_scene, "entities": enriched}


def _persist_combat_scene(combat_scene: dict | None) -> None:
    """Salva i nemici della combat_scene nello stato backend usato dagli endpoint tattici."""
    if not combat_scene or not isinstance(combat_scene.get("entities"), list):
        return
    _ensure_runtime_scene()

    entities: list[SceneEntity] = []
    for idx, raw in enumerate(combat_scene.get("entities") or [], start=1):
        if not isinstance(raw, dict):
            continue
        entity = dict(raw)
        entity.setdefault("id", f"enemy_{idx}")
        entity.setdefault("name", f"Nemico {idx}")
        entity.setdefault("type", "enemy")
        entity.setdefault("zone", "centro")
        entity.setdefault("hp", entity.get("max_hp", 10))
        entity.setdefault("max_hp", entity.get("hp", 10))
        entity.setdefault("dr", 0)
        entity.setdefault("attack_skill", 10)
        entity.setdefault("active_defense", 8)
        entity.setdefault("damage_dice", "1d6")
        entity.setdefault("damage_type", "cr")
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

class TileImagePayload(BaseModel):
    node_id: str

class MovePayload(BaseModel):
    node_id: str

class CombatAttackPayload(BaseModel):
    attacker_id: int
    action_name: str                    # nome dell'Action nel player.actions
    target_entity_id: str | None = None
    target_player_id: int | None = None
    action_type: str = "normal"         # "normal" | "all_out_attack"

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
    """Genera la bibbia strutturata dell'avventura."""
    return create_adventure(payload.genre, payload.players)

@app.post("/game/master/start-bible")
def master_start_bible_endpoint(payload: MasterStartBiblePayload):
    """Scena d'apertura con bibbia avventura."""
    _sync_players_from_payload(payload.players)
    result = master_start_with_bible(payload.genre, payload.players, payload.adventure)
    _ensure_runtime_scene(result.get("narrative", ""))
    return result

@app.post("/game/master/turn-bible")
def master_turn_bible_endpoint(payload: MasterTurnBiblePayload):
    """Turno Master con bibbia e tracking stato."""
    _sync_players_from_payload(payload.players)
    _ensure_runtime_scene()
    # Tiro GURPS reale prima di chiamare Claude — vincolante per la narrativa
    active_player = next((p for p in payload.players if p["id"] == payload.active_player_id), payload.players[0] if payload.players else None)
    roll_detail = None
    if active_player:
        threat_level = payload.game_state_data.get("threat_level", 1)
        scene_tags = list(game_state.scene.scene_tags) if game_state.scene else []
        roll_detail = roll_for_player_action(active_player, payload.player_action, threat_level, scene_tags)
        game_state.last_roll_details = [roll_detail]

    result = master_turn_with_bible(
        payload.genre, payload.players, payload.history,
        payload.player_action, payload.active_player_id,
        payload.adventure, payload.game_state_data,
        prerolled=roll_detail,
    )
    # Arricchisce combat_scene con stat GURPS persistenti dai WorldNPC
    su = result.get("state_updates") or {}
    print(f"[turn-bible] activate_combat={su.get('activate_combat')} combat_over={su.get('combat_over')} combat_scene={'presente' if su.get('combat_scene') else 'assente'}")
    if su.get("activate_combat") and su.get("combat_scene"):
        su["combat_scene"] = _enrich_combat_scene(su["combat_scene"])
        _persist_combat_scene(su["combat_scene"])
        result["state_updates"] = su
    if su.get("combat_over"):
        game_state.pending_attack = None

    # Valutazione vittorie personali quando la storia finisce
    if su.get("story_over"):
        final_narrative = result.get("narrative", "")
        group_victory = bool(su.get("victory", False))
        personal = evaluate_personal_victories(payload.players, payload.adventure, final_narrative, group_victory)
        game_state.personal_victories = personal
        su["personal_victories"] = personal
        result["state_updates"] = su

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
    game_state.last_roll_details = []   # consuma i dettagli dopo la prima lettura
    return snapshot

@app.get("/game/genres")
def get_genres():
    return {"genres": list(GENRE_PACKS.keys())}

@app.get("/game/debug-world")
def get_debug_world():
    return {"story": game_state.story, "map_state": game_state.map_state}

@app.post("/game/setup")
def setup_game(payload: SetupPayload):
    global game_state, strategic_map_image_cache
    set_active_provider(payload.provider)
    game_state = prepare_team_setup(payload.genre, provider=payload.provider)
    game_state.team_setup.image_provider = payload.image_provider
    strategic_map_image_cache = None
    return game_state

@app.post("/game/select-team")
def select_team(payload: TeamSelectionPayload):
    global game_state, strategic_map_image_cache
    game_state = start_game_from_selection(game_state, payload.selected_player_ids, payload.custom_names, payload.adventure_bible)
    strategic_map_image_cache = None
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
    )
    resp = game_state.model_dump()
    resp["combat_log"] = game_state.last_attack_result
    return resp


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
    return {"message": f"{player.name} si alza.", "players": [p.model_dump() for p in game_state.players]}


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


@app.post("/game/move")
def move_to_node(payload: MovePayload):
    global game_state
    game_state = advance_to_node(game_state, payload.node_id)
    return game_state

@app.post("/game/new")
def new_game():
    global game_state, tile_image_cache, strategic_map_image_cache
    game_state = empty_game_state()
    tile_image_cache = {}
    strategic_map_image_cache = None
    return game_state

@app.post("/game/generate-strategic-map-image")
def generate_strategic_map():
    global strategic_map_image_cache
    if strategic_map_image_cache:
        return {"image_b64": strategic_map_image_cache, "available": True}
    if not game_state.map_state or not game_state.mission:
        return {"image_b64": None, "available": False}
    provider = _resolve_image_provider()
    if not provider:
        return {"image_b64": None, "available": False}
    set_active_provider(provider)
    image_b64 = generate_strategic_map_image(
        game_state.map_state.model_dump(),
        game_state.mission.genre,
        game_state.mission.environment_type,
    )
    if image_b64:
        strategic_map_image_cache = image_b64
    return {"image_b64": image_b64, "available": bool(image_b64)}

@app.post("/game/generate-tile-image")
def generate_tile_image(payload: TileImagePayload):
    global tile_image_cache
    if cached := tile_image_cache.get(payload.node_id):
        return {"image_b64": cached, "available": True}
    if not game_state.map_state:
        return {"image_b64": None, "available": False}
    node = game_state.map_state.nodes.get(payload.node_id)
    if not node:
        return {"image_b64": None, "available": False}
    provider = _resolve_image_provider()
    if not provider:
        return {"image_b64": None, "available": False}
    set_active_provider(provider)
    image_b64 = generate_map_tile_image(node.name, node.kind, game_state.map_state.map_type)
    if image_b64:
        tile_image_cache[payload.node_id] = image_b64
    return {"image_b64": image_b64, "available": True}

@app.post("/game/generate-scene-image")
def generate_image(payload: ImageGenPayload):
    provider = _resolve_image_provider()
    if not provider:
        return {"image_base64": None, "available": False}
    set_active_provider(provider)
    image_b64 = generate_scene_image(
        payload.scene_text, payload.genre, payload.environment_type,
        player_photos_b64=payload.player_photos_b64 or None,
        player_names=payload.player_names or None,
    )
    return {"image_base64": image_b64, "available": bool(image_b64)}

class TacticalMapPayload(BaseModel):
    location_name: str = ""
    location_description: str = ""
    genre: str = "fantasy"
    environment_type: str = "indoor"
    scene_narrative: str = ""       # testo narrativo del turno in cui scatta il combattimento
    mission_environment: str = ""   # environment_type della missione (dal GameState)
    enemy_names: list[str] = []     # nomi dei nemici (per inferire il tipo di luogo)

@app.post("/game/generate-tactical-map-image")
def generate_tactical_map(payload: TacticalMapPayload):
    provider = _resolve_image_provider()
    if not provider:
        return {"image_b64": None, "available": False}
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
    )
    return {"image_b64": image_b64, "available": bool(image_b64)}

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

@app.get("/game/providers-available")
def providers_available():
    return {
        "claude": bool(os.getenv("ANTHROPIC_API_KEY")),
        "openai": bool(OPENAI_API_KEY) and _OPENAI_AVAILABLE,
        "gemini": bool(os.getenv("GOOGLE_AI_STUDIO_KEY")) and _GOOGLE_GENAI_AVAILABLE,
    }

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
    map_page: str = Form(default=""),
):
    """Estrae testo dal PDF e genera la bibbia. map_page opzionale: numero pagina (1-based) da usare come mappa."""
    import json as _json, base64
    try:
        import pdfplumber
        from PIL import Image
    except ImportError:
        return {"error": "pdfplumber/Pillow non installato sul server"}

    pdf_bytes = await file.read()
    text_pages = []
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

        for page in pdf.pages[:60]:
            t = page.extract_text()
            if t:
                text_pages.append(t)

    pdf_text = "\n\n".join(text_pages).strip()
    if not pdf_text:
        return {"error": "Impossibile estrarre testo dal PDF"}
    raw_chars = len(pdf_text)
    pdf_text = _clean_pdf_text(pdf_text)
    print(f"[adventure/from-pdf] estratte {len(text_pages)}/{total_pages} pagine, {raw_chars} caratteri → {len(pdf_text)} dopo pulizia ({100*len(pdf_text)//max(raw_chars,1)}%)")

    try:
        players_list = _json.loads(players)
    except Exception:
        players_list = []

    result = create_adventure_from_pdf_text(pdf_text, genre, players_list)
    if map_image_b64:
        result["map_image_b64"] = map_image_b64
    return result
