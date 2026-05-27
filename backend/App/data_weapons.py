"""
Tabella armi GURPS 4ª ed. Lite — per genere/epoca.

Ogni voce:
  name          str   — nome visualizzato
  skill         str   — skill di attacco (chiave in player.skills)
  attack_kind   str   — "melee" | "ranged"
  damage        str   — formula GURPS, es. "1d6+2", "sw+1", "thr+1"
  damage_type   str   — "cut" | "imp" | "cr" | "burn" | "pi" | "pi+" | "pi-" | "tox"
  acc           int   — bonus Acc (armi a distanza; 0 mischia)
  range_half    int   — gittata a penalità piena ½D (esagoni/yard; 0 mischia)
  range_max     int   — gittata massima (esagoni/yard; 0 mischia)
  bulk          int   — penalità bulk (solo distanza; 0 mischia)
  ammo          int   — caricatore / capacità; 0 = illimitato/rilevante solo narrativamente
  rcl           int   — rinculo (burst-fire penalty per colpo extra, GURPS B373); 1 = nessuno
  reload        int   — turni per ricaricare (0 = istantaneo/non applicabile)
  st_min        int   — ST minima per usarla senza penalità
  lc            int   — Legality Class (5=libera, 1=militare, 0=vietata)
  cost          int   — costo orientativo in moneta d'epoca/crediti
  weight        float — peso in libbre
  notes         str   — note regole speciali
  eras          list  — era compatibili (vedi GENRE_ERA_MAP sotto)
"""

from __future__ import annotations

# ── Costanti era ───────────────────────────────────────────────────────────────
ERA_PRIMITIVE   = "primitive"   # pietra/bronzo/ferro
ERA_MEDIEVAL    = "medieval"    # medievale/rinascimentale
ERA_MODERN      = "modern"      # '800–oggi: armi da fuoco reali
ERA_SCIFI       = "scifi"       # fantascienza
ERA_FANTASY     = "fantasy"     # magia e armi da mischia classiche
ERA_HORROR      = "horror"      # classico: pistole anni '20-'50
ERA_WESTERN     = "western"     # Vecchio West
ERA_STEAMPUNK   = "steampunk"   # vapore + armi ad avancarica/revolver

# ── Mappa genere GURPS→era ─────────────────────────────────────────────────────
GENRE_ERA_MAP: dict[str, list[str]] = {
    "fantasy":           [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY],
    "medievale":         [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY],
    "storico":           [ERA_PRIMITIVE, ERA_MEDIEVAL],
    "horror":            [ERA_MODERN, ERA_HORROR],
    "detective_classico":[ERA_MODERN, ERA_HORROR],
    "western":           [ERA_WESTERN, ERA_MODERN],
    "sci_fi":            [ERA_SCIFI],
    "cyberpunk":         [ERA_MODERN, ERA_SCIFI],
    "steampunk":         [ERA_MEDIEVAL, ERA_STEAMPUNK],
    "post_apocalypse":   [ERA_MODERN, ERA_SCIFI],
    "spy":               [ERA_MODERN, ERA_HORROR],
    "action":            [ERA_MODERN, ERA_HORROR],
    "thriller":          [ERA_MODERN, ERA_HORROR],
    "militare":          [ERA_MODERN],
}

# ── Tabella completa ───────────────────────────────────────────────────────────
WEAPON_TABLE: list[dict] = [

    # ─── ARMI DA MISCHIA ──────────────────────────────────────────────────────

    # Primitive / universali
    {
        "id": "pugno",     "name": "Pugno",        "skill": "pugilato",
        "attack_kind": "melee", "damage": "thr-1",  "damage_type": "cr",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": 0,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 0, "lc": 5,
        "cost": 0, "weight": 0.0,
        "notes": "Colpo a mano; danno di spinta −1.",
        "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY, ERA_MODERN, ERA_HORROR,
                 ERA_WESTERN, ERA_SCIFI, ERA_STEAMPUNK],
    },
    {
        "id": "calcio",    "name": "Calcio",        "skill": "calcio",
        "attack_kind": "melee", "damage": "thr",    "damage_type": "cr",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": 0,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 0, "lc": 5,
        "cost": 0, "weight": 0.0,
        "notes": "−2 difesa dopo il calcio.",
        "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY, ERA_MODERN, ERA_HORROR,
                 ERA_WESTERN, ERA_SCIFI, ERA_STEAMPUNK],
    },
    {
        "id": "clava",     "name": "Clava",         "skill": "mazza",
        "attack_kind": "melee", "damage": "sw+2",   "damage_type": "cr",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -4,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 10, "lc": 4,
        "cost": 5, "weight": 5.0,
        "notes": "ST minima 10; riceve bonus forza (sw).",
        "eras": [ERA_PRIMITIVE, ERA_FANTASY],
    },
    {
        "id": "lancia",    "name": "Lancia",        "skill": "lancia",
        "attack_kind": "melee", "damage": "thr+3",  "damage_type": "imp",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -6,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 9, "lc": 4,
        "cost": 40, "weight": 4.0,
        "notes": "Può essere lanciata (diventa ranged, range ×ST/10).",
        "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY],
    },
    {
        "id": "pugnale",   "name": "Pugnale",       "skill": "pugnale",
        "attack_kind": "melee", "damage": "thr-1",  "damage_type": "imp",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -1,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 5, "lc": 4,
        "cost": 20, "weight": 0.25,
        "notes": "Può essere lanciato (range C/10).",
        "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY, ERA_MODERN, ERA_HORROR,
                 ERA_WESTERN, ERA_SCIFI, ERA_STEAMPUNK],
    },
    {
        "id": "spada_corta","name": "Spada corta",  "skill": "spada",
        "attack_kind": "melee", "damage": "sw",     "damage_type": "cut",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -2,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 8, "lc": 3,
        "cost": 400, "weight": 2.0,
        "notes": "Parata a 0 (base skill/2+3).",
        "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY, ERA_STEAMPUNK],
    },
    {
        "id": "spada",     "name": "Spada",         "skill": "spada",
        "attack_kind": "melee", "damage": "sw+1",   "damage_type": "cut",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -3,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 10, "lc": 3,
        "cost": 650, "weight": 3.0,
        "notes": "Arma principale mischia medievale.",
        "eras": [ERA_MEDIEVAL, ERA_FANTASY, ERA_STEAMPUNK],
    },
    {
        "id": "spadone",   "name": "Spadone",       "skill": "spada_due_mani",
        "attack_kind": "melee", "damage": "sw+3",   "damage_type": "cut",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -5,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 13, "lc": 3,
        "cost": 900, "weight": 7.0,
        "notes": "Due mani; portata 1–2 yard.",
        "eras": [ERA_MEDIEVAL, ERA_FANTASY],
    },
    {
        "id": "ascia",     "name": "Ascia",         "skill": "ascia",
        "attack_kind": "melee", "damage": "sw+2",   "damage_type": "cut",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -2,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 11, "lc": 4,
        "cost": 50, "weight": 4.0,
        "notes": "Non può parare (ascia da guerra).",
        "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY],
    },
    {
        "id": "mazza",     "name": "Mazza d'arme",  "skill": "mazza",
        "attack_kind": "melee", "damage": "sw+3",   "damage_type": "cr",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -4,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 13, "lc": 3,
        "cost": 50, "weight": 8.0,
        "notes": "Colpo contundente: ignora ½ DR armatura leggermente.",
        "eras": [ERA_MEDIEVAL, ERA_FANTASY],
    },
    {
        "id": "bastone",   "name": "Bastone",       "skill": "bastone",
        "attack_kind": "melee", "damage": "sw+1",   "damage_type": "cr",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -4,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 7, "lc": 5,
        "cost": 10, "weight": 4.0,
        "notes": "Arma versatile; parata a +1.",
        "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY, ERA_MODERN, ERA_HORROR,
                 ERA_WESTERN, ERA_STEAMPUNK],
    },
    {
        "id": "stoccata",  "name": "Stocco / Fioretto", "skill": "stocco",
        "attack_kind": "melee", "damage": "thr+1",  "damage_type": "imp",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -2,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 7, "lc": 3,
        "cost": 500, "weight": 1.25,
        "notes": "Parata eccellente; arma da duello.",
        "eras": [ERA_MEDIEVAL, ERA_STEAMPUNK, ERA_HORROR],
    },
    {
        "id": "coltello_da_combattimento", "name": "Coltello da combattimento", "skill": "pugnale",
        "attack_kind": "melee", "damage": "sw-2",   "damage_type": "cut",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -1,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 6, "lc": 4,
        "cost": 60, "weight": 0.5,
        "notes": "Può tagliare o pungere (imp con impugnatura diversa).",
        "eras": [ERA_MODERN, ERA_HORROR, ERA_WESTERN, ERA_SCIFI],
    },
    {
        "id": "katana",    "name": "Katana",        "skill": "spada",
        "attack_kind": "melee", "damage": "sw+2",   "damage_type": "cut",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -3,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 10, "lc": 3,
        "cost": 2400, "weight": 2.5,
        "notes": "Eccellente qualità; parata a 0.",
        "eras": [ERA_MEDIEVAL, ERA_FANTASY, ERA_MODERN],
    },
    {
        "id": "mannaia",   "name": "Mannaia",       "skill": "ascia",
        "attack_kind": "melee", "damage": "sw+1",   "damage_type": "cut",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -2,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 9, "lc": 4,
        "cost": 35, "weight": 2.0,
        "notes": "",
        "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY],
    },
    # Moderno mischia
    {
        "id": "coltello_militare", "name": "Coltello militare", "skill": "pugnale",
        "attack_kind": "melee", "damage": "sw-1",   "damage_type": "cut",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -1,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 6, "lc": 4,
        "cost": 50, "weight": 0.5,
        "notes": "",
        "eras": [ERA_MODERN, ERA_HORROR, ERA_WESTERN],
    },
    {
        "id": "tirapugni",  "name": "Tirapugni",   "skill": "pugilato",
        "attack_kind": "melee", "damage": "thr",    "damage_type": "cr",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": 0,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 0, "lc": 4,
        "cost": 10, "weight": 0.25,
        "notes": "+1 danno rispetto al pugno nudo.",
        "eras": [ERA_MODERN, ERA_HORROR, ERA_WESTERN],
    },

    # ─── ARMI A DISTANZA — PRIMITIVE / MEDIEVALI ──────────────────────────────

    {
        "id": "fionda",    "name": "Fionda",        "skill": "fionda",
        "attack_kind": "ranged", "damage": "1d",    "damage_type": "cr",
        "acc": 0, "range_half": 8, "range_max": 16, "bulk": -4,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 7, "lc": 5,
        "cost": 5, "weight": 0.25,
        "notes": "Proiettili: sassi o pallini; +1 Acc con pietre levigate.",
        "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY],
    },
    {
        "id": "arco_corto", "name": "Arco corto",  "skill": "arco",
        "attack_kind": "ranged", "damage": "1d+1",  "damage_type": "imp",
        "acc": 1, "range_half": 15, "range_max": 20, "bulk": -6,
        "ammo": 20, "rcl": 1, "reload": 0, "st_min": 7, "lc": 4,
        "cost": 50, "weight": 2.0,
        "notes": "Rate of Fire 1; recupera frecce dopo il combattimento.",
        "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY],
    },
    {
        "id": "arco",      "name": "Arco lungo",    "skill": "arco",
        "attack_kind": "ranged", "damage": "1d+2",  "damage_type": "imp",
        "acc": 2, "range_half": 20, "range_max": 25, "bulk": -7,
        "ammo": 20, "rcl": 1, "reload": 0, "st_min": 11, "lc": 4,
        "cost": 200, "weight": 4.0,
        "notes": "ST minima 11; danno varia con ST arciere.",
        "eras": [ERA_MEDIEVAL, ERA_FANTASY],
    },
    {
        "id": "balestra",  "name": "Balestra",      "skill": "balestra",
        "attack_kind": "ranged", "damage": "1d+4",  "damage_type": "imp",
        "acc": 4, "range_half": 25, "range_max": 30, "bulk": -6,
        "ammo": 1, "rcl": 1, "reload": 4, "st_min": 7, "lc": 4,
        "cost": 150, "weight": 6.0,
        "notes": "Reload 4 turni (con cricca manuale).",
        "eras": [ERA_MEDIEVAL, ERA_FANTASY, ERA_STEAMPUNK],
    },
    {
        "id": "lancia_lanciata", "name": "Lancia (lanciata)", "skill": "lancia_lancio",
        "attack_kind": "ranged", "damage": "thr+3",  "damage_type": "imp",
        "acc": 2, "range_half": 10, "range_max": 15, "bulk": -6,
        "ammo": 1, "rcl": 1, "reload": 0, "st_min": 9, "lc": 4,
        "cost": 40, "weight": 4.0,
        "notes": "Una sola freccia; ST modifica la gittata.",
        "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY],
    },

    # ─── ARMI A DISTANZA — WESTERN (1850-1900) ────────────────────────────────

    {
        "id": "colt45",    "name": "Colt .45",      "skill": "pistola",
        "attack_kind": "ranged", "damage": "2d+2",  "damage_type": "pi",
        "acc": 2, "range_half": 50, "range_max": 600, "bulk": -2,
        "ammo": 6, "rcl": 4, "reload": 3, "st_min": 10, "lc": 3,
        "cost": 150, "weight": 3.0,
        "notes": "Revolver classico; reload 3 turni per 6 colpi.",
        "eras": [ERA_WESTERN],
    },
    {
        "id": "winchester", "name": "Winchester '73", "skill": "fucile",
        "attack_kind": "ranged", "damage": "2d+2",  "damage_type": "pi+",
        "acc": 4, "range_half": 175, "range_max": 1800, "bulk": -5,
        "ammo": 15, "rcl": 3, "reload": 1, "st_min": 9, "lc": 3,
        "cost": 250, "weight": 7.5,
        "notes": "Leva ad azione; 1 turno per ricarica singolo colpo.",
        "eras": [ERA_WESTERN],
    },
    {
        "id": "doppietta", "name": "Doppietta",     "skill": "fucile",
        "attack_kind": "ranged", "damage": "1d+1",  "damage_type": "pi",
        "acc": 3, "range_half": 5, "range_max": 50, "bulk": -5,
        "ammo": 2, "rcl": 4, "reload": 2, "st_min": 10, "lc": 3,
        "cost": 200, "weight": 8.0,
        "notes": "Pellet ×9 a 5 yard; danno ×4 a contatto.",
        "eras": [ERA_WESTERN, ERA_HORROR, ERA_MODERN],
    },

    # ─── ARMI A DISTANZA — MODERNO/HORROR (1900-oggi) ─────────────────────────

    {
        "id": "pistola_9mm", "name": "Pistola 9mm", "skill": "pistola",
        "attack_kind": "ranged", "damage": "2d+2",  "damage_type": "pi",
        "acc": 2, "range_half": 150, "range_max": 1800, "bulk": -2,
        "ammo": 17, "rcl": 2, "reload": 1, "st_min": 9, "lc": 3,
        "cost": 600, "weight": 1.5,
        "notes": "Caricatore 17 colpi; semi-auto.",
        "eras": [ERA_MODERN, ERA_HORROR, ERA_SCIFI],
    },
    {
        "id": "pistola_38", "name": "Revolver .38", "skill": "pistola",
        "attack_kind": "ranged", "damage": "2d+1",  "damage_type": "pi",
        "acc": 2, "range_half": 120, "range_max": 1400, "bulk": -2,
        "ammo": 6, "rcl": 4, "reload": 3, "st_min": 9, "lc": 3,
        "cost": 450, "weight": 2.0,
        "notes": "Revolver anni '20-'50; tipico detective classico.",
        "eras": [ERA_HORROR, ERA_MODERN, ERA_WESTERN],
    },
    {
        "id": "pistola_45acp", "name": "Colt 1911 (.45 ACP)", "skill": "pistola",
        "attack_kind": "ranged", "damage": "2d+2",  "damage_type": "pi+",
        "acc": 2, "range_half": 180, "range_max": 1900, "bulk": -2,
        "ammo": 7, "rcl": 3, "reload": 1, "st_min": 10, "lc": 3,
        "cost": 700, "weight": 2.5,
        "notes": "Classico del western moderno e della Seconda Guerra Mondiale.",
        "eras": [ERA_HORROR, ERA_MODERN, ERA_WESTERN],
    },
    {
        "id": "mitra",     "name": "Mitra (SMG)",   "skill": "fucile",
        "attack_kind": "ranged", "damage": "2d+2",  "damage_type": "pi",
        "acc": 3, "range_half": 140, "range_max": 1400, "bulk": -4,
        "ammo": 30, "rcl": 2, "reload": 2, "st_min": 9, "lc": 1,
        "cost": 1200, "weight": 8.0,
        "notes": "Full-auto disponibile; RCL 2 per colpo automatico.",
        "eras": [ERA_MODERN, ERA_HORROR],
    },
    {
        "id": "fucile_assalto", "name": "Fucile d'assalto", "skill": "fucile",
        "attack_kind": "ranged", "damage": "5d",    "damage_type": "pi",
        "acc": 4, "range_half": 500, "range_max": 3900, "bulk": -5,
        "ammo": 30, "rcl": 2, "reload": 2, "st_min": 9, "lc": 1,
        "cost": 2000, "weight": 8.5,
        "notes": "Semi-auto o raffica; gittata eccellente.",
        "eras": [ERA_MODERN],
    },
    {
        "id": "fucile_cecchino", "name": "Fucile da cecchino", "skill": "fucile",
        "attack_kind": "ranged", "damage": "6d+2",  "damage_type": "pi+",
        "acc": 6, "range_half": 800, "range_max": 4700, "bulk": -6,
        "ammo": 5, "rcl": 3, "reload": 3, "st_min": 10, "lc": 1,
        "cost": 6000, "weight": 12.0,
        "notes": "Richiede Aim per almeno 1 turno; bonus Acc +1 con bipode.",
        "eras": [ERA_MODERN],
    },
    {
        "id": "shotgun",   "name": "Fucile a pompa", "skill": "fucile",
        "attack_kind": "ranged", "damage": "1d+1",  "damage_type": "pi",
        "acc": 3, "range_half": 5, "range_max": 50, "bulk": -5,
        "ammo": 6, "rcl": 4, "reload": 1, "st_min": 10, "lc": 3,
        "cost": 500, "weight": 7.5,
        "notes": "Pellet ×9; danno devastante a corta distanza.",
        "eras": [ERA_MODERN, ERA_HORROR, ERA_WESTERN],
    },

    # ─── STEAMPUNK ─────────────────────────────────────────────────────────────

    {
        "id": "pistola_vapore", "name": "Pistola a vapore", "skill": "pistola",
        "attack_kind": "ranged", "damage": "2d",    "damage_type": "pi",
        "acc": 1, "range_half": 30, "range_max": 200, "bulk": -3,
        "ammo": 5, "rcl": 3, "reload": 3, "st_min": 10, "lc": 3,
        "cost": 400, "weight": 3.0,
        "notes": "Ricarica a pistoni a vapore; richiede serbatoio.",
        "eras": [ERA_STEAMPUNK],
    },
    {
        "id": "fucile_tesla", "name": "Fucile Tesla", "skill": "pistola_energia",
        "attack_kind": "ranged", "damage": "3d",    "damage_type": "burn",
        "acc": 3, "range_half": 50, "range_max": 100, "bulk": -5,
        "ammo": 8, "rcl": 1, "reload": 2, "st_min": 9, "lc": 2,
        "cost": 2000, "weight": 6.0,
        "notes": "Proiettile di plasma; nessun rinculo.",
        "eras": [ERA_STEAMPUNK],
    },

    # ─── FANTASCIENZA ───────────────────────────────────────────────────────────

    {
        "id": "blaster",   "name": "Blaster",       "skill": "pistola_energia",
        "attack_kind": "ranged", "damage": "3d",    "damage_type": "burn",
        "acc": 3, "range_half": 100, "range_max": 300, "bulk": -2,
        "ammo": 25, "rcl": 1, "reload": 1, "st_min": 9, "lc": 2,
        "cost": 1200, "weight": 1.5,
        "notes": "Fascio di plasma ionizzato; ignora armature metalliche leggere.",
        "eras": [ERA_SCIFI],
    },
    {
        "id": "folgoratore", "name": "Folgoratore",  "skill": "pistola_energia",
        "attack_kind": "ranged", "damage": "3d+3",  "damage_type": "burn",
        "acc": 3, "range_half": 150, "range_max": 500, "bulk": -3,
        "ammo": 20, "rcl": 1, "reload": 1, "st_min": 9, "lc": 2,
        "cost": 2000, "weight": 2.5,
        "notes": "Fascio energetico ad alta intensità; può stordire (danno non letale).",
        "eras": [ERA_SCIFI],
    },
    {
        "id": "fucile_laser", "name": "Fucile laser",  "skill": "fucile_energia",
        "attack_kind": "ranged", "damage": "6d",   "damage_type": "burn",
        "acc": 6, "range_half": 500, "range_max": 5000, "bulk": -5,
        "ammo": 15, "rcl": 1, "reload": 1, "st_min": 8, "lc": 1,
        "cost": 5000, "weight": 5.0,
        "notes": "Raggio coerente; Acc +1 con mirino ottico.",
        "eras": [ERA_SCIFI],
    },
    {
        "id": "railgun",   "name": "Railgun",       "skill": "artiglieria",
        "attack_kind": "ranged", "damage": "8d",   "damage_type": "pi++",
        "acc": 7, "range_half": 1000, "range_max": 10000, "bulk": -8,
        "ammo": 10, "rcl": 1, "reload": 3, "st_min": 12, "lc": 0,
        "cost": 50000, "weight": 30.0,
        "notes": "Arma militare; proiettile supersonico a contatto elettromagnetico.",
        "eras": [ERA_SCIFI],
    },
    {
        "id": "pistola_stordente", "name": "Pistola stordente", "skill": "pistola_energia",
        "attack_kind": "ranged", "damage": "2d+2",  "damage_type": "tox",
        "acc": 2, "range_half": 30, "range_max": 50, "bulk": -2,
        "ammo": 10, "rcl": 1, "reload": 1, "st_min": 8, "lc": 3,
        "cost": 800, "weight": 1.2,
        "notes": "Non letale; SA check o stordito per 1d×5 secondi.",
        "eras": [ERA_SCIFI, ERA_MODERN],
    },
    {
        "id": "lanciafiamme", "name": "Lanciafiamme",  "skill": "lanciafiamme",
        "attack_kind": "ranged", "damage": "1d+1",  "damage_type": "burn",
        "acc": 1, "range_half": 3, "range_max": 7, "bulk": -7,
        "ammo": 5, "rcl": 1, "reload": 3, "st_min": 10, "lc": 0,
        "cost": 3000, "weight": 40.0,
        "notes": "Area d'effetto; fuoco continuo; bersaglio continua a bruciare.",
        "eras": [ERA_MODERN, ERA_SCIFI],
    },
]

# ── Indici rapidi ──────────────────────────────────────────────────────────────
WEAPON_BY_ID: dict[str, dict] = {w["id"]: w for w in WEAPON_TABLE}

def get_weapons_for_genre(genre: str) -> list[dict]:
    """Ritorna le armi appropriate per il genere della campagna."""
    eras = GENRE_ERA_MAP.get(genre, [ERA_MODERN])
    era_set = set(eras)
    return [w for w in WEAPON_TABLE if any(e in era_set for e in w.get("eras", []))]

def get_weapon(weapon_id: str) -> dict | None:
    return WEAPON_BY_ID.get(weapon_id)

# ─── Mapping item-name → weapon_id ─────────────────────────────────────────────
# Usato per convertire le stringhe di `Player.items` / `base_items` in armi meccaniche.
# Le chiavi sono tutte lowercase; il matching è case-insensitive e substring.
ITEM_NAME_TO_WEAPON_ID: dict[str, str] = {
    # Mischia primitive/universale
    "pugno": "pugno", "calcio": "calcio", "clava": "clava", "bastone": "bastone",
    "lancia": "lancia", "tirapugni": "tirapugni",
    # Mischia medievale/fantasy
    "pugnale": "pugnale", "coltello": "coltello_da_combattimento", "knife": "coltello_da_combattimento",
    "coltello da combattimento": "coltello_da_combattimento",
    "stocco": "stoccata", "stoccata": "stoccata",
    "spada corta": "spada_corta", "spada corta": "spada_corta",
    "spada": "spada", "spadone": "spadone", "spada a due mani": "spadone",
    "katana": "katana",
    "ascia": "ascia", "ascia da guerra": "ascia", "mannaia": "mannaia",
    "mazza": "mazza", "mazza ferrata": "mazza", "mazza d'arme": "mazza",
    "flagello": "bastone",
    # Ranged primitive
    "fionda": "fionda",
    "arco corto": "arco_corto",
    "arco lungo": "arco", "arco": "arco",   # "arco" = Arco lungo in WEAPON_TABLE
    "balestra": "balestra",
    "lancia lanciata": "lancia_lanciata",
    # Firearms western
    "colt": "colt45", "revolver": "pistola_38", "pistola revolver": "pistola_38",
    "winchester": "winchester", "carabina": "winchester",
    "doppietta": "doppietta", "fucile a pompa": "doppietta",
    # Firearms modern
    "pistola": "pistola_9mm", "pistola 9mm": "pistola_9mm", "9mm": "pistola_9mm",
    "pistola silenziata": "pistola_9mm",
    "colt 1911": "pistola_45acp", "1911": "pistola_45acp",
    "mitra": "mitra", "submachine gun": "mitra",
    "fucile d'assalto": "fucile_assalto", "fucile da assalto": "fucile_assalto",
    "fucile da cecchino": "fucile_cecchino", "cecchino": "fucile_cecchino", "sniper": "fucile_cecchino",
    "shotgun": "shotgun",
    # Steampunk
    "pistola a vapore": "pistola_vapore", "fucile tesla": "fucile_tesla",
    # Sci-fi
    "blaster": "blaster", "pistola blaster": "blaster",
    "folgoratore": "folgoratore", "pistola folgoratore": "folgoratore",
    "fucile laser": "fucile_laser", "laser": "fucile_laser",
    "railgun": "railgun", "rail gun": "railgun",
    "pistola stordente": "pistola_stordente", "stordente": "pistola_stordente",
    "lanciafiamme": "lanciafiamme",
}


def item_to_weapon_id(item_name: str) -> str | None:
    """
    Cerca il weapon_id per un nome oggetto (case-insensitive).
    Match esatto prima, poi match per parola intera (evita falsi positivi come
    'fucile' dentro 'armatura' o 'ar' dentro 'armatura').
    """
    import re as _re
    low = item_name.lower().strip()
    # 1. Match esatto
    if low in ITEM_NAME_TO_WEAPON_ID:
        return ITEM_NAME_TO_WEAPON_ID[low]
    # 2. Match per parola intera — chiave più lunga prima
    for key in sorted(ITEM_NAME_TO_WEAPON_ID, key=len, reverse=True):
        if len(key) < 4:   # ignora chiavi troppo corte (rischio falsi positivi)
            continue
        # la chiave deve comparire come sequenza di parole nel nome
        pattern = r'(?<!\w)' + _re.escape(key) + r'(?!\w)'
        if _re.search(pattern, low):
            return ITEM_NAME_TO_WEAPON_ID[key]
    return None


# ─── Mappa archetipo → arma primaria (weapon_id, ammo_packs) ──────────────────
# Usato quando un PG o NPC non ha armi esplicite e va auto-equipaggiato.
ARCHETYPE_WEAPON_MAP: dict[str, tuple[str, int]] = {
    # Sci-fi
    "marine":      ("fucile_assalto",  3),
    "pilot":       ("pistola_9mm",     2),
    "scout":       ("pistola_9mm",     2),
    "solo":        ("fucile_assalto",  3),
    "sniper":      ("fucile_cecchino", 3),
    "operative":   ("pistola_9mm",     2),
    "rifleman":    ("fucile_assalto",  3),
    "medic":       ("pistola_9mm",     1),
    "field_medic": ("pistola_9mm",     1),
    # Fantasy
    "warrior":     ("spada",      0),
    "ranger":      ("arco",       3),   # "arco" = Arco lungo in WEAPON_TABLE
    "rogue":       ("pugnale",    0),
    "mage":        ("stoccata",   0),
    "cleric":      ("mazza",      0),
    "penitent":    ("bastone",    0),
    "knight":      ("spada",      0),
    # Horror/detective
    "detective":   ("pistola_9mm", 2),
    "inspector":   ("pistola_9mm", 1),
    "journalist":  ("pistola_9mm", 1),
    "forensic":    ("pistola_9mm", 1),
    # Western
    "hunter":      ("winchester",  2),
    "gunslinger":  ("colt45",      3),
    # Military
    "partisan":    ("fucile_assalto", 2),
    "officer":     ("pistola_9mm",    2),
    # Action/spy
    "agent":       ("pistola_9mm",  2),
    "hacker":      ("pistola_9mm",  1),
    "thug":        ("pistola_9mm",  1),
    "guard":       ("fucile_assalto", 2),
    "boss":        ("pistola_9mm",  2),
    "antagonist":  ("pistola_9mm",  2),
    "antagonista": ("pistola_9mm",  2),
    # Primitive
    "shaman":      ("bastone",    0),
    "barbarian":   ("ascia",      0),
    "archer":      ("arco",       3),
}


def default_weapon_for_archetype(archetype: str, genre: str) -> tuple[str, int] | tuple[None, int]:
    """
    Ritorna (weapon_id, ammo_packs) per un archetipo + genere.
    Se l'archetipo non è in ARCHETYPE_WEAPON_MAP, deduce dall'era del genere.
    """
    low = archetype.lower()
    if low in ARCHETYPE_WEAPON_MAP:
        wid, packs = ARCHETYPE_WEAPON_MAP[low]
        # Valida che l'arma sia compatibile con il genere
        w = WEAPON_BY_ID.get(wid)
        eras_for_genre = set(GENRE_ERA_MAP.get(genre, [ERA_MODERN]))
        if w and any(e in eras_for_genre for e in w.get("eras", [])):
            return wid, packs
    # Fallback per era
    eras = set(GENRE_ERA_MAP.get(genre, [ERA_MODERN]))
    if ERA_SCIFI in eras:
        return "pistola_9mm", 2
    if ERA_MODERN in eras or ERA_HORROR in eras:
        return "pistola_9mm", 2
    if ERA_WESTERN in eras:
        return "colt_45", 2
    if ERA_STEAMPUNK in eras:
        return "pistola_vapore", 2
    if ERA_MEDIEVAL in eras or ERA_FANTASY in eras:
        return "spada_corta", 0
    if ERA_PRIMITIVE in eras:
        return "clava", 0
    return None, 0


def _ammo_name_for_weapon(w: dict) -> str:
    """Deduce il nome delle munizioni dall'arma."""
    wid = w.get("id", "")
    if "arco" in wid or "balestra" in wid:
        return "Frecce (30)"
    if "fionda" in wid:
        return "Pietre (30)"
    if "fucile" in wid or "carabina" in wid or "winchester" in wid:
        return "Cartucce fucile (10)"
    if "shotgun" in wid or "doppietta" in wid:
        return "Cartucce shotgun (10)"
    if "mitra" in wid or "assalto" in wid:
        return "Caricatore (30 colpi)"
    if "blaster" in wid or "laser" in wid or "folgoratore" in wid or "rail" in wid:
        return "Celle energia (20)"
    if "lanciafiamme" in wid:
        return "Serbatoio carburante (1)"
    # pistola generica
    ammo = w.get("ammo", 7)
    return f"Caricatore ({ammo} colpi)"


def build_action_from_weapon(weapon_id: str, player_skill_level: int | None = None) -> dict:
    """Crea un dizionario Action-compatibile da un ID arma."""
    w = WEAPON_BY_ID.get(weapon_id)
    if not w:
        return {}
    return {
        "name": w["name"],
        "stat": "DE",
        "skill": w["skill"],
        "difficulty": 0,
        "effect_type": "combattere",
        "action_role": "core",
        "attack_kind": w["attack_kind"],
        "damage": w["damage"],
        "damage_type": w["damage_type"],
        "acc": w.get("acc", 0),
        "range_half": w.get("range_half", 0),
        "range_max": w.get("range_max", 0),
        "bulk": w.get("bulk", 0),
        "ammo": w.get("ammo", 0),
        "ammo_current": w.get("ammo", 0),
        "rcl": w.get("rcl", 1),
        "reload": w.get("reload", 0),
        "weapon_id": weapon_id,
        "weapon_notes": w.get("notes", ""),
    }
