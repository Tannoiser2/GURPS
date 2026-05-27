#!/usr/bin/env python3
"""
Batch-compila i PDF in gurps_avventure/ non ancora presenti in data/compiled_adventures/.

Uso:
    cd /Users/stefan0/Desktop/GURPS/backend
    python3 -u scripts/batch_compile_pdfs.py [--resume]
"""

from __future__ import annotations

import json
import re
import sys
import time
import traceback
from pathlib import Path

BACKEND_DIR    = Path(__file__).resolve().parents[1]
PROJECT_ROOT   = BACKEND_DIR.parent
ADVENTURES_DIR = PROJECT_ROOT / "gurps_avventure"
RESULTS_FILE   = BACKEND_DIR / "scripts" / "batch_compile_results.json"

sys.path.insert(0, str(BACKEND_DIR))

from App.adventure_compiler        import compile_pdf_pages_to_runtime
from App.adventure_validator       import check_raw_compilation_quality
from App.adventure_doctor          import run_doctor
from App.adventure_runtime_store   import save_runtime
from App.runtime_models            import AdventureDefinition, AdventureRuntimeState

# ── PDF già correttamente compilati (da non riprocessare) ─────────────────────
ALREADY_COMPILED_STEMS = {
    "Beast-of-Black-Keep-GURPS",
    "Flaw-in-the-Lens-GURPS",
    "Gotham-39-GURPS-1",
    "Mound-in-the-Yard-GURPS",
    "Never-Forget-to-Die-GURPS",
    "RailgunRoad-GURPS",
    "Scourge-of-Triton-GURPS",
    "Spectral-Tides-GURPS",
    "Third-Hall-of-Uzrah-GURPS",
    "Thrusher-Manor-GURPS",
}

# ── testo boilerplate da ignorare come titolo ─────────────────────────────────
_BAD_TITLE_PATTERNS = re.compile(
    r"^(about\s+the\s+adventure|by\s+\w|gurps|introduction|table\s+of\s+contents|"
    r"adventure\s+overview|preface|foreword|credits|legal|license|ogl|open\s+game)",
    re.IGNORECASE,
)

_LIGATURES = str.maketrans({"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"})


def _clean_pdf_text(text: str) -> str:
    text = text.translate(_LIGATURES)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _title_from_filename(pdf_path: Path) -> str:
    """Ricava un titolo pulito dal nome file, rimuovendo '-GURPS', '-1', '-2' ecc."""
    stem = pdf_path.stem
    stem = re.sub(r"[-_]GURPS[-_]?\d*$", "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"[-_]\d+$", "", stem)
    title = stem.replace("-", " ").replace("_", " ").strip()
    # Title case se tutto lowercase/uppercase
    if title == title.lower() or title == title.upper():
        title = title.title()
    return title


_GENERIC_STEMS = re.compile(r"^[A-Z]{2,5}\d{2,}", re.IGNORECASE)  # es. SJG37-2103


def _extract_title_from_pdf_pages(text_pages: list[str], pdf_path: Path) -> str:
    """
    Usa il filename come titolo primario (è sempre il titolo reale).
    Ricorre al testo del PDF solo se il filename è generico (es. 'SJG37-2103')
    o per PDF italiani senza il suffisso GURPS.
    """
    filename_title = _title_from_filename(pdf_path)

    # Se il filename già dà un buon titolo (non generico, >= 2 parole), usalo
    if not _GENERIC_STEMS.match(pdf_path.stem) and len(filename_title.split()) >= 2:
        return filename_title

    # Per filename generici tentiamo estrazione dal contenuto
    for page in text_pages[:3]:
        for line in page.splitlines()[:15]:
            line = line.strip()
            if len(line) < 4 or len(line) > 80:
                continue
            if _BAD_TITLE_PATTERNS.match(line):
                continue
            if re.search(r"[©®]\s*\d{4}|www\.|ISBN|page \d", line, re.IGNORECASE):
                continue
            if not re.search(r"[A-Za-zÀ-ÿ]{3}", line):
                continue
            words = line.split()
            if len(words) >= 2:
                return line

    return filename_title


def extract_pdf_text(path: Path) -> tuple[list[str], int]:
    try:
        import pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            raw_pages = [p.extract_text() or "" for p in pdf.pages]
    except ImportError:
        import pypdf as _pypdf
        reader = _pypdf.PdfReader(str(path))
        raw_pages = [p.extract_text() or "" for p in reader.pages]

    raw_chars = sum(len(p) for p in raw_pages)
    cleaned = [_clean_pdf_text(p) for p in raw_pages if _clean_pdf_text(p).strip()]
    return cleaned, raw_chars


def compile_one(pdf_path: Path) -> dict:
    start = time.time()
    print(f"\n{'─'*60}", flush=True)
    print(f"📄  {pdf_path.name}", flush=True)

    text_pages, raw_chars = extract_pdf_text(pdf_path)
    if not text_pages:
        print("    ⚠ Nessun testo estratto", flush=True)
        return {"status": "error", "reason": "Nessun testo estratto dal PDF"}

    print(f"    {len(text_pages)} pagine, {raw_chars} caratteri", flush=True)

    title = _extract_title_from_pdf_pages(text_pages, pdf_path)
    print(f"    Titolo: {title!r}", flush=True)

    compiled = compile_pdf_pages_to_runtime(
        text_pages,
        genre_hint=None,
        runtime_profile_hint=None,
        title=title,
    )

    quality_gate = check_raw_compilation_quality(compiled.get("adventure_definition") or {})
    print(f"    Quality gate: passed={quality_gate['passed']} score={quality_gate['score']}", flush=True)
    if not quality_gate["passed"]:
        issues = "; ".join(quality_gate.get("critical", []))
        print(f"    ❌ Quality fail: {issues}", flush=True)
        return {"status": "quality_fail", "reason": issues, "quality_gate": quality_gate}

    if compiled.get("validation_report") is None:
        compiled["validation_report"] = {}
    compiled["validation_report"]["quality_gate"] = quality_gate

    try:
        defn_dict = compiled["adventure_definition"]
        # run_doctor si aspetta un dict
        if hasattr(defn_dict, "model_dump"):
            defn_dict = defn_dict.model_dump()
        doctor_result = run_doctor(defn_dict, do_enrich=True)
        enriched = doctor_result.get("enriched_definition")
        if enriched:
            # enriched può essere dict o oggetto
            if hasattr(enriched, "model_dump"):
                enriched = enriched.model_dump()
            compiled["adventure_definition"] = enriched
            print(f"    Doctor: fix {doctor_result.get('score',0):.1f}→{doctor_result.get('score_after',0):.1f}", flush=True)
        else:
            print(f"    Doctor: score {doctor_result.get('score',0):.1f} ok", flush=True)
    except Exception as e:
        print(f"    Doctor: errore ({e})", flush=True)

    definition    = AdventureDefinition(**compiled["adventure_definition"])
    runtime_state = AdventureRuntimeState(**compiled["runtime_state"])
    save_runtime(definition, runtime_state, compiled["validation_report"])

    elapsed = time.time() - start
    print(f"    ✅  [{definition.genre}] {definition.title}  ({elapsed:.0f}s)", flush=True)
    return {"status": "ok", "id": definition.id, "title": definition.title,
            "genre": definition.genre or "", "elapsed": round(elapsed, 1)}


def main():
    resume = "--resume" in sys.argv

    prev_results: dict[str, dict] = {}
    if resume and RESULTS_FILE.exists():
        prev_results = json.loads(RESULTS_FILE.read_text())
        print(f"Resume: {len(prev_results)} già processati")

    pdfs = sorted(
        p for p in ADVENTURES_DIR.glob("*.pdf")
        if p.stem not in ALREADY_COMPILED_STEMS
    )
    print(f"\n=== Batch compile: {len(pdfs)} PDF da processare ===")

    results: dict[str, dict] = {}
    ok = fail = skip = 0

    for i, pdf in enumerate(pdfs, 1):
        key = pdf.stem
        if resume and key in prev_results and prev_results[key].get("status") == "ok":
            print(f"[{i:2}/{len(pdfs)}] ↷ {pdf.name}", flush=True)
            results[key] = prev_results[key]
            skip += 1
            continue

        print(f"\n[{i:2}/{len(pdfs)}]", flush=True)
        try:
            result = compile_one(pdf)
        except Exception as e:
            result = {"status": "error", "reason": str(e), "tb": traceback.format_exc()}
            print(f"    ❌ ERRORE: {e}", flush=True)

        results[key] = result
        ok += 1 if result["status"] == "ok" else 0
        fail += 1 if result["status"] != "ok" else 0
        RESULTS_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2))

    print(f"\n{'='*60}")
    print(f"Completato: ✅ {ok} ok  ❌ {fail} errori  ↷ {skip} saltati")

    from App.adventure_runtime_store import list_runtimes
    all_rows = list_runtimes()
    print(f"\n=== Archivio finale: {len(all_rows)} avventure ===")
    for row in all_rows:
        m = "✅" if row["playable"] else "⚠"
        print(f"  {m} [{row['genre_folder']:>14}] {row['title']}")


if __name__ == "__main__":
    main()
