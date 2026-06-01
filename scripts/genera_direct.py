#!/usr/bin/env python3
"""
Genera avventure chiamando direttamente le funzioni Python del backend,
senza bisogno di avviare uvicorn o un server HTTP.

Richiede solo ANTHROPIC_API_KEY come variabile d'ambiente.

Esegui dalla root del repo GURPS:
    ANTHROPIC_API_KEY=sk-ant-... python3 scripts/genera_direct.py
    python3 scripts/genera_direct.py --genres fantasy horror --scales compact
    python3 scripts/genera_direct.py --count 2   # 2 avventure per combinazione
"""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import time

# Aggiunge backend/ al path per gli import diretti
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

BASE = pathlib.Path(__file__).resolve().parents[1] / "data" / "compiled_adventures"


def _git_commit_push(message: str) -> None:
    """Commit incrementale: salva i progressi DURANTE la generazione così un eventuale
    timeout del job CI non fa perdere le avventure già completate. Ri-lanciando il
    workflow si riprende (i file già esistenti non vengono rigenerati).
    Attivo solo quando CI_COMMIT=1 (impostato dal workflow); in locale non tocca git."""
    if os.environ.get("CI_COMMIT") != "1":
        return
    try:
        subprocess.run(["git", "add", str(BASE)], check=False)
        if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode == 0:
            return  # niente di nuovo da committare
        subprocess.run(["git", "commit", "-m", message], check=False)
        push = subprocess.run(["git", "push", "origin", "main"])
        if push.returncode != 0:
            # rara collisione non-fast-forward: riallinea e ripeti
            subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=False)
            push = subprocess.run(["git", "push", "origin", "main"])
        if push.returncode != 0:
            print("  ⚠⚠ PUSH FALLITO: avventura salvata su disco ma NON su main. "
                  "Controlla i permessi del GITHUB_TOKEN (serve contents: write).",
                  file=sys.stderr)
    except Exception as e:
        print(f"  ⚠ commit incrementale fallito (non bloccante): {e}")

ALL_GENRES = ["action", "fantasy", "horror", "investigation", "romance", "sci_fi"]
ALL_SCALES = ["compact", "standard", "epic"]

GENRE_FOLDER = {
    "action":        "action",
    "fantasy":       "fantasy",
    "horror":        "horror",
    "investigation": "investigation",
    "romance":       "romance",
    "sci_fi":        "sci_fi",
}

DEFAULT_PLAYERS = [
    {"id": "p1", "name": "Thorin",  "hp": 12, "max_hp": 12, "skills": {"combattimento": 13, "furtività": 11}},
    {"id": "p2", "name": "Alara",   "hp": 10, "max_hp": 10, "skills": {"investigazione": 14, "persuasione": 12}},
    {"id": "p3", "name": "Okafor",  "hp": 11, "max_hp": 11, "skills": {"tecnologia": 13, "percezione": 12}},
]


def _slugify(text: str) -> str:
    text = text.lower().strip()
    for src, dst in [("à","a"),("á","a"),("â","a"),("è","e"),("é","e"),("ê","e"),
                     ("ì","i"),("í","i"),("î","i"),("ò","o"),("ó","o"),("ô","o"),
                     ("ù","u"),("ú","u"),("û","u")]:
        text = text.replace(src, dst)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")[:60]


def _target_path(genre: str, title: str, scale: str, index: int) -> pathlib.Path:
    folder = GENRE_FOLDER.get(genre, genre)
    dest = BASE / folder
    dest.mkdir(parents=True, exist_ok=True)
    if title and title not in ("?", "Avventura generata", ""):
        slug = _slugify(title)
        candidate = dest / f"ai_{slug}.json"
        if not candidate.exists():
            return candidate
        return dest / f"ai_{slug}_{index}.json"
    return dest / f"ai_{genre}_{scale}_{index}.json"


def main():
    parser = argparse.ArgumentParser(description="Genera avventure GURPS direttamente via Python")
    parser.add_argument("--genres", nargs="+", default=ALL_GENRES)
    parser.add_argument("--scales", nargs="+", default=ALL_SCALES)
    parser.add_argument("--count",  type=int,  default=1)
    args = parser.parse_args()

    # Verifica API key prima di importare il backend
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY non impostata. Impossibile generare avventure.")
        sys.exit(1)
    print(f"✅ ANTHROPIC_API_KEY presente ({len(api_key)} caratteri)")

    # Import backend (dopo aver verificato la chiave)
    print("Carico moduli backend...")
    try:
        from App.claude_service import create_adventure
        from App.adventure_compiler import compile_from_raw_structure
        from App.adventure_runtime_store import save_runtime
        from App.adventure_doctor import run_doctor
        from App.runtime_models import AdventureDefinition
        print("✅ Moduli backend caricati\n")
    except ImportError as e:
        print(f"❌ Errore import backend: {e}")
        sys.exit(1)

    genres = [g.lower().replace("-", "_") for g in args.genres]
    scales = [s.lower() for s in args.scales]
    total  = len(genres) * len(scales) * args.count

    print(f"Generi : {', '.join(genres)}")
    print(f"Scale  : {', '.join(scales)}")
    print(f"Totale : {total} avventure\n")

    ok = fail = 0
    saved_paths = []

    for genre in genres:
        for scale in scales:
            for n in range(1, args.count + 1):
                label = f"{genre}/{scale}" + (f" #{n}" if args.count > 1 else "")
                print(f"→ Genero {label} …")

                try:
                    # 1. Genera la bibbia strutturata
                    raw = create_adventure(genre, DEFAULT_PLAYERS, scale=scale)
                    if raw.get("error"):
                        print(f"  ✗ Errore generazione: {raw['error']}\n")
                        fail += 1
                        continue

                    raw["source_mode"] = "ai_generated"
                    title = raw.get("title", "")

                    # 2. Compila nel runtime
                    compiled = compile_from_raw_structure(
                        raw,
                        source_type="raw_text",
                        title=title or "Avventura generata",
                        genre_hint=genre,
                    )
                    definition    = compiled["adventure_definition"]
                    runtime_state = compiled["runtime_state"]

                    # 3. Salva runtime
                    saved = save_runtime(definition, runtime_state, compiled["validation_report"])

                    # 4. Doctor (audit + fix automatico)
                    defn_dict   = saved["adventure_definition"]
                    doctor_result = {"score": 10.0, "findings": [], "score_after": 10.0}
                    try:
                        doctor_result = run_doctor(defn_dict, do_enrich=True)
                        enriched = doctor_result.get("enriched_definition")
                        if enriched:
                            enr_def = AdventureDefinition(**{
                                k: v for k, v in enriched.items()
                                if k in AdventureDefinition.model_fields
                            })
                            enr_def.id = definition.id
                            saved = save_runtime(enr_def, runtime_state, compiled["validation_report"])
                            defn_dict = saved["adventure_definition"]
                    except Exception as de:
                        print(f"  ⚠ Doctor error (non bloccante): {de}")

                    score = doctor_result.get("score_after") or doctor_result.get("score") or "?"

                    # 5. Persisti su file
                    out = {
                        "adventure_definition": defn_dict,
                        "runtime_state":        saved["runtime_state"],
                        "validation_report":    saved["validation_report"],
                        "doctor": {
                            "score":      doctor_result.get("score", 10.0),
                            "score_after": doctor_result.get("score_after"),
                            "findings":   doctor_result.get("findings", []),
                            "auto_fixed": bool(doctor_result.get("enriched_definition")),
                        },
                    }
                    path = _target_path(genre, title, scale, n)
                    path.write_text(json.dumps(out, ensure_ascii=False, indent=2))

                    print(f"  ✓ «{title}» → {path.name}  (score {score})")
                    saved_paths.append(str(path))
                    ok += 1
                    _git_commit_push(f"gen: {path.name} «{title}» score={score} [skip ci]")

                except Exception as e:
                    print(f"  ✗ Eccezione: {type(e).__name__}: {e}\n")
                    import traceback; traceback.print_exc()
                    fail += 1

                time.sleep(2)

    print(f"\n{'='*55}")
    print(f"Completato: {ok} generate, {fail} fallite")
    if saved_paths:
        print("\nFile salvati:")
        for p in saved_paths:
            print(f"  {p}")

    if fail > 0 and ok == 0:
        sys.exit(1)  # Fallisce il workflow CI se nessuna avventura generata


if __name__ == "__main__":
    main()
