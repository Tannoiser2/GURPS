#!/usr/bin/env python3
"""
Genera nuove avventure chiamando il backend (locale o su Render).

Per ogni combinazione genere × scala richiesta, chiama POST /game/adventure/create
e salva il risultato in data/compiled_adventures/<genre>/.

Esegui dalla root del repo GURPS:
    python3 scripts/genera_avventure.py                                     # tutte: 6 generi × 3 scale
    python3 scripts/genera_avventure.py --genres action fantasy             # solo action e fantasy
    python3 scripts/genera_avventure.py --scales compact                    # solo compact
    python3 scripts/genera_avventure.py --backend http://127.0.0.1:8765     # backend locale
    python3 scripts/genera_avventure.py --count 2                           # 2 avventure per combinazione

Requisiti:
    pip install requests
"""

import argparse
import json
import pathlib
import re
import time

import requests

DEFAULT_BACKEND = "https://gurps-f93w.onrender.com"
BASE = pathlib.Path("data/compiled_adventures")

DEFAULT_PLAYERS = [
    {"id": "p1", "name": "Thorin",  "hp": 12, "max_hp": 12, "skills": {"combattimento": 13, "furtività": 11}},
    {"id": "p2", "name": "Alara",   "hp": 10, "max_hp": 10, "skills": {"investigazione": 14, "persuasione": 12}},
    {"id": "p3", "name": "Okafor",  "hp": 11, "max_hp": 11, "skills": {"tecnologia": 13, "percezione": 12}},
]

ALL_GENRES = ["action", "fantasy", "horror", "investigation", "romance", "sci_fi"]
ALL_SCALES = ["compact", "standard", "epic"]

# Mappa genre → cartella sul filesystem
GENRE_FOLDER = {
    "action":        "action",
    "fantasy":       "fantasy",
    "horror":        "horror",
    "investigation": "investigation",
    "romance":       "romance",
    "sci_fi":        "sci_fi",
}


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[àáâã]", "a", text)
    text = re.sub(r"[èéêë]", "e", text)
    text = re.sub(r"[ìíîï]", "i", text)
    text = re.sub(r"[òóôõ]", "o", text)
    text = re.sub(r"[ùúûü]", "u", text)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = text.strip("_")
    return text[:60]


def _target_path(genre: str, title: str, scale: str, index: int) -> pathlib.Path:
    folder = GENRE_FOLDER.get(genre, genre)
    dest = BASE / folder
    dest.mkdir(parents=True, exist_ok=True)
    if title and title not in ("?", "Avventura generata", ""):
        slug = _slugify(title)
        candidate = dest / f"ai_{slug}.json"
        if not candidate.exists():
            return candidate
        # file già esiste: aggiungi suffisso
        return dest / f"ai_{slug}_{index}.json"
    # fallback: usa schema genere_scala
    return dest / f"ai_{genre}_{scale}_{index}.json"


def genera(genre: str, scale: str, backend: str, retry: int = 3) -> dict | None:
    url = f"{backend}/game/adventure/create"
    payload = {"genre": genre, "players": DEFAULT_PLAYERS, "scale": scale}
    for attempt in range(1, retry + 1):
        try:
            resp = requests.post(url, json=payload, timeout=180)
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
    out = {
        "adventure_definition": api_response.get("adventure_definition"),
        "runtime_state":        api_response.get("runtime_state"),
        "validation_report":    api_response.get("validation_report"),
    }
    if api_response.get("live_game_state"):
        out["live_game_state"] = api_response["live_game_state"]
    if api_response.get("doctor"):
        out["doctor"] = api_response["doctor"]
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default=DEFAULT_BACKEND)
    parser.add_argument("--genres",  nargs="+", default=ALL_GENRES,
                        help="Generi da generare (default: tutti)")
    parser.add_argument("--scales",  nargs="+", default=ALL_SCALES,
                        help="Scale da generare: compact standard epic (default: tutte)")
    parser.add_argument("--count",   type=int, default=1,
                        help="Numero di avventure per combinazione genere×scala (default: 1)")
    args = parser.parse_args()

    backend = args.backend.rstrip("/")
    genres  = [g.lower().replace("-", "_") for g in args.genres]
    scales  = [s.lower() for s in args.scales]
    count   = max(1, args.count)

    total = len(genres) * len(scales) * count
    print(f"Backend : {backend}")
    print(f"Generi  : {', '.join(genres)}")
    print(f"Scale   : {', '.join(scales)}")
    print(f"Totale  : {total} avventure da generare")
    print()

    ok = fail = 0
    results = []

    for genre in genres:
        for scale in scales:
            for n in range(1, count + 1):
                label = f"{genre}/{scale}" + (f" #{n}" if count > 1 else "")
                print(f"→ Genero {label} …")
                data = genera(genre, scale, backend)
                if data is None:
                    print(f"  ✗ FALLITA\n")
                    fail += 1
                    continue

                title = (data.get("adventure_definition") or {}).get("title", "")
                doctor = data.get("doctor", {})
                score  = doctor.get("score_after") or doctor.get("score") or "?"

                path = _target_path(genre, title, scale, n)
                save_adventure(path, data)

                print(f"  ✓ «{title}» → {path.name}  (score {score})")
                results.append(str(path))
                ok += 1
                time.sleep(3)  # pausa tra chiamate

    print(f"\n{'='*55}")
    print(f"Completato: {ok} generate, {fail} fallite")
    if ok > 0:
        print("\nFile salvati:")
        for r in results:
            print(f"  {r}")
        print("\nComitta e pusha:")
        print("  git add data/compiled_adventures/")
        print(f"  git commit -m 'gen: {ok} nuove avventure ({len(genres)} generi × {len(scales)} scale)'")
        print("  git push origin main")


if __name__ == "__main__":
    main()
