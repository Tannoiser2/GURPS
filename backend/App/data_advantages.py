"""
Definizioni meccaniche vantaggi e svantaggi GURPS Lite 4ª ed. (PR3 + espansione).

Struttura di ogni voce:
  "nome_canonico": {
      "type":      "advantage" | "disadvantage",
      "cost":      punti GURPS (positivo = vantaggio, negativo = svantaggio),
      "skill_bonus":    {skill: bonus_int, ...}   — bonus ai tiri di quella skill
      "effect_type_bonus": {effect_type: bonus}  — bonus su tipo di effetto
      "stat_bonus":     {stat: bonus}             — modifica derivata (applicata al build)
      "dodge_bonus":    int                       — bonus alla schivata base
      "death_threshold_mult": float               — moltiplica soglia morte (default 1.0 → −PF)
      "hp_mult":        float                     — moltiplica max_hp (applicata al build)
      "morale_check":   bool                      — se True, deve tirare Volontà per ritirarsi
      "penalty_in_combat": int                    — penalità fissa in combattimento
      "reaction_modifier": int                    — modifica ai tiri di reazione NPC
      "notes":          str
  }
"""

ADVANTAGES: dict[str, dict] = {

    # ═══════════════════════════════════════════════════════════════════════════
    # VANTAGGI
    # ═══════════════════════════════════════════════════════════════════════════

    "Carisma": {
        "type": "advantage",
        "cost": 5,                      # 5 pt per livello
        "skill_bonus": {
            "persuadere":    2,
            "calmare":       2,
            "ispirare":      2,
            "comandare":     2,
            "intrattenere":  1,
            "etichetta":     1,
            "parlare_in_pubblico": 2,
        },
        "effect_type_bonus": {"negoziare": 2},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "reaction_modifier": 2,
        "notes": "+2 ai tiri di reazione NPC, +2 alle skill sociali chiave",
    },

    "Riflessi da Combattimento": {
        "type": "advantage",
        "cost": 15,
        "skill_bonus": {},
        "effect_type_bonus": {},
        "dodge_bonus": 1,               # +1 a schivata, parata, blocco
        "initiative_bonus": 2,
        "death_threshold_mult": 1.0,
        "notes": "+1 a schivata/parata/blocco, +2 iniziativa, mai colto di sorpresa",
    },

    "Duro da Uccidere": {
        "type": "advantage",
        "cost": 2,                      # 2 pt per livello
        "skill_bonus": {},
        "effect_type_bonus": {},
        "dodge_bonus": 0,
        "death_threshold_mult": 2.0,    # soglia morte a −2×PF
        "notes": "Soglia morte raddoppiata: muore solo sotto −2×PF",
    },

    "Sensi Acuti": {
        "type": "advantage",
        "cost": 2,                      # 2 pt per livello
        "skill_bonus": {
            "osservare":     2,
            "investigare":   1,
            "pedinare":      1,
            "seguire_tracce": 1,
        },
        "effect_type_bonus": {"rilevare": 2, "investigare": 1},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "notes": "+2 a Percezione, osservare e seguire tracce",
    },

    "Forza Aumentata": {
        "type": "advantage",
        "cost": 10,
        "skill_bonus": {
            "combattere": 1,
            "lottare":    1,
            "forzare":    2,
            "lanciare":   1,
        },
        "effect_type_bonus": {"forzare": 1, "combattere": 1},
        "stat_bonus": {"forza": 1},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "notes": "+1 FO effettiva per i tiri fisici",
    },

    "Alta Tecnologia": {
        "type": "advantage",
        "cost": 5,
        "skill_bonus": {"tecnologia": 2, "ingegneria": 1, "elettronica": 1, "informatica": 1},
        "effect_type_bonus": {"decifrare": 1, "forzare": 1},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "notes": "+2 a tecnologia e ingegneria con strumenti avanzati",
    },

    "Ambidestrezza": {
        "type": "advantage",
        "cost": 5,
        "skill_bonus": {"combattere": 1, "manualita": 1, "lottare": 1},
        "effect_type_bonus": {"combattere": 1},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "notes": "Nessuna penalità per la mano non dominante in combattimento",
    },

    "Bellezza": {
        "type": "advantage",
        "cost": 4,                      # Attraente +4, Bella +12, Molto Bella +16
        "skill_bonus": {
            "persuadere":  1,
            "seduzione":   2,
            "intrattenere": 1,
        },
        "effect_type_bonus": {"negoziare": 1},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "reaction_modifier": 1,
        "notes": "+1 ai tiri di reazione, +1 skill sociali con chi è attratto",
    },

    "Empatia": {
        "type": "advantage",
        "cost": 15,
        "skill_bonus": {
            "intuire":    3,
            "calmare":    2,
            "persuadere": 1,
        },
        "effect_type_bonus": {"rilevare": 2},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "notes": "+3 a Psicologia, percepisce emozioni e bugie istintivamente",
    },

    "Memoria Fotografica": {
        "type": "advantage",
        "cost": 10,
        "skill_bonus": {
            "investigare": 2,
            "decifrare":   2,
            "cultura":     1,
            "storia":      2,
            "linguistica": 1,
        },
        "effect_type_bonus": {"investigare": 1, "decifrare": 1},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "notes": "Ricorda tutto ciò che ha visto con precisione fotografica",
    },

    "Coraggio": {
        "type": "advantage",
        "cost": 10,
        "skill_bonus": {},
        "effect_type_bonus": {},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "will_bonus": 2,
        "notes": "+2 ai tiri di Volontà contro paura e stress",
    },

    "Sangue Freddo": {
        "type": "advantage",
        "cost": 5,
        "skill_bonus": {
            "mira":       1,
            "strategia":  1,
            "analizzare": 1,
        },
        "effect_type_bonus": {},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "notes": "Nessuna penalità da shock nei tiri di mira; +1 a tattica sotto pressione",
    },

    "Istinto di Sopravvivenza": {
        "type": "advantage",
        "cost": 5,
        "skill_bonus": {
            "sopravvivere":        2,
            "seguire_tracce":      1,
            "sopravvivenza_urbana": 1,
        },
        "effect_type_bonus": {"recuperare": 1},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "notes": "+2 Sopravvivenza, adatto a qualsiasi ambiente",
    },

    "Fortuna": {
        "type": "advantage",
        "cost": 15,
        "skill_bonus": {},
        "effect_type_bonus": {},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "luck_rerolls": 1,
        "notes": "Una volta per sessione può ritirare un tiro fallito e prendere il migliore",
    },

    "Contatti": {
        "type": "advantage",
        "cost": 3,
        "skill_bonus": {
            "investigare": 1,
            "comunicare":  1,
        },
        "effect_type_bonus": {"negoziare": 1},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "reaction_modifier": 1,
        "notes": "Rete di informatori/alleati; +1 ai tiri di reazione con il gruppo di riferimento",
    },

    "Status Sociale": {
        "type": "advantage",
        "cost": 5,                      # 5 pt per livello
        "skill_bonus": {
            "etichetta":   2,
            "comandare":   1,
            "persuadere":  1,
            "economia":    1,
            "politica":    1,
        },
        "effect_type_bonus": {"negoziare": 1},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "reaction_modifier": 1,
        "notes": "+5 pt per ogni livello di status; +1 reazione in contesti sociali appropriati",
    },

    "Ricchezza": {
        "type": "advantage",
        "cost": 10,
        "skill_bonus": {"economia": 2},
        "effect_type_bonus": {"negoziare": 1},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "notes": "Risorse finanziarie significative; sblocca opzioni costose",
    },

    "Talento": {
        "type": "advantage",
        "cost": 5,                      # 5-10 pt per livello di talento
        "skill_bonus": {},              # applicato dinamicamente per gruppo di skill
        "effect_type_bonus": {},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "notes": "+1 a un gruppo di skill tematicamente correlate per livello",
    },

    "Voce Bella": {
        "type": "advantage",
        "cost": 10,
        "skill_bonus": {
            "intrattenere":        2,
            "persuadere":          1,
            "parlare_in_pubblico": 2,
            "recitazione":         1,
        },
        "effect_type_bonus": {"negoziare": 1},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "reaction_modifier": 1,
        "notes": "+2 a intrattenere/parlare in pubblico; +1 reazione da chi la sente parlare",
    },

    "Autorità": {
        "type": "advantage",
        "cost": 5,
        "skill_bonus": {
            "comandare":   2,
            "intimidire":  1,
            "politica":    1,
        },
        "effect_type_bonus": {},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "notes": "Potere legale o militare; gli NPC di rango inferiore obbediscono",
    },

    "Linguaggio Nativo Extra": {
        "type": "advantage",
        "cost": 3,
        "skill_bonus": {"linguistica": 2, "comunicare": 1},
        "effect_type_bonus": {},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "notes": "Parla fluentemente un'altra lingua come madrelingua",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # SVANTAGGI
    # ═══════════════════════════════════════════════════════════════════════════

    "Animo Sanguinario": {
        "type": "disadvantage",
        "cost": -10,
        "skill_bonus": {},
        "effect_type_bonus": {},
        "dodge_bonus": -1,
        "death_threshold_mult": 1.0,
        "morale_check": True,
        "notes": "Continua ad attaccare anche quando sarebbe saggio ritirarsi. Morale check per ogni tentativo di fuga.",
    },

    "Codardo": {
        "type": "disadvantage",
        "cost": -5,
        "skill_bonus": {},
        "effect_type_bonus": {},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "penalty_in_combat": -2,
        "notes": "−2 a tutti i tiri quando è in pericolo fisico diretto",
    },

    "Sospettoso": {
        "type": "disadvantage",
        "cost": -5,
        "skill_bonus": {
            "persuadere": -2,
            "calmare":    -2,
        },
        "effect_type_bonus": {"negoziare": -2},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "notes": "−2 alle skill sociali. Difficile da convincere.",
    },

    "Avidità": {
        "type": "disadvantage",
        "cost": -15,
        "skill_bonus": {},
        "effect_type_bonus": {},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "will_penalty": -3,
        "notes": "Deve fare un tiro di Volontà (−3) per resistere all'acquisizione di ricchezze",
    },

    "Senso del Dovere": {
        "type": "disadvantage",
        "cost": -5,
        "skill_bonus": {},
        "effect_type_bonus": {},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "notes": "Non abbandona mai i compagni; −2 ai tiri contro ordini che contraddicono il gruppo",
    },

    "Nemico": {
        "type": "disadvantage",
        "cost": -5,                     # varia: −5 a −30 pt
        "skill_bonus": {},
        "effect_type_bonus": {},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "notes": "Un nemico attivo interferisce regolarmente con la vita del personaggio",
    },

    "Segreto": {
        "type": "disadvantage",
        "cost": -10,
        "skill_bonus": {},
        "effect_type_bonus": {},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "notes": "Ha qualcosa da nascondere; se scoperto, conseguenze gravi",
    },

    "Dipendenza": {
        "type": "disadvantage",
        "cost": -5,                     # varia a seconda della sostanza e frequenza
        "skill_bonus": {},
        "effect_type_bonus": {},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "penalty_in_combat": -1,
        "notes": "Astinenza: −1 a tutti i tiri. Deve trovare e usare la sostanza regolarmente.",
    },

    "Fobia": {
        "type": "disadvantage",
        "cost": -10,
        "skill_bonus": {},
        "effect_type_bonus": {},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "will_penalty": -4,
        "notes": "Paura intensa di un oggetto/situazione specifica; −4 Volontà quando esposto",
    },

    "Impulsività": {
        "type": "disadvantage",
        "cost": -10,
        "skill_bonus": {},
        "effect_type_bonus": {},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "will_penalty": -2,
        "notes": "Agisce senza pensare; −2 Volontà per resistere all'impulso immediato",
    },

    "Arroganza": {
        "type": "disadvantage",
        "cost": -5,
        "skill_bonus": {
            "persuadere": -1,
            "calmare":    -1,
        },
        "effect_type_bonus": {"negoziare": -1},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "reaction_modifier": -1,
        "notes": "−1 ai tiri di reazione con chi non lo conosce; sfida il comando altrui",
    },

    "Lealtà": {
        "type": "disadvantage",
        "cost": -5,
        "skill_bonus": {},
        "effect_type_bonus": {},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "notes": "Non può agire contro i propri alleati anche quando sarebbe razionale farlo",
    },

    "Poca Autostima": {
        "type": "disadvantage",
        "cost": -10,
        "skill_bonus": {
            "persuadere":    -1,
            "ispirare":      -2,
            "comandare":     -2,
            "parlare_in_pubblico": -2,
        },
        "effect_type_bonus": {},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "will_penalty": -1,
        "notes": "−2 alle skill di leadership; −1 Volontà nei momenti critici",
    },

    "Amnesia": {
        "type": "disadvantage",
        "cost": -10,
        "skill_bonus": {
            "storia":    -2,
            "cultura":   -1,
            "linguistica": -1,
        },
        "effect_type_bonus": {},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "notes": "Non ricorda parte del proprio passato; penalità alle skill di conoscenza pregressa",
    },

    "Mancanza di Empatia": {
        "type": "disadvantage",
        "cost": -15,
        "skill_bonus": {
            "intuire":    -3,
            "calmare":    -2,
            "persuadere": -1,
        },
        "effect_type_bonus": {"rilevare": -2},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "notes": "Non comprende le emozioni altrui; −3 Psicologia, −2 skill sociali empatiche",
    },

    "Curiosità Morbosa": {
        "type": "disadvantage",
        "cost": -5,
        "skill_bonus": {},
        "effect_type_bonus": {},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "will_penalty": -2,
        "notes": "Deve fare un tiro Volontà (−2) per non indagare luoghi/oggetti pericolosi",
    },

    "Smemoratezza": {
        "type": "disadvantage",
        "cost": -5,
        "skill_bonus": {
            "investigare": -1,
            "decifrare":   -1,
        },
        "effect_type_bonus": {},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "notes": "Dimentica dettagli importanti; può fallire il richiamo di informazioni critiche",
    },

    "Pessimismo": {
        "type": "disadvantage",
        "cost": -5,
        "skill_bonus": {
            "ispirare":   -2,
            "comunicare": -1,
        },
        "effect_type_bonus": {},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "will_penalty": -1,
        "notes": "Si aspetta sempre il peggio; −2 Leadership, penalizza il morale del gruppo",
    },
}

# ── Helper ──────────────────────────────────────────────────────────────────

def advantage_breakdown(all_traits: list[str], skill: str, effect_type: str) -> list[dict]:
    """Restituisce la lista di {name, delta} per ogni tratto che contribuisce al tiro.

    Regola: skill_bonus[skill] e effect_type_bonus[effect_type] sono ALTERNATIVI sullo stesso
    tratto — si prende il maggiore in valore assoluto (skill_bonus è più specifico).
    penalty_in_combat si somma separatamente perché è un malus indipendente.
    """
    result = []
    for adv in all_traits:
        entry = ADVANTAGES.get(adv)
        if not entry:
            continue
        sb = entry.get("skill_bonus", {}).get(skill, 0)
        etb = entry.get("effect_type_bonus", {}).get(effect_type, 0)
        # Prendi il più grande in valore assoluto tra skill_bonus e effect_type_bonus
        trait_delta = sb if abs(sb) >= abs(etb) else etb
        combat_delta = entry.get("penalty_in_combat", 0)
        delta = trait_delta + combat_delta
        if delta != 0:
            result.append({"name": adv, "delta": delta})
    return result


def advantage_skill_bonus(advantages: list[str], skill: str) -> int:
    """Somma tutti i bonus/malus a una skill specifica dai vantaggi del personaggio."""
    total = 0
    for adv in advantages:
        entry = ADVANTAGES.get(adv)
        if entry:
            total += entry.get("skill_bonus", {}).get(skill, 0)
    return total


def advantage_effect_type_bonus(advantages: list[str], effect_type: str) -> int:
    """Somma tutti i bonus/malus a un effect_type dai vantaggi del personaggio."""
    total = 0
    for adv in advantages:
        entry = ADVANTAGES.get(adv)
        if entry:
            total += entry.get("effect_type_bonus", {}).get(effect_type, 0)
    return total


def advantage_dodge_bonus(advantages: list[str]) -> int:
    """Somma i bonus/malus alla schivata dai vantaggi del personaggio."""
    total = 0
    for adv in advantages:
        entry = ADVANTAGES.get(adv)
        if entry:
            total += entry.get("dodge_bonus", 0)
    return total


def advantage_death_threshold_mult(advantages: list[str]) -> float:
    """
    Restituisce il moltiplicatore più alto per la soglia di morte.
    Duro da Uccidere: ×2.0; default: ×1.0.
    Se ha entrambi prende il massimo (favorevole al giocatore).
    """
    mult = 1.0
    for adv in advantages:
        entry = ADVANTAGES.get(adv)
        if entry:
            mult = max(mult, entry.get("death_threshold_mult", 1.0))
    return mult


def has_morale_check(disadvantages: list[str]) -> bool:
    """True se il personaggio ha uno svantaggio che richiede morale check per ritirarsi."""
    return any(
        ADVANTAGES.get(d, {}).get("morale_check", False)
        for d in disadvantages
    )


def advantage_combat_penalty(disadvantages: list[str]) -> int:
    """Penalità in combattimento da svantaggi come Codardo."""
    total = 0
    for d in disadvantages:
        entry = ADVANTAGES.get(d)
        if entry:
            total += entry.get("penalty_in_combat", 0)
    return total


def advantage_reaction_modifier(advantages: list[str]) -> int:
    """Modificatore ai tiri di reazione NPC da vantaggi/svantaggi."""
    total = 0
    for adv in advantages:
        entry = ADVANTAGES.get(adv)
        if entry:
            total += entry.get("reaction_modifier", 0)
    return total


def advantage_will_modifier(traits: list[str]) -> int:
    """Modifica netta alla Volontà da vantaggi/svantaggi."""
    total = 0
    for trait in traits:
        entry = ADVANTAGES.get(trait)
        if entry:
            total += entry.get("will_bonus", 0)
            total += entry.get("will_penalty", 0)
    return total


def all_advantages() -> list[str]:
    return [k for k, v in ADVANTAGES.items() if v["type"] == "advantage"]


def all_disadvantages() -> list[str]:
    return [k for k, v in ADVANTAGES.items() if v["type"] == "disadvantage"]
