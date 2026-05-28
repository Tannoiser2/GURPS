# Roadmap V2 — AI Game Master Solido e Coerente

Roadmap strategica basata su analisi integrale del codebase (maggio 2026).
Copre tutti i sistemi attivi, non solo le sprint recenti.

## Convenzioni

- **L#** = LLM/AI efficiency (costo token, qualità generazione)
- **N#** = Narrative quality (coerenza, immersione, controllo tono)
- **R#** = Runtime robustness (stabilità, sync stato, recovery)
- **U#** = UI/UX frontend
- **G#** = Game system (meccaniche GURPS non ancora implementate)
- **A#** = Adventure creation (pipeline, editor, template)
- **T#** = Test coverage
- Priorità: 🔴 critico · 🟠 alto · 🟡 medio · 🟢 basso
- Ogni voce: `[x]` done · `[~]` in corso · `[ ]` da fare

---

## 1. LLM / AI Efficiency

### 🔴 Critici

- [x] **L1 — Prompt caching** `claude_service.py`
  Implementare Anthropic prompt caching (`cache_control: ephemeral`) sul system prompt e sul blocco context boilerplate (regole GURPS, descrizione avventura, elenco NPC). Senza caching ogni turno ripaga lo stesso contesto ~4000 token. Per sessioni da 20 turni il risparmio stimato è 70-80% del token cost.
  - Blocchi da cachare: system prompt + adventure definition (statico per sessione) + NPC roster
  - Blocchi variabili (non cached): stato corrente, azione giocatore, eventi turno

- [x] **L2 — Context compression per sessioni lunghe** `claude_service.py`
  Dopo N turni (soglia suggerita: 12) il context window si avvicina al limite. Implementare una fase di "recap compresso": sumarizzare i turni vecchi in un blocco canonico (chi ha fatto cosa, quali indizi scoperti, quali NPC incontrati) e usarlo come sostituto del log completo. Senza questo le sessioni lunghe degradano silenziosamente.

- [x] **L3 — Model routing intelligente** `claude_service.py`
  Attualmente Sonnet 4.5 default per tutti i turni, Haiku solo per enrichment/deadlock. Introdurre routing basato su complessità del turno:
  - Haiku → turni di movimento puro, azioni semplici senza NPC critici
  - Sonnet → default investigation/combat/revelation
  - Opus → finale, revelation of hidden_truth, turning point narrativi
  Criterio: `director_decision.escalation_tier >= 4` o `thread.is_finale` → Opus.

### 🟠 Alti

- [x] **L4 — Retry robusto con fallback graduato** `claude_service.py`
  Attualmente fallback statico (testo hardcoded) se Claude fallisce. Sostituire con tre livelli:
  1. Retry immediato (stesso prompt, stessa temperatura)
  2. Retry semplificato (prompt ridotto, no context history)
  3. Fallback testuale deterministico contestualizzato (usa `director_decision` per costruire testo generico ma coerente, non un testimone anonimo generico)

- [x] **L5 — Deadlock guard con context ricco** `deadlock_guard.py`
  Il fallback statico attuale ("un testimone anonimo rivela...") rompe l'immersione se il clue mancante è critico. Passare al prompt LLM il `hidden_truth`, il `clue.description` e i 3 NPC più rilevanti in scena per generare un failforward coerente col materiale dell'avventura. Il fallback statico resta solo se il secondo LLM call fallisce.

---

## 2. Narrative Quality

### 🔴 Critici

- [x] **N1 — Canonical event log** `adventure_runtime_store.py` / `models.py`
  Il game master AI non ha memoria strutturata di cosa è già stato narrato. Rischio: ripetere rivelazioni già fatte, contraddire fatti stabiliti. Implementare un `canonical_log: list[CanonicalEvent]` nello stato sessione con voci tipo:
  ```
  {turn: 4, type: "clue_revealed", clue_id: "...", summary: "..."}
  {turn: 7, type: "npc_introduced", npc_id: "...", first_impression: "..."}
  {turn: 9, type: "fact_established", fact: "..."}
  ```
  Il `director_prompt_context()` inietta le ultime 8-10 voci del log come "FATTI GIÀ STABILITI — non contraddire".

- [x] **N2 — NPC voice consistency** `narrative_director.py`
  Ogni NPC ha `personality`, `motivation`, `speech_style` nel runtime ma questi non vengono iniettati nel prompt turno-per-turno. Risultato: Claude reinventa la voce dell'NPC ad ogni turno. Aggiungere al `director_prompt_context()` un blocco "PROFILO NPC PRESENTI IN SCENA" con speech_style + ultima battuta pronunciata (dal canonical log) per ogni NPC in scena.

- [x] **N3 — Tone register per genere** `genre_constraints.py` / `claude_service.py`
  Attualmente il system prompt non differenzia il registro linguistico per genere. Un'avventura horror deve avere un tono diverso da un western. Aggiungere a `GENRE_PROFILES` un campo `tone_instruction: str` (es. per horror: "usa frasi corte, aggettivi viscerali, non spiegare mai completamente il fenomeno") e iniettarlo nel system prompt.

### 🟠 Alti

- [x] **N4 — Revelation pacing control** `revelation_controller.py` / `world_simulator.py`
  `revelation_controller.py` è attualmente 23 righe di helper. Espandere con:
  - `pacing_score()`: calcola se la sessione è troppo lenta (poche revelations) o troppo rapida (troppe in pochi turni)
  - `suggest_revelation_timing()`: restituisce al director se il prossimo turno è il momento giusto per una revelation o meglio costruire più tensione
  - Protezione anti-dump: se >2 revelations nell'ultimo turno, bloccare una terza

- [x] **N5 — Witness protection come meccanica esplicita** `world_simulator.py` / `main.py`
  Il witness state (available→fearful→panicked→fled) è tracciato ma il giocatore non ha azioni concrete per influenzarlo. Aggiungere:
  - Azioni disponibili quando un witness è fearful: "Rassicurare [nome]", "Offrire protezione a [nome]"
  - Se il giocatore ignora un witness fearful per 2 turni → stato peggiora automaticamente
  - Successo su "Rassicurare" → clue del witness diventa disponibile + sblocca possible_action aggiuntiva

- [x] **N6 — Multi-session continuity** `adventure_runtime_store.py`
  Nessun meccanismo di "riepilogo iniziale sessione". Quando una sessione riprende dopo pausa, il primo messaggio del GM dovrebbe includere un recap automatico (2-3 frasi) basato sul canonical_log: dove si trovano i giocatori, ultimo fatto stabilito, prossima minaccia di clock. Generato da Haiku su prompt strutturato.

### 🟡 Medi

- [x] **N7 — Red herring gameplay attivo** `world_simulator.py`
  I `red_herring_clues` sono definiti nel deduction graph ma non vengono mai usati attivamente nel turno. Aggiungere logica: se un red herring clue è nella stessa location del giocatore e la pressione NPC è bassa, il director può far trovare il red herring come "indizio" senza label di tipo, lasciando al giocatore il dubbio se sia rilevante.

- [x] **N8 — Finale condition check esplicito** `narrative_director.py`
  Le `FinaleCondition` (da P5 compiler) vengono archiviate ma il director non le usa per segnalare attivamente al giocatore quando è vicino alla risoluzione. Aggiungere: quando ≥2 finale_conditions sono soddisfatte, il director inserisce nel prompt un blocco "CONDIZIONI FINALE VICINE" che guida Claude verso un climax coerente.

---

## 3. Runtime Robustness

### 🔴 Critici

- [x] **R1 — Client state sync con diff semantici** `main.py`
  Attualmente il turno ritorna `narrative + state_updates` come blob. Se il client perde un update (timeout, reload) lo stato diverge senza recovery. Implementare:
  - Ogni risposta include `turn_id: int` (incrementale)
  - Endpoint `GET /game/state/sync?from_turn=N` che restituisce il diff degli update dal turno N
  - Client può resync in qualsiasi momento senza perdere stato

- [x] **R2 — Session recovery dopo crash** `adventure_runtime_store.py`
  Il runtime viene salvato su filesystem ma nessun meccanismo di "ultimo stato valido noto". Se il server crasha a metà turno, il client si trova con stato parzialmente aggiornato. Aggiungere:
  - Write-ahead: salva `pending_state` prima di applicare; dopo conferma client → promuovi a `committed_state`
  - Recovery endpoint: `POST /game/recover` che legge l'ultimo `committed_state`

### 🟠 Alti

- [x] **R3 — main.py refactoring in router** `main.py`
  Il file ha ~3000 righe con endpoint eterogenei (combat, setup, adventure, master, character). Suddividere in router FastAPI:
  - `routers/adventure.py` — `/game/adventure/*`
  - `routers/master.py` — `/game/master/*`
  - `routers/combat.py` — `/game/combat/*`
  - `routers/character.py` — `/game/character/*`
  - `routers/setup.py` — `/game/setup`, `/game/select-team`
  Nessuna modifica logica, solo organizzazione.

- [x] **R4 — Token budget tracking per sessione** `claude_service.py`
  `_session_tokens` esiste ma non viene esposto all'utente né usato per decisioni di routing. Aggiungere:
  - Header di risposta `X-Session-Tokens-Used: N`
  - Warning automatico se sessione supera 80k token (→ suggerire context compression L2)
  - Hard cap configurabile per ambienti con budget fisso

### 🟡 Medi

- [x] **R5 — Hardcoded threshold review** `world_simulator.py` / `clock_engine.py`
  Soglie hardcoded identificate nell'analisi:
  - `world_simulator.py`: 70% clues → extraction phase; 50/70/90% urgency thresholds
  - `clock_engine.py`: max clock value = 8 (default fisso)
  - `escalation_limiter.py`: OUTCOME_DEFAULT_TIER dict fisso
  Spostare in un `config.py` o in `AdventureRuntimeConfig` nel runtime, così ogni avventura può avere ritmo personalizzato.

- [x] **R6 — world_reaction_engine espanso** `world_reaction_engine.py`
  Attualmente 63 righe, genera solo 4 tipi di reazione (pressure_increase, access_blocked, clock_step, npc_pressure_response). Il mondo non reagisce mai proattivamente ai successi del giocatore. Aggiungere:
  - `ally_revealed`: se il giocatore ha alta reputazione con una fazione, un NPC amico si materializza con informazioni
  - `evidence_threatened`: antagonista prende contromisure se clue critico è quasi trovato
  - `scene_change`: location diventa inaccessibile (incendio, lockdown) dopo certi eventi

---

## 4. Frontend / UX

### 🔴 Critici

- [x] **U1 — Clock visualization** `App.jsx`
  I clock sono il meccanismo di pressione centrale dell'engine ma non sono visibili nel frontend. Aggiungere per ogni clock attivo:
  - Barra di progresso con nome clock, segmenti completati/totali
  - Colore urgenza: verde (0-40%) → giallo (40-70%) → arancione (70-90%) → rosso (90%+)
  - Animazione quando un segmento avanza (shake/flash)
  - "Minaccia: [descrizione]" visibile solo quando il clock supera il 50%

- [x] **U2 — Clue discovery tracker** `App.jsx`
  Nessun pannello che mostri lo stato degli indizi. Il giocatore non sa cosa ha trovato e cosa è parziale. Aggiungere sidebar collassabile:
  - Indizi scoperti: icona + titolo + tipo (testimony/physical/document/...)
  - Indizi parziali: testo sfumato + indicatore "continua a indagare"
  - Thread di deduzione: quando le evidenze richieste sono tutte scoperte → badge "DEDUZIONE DISPONIBILE"

### 🟠 Alti

- [x] **U3 — Deduction interface** `App.jsx` / `main.py`
  Quando un thread ha tutte le `required_evidence_kinds` soddisfatte, il giocatore dovrebbe poter fare la deduzione esplicitamente (non solo tramite azione libera). Aggiungere:
  - Pulsante "Fai la deduzione: [thread.label]" visibile solo quando le evidenze sono pronte
  - Endpoint `POST /game/deduce` che prende `thread_id` + `player_conclusion` (testo libero)
  - Director confronta la conclusione del giocatore con `hidden_truth`; genera risposta: confermata / parzialmente corretta / sbagliata

- [x] **U4 — NPC status panel** `App.jsx`
  Nessuna visualizzazione dello stato degli NPC durante il gioco. Aggiungere lista collassabile degli NPC incontrati con:
  - Stato: disponibile / diffidente / spaventato / fuggito / eliminato
  - Pressione agenda (barra 0-5, visibile solo se il giocatore ha una skill sociale alta)
  - Ultima informazione fornita (dal canonical log)

- [x] **U5 — Action preview con probabilità** `App.jsx`
  L'endpoint `POST /game/preview-action` esiste in `main.py` ma non è chiaro se il frontend lo usa per mostrare probabilità prima del tiro. Collegare: quando il giocatore seleziona un'azione, mostrare in tempo reale "Probabilità successo: 74%" con breakdown skill + modificatori.

### 🟡 Medi

- [ ] **U6 — Adventure definition visual editor** `App.jsx`
  Attualmente avventure si caricano solo via JSON raw o PDF. Aggiungere un editor minimal post-import:
  - Lista NPC con campo note/agenda editabile
  - Lista clock con descrizione e max_value editabile
  - Lista indizi con collegamento ai thread editabile
  - Preview del deduction graph (grafico semplice nodi-archi)
  Non deve creare avventure da zero, solo permettere di correggere l'output del compiler.

- [x] **U7 — Combat log strutturato** `App.jsx`
  Il frontend mostra il testo narrativo ma il combat log meccanico (tiro, risultato, danno, effetti) è mescolato nella narrativa. Aggiungere un toggle "mostra log meccanico" che espone:
  - Ogni attacco: tiro 3d6, target level, successo/fallimento, danno calcolato
  - Ogni difesa: tipo (parry/dodge/block), modifiers, risultato
  - Status: shock, knockdown, major wound separati visivamente

---

## 5. Game Systems

### 🟠 Alti

- [ ] **G1 — Character progression tra sessioni** `character_creation.py` / `models.py`
  Nessun sistema di miglioramento personaggio. In GURPS i punti esperienza si chiamano "character points" e si spendono per aumentare skill/stat/vantaggi. Implementare:
  - `xp_earned: int` nel Player, incrementato a fine missione
  - `POST /game/character/{id}/spend-xp` con body `{stat/skill/advantage: ..., levels: N}`
  - Costo calcolato da `character_creation.skill_cost()` / `stat_cost()`
  - Validazione: non si può aumentare una stat > 16 o spendere XP che non si ha

- [ ] **G2 — Faction/reputation tracking** `models.py` / `world_simulator.py`
  Le fazioni sono estratte dal compiler (P4) ma durante il gioco non cambia nulla in base alle azioni del giocatore verso di esse. Aggiungere:
  - `faction_reputation: dict[str, int]` nel GameState (range -5 → +5)
  - Modificatori automatici: successo contro un nemico della fazione → +1, tradimento di un alleato → -2
  - In `world_simulator.py`: se reputazione con fazione_X > 3, NPC di quella fazione offrono clue proattivi

- [x] **G3 — Injury e recovery system** `combat.py` / `models.py`
  Il combattimento calcola danni, shock e knockdown ma non persiste le ferite tra turni in modo coerente. Implementare:
  - `wounds: list[Wound]` nel Player con severity (minor/major/critical) e turns_to_heal
  - Penalità cumulative: ogni major wound attiva non recuperata → -1 a tutte le skill
  - Recovery: riposo (1 FP recuperato per ora), kit medico (First Aid, recupera HP immediati)
  - Death check automatico se HP scende sotto -HP_max (già in combat.py ma non persistito)

### 🟡 Medi

- [ ] **G4 — Sistema magia per genere fantasy** `data_skills.py` / `engine.py`
  Il genere fantasy non ha meccaniche magiche. In GURPS 4e la magia usa la skill "Magia" + spell specifici. Implementare versione semplificata:
  - `SPELL_LIST`: dizionario incantesimi con cost_fp, effect, roll_skill (Magia)
  - Skill `magia` aggiunta a `SKILL_INFO` come Difficulty H, stat IN
  - Azione "Lanciare [incantesimo]" disponibile se il personaggio ha skill magia ≥ 10
  - FP cost applicato dopo lancio (fail → FP sprecato; success → effetto)

- [ ] **G5 — Veicoli per genere moderno/sci-fi** `data_items.py` / `engine.py`
  Nessuna meccanica veicolare. Per generi action/spy/sci-fi i veicoli sono fondamentali. Implementare livello base:
  - `VEHICLE_CATALOG`: auto, moto, elicottero, astronave con Speed, HT, DR passivo
  - Skill `guidare` e `pilotare` in `SKILL_INFO`
  - Azione "Guidare/Sfuggire inseguimento": skill check + esito narrativo
  - Combat su veicolo: +2 DR per pedoni vs. armi leggere

- [ ] **G6 — Sanità mentale per genere horror** `models.py` / `world_simulator.py`
  In generi horror/cosmic l'esposizione a eventi traumatici dovrebbe avere effetti meccanici. Implementare come sistema opzionale (attivato solo se `genre.profile.has_sanity`):
  - `sanity: int` (0-20) nel Player, inizia a 15
  - Trigger: scoperta di cadaveri, creature soprannaturali, rivelazioni cosmiche → Fright Check (IN - sanity_penalty)
  - Fallimento: penalità temporanea alle skill + possibile azione "involontaria" (urlo, fuga) per 1 turno

---

## 6. Adventure Creation

### 🟠 Alti

- [x] **A1 — Template library avventure** `adventure_compiler.py` / `main.py`
  Non esiste una libreria di template. I GM non-esperti devono creare avventure da zero o caricare un PDF. Aggiungere 5-6 template predefiniti:
  - `investigation_village`: indagine classica, 4 NPC, 8 clue, 2 clock
  - `dungeon_escape`: sopravvivenza, 3 NPC, 5 clue, 3 clock urgenti
  - `heist`: furto pianificato, 6 NPC, 10 clue, fase pre/esecuzione/exfil
  - `spy_mission`: spionaggio, 5 NPC, fazioni in conflitto, 2 percorsi finali
  - `horror_mansion`: 4 NPC, red herrings forti, clock "sanità collettiva"
  Endpoint `GET /adventure/templates` + `POST /adventure/from-template/{id}`

- [x] **A2 — Adventure doctor migliorato** `adventure_doctor.py`
  Adventure doctor fa audit + enrichment ma non spiega al GM *perché* qualcosa è problematico. Aggiungere:
  - Severità per ogni issue: `error` (invalida il runtime) vs. `warning` (degradata esperienza) vs. `suggestion`
  - Messaggi di audit leggibili dall'utente finale (non solo chiavi tecniche)
  - `estimated_session_length: str` ("2-3 ore", "4-5 ore") basato su numero clue + clock segments

### 🟡 Medi

- [x] **A3 — Raw text adventure mode migliorato** `adventure_compiler.py`
  Il percorso `raw_text` (avventura scritta a mano, non da PDF) è più limitato del percorso PDF. Aggiungere:
  - Wizard di creazione: prompt sequenziali (titolo → premise → NPC → clock → clue) con validazione step-by-step
  - Endpoint `POST /adventure/wizard/step/{step_id}` con state progressivo
  - Salvataggio bozze: `POST /adventure/draft/save` + `GET /adventure/draft/{id}`

---

## 7. Test Coverage

### 🔴 Critici

- [x] **T1 — Integration test full game loop** `tests/`
  Nessun test che attraversi il ciclo completo: setup → turno 1 → clue parziale → turno 2 → clue completo → deduzione → finale. Scrivere come test offline con mock di claude_service:
  - Fixture: avventura minimale (2 NPC, 4 clue, 1 clock, 1 thread)
  - Assert: dopo 4 turni simulati, stato è coherente (clue discoverd, clock avanzato, thread resolved)
  - Verifica: canonical_log contiene gli eventi attesi

- [x] **T2 — NPC pressure event tests** `tests/test_npc_pressure.py`
  `npc_state_machine.py` non ha test. Scrivere:
  - 4 test: pressure crossing ogni threshold (low→medium→high→extreme)
  - 4 test: idempotenza (stesso threshold non si ri-triggera)
  - 2 test: pressure event side-effects (destroy_clue, eliminate_npc)

### 🟠 Alti

- [x] **T3 — World simulator unit tests** `tests/test_world_simulator.py`
  Scrivere test offline per i path critici di `simulate_world_state()`:
  - Fail-forward tier classification: soft/pressure/hard su outcome diversi
  - Phase transition: investigation → extraction quando 70% clue found
  - Clock auto-discovery + auto-resolution
  - Witness state degradation su ignored fearful witness

- [x] **T4 — Escalation limiter edge cases** `tests/test_escalation.py`
  - Stallo 3+ turni → tier alzato automaticamente
  - Clock completion → forza tier 5
  - Finale condition → tier 6 e non di più
  - Genre max_default_tier: romance (tier ≤ 3) non può scalare oltre

- [x] **T5 — Equipment coherence** `tests/test_equipment_coherence.py`
  Già pianificato nella vecchia roadmap, ancora mancante:
  - Mitra in fantasy → warning
  - Cotta di maglia in sci_fi → warning
  - Kit medico in qualsiasi genere → nessun warning
  - Arma senza eras tag → nessun warning
  - `assign_starter_items("warrior", "fantasy")` → include cotta_maglia
  - `assign_starter_items("marine", "fantasy")` → NON include giubbotto_tattico

### 🟡 Medi

- [x] **T6 — Character creation end-to-end** `tests/test_character_creation.py`
  - `validate_draft` con stat fuori range → error corretto
  - Budget overflow → error
  - Troppi svantaggi → error
  - `build_custom_player` senza items → auto-assegna per genere
  - Derivate GURPS: basic_speed = (DE+SA)/4, move = int(basic_speed)

- [x] **T7 — Canonical event log coerenza** (post-N1)
  Una volta implementato il canonical_log (N1):
  - Revelation già loggata non viene riloggata
  - Director prompt contiene le ultime 8 voci
  - Multi-session resume: canonical_log caricato da store

---

## Dipendenze tra item

```
L1 (prompt caching)     → prerequisito per L2 (context compression)
L2                      → prerequisito per N6 (multi-session continuity)
N1 (canonical log)      → prerequisito per N2 (NPC voice consistency)
N1                      → prerequisito per T7 (canonical log tests)
N4 (revelation pacing)  → dipende da N1
R1 (state sync)         → prerequisito per R2 (session recovery)
U2 (clue tracker)       → dipende da U1 (clock viz) per UI coerente
U3 (deduction iface)    → dipende da U2
G1 (XP)                 → dipende da G3 (injury/recovery) per coerenza sessione
A1 (templates)          → dipende da A2 (adventure doctor migliorato)
T1 (integration test)   → dipende da N1 (canonical log) per assertions
```

---

## Stima impatto per area

| Area | Impatto sessione | Costo implementazione | Priorità |
|------|-----------------|----------------------|----------|
| L1 Prompt caching | 🔴 Costo token -70% | Basso (2-4h) | **1** |
| N1 Canonical log | 🔴 Coerenza narrazione | Medio (1-2gg) | **2** |
| U1 Clock viz | 🔴 Pressione percepita | Basso (4-6h) | **3** |
| L2 Context compression | 🔴 Sessioni lunghe | Medio (1gg) | **4** |
| N2 NPC voice | 🟠 Immersione NPC | Basso (2-4h) | **5** |
| U2 Clue tracker | 🟠 Agenzia giocatore | Medio (1gg) | **6** |
| R1 State sync | 🟠 Stabilità client | Alto (2gg) | **7** |
| N3 Tone per genere | 🟠 Atmosfera | Basso (2-3h) | **8** |
| U3 Deduction iface | 🟠 Soddisfazione narrativa | Medio (1gg) | **9** |
| L3 Model routing | 🟡 Costo/qualità | Basso (2-3h) | **10** |
| G1 XP progression | 🟡 Long-term engagement | Alto (3gg) | **11** |
| A1 Templates | 🟡 Onboarding GM | Alto (3gg) | **12** |
| G2 Faction tracking | 🟡 Profondità narrativa | Alto (3gg) | **13** |
| R3 main.py router | 🟢 Manutenibilità | Medio (1gg) | **14** |
| G4 Magia fantasy | 🟢 Completezza genere | Alto (2gg) | **15** |

---

## Sprint suggerito — "Session Quality"

I quattro item più ad alto impatto / basso costo che si possono fare in una sprint:

1. **L1** — Prompt caching (2-4h, risparmio immediato)
2. **N3** — Tone register per genere (2-3h, impatto qualitativo immediato)
3. **U1** — Clock visualization frontend (4-6h, tensione percepita)
4. **N2** — NPC voice consistency nel director prompt (2-4h, coerenza)

Totale stimato: ~2 giorni di lavoro per un salto qualitativo misurabile.
