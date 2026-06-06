"""
Persistenza campagne su file system.

Ogni campagna è salvata come JSON in:
  data/campaigns/{campaign_id}.json

Il directory viene creato al primo salvataggio.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .models import (
    Campaign, CampaignPlayer, CampaignSummary,
    AdventureRecord, ActiveCondition, Player,
)

# ─── Percorso base ─────────────────────────────────────────────────────────────

def _campaigns_dir() -> Path:
    here = Path(__file__).parent.parent.parent  # repo root
    d = here / "data" / "campaigns"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _campaign_path(campaign_id: str) -> Path:
    return _campaigns_dir() / f"{campaign_id}.json"


# ─── CRUD ──────────────────────────────────────────────────────────────────────

def save_campaign(campaign: Campaign) -> None:
    """Scrive la campagna su disco (sovrascrive se esiste)."""
    campaign.last_played_at = datetime.now(timezone.utc).isoformat()
    path = _campaign_path(campaign.id)
    path.write_text(
        campaign.model_dump_json(indent=2),
        encoding="utf-8",
    )


def load_campaign(campaign_id: str) -> Optional[Campaign]:
    """Carica una campagna dal file. Ritorna None se non esiste."""
    path = _campaign_path(campaign_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Campaign.model_validate(data)
    except Exception as e:
        raise ValueError(f"Campagna {campaign_id} corrotta: {e}") from e


def delete_campaign(campaign_id: str) -> bool:
    """Elimina una campagna. Ritorna True se esisteva."""
    path = _campaign_path(campaign_id)
    if path.exists():
        path.unlink()
        return True
    return False


def list_campaigns() -> List[CampaignSummary]:
    """Lista leggera di tutte le campagne (senza caricare i Player completi)."""
    summaries = []
    for path in sorted(_campaigns_dir().glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            summaries.append(CampaignSummary(
                id=data.get("id", path.stem),
                name=data.get("name", "?"),
                genre=data.get("genre", ""),
                world_name=data.get("world_name", ""),
                player_names=[
                    cp.get("player", {}).get("name", "?")
                    for cp in data.get("players", [])
                ],
                session_count=data.get("session_count", 0),
                last_played_at=data.get("last_played_at", ""),
                current_adventure_id=data.get("current_adventure_id", ""),
            ))
        except Exception:
            continue  # file corrotto — salta
    return summaries


# ─── Creazione ─────────────────────────────────────────────────────────────────

def create_campaign(
    name: str,
    genre: str,
    world_name: str = "",
    cp_per_session: int = 3,
    starting_cp: int = 100,
    max_disadvantage_cp: int = 50,
) -> Campaign:
    """Crea una nuova campagna vuota e la salva su disco."""
    now = datetime.now(timezone.utc).isoformat()
    campaign = Campaign(
        id=str(uuid.uuid4()),
        name=name,
        genre=genre,
        world_name=world_name,
        created_at=now,
        last_played_at=now,
        cp_per_session=cp_per_session,
        starting_cp=starting_cp,
        max_disadvantage_cp=max_disadvantage_cp,
    )
    save_campaign(campaign)
    return campaign


# ─── Gestione PG ───────────────────────────────────────────────────────────────

def add_player_to_campaign(campaign_id: str, player: Player) -> CampaignPlayer:
    """Aggiunge un PG già creato alla campagna e salva."""
    campaign = load_campaign(campaign_id)
    if not campaign:
        raise ValueError(f"Campagna {campaign_id} non trovata")

    cp = CampaignPlayer(
        id=str(uuid.uuid4()),
        player=player,
        money=_starting_money(campaign.genre),
    )
    campaign.players.append(cp)
    save_campaign(campaign)
    return cp


def update_player_in_campaign(campaign_id: str, campaign_player: CampaignPlayer) -> None:
    """Aggiorna un CampaignPlayer esistente (per id) e salva la campagna."""
    campaign = load_campaign(campaign_id)
    if not campaign:
        raise ValueError(f"Campagna {campaign_id} non trovata")

    for i, cp in enumerate(campaign.players):
        if cp.id == campaign_player.id:
            campaign.players[i] = campaign_player
            save_campaign(campaign)
            return
    raise ValueError(f"Giocatore {campaign_player.id} non trovato nella campagna {campaign_id}")


def _starting_money(genre: str) -> float:
    """Denaro iniziale approssimativo per genere (Wealth = 10 → Average)."""
    defaults = {
        "fantasy": 500.0,
        "medievale": 500.0,
        "storico": 500.0,
        "western": 300.0,
        "horror": 5000.0,
        "modern": 10000.0,
        "sci_fi": 20000.0,
        "steampunk": 1000.0,
        "noir": 5000.0,
    }
    return defaults.get(genre, 1000.0)


# ─── Fine avventura ────────────────────────────────────────────────────────────

def complete_adventure(
    campaign_id: str,
    adventure_id: str,
    adventure_name: str,
    outcome: str,
    cp_override: Optional[int],
    player_updates: List[dict],
    world_facts_new: List[str],
    faction_reputation_delta: dict,
) -> Campaign:
    """
    Chiude un'avventura:
    - Assegna CP ai PG
    - Aggiorna HP/ferite/condizioni dai player_updates
    - Aggiunge fatti al mondo
    - Aggiorna reputazione fazioni
    - Registra l'avventura nello storico di ogni PG
    - Applica guarigione naturale (1 HT roll/giorno per rest_days_accumulated)
    """
    campaign = load_campaign(campaign_id)
    if not campaign:
        raise ValueError(f"Campagna {campaign_id} non trovata")

    cp_awarded = cp_override if cp_override is not None else campaign.cp_per_session
    now_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Mappa aggiornamenti player per id
    updates_by_id = {u["campaign_player_id"]: u for u in player_updates}

    for cp in campaign.players:
        upd = updates_by_id.get(cp.id, {})

        # Aggiorna stato Player dal GameState (HP, FP, ferite, condizioni)
        if "player" in upd:
            cp.player = Player.model_validate(upd["player"])
        if "active_conditions" in upd:
            cp.active_conditions = [
                ActiveCondition.model_validate(c) for c in upd["active_conditions"]
            ]
        if "money_delta" in upd:
            cp.money = max(0.0, cp.money + float(upd["money_delta"]))
        if "reputation_delta" in upd:
            for group, delta in upd["reputation_delta"].items():
                cp.reputation[group] = max(-5, min(5, cp.reputation.get(group, 0) + delta))

        # Assegna CP
        cp.unspent_cp += cp_awarded
        cp.total_cp_earned += cp_awarded

        # Guarigione naturale per i giorni di riposo accumulati
        rest_days = int(upd.get("rest_days", 0))
        if rest_days > 0:
            cp.rest_days_accumulated += rest_days
            _apply_natural_healing(cp, rest_days)

        # Registra avventura nello storico
        cp.adventure_history.append(AdventureRecord(
            adventure_id=adventure_id,
            adventure_name=adventure_name,
            completed_at=now_date,
            cp_awarded=cp_awarded,
            outcome=outcome,
            hp_lost=int(upd.get("hp_lost", 0)),
            notable_events=upd.get("notable_events", []),
        ))

    # Aggiorna mondo
    campaign.world_facts.extend(world_facts_new)
    for faction, delta in faction_reputation_delta.items():
        current = campaign.faction_reputation.get(faction, 0)
        campaign.faction_reputation[faction] = max(-5, min(5, current + delta))

    # Chiudi avventura
    campaign.completed_adventure_ids.append(adventure_id)
    campaign.current_adventure_id = ""
    campaign.session_count += 1

    save_campaign(campaign)
    return campaign


def _apply_natural_healing(cp: CampaignPlayer, days: int) -> None:
    """Guarigione naturale GURPS (B424): tiro HT 1×/giorno → +1 PF su successo."""
    import random
    p = cp.player
    for _ in range(days):
        if p.hp >= p.max_hp:
            break
        roll = sum(random.randint(1, 6) for _ in range(3))
        ht = p.stats.get("SA", 10)
        if roll <= ht:
            p.hp = min(p.max_hp, p.hp + 1)

    # Riduci ferite persistenti: ogni 3 giorni le minor wounds decadono
    days_per_minor = 3
    healed = []
    for wound in p.wounds:
        if wound.severity == "minor" and days >= days_per_minor:
            continue  # rimossa
        healed.append(wound)
    p.wounds = healed


# ─── Avanzamento PG ────────────────────────────────────────────────────────────

# Costi GURPS (Character p.170)
_ATTRIBUTE_COSTS = {"FO": 10, "DE": 20, "IN": 20, "SA": 10}
_DERIVED_COSTS = {"volontà": 5, "percezione": 5, "pf": 2, "fp": 3}
_SKILL_DIFFICULTY_COST = {
    # costo per passare dal livello corrente al successivo
    "E": [1, 1, 2, 4],   # punto necessario per ogni step (0→1pt, 1→2pt, ecc.)
    "A": [1, 2, 4, 8],
    "H": [2, 4, 8, 16],
    "VH": [4, 8, 16, 32],
}


def spend_cp(
    campaign_id: str,
    campaign_player_id: str,
    improvement_type: str,
    target: str,
    levels: int = 1,
) -> dict:
    """
    Spende CP per migliorare un PG.

    improvement_type:
      "attribute"  → target = "FO"|"DE"|"IN"|"SA"|"volontà"|"percezione"|"pf"|"fp"
      "skill"      → target = nome skill
      "spell"      → target = spell_id (deve essere già nella spell list)
      "advantage"  → target = nome vantaggio (costo manuale, levels = costo totale in CP)

    Ritorna {"ok": True, "cp_spent": N, "new_value": V} o {"ok": False, "error": "..."}
    """
    campaign = load_campaign(campaign_id)
    if not campaign:
        return {"ok": False, "error": "Campagna non trovata"}

    cp_player = next((p for p in campaign.players if p.id == campaign_player_id), None)
    if not cp_player:
        return {"ok": False, "error": "PG non trovato"}

    p = cp_player.player
    result = _apply_improvement(p, cp_player, improvement_type, target, levels)
    if not result["ok"]:
        return result

    if cp_player.unspent_cp < result["cp_spent"]:
        return {"ok": False, "error": f"CP insufficienti ({cp_player.unspent_cp} disponibili, {result['cp_spent']} richiesti)"}

    cp_player.unspent_cp -= result["cp_spent"]
    _recalculate_derived(p)

    update_player_in_campaign(campaign_id, cp_player)
    return result


def _apply_improvement(
    p: Player,
    cp_player: CampaignPlayer,
    improvement_type: str,
    target: str,
    levels: int,
) -> dict:
    from .data_skills import get_skill_info

    if improvement_type == "attribute":
        cost_per = _ATTRIBUTE_COSTS.get(target) or _DERIVED_COSTS.get(target.lower())
        if cost_per is None:
            return {"ok": False, "error": f"Attributo '{target}' sconosciuto"}
        total_cost = cost_per * levels
        if target in ("FO", "DE", "IN", "SA"):
            p.stats[target] = p.stats.get(target, 10) + levels
        elif target.lower() == "volontà":
            p.will += levels
        elif target.lower() == "percezione":
            p.per += levels
        elif target.lower() == "pf":
            p.max_hp += levels
            p.hp = min(p.hp + levels, p.max_hp)
        elif target.lower() == "fp":
            p.max_fp += levels
            p.fp = min(p.fp + levels, p.max_fp)
        return {"ok": True, "cp_spent": total_cost, "new_value": p.stats.get(target, getattr(p, target.lower(), "?"))}

    elif improvement_type == "skill":
        info = get_skill_info(target)
        diff = info.get("difficulty", "A") if info else "A"
        current = p.skills.get(target, 0)
        cost = _skill_improvement_cost(diff, current, current + levels)
        p.skills[target] = current + levels
        return {"ok": True, "cp_spent": cost, "new_value": current + levels}

    elif improvement_type == "spell":
        entry = next((s for s in cp_player.spells if s.spell_id == target), None)
        if not entry:
            return {"ok": False, "error": f"Incantesimo '{target}' non nella spell list"}
        cost = _skill_improvement_cost("H", entry.skill_level, entry.skill_level + levels)
        entry.skill_level += levels
        # sincronizza anche nelle skills del Player per uso in combattimento
        p.skills[f"spell:{target}"] = entry.skill_level
        return {"ok": True, "cp_spent": cost, "new_value": entry.skill_level}

    elif improvement_type == "advantage":
        # levels = costo totale in CP (il GM verifica il vantaggio)
        cost = levels
        p.advantages.append(target)
        return {"ok": True, "cp_spent": cost, "new_value": target}

    return {"ok": False, "error": f"improvement_type '{improvement_type}' non riconosciuto"}


def _skill_improvement_cost(difficulty: str, from_level: int, to_level: int) -> int:
    """CP necessari per portare una skill da from_level a to_level (GURPS B170)."""
    # Approssimazione: ogni +1 sopra il default costa 1 pt per E, 2 per A, 4 per H, 8 per VH
    pts_per_level = {"E": 1, "A": 2, "H": 4, "VH": 8}.get(difficulty, 2)
    return max(1, (to_level - from_level) * pts_per_level)


def _recalculate_derived(p: Player) -> None:
    """Ricalcola tutte le caratteristiche derivate dopo un miglioramento."""
    fo = p.stats.get("FO", 10)
    de = p.stats.get("DE", 10)
    sa = p.stats.get("SA", 10)

    p.max_hp = fo
    p.max_fp = sa
    p.basic_speed = (de + sa) / 4.0
    p.move = int(p.basic_speed)
    p.dodge = int(p.basic_speed) + 3
    # Will e Per non si sovrascrivono se già modificati manualmente oltre il base
    # (l'utente li può aver alzati con CP separati)
