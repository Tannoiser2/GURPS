"""
Risoluzione combattimento meccanico GURPS 4ª ed. Basic Set.

Flusso: attacco (3d6≤attack_skill) → difesa attiva dichiarata (3d6≤defense_value)
        → se colpisce: tira danno − DR → applica PF → calcola soglia ferita
        → applica Shock, Major Wound, Knockdown, Death Check.

Niente turni fissi: ogni chiamata risolve un singolo scambio.
All-Out Attack/Defense dichiarati come action_type sul Player prima del tiro.
"""

import random
from .models import AttackResult, CombatDefenseRequest, Player, SceneEntity, Wound
from .data_advantages import advantage_dodge_bonus, advantage_death_threshold_mult, advantage_ignores_shock

# ─── Distribuzione esatta 3d6 (216 combinazioni) ────────────────────────────
_3D6_OUTCOMES: dict[int, int] = {
    3: 1, 4: 3, 5: 6, 6: 10, 7: 15, 8: 21, 9: 25, 10: 27,
    11: 27, 12: 25, 13: 21, 14: 15, 15: 10, 16: 6, 17: 3, 18: 1,
}
_3D6_TOTAL = 216


def _roll3d6() -> int:
    return sum(random.randint(1, 6) for _ in range(3))


def _is_critical_success(roll: int, skill: int) -> bool:
    if roll <= 4:
        return True
    if roll == 5 and skill >= 15:
        return True
    if roll == 6 and skill >= 16:
        return True
    return False


def _is_critical_failure(roll: int, skill: int) -> bool:
    if roll == 18:
        return True
    if roll == 17 and skill <= 15:
        return True
    return False


# ─── Parser formula danno ────────────────────────────────────────────────────

def roll_damage(formula: str) -> int:
    """Interpreta formule tipo '2d6', '1d6+2', '2d6-1', '3'."""
    formula = formula.strip().lower()
    bonus = 0
    if "+" in formula:
        parts = formula.split("+", 1)
        formula = parts[0].strip()
        bonus = int(parts[1].strip())
    elif formula.count("-") == 1 and not formula.startswith("-"):
        parts = formula.split("-", 1)
        formula = parts[0].strip()
        bonus = -int(parts[1].strip())

    if "d" in formula:
        num_d, sides = formula.split("d", 1)
        num_d = int(num_d) if num_d else 1
        sides = int(sides) if sides else 6   # "3d" → 3d6
        result = sum(random.randint(1, sides) for _ in range(num_d))
    else:
        result = int(formula)

    return max(0, result + bonus)


# ─── Danno swing/thrust GURPS (sw/thr → dadi secondo la Forza) ────────────────
# Tabella Basic Set: ST → (thrust, swing) come (numero_dadi, modificatore).
_BASIC_DAMAGE: dict[int, tuple[tuple[int, int], tuple[int, int]]] = {
    1: ((1, -6), (1, -5)), 2: ((1, -6), (1, -5)), 3: ((1, -5), (1, -4)),
    4: ((1, -5), (1, -4)), 5: ((1, -4), (1, -3)), 6: ((1, -4), (1, -3)),
    7: ((1, -3), (1, -2)), 8: ((1, -3), (1, -2)), 9: ((1, -2), (1, -1)),
    10: ((1, -2), (1, 0)), 11: ((1, -1), (1, 1)), 12: ((1, -1), (1, 2)),
    13: ((1, 0), (2, -1)), 14: ((1, 0), (2, 0)), 15: ((1, 1), (2, 1)),
    16: ((1, 1), (2, 2)), 17: ((1, 2), (3, -1)), 18: ((1, 2), (3, 0)),
    19: ((2, -1), (3, 1)), 20: ((2, -1), (3, 2)),
}


def resolve_swing_thrust(formula: str, st: int) -> str:
    """Converte le formule GURPS 'sw'/'thr' (con eventuale ±N) in dadi reali
    secondo la Forza dell'attaccante. Le formule già in dadi passano intatte."""
    f = (formula or "").strip().lower()
    for code, idx in (("thr", 0), ("sw", 1)):
        if f.startswith(code):
            num_d, mod = _BASIC_DAMAGE[max(1, min(20, int(st or 10)))][idx]
            rest = f[len(code):].replace(" ", "")
            if rest:
                try:
                    mod += int(rest)
                except ValueError:
                    pass
            out = f"{num_d}d"
            if mod > 0:
                out += f"+{mod}"
            elif mod < 0:
                out += f"{mod}"
            return out
    return formula


# ─── Modificatore danno per tipo ─────────────────────────────────────────────
# GURPS 4e: taglio ×1.5, impalante ×2, perforante pesante ×1.5, tox ×1.0
_DAMAGE_TYPE_WOUNDING: dict[str, float] = {
    "cut":  1.5,
    "imp":  2.0,
    "cr":   1.0,
    "burn": 1.0,
    "pi":   1.0,    # perforante standard (proiettili normali)
    "pi+":  1.5,    # perforante pesante (.45 ACP, pallottola espansiva)
    "pi-":  0.5,    # perforante piccolo (bossolo, pellet)
    "pi++": 2.0,    # perforante colossale (railgun, calibro grande)
    "tox":  1.0,    # tossico (stordente, veleno)
}


# ─── Soglie ferita GURPS ─────────────────────────────────────────────────────

def wound_threshold(current_hp: int, max_hp: int, death_mult: float = 1.0) -> str:
    """Restituisce lo stato ferita GURPS in base ai PF attuali."""
    if current_hp > max_hp // 3:
        return ""                                   # illeso / lievi graffi
    if current_hp > 0:
        return "ferito_grave"                       # ≤ PF/3 ma > 0
    if current_hp > -(max_hp * death_mult):
        return "fuori_combattimento"                # 0 .. -(PF × mult)
    return "morto"                                  # < -(PF × mult)


# ─── Shock GURPS (p.14 Lite) ─────────────────────────────────────────────────

def compute_shock(net_damage: int) -> int:
    """Malus Shock = danno netto, massimo −4. Dura fino al prossimo turno."""
    return min(net_damage, 4)


# ─── Ferite persistenti (G3) ─────────────────────────────────────────────────

def wounds_skill_penalty(player: Player) -> int:
    """Penalità cumulativa da ferite non guarite: −1 per ogni ferita major/critical."""
    return -sum(1 for w in (player.wounds or []) if w.severity in ("major", "critical"))


def tick_player_wounds(players: list) -> None:
    """Riduce turns_remaining per le ferite minor/major di tutti i giocatori.
    Chiamato una volta per turno. Rimuove le ferite guarite.
    Solo le ferite con turns_remaining > 0 decrescono automaticamente.
    """
    for player in players:
        if not hasattr(player, "wounds"):
            continue
        healed: list[Wound] = []
        for wound in player.wounds:
            if wound.turns_remaining > 0:
                wound.turns_remaining -= 1
                if wound.turns_remaining == 0 and wound.severity == "minor":
                    healed.append(wound)
        for w in healed:
            player.wounds.remove(w)


def apply_wound_recovery(player: Player, action: str = "rest") -> int:
    """Recupero ferite tramite azione esplicita del giocatore.

    action="rest":       decrementa turns_remaining per tutte le ferite, rimuove le minor guarite
    action="first_aid":  guarisce immediatamente una ferita minor, o converte la prima major
                         in minor (turns_remaining=3) — richiede kit_medico nell'inventario

    Restituisce il numero di ferite guarite/migliorate.
    """
    if not hasattr(player, "wounds") or not player.wounds:
        return 0

    healed = 0
    if action == "rest":
        to_remove: list[Wound] = []
        for wound in player.wounds:
            if wound.turns_remaining > 0:
                wound.turns_remaining -= 1
                if wound.turns_remaining == 0 and wound.severity == "minor":
                    to_remove.append(wound)
                    healed += 1
        for w in to_remove:
            player.wounds.remove(w)

    elif action == "first_aid":
        # Prima cura a disposizione: guarisce minor o migliora major → minor
        for wound in player.wounds:
            if wound.severity == "minor":
                player.wounds.remove(wound)
                healed += 1
                break
            elif wound.severity == "major":
                wound.severity = "minor"
                wound.turns_remaining = 3
                healed += 1
                break

    return healed


# ─── Tiro salvezza su Salute (SA) ────────────────────────────────────────────

def _ht_check(player: Player) -> tuple[int, bool]:
    """3d6 ≤ SA. Ritorna (roll, successo)."""
    sa = player.stats.get("SA", 10)
    roll = _roll3d6()
    return roll, roll <= sa


# ─── Calcolo valori difesa ───────────────────────────────────────────────────

def _encumbrance_level(player: Player) -> int:
    """
    Livello di ingombro GURPS (B17): 0 = None, 1 = Light, 2 = Medium, 3 = Heavy, 4 = Extra-Heavy.
    Basic Lift = ST²/5 (arrotondato). Peso portato in library di Player (summa equipment).
    """
    st = player.stats.get("FO", player.stats.get("ST", 10))
    basic_lift = st * st / 5.0
    # Peso totale attrezzatura (usa campo weight se presente)
    carried = sum(
        getattr(e, "weight", 0) or 0
        for e in getattr(player, "equipment", [])
    )
    if carried <= basic_lift:
        return 0
    elif carried <= basic_lift * 2:
        return 1
    elif carried <= basic_lift * 3:
        return 2
    elif carried <= basic_lift * 6:
        return 3
    else:
        return 4


def effective_move(player: Player) -> int:
    """Move ridotto dall'ingombro: Move × (1 - 0.2×enc_level), minimo 1."""
    base = player.move
    enc = _encumbrance_level(player)
    reduced = max(1, int(base * (1.0 - 0.2 * enc)))
    return reduced


def effective_dodge(player: Player) -> int:
    """Dodge ridotto dall'ingombro: Dodge - enc_level, minimo 1."""
    base = player.dodge
    enc = _encumbrance_level(player)
    return max(1, base - enc)


def _defense_value(
    target_player: Player | None,
    target_entity: SceneEntity | None,
    defense_request: CombatDefenseRequest | None,
    cover_bonus: int = 0,
    rear_attack: bool = False,
    attack_kind: str = "melee",
) -> int:
    """Calcola il valore di difesa effettivo inclusi vantaggi, postura e All-Out Defense.

    cover_bonus:  +X se il bersaglio è in copertura — passato dal frontend.
    rear_attack:  True se l'attacco arriva da dietro → nessuna difesa attiva.
    attack_kind:  "melee" | "ranged" — le armi ranged non possono essere parate
                  (GURPS Lite: solo schivata o blocco con scudo).
    """
    if rear_attack:
        return 0  # attacco da retro: nessuna difesa attiva GURPS Lite p.394

    is_ranged = attack_kind == "ranged"

    if target_player is not None:
        all_adv = target_player.advantages + target_player.disadvantages
        dodge_adv = advantage_dodge_bonus(all_adv)

        if defense_request and defense_request.defense_type == "parry" and not is_ranged:
            # Parata: skill/2 + 3. NON disponibile contro armi a distanza.
            skill_name = defense_request.defense_skill
            base = target_player.skills.get(skill_name, 0)
            dv = base // 2 + 3
            # Multiple Parries (B376): ogni parata successiva nello stesso turno = −4
            parry_count = getattr(target_player, "parry_count", 0)
            if parry_count > 0:
                dv -= 4 * parry_count
            # Incrementa il contatore (reset a fine turno via reset_action_type)
            target_player.parry_count = parry_count + 1
        elif defense_request and defense_request.defense_type == "block":
            # Blocco con scudo (B375): skill/2 + 3 + DB scudo. Max 1 blocco/turno.
            skill_name = defense_request.defense_skill
            base = target_player.skills.get(skill_name, 0)
            shield_db = int(defense_request.shield_db) if hasattr(defense_request, "shield_db") and defense_request.shield_db else 0
            dv = base // 2 + 3 + shield_db
            # Secondo blocco nello stesso turno: impossibile (B375)
            block_count = getattr(target_player, "block_count", 0)
            if block_count > 0:
                dv = 0  # blocco già usato
            target_player.block_count = block_count + 1
        else:
            # Schivata — usa dodge ridotto per ingombro
            dv = effective_dodge(target_player)
            if is_ranged and defense_request and defense_request.defense_type == "parry":
                # Tentativo di parare un proiettile: −1 malus (GURPS B376)
                dv -= 1

        dv += dodge_adv

        # All-Out Defense: +2 schivata/parata/blocco (action_type O flag proattivo)
        if target_player.action_type == "all_out_defense" or getattr(target_player, "all_out_defense_active", False):
            dv += 2

        # Retreat (B374): +3 alla difesa se ci si allontana di 1 hex dal nemico
        if getattr(defense_request, "retreat", False):
            dv += 3

        # Copertura: +bonus difesa da terreno
        dv += cover_bonus

        # Stordito: −4 difesa
        if target_player.stunned:
            dv -= 4

        # Postura: kneeling = −2 difesa mischia; prone = −3 mischia, +1 ranged
        posture = getattr(target_player, "posture", "standing")
        if posture == "kneeling":
            if not is_ranged:
                dv -= 2
        elif posture == "prone" or target_player.prone:
            if is_ranged:
                dv += 1   # a terra è più difficile da colpire con proiettili
            else:
                dv -= 3

        # Ferite persistenti: −1 difesa per ogni ferita major/critical non guarita
        dv += wounds_skill_penalty(target_player)

        return max(0, dv)

    elif target_entity is not None:
        # Attacco Totale dichiarato dall'entità nel suo turno → nessuna difesa
        if getattr(target_entity, "no_active_defense", False):
            return 0
        # Entità NPC: active_defense base (+ Difesa Totale se dichiarata)
        base = max(0, target_entity.active_defense
                   + getattr(target_entity, "defense_bonus", 0) + cover_bonus)
        return base

    return 0


def _resolve_defense(
    defense_request: CombatDefenseRequest | None,
    target_player: Player | None,
    target_entity: SceneEntity | None,
    cover_bonus: int = 0,
    rear_attack: bool = False,
    attack_kind: str = "melee",
) -> tuple[int, int, bool]:
    """
    Risolve il tiro di difesa.
    Ritorna (defense_value, roll, is_critical_fail).
    """
    dv = _defense_value(
        target_player, target_entity, defense_request,
        cover_bonus, rear_attack, attack_kind,
    )

    if dv <= 0:
        return 0, 99, False  # nessuna difesa (incluso attacco da retro)

    roll = _roll3d6()
    crit_fail = _is_critical_failure(roll, dv)
    return dv, roll, crit_fail


def _range_penalty(distance: int, range_half: int, range_max: int) -> int:
    """Penalità GURPS 4e B550: Size and Speed/Range Table.

    Ogni scaglione aumenta la distanza di ~×1.5 e costa −1.
    Sopra range_max il danno base è dimezzato (gestito dal chiamante);
    sopra range_max×2 l'attacco è praticamente impossibile.
    """
    if distance <= 0 or range_half <= 0:
        return 0  # mischia o range non definito

    if distance > range_max * 2:
        return -99  # fuori gittata massima pratica

    # Tabella B550: penalità per distanza in yard
    # (2, 3, 5, 7, 10, 15, 20, 30, 50, 70, 100, 150, 200, 300, 500, …)
    _RANGE_TABLE = [
        (0,   0),
        (2,   0),
        (3,  -1),
        (5,  -2),
        (7,  -3),
        (10, -4),
        (15, -5),
        (20, -6),
        (30, -7),
        (50, -8),
        (70, -9),
        (100,-10),
        (150,-11),
        (200,-12),
        (300,-13),
        (500,-14),
        (700,-15),
        (1000,-16),
        (1500,-17),
        (2000,-18),
        (3000,-19),
        (5000,-20),
        (7000,-21),
        (10000,-22),
    ]
    penalty = -22  # default oltre 10000 yard
    for threshold, pen in _RANGE_TABLE:
        if distance <= threshold:
            penalty = pen
            break
    return penalty


# ─── Rapid Fire: bonus al tiro per volume di fuoco (GURPS B373) ─────────────

def _rof_hit_bonus(shots: int) -> int:
    """Bonus al tiro d'attacco per volume di fuoco (B373, tabella Shots/Bonus to Hit)."""
    if shots < 2:
        return 0
    if shots <= 4:
        return 0
    if shots <= 8:
        return 1
    if shots <= 12:
        return 2
    if shots <= 16:
        return 3
    if shots <= 24:
        return 4
    if shots <= 49:
        return 5
    if shots <= 99:
        return 6
    # ogni ×2 oltre 100 → +1
    import math
    return 6 + int(math.log2(shots / 50))


def _rapid_fire_extra_hits(margin: int, rcl: int, shots_fired: int) -> int:
    """
    Colpi extra da Rapid Fire (B374).
    Un colpo extra per ogni multiplo intero di Rcl contenuto nel margine,
    fino al massimo di (shots_fired - 1).
    """
    if rcl <= 0 or shots_fired <= 1 or margin < rcl:
        return 0
    return min(margin // rcl, shots_fired - 1)


# ─── Calcolo livello attacco ─────────────────────────────────────────────────

def _attack_level(
    attacker: Player,
    attack_skill_name: str,
    attack_kind: str = "melee",
    acc: int = 0,
    distance: int = 0,
    range_half: int = 0,
    range_max: int = 0,
) -> int:
    # Normalizza il nome skill: le armi usano etichette come "pistola"/"fucile"
    # che NON sono chiavi skill (la skill GURPS è "mira"). Senza normalizzare,
    # la lookup falliva, lo stat-cardine diventava "forza" e la penalità il
    # default 5 → livello assurdamente basso (es. "pistola 5").
    from .data_skills import SKILL_INFO, skill_default_penalty, normalize_skill
    attack_skill_name = normalize_skill(attack_skill_name)
    level = attacker.skills.get(attack_skill_name, 0)
    if level == 0:
        stat_name = SKILL_INFO.get(attack_skill_name, {}).get("stat", "forza")
        stat_val = attacker.stats.get(stat_name, 10)
        penalty = skill_default_penalty(attack_skill_name)
        level = max(1, stat_val - penalty)

    # All-Out Attack: +4 attacco, nessuna difesa attiva questo turno
    if attacker.action_type == "all_out_attack":
        level += 4

    # Move and Attack: −4 al tiro (minimo 9, GURPS B324)
    if attacker.action_type == "move_attack":
        level = max(9, level - 4)

    # Evaluate: bonus cumulativo dalla manovra Valuta (max +3, si azzera se cambia bersaglio)
    if getattr(attacker, "evaluate_bonus", 0) > 0:
        level += attacker.evaluate_bonus

    # Kneeling: −2 attacco melee, −2 attacco ranged (ma +2 difesa ranged)
    if getattr(attacker, "posture", "standing") == "kneeling":
        level -= 2

    # Ranged: bonus Aim + penalità distanza
    if attack_kind == "ranged":
        # Bonus Aim accumulato (max +Acc dell'arma)
        if attacker.aimed and acc > 0:
            aim_bonus = min(attacker.aimed_turns, acc)
            level += aim_bonus

        # Penalità distanza
        if distance > 0 and range_half > 0:
            rp = _range_penalty(distance, range_half, range_max)
            level += rp  # rp è negativo o 0

    # Shock: malus al tiro attacco
    level -= attacker.shock_penalty

    # Ferite persistenti: −1 per ogni ferita major/critical non guarita
    level += wounds_skill_penalty(attacker)

    # Stordito: non può attaccare (gestito in engine prima di chiamare resolve_attack)
    # Prone: −3 attacco
    if attacker.prone:
        level -= 3

    return max(1, level)


# ─── Funzione principale ─────────────────────────────────────────────────────

def resolve_attack(
    attacker: Player,
    attack_skill_name: str,
    damage_formula: str,
    damage_type: str,
    target_player: Player | None = None,
    target_entity: SceneEntity | None = None,
    defense_request: CombatDefenseRequest | None = None,
    cover_bonus: int = 0,
    rear_attack: bool = False,
    # ── Parametri armi a distanza ──────────────────────────────────────────
    attack_kind: str = "melee",
    acc: int = 0,            # Acc dell'arma (da Action)
    distance: int = 0,       # distanza in esagoni/yard dal bersaglio (0 = contatto)
    range_half: int = 0,     # gittata ½D dell'arma
    range_max: int = 0,      # gittata massima dell'arma
    ammo_current: int = -1,  # munizioni rimanenti (−1 = non tracciato)
    shots_fired: int = 1,    # colpi sparati (Rapid Fire: 1..RoF)
    rcl: int = 1,            # Recoil dell'arma (1 = nessun rinculo/recoilless)
    prerolled: int | None = None,  # 3d6 già tirato dall'engine (evita la doppia tiratura)
) -> AttackResult:
    """
    Risolve un singolo scambio attacco/difesa/danno GURPS 4e Basic Set completo.

    Include: Shock, Major Wound, Knockdown, Death Check,
             All-Out Attack/Defense, penalità postura (prone), fatica (FP),
             regole ranged (no parry, penalità distanza, bonus Aim),
             Rapid Fire con colpi multipli (B373-374), Size/Speed/Range Table (B550).
    """
    # ── Munizioni: verifica prima di tutto ──────────────────────────────────
    # shots_fired non può superare le munizioni rimanenti
    if attack_kind == "ranged":
        if ammo_current == 0:
            return AttackResult(
                hit=False,
                attacker_margin=0,
                narrative_hint="munizioni_esaurite",
                fp_cost=0,
            )
        if ammo_current > 0:
            shots_fired = min(shots_fired, ammo_current)

    # ── FP: attaccare costa 1 FP se già sotto FP/3 (affaticamento) ──────────
    fp_cost = 0
    if attacker.fp <= attacker.max_fp // 3:
        fp_cost = 1
        attacker.fp = max(0, attacker.fp - 1)

    # Stordito: non può agire (ritorna senza attaccare)
    if attacker.stunned:
        return AttackResult(
            hit=False,
            attacker_margin=0,
            narrative_hint="attaccante_stordito",
            fp_cost=fp_cost,
        )

    effective_level = _attack_level(
        attacker, attack_skill_name,
        attack_kind=attack_kind, acc=acc,
        distance=distance, range_half=range_half, range_max=range_max,
    )

    # ── Rapid Fire: bonus al tiro per volume di fuoco (B373) ────────────────
    rof_hit_bonus = 0
    if attack_kind == "ranged" and shots_fired >= 2:
        rof_hit_bonus = _rof_hit_bonus(shots_fired)
        effective_level += rof_hit_bonus

    # Usa il 3d6 già tirato dall'engine se fornito: così il dado MOSTRATO è
    # esattamente quello che decide colpito/mancato (prima erano due tiri diversi).
    attack_roll = prerolled if prerolled is not None else _roll3d6()
    attacker_critical = _is_critical_success(attack_roll, effective_level)
    attacker_crit_fail = _is_critical_failure(attack_roll, effective_level)
    attacker_margin = effective_level - attack_roll

    # Azzera shock attaccante dopo aver attaccato (fine "turno" implicito)
    attacker.shock_penalty = 0

    # Critico fallimentare
    if attacker_crit_fail:
        return AttackResult(
            hit=False,
            effective_level=effective_level,
            attack_roll=attack_roll,
            attacker_margin=attacker_margin,
            narrative_hint="critico_fallimentare_attaccante",
            fp_cost=fp_cost,
        )

    # Attacco mancato (non critico)
    if attack_roll > effective_level and not attacker_critical:
        return AttackResult(
            hit=False,
            effective_level=effective_level,
            attack_roll=attack_roll,
            attacker_margin=attacker_margin,
            narrative_hint="colpo_mancato",
            fp_cost=fp_cost,
        )

    # ── Aim: azzera flag dopo lo sparo (il bonus si consuma) ────────────────
    if attack_kind == "ranged":
        attacker.aimed = False
        attacker.aimed_turns = 0

    # ── All-Out Attack: attaccante non può difendersi questo turno ──────────
    # (registrato su attacker.action_type; l'engine lo azzera a fine scambio)

    # ── Difesa attiva ────────────────────────────────────────────────────────
    if attacker_critical:
        # Critico: difesa impossibile (GURPS Lite p.12)
        defended = False
        def_value = 0
        defense_roll = 0
        defense_margin = 0
        def_crit_fail = False
    else:
        def_value, defense_roll, def_crit_fail = _resolve_defense(
            defense_request, target_player, target_entity,
            cover_bonus=cover_bonus, rear_attack=rear_attack,
            attack_kind=attack_kind,
        )
        defense_margin = def_value - defense_roll
        defended = defense_roll <= def_value and not def_crit_fail

    if defended:
        return AttackResult(
            hit=True,
            defended=True,
            effective_level=effective_level,
            attack_roll=attack_roll,
            attacker_margin=attacker_margin,
            defense_margin=defense_margin,
            attacker_critical=attacker_critical,
            narrative_hint="difesa_riuscita",
            fp_cost=fp_cost,
        )

    # ── Rapid Fire: colpi extra (B374) ──────────────────────────────────────
    # extra_hits = margin // rcl, capped a shots_fired − 1
    extra_hits = 0
    if attack_kind == "ranged" and shots_fired >= 2 and rcl >= 1:
        extra_hits = _rapid_fire_extra_hits(attacker_margin, rcl, shots_fired)

    # ── Danno ────────────────────────────────────────────────────────────────
    # Risolve sw/thr → dadi secondo la Forza dell'attaccante (armi da mischia).
    # Con Rapid Fire si applica il danno del primo colpo; i colpi extra
    # vengono riportati in extra_hits per la narrazione/frontend.
    # (Fast Damage Resolution B374: tira danno una volta, moltiplica i colpi.)
    _st = (attacker.stats.get("forza", attacker.stats.get("ST", 10))
           if getattr(attacker, "stats", None) else 10)
    raw = roll_damage(resolve_swing_thrust(damage_formula, _st))
    wounding_mult = _DAMAGE_TYPE_WOUNDING.get(damage_type, 1.0)
    effective_raw = int(raw * wounding_mult)

    target_dr = 0
    if target_player is not None:
        target_dr = target_player.dr
    elif target_entity is not None:
        target_dr = target_entity.dr

    # Danno totale: primo colpo + colpi extra (ciascuno = stessa penetrazione netta)
    net_per_hit = max(0, effective_raw - target_dr)
    net = net_per_hit * (1 + extra_hits)

    # ── Applica danno e condizioni al bersaglio ──────────────────────────────
    threshold = ""
    shock_applied = 0
    major_wound = False
    major_wound_check_passed = False
    knockdown = False
    knockdown_check_passed = False
    death_check = False
    death_check_passed = False
    target_stunned = False
    target_prone = False

    if target_player is not None:
        all_adv = target_player.advantages + target_player.disadvantages
        death_mult = advantage_death_threshold_mult(all_adv)
        # GURPS B419: morte automatica a −5×HP (indipendente da Duro da Uccidere).
        # Duro da Uccidere sposta la soglia dei death check, non quella istantanea.
        floor_hp = -target_player.max_hp * 5
        hp_before = target_player.hp
        was_above_zero = hp_before > 0

        target_player.hp = max(target_player.hp - net, floor_hp)
        # Morte automatica a −5×HP (GURPS B419)
        if target_player.hp <= -target_player.max_hp * 5:
            threshold = "morto"
        else:
            threshold = wound_threshold(target_player.hp, target_player.max_hp, death_mult)

        if net > 0:
            # ── Shock (GURPS Lite p.14) ──────────────────────────────────────
            # Malus al prossimo tiro attacco/difesa = danno netto, max −4
            if not advantage_ignores_shock(all_adv):
                shock_applied = compute_shock(net)
                target_player.shock_penalty = max(target_player.shock_penalty, shock_applied)

            # ── Major Wound (GURPS Lite p.14) ────────────────────────────────
            # Singolo colpo > max_hp/2 → tiro SA o stordito
            if net > target_player.max_hp // 2:
                major_wound = True
                mw_roll, mw_passed = _ht_check(target_player)
                major_wound_check_passed = mw_passed
                if not mw_passed:
                    target_player.stunned = True
                    target_stunned = True
                # G3: persisti la ferita grave — penalità −1 fino a cure
                if hasattr(target_player, "wounds"):
                    severity = "critical" if target_player.hp <= 0 else "major"
                    target_player.wounds.append(Wound(
                        severity=severity,
                        turns_remaining=0,
                        description=f"Ferita {severity} ({net} danni netti)",
                    ))

            # ── Knockdown (GURPS Lite p.14) ──────────────────────────────────
            # HP scende a 0 o meno → tiro SA o cade a terra (prone)
            if was_above_zero and target_player.hp <= 0:
                knockdown = True
                kd_roll, kd_passed = _ht_check(target_player)
                knockdown_check_passed = kd_passed
                if not kd_passed:
                    target_player.prone = True
                    target_player.posture = "prone"
                    target_prone = True

            # ── Death Check (GURPS B419) ──────────────────────────────────────
            # Un death check a ogni multiplo di max_hp sotto 0 attraversato
            # da questo colpo: 0, −HP, −2×HP, … fino a −4×HP (oltre è morte auto).
            # death_mult da Duro da Uccidere sposta la soglia fuori_combattimento,
            # ma i death check partono comunque da −1×HP in su.
            if target_player.hp < 0 and threshold != "morto":
                hp_now = target_player.hp
                death_check = True
                # Calcola quanti multipli di max_hp sono stati attraversati
                # da hp_before a hp_now (esclude 0, include ogni −N×max_hp).
                max_hp = target_player.max_hp
                # range dei multipli attraversati: 1 .. 4 (oltre è morte auto)
                for mult in range(1, 5):
                    threshold_val = -max_hp * mult
                    if hp_now <= threshold_val < hp_before:
                        _, dc_passed = _ht_check(target_player)
                        death_check_passed = dc_passed
                        if not dc_passed:
                            threshold = "morto"
                            break
                # Se era già sotto 0 prima del colpo, check per il nuovo valore
                if hp_before <= 0 and hp_now < hp_before:
                    for mult in range(1, 5):
                        threshold_val = -max_hp * mult
                        if hp_now <= threshold_val < hp_before:
                            _, dc_passed = _ht_check(target_player)
                            death_check_passed = dc_passed
                            if not dc_passed:
                                threshold = "morto"
                            break

        # Aggiorna status
        if threshold in ("fuori_combattimento", "morto"):
            target_player.status = "fuori_combattimento" if threshold != "morto" else "morto"
        elif threshold == "ferito_grave":
            target_player.status = "ferito_grave"
        elif net > 0:
            target_player.status = "ferito"

    elif target_entity is not None:
        target_entity.hp = max(0, target_entity.hp - net)
        if target_entity.hp <= 0:
            target_entity.status = "eliminato"
            threshold = "fuori_combattimento"

    # ── Munizioni: decrementa dopo lo sparo (B373) ──────────────────────────
    # Tracciamo il consumo sull'Action del chiamante via return; qui modifichiamo
    # solo il Player se ha l'Action inline (non disponibile direttamente).
    # Il decremento reale viene fatto dall'engine che possiede l'Action.

    # ── Hint narrativo ───────────────────────────────────────────────────────
    if attacker_critical:
        hint = "colpo_critico"
    elif net == 0:
        hint = "danno_assorbito"
    elif threshold == "morto":
        hint = "bersaglio_morto"
    elif threshold == "fuori_combattimento":
        hint = "bersaglio_abbattuto"
    elif major_wound and not major_wound_check_passed:
        hint = "ferita_grave_stordimento"
    elif threshold == "ferito_grave":
        hint = "ferita_grave"
    elif knockdown and not knockdown_check_passed:
        hint = "bersaglio_a_terra"
    elif extra_hits > 0:
        hint = "colpito_raffica"
    else:
        hint = "colpito"

    return AttackResult(
        hit=True,
        defended=False,
        effective_level=effective_level,
        attack_roll=attack_roll,
        raw_damage=raw,
        dr_absorbed=min(effective_raw, target_dr),
        net_damage=net,
        attacker_margin=attacker_margin,
        defense_margin=defense_margin if not attacker_critical else 0,
        attacker_critical=attacker_critical,
        defense_critical_fail=def_crit_fail if not attacker_critical else False,
        wound_threshold=threshold,
        narrative_hint=hint,
        shock_applied=shock_applied,
        major_wound=major_wound,
        major_wound_check_passed=major_wound_check_passed,
        knockdown=knockdown,
        knockdown_check_passed=knockdown_check_passed,
        death_check=death_check,
        death_check_passed=death_check_passed,
        fp_cost=fp_cost,
        target_stunned=target_stunned,
        target_prone=target_prone,
        shots_fired=shots_fired,
        extra_hits=extra_hits,
        rof_hit_bonus=rof_hit_bonus,
    )


# ─── Recupero stordimento (inizio turno del giocatore) ───────────────────────

def attempt_stun_recovery(player: Player) -> tuple[bool, int]:
    """
    3d6 ≤ SA: se riesce il giocatore non è più stordito.
    Chiamato all'inizio del turno di chi è stunned.
    Ritorna (recovered, roll).
    """
    roll, passed = _ht_check(player)
    if passed:
        player.stunned = False
    return passed, roll


# ─── Alzarsi da terra ────────────────────────────────────────────────────────

def stand_up(player: Player) -> None:
    """Il giocatore usa la sua azione per alzarsi. Costa 1 FP se affaticato."""
    player.prone = False
    if player.fp <= player.max_fp // 3:
        player.fp = max(0, player.fp - 1)


# ─── Azzera action_type a fine scambio ──────────────────────────────────────

def reset_action_type(player: Player) -> None:
    """Riporta action_type a 'normal' e azzera i flag di manovra dopo l'azione."""
    player.action_type = "normal"
    player.all_out_defense_active = False
    player.last_maneuver = ""
    # Reset contatori difese multiple a fine turno (B375-376)
    player.parry_count = 0
    player.block_count = 0


# ─── Self-Control Roll per svantaggi mentali (B121) ─────────────────────────

# Mappa svantaggio → (trigger_keywords, self_control_number)
# Il self_control_number è il numero GURPS (6/9/12/15) che indica la difficoltà.
# Se nessun numero è specificato nel nome, si usa 12 (difficoltà media).
_MENTAL_DISADVANTAGE_TRIGGERS: list[tuple[str, list[str], int]] = [
    ("impulsivo",        ["ritirarsi", "aspettare", "pianificare", "nascondersi", "fuggire"], 12),
    ("codardia",         ["attaccare", "avanzare", "combattere", "caricare", "restare"],       9),
    ("berserk",          ["fermarsi", "ritirarsi", "trattare", "non attaccare"],               6),
    ("fobia",            ["avvicinarsi", "stare vicino", "ignorare", "toccare"],               9),
    ("avarizia",         ["rifiutare", "donare", "cedere", "ignorare tesoro"],                12),
    ("dipendenza",       ["ignorare", "resistere", "rifiutare"],                              12),
    ("curiosità",        ["ignorare", "passare oltre", "non investigare"],                     12),
    ("ottimismo",        ["essere pessimista", "rinunciare", "fuggire"],                       15),
    ("sadismo",          ["risparmiare", "non torturare", "essere clemente"],                   6),
]


def self_control_check(player: Player, intended_action_description: str) -> dict:
    """
    Verifica se un PG con svantaggi mentali deve tirare per l'autocontrollo (B121).

    Ritorna un dict con:
      triggered: bool        — True se almeno uno svantaggio si attiva
      disadvantage: str      — nome svantaggio scattato
      self_control: int      — numero autocontrollo (6/9/12/15)
      roll: int              — dado tirato
      passed: bool           — True se ha resistito (roll ≤ self_control o critical_success)
      compelled_action: str  — cosa è COSTRETTO a fare se fallisce
    """
    action_lower = intended_action_description.lower()
    all_disadv = [d.lower() for d in player.disadvantages]

    for disadv_key, triggers, default_sc in _MENTAL_DISADVANTAGE_TRIGGERS:
        # Controlla se il PG ha questo svantaggio
        has_disadv = any(disadv_key in d for d in all_disadv)
        if not has_disadv:
            continue

        # Controlla se l'azione intendente è in conflitto col trigger
        action_conflicts = any(t in action_lower for t in triggers)
        if not action_conflicts:
            continue

        # Estrae il numero di autocontrollo dal nome svantaggio (es. "Codardia 9")
        sc_number = default_sc
        for d in all_disadv:
            if disadv_key in d:
                for word in d.split():
                    if word.isdigit():
                        sc_number = int(word)
                        break

        roll = _roll3d6()
        passed = roll <= sc_number or _is_critical_success(roll, sc_number)

        compelled = ""
        if not passed:
            # Cosa viene costretto a fare
            if disadv_key == "impulsivo":
                compelled = "Il PG agisce immediatamente senza pensare."
            elif disadv_key == "codardia":
                compelled = "Il PG deve fuggire o cercare riparo."
            elif disadv_key == "berserk":
                compelled = "Il PG entra in berserk: All-Out Attack obbligatorio fino a fine combattimento."
            elif disadv_key == "fobia":
                compelled = "Il PG è paralizzato dalla paura (Fright Check immediato)."
            elif disadv_key == "avarizia":
                compelled = "Il PG non può ignorare l'opportunità di guadagno."
            elif disadv_key == "curiosità":
                compelled = "Il PG deve indagare la fonte della curiosità."
            else:
                compelled = f"Il PG cede allo svantaggio '{disadv_key}'."

        return {
            "triggered": True,
            "disadvantage": disadv_key,
            "self_control": sc_number,
            "roll": roll,
            "passed": passed,
            "compelled_action": compelled,
        }

    return {"triggered": False, "passed": True}


# ─── Quick Contest (B348) ────────────────────────────────────────────────────

def resolve_quick_contest(
    attacker_skill: int,
    defender_skill: int,
    attacker_label: str = "PG",
    defender_label: str = "NPG",
) -> "QuickContestResult":
    """
    Risolve un Quick Contest GURPS (B348).

    Entrambi tirano 3d6 ≤ propria skill.
    - Se uno solo fallisce → l'altro vince.
    - Se entrambi riescono → chi ha il margine maggiore (skill - roll) vince.
    - Se entrambi falliscono → pareggio.
    - Parità di margine → pareggio (il defender tiene).
    """
    from .models import QuickContestResult

    att_roll = _roll3d6()
    def_roll = _roll3d6()

    att_margin = attacker_skill - att_roll
    def_margin = defender_skill - def_roll

    att_crit = _is_critical_success(att_roll, attacker_skill)
    def_crit = _is_critical_success(def_roll, defender_skill)
    att_crit_fail = _is_critical_failure(att_roll, attacker_skill)
    def_crit_fail = _is_critical_failure(def_roll, defender_skill)
    att_success = att_roll <= attacker_skill
    def_success = def_roll <= defender_skill

    # Critici hanno priorità assoluta
    if att_crit and not def_crit:
        winner = "attacker"
    elif def_crit and not att_crit:
        winner = "defender"
    elif att_crit_fail and not def_crit_fail:
        winner = "defender"
    elif def_crit_fail and not att_crit_fail:
        winner = "attacker"
    elif att_success and not def_success:
        winner = "attacker"
    elif def_success and not att_success:
        winner = "defender"
    elif not att_success and not def_success:
        winner = "tie"
    elif att_margin > def_margin:
        winner = "attacker"
    elif def_margin > att_margin:
        winner = "defender"
    else:
        winner = "tie"

    hint_map = {"attacker": attacker_label + " vince", "defender": defender_label + " vince", "tie": "pareggio"}
    hint = hint_map[winner]
    if att_crit and winner == "attacker":
        hint += " (critico)"
    if def_crit and winner == "defender":
        hint += " (critico)"

    return QuickContestResult(
        attacker_roll=att_roll,
        attacker_target=attacker_skill,
        attacker_margin=att_margin,
        attacker_critical=att_crit,
        attacker_critical_fail=att_crit_fail,
        defender_roll=def_roll,
        defender_target=defender_skill,
        defender_margin=def_margin,
        defender_critical=def_crit,
        defender_critical_fail=def_crit_fail,
        winner=winner,
        net_margin=att_margin - def_margin,
        narrative_hint=hint,
    )
