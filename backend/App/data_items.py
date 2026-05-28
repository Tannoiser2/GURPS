"""
data_items.py — Catalogo oggetti avventura GURPS 4th Edition.

Ogni voce del catalogo definisce:
  - name: nome italiano (usato anche per il matching narrativo)
  - category: "misc" | "quest_item" | "key_item" | "consumable" | "armor" | "tool"
  - skill_bonuses: dict skill→modificatore (positivo = bonus, negativo = malus)
  - conditional_bonuses: [{"skill": ..., "bonus": ..., "tags": [...]}]
  - weight: peso in kg
  - cost: valore approssimato in moneta di gioco
  - notes: effetto narrativo / meccanico extra
  - aliases: nomi alternativi per il pattern matching narrativo

Il pattern matching in _extract_found_items_from_narrative usa `aliases + [name]`
per identificare oggetti nella narrativa del GM.
"""

from typing import Dict, List

# ─── Catalogo oggetti ─────────────────────────────────────────────────────────

ITEM_CATALOG: Dict[str, Dict] = {

    # ── Strumenti investigativi / tecnologici ──────────────────────────────

    "scanner": {
        "name": "Scanner",
        "category": "tool",
        "eras": ["scifi", "modern"],
        "skill_bonuses": {"ricerca": 2, "percezione": 1, "investigare": 2},
        "conditional_bonuses": [
            {"skill": "ricerca", "bonus": 1, "tags": ["tecnologico", "laboratorio", "navicella", "base"]},
        ],
        "weight": 0.5, "cost": 500,
        "notes": "+2 ricerca/investigare, +1 percezione. +1 extra in ambienti tecnologici.",
        "aliases": ["scanner portatile", "analizzatore", "lettore biometrico"],
    },

    "kit_medico": {
        "name": "Kit medico",
        "category": "tool",
        "eras": [],  # universale
        "skill_bonuses": {"pronto_soccorso": 2, "medicina": 1},
        "conditional_bonuses": [
            {"skill": "pronto_soccorso", "bonus": 1, "tags": ["ospedale", "infermeria", "laboratorio"]},
        ],
        "weight": 1.0, "cost": 150,
        "notes": "+2 pronto soccorso, +1 medicina. Permette di stabilizzare feriti gravi.",
        "aliases": ["kit di pronto soccorso", "borsa medica", "trousse medica", "kit di emergenza",
                    "kit chirurgico", "medikit"],
    },

    "grimaldelli": {
        "name": "Grimaldelli",
        "category": "tool",
        "eras": [],  # universale
        "skill_bonuses": {"grimaldello": 2, "infiltrazione": 1, "ladrocinio": 1},
        "weight": 0.1, "cost": 50,
        "notes": "+2 grimaldello, +1 infiltrazione. Senza: malus −4 ai tiri su serrature.",
        "aliases": ["set di grimaldelli", "kit grimaldelli", "attrezzi da scasso"],
    },

    "binocolo": {
        "name": "Binocolo",
        "category": "tool",
        "eras": ["modern", "horror", "western", "scifi", "steampunk"],
        "skill_bonuses": {"percezione": 2, "sorveglianza": 2},
        "conditional_bonuses": [
            {"skill": "percezione", "bonus": 1, "tags": ["aperto", "esterno", "citta", "deserto", "montagna"]},
        ],
        "weight": 0.5, "cost": 80,
        "notes": "+2 percezione/sorveglianza a distanza. +1 in spazi aperti.",
        "aliases": ["cannocchiale", "visore", "binocolo tattico", "binocolo militare"],
    },

    "computer_portatile": {
        "name": "Computer portatile",
        "category": "tool",
        "eras": ["modern", "scifi"],
        "skill_bonuses": {"informatica": 2, "ricerca": 1, "hacking": 2, "elettronica": 1},
        "weight": 1.5, "cost": 1000,
        "notes": "+2 informatica/hacking, +1 ricerca/elettronica.",
        "aliases": ["laptop", "tablet", "computer", "pc portatile", "terminale"],
    },

    "radio_tattica": {
        "name": "Radio tattica",
        "category": "tool",
        "eras": ["modern", "horror", "scifi"],
        "skill_bonuses": {"comunicazioni": 2, "coordinamento": 1},
        "weight": 0.3, "cost": 200,
        "notes": "+2 comunicazioni. Permette coordinamento a lunga distanza.",
        "aliases": ["radio", "walkie-talkie", "ricetrasmittente", "radio militare", "radio da campo"],
    },

    "kit_elettronico": {
        "name": "Kit elettronico",
        "category": "tool",
        "eras": ["modern", "scifi"],
        "skill_bonuses": {"elettronica": 2, "riparazione": 1, "sabotaggio": 1},
        "weight": 1.0, "cost": 300,
        "notes": "+2 elettronica, +1 riparazione/sabotaggio.",
        "aliases": ["kit elettronico", "attrezzi elettronici", "kit da tecnico"],
    },

    "kit_meccanico": {
        "name": "Kit meccanico",
        "category": "tool",
        "eras": [],  # universale (fabbri esistono in ogni epoca)
        "skill_bonuses": {"meccanica": 2, "riparazione": 2},
        "weight": 2.0, "cost": 200,
        "notes": "+2 meccanica/riparazione.",
        "aliases": ["kit meccanico", "cassetta degli attrezzi", "kit da riparazione", "attrezzi meccanici",
                    "arnesi", "attrezzi da fabbro"],
    },

    "kit_esplosivi": {
        "name": "Kit esplosivi",
        "category": "tool",
        "eras": ["modern", "scifi"],
        "skill_bonuses": {"esplosivi": 2, "sabotaggio": 1},
        "weight": 1.5, "cost": 500,
        "notes": "+2 esplosivi, +1 sabotaggio. Pericoloso senza training.",
        "aliases": ["kit da esplosivista", "materiale esplosivo", "attrezzi per esplosivi",
                    "cariche esplosive", "esplosivi artigianali"],
    },

    "occhiali_notturni": {
        "name": "Occhiali notturni",
        "category": "tool",
        "eras": ["modern", "scifi"],
        "skill_bonuses": {"percezione": 2, "furtivita": 1},
        "conditional_bonuses": [
            {"skill": "percezione", "bonus": 2, "tags": ["buio", "notte", "oscurità"]},
            {"skill": "furtivita", "bonus": 1, "tags": ["buio", "notte", "oscurità"]},
        ],
        "weight": 0.3, "cost": 600,
        "notes": "+2 percezione, +1 furtività. Eliminano penalità oscurità.",
        "aliases": ["visore notturno", "occhiali NVG", "night vision", "visore termico"],
    },

    "maschera_antigas": {
        "name": "Maschera antigas",
        "category": "tool",
        "eras": ["modern", "scifi"],
        "skill_bonuses": {},
        "conditional_bonuses": [
            {"skill": "resistenza", "bonus": 4, "tags": ["gas", "tossico", "contaminato", "biologico"]},
        ],
        "weight": 0.5, "cost": 100,
        "notes": "Immunità a gas/tossine ambientali. Lieve penalità visione periferica.",
        "aliases": ["respiratore", "maschera antigas", "maschera antigas militare", "filtri"],
    },

    # ── Equipaggiamento militare/moderno ──────────────────────────────────────

    "granata_frammentazione": {
        "name": "Granata a frammentazione",
        "category": "consumable",
        "eras": ["modern", "scifi", "horror"],
        "skill_bonuses": {},
        "weight": 1.0, "cost": 50,
        "notes": "4d [2d] cr ex. Raggio frammenti 10 yard. Una sola; LC 1.",
        "aliases": ["granata", "granata offensiva", "frag grenade", "bomba a mano"],
    },

    "granata_fumogena": {
        "name": "Granata fumogena",
        "category": "consumable",
        "eras": ["modern", "scifi"],
        "skill_bonuses": {},
        "weight": 1.0, "cost": 30,
        "notes": "Crea nube fumogena 4 yard × 2 round. Penalità −4 a mira in zona.",
        "aliases": ["granata fumo", "smoke grenade", "bomba fumogena", "candelotto fumogeno"],
    },

    "granata_stordente": {
        "name": "Granata stordente (flashbang)",
        "category": "consumable",
        "eras": ["modern", "scifi"],
        "skill_bonuses": {},
        "weight": 0.5, "cost": 60,
        "notes": "Flashbang: HT-5 o stordito per 1d secondi. Non letale. LC 2.",
        "aliases": ["flashbang", "granata accecante", "stun grenade", "granata non letale"],
    },

    "giubbotto_tattico": {
        "name": "Giubbotto tattico",
        "category": "armor",
        "eras": ["modern", "scifi"],
        "skill_bonuses": {"furtivita": -1},
        "armor_dr": 6,
        "armor_location": "torso",
        "weight": 7.0, "cost": 500,
        "notes": "DR 6 torso (DR 12 vs proiettili, DR 5 vs altro). TL7. Kevlar moderno.",
        "aliases": ["kevlar tattico", "tactical vest", "giubbotto balistico avanzato", "body armor tattico"],
    },

    "elmetto_balistico": {
        "name": "Elmetto balistico",
        "category": "armor",
        "eras": ["modern", "scifi"],
        "skill_bonuses": {},
        "armor_dr": 5,
        "armor_location": "testa",
        "weight": 3.0, "cost": 125,
        "notes": "DR 5 cranio. TL7; frammenti e schegge. Visiera +DR 1 faccia ($25, +1.5lb).",
        "aliases": ["casco balistico", "elmetto militare", "frag helmet", "casco kevlar"],
    },

    "esplosivi_demolizione": {
        "name": "Cariche esplosive (demolizione)",
        "category": "consumable",
        "eras": ["modern", "scifi"],
        "skill_bonuses": {"esplosivi": 2, "sabotaggio": 2},
        "weight": 1.0, "cost": 100,
        "notes": "C4 o equivalente. +2 esplosivi/sabotaggio. 6d cr ex per carica. LC 0.",
        "aliases": ["c4", "esplosivo plastico", "carica demolitiva", "esplosivi", "cariche esplosive"],
    },

    "razioni": {
        "name": "Razioni da campo",
        "category": "misc",
        "eras": [],  # universale
        "skill_bonuses": {},
        "weight": 1.0, "cost": 10,
        "notes": "Cibo per 3 giorni. Evita penalità da fame in sopravvivenza.",
        "aliases": ["razioni militari", "cibo", "provviste", "vitto", "razioni di sopravvivenza"],
    },

    "manette": {
        "name": "Manette",
        "category": "misc",
        "eras": ["modern", "horror", "western", "scifi"],
        "skill_bonuses": {},
        "weight": 0.5, "cost": 25,
        "notes": "DR 5 vs tentativi di fuga. Chiave necessaria. LC 4.",
        "aliases": ["ammanettare", "braccialetti", "ceppi", "handcuffs", "ferri"],
    },

    "documento_falso": {
        "name": "Documento falso",
        "category": "misc",
        "eras": ["modern", "horror", "western", "scifi"],
        "skill_bonuses": {"persuadere": 1, "infiltrazione": 2},
        "weight": 0.1, "cost": 500,
        "notes": "+2 infiltrazione, +1 persuadere quando presentato. Scoperta = guai seri.",
        "aliases": ["documenti falsi", "documento contraffatto", "passaporto falso",
                    "identità falsa", "papers falsi"],
    },

    # ── Documenti / Indizi ─────────────────────────────────────────────────

    "diario": {
        "name": "Diario",
        "category": "quest_item",
        "skill_bonuses": {"investigare": 1, "storia": 1},
        "weight": 0.3, "cost": 0,
        "notes": "+1 investigare/storia quando consultato. Contiene informazioni rilevanti.",
        "aliases": ["diario personale", "giornale", "quaderno", "taccuino", "memoriale", "diari"],
    },

    "documento_segreto": {
        "name": "Documento segreto",
        "category": "quest_item",
        "skill_bonuses": {"investigare": 2, "politica": 1},
        "weight": 0.1, "cost": 0,
        "notes": "+2 investigare quando analizzato. Può sbloccare thread narrativi.",
        "aliases": ["documento classificato", "file segreto", "rapporto segreto", "dossier",
                    "cartella", "fascicolo", "documenti"],
    },

    "mappa": {
        "name": "Mappa",
        "category": "quest_item",
        "skill_bonuses": {"orientamento": 2, "sopravvivenza": 1, "tattica": 1},
        "weight": 0.1, "cost": 0,
        "notes": "+2 orientamento, +1 sopravvivenza/tattica in esplorazione.",
        "aliases": ["mappa del luogo", "piantina", "cartina", "mappa tattica", "mappe"],
    },

    "chiave": {
        "name": "Chiave",
        "category": "key_item",
        "skill_bonuses": {},
        "weight": 0.05, "cost": 0,
        "notes": "Apre una serratura specifica. Nessun tiro richiesto.",
        "aliases": ["chiave magnetica", "chiave master", "pass", "badge", "tesserino",
                    "chiavetta", "smart card", "scheda di accesso", "card di accesso"],
    },

    "medaglione": {
        "name": "Medaglione",
        "category": "quest_item",
        "skill_bonuses": {"storia": 1, "investigare": 1},
        "weight": 0.1, "cost": 0,
        "notes": "Oggetto narrativo chiave. Può identificare persone o sbloccare eventi.",
        "aliases": ["medaglione antico", "ciondolo", "amuleto", "pendente", "talismano"],
    },

    "cristallo": {
        "name": "Cristallo",
        "category": "quest_item",
        "skill_bonuses": {},
        "weight": 0.2, "cost": 0,
        "notes": "Oggetto narrativo. Può essere un'energia, un codice o un artefatto.",
        "aliases": ["cristallo energetico", "gemma", "sfera di cristallo", "pietra"],
    },

    "fotografia": {
        "name": "Fotografia",
        "category": "quest_item",
        "skill_bonuses": {"investigare": 1},
        "weight": 0.01, "cost": 0,
        "notes": "+1 investigare se usata come prova.",
        "aliases": ["foto", "fotografia compromettente", "immagine", "scatto", "istantanea"],
    },

    "campione": {
        "name": "Campione",
        "category": "quest_item",
        "skill_bonuses": {"scienza": 2, "medicina": 1, "investigare": 1},
        "weight": 0.2, "cost": 0,
        "notes": "+2 scienza se analizzato in laboratorio.",
        "aliases": ["campione biologico", "campione chimico", "provetta", "reperto"],
    },

    # ── Sopravvivenza / Avventura ──────────────────────────────────────────

    "corda": {
        "name": "Corda",
        "category": "misc",
        "skill_bonuses": {"scalata": 2, "atletica": 1},
        "weight": 2.0, "cost": 20,
        "notes": "+2 scalata, +1 atletica su superfici verticali.",
        "aliases": ["corda di arrampicata", "fune", "cavo", "corda tattica"],
    },

    "torcia": {
        "name": "Torcia",
        "category": "misc",
        "skill_bonuses": {"percezione": 1},
        "conditional_bonuses": [
            {"skill": "percezione", "bonus": 2, "tags": ["buio", "oscurità", "grotta", "sotterraneo"]},
        ],
        "weight": 0.3, "cost": 10,
        "notes": "Elimina penalità oscurità in raggio 10m.",
        "aliases": ["torcia elettrica", "lampada", "lanterna", "faro", "luce"],
    },

    "kit_sopravvivenza": {
        "name": "Kit di sopravvivenza",
        "category": "misc",
        "skill_bonuses": {"sopravvivenza": 2, "orientamento": 1},
        "weight": 2.0, "cost": 100,
        "notes": "+2 sopravvivenza, +1 orientamento in ambienti ostili.",
        "aliases": ["kit survival", "zaino di sopravvivenza", "equipaggiamento survival"],
    },

    "mascheratura": {
        "name": "Kit travestimento",
        "category": "misc",
        "skill_bonuses": {"travestimento": 3, "infiltrazione": 1},
        "weight": 1.0, "cost": 200,
        "notes": "+3 travestimento, +1 infiltrazione.",
        "aliases": ["kit da travestimento", "set travestimento", "trucchi", "kit makeup"],
    },

    "veleno": {
        "name": "Veleno",
        "category": "consumable",
        "skill_bonuses": {},
        "weight": 0.05, "cost": 200,
        "notes": "Usato su cibo/armi. Richiede tiro Chimica o Medicina per applicare.",
        "aliases": ["veleno letale", "tossina", "sostanza tossica", "droga"],
    },

    "antidoto": {
        "name": "Antidoto",
        "category": "consumable",
        "skill_bonuses": {"medicina": 1},
        "weight": 0.05, "cost": 150,
        "notes": "Neutralizza un veleno specifico. +1 Medicina con cui è usato.",
        "aliases": ["antitossina", "siero", "contravveleno"],
    },

    # ── Armature storiche (GURPS 4e Basic Set) ────────────────────────────

    "armatura_cuoio": {
        "name": "Armatura di cuoio",
        "category": "armor",
        "eras": ["primitive", "medieval", "fantasy", "western", "steampunk"],
        "skill_bonuses": {"furtivita": -1},
        "armor_dr": 2,
        "armor_location": "torso",
        "weight": 10.0, "cost": 100,
        "notes": "DR 2 torso/inguine. −1 furtività. Protezione base medievale/fantasy.",
        "aliases": ["cuoio", "armatura cuoio", "giubbotto di cuoio", "leather armor"],
    },

    "cotta_maglia": {
        "name": "Cotta di maglia",
        "category": "armor",
        "eras": ["primitive", "medieval", "fantasy", "steampunk"],
        "skill_bonuses": {"furtivita": -2, "acrobazia": -1},
        "armor_dr": 4,
        "armor_location": "torso",
        "weight": 16.0, "cost": 150,
        "notes": "DR 4 torso. −2 furtività, −1 acrobazia. Buona protezione medievale.",
        "aliases": ["maglia", "cotta di maglia corta", "mail shirt", "usbergo"],
    },

    "cotta_maglia_lunga": {
        "name": "Cotta di maglia lunga",
        "category": "armor",
        "eras": ["primitive", "medieval", "fantasy", "steampunk"],
        "skill_bonuses": {"furtivita": -3, "acrobazia": -2, "atletica": -1},
        "armor_dr": 4,
        "armor_location": "totale",
        "weight": 25.0, "cost": 230,
        "notes": "DR 4 torso/inguine, DR 2 braccia (rivetti). Protezione medievale completa.",
        "aliases": ["haubert", "cotta lunga", "mail hauberk", "maglia lunga", "cotta di maglia intera"],
    },

    "corazza_piastre": {
        "name": "Corazza di piastre",
        "category": "armor",
        "eras": ["medieval", "fantasy", "steampunk"],
        "skill_bonuses": {"furtivita": -2, "acrobazia": -1},
        "armor_dr": 5,
        "armor_location": "torso",
        "weight": 18.0, "cost": 500,
        "notes": "DR 5 torso. Piastra d'acciaio; protezione eccellente contro armi da taglio.",
        "aliases": ["pettorale", "breastplate", "piastra pettorale", "corazza acciaio"],
    },

    "armatura_piastre_pesante": {
        "name": "Armatura di piastre pesante",
        "category": "armor",
        "eras": ["medieval", "fantasy"],
        "skill_bonuses": {"furtivita": -4, "acrobazia": -3, "atletica": -2},
        "armor_dr": 7,
        "armor_location": "torso",
        "weight": 45.0, "cost": 2300,
        "notes": "DR 7 torso/inguine. Armatura di piastre pesante; massima protezione medievale.",
        "aliases": ["armatura completa pesante", "heavy steel corselet", "piastre pesanti"],
    },

    # ── Scudi (GURPS 4e Basic Set) ────────────────────────────────────────

    "scudo_leggero": {
        "name": "Scudo leggero",
        "category": "misc",
        "eras": ["primitive", "medieval", "fantasy", "western", "steampunk"],
        "skill_bonuses": {"proteggere": 1, "difendere": 1},
        "weight": 3.0, "cost": 30,
        "notes": "DB +1 alla difesa in blocco. DR 2 contro colpi diretti allo scudo.",
        "aliases": ["scudo piccolo", "buckler", "round shield", "targa"],
    },

    "scudo_medio": {
        "name": "Scudo medio",
        "category": "misc",
        "eras": ["primitive", "medieval", "fantasy", "steampunk"],
        "skill_bonuses": {"proteggere": 2, "difendere": 1},
        "weight": 7.0, "cost": 60,
        "notes": "DB +2 alla difesa in blocco. DR 3 contro colpi diretti allo scudo.",
        "aliases": ["scudo", "kite shield", "heater shield", "scudo rotondo"],
    },

    "scudo_grande": {
        "name": "Scudo grande",
        "category": "misc",
        "eras": ["primitive", "medieval", "fantasy"],
        "skill_bonuses": {"proteggere": 3, "difendere": 2, "furtivita": -1},
        "weight": 15.0, "cost": 90,
        "notes": "DB +3 alla difesa in blocco. DR 4. −1 schivata. Copertura quasi totale.",
        "aliases": ["scudo torre", "tower shield", "pavese", "grande scudo"],
    },

    # ── Armature speciali ─────────────────────────────────────────────────

    "armatura_pesante": {
        "name": "Armatura pesante",
        "category": "armor",
        "eras": ["medieval", "fantasy"],
        "skill_bonuses": {"furtivita": -2, "acrobazia": -2, "atletica": -1},
        "armor_dr": 5,
        "armor_location": "totale",
        "weight": 15.0, "cost": 2000,
        "notes": "DR 5 totale. −2 furtività/acrobazia, −1 atletica.",
        "aliases": ["armatura completa", "corazza pesante", "piastra completa"],
    },

    "giubbotto_antiproiettile": {
        "name": "Giubbotto antiproiettile",
        "category": "armor",
        "eras": ["modern", "horror", "scifi"],
        "skill_bonuses": {"furtivita": -1},
        "armor_dr": 3,
        "armor_location": "torso",
        "weight": 3.0, "cost": 600,
        "notes": "DR 3 torso. −1 furtività.",
        "aliases": ["kevlar", "giubbotto balistico", "body armor", "antiproiettile"],
    },

    "esoscheletro": {
        "name": "Esoscheletro",
        "category": "armor",
        "eras": ["scifi"],
        "skill_bonuses": {"forza_bruta": 3, "resistenza": 2, "furtivita": -3, "acrobazia": -2},
        "armor_dr": 8,
        "armor_location": "totale",
        "weight": 30.0, "cost": 50000,
        "notes": "DR 8, +3 Forza bruta, +2 Resistenza. Pesante e rumoroso.",
        "aliases": ["power armor", "armatura potenziata", "esoscheletro militare"],
    },

}

# ─── Funzioni di ricerca ──────────────────────────────────────────────────────

def get_item(item_id: str) -> Dict | None:
    """Restituisce la voce catalogo per un item_id, o None."""
    return ITEM_CATALOG.get(item_id)


def item_skill_bonuses(item_id: str) -> Dict[str, int]:
    """Restituisce i skill_bonuses dell'item, o {} se non trovato."""
    entry = ITEM_CATALOG.get(item_id)
    return entry.get("skill_bonuses", {}) if entry else {}


def item_conditional_bonuses(item_id: str, scene_tags: List[str]) -> Dict[str, int]:
    """
    Restituisce i bonus condizionali attivi dati i tag scena.
    Somma quelli applicabili su tutti i bonus condizionali dell'item.
    """
    entry = ITEM_CATALOG.get(item_id)
    if not entry:
        return {}
    result: Dict[str, int] = {}
    for cb in entry.get("conditional_bonuses", []):
        required_tags = cb.get("tags", [])
        if any(t in scene_tags for t in required_tags):
            skill = cb["skill"]
            result[skill] = result.get(skill, 0) + cb["bonus"]
    return result


def build_equipment_item_from_catalog(item_id: str, source_location: str = "", turn: int = 0):
    """
    Costruisce un EquipmentItem a partire da una voce del catalogo.
    Import lazy per evitare import circolari.
    """
    from .models import EquipmentItem
    entry = ITEM_CATALOG.get(item_id)
    if not entry:
        return None
    import uuid
    return EquipmentItem(
        id=f"{item_id}_{uuid.uuid4().hex[:6]}",
        name=entry["name"],
        category=entry.get("category", "misc"),
        skill_bonuses=entry.get("skill_bonuses", {}),
        conditional_bonuses=entry.get("conditional_bonuses", []),
        weight=entry.get("weight", 0.0),
        cost=entry.get("cost", 0),
        notes=entry.get("notes", ""),
        armor_dr=entry.get("armor_dr", 0),
        armor_location=entry.get("armor_location", ""),
        source_location=source_location,
        found_at_turn=turn,
    )


# ─── Pattern matching narrativo ───────────────────────────────────────────────

# Frasi italiane che indicano il ritrovamento di un oggetto
FIND_PATTERNS = [
    r"trov[iao]",           # trovi, trova, trovano, trovate
    r"hai trovato",
    r"avete trovato",
    r"raccog[lh]",          # raccogli, raccoglie
    r"prender?[ie]",        # prendi, prende
    r"recuper[ia]",         # recuperi, recupera
    r"scopr[iao]",          # scopri, scopre
    r"ottieni",
    r"ricevi",
    r"ti viene consegnato",
    r"viene lasciato",
    r"è lì",
    r"giace",
    r"appoggiato",
    r"nascosto",
    r"dentro",
    r"all'interno",
    r"nel cassetto",
    r"sulla scrivania",
]

# Build alias → item_id lookup (case-insensitive)
_ALIAS_TO_ITEM_ID: Dict[str, str] = {}
for _iid, _idata in ITEM_CATALOG.items():
    _all_names = [_idata["name"].lower()] + [a.lower() for a in _idata.get("aliases", [])]
    for _alias in _all_names:
        _ALIAS_TO_ITEM_ID[_alias] = _iid


def narrative_text_to_item_ids(text: str) -> List[str]:
    """
    Scansiona il testo narrativo e restituisce gli item_id degli oggetti trovati.
    Usa word-boundary matching per evitare falsi positivi.
    """
    import re
    low = text.lower()
    found: List[str] = []
    # Cerca prima se c'è un verbo di ritrovamento nel testo
    has_find_verb = any(re.search(p, low) for p in FIND_PATTERNS)
    # Poi cerca tutti gli alias presenti
    for alias in sorted(_ALIAS_TO_ITEM_ID, key=len, reverse=True):
        if len(alias) < 4:
            continue
        pattern = r"(?<!\w)" + re.escape(alias) + r"(?!\w)"
        if re.search(pattern, low):
            item_id = _ALIAS_TO_ITEM_ID[alias]
            if item_id not in found:
                found.append(item_id)
    # Solo se c'è un verbo di ritrovamento ritorniamo gli oggetti trovati,
    # altrimenti potrebbero essere solo menzioni (es. "il nemico aveva uno scanner")
    # Per oggetti quest_item/key_item: li ritorniamo sempre anche senza verbo esplicito
    if has_find_verb:
        return found
    # Filtra solo quest/key items se non c'è verbo di ritrovamento
    return [iid for iid in found if ITEM_CATALOG[iid].get("category") in ("quest_item", "key_item")]
