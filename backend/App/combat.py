"""
Risoluzione combattimento meccanico GURPS Lite 4ª ed. (PR2).

Flusso: attacco (3d6≤attack_skill) → difesa attiva dichiarata (3d6≤defense_value)
        → se colpisce: tira danno − DR → applica PF → calcola soglia ferita
        → applica Shock, Major Wound, Knockdown, Death Check.

Niente turni fissi: ogni chiamata risolve un singolo scambio.
All-Out Attack/Defense dichiarati come action_type sul Player prima del tiro.
"""

import random
from .models import AttackResult, CombatDefenseRequest, Player, SceneEntity
from .data_advantages import advantage_dodge_bonus, advantage_death_threshold_mult, advantage_combat_penalty, advantage_ignores_shock

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


# ─── Tiro salvezza su Salute (SA) ────────────────────────────────────────────

def _ht_check(player: Player) -> tuple[int, bool]:
    """3d6 ≤ SA. Ritorna (roll, successo)."""
    sa = player.stats.get("SA", 10)
    roll = _roll3d6()
    return roll, roll <= sa


# ─── Calcolo valori difesa ───────────────────────────────────────────────────

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
        elif defense_request and defense_request.defense_type == "block":
            # Blocco con scudo: disponibile anche contro proiettili (GURPS Lite p.12)
            skill_name = defense_request.defense_skill
            base = target_player.skills.get(skill_name, 0)
            dv = base // 2 + 3
        else:
            # Schivata (o tentativo di parata ranged → fallback automatico a schivata)
            dv = target_player.dodge
            if is_ranged and defense_request and defense_request.defense_type == "parry":
                # Tentativo di parare un proiettile: −1 malus (GURPS B376)
                dv -= 1

        dv += dodge_adv

        # All-Out Defense: +2 schivata/parata/blocco (action_type O flag proattivo)
        if target_player.action_type == "all_out_defense" or getattr(target_player, "all_out_defense_active", False):
            dv += 2

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

        return max(0, dv)

    elif target_entity is not None:
        # Entità NPC: active_defense base; a distanza usa sempre la schivata
        base = max(0, target_entity.active_defense + cover_bonus)
        if is_ranged:
            # Entità ranged: nessun bonus/malus aggiuntivo — già schivata
            pass
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
    """Penalità GURPS per distanza (GURPS Lite semplificato).

    0 yard … range_half  → 0
    range_half+1 … range_max → −3
    range_max+1 … range_max×2 → −6   (limite pratico)
    oltre → impossibile (ritorna −99)
    """
    if distance <= 0 or range_half <= 0:
        return 0  # mischia o range non definito
    if distance <= range_half:
        return 0
    if distance <= range_max:
        return -3
    if distance <= range_max * 2:
        return -6
    return -99  # fuori gittata massima


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
    level = attacker.skills.get(attack_skill_name, 0)
    if level == 0:
        from .data_skills import SKILL_INFO, skill_default_penalty
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
) -> AttackResult:
    """
    Risolve un singolo scambio attacco/difesa/danno GURPS Lite completo.

    Include: Shock, Major Wound, Knockdown, Death Check,
             All-Out Attack/Defense, penalità postura (prone), fatica (FP),
             regole ranged (no parry, penalità distanza, bonus Aim).
    """
    # ── Munizioni: verifica prima di tutto ──────────────────────────────────
    if attack_kind == "ranged" and ammo_current == 0:
        return AttackResult(
            hit=False,
            attacker_margin=0,
            narrative_hint="munizioni_esaurite",
            fp_cost=0,
        )

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
    attack_roll = _roll3d6()
    attacker_critical = _is_critical_success(attack_roll, effective_level)
    attacker_crit_fail = _is_critical_failure(attack_roll, effective_level)
    attacker_margin = effective_level - attack_roll

    # Azzera shock attaccante dopo aver attaccato (fine "turno" implicito)
    attacker.shock_penalty = 0

    # Critico fallimentare
    if attacker_crit_fail:
        return AttackResult(
            hit=False,
            attacker_margin=attacker_margin,
            narrative_hint="critico_fallimentare_attaccante",
            fp_cost=fp_cost,
        )

    # Attacco mancato (non critico)
    if attack_roll > effective_level and not attacker_critical:
        return AttackResult(
            hit=False,
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
            attacker_margin=attacker_margin,
            defense_margin=defense_margin,
            attacker_critical=attacker_critical,
            narrative_hint="difesa_riuscita",
            fp_cost=fp_cost,
        )

    # ── Danno ────────────────────────────────────────────────────────────────
    raw = roll_damage(damage_formula)
    wounding_mult = _DAMAGE_TYPE_WOUNDING.get(damage_type, 1.0)
    effective_raw = int(raw * wounding_mult)

    target_dr = 0
    if target_player is not None:
        target_dr = target_player.dr
    elif target_entity is not None:
        target_dr = target_entity.dr

    net = max(0, effective_raw - target_dr)

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
        floor_hp = -int(target_player.max_hp * death_mult)
        was_above_zero = target_player.hp > 0

        target_player.hp = max(target_player.hp - net, floor_hp)
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

            # ── Death Check (GURPS Lite p.14) ────────────────────────────────
            # Ogni volta che HP scende sotto 0 → tiro SA o morte istantanea
            if target_player.hp <= 0:
                death_check = True
                dc_roll, dc_passed = _ht_check(target_player)
                death_check_passed = dc_passed
                if not dc_passed:
                    threshold = "morto"

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
    else:
        hint = "colpito"

    return AttackResult(
        hit=True,
        defended=False,
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
    player.all_out_defense_active = False   # reset difesa totale proattiva
    player.last_maneuver = ""
