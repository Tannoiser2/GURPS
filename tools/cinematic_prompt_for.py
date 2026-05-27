#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def line_items(items, key1, key2=None, n=7):
    out = []
    for i, item in enumerate(items[:n], 1):
        a = item.get(key1, "")
        b = item.get(key2, "") if key2 else ""
        out.append(f"{i}. {a}" + (f": {b}" if b else ""))
    return "\n".join(out) or "Non specificato"


def prompt(data, kind: str) -> str:
    title = data["title"]
    genre = data["genre"]
    route = " -> ".join(f"{i+1} {l['name']}" for i, l in enumerate(data["locations"][:7]))
    locs = line_items(data["locations"], "name", "desc", 7)
    actors_public = line_items(data["actors"], "name", "public", 6)
    actors_secret = "\n".join(
        f"{i}. {a['name']} ({a.get('role') or 'NPC'}): {a.get('secret') or a.get('public')}"
        for i, a in enumerate(data["actors"][:7], 1)
    ) or "Non specificato"
    clues = line_items(data["clues"], "label", "reveals", 8)
    clocks = "\n".join(
        f"{i}. {c['label']}: max {c['max']}, tick/fail {c['tpf']}. {c['note']}"
        for i, c in enumerate(data["clocks"][:4], 1)
    ) or "Nessun clock nel JSON"
    finales = line_items(data["finales"], "label", "desc", 4)
    findings = "\n".join(
        f"{i}. {f['severity'].upper()} {f['category']}: {f['message']} FIX: {f['fix']}"
        for i, f in enumerate(data["findings"][:6], 1)
    ) or "Nessun finding automatico: controllare comunque ridondanza indizi, gate e pacing."

    base_style = (
        "Create a single cohesive A4 portrait cinematic illustrated tabletop RPG infographic poster. "
        "It must look like a deluxe RPG module spread with real painterly scenes, dramatic lighting, "
        "ornate borders, blackened metal and parchment panels, integrated route arrows and illustrated cards. "
        "No flat placeholder boxes, no wireframe look, no simple diagram style, no watermark. "
        "Short readable Italian labels only; prefer compact bullets over paragraphs. "
    )
    if kind == "player":
        return f"""Use case: infographic-diagram
Asset type: A4 portrait cinematic RPG PLAYER-FACING infographic.
{base_style}

TITLE: \"{title.upper()}\"
Subtitle: \"PRESENTAZIONE PER I GIOCATORI\"
Small subtitle: \"Cose note prima di iniziare - Spoiler safe\"
Genre/visual mood: {genre}. Make the art match this genre.

SPOILER-SAFE JSON DATA:
Premessa: {data['premise']}
Obiettivo visibile: {data['objective']}
Route conosciuta: {route}
Location note:
{locs}
NPC/voci pubbliche:
{actors_public}
Finali visibili o obiettivi:
{finales}

Required panels:
1. \"PANORAMICA DELL'AVVENTURA\" with 4-5 concise bullets from premessa and objective.
2. Central connected location graph with numbered illustrated nodes and arrows: {route}.
3. \"COSE NOTE\" with safe facts, risks, starting situation, and visible constraints.
4. \"VOCI E CONTATTI\" with public NPC names and labels.
5. \"RISCHI ATTESI\" with icons for dangers, investigation, rivals, environment, gates.
6. \"OBIETTIVO VISIBILE\" checklist.

The page must be information-rich but spoiler-safe. Do not reveal hidden truth, culprit, secret motives, or GM-only fixes."""

    return f"""Use case: infographic-diagram
Asset type: A4 portrait cinematic RPG GM SPOILER ANALYSIS infographic.
{base_style}

TITLE: \"{title.upper()}\"
Subtitle: \"SCHEDA GM - SPOILER, INDIZI, NPC E FIX\"
Small subtitle: \"Analisi runtime dal JSON compilato\"
Genre/visual mood: {genre}. Make the central illustration match this genre with high drama.

GM JSON DATA:
Premessa: {data['premise']}
Verita nascosta / core truth: {data['hidden_truth']}
Grafo location: {route}
Location:
{locs}
Indizi critici:
{clues}
NPC / segreti / pressione:
{actors_secret}
Clock / pressione:
{clocks}
Finali:
{finales}
Bug, incongruenze e fix:
{findings}

Required panels:
1. \"VERITA NASCOSTA\" with compact spoiler summary.
2. \"INDIZI CRITICI\" listing key clues and what they reveal.
3. Central \"GRAFO GM\" with route nodes, green movement arrows, blue investigation arrows, red pressure/destruction arrows, gold gate arrows.
4. \"NPC / SEGRETI / PRESSIONE\" with names and one-line secret/plan.
5. \"CLOCK E PRESSIONE\" escalation ladder.
6. Bottom-wide \"BUG, INCONGRUENZE E FIX\" with numbered fix cards.
7. \"CHECK GM\" with icons: ridondanza indizi, gate alternativi, piani NPC attivi, finale non bloccante.

This page is for the GM and may include spoilers. Dense information, cinematic art, readable headings."""


def main() -> int:
    manifest = Path(sys.argv[1])
    idx = int(sys.argv[2])
    kind = sys.argv[3]
    data = json.loads(manifest.read_text(encoding="utf-8"))[idx]
    print(prompt(data, kind))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
