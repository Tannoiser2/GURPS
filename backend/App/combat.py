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
        num_d, sides = formula.split("d")
        num_d = int(num_d) if num_d else 1
        sides = int(sides)
        result = sum(random.randint(1, sides) for _ in range(num_d))
    else:
        result = int(formula)

    return max(0, result + bonus)


# ─── Modificatore danno per tipo ─────────────────────────────────────────────
# GURPS: taglio ×1.5, impalante ×2 (applicati prima del DR per le ferite narrative)
_DAMAGE_TYPE_WOUNDING: dict[str, float] = {
    "cut":  1.5,
    "imp":  2.0,
    "cr":   1.0,
    "burn": 1.0,
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
) -> int:
    """Calcola il valore di difesa effettivo inclusi vantaggi, postura e All-Out Defense.

    cover_bonus: +2 se il bersaglio è in copertura (terrain=1) — passato dal frontend.
    rear_attack: True se l'attacco arriva da dietro — annulla la difesa attiva (dv→0).
    """
    if rear_attack:
        return 0  # attacco da retro: nessuna difesa attiva GURPS Lite p.394

    if target_player is not None:
        all_adv = target_player.advantages + target_player.disadvantages
        dodge_adv = advantage_dodge_bonus(all_adv)

        if defense_request and defense_request.defense_type == "parry":
            skill_name = defense_request.defense_skill
            base = target_player.skills.get(skill_name, 0)
            dv = base // 2 + 3
        elif defense_request and defense_request.defense_type == "block":
            skill_name = defense_request.defense_skill
            base = target_player.skills.get(skill_name, 0)
            dv = base // 2 + 3
        else:
            dv = target_player.dodge

        dv += dodge_adv

        # All-Out Defense: +2 schivata/parata
        if target_player.action_type == "all_out_defense":
            dv += 2

        # Copertura: +2 difesa da terreno
        dv += cover_bonus

        # Stordito: −4 difesa
        if target_player.stunned:
            dv -= 4

        # Prone: −3 in mischia, +1 contro proiettili (semplificato: −2 netto)
        if target_player.prone:
            dv -= 2

        return max(0, dv)

    elif target_entity is not None:
        return max(0, target_entity.active_defense + cover_bonus)

    return 0


def _resolve_defense(
    defense_request: CombatDefenseRequest | None,
    target_player: Player | None,
    target_entity: SceneEntity | None,
    cover_bonus: int = 0,
    rear_attack: bool = False,
) -> tuple[int, int, bool]:
    """
    Risolve il tiro di difesa.
    Ritorna (defense_value, roll, is_critical_fail).
    """
    dv = _defense_value(target_player, target_entity, defense_request, cover_bonus, rear_attack)

    if dv <= 0:
        return 0, 99, False  # nessuna difesa (incluso attacco da retro)

    roll = _roll3d6()
    crit_fail = _is_critical_failure(roll, dv)
    return dv, roll, crit_fail


# ─── Calcolo livello attacco ─────────────────────────────────────────────────

def _attack_level(attacker: Player, attack_skill_name: str) -> int:
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
) -> AttackResult:
    """
    Risolve un singolo scambio attacco/difesa/danno GURPS Lite completo.

    Include: Shock, Major Wound, Knockdown, Death Check,
             All-Out Attack/Defense, penalità postura (prone), fatica (FP).
    """
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

    effective_level = _attack_level(attacker, attack_skill_name)
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
        # All-Out Attack: bersaglio non può difendersi se l'attaccante ha AoA
        # (GURPS: AoA non toglie la difesa al bersaglio, la toglie all'attaccante)
        def_value, defense_roll, def_crit_fail = _resolve_defense(
            defense_request, target_player, target_entity,
            cover_bonus=cover_bonus, rear_attack=rear_attack,
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
    """Riporta action_type a 'normal' dopo che l'azione è stata usata."""
    player.action_type = "normal"
