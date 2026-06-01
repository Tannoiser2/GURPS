#!/usr/bin/env python3
"""
Rigenera le avventure AI "skeleton" (score 50, location placeholder)
chiamando direttamente le funzioni Python del backend, senza uvicorn.

Richiede solo ANTHROPIC_API_KEY come variabile d'ambiente.

Esegui dalla root del repo GURPS:
    ANTHROPIC_API_KEY=sk-ant-... python3 scripts/rigenera_skeleton_direct.py
    python3 scripts/rigenera_skeleton_direct.py --max 5
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

BASE   = pathlib.Path(__file__).resolve().parents[1] / "data" / "compiled_adventures"
BACKUP = BASE / "_backup_skeleton"


def _git_commit_push(message: str) -> None:
    """Commit incrementale: salva i progressi DURANTE la generazione così un eventuale
    timeout del job CI non fa perdere le avventure già completate. Ri-lanciando il
    workflow si riprende dalle avventure mancanti (le rigenerate non sono più skeleton).
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
            print("   ⚠⚠ PUSH FALLITO: avventura salvata su disco ma NON su main. "
                  "Controlla i permessi del GITHUB_TOKEN (serve contents: write).",
                  file=sys.stderr)
    except Exception as e:
        print(f"   ⚠ commit incrementale fallito (non bloccante): {e}")

DEFAULT_PLAYERS = [
    {"id": "p1", "name": "Thorin",  "hp": 12, "max_hp": 12, "skills": {"combattimento": 13, "furtività": 11}},
    {"id": "p2", "name": "Alara",   "hp": 10, "max_hp": 10, "skills": {"investigazione": 14, "persuasione": 12}},
    {"id": "p3", "name": "Okafor",  "hp": 11, "max_hp": 11, "skills": {"tecnologia": 13, "percezione": 12}},
]

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=0,
                        help="Numero massimo di avventure da rigenerare (0 = tutte)")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY non impostata.")
        sys.exit(1)
    print(f"✅ ANTHROPIC_API_KEY presente ({len(api_key)} caratteri)")

    print("Carico moduli backend...")
    try:
        from App.claude_service import create_adventure
        from App.adventure_compiler import compile_from_raw_structure
        from App.adventure_runtime_store import save_runtime
        from App.adventure_doctor import run_doctor
        from App.runtime_models import AdventureDefinition
        print("✅ Moduli caricati\n")
    except ImportError as e:
        print(f"❌ Errore import: {e}")
        sys.exit(1)

    MAX = args.max if args.max > 0 else len(SKELETONS)
    BACKUP.mkdir(parents=True, exist_ok=True)
    print(f"Max avventure: {MAX}")

    ok = fail = 0

    for path_rel, genre, scale in SKELETONS[:MAX]:
        path = BASE / path_rel
        if not path.exists():
            print(f"[SKIP] {path_rel} — file non trovato")
            continue

        try:
            orig_title = (json.loads(path.read_text()).get("adventure_definition") or {}).get("title", path.stem)
        except Exception:
            orig_title = path.stem

        if not _is_skeleton(path):
            print(f"[SKIP] {path_rel} — non più skeleton")
            continue

        print(f"\n→ {path_rel}  (era: «{orig_title}»)")

        backup_path = BACKUP / path_rel.replace("/", "_")
        shutil.copy2(path, backup_path)

        try:
            raw = create_adventure(genre, DEFAULT_PLAYERS, scale=scale)
            if raw.get("error"):
                print(f"   ✗ Errore generazione: {raw['error']}")
                fail += 1
                continue

            raw["source_mode"] = "ai_generated"
            title = raw.get("title", "")

            compiled = compile_from_raw_structure(
                raw,
                source_type="raw_text",
                title=title or "Avventura generata",
                genre_hint=genre,
            )
            definition    = compiled["adventure_definition"]
            runtime_state = compiled["runtime_state"]
            saved = save_runtime(definition, runtime_state, compiled["validation_report"])
            defn_dict = saved["adventure_definition"]

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
                print(f"   ⚠ Doctor error: {de}")

            score = doctor_result.get("score_after") or doctor_result.get("score") or "?"
            out = {
                "adventure_definition": defn_dict,
                "runtime_state":        saved["runtime_state"],
                "validation_report":    saved["validation_report"],
            }
            path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
            print(f"   ✓ «{title}»  score={score}")
            ok += 1
            _git_commit_push(f"regen: {path_rel} «{title}» score={score} [skip ci]")

        except Exception as e:
            print(f"   ✗ Eccezione: {type(e).__name__}: {e}")
            import traceback; traceback.print_exc()
            fail += 1

        time.sleep(2)

    print(f"\n{'='*50}")
    print(f"Completato: {ok} rigenerati, {fail} falliti")
    if fail > 0 and ok == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
