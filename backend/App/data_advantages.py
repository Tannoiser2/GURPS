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

import re

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
        "per_level": True,
        "skill_bonus": {},
        "effect_type_bonus": {},
        "dodge_bonus": 0,
        "death_threshold_mult": 2.0,    # soglia morte a −2×PF
        "death_check_bonus": 1,
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

    "Agilità del Gatto": {
        "type": "advantage",
        "cost": 10,
        "skill_bonus": {"acrobazia": 2, "saltare": 1},
        "effect_type_bonus": {"infiltrarsi": 1},
        "fall_reduction_m": 5,
        "notes": "Sottrae 5 metri dalle cadute; con tiro DE dimezza i danni da caduta.",
    },

    "Bilanciamento Perfetto": {
        "type": "advantage",
        "cost": 15,
        "skill_bonus": {"acrobazia": 1, "arrampicarsi": 1, "equilibrio": 6},
        "effect_type_bonus": {"infiltrarsi": 1},
        "balance_bonus": 6,
        "knockdown_bonus": 4,
        "notes": "+6 per restare in piedi su superfici difficili; +1 Acrobazia e Arrampicarsi.",
    },

    "Difesa Migliorata (Blocco)": {
        "type": "advantage",
        "cost": 5,
        "block_bonus": 1,
        "notes": "+1 ai tentativi di bloccare con Scudo.",
    },

    "Difesa Migliorata (Schivata)": {
        "type": "advantage",
        "cost": 15,
        "dodge_bonus": 1,
        "notes": "+1 al valore di Schivata.",
    },

    "Difesa Migliorata (Parata)": {
        "type": "advantage",
        "cost": 10,
        "parry_bonus": 1,
        "notes": "+1 ai tentativi di parata.",
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

    "Empatia con gli Animali": {
        "type": "advantage",
        "cost": 5,
        "skill_bonus": {"calmare": 2, "persuadere": 1, "intuire": 1, "cavalcare": 1},
        "effect_type_bonus": {"negoziare": 1, "rilevare": 1},
        "notes": "Capisce lo stato emotivo degli animali e può usare abilità di Influenza su di loro.",
    },

    "Flessuoso": {
        "type": "advantage",
        "cost": 5,
        "skill_bonus": {"arrampicarsi": 3, "acrobazia": 1, "meccanica": 1, "demolire": 1},
        "effect_type_bonus": {"infiltrarsi": 1, "forzare": 1},
        "tight_space_penalty_ignore": 3,
        "notes": "+3 ad Arrampicarsi e per liberarsi da legacci; ignora fino a -3 in spazi stretti.",
    },

    "Snodato": {
        "type": "advantage",
        "cost": 15,
        "skill_bonus": {"arrampicarsi": 5, "acrobazia": 2, "meccanica": 2, "demolire": 2},
        "effect_type_bonus": {"infiltrarsi": 2, "forzare": 1},
        "tight_space_penalty_ignore": 5,
        "notes": "+5 ad Arrampicarsi e per liberarsi; ignora fino a -5 in spazi stretti.",
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

    "Intrepido": {
        "type": "advantage",
        "cost": 2,
        "per_level": True,
        "will_bonus": 1,
        "fear_bonus": 1,
        "resist_intimidation_bonus": 1,
        "notes": "+1/livello a Volontà contro paura, Intimidire e poteri che inducono paura.",
    },

    "Elevata Soglia del Dolore": {
        "type": "advantage",
        "cost": 10,
        "no_shock": True,
        "knockdown_bonus": 3,
        "torture_resistance_bonus": 3,
        "notes": "Non subisce penalità da shock; +3 a SA per evitare stordimento/atterramento e resistere al dolore.",
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
        "notes": "Una volta per ora di gioco può ritirare una valutazione negativa due volte e tenere il migliore.",
    },

    "Fortuna Straordinaria": {
        "type": "advantage",
        "cost": 30,
        "skill_bonus": {},
        "effect_type_bonus": {},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "luck_rerolls": 1,
        "luck_cooldown_minutes": 30,
        "notes": "Come Fortuna, ma utilizzabile ogni 30 minuti di gioco.",
    },

    "Fortuna Smodata": {
        "type": "advantage",
        "cost": 60,
        "skill_bonus": {},
        "effect_type_bonus": {},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "luck_rerolls": 1,
        "luck_cooldown_minutes": 10,
        "notes": "Come Fortuna, ma utilizzabile ogni 10 minuti di gioco.",
    },

    "Spericolato": {
        "type": "advantage",
        "cost": 15,
        "reckless_bonus": 1,
        "reckless_crit_fail_reroll": True,
        "notes": "+1 alle abilità quando corre rischi non necessari; può ritirare fallimenti critici in tali azioni.",
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

    "Talento (Artificiere)": {
        "type": "advantage",
        "cost": 10,
        "per_level": True,
        "max_level": 4,
        "skill_bonus": {"ingegneria": 1, "meccanica": 1, "elettronica": 1, "tecnologia": 1, "informatica": 1},
        "effect_type_bonus": {"forzare": 1},
        "notes": "+1/livello alle abilità tecniche e di costruzione/riparazione.",
    },

    "Talento (Sopravvivenza)": {
        "type": "advantage",
        "cost": 10,
        "per_level": True,
        "max_level": 4,
        "skill_bonus": {"mimetizzare": 1, "navigare": 1, "sopravvivere": 1, "seguire_tracce": 1, "osservare": 1},
        "effect_type_bonus": {"recuperare": 1, "rilevare": 1},
        "notes": "+1/livello alle abilità di esplorazione, sopravvivenza e caccia.",
    },

    "Talento (Parlantina)": {
        "type": "advantage",
        "cost": 15,
        "per_level": True,
        "max_level": 4,
        "skill_bonus": {
            "persuadere": 1, "ingannare": 1, "intimidire": 1, "seduzione": 1,
            "recitazione": 1, "intrattenere": 1, "ispirare": 1, "parlare_in_pubblico": 1,
        },
        "effect_type_bonus": {"negoziare": 1, "ingannare": 1},
        "notes": "+1/livello alle abilità di Influenza, Recitazione, Socializzare, Leadership e Parlare in Pubblico.",
    },

    "Talento Linguistico": {
        "type": "advantage",
        "cost": 10,
        "skill_bonus": {"linguistica": 2, "comunicare": 1},
        "effect_type_bonus": {"decifrare": 1, "negoziare": 1},
        "notes": "Apprende le lingue a un livello di comprensione superiore; bonus a Linguistica e comunicazione.",
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

    "Resistente alle Malattie": {
        "type": "advantage",
        "cost": 3,
        "resistance_bonus": {"malattie": 3},
        "notes": "+3 alle valutazioni di SA per resistere alle malattie.",
    },

    "Resistente alle Malattie 8": {
        "type": "advantage",
        "cost": 5,
        "resistance_bonus": {"malattie": 8},
        "notes": "+8 alle valutazioni di SA per resistere alle malattie.",
    },

    "Resistente ai Veleni": {
        "type": "advantage",
        "cost": 5,
        "resistance_bonus": {"veleni": 3},
        "notes": "+3 alle valutazioni di SA per resistere ai veleni.",
    },

    "Udito Acuto": {
        "type": "advantage",
        "cost": 2,
        "per_level": True,
        "skill_bonus": {"osservare": 1},
        "effect_type_bonus": {"rilevare": 1},
        "sense_bonus": {"udito": 1},
        "notes": "+1/livello alle valutazioni sui sensi basate sull'udito.",
    },

    "Gusto e Odorato Acuti": {
        "type": "advantage",
        "cost": 2,
        "per_level": True,
        "skill_bonus": {"osservare": 1, "seguire_tracce": 1},
        "effect_type_bonus": {"rilevare": 1},
        "sense_bonus": {"gusto_odorato": 1},
        "notes": "+1/livello alle valutazioni sui sensi basate su gusto e odorato.",
    },

    "Tatto Acuto": {
        "type": "advantage",
        "cost": 2,
        "per_level": True,
        "skill_bonus": {"osservare": 1, "manualita": 1, "scassinare": 1},
        "effect_type_bonus": {"rilevare": 1},
        "sense_bonus": {"tatto": 1},
        "notes": "+1/livello alle valutazioni sui sensi basate sul tatto.",
    },

    "Vista Acuta": {
        "type": "advantage",
        "cost": 2,
        "per_level": True,
        "skill_bonus": {"osservare": 1, "mira": 1, "seguire_tracce": 1},
        "effect_type_bonus": {"rilevare": 1},
        "sense_bonus": {"vista": 1},
        "notes": "+1/livello alle valutazioni sui sensi basate sulla vista.",
    },

    "Visione Notturna": {
        "type": "advantage",
        "cost": 1,
        "per_level": True,
        "max_level": 9,
        "night_vision": 1,
        "notes": "Ignora -1/livello di penalità alla vista o al combattimento dovuta all'oscurità.",
    },

    "Viaggiatore (Tempo)": {
        "type": "advantage",
        "cost": 100,
        "travel_power": "tempo",
        "fp_cost": 1,
        "notes": "Può viaggiare nel tempo con concentrazione, tiro IN e costo minimo 1 PFatica.",
    },

    "Viaggiatore (Dimensioni)": {
        "type": "advantage",
        "cost": 100,
        "travel_power": "dimensioni",
        "fp_cost": 1,
        "notes": "Può viaggiare tra dimensioni/linee temporali con concentrazione, tiro IN e costo minimo 1 PFatica.",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # SVANTAGGI
    # ═══════════════════════════════════════════════════════════════════════════

    "Animo Sanguinario": {
        "type": "disadvantage",
        "cost": -10,
        "self_control": 12,
        "villainous": True,
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
        "self_control": 12,
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
        "self_control": 12,
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
        "self_control": 12,
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
        "self_control": 12,
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

    "Vista Imperfetta": {
        "type": "disadvantage",
        "cost": -10,
        "skill_bonus": {
            "osservare": -6,
            "mira": -2,
            "seguire_tracce": -2,
            "investigare": -2,
        },
        "effect_type_bonus": {"rilevare": -6},
        "dodge_bonus": 0,
        "death_threshold_mult": 1.0,
        "notes": "-6 alle valutazioni di Vista e -2 per colpire in combattimento se non corretta.",
    },

    "Codice d'Onore (Pirata)": {
        "type": "disadvantage",
        "cost": -5,
        "notes": "Vendica gli insulti, sostiene gli amici, non attacca i compagni se non in duello leale.",
    },

    "Codice d'Onore (Gentiluomo)": {
        "type": "disadvantage",
        "cost": -10,
        "reaction_modifier": 1,
        "notes": "Non infrange la parola, risponde agli insulti con scuse o duello e non cerca vantaggi sleali.",
    },

    "Codice d'Onore (Formale)": {
        "type": "disadvantage",
        "cost": -15,
        "reaction_modifier": 1,
        "notes": "Segue sempre un codice formale rigido; romperlo puo richiedere riparazione estrema o sacrificio.",
    },

    "Curiosità": {
        "type": "disadvantage",
        "cost": -5,
        "self_control": 12,
        "will_penalty": -2,
        "notes": "Deve resistere per non esaminare oggetti o situazioni interessanti anche quando sono pericolosi.",
    },

    "Gelosia": {
        "type": "disadvantage",
        "cost": -10,
        "skill_bonus": {"persuadere": -1, "calmare": -1, "comunicare": -1},
        "effect_type_bonus": {"negoziare": -1},
        "reaction_modifier": -2,
        "notes": "Reagisce male a rivali piu capaci, attraenti o al centro dell'attenzione.",
    },

    "Ghiottoneria": {
        "type": "disadvantage",
        "cost": -5,
        "self_control": 12,
        "notes": "Deve resistere per non indulgere in cibo o bevande desiderabili anche quando sarebbe imprudente.",
    },

    "Illusione Minore": {
        "type": "disadvantage",
        "cost": -5,
        "reaction_modifier": -1,
        "notes": "Crede in qualcosa di falso che influenza il comportamento; gli altri reagiscono a -1.",
    },

    "Illusione Maggiore": {
        "type": "disadvantage",
        "cost": -10,
        "reaction_modifier": -2,
        "skill_bonus": {"investigare": -1, "intuire": -1},
        "notes": "Falsa convinzione che condiziona notevolmente le scelte; gli altri reagiscono a -2.",
    },

    "Illusione Severa": {
        "type": "disadvantage",
        "cost": -15,
        "reaction_modifier": -3,
        "skill_bonus": {"investigare": -2, "intuire": -2, "comunicare": -1},
        "notes": "Falsa convinzione grave che compromette l'efficienza quotidiana; gli altri reagiscono a -3.",
    },

    "Fobia (Sangue)": {
        "type": "disadvantage",
        "cost": -10,
        "self_control": 12,
        "will_penalty": -4,
        "skill_bonus": {"medicina": -2, "curare": -2, "combattere": -1},
        "notes": "Paura del sangue; quando presente subisce penalita e puo andare in panico.",
    },

    "Fobia (Buio)": {
        "type": "disadvantage",
        "cost": -15,
        "self_control": 12,
        "will_penalty": -4,
        "skill_bonus": {"osservare": -2, "furtivita": -1, "combattere": -1},
        "notes": "Paura del buio; in oscurita deve resistere o agire in panico.",
    },

    "Fobia (Altezza)": {
        "type": "disadvantage",
        "cost": -10,
        "self_control": 12,
        "will_penalty": -4,
        "skill_bonus": {"arrampicarsi": -2, "acrobazia": -2, "equilibrio": -2},
        "notes": "Paura delle altezze; su precipizi o luoghi elevati subisce penalita e puo bloccarsi.",
    },

    "Fobia (Ragni)": {
        "type": "disadvantage",
        "cost": -5,
        "self_control": 12,
        "will_penalty": -4,
        "notes": "Paura dei ragni; quando presenti richiede autocontrollo.",
    },

    "Intolleranza Totale": {
        "type": "disadvantage",
        "cost": -10,
        "reaction_modifier": -3,
        "skill_bonus": {"persuadere": -2, "calmare": -2, "comunicare": -2},
        "effect_type_bonus": {"negoziare": -2},
        "notes": "Pregiudizio totale verso chi non appartiene al proprio gruppo; reazioni e socialita peggiorano.",
    },

    "Intolleranza Specifica": {
        "type": "disadvantage",
        "cost": -5,
        "reaction_modifier": -2,
        "skill_bonus": {"persuadere": -1, "calmare": -1, "comunicare": -1},
        "effect_type_bonus": {"negoziare": -1},
        "notes": "Pregiudizio verso un gruppo specifico; applica penalita quando quel gruppo e coinvolto.",
    },

    "Irascibile": {
        "type": "disadvantage",
        "cost": -10,
        "self_control": 12,
        "will_penalty": -2,
        "skill_bonus": {"persuadere": -1, "calmare": -1},
        "effect_type_bonus": {"negoziare": -1},
        "notes": "In situazioni stressanti deve resistere per non insultare, attaccare o perdere il controllo.",
    },

    "Libidine": {
        "type": "disadvantage",
        "cost": -15,
        "self_control": 12,
        "will_penalty": -2,
        "skill_bonus": {"seduzione": 1, "persuadere": -1},
        "notes": "Forte desiderio di avventure passionali; deve resistere quando incontra qualcuno da cui e attratto.",
    },

    "Onestà": {
        "type": "disadvantage",
        "cost": -10,
        "self_control": 12,
        "skill_bonus": {"ingannare": -2, "scassinare": -1, "borseggiare": -2},
        "effect_type_bonus": {"ingannare": -2},
        "notes": "Obbedisce alla legge e tende a farla rispettare; deve resistere per infrangerla.",
    },

    "Ossessione Breve": {
        "type": "disadvantage",
        "cost": -5,
        "self_control": 12,
        "will_penalty": -1,
        "notes": "Obiettivo ossessivo a breve termine; deve resistere per cambiare linea di condotta.",
    },

    "Ossessione Lunga": {
        "type": "disadvantage",
        "cost": -10,
        "self_control": 12,
        "will_penalty": -2,
        "notes": "Obiettivo ossessivo di lungo periodo; influenza molte decisioni e priorita.",
    },

    "Pacifismo (Riluttante a Uccidere)": {
        "type": "disadvantage",
        "cost": -5,
        "skill_bonus": {"combattere": -4, "mira": -4, "lanciare": -4},
        "effect_type_bonus": {"combattere": -4},
        "notes": "-4 per colpire persone con attacchi mortali; -2 se non vede il volto.",
    },

    "Pacifismo (Incapace di Fare del Male a Innocenti)": {
        "type": "disadvantage",
        "cost": -10,
        "skill_bonus": {"combattere": -2, "mira": -2, "intimidire": -1},
        "effect_type_bonus": {"combattere": -2},
        "notes": "Usa forza letale solo contro nemici che stanno per causare danni seri.",
    },

    "Presunzione": {
        "type": "disadvantage",
        "cost": -5,
        "self_control": 12,
        "reaction_modifier": -2,
        "will_penalty": -1,
        "notes": "Si crede piu capace di quanto sia; deve resistere per agire con cautela ragionevole.",
    },

    "Senso del Dovere (Individuo)": {"type": "disadvantage", "cost": -2, "notes": "Non tradisce o abbandona mai una persona specifica."},
    "Senso del Dovere (Squadra)": {"type": "disadvantage", "cost": -5, "notes": "Non abbandona i compagni d'avventura o la propria squadra."},
    "Senso del Dovere (Nazione)": {"type": "disadvantage", "cost": -10, "notes": "Si sente obbligato verso una nazione, religione o gruppo ampio."},
    "Senso del Dovere (Razza)": {"type": "disadvantage", "cost": -15, "notes": "Si sente obbligato verso un'intera razza o specie."},
    "Senso del Dovere (Ogni Vivente)": {"type": "disadvantage", "cost": -20, "notes": "Si sente obbligato verso qualsiasi essere vivente."},

    "Sfortuna": {
        "type": "disadvantage",
        "cost": -10,
        "unluckiness": True,
        "notes": "Una volta per sessione il GM puo far andare male qualcosa nel momento peggiore, senza morte improvvisa.",
    },

    "Sincerità": {
        "type": "disadvantage",
        "cost": -5,
        "self_control": 12,
        "skill_bonus": {"ingannare": -5, "recitazione": -5, "persuadere": -5},
        "effect_type_bonus": {"ingannare": -5},
        "notes": "Detesta mentire; deve resistere per omettere verita scomode o dire falsita.",
    },

    "Sordità Parziale": {
        "type": "disadvantage",
        "cost": -10,
        "skill_bonus": {"osservare": -4, "comunicare": -2, "interrogare": -2},
        "effect_type_bonus": {"rilevare": -4, "negoziare": -1},
        "hearing_penalty": -4,
        "notes": "-4 alle valutazioni sull'udito e penalita quando comprendere qualcuno e importante.",
    },

    "Vista Imperfetta Non Correggibile": {
        "type": "disadvantage",
        "cost": -25,
        "skill_bonus": {"osservare": -6, "mira": -2, "seguire_tracce": -2, "investigare": -2},
        "effect_type_bonus": {"rilevare": -6},
        "notes": "-6 alle valutazioni di Vista e -2 per colpire; non correggibile al LT corrente.",
    },

    "Voto Minore": {"type": "disadvantage", "cost": -5, "notes": "Giuramento con inconvenienti moderati."},
    "Voto Maggiore": {"type": "disadvantage", "cost": -10, "notes": "Giuramento con forti limitazioni pratiche."},
    "Voto Superiore": {"type": "disadvantage", "cost": -15, "notes": "Giuramento molto gravoso e vincolante."},
}

# Alias case-insensitive + nomi alternativi comuni → chiave canonica in ADVANTAGES
_TRAIT_ALIASES: dict[str, str] = {
    "forza bruta":           "Forza Aumentata",
    "riflessi veloci":       "Riflessi da Combattimento",
    "vista acuta":           "Sensi Acuti",
    "udito acuto":           "Sensi Acuti",
    "istinto":               "Riflessi da Combattimento",
    "sangue freddo":         "Sangue Freddo",
    "duro da uccidere":      "Duro da Uccidere",
    "tiro fortunato":        "Tiro Fortunato",
    "memoria fotografica":   "Memoria Fotografica",
    "ambidestria":           "Ambidestria",
    "fobia":                 "Fobia",
    "dipendenza":            "Dipendenza",
    "avarizia":              "Avarizia",
    "codardìa":              "Codardo",
    "impulsivita":           "Impulsività",
    "curiosita morbosa":     "Curiosità Morbosa",
}

# Indice lowercase di tutte le chiavi per lookup case-insensitive
_ADVANTAGES_LC: dict[str, str] = {k.lower(): k for k in ADVANTAGES}

# ── Helper ──────────────────────────────────────────────────────────────────

def _canonical_trait_key(raw: str) -> str | None:
    """Restituisce la chiave canonica in ADVANTAGES, o None se non trovata.
    Prova: match esatto → alias → case-insensitive."""
    if raw in ADVANTAGES:
        return raw
    alias = _TRAIT_ALIASES.get(raw.lower())
    if alias and alias in ADVANTAGES:
        return alias
    return _ADVANTAGES_LC.get(raw.lower())


def _trait_entry_and_level(trait: str) -> tuple[str, dict | None, int]:
    """Riconosce 'Vantaggio 3' come base 'Vantaggio', livello 3.

    Mantiene compatibilita con le chiavi esatte gia esistenti: se la stringa
    completa e nel catalogo, vince quella. Supporta case-insensitive e alias.
    """
    raw = str(trait or "").strip()
    canon = _canonical_trait_key(raw)
    if canon:
        return canon, ADVANTAGES[canon], 1
    match = re.match(r"^(.*?)[ ]+([1-9][0-9]*)$", raw)
    if match:
        base = match.group(1).strip()
        level = int(match.group(2))
        canon_base = _canonical_trait_key(base)
        if canon_base:
            entry = ADVANTAGES[canon_base]
            max_level = int(entry.get("max_level", level) or level)
            return canon_base, entry, max(1, min(level, max_level))
    return raw, None, 1


def _scaled_number(entry: dict, field: str, level: int, default=0):
    value = entry.get(field, default)
    if entry.get("per_level") and isinstance(value, (int, float)):
        return value * level
    return value


def _scaled_map(entry: dict, field: str, level: int) -> dict:
    values = entry.get(field, {}) or {}
    if not isinstance(values, dict):
        return {}
    if entry.get("per_level"):
        return {k: v * level for k, v in values.items()}
    return dict(values)


def trait_cost(trait: str) -> int:
    """Costo effettivo di un tratto, includendo eventuale livello nel nome."""
    _, entry, level = _trait_entry_and_level(trait)
    if not entry:
        return 0
    cost = int(entry.get("cost", 0) or 0)
    return cost * level if entry.get("per_level") else cost


def advantage_breakdown(all_traits: list[str], skill: str, effect_type: str) -> list[dict]:
    """Restituisce la lista di {name, delta} per ogni tratto che contribuisce al tiro.

    Regola: skill_bonus[skill] e effect_type_bonus[effect_type] sono ALTERNATIVI sullo stesso
    tratto — si prende il maggiore in valore assoluto (skill_bonus è più specifico).
    penalty_in_combat si somma separatamente perché è un malus indipendente.
    """
    result = []
    for raw_trait in all_traits:
        base_name, entry, level = _trait_entry_and_level(raw_trait)
        if not entry:
            continue
        sb = _scaled_map(entry, "skill_bonus", level).get(skill, 0)
        etb = _scaled_map(entry, "effect_type_bonus", level).get(effect_type, 0)
        # Prendi il più grande in valore assoluto tra skill_bonus e effect_type_bonus
        trait_delta = sb if abs(sb) >= abs(etb) else etb
        combat_delta = _scaled_number(entry, "penalty_in_combat", level, 0)
        delta = trait_delta + combat_delta
        if delta != 0:
            display = raw_trait if raw_trait != base_name or level == 1 else f"{base_name} {level}"
            result.append({"name": display, "delta": delta})
    return result


def advantage_skill_bonus(advantages: list[str], skill: str) -> int:
    """Somma tutti i bonus/malus a una skill specifica dai vantaggi del personaggio."""
    total = 0
    for adv in advantages:
        _, entry, level = _trait_entry_and_level(adv)
        if entry:
            total += _scaled_map(entry, "skill_bonus", level).get(skill, 0)
    return total


def advantage_effect_type_bonus(advantages: list[str], effect_type: str) -> int:
    """Somma tutti i bonus/malus a un effect_type dai vantaggi del personaggio."""
    total = 0
    for adv in advantages:
        _, entry, level = _trait_entry_and_level(adv)
        if entry:
            total += _scaled_map(entry, "effect_type_bonus", level).get(effect_type, 0)
    return total


def advantage_dodge_bonus(advantages: list[str]) -> int:
    """Somma i bonus/malus alla schivata dai vantaggi del personaggio."""
    total = 0
    for adv in advantages:
        _, entry, level = _trait_entry_and_level(adv)
        if entry:
            total += int(_scaled_number(entry, "dodge_bonus", level, 0) or 0)
    return total


def advantage_death_threshold_mult(advantages: list[str]) -> float:
    """
    Restituisce il moltiplicatore più alto per la soglia di morte.
    Duro da Uccidere: ×2.0; default: ×1.0.
    Se ha entrambi prende il massimo (favorevole al giocatore).
    """
    mult = 1.0
    for adv in advantages:
        _, entry, level = _trait_entry_and_level(adv)
        if entry:
            mult = max(mult, entry.get("death_threshold_mult", 1.0))
    return mult


def has_morale_check(disadvantages: list[str]) -> bool:
    """True se il personaggio ha uno svantaggio che richiede morale check per ritirarsi."""
    return any(
        (_trait_entry_and_level(d)[1] or {}).get("morale_check", False)
        for d in disadvantages
    )


def advantage_combat_penalty(disadvantages: list[str]) -> int:
    """Penalità in combattimento da svantaggi come Codardo."""
    total = 0
    for d in disadvantages:
        _, entry, level = _trait_entry_and_level(d)
        if entry:
            total += int(_scaled_number(entry, "penalty_in_combat", level, 0) or 0)
    return total


def advantage_reaction_modifier(advantages: list[str]) -> int:
    """Modificatore ai tiri di reazione NPC da vantaggi/svantaggi."""
    total = 0
    for adv in advantages:
        _, entry, level = _trait_entry_and_level(adv)
        if entry:
            total += int(_scaled_number(entry, "reaction_modifier", level, 0) or 0)
    return total


def advantage_will_modifier(traits: list[str]) -> int:
    """Modifica netta alla Volontà da vantaggi/svantaggi."""
    total = 0
    for trait in traits:
        _, entry, level = _trait_entry_and_level(trait)
        if entry:
            total += int(_scaled_number(entry, "will_bonus", level, 0) or 0)
            total += int(_scaled_number(entry, "will_penalty", level, 0) or 0)
    return total


def advantage_luck_rerolls(traits: list[str]) -> int:
    """Numero di ritiri concessi da Fortuna o tratti simili."""
    total = 0
    for trait in traits:
        _, entry, level = _trait_entry_and_level(trait)
        if entry:
            total += int(_scaled_number(entry, "luck_rerolls", level, 0) or 0)
    return total


def advantage_per_modifier(traits: list[str]) -> int:
    """Bonus ai tiri di Percezione/sensi generici."""
    total = 0
    for trait in traits:
        _, entry, level = _trait_entry_and_level(trait)
        if entry:
            total += sum(int(v) for v in _scaled_map(entry, "sense_bonus", level).values())
    return total


def advantage_night_vision(traits: list[str]) -> int:
    """Livelli di penalita da oscurita ignorati."""
    total = 0
    for trait in traits:
        _, entry, level = _trait_entry_and_level(trait)
        if entry:
            total += int(_scaled_number(entry, "night_vision", level, 0) or 0)
    return total


def advantage_ignores_shock(traits: list[str]) -> bool:
    return any(bool((_trait_entry_and_level(t)[1] or {}).get("no_shock")) for t in traits)


def advantage_reckless_bonus(traits: list[str]) -> int:
    total = 0
    for trait in traits:
        _, entry, level = _trait_entry_and_level(trait)
        if entry:
            total += int(_scaled_number(entry, "reckless_bonus", level, 0) or 0)
    return total


def trait_self_control_target(trait: str) -> int | None:
    """Target del tiro di autocontrollo, se lo svantaggio lo prevede."""
    _, entry, _ = _trait_entry_and_level(trait)
    if not entry:
        return None
    value = entry.get("self_control")
    return int(value) if isinstance(value, int) else None


def traits_requiring_self_control(traits: list[str]) -> list[dict]:
    """Lista degli svantaggi che possono richiedere autocontrollo."""
    result = []
    for trait in traits:
        target = trait_self_control_target(trait)
        if target is not None:
            result.append({"name": trait, "target": target})
    return result


def trait_story_notes(traits: list[str], limit: int = 4) -> list[str]:
    """Note brevi per far pesare vantaggi/svantaggi anche nella narrazione AI."""
    notes = []
    for trait in traits:
        base_name, entry, level = _trait_entry_and_level(trait)
        if not entry:
            continue
        note = entry.get("notes", "")
        if note:
            name = trait if trait != base_name or level == 1 else f"{base_name} {level}"
            notes.append(f"{name}: {note}")
        if len(notes) >= limit:
            break
    return notes


def all_advantages() -> list[str]:
    return [k for k, v in ADVANTAGES.items() if v["type"] == "advantage"]


def all_disadvantages() -> list[str]:
    return [k for k, v in ADVANTAGES.items() if v["type"] == "disadvantage"]
