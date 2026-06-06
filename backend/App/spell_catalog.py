"""
Catalogo incantesimi GURPS 4ª ed. Basic Set (Character p.234-253).

Ogni voce segue SpellDefinition in models.py:
  id              str   — slug univoco
  name            str   — nome italiano
  college         str   — college GURPS (Air, Fire, Healing, ecc.)
  energy_cost     int   — FP minimi per lanciare
  energy_cost_max int   — FP massimi (0 = fisso)
  maintenance_cost int  — FP/turno per mantenere (0 = non mantenibile)
  casting_time    int   — turni di Concentrate (1 = standard)
  effect_type     str   — "damage"|"heal"|"condition"|"buff"|"utility"|"summon"
  damage          str   — formula dado (es. "1d per energy") se damage
  damage_type     str   — tipo danno se damage
  heal_formula    str   — formula guarigione se heal
  area            int   — raggio yard (0 = singolo bersaglio)
  duration        str   — durata effetto
  resisted_by     str   — "" | "Volontà" | "SA" | "IN"
  condition_applied str — condizione applicata al bersaglio
  prerequisites   list  — spell_id richiesti (skill ≥ 12)
  min_skill       int   — livello minimo per poter lanciare
  eras            list  — [] = tutti i mondi magici
  description     str
  notes           str
"""

from __future__ import annotations
from typing import Optional

# ── Generi per tipo di potere ─────────────────────────────────────────────────
MAGIC_GENRES   = {"fantasy", "medievale", "storico", "horror", "steampunk"}
PSIONIC_GENRES = {"sci_fi", "horror"}          # horror accetta sia magia che psionico
ALL_POWER_GENRES = MAGIC_GENRES | PSIONIC_GENRES

# ── Catalogo ──────────────────────────────────────────────────────────────────

SPELL_TABLE: list[dict] = [

    # ═══════════════════════════════════════════════════════════════════════════
    # COLLEGE: HEALING (Guarigione) — Character p.247
    # ═══════════════════════════════════════════════════════════════════════════

    {
        "id": "minor_healing",
        "name": "Guarigione minore",
        "college": "Healing",
        "energy_cost": 1, "energy_cost_max": 3,
        "maintenance_cost": 0, "casting_time": 1,
        "effect_type": "heal",
        "heal_formula": "1d per energy",
        "duration": "permanente",
        "resisted_by": "",
        "prerequisites": [],
        "min_skill": 12,
        "description": "Ripristina PF al bersaglio (max PF originali). 1-3 energia = 1d-3d PF.",
        "notes": "Non può portare oltre i PF massimi. Non guarisce danni da veleno/malattia.",
    },
    {
        "id": "major_healing",
        "name": "Guarigione maggiore",
        "college": "Healing",
        "energy_cost": 5, "energy_cost_max": 0,
        "maintenance_cost": 0, "casting_time": 1,
        "effect_type": "heal",
        "heal_formula": "3d",
        "duration": "permanente",
        "resisted_by": "",
        "prerequisites": ["minor_healing"],
        "min_skill": 15,
        "description": "Guarisce 3d PF. Può ripristinare arti storpiati se lanciato entro 1 ora.",
        "notes": "Richiede Minor Healing a skill ≥ 12.",
    },
    {
        "id": "cure_disease",
        "name": "Cura malattia",
        "college": "Healing",
        "energy_cost": 4, "energy_cost_max": 0,
        "maintenance_cost": 0, "casting_time": 10,
        "effect_type": "condition",
        "condition_applied": "",  # rimuove condizione disease
        "duration": "permanente",
        "resisted_by": "",
        "prerequisites": ["minor_healing"],
        "min_skill": 12,
        "description": "Rimuove una malattia dal bersaglio. Casting time 10 turni.",
    },
    {
        "id": "cure_poison",
        "name": "Cura veleno",
        "college": "Healing",
        "energy_cost": 3, "energy_cost_max": 0,
        "maintenance_cost": 0, "casting_time": 1,
        "effect_type": "condition",
        "condition_applied": "",  # rimuove condizione poison
        "duration": "permanente",
        "resisted_by": "",
        "prerequisites": ["minor_healing"],
        "min_skill": 12,
        "description": "Neutralizza un veleno attivo nel bersaglio.",
    },
    {
        "id": "awaken",
        "name": "Risveglio",
        "college": "Healing",
        "energy_cost": 1, "energy_cost_max": 0,
        "maintenance_cost": 0, "casting_time": 1,
        "effect_type": "condition",
        "duration": "istantaneo",
        "resisted_by": "",
        "prerequisites": [],
        "min_skill": 10,
        "description": "Sveglia immediatamente un bersaglio incosciente (non morto).",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # COLLEGE: FIRE (Fuoco) — Character p.243
    # ═══════════════════════════════════════════════════════════════════════════

    {
        "id": "ignite_fire",
        "name": "Accendi fuoco",
        "college": "Fire",
        "energy_cost": 1, "energy_cost_max": 0,
        "maintenance_cost": 0, "casting_time": 1,
        "effect_type": "utility",
        "duration": "permanente",
        "resisted_by": "",
        "prerequisites": [],
        "min_skill": 10,
        "description": "Accende materiale infiammabile a contatto (candela, torcia, legna).",
    },
    {
        "id": "create_fire",
        "name": "Crea fuoco",
        "college": "Fire",
        "energy_cost": 2, "energy_cost_max": 0,
        "maintenance_cost": 1, "casting_time": 1,
        "effect_type": "utility",
        "area": 1,
        "duration": "mantenuto",
        "resisted_by": "",
        "prerequisites": ["ignite_fire"],
        "min_skill": 12,
        "description": "Crea un falò (raggio 1 yard) che illumina 4 yard. Mantenimento 1 FP/minuto.",
    },
    {
        "id": "fireball",
        "name": "Palla di fuoco",
        "college": "Fire",
        "energy_cost": 1, "energy_cost_max": 6,
        "maintenance_cost": 0, "casting_time": 1,
        "effect_type": "damage",
        "damage": "1d per energy",
        "damage_type": "burn",
        "area": 0,
        "duration": "istantaneo",
        "resisted_by": "",
        "prerequisites": ["create_fire"],
        "min_skill": 12,
        "description": "Sfera di fuoco scagliata come proiettile. 1-6 energia = 1d-6d danno burn.",
        "notes": "Range: skill/2 yard. Acc 0. Colpisce come attacco ranged.",
    },
    {
        "id": "explosive_fireball",
        "name": "Palla di fuoco esplosiva",
        "college": "Fire",
        "energy_cost": 2, "energy_cost_max": 10,
        "maintenance_cost": 0, "casting_time": 1,
        "effect_type": "damage",
        "damage": "1d per 2 energy",
        "damage_type": "burn",
        "area": 2,
        "duration": "istantaneo",
        "resisted_by": "",
        "prerequisites": ["fireball"],
        "min_skill": 15,
        "description": "Esplosione di fuoco in raggio 2 yard. Dimezza danno per yard di distanza dall'impatto.",
    },
    {
        "id": "resist_fire",
        "name": "Resistenza al fuoco",
        "college": "Fire",
        "energy_cost": 2, "energy_cost_max": 0,
        "maintenance_cost": 1, "casting_time": 1,
        "effect_type": "buff",
        "duration": "mantenuto",
        "resisted_by": "",
        "prerequisites": ["ignite_fire"],
        "min_skill": 12,
        "description": "Concede DR 5 vs danno fuoco per la durata. Non protegge da fuoco magico.",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # COLLEGE: EARTH (Terra) — Character p.242
    # ═══════════════════════════════════════════════════════════════════════════

    {
        "id": "sense_earth",
        "name": "Percepire la terra",
        "college": "Earth",
        "energy_cost": 2, "energy_cost_max": 0,
        "maintenance_cost": 1, "casting_time": 1,
        "effect_type": "utility",
        "duration": "mantenuto",
        "resisted_by": "",
        "prerequisites": [],
        "min_skill": 10,
        "description": "Percepisce composizione e struttura del terreno entro 10 yard.",
    },
    {
        "id": "shape_earth",
        "name": "Modella terra",
        "college": "Earth",
        "energy_cost": 3, "energy_cost_max": 0,
        "maintenance_cost": 0, "casting_time": 2,
        "effect_type": "utility",
        "duration": "permanente",
        "resisted_by": "",
        "prerequisites": ["sense_earth"],
        "min_skill": 12,
        "description": "Sposta fino a 0.1 m³ di terra/pietra. Può creare trincee, sigillare porte di pietra.",
    },
    {
        "id": "stone_missile",
        "name": "Proiettile di pietra",
        "college": "Earth",
        "energy_cost": 2, "energy_cost_max": 4,
        "maintenance_cost": 0, "casting_time": 1,
        "effect_type": "damage",
        "damage": "2d per 2 energy",
        "damage_type": "cr",
        "duration": "istantaneo",
        "resisted_by": "",
        "prerequisites": ["shape_earth"],
        "min_skill": 12,
        "description": "Scaglia un masso. 2/4 energia = 2d/4d danno cr.",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # COLLEGE: AIR (Aria) — Character p.238
    # ═══════════════════════════════════════════════════════════════════════════

    {
        "id": "create_air",
        "name": "Crea aria",
        "college": "Air",
        "energy_cost": 1, "energy_cost_max": 0,
        "maintenance_cost": 0, "casting_time": 1,
        "effect_type": "utility",
        "duration": "permanente",
        "resisted_by": "",
        "prerequisites": [],
        "min_skill": 10,
        "description": "Crea un getto d'aria respirabile sufficiente per 1 persona per 1 minuto.",
    },
    {
        "id": "windstorm",
        "name": "Tempesta di vento",
        "college": "Air",
        "energy_cost": 4, "energy_cost_max": 0,
        "maintenance_cost": 2, "casting_time": 2,
        "effect_type": "condition",
        "area": 4,
        "duration": "mantenuto",
        "resisted_by": "FO",
        "prerequisites": ["create_air"],
        "min_skill": 14,
        "description": "Vento forte (4 yard raggio). I bersagli devono passare tiro FO o cadono prone. Penalità -4 a tiri ranged nell'area.",
    },
    {
        "id": "lightning",
        "name": "Fulmine",
        "college": "Air",
        "energy_cost": 2, "energy_cost_max": 8,
        "maintenance_cost": 0, "casting_time": 1,
        "effect_type": "damage",
        "damage": "1d per energy",
        "damage_type": "burn",
        "duration": "istantaneo",
        "resisted_by": "",
        "prerequisites": ["create_air"],
        "min_skill": 15,
        "description": "Fulmine 2-8 energia = 2d-8d danno burn. Range: skill yard. Ignore DR di armature metalliche.",
        "notes": "Armature metalliche ignorano solo la loro DR vs questo attacco.",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # COLLEGE: MIND CONTROL (Controllo Mentale) — Character p.249
    # ═══════════════════════════════════════════════════════════════════════════

    {
        "id": "fear",
        "name": "Paura",
        "college": "Mind Control",
        "energy_cost": 2, "energy_cost_max": 0,
        "maintenance_cost": 0, "casting_time": 1,
        "effect_type": "condition",
        "duration": "istantaneo",
        "resisted_by": "Volontà",
        "condition_applied": "frightened",
        "prerequisites": [],
        "min_skill": 12,
        "description": "Quick Contest vs Volontà. Se perde: Fright Check immediato (Campaigns p.360).",
    },
    {
        "id": "sleep",
        "name": "Sonno",
        "college": "Mind Control",
        "energy_cost": 4, "energy_cost_max": 0,
        "maintenance_cost": 1, "casting_time": 1,
        "effect_type": "condition",
        "duration": "mantenuto",
        "resisted_by": "SA",
        "condition_applied": "unconscious",
        "prerequisites": ["fear"],
        "min_skill": 12,
        "description": "Quick Contest vs SA. Bersaglio cade addormentato. Non funziona su non-viventi.",
    },
    {
        "id": "daze",
        "name": "Confusione",
        "college": "Mind Control",
        "energy_cost": 2, "energy_cost_max": 0,
        "maintenance_cost": 1, "casting_time": 1,
        "effect_type": "condition",
        "duration": "mantenuto",
        "resisted_by": "Volontà",
        "condition_applied": "stunned",
        "prerequisites": [],
        "min_skill": 10,
        "description": "Quick Contest vs Volontà. Bersaglio stordito: -4 IQ, -2 DX, non può usare skill complesse.",
    },
    {
        "id": "suggest",
        "name": "Suggestione",
        "college": "Mind Control",
        "energy_cost": 3, "energy_cost_max": 0,
        "maintenance_cost": 2, "casting_time": 1,
        "effect_type": "utility",
        "duration": "mantenuto",
        "resisted_by": "Volontà",
        "prerequisites": ["daze"],
        "min_skill": 14,
        "description": "Quick Contest vs Volontà. Il bersaglio esegue un'azione ragionevole suggerita dal mago.",
        "notes": "Non funziona per azioni contro la natura del bersaglio (es. attaccare amici).",
    },
    {
        "id": "mind_reading",
        "name": "Lettura del pensiero",
        "college": "Mind Control",
        "energy_cost": 3, "energy_cost_max": 0,
        "maintenance_cost": 2, "casting_time": 1,
        "effect_type": "utility",
        "duration": "mantenuto",
        "resisted_by": "Volontà",
        "prerequisites": ["suggest"],
        "min_skill": 15,
        "description": "Quick Contest vs Volontà. Il mago legge i pensieri superficiali del bersaglio.",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # COLLEGE: PROTECTION (Protezione) — Character p.250
    # ═══════════════════════════════════════════════════════════════════════════

    {
        "id": "shield",
        "name": "Scudo magico",
        "college": "Protection",
        "energy_cost": 2, "energy_cost_max": 0,
        "maintenance_cost": 2, "casting_time": 1,
        "effect_type": "buff",
        "duration": "mantenuto",
        "resisted_by": "",
        "prerequisites": [],
        "min_skill": 12,
        "description": "Aggiunge DB 2 alla difesa del bersaglio (come uno scudo medio) per la durata.",
        "notes": "Non si cumula con scudo fisico. Funziona contro attacchi fisici e magici.",
    },
    {
        "id": "armor",
        "name": "Armatura magica",
        "college": "Protection",
        "energy_cost": 1, "energy_cost_max": 5,
        "maintenance_cost": 1, "casting_time": 1,
        "effect_type": "buff",
        "duration": "mantenuto",
        "resisted_by": "",
        "prerequisites": ["shield"],
        "min_skill": 12,
        "description": "Aggiunge DR 1 per FP investito (max 5 DR). Si cumula con armatura fisica.",
    },
    {
        "id": "deflect",
        "name": "Deviazione",
        "college": "Protection",
        "energy_cost": 2, "energy_cost_max": 0,
        "maintenance_cost": 1, "casting_time": 1,
        "effect_type": "buff",
        "duration": "mantenuto",
        "resisted_by": "",
        "prerequisites": ["shield"],
        "min_skill": 14,
        "description": "+2 alla schivata del bersaglio per la durata.",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # COLLEGE: MOVEMENT (Movimento) — Character p.249
    # ═══════════════════════════════════════════════════════════════════════════

    {
        "id": "haste",
        "name": "Accelerazione",
        "college": "Movement",
        "energy_cost": 2, "energy_cost_max": 0,
        "maintenance_cost": 2, "casting_time": 1,
        "effect_type": "buff",
        "duration": "mantenuto",
        "resisted_by": "",
        "prerequisites": [],
        "min_skill": 12,
        "description": "+2 al Move del bersaglio per la durata. Bonus alla schivata di +1.",
    },
    {
        "id": "levitation",
        "name": "Levitazione",
        "college": "Movement",
        "energy_cost": 3, "energy_cost_max": 0,
        "maintenance_cost": 3, "casting_time": 1,
        "effect_type": "buff",
        "duration": "mantenuto",
        "resisted_by": "",
        "prerequisites": ["haste"],
        "min_skill": 14,
        "description": "Il bersaglio levita (Move 2 verticale). Immune a danni da caduta per la durata.",
    },
    {
        "id": "flight",
        "name": "Volo",
        "college": "Movement",
        "energy_cost": 4, "energy_cost_max": 0,
        "maintenance_cost": 4, "casting_time": 1,
        "effect_type": "buff",
        "duration": "mantenuto",
        "resisted_by": "",
        "prerequisites": ["levitation"],
        "min_skill": 16,
        "description": "Volo pieno a Move base del bersaglio. Manovre aeree possibili.",
    },
    {
        "id": "teleport",
        "name": "Teletrasporto",
        "college": "Movement",
        "energy_cost": 5, "energy_cost_max": 20,
        "maintenance_cost": 0, "casting_time": 2,
        "effect_type": "utility",
        "duration": "istantaneo",
        "resisted_by": "",
        "prerequisites": ["flight"],
        "min_skill": 17,
        "description": "Teletrasporta il mago a un luogo noto. Costo cresce con la distanza (B250).",
        "notes": "Destinazione deve essere nota e visualizzabile. Fallimento = materializzazione errata.",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # COLLEGE: LIGHT & DARKNESS (Luce e Oscurità) — Character p.248
    # ═══════════════════════════════════════════════════════════════════════════

    {
        "id": "light",
        "name": "Luce",
        "college": "Light/Darkness",
        "energy_cost": 1, "energy_cost_max": 0,
        "maintenance_cost": 1, "casting_time": 1,
        "effect_type": "utility",
        "area": 4,
        "duration": "mantenuto",
        "resisted_by": "",
        "prerequisites": [],
        "min_skill": 10,
        "description": "Illumina un'area di 4 yard raggio (come una torcia). Mantenimento 1 FP/minuto.",
    },
    {
        "id": "darkness",
        "name": "Oscurità",
        "college": "Light/Darkness",
        "energy_cost": 3, "energy_cost_max": 0,
        "maintenance_cost": 3, "casting_time": 1,
        "effect_type": "condition",
        "area": 3,
        "duration": "mantenuto",
        "resisted_by": "",
        "prerequisites": ["light"],
        "min_skill": 14,
        "description": "Oscurità magica (3 yard raggio). Non può essere eliminata da luce non magica.",
    },
    {
        "id": "invisibility",
        "name": "Invisibilità",
        "college": "Light/Darkness",
        "energy_cost": 5, "energy_cost_max": 0,
        "maintenance_cost": 5, "casting_time": 1,
        "effect_type": "buff",
        "duration": "mantenuto",
        "resisted_by": "",
        "prerequisites": ["darkness"],
        "min_skill": 15,
        "description": "Rende il bersaglio invisibile. Gli attacchi contro bersagli invisibili hanno -10.",
        "notes": "Cessano effetto se il bersaglio attacca.",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # COLLEGE: KNOWLEDGE (Conoscenza) — Character p.248
    # ═══════════════════════════════════════════════════════════════════════════

    {
        "id": "seek_earth",
        "name": "Cerca terra",
        "college": "Knowledge",
        "energy_cost": 3, "energy_cost_max": 0,
        "maintenance_cost": 0, "casting_time": 1,
        "effect_type": "utility",
        "duration": "istantaneo",
        "resisted_by": "",
        "prerequisites": [],
        "min_skill": 10,
        "description": "Indica la direzione del tipo di minerale/metallo desiderato più vicino entro 100 yard.",
    },
    {
        "id": "detect_magic",
        "name": "Rileva magia",
        "college": "Knowledge",
        "energy_cost": 2, "energy_cost_max": 0,
        "maintenance_cost": 0, "casting_time": 1,
        "effect_type": "utility",
        "area": 5,
        "duration": "istantaneo",
        "resisted_by": "",
        "prerequisites": [],
        "min_skill": 10,
        "description": "Rileva presenza di oggetti/creature magiche entro 5 yard. Non identifica il tipo.",
    },
    {
        "id": "identify_spell",
        "name": "Identifica incantesimo",
        "college": "Knowledge",
        "energy_cost": 3, "energy_cost_max": 0,
        "maintenance_cost": 0, "casting_time": 1,
        "effect_type": "utility",
        "duration": "istantaneo",
        "resisted_by": "",
        "prerequisites": ["detect_magic"],
        "min_skill": 14,
        "description": "Identifica college, effetto e caster di un incantesimo attivo o oggetto magico.",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # COLLEGE: NECROMANCY (Necromanzia) — Character p.249
    # ═══════════════════════════════════════════════════════════════════════════

    {
        "id": "sense_life",
        "name": "Senti la vita",
        "college": "Necromancy",
        "energy_cost": 2, "energy_cost_max": 0,
        "maintenance_cost": 1, "casting_time": 1,
        "effect_type": "utility",
        "area": 10,
        "duration": "mantenuto",
        "resisted_by": "",
        "prerequisites": [],
        "min_skill": 10,
        "description": "Percepisce presenza e numero di esseri viventi entro 10 yard (non tipo o identità).",
    },
    {
        "id": "death_touch",
        "name": "Tocco della morte",
        "college": "Necromancy",
        "energy_cost": 2, "energy_cost_max": 6,
        "maintenance_cost": 0, "casting_time": 1,
        "effect_type": "damage",
        "damage": "1d per energy",
        "damage_type": "tox",
        "duration": "istantaneo",
        "resisted_by": "SA",
        "prerequisites": ["sense_life"],
        "min_skill": 14,
        "description": "Quick Contest vs SA. Infligge 1d per FP (danno tossico, ignora DR). Solo a contatto.",
    },
    {
        "id": "animate_dead",
        "name": "Anima i morti",
        "college": "Necromancy",
        "energy_cost": 8, "energy_cost_max": 0,
        "maintenance_cost": 4, "casting_time": 5,
        "effect_type": "summon",
        "duration": "mantenuto",
        "resisted_by": "",
        "prerequisites": ["death_touch"],
        "min_skill": 16,
        "description": "Anima un cadavere come non-morto obbediente. Stat: HP originali/3, DE 7, ST originale.",
        "notes": "Il non-morto collassa se il mago smette di mantenere l'incantesimo.",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # COLLEGE: WATER (Acqua) — Character p.252
    # ═══════════════════════════════════════════════════════════════════════════

    {
        "id": "create_water",
        "name": "Crea acqua",
        "college": "Water",
        "energy_cost": 1, "energy_cost_max": 0,
        "maintenance_cost": 0, "casting_time": 1,
        "effect_type": "utility",
        "duration": "permanente",
        "resisted_by": "",
        "prerequisites": [],
        "min_skill": 10,
        "description": "Crea 1 litro d'acqua potabile per FP investito.",
    },
    {
        "id": "water_jet",
        "name": "Getto d'acqua",
        "college": "Water",
        "energy_cost": 2, "energy_cost_max": 0,
        "maintenance_cost": 0, "casting_time": 1,
        "effect_type": "damage",
        "damage": "1d+2",
        "damage_type": "cr",
        "duration": "istantaneo",
        "resisted_by": "",
        "prerequisites": ["create_water"],
        "min_skill": 12,
        "description": "Potente getto d'acqua. Danno 1d+2 cr. Se spinge: Quick Contest FO vs bersaglio.",
        "notes": "Spegne fuochi non magici di 1 yard raggio.",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # COLLEGE: BODY CONTROL (Controllo Corporeo) — Character p.239
    # ═══════════════════════════════════════════════════════════════════════════

    {
        "id": "itch",
        "name": "Prurito",
        "college": "Body Control",
        "energy_cost": 2, "energy_cost_max": 0,
        "maintenance_cost": 1, "casting_time": 1,
        "effect_type": "condition",
        "duration": "mantenuto",
        "resisted_by": "SA",
        "condition_applied": "nauseated",
        "prerequisites": [],
        "min_skill": 10,
        "description": "Quick Contest vs SA. Il bersaglio ha prurito intenso: -2 a tutti i tiri skill.",
    },
    {
        "id": "pain",
        "name": "Dolore",
        "college": "Body Control",
        "energy_cost": 3, "energy_cost_max": 0,
        "maintenance_cost": 2, "casting_time": 1,
        "effect_type": "condition",
        "duration": "mantenuto",
        "resisted_by": "SA",
        "condition_applied": "stunned",
        "prerequisites": ["itch"],
        "min_skill": 14,
        "description": "Quick Contest vs SA. Dolore acuto: il bersaglio è stordito (-4 tiri, no attività complesse).",
    },
    {
        "id": "paralyze_limb",
        "name": "Paralisi arto",
        "college": "Body Control",
        "energy_cost": 3, "energy_cost_max": 0,
        "maintenance_cost": 3, "casting_time": 1,
        "effect_type": "condition",
        "duration": "mantenuto",
        "resisted_by": "SA",
        "condition_applied": "paralyzed",
        "prerequisites": ["pain"],
        "min_skill": 15,
        "description": "Quick Contest vs SA. Un arto del bersaglio è paralizzato (specificare: braccio/gamba).",
    },
]

# ── Indici ────────────────────────────────────────────────────────────────────

# ── Nomi psionici per college compatibili ─────────────────────────────────────
# College che hanno un equivalente psionico in sci-fi / horror.
# La meccanica è identica; cambia solo il flavor name mostrato al giocatore.
_PSIONIC_NAME_MAP: dict[str, str] = {
    "minor_healing":    "Biocinesi minore",
    "major_healing":    "Biocinesi maggiore",
    "cure_disease":     "Purificazione biologica",
    "cure_poison":      "Neutralizzazione tossine",
    "awaken":           "Risveglio psichico",
    "fear":             "Proiezione del terrore",
    "sleep":            "Induzione del sonno",
    "daze":             "Nebbia mentale",
    "suggest":          "Suggestione psichica",
    "mind_reading":     "Telepatia",
    "sense_life":       "Percezione extrasensoriale (ESP)",
    "death_touch":      "Assalto psiconico",
    "haste":            "Accelerazione biocinesi",
    "levitation":       "Telecinesi — levitazione",
    "flight":           "Telecinesi — volo",
    "teleport":         "Teletrasporto psionico",
    "detect_magic":     "Rilevamento psichico",
    "identify_spell":   "Analisi psichica",
    "itch":             "Interferenza neuronica",
    "pain":             "Impulso di dolore",
    "paralyze_limb":    "Blocco neuromotorio",
    "deflect":          "Schermo psionico",
    "shield":           "Campo psionico",
    "armor":            "Schermo cinetico",
}

# College puramente magici (nessun equivalente psionico)
_MAGIC_ONLY_COLLEGES = {"Fire", "Earth", "Air", "Water", "Light/Darkness", "Necromancy"}


def _psionic_view(spell: dict) -> dict:
    """Restituisce una copia del record con nome psionico e flag psionic=True."""
    name = _PSIONIC_NAME_MAP.get(spell["id"], spell["name"])
    return {**spell, "name": name, "psionic": True}


# ── Indici ────────────────────────────────────────────────────────────────────

SPELL_BY_ID: dict[str, dict] = {s["id"]: s for s in SPELL_TABLE}

SPELLS_BY_COLLEGE: dict[str, list[dict]] = {}
for _s in SPELL_TABLE:
    SPELLS_BY_COLLEGE.setdefault(_s["college"], []).append(_s)


def get_spell(spell_id: str) -> Optional[dict]:
    return SPELL_BY_ID.get(spell_id)


def get_spells_for_genre(genre: str) -> list[dict]:
    """
    Ritorna i poteri disponibili per un genere.

    - Fantasy/medievale/storico/steampunk → tutti gli incantesimi magici, psionic=False
    - Horror → tutti gli incantesimi magici + versioni psioniche dei college compatibili
    - Sci-fi → solo versioni psioniche dei college compatibili (no fire/earth/air/ecc.)
    - Altri → lista vuota
    """
    if genre in MAGIC_GENRES and genre not in PSIONIC_GENRES:
        # Magia pura: tutti gli incantesimi, nessun flavor psionico
        return [{**s, "psionic": False} for s in SPELL_TABLE]

    if genre in MAGIC_GENRES and genre in PSIONIC_GENRES:
        # Horror: magia + psionico (college compatibili con entrambi i nomi)
        result = []
        for s in SPELL_TABLE:
            result.append({**s, "psionic": False})
            if s["college"] not in _MAGIC_ONLY_COLLEGES and s["id"] in _PSIONIC_NAME_MAP:
                result.append(_psionic_view(s))
        return result

    if genre in PSIONIC_GENRES:
        # Sci-fi: solo college non-magici con flavor psionico
        return [
            _psionic_view(s)
            for s in SPELL_TABLE
            if s["college"] not in _MAGIC_ONLY_COLLEGES
            and s["id"] in _PSIONIC_NAME_MAP
        ]

    return []


def get_prerequisites_met(spell_id: str, known_spells: dict[str, int]) -> bool:
    """Verifica che i prerequisiti siano soddisfatti (tutti a skill ≥ 12)."""
    spell = get_spell(spell_id)
    if not spell:
        return False
    for req_id in spell.get("prerequisites", []):
        if known_spells.get(req_id, 0) < 12:
            return False
    return True


def spells_learnable(known_spells: dict[str, int], genre: str) -> list[dict]:
    """Lista poteri che il PG può imparare (prerequisiti soddisfatti, non già noti)."""
    available = get_spells_for_genre(genre)
    seen_ids: set[str] = set()
    result = []
    for s in available:
        sid = s["id"]
        if sid in known_spells:
            continue
        if sid in seen_ids:
            continue
        if get_prerequisites_met(sid, known_spells):
            seen_ids.add(sid)
            result.append(s)
    return result
