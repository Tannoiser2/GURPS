from __future__ import annotations

import re
from copy import deepcopy


_GENRE_PROPS = {
    "fantasy": {
        "access": "chiave di ferro annerita",
        "document": "pergamena cerata con sigillo spezzato",
        "log": "registro del custode con pagina strappata",
        "cover": ["sarcofagi di pietra", "colonne spezzate", "altare incrinato", "bracieri rovesciati"],
        "hazards": ["pietre instabili", "rune che si accendono a impulsi"],
    },
    "sci_fi": {
        "access": "badge tecnico bruciato",
        "document": "Protocollo Sigma-7 stampato a meta",
        "log": "log di sicurezza cancellato alle 02:13 con credenziali anomale",
        "cover": ["rack server", "paratie blindate", "muletti elettrici", "condotti manutenzione"],
        "hazards": ["blackout intermittente", "sprinkler attivati"],
    },
    "detective_classico": {
        "access": "chiave graffiata con etichetta falsa",
        "document": "ricevuta piegata con orario corretto a penna",
        "log": "registro accessi con firma falsificata",
        "cover": ["scrivanie rovesciate", "archivi metallici", "vetrate opache", "scaffali pieni di fascicoli"],
        "hazards": ["folla curiosa", "telefono che squilla nel momento sbagliato"],
    },
    "mystery_horror": {
        "access": "chiave umida legata con filo rosso",
        "document": "pagina di diario macchiata di muffa",
        "log": "album fotografico con una data raschiata via",
        "cover": ["armadi pesanti", "specchi coperti", "letti ferrati", "casse inchiodate"],
        "hazards": ["porte che si chiudono da sole", "pavimento marcio"],
    },
    "ww2": {
        "access": "lasciapassare militare bruciacchiato",
        "document": "ordine cifrato con bordo strappato",
        "log": "registro radio con frequenza cancellata",
        "cover": ["sacchi di sabbia", "cassette munizioni", "muri crollati", "camion spento"],
        "hazards": ["colpi di artiglieria lontani", "fumo che riduce la vista"],
    },
    "action": {
        "access": "tessera magnetica piegata",
        "document": "dossier operativo con ultima pagina mancante",
        "log": "log CCTV esportato e subito cancellato",
        "cover": ["container metallici", "auto parcheggiate", "bancali di casse", "porte tagliafuoco"],
        "hazards": ["allarme silenzioso", "sistemi antincendio impazziti"],
    },
}


def _props(genre: str) -> dict:
    return _GENRE_PROPS.get(genre, _GENRE_PROPS["detective_classico"])


def _location_props(name: str, description: str = "", genre: str = "") -> tuple[list[str], list[str]]:
    blob = f"{name} {description}".lower()
    if not genre and any(w in blob for w in ["arpie", "ragno gigante", "orchetti", "lupi", "mago", "torre", "tesoro", "shado"]):
        genre = "fantasy"
    if any(w in blob for w in ["taverna", "locanda", "osteria", "saloon", "anello di ferro"]):
        return (
            ["tavoli ribaltabili", "bancone massiccio", "camino acceso", "ballatoio o scala interna"],
            ["vetri rotti sul pavimento", "clienti in panico"],
        )
    if any(w in blob for w in ["biblioteca", "archivio", "scriptorium", "monastero"]):
        return (
            ["scaffali alti come copertura", "tavoli di lettura", "scale mobili", "vetrine con manoscritti"],
            ["scaffali instabili", "pergamene infiammabili"],
        )
    if any(w in blob for w in ["bosco", "foresta", "radura", "giardino"]):
        return (
            ["tronchi caduti", "rocce muschiose", "radici affioranti", "cespugli fitti"],
            ["rovi che rallentano", "nebbia tra gli alberi"],
        )
    if any(w in blob for w in ["castello", "fortezza", "torre", "cortile", "bastione"]):
        return (
            ["muretti merlati", "scale di pietra", "portoni ferrati", "alcove difensive"],
            ["feritoie sorvegliate", "pietre sconnesse"],
        )
    if any(w in blob for w in ["cripta", "tomba", "catacomb", "sepol", "necrop", "sarcof"]):
        return (
            ["sarcofagi di pietra", "colonne spezzate", "altare incrinato", "bracieri rovesciati"],
            ["pietre instabili", "rune che si accendono a impulsi"],
        )
    props = _props(genre)
    return list(props["cover"]), list(props["hazards"])


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(text or "").lower()).strip("_")[:32] or "item"


def _location_name(raw: dict, fallback: str = "Scena iniziale") -> str:
    return str(raw.get("source_location") or raw.get("location") or raw.get("name") or fallback).strip() or fallback


def _is_abstract(text: str) -> bool:
    low = str(text or "").lower()
    abstract = [
        "contraddizione", "copertura", "procedura", "incompleta", "traccia",
        "accesso laterale", "indizio strutturale", "prova decisiva", "elemento",
        "coperture coerenti", "soluzione", "minaccia", "informazione",
        "prova concreta", "testimonianza utile", "contraddizione verificabile",
        "leva finale", "indizio", "dettaglio chiave",
    ]
    return any(a in low for a in abstract) or len(low.split()) <= 2


def _name_hint(*values: str) -> str:
    blob = " ".join(str(v or "") for v in values)
    names = re.findall(r"\b[A-ZÀ-Ü][a-zà-ÿ]{2,}(?:\s+[A-ZÀ-Ü][a-zà-ÿ]{2,}){0,2}\b", blob)
    ignored = {"Foresta", "Capanna", "Camera", "Casa", "Villaggio", "Rito", "Rituale", "Dove", "Come", "Indizio", "Prova", "Testimonianza"}
    for name in names:
        if name.split()[0] not in ignored:
            return name
    return ""


def _location_hint(location: str) -> str:
    loc = str(location or "").strip()
    if not loc:
        return "nella scena"
    return loc if len(loc) <= 48 else loc[:45].rstrip() + "..."


def _semantic_concrete_clue(label: str, text: str, reveals: str, loc_name: str, clue_type: str, genre: str) -> tuple[str, str, str, list[str]]:
    """Crea un oggetto/segno giocabile senza usare lo stesso prop generico per ogni indizio."""
    blob = f"{label} {text} {reveals} {loc_name}".lower()
    person = _name_hint(label, text, reveals, loc_name)
    loc = _location_hint(loc_name)
    ctype = str(clue_type or "").lower()

    if ctype == "testimony" or any(w in blob for w in ["testimon", "veggente", "racconta", "dice", "confessa", "ha visto"]):
        subject = person or ("la Veggente" if "veggente" in blob else "il testimone")
        concrete = f"Testimonianza di {subject}"
        implication = reveals or f"{subject} collega {loc} alla pista attiva"
        actions = ["interrogare il testimone", "verificare il racconto sul posto", "cercare una contraddizione concreta"]
        return concrete, implication, "testimony", actions

    if any(w in blob for w in ["diario", "giornale", "appunti", "quaderno"]):
        subject = person or "chi lo ha scritto"
        concrete = f"Diario di {subject}" if "diario" not in label.lower() else label
        implication = reveals or f"gli appunti indicano dove {subject} stava andando"
        actions = ["leggere le ultime pagine", "confrontare date e luoghi", "cercare nomi ricorrenti"]
        return concrete, implication, "document", actions

    if any(w in blob for w in ["ritual", "rito", "cerchio", "sigillo", "portale", "officiante", "sacrificio"]):
        if any(w in blob for w in ["foresta", "bosco", "radura", "alberi"]):
            concrete = f"Cerchio di radici bruciate in {loc}"
        else:
            concrete = f"Segni rituali incompleti in {loc}"
        implication = reveals or "mostra quale parte del rito puo essere interrotta"
        actions = ["esaminare il cerchio", "cancellare o alterare un segno", "seguire la traccia verso l'officiante"]
        return concrete, implication, "physical_evidence", actions

    if any(w in blob for w in ["magie antiche", "magia antica", "rune", "arcano", "incantesimo"]):
        concrete = f"Rune incise su pietra o corteccia in {loc}"
        implication = reveals or "prova che la magia non e casuale ma vincolata a un luogo preciso"
        actions = ["decifrare le rune", "confrontarle con una leggenda locale", "cercare il punto dove convergono"]
        return concrete, implication, "location_detail", actions

    if any(w in blob for w in ["forze oscure", "tenebre", "ombra", "corruzione", "sangue", "cenere"]):
        concrete = f"Cenere fredda e impronte annerite in {loc}"
        implication = reveals or "collega la scena a una presenza ostile concreta"
        actions = ["seguire le impronte", "analizzare la cenere", "proteggersi prima di avanzare"]
        return concrete, implication, "physical_evidence", actions

    if any(w in blob for w in ["movimenti", "pedin", "si sposta", "non ha condiviso", "nasconde"]):
        subject = person or "il sospetto"
        concrete = f"Movimenti sospetti di {subject}"
        implication = reveals or f"{subject} conosce un accesso o un fatto non dichiarato"
        actions = ["pedinare il sospetto", "confrontarlo con discrezione", "controllare dove si e diretto"]
        return concrete, implication, "behavior", actions

    if any(w in blob for w in ["mappa", "posizione", "luogo esatto", "sentiero", "percorso"]):
        concrete = f"Traccia di percorso verso {loc}"
        implication = reveals or "indica una rotta giocabile verso la prossima zona"
        actions = ["seguire la traccia", "cercare punti di riferimento", "preparare una via di ritorno"]
        return concrete, implication, "location_detail", actions

    return "", "", clue_type or "physical_evidence", []


def concretize_clue(clue: dict, *, genre: str = "", locations: list[dict] | None = None, actors: list[dict] | None = None) -> dict:
    clue = dict(clue or {})
    # LLM-extracted clues are already concrete and grounded in the source text.
    # Don't rewrite their label/text — only backfill missing runtime fields.
    if clue.get("llm_extracted"):
        clue.setdefault("immediate_information", clue.get("text") or clue.get("label") or "")
        clue.setdefault("hidden_implication", clue.get("reveals") or "")
        clue.setdefault("unlocks", [clue.get("thread_id") or "thread"])
        clue.setdefault("possible_actions", ["esaminare il dettaglio", "confrontarlo con un testimone"])
        clue.setdefault("wrong_interpretations", ["scambiarlo per dettaglio d'atmosfera"])
        clue["source_location"] = clue.get("source_location") or clue.get("location") or (locations or [{}])[0].get("name", "")
        clue["location"] = clue.get("location") or clue["source_location"]
        return clue
    props = _props(genre)
    label = str(clue.get("label") or clue.get("text") or clue.get("id") or "Indizio")
    text = str(clue.get("text") or label)
    reveals = str(clue.get("reveals") or clue.get("payoff") or "")
    loc_name = _location_name(clue, (locations or [{}])[0].get("name", "Scena iniziale"))
    clue_type = str(clue.get("type") or "").lower()
    low = f"{label} {text} {reveals}".lower()

    if clue.get("source_status") == "inferred" and "dettaglio chiave" in low:
        loc_hint = _location_hint(loc_name)
        if any(w in low for w in ["arpie", "ragno", "lupi", "orchetti", "teihiihan", "terror", "mostro", "creatura"]):
            clue["label"] = f"Tracce del pericolo in {loc_hint}"
            clue["type"] = "location_detail"
            clue["possible_actions"] = list(dict.fromkeys(clue.get("possible_actions") or ["leggere le tracce", "prepararsi allo scontro", "cercare una via laterale"]))
        elif any(w in low for w in ["sumar", "nasconde", "pelli", "tesoro", "finale"]):
            clue["label"] = f"Segno della rivelazione finale in {loc_hint}"
            clue["type"] = "physical_evidence"
            clue["possible_actions"] = list(dict.fromkeys(clue.get("possible_actions") or ["esaminare il dettaglio", "collegarlo alle prove precedenti", "sbloccare il confronto finale"]))
        else:
            clue["label"] = f"Dettaglio canonico in {loc_hint}"
            clue["type"] = clue.get("type") or "location_detail"
            clue["possible_actions"] = list(dict.fromkeys(clue.get("possible_actions") or ["esaminare il dettaglio", "confrontarlo con la mappa", "seguirne le conseguenze"]))
        clue["text"] = clue["label"]
        clue["source_location"] = clue.get("source_location") or clue.get("location") or loc_name
        clue["location"] = clue.get("location") or clue["source_location"]
        clue["immediate_information"] = clue.get("immediate_information") or clue["text"]
        clue["hidden_implication"] = clue.get("hidden_implication") or reveals or "collega questa scena alla progressione canonica del modulo"
        clue["reveals"] = clue.get("reveals") or clue["hidden_implication"]
        clue["unlocks"] = list(dict.fromkeys(clue.get("unlocks") or [clue.get("thread_id") or "thread"]))
        clue["payoff"] = clue.get("payoff") or f"Sblocca: {', '.join(clue['unlocks'][:2])}"
        clue["wrong_interpretations"] = list(dict.fromkeys(clue.get("wrong_interpretations") or ["trattarlo come colore locale", "saltare direttamente al finale senza collegarlo alle altre prove"]))
        return clue

    semantic_label, semantic_implication, semantic_type, semantic_actions = _semantic_concrete_clue(label, text, reveals, loc_name, clue_type, genre)

    if semantic_label and (_is_abstract(label) or _is_abstract(text) or "pergamena cerata" in low or clue_type == "testimony"):
        concrete_label = semantic_label
        implication = semantic_implication
        unlocks = [clue.get("thread_id") or "thread"]
        actions = semantic_actions
        inferred_type = semantic_type
    elif "access" in low or "passaggio" in low or "tunnel" in low or "laterale" in low:
        concrete_label = f"{props['access']} vicino all'accesso di servizio"
        implication = "qualcuno ha usato un percorso secondario non dichiarato"
        unlocks = ["route_tunnel_laterale", loc_name]
        actions = ["analizzare il badge o la chiave", "controllare i log di accesso", "seguire i segni verso il passaggio"]
        inferred_type = "physical_evidence"
    elif "procedura" in low or "protocollo" in low or "ritual" in low or "codice" in low:
        concrete_label = semantic_label or props["document"]
        implication = "la procedura finale esiste ma manca un passaggio da verificare sul posto"
        unlocks = ["finale_method"]
        actions = ["ricostruire la pagina mancante", "confrontare il documento con la scena finale", "interrogare chi lo ha stampato"]
        inferred_type = semantic_type or "document"
    elif "contradd" in low or "copertura" in low or "fals" in low or "responsabile" in low:
        concrete_label = props["log"]
        implication = "la versione ufficiale e stata alterata da qualcuno con accesso interno"
        unlocks = ["antagonist_pressure", "thread_responsabile"]
        actions = ["verificare la firma", "confrontare gli orari", "interrogare il responsabile dei registri"]
        inferred_type = "document"
    else:
        concrete_label = label if not _is_abstract(label) else (semantic_label or f"Dettaglio verificabile in {loc_name}")
        implication = reveals or "collega la scena a una pista gia presente nel canovaccio"
        unlocks = [clue.get("thread_id") or "thread"]
        actions = semantic_actions or ["esaminare il reperto", "confrontarlo con un testimone", "cercare tracce nella location"]
        inferred_type = semantic_type or clue.get("type") or "physical_evidence"

    if _is_abstract(label) or _is_abstract(text):
        clue["label"] = concrete_label
        clue["text"] = concrete_label
    else:
        clue["label"] = label
        clue["text"] = text
    clue["source_location"] = clue.get("source_location") or clue.get("location") or loc_name
    clue["location"] = clue.get("location") or clue["source_location"]
    clue["type"] = inferred_type or clue.get("type") or ("document" if "document" in concrete_label.lower() or "protocollo" in concrete_label.lower() else "physical_evidence")
    clue["immediate_information"] = clue.get("immediate_information") or clue["text"]
    clue["hidden_implication"] = clue.get("hidden_implication") or implication
    clue["unlocks"] = list(dict.fromkeys(clue.get("unlocks") or unlocks))
    clue["possible_actions"] = list(dict.fromkeys(clue.get("possible_actions") or actions))
    clue["wrong_interpretations"] = list(dict.fromkeys(clue.get("wrong_interpretations") or ["scambiarlo per semplice dettaglio di scena", "attribuirlo al primo sospetto senza verifica"]))
    clue["payoff"] = clue.get("payoff") or f"Sblocca: {', '.join(clue['unlocks'][:2])}"
    clue["reveals"] = clue.get("reveals") or clue["hidden_implication"]
    return clue


def dedupe_clues(clues: list[dict]) -> list[dict]:
    seen: dict[str, int] = {}
    result = []
    for clue in clues:
        clue = dict(clue or {})
        key = str(clue.get("label") or "").strip().lower()
        seen[key] = seen.get(key, 0) + 1
        if key and seen[key] > 1:
            loc = _location_hint(clue.get("source_location") or clue.get("location") or "")
            reveal = str(clue.get("reveals") or clue.get("hidden_implication") or "").strip()
            if reveal:
                clue["label"] = f"{clue.get('label')} — {reveal[:42]}"
            elif loc:
                clue["label"] = f"{clue.get('label')} — {loc}"
        result.append(clue)
    return result


def concretize_location_features(location: dict, *, genre: str = "", clues: list[dict] | None = None) -> dict:
    loc = dict(location or {})
    name = str(loc.get("name") or "Location")
    default_features, default_hazards = _location_props(name, str(loc.get("description") or ""), genre)
    features = list(loc.get("concrete_features") or loc.get("features") or [])
    if len(features) < 3:
        features = list(dict.fromkeys(features + default_features))[:4]
    hazards = list(loc.get("hazards") or [])
    if len(hazards) < 2:
        hazards = list(dict.fromkeys(hazards + default_hazards))[:2]
    exits = list(loc.get("exits") or [])
    if len(exits) < 2:
        exits = list(dict.fromkeys(exits + ["corridoio principale", "passaggio laterale o manutenzione"]))[:2]
    clue_slots = list(loc.get("clue_slots") or [])
    loc_clues = [
        c.get("id") for c in (clues or [])
        if c.get("source_location") and (c["source_location"].lower() in name.lower() or name.lower() in c["source_location"].lower())
    ]
    clue_slots = list(dict.fromkeys(clue_slots + [c for c in loc_clues if c]))[:4]
    tactical = list(loc.get("tactical_features") or [])
    if len(tactical) < 3:
        tactical = list(dict.fromkeys(tactical + features[:3]))
    loc["visual_identity"] = loc.get("visual_identity") or f"{name}: {', '.join(features[:3])}"
    loc["gameplay_function"] = loc.get("gameplay_function") or ("finale/confronto" if loc.get("has_combat_potential") else "indagine e orientamento")
    loc["concrete_features"] = features
    loc["hazards"] = hazards
    loc["exits"] = exits
    loc["locked_paths"] = list(loc.get("locked_paths") or (["accesso finale bloccato finche non emerge l'indizio corretto"] if loc.get("access_state") in {"locked", "blocked"} else []))
    loc["clue_slots"] = clue_slots
    loc["tactical_features"] = tactical
    tactical_map = dict(loc.get("tactical_map") or {})
    tactical_trigger = str(tactical_map.get("trigger") or loc.get("description") or "").lower()
    tactical_role = str(tactical_map.get("role") or "").lower()
    wants_tactical = bool(loc.get("has_combat_potential") or tactical_map.get("enabled") or tactical_role in {"hot_zone", "finale", "boss", "combat"})
    if not wants_tactical and tactical_role == "neutral" and not any(w in tactical_trigger for w in ["scontro", "combatt", "agguato", "confronto", "assalto", "fuga"]):
        tactical_map["enabled"] = False
        loc["tactical_map"] = tactical_map
    elif wants_tactical:
        tactical_map["enabled"] = True
        tactical_map["features"] = list(dict.fromkeys(tactical_map.get("features") or tactical))
        tactical_map["hazards"] = list(dict.fromkeys(tactical_map.get("hazards") or hazards))
        tactical_map.setdefault("trigger", "quando la scena porta a un confronto diretto o a una fuga sotto pressione")
        loc["tactical_map"] = tactical_map
    return loc


def concretize_npc_goal(actor: dict, *, genre: str = "", clues: list[dict] | None = None, locations: list[dict] | None = None) -> dict:
    actor = dict(actor or {})
    name = actor.get("name") or "PNG"
    role = str(actor.get("role") or "neutral").lower()
    final_loc = (locations or [{}])[-1].get("name", "zona finale")
    clue = (clues or [{}])[0]
    actor["goal"] = actor.get("goal") or actor.get("motivation") or f"controllare {final_loc} prima che la squadra usi {clue.get('label', 'la prova')}"
    actor["fear"] = actor.get("fear") or f"che {clue.get('label', 'una prova concreta')} riveli il suo ruolo"
    actor["current_plan"] = actor.get("current_plan") or f"bloccare l'accesso a {final_loc} e spostare le prove"
    actor["fallback_plan"] = actor.get("fallback_plan") or f"ritirarsi verso {final_loc} usando un percorso secondario"
    actor["resources"] = list(dict.fromkeys(actor.get("resources") or ["accessi", "contatti", "tempo"]))
    actor["knows"] = list(dict.fromkeys(actor.get("knows") or [clue.get("id", "clue_core")]))
    actor["wants"] = list(dict.fromkeys(actor.get("wants") or [actor["goal"]]))
    actor["avoids"] = list(dict.fromkeys(actor.get("avoids") or [actor["fear"]]))
    if not actor.get("pressure_response"):
        if "antagon" in role:
            actor["pressure_response"] = {
                "low": "depista e osserva",
                "medium": "manda oppositori o chiude un accesso",
                "high": "distrugge una prova o sposta un ostaggio/testimone",
                "critical": "fugge verso la zona finale forzando il confronto",
            }
        elif "witness" in role or "testim" in role:
            actor["pressure_response"] = {
                "low": "esita",
                "medium": "si nasconde",
                "high": "cerca protezione dalla squadra",
                "critical": "scompare lasciando una traccia incompleta",
            }
        else:
            actor["pressure_response"] = {
                "low": "collabora se rassicurato",
                "medium": "chiede una prova concreta",
                "high": "si ritira o protegge le proprie risorse",
                "critical": "sceglie una parte e cambia la scena",
            }
    actor["reaction_table"] = actor.get("reaction_table") or {
        "helped": "offre accesso, informazione o copertura",
        "threatened": "resiste o chiama rinforzi",
        "deceived": "collabora finche non nota la contraddizione",
        "exposed": "rivela il proprio segreto o fugge",
    }
    return actor


def concretize_clock_events(clock: dict, *, genre: str = "", antagonist: str = "la minaccia") -> dict:
    clock = dict(clock or {})
    label = clock.get("label") or clock.get("name") or f"{antagonist} avanza il piano"
    max_value = int(clock.get("max_value") or clock.get("max") or 6)
    templates = [
        "allarme interno attivato",
        "accessi ordinari sospesi",
        "prova secondaria rimossa dalla scena",
        f"un testimone viene cercato dagli uomini di {antagonist}",
        "percorso laterale minacciato o sigillato",
        f"{antagonist} raggiunge la zona finale",
        "prove trasferite o rese instabili",
        "piano completato se nessuno interviene",
    ]
    steps = []
    for idx in range(1, max_value + 1):
        text = templates[min(idx - 1, len(templates) - 1)]
        steps.append({
            "step": idx,
            "event": text,
            "world_state_change": text,
            "scene_prompt": f"Mostra in scena: {text}.",
            "possible_player_response": "intervenire, aggirare il costo, proteggere una prova o cambiare percorso",
        })
    clock["label"] = label
    clock["max_value"] = max_value
    clock["steps"] = clock.get("steps") or steps
    clock["consequence"] = clock.get("consequence") or steps[-1]["world_state_change"]
    clock["on_complete"] = clock.get("on_complete") or clock["consequence"]
    return clock


def concretize_finale_condition(finale: dict, *, required_clues: list[str] | None = None, final_location: str = "zona finale") -> dict:
    finale = dict(finale or {})
    finale["label"] = finale.get("label") or finale.get("description") or f"Risolvere il confronto in {final_location}"
    finale["required_clues"] = list(dict.fromkeys(finale.get("required_clues") or (required_clues or [])[:2]))
    finale["method"] = finale.get("method") or f"usare le prove raccolte nella scena di {final_location}"
    finale["concrete_choice"] = finale.get("concrete_choice") or "scegliere se smascherare, neutralizzare, negoziare o sacrificare una risorsa concreta"
    finale["depends_on"] = list(dict.fromkeys(finale.get("depends_on") or finale["required_clues"]))
    return finale


def add_survival_routes(raw: dict) -> dict:
    raw = dict(raw or {})
    profiles = raw.get("runtime_profiles") or raw.get("runtime_profile") or []
    if isinstance(profiles, str):
        profiles = [profiles]
    blob = str(raw).lower()
    needs = "survival_escape" in profiles or any(w in blob for w in ("fuga", "evacu", "sopravviv", "escape"))
    if not needs:
        return raw
    genre_runtime = dict(raw.get("genre_runtime") or {})
    locations = raw.get("locations") or []
    start = (locations[0] if locations else {}).get("name", "ingresso")
    final = (locations[-1] if locations else {}).get("name", "uscita")
    genre_runtime.setdefault("routes", [
        {"id": "route_main", "label": "percorso principale", "speed": "rapido", "risk": "sorvegliato", "from": start, "to": final},
        {"id": "route_side", "label": "tunnel laterale", "speed": "medio", "risk": "sicuro se scoperto", "from": start, "to": final},
    ])
    genre_runtime.setdefault("safe_nodes", [{"id": "safe_1", "label": "rifugio temporaneo", "benefit": "recuperare fiato e riorganizzare il gruppo"}])
    genre_runtime.setdefault("danger_zones", [{"id": "danger_1", "label": final, "risk": "confronto o perdita risorsa"}])
    raw["genre_runtime"] = genre_runtime
    resources = list(raw.get("resources") or [])
    if len(resources) < 2:
        resources.extend([
            {"id": "res_tempo", "label": "tempo", "value": 4, "max_value": 4},
            {"id": "res_accessi", "label": "accessi sicuri", "value": 2, "max_value": 2},
        ])
    raw["resources"] = resources
    return raw


def concretize_adventure_raw(raw: dict, *, genre_hint: str = "") -> dict:
    raw = deepcopy(raw or {})
    genre = genre_hint or raw.get("genre") or raw.get("detected_genre") or ""
    preserve_source = raw.get("source_mode") in {"pdf_import", "pdf_import_fallback", "manual_json"} or bool((raw.get("preservation_policy") or {}).get("forbid_structural_compression"))
    locations = list(raw.get("locations") or [])
    actors = list(raw.get("actors") or raw.get("npcs") or [])
    clues = dedupe_clues([concretize_clue(c, genre=genre, locations=locations, actors=actors) for c in list(raw.get("clues") or [])])
    raw["clues"] = clues
    locations = [concretize_location_features(l, genre=genre, clues=clues) for l in locations]
    raw["locations"] = locations
    actor_key = "actors" if raw.get("actors") else "npcs"
    raw[actor_key] = [concretize_npc_goal(a, genre=genre, clues=clues, locations=locations) for a in actors]
    antagonist = next((a.get("name") for a in raw[actor_key] if "antagon" in str(a.get("role", "")).lower()), "la minaccia")
    raw["event_clocks"] = [concretize_clock_events(c, genre=genre, antagonist=antagonist) for c in list(raw.get("event_clocks") or [])]
    if not raw["event_clocks"] and not preserve_source:
        raw["event_clocks"] = [concretize_clock_events({"id": "clock_main", "label": raw.get("threat_description") or f"{antagonist} completa il piano", "max_value": raw.get("threat_max_turns") or 8}, genre=genre, antagonist=antagonist)]
    required = [c["id"] for c in clues if c.get("is_required", True)]
    final_location = (locations[-1] if locations else {}).get("name", "zona finale")
    raw["finale_conditions"] = [concretize_finale_condition(f, required_clues=required, final_location=final_location) for f in list(raw.get("finale_conditions") or [])]
    if not raw["finale_conditions"]:
        raw["finale_conditions"] = [concretize_finale_condition({"id": "finale_main", "label": raw.get("win_condition") or "Completare l'avventura"}, required_clues=required, final_location=final_location)]
    raw = add_survival_routes(raw)
    return raw
