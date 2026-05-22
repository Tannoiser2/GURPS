# GURPS Lite 4ª ed. — Roadmap migrazione

> 🟢 completato · 🟡 in coda · 🔴 rinviato/bloccante

---

## 🟢 PR1 — Modello personaggio + risoluzione 3d6 (2026-05-20)

- 🟢 `models.py` — `Player` con `skills`, `advantages`, `max_fp/fp`, `will`, `per`, `basic_speed`, `dodge`, `move`, `dr`
- 🟢 `data_skills.py` — `SKILL_INFO` (stat + difficoltà E/M/D), helper `skill_stat`, `skill_default_penalty`
- 🟢 `data_roles.py` — archetipi rigenerati su scala 8–14 con `skills` esplicite (livello Eccezionale 12–14)
- 🟢 `engine.py` — `_resolve_action_roll` → 3d6≤target con margine; `apply_effect` su soglie 10/5/0; `preview_action_outcomes` con distribuzione esatta 3d6
- 🟢 `claude_service.py` — `generate_candidate_pool` passa `skills` ai dict candidati

**Decisioni rinviate:**
- 🟢 PR1.5 — nomi GURPS via alias bidirezionale (2026-05-21) — zero regression
- 🔴 PR1.6 — rinomina chiavi stat `forza/agilita/intelligenza/empatia` → `FO/DE/IN/SA` — ~30 punti in engine.py + claude_service.py

---

## 🟢 PR1.4 — Fix integrazione skill (2026-05-21)

- 🟢 `claude_service.py` — prompt Claude include `Skills:[mira:14, ...]` (top 6) per ogni personaggio
- 🟢 `claude_service.py:_fallback_actions_for_player` — helper `_best_skill_in`, azioni adattate al profilo reale
- 🟢 `engine.py:_infer_action_from_intent` — tra più skill candidate sceglie quella col livello più alto in `player.skills`

---

## 🟢 PR2 — Combattimento meccanico GURPS (2026-05-21)

- 🟢 `models.py` — `SceneEntity` + `max_hp/dr/attack_skill/active_defense/damage_dice/damage_type`; `Action` + `attack_kind/damage/damage_type`; nuovi `CombatDefenseRequest`, `AttackResult`; `GameState.pending_attack`
- 🟢 `combat.py` (nuovo) — `resolve_attack`, `roll_damage`, `wound_threshold`; critico/fail critico; moltiplicatori danno (cut ×1.5, imp ×2.0, cr ×1.0)
- 🟢 `engine.py` — `initiate_combat_action` (auto vs entità, sospende vs Player); `declare_defense` (seconda metà interattiva); `_combat_result_to_log`
- 🟢 `main.py` — `POST /game/combat/attack`, `POST /game/combat/defend`

**Scelte confermate:**
- 🟢 Difesa attiva **dichiarata dal giocatore** (non automatica)
- 🟢 PF tracciati **per entità** (non solo soglie narrative)

---

## 🟢 PR3 — Vantaggi e svantaggi (2026-05-21)

- 🟢 `data_advantages.py` (nuovo) — definizioni meccaniche: `ADVANTAGES` dict + helper `advantage_skill_bonus`, `advantage_effect_type_bonus`, `advantage_dodge_bonus`, `advantage_death_threshold_mult`, `has_morale_check`, `advantage_combat_penalty`
- 🟢 Bonus meccanici integrati in `_resolve_action_roll`, `_resolve_defense`, e `build_players_from_dicts`
- 🟢 `data_roles.py` — vantaggi assegnati agli archetipi (Riflessi, Duro, Sensi Acuti, Carisma, Animo Sanguinario, Sospettoso)

---

## 🟢 PR4 — Reazioni sociali complete (2026-05-21)

- 🟢 `models.py` — `WorldNPC` + `reaction_modifier / last_reaction_level / last_reaction_roll`; `ReactionResult`
- 🟢 `engine.py` — `resolve_reaction_roll`: 3d6 + npc_modifier + Carisma + skill_bonus + consulted_bonus − team_status_malus
- 🟢 `main.py` — `POST /game/reaction`

---

## 🟢 PR5 — Creazione personaggio / spesa punti (2026-05-21)

- 🟢 `models.py` — `CharacterDraft`, `CharacterValidation`
- 🟢 `character_creation.py` (nuovo) — validazione GURPS, `validate_draft`, `build_custom_player`
- 🟢 `main.py` — `POST /game/character/validate`, `POST /game/character/create`
- 🟢 Budget 100 pt, stat 6–16, limite svantaggi −40 pt

---

## 🟢 PR6 — Mappa tattica hex + combattimento visuale (2026-05-21)

- 🟢 **Griglia hex flat-top** SVG (15×10 col/row, HEX_SIZE=28) con coordinate offset e distanza via cubiche
- 🟢 **Terrain**: 0=normale, 1=copertura (+2 difesa), 2=difficile (×2 mov.), 3=muro (bloccante)
- 🟢 **Token** con cerchio colorato, triangolo di direzione (facing 0–5), barra PF
- 🟢 **Initiative bar**: ordinata per Basic Speed (DE+SA)/4 GURPS RAW
- 🟢 **Azioni**: Muovi (celle raggiungibili evidenziate), Attacca (range melee/ranged), Ruota facing
- 🟢 **Attacco da retro**: rilevato geometricamente, loggato nel combat log
- 🟢 **Copertura**: bonus +2 difesa da terrain=1, calcolato al click
- 🟢 **Immagine di sfondo**: generata via AI coerente con genere/ambiente (una volta sola per combattimento)
- 🟢 **Pannello difesa**: Schivata / Parata / Bloccata / Difesa Totale inline nella mappa
- 🟢 **CombatLogMessage** con badge completi: dado attacco/difesa, WoundBadge, DamageTypeBadge, AdvantagesBadges
- 🟢 **Narrazione Master** dopo ogni scambio (1-2 frasi italiane via Claude)
- 🟢 **Chiusura automatica mappa** quando tutti i nemici sono eliminati

---

## 🟢 PR7 — Badge system visuale (2026-05-21)

- 🟢 `SKILL_META` (40 skill), `ADVANTAGE_META`, `WOUND_META`, `DAMAGE_TYPE_META`, `DEFENSE_META`, `NPC_STATUS_META`, `NPC_ATTITUDE_META`, `NARRATIVE_HINT_META`
- 🟢 Componenti: `Badge`, `SkillBadge`, `AdvantagesBadges`, `WoundBadge`, `DamageTypeBadge`, `DefenseBadge`, `NpcStatusBadge`, `NpcAttitudeBadge`, `NarrativeHintBadge`
- 🟢 `CombatLogMessage` — tutti i valori di gioco mostrati come badge colorati
- 🟢 `SidePanel` tab NPC — stato e atteggiamento come `NpcStatusBadge` + `NpcAttitudeBadge`
- 🟢 `OptionsBar` — skill dei suggerimenti come `SkillBadge`

---

## 🟢 PR8 — Avventura + Splash screen (2026-05-21)

- 🟢 **Bibbia avventura** (create_adventure, master_start_with_bible, master_turn_with_bible)
- 🟢 **PDF upload** → estrazione testo → bibbia avventura (pdfplumber, `POST /game/adventure/from-pdf`)
- 🟢 **Splash screen**: banner PNG superiore, badge PNG per PDF upload, griglia genere solo PNG (niente testo duplicato)
- 🟢 **SecretsPanel**: modale playtest con 4 tab — Verità / Indizi / PNG / Twist
- 🟢 **Story ending screen**: schermata fine storia con obiettivo, testo conclusivo e pulsante rivela segreti
- 🟢 **Abort mission**: `POST /game/abort-mission` per uscire da partite bloccate

---

## 🟢 PR9 — Mappa strategica + NPC combat stats (2026-05-21)

- 🟢 **Mappa strategica**: immagine pre-generata AI (`POST /game/generate-strategic-map-image`), token che indica la posizione corrente
- 🟢 **SVG overlay**: nodi colorati per stato (corrente/raggiungibile/visitato/bloccato), connessioni, tooltip con badge
- 🟢 **Navigazione**: click su nodo raggiungibile → `POST /game/move` → messaggio Master in chat
- 🟢 **NPC combat stats persistenti**: generati al primo ingresso in combattimento (`_generate_npc_combat_stats`, `_enrich_combat_scene`), riutilizzati nei turni successivi
- 🟢 **Mappa tattica contestuale**: prompt AI con location_name, location_description, scene_narrative, mission_environment, enemy_names per coerenza ambiente/genere

---

## 🟢 PR10 — Regole GURPS ferite complete (2026-05-21)

Tutte le meccaniche mancanti rispetto a GURPS Lite 4ª ed. implementate:

### `models.py`
- 🟢 `Player` + `shock_penalty`, `stunned`, `prone`, `action_type`, `death_check_pending`
- 🟢 `AttackResult` + `shock_applied`, `major_wound`, `major_wound_check_passed`, `knockdown`, `knockdown_check_passed`, `death_check`, `death_check_passed`, `fp_cost`, `target_stunned`, `target_prone`

### `combat.py`
- 🟢 **Shock** (GURPS Lite p.14): −net_damage ai prossimi tiri attacco/difesa, max −4, si azzera dopo l'azione
- 🟢 **Major Wound**: singolo colpo > max_hp/2 → 3d6≤SA o stordito
- 🟢 **Knockdown**: HP scende a 0 → 3d6≤SA o prone (a terra)
- 🟢 **Death Check**: HP < 0 → 3d6≤SA o morto istantaneamente (ogni volta che scende ulteriormente)
- 🟢 **Stordito**: niente azioni attive; all'inizio del turno 3d6≤SA per recuperare
- 🟢 **Prone**: −3 attacco, −2 difesa netta; `stand_up()` consuma l'azione
- 🟢 **All-Out Attack**: +4 al tiro attacco, impossibilità di difendersi quel turno (`action_type = "all_out_attack"`)
- 🟢 **All-Out Defense**: +2 difesa (schivata/parata), nessun attacco quel turno
- 🟢 **FP in combattimento**: se FP ≤ FP/3, ogni attacco costa 1 FP aggiuntivo
- 🟢 `attempt_stun_recovery()`, `stand_up()`, `reset_action_type()` — helper di stato

### `engine.py` + `main.py`
- 🟢 `initiate_combat_action` — accetta `action_type`, blocca il turno se stordito con tiro di recupero automatico
- 🟢 `declare_defense` — accetta `defense_action_type`, resetta action_type dopo lo scambio, propaga tutte le condizioni nel `last_attack_result`
- 🟢 `_combat_result_to_log` — mostra Shock/Major Wound/Knockdown/Death Check nel log
- 🟢 `POST /game/combat/defend` — ora accetta `defense_action_type`
- 🟢 `POST /game/combat/standup` — nuovo endpoint per alzarsi da terra

### Frontend
- 🟢 Badge sui token hex: 💫 stordito, ⬇ prone, ⚡ shock
- 🟢 Bottoni **⚔⚔ Totale** (All-Out Attack) e **🛡🛡 Difesa Totale** nella mappa
- 🟢 Bottone **⬆ Alzati** visibile solo quando il personaggio è prone
- 🟢 `CombatLogMessage` — nuovi badge: Shock, Ferita Grave+esito SA, Caduta+esito SA, Tiro Morte+esito SA, FP consumati, tag Attacco/Difesa Totale

---

## 🟢 PR11 — Contenuto GURPS completo + Coerenza narrativa (2026-05-21)

### `data_skills.py` — da 30 a 72 skill
- 🟢 **Nuove FO**: Nuotare (SA/E), Arrampicarsi (DE/M), Lanciare (DE/E), Sollevare (FO/E), Saltare (DE/E)
- 🟢 **Nuove DE**: Cavalcare (DE/M), Mimetizzarsi (IN/M), Equilibrio (DE/E), Borseggio (DE/M)
- 🟢 **Nuove IN**: Legge, Occultismo, Seguire Tracce, Navigazione, Sopravvivenza Urbana, Storia, Economia, Meccanica, Elettronica, Informatica, Astronomia, Biologia, Chimica, Fisica, Linguistica, Filosofia, Teologia, Politica (tutte IN/M o IN/D)
- 🟢 **Nuove SA**: Recitazione (SA/M), Parlare in Pubblico (SA/M), Interrogatorio (IN/M), Seduzione (SA/M)
- 🟢 **Fix attributi**: `ingannare` → IN/M, `intuire` → IN/M, `etichetta` → IN/E (corretti per GURPS Lite)

### `data_advantages.py` — da 9 a 39 trait
- 🟢 **Nuovi vantaggi** (21 tot.): Ambidestrezza, Bellezza, Empatia, Memoria Fotografica, Coraggio, Sangue Freddo, Istinto di Sopravvivenza, Fortuna, Contatti, Status Sociale, Ricchezza, Talento, Voce Bella, Autorità, Linguaggio Nativo Extra
- 🟢 **Nuovi svantaggi** (18 tot.): Avidità, Senso del Dovere, Nemico, Segreto, Dipendenza, Fobia, Impulsività, Arroganza, Lealtà, Poca Autostima, Amnesia, Mancanza di Empatia, Curiosità Morbosa, Smemoratezza, Pessimismo
- 🟢 Nuovi helper: `advantage_reaction_modifier`, `advantage_will_modifier`, `all_advantages`, `all_disadvantages`

### Coerenza personaggio ↔ storia
- 🟢 **Famiglia "storico"** aggiunta a `mystery_horror` — ambienti medievali/rinascimentali, blacklist oggetti moderni
- 🟢 **`THEME_FAMILY_ROLE_OVERRIDE`** in `data_roles.py`: mappa `theme_family → chiave ROLE_LIBRARY alternativa`
- 🟢 **`mystery_horror_storico`** (8 archetipi): Inquisitore, Studioso, Cavaliere, Erborista, Agente Segreto, Mercante, Pellegrino, Ladro — con equipaggiamento d'epoca
- 🟢 `generate_candidate_pool` riceve `theme_family` e seleziona il roster corretto automaticamente
- 🟢 `forbidden_elements` da famiglia storica (smartphone, computer, pistola a proiettili…) propagati al prompt Claude

### Badge system aggiornato (`App.jsx`)
- 🟢 `SKILL_META` espansa: 72 skill con `attr` corretto (FO/DE/IN/SA) e colore semantico per attributo
- 🟢 `ADVANTAGE_META` espansa: 21 vantaggi + 18 svantaggi con icone dedicate

---

## 🟢 PR12 — Wiring geometrico combattimento ↔ backend (2026-05-21)

### `combat.py`
- 🟢 `_defense_value` accetta `cover_bonus: int` e `rear_attack: bool`
- 🟢 `rear_attack=True` → difesa annullata immediatamente (GURPS Lite: attacco da retro ignora Active Defense)
- 🟢 `cover_bonus` sommato al valore di difesa (bersaglio su terreno copertura +2)
- 🟢 `_resolve_defense` e `resolve_attack` passano entrambi i parametri

### `engine.py`
- 🟢 `declare_defense` accetta `cover_bonus` e `rear_attack`, li passa a `resolve_attack`
- 🟢 Entrambi tracciati in `last_attack_result` per il log

### `main.py`
- 🟢 `CombatDefendPayload` + campi `cover_bonus: int = 0` e `rear_attack: bool = False`
- 🟢 `POST /game/combat/defend` forwarda i valori geometrici dal frontend
- 🟢 `POST /game/combat/will-check` — tiro Volontà (IN) per paura/stress: 3d6 ≤ IN+modifier

### Frontend (`App.jsx`)
- 🟢 Pannello difesa mostra copertura attiva e avviso attacco da retro in tempo reale
- 🟢 Pulsanti difesa trasmettono `cover_bonus` e `rear_attack` dal contesto geometrico mappa
- 🟢 `handleDefend` signature estesa per forwarding completo

---

## 🟢 PR13 — Qualità e polish (2026-05-21)

### Initiative bar
- 🟢 Indicatore **"▶ Turno giocatori"** / **"⚔ Turno nemici"** nell'initiative bar
- 🟢 Token del giocatore attivo evidenziato con glow viola durante il suo turno

### Animazioni token mappa tattica
- 🟢 **Movimento**: token scala a 1.18× per 180ms durante lo spostamento hex
- 🟢 **Attacco**: token scala a 1.25× con glow giallo e stroke dorato per 400ms
- 🟢 State `animating: {key → "move"|"attack"}` che si autopulisce dopo il timeout

### Tooltip GURPS inline sui badge
- 🟢 `SKILL_TOOLTIP`: 70 voci con attributo, difficoltà, default e regola GURPS Lite
- 🟢 `ADVANTAGE_TOOLTIP`: 39 voci (21 vantaggi + 18 svantaggi) con effetto meccanico e costo in punti
- 🟢 `BadgeTooltip`: popup flottante sopra il badge al hover, con freccia, stile dark
- 🟢 `Badge` accetta prop `tooltip` — mostra il popup su `onMouseEnter`
- 🟢 `SkillBadge` e `AdvantagesBadges` passano automaticamente il tooltip

---

## 🟢 PR14 — Schede GURPS NPC importanti + provider separati (2026-05-22)

### Schede GURPS pre-generate per NPC importanti
- 🟢 `WorldNPC` — nuovi campi: `gurps_fo/de/in/sa`, `gurps_skills`, `gurps_advantages`, `gurps_disadvantages`
- 🟢 `_generate_npc_full_gurps_stats()` — genera scheda GURPS completa via Claude per NPC con `threat >= 2`
- 🟢 `generate_initial_world_npcs()` — chiama la generazione scheda al momento della creazione NPC
- 🟢 Stat pre-generate usate automaticamente in `_enrich_combat_scene` (combat_hp/attack_skill già settati)
- 🟢 Prompt master include stat GURPS degli NPC importanti (FO/DE/IN/SA, skill top-4, vantaggi/svantaggi)
- 🟢 `SidePanel` tab PNG — NPC con scheda mostrano badge "★ scheda", card espandibile al click con attributi, skill e trait colorati
- 🟢 `fetchGameState()` legge `world_npcs` da `/game/state` e li fonde con `adventure.npcs` nel pannello

### Provider AI separati (Testo vs Grafica)
- 🟢 `TeamSetupState` — nuovo campo `image_provider: str = "auto"` separato da `provider` (testo)
- 🟢 `SetupPayload` — accetta `image_provider` indipendente
- 🟢 `_resolve_image_provider()` — helper che rispetta `auto | openai | gemini | none`
- 🟢 Tutti gli endpoint immagini (`scene-image`, `strategic-map`, `tile`, `tactical-map`, `avatar`) usano `_resolve_image_provider()`
- 🟢 Opzione **"Nessuna"** — disabilita completamente la generazione grafica senza toccare l'AI testuale
- 🟢 Splash screen — due picker distinti: **AI Narrativa** (Claude/OpenAI) e **AI Grafica** (Auto/OpenAI/Gemini/Nessuna)

### Fix immagini
- 🟢 Fallback a cascata immagini: Imagen 4 → OpenAI `gpt-image-1` quando quota Imagen esaurita (429)
- 🟢 Rimosso `response_format="b64_json"` (non supportato da client attuale) da tutti i 4 punti OpenAI
- 🟢 `gpt-image-1` usato uniformemente per tutte le generazioni OpenAI (restituisce b64 nativo)

### Riferimento GURPS
- 🟢 `GURPS_REFERENCE.md` — documento con tutte le 70 skill (chiave/etichetta/attributo/difficoltà), 21 vantaggi e 18 svantaggi con costi ed effetti meccanici

---

## 🟢 PR15 — Fine avventura e ritmo indizi (2026-05-22)

### Chiusura avventura garantita
- 🟢 Prompt master-bibbia: istruzione esplicita **"questo è l'ULTIMO turno"** quando `threat_pct >= 100%`
- 🟢 Regola vittoria esplicita nel prompt: se win_condition soddisfatta → `story_over=true, victory=true`
- 🟢 **Guardia backend**: se il modello non imposta `story_over` nonostante `threat_pct >= 100`, viene forzato lato Python dopo la risposta
- 🟢 Quando `story_over` forzato: narrative di fallback coerente con `threat_description`

### Ritmo indizi adattivo
- 🟢 Contatore `N/totale indizi trovati` visibile al master in ogni turno
- 🟢 Quando `threat_pct >= 80%`: label indizi passa da "non rivelare direttamente" a **"FAI TROVARE ORA"**
- 🟢 Warning esplicito al master: "ATTENZIONE: tempo quasi esaurito, fai emergere i restanti indizi ATTIVAMENTE"

---

## 🟢 PR16 — Risoluzione dado robusta + nomi reali pool (2026-05-22)

### Enforcement esiti dadi (VINCOLANTI)
- 🟢 `engine.py:resolve_actions` — raccoglie `per_player_outcomes` con formula completa per ogni giocatore: `base_skill`, `item_bonus`, `adv_bonus`, `coord_bonus`, `difficulty`, `status_malus`, `threat_malus`, `effective_skill`, `rolled`, `margin`, `outcome`
- 🟢 Blocco `══ ESITI DEI TIRI — VINCOLANTI PER LA NARRATIVA ══` inserito come prima sezione di `action_results_summary` — precede tutte le istruzioni narrative
- 🟢 `claude_service.py:generate_scene_package` — Regola 0 assoluta: Claude **non può trasformare un FALLIMENTO in successo**; successo parziale ammesso solo con costo narrativo esplicito
- 🟢 `models.py:GameState` — nuovo campo `last_roll_details: List[Dict] = []`

### Tiri coordinati (+2 bonus)
- 🟢 `engine.py:resolve_actions` — dizionario `effect_types_this_turn` traccia chi ha già agito su ogni `effect_type`; secondo+ giocatore sullo stesso tipo riceve `coordination_bonus = +2`
- 🟢 `_resolve_action_roll` accetta `coordination_bonus: int = 0`, lo aggiunge a `effective_skill` e lo include nel dizionario di ritorno

### Pool 6 personaggi + nomi reali
- 🟢 `claude_service.py` — `POOL_TARGET = 6` (da 8); rimossi suffissi numerici (`Scienziato 1` → nome reale)
- 🟢 `_NAMES_BY_GENRE` — ~15 nomi per genere: `sci_fi` (Kovač, Yuen, Okafor…), `fantasy` (Aldric, Mira…), `mystery_horror` (Carver, Dupont…), `storico` (Lorenzo, Beatrice…), `post_apocalyptic` (Rex, Zara…)
- 🟢 `_pick_names(genre, count)` — helper che shuffla il pool e ritorna i nomi richiesti; `role` rimane etichetta sotto il nome

### Fix candidate pool skills/vantaggi
- 🟢 `engine.py:start_game_from_selection` — `candidate_pool_dicts` ora include `skills`, `advantages`, `disadvantages`; prima erano vuoti, causando tab Gruppo senza dati nella SidePanel

---

## 🟢 PR17 — Timer opzionale + mappa coerente con l'avventura (2026-05-22)

### Timer opzionale (`has_time_pressure`)
- 🟢 `claude_service.py` — campo `has_time_pressure: bool` aggiunto alla bibbia avventura (template procedurale e PDF); Claude imposta `false` per avventure esplorative/investigative senza conto alla rovescia esplicito
- 🟢 `engine.py:_bible_has_time_pressure()` — helper che legge il campo con default `True` per retrocompatibilità
- 🟢 `engine.py:start_game_from_selection` — quando `has_time_pressure=False`: `max_turns=999`, `time_limit=0`, `time_left=0`
- 🟢 `engine.py:resolve_actions` — decremento timer e condizione timeout ora gated su `scene.time_limit > 0`
- 🟢 `engine.py:_scene_stakes_text()` — linee di pressione temporale gated su `time_limit > 0`
- 🟢 `engine.py:advance_to_node` — `adjusted_time = 0` quando `time_limit == 0` (nodo successivo non eredita timer)
- 🟢 `App.jsx:SidePanel` — mostra "Nessun limite di tempo" (verde) invece del timer quando `has_time_pressure === false`

### Mappa strategica da locazioni bibbia
- 🟢 `engine.py:generate_map_from_bible_locations()` — nuova funzione: costruisce `MapState` direttamente dall'array `locations` della bibbia con layout a catena lineare; obiettivo = ultima location con `has_combat_potential=True` (o ultima in assoluto)
- 🟢 `engine.py:start_game_from_selection` — se la bibbia ha `locations`, usa `generate_map_from_bible_locations` invece di `generate_map_for_genre`; tutti i nodi riflettono locazioni reali dell'avventura
- 🟢 Nodo iniziale marcato `visited=True`; coordinate grid assegnate per layout SVG coerente

---

## 🟢 PR18 — Pannello formula dado collassabile + guardia sessione (2026-05-22)

### Collapsible dice formula (playtest)
- 🟢 `App.jsx:DiceFormulaRow` — nuovo componente: riga formula per giocatore con parti colorate (base bianco, malus rosso, bonus blu/verde/viola, roll giallo)
- 🟢 `App.jsx:DiceResult` — aggiornato: in modalità `rollDetails` mostra header collassato `▼ formula` (espandibile); in modalità `roll` funzionamento invariato
- 🟢 `App.jsx:fetchGameState` — legge `gs.last_roll_details` e aggancia l'array all'ultimo messaggio master come `roll_details`
- 🟢 Call site `<DiceResult>` — accetta sia `roll` che `rollDetails`; pannello formula visibile solo in playtest senza impatto sull'interfaccia narrativa

### Guardia sessione vuota
- 🟢 `App.jsx:GameScreen useEffect` — se `initialPlayers` è vuoto o null all'avvio, chiama `onRestart()` immediatamente; evita schermata bianca dopo restart backend con stato globale azzerato

---

## 🟡 Prossimi obiettivi

### PR19 — Polish avanzato
- 🟡 Animazione "danno ricevuto" sul token bersaglio (flash rosso dopo colpo)
- 🟡 Morale check per Animo Sanguinario verificato in battaglia reale
- 🟡 Rinomina stat interna `forza/agilita/intelligenza/empatia` → `FO/DE/IN/SA` (cleanup tecnico)
- 🟡 Calibrazione difficoltà: i tiri riescono ancora troppo spesso — rivedere malus threat/difficoltà base

---

## Riferimenti

- 🟢 Regolamento: `GURPS_Lite_Italian_Fourth_Edition.pdf` (repo root)
- 🟢 Power level: **Eccezionale** (75–100 pt) — stat 10–13, skill chiave 12–14
- 🟢 Formula: `3d6 ≤ abilità_effettiva`, margine = target − roll
- 🟢 Soglie: margine ≥10 critico · ≥5 pieno · ≥0 parziale · <0 fail; roll≤4 critico · roll≥17 fail critico
- 🟢 PF = FO (RAW, fedele al manuale)
