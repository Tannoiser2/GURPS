from __future__ import annotations

import json
import os
from pathlib import Path

from .runtime_models import AdventureDefinition, AdventureRuntimeState


# ─── Cartella radice ──────────────────────────────────────────────────────────

_default_store = Path(__file__).resolve().parents[2] / "data" / "compiled_adventures"
STORE_DIR = Path(
    os.getenv("ADVENTURE_RUNTIME_STORE_DIR")
    or ("/tmp/compiled_adventures" if os.getenv("VERCEL") else _default_store)
)
STORE_DIR.mkdir(parents=True, exist_ok=True)


# ─── Mapping genere → sottocartella ──────────────────────────────────────────

_GENRE_FOLDER: dict[str, str] = {
    # Fantascienza
    "sci_fi":            "sci-fi",
    "sci-fi":            "sci-fi",
    "scifi":             "sci-fi",
    "cyberpunk":         "sci-fi",
    "space_opera":       "sci-fi",
    "post_apocalyptic":  "sci-fi",
    # Fantasy
    "fantasy":           "fantasy",
    "dark_fantasy":      "fantasy",
    "mythic":            "fantasy",
    "sword_and_sorcery": "fantasy",
    # Horror
    "horror":            "horror",
    "mystery_horror":    "horror",
    "cosmic_horror":     "horror",
    "survival_horror":   "horror",
    "gothic":            "horror",
    # Investigazione / Mistero
    "detective_classico":  "investigation",
    "investigation":       "investigation",
    "mystery":             "investigation",
    "noir":                "investigation",
    "thriller":            "investigation",
    "spy":                 "investigation",
    # Azione / Avventura
    "action":            "action",
    "action_adventure":  "action",
    "heist":             "action",
    "military":          "action",
    # Storico / Epoche
    "ww2":               "storico",
    "western":           "storico",
    "historical":        "storico",
    "renaissance":       "storico",
    "ancient":           "storico",
    # Romance / Drama
    "romance":           "romance",
    "drama":             "romance",
    "social":            "romance",
}

_GENRE_LABELS: dict[str, str] = {
    "sci-fi":       "Fantascienza",
    "fantasy":      "Fantasy",
    "horror":       "Horror",
    "investigation": "Investigazione",
    "action":       "Azione",
    "storico":      "Storico",
    "romance":      "Romance",
    "_other":       "Altro",
}


def genre_folder(genre: str) -> str:
    """Restituisce il nome della sottocartella per un dato genere."""
    key = str(genre or "").lower().strip().replace(" ", "_").replace("-", "_")
    return _GENRE_FOLDER.get(key, "_other")


def _genre_dir(genre: str) -> Path:
    d = STORE_DIR / genre_folder(genre)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_id(runtime_id: str) -> str:
    return (
        "".join(ch for ch in runtime_id if ch.isalnum() or ch in ("-", "_")).strip()
        or "runtime"
    )


def _path(runtime_id: str, genre: str = "") -> Path:
    """Percorso canonico per salvare un runtime (nella sottocartella genere)."""
    return _genre_dir(genre) / f"{_safe_id(runtime_id)}.json"


def _find_path(runtime_id: str) -> Path | None:
    """
    Cerca un runtime_id in tutte le sottocartelle.
    Utile per load/update quando non si conosce il genere a priori.
    """
    safe = _safe_id(runtime_id)
    filename = f"{safe}.json"
    # Prima controlla la root (retrocompatibilità)
    root_path = STORE_DIR / filename
    if root_path.exists():
        return root_path
    # Poi cerca nelle sottocartelle
    for subfolder in STORE_DIR.iterdir():
        if subfolder.is_dir():
            candidate = subfolder / filename
            if candidate.exists():
                return candidate
    return None


# ─── API pubblica ─────────────────────────────────────────────────────────────

def save_runtime(
    definition: AdventureDefinition,
    runtime_state: AdventureRuntimeState,
    validation_report: dict,
) -> dict:
    """Salva il runtime nella sottocartella del genere."""
    payload = {
        "adventure_definition": definition.model_dump(),
        "runtime_state":        runtime_state.model_dump(),
        "validation_report":    validation_report,
        "live_game_state":      None,
    }
    path = _path(definition.id, definition.genre or "")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def load_runtime(runtime_id: str) -> dict | None:
    """Carica un runtime cercandolo in tutte le sottocartelle."""
    path = _find_path(runtime_id)
    if not path:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_runtimes(genre_filter: str | None = None) -> list[dict]:
    """
    Elenca tutti i runtime disponibili.
    Se genre_filter è specificato, restituisce solo quelli di quel genere/cartella.
    """
    rows = []
    search_dirs: list[Path] = []

    if genre_filter:
        folder = genre_folder(genre_filter)
        d = STORE_DIR / folder
        if d.exists():
            search_dirs = [d]
    else:
        # Root (file legacy) + tutte le sottocartelle (escluso _debug_pdf)
        search_dirs = [STORE_DIR] + [
            p for p in STORE_DIR.iterdir()
            if p.is_dir() and p.name != "_debug_pdf"
        ]

    seen: set[str] = set()
    for search_dir in search_dirs:
        for path in sorted(search_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            if path.name in seen:
                continue
            seen.add(path.name)
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                # Salta i file di debug PDF (non sono runtime di gioco)
                if data.get("export_type"):
                    continue
                definition  = data.get("adventure_definition") or {}
                validation  = data.get("validation_report") or {}
                rid = definition.get("id") or path.stem
                g   = definition.get("genre", "")
                rows.append({
                    "id":               rid,
                    "title":            definition.get("title") or path.stem,
                    "genre":            g,
                    "genre_folder":     genre_folder(g),
                    "genre_label":      _GENRE_LABELS.get(genre_folder(g), genre_folder(g)),
                    "runtime_profiles": definition.get("runtime_profiles", []),
                    "playable":         validation.get("playable", False),
                    "playable_score":   (
                        validation.get("playable_score")
                        or validation.get("quality", {}).get("fiction_density_score", 0)
                    ),
                    "warnings":         len(validation.get("warnings") or []),
                    "errors":           len(validation.get("errors") or []),
                    "has_live_state":   bool(data.get("live_game_state")),
                    "folder":           path.parent.name,
                })
            except Exception:
                continue

    # Ordina: prima per cartella (genere), poi per mtime desc
    rows.sort(key=lambda r: (r["genre_folder"], r["title"].lower()))
    return rows


def update_runtime(runtime_id: str, patch: dict) -> dict | None:
    """Aggiorna un runtime esistente (cercandolo in tutte le sottocartelle)."""
    path = _find_path(runtime_id)
    if not path:
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    _KNOWN_KEYS = {"adventure_definition", "runtime_state", "validation_report", "live_game_state"}
    for key, value in patch.items():
        data[key] = value
    # Se il genere è cambiato, sposta nella cartella giusta
    new_genre = (patch.get("adventure_definition") or {}).get("genre") or \
                data.get("adventure_definition", {}).get("genre", "")
    correct_path = _path(runtime_id, new_genre)
    if correct_path != path and not correct_path.exists():
        path.rename(correct_path)
        path = correct_path
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data
