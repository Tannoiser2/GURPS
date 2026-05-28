"""
Creazione personaggio manuale GURPS Lite 4ª ed. (PR5).

Budget: 100 punti (power level Eccezionale, 75-100 pt).
Questo modulo gestisce:
  - calcolo costo punti per stat, skill, vantaggi/svantaggi
  - validazione vincoli (range stat, livelli skill, budget)
  - calcolo derivate (PF, FP, schivata, velocità...)
  - costruzione di un Player completo da un CharacterDraft
"""

from .models import CharacterDraft, CharacterValidation, Player, Action
from .data_skills import SKILL_INFO, default_skill_for, VALID_SKILLS, normalize_skill, normalize_stat
from .data_advantages import ADVANTAGES, advantage_dodge_bonus, advantage_death_threshold_mult, advantage_will_modifier, advantage_per_modifier, trait_cost
from .engine import build_players_from_dicts
from .equipment_coherence import validate_gear_for_genre, starter_item_names

# ─── Costo stat GURPS ────────────────────────────────────────────────────────
# Ogni punto oltre 10 costa 10 pt; ogni punto sotto 10 restituisce 10 pt.
# Forza e Salute (FO/SA) costano 10/livello.
# Destrezza e Intelligenza (DE/IN) costano 20/livello.
_STAT_COST_PER_LEVEL: dict[str, int] = {
    "forza":        10,
    "agilita":      20,
    "intelligenza": 20,
    "empatia":      10,
}
_STAT_BASE = 10


def stat_cost(stat: str, value: int) -> int:
    """Costo in punti GURPS per portare stat da 10 a value (negativo = rimborso)."""
    cost_per = _STAT_COST_PER_LEVEL.get(stat, 10)
    return (value - _STAT_BASE) * cost_per


# ─── Costo skill GURPS Lite 4ª ───────────────────────────────────────────────
# Tabella costi abilita:
#   Facile:    Attributo=1, Attributo+1=2, Attributo+2=4, Attributo+3=8, +4/livello
#   Media:     Attributo-1=1, Attributo=2, Attributo+1=4, Attributo+2=8, +4/livello
#   Difficile: Attributo-2=1, Attributo-1=2, Attributo=4, Attributo+1=8, +4/livello
_SKILL_COST_TABLE: dict[str, dict[int, int]] = {
    "E": {0: 1, 1: 2, 2: 4, 3: 8},
    "M": {-1: 1, 0: 2, 1: 4, 2: 8, 3: 12},
    "D": {-2: 1, -1: 2, 0: 4, 1: 8, 2: 12, 3: 16},
}


def _skill_cost_from_relative_level(difficulty: str, relative_level: int) -> int:
    table = _SKILL_COST_TABLE.get(difficulty, _SKILL_COST_TABLE["M"])
    minimum_relative = min(table)
    if relative_level < minimum_relative:
        return 0
    if relative_level in table:
        return table[relative_level]
    highest_relative = max(table)
    return table[highest_relative] + ((relative_level - highest_relative) * 4)


def skill_cost(skill_name: str, target_level: int, stats: dict[str, int]) -> int:
    """
    Costo in punti GURPS per portare skill_name al target_level.
    Restituisce 0 se il livello è ≤ default (non ha senso comprare sotto il default).
    """
    info = SKILL_INFO.get(skill_name, {})
    difficulty = info.get("difficulty", "M")
    stat_name = info.get("stat", "intelligenza")
    stat_val = stats.get(stat_name, 10)

    return _skill_cost_from_relative_level(difficulty, target_level - stat_val)


# ─── Costo vantaggi / rimborso svantaggi ─────────────────────────────────────

def advantage_cost(adv_name: str) -> int:
    """Costo (positivo) o rimborso (negativo) di un vantaggio/svantaggio."""
    return trait_cost(adv_name)


# ─── Calcolo totale punti ────────────────────────────────────────────────────

def point_total(draft: CharacterDraft) -> tuple[int, int, int, int]:
    """
    Restituisce (totale, stat_cost_total, skill_cost_total, adv_cost_total).
    Svantaggi hanno costo negativo (rimborso).
    """
    stats = {normalize_stat(k): v for k, v in (draft.stats or {}).items()}
    sc = sum(stat_cost(s, v) for s, v in stats.items())
    skc = sum(skill_cost(normalize_skill(sk), lvl, stats) for sk, lvl in (draft.skills or {}).items())
    avc = sum(advantage_cost(a) for a in (draft.advantages or []))
    disc = sum(advantage_cost(d) for d in (draft.disadvantages or []))
    return sc + skc + avc + disc, sc, skc, avc + disc


# ─── Validazione ─────────────────────────────────────────────────────────────

_STAT_MIN = 6
_STAT_MAX = 16
_SKILL_MIN = 1
_SKILL_MAX = 20
_POINT_BUDGET = 100
_DISADV_LIMIT = -40     # GURPS Lite: svantaggi non possono valere più di 40 pt di rimborso


def validate_draft(draft: CharacterDraft) -> CharacterValidation:
    """
    Valida un CharacterDraft e restituisce un CharacterValidation con:
      - valid: bool
      - errori e warning
      - derivate calcolate
      - breakdown costi
    """
    errors: list[str] = []
    warnings: list[str] = []
    stats = {normalize_stat(k): v for k, v in (draft.stats or {}).items()}

    # ── Stat ──────────────────────────────────────────────────────────────────
    for s in ("forza", "agilita", "intelligenza", "empatia"):
        v = stats.get(s, 10)
        if v < _STAT_MIN:
            errors.append(f"{s} = {v} sotto il minimo ({_STAT_MIN})")
        elif v > _STAT_MAX:
            errors.append(f"{s} = {v} sopra il massimo ({_STAT_MAX})")
        if v < 8:
            warnings.append(f"{s} = {v} è molto bassa per power level Eccezionale (consigliato ≥8)")
        elif v > 14:
            warnings.append(f"{s} = {v} è alta per power level Eccezionale (consigliato ≤14)")

    # ── Skill ─────────────────────────────────────────────────────────────────
    for sk, lvl in (draft.skills or {}).items():
        if normalize_skill(sk) not in VALID_SKILLS:
            warnings.append(f"Skill '{sk}' non riconosciuta — verrà ignorata dal motore")
        if lvl < _SKILL_MIN:
            errors.append(f"Skill {sk} = {lvl} sotto il minimo ({_SKILL_MIN})")
        elif lvl > _SKILL_MAX:
            errors.append(f"Skill {sk} = {lvl} sopra il massimo ({_SKILL_MAX})")

    # ── Vantaggi/Svantaggi ───────────────────────────────────────────────────
    for a in (draft.advantages or []):
        base = a.rsplit(" ", 1)[0] if a.rsplit(" ", 1)[-1].isdigit() else a
        entry = ADVANTAGES.get(a) or ADVANTAGES.get(base)
        if not entry:
            warnings.append(f"Vantaggio '{a}' non riconosciuto — nessun effetto meccanico")
        elif entry.get("type") != "advantage":
            errors.append(f"'{a}' è uno svantaggio, non un vantaggio")

    disadv_refund = 0
    for d in (draft.disadvantages or []):
        base = d.rsplit(" ", 1)[0] if d.rsplit(" ", 1)[-1].isdigit() else d
        entry = ADVANTAGES.get(d) or ADVANTAGES.get(base)
        if not entry:
            warnings.append(f"Svantaggio '{d}' non riconosciuto — nessun effetto meccanico")
        elif entry.get("type") != "disadvantage":
            errors.append(f"'{d}' è un vantaggio, non uno svantaggio")
        else:
            disadv_refund += entry.get("cost", 0)   # negativo
    if disadv_refund < _DISADV_LIMIT:
        errors.append(f"Troppi svantaggi: rimborso totale {disadv_refund} supera il limite di {_DISADV_LIMIT} pt")

    # ── Coerenza equipaggiamento con il genere ───────────────────────────────
    if draft.items and draft.genre:
        gear_warnings = validate_gear_for_genre(list(draft.items), draft.genre)
        warnings.extend(gear_warnings)

    # ── Punti ─────────────────────────────────────────────────────────────────
    total, sc, skc, avc = point_total(draft)
    remaining = _POINT_BUDGET - total
    if total > _POINT_BUDGET:
        errors.append(f"Punti spesi ({total}) superano il budget ({_POINT_BUDGET})")
    elif remaining > 20:
        warnings.append(f"Rimangono {remaining} pt non spesi — personaggio sottopotenziato")

    # ── Derivate ──────────────────────────────────────────────────────────────
    forza = stats.get("forza", 10)
    agilita = stats.get("agilita", 10)
    empatia = stats.get("empatia", 10)
    intelligenza = stats.get("intelligenza", 10)

    max_hp = max(1, forza)
    max_fp = max(1, empatia)
    will = intelligenza
    per = intelligenza
    basic_speed = (agilita + empatia) / 4.0
    move = int(basic_speed)
    all_adv = list(draft.advantages or []) + list(draft.disadvantages or [])
    dodge = move + 3 + advantage_dodge_bonus(all_adv)
    will += advantage_will_modifier(all_adv)
    per += advantage_per_modifier(all_adv)

    return CharacterValidation(
        valid=len(errors) == 0,
        point_total=total,
        point_budget=_POINT_BUDGET,
        points_remaining=remaining,
        errors=errors,
        warnings=warnings,
        max_hp=max_hp,
        max_fp=max_fp,
        will=will,
        per=per,
        basic_speed=round(basic_speed, 2),
        dodge=dodge,
        move=move,
        stat_cost=sc,
        skill_cost=skc,
        advantage_cost=avc,
        disadvantage_refund=disadv_refund,
    )


# ─── Build Player da CharacterDraft ──────────────────────────────────────────

_NEXT_CUSTOM_ID = 100   # ID > 8 (pool di candidati usa 1-8)


def build_custom_player(draft: CharacterDraft) -> Player:
    """
    Converte un CharacterDraft validato in un Player completo con derivate GURPS.
    Assegna un ID univoco partendo da 100.
    """
    global _NEXT_CUSTOM_ID
    player_id = _NEXT_CUSTOM_ID
    _NEXT_CUSTOM_ID += 1

    # Auto-assegna equipaggiamento iniziale se non specificato
    if draft.items:
        assigned_items = list(draft.items)
    else:
        archetype = (draft.archetype or "").lower()
        genre = draft.genre or "fantasy"
        assigned_items = starter_item_names(archetype, genre)

    player_dict = {
        "id": player_id,
        "name": draft.name,
        "role": draft.role,
        "archetype": draft.archetype,
        "stats": dict(draft.stats or {}),
        "skills": {normalize_skill(k): v for k, v in (draft.skills or {}).items()},
        "advantages": list(draft.advantages or []),
        "disadvantages": list(draft.disadvantages or []),
        "dr": draft.dr,
        "items": assigned_items,
        "backstory": draft.backstory or "",
        "motivation": draft.motivation or "",
        "actions": [],
    }

    players = build_players_from_dicts([player_dict])
    return players[0]
