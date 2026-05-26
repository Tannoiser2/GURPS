#!/usr/bin/env python3
"""
JSON Doctor — CLI tool for auditing and enriching GURPS adventure JSON files.

Usage:
  python -m tools.json_doctor audit [FILE_OR_DIR]
  python -m tools.json_doctor enrich FILE [--all] [--dry-run]
  python -m tools.json_doctor validate [FILE_OR_DIR]
  python -m tools.json_doctor report [FILE_OR_DIR]
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import List

from .rules import audit, score, Finding
from .validator import validate_file
from .enricher import enrich

# Default path relative to this file
_DEFAULT_DIR = Path(__file__).parent.parent.parent / "data" / "compiled_adventures"

SEVERITY_COLOR = {
    "critical": "\033[91m",  # red
    "warning":  "\033[93m",  # yellow
    "info":     "\033[94m",  # blue
}
RESET = "\033[0m"
BOLD = "\033[1m"


def _color(text: str, color: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"{color}{text}{RESET}"


def _load_raw(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_json(path: Path) -> dict:
    """Load JSON and unwrap adventure_definition wrapper if present."""
    raw = _load_raw(path)
    if "adventure_definition" in raw:
        return raw["adventure_definition"]
    return raw


def _find_json_files(target: Path) -> List[Path]:
    if target.is_file():
        return [target]
    return sorted(target.glob("*.json"))


def _print_findings(findings: List[Finding], verbose: bool = True) -> None:
    grouped = {}
    for f in findings:
        grouped.setdefault(f.severity, []).append(f)

    for sev in ("critical", "warning", "info"):
        items = grouped.get(sev, [])
        if not items:
            continue
        color = SEVERITY_COLOR[sev]
        print(f"\n  {_color(sev.upper(), color)} ({len(items)})")
        for f in items:
            msg = f"    [{f.category}] {f.message}"
            if verbose and f.fix_hint:
                msg += f"\n      → {f.fix_hint}"
            print(msg)


def cmd_validate(args) -> int:
    target = Path(args.path) if args.path else _DEFAULT_DIR
    files = _find_json_files(target)
    if not files:
        print(f"Nessun file JSON trovato in: {target}")
        return 1

    all_ok = True
    for path in files:
        ok, errors = validate_file(path)
        status = _color("✓", "\033[92m") if ok else _color("✗", "\033[91m")
        print(f"{status} {path.name}")
        if not ok:
            all_ok = False
            for e in errors:
                print(f"   • {e}")

    return 0 if all_ok else 1


def cmd_audit(args) -> int:
    target = Path(args.path) if args.path else _DEFAULT_DIR
    files = _find_json_files(target)
    if not files:
        print(f"Nessun file JSON trovato in: {target}")
        return 1

    verbose = not args.brief
    results = []

    for path in files:
        try:
            data = _load_json(path)
        except Exception as e:
            print(f"{_color('ERROR', SEVERITY_COLOR['critical'])} {path.name}: {e}")
            continue

        findings = audit(data)
        s = score(findings)
        results.append((path.name, s, findings))

    # Sort by score ascending (worst first)
    results.sort(key=lambda x: x[1])

    print(f"\n{BOLD}=== AUDIT REPORT — {len(results)} avventure ==={RESET}\n")
    for name, s, findings in results:
        score_color = "\033[92m" if s >= 8 else ("\033[93m" if s >= 5 else "\033[91m")
        print(f"{_color(f'{s:4.1f}', score_color)}  {BOLD}{name}{RESET}  ({len(findings)} findings)")
        if findings:
            _print_findings(findings, verbose=verbose)
        print()

    avg = sum(r[1] for r in results) / len(results) if results else 0
    print(f"{BOLD}Score medio: {avg:.1f}/10{RESET}")
    criticals = sum(1 for _, _, fs in results for f in fs if f.severity == "critical")
    warnings  = sum(1 for _, _, fs in results for f in fs if f.severity == "warning")
    print(f"Totale: {_color(str(criticals), SEVERITY_COLOR['critical'])} critici, "
          f"{_color(str(warnings), SEVERITY_COLOR['warning'])} warning\n")

    return 0


def cmd_enrich(args) -> int:
    target = Path(args.path) if args.path else None

    if args.all:
        files = _find_json_files(_DEFAULT_DIR)
    elif target:
        files = _find_json_files(target)
    else:
        print("Specifica un file o usa --all per arricchire tutte le avventure")
        return 1

    if not files:
        print("Nessun file trovato")
        return 1

    dry_run = args.dry_run
    backup = not args.no_backup

    for path in files:
        print(f"\n{BOLD}→ {path.name}{RESET}")
        try:
            raw = _load_raw(path)
        except Exception as e:
            print(f"  Errore lettura: {e}")
            continue

        # Unwrap to get the adventure data
        is_wrapped = "adventure_definition" in raw
        data = raw["adventure_definition"] if is_wrapped else raw

        findings = audit(data)
        s = score(findings)
        print(f"  Score attuale: {s:.1f}/10, {len(findings)} findings")

        if s >= 9.0 and not args.force:
            print(f"  Score alto — skip (usa --force per forzare)")
            continue

        if dry_run:
            print(f"  [dry-run] Trovate {len(findings)} aree da migliorare")
            _print_findings(findings, verbose=True)
            continue

        # Backup
        if backup:
            bak = path.with_suffix(".json.bak")
            shutil.copy2(path, bak)
            print(f"  Backup → {bak.name}")

        # Enrich
        enriched_def = enrich(data, findings, dry_run=False)

        # Re-score
        new_findings = audit(enriched_def)
        new_score = score(new_findings)
        print(f"  Score dopo: {new_score:.1f}/10")

        # Save — preserve wrapper if present
        if is_wrapped:
            raw["adventure_definition"] = enriched_def
            out_data = raw
        else:
            out_data = enriched_def

        with open(path, "w", encoding="utf-8") as f:
            json.dump(out_data, f, ensure_ascii=False, indent=2)
        print(f"  Salvato: {path.name}")

    return 0


def cmd_report(args) -> int:
    """Generate a markdown audit report."""
    target = Path(args.path) if args.path else _DEFAULT_DIR
    files = _find_json_files(target)

    out_path = Path(args.output) if args.output else Path("json_doctor_report.md")

    rows = []
    for path in files:
        try:
            data = _load_json(path)
            findings = audit(data)
            s = score(findings)
            criticals = sum(1 for f in findings if f.severity == "critical")
            warnings  = sum(1 for f in findings if f.severity == "warning")
            infos     = sum(1 for f in findings if f.severity == "info")
            rows.append({
                "file": path.name,
                "title": data.get("title", path.stem),
                "genre": data.get("genre", ""),
                "score": s,
                "critical": criticals,
                "warning": warnings,
                "info": infos,
                "findings": findings,
            })
        except Exception as e:
            rows.append({
                "file": path.name, "title": path.stem, "genre": "", "score": 0,
                "critical": 1, "warning": 0, "info": 0,
                "findings": [], "error": str(e)
            })

    rows.sort(key=lambda r: r["score"])

    lines = [
        "# JSON Doctor — Report",
        "",
        f"**Avventure analizzate:** {len(rows)}",
        f"**Score medio:** {sum(r['score'] for r in rows)/len(rows):.1f}/10",
        "",
        "| File | Titolo | Genere | Score | Critici | Warning | Info |",
        "|------|--------|--------|-------|---------|---------|------|",
    ]

    for r in rows:
        score_str = f"{r['score']:.1f}"
        lines.append(
            f"| `{r['file']}` | {r['title']} | {r['genre']} | {score_str} "
            f"| {r['critical']} | {r['warning']} | {r['info']} |"
        )

    lines.extend(["", "---", ""])

    for r in rows:
        if r.get("error"):
            lines.append(f"## {r['title']}\n\n**ERRORE:** {r['error']}\n")
            continue
        if not r["findings"]:
            continue
        lines.append(f"## {r['title']} — {r['score']:.1f}/10")
        lines.append("")
        for sev in ("critical", "warning", "info"):
            flist = [f for f in r["findings"] if f.severity == sev]
            if flist:
                lines.append(f"**{sev.upper()}**")
                for f in flist:
                    lines.append(f"- [{f.category}] {f.message}")
                    if f.fix_hint:
                        lines.append(f"  - *Fix:* {f.fix_hint}")
        lines.append("")

    content = "\n".join(lines)
    out_path.write_text(content, encoding="utf-8")
    print(f"Report salvato: {out_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="json_doctor",
        description="Audita e arricchisce i file JSON delle avventure GURPS"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # validate
    p_val = sub.add_parser("validate", help="Controlla la validità JSON e lo schema")
    p_val.add_argument("path", nargs="?", help="File o directory (default: data/compiled_adventures/)")

    # audit
    p_aud = sub.add_parser("audit", help="Analizza la qualità delle avventure")
    p_aud.add_argument("path", nargs="?", help="File o directory")
    p_aud.add_argument("--brief", action="store_true", help="Solo scores, nessun dettaglio")

    # enrich
    p_enr = sub.add_parser("enrich", help="Arricchisce con Claude AI")
    p_enr.add_argument("path", nargs="?", help="File singolo")
    p_enr.add_argument("--all", action="store_true", help="Arricchisci tutte le avventure")
    p_enr.add_argument("--dry-run", action="store_true", help="Mostra cosa verrebbe cambiato senza salvare")
    p_enr.add_argument("--force", action="store_true", help="Forza enrichment anche con score alto")
    p_enr.add_argument("--no-backup", action="store_true", help="Non creare backup .bak")

    # report
    p_rep = sub.add_parser("report", help="Genera un report markdown")
    p_rep.add_argument("path", nargs="?", help="File o directory")
    p_rep.add_argument("--output", "-o", help="File output (default: json_doctor_report.md)")

    args = parser.parse_args()

    if args.command == "validate":
        return cmd_validate(args)
    elif args.command == "audit":
        return cmd_audit(args)
    elif args.command == "enrich":
        return cmd_enrich(args)
    elif args.command == "report":
        return cmd_report(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
