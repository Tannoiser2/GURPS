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

- [x] **P4** — `extract_factions_with_llm()`: estrae fazioni con agenda, status (quiet→dominant), pressure 0-5, allies/enemies/key_npc. Collegato al compiler dopo actor enrichment in entrambi i percorsi PDF e raw_text.
- [x] **P5** — `extract_finale_conditions_with_llm()`: cerca sezioni ending/conclusion/risoluzione nel PDF (regex + boxed text + tail fallback), genera FinaleCondition con concrete_choice specifiche. Collegato al compiler dopo synthesis.

## Engine — completato

- [x] **F1** — Scene-aware visibility API: `scene_context.py` con `visible_clues_at`, `present_actors_at`, `actions_for_scene`, `current_location`. Match tollerante case-insensitive substring.
- [x] **F2** — Action templates location-aware: `_initial_runtime_options()` usa `actions_for_scene()`. Usa `clue.possible_actions[0]` LLM verbatim, non `"Cercare X a Y"`. Fallback "Esplora attivamente".
- [x] **F3a** — Failure non avanza investigazione: `apply_story_updates(state, updates, *, outcome=...)` droppa clues_found/clue_progress/discovered_facts su fallimento.
- [x] **F3c** — Progressione PbtA-style: successo pieno → pieno; parziale → demote a clue_progress; fallimento → niente.

## Engine — da fare

- [x] **F4** — Visibility constraints nel prompt Master IA: `director_prompt_context` aggiunge blocco "INDIZI/NPC PRESENTI IN SCENA" + "REGOLA VISIBILITÀ". `make_director_decision` calcola elementi visibili via `scene_context`.
- [x] **F5** — `current_scene_id` sync atomico col movimento: `_resolve_movement_destination()` in `claude_service.py` — se `player_action` è "Spostarsi verso X" risolve la destinazione *prima* della decisione director. Elimina race tra movimento e narrazione.

## Sistema Equipaggiamento — completato

- [x] **E1** — Integrazione armi da GURPS 4e Basic Set (PDF): +30 armi (polearm, storiche, avancarica, sciabola, ecc.) · `data_weapons.py` ora ha 58 armi
- [x] **E2** — Armature storiche e scudi da Basic Set: cuoio DR 2, cotta DR 4, corazza DR 5, piastre DR 7, scudi DB +1/+2/+3 · `data_items.py`
- [x] **E3** — Equipaggiamento militare/moderno: granata frammentazione/fumogena/stordente, giubbotto tattico DR 6, elmetto balistico DR 5, esplosivi demolizione, razioni, manette, documento falso · `data_items.py`
- [x] **E4** — Tagging `eras` su tutti gli item del catalogo: item era-specifici (scanner, computer, giubbotto, esoscheletro…) hanno lista `eras`; universali (kit medico, torcia, corda…) `eras: []`
- [x] **E5** — Controllo coerenza genere: `equipment_coherence.validate_gear_for_genre(items, genre)` → warning se arma/item fuori epoca (es. mitra in fantasy, cotta di maglia in sci-fi) · `equipment_coherence.py`
- [x] **E6** — Auto-assegnazione equipaggiamento in character creation: `assign_starter_items(archetype, genre)` assegna base-kit per genere + extra per archetipo filtrati per era · `equipment_coherence.py`
- [x] **E7** — Integrazione in `character_creation.py`: `validate_draft()` aggiunge warning di coerenza; `build_custom_player()` auto-assegna item se `draft.items` è vuoto

## Test plan

- [x] Suite esistente 99 verdi in 0.05s offline
- [x] `test_scene_context.py`: 11 test — filtro scena, tollerante prefix match, azioni, attori
- [x] `test_clue_progression.py`: 9 test — successo/parziale/fallimento → outcome corretto
- [x] `test_action_generation.py`: 8 test — LLM labels, filtro location, global clue, actor filter, move actions, discovered skip, fallback explore, skill_hints
- [ ] Integration: failure check su Thrusher → clue resta nascosto + narrativa non rivela contenuto
- [ ] Equipment coherence: mitra in fantasy → warning; cotta in sci_fi → warning; kit medico in qualsiasi genere → nessun warning
