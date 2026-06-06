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
    "sci_fi":            [ERA_SCIFI, ERA_MODERN],
    "cyberpunk":         [ERA_MODERN, ERA_SCIFI],
    "steampunk":         [ERA_MEDIEVAL, ERA_STEAMPUNK],
    "post_apocalypse":   [ERA_MODERN, ERA_SCIFI],
    "spy":               [ERA_MODERN, ERA_HORROR],
    "action":            [ERA_MODERN, ERA_HORROR],
    "thriller":          [ERA_MODERN, ERA_HORROR],
    "militare":          [ERA_MODERN],
    "investigation":     [ERA_MODERN, ERA_HORROR],
    "investigazione":    [ERA_MODERN, ERA_HORROR],
    "noir":              [ERA_MODERN],
    "giallo":            [ERA_MODERN],
    "romance":           [ERA_MODERN, ERA_MEDIEVAL],
    "romantico":         [ERA_MODERN, ERA_MEDIEVAL],
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
        "attack_kind": "ranged", "damage": "thr",   "damage_type": "imp",
        "acc": 1, "range_half": 15, "range_max": 20, "bulk": -6,
        "ammo": 20, "rcl": 1, "reload": 0, "st_min": 7, "lc": 4,
        "cost": 50, "weight": 2.0,
        "notes": "B:275 Short Bow. Range ×10/×15 ST. RoF 1; recupera frecce.",
        "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY],
    },
    {
        "id": "arco",      "name": "Arco lungo",    "skill": "arco",
        "attack_kind": "ranged", "damage": "thr+2",  "damage_type": "imp",
        "acc": 3, "range_half": 20, "range_max": 25, "bulk": -8,
        "ammo": 20, "rcl": 1, "reload": 0, "st_min": 11, "lc": 4,
        "cost": 200, "weight": 3.0,
        "notes": "B:275 Longbow. Range ×15/×20 ST. Danno e range scalano con ST.",
        "eras": [ERA_MEDIEVAL, ERA_FANTASY],
    },
    {
        "id": "balestra",  "name": "Balestra",      "skill": "balestra",
        "attack_kind": "ranged", "damage": "thr+4",  "damage_type": "imp",
        "acc": 4, "range_half": 25, "range_max": 30, "bulk": -6,
        "ammo": 1, "rcl": 1, "reload": 4, "st_min": 7, "lc": 4,
        "cost": 150, "weight": 6.0,
        "notes": "B:276 Crossbow. Range ×20/×25 ST. Reload 4 turni.",
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
        "id": "colt45",    "name": "Revolver .36",  "skill": "pistola",
        "attack_kind": "ranged", "damage": "2d-1",  "damage_type": "pi",
        "acc": 1, "range_half": 120, "range_max": 1300, "bulk": -2,
        "ammo": 6, "rcl": 2, "reload": 3, "st_min": 10, "lc": 3,
        "cost": 150, "weight": 2.5,
        "notes": "B:278 Revolver .36 (TL5). Reload 3 turni per 6 colpi (individuale).",
        "eras": [ERA_WESTERN],
    },
    {
        "id": "winchester", "name": "Winchester '73", "skill": "fucile",
        "attack_kind": "ranged", "damage": "5d",    "damage_type": "pi",
        "acc": 4, "range_half": 450, "range_max": 3000, "bulk": -4,
        "ammo": 6, "rcl": 2, "reload": 1, "st_min": 10, "lc": 3,
        "cost": 300, "weight": 7.0,
        "notes": "B:279 Lever-Action Carbine .30 (TL5). Reload individuale per colpo.",
        "eras": [ERA_WESTERN],
    },
    {
        "id": "doppietta", "name": "Doppietta 10G", "skill": "fucile",
        "attack_kind": "ranged", "damage": "1d+2",  "damage_type": "pi",
        "acc": 3, "range_half": 50, "range_max": 125, "bulk": -5,
        "ammo": 2, "rcl": 1, "reload": 3, "st_min": 11, "lc": 4,
        "cost": 450, "weight": 10.0,
        "notes": "B:279 Double Shotgun 10G (TL5). RoF 2×9 pellet per canna.",
        "eras": [ERA_WESTERN, ERA_HORROR, ERA_MODERN],
    },

    # ─── ARMI A DISTANZA — MODERNO/HORROR (1900-oggi) ─────────────────────────

    {
        "id": "pistola_9mm", "name": "Pistola 9mm", "skill": "pistola",
        "attack_kind": "ranged", "damage": "2d+2",  "damage_type": "pi",
        "acc": 2, "range_half": 150, "range_max": 1850, "bulk": -2,
        "ammo": 15, "rcl": 2, "reload": 1, "st_min": 9, "lc": 3,
        "cost": 600, "weight": 2.6,
        "notes": "B:278 Auto Pistol 9mm (TL7). Caricatore 15+1; semi-auto RoF 3.",
        "eras": [ERA_MODERN, ERA_HORROR],
    },
    {
        "id": "pistola_38", "name": "Revolver .38", "skill": "pistola",
        "attack_kind": "ranged", "damage": "2d-1",  "damage_type": "pi",
        "acc": 2, "range_half": 120, "range_max": 1500, "bulk": -2,
        "ammo": 6, "rcl": 2, "reload": 3, "st_min": 8, "lc": 3,
        "cost": 400, "weight": 2.0,
        "notes": "B:278 Revolver .38 (TL6). Tipico detective classico; reload individuale.",
        "eras": [ERA_HORROR, ERA_MODERN, ERA_WESTERN],
    },
    {
        "id": "pistola_45acp", "name": "Colt 1911 (.45 ACP)", "skill": "pistola",
        "attack_kind": "ranged", "damage": "2d",    "damage_type": "pi+",
        "acc": 2, "range_half": 175, "range_max": 1700, "bulk": -2,
        "ammo": 7, "rcl": 3, "reload": 1, "st_min": 10, "lc": 3,
        "cost": 300, "weight": 3.0,
        "notes": "B:278 Auto Pistol .45 (TL6). Colt 1911; WWII e western moderno.",
        "eras": [ERA_HORROR, ERA_MODERN, ERA_WESTERN],
    },
    {
        "id": "mitra",     "name": "Mitra SMG 9mm", "skill": "fucile",
        "attack_kind": "ranged", "damage": "3d-1",  "damage_type": "pi",
        "acc": 4, "range_half": 160, "range_max": 1900, "bulk": -4,
        "ammo": 30, "rcl": 2, "reload": 3, "st_min": 10, "lc": 2,
        "cost": 1200, "weight": 7.5,
        "notes": "B:278 SMG 9mm (TL7). RoF 13; versione civile semi-auto LC3.",
        "eras": [ERA_MODERN, ERA_HORROR],
    },
    {
        "id": "fucile_assalto", "name": "Fucile d'assalto 5.56mm", "skill": "fucile",
        "attack_kind": "ranged", "damage": "5d",    "damage_type": "pi",
        "acc": 5, "range_half": 500, "range_max": 3500, "bulk": -4,
        "ammo": 30, "rcl": 2, "reload": 3, "st_min": 9, "lc": 2,
        "cost": 800, "weight": 9.0,
        "notes": "B:279 Assault Rifle 5.56mm (TL7). RoF 12.",
        "eras": [ERA_MODERN],
    },
    {
        "id": "fucile_cecchino", "name": "Fucile da cecchino .338", "skill": "fucile",
        "attack_kind": "ranged", "damage": "9d+1",  "damage_type": "pi",
        "acc": 6, "range_half": 1500, "range_max": 5500, "bulk": -6,
        "ammo": 4, "rcl": 4, "reload": 3, "st_min": 11, "lc": 3,
        "cost": 5600, "weight": 17.5,
        "notes": "B:279 Sniper Rifle .338 (TL8). Richiede Aim; bipode incluso (B).",
        "eras": [ERA_MODERN],
    },
    {
        "id": "shotgun",   "name": "Fucile a pompa 12G", "skill": "fucile",
        "attack_kind": "ranged", "damage": "1d+1",  "damage_type": "pi",
        "acc": 3, "range_half": 50, "range_max": 125, "bulk": -5,
        "ammo": 5, "rcl": 1, "reload": 3, "st_min": 10, "lc": 4,
        "cost": 240, "weight": 8.0,
        "notes": "B:279 Pump Shotgun 12G (TL6). RoF 2×9 pellet; danno devastante a corta dist.",
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

    # ─── FANTASCIENZA — MISCHIA ────────────────────────────────────────────────

    {
        "id": "vibrolama",  "name": "Vibrolama",     "skill": "spada",
        "attack_kind": "melee", "damage": "sw+2",   "damage_type": "cut",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -2,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 8, "lc": 2,
        "cost": 3000, "weight": 1.5,
        "notes": "Lama ad alta frequenza; ignora DR 2 (armor divisor 2 vs DR ≤4).",
        "eras": [ERA_SCIFI],
    },
    {
        "id": "manganello_stordente", "name": "Manganello stordente", "skill": "mazza",
        "attack_kind": "melee", "damage": "1d",     "damage_type": "burn",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -1,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 6, "lc": 3,
        "cost": 400, "weight": 0.5,
        "notes": "Non letale; SA check o stordito.",
        "eras": [ERA_SCIFI, ERA_MODERN],
    },
    {
        "id": "spada_forza",  "name": "Spada di forza", "skill": "spada",
        "attack_kind": "melee", "damage": "8d",     "damage_type": "burn",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -2,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 3, "lc": 2,
        "cost": 10000, "weight": 2.0,
        "notes": "B:272 Force Sword. Armour divisor (5); lama energetica attiva/disattiva con Ready. $100/batteria (300s).",
        "eras": [ERA_SCIFI],
    },
    {
        "id": "artigli_esoscheletro", "name": "Artigli esoscheletro", "skill": "pugilato",
        "attack_kind": "melee", "damage": "thr+4",  "damage_type": "cut",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": 0,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 0, "lc": 2,
        "cost": 5000, "weight": 0.0,
        "notes": "Montati sull'esoscheletro; non richiede ST propria.",
        "eras": [ERA_SCIFI],
    },

    # ─── FANTASCIENZA — DISTANZA ───────────────────────────────────────────────

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

    # ─── ARMI DA MISCHIA — AGGIUNTIVE GURPS 4e Basic Set ─────────────────────

    {
        "id": "morningstar", "name": "Stella del mattino", "skill": "flagello",
        "attack_kind": "melee", "damage": "sw+3",  "damage_type": "cr",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -4,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 12, "lc": 3,
        "cost": 80, "weight": 6.0,
        "notes": "Flagello; tentativo di parare a −4. Armi da scherma non possono pararlo.",
        "eras": [ERA_MEDIEVAL, ERA_FANTASY],
    },
    {
        "id": "falcione", "name": "Falcione", "skill": "asta",
        "attack_kind": "melee", "damage": "sw+3",  "damage_type": "cut",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -6,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 11, "lc": 3,
        "cost": 100, "weight": 8.0,
        "notes": "Due mani; portata 2–3 yard. Colpo alternativo: thr+3 imp.",
        "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY],
    },
    {
        "id": "alabarda", "name": "Alabarda", "skill": "asta",
        "attack_kind": "melee", "damage": "sw+5",  "damage_type": "cut",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -7,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 13, "lc": 3,
        "cost": 150, "weight": 12.0,
        "notes": "Due mani; portata 2–3 yard. Colpo alternativo: sw+4 imp o thr+3 imp.",
        "eras": [ERA_MEDIEVAL, ERA_FANTASY],
    },
    {
        "id": "lancia_lunga", "name": "Lancia lunga", "skill": "lancia",
        "attack_kind": "melee", "damage": "thr+2",  "damage_type": "imp",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -7,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 10, "lc": 3,
        "cost": 60, "weight": 5.0,
        "notes": "Due mani; portata 2–3 yard. Ottima in formazione.",
        "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY],
    },
    {
        "id": "lancia_cavallerizza", "name": "Lancia da cavaliere", "skill": "lancia",
        "attack_kind": "melee", "damage": "thr+3",  "damage_type": "imp",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -6,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 12, "lc": 3,
        "cost": 60, "weight": 6.0,
        "notes": "Portata 4 yard; non può parare. Usata in carica montata.",
        "eras": [ERA_MEDIEVAL, ERA_FANTASY],
    },
    {
        "id": "martello_guerra", "name": "Martello da guerra", "skill": "mazza",
        "attack_kind": "melee", "damage": "sw+3",  "damage_type": "imp",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -5,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 12, "lc": 3,
        "cost": 100, "weight": 7.0,
        "notes": "Due mani; portata 1–2 yard. Penetra bene le armature.",
        "eras": [ERA_MEDIEVAL, ERA_FANTASY],
    },
    {
        "id": "mazzafrusto", "name": "Mazzafrusto", "skill": "mazza",
        "attack_kind": "melee", "damage": "sw+4",  "damage_type": "cr",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -5,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 13, "lc": 3,
        "cost": 80, "weight": 12.0,
        "notes": "Due mani; portata 1–2 yard. L'arma da mischia più devastante.",
        "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY],
    },
    {
        "id": "grande_ascia", "name": "Grande ascia", "skill": "ascia",
        "attack_kind": "melee", "damage": "sw+3",  "damage_type": "cut",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -6,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 12, "lc": 3,
        "cost": 100, "weight": 8.0,
        "notes": "Due mani; portata 1–2 yard.",
        "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY],
    },
    {
        "id": "sciabola", "name": "Sciabola", "skill": "spada",
        "attack_kind": "melee", "damage": "sw-1",  "damage_type": "cut",
        "acc": 0, "range_half": 0, "range_max": 0, "bulk": -3,
        "ammo": 0, "rcl": 1, "reload": 0, "st_min": 8, "lc": 3,
        "cost": 700, "weight": 2.0,
        "notes": "Arma da scherma (parata F). Colpo alternativo: thr+1 imp.",
        "eras": [ERA_MEDIEVAL, ERA_STEAMPUNK, ERA_WESTERN, ERA_HORROR, ERA_FANTASY],
    },

    # ─── ARMI A DISTANZA — STORICHE (GURPS 4e Basic Set) ─────────────────────

    {
        "id": "giavellotto", "name": "Giavellotto", "skill": "lancia_lancio",
        "attack_kind": "ranged", "damage": "thr+1",  "damage_type": "imp",
        "acc": 2, "range_half": 15, "range_max": 20, "bulk": -4,
        "ammo": 1, "rcl": 1, "reload": 0, "st_min": 6, "lc": 4,
        "cost": 30, "weight": 2.0,
        "notes": "Giavellotto da lancio; in mischia: portata 1, parata +2.",
        "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY],
    },
    {
        "id": "pistola_focaia", "name": "Pistola ad avancarica", "skill": "pistola",
        "attack_kind": "ranged", "damage": "2d-1",  "damage_type": "pi+",
        "acc": 1, "range_half": 75, "range_max": 450, "bulk": -3,
        "ammo": 1, "rcl": 2, "reload": 20, "st_min": 10, "lc": 4,
        "cost": 150, "weight": 3.0,
        "notes": "Pietra focaia TL4; ricarica 20 turni. Mano singola.",
        "eras": [ERA_STEAMPUNK],
    },
    {
        "id": "moschetto", "name": "Moschetto ad avancarica", "skill": "fucile",
        "attack_kind": "ranged", "damage": "4d",    "damage_type": "pi++",
        "acc": 2, "range_half": 100, "range_max": 1500, "bulk": -6,
        "ammo": 1, "rcl": 4, "reload": 15, "st_min": 10, "lc": 4,
        "cost": 200, "weight": 13.0,
        "notes": "Moschetto a pietra focaia TL4; ricarica 15 turni.",
        "eras": [ERA_STEAMPUNK],
    },
    {
        "id": "revolver_36", "name": "Revolver .36", "skill": "pistola",
        "attack_kind": "ranged", "damage": "2d-1",  "damage_type": "pi",
        "acc": 2, "range_half": 120, "range_max": 1300, "bulk": -2,
        "ammo": 6, "rcl": 2, "reload": 3, "st_min": 10, "lc": 3,
        "cost": 80, "weight": 2.5,
        "notes": "Revolver anni 1850; precursore del Colt .45.",
        "eras": [ERA_WESTERN],
    },
    {
        "id": "fucile_rigato", "name": "Fucile rigato", "skill": "fucile",
        "attack_kind": "ranged", "damage": "4d",    "damage_type": "pi+",
        "acc": 4, "range_half": 700, "range_max": 2100, "bulk": -6,
        "ammo": 1, "rcl": 3, "reload": 15, "st_min": 10, "lc": 3,
        "cost": 150, "weight": 8.5,
        "notes": "Fucile ad avancarica rigato TL5; Guerra Civile. Ricarica 15 turni.",
        "eras": [ERA_WESTERN],
    },

    # ─── ARMI A DISTANZA — MODERNE AGGIUNTIVE (GURPS 4e Basic Set) ──────────

    {
        "id": "blunderbuss", "name": "Blunderbuss", "skill": "fucile",
        "attack_kind": "ranged", "damage": "1d",    "damage_type": "pi",
        "acc": 1, "range_half": 15, "range_max": 100, "bulk": -5,
        "ammo": 1, "rcl": 1, "reload": 15, "st_min": 11, "lc": 4,
        "cost": 150, "weight": 12.0,
        "notes": "Sparo a pallini ×9; efficace solo a corta distanza. TL4. Ricarica 15 turni.",
        "eras": [ERA_STEAMPUNK],
    },
    {
        "id": "derringer", "name": "Derringer", "skill": "pistola",
        "attack_kind": "ranged", "damage": "1d",    "damage_type": "pi+",
        "acc": 1, "range_half": 80, "range_max": 650, "bulk": -1,
        "ammo": 2, "rcl": 2, "reload": 3, "st_min": 9, "lc": 4,
        "cost": 150, "weight": 0.5,
        "notes": "Pistola tascabile nascondibile (TL5); 2 colpi; facile da occultare.",
        "eras": [ERA_WESTERN, ERA_HORROR],
    },
    {
        "id": "carabina_lever_action", "name": "Carabina a leva", "skill": "fucile",
        "attack_kind": "ranged", "damage": "5d",    "damage_type": "pi",
        "acc": 4, "range_half": 450, "range_max": 3000, "bulk": -4,
        "ammo": 6, "rcl": 2, "reload": 1, "st_min": 10, "lc": 3,
        "cost": 300, "weight": 7.0,
        "notes": "Azione a leva TL5; 1 turno per ricaricare singolo colpo.",
        "eras": [ERA_WESTERN, ERA_MODERN],
    },
    {
        "id": "fucile_bolt_action", "name": "Fucile a otturatore 7.62mm", "skill": "fucile",
        "attack_kind": "ranged", "damage": "7d",    "damage_type": "pi",
        "acc": 5, "range_half": 1000, "range_max": 4200, "bulk": -5,
        "ammo": 5, "rcl": 4, "reload": 3, "st_min": 10, "lc": 3,
        "cost": 350, "weight": 8.9,
        "notes": "B:279 Bolt-Action Rifle 7.62mm (TL6). WWI/II; Rcl 4.",
        "eras": [ERA_MODERN, ERA_HORROR],
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
    "flagello": "morningstar", "stella del mattino": "morningstar", "morningstar": "morningstar",
    "falcione": "falcione", "glaive": "falcione",
    "alabarda": "alabarda", "halberd": "alabarda",
    "lancia lunga": "lancia_lunga", "picca": "lancia_lunga", "pike": "lancia_lunga",
    "lancia da cavaliere": "lancia_cavallerizza", "lancia cavallerizza": "lancia_cavallerizza",
    "martello da guerra": "martello_guerra", "warhammer": "martello_guerra",
    "mazzafrusto": "mazzafrusto", "maul": "mazzafrusto",
    "grande ascia": "grande_ascia", "great axe": "grande_ascia", "ascia a due mani": "grande_ascia",
    "sciabola": "sciabola", "saber": "sciabola",
    # Ranged primitive
    "giavellotto": "giavellotto", "javelin": "giavellotto",
    "fionda": "fionda",
    "arco corto": "arco_corto",
    "arco lungo": "arco", "arco": "arco",   # "arco" = Arco lungo in WEAPON_TABLE
    "balestra": "balestra",
    "lancia lanciata": "lancia_lanciata",
    # Storico ad avancarica
    "pistola ad avancarica": "pistola_focaia", "pistola focaia": "pistola_focaia", "flintlock": "pistola_focaia",
    "moschetto": "moschetto", "musket": "moschetto", "moschetto ad avancarica": "moschetto",
    "revolver 36": "revolver_36", "revolver .36": "revolver_36",
    "fucile rigato": "fucile_rigato", "rifle musket": "fucile_rigato",
    # Moderni aggiuntivi
    "blunderbuss": "blunderbuss", "archibugio": "blunderbuss",
    "derringer": "derringer", "pistola tascabile": "derringer",
    "carabina a leva": "carabina_lever_action",
    "fucile a otturatore": "fucile_bolt_action", "bolt action": "fucile_bolt_action",
    "fucile seconda guerra": "fucile_bolt_action",
    # Firearms western
    "colt": "colt45", "revolver": "pistola_38", "pistola revolver": "pistola_38",
    "winchester": "winchester", "carabina": "carabina_lever_action",
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
    # Sci-fi mischia
    "vibrolama": "vibrolama", "vibroblade": "vibrolama",
    "manganello stordente": "manganello_stordente", "stun baton": "manganello_stordente",
    "spada di forza": "spada_forza", "energy sword": "spada_forza", "spada forza": "spada_forza",
    "artigli esoscheletro": "artigli_esoscheletro",
    # Sci-fi ranged
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
    # Sci-fi — ranged
    "marine":      ("fucile_assalto",  3),
    "pilot":       ("pistola_9mm",     2),
    "scout":       ("pistola_9mm",     2),
    "solo":        ("fucile_assalto",  3),
    "sniper":      ("fucile_cecchino", 3),
    "operative":   ("pistola_9mm",     2),
    "rifleman":    ("fucile_assalto",  3),
    "medic":       ("pistola_9mm",     1),
    "field_medic": ("pistola_9mm",     1),
    # Sci-fi — melee
    "soldier_melee": ("vibrolama",       0),
    "bounty_hunter": ("vibrolama",       0),
    # Fantasy
    "warrior":     ("spada",             0),
    "ranger":      ("arco",              3),   # "arco" = Arco lungo in WEAPON_TABLE
    "rogue":       ("pugnale",           0),
    "mage":        ("stoccata",          0),
    "cleric":      ("mazza",             0),
    "penitent":    ("bastone",           0),
    "knight":      ("lancia_cavallerizza", 0),
    "pikeman":     ("lancia_lunga",       0),
    "barbarian":   ("grande_ascia",       0),
    "halberdier":  ("alabarda",           0),
    # Horror/detective
    "detective":   ("pistola_9mm", 2),
    "inspector":   ("pistola_9mm", 1),
    "journalist":  ("pistola_9mm", 1),
    "forensic":    ("pistola_9mm", 1),
    # Western
    "hunter":      ("winchester",  2),
    "sharpshooter": ("fucile_bolt_action", 3),
    "cowboy":       ("carabina_lever_action", 2),
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
    # Normalizza il genere: "Sci-Fi" / "sci fi" → "sci_fi", così non cade sul
    # default ERA_MODERN (→ pistola 9mm) per una semplice differenza di formato.
    genre = (genre or "").strip().lower().replace("-", "_").replace(" ", "_")
    low = archetype.lower()
    era_list = GENRE_ERA_MAP.get(genre, [ERA_MODERN])
    primary_era = era_list[0] if era_list else ERA_MODERN
    if low in ARCHETYPE_WEAPON_MAP:
        wid, packs = ARCHETYPE_WEAPON_MAP[low]
        w = WEAPON_BY_ID.get(wid)
        weapon_eras = set(w.get("eras", [])) if w else set()
        # L'arma dell'archetype deve essere compatibile con il genere E avere
        # l'era primaria del genere (così evitare di usare pistola moderna in sci-fi).
        if w and primary_era in weapon_eras:
            return wid, packs
    # Fallback per era — l'ordine delle ere nel GENRE_ERA_MAP stabilisce la
    # priorità: il primo elemento della lista vince se ha un'arma di default.
    era_list = GENRE_ERA_MAP.get(genre, [ERA_MODERN])
    eras = set(era_list)
    # Generi con ERA_SCIFI come era primaria (primo elemento) → blaster
    primary_era = era_list[0] if era_list else ERA_MODERN
    if primary_era == ERA_SCIFI:
        return "blaster", 2
    if ERA_MODERN in eras or ERA_HORROR in eras:
        return "pistola_9mm", 2
    if ERA_SCIFI in eras:
        return "blaster", 2
    if ERA_WESTERN in eras:
        return "colt45", 2
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
