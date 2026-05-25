"""Dry-run del compiler P0+P1 su un PDF reale.

Compila lo stesso PDF due volte (baseline regex-only vs LLM-enabled) e stampa
un confronto strutturato. Pensato per girare a mano dalla directory backend/.

Uso:
    cd backend
    python3 scripts/dry_run_p0_p1.py "../gurps_avventure/Gotham-39-GURPS-1.pdf"

Richiede che ``backend/.env`` esponga ``ANTHROPIC_API_KEY`` (o ``OPENAI_API_KEY``).
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path


def _load_pdf_pages(pdf_path: Path) -> list[str]:
    import pdfplumber
    pages: list[str] = []
    with pdfplumber.open(io.BytesIO(pdf_path.read_bytes())) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages.append(text)
    return pages


def _compile(pages: list[str], title: str, *, enable_llm: bool) -> dict:
    # Forziamo i flag prima dell'import di claude_service in modo che il primo
    # _text_provider_available() veda lo stato voluto. Usiamo reload per
    # essere certi che il modulo legga le env aggiornate.
    if enable_llm:
        os.environ["GURPS_ENABLE_LLM_CLASSIFIER"] = "1"
        os.environ["GURPS_ENABLE_LLM_EXTRACTORS"] = "1"
    else:
        os.environ.pop("GURPS_ENABLE_LLM_CLASSIFIER", None)
        os.environ.pop("GURPS_ENABLE_LLM_EXTRACTORS", None)

    from App.adventure_compiler import compile_pdf_pages_to_runtime
    start = time.time()
    compiled = compile_pdf_pages_to_runtime(pages, title=title)
    elapsed = time.time() - start
    compiled["__elapsed_seconds"] = round(elapsed, 2)
    return compiled


def _summary(compiled: dict) -> dict:
    definition = compiled["adventure_definition"]
    clue_types = Counter((c.type or "physical_evidence") for c in definition.clues)
    clue_examples = [
        {
            "id": c.id,
            "label": c.label[:90],
            "type": c.type,
            "source_location": c.source_location[:60],
            "llm_extracted": getattr(c, "llm_extracted", False),
        }
        for c in definition.clues[:6]
    ]
    actor_examples = [
        {
            "name": a.name,
            "role": a.role,
            "goal": a.goal[:120],
            "fear": a.fear[:100],
            "pressure_medium": (a.pressure_response or {}).get("medium", ""),
            "llm_enriched": getattr(a, "llm_enriched", False),
        }
        for a in definition.actors[:6]
    ]
    revelation_examples = [
        {
            "statement": r.statement[:120],
            "required_clues": r.required_clues,
            "required_evidence_kinds": r.required_evidence_kinds,
            "minimum_independent_kinds": r.minimum_independent_kinds,
            "red_herring_clues": r.red_herring_clues,
            "llm_generated": getattr(r, "llm_generated", False),
        }
        for r in definition.revelations[:5]
    ]
    return {
        "elapsed_seconds": compiled.get("__elapsed_seconds"),
        "revelation_examples": revelation_examples,
        "genre": definition.genre,
        "archetype_primary": definition.archetype_profile.get("primary_archetype"),
        "archetype_source": definition.archetype_profile.get("source"),
        "archetype_confidence": definition.archetype_profile.get("confidence"),
        "archetype_secondary": definition.archetype_profile.get("secondary_archetypes"),
        "tone": definition.tone or (definition.archetype_profile.get("llm_metadata") or {}).get("tone"),
        "counts": {
            "locations": len(definition.locations),
            "clues": len(definition.clues),
            "clue_types": dict(clue_types),
            "actors": len(definition.actors),
            "factions": len(definition.factions),
            "event_clocks": len(definition.event_clocks),
            "revelations": len(definition.revelations),
        },
        "clue_examples": clue_examples,
        "actor_examples": actor_examples,
        "llm_reason": definition.archetype_profile.get("reason"),
    }


def _print_block(title: str, summary: dict) -> None:
    print(f"\n{'='*72}\n{title}\n{'='*72}")
    print(f"elapsed: {summary['elapsed_seconds']}s")
    print(f"genre: {summary['genre']}")
    print(f"archetype: {summary['archetype_primary']} (conf={summary['archetype_confidence']}, src={summary['archetype_source']})")
    print(f"secondary: {summary['archetype_secondary']}")
    print(f"tone: {summary['tone']}")
    print(f"reason: {summary['llm_reason']}")
    print(f"counts: {json.dumps(summary['counts'], ensure_ascii=False)}")
    print("\nclue examples:")
    for c in summary["clue_examples"]:
        print(f"  - [{c['type']:18s}] {c['label']!r}  @ {c['source_location']!r}  llm={c['llm_extracted']}")
    print("\nrevelations (deduction graph):")
    for r in summary["revelation_examples"]:
        print(f"  - {r['statement']!r}  llm={r['llm_generated']}")
        if r["required_evidence_kinds"]:
            print(f"      kinds: {r['required_evidence_kinds']}  min_independent: {r['minimum_independent_kinds']}")
        if r["required_clues"]:
            print(f"      requires: {r['required_clues']}")
        if r["red_herring_clues"]:
            print(f"      red_herrings: {r['red_herring_clues']}")
    print("\nactor examples:")
    for a in summary["actor_examples"]:
        print(f"  - {a['name']!r}  role={a['role']}  llm={a['llm_enriched']}")
        if a["goal"]:
            print(f"      goal: {a['goal']}")
        if a["fear"]:
            print(f"      fear: {a['fear']}")
        if a["pressure_medium"]:
            print(f"      pressure[medium]: {a['pressure_medium']}")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    pdf_path = Path(argv[1]).expanduser().resolve()
    if not pdf_path.is_file():
        print(f"PDF non trovato: {pdf_path}")
        return 2

    title = pdf_path.stem.replace("-", " ").replace("_", " ")
    print(f"Loading PDF: {pdf_path.name}")
    pages = _load_pdf_pages(pdf_path)
    print(f"Pages extracted: {len(pages)}, total chars: {sum(len(p) for p in pages)}")

    baseline = _compile(pages, title, enable_llm=False)
    _print_block("BASELINE — regex only (P0 attivo, no LLM)", _summary(baseline))

    print("\n[running LLM compile — può richiedere 30-60s]")
    llm = _compile(pages, title, enable_llm=True)
    _print_block("WITH LLM — classifier + extractors", _summary(llm))

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
