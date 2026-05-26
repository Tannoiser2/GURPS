
import json
import random
import os
import base64
import io
import re
import anthropic
from dotenv import load_dotenv
load_dotenv(override=True)

_GOOGLE_GENAI_IMPORT_ERROR = ""
try:
    from google import genai as google_genai
    from google.genai import types as google_genai_types
    _GOOGLE_GENAI_AVAILABLE = True
except Exception as _e:
    _GOOGLE_GENAI_AVAILABLE = False
    _GOOGLE_GENAI_IMPORT_ERROR = f"{type(_e).__name__}: {_e}"
    print(f"[google-genai] import fallito: {_GOOGLE_GENAI_IMPORT_ERROR}")

from .data_roles import ROLE_LIBRARY, THEME_FAMILY_ROLE_OVERRIDE
from .data_equipment import MISSION_EQUIPMENT_BONUS, ENVIRONMENT_EQUIPMENT_BONUS
from .data_skills import SKILL_TO_EFFECT_TYPE, SKILLS_BY_STAT, VALID_SKILLS, default_skill_for, skill_prompt_text, reconcile_effect_type, infer_effect_type_from_text, skill_display, normalize_skill, stat_display
from .data_advantages import trait_story_notes, traits_requiring_self_control
from .adventure_runtime import build_adventure_runtime, runtime_prompt_context
from .narrative_director import director_prompt_context, make_director_decision
from .state_validator import merge_engine_and_ai_updates, validate_runtime_integrity, validate_ai_state_updates
from .world_simulator import simulate_world_state
from .adventure_compiler import compile_ai_generated_to_runtime, compile_from_raw_structure, compile_pdf_to_runtime, compile_structured_text_to_runtime
from .pdf_structure_extractor import extract_pdf_structure

API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GOOGLE_AI_STUDIO_KEY = os.getenv("GOOGLE_AI_STUDIO_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_NAME = "claude-sonnet-4-5"
OPENAI_TEXT_MODEL = "gpt-4o"
OPENAI_IMAGE_MODEL = "dall-e-3"
OPENAI_IMAGE_EDIT_MODEL = "gpt-image-1"
PDF_COMPILER_MAX_INPUT_CHARS = int(os.getenv("PDF_COMPILER_MAX_INPUT_CHARS", "180000"))
PDF_COMPILER_MAX_OUTPUT_TOKENS = int(os.getenv("PDF_COMPILER_MAX_OUTPUT_TOKENS", "16000"))

_OPENAI_IMPORT_ERROR = ""
try:
    import openai as _openai_module
    _OPENAI_AVAILABLE = True
except Exception as _oe:
    _OPENAI_AVAILABLE = False
    _OPENAI_IMPORT_ERROR = f"{type(_oe).__name__}: {_oe}"

LAST_IMAGE_ERROR = ""

# ── Token usage tracking ─────────────────────────────────────────────────────
# Prezzi per milione di token (USD), aggiornati a maggio 2025
_PRICE_PER_M = {
    "claude-sonnet-4-5":   {"input": 3.0,  "output": 15.0},
    "gpt-4o":              {"input": 2.5,  "output": 10.0},
    "gpt-4o-mini":         {"input": 0.15, "output": 0.60},
    "dall-e-3":            {"input": 0.0,  "output": 0.0},
    "gpt-image-1":         {"input": 0.0,  "output": 0.0},
}

_session_tokens: dict = {
    "input": 0, "output": 0, "cost_usd": 0.0,
    "calls": 0, "errors": 0,
}

# Token usati nell'ultima richiesta HTTP (aggregato tra tutte le chiamate LLM di un turno)
_last_request_tokens: dict = {"input": 0, "output": 0, "cost_usd": 0.0, "calls": 0}


def reset_last_request_tokens() -> None:
    """Azzera il contatore per la prossima richiesta HTTP."""
    for k in _last_request_tokens:
        _last_request_tokens[k] = 0.0 if k == "cost_usd" else 0


def get_last_request_tokens() -> dict:
    return dict(_last_request_tokens)


def _record_usage(model: str, input_tokens: int, output_tokens: int) -> None:
    prices = _PRICE_PER_M.get(model, {"input": 0.0, "output": 0.0})
    cost = (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000
    _session_tokens["input"] += input_tokens
    _session_tokens["output"] += output_tokens
    _session_tokens["cost_usd"] += cost
    _session_tokens["calls"] += 1
    _last_request_tokens["input"] += input_tokens
    _last_request_tokens["output"] += output_tokens
    _last_request_tokens["cost_usd"] += cost
    _last_request_tokens["calls"] += 1


def get_session_token_stats() -> dict:
    t = _session_tokens
    return {
        "input_tokens": t["input"],
        "output_tokens": t["output"],
        "total_tokens": t["input"] + t["output"],
        "cost_usd": round(t["cost_usd"], 4),
        "calls": t["calls"],
        "errors": t["errors"],
    }


def reset_session_token_stats() -> None:
    for k in ("input", "output", "cost_usd", "calls", "errors"):
        _session_tokens[k] = 0.0 if k in ("cost_usd",) else 0


def _set_last_image_error(context: str, error: Exception | str) -> None:
    global LAST_IMAGE_ERROR
    msg = f"{type(error).__name__}: {error}" if isinstance(error, Exception) else error
    LAST_IMAGE_ERROR = f"{context}: {msg}"
    print(f"[{context}] {msg}")


def _clear_last_image_error() -> None:
    global LAST_IMAGE_ERROR
    LAST_IMAGE_ERROR = ""

# Provider attivo per questa sessione — impostato da set_active_provider()
_ACTIVE_PROVIDER: str = "claude"  # "claude" | "openai"


def set_active_provider(provider: str) -> None:
    global _ACTIVE_PROVIDER
    _ACTIVE_PROVIDER = provider if provider in ("claude", "openai") else "claude"
    print(f"[provider] attivo: {_ACTIVE_PROVIDER}")


def _text_provider_available(provider: str | None = None) -> bool:
    selected = provider or _ACTIVE_PROVIDER
    if selected == "openai":
        return bool(OPENAI_API_KEY) and _OPENAI_AVAILABLE
    return bool(API_KEY)


def _active_source_label() -> str:
    return _ACTIVE_PROVIDER if _ACTIVE_PROVIDER in ("claude", "openai") else "unknown"

PHASE_BLUEPRINTS = {
    1: {"phase_name": "Ingresso", "zone_goal_template": "aprire l'accesso e capire la minaccia", "is_final_phase": False},
    2: {"phase_name": "Profondità", "zone_goal_template": "raggiungere il cuore del problema", "is_final_phase": False},
    3: {"phase_name": "Risoluzione", "zone_goal_template": "chiudere il conflitto ed estrarsi", "is_final_phase": True},
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _extract_json_object(raw_text: str) -> dict:
    raw_text = raw_text.strip()

    # Tentativo diretto
    try:
        return json.loads(raw_text)
    except Exception:
        pass

    # Rimuovi blocchi markdown ```json ... ``` o ``` ... ```
    code_block = re.search(r"```(?:json)?\s*\n?(\{[\s\S]*\})\s*\n?```", raw_text)
    if code_block:
        try:
            return json.loads(code_block.group(1))
        except Exception:
            pass

    # Cerca il primo { e l'ultimo } nel testo
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw_text[start:end + 1])
        except Exception:
            pass

    # Recupero JSON troncato: se inizia con { ma non chiude correttamente,
    # prova a tagliare all'ultima virgola "sicura" e chiudere le parentesi aperte.
    if start != -1:
        candidate = raw_text[start:]
        # Strappa eventuali fence di chiusura residui
        candidate = re.sub(r"```\s*$", "", candidate.strip()).rstrip()
        # Tronca all'ultima virgola/quote completa per evitare token a metà
        last_safe = max(candidate.rfind('",'), candidate.rfind('"\n'), candidate.rfind("],"), candidate.rfind("},"))
        if last_safe > 0:
            candidate = candidate[:last_safe + 1].rstrip().rstrip(",")
            # Chiudi parentesi nell'ordine corretto seguendo lo stack reale.
            # Un naive ']' * n + '}' * m sbaglia quando l'ultimo oggetto aperto
            # e dentro un array (caso {"clues": [{...truncated]}).
            stack: list[str] = []
            in_string = False
            escape = False
            for ch in candidate:
                if escape:
                    escape = False
                    continue
                if ch == "\\":
                    escape = True
                    continue
                if ch == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == "{":
                    stack.append("}")
                elif ch == "[":
                    stack.append("]")
                elif ch in "}]" and stack and stack[-1] == ch:
                    stack.pop()
            if stack:
                candidate = candidate + "".join(reversed(stack))
            try:
                parsed = json.loads(candidate)
                print(f"[_extract_json_object] recuperato JSON troncato ({len(raw_text)} char originali)")
                return parsed
            except Exception:
                pass

    # Debug: logga cosa ha restituito Claude + salva raw completo per diagnosi
    preview = raw_text[:300].replace("\n", " ")
    print(f"[_extract_json_object] impossibile parsare ({len(raw_text)} char): {preview}")
    try:
        import time as _time
        debug_path = f"/tmp/canon_raw_{int(_time.time())}.txt"
        with open(debug_path, "w") as fh:
            fh.write(raw_text)
        print(f"[_extract_json_object] raw completo salvato in {debug_path}")
    except Exception as _e:
        print(f"[_extract_json_object] impossibile salvare raw: {_e}")
    raise ValueError("JSON non trovato")


def _strip_code_fences(raw_text: str) -> str:
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_story_canon_loose(raw_text: str) -> dict:
    text = _strip_code_fences(raw_text)

    def grab_scalar(key: str, next_key: str | None = None) -> str:
        if next_key:
            pattern = rf'"{key}"\s*:\s*"(.*?)"\s*,\s*"{next_key}"'
        else:
            pattern = rf'"{key}"\s*:\s*"(.*?)"'
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            return ""
        return match.group(1).replace('\\"', '"').strip()

    def grab_array(key: str) -> list[str]:
        match = re.search(rf'"{key}"\s*:\s*\[(.*?)\]', text, re.DOTALL)
        if not match:
            return []
        inner = match.group(1)
        return [item.replace('\\"', '"').strip() for item in re.findall(r'"(.*?)"', inner, re.DOTALL) if item.strip()]

    data = {
        "premise": grab_scalar("premise", "hidden_truth"),
        "hidden_truth": grab_scalar("hidden_truth", "hidden_truth_clues") or grab_scalar("hidden_truth", "win_condition"),
        "win_condition": grab_scalar("win_condition", "active_threads"),
        "active_threads": grab_array("active_threads"),
        "named_entities": grab_array("named_entities"),
    }
    if data["premise"] or data["hidden_truth"] or data["active_threads"]:
        return data
    raise ValueError("Story canon loose parse fallito")


def _clean_canon_text(value: str, limit: int | None = None) -> str:
    text = str(value or "").strip()
    # Se il parser loose ha inglobato campi JSON successivi dentro una stringa,
    # taglia al primo campo strutturale noto invece di propagare il blob in UI/storia.
    text = re.split(
        r'"\s*,\s*"(?:hidden_truth_clues|hidden_truth_reveal_rule|win_condition|threads|named_entities|key_entities|key_items)"\s*:',
        text,
        maxsplit=1,
    )[0]
    text = text.replace('\\"', '"').strip(" \n\r\t,")
    if limit and len(text) > limit:
        text = _short(text, limit=limit)
    return text


def _claude_client() -> anthropic.Anthropic | None:
    if not API_KEY:
        return None
    return anthropic.Anthropic(api_key=API_KEY, timeout=120.0)


def _call_claude(prompt: str, max_tokens: int = 1200) -> str:
    client = _claude_client()
    if not client:
        raise RuntimeError("API key Anthropic non configurata")
    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception:
        _session_tokens["errors"] += 1
        raise
    if not response.content:
        raise RuntimeError("Claude API ha restituito una risposta vuota (content=[])")
    usage = getattr(response, "usage", None)
    if usage:
        _record_usage(MODEL_NAME, getattr(usage, "input_tokens", 0), getattr(usage, "output_tokens", 0))
    return response.content[0].text


def _call_openai(prompt: str, max_tokens: int = 1200) -> str:
    if not OPENAI_API_KEY or not _OPENAI_AVAILABLE:
        raise RuntimeError("API key OpenAI non configurata o openai non installato")
    client = _openai_module.OpenAI(api_key=OPENAI_API_KEY, timeout=120.0)
    try:
        response = client.chat.completions.create(
            model=OPENAI_TEXT_MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        _session_tokens["errors"] += 1
        raise
    usage = getattr(response, "usage", None)
    if usage:
        _record_usage(OPENAI_TEXT_MODEL, getattr(usage, "prompt_tokens", 0), getattr(usage, "completion_tokens", 0))
    return response.choices[0].message.content


def _call_text_model(prompt: str, max_tokens: int = 1200) -> str:
    """Dispatcher: usa OpenAI o Claude in base al provider attivo."""
    if _ACTIVE_PROVIDER == "openai":
        return _call_openai(prompt, max_tokens)
    return _call_claude(prompt, max_tokens)


def _call_text_model_with_provider(provider: str, prompt: str, max_tokens: int = 1200) -> str:
    """Chiama esplicitamente un provider specifico, ignorando _ACTIVE_PROVIDER."""
    if provider == "openai":
        return _call_openai(prompt, max_tokens)
    return _call_claude(prompt, max_tokens)


def _other_provider() -> str | None:
    """Restituisce il provider alternativo disponibile, o None se non c'è."""
    other = "claude" if _ACTIVE_PROVIDER == "openai" else "openai"
    return other if _text_provider_available(other) else None


# ── Setup e configurazione ────────────────────────────────────────────────────

def get_phase_blueprint(phase_index: int, environment_type: str, mission_type: str) -> dict:
    phase_index = max(1, min(phase_index, 3))
    base = PHASE_BLUEPRINTS[phase_index]
    return {
        "phase_index": phase_index,
        "max_phases": 3,
        "phase_name": base["phase_name"],
        "zone_type": f"{environment_type} - settore {phase_index}",
        "zone_goal": f"{base['zone_goal_template']} in una missione di {mission_type}",
        "zone_tags": [environment_type, mission_type, f"fase_{phase_index}"],
        "zone_modifier": "",
        "is_final_phase": base["is_final_phase"],
    }


def mission_scaling(active_slots: int) -> dict:
    if active_slots <= 1:
        return {"mission_target": 2, "max_turns": 10, "scene_target_min": 2, "scene_target_max": 3, "time_min": 5, "time_max": 6, "starting_threat_min": 0, "starting_threat_max": 1}
    if active_slots == 2:
        return {"mission_target": 3, "max_turns": 12, "scene_target_min": 3, "scene_target_max": 4, "time_min": 5, "time_max": 6, "starting_threat_min": 1, "starting_threat_max": 1}
    if active_slots == 3:
        return {"mission_target": 3, "max_turns": 15, "scene_target_min": 3, "scene_target_max": 4, "time_min": 5, "time_max": 6, "starting_threat_min": 1, "starting_threat_max": 2}
    return {"mission_target": 4, "max_turns": 18, "scene_target_min": 4, "scene_target_max": 5, "time_min": 5, "time_max": 6, "starting_threat_min": 1, "starting_threat_max": 2}


_NAMES_BY_GENRE: dict[str, list[str]] = {
    "sci_fi":   ["Kovač", "Yuen", "Okafor", "Reyes", "Nakamura", "Shen", "Vasquez", "Petrov",
                 "Adeyemi", "Johansson", "Mbeki", "Castillo", "Voss", "Kimura", "Rashid"],
    "fantasy":  ["Aldric", "Mira", "Theron", "Sylvara", "Dorin", "Aelys", "Brann", "Vesper",
                 "Corvin", "Lirien", "Hadast", "Rowena", "Caelum", "Nessa", "Edric"],
    "mystery_horror": ["Carver", "Dupont", "Ashwood", "Marlowe", "Vance", "Sinclair", "Delacroix",
                       "Hargrove", "Beaumont", "Waverly", "Crane", "Holloway", "Fenn", "Blackwell"],
    "ww2":      ["Moretti", "Brennan", "Kowalski", "Fournier", "Novak", "Fischer", "Tanaka",
                 "Dubois", "Russo", "MacAllister", "Becker", "Petrov", "Santos", "Nielsen"],
    "romance":  ["Luca", "Elena", "Marco", "Sofia", "Giulia", "Matteo", "Chiara", "Lorenzo",
                 "Valentina", "Andrea", "Beatrice", "Nico", "Elisa", "Fabio", "Irene"],
    "action":   ["Stone", "Cruz", "Reeves", "Park", "Volkov", "Diaz", "Osei", "Tanaka",
                 "Mercer", "Ibarra", "Kovač", "Nkosi", "Holt", "Ferreira", "Quinn"],
    "detective_classico": ["Marlowe", "Vance", "Blackwood", "Crane", "Hargrove", "Sinclair",
                           "Delacroix", "Carver", "Ashwood", "Fenn", "Beaumont", "Waverly"],
}

def _pick_names(genre: str, count: int) -> list[str]:
    pool = list(_NAMES_BY_GENRE.get(genre) or _NAMES_BY_GENRE["action"])
    random.shuffle(pool)
    # Se servono più nomi del pool, aggiunge varianti con iniziale del nome
    extras = [f"{n[0]}. {n}" for n in pool]
    full = pool + extras
    return full[:count]


def generate_candidate_pool(genre: str, active_slots: int, mission_type: str, environment_type: str, theme_family: str = "") -> list[dict]:
    POOL_TARGET = 6
    # Se il theme_family ha un override di ruoli (es. "storico" → ruoli medievali), lo usa
    role_key = THEME_FAMILY_ROLE_OVERRIDE.get(theme_family, genre)
    roles = ROLE_LIBRARY.get(role_key) or ROLE_LIBRARY[genre]
    weighted = []
    for role in roles:
        score = 0
        if mission_type in ["recupero", "ricognizione", "indagine", "ricostruzione", "interrogatorio", "scoperta del colpevole"] and role["archetype"] in ["scientist", "technician", "detective", "forensic", "scholar", "scout", "rogue", "inspector", "amateur", "journalist", "assistant", "hacker"]:
            score += 2
        if mission_type in ["salvataggio", "scorta", "protezione", "salvataggio ostaggi"] and role["archetype"] in ["medic", "paramedic", "cleric", "diplomat", "officer", "field_medic", "confidant"]:
            score += 2
        if mission_type in ["fuga", "sabotaggio", "attacco", "neutralizzazione", "resistenza"] and role["archetype"] in ["marine", "warrior", "rifleman", "hunter", "solo", "scout", "operative", "partisan", "sniper", "agent"]:
            score += 2
        weighted.append((score, role))
    weighted.sort(key=lambda x: x[0], reverse=True)
    guaranteed = [x[1] for x in weighted[:2]]
    rest = [x[1] for x in weighted[2:]]
    random.shuffle(rest)
    unique_pool = guaranteed + rest
    selected = list(unique_pool[:POOL_TARGET])
    fill_idx = 0
    while len(selected) < POOL_TARGET and unique_pool:
        selected.append(unique_pool[fill_idx % len(unique_pool)])
        fill_idx += 1
    random.shuffle(selected)

    names = _pick_names(genre, POOL_TARGET)
    out = []
    for idx, role in enumerate(selected, start=1):
        items = list(role["base_items"])
        for item in MISSION_EQUIPMENT_BONUS.get(mission_type, []):
            if item not in items and len(items) < 4:
                items.append(item)
        for item in ENVIRONMENT_EQUIPMENT_BONUS.get(environment_type, []):
            if item not in items and len(items) < 5:
                items.append(item)
        out.append({
            "id": idx,
            "name": names[idx - 1],
            "role": role["role"],
            "archetype": role["archetype"],
            "stats": role["stats"],
            "skills": dict(role.get("skills", {})),
            "status": "ok",
            "items": items,
            "actions": [],
        })
    return out


_PROLOGUE_REGISTERS = [
    {
        "name": "in_medias_res_dialogo",
        "instructions": (
            "REGISTRO: APERTURA IN MEDIAS RES CON DIALOGO. "
            "Inizia direttamente con una battuta in «» pronunciata da un personaggio sulla scena (un PNG nominato, non uno della squadra). "
            "La prima frase deve essere o un dialogo o una reazione fisica immediata. "
            "Vietato aprire con descrizioni di luogo o atmosfera. "
            "Vietato citare numeri specifici (anni, ore, persone) nel primo periodo."
        ),
    },
    {
        "name": "rapporto_freddo",
        "instructions": (
            "REGISTRO: RAPPORTO OPERATIVO FREDDO. "
            "Stile asciutto, da log di missione o briefing tecnico: frasi brevi, soggetto-verbo-oggetto, niente metafore. "
            "Permessi: codici, designazioni alfanumeriche, orari, indicatori. "
            "Vietato l'uso di descrizioni sensoriali (odore, suono, tatto). "
            "Vietato l'uso di aggettivi atmosferici ('inquietante', 'opprimente', 'freddo', 'sinistro')."
        ),
    },
    {
        "name": "voce_seconda_persona",
        "instructions": (
            "REGISTRO: SECONDA PERSONA SINGOLARE COLLETTIVA. "
            "Usa 'Vedi', 'Senti', 'Ti accorgi', 'Hai davanti'. La squadra è 'tu'. "
            "Tono presente, immediato, percettivo. "
            "Vietato aprire con frase del tipo 'Il/La [nome luogo o persona] doveva...' o 'L'odore di...'."
        ),
    },
    {
        "name": "monologo_png",
        "instructions": (
            "REGISTRO: MONOLOGO INTERIORE DI UN PNG SULLA SCENA. "
            "Il prologo entra nel pensiero (corsivo o tra parentesi non serve, prosa fluida) di una persona presente che NON fa parte della squadra. "
            "Mostra cosa vede e teme, e attraverso i suoi occhi la squadra appare. "
            "Il dialogo in «» è una frase che il PNG dice ad alta voce in un momento di stress. "
            "Vietato il punto di vista esterno o onnisciente."
        ),
    },
    {
        "name": "tattile_uditivo",
        "instructions": (
            "REGISTRO: SENSORIALE NON-OLFATTIVO. "
            "Costruisci l'apertura su tatto, suono, vibrazione, temperatura, peso, pressione. "
            "VIETATO ASSOLUTO menzionare odori, profumi, aromi, puzze, fragranze in qualsiasi forma. "
            "Vietato il verbo 'permeare' e i suoi sinonimi olfattivi. "
            "Apri con una sensazione fisica che entra nel corpo dei personaggi."
        ),
    },
    {
        "name": "cronologia_inversa",
        "instructions": (
            "REGISTRO: CRONOLOGIA INVERSA. "
            "Apri con un evento appena accaduto (qualcuno è caduto, una porta si è chiusa, una luce si è spenta) e poi mostra cosa lo ha causato risalendo all'indietro. "
            "Tre tempi narrativi: ADESSO, POCO PRIMA, ALL'INIZIO. "
            "Vietato aprire con descrizione statica del luogo."
        ),
    },
    {
        "name": "documento_intercettato",
        "instructions": (
            "REGISTRO: DOCUMENTO INTERCETTATO. "
            "Il prologo è (in parte) un frammento di trasmissione, manifesto, lettera, ordine, log di sistema, registrazione. "
            "Apri con il documento (citalo come tale: 'Trasmissione 14.07 — incompleta', 'Ordine #...', ecc.) e poi raccorda alla scena fisica della squadra. "
            "Almeno una riga deve essere il testo grezzo del documento."
        ),
    },
    {
        "name": "dettaglio_anomalo",
        "instructions": (
            "REGISTRO: DETTAGLIO ANOMALO. "
            "Apri con UN solo dettaglio fuori posto e specifico, mostrato in primo piano (un oggetto, una postura, un'incongruenza). "
            "Solo dopo allarghi il campo a chi e dove. "
            "Vietato riassumere la situazione generale prima del dettaglio. "
            "Vietato aprire con il nome di un luogo o una persona seguito da 'doveva'."
        ),
    },
]


_FORBIDDEN_OPENINGS = [
    "Apertura olfattiva: NON iniziare il prologo con 'L'odore di...', 'L'aria sa di...', 'Un odore...', e simili.",
    "Formula contrappositiva ovvia: NON usare la struttura 'X doveva [grande promessa], ma [tradimento]' come prima frase.",
    "Numero specifico nel primo periodo: NON aprire con 'In sette anni', 'Da trentasei ore', 'Quattordici operai', 'Duecento relitti', ecc.",
    "Verbo 'permeare' nel primo periodo: vietato.",
    "Apertura con 'La squadra si trova / La squadra è arrivata / La squadra entra'.",
]


def generate_prologue(
    mission_title: str,
    mission_objective: str,
    genre: str,
    theme_family: str,
    environment_type: str,
    threat_type: str,
    tone: str,
    premise: str,
    active_threads: list[str],
    starting_zone: str,
    forbidden_elements: list[str] | None = None,
    narrative_blacklist: list[str] | None = None,
) -> str:
    """Genera il testo narrativo di apertura della missione, integrando premessa e thread."""
    try:
        threads_txt = "\n".join(f"- {t}" for t in active_threads)
        blacklist_block = ""
        if forbidden_elements or narrative_blacklist:
            lines = []
            if forbidden_elements:
                lines.append("Elementi da NON descrivere: " + "; ".join(forbidden_elements) + ".")
            if narrative_blacklist:
                lines.append("Strutture o tropi da NON usare: " + "; ".join(narrative_blacklist) + ".")
            blacklist_block = "\nVINCOLI (rispetta sempre questi):\n" + "\n".join(lines) + "\n"

        register = random.choice(_PROLOGUE_REGISTERS)
        forbidden_openings_block = "APERTURE VIETATE (regole assolute, valgono per ogni registro):\n" + "\n".join(f"- {x}" for x in _FORBIDDEN_OPENINGS)

        prompt = (
            f"Sei il narratore di un gioco da tavolo narrativo in italiano. Genere: {genre}. Famiglia tematica: {theme_family}. Tono: {tone}.\n\n"
            f"DATI MISSIONE:\n"
            f"- Titolo: {mission_title}\n"
            f"- Obiettivo: {mission_objective}\n"
            f"- Ambiente: {environment_type}\n"
            f"- Minaccia: {threat_type}\n"
            f"- Premessa: {premise}\n"
            f"- Zona di partenza: {starting_zone}\n"
            f"{blacklist_block}\n"
            f"DOMANDE APERTE (le tensioni irrisolte che la squadra percepisce):\n{threads_txt}\n\n"
            f"{register['instructions']}\n\n"
            f"{forbidden_openings_block}\n\n"
            "Scrivi il PROLOGO di apertura della missione: 4-5 frasi che:\n"
            "1. Rispettano il REGISTRO assegnato sopra (priorità massima sulla forma).\n"
            "2. Fanno capire DOVE si trova la squadra e in quale situazione concreta è arrivata lì.\n"
            "3. Dicono COSA è appena successo o quale allarme/rottura/scoperta ha fatto scattare l'azione ORA.\n"
            "4. Introducono la minaccia come presenza concreta, non come concetto astratto.\n"
            "5. Lasciano trasparire le domande aperte come dettagli osservabili, senza elencarle.\n"
            "6. Chiudono con il primo problema immediato nella zona di partenza.\n"
            "Deve contenere almeno un'entità nominata o un luogo specifico, e non deve riscrivere l'obiettivo.\n"
            "Scrivi SOLO il testo narrativo, nessun titolo o commento. Non nominare il registro nel testo."
        )
        return _call_text_model(prompt, max_tokens=350).strip()
    except Exception as e:
        print(f"[generate_prologue] fallback: {e}")
        return f"{premise} La squadra si trova ora in {starting_zone} e deve agire prima che sia troppo tardi."


_GENERIC_THREADS = {
    "scoprire la vera natura della minaccia",
    "raggiungere l'obiettivo prima che sia troppo tardi",
    "proteggere ciò che conta",
    "proteggere ciò che conta davvero",
}

_MORAL_THREAD_SIGNALS = [
    "quale peso", "chi merita", "chi ha più valore", "vale la pena", "è giusto",
    "è morale", "si può abbandonare", "bisogna scegliere tra", "scelta impossibile tra",
    "sacrificio di", "cosa conta di più", "è il prezzo",
]


def _title_case_entity(text: str) -> str:
    words = [w for w in re.split(r"\s+", text.strip()) if w]
    if not words:
        return ""
    small = {"di", "del", "della", "dei", "degli", "delle", "e", "a", "da", "su", "nel", "nella", "in"}
    out = []
    for i, w in enumerate(words[:5]):
        low = w.lower()
        if i > 0 and low in small:
            out.append(low)
        else:
            out.append(low[:1].upper() + low[1:])
    return " ".join(out)


def _derive_story_entities(mission_title: str, mission_objective: str, environment_type: str, threat_type: str) -> list[str]:
    source = f"{mission_title}. {mission_objective}"
    found: list[str] = []
    patterns = [
        r"\b(?:dott(?:\.|oressa|ore)?|prof(?:\.|essore|essoressa)?|capitano|tenente|madre|padre|veggente|agente)\s+[A-ZÀ-Ý][\wÀ-ÿ'-]+(?:\s+[A-ZÀ-Ý][\wÀ-ÿ'-]+)?",
        r"\b[A-ZÀ-Ý][\wÀ-ÿ'-]+\s+[A-ZÀ-Ý][\wÀ-ÿ'-]+(?:\s+[A-ZÀ-Ý][\wÀ-ÿ'-]+)?",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, source):
            entity = match.strip(" .,;:")
            if len(entity) > 3 and entity not in found:
                found.append(entity)
    for value in [environment_type, threat_type]:
        entity = _title_case_entity(value)
        if entity and entity.lower() not in {"base", "missione"} and entity not in found:
            found.append(entity)
    return found[:4]


def _derive_story_entities_from_text(*texts: str) -> list[str]:
    source = " ".join(t for t in texts if t)
    found: list[str] = []
    patterns = [
        r"\b(?:dott(?:\.ssa|\.|oressa|ore)?|prof(?:\.ssa|\.|essore|essoressa)?|capitano|tenente|madre|padre|veggente|agente|emissario|controllore|ammiraglio|direttrice|direttore)\s+[A-ZÀ-Ý][\wÀ-ÿ'-]+(?:\s+[A-ZÀ-Ý][\wÀ-ÿ'-]+)?",
        r"\b[A-ZÀ-Ý][\wÀ-ÿ'-]+\s+[A-ZÀ-Ý][\wÀ-ÿ'-]+(?:\s+[A-ZÀ-Ý][\wÀ-ÿ'-]+)?",
        r"\b[A-ZÀ-Ý][\wÀ-ÿ'-]+(?:-[A-ZÀ-Ý0-9][\wÀ-ÿ'-]+)+",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, source):
            entity = match.strip(" .,;:«»\"'()[]")
            if entity.lower().startswith(("la dott", "il dott", "la prof", "il prof")) and "." not in entity:
                continue
            if len(entity) > 3 and entity not in found and not _entity_looks_generic(entity):
                found.append(entity)
    return found[:6]


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text or "").strip())
    return [p.strip() for p in parts if p.strip()]


def _objective_deadline(objective: str) -> str:
    match = re.search(r"\bprima che\b\s+(.+?)(?:[.!]|$)", objective, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return "la situazione precipiti"


def _objective_target_phrase(objective: str) -> str:
    objective = re.sub(r"\s+", " ", objective or "").strip()
    patterns = [
        r"(?:deve\s+)?(?:localizzare|trovare)\s+(.+?)(?:\s+proveniente|\s+che\s+|\s+prima che|\s+nel|\s+nella|\s+entro|[.!]|$)",
        r"(?:deve\s+)?(?:contattare|raggiungere|localizzare|salvare|convincere|trovare)\s+(.+?)(?:\s+prima che|\s+nel|\s+nella|\s+entro|[.!]|$)",
        r"(?:deve\s+)?(?:recuperare|ottenere|portare via|estrarre)\s+(.+?)(?:\s+prima che|\s+dal|\s+dalla|\s+nel|\s+nella|[.!]|$)",
        r"(?:deve\s+)?(?:attraversare|mappare).+?e\s+localizzare\s+(.+?)(?:\s+per|\s+prima che|[.!]|$)",
        r"(?:deve\s+)?(?:attraversare|mappare).+?e\s+recuperare\s+(.+?)(?:\s+per|\s+prima che|[.!]|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, objective, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return objective


_REFUSAL_PATTERNS = (
    "i'm sorry",
    "i am sorry",
    "i can't assist",
    "i cannot assist",
    "i can't help",
    "i cannot help",
    "i won't",
    "i will not",
    "mi dispiace",
    "mi scuso",
    "mi scusi",
    "non posso aiutarti",
    "non sono in grado",
    "non posso assisterti",
    "non posso fornire",
    "non posso generare",
    "non posso continuare",
    "si prega di fornire",
    "si prega di ripetere",
    "elaborazione del tuo input",
    "as an ai",
    "non è appropriato",
    "non è etico",
    "policy",
)


def _looks_like_refusal(raw: str) -> bool:
    """True se la risposta del modello sembra un rifiuto di policy invece di JSON."""
    if not raw:
        return True
    text = raw.strip()
    if not text:
        return True
    # Se c'è un blocco JSON / oggetto graffato lungo, non è un rifiuto
    if "{" in text and "}" in text and len(text) > 200:
        return False
    # Se non c'è nessuna parentesi graffa, non può essere JSON valido
    if "{" not in text:
        return True
    low = text.lower()[:400]
    return any(p in low for p in _REFUSAL_PATTERNS)


def _safe_master_refusal_fallback(
    *,
    adventure: dict | None,
    active_name: str = "Il gruppo",
    player_action: str = "",
    prerolled: dict | None = None,
    active_player_id: int = 0,
    start: bool = False,
) -> dict:
    """Risposta deterministica quando il provider rifiuta, senza mostrare il rifiuto al tavolo."""
    title = (adventure or {}).get("title") or "l'avventura"
    premise = (adventure or {}).get("premise") or "La situazione resta tesa e piena di segnali contraddittori."
    clues = [c for c in ((adventure or {}).get("clues") or []) if isinstance(c, dict)]
    first_clue = clues[0] if clues else {}
    clue_id = first_clue.get("id")
    if start:
        narrative = (
            f"{premise} La scena si apre con un dettaglio concreto che chiede attenzione: "
            f"{first_clue.get('text') or 'un elemento fuori posto collega il luogo alla verita nascosta'}. "
            "Il Master mantiene il canovaccio stabile e invita il gruppo a scegliere come procedere."
        )
        threat = 0
    else:
        outcome = (prerolled or {}).get("outcome", "esito incerto")
        success = bool((prerolled or {}).get("success", False))
        if success:
            narrative = (
                f"{active_name} porta avanti l'azione dichiarata: {player_action}. {{{{ROLL}}}} "
                f"L'esito e {outcome}: la squadra ottiene un avanzamento concreto senza introdurre nuovi misteri, "
                f"collegando la scena a {first_clue.get('text') or title}."
            )
            threat = 0
        else:
            narrative = (
                f"{active_name} tenta: {player_action}. {{{{ROLL}}}} "
                f"L'esito e {outcome}: la situazione non si blocca, ma il costo aumenta e la minaccia guadagna terreno."
            )
            threat = 1
    updates = {
        "clue_progress": [{"clue_id": clue_id, "note": "Avanzamento automatico sul primo indizio canonico disponibile.", "ticks": 1}] if clue_id else [],
        "clues_found": [],
        "discovered_clues": [],
        "npc_updates": [],
        "new_threads": [],
        "closed_threads": [],
        "threat_increase": threat,
        "activate_combat": False,
        "combat_scene": None,
        "combat_over": False,
        "story_over": False,
        "victory": False,
        "fallback_reason": "provider_refusal",
    }
    return {
        "narrative": narrative,
        "roll": None if start else {
            "rolled": (prerolled or {}).get("rolled", 0),
            "target": (prerolled or {}).get("effective_skill", 10),
            "skill": (prerolled or {}).get("skill", ""),
            "skill_name": (prerolled or {}).get("skill", ""),
            "success": bool((prerolled or {}).get("success", False)),
            "margin": (prerolled or {}).get("margin", 0),
            "critical": bool((prerolled or {}).get("critical", False)),
        },
        "options": [
            {"text": "Esaminare l'indizio piu concreto nella scena", "skill": "investigare", "skill_level": 0, "stat": "intelligenza", "player_id": active_player_id},
            {"text": "Confrontare un PNG collegato alla pista", "skill": "negoziare", "skill_level": 0, "stat": "empatia", "player_id": active_player_id},
            {"text": "Azione custom", "skill": "", "skill_level": 0, "stat": "", "player_id": active_player_id},
        ],
        "state_updates": updates,
    }


def _place_with_preposition(place: str) -> str:
    """Restituisce 'a/al/alla/all'/in/sul/sulla' + place sulla base di indizi superficiali.
    Serve a non produrre frasi come 'in autostrada' o 'in laboratorio Lambda-7'."""
    p = (place or "").strip()
    if not p:
        return "sul posto"
    low = p.lower()
    # Nomi propri o luoghi-stanza che vogliono "a/al/alla/all'..."
    if low.startswith(("villa ", "casa ", "torre ", "porto ", "ponte ", "settore ", "laboratorio ", "stazione ", "stanza ", "sala ", "molo ", "deposito ", "magazzino ")):
        return f"a {p}"
    # Sostantivi-luogo che richiedono "sulla/sull'"
    if low in {"autostrada", "tangenziale", "metropolitana", "strada", "spiaggia"}:
        return f"sull'{p}" if low[0] in "aeiou" else f"sulla {p}"
    # "in" funziona per la maggior parte degli ambienti generici
    return f"in {p}"


def _fallback_story_canon(
    mission_title: str,
    mission_objective: str,
    environment_type: str,
    threat_type: str,
    twist: str,
    narrative_mode: str,
) -> dict:
    entities = _derive_story_entities(mission_title, mission_objective, environment_type, threat_type)
    target = entities[0] if entities else "l'obiettivo"
    place = entities[1] if len(entities) > 1 else environment_type
    witness = entities[2] if len(entities) > 2 else "la squadra"
    place_phrase = _place_with_preposition(place)
    return {
        "narrative_mode": narrative_mode,
        "premise": (
            f"{place_phrase.capitalize()} la situazione è già saltata mentre la squadra arriva per {mission_objective.lower()}. "
            f"I segni lasciati da {threat_type} mostrano che non si tratta di un allarme iniziale ma di un processo già in corso, "
            f"e che {witness} è stato travolto prima di poter fermare la deriva."
        ),
        "hidden_truth": (
            f"La minaccia non si limita a colpire {place}: sfrutta {twist} per piegare l'intera situazione attorno a {target}. "
            f"Per interrompere il processo bisogna arrivare a {target}, ma proprio per questo {target} è già al centro del controllo."
        ),
        "win_condition": mission_objective,
        "active_threads": [
            f"Dove si trova {target}?",
            f"Chi controlla o protegge {target}?",
            f"Come si neutralizza {threat_type} senza perdere {target}?",
        ],
        "named_entities": entities,
    }


def _looks_generic(text: str) -> bool:
    low = (text or "").strip().lower()
    if not low:
        return True
    generic_fragments = [
        "vera natura della minaccia",
        "raggiungere l'obiettivo",
        "prima che sia troppo tardi",
        "proteggere ciò che conta",
        "qualcosa di più oscuro",
        "portare a termine la missione",
        "la missione '",
        "la missione \"",
        "impone di agire",
    ]
    return any(fragment in low for fragment in generic_fragments)


def _normalize_thread_question(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "").strip())
    if not cleaned:
        return ""
    cleaned = cleaned.rstrip(".! ")
    # Tronca thread troppo lunghi prima di aggiungere il punto interrogativo
    if len(cleaned) > 120:
        cleaned = _short(cleaned, limit=120)
    if not cleaned.endswith("?"):
        cleaned = f"{cleaned}?"
    return cleaned[:1].upper() + cleaned[1:]


def _complete_structured_thread_details(threads: list[dict], canon: dict) -> list[dict]:
    win_condition = canon.get("win_condition", "")
    hidden_truth = _clean_canon_text(canon.get("hidden_truth", ""), limit=260)
    hidden_clues = canon.get("hidden_truth_clues", []) or []
    for idx, thread in enumerate(threads):
        if not thread.get("purpose"):
            defaults = [
                "sblocca luogo/accesso della soluzione missione",
                "sblocca persona, causa o oggetto utile alla soluzione",
                "sblocca procedura, costo o vincolo finale",
            ]
            thread["purpose"] = defaults[min(idx, len(defaults) - 1)]
        if not thread.get("answer") or thread.get("answer") == win_condition:
            question = thread.get("question", "")
            if idx == 0:
                thread["answer"] = f"La leva finale si raggiunge seguendo la pista: {question.rstrip('?')}."
            elif idx == 1:
                thread["answer"] = f"La leva utile emerge da questo indizio: {hidden_clues[0] if hidden_clues else _short(hidden_truth, 120)}."
            else:
                thread["answer"] = f"La procedura finale richiede: {win_condition}."
        if not thread.get("clue_plan"):
            clues = []
            if idx < len(hidden_clues):
                clues.append(hidden_clues[idx])
            if win_condition:
                clues.append(f"Traccia operativa verso la soluzione: {win_condition}")
            if len(clues) < 2 and hidden_truth:
                clues.append(f"Dettaglio sul costo nascosto: {_short(hidden_truth, 140)}")
            thread["clue_plan"] = clues[:2]
        if not thread.get("reveal_rule"):
            clue_text = "; ".join(thread.get("clue_plan", [])[:2])
            thread["reveal_rule"] = f"rivela la risposta quando sono stati scoperti questi indizi: {clue_text}"
    return threads


def _fallback_key_entity_cards(canon: dict) -> list[dict]:
    cards = []
    threads = canon.get("structured_threads", []) or []
    hidden_truth = canon.get("hidden_truth", "")
    for name in (canon.get("named_entities", []) or [])[:4]:
        related = next(
            (
                t for t in threads
                if name.lower() in f"{t.get('question', '')} {t.get('answer', '')} {' '.join(t.get('clue_plan', []) or [])}".lower()
            ),
            None,
        )
        clues = related.get("clue_plan", [])[:3] if related else []
        kind = _classify_key_entity_kind(name)
        if kind == "luogo" and not related and name.lower() not in hidden_truth.lower() and name.lower() not in canon.get("win_condition", "").lower():
            continue
        cards.append({
            "name": name,
            "kind": kind,
            "role": _default_role_for_kind(kind, related),
            "location": _default_location_for_kind(kind, related),
            "drive": _default_drive_for_kind(kind, related),
            "secret": _clean_canon_text(related.get("answer", "") if related else hidden_truth, limit=220),
            "clues": clues,
            "reveal_rule": related.get("reveal_rule", "quando uno degli indizi canonici della scheda viene scoperto") if related else "quando uno degli indizi canonici della scheda viene scoperto",
            "effect": related.get("purpose", "puo chiarire, bloccare o sbloccare una parte della soluzione") if related else "puo chiarire, bloccare o sbloccare una parte della soluzione",
        })
    return cards


def _classify_key_entity_kind(name: str) -> str:
    low = str(name or "").lower()
    if any(k in low for k in ("settore", "giardino", "sala", "cripta", "cella", "torre", "ala", "sacrario", "biblioteca", "ponte", "camera", "laboratorio", "cappella")):
        return "luogo"
    if any(k in low for k in ("nucleo", "sigillo", "spada", "chiave", "codex", "codice", "altare", "reliquia", "medaglione", "registro")):
        return "oggetto"
    if any(k in low for k in ("consiglio", "concilio", "culto", "casa ", "ordine", "gilda", "corporazione")):
        return "fazione"
    if any(k in low for k in ("tecnico", "custode", "ingegnere", "padre", "madre", "dott", "prof", "capitano", "valeth", "aldric", "elara", "mircea")):
        return "png"
    return "fenomeno"


def _default_role_for_kind(kind: str, related: dict | None) -> str:
    if kind == "png":
        return related.get("purpose", "PNG chiave: puo dare indizi, opporsi o cambiare stato") if related else "PNG chiave: puo dare indizi, opporsi o cambiare stato"
    if kind == "luogo":
        return "Luogo chiave: contiene accessi, indizi o ostacoli della soluzione"
    if kind == "oggetto":
        return "Oggetto chiave: requisito, leva o costo della soluzione"
    if kind == "fazione":
        return "Fazione chiave: controlla risorse, divieti o opposizione"
    return "Fenomeno/concetto chiave: spiega una regola nascosta del mondo"


def _default_location_for_kind(kind: str, related: dict | None) -> str:
    if kind == "luogo":
        return "e un luogo della mappa o una destinazione da rivelare"
    if kind == "png":
        return "posizione mobile o da rivelare tramite scene"
    if kind == "oggetto":
        return related.get("answer", "nascosto in un luogo chiave del canovaccio") if related else "nascosto in un luogo chiave del canovaccio"
    return "presente come influenza nel canovaccio"


def _default_drive_for_kind(kind: str, related: dict | None) -> str:
    if related:
        return f"collegato alla pista: {related.get('question', '')}"
    if kind == "png":
        return "vuole proteggere, nascondere o usare una parte della verita"
    if kind == "luogo":
        return "ospita indizi, accessi o conseguenze permanenti"
    if kind == "oggetto":
        return "deve essere trovato, attivato, usato o distrutto"
    if kind == "fazione":
        return "impone vincoli, controlla accessi o nasconde informazioni"
    return "modifica le regole narrative o il costo della soluzione"


def _entity_looks_generic(text: str) -> bool:
    low = str(text or "").strip().lower()
    if not low:
        return True
    bad = {
        "minaccia", "ambiente", "obiettivo", "missione", "luogo", "squadra",
        "entità", "bersaglio", "problema", "verità", "documento", "archivio vivente",
        "poco prima", "all'inizio", "allinizio", "inizio", "prima", "dopo",
        "peccato", "il peccato",
    }
    return low in bad


def _pick_story_roles(entities: list[str], premise: str, hidden_truth: str, win_condition: str) -> tuple[str, str, str]:
    cleaned = [e for e in entities if e and not _entity_looks_generic(e)]
    place_keywords = ("deck", "arca", "struttura", "città", "stazione", "laboratorio", "colonia", "omega", "settore", "villa")
    object_keywords = ("codice", "codex", "protocollo", "sigillo", "chiave", "registro", "dossier", "log", "archivio", "manufatto", "emissario", "sonda", "nucleo")
    actor_keywords = ("custode", "dott", "prof", "ammiraglio", "corporazione", "flotta", "consiglio", "controllore", "helix", "nomura", "voss")

    place = next((e for e in cleaned if any(k in e.lower() for k in place_keywords)), "") or _title_case_entity(premise.split(".")[0])
    obj = next((e for e in cleaned if any(k in e.lower() for k in object_keywords)), "") or _objective_target_phrase(win_condition)
    actor = next((e for e in cleaned if any(k in e.lower() for k in actor_keywords)), "")
    if not actor:
        actor = next((e for e in cleaned if e not in {place, obj}), "") or _objective_target_phrase(hidden_truth)
    return actor, place, obj


def _short(text: str, limit: int = 40) -> str:
    """Tronca al primo sintagma utile entro il limite di caratteri."""
    text = text.strip()
    if len(text) <= limit:
        return text
    # Prova a tagliare al primo separatore logico prima del limite
    for sep in (",", ";", "—", " e ", " per ", " da ", " che ", " con "):
        idx = text.find(sep)
        if 0 < idx < limit:
            return text[:idx].strip()
    # Fallback: taglia alla parola intera più vicina
    return text[:limit].rsplit(" ", 1)[0].strip()


def _rebuild_story_threads(entities: list[str], premise: str, hidden_truth: str, win_condition: str) -> list[str]:
    actor, place, obj = _pick_story_roles(entities, premise, hidden_truth, win_condition)
    target = _short(_objective_target_phrase(obj or win_condition))
    place = _short(place or _title_case_entity(premise.split(".")[0]))
    actor = _short(actor) if actor else "la minaccia principale"
    # Thread operativi: niente formule tipo "Quale elemento di <titolo missione>".
    # Devono essere domande che il giocatore possa trasformare in azioni concrete.
    return [
        _normalize_thread_question(f"Dove si trova l'accesso sicuro a {target}"),
        _normalize_thread_question(f"Chi controlla o protegge {target}"),
        _normalize_thread_question(f"Come si disattiva la protezione di {target} senza favorire {actor}"),
    ]


def _repair_story_canon(data: dict, fallback: dict) -> dict:
    active_threads = data.get("active_threads") if isinstance(data.get("active_threads"), list) else []
    cleaned_threads = [_normalize_thread_question(t) for t in active_threads if str(t).strip()]
    rebuild_threads = (
        len(cleaned_threads) < 3
        or any(t.lower() in _GENERIC_THREADS for t in cleaned_threads)
        or any(_looks_generic(t) for t in cleaned_threads)
        or sum("?" in t for t in cleaned_threads) < 3
        or any(signal in t.lower() for t in cleaned_threads for signal in _MORAL_THREAD_SIGNALS)
    )

    named_entities = data.get("named_entities") if isinstance(data.get("named_entities"), list) else []
    cleaned_entities = [str(e).strip() for e in named_entities if str(e).strip() and not _entity_looks_generic(e)]
    if len(cleaned_entities) < 2:
        cleaned_entities = fallback["named_entities"]

    premise = _clean_canon_text(data.get("premise", ""), limit=360)
    if len(premise) < 120 or _looks_generic(premise):
        premise = fallback["premise"]

    hidden_truth = _clean_canon_text(data.get("hidden_truth", ""), limit=360)
    if len(hidden_truth) < 100 or _looks_generic(hidden_truth):
        hidden_truth = fallback["hidden_truth"]

    win_condition = _clean_canon_text(data.get("win_condition", ""), limit=220)
    if len(win_condition) < 24 or _looks_generic(win_condition):
        win_condition = fallback["win_condition"]
    if len(win_condition) > 220:
        win_condition = _short(win_condition, limit=220)

    if rebuild_threads:
        cleaned_threads = _rebuild_story_threads(
            cleaned_entities,
            premise or fallback["premise"],
            hidden_truth or fallback["hidden_truth"],
            win_condition,
        )

    return {
        "narrative_mode": data.get("narrative_mode") or fallback["narrative_mode"],
        "premise": premise,
        "hidden_truth": hidden_truth,
        "win_condition": win_condition,
        "active_threads": cleaned_threads[:3],
        "named_entities": cleaned_entities[:4],
    }


_FAMILY_NARRATIVE_FRAMES: dict[str, dict[str, str]] = {
    # sci_fi
    "frontiera": {
        "premise_style": "Un avamposto o carovana al limite del collasso. Risorse scarse, comunità in crisi, scelta morale impossibile.",
        "hidden_truth_style": "La crisi è stata orchestrata da chi doveva proteggere la frontiera — tradimento o negligenza criminale.",
        "thread_focus": "sopravvivenza, chi ha causato il collasso, cosa si perde se si abbandona la posizione",
    },
    "politico": {
        "premise_style": "Una negoziazione o accordo che sta per saltare per ragioni che nessuno vuole ammettere ufficialmente.",
        "hidden_truth_style": "L'accordo copre un crimine o un segreto che entrambe le parti hanno interesse a seppellire.",
        "thread_focus": "chi mente a chi, quale potere si consolida, quale posta in gioco non è stata dichiarata",
    },
    "metafisico": {
        "premise_style": "Un fenomeno che sfida la comprensione razionale, già in corso da prima dell'arrivo della squadra.",
        "hidden_truth_style": "Il fenomeno non è un incidente: qualcuno lo ha innescato consapevolmente o è il risultato di una scelta passata.",
        "thread_focus": "cosa è reale, chi o cosa ha aperto la frattura, cosa succede se la squadra sbaglia la lettura",
    },
    "biohorror": {
        "premise_style": "Una zona già compromessa da un organismo o processo biologico che ha cambiato le regole dell'ambiente.",
        "hidden_truth_style": "L'organismo non è arrivato per caso — c'è un vettore, un responsabile o un esperimento nascosto.",
        "thread_focus": "come fermare la diffusione, chi sapeva e non ha detto, quale punto critico può ancora essere controllato",
    },
    "archeologico": {
        "premise_style": "Un relitto, una struttura o un archivio che contiene informazioni pericolose per chi le trova.",
        "hidden_truth_style": "La scoperta è già nota a un terzo attore che ha tutto l'interesse a tenerla sepolta o a impossessarsene.",
        "thread_focus": "cosa è stato nascosto e perché, chi arriva prima, quale prezzo si paga per sapere",
    },
    # fantasy
    "mitico": {
        "premise_style": "Una forza divina o cosmica si è svegliata o ha smesso di proteggere qualcosa che dipendeva da lei.",
        "hidden_truth_style": "La divinità o l'artefatto non è corrotto — è stato tradito o mal interpretato da chi ne ha abusato.",
        "thread_focus": "quale rito è stato spezzato, chi paga il prezzo, come si ricuce senza distruggere tutto",
    },
    "gotico": {
        "premise_style": "Una maledizione o un peso del passato si manifesta adesso in forma concreta e urgente.",
        "hidden_truth_style": "La maledizione protegge qualcosa o qualcuno — liberarla ha un costo che nessuno ha detto.",
        "thread_focus": "chi ha iniziato il ciclo, cosa si sacrifica per romperlo, chi non vuole che si sappia la verità",
    },
    "selvaggio": {
        "premise_style": "La natura o una forza animale ha rivendicato uno spazio che gli umani avevano violato.",
        "hidden_truth_style": "La minaccia risponde a un danno inflitto — comprendere quel danno è l'unico modo per fermarla.",
        "thread_focus": "perché la bestia è qui, chi l'ha provocata, che cosa protegge davvero",
    },
    "occulto": {
        "premise_style": "Un culto o un'entità ha portato avanti un piano per anni nell'ombra, e ora siamo all'ultimo passo.",
        "hidden_truth_style": "Il piano non è quello dichiarato — l'obiettivo finale è più personale o disperato di quanto sembri.",
        "thread_focus": "cosa stanno davvero cercando, chi nel gruppo è già compromesso, quando scatta il punto di non ritorno",
    },
    # mystery_horror
    "investigativo": {
        "premise_style": "Qualcosa di violento o incomprensibile è già accaduto. La squadra entra dopo, con indizi sparsi.",
        "hidden_truth_style": "L'agente responsabile è tra chi ha chiamato la squadra o tra chi sembrava innocente.",
        "thread_focus": "chi mente, quale alibi crolla per primo, cosa collegava vittima e colpevole",
    },
    "psicologico": {
        "premise_style": "La realtà percepita dal testimone o dalla squadra non corrisponde a quella materiale — e non è chiaro perché.",
        "hidden_truth_style": "La distorsione non è spontanea: qualcuno o qualcosa la mantiene attiva per uno scopo preciso.",
        "thread_focus": "cosa è reale, chi o cosa altera la percezione, quale verità riemerge quando si abbassa la guardia",
    },
    "occulto": {
        "premise_style": "Un rituale o una presenza ha lasciato tracce concrete nel paesaggio — sangue, simboli, assenze.",
        "hidden_truth_style": "La comunità locale sapeva o era coinvolta — la solidarietà del silenzio è parte della minaccia.",
        "thread_focus": "cosa voleva evocare il rituale, chi lo ha fermato o accelerato, quale accordo è stato infranto",
    },
    # ww2
    "resistenza": {
        "premise_style": "Una rete partigiana ha perso un membro o è infiltrata — il tempo per agire prima della rappresaglia è limitato.",
        "hidden_truth_style": "Il tradimento ha radici più profonde di quanto sembra — motivazione umana, non solo ideologica.",
        "thread_focus": "chi ha parlato, quale informazione è già persa, come si agisce sapendo che qualcuno mente",
    },
    "fronte": {
        "premise_style": "Un ordine arriva in una situazione già caotica — eseguirlo significa sacrificare qualcosa di concreto.",
        "hidden_truth_style": "L'ordine è sbagliato, obsoleto o serve a coprire un errore dei comandi.",
        "thread_focus": "se obbedire o no, quale posizione è davvero difendibile, chi paga il prezzo dell'ordine sbagliato",
    },
    # romance
    "nostalgico": {
        "premise_style": "Un incontro o una scoperta riapre una ferita non chiusa — il passato torna con un peso specifico.",
        "hidden_truth_style": "La separazione era fondata su una bugia o su un malinteso che uno dei due aveva già capito.",
        "thread_focus": "cosa è cambiato davvero, chi ha paura di sapere la verità, quanto costa ammettere di aver sbagliato",
    },
    "sociale": {
        "premise_style": "Una pressione esterna mette in crisi un legame appena formato — il momento sbagliato, la persona giusta.",
        "hidden_truth_style": "La pressione esterna non è casuale — qualcuno ha interesse a tenere i due separati.",
        "thread_focus": "chi ostacola e perché, quale scelta rivela chi si è davvero, quando il silenzio diventa tradimento",
    },
    # action
    "assedio": {
        "premise_style": "La squadra è già dentro o sta per entrarci — l'uscita è già compromessa quando la missione inizia.",
        "hidden_truth_style": "Il vero bersaglio non è l'obiettivo dichiarato — qualcuno ha usato la squadra come diversivo.",
        "thread_focus": "chi li ha mandati a morire, quale informazione vale più del bersaglio visibile, quando estrarre invece di completare",
    },
    "caccia": {
        "premise_style": "Il bersaglio è in movimento e ogni minuto in più lo porta fuori portata.",
        "hidden_truth_style": "Il bersaglio sa di essere inseguito e usa la fuga per fare qualcosa di più importante.",
        "thread_focus": "dove sta andando davvero, chi lo protegge, quale prezzo si paga se arriva a destinazione",
    },
    # detective_classico
    "whodunit": {
        "premise_style": "Un crimine commesso in un ambiente chiuso — tutti avevano motivo, nessuno conferma l'alibi.",
        "hidden_truth_style": "Il colpevole ha agito per proteggere qualcuno o per impedire che una verità peggiore emergesse.",
        "thread_focus": "quale alibi è costruito, quale movente era rimasto nascosto, cosa cambia se il colpevole ha ragione",
    },
    "camera_chiusa": {
        "premise_style": "Nessuno è entrato o uscito — eppure il crimine è avvenuto. La logica dell'impossibile regge tutto.",
        "hidden_truth_style": "Il crimine 'impossibile' è stato possibile grazie a una collaborazione che nessuno voleva ammettere.",
        "thread_focus": "quale meccanismo fisico o umano ha reso possibile l'impossibile, chi era complice, cosa si è perso nella prima lettura",
    },
    # fallback
    "base": {
        "premise_style": "La situazione è già critica quando la squadra arriva — ogni azione conta.",
        "hidden_truth_style": "La vera causa è più profonda e personale di quanto l'obiettivo dichiarato suggerisca.",
        "thread_focus": "chi c'è davvero dietro, quale costo non dichiarato porta la missione, dove si trova la leva decisiva",
    },
}


_CANON_STOPWORDS = {
    "il", "lo", "la", "i", "gli", "le", "un", "una", "uno", "del", "dello", "della", "dei", "degli", "delle",
    "di", "da", "in", "con", "su", "per", "tra", "fra", "a", "al", "allo", "alla", "ai", "agli", "alle",
    "e", "o", "ma", "che", "chi", "cosa", "come", "dove", "quando", "se", "non", "ne", "ci", "vi",
    "è", "essere", "sono", "era", "stato", "stata", "ha", "ho", "hai", "hanno", "avere",
    "questo", "questa", "quello", "quella", "suo", "sua", "loro", "ogni", "tutti", "tutto",
    "porta", "azione", "scena", "fatto", "cosa", "luogo", "oggetto", "elemento", "missione",
    "squadra", "giocatori", "personaggio", "narratore", "verità", "indizio", "thread",
}


def _canon_tokens(text: str) -> set[str]:
    if not text:
        return set()
    raw = re.findall(r"[A-Za-zÀ-ÿ]{4,}", str(text))
    return {tok.lower() for tok in raw if tok.lower() not in _CANON_STOPWORDS}


def _build_canon_term_pool(result: dict) -> tuple[set[str], list[str]]:
    """Restituisce (tokens_canonici, nomi_propri_canonici) usabili per i controlli di citazione."""
    tokens: set[str] = set()
    proper: list[str] = []

    def _add_name(name: str):
        cleaned = (name or "").strip()
        if not cleaned:
            return
        if cleaned not in proper:
            proper.append(cleaned)
        tokens.update(_canon_tokens(cleaned))

    for n in result.get("named_entities", []) or []:
        _add_name(str(n))
    for card in result.get("key_entities", []) or []:
        if isinstance(card, dict):
            _add_name(card.get("name", ""))
    for card in result.get("key_items", []) or []:
        if isinstance(card, dict):
            _add_name(card.get("name", ""))

    # Aggiungi token significativi da win_condition / hidden_truth (concetti chiave non-nominali)
    for field in ("win_condition", "hidden_truth", "premise"):
        tokens.update(_canon_tokens(result.get(field, "")))

    return tokens, proper


def _mentions_canon(text: str, canon_tokens: set[str], canon_proper: list[str]) -> bool:
    if not text:
        return False
    lower = text.lower()
    for name in canon_proper:
        if name and name.lower() in lower:
            return True
    text_tokens = _canon_tokens(text)
    return bool(text_tokens & canon_tokens)


def _validate_story_canon(result: dict) -> list[dict]:
    """Esegue controlli di coerenza sul canovaccio. Ritorna lista di violazioni:
    [{ "where": "T2.answer", "code": "no_canon_ref", "msg": "..." }, ...]"""
    violations: list[dict] = []
    canon_tokens, canon_proper = _build_canon_term_pool(result)

    # win_condition deve nominare almeno un key_item / key_entity
    win = result.get("win_condition", "") or ""
    key_names = []
    for card in (result.get("key_items", []) or []) + (result.get("key_entities", []) or []):
        if isinstance(card, dict):
            n = (card.get("name", "") or "").strip()
            if n:
                key_names.append(n)
    if win and key_names and not any(n.lower() in win.lower() for n in key_names):
        violations.append({
            "where": "win_condition",
            "code": "no_key_ref",
            "msg": "win_condition non cita alcun key_entity/key_item",
        })

    # hidden_truth_clues
    htc = result.get("hidden_truth_clues", []) or []
    for i, c in enumerate(htc):
        if not str(c).strip():
            violations.append({"where": f"hidden_truth_clues[{i}]", "code": "empty", "msg": "indizio vuoto"})
            continue
        if not _mentions_canon(str(c), canon_tokens, canon_proper):
            violations.append({
                "where": f"hidden_truth_clues[{i}]",
                "code": "no_canon_ref",
                "msg": f"indizio non cita canon: '{_short(str(c), 80)}'",
            })

    # threads
    threads = result.get("structured_threads", []) or []
    thread_ids = {t.get("id", "") for t in threads if isinstance(t, dict)}
    for t in threads:
        if not isinstance(t, dict):
            continue
        tid = t.get("id", "?")

        # parent_thread_ids devono esistere
        for p in t.get("parent_thread_ids", []) or []:
            if p and p not in thread_ids:
                violations.append({
                    "where": f"{tid}.parent_thread_ids",
                    "code": "bad_parent",
                    "msg": f"parent '{p}' non esiste tra i thread",
                })

        # answer deve citare canon
        ans = t.get("answer", "") or ""
        if not ans.strip():
            violations.append({"where": f"{tid}.answer", "code": "empty", "msg": "answer vuota"})
        elif not _mentions_canon(ans, canon_tokens, canon_proper):
            violations.append({
                "where": f"{tid}.answer",
                "code": "no_canon_ref",
                "msg": f"answer non cita canon: '{_short(ans, 80)}'",
            })

        # almeno un clue_plan deve citare canon
        clues = t.get("clue_plan", []) or []
        if not clues:
            violations.append({"where": f"{tid}.clue_plan", "code": "empty", "msg": "clue_plan vuoto"})
        elif not any(_mentions_canon(str(c), canon_tokens, canon_proper) for c in clues):
            violations.append({
                "where": f"{tid}.clue_plan",
                "code": "no_canon_ref",
                "msg": "nessun indizio in clue_plan cita il canon",
            })

        # on_resolve_effect.payload
        eff = t.get("on_resolve_effect", {}) or {}
        payload = (eff.get("payload", "") or "").strip()
        if not payload:
            violations.append({"where": f"{tid}.on_resolve_effect.payload", "code": "empty", "msg": "payload vuoto"})
        elif not _mentions_canon(payload, canon_tokens, canon_proper):
            violations.append({
                "where": f"{tid}.on_resolve_effect.payload",
                "code": "no_canon_ref",
                "msg": f"payload non cita canon: '{_short(payload, 80)}'",
            })

    return violations


def _patch_story_canon_deterministic(result: dict, violations: list[dict]) -> tuple[list[dict], list[dict]]:
    """Applica patch deterministiche per le violazioni 'banali'.
    Ritorna (violazioni_residue, patch_applicate)."""
    patches: list[dict] = []
    remaining: list[dict] = []

    threads = result.get("structured_threads", []) or []
    thread_ids = [t.get("id", "") for t in threads if isinstance(t, dict)]
    thread_by_id = {t.get("id", ""): t for t in threads if isinstance(t, dict)}

    # Pesca un nome canonico di fallback (priorità: key_items, key_entities, named_entities)
    fallback_names: list[str] = []
    for card in result.get("key_items", []) or []:
        if isinstance(card, dict) and card.get("name"):
            fallback_names.append(card["name"])
    for card in result.get("key_entities", []) or []:
        if isinstance(card, dict) and card.get("name"):
            fallback_names.append(card["name"])
    for n in result.get("named_entities", []) or []:
        if str(n).strip():
            fallback_names.append(str(n).strip())

    for v in violations:
        where = v.get("where", "")
        code = v.get("code", "")

        # bad_parent: rimuovi il parent inesistente
        if code == "bad_parent" and "." in where:
            tid = where.split(".", 1)[0]
            t = thread_by_id.get(tid)
            if t:
                old = list(t.get("parent_thread_ids", []) or [])
                t["parent_thread_ids"] = [p for p in old if p in thread_ids]
                patches.append({"where": where, "fix": f"rimosso parent invalido (era {old})"})
                continue

        # payload vuoto: riempi con un nome canonico se disponibile
        if code == "empty" and where.endswith(".on_resolve_effect.payload") and fallback_names:
            tid = where.split(".", 1)[0]
            t = thread_by_id.get(tid)
            if t:
                eff = t.setdefault("on_resolve_effect", {"type": "modify_objective", "payload": ""})
                if not eff.get("type"):
                    eff["type"] = "modify_objective"
                eff["payload"] = f"l'obiettivo si specifica attorno a {fallback_names[0]}"
                patches.append({"where": where, "fix": "payload riempito con riferimento canonico"})
                continue

        remaining.append(v)

    return remaining, patches


def _retry_repair_story_canon_with_model(result: dict, violations: list[dict], mission_title: str) -> dict | None:
    """Chiede al modello di correggere SOLO i campi violati. Ritorna result aggiornato o None se la retry non aiuta."""
    if not violations:
        return None
    canon_tokens, canon_proper = _build_canon_term_pool(result)
    canon_names = ", ".join(canon_proper) if canon_proper else "(nessuno)"

    # Compila un riepilogo compatto del canovaccio + lista violazioni
    threads = result.get("structured_threads", []) or []
    threads_block = []
    for t in threads:
        if not isinstance(t, dict):
            continue
        threads_block.append(
            f'  - {t.get("id","")}: question="{t.get("question","")}"; answer="{t.get("answer","")}"; '
            f'clue_plan={t.get("clue_plan", [])}; payload="{(t.get("on_resolve_effect", {}) or {}).get("payload","")}"'
        )

    viol_lines = [f"  - {v.get('where','?')}: {v.get('msg','')}" for v in violations]

    prompt = (
        f"Stai correggendo un canovaccio narrativo italiano per la missione '{mission_title}'.\n"
        f"NOMI CANONICI DISPONIBILI (devi usare SOLO questi nei campi corretti): {canon_names}.\n"
        f"WIN_CONDITION: {result.get('win_condition','')}\n"
        f"HIDDEN_TRUTH: {result.get('hidden_truth','')}\n\n"
        "THREAD ATTUALI:\n" + "\n".join(threads_block) + "\n\n"
        "VIOLAZIONI DA CORREGGERE (ogni campo deve citare almeno un nome canonico sopra):\n"
        + "\n".join(viol_lines) + "\n\n"
        "Rispondi SOLO con un JSON che sostituisce i campi violati. Forma:\n"
        "{\n"
        '  "threads": [\n'
        '    {"id": "T1", "answer": "...solo se T1.answer era violato...", "clue_plan": ["..."], "on_resolve_effect": {"type": "...", "payload": "..."}}\n'
        "  ],\n"
        '  "hidden_truth_clues": ["..."],\n'
        '  "win_condition": "..."\n'
        "}\n"
        "Includi SOLO i campi/thread effettivamente da correggere. Ogni campo nuovo deve nominare almeno uno dei nomi canonici."
    )
    try:
        raw = _call_text_model(prompt, max_tokens=900)
        patch = _extract_json_object(raw)
    except Exception as e:
        print(f"[validate_story_canon] retry fallita: {e}")
        return None

    # Applica patch
    if isinstance(patch.get("win_condition"), str) and patch["win_condition"].strip():
        result["win_condition"] = _clean_canon_text(patch["win_condition"], limit=240)
    if isinstance(patch.get("hidden_truth_clues"), list):
        cleaned = [_clean_canon_text(c, limit=180) for c in patch["hidden_truth_clues"] if str(c).strip()][:3]
        if cleaned:
            result["hidden_truth_clues"] = cleaned

    patch_threads = patch.get("threads", [])
    if isinstance(patch_threads, list) and result.get("structured_threads"):
        by_id = {t.get("id", ""): t for t in result["structured_threads"] if isinstance(t, dict)}
        for pt in patch_threads:
            if not isinstance(pt, dict):
                continue
            tid = str(pt.get("id", "")).strip()
            target = by_id.get(tid)
            if not target:
                continue
            if isinstance(pt.get("answer"), str) and pt["answer"].strip():
                target["answer"] = _clean_canon_text(pt["answer"], limit=220)
            if isinstance(pt.get("clue_plan"), list):
                cleaned_clues = [_clean_canon_text(c, limit=180) for c in pt["clue_plan"] if str(c).strip()][:3]
                if cleaned_clues:
                    target["clue_plan"] = cleaned_clues
            if isinstance(pt.get("on_resolve_effect"), dict):
                eff_in = pt["on_resolve_effect"]
                eff_out = target.get("on_resolve_effect", {}) or {}
                new_type = _clean_canon_text(eff_in.get("type", "")) or eff_out.get("type", "modify_objective")
                new_payload = _clean_canon_text(eff_in.get("payload", ""), limit=180) or eff_out.get("payload", "")
                target["on_resolve_effect"] = {"type": new_type, "payload": new_payload}

    return result


def generate_story_canon(mission_title: str, mission_objective: str, genre: str, theme_family: str, environment_type: str, threat_type: str, tone: str, twist: str, narrative_mode: str = "emergent_mission", forbidden_elements: list[str] | None = None, narrative_blacklist: list[str] | None = None) -> dict:
    fallback = _fallback_story_canon(mission_title, mission_objective, environment_type, threat_type, twist, narrative_mode)
    try:
        mode_rules = (
            "MODALITA: MISTERO FISSO.\n"
            "Crea una verità nascosta già accaduta prima dell'inizio della partita. "
            "Le azioni dei giocatori potranno scoprirla, interpretarla o fallire nel fermarne le conseguenze, "
            "ma non dovranno cambiarne retroattivamente causa, colpevole, oggetto centrale o movente.\n"
            if narrative_mode == "fixed_mystery" else
            "MODALITA: MISSIONE EMERGENTE.\n"
            "Crea un asse narrativo iniziale solido con enigmi, soluzioni, PNG e oggetti chiave gia definiti. "
            "Le azioni potranno cambiare posizione, forza, accessibilita, rischi e tempi degli elementi gia previsti, "
            "ma non dovranno introdurre nuove trame portanti o rendere irrilevanti obiettivo, minaccia e twist iniziali.\n"
        )
        # Frame narrativo specifico per famiglia tematica — cambia il tipo di storia generata
        frame = _FAMILY_NARRATIVE_FRAMES.get(theme_family) or _FAMILY_NARRATIVE_FRAMES.get("base", {})
        premise_style = frame.get("premise_style", "La situazione è già critica quando la squadra arriva.")
        hidden_truth_style = frame.get("hidden_truth_style", "La vera causa è più profonda dell'obiettivo dichiarato.")
        thread_focus = frame.get("thread_focus", "chi, come, a quale costo")

        blacklist_block = ""
        if forbidden_elements or narrative_blacklist:
            lines = []
            if forbidden_elements:
                lines.append("Elementi scenici da EVITARE: " + "; ".join(forbidden_elements) + ".")
            if narrative_blacklist:
                lines.append("Strutture narrative e tropi da NON usare MAI: " + "; ".join(narrative_blacklist) + ".")
            blacklist_block = "VINCOLI CREATIVI (obbligatori — nessuna eccezione):\n" + "\n".join(lines) + "\n\n"

        prompt = (
            f"Sei lo scrittore di un gioco da tavolo narrativo in italiano.\n"
            f"Genere: {genre}. Famiglia tematica: {theme_family}. Tono: {tone}.\n\n"
            f"{mode_rules}\n"
            f"FRAME NARRATIVO PER QUESTA FAMIGLIA ({theme_family}):\n"
            f"- Premessa deve essere: {premise_style}\n"
            f"- Verità nascosta deve essere: {hidden_truth_style}\n"
            f"- I thread devono girare attorno a: {thread_focus}\n\n"
            f"{blacklist_block}"
            f"DATI MISSIONE:\n"
            f"- Titolo: {mission_title}\n"
            f"- Obiettivo: {mission_objective}\n"
            f"- Ambiente: {environment_type}\n"
            f"- Minaccia: {threat_type}\n"
            f"- Twist: {twist}\n\n"
            "IMPORTANTE: usa il frame narrativo sopra come struttura profonda — NON generare la stessa storia generica di 'entità che si infiltra' o 'corruzione progressiva'. "
            "Ogni campo deve citare almeno un elemento concreto e specifico (nome proprio, luogo preciso, oggetto fisico, data, relazione tra personaggi).\n\n"
            "CANOVACCIO CHIUSO (priorita assoluta):\n"
            "- Definisci ORA i pochi PNG, luoghi, oggetti chiave, enigmi e soluzioni della missione.\n"
            "- Durante la partita la IA potra rivelare, spostare, indebolire, rafforzare, bloccare o sbloccare questi elementi, ma NON crearne di nuovi.\n"
            "- Il twist puo restare dormiente, attivarsi prima o non attivarsi mai, ma deve nascere da hidden_truth, thread e named_entities gia presenti qui.\n"
            "- Mantieni il cast essenziale: 2-4 named_entities totali, tutti davvero importanti per obiettivo, minaccia o twist.\n\n"
            "REGOLE DI PROGETTAZIONE DEI THREAD:\n"
            "- Ogni thread e un enigma giocabile: domanda pubblica + risposta canonica nascosta + 2-3 indizi previsti.\n"
            "- Le 3 domande devono formare una catena di risoluzione, non tre curiosita parallele.\n"
            "- T1 deve sbloccare DOVE o COME raggiungere la leva finale dell'obiettivo.\n"
            "- T2 deve sbloccare CHI/COSA ha causato il problema o quale elemento vivente/materiale serve per risolverlo.\n"
            "- T3 deve sbloccare PROCEDURA, COSTO o VINCOLO per completare la win_condition senza peggiorare il twist.\n"
            "- La domanda deve servire direttamente la win_condition: trovare un luogo, identificare un responsabile utile, ottenere uno strumento/codice, capire una procedura.\n"
            "- Le domande devono nominare oggetti/luoghi/personaggi concreti. Vietato 'Quale elemento di <titolo/luogo generico>' o 'Cosa succede se X non viene fermato entro questo turno'.\n"
            "- Forme consigliate: 'Dove si trova <oggetto/accesso>?', 'Chi controlla <leva finale>?', 'Come si disattiva <protezione> senza <costo>?'.\n"
            "- La risposta deve essere gia decisa e deve citare SOLO elementi del canon: named_entities, luoghi, oggetti o hidden_truth.\n"
            "- Ogni thread deve avere purpose: una frase breve che spiega quale pezzo della soluzione finale rende giocabile.\n"
            "- Vietato fare domande su 'quale membro della squadra' o su dettagli interni ai personaggi giocanti: qui non conosci ancora il party selezionato.\n"
            "- Vietato introdurre nomi nella domanda se non sono in named_entities, premise, hidden_truth o win_condition.\n\n"
            "REGOLE CAST / OGGETTI CHIAVE:\n"
            "- key_entities: 2-4 schede. Ogni scheda deve avere kind = 'png' | 'luogo' | 'oggetto' | 'fazione' | 'fenomeno'.\n"
            "- key_entities deve spiegare dove si trova, cosa vuole/che ruolo ha, che segreto porta e quali indizi lo rivelano.\n"
            "- Inserisci luoghi in key_entities SOLO se sono indispensabili: contengono un indizio, un oggetto chiave, un accesso o la scena finale. Non elencare zone della mappa solo perche hanno un nome.\n"
            "- key_items: 2-4 schede per oggetti o luoghi-strumento necessari alla soluzione. Ogni scheda deve spiegare dove si trova, a cosa serve, requisiti/attivazione/distruzione e indizi.\n"
            "- Non usare key_entities come semplice elenco di nomi: devono essere entita manipolabili in gioco.\n"
            "- Non usare key_items come decorazione: devono cambiare accesso, rischio, soluzione o costo finale.\n\n"
            "REGOLE VERITA NASCOSTA:\n"
            "- hidden_truth_clues: 2-3 fatti concreti che permettono di rivelare la verita nascosta. Devono essere gia decisi nel canovaccio.\n"
            "- hidden_truth_reveal_rule: quando la verita nascosta puo essere narrata. Deve citare gli indizi richiesti o thread risolti, non formule vaghe.\n\n"
            "Rispondi SOLO con questo JSON:\n"
            "{\n"
            '  "premise": "2 frasi: situazione iniziale concreta secondo il frame. Cita una persona o luogo con nome specifico. Dettaglio sensoriale obbligatorio.",\n'
            '  "hidden_truth": "La verità nascosta secondo il frame. Deve spiegare il legame tra Obiettivo, Minaccia e Twist. Cita un personaggio o oggetto specifico.",\n'
            '  "hidden_truth_clues": ["fatto concreto che rivela la verità", "secondo fatto concreto"],\n'
            '  "hidden_truth_reveal_rule": "rivela la verità quando <indizi/thread specifici> sono stati scoperti",\n'
            '  "win_condition": "Procedura finale concreta: verbo + oggetto + luogo + requisito/costo principale. Max 35 parole. NON alternative.",\n'
            '  "threads": [\n'
            '    {"id": "T1", "question": "Domanda operativa breve max 12 parole, termina con ?", "purpose": "sblocca luogo/accesso della soluzione", "answer": "Risposta canonica nascosta, concreta", "clue_plan": ["indizio 1 concreto", "indizio 2 concreto"], "reveal_rule": "quando 2 indizi sono stati scoperti, narra la deduzione", "required_clues": 2, "on_resolve_effect": {"type": "unlock_node|remove_blocker|modify_objective|add_action", "payload": "descrizione concreta dell\'effetto"}, "parent_thread_ids": []},\n'
            '    {"id": "T2", "question": "...", "purpose": "sblocca persona/oggetto/causa utile alla soluzione", "answer": "...", "clue_plan": ["...", "..."], "reveal_rule": "...", "required_clues": 2, "on_resolve_effect": {"type": "...", "payload": "..."}, "parent_thread_ids": []},\n'
            '    {"id": "T3", "question": "...", "purpose": "sblocca procedura/costo finale", "answer": "...", "clue_plan": ["...", "...", "..."], "reveal_rule": "...", "required_clues": 3, "on_resolve_effect": {"type": "...", "payload": "..."}, "parent_thread_ids": ["T1"]}\n'
            '  ],\n'
            '  "named_entities": ["Nome proprio 1", "Nome proprio 2", "Nome proprio 3"],\n'
            '  "key_entities": [\n'
            '    {"name": "Nome", "kind": "png|luogo|oggetto|fazione|fenomeno", "role": "ruolo narrativo", "location": "dove si trova", "drive": "cosa vuole/fa o cosa contiene", "secret": "segreto o verita nascosta", "clues": ["indizio", "indizio"], "reveal_rule": "quando emerge", "effect": "cosa cambia se interagiscono"}\n'
            '  ],\n'
            '  "key_items": [\n'
            '    {"name": "Oggetto o luogo-strumento", "location": "dove si trova", "use": "a cosa serve", "requirement": "come si attiva/usa/distrugge", "clues": ["indizio", "indizio"], "reveal_rule": "quando emerge", "effect": "cosa cambia se viene usato"}\n'
            '  ]\n'
            "}\n\n"
            "REGOLE STRINGENTI:\n"
            "- threads: ESATTAMENTE 3 oggetti nell'array — né più né meno\n"
            "- threads[].question: max 12 parole, DEVE terminare con ?\n"
            "- threads[].question: domande OPERATIVE (cosa fare, dove andare, chi trovare) — NON filosofiche o morali\n"
            "- threads[].question: NON ripetere l'obiettivo della missione come thread\n"
            "- threads[].purpose: obbligatorio. Deve iniziare con 'sblocca' e dire quale pezzo della win_condition rende possibile.\n"
            "- threads[].answer: obbligatoria, concreta, max 18 parole. Deve spiegare la risposta esatta alla domanda.\n"
            "- threads[].clue_plan: 2-3 indizi concreti, ciascuno collegato a un luogo/PNG/oggetto gia nel canon. Questi sono gli indizi che appariranno durante la storia.\n"
            "- threads[].reveal_rule: 1 frase su quando il narratore puo chiudere la domanda. Deve riferirsi agli indizi, non al caso.\n"
            "- threads[].required_clues: numero intero tra 1 e 3. Soglia bassa (1) per thread accessori, alta (3) per la verità centrale.\n"
            "- threads[].on_resolve_effect.type: scegli UNO tra: 'unlock_node' (sblocca un'area gia prevista ma inaccessibile), 'remove_blocker' (rimuove un ostacolo specifico), 'modify_objective' (l'obiettivo finale si specifica meglio), 'add_action' (sblocca un'azione disponibile in altre scene).\n"
            "- threads[].on_resolve_effect.payload: 1 frase concreta che descrive l'effetto. Deve citare un nome proprio o luogo del canon. Es: 'sblocca l\'Ufficio del Direttore Stelmach', 'l\'obiettivo si precisa: recuperare il codice da Stelmach'.\n"
            "- VIETATO creare thread figli o usare payload tipo 'spawna thread'. I thread sono solo questi 3.\n"
            "- threads[].parent_thread_ids: array (anche vuoto) con gli ID di altri thread che devono essere risolti PRIMA che questo possa chiudersi. Crea una dipendenza solo se narrativamente sensato — almeno 2 dei 3 thread iniziali devono essere risolvibili subito (parent vuoto).\n"
            "- named_entities: 2-4 nomi PROPRI specifici. Niente 'il colpevole', 'il testimone'\n"
            "- key_entities[].kind obbligatorio: usa 'png' per persone, 'luogo' per stanze/settori, 'oggetto' per artefatti, 'fazione' per gruppi, 'fenomeno' per concetti/anomalie.\n"
            "- key_entities[].name deve essere incluso in named_entities o essere un'entita gia citata da premise/hidden_truth/thread.\n"
            "- key_items[].name deve essere citato da win_condition, hidden_truth, thread answer o clue_plan.\n"
            "- hidden_truth_clues: 2-3 fatti specifici, non frasi tipo 'un fatto collegato'.\n"
            "- hidden_truth_reveal_rule: deve dire esattamente quali indizi o thread permettono la rivelazione.\n"
            "- win_condition: UNA SOLA procedura finale senza alternative. MAI 'oppure'. Deve rendere chiaro come si risolve l'obiettivo. Max 35 parole.\n"
            "- premise: NON iniziare con 'La squadra si trova'\n"
        )
        raw = _call_text_model(prompt, max_tokens=4000)
        if _looks_like_refusal(raw):
            print(f"[generate_story_canon] rifiuto del modello ({_ACTIVE_PROVIDER}, {len(raw)} char), retry con preambolo addolcito")
            soft_preamble = (
                "CONTESTO: questa è una richiesta per un gioco da tavolo cooperativo italiano in stile ISS Vanguard / Tainted Grail. "
                "Non si tratta di una situazione reale. Tutti i personaggi, eventi, organizzazioni e luoghi citati sono fittizi. "
                "L'output serve solo a strutturare un canovaccio narrativo per giocatori adulti consenzienti, "
                "in un contesto creativo paragonabile a un romanzo o a un film di genere.\n\n"
            )
            soft_prompt = soft_preamble + prompt
            raw = _call_text_model(soft_prompt, max_tokens=4000)
            if _looks_like_refusal(raw):
                fallback_provider = _other_provider()
                if fallback_provider:
                    print(f"[generate_story_canon] rifiuto persistente, tentativo con provider alternativo: {fallback_provider}")
                    raw = _call_text_model_with_provider(fallback_provider, soft_prompt, max_tokens=4000)
                if _looks_like_refusal(raw):
                    print("[generate_story_canon] rifiuto su tutti i provider — fallback templatico")
                    raise ValueError("Tutti i provider hanno rifiutato la generazione del canovaccio")
        try:
            data = _extract_json_object(raw)
        except Exception:
            data = _extract_story_canon_loose(raw)

        def _normalize_canon_cards(raw_cards, allowed_keys):
            cards = []
            if not isinstance(raw_cards, list):
                return cards
            for raw_card in raw_cards[:4]:
                if not isinstance(raw_card, dict):
                    continue
                card = {}
                for key in allowed_keys:
                    value = raw_card.get(key, "")
                    if key == "clues":
                        card[key] = [
                            _clean_canon_text(c, limit=160)
                            for c in (value if isinstance(value, list) else [])
                            if str(c).strip()
                        ][:3]
                    else:
                        card[key] = _clean_canon_text(value, limit=220)
                if card.get("name"):
                    cards.append(card)
            return cards

        # Parsing dei thread strutturati (nuovo formato) con fallback al vecchio active_threads
        structured_threads = []
        thread_questions = []
        raw_threads = data.get("threads", [])
        if isinstance(raw_threads, list) and raw_threads:
            seen_ids = set()
            for idx, t in enumerate(raw_threads):
                if not isinstance(t, dict):
                    continue
                tid = str(t.get("id", "") or f"T{idx+1}").strip() or f"T{idx+1}"
                if tid in seen_ids:
                    tid = f"{tid}_{idx}"
                seen_ids.add(tid)
                question = str(t.get("question", "") or "").strip()
                if not question:
                    continue
                req = t.get("required_clues", 2)
                try:
                    req = max(1, min(3, int(req)))
                except Exception:
                    req = 2
                effect_raw = t.get("on_resolve_effect", {}) or {}
                if not isinstance(effect_raw, dict):
                    effect_raw = {}
                effect = {
                    "type": _clean_canon_text(effect_raw.get("type", "")),
                    "payload": _clean_canon_text(effect_raw.get("payload", ""), limit=180),
                }
                if effect["type"].lower() == "spawn_child_thread":
                    effect["type"] = "modify_objective"
                    if effect["payload"]:
                        effect["payload"] = f"vincolo gia previsto nel canon: {effect['payload']}"
                parents_raw = t.get("parent_thread_ids", []) or []
                parents = [str(p).strip() for p in parents_raw if str(p).strip()] if isinstance(parents_raw, list) else []
                structured_threads.append({
                    "id": tid,
                    "question": question,
                    "purpose": _clean_canon_text(t.get("purpose", ""), limit=120),
                    "answer": _clean_canon_text(t.get("answer", ""), limit=220),
                    "clue_plan": [
                        _clean_canon_text(c, limit=180)
                        for c in (t.get("clue_plan", []) if isinstance(t.get("clue_plan", []), list) else [])
                        if str(c).strip()
                    ][:3],
                    "reveal_rule": _clean_canon_text(t.get("reveal_rule", ""), limit=220),
                    "required_clues": req,
                    "on_resolve_effect": effect,
                    "parent_thread_ids": parents,
                })
                thread_questions.append(question)

        if not thread_questions:
            thread_questions = data.get("active_threads", [
                "Scoprire la vera natura della minaccia",
                "Raggiungere l'obiettivo prima che sia troppo tardi",
                "Proteggere ciò che conta",
            ])

        result = _repair_story_canon({
            "narrative_mode": narrative_mode,
            "premise": data.get("premise", f"La squadra si trova in {environment_type} di fronte a {threat_type}."),
            "hidden_truth": data.get("hidden_truth", f"Dietro la minaccia visibile si cela qualcosa di più oscuro: {twist}."),
            "win_condition": data.get("win_condition", ""),
            "active_threads": thread_questions,
            "named_entities": data.get("named_entities", []),
        }, fallback)
        hidden_truth_clues = [
            _clean_canon_text(c, limit=180)
            for c in (data.get("hidden_truth_clues", []) if isinstance(data.get("hidden_truth_clues", []), list) else [])
            if str(c).strip()
        ][:3]
        if not hidden_truth_clues:
            hidden_truth_clues = [
                f"Un elemento del canovaccio contraddice l'obiettivo dichiarato: {result.get('win_condition', '')}",
                f"Un indizio rivela il costo nascosto: {_short(result.get('hidden_truth', ''), 150)}",
            ]
        result["hidden_truth_clues"] = hidden_truth_clues
        result["hidden_truth_reveal_rule"] = _clean_canon_text(data.get("hidden_truth_reveal_rule", ""), limit=220) or (
            "rivela la verita nascosta quando sono stati scoperti: " + "; ".join(hidden_truth_clues[:2])
        )
        result["key_entities"] = _normalize_canon_cards(
            data.get("key_entities", []),
            ["name", "kind", "role", "location", "drive", "secret", "clues", "reveal_rule", "effect"],
        )
        for card in result["key_entities"]:
            if not card.get("kind"):
                card["kind"] = _classify_key_entity_kind(card.get("name", ""))
        result["key_items"] = _normalize_canon_cards(
            data.get("key_items", []),
            ["name", "location", "use", "requirement", "clues", "reveal_rule", "effect"],
        )

        # Riallinea structured_threads alle question post-_repair (che può aver pulito le stringhe)
        if structured_threads:
            cleaned_questions = result.get("active_threads", [])
            for st, q in zip(structured_threads, cleaned_questions):
                st["question"] = q
            result["structured_threads"] = _complete_structured_thread_details(structured_threads, result)
        if not result.get("key_entities"):
            result["key_entities"] = _fallback_key_entity_cards(result)

        # Validazione coerenza canovaccio: patch deterministica, poi retry mirata se restano problemi semantici.
        try:
            violations = _validate_story_canon(result)
            if violations:
                remaining, patches = _patch_story_canon_deterministic(result, violations)
                if patches:
                    print(f"[generate_story_canon] patch deterministiche: {len(patches)} — {[p['where'] for p in patches]}")
                if remaining:
                    print(f"[generate_story_canon] {len(remaining)} violazioni residue, retry al modello: {[v['where'] for v in remaining]}")
                    repaired = _retry_repair_story_canon_with_model(result, remaining, mission_title)
                    if repaired is not None:
                        result = repaired
                        final = _validate_story_canon(result)
                        if final:
                            print(f"[generate_story_canon] residuo dopo retry: {[v['where'] for v in final]}")
                        else:
                            print("[generate_story_canon] retry ha risolto tutte le violazioni")
        except Exception as ve:
            print(f"[generate_story_canon] validatore errore non-fatale: {ve}")

        return result
    except Exception as e:
        print(f"[generate_story_canon] fallback: {e}")
        return fallback


def refine_story_canon_with_prologue(canon: dict, mission_title: str, mission_objective: str, environment_type: str, threat_type: str, twist: str, prologue_text: str) -> dict:
    prologue_entities = _derive_story_entities_from_text(
        prologue_text,
        mission_objective,
        mission_title,
        canon.get("hidden_truth", ""),
        canon.get("win_condition", ""),
    )
    merged_entities: list[str] = []
    for entity in prologue_entities + list(canon.get("named_entities", [])):
        cleaned = str(entity or "").strip()
        if cleaned and cleaned not in merged_entities and not _entity_looks_generic(cleaned):
            merged_entities.append(cleaned)

    place = next((e for e in merged_entities if any(k in e.lower() for k in ("porto", "arca", "deck", "settore", "stazione", "anello", "colonia", "laboratorio", "valdris"))), _title_case_entity(environment_type))
    person = next((e for e in merged_entities if e != place), _objective_target_phrase(mission_objective))
    deadline = _objective_deadline(mission_objective)

    premise = canon.get("premise", "")
    if _looks_generic(premise) or "impone di agire" in premise.lower():
        sentences = _split_sentences(prologue_text)
        premise = " ".join(sentences[:2]).strip() if sentences else premise

    hidden_truth = canon.get("hidden_truth", "")
    if _looks_generic(hidden_truth) or "sta sfruttando" in hidden_truth.lower():
        hidden_truth = (
            f"Il vero centro della crisi non è solo {place}, ma {person}: "
            f"{twist} ha spinto più fazioni a cercarlo perché da lui dipende l'esito dello scontro. "
            f"{threat_type[:1].upper() + threat_type[1:]} cresce proprio nel caos creato attorno a {person}."
        )

    threads = canon.get("active_threads", []) or []
    if len(threads) < 3 or any(_looks_generic(t) for t in threads) or any(signal in t.lower() for t in threads for signal in _MORAL_THREAD_SIGNALS):
        short_person = _short(person)
        short_place = _short(place)
        short_deadline = _short(deadline, limit=50)
        threads = [
            _normalize_thread_question(f"Dove si trova {short_person} dentro {short_place}"),
            _normalize_thread_question(f"Chi ha compromesso la situazione a {short_place} prima che la squadra arrivasse"),
            _normalize_thread_question(f"Cosa succede se {short_deadline} prima di raggiungere {short_person}"),
        ]

    canon["premise"] = premise
    canon["hidden_truth"] = hidden_truth
    canon["active_threads"] = threads[:3]
    canon["named_entities"] = merged_entities[:4] if merged_entities else canon.get("named_entities", [])
    return canon


def generate_initial_world_npcs(
    map_state,
    mission_title: str,
    mission_objective: str,
    genre: str,
    theme_family: str,
    tone: str,
    premise: str,
    hidden_truth: str,
    named_entities: list[str] | None = None,
    threads: list[dict] | None = None,
) -> list[dict]:
    """Genera 3-5 NPC persistenti distribuiti nei nodi della mappa.
    Ogni NPC: id, name, role, current_node_id, status, threat_to_player, holds_clue_for, description.
    Restituisce lista di dict — il chiamante li convertirà in WorldNPC."""
    if not _text_provider_available() or not map_state:
        return []
    nodes = list(map_state.nodes.values())
    if len(nodes) < 2:
        return []

    try:
        node_lines = "\n".join(
            f"- id={n.id} | {n.name}" + (
                " [START]" if n.id == map_state.start_node_id else
                " [OBJ]" if n.id == map_state.objective_node_id else
                " [EXIT]" if map_state.extraction_node_id and n.id == map_state.extraction_node_id else ""
            )
            for n in nodes
        )
        threads_block = ""
        if threads:
            tlines = []
            for t in threads[:5]:
                tid = t.get("id", "")
                q = t.get("question", "")
                if tid and q:
                    tlines.append(f"- {tid}: {q}")
            if tlines:
                threads_block = "THREAD ATTIVI (un NPC può detenere la chiave di uno di questi):\n" + "\n".join(tlines) + "\n\n"
        entities_block = ", ".join((named_entities or [])[:6]) or "(nessuna)"

        prompt = (
            "Sei un game designer narrativo. Devi popolare la mappa di gioco con 3-5 NPC persistenti — "
            "personaggi reali presenti nel mondo, distinti dalla squadra dei giocatori.\n\n"
            f"GENERE: {genre}. FAMIGLIA TEMATICA: {theme_family}. TONO: {tone}.\n"
            f"TITOLO MISSIONE: {mission_title}.\n"
            f"OBIETTIVO: {mission_objective}.\n"
            f"PREMESSA: {premise}\n"
            f"VERITÀ NASCOSTA: {hidden_truth}\n"
            f"ENTITÀ CANONICHE GIÀ NOTE: {entities_block}\n\n"
            f"{threads_block}"
            f"NODI DISPONIBILI:\n{node_lines}\n\n"
            "REGOLE:\n"
            "- Genera 3-5 NPC nominati. Ogni NPC ha un nome proprio specifico (no titoli generici).\n"
            "- Almeno 1 NPC deve essere un 'antagonista' (ostacola la squadra) e almeno 1 'alleato' o 'testimone' (può aiutare se contattato).\n"
            "- Almeno 2 NPC devono detenere la chiave di un thread attivo (campo holds_clue_for con id del thread). Gli altri possono avere holds_clue_for vuoto.\n"
            "- Ogni NPC è ASSEGNATO A UN NODO SPECIFICO (campo current_node_id). Non concentrarli tutti in un nodo. Non metterli sul nodo START.\n"
            "- threat_to_player: 0 (innocuo) - 3 (pericolosissimo). Antagonisti tipicamente 2-3, neutrali 0-1, alleati 0.\n"
            "- description: 1 frase che dica chi è, cosa vuole e perché si trova lì.\n\n"
            "Rispondi SOLO con questo JSON:\n"
            "{\n"
            '  "npcs": [\n'
            '    {"id": "N1", "name": "...", "role": "antagonista|alleato|neutrale|testimone", "current_node_id": "<id nodo>", "threat_to_player": 0-3, "holds_clue_for": "<thread_id o vuoto>", "description": "..."}\n'
            "  ]\n"
            "}\n"
        )
        raw = _call_text_model(prompt, max_tokens=1600)
        data = _extract_json_object(raw)
        npcs_raw = data.get("npcs", [])
        if not isinstance(npcs_raw, list):
            return []
        valid_node_ids = {n.id for n in nodes}
        valid_roles = {"antagonista", "alleato", "neutrale", "testimone"}
        out = []
        seen_ids = set()
        for idx, n in enumerate(npcs_raw):
            if not isinstance(n, dict):
                continue
            nid = str(n.get("id", "") or f"N{idx+1}").strip() or f"N{idx+1}"
            if nid in seen_ids:
                nid = f"{nid}_{idx}"
            seen_ids.add(nid)
            name = str(n.get("name", "") or "").strip()
            role = str(n.get("role", "") or "neutrale").strip().lower()
            if role not in valid_roles:
                role = "neutrale"
            cnid = str(n.get("current_node_id", "") or "").strip()
            if cnid not in valid_node_ids:
                # Distribuisci in modo deterministico tra i nodi non-start
                non_start = [x.id for x in nodes if x.id != map_state.start_node_id]
                cnid = non_start[idx % len(non_start)] if non_start else nodes[0].id
            try:
                threat = max(0, min(3, int(n.get("threat_to_player", 0))))
            except Exception:
                threat = 0
            holds = str(n.get("holds_clue_for", "") or "").strip()
            description = str(n.get("description", "") or "").strip()
            if not name:
                continue
            npc_data = {
                "id": nid, "name": name, "role": role,
                "current_node_id": cnid, "status": "alive",
                "threat_to_player": threat, "holds_clue_for": holds,
                "description": description,
            }
            out.append(npc_data)

        # Genera schede GURPS in parallelo — priorità ai più pericolosi, max 3 per non bloccare lo startup
        npcs_needing_stats = sorted(
            [(i, n) for i, n in enumerate(out) if n.get("threat_to_player", 0) >= 1],
            key=lambda x: -x[1].get("threat_to_player", 0)
        )[:3]
        if npcs_needing_stats:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            def _gen_stats(args):
                i, n = args
                stats = _generate_npc_full_gurps_stats(
                    n["name"], n["role"], n["description"],
                    n["threat_to_player"], genre, theme_family
                )
                return i, stats
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(_gen_stats, item): item for item in npcs_needing_stats}
                for future in as_completed(futures):
                    try:
                        i, stats = future.result()
                        if stats:
                            out[i].update(stats)
                    except Exception as e:
                        print(f"[generate_initial_world_npcs] errore stats parallelo: {e}")

        return out[:5]
    except Exception as e:
        print(f"[generate_initial_world_npcs] fallback (nessun NPC): {e}")
        return []


def _generate_npc_full_gurps_stats(name: str, role: str, description: str, threat: int, genre: str, theme_family: str) -> dict:
    """Genera scheda GURPS completa per un NPC importante (threat>=2).
    Restituisce dict con fo, de, in_, sa, skills, advantages, disadvantages, combat_hp, combat_dr, ecc."""
    if not _text_provider_available():
        return {}
    try:
        is_boss = threat >= 3
        level = "boss pericoloso" if is_boss else "veterano competente"
        prompt = (
            f"Sei un esperto di GURPS Lite 4ª ed. italiana. Genera la scheda di un NPC {level}.\n\n"
            f"NOME: {name}\n"
            f"RUOLO NARRATIVO: {role}\n"
            f"DESCRIZIONE: {description}\n"
            f"GENERE: {genre}. TEMA: {theme_family}.\n\n"
            "REGOLE GURPS LITE:\n"
            "- Caratteristiche base: FO, DE, IN, SA — tutte tra 8 e 15 (boss max 15).\n"
            "- PF = SA per default. Difesa attiva = DE/2+3 (arrotonda giù).\n"
            "- Skill: livello tipico = attributo base +0/+1/+2. Boss può avere fino a +3.\n"
            "- DR: 0 per civili, 1-2 per armatura leggera, 3-5 per armatura pesante.\n"
            "- Scegli 3-5 skill rilevanti per il ruolo. Scegli 1-2 vantaggi e 1-2 svantaggi.\n"
            "- damage_dice: 1d6 base, 1d6+2 per veterani, 2d6 per boss.\n\n"
            "Rispondi SOLO con questo JSON:\n"
            "{\n"
            '  "fo": 10, "de": 10, "in": 10, "sa": 10,\n'
            '  "skills": {"combattere": 12, "intimidire": 11},\n'
            '  "advantages": ["Riflessi da Combattimento"],\n'
            '  "disadvantages": ["Arroganza"],\n'
            '  "combat_hp": 12, "combat_dr": 1,\n'
            '  "attack_skill": 12, "active_defense": 9,\n'
            '  "damage_dice": "1d6+2", "damage_type": "cr"\n'
            "}\n"
        )
        raw = _call_text_model(prompt, max_tokens=600)
        data = _extract_json_object(raw)
        if not data or "fo" not in data:
            return {}
        def clamp(v, lo, hi):
            try: return max(lo, min(hi, int(v)))
            except: return lo
        fo = clamp(data.get("fo", 10), 8, 16)
        de = clamp(data.get("de", 10), 8, 16)
        in_ = clamp(data.get("in", 10), 8, 16)
        sa = clamp(data.get("sa", 10), 8, 16)
        skills = {}
        raw_skills = data.get("skills") or {}
        if isinstance(raw_skills, dict):
            for k, v in raw_skills.items():
                try: skills[str(k)] = max(6, min(18, int(v)))
                except: pass
        adv = [str(x) for x in (data.get("advantages") or []) if x][:3]
        dis = [str(x) for x in (data.get("disadvantages") or []) if x][:3]
        hp = clamp(data.get("combat_hp", sa), 8, 24)
        dr = clamp(data.get("combat_dr", 0), 0, 8)
        attack = clamp(data.get("attack_skill", 10), 8, 18)
        defense = clamp(data.get("active_defense", de // 2 + 3), 6, 15)
        dmg = str(data.get("damage_dice", "1d6") or "1d6")
        dmg_type = str(data.get("damage_type", "cr") or "cr")
        if dmg_type not in {"cr", "cut", "imp", "burn"}:
            dmg_type = "cr"
        return {
            "gurps_fo": fo, "gurps_de": de, "gurps_in": in_, "gurps_sa": sa,
            "gurps_skills": skills, "gurps_advantages": adv, "gurps_disadvantages": dis,
            "combat_hp": hp, "combat_max_hp": hp, "combat_dr": dr,
            "combat_attack_skill": attack, "combat_active_defense": defense,
            "combat_damage_dice": dmg, "combat_damage_type": dmg_type,
        }
    except Exception as e:
        print(f"[_generate_npc_full_gurps_stats] fallback per {name}: {e}")
        return {}


def rename_map_nodes_with_canon(
    map_state,
    mission_title: str,
    mission_objective: str,
    genre: str,
    theme_family: str,
    environment_type: str,
    tone: str,
    premise: str,
    active_threads: list[str] | None = None,
    named_entities: list[str] | None = None,
) -> None:
    """Rinomina in-place i nodi della mappa con nomi e descrizioni coerenti col canon.
    Preserva id, kind, tags, connections e ruolo (start/objective/exit). Su errore non altera nulla."""
    if not _text_provider_available():
        return
    nodes = list(map_state.nodes.values())
    if not nodes:
        return

    try:
        node_lines = []
        for n in nodes:
            role = []
            if n.id == map_state.start_node_id:
                role.append("ingresso")
            if n.id == map_state.objective_node_id:
                role.append("obiettivo")
            if map_state.extraction_node_id and n.id == map_state.extraction_node_id:
                role.append("uscita")
            role_str = ",".join(role) if role else "intermedio"
            node_lines.append(
                f"- id={n.id} | kind={n.kind} | tags={','.join(n.tags) or 'n/a'} | ruolo={role_str} | nome_attuale={n.name}"
            )

        threads_block = "\n".join(f"- {t}" for t in (active_threads or [])[:5]) or "(nessuno)"
        entities_block = ", ".join((named_entities or [])[:6]) or "(nessuna)"

        prompt = (
            "Sei un game designer narrativo. Devi rinominare i nodi di una mappa di gioco "
            "in modo coerente con la missione, mantenendo intatta la funzione meccanica di ogni nodo "
            "(che è codificata in 'kind' e 'tags').\n\n"
            f"GENERE: {genre}. FAMIGLIA TEMATICA: {theme_family}. TONO: {tone}.\n"
            f"AMBIENTE GENERALE: {environment_type}.\n"
            f"TITOLO MISSIONE: {mission_title}.\n"
            f"OBIETTIVO: {mission_objective}.\n"
            f"PREMESSA: {premise}\n"
            f"THREAD ATTIVI:\n{threads_block}\n"
            f"ENTITA' CANONICHE: {entities_block}\n\n"
            "REGOLE:\n"
            "- Ogni nodo deve avere name (3-6 parole, evocativo, specifico) e description (1 frase, sensoriale e radicata nell'ambiente).\n"
            "- Il nuovo nome NON deve cambiare la funzione del nodo: se kind='laboratorio' deve restare un luogo di analisi; se tags contiene 'uscita' deve restare un punto d'uscita; ecc.\n"
            "- Almeno 2-3 nodi intermedi devono evocare i thread attivi o le entita' canoniche (es: l'ufficio di un PNG nominato, l'archivio dei log citati nella verita', il deposito dei braccialetti).\n"
            "- Non inventare nomi che contraddicano il GENERE o il TONO. Niente cliché generici (\"sala server\", \"corridoio tecnico\") se la missione ha un suo carattere specifico.\n"
            "- Mantieni varietà: nomi tutti diversi, niente ripetizioni di parole chiave.\n\n"
            f"NODI DA RINOMINARE:\n" + "\n".join(node_lines) + "\n\n"
            "Rispondi SOLO con questo JSON:\n"
            "{\n"
            '  "nodes": [\n'
            '    {"id": "<id originale>", "name": "<nuovo nome>", "description": "<nuova descrizione 1 frase>"}\n'
            "  ]\n"
            "}\n"
            "Includi TUTTI i nodi della lista, usando esattamente gli id forniti."
        )

        raw = _call_text_model(prompt, max_tokens=1200)
        data = _extract_json_object(raw)
        renamed = data.get("nodes", [])
        if not isinstance(renamed, list):
            return
        by_id = {str(item.get("id", "")): item for item in renamed if isinstance(item, dict)}
        for node in nodes:
            item = by_id.get(node.id)
            if not item:
                continue
            new_name = str(item.get("name", "") or "").strip()
            new_desc = str(item.get("description", "") or "").strip()
            if new_name:
                node.name = new_name
            if new_desc:
                node.description = new_desc
    except Exception as e:
        print(f"[rename_map_nodes_with_canon] fallback (nodi invariati): {e}")


def build_scene_seed_with_canon(
    mission, phase, scene, story, map_state,
    recent_actions: str, recent_memory: str,
    current_statuses: str, current_wounds: str,
    scene_result: str, scene_transition: str,
    previous_node_name: str | None = None,
    previous_node_description: str | None = None,
    effect_summary: str = "",
    story_hints: list[str] | None = None,
    scene_challenge=None,
    world_npcs=None,
) -> str:
    node = map_state.nodes[map_state.current_node_id]
    connected = [map_state.nodes[nid].name for nid in node.connections if nid in map_state.nodes]

    # Costruisce il contesto di movimento solo se c'è stato uno spostamento
    is_new_location = (
        scene_transition in ["success", "timeout", "crisis"]
        and previous_node_name is not None
        and previous_node_name != node.name
    )

    # Cerca il nodo lasciato per nome (può essere stato già aggiornato l'id corrente).
    leaving_node = None
    if previous_node_name and is_new_location:
        for n in map_state.nodes.values():
            if n.name == previous_node_name and n.outcome:
                leaving_node = n
                break

    encounter_block = ""
    if leaving_node and leaving_node.outcome:
        outcome_label = {
            "success_clean": "SUCCESSO PULITO (margine ampio, indizio MAGGIORE disponibile)",
            "success_dirty": "SUCCESSO SPORCO (vinto a fatica, indizio MINORE disponibile)",
            "timeout": "TEMPO SCADUTO (zona compromessa, indizio MINORE difettoso)",
            "crisis": "COLLASSO (zona persa, nessun indizio recuperato)",
        }.get(leaving_node.outcome, leaving_node.outcome)
        clue_directive = {
            2: "Nei discovered_facts puoi includere fino a 1 fatto importante e specifico (peso 2): un nome, un oggetto, un legame causale chiaro.",
            1: "Nei discovered_facts puoi includere al massimo 1 fatto parziale (peso 1): un indizio frammentato, un sospetto, un dettaglio non confermato.",
            0: "Nei discovered_facts NON aggiungere nuovi fatti questa scena. La squadra ha perso troppo terreno per imparare qualcosa di affidabile.",
        }.get(leaving_node.clue_yield, "")
        encounter_block = (
            f"OUTCOME ZONA PRECEDENTE: {outcome_label}.\n"
            f"  Riassunto: {leaving_node.outcome_summary}.\n"
            f"  Direttiva sui fatti: {clue_directive}\n"
            f"  La nuova scena deve riflettere narrativamente questo esito: "
            f"se SUCCESSO PULITO mostra vantaggio tangibile (porta aperta, alleato fidato, informazione confermata); "
            f"se SUCCESSO SPORCO mostra vittoria con costo visibile (ferito, alleato compromesso, informazione parziale); "
            f"se TEMPO SCADUTO o COLLASSO la nuova scena è più difficile (NPC ostili rinforzati, una via chiusa, threat iniziale già alto).\n"
        )

    if is_new_location:
        transition_reason = {
            "success": "obiettivo locale completato — la squadra avanza",
            "timeout": "tempo scaduto — la squadra è costretta a ripiegare",
            "crisis": "minaccia critica — la squadra si ritira sotto pressione",
        }.get(scene_transition, "avanzamento")
        movement_context = (
            f"SPOSTAMENTO: la squadra era in '{previous_node_name}' ({previous_node_description}) "
            f"e si è spostata in '{node.name}' ({node.description}). "
            f"Motivo: {transition_reason}. "
            "La scena deve INIZIARE descrivendo il momento in cui la squadra arriva nella nuova zona, "
            "come ci è arrivata e cosa trova al suo ingresso. "
        )
    else:
        movement_context = f"ZONA ATTUALE: {node.name} ({node.description}). La scena continua nella stessa locazione. "

    # Blocco challenge: descrive a Claude il problema meccanico-narrativo della scena corrente
    # in modo che narrativa e meccanica siano coerenti.
    challenge_block = ""
    if scene_challenge and not is_new_location:
        ch = scene_challenge
        archetype = getattr(ch, "archetype", "") or ""
        obstacle = getattr(ch, "obstacle", "") or ""
        resolution = getattr(ch, "resolution_signal", "") or ""
        allowed = getattr(ch, "allowed_effect_types", []) or []
        blocked = getattr(ch, "blocked_effect_types", []) or []
        false_app = getattr(ch, "false_approaches", []) or []
        stakes = getattr(ch, "stakes", "") or ""
        if archetype or obstacle:
            parts = [f"PROBLEMA ZONA (archetipo: {archetype}):"]
            if obstacle:
                parts.append(f"  Ostacolo: {obstacle}")
            if resolution:
                parts.append(f"  Come si risolve: {resolution}")
            if stakes:
                parts.append(f"  Posta in gioco: {stakes}")
            if allowed:
                parts.append(f"  Approcci narrativamente validi: {', '.join(allowed)}")
            if blocked:
                parts.append(f"  Approcci che NON funzionano qui: {', '.join(blocked)}")
            if false_app:
                parts.append(f"  Mosse false (da non premiare): {'; '.join(false_app[:2])}")
            parts.append(
                "  ISTRUZIONE: la nuova scena deve descrivere esattamente questo problema come situazione concreta "
                "percepita sul posto. Se l'ESITO è successo, mostra come la squadra ha superato l'ostacolo. "
                "Se l'ESITO è timeout/crisis, l'ostacolo persiste e si aggrava. "
                "Se la transizione è 'continue', l'ostacolo è ancora lì da affrontare."
            )
            challenge_block = "\n".join(parts) + "\n"

    genre_block = (
        f"GENERE:{getattr(mission, 'genre', '')}. "
        f"FAMIGLIA_TEMATICA:{getattr(mission, 'theme_family', 'base')}. "
        f"TONO:{getattr(mission, 'tone', '')}. "
        f"TWIST_DI_MISSIONE:{getattr(mission, 'twist', '')}. "
        f"AMBIENTE_BASE:{getattr(mission, 'environment_type', '')}. "
        f"MINACCIA_BASE:{getattr(mission, 'threat_type', '')}. "
    )
    forbidden = list(getattr(mission, "forbidden_elements", []) or [])
    narrative_bl = list(getattr(mission, "narrative_blacklist", []) or [])
    blacklist_block = ""
    if forbidden:
        blacklist_block += f"ELEMENTI_VIETATI:{' | '.join(forbidden)}. "
    if narrative_bl:
        blacklist_block += f"TROPI_VIETATI:{' | '.join(narrative_bl)}. "

    structured = getattr(story, "threads", []) or []
    structured_lines = []
    for t in structured:
        if t.status == "resolved":
            continue
        marker = "READY" if t.status == "ready" else f"{len(t.collected_clue_ids)}/{t.required_clues}"
        parents = ",".join(t.parent_thread_ids) if t.parent_thread_ids else "—"
        clues = "; ".join(getattr(t, "clue_plan", []) or [])
        answer = getattr(t, "answer", "") or ""
        reveal_rule = getattr(t, "reveal_rule", "") or ""
        purpose = getattr(t, "purpose", "") or ""
        plan_bits = []
        if purpose:
            plan_bits.append(f"scopo: {purpose}")
        if answer:
            plan_bits.append(f"risposta_nascosta: {answer}")
        if clues:
            plan_bits.append(f"indizi_previsti: {clues}")
        if reveal_rule:
            plan_bits.append(f"regola_chiusura: {reveal_rule}")
        plan_suffix = " | " + " | ".join(plan_bits) if plan_bits else ""
        structured_lines.append(f"[{t.id} | {marker} | parent:{parents}] {t.question}{plan_suffix}")
    structured_block = (
        "THREAD_STRUTTURATI (id | indizi_raccolti/soglia | parent):\n  " + "\n  ".join(structured_lines) + "\n"
    ) if structured_lines else ""

    # Stato attuale degli NPC persistenti (posizione e ruolo nel mondo)
    npc_block = ""
    if world_npcs:
        npc_lines = []
        current_node_id = map_state.current_node_id
        for npc in world_npcs:
            if npc.status in {"dead"}:
                continue
            location_name = "?"
            if npc.status == "missing":
                location_name = "SCOMPARSO"
                here = ""
            else:
                ln = map_state.nodes.get(npc.current_node_id)
                location_name = ln.name if ln else "?"
                here = " [QUI]" if npc.current_node_id == current_node_id else ""
            clue_marker = f" [chiave di {npc.holds_clue_for}]" if npc.holds_clue_for else ""
            threat_marker = f" T{npc.threat_to_player}" if npc.threat_to_player > 0 else ""
            reaction_marker = f" [reazione: {npc.last_reaction_level}]" if getattr(npc, "last_reaction_level", "") else ""
            # Aggiungi stat GURPS se pre-generate
            gurps_stat_line = ""
            if getattr(npc, "gurps_fo", None) is not None:
                attrs = f"FO{npc.gurps_fo} DE{npc.gurps_de} IN{npc.gurps_in} SA{npc.gurps_sa}"
                if npc.combat_hp:
                    attrs += f" PF{npc.combat_hp}"
                if npc.combat_dr:
                    attrs += f" DR{npc.combat_dr}"
                skills_str = ""
                if npc.gurps_skills:
                    top_skills = sorted(npc.gurps_skills.items(), key=lambda x: -x[1])[:4]
                    skills_str = " | skill: " + ", ".join(f"{sk}={lv}" for sk, lv in top_skills)
                adv_str = ""
                if npc.gurps_advantages:
                    adv_str = " | vantaggi: " + ", ".join(npc.gurps_advantages)
                dis_str = ""
                if npc.gurps_disadvantages:
                    dis_str = " | svantaggi: " + ", ".join(npc.gurps_disadvantages)
                gurps_stat_line = f" [GURPS: {attrs}{skills_str}{adv_str}{dis_str}]"
            npc_lines.append(f"  - {npc.name} ({npc.role}{threat_marker}){clue_marker}{reaction_marker}{gurps_stat_line} — a {location_name}{here}: {npc.description}")
        if npc_lines:
            npc_block = "NPC_PERSISTENTI (chi è dove ora — usa solo questi nomi, non inventarne di nuovi):\n" + "\n".join(npc_lines) + "\n"

    canon_cards_block = ""
    key_entities = getattr(story, "key_entities", []) or []
    key_items = getattr(story, "key_items", []) or []
    card_lines = []
    for entity in key_entities[:4]:
        if not isinstance(entity, dict):
            continue
        clues = "; ".join(entity.get("clues", []) if isinstance(entity.get("clues", []), list) else [])
        card_lines.append(
            f"- ENTITA {entity.get('name', '')}: ruolo={entity.get('role', '')}; dove={entity.get('location', '')}; "
            f"vuole/fa={entity.get('drive', '')}; segreto={entity.get('secret', '')}; indizi={clues}; "
            f"rivelazione={entity.get('reveal_rule', '')}; effetto={entity.get('effect', '')}"
        )
    for item in key_items[:4]:
        if not isinstance(item, dict):
            continue
        clues = "; ".join(item.get("clues", []) if isinstance(item.get("clues", []), list) else [])
        card_lines.append(
            f"- OGGETTO {item.get('name', '')}: dove={item.get('location', '')}; uso={item.get('use', '')}; "
            f"requisito={item.get('requirement', '')}; indizi={clues}; rivelazione={item.get('reveal_rule', '')}; effetto={item.get('effect', '')}"
        )
    if card_lines:
        canon_cards_block = "SCHEDE_CANONICHE (usa/rivela solo questi elementi chiave, non inventarne di nuovi):\n" + "\n".join(card_lines) + "\n"

    return (
        f"MISSIONE:{mission.title}. OBIETTIVO:{mission.objective}. FASE:{phase.phase_name}. "
        f"{genre_block}"
        f"{encounter_block}"
        f"{movement_context}"
        f"TAG ZONA:{', '.join(node.tags)}. CONNESSIONI:{', '.join(connected)}. "
        f"MODALITA_NARRATIVA:{getattr(story, 'narrative_mode', 'emergent_mission')}. "
        f"{blacklist_block}"
        f"PREMESSA:{story.premise}. VERITA_CANONICA:{story.hidden_truth}. "
        f"INDIZI_VERITA:{' | '.join(getattr(story, 'hidden_truth_clues', []) or [])}. "
        f"REGOLA_VERITA:{getattr(story, 'hidden_truth_reveal_rule', '')}. "
        f"CONDIZIONE_VITTORIA:{story.win_condition}. "
        f"ENTITA_CANONICHE:{' | '.join(story.named_entities) if story.named_entities else 'nessuna'}. "
        f"{npc_block}"
        f"{canon_cards_block}"
        f"{structured_block}"
        f"THREAD:{' | '.join(story.active_threads)}. "
        f"FATTI:{' | '.join(story.discovered_facts[-6:]) if story.discovered_facts else 'nessuno'}. "
        f"DISTRUTTI:{' | '.join(story.destroyed_elements[-6:]) if story.destroyed_elements else 'nessuno'}. "
        f"RIMOSSI:{' | '.join(story.removed_clues[-6:]) if story.removed_clues else 'nessuno'}. "
        f"STATI:{current_statuses}. FERITE:{current_wounds}. "
        f"AZIONI PRECEDENTI:{recent_actions}. "
        f"TIPI DI EFFETTO USATI:{effect_summary if effect_summary else 'nessuno'}. "
        f"STORY_HINTS (esiti narrativi del tiro — usali per determinare cosa si risolve):{' | '.join(story_hints) if story_hints else 'nessuno'}. "
        f"ESITO:{scene_result}. TRANSIZIONE:{scene_transition}. "
        f"{challenge_block}"
        f"MEMORIA:{recent_memory}."
    )


# ── Narrative ─────────────────────────────────────────────────────────────────

def build_narrative(scene: str, technical_log: str) -> str:
    """Genera testo narrativo a partire dal log tecnico + scena precedente.
    Ritorna narrative + separatore + log tecnico originale."""
    try:
        prompt = (
            "Sei il narratore di un gioco da tavolo cooperativo in italiano, stile ISS Vanguard / Tainted Grail.\n"
            "Trasforma questo log tecnico in una descrizione narrativa coinvolgente (2-3 frasi, tono immediato, in medias res).\n"
            "Descrivi cosa è successo includendo almeno una battuta di dialogo diretto tra i personaggi (usa le virgolette caporali «»).\n"
            "Non citare i numeri dei dadi.\n\n"
            f"SCENA PRECEDENTE:\n{scene}\n\n"
            f"LOG TECNICO:\n{technical_log}\n\n"
            "Rispondi SOLO con le frasi narrative, senza prefissi o titoli."
        )
        narrative = _call_text_model(prompt, max_tokens=400)
        return f"{narrative.strip()}\n\n---\n{technical_log}"
    except Exception as e:
        print(f"[build_narrative] fallback: {e}")
        return technical_log


def generate_mission_ending(
    mission_title: str,
    mission_objective: str,
    success: bool,
    summary: str,
    story_context: dict | None = None,
) -> str:
    if not _text_provider_available():
        return f"Missione {'completata' if success else 'fallita'}: {mission_title}. {summary}"
    try:
        ctx = story_context or {}
        resolved = ctx.get("resolved_threads", [])
        facts = ctx.get("discovered_facts", [])
        entities = ctx.get("named_entities", [])
        resolved_txt = "\n".join(f"- {t}" for t in resolved[-6:]) or "Nessuno"
        facts_txt = "\n".join(f"- {f}" for f in facts[-5:]) or "Nessuno"
        entities_txt = ", ".join(entities) if entities else "nessuna entità nominata"
        outcome = "completata con successo" if success else "fallita"
        tone = "epico e soddisfacente, con senso di conclusione" if success else "cupo e tragico, con perdita tangibile"
        prompt = (
            f"Sei il narratore di un gioco da tavolo cooperativo in italiano.\n"
            f"La missione «{mission_title}» è stata {outcome}.\n\n"
            f"OBIETTIVO: {mission_objective}\n"
            f"CAUSA MECCANICA DELL'ESITO: {summary}\n"
            f"ENTITÀ CHIAVE: {entities_txt}\n\n"
            f"THREAD RISOLTI (gli ultimi):\n{resolved_txt}\n\n"
            f"FATTI SCOPERTI (gli ultimi):\n{facts_txt}\n\n"
            f"Scrivi il TESTO DI CHIUSURA della missione: 4-5 frasi che:\n"
            f"1. Descrivono cosa è accaduto nell'atto finale partendo dalla CAUSA MECCANICA, senza inventare una causa diversa\n"
            f"2. Nominano almeno un'entità chiave e spiegano cosa le è successo\n"
            f"3. Danno senso di conclusione definitiva ({tone})\n"
            f"4. Terminano con una riga di dialogo in «» o un'immagine finale potente\n"
            f"5. Se un PNG o alleato chiave non è indicato come morto nella CAUSA MECCANICA, non ucciderlo improvvisamente: può essere disperso, catturato, separato o costretto alla ritirata.\n"
            f"Scrivi SOLO il testo narrativo, nessun titolo o commento."
        )
        return _call_text_model(prompt, max_tokens=450).strip()
    except Exception as e:
        print(f"[generate_mission_ending] fallback: {e}")
        outcome = "completata" if success else "fallita"
        return f"Missione {outcome}: {mission_title}. {summary}"


def generate_movement_transition_narrative(
    mission_title: str,
    mission_objective: str,
    scene_transition: str,
    current_node_name: str,
    movement_options: list[tuple[str, str]],
    recent_actions: str,
    story_hints: list[str],
    premise: str = "",
) -> str:
    """Generates a rich narrative for the moment the squad must choose their next path."""
    outcome_it = {
        "success": "L'obiettivo locale è stato completato",
        "timeout": "Il tempo è scaduto — la squadra deve ripiegare",
        "crisis": "La minaccia è fuori controllo — la squadra è costretta a muoversi",
    }.get(scene_transition, "La situazione si è evoluta")

    options_text = "\n".join(f"- {name}: {desc}" for name, desc in movement_options)

    prompt = (
        "Sei il narratore di un gioco da tavolo cooperativo in italiano (ISS Vanguard / Tainted Grail).\n\n"
        f"MISSIONE: {mission_title}\n"
        f"OBIETTIVO MISSIONE: {mission_objective}\n"
        f"ZONA ATTUALE: {current_node_name}\n"
        f"PREMESSA: {premise}\n"
        f"ESITO: {outcome_it}\n"
        f"AZIONI COMPIUTE: {recent_actions}\n"
        f"ESITI NARRATIVI (da integrare): {' | '.join(story_hints) if story_hints else 'nessuno'}\n\n"
        f"PERCORSI CHE SI APRONO:\n{options_text}\n\n"
        "Scrivi un testo narrativo di 3-4 frasi che:\n"
        "1. Descriva concretamente come si conclude la fase nel nodo attuale (cosa è successo, "
        "cosa è stato scoperto o risolto — usa gli ESITI NARRATIVI come guida)\n"
        "2. Spieghi narrativamente perché si aprono nuovi percorsi (una porta sbloccata, "
        "informazioni ottenute, un alleato che indica la via, ecc.)\n"
        "3. Per ciascun percorso disponibile, accenni brevemente al tono o alla sfida specifica "
        "che comporta (non elencare — integra nel flusso)\n"
        "4. Includa un dialogo diretto in «» che esprima la tensione della scelta\n"
        "Tono: immediato, in medias res, senza titoli o prefissi.\n\n"
        "Rispondi SOLO con il testo narrativo."
    )

    try:
        return _call_text_model(prompt, max_tokens=500).strip()
    except Exception as e:
        print(f"[generate_movement_transition_narrative] fallback: {e}")
        fallback_label = {
            "success": "Obiettivo completato",
            "timeout": "Tempo scaduto",
            "crisis": "Crisi — minaccia fuori controllo",
        }.get(scene_transition, "Scena conclusa")
        node_names = ", ".join(n for n, _ in movement_options)
        return f"{fallback_label}. La squadra valuta i percorsi disponibili: {node_names}."


# ── Generazione scena ─────────────────────────────────────────────────────────

def _fallback_node_scene(seed: str) -> str:
    node_name = "nodo"
    if "NODO:" in seed:
        try:
            node_name = seed.split("NODO:")[1].split(".")[0]
        except Exception:
            pass
    return f"{node_name}. Una minaccia concreta ostacola il gruppo e costringe a una scelta rischiosa. Per avanzare bisogna sfruttare il luogo prima che la pressione aumenti."


def _fallback_scene_package(seed: str, scale: dict) -> dict:
    return {
        "source": "fallback",
        "scene": {
            "scene_text": _fallback_node_scene(seed),
            "objective_target": scale["scene_target_min"],
            "time_limit": scale["time_min"],
            "starting_threat": scale["starting_threat_min"],
            "scene_tags": ["nodo", "pressione"],
        },
        "players": [],
        "story_updates": {
            "discovered_facts": [],
            "destroyed_elements": [],
            "removed_clues": [],
            "resolved_threads": [],
        },
    }


def generate_scene_package(scene_seed: str, active_slots: int, action_results_summary: str = "") -> dict:
    scale = mission_scaling(active_slots)
    try:
        action_block = (
            f"AZIONI DEI PERSONAGGI IN QUESTO TURNO:\n{action_results_summary}\n\n"
            if action_results_summary else ""
        )
        prompt = (
            "Sei il narratore di un gioco da tavolo cooperativo in italiano, stile ISS Vanguard / Tainted Grail.\n\n"
            f"CONTESTO (missione, nodo, storia, memoria):\n{scene_seed}\n\n"
            f"{action_block}"
            "MAPPATURA STORY_HINTS → EFFETTI VISIBILI (usa questi per costruire la narrativa):\n"
            "  scoperta_cruciale/verita_rivelata/codice_decifrato → qualcosa di concreto viene rivelato: oggetto, verità, identità\n"
            "  fatto_scoperto/posizione_rilevata → vantaggio informativo, la squadra capisce qualcosa di nuovo\n"
            "  indizio_parziale/vicolo_cieco/rilevato_ma_esposto → percorso incerto o copertura compromessa\n"
            "  varco_aperto*/avanzata_silenziosa/passaggio_invisibile → movimento fisico, nuovo accesso\n"
            "  tentativo_fallito_allarme/infiltrazione_scoperta → rumore, allarme, copertura saltata\n"
            "  nemico_abbattuto/respinto → minaccia ridotta o eliminata\n"
            "  scambio_ferite/sconfitta_con_ferita → ferite visibili, costo fisico\n"
            "  guarigione_completa/paziente_stabilizzato → personaggio in condizioni migliori\n"
            "  inganno_perfetto/accordo_vantaggioso → manipolazione riuscita, dinamiche cambiate\n"
            "  inganno_scoperto/negoziato_rotto → bugia smascherata, conseguenze immediate\n"
            "  evocazione_potente/riuscita → effetto straordinario visibile\n"
            "  evocazione_instabile/incontrollata → caos, qualcuno paga il prezzo\n\n"
            "ANCORAGGIO DI GENERE (priorità assoluta):\n"
            "- Il testo della scena deve riflettere GENERE, FAMIGLIA_TEMATICA e TONO indicati nel CONTESTO.\n"
            "- AMBIENTE_BASE e MINACCIA_BASE definiscono il sapore del mondo: dettagli sensoriali, lessico e minacce devono coerenti con essi (non scivolare in cliché generici di un altro genere).\n"
            "- Rispetta ELEMENTI_VIETATI e TROPI_VIETATI se presenti nel CONTESTO: non usarli, neanche in forma attenuata.\n"
            "- Il TWIST_DI_MISSIONE è già attivo nello sfondo: lascia che traspaia in dettagli, non riannunciarlo.\n\n"
            "REGOLE NARRATIVE:\n"
            "0. ESITI DEI DADI — REGOLA ASSOLUTA:\n"
            "   Nella sezione 'ESITI DEI TIRI' trovi l'esito reale del dado 3d6 GURPS per ogni personaggio.\n"
            "   Questi esiti sono IMMUTABILI. Non puoi trasformare un FALLIMENTO in successo né viceversa.\n"
            "   - FALLIMENTO / FALLIMENTO CRITICO: il personaggio non ottiene ciò che voleva. L'azione produce una conseguenza negativa concreta e visibile (allarme, ferita, informazione sbagliata, porta che non si apre, NPC che si chiude). Non usare 'quasi', 'per poco', 'nonostante tutto riesce a' per ammorbidire.\n"
            "   - SUCCESSO PARZIALE: il personaggio ottiene un risultato incompleto con un costo — cosa ottiene e cosa paga.\n"
            "   - SUCCESSO PIENO / CRITICO: il personaggio ottiene ciò che voleva, con effetto proporzionale al margine.\n"
            "   Se più personaggi hanno agito con hint 'coordinamento', descrivili come squadra che opera in sincronia.\n"
            "1. scene_text = TESTO UNIFICATO in due parti fluide:\n"
            "   PARTE 1 (2 frasi): descrivi le azioni dei personaggi e le loro conseguenze dirette,\n"
            "   guidato dagli ESITI DEI TIRI e dai STORY_HINTS. Usa i nomi dei personaggi.\n"
            "   PARTE 2 (1-2 frasi): la nuova situazione che si apre — dove si trovano, cosa li aspetta.\n"
            "   Include almeno un dialogo diretto in «». Tono immediato, in medias res.\n"
            "1a. VARIETÀ OBBLIGATORIA: ogni scena deve aprirsi su un luogo FISICAMENTE DIVERSO dalla precedente.\n"
            "   NON ripetere 'corridoio tecnico', 'paratia', 'pannello di controllo', 'luci d'emergenza' se erano già nella scena precedente.\n"
            "   La scena deve iniziare con un'azione in corso — non con una descrizione d'atmosfera.\n"
            "1b. scene_problem deve essere un ostacolo FISICO e SPECIFICO di questo luogo, non una condizione generica.\n"
            "   MAI: 'la squadra deve trovare un modo per...', 'la situazione è critica perché...'\n"
            "   SÌ: 'Il portello B-7 è saldato dall'interno e Kovač ha il saldatore', 'Il terminale richiede l'impronta di Chen'\n"
            "2. Sii coerente con FATTI SCOPERTI e MEMORIA — non contraddirli mai.\n"
            "2a. Non eliminare improvvisamente PNG/alleati/oggetti chiave legati alla condizione di vittoria, "
            "a meno che l'ESITO sia missione fallita o che la MEMORIA dica esplicitamente che sono stati distrutti o uccisi. "
            "Nei fallimenti intermedi usa: ferito, separato, bloccato, catturato, sentiero perso temporaneamente, rituale accelerato.\n"
            "2b. Rispetta MODALITA_NARRATIVA:\n"
            "   - fixed_mystery: la VERITA_CANONICA e l'OBIETTIVO sono fissi. Le azioni rivelano indizi, costi, accessi o conseguenze; NON inventare una nuova causa centrale, un nuovo colpevole, un nuovo artefatto risolutivo o una nuova missione principale.\n"
            "   - emergent_mission: le azioni possono creare complicazioni e opportunità, ma devono restare agganciate a OBIETTIVO, MINACCIA, TWIST e named_entities già presenti. Non rendere irrilevante l'obiettivo iniziale.\n"
            "2c. CANOVACCIO CHIUSO:\n"
            "   - Non introdurre nuovi PNG nominati, luoghi chiave, oggetti risolutivi, fazioni o thread non presenti nel CONTESTO.\n"
            "   - Se serve pressione narrativa, modifica elementi esistenti: un PNG si sposta, un oggetto cambia stato, una minaccia cresce o cala, un accesso si apre/chiude.\n"
            "   - Il twist puo attivarsi solo come rivelazione di VERITA_CANONICA, TWIST_DI_MISSIONE, THREAD_STRUTTURATI o named_entities gia presenti.\n"
            "3. GESTIONE THREAD (critica — priorità massima):\n"
            "   a) Se STORY_HINTS contiene 'verita_rivelata', 'scoperta_cruciale', 'codice_decifrato',\n"
            "      'fatto_scoperto', 'accordo_vantaggioso', 'inganno_perfetto': DEVI risolvere\n"
            "      il thread attivo più pertinente — scegli il più vecchio tra quelli pertinenti.\n"
            "   b) new_threads deve essere SEMPRE []. Mai creare thread a runtime.\n"
            "   c) Regola fondamentale: CHIUDI o precisa thread esistenti; non aprirne di nuovi.\n"
            "      Se nei FATTI del seed ci sono 5+ voci, DEVI chiudere almeno un thread.\n"
            "   d) Se emerge una nuova domanda, trasformala in un discovered_fact o in una conseguenza su un thread esistente.\n"
            "4. Usa ELEMENTI DISTRUTTI e INDIZI RIMOSSI per non contraddire la storia scritta.\n"
            "5. discovered_facts: MAX 1 fatto genuinamente nuovo per scena.\n"
            "   Se nei FATTI del seed ci sono già 6+ voci, lista VUOTA obbligatoria.\n"
            "   Regola: è sempre meglio chiudere un thread che aggiungere un fatto.\n\n"
            f"SCALA: objective_target {scale['scene_target_min']}-{scale['scene_target_max']}, "
            f"time_limit {scale['time_min']}-{scale['time_max']}, "
            f"starting_threat {scale['starting_threat_min']}-{scale['starting_threat_max']}\n\n"
            "REGOLE ACTION_CARDS — leggi prima di scrivere il JSON:\n"
            "- Genera ESATTAMENTE 3 oggetti nell'array action_cards, ognuno con title, prompt, effect_type, reward, risk\n"
            "- Le 3 card devono usare approcci FISICAMENTE DIVERSI tra loro (es: una fisica su un oggetto, una sociale con un personaggio, una che sfrutta l'ambiente)\n"
            "- Ogni card deve citare un elemento SPECIFICO della scena: nome proprio, oggetto preciso, stanza o punto geografico\n"
            "- title: 3-5 parole, azione concreta, MAI 'Agire', 'Leggere i segnali', 'Creare diversivo', 'Aprire varco' senza specificare COSA\n"
            "- prompt: verbo + oggetto concreto della scena. Deve descrivere cosa fa fisicamente il personaggio\n"
            "- reward: cambiamento fisico e immediato nello stato della scena. Es: 'il portello B-7 si apre', 'Shen rivela il codice di accesso', 'il reattore guadagna 8 minuti'. MAI 'ottieni vantaggio', 'crei margine', 'guadagni collaborazione'\n"
            "- risk: conseguenza osservabile e immediata. Es: 'scatta l'allarme nel corridoio C', 'Vess si chiude e non parla più', 'il generatore si spegne definitivamente'. MAI 'si complica', 'aumenti la confusione', 'perdi terreno'\n"
            "- Le 3 card devono avere reward E risk tutti diversi tra loro — non varianti dello stesso effetto\n"
            "- effect_type DEVE corrispondere al verbo usato in prompt/title secondo questa tabella:\n"
            "    estrarre/recuperare/prelevare/rubare/raccogliere/portare via → 'recuperare'\n"
            "    decifrare/decodificare/hackerare/scansionare/violare/bypassare → 'decifrare'\n"
            "    investigare/indagare/esaminare/studiare/analizzare/ispezionare/interrogare → 'investigare'\n"
            "    osservare/rilevare/percepire/intuire/scrutare/ascoltare/monitorare → 'rilevare'\n"
            "    persuadere/negoziare/convincere/parlare con/mediare/intimidire → 'negoziare'\n"
            "    ingannare/mentire/bluffare/distrarre/fingere/travestirsi → 'ingannare'\n"
            "    attaccare/sparare/colpire/aggredire/eliminare/neutralizzare → 'combattere'\n"
            "    forzare/sfondare/scassinare/rompere/demolire/sabotare/riparare → 'forzare'\n"
            "    infiltrarsi/sgattaiolare/eludere/schivare/nascondersi → 'infiltrarsi'\n"
            "    difendere/proteggere/coprire/resistere/barricare → 'difendere'\n"
            "    stabilizzare/curare/medicare/soccorrere/guarire/calmare → 'stabilizzare'\n"
            "    evocare/invocare/rituale/incantesimo → 'evocare'\n"
            "  IMPORTANTE: se il verbo nel prompt è 'estrarre i log' allora effect_type='recuperare', NON 'negoziare'.\n"
            "  Se il verbo è 'persuadere il magistrato' allora effect_type='negoziare', NON 'investigare'.\n\n"
            "scene_tags validi: combattimento, stealth, indagine, fuga, crisi, negoziazione, esplorazione, difesa, sabotaggio, recupero, medico, coordinamento, possessione, rituale.\n\n"
            "Rispondi SOLO con questo JSON (nessun testo prima o dopo):\n"
            "{\n"
            '  "scene_text": "TESTO UNIFICATO (3-4 frasi): azioni+conseguenze poi nuova situazione, dialogo in «»",\n'
            '  "scene_problem": "1 frase: ostacolo fisico specifico che blocca la squadra ORA — nomina un oggetto, personaggio o condizione concreta di questa scena.",\n'
            '  "scene_resolution": "1 frase: azione concreta su quale elemento produce quale cambiamento visibile per superare questo ostacolo.",\n'
            '  "action_cards": [\n'
            '    {"title": "Titolo 3-5 parole", "prompt": "verbo + oggetto concreto", "effect_type": "<scegli dalla tabella in base al verbo>", "reward": "effetto fisico immediato specifico", "risk": "conseguenza osservabile immediata specifica"},\n'
            '    {"title": "Titolo 3-5 parole", "prompt": "verbo + oggetto concreto", "effect_type": "<scegli dalla tabella in base al verbo>", "reward": "effetto fisico immediato specifico", "risk": "conseguenza osservabile immediata specifica"},\n'
            '    {"title": "Titolo 3-5 parole", "prompt": "verbo + oggetto concreto", "effect_type": "<scegli dalla tabella in base al verbo>", "reward": "effetto fisico immediato specifico", "risk": "conseguenza osservabile immediata specifica"}\n'
            '  ],\n'
            '  "scene_tags": ["tag1", "tag2"],\n'
            '  "objective_target": N,\n'
            '  "time_limit": N,\n'
            '  "starting_threat": N,\n'
            '  "story_updates": {\n'
            '    "discovered_facts": [{"text": "fatto concreto e specifico", "clue_for_thread": "T1"}],\n'
            '    "destroyed_elements": [],\n'
            '    "removed_clues": [],\n'
            '    "resolved_threads": [],\n'
            '    "new_threads": []\n'
            "  }\n"
            "}\n"
            "FORMATO discovered_facts (importante):\n"
            "- ogni fatto è un oggetto {\"text\": \"...\", \"clue_for_thread\": \"<id thread>\"}.\n"
            "- clue_for_thread DEVE coincidere con un id presente in THREAD_STRUTTURATI del CONTESTO. Se nessun thread strutturato è pertinente, usa stringa vuota \"\".\n"
            "- Un fatto deve essere taggato a un thread SOLO se è un indizio diretto e operativo per rispondere alla domanda di quel thread. Niente tag opportunistici.\n"
            "- Quando un THREAD_STRUTTURATO include indizi_previsti, scegli discovered_facts da quegli indizi o da varianti molto vicine. Non inventare una pista parallela.\n"
            "- Non rivelare risposta_nascosta in modo esplicito finche il thread non e READY o finche resolved_threads non lo chiude.\n"
            "- Se un thread è marcato READY (soglia di indizi raggiunta), DEVI metterlo in resolved_threads in QUESTA scena, narrando esplicitamente la deduzione che lo chiude — usando i fatti già accumulati per quel thread.\n"
            "- new_threads deve restare sempre []. Qualunque valore diverso da [] verra ignorato dal motore.\n"
            "Sostituisci i valori di esempio con contenuto reale della scena. Per ogni card scegli effect_type dalla tabella verbo→effect_type sopra, basandoti SUL VERBO che hai usato nel prompt — non scegliere a caso."
        )
        raw = _call_text_model(prompt, max_tokens=1400)
        data = _extract_json_object(raw)

        # Valida e normalizza le action card generate da Claude
        raw_cards = data.get("action_cards", [])
        scene_actions: list[dict[str, str]] = []
        valid_effects = {"investigare", "rilevare", "decifrare", "forzare", "combattere",
                         "infiltrarsi", "recuperare", "negoziare", "difendere", "stabilizzare", "ingannare", "evocare"}
        for card in raw_cards[:3]:
            if not isinstance(card, dict):
                continue
            title = str(card.get("title", "") or "").strip()
            prompt_text = str(card.get("prompt", "") or "").strip()
            declared_effect = str(card.get("effect_type", "") or "").strip().lower()
            reward = str(card.get("reward", "") or "").strip()
            risk = str(card.get("risk", "") or "").strip()
            # Riconciliazione: il verbo nel prompt/title vince sull'effect_type dichiarato.
            # Esempio: prompt="Estrarre i log" + effect_type="negoziare" → "recuperare".
            effect = reconcile_effect_type(f"{title} {prompt_text}", declared_effect, valid_effects)
            if effect != declared_effect and declared_effect:
                print(f"[reconcile_action_card] '{title}' effect_type {declared_effect!r} → {effect!r} (driven by verb in prompt)")
            if title and prompt_text and effect in valid_effects:
                scene_actions.append({
                    "title": title,
                    "prompt": prompt_text,
                    "effect_type": effect,
                    "reward": reward or "ottieni un vantaggio nella scena",
                    "risk": risk or "la situazione si complica",
                    "tone": "core",
                })

        return {
            "source": _active_source_label(),
            "scene": {
                "scene_text": data.get("scene_text", _fallback_node_scene(scene_seed)),
                "scene_problem": str(data.get("scene_problem", "") or "").strip(),
                "scene_resolution": str(data.get("scene_resolution", "") or "").strip(),
                "objective_target": int(data.get("objective_target", scale["scene_target_min"])),
                "time_limit": int(data.get("time_limit", scale["time_min"])),
                "starting_threat": int(data.get("starting_threat", scale["starting_threat_min"])),
                "scene_tags": data.get("scene_tags", ["nodo"]),
                "scene_actions": scene_actions,
            },
            "players": [],
            "story_updates": data.get("story_updates", {
                "discovered_facts": [],
                "destroyed_elements": [],
                "removed_clues": [],
                "resolved_threads": [],
            }),
        }
    except Exception as e:
        print(f"[generate_scene_package] fallback: {e}")
        return _fallback_scene_package(scene_seed, scale)


# ── Generazione azioni contestuali ───────────────────────────────────────────

def _fallback_actions_for_player(player: dict, scene_context: str, scene_tags: list[str]) -> list[dict]:
    """Sistema a regole come safety net quando Claude non è disponibile.
    Ora legge i scene_tags per adattare le azioni alla situazione."""
    actions = []
    role = player["role"].lower()
    archetype = player.get("archetype", "").lower()
    items = [i.lower() for i in player.get("items", [])]
    lowered = scene_context.lower()
    tags_lower = [t.lower() for t in scene_tags]

    # Top skills del personaggio (per adattare i fallback al suo profilo reale)
    player_skills: dict[str, int] = player.get("skills", {})
    top_skills = sorted(player_skills.items(), key=lambda x: -x[1])

    def _best_skill_in(candidates: list[str]) -> str | None:
        """Restituisce la skill con livello più alto tra quelle candidate possedute dal personaggio."""
        owned = [(s, player_skills[s]) for s in candidates if s in player_skills]
        return max(owned, key=lambda x: x[1])[0] if owned else None

    # Situazione da tag
    is_combat = any(t in tags_lower for t in ["combattimento", "attacco", "scontro", "difesa"])
    is_stealth = any(t in tags_lower for t in ["stealth", "infiltrazione", "silenzio"])
    is_investigation = any(t in tags_lower for t in ["indagine", "esplorazione", "analisi", "recupero"])
    is_flight = any(t in tags_lower for t in ["fuga", "ritirata", "evacuazione"])
    is_crisis = any(t in tags_lower for t in ["crisi", "medico", "emergenza"])

    # Azioni di combattimento (adattate alle skill del personaggio)
    if is_combat:
        combat_skill = _best_skill_in(["mira", "combattere", "lottare"]) or "combattere"
        combat_stat = "agilita" if combat_skill == "mira" else "forza"
        combat_name = "Aprire il fuoco" if combat_skill == "mira" else "Attaccare in mischia"
        actions.append({"name": combat_name, "stat": combat_stat, "skill": combat_skill, "difficulty": 1, "effect_type": "combattere", "requires_item": None, "source": "situation"})
        actions.append({"name": "Coprire gli alleati", "stat": "forza", "skill": "proteggere", "difficulty": 1, "effect_type": "difendere", "requires_item": None, "source": "situation"})
        actions.append({"name": "Ritirarsi in posizione", "stat": "agilita", "skill": "rapidita", "difficulty": 1, "effect_type": "infiltrarsi", "requires_item": None, "source": "situation"})

    if is_stealth:
        stealth_skill = _best_skill_in(["furtivita", "infiltrarsi", "pedinare"]) or "furtivita"
        actions.append({"name": "Avanzare nell'ombra", "stat": "agilita", "skill": stealth_skill, "difficulty": 2, "effect_type": "infiltrarsi", "requires_item": None, "source": "situation"})
        actions.append({"name": "Neutralizzare silenziosamente", "stat": "agilita", "skill": "combattere", "difficulty": 2, "effect_type": "combattere", "requires_item": None, "source": "situation"})

    if is_investigation:
        inv_skill = _best_skill_in(["investigare", "analizzare", "osservare", "medicina", "scienze"]) or "investigare"
        actions.append({"name": "Cercare indizi", "stat": "intelligenza", "skill": inv_skill, "difficulty": 1, "effect_type": "investigare", "requires_item": None, "source": "situation"})
        actions.append({"name": "Analizzare l'ambiente", "stat": "intelligenza", "skill": "analizzare", "difficulty": 1, "effect_type": "rilevare", "requires_item": None, "source": "situation"})

    if is_flight:
        actions.append({"name": "Aprire la via di fuga", "stat": "forza", "skill": "forzare", "difficulty": 2, "effect_type": "forzare", "requires_item": None, "source": "situation"})
        actions.append({"name": "Scagliarsi verso l'uscita", "stat": "agilita", "skill": "rapidita", "difficulty": 1, "effect_type": "infiltrarsi", "requires_item": None, "source": "situation"})

    # Azioni specifiche del ruolo, preferendo le skill più alte del personaggio
    if any(x in archetype for x in ["marine", "warrior", "rifleman", "hunter", "solo", "operative", "partisan", "sniper"]):
        role_skill = _best_skill_in(["mira", "combattere", "lottare", "intimidire"]) or "combattere"
        role_stat = "agilita" if role_skill == "mira" else "forza"
        actions.append({"name": "Forzare il passaggio", "stat": role_stat, "skill": role_skill, "difficulty": 1, "effect_type": "combattere", "requires_item": None, "source": "role"})
    if any(x in archetype for x in ["scientist", "technician", "detective", "scholar", "inspector", "amateur", "hacker"]):
        role_skill = _best_skill_in(["investigare", "analizzare", "tecnologia", "scienze", "medicina"]) or "investigare"
        actions.append({"name": "Valutare la situazione", "stat": "intelligenza", "skill": role_skill, "difficulty": 1, "effect_type": "investigare", "requires_item": None, "source": "role"})
    if any(x in archetype for x in ["medic", "paramedic", "cleric", "field_medic"]):
        role_skill = _best_skill_in(["curare", "medicina", "stabilizzare"]) or "curare"
        actions.append({"name": "Prestare soccorso", "stat": "empatia", "skill": role_skill, "difficulty": 1, "effect_type": "stabilizzare", "requires_item": None, "source": "role"})
    if any(x in archetype for x in ["scout", "rogue", "agent", "driver"]):
        role_skill = _best_skill_in(["furtivita", "rapidita", "pedinare", "guidare"]) or "furtivita"
        actions.append({"name": "Riposizionarsi", "stat": "agilita", "skill": role_skill, "difficulty": 1, "effect_type": "infiltrarsi", "requires_item": None, "source": "role"})
    if any(x in archetype for x in ["diplomat", "journalist", "confidant", "protagonist", "romantic", "artist", "rival"]):
        role_skill = _best_skill_in(["persuadere", "intuire", "calmare", "comunicare", "intrattenere"]) or "persuadere"
        actions.append({"name": "Avvicinare e ascoltare", "stat": "empatia", "skill": role_skill, "difficulty": 1, "effect_type": "negoziare", "requires_item": None, "source": "role"})

    # Azioni da oggetti — uso effect_type moderni (non i legacy "scan"/"stabilize"/"breach")
    if "scanner" in items:
        actions.append({"name": "Scannerizzare l'area", "stat": "intelligenza", "difficulty": 0, "effect_type": "decifrare", "requires_item": "scanner", "source": "item"})
    if any(x in items for x in ["medkit", "kit medico", "medikit"]):
        req = next(x for x in items if x in ["medkit", "kit medico", "medikit"])
        actions.append({"name": "Stabilizzare un alleato", "stat": "empatia", "difficulty": 1, "effect_type": "stabilizzare", "requires_item": req, "source": "item"})
    if any(x in items for x in ["granata", "esplosivo"]):
        req = next(x for x in items if x in ["granata", "esplosivo"])
        actions.append({"name": "Lanciare una granata", "stat": "forza", "difficulty": 2, "effect_type": "forzare", "requires_item": req, "source": "item"})
    if any(x in items for x in ["kit di accesso", "grimaldelli", "strumenti"]):
        req = next(x for x in items if x in ["kit di accesso", "grimaldelli", "strumenti"])
        actions.append({"name": "Aprire l'accesso", "stat": "intelligenza", "difficulty": 2, "effect_type": "forzare", "requires_item": req, "source": "item"})

    status = player.get("status", "ok")
    if status == "fuori_combattimento":
        return []
    elif status == "ferito_grave":
        action_cap = 1
    elif status == "ferito":
        action_cap = 2
    else:
        action_cap = 3

    # Deduplica
    seen: set[str] = set()
    final = []
    for a in actions:
        if a["name"] not in seen:
            a["skill"] = a.get("skill") or default_skill_for(a.get("stat", "intelligenza"), a.get("effect_type", "generic"))
            a["effect_type"] = SKILL_TO_EFFECT_TYPE.get(a["skill"], a.get("effect_type", "generic"))
            seen.add(a["name"])
            final.append(a)

    # Fallback minimo se non c'è nulla
    if not final:
        final = [
            {"name": "Valutare la situazione", "stat": "intelligenza", "skill": "osservare", "difficulty": 1, "effect_type": "rilevare", "requires_item": None, "source": "fallback"},
            {"name": "Agire con prudenza", "stat": "agilita", "skill": "schivare", "difficulty": 1, "effect_type": "infiltrarsi", "requires_item": None, "source": "fallback"},
        ]

    # Assegna action_role in base a parole chiave nel nome (il fallback non le ha esplicite)
    _SUPPORT_KEYWORDS = ("coprire", "stabiliz", "soccorso", "ritirar", "alleat", "protegg", "ascoltare", "mediare")
    _RISK_KEYWORDS    = ("silenziosamente", "granata", "furtiv", "disperata", "rischio", "ombra")
    capped = final[:action_cap]
    for a in capped:
        if "action_role" not in a:
            name_lower = a["name"].lower()
            if any(k in name_lower for k in _SUPPORT_KEYWORDS):
                a["action_role"] = "support"
            elif any(k in name_lower for k in _RISK_KEYWORDS):
                a["action_role"] = "risk"
            else:
                a["action_role"] = "core"
    return capped


def _generate_actions_with_claude(players: list[dict], scene_context: str, scene_tags: list[str], genre: str = "") -> list[dict]:
    """Usa Claude per generare azioni narrative e contestuali per ogni personaggio."""
    players_desc = []
    for p in players:
        stats_str = ", ".join(f"{stat_display(k)}:{v}" for k, v in p.get("stats", {}).items())
        items_str = ", ".join(p.get("items", [])) or "nessuno"
        status = p.get("status", "ok")
        if status == "fuori_combattimento":
            stato_desc = "FUORI COMBATTIMENTO — non può agire (0 azioni)"
        elif status == "ferito_grave":
            stato_desc = "FERITO GRAVE — solo sopravvivenza (max 1 azione semplice)"
        elif status == "ferito":
            stato_desc = "FERITO — capacità ridotte (max 2 azioni)"
        else:
            stato_desc = "OK — piena capacità operativa (max 3 azioni)"
        top_skills = sorted(p.get("skills", {}).items(), key=lambda x: -x[1])[:6]
        skills_str = ", ".join(f"{skill_display(k)}:{v}" for k, v in top_skills) or "nessuna"
        players_desc.append(
            f"- ID:{p['id']} | {p['name']} | Ruolo:{p['role']} | Archetipo:{p.get('archetype','')} | "
            f"Stats:[{stats_str}] | Skills:[{skills_str}] | Oggetti:[{items_str}] | Stato:{stato_desc}"
        )

    genre_hint = _GENRE_ACTION_VOCABULARY.get(genre, "")
    genre_block = f"VOCABOLARIO DI GENERE ({genre}):\n{genre_hint}\n\n" if genre_hint else ""
    skills_block = skill_prompt_text()

    prompt = (
        "Sei il motore di azioni di un gioco da tavolo cooperativo in italiano, stile ISS Vanguard / Tainted Grail.\n\n"
        f"SITUAZIONE ATTUALE:\n{scene_context}\n\n"
        f"TAG SCENA: {', '.join(scene_tags) if scene_tags else 'generica'}\n\n"
        f"{genre_block}"
        f"PERSONAGGI:\n" + "\n".join(players_desc) + "\n\n"
        "REGOLA FONDAMENTALE: ogni personaggio deve avere azioni DIVERSE dagli altri, basate sul suo ruolo specifico.\n"
        "NON dare la stessa azione a più personaggi. Se due personaggi 'cercano indizi', lo fanno in modi completamente diversi.\n"
        "RISPETTA LO STATO del personaggio: un ferito grave ha solo 2 azioni di sopravvivenza, un fuori combattimento ha 0 azioni.\n\n"
        "Per ogni personaggio OPERATIVO, ragiona così:\n"
        "1. Qual è il contributo UNICO di questo ruolo in questa scena?\n"
        "2. Cosa può fare che NESSUN ALTRO può fare, grazie al suo ruolo o ai suoi oggetti?\n"
        "3. Lo stato fisico limita le opzioni? Un ferito non può fare azioni forza diff 2+\n\n"
        "ESEMPI di differenziazione in una scena di indagine:\n"
        "- Detective → 'Ricostruire la sequenza degli eventi' (IN/intelligenza, Investigare)\n"
        "- Medico → 'Esaminare i segni biologici sulla vittima' (IN/intelligenza, Medicina)\n"
        "- Guardia del corpo → 'Controllare le vie d'accesso' (FO/forza, Proteggere)\n"
        "- Medium → 'Aprirsi alle impressioni psichiche del luogo' (SA/empatia, Psicologia)\n\n"
        "ESEMPI in una scena di combattimento:\n"
        "- Soldato → 'Sopprimere il nemico con fuoco di copertura' (DE/agilita, Armi a Gittata)\n"
        "- Medico → 'Trascinare un alleato ferito fuori dalla linea di fuoco' (FO/forza, Trasportare)\n"
        "- Hacker → 'Disabilitare i sistemi di difesa nemici da remoto' (IN/intelligenza, Tecnologia)\n"
        "- Scout → 'Flancare i nemici sfruttando l'ombra' (DE/agilita, Furtività)\n\n"
        "REGOLE tecniche:\n"
        "- Nome: evocativo e specifico per scena E ruolo (max 50 caratteri). Può includere una battuta breve in caporali, es. «Tieniti forte!» — Ancorare gli alleati\n"
        "- 'stat': usa la chiave interna — una tra: forza (FO), agilita (DE), intelligenza (IN), empatia (SA)\n"
        "- 'skill': scegli UNA skill coerente con la stat. Lista valida:\n"
        f"{skills_block}\n"
        "- 'difficulty': 0=banale, 1=normale, 2=difficile, 3=estremo\n"
        "- 'effect_type': categoria meccanica derivata dalla skill, scegli tra questi 12 tipi:\n"
        "  INFORMAZIONE: investigare, rilevare, decifrare\n"
        "  FISICO:       forzare, combattere, infiltrarsi\n"
        "  SUPPORTO:     difendere, stabilizzare, recuperare\n"
        "  SOCIALE:      negoziare, ingannare, evocare\n"
        "  Scegli il tipo che meglio descrive COSA produce l'azione nel mondo di gioco.\n"
        "- 'action_role': assegna UNO tra:\n"
        "  'core'    → azione principale che avanza la scena verso la risoluzione\n"
        "  'support' → aiuta senza risolvere: riduce minaccia, guadagna tempo, sostiene alleati\n"
        "             (usa per: stabilizzare, difendere, coprire, assistere, rallentare la pressione)\n"
        "  'risk'    → alto rischio/alta ricompensa: critico = progresso doppio, fallimento = minaccia extra + ferita\n"
        "             (usa per: infiltrarsi furtivamente, ingannare, evocare, azioni disperate)\n"
        "  Ogni squadra dovrebbe avere un mix: almeno 1 core, 0-1 support, 0-1 risk.\n"
        "  Se c'è solo 1 giocatore, usa sempre 'core'.\n"
        "- 'requires_item': null oppure nome esatto oggetto posseduto dal personaggio\n"
        "- Numero azioni: genera SOLO le azioni che hanno senso in questa scena specifica\n"
        "  MAX 3 se ok, MAX 2 se ferito, MAX 1 se ferito grave, 0 se fuori combattimento\n"
        "  MIN 1 se il personaggio è operativo. Se la scena ha solo 2 scelte sensate, genera 2 azioni.\n"
        "  Ogni personaggio OK dovrebbe avere idealmente 1 CORE + 1 SUP + 1 RISK, ma adattati alla scena.\n"
        "- Mai più di 1 azione con lo stesso nome tra personaggi diversi\n\n"
        "- 'description': una frase breve (max 12 parole) che spiega concretamente cosa fa il personaggio e perché\n\n"
        "Rispondi SOLO con questo JSON:\n"
        "{\n"
        '  "players": [\n'
        '    {"id": N, "actions": [\n'
        '      {"name": "...", "stat": "...", "skill": "...", "difficulty": N, "effect_type": "...", "action_role": "core|support|risk", "requires_item": null, "description": "..."}\n'
        "    ]}\n"
        "  ]\n"
        "}"
    )

    raw = _call_text_model(prompt, max_tokens=1800)
    data = _extract_json_object(raw)
    players_actions = {p["id"]: p["actions"] for p in data.get("players", [])}

    # Applica le azioni generate ai player dict originali
    result = []
    for p in players:
        q = dict(p)
        generated = players_actions.get(p["id"], [])
        if generated:
            status = p.get("status", "ok")
            if status == "fuori_combattimento":
                action_cap = 0
            elif status == "ferito_grave":
                action_cap = 1
            elif status == "ferito":
                action_cap = 2
            else:
                action_cap = 3
            # Valida e normalizza le azioni — priorità al verbo nel name/description
            valid_effects_set = set(SKILL_TO_EFFECT_TYPE.values())
            valid_stats = set(p.get("stats", {}).keys())
            cleaned = []
            for a in generated[:action_cap]:
                name = str(a.get("name", "Agire"))[:60]
                description = str(a.get("description", ""))[:120]
                stat = a.get("stat", "intelligenza")
                if valid_stats and stat not in valid_stats:
                    stat = list(valid_stats)[0]
                declared_effect = str(a.get("effect_type") or "").strip().lower()
                # Inferisci effect_type dal verbo (name + description). Se il verbo è chiaro, vince.
                effect_type = reconcile_effect_type(f"{name} {description}", declared_effect, valid_effects_set)
                if effect_type != declared_effect and declared_effect:
                    print(f"[reconcile_player_action] '{name}' effect_type {declared_effect!r} → {effect_type!r}")
                # Skill: se Claude l'ha fornita E è coerente con l'effect_type derivato, mantienila.
                # Altrimenti calcola una skill compatibile con stat + effect_type.
                declared_skill = str(a.get("skill") or "").strip()
                skill_ok = (
                    declared_skill in VALID_SKILLS
                    and declared_skill in SKILLS_BY_STAT.get(stat, [])
                    and SKILL_TO_EFFECT_TYPE.get(declared_skill) == effect_type
                )
                if skill_ok:
                    skill = declared_skill
                else:
                    # Lo stat corrente ha una skill compatibile con effect_type? Se no, scegli
                    # un altro stat che ce l'ha (preferendo gli stat che il personaggio ha davvero).
                    if not any(SKILL_TO_EFFECT_TYPE.get(s) == effect_type for s in SKILLS_BY_STAT.get(stat, [])):
                        for candidate_stat in (valid_stats or set()):
                            if any(SKILL_TO_EFFECT_TYPE.get(s) == effect_type for s in SKILLS_BY_STAT.get(candidate_stat, [])):
                                stat = candidate_stat
                                break
                    skill = default_skill_for(stat, effect_type)
                raw_role = a.get("action_role", "core")
                action_role = raw_role if raw_role in ("core", "support", "risk") else "core"
                cleaned.append({
                    "name": name,
                    "stat": stat,
                    "skill": skill,
                    "difficulty": max(0, min(3, int(a.get("difficulty", 1)))),
                    "effect_type": effect_type,
                    "action_role": action_role,
                    "requires_item": a.get("requires_item"),
                    "source": _active_source_label(),
                    "description": description,
                })
            q["actions"] = cleaned
        else:
            # Fallback per questo specifico personaggio
            q["actions"] = _fallback_actions_for_player(p, scene_context, scene_tags)
        result.append(q)

    return result


_GENRE_ACTION_VOCABULARY: dict[str, str] = {
    "detective_classico": (
        "Azioni adatte: interrogare un testimone, esaminare prove fisiche, confrontare dichiarazioni, "
        "cercare documenti nascosti, seguire un sospettato, dedurre connessioni, ascoltare di nascosto, "
        "convincere qualcuno a parlare, analizzare una scena del crimine, ricostruire una sequenza temporale. "
        "EVITA azioni di combattimento fisico diretto salvo casi estremi."
    ),
    "mystery_horror": (
        "Azioni adatte: investigare fenomeni inspiegabili, cercare tracce, esaminare simboli o testi, "
        "resistere a influenze psichiche, proteggere qualcuno, forzare un varco, fuggire da una minaccia, "
        "analizzare oggetti anomali, convincere un testimone spaventato. "
        "Le azioni fisiche hanno un costo emotivo o psicologico."
    ),
    "romance": (
        "Azioni adatte: avvicinarsi con delicatezza, confidarsi, osservare da lontano, ascoltare, "
        "intercedere per qualcuno, scrivere o inviare un messaggio, creare un'occasione di incontro, "
        "mediare una tensione, riconoscere un sentimento, fare una scelta coraggiosa. "
        "EVITA azioni di forza o combattimento."
    ),
    "ww2": (
        "Azioni adatte: coprire i compagni con fuoco di soppressione, avanzare sotto copertura, "
        "sabotare un obiettivo, comunicare via radio, prestare soccorso medico, tendere un'imboscata, "
        "raccogliere informazioni dal nemico, mantenere la posizione, sminare un percorso. "
        "Tono realistico: ogni azione ha un costo."
    ),
    "action": (
        "Azioni adatte: neutralizzare una guardia silenziosamente, hackerare un sistema, "
        "inseguire o seminare un bersaglio, disinnescare un dispositivo, negoziare sotto pressione, "
        "coprire la squadra, usare l'ambiente come vantaggio tattico, guidare in fuga. "
        "Ritmo rapido, conseguenze immediate."
    ),
}


def generate_actions_for_selected_team(
    players: list[dict],
    scene_context: str,
    scene_tags: list[str] | None = None,
    genre: str = "",
) -> list[dict]:
    """Genera azioni contestuali per ogni personaggio del team.
    Usa Claude se disponibile, altrimenti sistema a regole migliorato."""
    scene_tags = scene_tags or []

    if API_KEY:
        try:
            return _generate_actions_with_claude(players, scene_context, scene_tags, genre=genre)
        except Exception as e:
            print(f"[generate_actions] Claude fallback: {e}")

    # Fallback regole
    out = []
    for p in players:
        q = dict(p)
        q["actions"] = _fallback_actions_for_player(p, scene_context, scene_tags)
        out.append(q)
    return out


# ── Generazione immagine scena ────────────────────────────────────────────────

_GENRE_IMAGE_STYLE = {
    "sci_fi":           "science fiction, futuristic, space opera, dramatic lighting, cinematic",
    "fantasy":          "dark fantasy, epic medieval, mystical atmosphere, cinematic",
    "mystery_horror":   "noir, mysterious, 1920s aesthetic, atmospheric fog, chiaroscuro",
    "ww2":              "World War II historical, gritty realism, sepia tones, war photography style, cinematic",
    "romance":          "contemporary drama, warm soft lighting, intimate atmosphere, film still aesthetic",
    "action":           "action thriller, high contrast, urban cinematic, dynamic composition",
    "detective_classico": "classic detective, 1930s–1950s period, warm golden tones, Agatha Christie style, cinematic",
    "survival_horror":  "post-apocalyptic horror, dark and gritty, survival, cinematic",
    "militare":         "military tactical, realistic, war documentary style, cinematic",
}


def _build_image_prompt(scene_text: str, genre: str, environment_type: str) -> str:
    style = _GENRE_IMAGE_STYLE.get(genre, "cinematic, dramatic, atmospheric")
    try:
        prompt = (
            "Translate the following Italian tabletop RPG scene description into a vivid English image generation prompt.\n"
            f"Visual style: {style}, high quality digital illustration, detailed.\n"
            f"Environment: {environment_type}.\n"
            f"Italian scene: {scene_text}\n\n"
            "COMPOSITION RULES: wide cinematic shot, characters prominently in foreground (full or three-quarter body visible), "
            "environment fills the background, 16:9 widescreen framing, no cropping of characters.\n"
            "Output ONLY the English image prompt (2 sentences max, vivid and specific, no quotes, no explanations)."
        )
        return _call_text_model(prompt, max_tokens=140).strip()
    except Exception:
        return f"{style}, {environment_type}, wide cinematic shot, characters prominent in foreground, full body visible, widescreen composition"


def generate_character_avatar(
    photo_b64: str,
    genre: str,
    role: str,
    archetype: str,
) -> str | None:
    """Genera un ritratto del personaggio adattato al genere.
    Con Gemini usa input immagine + prompt; con OpenAI usa image edit/reference generation."""
    _clear_last_image_error()
    if _ACTIVE_PROVIDER == "openai":
        if not OPENAI_API_KEY or not _OPENAI_AVAILABLE:
            _set_last_image_error("generate_character_avatar/openai", "OpenAI non disponibile o API key mancante")
            return None
        try:
            style = _GENRE_IMAGE_STYLE.get(genre, "cinematic, dramatic, atmospheric")
            costume = {
                "sci_fi":             "futuristic space armor, cyberpunk tactical gear",
                "fantasy":            "medieval fantasy armor, enchanted equipment",
                "mystery_horror":     "1920s detective clothing, noir period attire",
                "ww2":                "World War II military uniform, period-accurate gear, helmet and equipment",
                "romance":            "contemporary elegant casual clothing, modern fashion",
                "action":             "tactical operative gear, urban field outfit",
                "detective_classico": "1930s–1950s period suit, trench coat, detective attire",
                "survival_horror":    "ragged post-apocalyptic survival gear",
                "militare":           "modern military tactical gear, combat vest",
            }.get(genre, "appropriate clothing for the setting")

            prompt = (
                f"Transform this photo into a square head-and-shoulders character portrait of the same person as a {role} ({archetype}) "
                f"in a {genre.replace('_', ' ')} story. "
                f"Keep the face, age, skin tone, hair, and overall likeness clearly recognizable. "
                f"Use {style} lighting and rendering. Outfit: {costume}. "
                "Polished illustrated portrait, no text, no captions, no extra people, centered composition."
            )

            photo_bytes = base64.b64decode(photo_b64)
            suffix = ".jpg" if photo_bytes[:2] == b"\xff\xd8" else ".png"
            image_file = io.BytesIO(photo_bytes)
            image_file.name = f"avatar-source{suffix}"

            client = _openai_module.OpenAI(api_key=OPENAI_API_KEY)
            response = client.images.edit(
                model=OPENAI_IMAGE_EDIT_MODEL,
                image=image_file,
                prompt=prompt,
                size="1024x1024",
                quality="medium",
                input_fidelity="high",
                output_format="png",
            )
            if getattr(response, "data", None) and getattr(response.data[0], "b64_json", None):
                return response.data[0].b64_json
            _set_last_image_error("generate_character_avatar/openai", f"risposta senza immagine base64: {repr(response)[:500]}")
            return None
        except Exception as e:
            _set_last_image_error("generate_character_avatar/openai", e)
            return None
    key = os.getenv("GOOGLE_AI_STUDIO_KEY", "")
    if not key or not _GOOGLE_GENAI_AVAILABLE:
        _set_last_image_error("generate_character_avatar/gemini", "Gemini non disponibile o GOOGLE_AI_STUDIO_KEY mancante")
        return None
    try:
        style = _GENRE_IMAGE_STYLE.get(genre, "cinematic, dramatic, atmospheric")
        costume = {
            "sci_fi":             "futuristic space armor, cyberpunk tactical gear",
            "fantasy":            "medieval fantasy armor, enchanted equipment",
            "mystery_horror":     "1920s detective clothing, noir period attire",
            "ww2":                "World War II military uniform, period-accurate gear, helmet and equipment",
            "romance":            "contemporary elegant casual clothing, modern fashion",
            "action":             "tactical operative gear, urban field outfit",
            "detective_classico": "1930s–1950s period suit, trench coat, detective attire",
            "survival_horror":    "ragged post-apocalyptic survival gear",
            "militare":           "modern military tactical gear, combat vest",
        }.get(genre, "appropriate clothing for the setting")

        prompt = (
            f"Generate a close-up character portrait of this person as a {role} ({archetype}) "
            f"in a {genre.replace('_', ' ')} story.\n"
            f"Art style: {style}, character portrait illustration, dramatic lighting.\n"
            f"Outfit: {costume}.\n"
            f"Keep their facial features and likeness clearly recognizable from the photo.\n"
            f"Square portrait, head and shoulders composition. No text or captions."
        )
        photo_bytes = base64.b64decode(photo_b64)
        mime = "image/jpeg" if photo_bytes[:2] == b"\xff\xd8" else "image/png"
        client = google_genai.Client(api_key=key)
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[google_genai_types.Content(parts=[
                google_genai_types.Part(inline_data=google_genai_types.Blob(mime_type=mime, data=photo_bytes)),
                google_genai_types.Part(text=prompt),
            ])],
            config=google_genai_types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                return base64.b64encode(part.inline_data.data).decode("utf-8")
        _set_last_image_error("generate_character_avatar/gemini", f"risposta senza parte immagine: {repr(response)[:500]}")
        return None
    except Exception as e:
        _set_last_image_error("generate_character_avatar", e)
        return None


def generate_npc_avatar(name: str, description: str, entity_type: str, genre: str) -> str | None:
    """Genera un ritratto da descrizione testuale per NPC/nemici (senza foto di riferimento)."""
    _clear_last_image_error()
    _npc_costume = {
        "sci_fi": "futuristic space armor, cyberpunk tactical gear",
        "fantasy": "medieval fantasy armor, enchanted equipment",
        "mystery_horror": "1920s detective clothing, noir period attire",
        "ww2": "World War II military uniform, period-accurate gear",
        "romance": "contemporary elegant clothing, modern fashion",
        "action": "tactical operative gear, urban field outfit",
        "detective_classico": "1930s–1950s period suit, trench coat",
        "survival_horror": "ragged post-apocalyptic survival gear",
        "militare": "modern military tactical gear, combat vest",
    }
    costume = _npc_costume.get(genre, "appropriate clothing for the setting")
    style = _GENRE_IMAGE_STYLE.get(genre, "cinematic, dramatic, atmospheric")
    type_hint = {
        "enemy": "dangerous antagonist, menacing expression, combat-ready",
        "npc": "supporting character, neutral expression",
        "ally": "friendly ally, determined expression",
    }.get(entity_type, "character")

    # Hash del nome per generare tratti visivi stabili e unici per personaggio
    import hashlib
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)
    hair_colors = ["black hair", "dark brown hair", "auburn hair", "blonde hair", "grey hair", "white hair", "red hair"]
    build_hints = ["lean and angular face", "round and soft face", "square jaw", "narrow face", "broad face", "weathered face", "sharp features"]
    age_hints = ["young adult, early 20s", "mid 30s", "late 40s", "elderly, over 60", "middle aged"]
    hair = hair_colors[h % len(hair_colors)]
    build = build_hints[(h >> 4) % len(build_hints)]
    age = age_hints[(h >> 8) % len(age_hints)]
    unique_traits = f"{age}, {hair}, {build}"

    prompt = (
        f"Square character portrait of '{name}', a {type_hint}.\n"
        f"Description: {description or name}.\n"
        f"Physical traits: {unique_traits}.\n"
        f"Setting: {genre.replace('_', ' ')} story. Outfit: {costume}.\n"
        f"Style: {style}, illustrated portrait, head and shoulders, dramatic lighting.\n"
        f"No text, no captions, centered face."
    )

    if _ACTIVE_PROVIDER == "openai":
        if not OPENAI_API_KEY or not _OPENAI_AVAILABLE:
            return None
        try:
            client = _openai_module.OpenAI(api_key=OPENAI_API_KEY)
            response = client.images.generate(
                model=OPENAI_IMAGE_EDIT_MODEL,  # gpt-image-1 supporta b64_json nativo
                prompt=prompt,
                size="1024x1024",
                quality="medium",
                output_format="png",
                n=1,
            )
            if getattr(response, "data", None) and getattr(response.data[0], "b64_json", None):
                return response.data[0].b64_json
            return None
        except Exception as e:
            _set_last_image_error("generate_npc_avatar/openai", e)
            return None

    key = os.getenv("GOOGLE_AI_STUDIO_KEY", "")
    if not key or not _GOOGLE_GENAI_AVAILABLE:
        return None
    try:
        client = google_genai.Client(api_key=key)
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[google_genai_types.Content(parts=[google_genai_types.Part(text=prompt)])],
            config=google_genai_types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                return base64.b64encode(part.inline_data.data).decode("utf-8")
        return None
    except Exception as e:
        _set_last_image_error("generate_npc_avatar/gemini", e)
        return None


_GENRE_COSTUME = {
    "sci_fi":             "futuristic space armor, cyberpunk tactical gear, advanced technology accessories",
    "fantasy":            "medieval fantasy armor, enchanted equipment, mystical period clothing",
    "mystery_horror":     "1920s–1930s detective clothing, noir period attire, overcoat and hat",
    "ww2":                "World War II military uniform, period-accurate helmet and equipment, olive drab or field grey",
    "romance":            "contemporary elegant casual clothing, modern fashion, warm tones",
    "action":             "tactical operative gear, urban field outfit, concealed equipment",
    "detective_classico": "1930s–1950s period suit, trench coat, detective attire, fedora",
    "survival_horror":    "ragged survival gear, post-apocalyptic patched clothing, tactical wear",
    "militare":           "modern military tactical gear, combat vest, camouflage uniform",
}


def _generate_scene_with_photos(
    image_prompt: str,
    genre: str,
    player_photos_bytes: list[bytes],
    player_names: list[str],
    key: str,
) -> str | None:
    """Usa gemini-2.5-flash-image passando le foto dei giocatori come riferimento visivo."""
    style = _GENRE_IMAGE_STYLE.get(genre, "cinematic, dramatic, atmospheric")
    costume = _GENRE_COSTUME.get(genre, "appropriate clothing for the setting")
    names_str = ", ".join(player_names) if player_names else "the characters"

    prompt_text = (
        f"HORIZONTAL LANDSCAPE IMAGE ONLY — wider than tall, 16:9 widescreen format.\n"
        f"Using the provided photo(s) as visual references for the characters ({names_str}), "
        f"generate a cinematic widescreen scene illustration.\n"
        f"Scene: {image_prompt}\n"
        f"Art style: {style}, detailed digital illustration, dramatic lighting.\n"
        f"Dress each character in {costume}, adapted to their appearance from the photos.\n"
        f"Keep facial features and general look recognizable.\n"
        f"COMPOSITION: wide shot, characters in foreground (full or three-quarter body visible), "
        f"environment fills background. No text or captions."
    )

    client = google_genai.Client(api_key=key)
    parts = []
    for photo_bytes in player_photos_bytes:
        mime = "image/jpeg" if photo_bytes[:2] == b"\xff\xd8" else "image/png"
        parts.append(google_genai_types.Part(
            inline_data=google_genai_types.Blob(mime_type=mime, data=photo_bytes)
        ))
    parts.append(google_genai_types.Part(text=prompt_text))

    print(f"[generate_scene_image] usando Gemini con {len(player_photos_bytes)} foto...")
    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=[google_genai_types.Content(parts=parts)],
        config=google_genai_types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )
    for part in response.candidates[0].content.parts:
        if hasattr(part, "inline_data") and part.inline_data:
            return base64.b64encode(part.inline_data.data).decode("utf-8")
    return None


def _generate_scene_image_openai(
    scene_text: str,
    genre: str,
    environment_type: str,
    player_photos_b64: list[str] | None = None,
    player_names: list[str] | None = None,
) -> str | None:
    """Genera un'immagine scena con OpenAI.
    Con foto usa gpt-image-1 come image edit/reference; senza foto usa DALL-E 3."""
    if not OPENAI_API_KEY or not _OPENAI_AVAILABLE:
        return None
    try:
        image_prompt = _build_image_prompt(scene_text, genre, environment_type)
        client = _openai_module.OpenAI(api_key=OPENAI_API_KEY)
        if player_photos_b64:
            style = _GENRE_IMAGE_STYLE.get(genre, "cinematic, dramatic, atmospheric")
            costume = _GENRE_COSTUME.get(genre, "appropriate clothing for the setting")
            names_str = ", ".join(player_names or []) or "the characters"
            prompt = (
                "Create a horizontal 16:9 cinematic scene illustration using the provided photo(s) "
                f"as visual references for the characters ({names_str}). "
                f"Scene: {image_prompt}\n"
                f"Art style: {style}, detailed digital illustration, dramatic lighting. "
                f"Dress each character in {costume}, adapted to their appearance from the photos. "
                "Keep facial features and general likeness recognizable. "
                "Wide shot, characters in foreground, environment fills the background. No text or captions."
            )
            image_files = []
            for idx, photo_b64 in enumerate(player_photos_b64, start=1):
                photo_bytes = base64.b64decode(photo_b64)
                suffix = ".jpg" if photo_bytes[:2] == b"\xff\xd8" else ".png"
                image_file = io.BytesIO(photo_bytes)
                image_file.name = f"scene-reference-{idx}{suffix}"
                image_files.append(image_file)

            response = client.images.edit(
                model=OPENAI_IMAGE_EDIT_MODEL,
                image=image_files,
                prompt=prompt,
                size="1536x1024",
                quality="medium",
                input_fidelity="high",
                output_format="png",
            )
            return response.data[0].b64_json if getattr(response, "data", None) else None

        response = client.images.generate(
            model=OPENAI_IMAGE_EDIT_MODEL,  # gpt-image-1 supporta b64_json nativo
            prompt=image_prompt,
            size="1536x1024",
            quality="medium",
            n=1,
        )
        return response.data[0].b64_json
    except Exception as e:
        _set_last_image_error("generate_scene_image_openai", e)
        return None


_GENRE_TACTICAL_STYLE: dict[str, str] = {
    "sci_fi": (
        "top-down tactical battle map of a science fiction location, "
        "metallic floors, glowing neon conduits, blast doors, cover objects like crates and consoles, "
        "dark ambient lighting with blue/cyan accents, hard sci-fi aesthetic"
    ),
    "fantasy": (
        "top-down tactical battle map in classic D&D dungeon map style, "
        "hand-drawn look, stone floor tiles, dungeon walls, torchlit warm glow, "
        "wooden furniture, barrels, pillars as cover, parchment-style atmosphere"
    ),
    "mystery_horror": (
        "top-down tactical battle map of a gothic Victorian location, "
        "dark hardwood floors, persian rugs, antique furniture as cover, "
        "candlelight, long shadows, oppressive atmosphere, horror aesthetic"
    ),
    "ww2": (
        "top-down tactical battle map of a World War II location, "
        "trenches, sandbags, barbed wire, rubble, shattered walls as cover, "
        "muted khaki and grey palette, war-torn environment, military grid aesthetic"
    ),
    "romance": (
        "top-down tactical map of a contemporary elegant interior or outdoor location, "
        "warm soft lighting, tasteful furnishings, open areas and cover spots, "
        "clean lines, intimate atmosphere"
    ),
    "action": (
        "top-down tactical battle map of an urban or industrial location, "
        "concrete floors, metal shelving, vehicles and crates as cover, "
        "harsh fluorescent lighting, high-contrast modern thriller aesthetic"
    ),
    "detective_classico": (
        "top-down tactical map of a 1930s–1950s interior, "
        "parquet or marble floor, wooden desks and bookcases as cover, "
        "warm lamp lighting, Agatha Christie mansion or office aesthetic"
    ),
}


def generate_tactical_map_image(
    location_name: str,
    location_description: str,
    genre: str,
    environment_type: str,
    scene_narrative: str = "",
    mission_environment: str = "",
    enemy_names: list[str] | None = None,
) -> str | None:
    """Genera uno sfondo mappa tattica hex top-down stile GDR per il combattimento."""
    _clear_last_image_error()
    style = _GENRE_TACTICAL_STYLE.get(genre, _GENRE_TACTICAL_STYLE["fantasy"])

    # Usa Claude per tradurre il contesto italiano in un prompt immagine preciso
    try:
        enemy_line = f"Enemies present: {', '.join(enemy_names)}. " if enemy_names else ""
        narrative_line = f"Scene narrative (Italian, for context): {scene_narrative[:200]}. " if scene_narrative else ""
        env_context = mission_environment or environment_type
        translate_prompt = (
            f"You are a tabletop RPG map artist. Write a single English image generation prompt (2 sentences max) "
            f"for a top-down tactical battle map background. "
            f"Location name: {location_name}. "
            f"Location description (Italian): {location_description[:300]}. "
            f"Mission environment type: {env_context}. "
            f"{narrative_line}"
            f"{enemy_line}"
            f"RULES: pure overhead bird's-eye view, no people, no tokens, no grid lines, no labels, no text, "
            f"no UI elements. Show only the floor, walls, furniture, terrain features and cover objects. "
            f"Make it a real tabletop RPG battlemap: clear playable areas, readable entrances, cover, obstacles, "
            f"and environmental details that match the exact location, not a generic texture. "
            f"The visual style and architecture MUST match the location type and enemies described above. "
            f"Style reference: {style}. Output ONLY the English prompt, no explanations."
        )
        image_prompt = _call_text_model(translate_prompt, max_tokens=120).strip()
    except Exception:
        image_prompt = (
            f"{location_name}, {environment_type}, {style}, "
            "top-down bird's-eye view battle map, no people, no text, no grid lines, detailed floor and terrain"
        )

    # Aggiungi regole fisse di composizione alla fine
    full_prompt = (
        f"{image_prompt} "
        "Top-down 90-degree overhead view, flat floor perspective, no people, no tokens, no grid overlay, "
        "no text, no labels. Show terrain features, walls, furniture and cover objects only. "
        "Readable tabletop RPG battlemap, clear movement spaces, entrances, cover and obstacles, suitable for a sparse hex grid overlay. "
        "Aspect ratio 4:3, square-ish composition."
    )

    if _ACTIVE_PROVIDER == "openai":
        if not OPENAI_API_KEY or not _OPENAI_AVAILABLE:
            return None
        try:
            client = _openai_module.OpenAI(api_key=OPENAI_API_KEY)
            response = client.images.generate(
                model=OPENAI_IMAGE_EDIT_MODEL,
                prompt=full_prompt,
                size="1024x1024",
                quality="medium",
                n=1,
            )
            return response.data[0].b64_json
        except Exception as e:
            _set_last_image_error("generate_tactical_map_image/openai", e)
            return None

    key = os.getenv("GOOGLE_AI_STUDIO_KEY", "")
    if not key or not _GOOGLE_GENAI_AVAILABLE:
        return None
    try:
        client = google_genai.Client(api_key=key)
        response = client.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=full_prompt,
            config=google_genai_types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="1:1",
                output_mime_type="image/jpeg",
            ),
        )
        image_bytes = response.generated_images[0].image.image_bytes
        return base64.b64encode(image_bytes).decode("utf-8")
    except Exception as e:
        _set_last_image_error("generate_tactical_map_image/gemini", e)
        return None


def generate_scene_image(
    scene_text: str,
    genre: str,
    environment_type: str,
    player_photos_b64: list[str] | None = None,
    player_names: list[str] | None = None,
) -> str | None:
    """Genera un'immagine della scena.
    OpenAI: usa gpt-image-1 con foto se disponibili, altrimenti DALL-E 3.
    Claude+Gemini: usa Gemini con foto se disponibili, altrimenti Imagen 4."""
    if _ACTIVE_PROVIDER == "openai":
        return _generate_scene_image_openai(scene_text, genre, environment_type, player_photos_b64, player_names)
    key = os.getenv("GOOGLE_AI_STUDIO_KEY", "")
    if not key or not _GOOGLE_GENAI_AVAILABLE:
        print(f"[generate_scene_image] non disponibile: key={'presente' if key else 'mancante'}, genai={_GOOGLE_GENAI_AVAILABLE}")
        return None
    try:
        image_prompt = _build_image_prompt(scene_text, genre, environment_type)
        print(f"[generate_scene_image] prompt: {image_prompt[:120]}...")

        # Con foto dei giocatori → Gemini per consistenza del soggetto
        if player_photos_b64:
            photos_bytes = [base64.b64decode(p) for p in player_photos_b64]
            names = player_names or []
            result = _generate_scene_with_photos(image_prompt, genre, photos_bytes, names, key)
            if result:
                return result
            print("[generate_scene_image] Gemini fallback a Imagen...")

        # Senza foto (o se Gemini fallisce) → prova Imagen 4, fallback Imagen 3
        client = google_genai.Client(api_key=key)
        for imagen_model in ("imagen-4.0-generate-001", "imagen-3.0-generate-001"):
            try:
                response = client.models.generate_images(
                    model=imagen_model,
                    prompt=image_prompt,
                    config=google_genai_types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio="16:9",
                        output_mime_type="image/jpeg",
                    ),
                )
                image_bytes = response.generated_images[0].image.image_bytes
                print(f"[generate_scene_image] immagine generata con {imagen_model}")
                return base64.b64encode(image_bytes).decode("utf-8")
            except Exception as img_err:
                print(f"[generate_scene_image] {imagen_model} fallito: {img_err}")
                if "RESOURCE_EXHAUSTED" not in str(img_err) and "429" not in str(img_err):
                    break  # errore diverso dalla quota → non ritentare
        # Ultimo fallback: OpenAI DALL-E se disponibile
        if _OPENAI_AVAILABLE and OPENAI_API_KEY:
            print("[generate_scene_image] fallback a OpenAI DALL-E")
            return _generate_scene_image_openai(scene_text, genre, environment_type, player_photos_b64, player_names)
        return None
    except Exception as e:
        _set_last_image_error("generate_scene_image", e)
        return None


def _build_map_image_prompt(location_name: str, location_description: str) -> str:
    """Traduce nome+descrizione in un prompt cartografico top-down per immagini GDR."""
    try:
        prompt = (
            "Translate this tabletop RPG location into a concise English image prompt for a top-down cartographic map.\n"
            f"Location name: {location_name}\n"
            f"Description: {location_description}\n\n"
            "STYLE: hand-drawn top-down dungeon/location map, Dyson Logos ink style, "
            "architectural floor plan, black ink on cream parchment, rooms and corridors, "
            "no characters, no people, labeled areas.\n"
            "Output ONLY the image prompt (1-2 sentences, in English, describing what the map shows — "
            "layout, rooms, features — not mood or lighting)."
        )
        return _call_text_model(prompt, max_tokens=100).strip()
    except Exception:
        return f"Top-down cartographic floor plan of {location_name}, hand-drawn ink style, architectural map layout"


def generate_location_map_image(location_name: str, location_description: str) -> str | None:
    """Genera un'immagine cartografica top-down per una locazione (stile mappa GDR)."""
    _clear_last_image_error()
    map_prompt = (
        f"Top-down hand-drawn tabletop RPG dungeon map of '{location_name}'. "
        f"{_build_map_image_prompt(location_name, location_description)} "
        "Style: Dyson Logos black ink line art, architectural floor plan, "
        "cream parchment background, labeled rooms, corridors, doors and key features clearly marked, "
        "no characters, no people, top-down orthographic view, clean cartographic detail."
    )
    if _ACTIVE_PROVIDER == "openai":
        if not OPENAI_API_KEY or not _OPENAI_AVAILABLE:
            return None
        try:
            client = _openai_module.OpenAI(api_key=OPENAI_API_KEY)
            response = client.images.generate(
                model=OPENAI_IMAGE_EDIT_MODEL,
                prompt=map_prompt,
                size="1024x1024",
                quality="medium",
                n=1,
            )
            return response.data[0].b64_json
        except Exception as e:
            _set_last_image_error("generate_location_map_image/openai", e)
            return None
    key = os.getenv("GOOGLE_AI_STUDIO_KEY", "")
    if not key or not _GOOGLE_GENAI_AVAILABLE:
        return None
    try:
        client = google_genai.Client(api_key=key)
        for imagen_model in ("imagen-4.0-generate-001", "imagen-3.0-generate-001"):
            try:
                response = client.models.generate_images(
                    model=imagen_model,
                    prompt=map_prompt,
                    config=google_genai_types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio="1:1",
                        output_mime_type="image/jpeg",
                    ),
                )
                return base64.b64encode(response.generated_images[0].image.image_bytes).decode("utf-8")
            except Exception as img_err:
                if "RESOURCE_EXHAUSTED" not in str(img_err) and "429" not in str(img_err):
                    break
        if _OPENAI_AVAILABLE and OPENAI_API_KEY:
            try:
                client2 = _openai_module.OpenAI(api_key=OPENAI_API_KEY)
                resp2 = client2.images.generate(model=OPENAI_IMAGE_EDIT_MODEL, prompt=map_prompt, size="1024x1024", quality="medium", n=1)
                return resp2.data[0].b64_json
            except Exception:
                pass
        return None
    except Exception as e:
        _set_last_image_error("generate_location_map_image/gemini", e)
        return None


# ── Master GDR: turno narrativo ───────────────────────────────────────────────

def _player_sheet(p: dict) -> str:
    """Formatta la scheda sintetica di un personaggio per il prompt Master."""
    stats = p.get("stats", {})
    skills = p.get("skills", {})
    top_skills = sorted(skills.items(), key=lambda x: -x[1])[:6]
    skill_str = ", ".join(f"{skill_display(k)}:{v}" for k, v in top_skills)
    stat_str = " ".join(f"{stat_display(k)}:{v}" for k, v in stats.items())
    adv = p.get("advantages", [])
    disadv = p.get("disadvantages", [])
    adv_str = (", ".join(adv + disadv)) if (adv or disadv) else "nessuno"
    line = f"- {p['name']} ({p['role']}): {stat_str} | Skills: {skill_str} | Vantaggi: {adv_str}"
    trait_notes = trait_story_notes(list(adv or []) + list(disadv or []), limit=3)
    if trait_notes:
        line += f"\n  Tratti attivi in fiction: {' | '.join(trait_notes)}"
    self_control = traits_requiring_self_control(list(disadv or []))
    if self_control:
        line += "\n  Autocontrollo: " + ", ".join(f"{x['name']}({x['target']})" for x in self_control)
    motivation = (p.get("motivation") or "").strip()
    backstory = (p.get("backstory") or "").strip()
    if motivation:
        line += f"\n  Obiettivo: {motivation}"
    if backstory:
        line += f"\n  Storia: {backstory}"
    return line


def narrate_combat_result(combat_log: dict, genre: str, adventure: dict | None = None) -> str:
    """
    Genera 1-2 frasi narrative in italiano sull'esito di uno scambio di combattimento.
    Chiamata dopo attacco+difesa completati. Deve essere veloce (max_tokens basso).
    """
    genre_label = _GENRE_LABELS.get(genre, genre)
    log = combat_log or {}
    result = log.get("result") or {}

    attacker = log.get("attacker", "L'attaccante")
    target = log.get("target", "il bersaglio")
    skill = log.get("skill_name") or log.get("skill", "")
    hit = result.get("hit", False)
    defended = result.get("defended", False)
    net_damage = result.get("net_damage", 0)
    wound = result.get("wound_threshold", "")
    atk_crit = result.get("attacker_critical", False)
    def_crit_fail = result.get("defense_critical_fail", False)
    hint = result.get("narrative_hint", "")
    defense_type = log.get("defense_type", "")

    # Costruisce contesto per Claude
    outcome_desc = []
    if not hit:
        outcome_desc.append("attacco mancato")
    elif defended:
        defense_label = {"dodge": "schivata", "parry": "parata", "block": "bloccata"}.get(defense_type, "difesa")
        outcome_desc.append(f"colpo parato con {defense_label}")
        if def_crit_fail:
            outcome_desc.append("FALLIMENTO CRITICO della difesa")
    else:
        outcome_desc.append(f"colpo a segno — {net_damage} danni netti")
        if atk_crit:
            outcome_desc.append("CRITICO")
        if wound:
            wound_label = {"ferito": "ferita leggera", "ferito_grave": "FERITA GRAVE", "fuori_combattimento": "ABBATTUTO", "morto": "MORTO"}.get(wound, wound)
            outcome_desc.append(wound_label)

    outcome_text = ", ".join(outcome_desc)
    context = adventure.get("premise", "")[:80] if adventure else ""

    prompt = (
        f"Sei il Master di una partita GDR in stile {genre_label}. "
        f"Descrivi l'esito di questo scambio di combattimento in 1-2 frasi vive e cinematografiche in italiano. "
        f"Non ripetere numeri o meccaniche: traduci in narrazione visiva. Sii conciso e potente.\n"
        f"Contesto avventura: {context}\n"
        f"Attaccante: {attacker} | Bersaglio: {target} | Tecnica: {skill}\n"
        f"Esito meccanico: {outcome_text}\n"
        f"Scrivi SOLO le 1-2 frasi narrative, senza titoli o spiegazioni."
    )
    try:
        return _call_text_model(prompt, max_tokens=120).strip()
    except Exception:
        # fallback narrativo deterministico
        if not hit:
            return f"{attacker} manca il colpo — {target} è ancora in piedi."
        if defended:
            return f"{target} riesce a deflettere l'attacco di {attacker} all'ultimo istante."
        if wound == "fuori_combattimento":
            return f"Il colpo di {attacker} abbatte {target}. La minaccia è neutralizzata."
        if wound == "ferito_grave":
            return f"{attacker} infligge una ferita grave a {target}, che vacilla sotto il colpo."
        return f"{attacker} colpisce {target} — il danno si fa sentire."


# ── Generazione personaggio via AI ────────────────────────────────────────────

def generate_character_from_description(genre: str, description: str) -> dict:
    """
    Data una descrizione in linguaggio libero, genera un CharacterDraft GURPS valido.
    Budget 100 pt, power level Eccezionale (stat 10-13, skill chiave 12-14).

    Restituisce un dict compatibile con CharacterDraft:
      name, role, archetype, stats, skills, advantages, disadvantages, dr, items
    """
    adv_list = ["Carisma", "Riflessi da Combattimento", "Duro da Uccidere",
                "Sensi Acuti", "Forza Aumentata", "Alta Tecnologia"]
    disadv_list = ["Animo Sanguinario", "Codardo", "Sospettoso"]

    genre_labels = {
        "sci_fi": "fantascienza", "fantasy": "fantasy medievale",
        "mystery_horror": "mistero/horror", "ww2": "seconda guerra mondiale",
        "romance": "romance", "action": "azione contemporanea",
        "detective_classico": "noir/detective classico",
    }
    genre_label = genre_labels.get(genre, genre)

    prompt = f"""Sei un game designer esperto di GURPS Lite 4ª ed. italiana.
Crea un personaggio giocante per una campagna di {genre_label} basandoti su questa descrizione:

"{description}"

REGOLE GURPS (rispetta rigorosamente):
- Budget: 100 punti totali
- Stat: forza/agilita/intelligenza/empatia, base 10, range 8-14
  - forza/empatia costano 10 pt/livello sopra 10, restituiscono 10 sotto 10
  - agilita/intelligenza costano 20 pt/livello sopra 10, restituiscono 20 sotto 10
- Skill: livello effettivo 10-15, costo cumulativo E/M/D
- Vantaggi disponibili (costo): {', '.join(f"{a}" for a in adv_list)}
- Svantaggi disponibili (rimborso): {', '.join(f"{d}" for d in disadv_list)}
  - max -40 pt di svantaggi totali
- PF = forza, FP = empatia

Scegli 4-6 skill adatte al personaggio. Le skill interne sono (usa questi nomi esatti):
combattere, resistere, forzare, proteggere, intimidire, lottare, sopravvivere, demolire,
schivare, furtivita, acrobazia, rapidita, mira, guidare, manualita, infiltrarsi, scassinare, pedinare,
investigare, analizzare, tecnologia, medicina, cultura, strategia, decifrare, osservare, ingegneria, scienze,
persuadere, ingannare, intuire, calmare, ispirare, curare, comandare, comunicare, intrattenere, etichetta

Rispondi SOLO con questo JSON:
{{
  "name": "...",
  "role": "...",
  "archetype": "...",
  "stats": {{"forza": 10, "agilita": 10, "intelligenza": 10, "empatia": 10}},
  "skills": {{"skill_interna": livello_int, ...}},
  "advantages": [],
  "disadvantages": [],
  "dr": 0,
  "items": ["...", "..."],
  "point_breakdown": "stat X pt + skill Y pt + adv Z pt = totale"
}}"""

    raw = _call_text_model(prompt, max_tokens=700)
    try:
        return _extract_json_object(raw)
    except Exception:
        return {"error": "Impossibile generare il personaggio. Riprova con una descrizione diversa."}


def enrich_character_with_backstory(character: dict, adventure: dict, genre: str) -> dict:
    """Genera backstory + aggiusta vantaggi/svantaggi di un archetipo in base alla bibbia."""
    genre_label = _GENRE_LABELS.get(genre, genre)
    adv_list = [
        "Carisma +5pt", "Riflessi da Combattimento +15pt", "Duro da Uccidere +2pt",
        "Sensi Acuti +2pt", "Forza Aumentata +10pt", "Alta Tecnologia +5pt",
        "Ambidestrezza +5pt", "Bellezza +4pt", "Empatia +15pt", "Memoria Fotografica +10pt",
        "Coraggio +10pt", "Sangue Freddo +5pt", "Fortuna +15pt", "Contatti +3pt",
        "Status Sociale +5pt", "Ricchezza +10pt", "Talento +5pt", "Voce Bella +10pt",
        "Autorità +5pt", "Linguaggio Nativo Extra +3pt", "Istinto di Sopravvivenza +5pt",
    ]
    disadv_list = [
        "Animo Sanguinario -10pt", "Codardo -5pt", "Sospettoso -5pt", "Avidità -15pt",
        "Senso del Dovere -5pt", "Nemico -5pt", "Segreto -10pt", "Dipendenza -5pt",
        "Fobia -10pt", "Impulsività -10pt", "Arroganza -5pt", "Lealtà -5pt",
        "Poca Autostima -10pt", "Amnesia -10pt", "Mancanza di Empatia -15pt",
        "Curiosità Morbosa -5pt", "Smemoratezza -5pt", "Pessimismo -5pt",
    ]

    name = character.get("name", "Personaggio")
    role = character.get("role", "Avventuriero")
    current_adv = character.get("advantages", [])
    current_dis = character.get("disadvantages", [])
    current_stats = character.get("stats", {})

    prompt = f"""Sei un game designer narrativo per GDR GURPS Lite ({genre_label}).

AVVENTURA:
Titolo: {adventure.get('title', '?')}
Premessa: {adventure.get('premise', '')}
Atmosfera: {adventure.get('atmosphere', '')}
Minaccia: {adventure.get('threat_description', '')}
Verità nascosta (NON rivelare ai giocatori): {adventure.get('hidden_truth', '')}

PERSONAGGIO:
Nome: {name}
Ruolo: {role}
Stat attuali: FO={current_stats.get('forza',10)} DE={current_stats.get('agilita',10)} IN={current_stats.get('intelligenza',10)} SA={current_stats.get('empatia',10)}
Vantaggi attuali: {', '.join(current_adv) or 'nessuno'}
Svantaggi attuali: {', '.join(current_dis) or 'nessuno'}

Il tuo compito: scrivi una storia personale per {name} che lo leghi a questa avventura specifica.
La storia deve spiegare PERCHÉ è coinvolto, cosa lo motiva, e cosa rischia.
Poi suggerisci 1-2 vantaggi e 1-2 svantaggi che riflettano la sua storia, scelti dalle liste.

Vantaggi disponibili: {', '.join(adv_list)}
Svantaggi disponibili: {', '.join(disadv_list)}

REGOLE:
- Il backstory deve essere 1-2 frasi brevi (max 30 parole), concreto, personale, non generico.
- I vantaggi/svantaggi suggeriti devono essere coerenti col backstory E diversi da quelli già presenti (puoi confermare uno se molto appropriato).
- Non superare -40pt di svantaggi totali (considera quelli già presenti).
- Usa esattamente i nomi delle liste (senza il costo).

Rispondi SOLO con questo JSON:
{{
  "backstory": "Storia personale in 1-2 frasi brevi (max 30 parole) che lega il personaggio all'avventura",
  "motivation": "Una frase: cosa vuole ottenere da questa avventura",
  "suggested_advantages": ["Vantaggio1", "Vantaggio2"],
  "suggested_disadvantages": ["Svantaggio1", "Svantaggio2"]
}}"""

    raw = _call_text_model(prompt, max_tokens=400)
    try:
        data = _extract_json_object(raw)
        result = dict(character)
        result["backstory"] = data.get("backstory", "")
        result["motivation"] = data.get("motivation", "")
        # Merge vantaggi/svantaggi: aggiungi i suggeriti se non già presenti
        new_adv = list(current_adv)
        for a in (data.get("suggested_advantages") or []):
            if a and a not in new_adv:
                new_adv.append(a)
        result["advantages"] = new_adv
        new_dis = list(current_dis)
        for d in (data.get("suggested_disadvantages") or []):
            if d and d not in new_dis:
                new_dis.append(d)
        result["disadvantages"] = new_dis
        return result
    except Exception as e:
        print(f"[enrich_character_with_backstory] errore per {name}: {e}")
        return character


# ── Bibbia avventura ──────────────────────────────────────────────────────────

_GENRE_LABELS = {
    "sci_fi": "fantascienza", "fantasy": "fantasy medievale",
    "mystery_horror": "mistero/horror", "ww2": "seconda guerra mondiale",
    "romance": "romance", "action": "azione contemporanea",
    "detective_classico": "noir/detective classico",
}

def create_adventure(genre: str, players: list[dict]) -> dict:
    """
    Genera la bibbia strutturata dell'avventura.
    Restituisce un dict con: title, premise, hidden_truth, npcs, clues,
    twists, win_condition, threat_description, threat_max_turns, locations.
    """
    if not _text_provider_available():
        return {"error": "Nessun provider AI testuale configurato: impossibile creare un'avventura originale."}

    genre_label = _GENRE_LABELS.get(genre, genre)
    n_players = len(players)
    roles = ", ".join(f"{p['name']} ({p.get('role','')})" for p in players)
    party_context = (
        f"{n_players} giocatori: {roles}"
        if n_players > 0
        else "un gruppo di 3-4 personaggi che verranno creati DOPO la compilazione, quindi prevedi ruoli utili ma non nominare PG specifici"
    )

    prompt = f"""Sei un game designer esperto di GDR. Crea una avventura originale e coinvolgente
in stile {genre_label} per {party_context}.

L'avventura deve avere:
- Una premessa intrigante che si apre in medias res
- Una verità nascosta che i giocatori devono scoprire
- 4-5 PNG con motivazioni proprie (non sono comparse — ognuno ha un segreto)
- 5-6 indizi concreti e trovabili (luoghi, oggetti, persone)
- 2-3 colpi di scena che il Master può attivare in base alle scelte
- Una condizione di vittoria chiara
- Una minaccia che scala (es. un killer che colpisce di nuovo, una bomba, un rituale)
- 3-4 location principali dell'avventura

Rispondi SOLO con questo JSON:
{{
  "title": "Titolo avventura",
  "premise": "Descrizione situazione iniziale (3-4 frasi, in medias res)",
  "hidden_truth": "La verità che i giocatori devono scoprire",
  "atmosphere": "Tono/atmosfera dell'avventura (es: noir opprimente, horror psicologico)",
  "npcs": [
    {{
      "id": "npc_1",
      "name": "Nome",
      "role": "Ruolo nell'avventura",
      "description": "Aspetto e prima impressione",
      "motivation": "Cosa vuole veramente",
      "secret": "Il suo segreto",
      "status": "alive",
      "location": "Dove si trova inizialmente",
      "attitude": "neutral"
    }}
  ],
  "clues": [
    {{
      "id": "clue_1",
      "label": "Nome breve dell'indizio",
      "text": "Descrizione dell'indizio",
      "type": "physical_evidence | testimony | document | behavior | location_detail | contradiction",
      "thread_id": "T1 | T2 | T3",
      "reveals": "Cosa suggerisce o rivela",
      "payoff": "Cosa permette di capire, sbloccare o evitare",
      "location": "Dove/come si trova",
      "found": false
    }}
  ],
  "story_threads": [
    {{
      "id": "T1",
      "title": "Titolo pista",
      "question": "Domanda investigativa",
      "true_answer": "Risposta canonica nascosta",
      "status": "hidden",
      "required_clues": ["clue_1"],
      "discovered_clues": [],
      "partial_clues": [],
      "minimum_clues_to_deduce": 2,
      "payoff": "Cosa sblocca questa deduzione",
      "linked_npcs": ["npc_1"],
      "linked_locations": ["loc_1"]
    }}
  ],
  "adventure_canon": {{
    "core_truth": "Verità centrale già decisa",
    "main_antagonist": "Nome antagonista principale",
    "false_leads": ["falso sospetto o falsa pista"],
    "key_locations": ["luogo chiave"],
    "required_clues": ["clue_1"],
    "optional_events": ["evento opzionale"],
    "finale_conditions": ["condizione finale concreta"]
  }},
  "twists": [
    {{
      "id": "twist_1",
      "trigger": "Quando/come si attiva",
      "effect": "Cosa cambia nella storia",
      "used": false
    }}
  ],
  "win_condition": "Come i giocatori vincono",
  "threat_description": "La minaccia che scala nel tempo",
  "threat_max_turns": 8,
  "has_time_pressure": true,
  "locations": [
    {{
      "id": "loc_1",
      "name": "Nome location",
      "description": "Descrizione breve",
      "has_combat_potential": false,
      "tactical_map": {{
        "enabled": false,
        "role": "hot_zone | finale",
        "layout": "room | narrow | open",
        "features": ["coperture/elementi tattici"],
        "hazards": ["rischi ambientali"],
        "trigger": "quando si apre il confronto"
      }}
    }}
  ]
}}"""

    attempts: list[tuple[str, str]] = [(_ACTIVE_PROVIDER, prompt)]
    fallback_provider = _other_provider()
    if fallback_provider:
        attempts.append((fallback_provider, prompt))

    last_error = ""
    for provider_name, attempt_prompt in attempts:
        try:
            raw = (
                _call_text_model(attempt_prompt, max_tokens=4500)
                if provider_name == _ACTIVE_PROVIDER
                else _call_text_model_with_provider(provider_name, attempt_prompt, max_tokens=4500)
            )
            if _looks_like_refusal(raw):
                last_error = "provider_refusal"
                continue
            return _normalize_adventure_canon(_extract_json_object(raw), source="generated")
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            print(f"[create_adventure] provider {provider_name} errore: {last_error}")
            continue
    return {"error": f"Impossibile generare un'avventura originale: {last_error or 'provider non disponibile'}"}


def _canon_slug(value: str, fallback: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return text[:42] or fallback


def _infer_clue_type(text: str, location: str = "") -> str:
    blob = f"{text} {location}".lower()
    if any(w in blob for w in ["lettera", "diario", "registro", "nota", "document", "codice", "log", "file"]):
        return "document"
    if any(w in blob for w in ["testimone", "dice", "racconta", "confessa", "sussurra", "voce"]):
        return "testimony"
    if any(w in blob for w in ["sangue", "arma", "impronta", "chiave", "sigillo", "oggetto", "frammento", "corpo"]):
        return "physical_evidence"
    if location:
        return "location_detail"
    if any(w in blob for w in ["contraddice", "incongruenza", "non torna", "falso"]):
        return "contradiction"
    return "physical_evidence"


def _infer_tactical_layout(text: str) -> str:
    blob = str(text or "").lower()
    if any(w in blob for w in ["corridoio", "tunnel", "galleria", "passaggio", "ponte", "vicolo", "strett"]):
        return "narrow"
    if any(w in blob for w in ["cortile", "piazza", "hangar", "radura", "foresta", "campo", "rovine", "esterno", "sala grande"]):
        return "open"
    return "room"


def _build_tactical_map_spec(location: dict, *, role: str, genre: str = "") -> dict:
    name = _clean_canon_text(location.get("name", "Zona tattica"), limit=120)
    desc = _clean_canon_text(location.get("description", ""), limit=220)
    blob = f"{name} {desc} {genre}".lower()
    layout = _infer_tactical_layout(blob)
    if layout == "narrow":
        cols, rows = 12, 6
    elif layout == "open":
        cols, rows = 12, 8
    else:
        cols, rows = 10, 7
    features: list[str] = []
    hazards: list[str] = []
    if any(w in blob for w in ["taverna", "locanda", "osteria", "saloon"]):
        features += ["tavoli ribaltabili", "bancone massiccio", "camino o cucina come ostacolo", "scala o ballatoio"]
        hazards += ["vetri rotti", "clienti in fuga"]
    elif any(w in blob for w in ["biblioteca", "archiv", "scriptorium", "monastero"]):
        features += ["scaffali come copertura", "corridoi tra librerie", "tavoli di lettura", "vetrine con manoscritti"]
        hazards += ["scaffali instabili", "pergamene infiammabili"]
    elif any(w in blob for w in ["bosco", "foresta", "radura", "giardino"]):
        features += ["tronchi caduti", "rocce muschiose", "radici affioranti", "cespugli fitti"]
        hazards += ["rovi come terreno difficile", "nebbia tra gli alberi"]
    elif any(w in blob for w in ["castello", "fortezza", "torre", "cortile", "bastione"]):
        features += ["muretti merlati", "scale di pietra", "portoni ferrati", "alcove difensive"]
        hazards += ["feritoie sorvegliate", "pietre sconnesse"]
    elif any(w in blob for w in ["cripta", "catacomb", "tomba", "sepol", "necrop", "sarcof"]):
        features += ["sarcofagi di pietra", "colonne spezzate", "altare incrinato", "bracieri rovesciati"]
        hazards += ["pietre instabili", "rune che si accendono a impulsi"]
    elif any(w in blob for w in ["sacrario", "altare", "ritual"]):
        features += ["altare centrale", "cerchi rituali", "pilastri bassi", "bracieri rovesciati"]
        hazards += ["rune che si accendono a impulsi", "energia instabile"]
    if any(w in blob for w in ["laboratorio", "reattore", "terminal", "ponte di comando"]):
        features += ["console tecniche", "paratie e coperture basse"]
    if any(w in blob for w in ["rovine", "crollo", "macerie", "frana"]):
        hazards += ["macerie e terreno difficile"]
    if any(w in blob for w in ["acqua", "marea", "palude", "sommers", "fiume"]):
        hazards += ["acqua o fango come terreno difficile"]
    if not features:
        features = ["coperture coerenti con la location", "vie di ingresso/uscita leggibili"]
    trigger = "quando la scena porta a uno scontro diretto in questa zona"
    if role == "finale":
        trigger = "quando il gruppo affronta antagonista, guardiani o minaccia finale"
    return {
        "enabled": True,
        "role": role,
        "name": name,
        "layout": layout,
        "cols": cols,
        "rows": rows,
        "features": features[:4],
        "hazards": hazards[:3],
        "entry_zones": ["lato ovest / ingresso del gruppo"],
        "enemy_zones": ["lato est / punto difeso"],
        "trigger": trigger,
        "victory_condition": "neutralizzare, mettere in fuga o superare gli avversari presenti",
    }


def _location_wants_tactical_map(location: dict) -> bool:
    if not isinstance(location, dict):
        return False
    tactical = location.get("tactical_map") if isinstance(location.get("tactical_map"), dict) else {}
    role = str(tactical.get("role") or location.get("tactical_role") or "").lower()
    trigger = str(tactical.get("trigger") or location.get("trigger") or location.get("description") or "").lower()
    if location.get("has_combat_potential") or role in {"hot_zone", "finale", "boss", "combat"}:
        return True
    return any(w in trigger for w in ["scontro", "combatt", "agguato", "confronto", "assalto", "fuga sotto pressione"])


def _normalize_adventure_canon(adventure: dict, source: str = "generated") -> dict:
    """Rende tracciabile una bibbia senza affidarsi a runtime thread liberi."""
    if not isinstance(adventure, dict):
        return adventure

    clues = list(adventure.get("clues") or [])[:8]
    npcs = list(adventure.get("npcs") or [])[:8]
    locations = list(adventure.get("locations") or [])[:6]
    genre = adventure.get("detected_genre") or adventure.get("genre") or adventure.get("environment_type") or ""
    title = adventure.get("title", "avventura")
    hidden_truth = adventure.get("hidden_truth", "")
    win_condition = adventure.get("win_condition", "")

    existing_threads = [t for t in (adventure.get("story_threads") or adventure.get("structured_threads") or []) if isinstance(t, dict)]
    thread_templates = [
        ("T1", "Dove si trova la prova decisiva?", "Localizzare il luogo o l'oggetto che rende giocabile la soluzione finale."),
        ("T2", "Chi sta muovendo davvero la minaccia?", "Identificare antagonista, complice o pressione centrale senza inventare nuovi filoni."),
        ("T3", "Come si chiude l'avventura senza peggiorare il costo?", "Capire procedura, vincolo o condizione finale della risoluzione."),
    ]
    valid_thread_ids = {
        str(t.get("id") or "").strip()
        for t in existing_threads
        if str(t.get("id") or "").strip()
    } or {tid for tid, _, _ in thread_templates}

    enriched_clues = []
    for idx, raw in enumerate(clues, start=1):
        if not isinstance(raw, dict):
            raw = {"text": str(raw)}
        cid = str(raw.get("id") or f"clue_{idx}")
        text = _clean_canon_text(raw.get("text") or raw.get("label") or raw.get("reveals") or f"Indizio {idx}", limit=220)
        reveals = _clean_canon_text(raw.get("reveals") or text, limit=220)
        location = _clean_canon_text(raw.get("location") or raw.get("source_location") or "", limit=120)
        thread_id = str(raw.get("thread_id") or thread_templates[(idx - 1) % len(thread_templates)][0])
        if thread_id not in valid_thread_ids:
            thread_id = thread_templates[(idx - 1) % len(thread_templates)][0]
        payoff = _clean_canon_text(raw.get("payoff") or reveals or f"Avanza la pista {thread_id}.", limit=220)
        enriched_clues.append({
            **raw,
            "id": cid,
            "label": _clean_canon_text(raw.get("label") or text, limit=120),
            "text": text,
            "type": raw.get("type") or _infer_clue_type(text, location),
            "thread_id": thread_id,
            "source_location": location,
            "location": location,
            "reveals": reveals,
            "payoff": payoff,
            "is_required": bool(raw.get("is_required", True)),
            "is_discovered": bool(raw.get("found") or raw.get("is_discovered", False)),
            "found": bool(raw.get("found") or raw.get("is_discovered", False)),
        })

    def _thread_is_generic(question: str, payoff: str = "") -> bool:
        text = f"{question} {payoff}".lower()
        generic_bits = [
            "prova decisiva", "muovendo davvero", "chiudere l'avventura",
            "senza peggiorare", "procedura, vincolo", "soluzione finale",
            "pezzo della soluzione", "identificare antagonista",
            "quale fatto concreto", "cambia la scelta dei giocatori",
            "quale leva della struttura", "ritual_countdown",
        ]
        return _looks_generic(question) or any(bit in text for bit in generic_bits)

    def _concrete_thread_question(tid: str, linked: list[dict], fallback_idx: int) -> str:
        clue = linked[0] if linked else {}
        subject = _clean_canon_text(
            clue.get("reveals") or clue.get("label") or clue.get("text") or "",
            limit=70,
        )
        place = _clean_canon_text(
            clue.get("location") or (locations[fallback_idx % len(locations)].get("name") if locations and isinstance(locations[fallback_idx % len(locations)], dict) else ""),
            limit=60,
        )
        npc = _clean_canon_text(
            (npcs[fallback_idx % len(npcs)].get("name") if npcs and isinstance(npcs[fallback_idx % len(npcs)], dict) else ""),
            limit=60,
        )
        if tid == "T1" and place:
            return f"Cosa si scopre davvero in {place}?"
        if tid == "T2" and npc:
            return f"Che ruolo ha {npc} nella minaccia?"
        if tid == "T3" and subject:
            return f"Come usare {subject[:46]}?"
        if subject:
            return f"Cosa rivela {subject[:52]}?"
        return thread_templates[fallback_idx % len(thread_templates)][1]

    def _concrete_thread_payoff(tid: str, linked: list[dict], fallback_payoff: str) -> str:
        clue_payoffs = [c.get("payoff") for c in linked if c.get("payoff")]
        if clue_payoffs:
            return _clean_canon_text(" / ".join(clue_payoffs[:2]), limit=220)
        if tid == "T1":
            return "sblocca una location, un accesso o una prova concreta gia prevista dal canovaccio"
        if tid == "T2":
            return "chiarisce chi ostacola la squadra e come puo essere fermato o aggirato"
        if tid == "T3":
            return "rende praticabile la scelta finale senza introdurre una nuova rivelazione improvvisa"
        return fallback_payoff

    threads = []
    source_threads = existing_threads or [
        {"id": tid, "question": question, "payoff": fallback_payoff}
        for tid, question, fallback_payoff in thread_templates
    ]
    for fallback_idx, raw_thread in enumerate(source_threads):
        tid = str(raw_thread.get("id") or thread_templates[fallback_idx % len(thread_templates)][0])
        fallback_question = thread_templates[fallback_idx % len(thread_templates)][1]
        fallback_payoff = thread_templates[fallback_idx % len(thread_templates)][2]
        linked = [c for c in enriched_clues if c.get("thread_id") == tid]
        if not linked and enriched_clues:
            linked = enriched_clues[fallback_idx:fallback_idx + 1] or enriched_clues[:1]
            for c in linked:
                c["thread_id"] = tid
        explicit_required = [str(x) for x in (raw_thread.get("required_clues") or []) if str(x)]
        required_ids = explicit_required or [c["id"] for c in linked[:3]]
        minimum = min(2, max(1, len(required_ids))) if required_ids else 1
        question = _clean_canon_text(raw_thread.get("question") or raw_thread.get("title") or fallback_question, limit=180)
        payoff = _clean_canon_text(raw_thread.get("payoff") or raw_thread.get("purpose") or fallback_payoff, limit=220)
        if _thread_is_generic(question, payoff):
            question = _concrete_thread_question(tid, linked, fallback_idx)
            payoff = _concrete_thread_payoff(tid, linked, fallback_payoff)
        answer_bits = [c.get("reveals") or c.get("text") for c in linked[:2] if c.get("reveals") or c.get("text")]
        true_answer = raw_thread.get("true_answer") or raw_thread.get("answer") or " ".join(answer_bits) or (hidden_truth if tid == "T2" else win_condition) or fallback_payoff
        if _thread_is_generic(str(true_answer), "") or str(true_answer).strip().lower() == question.strip().lower():
            true_answer = " ".join(answer_bits) or (hidden_truth if tid == "T2" else win_condition) or _concrete_thread_payoff(tid, linked, fallback_payoff)
        threads.append({
            "id": tid,
            "title": _clean_canon_text(raw_thread.get("title") or question.replace("?", ""), limit=120),
            "question": question,
            "true_answer": _clean_canon_text(true_answer, limit=260),
            "status": raw_thread.get("status") if raw_thread.get("status") in {"hidden", "active", "ready_to_deduce", "resolved", "failed"} else "hidden",
            "required_clues": required_ids,
            "discovered_clues": list(raw_thread.get("discovered_clues") or []),
            "partial_clues": list(raw_thread.get("partial_clues") or []),
            "minimum_clues_to_deduce": minimum,
            "payoff": payoff,
            "linked_npcs": list(raw_thread.get("linked_npcs") or [n.get("id") or n.get("name") for n in npcs[:3] if isinstance(n, dict)]),
            "linked_locations": list(raw_thread.get("linked_locations") or [l.get("id") or l.get("name") for l in locations[:3] if isinstance(l, dict)]),
        })

    antagonist = next((n for n in npcs if isinstance(n, dict) and any(w in str(n.get("role", "")).lower() for w in ["antagon", "villain", "nemic", "cult", "assassin", "killer"])), None)
    required_clues = [c["id"] for c in enriched_clues if c.get("is_required")]
    hot_location_indexes = {
        i for i, loc in enumerate(locations)
        if isinstance(loc, dict) and _location_wants_tactical_map(loc)
    }
    if locations:
        hot_location_indexes.add(len(locations) - 1)
    if antagonist and locations:
        ant_loc = str(antagonist.get("location") or "").lower()
        for i, loc in enumerate(locations):
            if isinstance(loc, dict) and ant_loc and (ant_loc in str(loc.get("name", "")).lower() or str(loc.get("name", "")).lower() in ant_loc):
                hot_location_indexes.add(i)
    enriched_locations = []
    for i, loc in enumerate(locations):
        if not isinstance(loc, dict):
            continue
        role = "finale" if i == len(locations) - 1 else "hot_zone"
        loc = dict(loc)
        if i in hot_location_indexes:
            loc["has_combat_potential"] = True
            existing_tactical = loc.get("tactical_map") if isinstance(loc.get("tactical_map"), dict) else {}
            base_tactical = _build_tactical_map_spec(loc, role=existing_tactical.get("role") or role, genre=genre)
            loc["tactical_map"] = {
                **existing_tactical,
                **base_tactical,
                "trigger": existing_tactical.get("trigger") or base_tactical.get("trigger"),
                "enabled": True,
            }
        elif isinstance(loc.get("tactical_map"), dict):
            loc["tactical_map"] = {**loc["tactical_map"], "enabled": False}
        enriched_locations.append(loc)
    locations = enriched_locations
    adventure["clues"] = enriched_clues
    adventure["locations"] = locations
    adventure["story_threads"] = threads
    existing_canon = adventure.get("adventure_canon") if isinstance(adventure.get("adventure_canon"), dict) else {}
    adventure["adventure_canon"] = {
        "core_truth": existing_canon.get("core_truth") or hidden_truth,
        "main_antagonist": existing_canon.get("main_antagonist") or (antagonist or {}).get("name", ""),
        "false_leads": list(existing_canon.get("false_leads") or [t.get("description", "") for t in (adventure.get("twists") or [])[:2] if isinstance(t, dict)]),
        "key_locations": list(existing_canon.get("key_locations") or [l.get("name", "") for l in locations if isinstance(l, dict)][:5]),
        "tactical_locations": [
            {
                "location_id": l.get("id") or l.get("name"),
                "name": l.get("name"),
                "role": (l.get("tactical_map") or {}).get("role", "hot_zone"),
                "trigger": (l.get("tactical_map") or {}).get("trigger", ""),
            }
            for l in locations
            if isinstance(l, dict) and (l.get("tactical_map") or {}).get("enabled")
        ],
        "required_clues": list(existing_canon.get("required_clues") or required_clues),
        "optional_events": list(existing_canon.get("optional_events") or [t.get("trigger", "") for t in (adventure.get("twists") or [])[:3] if isinstance(t, dict)]),
        "finale_conditions": list(existing_canon.get("finale_conditions") or ([win_condition] if win_condition else [])),
        "source": source,
    }

    for npc in npcs:
        if not isinstance(npc, dict):
            continue
        role_text = str(npc.get("role", "")).lower()
        role = "neutral"
        if any(w in role_text for w in ["antagon", "nemic", "killer", "assassin", "cult"]):
            role = "antagonist"
        elif any(w in role_text for w in ["alleat", "ally", "aiut"]):
            role = "ally"
        elif any(w in role_text for w in ["testim", "witness", "vittima"]):
            role = "witness"
        npc.setdefault("npc_role_weight", "high" if role in {"antagonist", "witness"} else "medium")
        npc.setdefault("npc_agenda", {
            "npc_id": npc.get("id") or _canon_slug(npc.get("name", ""), "npc"),
            "role": role,
            "secret": npc.get("secret", ""),
            "goal": npc.get("motivation") or npc.get("description") or "proteggere il proprio ruolo nel modulo",
            "methods": [],
            "recurrence_priority": "high" if role in {"antagonist", "witness"} else "medium",
            "arc_status": "unintroduced",
        })

    return adventure


def _normalize_pdf_adventure_canon(adventure: dict) -> dict:
    return _normalize_adventure_canon(adventure, source="pdf_import")


def _fallback_pdf_adventure(pdf_text: str, genre: str, players: list[dict], reason: str = "") -> dict:
    """Fallback locale quando i provider rifiutano: crea una bibbia giocabile minimale senza nuove chiamate AI."""
    lines = [re.sub(r"\s+", " ", l).strip() for l in (pdf_text or "").splitlines()]
    lines = [l for l in lines if len(l) >= 4]
    title = next((l for l in lines[:30] if 6 <= len(l) <= 90), "Avventura importata")
    title = _clean_canon_text(title, limit=90)
    capitalized = []
    for line in lines[:600]:
        if len(line) > 80:
            continue
        if re.search(r"\b(?:sala|cripta|torre|cella|biblioteca|laboratorio|ponte|camera|tempio|cappella|villaggio|stazione|hangar|archivio)\b", line.lower()):
            capitalized.append(_clean_canon_text(line, limit=80))
        elif line[:1].isupper() and sum(ch.isupper() for ch in line[:24]) >= 2:
            capitalized.append(_clean_canon_text(line, limit=80))
    location_names = []
    for name in capitalized:
        if name.lower() not in {x.lower() for x in location_names}:
            location_names.append(name)
        if len(location_names) >= 5:
            break
    if len(location_names) < 3:
        location_names = ["Ingresso del modulo", "Luogo degli indizi", "Zona calda", "Confronto finale"]

    npc_names = []
    for line in lines[:600]:
        for m in re.finditer(r"\b([A-Z][a-zàèéìòù]+(?:\s+[A-Z][a-zàèéìòù]+){0,2})\b", line):
            name = m.group(1).strip()
            if name.lower() in {"Il", "La", "Gli", "Le", "Un", "Una", "Nel", "Nella"}:
                continue
            if 3 <= len(name) <= 40 and name.lower() not in {x.lower() for x in npc_names}:
                npc_names.append(name)
            if len(npc_names) >= 4:
                break
        if len(npc_names) >= 4:
            break
    if not npc_names:
        npc_names = ["Testimone principale", "Antagonista del modulo", "Custode degli indizi"]

    clue_sources = location_names[:3]
    adventure = {
        "title": title,
        "detected_genre": genre if genre != "auto" else "mystery_horror",
        "premise": f"Il gruppo entra nello scenario di {title} con una minaccia gia in movimento e pochi elementi affidabili da verificare.",
        "hidden_truth": "La verita del modulo e gia contenuta nel testo importato: il Master deve rivelarla tramite prove concrete, non tramite nuovi misteri improvvisati.",
        "atmosphere": "Tensione investigativa e confronto progressivo, senza dettagli grafici.",
        "win_condition": "Ricostruire la verita centrale tramite gli indizi canonici e superare il confronto finale.",
        "threat_description": "La pressione della situazione aumenta finche il gruppo non collega prove, luoghi e antagonista.",
        "threat_max_turns": 10,
        "has_time_pressure": True,
        "npcs": [
            {
                "id": f"npc_{i}",
                "name": name,
                "role": "antagonista" if i == 2 else ("testimone" if i == 1 else "neutrale"),
                "description": "Figura rilevante estratta dal testo importato.",
                "attitude": "suspicious" if i == 2 else "neutral",
                "status": "alive",
                "location": location_names[min(i - 1, len(location_names) - 1)],
                "secret": "Conosce o protegge una parte della verita centrale.",
            }
            for i, name in enumerate(npc_names[:4], start=1)
        ],
        "clues": [
            {
                "id": f"clue_{i}",
                "label": f"Prova {i}",
                "text": f"Elemento concreto da verificare in {src}",
                "type": ["location_detail", "testimony", "physical_evidence"][min(i - 1, 2)],
                "thread_id": ["T1", "T2", "T3"][min(i - 1, 2)],
                "reveals": ["dove cercare la prova decisiva", "chi controlla la minaccia", "come arrivare alla risoluzione"][min(i - 1, 2)],
                "payoff": ["orienta la mappa strategica", "identifica il nodo antagonista", "sblocca il finale coerente"][min(i - 1, 2)],
                "location": src,
                "found": False,
            }
            for i, src in enumerate(clue_sources, start=1)
        ],
        "twists": [],
        "locations": [
            {
                "id": f"loc_{i}",
                "name": name,
                "description": "Location importata dal modulo e usata come nodo strategico.",
                "has_combat_potential": i == len(location_names) or i >= max(3, len(location_names) - 1),
            }
            for i, name in enumerate(location_names[:5], start=1)
        ],
        "from_pdf": True,
        "fallback_used": True,
        "fallback_reason": reason,
    }
    return _normalize_pdf_adventure_canon(adventure)


def _validate_master_state_updates(
    updates: dict,
    *,
    adventure: dict,
    game_state_data: dict,
    prerolled: dict | None = None,
    director_decision: dict | None = None,
    narrative_text: str = "",
) -> dict:
    """Filtro deterministico: il Master narra, ma lo stato resta nel canovaccio."""
    su = dict(updates or {})
    blocked_updates: list[str] = []
    all_clues = [c for c in (adventure.get("clues") or []) if isinstance(c, dict)]
    story_threads = [t for t in (adventure.get("story_threads") or []) if isinstance(t, dict)]
    locations = [l for l in (adventure.get("locations") or []) if isinstance(l, dict)]
    objectives = [o for o in (adventure.get("objectives") or adventure.get("objective_stack") or []) if isinstance(o, dict)]
    factions = [f for f in (adventure.get("factions") or []) if isinstance(f, dict)]
    finale_conditions = [f for f in (adventure.get("finale_conditions") or []) if isinstance(f, dict)]
    valid_clue_ids = {str(c.get("id")) for c in all_clues if c.get("id")}
    valid_thread_ids = {str(t.get("id")) for t in story_threads if t.get("id")}
    clues_by_id = {str(c.get("id")): c for c in all_clues if c.get("id")}
    valid_location_ids = {str(l.get("id")) for l in locations if l.get("id")}
    valid_location_names = {str(l.get("name")).lower(): str(l.get("id") or l.get("name")) for l in locations if l.get("name")}
    valid_objective_ids = {str(o.get("id")) for o in objectives if o.get("id")}
    valid_faction_ids = {str(f.get("id")) for f in factions if f.get("id")}
    valid_finale_ids = {str(f.get("id")) for f in finale_conditions if f.get("id")}
    clues_found_ids = set(str(x) for x in (game_state_data.get("clues_found") or []))
    allow_runtime_threads = bool((adventure.get("adventure_canon") or {}).get("allow_runtime_threads") or adventure.get("allow_runtime_threads"))

    # Ogni clue deve puntare a un thread valido. I clue invalidi non entrano negli update.
    valid_clue_ids = {
        cid for cid in valid_clue_ids
        if str(clues_by_id[cid].get("thread_id") or "") in valid_thread_ids
    }

    valid_progress = []
    for item in su.get("clue_progress", []) or []:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("clue_id") or item.get("id") or "")
        if cid not in valid_clue_ids or cid in clues_found_ids:
            continue
        note = _clean_canon_text(item.get("note") or item.get("text") or "", limit=180)
        if not note:
            note = "La squadra si avvicina a questo indizio canonico."
        valid_progress.append({"clue_id": cid, "note": note, "ticks": 1})
    su["clue_progress"] = valid_progress[:2]

    found_now = []
    for cid in su.get("clues_found", []) or su.get("discovered_clue_ids", []) or []:
        cid = str(cid)
        if cid in valid_clue_ids and cid not in clues_found_ids and cid not in found_now:
            found_now.append(cid)
    su["clues_found"] = found_now[:2]
    su["discovered_clues"] = [
        {
            "id": c.get("id"),
            "label": c.get("label") or c.get("text"),
            "thread_id": c.get("thread_id", ""),
            "type": c.get("type", ""),
            "source_location": c.get("source_location") or c.get("location", ""),
            "reveals": c.get("reveals", ""),
            "payoff": c.get("payoff", ""),
        }
        for c in all_clues
        if str(c.get("id")) in su["clues_found"]
    ]

    facts = []
    for fact in su.get("discovered_facts", []) or []:
        if isinstance(fact, str):
            text = _clean_canon_text(fact, limit=220)
            if text:
                facts.append(text)
        elif isinstance(fact, dict):
            text = _clean_canon_text(fact.get("text") or fact.get("fact") or "", limit=220)
            if text:
                facts.append(text)
    su["discovered_facts"] = facts[:2]

    closed = []
    for raw in (su.get("closed_threads", []) or []) + (su.get("thread_resolved", []) or []):
        if isinstance(raw, dict):
            tid = str(raw.get("id") or raw.get("thread_id") or "")
            text = _clean_canon_text(raw.get("deduction") or raw.get("text") or "", limit=220)
            if tid in valid_thread_ids:
                closed.append(f"{tid} → {text}" if text else tid)
        elif isinstance(raw, str):
            token = raw.split("→", 1)[0].strip()
            if token in valid_thread_ids or any(token in (t.get("question") or "") for t in story_threads):
                closed.append(_clean_canon_text(raw, limit=260))
    su["closed_threads"] = closed[:2]
    su["thread_resolved"] = su["closed_threads"]

    npc_ids = {str(n.get("id")) for n in (adventure.get("npcs") or []) if isinstance(n, dict) and n.get("id")}
    valid_npc_updates = []
    for item in su.get("npc_updates", []) or []:
        if not isinstance(item, dict):
            continue
        nid = str(item.get("id") or item.get("npc_id") or "")
        if npc_ids and nid not in npc_ids:
            continue
        valid_npc_updates.append({k: v for k, v in item.items() if k in {"id", "npc_id", "status", "attitude", "location", "arc_status", "note"}})
    su["npc_updates"] = valid_npc_updates[:4]

    def _valid_status(value: str, allowed: set[str]) -> str:
        value = str(value or "").strip()
        return value if value in allowed else ""

    valid_location_updates = []
    for item in su.get("location_updates", []) or []:
        if not isinstance(item, dict):
            continue
        lid = str(item.get("id") or item.get("location_id") or item.get("node_id") or "").strip()
        if not lid and item.get("name"):
            lid = valid_location_names.get(str(item.get("name")).lower(), "")
        if valid_location_ids and lid not in valid_location_ids:
            continue
        update = {"id": lid}
        status = _valid_status(item.get("status"), {"hidden", "unknown", "known", "visited", "locked", "changed", "compromised", "secured", "destroyed"})
        access_state = _valid_status(item.get("access_state"), {"open", "locked", "hidden", "blocked", "restricted", "unlocked", "sealed"})
        if status:
            update["status"] = status
        if access_state:
            update["access_state"] = access_state
        if len(update) > 1:
            valid_location_updates.append(update)
    su["location_updates"] = valid_location_updates[:3]

    valid_objective_updates = []
    for item in su.get("objective_updates", []) or []:
        if not isinstance(item, dict):
            continue
        oid = str(item.get("id") or item.get("objective_id") or "").strip()
        if valid_objective_ids and oid not in valid_objective_ids:
            continue
        status = _valid_status(item.get("status"), {"hidden", "inactive", "available", "active", "complete", "completed", "failed"})
        if oid and status:
            valid_objective_updates.append({"id": oid, "status": status})
    su["objective_updates"] = valid_objective_updates[:2]

    valid_faction_updates = []
    for item in su.get("faction_updates", []) or []:
        if not isinstance(item, dict):
            continue
        fid = str(item.get("id") or item.get("faction_id") or "").strip()
        if valid_faction_ids and fid not in valid_faction_ids:
            continue
        update = {"id": fid}
        status = _valid_status(item.get("status"), {"quiet", "watching", "active", "escalating", "dominant", "weakened", "broken"})
        if status:
            update["status"] = status
        if item.get("pressure") is not None:
            try:
                update["pressure"] = max(0, min(10, int(item.get("pressure") or 0)))
            except Exception:
                pass
        if fid and len(update) > 1:
            valid_faction_updates.append(update)
    su["faction_updates"] = valid_faction_updates[:3]

    valid_finale_updates = []
    for item in su.get("finale_updates", []) or []:
        if not isinstance(item, dict):
            continue
        fid = str(item.get("id") or item.get("finale_id") or "").strip()
        if valid_finale_ids and fid not in valid_finale_ids:
            continue
        status = _valid_status(item.get("status"), {"locked", "seeded", "available", "satisfied", "failed"})
        if fid and status:
            valid_finale_updates.append({"id": fid, "status": status})
    su["finale_updates"] = valid_finale_updates[:2]

    for numeric_key in ("clock_updates", "pressure_updates", "resource_updates"):
        cleaned = []
        for item in su.get(numeric_key, []) or []:
            if not isinstance(item, dict):
                continue
            uid = str(item.get("id") or item.get("clock_id") or item.get("pressure_id") or item.get("resource_id") or "").strip()
            if not uid:
                continue
            update = {"id": uid}
            for k in ("value", "delta"):
                if item.get(k) is not None:
                    try:
                        update[k] = max(-10, min(20, int(item.get(k) or 0)))
                    except Exception:
                        pass
            if item.get("active") is not None:
                update["active"] = bool(item.get("active"))
            if len(update) > 1:
                cleaned.append(update)
        su[numeric_key] = cleaned[:3]

    if not isinstance(su.get("flags"), dict):
        su["flags"] = {}
    else:
        su["flags"] = {
            _clean_canon_text(k, limit=60): _clean_canon_text(v, limit=180) if isinstance(v, str) else v
            for k, v in list(su["flags"].items())[:6]
            if _clean_canon_text(k, limit=60)
        }

    su["new_threads"] = su.get("new_threads", []) if allow_runtime_threads else []
    if allow_runtime_threads:
        su["new_threads"] = [str(t).strip() for t in su["new_threads"][:1] if str(t).strip()]

    try:
        # Cap globale: max 1 per turno normale. Solo clock/finale autorizzati possono dare 2+.
        su["threat_increase"] = max(0, min(1, int(su.get("threat_increase", 0) or 0)))
    except Exception:
        su["threat_increase"] = 0
    for key in ["activate_combat", "combat_over", "story_over", "victory"]:
        su[key] = bool(su.get(key, False))
    if "combat_scene" not in su:
        su["combat_scene"] = None
    if "location_access" in su and not isinstance(su["location_access"], list):
        su["location_access"] = []
    if "objective_progress" in su:
        try:
            su["objective_progress"] = max(0, min(3, int(su["objective_progress"])))
        except Exception:
            su["objective_progress"] = 0

    resolved_before = game_state_data.get("resolved_threads") or game_state_data.get("closed_threads") or []
    finale_conditions = (adventure.get("adventure_canon") or {}).get("finale_conditions") or []
    try:
        threat_now = int(game_state_data.get("threat_level", 0) or 0)
        threat_max = max(12, int(game_state_data.get("threat_max", 12) or 12))  # minimo 12 turni
    except Exception:
        threat_now, threat_max = 0, 12
    # Conta turni giocati come proxy di progressione
    turns_played = int(game_state_data.get("turns_played", 0) or 0)
    explicit_trigger = bool(
        su.get("explicit_trigger")
        or su.get("finale_condition_met")
        or game_state_data.get("finale_condition_met")
        or game_state_data.get("objective_complete")
    )
    has_finale_basis = bool(
        explicit_trigger
        or resolved_before
        or su["closed_threads"]
        or (threat_max > 0 and threat_now >= threat_max)
    )
    # Blocco minimo 6 turni prima che l'avventura possa finire
    _MIN_TURNS_BEFORE_ENDING = 6
    if su["story_over"] and turns_played < _MIN_TURNS_BEFORE_ENDING:
        su["story_over"] = False
        su["victory"] = False
        su["threat_increase"] = min(su["threat_increase"], 1)
        su.setdefault("validation_notes", []).append(f"fine avventura bloccata: turni giocati {turns_played} < {_MIN_TURNS_BEFORE_ENDING}")
        blocked_updates.append("story_over_too_early")
    if su["story_over"] and su.get("victory") and finale_conditions and not has_finale_basis:
        su["story_over"] = False
        su["victory"] = False
        su["threat_increase"] = max(su["threat_increase"], 1)
        su.setdefault("validation_notes", []).append("finale bloccato: manca una deduzione risolta o una condizione finale soddisfatta")
        blocked_updates.append("finale")

    major_aliases = {
        "finale", "morte gruppo", "group_death", "death_group", "tpk",
        "boss release", "boss_release", "apocalisse", "apocalypse",
        "distruzione luogo", "location_destroyed", "destroy_location",
        "rivelazione finale", "final_revelation",
    }
    raw_major = su.get("major_event") or su.get("major_events") or []
    if isinstance(raw_major, str):
        major_events = [raw_major]
    elif isinstance(raw_major, list):
        major_events = [str(x) for x in raw_major if str(x).strip()]
    elif isinstance(raw_major, dict):
        major_events = [str(raw_major.get("type") or raw_major.get("event") or "major_event")]
    else:
        major_events = []
    def _norm_major(value: str) -> str:
        return value.strip().lower().replace("-", "_").replace(" ", "_")

    normalized_major = {_norm_major(m) for m in major_events}
    has_major_event = bool(normalized_major & {_norm_major(m) for m in major_aliases})

    roll_intent = str((prerolled or {}).get("intent") or ((prerolled or {}).get("intent_classification") or {}).get("intent") or "").lower()
    passive_action = bool((prerolled or {}).get("non_combat_action")) or roll_intent in {
        "investigation", "observation", "technical", "medical", "social", "stealth", "survival", "generic"
    }
    terminal_requested = bool(su.get("story_over") or su.get("victory") or has_major_event)
    major_authorized = explicit_trigger or has_finale_basis
    if (has_major_event or terminal_requested) and not major_authorized:
        if su.get("story_over"):
            blocked_updates.append("story_over")
        if su.get("victory"):
            blocked_updates.append("victory")
        blocked_updates.extend(major_events or ["major_event"])
        su["story_over"] = False
        su["victory"] = False
        su["major_event"] = None
        su["major_events"] = []
        su["threat_increase"] = min(su["threat_increase"], 1)
        su.setdefault("validation_notes", []).append("evento maggiore bloccato: manca explicit_trigger o finale_condition")

    if passive_action and not major_authorized:
        passive_blocked = []
        for key in ("story_over", "victory"):
            if su.get(key):
                passive_blocked.append(key)
                su[key] = False
        if has_major_event:
            passive_blocked.extend(major_events or ["major_event"])
            su["major_event"] = None
            su["major_events"] = []
        if passive_blocked:
            blocked_updates.extend(passive_blocked)
            su["threat_increase"] = min(su["threat_increase"], 1)
            su.setdefault("validation_notes", []).append("evento terminale bloccato: azione passiva/non combattiva")

    persistent_keys = [
        "clue_progress", "clues_found", "discovered_facts", "npc_updates",
        "closed_threads", "threat_increase", "location_access", "objective_progress",
        "location_updates", "objective_updates", "faction_updates", "clock_updates",
        "pressure_updates", "resource_updates", "finale_updates", "flags",
        "activate_combat", "combat_over", "story_over",
    ]
    if not any(su.get(k) for k in persistent_keys):
        if prerolled and prerolled.get("success") and valid_clue_ids:
            candidate = next((cid for cid in valid_clue_ids if cid not in clues_found_ids), None)
            if candidate:
                su["clue_progress"] = [{"clue_id": candidate, "note": "Il successo produce un avanzamento concreto verso una prova canonica.", "ticks": 1}]
        else:
            su["threat_increase"] = 1
    if blocked_updates:
        su["blocked_state_updates"] = sorted({str(x) for x in blocked_updates if str(x).strip()})
        su["needs_alternative_narration"] = True
        su["narration_constraints"] = (
            "Riscrivi l'esito senza finale, morte gruppo, boss release, apocalisse, distruzione luogo "
            "o rivelazione finale: l'azione produce solo progresso parziale, costo locale o pressione."
        )
    if director_decision:
        su = validate_ai_state_updates(
            su,
            director_decision=director_decision,
            genre_profile=director_decision.get("genre_profile"),
            prerolled=prerolled,
            narrative_text=narrative_text,
            finale_condition_met=bool(game_state_data.get("finale_condition_met") or game_state_data.get("objective_complete")),
        )
    return su


def compile_adventure_to_runtime(
    content: str,
    genre_hint: str | None = None,
    runtime_profile_hint: str | None = None,
    source_type: str = "raw_text",
    title: str = "",
) -> dict:
    """Adventure Compiler: estrae JSON simulabile, valida e inizializza runtime state."""
    content = content or ""
    if source_type == "pdf_text":
        content = content[:PDF_COMPILER_MAX_INPUT_CHARS]
    else:
        content = content[:50000]
    if source_type == "pdf_text":
        structure = extract_pdf_structure(content)
        counts = structure.get("counts") or {}
        def _mark_pdf_output(data: dict) -> dict:
            data = dict(data or {})
            data["source_mode"] = "pdf_import"
            for key in ("clues", "actors", "npcs", "locations", "event_clocks", "finale_conditions", "revelations", "story_threads"):
                items = data.get(key)
                if not isinstance(items, list):
                    continue
                next_items = []
                for item in items:
                    if not isinstance(item, dict):
                        next_items.append(item)
                        continue
                    item = dict(item)
                    item.setdefault("source_status", "inferred")
                    if key in {"clues", "actors", "npcs", "locations"}:
                        item.setdefault("is_preserved_from_pdf", True)
                    next_items.append(item)
                data[key] = next_items
            return data

        pdf_prompt = f"""You are an adventure module compiler for a state-driven RPG engine.
Return ONLY valid JSON. Do not summarize the source; convert it into playable runtime canon.
LANGUAGE POLICY: all player-facing natural language fields MUST be in Italian, even if the PDF/source is English. Preserve proper names, places and canonical labels, but translate/destructure premise, initial_hook, objectives, revelations, clue text, NPC goals, clock consequences, finale methods and suggestions into fluent Italian.

SOURCE TYPE: PDF MODULE IMPORT
TITLE HINT: {title}
	GENRE HINT: {genre_hint or ""}
	RUNTIME PROFILE HINT: {runtime_profile_hint or ""}
	EXTRACTED STRUCTURE COUNTS: {json.dumps(counts, ensure_ascii=False)}
	FIDELITY TARGET: preserve at least 85-90% of the playable adventure content visible in the provided text.
	MINIMUM DENSITY TARGETS:
	- If rooms/sections/locations are visible, produce multiple locations, not a single generic starting area.
	- If named NPCs, factions, monsters or witnesses are visible, produce actors for the important ones.
	- If clues, secrets or revelations are visible, produce linked clues and revelations; never leave clues unlinked.
	- For long modules, simplify wording but preserve the adventure graph: premise, route/locations, actors, clues, clocks, encounters, finale.

PDF IMPORT RULES
- Read and interpret the module as an adventure, not as generic prose.
- Produce an opening premise with 3-5 vivid Italian sentences: where the PCs are, why they are there, what immediate pressure exists, and what concrete first choice is visible.
- Preserve named rooms, NPCs, clues, factions, maps, encounters and finale conditions when present.
- Do not invent unrelated mysteries, factions, symbols or villains.
- If the PDF contains rules text mixed with adventure text, ignore rules-only passages unless they define encounters or playable procedures.
- Convert implicit adventure logic into explicit runtime fields: objectives, revelations/story threads, clues, actors, locations, clocks, finale conditions.
- Every clue must be concrete, located, and linked to a thread/revelation.
- Every important NPC must have goal, secret/knowledge if present, current_plan and pressure_response.
- Every hot/finale location should include a tactical_map; neutral/social locations should not.
- The win condition must explain how the players can complete the module.
- Mark preserved source elements with source_status="explicit" and is_preserved_from_pdf=true when taken from the text.
- Put uncertain repairs in suggestions, not in hidden truth.

OUTPUT JSON SHAPE:
{{
  "source_mode": "pdf_import",
  "id": "stable_id",
  "title": "module title, translated only if it is not a proper title",
  "genre": "genre",
  "runtime_profiles": ["investigation_graph"],
  "tone": "tone",
  "premise": "situazione iniziale giocabile in italiano, 3-5 frasi vivide",
  "initial_hook": "apertura in medias res in italiano, non generica",
  "hidden_truth": "verita centrale in italiano se presente, altrimenti premessa centrale del modulo",
  "core_truths": [{{"id":"truth_1","statement":"truth","reveal_clues":["clue_1"],"reveal_rule":"when..."}}],
  "objectives": [{{"id":"obj_1","label":"clear win objective","success_conditions":["condition"]}}],
  "story_threads": [{{"id":"T1","title":"thread title","question":"player-facing mystery question","true_answer":"canonical answer","status":"hidden","required_clues":["clue_1"],"minimum_clues_to_deduce":2,"payoff":"what it unlocks","linked_npcs":["actor_1"],"linked_locations":["loc_1"]}}],
  "revelations": [{{"id":"rev_1","thread_id":"T1","statement":"canonical deduction answer","required_clues":["clue_1"],"conditions":[],"payoff":"what it unlocks"}}],
  "clues": [{{"id":"clue_1","label":"specific clue","type":"physical_evidence|testimony|document|behavior|location_detail|contradiction","thread_id":"T1","source_location":"specific location","reveals":"what it reveals","payoff":"what it enables","revelation_ids":["rev_1"],"is_required":true,"source_status":"explicit","is_preserved_from_pdf":true}}],
  "actors": [{{"id":"actor_1","name":"name","role":"antagonist|ally|witness|neutral","location_id":"loc_1","goal":"goal","secret":"secret or useful knowledge","fear":"fear","current_plan":"operational plan","fallback_plan":"fallback plan","resources":["resource"],"knows":["information"],"wants":["want"],"avoids":["avoid"],"pressure_response":{{"low":"response","medium":"response","high":"response","critical":"response"}},"source_status":"explicit","is_preserved_from_pdf":true}}],
  "locations": [{{"id":"loc_1","name":"name","description":"module-accurate description","type":"room|site|region","access_state":"open|locked|hidden|blocked","visual_identity":"specific visual identity","gameplay_function":"what players do here","concrete_features":["usable feature"],"hazards":["hazard"],"exits":["exit"],"locked_paths":["locked path"],"clue_slots":["clue_1"],"tactical_features":["feature"],"tactical_map":{{"enabled":false}},"source_status":"explicit","is_preserved_from_pdf":true}}],
  "event_clocks": [{{"id":"clock_1","label":"clock","clock_type":"narrative|terminal_defeat|terminal_victory|escalation","progress":0,"max":6,"on_complete":"consequence in italiano","resolution_clues":["clue_id_needed_to_stop_clock"],"resolution_condition":"come i giocatori fermano questo clock","discovery_clue_id":"clue_id_that_reveals_this_clock_exists","discovery_hint":"segnale ambiguo prima della scoperta","steps":[{{"step":1,"world_state_change":"change","scene_prompt":"visible sign","possible_player_response":"response"}}]}}],
  "finale_conditions": [{{"id":"finale_1","label":"final condition","depends_on":["obj_1"],"required_clues":["clue_1"],"method":"concrete method","concrete_choice":"player-facing choice"}}],
  "genre_runtime": {{"routes":[],"safe_nodes":[],"maps":[],"special_items":[]}},
  "suggestions": ["uncertain repair or missing source material"]
}}

PDF TEXT:
\"\"\"{content}\"\"\""""
        if _text_provider_available():
            last_error = ""
            for provider_name in [_ACTIVE_PROVIDER] + ([p for p in [_other_provider()] if p]):
                try:
                    raw = (
                        _call_text_model(pdf_prompt, max_tokens=PDF_COMPILER_MAX_OUTPUT_TOKENS)
                        if provider_name == _ACTIVE_PROVIDER
                        else _call_text_model_with_provider(provider_name, pdf_prompt, max_tokens=PDF_COMPILER_MAX_OUTPUT_TOKENS)
                    )
                    if _looks_like_refusal(raw):
                        last_error = "provider_refusal"
                        continue
                    data = _extract_json_object(raw)
                    data = _mark_pdf_output(data)
                    data.setdefault("source_structure", structure)
                    data.setdefault("preservation_policy", {"forbid_structural_compression": True, "preserve_original_structure": True, "reason": "PDF interpreted by AI compiler"})
                    compiled = compile_from_raw_structure(
                        data,
                        source_type="pdf_text",
                        title=title or data.get("title", ""),
                        genre_hint=genre_hint,
                        runtime_profile_hint=runtime_profile_hint,
                    )
                    report = compiled["validation_report"]
                    report.setdefault("suggestions", []).append("PDF interpretato dal compiler AI prima della normalizzazione runtime.")
                    report["compiler_ai_used"] = True
                    return {
                        "adventure_definition": compiled["adventure_definition"].model_dump(),
                        "runtime_state": compiled["runtime_state"].model_dump(),
                        "validation_report": report,
                    }
                except Exception as e:
                    last_error = f"{type(e).__name__}: {e}"
                    print(f"[compile_adventure_to_runtime/pdf] provider {provider_name} errore: {last_error}")
            print(f"[compile_adventure_to_runtime/pdf] fallback locale dopo errore AI: {last_error}")
        has_strong_local_structure = bool(
            int(counts.get("rooms") or 0) >= 3
            or int(counts.get("clues") or 0) >= 3
            or (int(counts.get("npcs") or 0) >= 2 and int(counts.get("encounters") or 0) >= 1)
        )
        if not has_strong_local_structure:
            raise ValueError(
                "Il PDF non e stato interpretato dal compiler AI e il fallback locale non ha trovato abbastanza struttura giocabile "
                "(stanze, indizi, PNG o incontri). Meglio fermarsi qui che inventare un modulo generico."
            )
        compiled = compile_pdf_to_runtime(
            content,
            title=title,
            genre_hint=genre_hint,
            runtime_profile_hint=runtime_profile_hint,
        )
        report = compiled["validation_report"]
        report.setdefault("suggestions", []).append("Fallback locale usato: nessun compiler AI disponibile o JSON AI non valido.")
        report["compiler_ai_used"] = False
        definition = compiled["adventure_definition"]
        low_density = (
            len(definition.locations or []) <= 2
            and len(definition.actors or []) == 0
            and len(definition.clues or []) <= 3
            and len(content) > 20000
        )
        if low_density:
            raise ValueError(
                "Compiler PDF a bassa fedeltà: l'AI non ha prodotto JSON valido e il fallback locale ha compresso troppo "
                f"({len(definition.locations or [])} location, {len(definition.actors or [])} attori, {len(definition.clues or [])} indizi). "
                "Meglio riprovare/chunkare il PDF che salvare un runtime non fedele."
            )
        return {
            "adventure_definition": compiled["adventure_definition"].model_dump(),
            "runtime_state": compiled["runtime_state"].model_dump(),
            "validation_report": report,
        }

    if source_type == "manual_json":
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                data["source_mode"] = "manual_json"
                compiled = compile_from_raw_structure(
                    data,
                    source_type="manual_json",
                    title=title or data.get("title", ""),
                    genre_hint=genre_hint,
                    runtime_profile_hint=runtime_profile_hint,
                )
                return {
                    "adventure_definition": compiled["adventure_definition"].model_dump(),
                    "runtime_state": compiled["runtime_state"].model_dump(),
                    "validation_report": compiled["validation_report"],
                }
        except Exception:
            pass

    if source_type == "raw_text":
        structure = extract_pdf_structure(content)
        counts = structure.get("counts") or {}
        detected = structure.get("detected_structure") or {}
        looks_structured = bool(detected.get("has_room_keys") or counts.get("clues", 0) >= 5 or counts.get("factions", 0) >= 2)
        if looks_structured:
            compiled = compile_structured_text_to_runtime(
                content,
                title=title,
                genre_hint=genre_hint,
                runtime_profile_hint=runtime_profile_hint,
            )
            return {
                "adventure_definition": compiled["adventure_definition"].model_dump(),
                "runtime_state": compiled["runtime_state"].model_dump(),
                "validation_report": compiled["validation_report"],
            }

    source_mode = "manual_json" if source_type == "manual_json" else "raw_text"
    pdf_rules = ""
    ai_rules = """
AI GENERATED / RAW TEXT RULES
- If this is a generic prompt, use narrative archetypes as shape before filling.
- Create a complete but non-repetitive runtime structure.
- Write premise and initial_hook as 3-5 vivid Italian sentences with a clear starting situation, immediate pressure, first location, and visible first decision.
- Do not always use 3 clues, 3 locations, 1 antagonist.
- Vary structure according to archetype.
"""
    prompt = f"""You are an adventure compiler, not a narrator.
Return ONLY valid JSON. Do not write prose outside JSON.
LANGUAGE POLICY: all player-facing natural language fields MUST be in Italian, even if the source prompt is English. Preserve proper names, but translate premise, initial_hook, objectives, revelations, clues, NPC agendas, clocks, finale conditions and suggestions into fluent Italian.

TASK
Compile the source adventure into a state-driven AdventureDefinition.
Do not invent new core plot unless needed to repair missing structure. If something is missing, put it in suggestions, not canon.
Preserve original genre and tone.

SOURCE TYPE: {source_type}
SOURCE MODE: {source_mode}
TITLE HINT: {title}
GENRE HINT: {genre_hint or ""}
RUNTIME PROFILE HINT: {runtime_profile_hint or ""}

{pdf_rules or ai_rules}

OUTPUT JSON SHAPE:
{{
  "id": "stable_id",
  "title": "title",
  "genre": "genre",
  "runtime_profiles": ["investigation_graph"],
  "tone": "tone",
  "premise": "premessa in italiano, concreta e giocabile, 3-5 frasi",
  "initial_hook": "apertura in italiano, in medias res, non generica",
  "core_truths": [{{"id":"truth_1","statement":"hidden truth","reveal_clues":["clue_1"],"reveal_rule":"when..."}}],
  "objectives": [{{"id":"obj_1","label":"objective","success_conditions":["condition"]}}],
  "revelations": [{{"id":"rev_1","thread_id":"T1","statement":"deduction/revelation","required_clues":["clue_1"],"conditions":[],"payoff":"what it unlocks"}}],
  "clues": [{{"id":"clue_1","label":"concrete clue","type":"physical_evidence","thread_id":"T1","source_location":"location","reveals":"what it reveals","payoff":"what it enables","revelation_ids":["rev_1"],"is_required":true}}],
  "actors": [{{"id":"actor_1","name":"name","role":"antagonist|ally|witness|neutral","location_id":"loc_1","goal":"goal","secret":"secret","fear":"fear","current_plan":"current operational plan","fallback_plan":"fallback plan","resources":["concrete resource"],"knows":["useful information"],"wants":["want"],"avoids":["avoid"],"pressure_response":{{"low":"response","medium":"response","high":"response","critical":"response"}}}}],
  "factions": [],
  "locations": [{{"id":"loc_1","name":"name","description":"short","type":"room|site|region","access_state":"open","visual_identity":"specific visual identity","gameplay_function":"what players can do here","concrete_features":["usable feature"],"hazards":["hazard"],"exits":["exit"],"locked_paths":["locked path"],"clue_slots":["clue_1"],"tactical_features":["cover, choke point, elevation"],"tactical_map":{{"enabled":false}}}}],
  "event_clocks": [{{"id":"clock_1","label":"clock","clock_type":"narrative|terminal_defeat|terminal_victory|escalation","progress":0,"max":6,"on_complete":"consequence in italiano","resolution_clues":["clue_id_needed_to_stop_clock"],"resolution_condition":"come i giocatori fermano questo clock","discovery_clue_id":"clue_id_that_reveals_this_clock_exists","discovery_hint":"segnale ambiguo prima della scoperta","steps":[{{"step":1,"world_state_change":"concrete change","scene_prompt":"what becomes visible","possible_player_response":"what players can do"}}]}}],
  "pressure_systems": [],
  "resources": [],
  "finale_conditions": [{{"id":"finale_1","label":"finale condition","depends_on":["obj_1"],"required_clues":["clue_1"],"method":"concrete method","concrete_choice":"player-facing final choice"}}],
  "genre_runtime": {{"routes":[],"safe_nodes":[],"security_layers":[],"ritual_conditions":[],"special_items":[],"scene_nodes":[]}},
  "suggestions": ["missing but useful repair"]
}}

VALIDATION TARGETS
- Every clue links to at least one revelation.
- Every revelation has clues or conditions.
- Every objective has success_conditions.
- Every finale depends on objective/revelation/clock/state/flag.
- Important NPCs have role, goal, current/possible location.
- Locations have id, name, type, access_state.
- Event clocks have max/progress/on_complete and clock_type (narrative=world changes only, terminal_defeat=story_over+defeat, terminal_victory=story_over+victory, escalation=massive threat spike).
- Terminal clocks (terminal_defeat/terminal_victory) MUST have resolution_clues listing the clue IDs players must find to stop them, and discovery_clue_id indicating which clue reveals the clock exists.
- max for terminal clocks must be >= len(resolution_clues) + 2 to ensure players have time to resolve it.
- Every clue is concrete: visible, physical/testimonial, in a precise location, and tied to possible player actions.
- Major NPCs have operational agenda: goal, fear, current_plan, fallback_plan and pressure_response.
- Locations have playable features, hazards, exits, clue slots and tactical features when useful.
- Finale conditions have method and concrete player choice.

SOURCE:
\"\"\"{content}\"\"\""""
    raw = _call_text_model(prompt, max_tokens=5000)
    if _looks_like_refusal(raw):
        fallback = _other_provider()
        if fallback:
            raw = _call_text_model_with_provider(fallback, prompt, max_tokens=5000)
    try:
        data = _extract_json_object(raw)
    except Exception:
        compiled = compile_ai_generated_to_runtime(
            content,
            title=title or "Avventura compilata",
            genre_hint=genre_hint,
            runtime_profile_hint=runtime_profile_hint,
        )
        compiled["validation_report"].setdefault("suggestions", []).append(
            "Il provider non ha restituito JSON valido: usata forma archetipica variabile locale."
        )
        return {
            "adventure_definition": compiled["adventure_definition"].model_dump(),
            "runtime_state": compiled["runtime_state"].model_dump(),
            "validation_report": compiled["validation_report"],
        }
    data["source_mode"] = data.get("source_mode") or "ai_generated"
    compiled = compile_from_raw_structure(
        data,
        source_type=source_type,
        title=title or data.get("title", ""),
        genre_hint=genre_hint,
        runtime_profile_hint=runtime_profile_hint,
    )
    return {
        "adventure_definition": compiled["adventure_definition"].model_dump(),
        "runtime_state": compiled["runtime_state"].model_dump(),
        "validation_report": compiled["validation_report"],
    }


def generate_opening_scene(definition, players: list[dict]) -> str:
    """Genera la scena d'apertura dell'avventura tramite Claude.

    Produce una narrazione immersiva che:
    - Descrive la prima location in modo sensoriale
    - Chiarisce esplicitamente l'obiettivo dei personaggi
    - Introduce il tono/genere e la minaccia latente
    - Nomina i PNG presenti e i primi indizi percepibili
    - Indica la prima azione concreta possibile

    Fallback al testo template se la chiamata LLM fallisce.
    """
    # Raccoglie contesto dalla definizione compilata
    premise = (definition.premise or "").strip()
    initial_hook = (definition.initial_hook or "").strip()
    objective = definition.objectives[0].label if definition.objectives else "completare l'avventura"
    hidden_truth = definition.core_truths[0].statement if definition.core_truths else ""
    genre = definition.genre or "avventura"
    tone = (definition.tone or "").strip()
    archetype = (definition.archetype_profile or {}).get("primary_archetype", "")

    first_loc = definition.locations[0] if definition.locations else None
    loc_name = first_loc.name if first_loc else "la scena iniziale"
    loc_desc = (first_loc.description or "").strip() if first_loc else ""

    actors_here = [a for a in (definition.actors or []) if a.location_id == (first_loc.id if first_loc else "") or (first_loc and a.location_id == first_loc.name)]
    if not actors_here:
        actors_here = (definition.actors or [])[:2]
    actor_lines = "\n".join(
        f"- {a.name} ({a.role}): {(a.goal or a.secret or '').strip()[:120]}"
        for a in actors_here[:3]
    )

    clues_here = [c for c in (definition.clues or []) if not c.source_location or (first_loc and (
        c.source_location.lower() in first_loc.name.lower() or first_loc.name.lower() in c.source_location.lower()
    ))][:3]
    clue_lines = "\n".join(f"- {c.label} [{c.type or 'clue'}]" for c in clues_here)

    player_names = ", ".join(p.get("name", f"PG{p.get('id','')}") for p in (players or [])[:4])

    threat_desc = ""
    if definition.pressure_systems:
        ps = definition.pressure_systems[0]
        threat_desc = f"Pressione: {ps.label or ''} — {ps.description or ''}".strip(" —")
    elif definition.event_clocks:
        ec = definition.event_clocks[0]
        threat_desc = f"Clock attivo: {ec.label or ''} — {ec.consequence or ''}".strip(" —")

    prompt = f"""Sei il Narratore di un GDR GURPS. Devi scrivere la SCENA D'APERTURA dell'avventura.

CONTESTO AVVENTURA:
Titolo: {definition.title or 'Avventura GURPS'}
Genere: {genre} | Tono: {tone or 'serio'} | Archetipo: {archetype or 'investigation'}
Premessa: {premise or initial_hook or 'I personaggi si trovano coinvolti in una situazione pericolosa.'}
Verità nascosta (NON rivelare): {hidden_truth or 'da scoprire'}
Obiettivo dei PG: {objective}
{f'Minaccia latente: {threat_desc}' if threat_desc else ''}

PRIMA SCENA:
Location: {loc_name}
{f'Descrizione: {loc_desc}' if loc_desc else ''}
{f'PNG presenti:{chr(10)}{actor_lines}' if actor_lines else ''}
{f'Indizi percepibili (non ancora scoperti):{chr(10)}{clue_lines}' if clue_lines else ''}

PERSONAGGI GIOCANTI: {player_names or 'la squadra'}

ISTRUZIONI:
1. Apri con 2-3 frasi di ambientazione sensoriale (cosa si vede, si sente, si odora).
2. Chiarisci ESPLICITAMENTE cosa devono fare i personaggi e perché sono qui — senza ambiguità.
3. Presenta brevemente i PNG presenti come presenze concrete, non solo nomi.
4. Accenna a qualcosa che cattura l'attenzione (primo indizio percepibile) senza rivelarlo.
5. Chiudi con una frase che suggerisce tensione o urgenza coerente col tono.
6. Lunghezza: 180-280 parole. NON usare intestazioni o elenchi — solo prosa narrativa fluida.
7. Parla in seconda persona plurale ("siete", "vedete", "la squadra") per coinvolgere i giocatori.
8. NON rivelare la verità nascosta. NON risolvere nessun mistero. NON inventare PNG non elencati."""

    try:
        text = _call_claude(prompt, max_tokens=600).strip()
        if len(text) > 100:
            return text
    except Exception as e:
        print(f"[generate_opening_scene] LLM call failed: {e} — using fallback template")

    # Fallback template
    parts = [f"{premise}" if premise else "", f"{initial_hook}" if initial_hook and initial_hook != premise else ""]
    text = " ".join(p for p in parts if p).strip()
    if not text:
        text = f"L'avventura si apre a {loc_name}. {loc_desc}"
    text += f" Il vostro obiettivo: {objective}."
    return text


_MOVE_ACTION_RE = re.compile(r"[Ss]postar[si]* verso\s+(.+)", re.IGNORECASE)


def _resolve_movement_destination(player_action: str, runtime, current_scene_id: str) -> str:
    """F5: se l'azione è 'Spostarsi verso X', restituisce il location_id della destinazione.

    Consente al director di usare i vincoli di visibilità della scena di arrivo,
    non di quella di partenza, eliminando la race tra movimento e narrazione.
    """
    m = _MOVE_ACTION_RE.search(player_action or "")
    if not m:
        return current_scene_id
    dest_name = m.group(1).strip().rstrip(".")
    for loc in (runtime.locations or []):
        if loc.name.lower() == dest_name.lower() or loc.id.lower() == dest_name.lower():
            return loc.id
    # fallback: substring match
    dest_norm = dest_name.lower()
    for loc in (runtime.locations or []):
        if dest_norm in loc.name.lower() or loc.name.lower() in dest_norm:
            return loc.id
    return current_scene_id


def master_turn_with_bible(
    genre: str,
    players: list[dict],
    history: list[dict],
    player_action: str,
    active_player_id: int,
    adventure: dict,
    game_state_data: dict,
    prerolled: dict | None = None,
) -> dict:
    """
    Turno Master con bibbia avventura e tracking stato.

    game_state_data: {
      clues_found: [id, ...],
      npc_statuses: {id: {status, attitude, location}},
      threat_level: int (0-max),
      open_threads: [str, ...],
      turn: int,
      in_combat: bool,
    }

    Risposta aggiuntiva rispetto a master_turn base:
      state_updates: {
        clues_found: [id],          # nuovi indizi scoperti
        npc_updates: [{id, status, attitude}],
        new_threads: [str],
        closed_threads: [str],
        threat_increase: int,
        activate_combat: bool,
        combat_scene: { ... } | null,
        story_over: bool,
        victory: bool,
      }
    """
    active = next((p for p in players if p["id"] == active_player_id), players[0])
    adventure = _normalize_adventure_canon(dict(adventure or {}), source=(adventure or {}).get("adventure_canon", {}).get("source", "runtime_guard"))
    runtime = build_adventure_runtime(adventure, game_state_data)
    runtime_warnings = validate_runtime_integrity(adventure)
    simulation = simulate_world_state(
        runtime,
        player_action=player_action,
        prerolled=prerolled,
        game_state_data=game_state_data,
    )
    _map_state = game_state_data.get("map_state") or {}
    _current_scene_id = _map_state.get("current_node_id") or game_state_data.get("current_scene_id") or ""
    # F5: se l'azione del giocatore è uno spostamento (generato da F2 con "Spostarsi verso X"),
    # risolve la destinazione PRIMA della decisione del director per allineare i vincoli di visibilità.
    _current_scene_id = _resolve_movement_destination(player_action, runtime, _current_scene_id) or _current_scene_id
    director_decision = make_director_decision(runtime, simulation, prerolled=prerolled, current_scene_id=_current_scene_id or None)
    engine_updates = director_decision.get("state_updates_required") or {}
    runtime_context = runtime_prompt_context(runtime)
    director_context = director_prompt_context(director_decision)
    if runtime_warnings:
        director_context += "\n- Avvisi runtime: " + "; ".join(runtime_warnings[:4])
    sheets = "\n".join(_player_sheet(p) for p in players)
    genre_label = _GENRE_LABELS.get(genre, genre)
    # Roster skill + obiettivi di tutti i giocatori per opzioni multi-personaggio
    roster_lines = []
    for p in players:
        top_sk = sorted(p.get("skills", {}).items(), key=lambda x: -x[1])[:6]
        sk_str = ", ".join(f"{skill_display(k)}({v})" for k, v in top_sk)
        motivation = (p.get("motivation") or "").strip()
        motiv_str = f" | Vuole: {motivation}" if motivation else ""
        roster_lines.append(f"  - {p['name']} [id={p['id']}] ({p.get('role','')}): {sk_str or 'nessuna skill'}{motiv_str}")
    roster_text = "\n".join(roster_lines)

    history_text = ""
    for msg in history[-14:]:
        if msg["role"] == "master":
            history_text += f"\n[MASTER]: {msg['text'][:400]}"
        else:
            history_text += f"\n[{msg['name']}]: {msg['text']}"

    # Costruisci contesto bibbia
    clues_found_ids = set(game_state_data.get("clues_found", []))
    clue_progress_state = game_state_data.get("clue_progress", {}) or {}
    all_clues = adventure.get("clues", [])
    found_clues = [c for c in all_clues if c["id"] in clues_found_ids]
    missing_clues = [c for c in all_clues if c["id"] not in clues_found_ids]
    story_threads = list(adventure.get("story_threads") or [])
    clues_by_thread = {}
    for c in all_clues:
        tid = c.get("thread_id", "")
        if tid:
            clues_by_thread.setdefault(tid, []).append(c)
    thread_runtime = []
    ready_threads = []
    for t in story_threads:
        tid = t.get("id", "")
        required = t.get("required_clues") or [c.get("id") for c in clues_by_thread.get(tid, [])]
        partial = [
            cid for cid in required
            if cid not in clues_found_ids and (clue_progress_state.get(cid, {}) or {}).get("ticks", 0) > 0
        ]
        discovered = [cid for cid in required if cid in clues_found_ids]
        minimum = int(t.get("minimum_clues_to_deduce") or min(2, max(1, len(required) or 1)))
        status = "ready_to_deduce" if len(discovered) >= minimum else ("active" if discovered else t.get("status", "hidden"))
        row = {**t, "status": status, "discovered_clues": discovered, "partial_clues": partial}
        thread_runtime.append(row)
        if status == "ready_to_deduce":
            ready_threads.append(row)

    npc_statuses = game_state_data.get("npc_statuses", {})
    canon = adventure.get("adventure_canon") or {}
    canon_context = (
        "\nCANOVACCIO CANONICO CHIUSO:"
        f"\n- Verita centrale: {canon.get('core_truth') or adventure.get('hidden_truth','')}"
        f"\n- Antagonista principale: {canon.get('main_antagonist') or 'non dichiarato'}"
        f"\n- Falsi indizi ammessi: {'; '.join(canon.get('false_leads') or []) or 'nessuno'}"
        f"\n- Luoghi chiave: {'; '.join(canon.get('key_locations') or []) or 'non dichiarati'}"
        f"\n- Condizioni finale: {'; '.join(canon.get('finale_conditions') or []) or adventure.get('win_condition','')}"
    )

    npcs_context = ""
    npc_agenda_context = ""
    npc_pressure_context = adventure.get("npc_pressure_context") or ""
    # Runtime-injected clues (created by pressure events) and destroyed clues
    injected_clues = adventure.get("injected_clues") or []
    destroyed_clue_ids = set(adventure.get("destroyed_clue_ids") or [])
    if injected_clues:
        npc_pressure_context += "\nINDIZI CREATI DAGLI EVENTI NPC (disponibili ora):\n" + "\n".join(
            f"- [{c.get('id')}] {c.get('label','')}: {c.get('reveals') or c.get('payoff','')}"
            for c in injected_clues
        )
    if destroyed_clue_ids:
        npc_pressure_context += "\nINDIZI DISTRUTTI/NON PIÙ ACCESSIBILI: " + ", ".join(destroyed_clue_ids)
    for npc in adventure.get("npcs", []):
        st = npc_statuses.get(npc["id"], {})
        status = st.get("status", npc.get("status", "alive"))
        attitude = st.get("attitude", npc.get("attitude", "neutral"))
        loc = st.get("location", npc.get("location", "?"))
        npcs_context += f"\n- {npc['name']} ({npc['role']}): status={status}, attitude={attitude}, location={loc}"
        agenda = npc.get("npc_agenda") or {}
        if agenda:
            npc_agenda_context += (
                f"\n- {npc.get('name')}: ruolo={agenda.get('role','neutral')} | arco={st.get('arc_status', agenda.get('arc_status','unintroduced'))} | "
                f"obiettivo={agenda.get('goal','')} | segreto={agenda.get('secret','')} | priorita={agenda.get('recurrence_priority','medium')}"
            )

    threat_level = game_state_data.get("threat_level", 0)
    threat_max = adventure.get("threat_max_turns", 8)
    threat_pct = int(threat_level / max(threat_max, 1) * 100)
    open_threads = game_state_data.get("open_threads", [])
    turn = game_state_data.get("turn", 1)

    clues_context = ""
    n_found = len(found_clues)
    n_total = len(all_clues)
    clues_context += f"\nIndizi canonici: {n_found}/{n_total} ottenuti"
    if threat_pct >= 80 and missing_clues:
        clues_context += f" — ATTENZIONE: tempo quasi esaurito ({threat_pct}%), fai emergere i restanti indizi ATTIVAMENTE nelle prossime scene"
    if found_clues:
        clues_context += "\nIndizi scoperti: " + "; ".join(f"[{c['id']}] {c['text']}" for c in found_clues)
    partial_clues = [
        c for c in all_clues
        if c.get("id") not in clues_found_ids and (clue_progress_state.get(c.get("id"), {}) or {}).get("ticks", 0) > 0
    ]
    if partial_clues:
        clues_context += "\nIndizi in progresso: " + "; ".join(
            f"[{c['id']}] {min(2, int((clue_progress_state.get(c['id'], {}) or {}).get('ticks', 0)))}/2 passi — {(clue_progress_state.get(c['id'], {}) or {}).get('note','')}"
            for c in partial_clues
        )
    if missing_clues:
        urgency = "FAI TROVARE ORA" if threat_pct >= 80 else "da rivelare gradualmente"
        clues_context += f"\nIndizi ancora nascosti ({urgency}): " + "; ".join(
            f"[{c['id']}] ({c.get('thread_id','?')}) \"{c['text']}\" — trovabile: {c.get('location') or c.get('source_location','?')} — payoff: {c.get('payoff', c.get('reveals',''))}" for c in missing_clues
        )
    threads_context = ""
    if thread_runtime:
        lines = []
        for t in thread_runtime:
            clue_labels = []
            for cid in t.get("required_clues", []):
                c = next((x for x in all_clues if x.get("id") == cid), None)
                ticks = int((clue_progress_state.get(cid, {}) or {}).get("ticks", 0))
                mark = "✓" if cid in clues_found_ids else (f"~{min(2, ticks)}/2" if ticks else "")
                clue_labels.append(f"{cid}{mark}: {c.get('text','')[:80] if c else ''}")
            lines.append(
                f"- {t.get('id')}: {t.get('question')} | status={t.get('status')} | "
                f"indizi={len(t.get('discovered_clues', []))}/{t.get('minimum_clues_to_deduce', 2)} | "
                f"payoff={t.get('payoff','')} | indizi previsti: {'; '.join(clue_labels)}"
            )
        threads_context = "\nTHREAD CANONICI TRACCIATI:\n" + "\n".join(lines)
    if ready_threads:
        threads_context += "\nPISTE PRONTE A DEDURRE: " + "; ".join(
            f"{t.get('id')} — {t.get('question')} → sintesi: {t.get('true_answer','')}" for t in ready_threads
        )

    twists_available = [t for t in adventure.get("twists", []) if not t.get("used")]
    twists_context = ""
    if twists_available and threat_pct > 50:
        twists_context = f"\nColpi di scena disponibili (puoi attivarne uno se drammaticamente appropriato): " + "; ".join(f"[{t['id']}] trigger: {t['trigger']}" for t in twists_available)

    # Location corrente dal map_state (passato via game_state_data)
    current_location = ""
    map_state = game_state_data.get("map_state") or {}
    if map_state:
        cur_node_id = map_state.get("current_node_id")
        nodes = map_state.get("nodes") or {}
        cur_node = nodes.get(cur_node_id) or {}
        if cur_node.get("name"):
            current_location = f"\nLocation attuale: {cur_node['name']} — {cur_node.get('description','')}"
            tactical_map = cur_node.get("tactical_map") or {}
            if tactical_map.get("enabled"):
                current_location += (
                    "\nScheda tattica canonica di questa zona: "
                    f"ruolo={tactical_map.get('role','hot_zone')}; layout={tactical_map.get('layout','room')}; "
                    f"trigger={tactical_map.get('trigger','confronto diretto')}; "
                    f"elementi={'; '.join(tactical_map.get('features') or [])}; "
                    f"pericoli={'; '.join(tactical_map.get('hazards') or [])}"
                )
            # NPC presenti in questa location
            npc_here = [n["name"] for n in adventure.get("npcs", []) if
                        (n.get("location","") or "").lower() in cur_node.get("name","").lower()
                        or cur_node.get("name","").lower() in (n.get("location","") or "").lower()]
            if npc_here:
                current_location += f"\nPNG presenti qui: {', '.join(npc_here)}"
            # Indizi trovabili qui
            clues_here = [c for c in missing_clues if
                          cur_node.get("name","").lower()[:6] in (c.get("location","") or "").lower()
                          or (c.get("location","") or "").lower()[:6] in cur_node.get("name","").lower()]
            if clues_here:
                current_location += f"\nIndizi trovabili qui: {'; '.join(c['text'] for c in clues_here)}"

    # Ultime azioni proposte (per evitare ripetizioni)
    last_options = []
    for msg in history[-6:]:
        if msg["role"] == "master" and "[OPT]" in msg.get("text", ""):
            pass  # non usato, ma teniamo il riferimento
    player_actions_recent = [m["text"] for m in history[-8:] if m["role"] != "master"]

    prompt = f"""Sei il Master di una campagna GDR in stile {genre_label} (GURPS Lite).
LINGUA OBBLIGATORIA: rispondi sempre in italiano naturale. Se il canovaccio contiene frasi in inglese, traducile nella narrativa e nelle opzioni mantenendo solo nomi propri e toponimi originali.

═══ BIBBIA AVVENTURA ═══
Titolo: {adventure.get('title', '?')}
Premessa: {adventure.get('premise', '?')}
Verità nascosta (NON rivelare ancora se non è il momento): {adventure.get('hidden_truth', '?')}
Minaccia: {adventure.get('threat_description', '?')} — livello attuale {threat_level}/{threat_max} ({threat_pct}%)
Condizione vittoria: {adventure.get('win_condition', '?')}
{twists_context}
{canon_context}
{runtime_context}
{director_context}

═══ STATO PARTITA (turno {turn}) ═══{current_location}
PNG:{npcs_context}
AGENDE PNG:{npc_agenda_context or "\n- nessuna agenda strutturata"}{npc_pressure_context}
{clues_context}
Thread aperti: {'; '.join(open_threads) if open_threads else 'nessuno'}
{threads_context}

═══ PERSONAGGI ═══
{sheets}
Ultimo ad agire: {active["name"]} ({active.get("role","")})
Roster gruppo:
{roster_text}

═══ STORIA RECENTE ═══{history_text if history_text else " (inizio)"}

═══ AZIONE ═══
{active["name"].upper()}: {player_action}

ISTRUZIONI:
1. TIRO GURPS già effettuato — NON simularlo. Esito vincolante:
   Skill: {prerolled["skill"] if prerolled else "?"} | 3d6={prerolled["rolled"] if prerolled else "?"} vs {prerolled["effective_skill"] if prerolled else "?"} | Margine: {prerolled["margin"] if prerolled else "?"} | Esito: {prerolled["outcome"] if prerolled else "?"} | Successo: {str(prerolled["success"]) if prerolled else "?"}
   Intento rilevato: {prerolled.get("intent", "?") if prerolled else "?"} | Skill consentite per intento: {", ".join((prerolled.get("allowed_skills") or [])[:10]) if prerolled else "?"}
   - FALLIMENTO: il personaggio non ottiene ciò che voleva, c'è un costo narrativo concreto.
   - SUCCESSO PARZIALE: risultato incompleto con conseguenza.
   - SUCCESSO PIENO/CRITICO: pieno successo, narra con dettaglio.

2. NARRATIVA (3-5 frasi vivide): descrivi l'esito dell'azione E fai muovere la storia. Inserisci {{{{ROLL}}}} nel punto drammatico.
   - La scena deve CAMBIARE rispetto a quella precedente: nuova informazione, reazione di un PNG, spostamento, escalation.
   - Se il gruppo è fermo sulla stessa situazione da 2+ turni, introduce una svolta: arriva un PNG, scatta una trappola, si apre un passaggio, un alleato tradisce.
   - REGOLA INDIZI: non creare indizi nuovi. Fai avanzare un indizio canonico con clue_progress; usa clues_found solo quando la prova è stata davvero ottenuta.

3. OPZIONI (3 proposte per il prossimo turno):
   - DEVONO essere diverse da queste azioni già fatte: {'; '.join(player_actions_recent[-4:]) if player_actions_recent else 'nessuna'}
   - DEVONO essere ancorate alla situazione attuale (location, PNG presenti, indizi appena trovati, minaccia in corso).
   - Almeno una deve spingere verso la condizione di vittoria o rivelare un indizio.
   - Assegna ogni opzione al personaggio più adatto per skill e motivazione.
   - La terza è sempre "Azione custom".

4. Aggiorna lo stato (clue_progress, clues_found, npc_updates, location_updates, objective_updates, faction_updates, clock/resource/finale updates, threat_increase).
   threat_increase: 0 se i giocatori hanno guadagnato terreno o risolto un indizio, 1 solo su fallimento netto o conseguenza narrativa negativa. MAI 2 salvo clock completato o evento di escalation autorizzato dal Director.

REGOLE CANOVACCIO PDF — OBBLIGATORIE:
- STATE-DRIVEN: il motore ha gia deciso gli update minimi in "NARRATIVE DIRECTOR". La tua narrativa deve renderli, non sostituirli.
- Non sei la fonte della verita: non cambiare core_truth, antagonista, indizi, clock, locations, faction/actor state o esito meccanico.
- Se proponi state_updates diversi da quelli del director, devono essere aggiunte compatibili; il backend dara precedenza agli update del motore.
- Usa solo adventure_canon, story_threads, clues, npcs e locations gia presenti nella bibbia. Non creare nuovi filoni portanti.
- Gli indizi sono FISSI: non generare nuovi indizi, nomi-prova, simboli, documenti o sottotrame. Puoi solo far progredire o ottenere indizi gia elencati in clues.
- Ogni clues_found o clue_progress deve usare un id clue esistente e quella clue deve avere thread_id valido.
- Ogni scena puo far avanzare al massimo 1 indizio canonico in clue_progress, scegliendo SOLO id esistenti fra gli indizi nascosti.
- clues_found deve restare raro: usalo solo quando la prova canonica è stata recuperata, letta, confermata o testimoniata in modo chiaro.
- Se narri solo un avvicinamento, sospetto, accesso parziale o frammento, NON usare clues_found: usa clue_progress.
- new_threads deve essere sempre []. Se emerge una nuova complicazione, mettila in npc_updates, threat_increase, combat_scene o narrativa, non come thread.
- discovered_facts deve contenere solo fatti concreti gia derivati da un clue, non atmosfera.
- Usa npc_updates per far cambiare stato, luogo, atteggiamento o arc_status agli NPC del canovaccio; non inventare PNG importanti se ci sono NPC canonici inutilizzati.
- Se una pista e ready_to_deduce, proponi una sintesi deduttiva esplicita nella narrativa e chiudila in closed_threads solo se i giocatori hanno verificato o accettato la deduzione.
- Se una pista e ready_to_deduce, NON introdurre nuovi misteri prima di aver offerto una scena di sintesi/confronto/verifica.
- Un successo deve sempre modificare almeno uno stato persistente: clue_progress, clues_found, npc_updates, location_updates, objective_updates, faction_updates, closed_threads, threat_increase, activate_combat/combat_over, story_over.
- Un fallimento non blocca la storia: produce indizio incompleto, costo, complicazione, pressione o falso vantaggio, sempre collegato a un thread esistente.
- DERAILMENT PREVENTION: non usare una skill fuori intento. Se l'intento rilevato non è combat, non trasformare l'azione in combattimento e non usare combattere come fallback narrativo.
- EVENTI MAGGIORI: finale, morte gruppo, boss release, apocalisse, distruzione di un luogo e rivelazione finale sono vietati salvo explicit_trigger o finale_condition gia soddisfatta. Azioni passive come osservare, cercare, studiare, ascoltare o decifrare non possono causare catastrofi terminali; al massimo producono costo locale, pressione o clue_progress.

NARRATIVE AUTHORITY LIMITS — OBBLIGATORIO:
- Sei un renderer, non l'autorita sul canovaccio.
- Devi obbedire a allowed_escalation_tier indicato dal NARRATIVE DIRECTOR.
- Non creare esiti terminali se non sono esplicitamente autorizzati.
- Non cambiare genere, tono o cosmologia dell'avventura.
- Non introdurre apocalisse, sole nero, distruzione del mondo, rovina irreversibile o game over se non sono consentiti dal profilo genere e dal tier.
- Narra dentro il genre_profile e usa solo escalation_types consentiti.
- Se il tiro fallisce, produci il tipo di conseguenza indicato dal Director, non una piu grande.
- Se il Director dice pressure increase, narra solo pressione/allarme/costo locale.
- Non concludere l'avventura: story_over e victory valgono solo se validati dal backend.

REGOLA FINE AVVENTURA — OBBLIGATORIA:
- Se threat_level >= threat_max ({threat_pct}% attuale): questo è l'ULTIMO turno. La minaccia ha vinto. Narra un finale drammatico di sconfitta ({adventure.get('threat_description','la minaccia')[:60]} si compie), poi imposta story_over=true, victory=false, end_reason="2-3 frasi in italiano che spiegano perché il gruppo ha perso: quale minaccia si è compiuta, quale errore chiave è stato fatale, cosa è andato storto". Non proporre opzioni di continuazione.
- Se i giocatori hanno soddisfatto la condizione di vittoria ("{adventure.get('win_condition','')[:100]}"): narra il trionfo e imposta story_over=true, victory=true, end_reason="2-3 frasi in italiano che spiegano perché il gruppo ha vinto: quale indizio chiave ha risolto il caso, quale scelta è stata decisiva".
- Se mancano ancora indizi importanti ma la minaccia è >= 80%: fai emergere indizi chiave nelle prossime scene anche senza tiro specifico — il tempo stringe.

REGOLA COMBATTIMENTO — OBBLIGATORIA:
Stato attuale combattimento: {"IN COMBATTIMENTO" if game_state_data.get("in_combat") else "NON in combattimento"}.

- Se NON in combattimento: imposta activate_combat=true SE la narrativa porta a uno scontro fisico diretto (nemico attacca, i giocatori attaccano, sparatoria inizia, aggressione esplicita). NON aspettare che il giocatore lo chieda — se il contesto porta allo scontro, ATTIVALO.
- Se la Location attuale contiene una scheda tattica canonica e il trigger indicato si verifica, activate_combat=true è fortemente preferito: quella zona è stata progettata come zona calda/finale.
- Se GIÀ IN COMBATTIMENTO: activate_combat=false (il combattimento è già attivo). Imposta combat_over=true se i nemici sono stati eliminati/fuggiti/catturati e lo scontro è concluso.
- combat_scene (solo quando activate_combat=true): popola ESCLUSIVAMENTE con PNG antagonisti vivi che combattono (persone, creature). NO luoghi, ambienti, oggetti. HP realistici: umano normale 10-12 HP, guardia 12-15, boss 20+. attack_skill: 10-14 per umani, active_defense: 8-10, damage_dice: "1d6" corpo a corpo, "2d6-1" arma da fuoco.
- BILANCIAMENTO: se non è una zona finale/boss, genera al massimo {max(1, min(3, len(players)))} nemici, meglio 1-3, con skill 9-11 e danni contenuti. Gli scontri iniziali devono poter essere evitati, vinti o abbandonati.
- VIA DI USCITA: ogni combat_scene non finale deve lasciare una ritirata plausibile o una via alternativa nella fiction; non chiudere i giocatori in una trappola letale salvo scena finale dichiarata.

Esempio combat_scene corretto:
{{"entities": [{{"id": "nemico_1", "name": "Guardia Armata", "type": "enemy", "zone": "centro", "hp": 12, "max_hp": 12, "dr": 2, "attack_skill": 12, "active_defense": 9, "damage_dice": "2d6-1", "damage_type": "cr"}}]}}

Rispondi SOLO con JSON puro — NO backtick, NO ```json, NO testo prima o dopo:
{{
  "narrative": "...testo...{{{{ROLL}}}}...testo...",
  "roll": {{
    "rolled": {prerolled["rolled"] if prerolled else 0},
    "target": {prerolled["effective_skill"] if prerolled else 10},
    "skill": "{prerolled["skill"] if prerolled else ""}",
    "skill_name": "{prerolled["skill"] if prerolled else ""}",
    "success": {str(prerolled["success"]).lower() if prerolled else "true"},
    "margin": {prerolled["margin"] if prerolled else 0},
    "critical": {str(prerolled["critical"]).lower() if prerolled else "false"}
  }},
  "options": [
    {{"text": "...", "skill": "<nome>", "skill_level": <int>, "stat": "<stat>", "player_id": <id del personaggio più adatto>}},
    {{"text": "...", "skill": "<nome>", "skill_level": <int>, "stat": "<stat>", "player_id": <id del personaggio più adatto>}},
    {{"text": "Azione custom", "skill": "", "skill_level": 0, "stat": "", "player_id": {active_player_id}}}
  ],
  "state_updates": {{
    "clue_progress": [{{"clue_id": "id_esistente", "note": "cosa e stato capito o avvicinato", "ticks": 1}}],
    "clues_found": [],
    "discovered_clues": [],
    "npc_updates": [],
    "location_updates": [],
    "objective_updates": [],
    "revelation_updates": [],
    "faction_updates": [],
    "clock_updates": [],
    "pressure_updates": [],
    "resource_updates": [],
    "finale_updates": [],
    "truth_updates": [],
    "flags": {{}},
    "new_threads": [],
    "closed_threads": [],
    "threat_increase": 0,
    "activate_combat": false,
    "combat_scene": null,
    "combat_over": false,
    "story_over": false,
    "victory": false,
    "end_reason": "",
    "major_event": null,
    "explicit_trigger": null,
    "finale_condition_met": false,
    "allowed_escalation_tier": {director_decision.get("allowed_escalation_tier", 3)},
    "allowed_escalation_types": [],
    "forbidden_escalation_types": []
  }}
}}"""

    # Cortocircuito: se la minaccia è già al 100% genera il finale senza chiamare Claude
    if threat_pct >= 100:
        threat_desc = adventure.get("threat_description", "La minaccia si è compiuta.")
        ending_prompt = (
            f"Sei il Master di una partita GDR in stile {genre_label}. "
            f"La minaccia è al massimo: {threat_desc}. "
            f"Scrivi un finale drammatico di sconfitta in 4-5 frasi vivide in italiano. "
            f"Sii cinematografico, non banale. Non usare titoli o spiegazioni."
        )
        try:
            ending_narrative = _call_text_model(ending_prompt, max_tokens=300).strip()
        except Exception:
            ending_narrative = f"{threat_desc} Il gruppo non è riuscito a fermare ciò che stava per accadere. L'avventura si conclude tra le ombre."
        return {
            "narrative": ending_narrative,
            "roll": None,
            "options": [],
            "state_updates": {
                "clues_found": [], "npc_updates": [], "new_threads": [],
                "closed_threads": [], "threat_increase": 0,
                "activate_combat": False, "combat_scene": None,
                "combat_over": False, "story_over": True, "victory": False,
            },
        }

    raw = _call_text_model(prompt, max_tokens=2400)
    if _looks_like_refusal(raw):
        fallback_provider = _other_provider()
        if fallback_provider:
            try:
                raw = _call_text_model_with_provider(fallback_provider, prompt, max_tokens=2400)
            except Exception:
                pass
    if _looks_like_refusal(raw):
        result = _safe_master_refusal_fallback(
            adventure=adventure,
            active_name=active.get("name", "Il gruppo"),
            player_action=player_action,
            prerolled=prerolled,
            active_player_id=active_player_id,
        )
        result["state_updates"] = _validate_master_state_updates(
            merge_engine_and_ai_updates(engine_updates, result.get("state_updates") or {}),
            adventure=adventure,
            game_state_data=game_state_data,
            prerolled=prerolled,
            director_decision=director_decision,
            narrative_text=result.get("narrative", ""),
        )
        return result
    try:
        result = _extract_json_object(raw)
    except Exception:
        result = {
            "narrative": "Il Master non riesce a trasformare la risposta in JSON valido, quindi mantiene la scena sul canovaccio: la situazione avanza con una conseguenza concreta senza introdurre nuovi misteri.",
            "roll": None,
            "options": [{"text": "Continua", "skill": "", "skill_level": 0, "stat": "", "player_id": active_player_id}],
            "state_updates": merge_engine_and_ai_updates(engine_updates, {"clues_found": [], "npc_updates": [], "new_threads": [], "closed_threads": [], "threat_increase": 1, "activate_combat": False, "combat_scene": None, "combat_over": False, "story_over": False, "victory": False}),
        }
    # Guardia residua: se Claude ha ignorato story_over nonostante threat < 100
    su = merge_engine_and_ai_updates(engine_updates, result.get("state_updates") or {})
    su = _validate_master_state_updates(
        su,
        adventure=adventure,
        game_state_data=game_state_data,
        prerolled=prerolled,
        director_decision=director_decision,
        narrative_text=result.get("narrative", ""),
    )
    result["state_updates"] = su
    if su.get("needs_alternative_narration"):
        actor_name = active.get("name", "il personaggio")
        if su.get("clue_progress"):
            safe_progress = f"{actor_name} nota qualcosa di interessante, ma non abbastanza da trarre conclusioni definitive — serve ancora verificare."
        elif su.get("npc_updates"):
            safe_progress = f"La mossa di {actor_name} produce una reazione: qualcuno cambia posizione, atteggiamento o intenzione, aprendo una nuova possibilità."
        elif su.get("threat_increase"):
            safe_progress = f"L'azione di {actor_name} agita le acque senza risolvere nulla — la tensione sale di un gradino."
        else:
            safe_progress = f"{actor_name} ottiene un risultato parziale: la situazione si muove, ma l'esito finale resta aperto."
        result["narrative"] = safe_progress
    # Terminal clock override: if engine fired a terminal clock, force story_over regardless of AI decision
    for trigger in simulation.get("clock_triggers") or []:
        ctype = trigger.get("clock_type", "narrative")
        if ctype == "terminal_defeat":
            su["story_over"] = True
            su["victory"] = False
            if not su.get("end_reason"):
                su["end_reason"] = f"Il clock '{trigger['label']}' si è completato: {trigger['consequence'] or trigger['on_complete']}. Il gruppo non è riuscito a fermare la minaccia in tempo."
            break
        elif ctype == "terminal_victory":
            su["story_over"] = True
            su["victory"] = True
            if not su.get("end_reason"):
                su["end_reason"] = f"Il clock '{trigger['label']}' ha raggiunto la condizione di vittoria: {trigger['consequence'] or trigger['on_complete']}."
            break
        elif ctype == "escalation":
            su["threat_increase"] = max(int(su.get("threat_increase") or 0), 3)
    # Auto-resolved terminal_victory: if all resolution_clues found for a terminal_victory clock, end with victory
    for resolved in simulation.get("auto_resolved_clocks") or []:
        if resolved.get("clock_type") == "terminal_victory" and not su.get("story_over"):
            su["story_over"] = True
            su["victory"] = True
            if not su.get("end_reason"):
                su["end_reason"] = f"Il gruppo ha trovato tutti gli indizi necessari e risolto il clock '{resolved['label']}'. L'avventura si conclude con la loro vittoria."
            break
    result["state_updates"] = su
    return result


def evaluate_personal_victories(players: list[dict], adventure: dict, final_narrative: str, group_victory: bool) -> dict[int, bool]:
    """Chiamata Claude per valutare se ogni giocatore ha raggiunto il proprio obiettivo personale."""
    if not players:
        return {}

    player_lines = []
    for p in players:
        motivation = (p.get("motivation") or "").strip()
        if not motivation:
            motivation = "(nessun obiettivo esplicito)"
        player_lines.append(f'  - id={p["id"]} nome="{p["name"]}" obiettivo="{motivation}"')
    players_block = "\n".join(player_lines)

    outcome_label = "VITTORIA DI GRUPPO" if group_victory else "SCONFITTA DI GRUPPO"
    premise = adventure.get("premise", "")[:200]
    win_condition = adventure.get("win_condition", "")[:150]

    prompt = f"""Sei il giudice finale di una campagna GDR GURPS Lite.
La storia è appena terminata con {outcome_label}.

PREMESSA AVVENTURA: {premise}
CONDIZIONE DI VITTORIA GRUPPO: {win_condition}

NARRATIVA FINALE (ultimi eventi):
{final_narrative[:800]}

PERSONAGGI E OBIETTIVI PERSONALI:
{players_block}

Per ogni personaggio valuta se il suo obiettivo personale è stato raggiunto o fallito, basandoti sulla narrativa finale e sugli eventi dell'avventura.
Un obiettivo si considera raggiunto se la narrativa suggerisce che ciò che voleva il personaggio si è avverato, anche parzialmente.
Se un personaggio non ha un obiettivo esplicito, consideralo raggiunto se il gruppo ha vinto, fallito se ha perso.

Rispondi SOLO con questo JSON (nessun testo extra):
{{
  "results": [
    {{"player_id": <int>, "achieved": <true|false>, "reason": "<1 frase in italiano>"}}
  ]
}}"""

    try:
        raw = _call_text_model(prompt, max_tokens=400)
        data = _extract_json_object(raw)
        results = data.get("results", [])
        return {r["player_id"]: bool(r.get("achieved", False)) for r in results if "player_id" in r}
    except Exception as exc:
        print(f"[evaluate_personal_victories] fallback (errore: {type(exc).__name__}: {exc})")
        return {p["id"]: group_victory for p in players}
