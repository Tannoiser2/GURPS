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

## Engine — completato

- [x] **F1** — Scene-aware visibility API: `scene_context.py` con `visible_clues_at`, `present_actors_at`, `actions_for_scene`, `current_location`. Match tollerante case-insensitive substring.
- [x] **F2** — Action templates location-aware: `_initial_runtime_options()` usa `actions_for_scene()`. Usa `clue.possible_actions[0]` LLM verbatim, non `"Cercare X a Y"`. Fallback "Esplora attivamente".
- [x] **F3a** — Failure non avanza investigazione: `apply_story_updates(state, updates, *, outcome=...)` droppa clues_found/clue_progress/discovered_facts su fallimento.
- [x] **F3c** — Progressione PbtA-style: successo pieno → pieno; parziale → demote a clue_progress; fallimento → niente.

## Engine — da fare

- [x] **F4** — Visibility constraints nel prompt Master IA: `director_prompt_context` aggiunge blocco "INDIZI/NPC PRESENTI IN SCENA" + "REGOLA VISIBILITÀ". `make_director_decision` calcola elementi visibili via `scene_context`.
- [x] **F5** — `current_scene_id` sync atomico col movimento: `_resolve_movement_destination()` in `claude_service.py` — se `player_action` è "Spostarsi verso X" risolve la destinazione *prima* della decisione director. Elimina race tra movimento e narrazione.

## Test plan

- [x] Suite esistente 99 verdi in 0.05s offline
- [x] `test_scene_context.py`: 11 test — filtro scena, tollerante prefix match, azioni, attori
- [x] `test_clue_progression.py`: 9 test — successo/parziale/fallimento → outcome corretto
- [ ] `test_action_generation.py`: fixture Thrusher Manor → action list contiene `possible_actions` LLM, non "Cercare X a Y"
- [ ] Integration: failure check su Thrusher → clue resta nascosto + narrativa non rivela contenuto
