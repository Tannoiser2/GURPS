SKILLS_BY_STAT: dict[str, list[str]] = {
    "forza": [
        "combattere", "resistere", "forzare", "proteggere",
        "trasportare", "intimidire", "lottare", "sopravvivere",
        "demolire", "nuotare", "arrampicarsi", "lanciare",
        "sollevare", "saltare",
    ],
    "agilita": [
        "schivare", "furtivita", "acrobazia", "rapidita",
        "mira", "guidare", "manualita", "infiltrarsi",
        "scassinare", "pedinare", "cavalcare", "mimetizzare",
        "equilibrio", "borseggiare",
    ],
    "intelligenza": [
        "investigare", "analizzare", "tecnologia", "medicina",
        "cultura", "strategia", "decifrare", "osservare",
        "ingegneria", "scienze", "legge", "occultismo",
        "seguire_tracce", "navigare", "sopravvivenza_urbana",
        "storia", "economia", "meccanica", "elettronica",
        "informatica", "astronomia", "biologia", "chimica",
        "fisica", "linguistica", "filosofia", "teologia",
        "politica",
    ],
    "empatia": [
        "persuadere", "ingannare", "intuire", "calmare",
        "ispirare", "curare", "comandare", "comunicare",
        "intrattenere", "etichetta", "recitazione", "parlare_in_pubblico",
        "interrogare", "seduzione",
    ],
}

SKILL_TO_EFFECT_TYPE: dict[str, str] = {
    # Forza
    "combattere":        "combattere",
    "resistere":         "difendere",
    "forzare":           "forzare",
    "proteggere":        "difendere",
    "trasportare":       "recuperare",
    "intimidire":        "negoziare",
    "lottare":           "combattere",
    "sopravvivere":      "recuperare",
    "demolire":          "forzare",
    "nuotare":           "infiltrarsi",
    "arrampicarsi":      "infiltrarsi",
    "lanciare":          "combattere",
    "sollevare":         "forzare",
    "saltare":           "infiltrarsi",
    # Agilità
    "schivare":          "infiltrarsi",
    "furtivita":         "infiltrarsi",
    "acrobazia":         "infiltrarsi",
    "rapidita":          "recuperare",
    "mira":              "combattere",
    "guidare":           "infiltrarsi",
    "manualita":         "forzare",
    "infiltrarsi":       "infiltrarsi",
    "scassinare":        "forzare",
    "pedinare":          "rilevare",
    "cavalcare":         "infiltrarsi",
    "mimetizzare":       "infiltrarsi",
    "equilibrio":        "infiltrarsi",
    "borseggiare":       "forzare",
    # Intelligenza
    "investigare":       "investigare",
    "analizzare":        "rilevare",
    "tecnologia":        "forzare",
    "medicina":          "stabilizzare",
    "cultura":           "decifrare",
    "strategia":         "difendere",
    "decifrare":         "decifrare",
    "osservare":         "rilevare",
    "ingegneria":        "forzare",
    "scienze":           "rilevare",
    "legge":             "investigare",
    "occultismo":        "decifrare",
    "seguire_tracce":    "rilevare",
    "navigare":          "infiltrarsi",
    "sopravvivenza_urbana": "recuperare",
    "storia":            "decifrare",
    "economia":          "negoziare",
    "meccanica":         "forzare",
    "elettronica":       "forzare",
    "informatica":       "decifrare",
    "astronomia":        "decifrare",
    "biologia":          "stabilizzare",
    "chimica":           "forzare",
    "fisica":            "forzare",
    "linguistica":       "decifrare",
    "filosofia":         "decifrare",
    "teologia":          "decifrare",
    "politica":          "negoziare",
    # Empatia
    "persuadere":        "negoziare",
    "ingannare":         "ingannare",
    "intuire":           "rilevare",
    "calmare":           "stabilizzare",
    "ispirare":          "recuperare",
    "curare":            "stabilizzare",
    "comandare":         "difendere",
    "comunicare":        "negoziare",
    "intrattenere":      "negoziare",
    "etichetta":         "negoziare",
    "recitazione":       "ingannare",
    "parlare_in_pubblico": "negoziare",
    "interrogare":       "investigare",
    "seduzione":         "negoziare",
}

LEGACY_EFFECT_TO_SKILL: dict[str, str] = {
    "analysis": "investigare",
    "scan": "osservare",
    "breach": "forzare",
    "defense": "proteggere",
    "move": "infiltrarsi",
    "stabilize": "curare",
    "diplomacy": "persuadere",
    "generic": "forzare",
    "demolition": "demolire",
    "lockpick": "scassinare",
    "security": "scassinare",
    "tail": "pedinare",
    "repair": "meccanica",
    "science": "scienze",
    "performance": "intrattenere",
    "protocol": "etichetta",
    "investigare": "investigare",
    "rilevare": "osservare",
    "decifrare": "decifrare",
    "forzare": "forzare",
    "combattere": "combattere",
    "infiltrarsi": "infiltrarsi",
    "difendere": "proteggere",
    "stabilizzare": "curare",
    "recuperare": "sopravvivere",
    "negoziare": "persuadere",
    "ingannare": "ingannare",
    "evocare": "occultismo",
}

VALID_SKILLS = {skill for skills in SKILLS_BY_STAT.values() for skill in skills}

# GURPS Lite (4ª ed.): ogni abilità ha un attributo cardine e una difficoltà E/M/D.
# Chi conosce l'abilità ha un livello memorizzato in Player.skills.
# Chi non la conosce tira contro (attributo_cardine - default_penalty), dove:
#   E (Facile)    → attributo - 4
#   M (Media)     → attributo - 5
#   D (Difficile) → attributo - 6
SKILL_INFO: dict[str, dict[str, str]] = {
    # ── Forza ──────────────────────────────────────────────────────────────────
    "combattere":    {"stat": "forza",        "difficulty": "M"},  # Rissa armata FO/M
    "resistere":     {"stat": "empatia",      "difficulty": "E"},  # tiro SA (Salute)
    "forzare":       {"stat": "forza",        "difficulty": "E"},  # sfondare porte FO/E
    "proteggere":    {"stat": "forza",        "difficulty": "M"},  # Scudo FO/M
    "trasportare":   {"stat": "forza",        "difficulty": "E"},  # FO/E
    "intimidire":    {"stat": "intelligenza", "difficulty": "M"},  # Intimidire IN/M
    "lottare":       {"stat": "forza",        "difficulty": "M"},  # Lottare FO/M
    "sopravvivere":  {"stat": "intelligenza", "difficulty": "M"},  # Sopravvivenza IN/M
    "demolire":      {"stat": "intelligenza", "difficulty": "M"},  # Esplosivi IN/M
    "nuotare":       {"stat": "empatia",      "difficulty": "E"},  # Nuotare SA/E (Salute)
    "arrampicarsi":  {"stat": "agilita",      "difficulty": "M"},  # Arrampicarsi DE/M
    "lanciare":      {"stat": "agilita",      "difficulty": "E"},  # Lanciare DE/E
    "sollevare":     {"stat": "forza",        "difficulty": "E"},  # FO/E
    "saltare":       {"stat": "agilita",      "difficulty": "E"},  # Saltare DE/E
    # ── Agilità ────────────────────────────────────────────────────────────────
    "schivare":      {"stat": "agilita",      "difficulty": "E"},  # Schivata DE/E
    "furtivita":     {"stat": "agilita",      "difficulty": "M"},  # Furtività DE/M
    "acrobazia":     {"stat": "agilita",      "difficulty": "D"},  # Acrobazia DE/D
    "rapidita":      {"stat": "agilita",      "difficulty": "E"},  # Scattare DE/E
    "mira":          {"stat": "agilita",      "difficulty": "E"},  # Arco/Pistola/Fucile DE/E
    "guidare":       {"stat": "agilita",      "difficulty": "M"},  # Pilotare DE/M
    "manualita":     {"stat": "agilita",      "difficulty": "M"},  # Manualità DE/M
    "infiltrarsi":   {"stat": "agilita",      "difficulty": "M"},  # Infiltrarsi DE/M
    "scassinare":    {"stat": "intelligenza", "difficulty": "M"},  # Scassinare/LT IN/M
    "pedinare":      {"stat": "intelligenza", "difficulty": "M"},  # Seguire/Sorvegliare IN/M
    "cavalcare":     {"stat": "agilita",      "difficulty": "M"},  # Cavalcare DE/M
    "mimetizzare":   {"stat": "intelligenza", "difficulty": "M"},  # Mimetizzarsi IN/M
    "equilibrio":    {"stat": "agilita",      "difficulty": "E"},  # Equilibrio DE/E
    "borseggiare":   {"stat": "agilita",      "difficulty": "M"},  # Borseggio DE/M
    # ── Intelligenza ───────────────────────────────────────────────────────────
    "investigare":   {"stat": "intelligenza", "difficulty": "M"},  # Investigare IN/M
    "analizzare":    {"stat": "intelligenza", "difficulty": "D"},  # Analisi IN/D
    "tecnologia":    {"stat": "intelligenza", "difficulty": "M"},  # Utente di Apparecchiature IN/M
    "medicina":      {"stat": "intelligenza", "difficulty": "D"},  # Medicina/LT IN/D
    "cultura":       {"stat": "intelligenza", "difficulty": "M"},  # Cultura IN/M
    "strategia":     {"stat": "intelligenza", "difficulty": "D"},  # Tattica IN/D
    "decifrare":     {"stat": "intelligenza", "difficulty": "D"},  # Criptografia IN/D
    "osservare":     {"stat": "intelligenza", "difficulty": "E"},  # Osservare IN/E
    "ingegneria":    {"stat": "intelligenza", "difficulty": "D"},  # Ingegneria IN/D
    "scienze":       {"stat": "intelligenza", "difficulty": "D"},  # Scienze IN/D
    "legge":         {"stat": "intelligenza", "difficulty": "M"},  # Legge IN/M
    "occultismo":    {"stat": "intelligenza", "difficulty": "M"},  # Occultismo IN/M
    "seguire_tracce": {"stat": "intelligenza","difficulty": "M"},  # Seguire Tracce IN/M
    "navigare":      {"stat": "intelligenza", "difficulty": "M"},  # Navigazione IN/M
    "sopravvivenza_urbana": {"stat": "intelligenza", "difficulty": "M"},  # IN/M
    "storia":        {"stat": "intelligenza", "difficulty": "M"},  # Storia IN/M
    "economia":      {"stat": "intelligenza", "difficulty": "M"},  # Economia IN/M
    "meccanica":     {"stat": "intelligenza", "difficulty": "M"},  # Meccanica/LT IN/M
    "elettronica":   {"stat": "intelligenza", "difficulty": "M"},  # Elettronica/LT IN/M
    "informatica":   {"stat": "intelligenza", "difficulty": "M"},  # Informatica IN/M
    "astronomia":    {"stat": "intelligenza", "difficulty": "D"},  # Astronomia IN/D
    "biologia":      {"stat": "intelligenza", "difficulty": "D"},  # Biologia IN/D
    "chimica":       {"stat": "intelligenza", "difficulty": "D"},  # Chimica IN/D
    "fisica":        {"stat": "intelligenza", "difficulty": "D"},  # Fisica IN/D
    "linguistica":   {"stat": "intelligenza", "difficulty": "M"},  # Linguistica IN/M
    "filosofia":     {"stat": "intelligenza", "difficulty": "M"},  # Filosofia IN/M
    "teologia":      {"stat": "intelligenza", "difficulty": "M"},  # Teologia IN/M
    "politica":      {"stat": "intelligenza", "difficulty": "M"},  # Politica IN/M
    # ── Empatia (SA) ───────────────────────────────────────────────────────────
    "persuadere":    {"stat": "empatia",      "difficulty": "M"},  # Diplomazia SA/M
    "ingannare":     {"stat": "intelligenza", "difficulty": "M"},  # Fast-Talk IN/M (manuale)
    "intuire":       {"stat": "intelligenza", "difficulty": "M"},  # Psicologia IN/M (manuale)
    "calmare":       {"stat": "empatia",      "difficulty": "M"},  # SA/M
    "ispirare":      {"stat": "empatia",      "difficulty": "M"},  # Leadership SA/M
    "curare":        {"stat": "intelligenza", "difficulty": "M"},  # Pronto Soccorso IN/M
    "comandare":     {"stat": "empatia",      "difficulty": "M"},  # Comandare SA/M
    "comunicare":    {"stat": "empatia",      "difficulty": "E"},  # SA/E
    "intrattenere":  {"stat": "empatia",      "difficulty": "M"},  # Intrattenimento SA/M
    "etichetta":     {"stat": "intelligenza", "difficulty": "E"},  # Savoir-Faire IN/E (manuale)
    "recitazione":   {"stat": "empatia",      "difficulty": "M"},  # Recitazione SA/M
    "parlare_in_pubblico": {"stat": "empatia","difficulty": "M"},  # Parlare in Pubblico SA/M
    "interrogare":   {"stat": "intelligenza", "difficulty": "M"},  # Interrogatorio IN/M
    "seduzione":     {"stat": "empatia",      "difficulty": "M"},  # Seduzione SA/M
}

DEFAULT_PENALTY_BY_DIFFICULTY: dict[str, int] = {"E": 4, "M": 5, "D": 6}

# Alcune abilita GURPS non hanno valore minimo. Il catalogo attuale usa ancora
# macro-skill ampie, quindi questa lista resta prudente e va raffinata quando
# aggiungeremo il catalogo GURPS completo in italiano.
NO_DEFAULT_SKILLS: set[str] = set()

# Skill tecnologiche: nel catalogo GURPS completo saranno salvate come
# "abilita/LT". Qui segnaliamo le macro-skill attuali che dipendono dal livello
# tecnologico della campagna/personaggio.
TECH_LEVEL_SKILLS: set[str] = {
    "tecnologia",
    "medicina",
    "scassinare",
    "ingegneria",
    "meccanica",
    "elettronica",
    "informatica",
    "astronomia",
    "biologia",
    "chimica",
    "fisica",
    "demolire",
    "guidare",
    "mira",
    "navigare",
}

# ── PR1.6: alias attributi stat ──────────────────────────────────────────────
# Chiavi interne: forza / agilita / intelligenza / empatia (zero rename nel codice).
# STAT_DISPLAY_NAME: chiave_interna → sigla GURPS ufficiale.
# STAT_ALIAS:        sigla.lower() / varianti → chiave_interna.

STAT_DISPLAY_NAME: dict[str, str] = {
    "forza":        "FO",
    "agilita":      "DE",
    "intelligenza": "IN",
    "empatia":      "SA",
}

STAT_ALIAS: dict[str, str] = {
    "fo": "forza", "forza": "forza",
    "de": "agilita", "agilita": "agilita", "destrezza": "agilita",
    "in": "intelligenza", "intelligenza": "intelligenza",
    "sa": "empatia", "empatia": "empatia", "salute": "empatia",
    # varianti inglesi per robustezza
    "st": "forza", "dx": "agilita", "iq": "intelligenza", "ht": "empatia",
}


def normalize_stat(name: str) -> str:
    """Converte sigla GURPS (FO/DE/IN/SA) o variante → chiave interna italiana."""
    return STAT_ALIAS.get(name.strip().lower(), name.strip().lower())


def stat_display(stat: str) -> str:
    """Sigla GURPS per un attributo (FO/DE/IN/SA). Fallback: nome interno."""
    return STAT_DISPLAY_NAME.get(stat, stat.upper())


# ── PR1.5: nomi GURPS ufficiali ───────────────────────────────────────────────
# Le chiavi interne rimangono in italiano minuscolo (zero regression).
# SKILL_DISPLAY_NAME: chiave_interna → nome visualizzato (GURPS ufficiale italiano).
# SKILL_ALIAS:        nome_gurps.lower() → chiave_interna  (accetta input utente/Claude).

SKILL_DISPLAY_NAME: dict[str, str] = {
    # Forza
    "combattere":    "Rissa",
    "resistere":     "Resistenza",
    "forzare":       "Forzare",
    "proteggere":    "Scudo",
    "trasportare":   "Trasportare",
    "intimidire":    "Intimidire",
    "lottare":       "Lottare",
    "sopravvivere":  "Sopravvivenza",
    "demolire":      "Esplosivi",
    "nuotare":       "Nuotare",
    "arrampicarsi":  "Arrampicarsi",
    "lanciare":      "Lanciare",
    "sollevare":     "Sollevare",
    "saltare":       "Saltare",
    # Agilità
    "schivare":      "Schivata",
    "furtivita":     "Furtività",
    "acrobazia":     "Acrobazia",
    "rapidita":      "Scattare",
    "mira":          "Armi a Gittata",
    "guidare":       "Pilotare",
    "manualita":     "Manualità",
    "infiltrarsi":   "Infiltrarsi",
    "scassinare":    "Scassinare",
    "pedinare":      "Sorvegliare",
    "cavalcare":     "Cavalcare",
    "mimetizzare":   "Mimetizzarsi",
    "equilibrio":    "Equilibrio",
    "borseggiare":   "Borseggio",
    # Intelligenza
    "investigare":   "Investigare",
    "analizzare":    "Analisi",
    "tecnologia":    "Tecnologia",
    "medicina":      "Medicina",
    "cultura":       "Cultura",
    "strategia":     "Tattica",
    "decifrare":     "Decifrare",
    "osservare":     "Osservare",
    "ingegneria":    "Ingegneria",
    "scienze":       "Scienze",
    "legge":         "Legge",
    "occultismo":    "Occultismo",
    "seguire_tracce": "Seguire Tracce",
    "navigare":      "Navigazione",
    "sopravvivenza_urbana": "Sopravvivenza Urbana",
    "storia":        "Storia",
    "economia":      "Economia",
    "meccanica":     "Meccanica",
    "elettronica":   "Elettronica",
    "informatica":   "Informatica",
    "astronomia":    "Astronomia",
    "biologia":      "Biologia",
    "chimica":       "Chimica",
    "fisica":        "Fisica",
    "linguistica":   "Linguistica",
    "filosofia":     "Filosofia",
    "teologia":      "Teologia",
    "politica":      "Politica",
    # Empatia
    "persuadere":    "Diplomazia",
    "ingannare":     "Raggiro",
    "intuire":       "Psicologia",
    "calmare":       "Calmare",
    "ispirare":      "Leadership",
    "curare":        "Pronto Soccorso",
    "comandare":     "Comandare",
    "comunicare":    "Comunicare",
    "intrattenere":  "Intrattenere",
    "etichetta":     "Galateo",
    "recitazione":   "Recitazione",
    "parlare_in_pubblico": "Parlare in Pubblico",
    "interrogare":   "Interrogatorio",
    "seduzione":     "Seduzione",
}

# Inverso: accetta nome GURPS (o varianti) → chiave interna
SKILL_ALIAS: dict[str, str] = {
    display.lower(): internal
    for internal, display in SKILL_DISPLAY_NAME.items()
}
# Alias extra per termini comuni
SKILL_ALIAS.update({
    "karate":              "combattere",
    "pistola":             "mira",
    "fucile":              "mira",
    "arco":                "mira",
    "balestra":            "mira",
    "spada":               "combattere",
    "ascia":               "combattere",
    "coltello":            "combattere",
    "pronto soccorso":     "curare",
    "diplomazia":          "persuadere",
    "fast-talk":           "ingannare",
    "fast talk":           "ingannare",
    "psicologia":          "intuire",
    "leadership":          "ispirare",
    "savoir-faire":        "etichetta",
    "tattica":             "strategia",
    "pilotare":            "guidare",
    "furtività":           "furtivita",
    "manualità":           "manualita",
    "scattare":            "rapidita",
    "seguire tracce":      "seguire_tracce",
    "sopravvivenza urbana": "sopravvivenza_urbana",
    "parlare in pubblico": "parlare_in_pubblico",
    "borseggio":           "borseggiare",
    "mimetizzarsi":        "mimetizzare",
    "arrampicare":         "arrampicarsi",
    "nuoto":               "nuotare",
    "interrogatorio":      "interrogare",
})


def normalize_skill(name: str) -> str:
    """Converte un nome skill (GURPS ufficiale, alias o chiave interna) → chiave interna.
    Restituisce il nome originale lowercased se non trovato (compatibilità forward)."""
    key = name.strip().lower()
    if key in SKILL_INFO:
        return key
    return SKILL_ALIAS.get(key, key)


def skill_display(skill: str) -> str:
    """Nome visualizzato GURPS per una skill. Fallback: nome interno capitalizzato."""
    return SKILL_DISPLAY_NAME.get(skill, skill.capitalize())


def skill_stat(skill: str) -> str:
    """Attributo cardine GURPS per una skill. Default: intelligenza (la più neutra)."""
    info = SKILL_INFO.get(skill)
    return info["stat"] if info else "intelligenza"


def skill_default_penalty(skill: str) -> int:
    """Penalità per tirare la skill 'da default' (senza addestramento)."""
    info = SKILL_INFO.get(skill)
    if not info:
        return 5
    return DEFAULT_PENALTY_BY_DIFFICULTY[info["difficulty"]]


def skill_has_default(skill: str) -> bool:
    """True se la skill puo essere usata senza addestramento."""
    return skill not in NO_DEFAULT_SKILLS


def skill_default_level(skill: str, stats: dict[str, int]) -> int | None:
    """Valore minimo GURPS Lite: attributo cardine -4/-5/-6, con Regola del 20.

    Ritorna None per abilita senza valore minimo.
    """
    if not skill_has_default(skill):
        return None
    info = SKILL_INFO.get(skill)
    if not info:
        return None
    stat_name = info.get("stat", "intelligenza")
    stat_val = min(int(stats.get(stat_name, 10)), 20)
    return stat_val - skill_default_penalty(skill)


def skill_is_tech_level(skill: str) -> bool:
    """True se la skill va trattata come dipendente dal Livello Tecnologico."""
    return skill in TECH_LEVEL_SKILLS

# Tabella verbo italiano → effect_type canonico.
# Il match avviene per radice (verbo troncato): "estra" copre estrarre/estrai/estratto/estrazione.
# Ordine: voci più specifiche/lunghe per prime (il primo match vince).
VERB_ROOT_TO_EFFECT: list[tuple[str, str]] = [
    # recuperare: prendere/portare via/estrarre
    ("recupera", "recuperare"), ("recuperar", "recuperare"),
    ("estrar", "recuperare"), ("estrai", "recuperare"), ("estraz", "recuperare"),
    ("preleva", "recuperare"), ("prender", "recuperare"), ("prendi", "recuperare"),
    ("ottener", "recuperare"), ("ottieni", "recuperare"),
    ("raccoglier", "recuperare"), ("raccogli", "recuperare"),
    ("portar via", "recuperare"), ("rubare", "recuperare"), ("ruba", "recuperare"),
    ("caricar", "recuperare"), ("trasportar", "recuperare"),
    # decifrare: codici, hack, scansioni dati
    ("decifra", "decifrare"), ("decodifi", "decifrare"),
    ("hackera", "decifrare"), ("hacker", "decifrare"),
    ("scansiona", "decifrare"), ("scansion", "decifrare"),
    ("decritta", "decifrare"), ("crittog", "decifrare"),
    ("violar", "decifrare"), ("bypass", "decifrare"),
    ("interpreta", "decifrare"), ("tradur", "decifrare"), ("traduc", "decifrare"),
    # investigare: cercare informazioni, esaminare
    ("investigar", "investigare"), ("investiga", "investigare"),
    ("indaga", "investigare"), ("indagar", "investigare"),
    ("esamina", "investigare"), ("esaminar", "investigare"),
    ("studia", "investigare"), ("studiar", "investigare"),
    ("analizza", "investigare"), ("analizzar", "investigare"),
    ("ispezion", "investigare"), ("ricerca", "investigare"), ("ricercar", "investigare"),
    ("interroga", "investigare"), ("interrogar", "investigare"),
    # rilevare: percepire, osservare a distanza, intuire
    ("osserva", "rilevare"), ("osservar", "rilevare"),
    ("rileva", "rilevare"), ("rilevar", "rilevare"),
    ("percepi", "rilevare"), ("intui", "rilevare"),
    ("scrutar", "rilevare"), ("scruta", "rilevare"),
    ("ascoltar", "rilevare"), ("ascolta", "rilevare"),
    ("annusa", "rilevare"), ("fiuta", "rilevare"),
    ("monitora", "rilevare"), ("monitor", "rilevare"),
    # negoziare: convincere, parlare, mediare
    ("negozi", "negoziare"), ("persuad", "negoziare"),
    ("convinc", "negoziare"), ("convince", "negoziare"),
    ("parla con", "negoziare"), ("parlar con", "negoziare"),
    ("dialoga", "negoziare"), ("dialogar", "negoziare"),
    ("mediar", "negoziare"), ("media tra", "negoziare"),
    ("contrattar", "negoziare"), ("trattar", "negoziare"),
    ("supplica", "negoziare"), ("implora", "negoziare"),
    ("intimi", "negoziare"),  # intimidire ha sapore negoziale
    # ingannare: bluff, distrazione, mentire
    ("inganna", "ingannare"), ("ingannar", "ingannare"),
    ("mentir", "ingannare"), ("mente", "ingannare"),
    ("bluffa", "ingannare"), ("simulare", "ingannare"), ("simula", "ingannare"),
    ("distrar", "ingannare"), ("distrai", "ingannare"),
    ("fingere", "ingannare"), ("fingi", "ingannare"),
    ("travestir", "ingannare"), ("travesti", "ingannare"),
    # combattere: attaccare, sparare, colpire
    ("combatter", "combattere"), ("combatti", "combattere"),
    ("attacca", "combattere"), ("attaccar", "combattere"),
    ("sparar", "combattere"), ("spara", "combattere"),
    ("colpir", "combattere"), ("colpi", "combattere"),
    ("aggredir", "combattere"), ("aggredi", "combattere"),
    ("ingaggia", "combattere"), ("affront", "combattere"),
    ("eliminar", "combattere"), ("elimina", "combattere"),
    ("neutralizz", "combattere"), ("abbatte", "combattere"), ("abbatter", "combattere"),
    # forzare: rompere, sfondare, scassinare
    ("forzar", "forzare"), ("forza ", "forzare"),
    ("sfonda", "forzare"), ("sfondar", "forzare"),
    ("scassina", "forzare"), ("scassinar", "forzare"),
    ("rompe", "forzare"), ("romper", "forzare"),
    ("demoli", "forzare"), ("distrugger", "forzare"), ("distruggi", "forzare"),
    ("svellere", "forzare"), ("strappa", "forzare"),
    ("smonta", "forzare"), ("smontar", "forzare"),
    ("collega ", "forzare"),  # collegare cavi/dispositivi è azione fisica
    ("riparar", "forzare"), ("ripara", "forzare"),
    ("sabotar", "forzare"), ("sabota", "forzare"),
    # infiltrarsi: muoversi furtivi, eludere
    ("infiltrar", "infiltrarsi"), ("infiltra", "infiltrarsi"),
    ("intrufol", "infiltrarsi"), ("sgattaiol", "infiltrarsi"),
    ("eludere", "infiltrarsi"), ("eludi", "infiltrarsi"),
    ("schivar", "infiltrarsi"), ("schiva", "infiltrarsi"),
    ("evitar", "infiltrarsi"), ("evita", "infiltrarsi"),
    ("nascondi", "infiltrarsi"), ("nascond", "infiltrarsi"),
    ("muoversi", "infiltrarsi"), ("avanzar", "infiltrarsi"),
    ("attraversar furtiv", "infiltrarsi"),
    # difendere: proteggere, coprire
    ("difender", "difendere"), ("difendi", "difendere"),
    ("protegger", "difendere"), ("proteggi", "difendere"),
    ("coprir", "difendere"), ("copri", "difendere"),
    ("resister", "difendere"), ("resisti", "difendere"),
    ("baricca", "difendere"), ("barricar", "difendere"),
    ("para ", "difendere"), ("parar", "difendere"),
    # stabilizzare: curare, soccorrere, calmare
    ("stabilizz", "stabilizzare"),
    ("curar", "stabilizzare"), ("cura ", "stabilizzare"),
    ("medicar", "stabilizzare"), ("medica", "stabilizzare"),
    ("soccorrer", "stabilizzare"), ("soccorri", "stabilizzare"),
    ("guarir", "stabilizzare"), ("guarisci", "stabilizzare"),
    ("rianima", "stabilizzare"), ("rianimar", "stabilizzare"),
    ("calmar", "stabilizzare"), ("calma ", "stabilizzare"),
    ("rassicur", "stabilizzare"),
    # evocare: rituale, magia, invocazione, occultismo
    ("evocar", "evocare"), ("evoca ", "evocare"),
    ("invocar", "evocare"), ("invoca", "evocare"),
    ("rituale", "evocare"), ("incantesimo", "evocare"),
    ("preghiera", "evocare"), ("pregar", "evocare"),
]


def infer_effect_type_from_text(*texts: str) -> str | None:
    """Cerca il primo verbo conosciuto nei testi forniti e restituisce l'effect_type associato.
    Ritorna None se nessun verbo è riconosciuto (in tal caso il chiamante mantiene quanto fornito).
    Il match è su radice (substring), case-insensitive.
    """
    blob = " ".join(t for t in texts if t).lower()
    if not blob:
        return None
    mechanical_targets = (
        "lucchett", "serratur", "chiavistell", "pannell", "consolle", "console",
        "terminale", "boccaport", "porta", "rampa",
    )
    if any(target in blob for target in mechanical_targets):
        if any(root in blob for root in ("sequenza", "codice", "cifr", "numero", "password", "led")):
            return "decifrare"
        if any(root in blob for root in ("colpir", "colpi", "sfond", "romp", "forzar", "apr", "sbloc", "scassin", "manomet", "smont")):
            return "forzare"
    # Cerca per ordine di lunghezza decrescente del trigger, così "raccoglier" batte "racc"
    for trigger, effect in sorted(VERB_ROOT_TO_EFFECT, key=lambda x: -len(x[0])):
        if trigger in blob:
            return effect
    return None


def reconcile_effect_type(text: str, declared_effect: str, valid_effects: set[str] | None = None) -> str:
    """Ritorna l'effect_type corretto per un'azione, dando priorità al verbo nel testo.
    - Se il testo contiene un verbo riconosciuto e il match diverge da declared_effect → vince il verbo.
    - Altrimenti mantiene declared_effect (se valido) o ricade su 'investigare'.
    """
    inferred = infer_effect_type_from_text(text)
    if inferred:
        return inferred
    if valid_effects is not None:
        return declared_effect if declared_effect in valid_effects else "investigare"
    return declared_effect or "investigare"


def skill_prompt_text() -> str:
    """Lista skill per il prompt Claude, con nomi GURPS ufficiali e chiave interna in parentesi."""
    lines = []
    for stat, skills in SKILLS_BY_STAT.items():
        skill_labels = []
        for s in skills:
            display = SKILL_DISPLAY_NAME.get(s, s)
            skill_labels.append(f"{display} ({s})" if display != s else s)
        lines.append(f"  {stat}: {', '.join(skill_labels)}")
    return "\n".join(lines)


def default_skill_for(stat: str, effect_type: str = "") -> str:
    legacy = LEGACY_EFFECT_TO_SKILL.get(effect_type)
    if legacy in SKILLS_BY_STAT.get(stat, []):
        return legacy
    # Fallback per effect_type moderno: trova la prima skill nello stat che mappa su quell'effect_type
    if effect_type:
        for skill in SKILLS_BY_STAT.get(stat, []):
            if SKILL_TO_EFFECT_TYPE.get(skill) == effect_type:
                return skill
    return (SKILLS_BY_STAT.get(stat) or ["investigare"])[0]
