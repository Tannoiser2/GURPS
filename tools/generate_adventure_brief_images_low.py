#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.generate_adventure_brief_catalog import brief_order, image_for, json_files, ordered_files, title_for
from tools.generate_adventure_brief_sample_page import BRIEF, parse_brief


IMAGE_GEN = Path.home() / ".codex" / "skills" / ".system" / "imagegen" / "scripts" / "image_gen.py"
TMP_DIR = ROOT / "tmp" / "imagegen"
ASSET_DIR = ROOT / "data" / "compiled_adventures" / "_catalogo" / "assets"


def safe_prompt(title: str, prompt: str) -> str:
    base = prompt.strip()
    if not base:
        base = f"Crea un'immagine di copertina per l'avventura «{title}»."
    replacements = [
        (r"\bcorpi?\b[^.]*\.", "tracce inquietanti dell'incidente sono visibili nell'ambiente."),
        (r"\bcadavere\b[^.]*\.", "un evento misterioso ha lasciato la scena sotto indagine."),
        (r"\bmorto\b", "scomparso"),
        (r"\bmorta\b", "scomparsa"),
        (r"\bmorti\b", "scomparsi"),
        (r"\bmorte\b", "scomparse"),
        (r"\buccisioni\b", "sparizioni"),
        (r"\bsventrato\b", "trovato in circostanze inquietanti"),
        (r"\bsangue\b", "tracce scure"),
    ]
    for pattern, replacement in replacements:
        base = re.sub(pattern, replacement, base, flags=re.IGNORECASE)
    return "\n".join(
        [
            "Use case: illustration-story",
            "Asset type: square thumbnail artwork for a printable adventure catalog card",
            "Primary request:",
            base,
            "Composition: square thumbnail, strong readable silhouette, clear focal point, suitable for small print.",
            "Constraints: no text, no logos, no watermark, no gore, no bodies, no graphic injury, no readable screens or documents.",
        ]
    )


def build_jobs(limit: int | None, offset: int, force: bool) -> list[dict[str, str]]:
    brief = parse_brief(BRIEF)
    files = ordered_files(json_files(), brief_order(BRIEF))
    jobs: list[dict[str, str]] = []
    for json_path in files:
        title = title_for(json_path)
        out_path = image_for(json_path)
        if out_path.exists() and not force:
            continue
        prompt = safe_prompt(title, brief.get(title, {}).get("prompt", ""))
        jobs.append(
            {
                "prompt": prompt,
                "use_case": "illustration-story",
                "style": "cinematic adventure thumbnail",
                "composition": "square thumbnail, readable at small size",
                "constraints": "no text, no logos, no watermark, no gore, no bodies, no graphic injury",
                "quality": "low",
                "size": "1024x1024",
                "out": out_path.name,
            }
        )
    if offset:
        jobs = jobs[offset:]
    if limit is not None:
        jobs = jobs[:limit]
    return jobs


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate low-quality preview images for the adventure brief catalog.")
    parser.add_argument("--limit", type=int, default=6, help="Maximum number of missing images to generate.")
    parser.add_argument("--offset", type=int, default=0, help="Skip this many missing images.")
    parser.add_argument("--concurrency", type=int, default=2, help="Batch generation concurrency.")
    parser.add_argument("--force", action="store_true", help="Regenerate images even if assets already exist.")
    parser.add_argument("--dry-run", action="store_true", help="Prepare JSONL and print the CLI command without API calls.")
    args = parser.parse_args()

    if not IMAGE_GEN.exists():
        print(f"CLI image_gen.py non trovato: {IMAGE_GEN}")
        return 1

    jobs = build_jobs(args.limit, args.offset, args.force)
    if not jobs:
        print("Nessuna immagine da generare.")
        return 0

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    batch_path = TMP_DIR / "adventure_brief_low_batch.jsonl"
    batch_path.write_text("\n".join(json.dumps(job, ensure_ascii=False) for job in jobs) + "\n", encoding="utf-8")

    cmd = [
        sys.executable,
        str(IMAGE_GEN),
        "generate-batch",
        "--input",
        str(batch_path),
        "--out-dir",
        str(ASSET_DIR),
        "--concurrency",
        str(args.concurrency),
    ]
    if args.dry_run:
        print(f"Job pronti: {len(jobs)}")
        print(f"JSONL: {batch_path.relative_to(ROOT)}")
        print("Comando:")
        print(" ".join(cmd))
        return 0

    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY non impostata. Impostala nell'ambiente e rilancia, oppure usa --dry-run.")
        return 2

    print(f"Genero {len(jobs)} immagini preview low...")
    return subprocess.run(cmd, cwd=ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
