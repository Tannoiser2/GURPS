# Roadmap — Narrative Runtime Compiler & Engine fixes

Roadmap viva delle migliorie su compiler PDF→runtime e game engine, partendo dai problemi sistemici identificati nel `Narrative_Runtime_Compiler_Evaluation.md`.

## Convenzioni

- **F#** = engine fix (turno di gioco, runtime narration)
- **P#** = pipeline fix (compilation PDF → runtime JSON)
- Ogni voce: `[x]` done · `[~]` in corso · `[ ]` da fare

## Pipeline (compiler) — committato

- [x] **P0** — PDF cleanup: rimozione `(e.g., ...)`, doubled-letter, stat-block, header/footer ricorrenti, byline d'autore · `15d8118`, `dd46806`
- [x] **P1.1** — LLM classifier per genre/archetype (opt-in `GURPS_ENABLE_LLM_CLASSIFIER`) · `15d8118`
- [x] **P1.2** — LLM clue extractor tipizzato (testimony/physical_evidence/document/scene_observation/forensic/contradiction) · `15d8118`, `937ecbe`
- [x] **P1.3** — LLM actor enrichment con batching da 5 NPC + retry su content vuoto · `15d8118`, `e9010e5`
- [x] **P1.4** — Deduction graph reale con `required_evidence_kinds` e `red_herring_clues` · `15d8118`
- [x] **P1.5** — LLM narrative synthesis di `premise`/`hidden_truth`/`win_condition`/`threat_description`/`initial_hook` con override anche su `objectives[0].label` e `core_truths[0].statement` · `e9010e5`, `076dceb`
- [x] **P2** — Timeline ladder parser (Day/Hour/Turn/Round/Phase) senza prefisso obbligatorio · `15d8118`
- [x] **P3** — Filter meta-section come clue source_location ("Adventure Background" non viene più usato come scena) · `937ecbe`
- [x] **PYDANTIC** — Fix `**model` unpacking per `AdventureDefinition` / `AdventureRuntimeState` con `_MappingCompatibleBase` · `6824a5e`

## Pipeline — residui

- [ ] **P4** — Faction relationship matrix LLM (oggi `factions: []` quasi sempre vuoto su moduli con fazioni implicite)
- [ ] **P5** — Source-aware finale: cercare boxed_text/sezione "ending|conclusion|risoluzione" per generare `FinaleCondition.concrete_choice`

## Engine — in corso

### F1 — Scene-aware visibility API · in corso
Nuovo modulo `scene_context.py` con funzioni pure riutilizzabili dal resto della pipeline:

- `visible_clues_at(runtime, definition, scene_id) → list[RuntimeClue]`
- `present_actors_at(runtime, definition, scene_id) → list[ActorState]`
- `actions_for_scene(runtime, definition, scene_id) → list[dict]`

Match tollerante: case-insensitive, prefisso e suffisso (es. "Torre - Stanza 4" matcha "Stanza 4"). Default visibility = solo elementi nella scena corrente. Usato poi da F2 e F4 senza duplicazione.

### F3a — Failure non avanza investigazione · in corso
`apply_story_updates(state, updates, *, outcome=...)`: se outcome ∈ {"fallimento", "fallimento critico"} → drop di `clues_found`, `clue_progress` e `discovered_facts.clue_for_thread`. Log esplicito di cosa viene scartato. Backward-compat: parametro default "successo pieno".

### F3c — Progressione PbtA-style differenziata · in corso
Nello stesso `apply_story_updates`:

- `successo critico` / `successo pieno` → accetta sia `clues_found` che `clue_progress` come oggi
- `successo parziale` → `clues_found` viene **demoted** a `clue_progress` (i PG ottengono progresso ma non la scoperta piena)
- `fallimento` / `fallimento critico` → F3a (nessun avanzamento, solo costo narrativo)

Singolo signature change in `main.py:1215` per passare `roll_detail["outcome"]`.

## Engine — da fare dopo F1+F3

### F2 — Action templates location-aware
Sostituzione di `f"Cercare {clue.label} a {place}"` ([main.py:857](backend/App/main.py:857)) con:

1. Filtro `actions_for_scene(current_scene_id)` da F1
2. Usa `clue.possible_actions[0]` (già generato come frase completa dal LLM) invece di prependere "Cercare"
3. Endpoint `/game/turn/options` per ricalcolo turno-per-turno (oggi le azioni sono solo iniziali)
4. Fallback "Esplora attivamente {scene.name}" quando location vuota

### F4 — Visibility constraints nel prompt Master IA
In `narrative_director.py:director_prompt_context` aggiungere blocco esplicito:
```
ELEMENTI PRESENTI IN SCENA: clue=[...], npc=[...]
REGOLA: non narrare elementi assenti come presenti
```
Riduce allucinazioni (esempio reale: failure check che "rivela" il clue testuale).

### F5 — `current_scene_id` sync atomico col movimento
Spostare la sync da post-turno ([main.py:1120](backend/App/main.py:1120)) a pre-narrazione, dentro `resolve_actions` se il giocatore si sposta. Evita race con director.

## Test plan

- [x] Suite esistente 99 verdi in 0.05s offline
- [ ] `test_scene_context.py`: 3 location, 5 clue distribuiti, 2 actor → asserire filtro per scena
- [ ] `test_clue_progression.py`: successo/parziale/fallimento → outcome corretto su `clues_found` e `clue_progress`
- [ ] `test_action_generation.py`: fixture Thrusher Manor → action list contiene `possible_actions` LLM, non "Cercare X a Y"
- [ ] Integration: failure check su Thrusher → clue resta nascosto + narrativa non rivela contenuto
