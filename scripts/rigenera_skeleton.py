#!/usr/bin/env python3
"""
Rigenera le 20 avventure AI "skeleton" (score 50, location placeholder)
chiamando il backend (locale o su Render) e salvando i nuovi JSON al posto degli originali.

Esegui dalla root del repo GURPS:
    python3 scripts/rigenera_skeleton.py                           # usa Render
    python3 scripts/rigenera_skeleton.py --backend http://127.0.0.1:8765  # backend locale
    python3 scripts/rigenera_skeleton.py --max 5                   # rigenera solo le prime 5

Requisiti:
    pip install requests

Le avventure originali vengono salvate in backup/ prima di sovrascriverle.
"""

import argparse
import json
import os
import pathlib
import shutil
import time

import requests

DEFAULT_BACKEND = "https://gurps-f93w.onrender.com"
BASE = pathlib.Path("data/compiled_adventures")
BACKUP = pathlib.Path("data/compiled_adventures/_backup_skeleton")

# Giocatori default per le avventure compact
DEFAULT_PLAYERS = [
    {"id": "p1", "name": "Thorin",   "hp": 12, "max_hp": 12, "skills": {"combattimento": 13, "furtività": 11}},
    {"id": "p2", "name": "Alara",    "hp": 10, "max_hp": 10, "skills": {"investigazione": 14, "persuasione": 12}},
    {"id": "p3", "name": "Okafor",   "hp": 11, "max_hp": 11, "skills": {"tecnologia": 13, "percezione": 12}},
]

# Mappa genre folder → genre string per l'API
GENRE_MAP = {
    "action":        "action",
    "fantasy":       "fantasy",
    "horror":        "horror",
    "investigation": "investigation",
    "romance":       "romance",
    "sci-fi":        "sci_fi",
    "sci_fi":        "sci_fi",
}

# Le 20 avventure skeleton rilevate con genre e scala
SKELETONS = [
    ("action/ai_autostrada_dei_santi.json",          "action",        "compact"),
    ("action/ai_trincea_17.json",                    "action",        "compact"),
    ("fantasy/ai_banchetto_degli_dei_morti.json",    "fantasy",       "compact"),
    ("fantasy/ai_biblioteca_sogni_rubati.json",      "fantasy",       "compact"),
    ("fantasy/ai_il_principe_delle_sabbie.json",     "fantasy",       "compact"),
    ("fantasy/ai_la_stirpe_del_ferro_silente.json",  "fantasy",       "compact"),
    ("fantasy/ai_maledizione_di_raven_hollow.json",  "fantasy",       "compact"),
    ("fantasy/ai_santuario_delle_ceneri.json",       "fantasy",       "compact"),
    ("horror/ai_la_biblioteca_che_respira.json",     "horror",        "compact"),
    ("horror/ai_luci_sotto_il_ghiaccio.json",        "horror",        "compact"),
    ("investigation/ai_il_mercato_dei_ricordi.json", "investigation", "compact"),
    ("investigation/ai_il_miglio_sommerso.json",     "investigation", "compact"),
    ("investigation/ai_opera_delle_maschere.json",   "investigation", "compact"),
    ("romance/ai_il_debito_del_drago.json",          "romance",       "compact"),
    ("sci-fi/ai_corsa_alla_luna_nera.json",          "sci_fi",        "compact"),
    ("sci_fi/ai_codice_ultimo_umano.json",           "sci_fi",        "compact"),
    ("sci_fi/ai_contrabbando_di_stelle.json",        "sci_fi",        "compact"),
    ("sci_fi/ai_eredita_di_nova_prime.json",         "sci_fi",        "compact"),
    ("sci_fi/ai_frequenza_fantasma.json",            "sci_fi",        "compact"),
    ("sci_fi/ai_protocollo_silenzio.json",           "sci_fi",        "compact"),
]


def _is_skeleton(path: pathlib.Path) -> bool:
    try:
        d = json.loads(path.read_text())
        locs = (d.get("adventure_definition") or {}).get("locations") or []
        return bool(locs) and all(
            any(str(l.get("id", "")).startswith(p)
                for p in ("loc_start", "loc_node", "loc_finale", "loc_ai_"))
            for l in locs if isinstance(l, dict)
        )
    except Exception:
        return False


def rigenera(path_rel: str, genre: str, scale: str, backend: str, retry: int = 3) -> dict | None:
    url = f"{backend}/game/adventure/create"
    payload = {"genre": genre, "players": DEFAULT_PLAYERS, "scale": scale}
    for attempt in range(1, retry + 1):
        try:
            resp = requests.post(url, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            if data.get("error"):
                print(f"  ⚠  API error: {data['error']}")
                return None
            return data
        except requests.exceptions.Timeout:
            print(f"  ⚠  timeout (tentativo {attempt}/{retry})")
            if attempt < retry:
                time.sleep(2 ** attempt)
        except requests.exceptions.HTTPError as e:
            print(f"  ⚠  HTTP {e.response.status_code}: {e}")
            if attempt < retry:
                time.sleep(2 ** attempt)
        except Exception as e:
            print(f"  ⚠  errore: {e}")
            if attempt < retry:
                time.sleep(2 ** attempt)
    return None


def save_adventure(path: pathlib.Path, api_response: dict) -> None:
    """Salva la risposta API nel formato atteso dai file compiled_adventures."""
    out = {
        "adventure_definition": api_response.get("adventure_definition"),
        "runtime_state":        api_response.get("runtime_state"),
        "validation_report":    api_response.get("validation_report"),
    }
    if api_response.get("live_game_state"):
        out["live_game_state"] = api_response["live_game_state"]
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default=DEFAULT_BACKEND,
                        help="URL del backend (default: Render)")
    parser.add_argument("--max", type=int, default=0,
                        help="Numero massimo di avventure da rigenerare (0 = tutte)")
    args = parser.parse_args()

    BACKEND = args.backend.rstrip("/")
    MAX = args.max if args.max > 0 else len(SKELETONS)

    BACKUP.mkdir(parents=True, exist_ok=True)
    print(f"Backend: {BACKEND}")
    print(f"Max avventure: {MAX}")

    ok = 0
    fail = 0

    for path_rel, genre, scale in SKELETONS[:MAX]:
        path = BASE / path_rel
        if not path.exists():
            print(f"[SKIP] {path_rel} — file non trovato")
            continue

        try:
            orig = json.loads(path.read_text())
            orig_title = (orig.get("adventure_definition") or {}).get("title", path.stem)
        except Exception:
            orig_title = path.stem

        if not _is_skeleton(path):
            print(f"[SKIP] {path_rel} — non più skeleton")
            continue

        print(f"\n→ {path_rel}")
        print(f"   Titolo originale: {orig_title}")
        print(f"   Genre={genre}  Scale={scale}")

        backup_path = BACKUP / path_rel.replace("/", "_")
        shutil.copy2(path, backup_path)

        result = rigenera(path_rel, genre, scale, backend=BACKEND)
        if result is None:
            print(f"   ✗ FALLITA")
            fail += 1
            continue

        new_title = (result.get("adventure_definition") or {}).get("title", "?")
        print(f"   ✓ Nuovo titolo: {new_title}")
        save_adventure(path, result)
        ok += 1

        time.sleep(2)

    print(f"\n{'='*50}")
    print(f"Completato: {ok} rigenerati, {fail} falliti")
    print(f"Backup in: {BACKUP}/")
    if ok > 0:
        print("\nComitta e pusha:")
        print("  git add data/compiled_adventures/")
        print(f"  git commit -m 'regen: {ok} avventure skeleton sostituite'")
        print("  git push origin main")


if __name__ == "__main__":
    main()
