from __future__ import annotations

import json
import os
from pathlib import Path

from .runtime_models import AdventureDefinition, AdventureRuntimeState


_default_store = Path(__file__).resolve().parents[2] / "data" / "compiled_adventures"
STORE_DIR = Path(os.getenv("ADVENTURE_RUNTIME_STORE_DIR") or ("/tmp/compiled_adventures" if os.getenv("VERCEL") else _default_store))
STORE_DIR.mkdir(parents=True, exist_ok=True)


def _path(runtime_id: str) -> Path:
    safe = "".join(ch for ch in runtime_id if ch.isalnum() or ch in ("-", "_")).strip() or "runtime"
    return STORE_DIR / f"{safe}.json"


def save_runtime(definition: AdventureDefinition, runtime_state: AdventureRuntimeState, validation_report: dict) -> dict:
    payload = {
        "adventure_definition": definition.model_dump(),
        "runtime_state": runtime_state.model_dump(),
        "validation_report": validation_report,
        "live_game_state": None,
    }
    _path(definition.id).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def load_runtime(runtime_id: str) -> dict | None:
    path = _path(runtime_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_runtimes() -> list[dict]:
    rows = []
    for path in sorted(STORE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            definition = data.get("adventure_definition") or {}
            validation = data.get("validation_report") or {}
            rows.append({
                "id": definition.get("id") or path.stem,
                "title": definition.get("title") or path.stem,
                "genre": definition.get("genre", ""),
                "runtime_profiles": definition.get("runtime_profiles", []),
                "playable": validation.get("playable", False),
                "playable_score": validation.get("playable_score") or validation.get("quality", {}).get("fiction_density_score", 0),
                "warnings": len(validation.get("warnings") or []),
                "errors": len(validation.get("errors") or []),
                "has_live_state": bool(data.get("live_game_state")),
            })
        except Exception:
            continue
    return rows


def update_runtime(runtime_id: str, patch: dict) -> dict | None:
    data = load_runtime(runtime_id)
    if not data:
        return None
    if "adventure_definition" in patch:
        data["adventure_definition"] = patch["adventure_definition"]
    if "runtime_state" in patch:
        data["runtime_state"] = patch["runtime_state"]
    if "validation_report" in patch:
        data["validation_report"] = patch["validation_report"]
    if "live_game_state" in patch:
        data["live_game_state"] = patch["live_game_state"]
    for key, value in patch.items():
        if key not in {"adventure_definition", "runtime_state", "validation_report", "live_game_state"}:
            data[key] = value
    _path(runtime_id).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data
