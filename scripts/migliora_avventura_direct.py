#!/usr/bin/env python3
"""
Arricchisce avventure ESISTENTI MANTENENDONE la storia (doctor enrichment).

A differenza della generazione/rigenerazione (che creano una storia NUOVA), qui si
applica solo l'arricchimento del "doctor": riempie le piste narrative mancanti,
sviluppa i PNG carenti, completa luoghi/indizi e sistema la struttura. Titolo,
premessa e trama restano invariati (il doctor li usa solo come contesto).

Aggiornamento IN-PLACE di ciascun file (niente duplicati) e preservazione di
runtime_state / live_game_state esistenti.

Richiede ANTHROPIC_API_KEY come variabile d'ambiente.

    # una sola avventura
    python3 scripts/migliora_avventura_direct.py --target fantasy/pdf_lupo_di_kosmar.json
    # tutte
    python3 scripts/migliora_avventura_direct.py --target all
    # tutte di un genere, max 5, saltando quelle già ottime (score >= 7.5)
    python3 scripts/migliora_avventura_direct.py --target all --genre fantasy --max 5 --skip-above 7.5
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
BACKUP = BASE / "_backup_migliora"


def _git_commit_push(message: str) -> None:
    """Commit incrementale solo in CI (CI_COMMIT=1); in locale non tocca git."""
    if os.environ.get("CI_COMMIT") != "1":
        return
    try:
        subprocess.run(["git", "add", str(BASE)], check=False)
        if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode == 0:
            return
        subprocess.run(["git", "commit", "-m", message], check=False)
        push = subprocess.run(["git", "push", "origin", "main"])
        if push.returncode != 0:
            subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=False)
            push = subprocess.run(["git", "push", "origin", "main"])
        if push.returncode != 0:
            print("   ⚠⚠ PUSH FALLITO: avventura salvata su disco ma NON su main. "
                  "Controlla i permessi del GITHUB_TOKEN (serve contents: write).",
                  file=sys.stderr)
    except Exception as e:
        print(f"   ⚠ commit incrementale fallito (non bloccante): {e}")


def _collect_targets(target: str, genre: str | None) -> list[pathlib.Path]:
    if target and target.lower() != "all":
        return [BASE / target]
    files: list[pathlib.Path] = []
    for p in sorted(BASE.rglob("*.json")):
        # salta backup e sottocartelle tecniche (_backup*, _debug_pdf, ...)
        if any(part.startswith("_") for part in p.relative_to(BASE).parts):
            continue
        if genre and p.relative_to(BASE).parts[0] != genre:
            continue
        files.append(p)
    return files


def _enrich_one(path: pathlib.Path, run_doctor, audit, score, AdventureDefinition,
                skip_above: float) -> str:
    """Ritorna una stringa di esito ('ok'/'skip'/'fail')."""
    rel = path.relative_to(BASE).as_posix()
    try:
        data = json.loads(path.read_text())
    except Exception as e:
        print(f"[FAIL] {rel} — JSON illeggibile: {e}")
        return "fail"

    defn_dict = data.get("adventure_definition") or {}
    if not defn_dict:
        print(f"[SKIP] {rel} — nessuna adventure_definition")
        return "skip"

    orig_id = defn_dict.get("id")
    orig_title = defn_dict.get("title", path.stem)

    # Pre-controllo LOCALE (audit/score non chiamano l'AI): salta SENZA spendere
    # chiamate LLM le avventure già abbastanza buone.
    score_before = score(audit(defn_dict))
    if skip_above and isinstance(score_before, (int, float)) and score_before >= skip_above:
        print(f"[SKIP] {rel} — «{orig_title}» già buona (score {score_before} ≥ {skip_above})")
        return "skip"

    result = run_doctor(defn_dict, do_enrich=True)
    enriched = result.get("enriched_definition")
    if not enriched:
        print(f"[SKIP] {rel} — nessun arricchimento prodotto (score {score_before})")
        return "skip"

    enr_def = AdventureDefinition(**{
        k: v for k, v in enriched.items() if k in AdventureDefinition.model_fields
    })
    if orig_id:
        enr_def.id = orig_id

    BACKUP.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, BACKUP / rel.replace("/", "_"))

    data["adventure_definition"] = enr_def.model_dump()
    score_after = result.get("score_after")
    if isinstance(data.get("validation_report"), dict) and score_after is not None:
        data["validation_report"]["doctor_score"] = score_after
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    threads_before = len(defn_dict.get("story_threads") or [])
    threads_after = len(enr_def.story_threads or [])
    print(f"[OK]   {rel} — «{enr_def.title}»  score {score_before} → {score_after}  "
          f"(piste {threads_before}→{threads_after})")
    _git_commit_push(
        f"improve: {rel} «{enr_def.title}» score {score_before}→{score_after} [skip ci]"
    )
    return "ok"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="all",
                        help="'all' oppure un percorso relativo (es: fantasy/pdf_lupo_di_kosmar.json)")
    parser.add_argument("--genre", default="", help="Filtro di genere quando --target all")
    parser.add_argument("--max", type=int, default=0, help="Numero massimo di avventure (0 = tutte)")
    parser.add_argument("--skip-above", type=float, default=0.0,
                        help="Salta le avventure già con score >= questo valore (0 = non saltare)")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY non impostata.")
        sys.exit(1)
    print(f"✅ ANTHROPIC_API_KEY presente ({len(api_key)} caratteri)")

    print("Carico moduli backend...")
    try:
        from App.adventure_doctor import run_doctor, audit, score
        from App.runtime_models import AdventureDefinition
        print("✅ Moduli caricati\n")
    except ImportError as e:
        print(f"❌ Errore import: {e}")
        sys.exit(1)

    targets = _collect_targets(args.target, args.genre or None)
    if args.max > 0:
        targets = targets[:args.max]
    print(f"Avventure da processare: {len(targets)}"
          + (f"  (skip se score ≥ {args.skip_above})" if args.skip_above else ""))

    ok = skip = fail = 0
    for path in targets:
        if not path.exists():
            print(f"[FAIL] {path} — file non trovato")
            fail += 1
            continue
        outcome = _enrich_one(path, run_doctor, audit, score, AdventureDefinition, args.skip_above)
        ok += outcome == "ok"
        skip += outcome == "skip"
        fail += outcome == "fail"
        time.sleep(1)

    print(f"\n{'='*50}")
    print(f"Completato: {ok} arricchite, {skip} saltate, {fail} fallite")
    if fail > 0 and ok == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
