"""Bestiario — creature/NPC generici pre-statati (GURPS Lite) per incontri casuali.

Stessa filosofia di data_weapons.py: una tabella di dati pura, senza dipendenze
sul runtime. Ogni voce ha statistiche di combattimento che mappano 1:1 su
``SceneEntity`` (hp/dr/attack_skill/active_defense/damage), più le ere/generi in
cui è plausibile incontrarla. Serve per "wandering monster" / incontri casuali
appropriati al genere dell'avventura.

Per espandere: il capitolo *Animals* di "GURPS 4th Edition - Basic Set.pdf"
contiene molte creature statate da cui si può attingere (estrazione offline).
"""
from __future__ import annotations

import random
from typing import Optional

from .data_weapons import (
    ERA_FANTASY, ERA_HORROR, ERA_MEDIEVAL, ERA_MODERN, ERA_PRIMITIVE,
    ERA_SCIFI, ERA_STEAMPUNK, ERA_WESTERN, GENRE_ERA_MAP,
)

# Ogni creatura:
#   id, name, eras, threat (0-3, peso/difficoltà), hp, dr,
#   attack_skill, active_defense, damage_dice, damage_type ("cut|imp|cr|pi|burn"),
#   morale ("" ritirata al 33% | "tenace" 20% | "fanatico" mai), tags, desc,
#   habitats (opzionale): ambienti compatibili (acquatico/montano/foresta/desertico/
#     gelido/sotterraneo/urbano/interno/palude/rurale/cielo). Assente = ubiqua.
# Le stat degli animali reali seguono GURPS Basic Set (cap. Animals): hp=ST,
# dodge, Brawling, e danno da "Damage for Animals" (spinta per ST −1 morso/artiglio,
# +1/dado se Brawling a DX+2, tipo per Sharp Teeth/Claws/Striker).
CREATURE_TABLE: list[dict] = [
    # ─── Fantasy / Medievale / Primitivo ──────────────────────────────────────
    {"id": "lupo", "name": "Lupo", "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY],
     "threat": 1, "hp": 10, "dr": 1, "attack_skill": 14, "active_defense": 9,
     "damage_dice": "1d-2", "damage_type": "cut", "morale": "",
     "habitats": ["foresta", "montano", "gelido", "rurale"],
     "tags": ["bestia", "branco"], "desc": "Predatore agile che caccia in branco."},
    {"id": "orso", "name": "Orso grizzly", "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY],
     "threat": 3, "hp": 19, "dr": 2, "attack_skill": 13, "active_defense": 9,
     "damage_dice": "2d", "damage_type": "cut", "morale": "tenace",
     "habitats": ["foresta", "montano", "gelido"],
     "tags": ["bestia", "grande"], "desc": "Massa di muscoli e artigli, territoriale e irascibile (Bad Temper)."},
    {"id": "ratto_gigante", "name": "Ratto gigante", "eras": [ERA_MEDIEVAL, ERA_FANTASY, ERA_HORROR],
     "threat": 0, "hp": 6, "dr": 0, "attack_skill": 12, "active_defense": 9,
     "damage_dice": "1d-3", "damage_type": "imp", "morale": "",
     "habitats": ["sotterraneo", "urbano"],
     "tags": ["bestia", "sciame"], "desc": "Roditore famelico delle fogne e cripte."},
    {"id": "goblin", "name": "Goblin", "eras": [ERA_FANTASY],
     "threat": 1, "hp": 9, "dr": 2, "attack_skill": 11, "active_defense": 9,
     "damage_dice": "1d", "damage_type": "cut", "morale": "",
     "tags": ["umanoide", "branco"], "desc": "Predone vile ma numeroso, mazza o lama corta."},
    {"id": "scheletro", "name": "Scheletro", "eras": [ERA_FANTASY, ERA_HORROR],
     "threat": 1, "hp": 11, "dr": 2, "attack_skill": 11, "active_defense": 8,
     "damage_dice": "1d", "damage_type": "cut", "morale": "fanatico",
     "tags": ["non-morto", "immune_paura"], "desc": "Guerriero rianimato, non conosce paura né dolore."},
    {"id": "bandito", "name": "Bandito", "eras": [ERA_MEDIEVAL, ERA_FANTASY, ERA_WESTERN],
     "threat": 1, "hp": 11, "dr": 1, "attack_skill": 12, "active_defense": 9,
     "damage_dice": "1d+1", "damage_type": "cut", "morale": "",
     "tags": ["umanoide", "predone"], "desc": "Tagliagole opportunista in cerca di bottino."},

    # ─── Moderno / Horror ──────────────────────────────────────────────────────
    {"id": "teppista", "name": "Teppista", "eras": [ERA_MODERN, ERA_WESTERN],
     "threat": 1, "hp": 11, "dr": 0, "attack_skill": 11, "active_defense": 9,
     "damage_dice": "1d-1", "damage_type": "imp", "morale": "",
     "tags": ["umanoide", "criminale"], "desc": "Delinquente da vicolo, coltello o tirapugni."},
    {"id": "cane_guardia", "name": "Cane da guardia", "eras": [ERA_MODERN, ERA_WESTERN, ERA_MEDIEVAL],
     "threat": 1, "hp": 9, "dr": 0, "attack_skill": 13, "active_defense": 8,
     "damage_dice": "1d-2", "damage_type": "cut", "morale": "tenace",
     "habitats": ["urbano", "rurale", "interno"],
     "tags": ["bestia", "addestrato"], "desc": "Molosso addestrato, morso tenace."},
    {"id": "zombie", "name": "Zombie", "eras": [ERA_MODERN, ERA_HORROR],
     "threat": 2, "hp": 13, "dr": 0, "attack_skill": 10, "active_defense": 7,
     "damage_dice": "1d", "damage_type": "cr", "morale": "fanatico",
     "tags": ["non-morto", "lento", "immune_paura"], "desc": "Cadavere ambulante, lento ma inarrestabile."},
    {"id": "ghoul", "name": "Ghoul", "eras": [ERA_HORROR, ERA_FANTASY],
     "threat": 2, "hp": 13, "dr": 1, "attack_skill": 12, "active_defense": 9,
     "damage_dice": "1d", "damage_type": "cut", "morale": "tenace",
     "tags": ["non-morto", "agile"], "desc": "Divoratore di carogne dagli artigli affilati."},
    {"id": "cultista", "name": "Cultista", "eras": [ERA_MODERN, ERA_HORROR],
     "threat": 1, "hp": 10, "dr": 0, "attack_skill": 11, "active_defense": 8,
     "damage_dice": "1d-1", "damage_type": "cut", "morale": "fanatico",
     "tags": ["umanoide", "fanatico"], "desc": "Adepto invasato pronto a sacrificarsi."},

    # ─── Sci-Fi / Cyberpunk ────────────────────────────────────────────────────
    {"id": "drone_sicurezza", "name": "Drone di sicurezza", "eras": [ERA_SCIFI, ERA_STEAMPUNK],
     "threat": 2, "hp": 8, "dr": 4, "attack_skill": 12, "active_defense": 9,
     "damage_dice": "2d", "damage_type": "burn", "morale": "fanatico",
     "tags": ["macchina", "volante"], "desc": "Sentinella automatica con arma a energia."},
    {"id": "androide_canaglia", "name": "Androide canaglia", "eras": [ERA_SCIFI],
     "threat": 3, "hp": 14, "dr": 3, "attack_skill": 13, "active_defense": 10,
     "damage_dice": "1d+1", "damage_type": "cr", "morale": "fanatico",
     "tags": ["macchina", "umanoide"], "desc": "Sintetico fuori controllo, forte e implacabile."},
    {"id": "bestia_aliena", "name": "Bestia aliena", "eras": [ERA_SCIFI, ERA_HORROR],
     "threat": 3, "hp": 16, "dr": 2, "attack_skill": 12, "active_defense": 9,
     "damage_dice": "2d-1", "damage_type": "cut", "morale": "tenace",
     "tags": ["alieno", "grande"], "desc": "Organismo xeno ostile, artigli e fauci."},

    # ─── Western ───────────────────────────────────────────────────────────────
    {"id": "serpente_sonagli", "name": "Serpente a sonagli", "eras": [ERA_WESTERN, ERA_MODERN],
     "threat": 1, "hp": 5, "dr": 0, "attack_skill": 15, "active_defense": 9,
     "damage_dice": "1d-3", "damage_type": "imp", "morale": "",
     "habitats": ["desertico", "rurale"],
     "tags": ["bestia", "veleno", "piccolo"], "desc": "Morso fulmineo con zanne: piccolo danno ma veleno potente (Toxic)."},
    {"id": "puma", "name": "Puma", "eras": [ERA_WESTERN, ERA_PRIMITIVE, ERA_MEDIEVAL],
     "threat": 2, "hp": 13, "dr": 0, "attack_skill": 14, "active_defense": 11,
     "damage_dice": "1d-1", "damage_type": "cut", "morale": "",
     "habitats": ["montano", "foresta", "desertico"],
     "tags": ["bestia", "agguato"], "desc": "Felino in agguato, balzo rapido e letale."},

    # ─── Fantasy aggiuntive ────────────────────────────────────────────────────
    {"id": "orco", "name": "Orco", "eras": [ERA_FANTASY],
     "threat": 2, "hp": 13, "dr": 2, "attack_skill": 12, "active_defense": 9,
     "damage_dice": "2d-1", "damage_type": "cut", "morale": "tenace",
     "tags": ["umanoide", "guerriero"], "desc": "Bruto da guerra con ascia o mazza pesante."},
    {"id": "ragno_gigante", "name": "Ragno gigante", "eras": [ERA_FANTASY, ERA_HORROR],
     "threat": 2, "hp": 14, "dr": 1, "attack_skill": 13, "active_defense": 10,
     "damage_dice": "1d-2", "damage_type": "imp", "morale": "",
     "habitats": ["sotterraneo", "foresta"],
     "tags": ["bestia", "veleno", "tela"], "desc": "Aracnide enorme: morso velenoso e tele."},
    {"id": "spettro", "name": "Spettro", "eras": [ERA_HORROR, ERA_FANTASY],
     "threat": 3, "hp": 12, "dr": 0, "attack_skill": 13, "active_defense": 11,
     "damage_dice": "1d", "damage_type": "burn", "morale": "fanatico",
     "tags": ["non-morto", "incorporeo", "immune_paura"], "desc": "Apparizione che drena con tocco gelido."},

    # ─── Sci-Fi aggiuntive ─────────────────────────────────────────────────────
    {"id": "soldato_clone", "name": "Soldato clone", "eras": [ERA_SCIFI],
     "threat": 2, "hp": 12, "dr": 3, "attack_skill": 13, "active_defense": 10,
     "damage_dice": "2d", "damage_type": "burn", "morale": "fanatico",
     "tags": ["umanoide", "militare"], "desc": "Fante geneticamente prodotto, fucile a impulsi."},
    {"id": "sciame_nanitico", "name": "Sciame nanitico", "eras": [ERA_SCIFI, ERA_STEAMPUNK],
     "threat": 2, "hp": 8, "dr": 1, "attack_skill": 12, "active_defense": 8,
     "damage_dice": "1d", "damage_type": "cr", "morale": "fanatico",
     "tags": ["macchina", "sciame", "corrosivo"], "desc": "Nube di micro-robot che corrode e disassembla."},
    {"id": "predatore_xeno", "name": "Predatore xeno", "eras": [ERA_SCIFI, ERA_HORROR],
     "threat": 3, "hp": 17, "dr": 3, "attack_skill": 14, "active_defense": 11,
     "damage_dice": "2d", "damage_type": "imp", "morale": "tenace",
     "tags": ["alieno", "agguato", "grande"], "desc": "Cacciatore alieno mimetico, code e fauci."},

    # ─── Moderno aggiuntive ────────────────────────────────────────────────────
    {"id": "mercenario", "name": "Mercenario armato", "eras": [ERA_MODERN],
     "threat": 2, "hp": 12, "dr": 2, "attack_skill": 13, "active_defense": 10,
     "damage_dice": "2d", "damage_type": "pi", "morale": "",
     "tags": ["umanoide", "armato"], "desc": "Soldato di ventura con arma da fuoco e giubbotto."},

    # ─── Animali (multi-era: natura/wilderness) ────────────────────────────────
    {"id": "coccodrillo", "name": "Coccodrillo", "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_MODERN, ERA_FANTASY],
     "threat": 2, "hp": 16, "dr": 2, "attack_skill": 12, "active_defense": 8,
     "damage_dice": "2d", "damage_type": "cut", "morale": "tenace",
     "habitats": ["acquatico", "palude"],
     "tags": ["bestia", "acquatico", "agguato"], "desc": "Rettile in agguato nell'acqua, morso devastante."},
    {"id": "cinghiale", "name": "Cinghiale", "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY, ERA_WESTERN],
     "threat": 2, "hp": 15, "dr": 2, "attack_skill": 12, "active_defense": 10,
     "damage_dice": "1d+2", "damage_type": "cut", "morale": "tenace",
     "habitats": ["foresta", "rurale", "palude"],
     "tags": ["bestia", "carica"], "desc": "Suino selvatico aggressivo: zanne taglienti (Striker), carica e travolge (Combat Reflexes)."},
    {"id": "leone", "name": "Leone", "eras": [ERA_PRIMITIVE, ERA_FANTASY, ERA_MEDIEVAL],
     "threat": 2, "hp": 16, "dr": 1, "attack_skill": 15, "active_defense": 9,
     "damage_dice": "1d+1", "damage_type": "cut", "morale": "",
     "habitats": ["rurale", "desertico", "foresta"],
     "tags": ["bestia", "predatore"], "desc": "Grande felino, balzo potente e morso alla gola."},
    {"id": "squalo", "name": "Squalo tigre", "eras": [ERA_MODERN, ERA_PRIMITIVE, ERA_SCIFI],
     "threat": 2, "hp": 19, "dr": 0, "attack_skill": 15, "active_defense": 10,
     "damage_dice": "2d", "damage_type": "cut", "morale": "tenace",
     "habitats": ["acquatico"],
     "tags": ["bestia", "acquatico"], "desc": "Predatore marino aggressivo, fauci che recidono (Combat Reflexes)."},
    {"id": "sciame_insetti", "name": "Sciame d'insetti", "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY, ERA_MODERN, ERA_HORROR],
     "threat": 1, "hp": 6, "dr": 0, "attack_skill": 12, "active_defense": 7,
     "damage_dice": "1d-3", "damage_type": "cor", "morale": "fanatico",
     "habitats": ["foresta", "palude", "rurale", "urbano"],
     "tags": ["sciame", "veleno"], "desc": "Nube di insetti che soffoca e punge senza sosta."},
    {"id": "rapace_gigante", "name": "Rapace gigante", "eras": [ERA_FANTASY, ERA_PRIMITIVE],
     "threat": 2, "hp": 12, "dr": 0, "attack_skill": 14, "active_defense": 12,
     "damage_dice": "1d", "damage_type": "cut", "morale": "",
     "habitats": ["montano", "foresta", "cielo", "rurale"],
     "tags": ["bestia", "volante"], "desc": "Uccello da preda enorme, artigli e picchiata fulminea."},

    # ─── Fantasy aggiuntive ────────────────────────────────────────────────────
    {"id": "troll", "name": "Troll", "eras": [ERA_FANTASY],
     "threat": 3, "hp": 22, "dr": 2, "attack_skill": 13, "active_defense": 9,
     "damage_dice": "2d+1", "damage_type": "cut", "morale": "tenace",
     "tags": ["umanoide", "grande", "rigenera"], "desc": "Bestione che rigenera le ferite, teme solo il fuoco."},
    {"id": "non_morto_guerriero", "name": "Spettro guerriero", "eras": [ERA_FANTASY, ERA_HORROR],
     "threat": 3, "hp": 15, "dr": 3, "attack_skill": 14, "active_defense": 11,
     "damage_dice": "1d+2", "damage_type": "cut", "morale": "fanatico",
     "tags": ["non-morto", "armato", "immune_paura"], "desc": "Campione caduto in armatura, freddo e implacabile."},
    {"id": "kobold", "name": "Kobold", "eras": [ERA_FANTASY],
     "threat": 0, "hp": 7, "dr": 1, "attack_skill": 11, "active_defense": 10,
     "damage_dice": "1d-2", "damage_type": "imp", "morale": "",
     "tags": ["umanoide", "branco", "trappole"], "desc": "Piccolo predone vile, attacca in sciami e con trappole."},
    {"id": "golem_pietra", "name": "Golem di pietra", "eras": [ERA_FANTASY],
     "threat": 3, "hp": 20, "dr": 5, "attack_skill": 12, "active_defense": 8,
     "damage_dice": "2d", "damage_type": "cr", "morale": "fanatico",
     "tags": ["costrutto", "grande", "immune_paura"], "desc": "Statua animata, lentissima ma quasi indistruttibile."},

    # ─── Horror aggiuntive ─────────────────────────────────────────────────────
    {"id": "vampiro", "name": "Vampiro", "eras": [ERA_HORROR, ERA_FANTASY],
     "threat": 3, "hp": 14, "dr": 2, "attack_skill": 14, "active_defense": 12,
     "damage_dice": "1d", "damage_type": "cut", "morale": "",
     "tags": ["non-morto", "drena", "rigenera"], "desc": "Predatore notturno affascinante, forza sovrumana e morso che drena."},
    {"id": "licantropo", "name": "Licantropo", "eras": [ERA_HORROR, ERA_FANTASY, ERA_MODERN],
     "threat": 3, "hp": 16, "dr": 2, "attack_skill": 14, "active_defense": 11,
     "damage_dice": "2d-1", "damage_type": "cut", "morale": "tenace",
     "habitats": ["foresta", "montano", "rurale", "urbano"],
     "tags": ["mutaforma", "bestia", "rigenera"], "desc": "Uomo-lupo furioso, vulnerabile solo all'argento."},

    # ─── Sci-Fi aggiuntive ─────────────────────────────────────────────────────
    {"id": "robot_da_guerra", "name": "Robot da guerra", "eras": [ERA_SCIFI],
     "threat": 3, "hp": 18, "dr": 5, "attack_skill": 13, "active_defense": 9,
     "damage_dice": "3d", "damage_type": "burn", "morale": "fanatico",
     "tags": ["macchina", "grande", "corazzato"], "desc": "Mech da combattimento corazzato con armi pesanti."},
    {"id": "mutante", "name": "Mutante radioattivo", "eras": [ERA_SCIFI, ERA_HORROR],
     "threat": 2, "hp": 15, "dr": 1, "attack_skill": 12, "active_defense": 9,
     "damage_dice": "1d+2", "damage_type": "cut", "morale": "tenace",
     "tags": ["mutante", "contaminato"], "desc": "Sopravvissuto deforme dalle terre contaminate, forte e imprevedibile."},
    {"id": "parassita_alieno", "name": "Parassita alieno", "eras": [ERA_SCIFI, ERA_HORROR],
     "threat": 2, "hp": 8, "dr": 1, "attack_skill": 13, "active_defense": 11,
     "damage_dice": "1d-1", "damage_type": "imp", "morale": "fanatico",
     "tags": ["alieno", "piccolo", "infesta"], "desc": "Organismo che balza e si attacca per infestare l'ospite."},

    # ─── Predatori canonici (GURPS Basic Set, p.455-457) ───────────────────────
    {"id": "tigre", "name": "Tigre", "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY, ERA_MODERN],
     "threat": 2, "hp": 17, "dr": 1, "attack_skill": 15, "active_defense": 10,
     "damage_dice": "1d+2", "damage_type": "cut", "morale": "tenace",
     "habitats": ["foresta", "montano"],
     "tags": ["bestia", "agguato"], "desc": "Felino cacciatore solitario della giungla, artigli e morso letali (Combat Reflexes)."},
    {"id": "pitone", "name": "Pitone", "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY, ERA_MODERN],
     "threat": 2, "hp": 13, "dr": 0, "attack_skill": 13, "active_defense": 8,
     "damage_dice": "1d", "damage_type": "cr", "morale": "",
     "habitats": ["foresta", "palude", "acquatico"],
     "tags": ["bestia", "costrizione", "agguato"], "desc": "Grande costrittore: afferra la preda e la stritola (Constriction Attack)."},
    {"id": "squalo_bianco", "name": "Grande squalo bianco", "eras": [ERA_MODERN, ERA_PRIMITIVE, ERA_SCIFI],
     "threat": 3, "hp": 38, "dr": 0, "attack_skill": 12, "active_defense": 9,
     "damage_dice": "4d+3", "damage_type": "cut", "morale": "tenace",
     "habitats": ["acquatico"],
     "tags": ["bestia", "acquatico", "enorme"], "desc": "Predatore apicale degli abissi: morso devastante, durissimo da uccidere (Hard to Kill)."},
    {"id": "falco", "name": "Falco", "eras": [ERA_PRIMITIVE, ERA_MEDIEVAL, ERA_FANTASY, ERA_MODERN, ERA_WESTERN],
     "threat": 0, "hp": 3, "dr": 0, "attack_skill": 16, "active_defense": 9,
     "damage_dice": "1d-5", "damage_type": "cut", "morale": "",
     "habitats": ["montano", "foresta", "cielo", "rurale"],
     "tags": ["bestia", "volante", "piccolo"], "desc": "Rapace addestrato o disturbato: becco e artigli, picchiata fulminea."},
]

CREATURE_BY_ID: dict[str, dict] = {c["id"]: c for c in CREATURE_TABLE}


# Ambiente (testo libero) → insieme di habitat compatibili. Permissivo: ad ogni
# ambiente associamo gli habitat plausibili, così si escludono solo gli accostamenti
# palesemente incoerenti (es. una creatura solo "acquatico" in montagna).
_ENVIRONMENT_HABITATS: list[tuple[tuple[str, ...], set[str]]] = [
    # (parole chiave, habitat compatibili)
    (("montagn", "montan", "picco", "vetta", "cima", "rupe", "scoglier", "altopiano", "valico"),
     {"montano", "gelido", "foresta", "rurale", "cielo"}),
    (("sottomarin", "subacque", "fondale", "abiss", "oceano", "marin", "mare", "scogli", "barriera coral"),
     {"acquatico"}),
    (("fiume", "lago", "stagno", "costa", "spiaggia", "porto", "molo", "lacustre", "riva"),
     {"acquatico", "palude", "costiero", "rurale"}),
    (("palud", "acquitrin", "marsh", "torbier", "pantano"),
     {"palude", "acquatico", "foresta"}),
    (("foresta", "bosco", "boscaglia", "giungla", "selva", "radura", "albero", "fronde", "sottobosco"),
     {"foresta", "rurale", "montano"}),
    (("deserto", "dune", "sabbia", "arido", "canyon", "savana", "steppa", "badland"),
     {"desertico", "rurale"}),
    (("nev", "ghiacc", "artic", "polar", "tundra", "gelo", "glacial", "iceberg"),
     {"gelido", "montano"}),
    (("grotta", "cavern", "sotterran", "cripta", "fogn", "tunnel", "minier", "catacomb", "dungeon", "sottosuolo", "cunicol"),
     {"sotterraneo", "urbano"}),
    (("citt", "urban", "strada", "vicolo", "quartiere", "metropoli", "slum", "piazza", "periferia"),
     {"urbano", "sotterraneo", "interno"}),
    (("edifici", "stanza", "corridoio", "interno", "magazzin", "laborator", "base", "stazione", "astronav", "bunker", "complesso", "struttura", "nave spaziale", "modulo", "hangar", "raffineria", "impianto", "rovine al chiuso"),
     {"interno", "urbano"}),
    (("pianur", "prateri", "campagn", "rurale", "collin", "villaggio", "podere", "fattoria", "pascolo"),
     {"rurale", "foresta"}),
]


def habitats_for_environment(environment: str) -> set[str]:
    """Mappa un ambiente (testo libero: environment_type, tag scena, nome nodo…)
    sull'insieme degli habitat plausibili. Vuoto = ambiente non riconosciuto →
    nessun filtro (comportamento neutro)."""
    text = (environment or "").lower()
    if not text:
        return set()
    habs: set[str] = set()
    for keywords, mapped in _ENVIRONMENT_HABITATS:
        if any(k in text for k in keywords):
            habs |= mapped
    return habs


def creatures_for_genre(genre: str, max_threat: Optional[int] = None,
                        environment: str = "") -> list[dict]:
    """Creature plausibili per il genere (via le sue ere), opzionalmente limitate
    a una soglia di pericolosità e all'ambiente (habitat).

    Coerenza ambientale: se ``environment`` è riconoscibile (es. "montagna",
    "fondale marino", "stazione spaziale"), si escludono le creature il cui
    ``habitats`` non è compatibile — niente squalo in montagna. Le creature SENZA
    ``habitats`` (umanoidi, non-morti, macchine, costrutti…) sono ubique e passano
    sempre. Il filtro degrada con grazia: se azzererebbe il pool, viene ignorato."""
    genre = (genre or "").strip().lower().replace("-", "_").replace(" ", "_")
    eras = set(GENRE_ERA_MAP.get(genre, [ERA_MODERN]))
    out = [c for c in CREATURE_TABLE if eras.intersection(c["eras"])]
    if max_threat is not None:
        out = [c for c in out if c["threat"] <= max_threat]
    if environment:
        habs = habitats_for_environment(environment)
        if habs:
            coherent = [
                c for c in out
                if not c.get("habitats") or habs.intersection(c["habitats"])
            ]
            if coherent:  # solo se resta qualcosa: mai svuotare il pool
                out = coherent
    return out


def random_encounter_for(genre: str, max_threat: Optional[int] = None,
                         rng: Optional[random.Random] = None,
                         environment: str = "") -> Optional[dict]:
    """Pesca una creatura casuale appropriata al genere e all'ambiente (None se
    nessuna)."""
    pool = creatures_for_genre(genre, max_threat, environment=environment)
    if not pool:
        return None
    return (rng or random).choice(pool)


def creature_to_entity_dict(creature: dict, entity_id: str, zone: str = "minaccia") -> dict:
    """Converte una voce del bestiario in kwargs compatibili con SceneEntity."""
    return {
        "id": entity_id,
        "name": creature["name"],
        "type": "enemy",
        "zone": zone,
        "hp": creature["hp"],
        "max_hp": creature["hp"],
        "dr": creature.get("dr", 0),
        "attack_skill": creature.get("attack_skill", 10),
        "active_defense": creature.get("active_defense", 8),
        "damage_dice": creature.get("damage_dice", "1d-1"),
        "damage_type": creature.get("damage_type", "cr"),
        "morale": creature.get("morale", ""),
        "tags": ["nemico"] + list(creature.get("tags", [])),
    }
