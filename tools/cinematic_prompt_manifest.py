#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from textwrap import shorten

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.json_doctor.rules import audit


def txt(v) -> str:
    if not v:
        return ""
    if isinstance(v, str):
        return re.sub(r"\s+", " ", v).strip()
    if isinstance(v, list):
        return "; ".join(txt(x) for x in v if txt(x))
    if isinstance(v, dict):
        return "; ".join(f"{k}: {txt(x)}" for k, x in v.items() if txt(x))
    return str(v)


def name(x: dict, fallback: str) -> str:
    return txt(x.get("name") or x.get("label") or x.get("title") or x.get("id") or fallback)


def brief(v, n=170) -> str:
    return shorten(txt(v), width=n, placeholder="...")


def summarize(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    d = raw.get("adventure_definition", raw)
    findings = audit(d)
    return {
        "path": str(path),
        "stem": path.stem,
        "category": path.parent.name,
        "title": txt(d.get("title") or path.stem),
        "genre": txt(d.get("genre") or path.parent.name),
        "premise": brief(d.get("premise") or d.get("initial_hook"), 360),
        "objective": brief(d.get("player_facing_objective") or d.get("objectives"), 240),
        "hidden_truth": brief(d.get("hidden_truth") or d.get("core_truths") or d.get("revelations"), 360),
        "locations": [
            {
                "id": txt(l.get("id")),
                "name": name(l, "Location"),
                "desc": brief(l.get("description") or l.get("visual_identity") or l.get("gameplay_function"), 120),
                "exits": [txt(e) for e in (l.get("exits") or [])][:4],
                "hazards": brief(l.get("hazards") or l.get("locked_paths"), 90),
            }
            for l in (d.get("locations") or [])[:8]
        ],
        "actors": [
            {
                "name": name(a, "NPC"),
                "role": txt(a.get("role")),
                "public": brief(a.get("description") or a.get("motivation"), 115),
                "secret": brief(a.get("secret") or a.get("current_plan") or a.get("fallback_plan"), 130),
            }
            for a in (d.get("actors") or [])[:8]
        ],
        "clues": [
            {
                "label": name(c, "Indizio"),
                "reveals": brief(c.get("reveals") or c.get("payoff") or c.get("hidden_implication"), 140),
            }
            for c in (d.get("clues") or [])[:10]
        ],
        "clocks": [
            {
                "label": name(c, "Clock"),
                "max": c.get("max_value", "?"),
                "tpf": c.get("ticks_per_failure", "?"),
                "note": brief(c.get("resolution_condition") or c.get("discovery_hint") or c.get("steps"), 120),
            }
            for c in (d.get("event_clocks") or [])[:4]
        ],
        "finales": [
            {
                "label": name(f, "Finale"),
                "desc": brief(f.get("description") or f.get("method") or f.get("concrete_choice"), 130),
            }
            for f in (d.get("finale_conditions") or [])[:4]
            if isinstance(f, dict)
        ],
        "findings": [
            {
                "severity": f.severity,
                "category": f.category,
                "message": brief(f.message, 100),
                "fix": brief(f.fix_hint, 100),
            }
            for f in findings[:8]
        ],
    }


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "compiled_adventures"
    files = sorted(p for p in root.glob("*/*.json") if "_debug_pdf" not in p.parts)
    out = [summarize(p) for p in files]
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
