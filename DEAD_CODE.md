# Codice obsoleto — Vecchio motore narrativo

Questo documento raccoglie il codice non più chiamato dal frontend o dall'engine principale dopo la migrazione a GURPS Lite.

---

## Rimosso (2026-05-22)

I seguenti elementi sono stati cancellati definitivamente:

| Cosa | File | Righe eliminate |
|------|------|----------------|
| `POST /game/master/start` + `MasterStartPayload` | main.py | ~6 |
| `POST /game/master/turn` + `MasterTurnPayload` | main.py | ~12 |
| `POST /game/resolve` + `ActionPayload` | main.py | ~8 |
| `master_turn()` | claude_service.py | ~102 |
| `master_start()` | claude_service.py | ~45 |
| Import `master_turn`, `master_start` | main.py | 1 |

**Totale rimosso: ~174 righe**

---

## Ancora presente ma inutilizzato

### SceneChallenge / motore procedurale locale — `engine.py`

Il sottosistema che costruisce `SceneChallenge` in modo deterministico lato Python è oggi **bypassato** dalla modalità bibbia. L'output (`state.scene.challenge`) non viene più letto dal prompt `master_turn_with_bible`.

Stima: ~650 righe. Rischio rimozione: **medio** (testare che `resolve_actions` funzioni ancora dopo — è ancora usata internamente).

Funzioni coinvolte: `refresh_scene_state`, `_build_scene_challenge`, `_classify_scene_archetype`, `_derive_scene_solution_profile`, `_scene_action_cards`, `_scene_resolution_handles`, `_scene_display_terms`, `_scene_stakes_text`, `_scene_summary_text`, `_scene_problem_context`, `_preferred_effect_order`, `_get_prompt_for_effect`, `_scene_focus_terms`, `_has_scene_focus`, `_extract_focus_from_problem`, `_scene_primary_entity`, `_scene_object_entity`, `_scene_npc_entity`, `_scene_obstacle_text`, `_scene_resolution_text`, `_scene_keyword_roots`.

### Modello `SceneChallenge` — `models.py:40`

Ancora istanziato da `refresh_scene_state` ma il campo `challenge` di `SceneState` non viene mai letto dal percorso principale. Può restare (non rompe nulla).

---

## Cosa è vivo e NON deve essere rimosso

- `resolve_actions()` — chiamata da `master_turn_with_bible` dopo aver ricevuto il JSON di Claude
- `initiate_combat_action()`, `declare_defense()`, `npc_combat_turn()` — combattimento attivo
- `advance_to_node()`, `move_world_npcs()` — navigazione mappa strategica
- `_resolve_action_roll()`, `_apply_action_role_modifiers()` — cuore meccanico GURPS
- `mission_should_fail()`, `update_phase()` — progressione missione
- `roll_for_player_action()` — tiro GURPS pre-turno
- `advantage_breakdown()` — formula dettagliata vantaggi/svantaggi
