# PDF Quality Report — Avventure con Score Basso (40–57)

Analisi condotta il 2026-05-30 sui JSON compilati in `data/compiled_adventures/`.

---

## 1. Tabella Riassuntiva

| # | File | Score | c1 /40 | c2 /25 | c3 /20 | c4 /15 | Titolo estratto? | Loc ID reali? | connections_to? | contains_actors? | contains_clues? | NPC loc risolte? | Clue src risolte? | Problema principale |
|---|------|-------|--------|--------|--------|--------|-----------------|--------------|----------------|-----------------|----------------|-----------------|------------------|---------------------|
| 1 | `fantasy/pdf_il_tempio_della_luna_piena.json` | **40** | 20 | 10 | **0** | 10 | Si | Si | No | No | Parz. | **No** (p3_room_1…) | **No** (nomi PDF raw) | Playable basso (50/100) + errore compressione strutturale (19 stanze→8 loc) + 100% cross-ref rotti |
| 2 | `horror/pdf_dark_wicche.json` | **48** | 23 | 10 | **0** | 15 | Si | Si | No | No | No | **No** (section_1…) | **No** (nomi sezione PDF) | Playable medio-basso (57/100) + 100% NPC e clue con location non riconosciute (section_N) |
| 3 | `sci-fi/pdf_clear_light_of_doomsday.json` | **47** | 27 | 10 | **0** | 10 | Si | Si | No | No | Parz. | **No** (section_1…) | **No** (nomi personaggio come location) | Playable 67/100 + 100% cross-ref rotti + solo 4 loc su 8 con clocks non operativi |
| 4 | `fantasy/pdf_cattedrale_luna_infernale.json` | **52** | 32 | 10 | **0** | 10 | Si | Si | No | No | No | **No** (p2_room_N…) | **No** (nomi viaggio) | Playable 79/100 ma 100% cross-ref rotti; nessun contains_clues |
| 5 | `horror/pdf_opera_unceasing.json` | **53** | 28 | 10 | **0** | 15 | Si | Si | No | No | No | **No** (section_1…) | **No** (nomi luoghi PDF) | 100% NPC e clue non risolti, solo 4 location, playable 69/100 |
| 6 | `action/pdf_minutes_not_hours.json` | **53** | 28 | 10 | **0** | 15 | Si | Si | No | No | No | **No** (section_1…) | **No** (nomi personaggi come location) | 100% cross-ref rotti; NPC tutti a section_N; playable 69/100 |
| 7 | `action/pdf_the_sirens_citadel.json` | **51** | 31 | 10 | **0** | 10 | Si | Si | No | No | Parz. | **No** (section_1…) | **No** (nomi luoghi PDF raw) | 100% cross-ref rotti; solo 10 clue; playable 77/100 ma c3=0 affonda il totale |
| 8 | `fantasy/pdf_cat_nani.json` | **55** | 30 | 10 | **0** | 15 | Si | Si | No | No | Parz. | **No** (p2_room_N…) | **No** (nomi sezione PDF raw) | 100% cross-ref rotti; NPC a p-room placeholder; playable 75/100 |
| 9 | `fantasy/pdf_lupo_di_kosmar.json` | **55** | 30 | 10 | **0** | 15 | Si | Si | No | No | Parz. | **No** (p7_room_N…) | **No** (nomi uppercase come "KOSMAR") | 100% cross-ref rotti; clue src uppercase diverso dagli ID slug |
| 10 | `fantasy/pdf_la_foresta_dei_sogni_impossibili.json` | **57** | 32 | 10 | **0** | 10 | Si | Si | No | No | Parz. | **No** (section_1…) | **No** (nome della foresta come location) | Solo 2 location (estrema compressione); 100% cross-ref rotti; c2 limitato |

---

## 2. Dettaglio per file

### `fantasy/pdf_il_tempio_della_luna_piena.json` — Score 40

**Punteggio peggiore della lista.** Il compilatore ha emesso un **errore critico**: la compressione strutturale ha ridotto 19 stanze originali a sole 8 location, violando la soglia di fedeltà. Il `playable_score` (50/100) riflette questo: quality gate penalizza il `clock_operational_score` (solo 33 — i 2 event_clock hanno 3 step invece dei 4 richiesti). Tutti e 3 gli NPC hanno `location_id` di tipo `p3_room_1` / `p5_room_2` / `p5_room_4`, riferimenti alle stanze originali del PDF non risolti nelle location compilate. Tutti e 11 i clue usano `source_location` come "Megalos" (nome descrittivo, non ID slug) — 0 cross-reference valide → c3=0. Nessun `connections_to` e quasi nessun `contains_actors`.

**Score breakdown:** c1=20 + c2=10 + c3=0 + c4=10 = **40**

---

### `fantasy/pdf_la_foresta_dei_sogni_impossibili.json` — Score 57

Score più alto del gruppo grazie a playable=79. Il problema principale è la **estrema compressione**: solo 2 location (`loc_foresta_sogni_impossibili`, `loc_gabbia_enorme`) per un'avventura articolata. Le 2 location hanno exits, ma il 100% degli attori ha `location_id` del tipo `section_1`/`section_2` e tutti i 10 clue hanno `source_location` impostata al nome letterale della foresta, non all'ID slug → c3=0. Mancano `contains_actors` su tutte le location (nessun punto per c2). Un solo clock con abbastanza step.

**Score breakdown:** c1=32 + c2=15 + c3=0 + c4=10 = **57**

---

### `fantasy/pdf_cat_nani.json` — Score 55

10 location con ID reali e ben strutturate, ma il 100% dei cross-reference è rotto. Gli NPC puntano a stanze raw (`p2_room_4`, `p1_room_4`) e tutti i 11 clue hanno `source_location` testuali ("In viaggio per Zarak", "Arrivo a Serakis") invece degli ID slug. Nessun `contains_actors` su nessuna location, `contains_clues` solo parziale (1 location su 10). FOW uniforme (`status=known`), nessuna location hidden/unknown → c2 perde i 5 punti FOW.

**Score breakdown:** c1=30 + c2=10 + c3=0 + c4=15 = **55**

---

### `fantasy/pdf_lupo_di_kosmar.json` — Score 55

12 location con ID reali, struttura ricca, ma stessa patologia: NPC con `location_id` tipo `p7_room_1` / `p8_room_5`; 12 clue con `source_location` in uppercase ("KOSMAR", "IOTRAS") — case mismatch con gli ID slug lowercase → 0 match → c3=0. Nessun `contains_actors`. FOW uniforme.

**Score breakdown:** c1=30 + c2=10 + c3=0 + c4=15 = **55**

---

### `fantasy/pdf_cattedrale_luna_infernale.json` — Score 52

Playable alto (79/100), 8 location con ID reali e exits. Ma **zero** `contains_clues` e **zero** `contains_actors` su tutte le 8 location. NPC a `p2_room_N`, clue con `source_location` descrittivi ("In viaggio per megalos"). Cross-reference rotte al 100%. FOW uniforme. Un solo clock con 0 step sufficienti.

**Score breakdown:** c1=32 + c2=10 + c3=0 + c4=10 = **52**

---

### `horror/pdf_dark_wicche.json` — Score 48

Playable mediocre (57/100) — il validation report ha 16 warning. 9 NPC (il numero più alto del gruppo) tutti con `location_id = section_1/2/3` — evidentemente il compilatore ha mappato gli NPC alle sezioni del PDF, non alle location semantiche. 11 clue con `source_location` come nomi di sezioni PDF ("A Profane Inferno", "Council with Giebelstadt") non riconoscibili come ID. Zero `contains_actors`, zero `contains_clues`, zero FOW differenziato.

**Score breakdown:** c1=23 + c2=10 + c3=0 + c4=15 = **48**

---

### `horror/pdf_opera_unceasing.json` — Score 53

Solo 4 location (molte meno dell'avventura reale). 7 NPC tutti a `section_1/2/3`, 13 clue con `source_location` come nomi di luoghi testuali ("The Director's Office", "Armand Albret's Attic Room") mai risolti in ID. Zero `contains_actors/clues` su tutte le location. Playable 69/100.

**Score breakdown:** c1=28 + c2=10 + c3=0 + c4=15 = **53**

---

### `action/pdf_minutes_not_hours.json` — Score 53

5 location con ID reali. 6 NPC con `location_id = section_1/2/3` (nome del personaggio come location_id, non il nome luogo). 10 clue con `source_location` come nomi propri di personaggi o nomi di sezione ("The Inside Info", "ADRIAN PINTLE"). Zero `contains_actors/clues`. Playable 69/100.

**Score breakdown:** c1=28 + c2=10 + c3=0 + c4=15 = **53**

---

### `action/pdf_the_sirens_citadel.json` — Score 51

6 location con ID reali. Solo 2 NPC, entrambi con `section_1`/`section_2`. 10 clue con `source_location` come nomi di luoghi testuali ("The Drunken Hangman", "Connors") — non risolti. `contains_clues` parziale (1 location). Playable 77/100 ma c3=0 abbassa drasticamente il totale.

**Score breakdown:** c1=31 + c2=10 + c3=0 + c4=10 = **51**

---

### `sci-fi/pdf_clear_light_of_doomsday.json` — Score 47

8 location con ID reali (nomi Star Trek). 5 NPC con `section_1/2/3`. 10 clue con `source_location` come nomi di personaggi ("Dr. John O'Flaherty") o luoghi testuali ("Ectair IV" — maiuscolo vs slug `ectair_iv`). 3 clock ma 0 con più di 3 step → c4 perde 5 punti. Playable 67/100.

**Score breakdown:** c1=27 + c2=10 + c3=0 + c4=10 = **47**

---

## 3. Pattern Comuni tra le PDF Deboli

### Pattern 1 — Cross-reference completamente rotte (c3 = 0 su tutti e 10)

**100% dei file** ottiene c3=0. Ci sono due cause principali:

- **NPC → location_id non risolto**: il compilatore PDF mappa gli attori alle **sezioni del documento** (`section_1`, `section_2`) o alle **stanze originali** (`p3_room_1`, `p7_room_2`) invece delle location semantiche della `adventure_definition`.
- **Clue → source_location testuale non risolto**: i clue ricevono `source_location` come stringhe descrittive leggibili ("Megalos", "The Director's Office", "KOSMAR") invece degli ID slug presenti nell'array `locations`.

Questi due problemi fanno perdere sistematicamente i 20 punti di c3.

### Pattern 2 — contains_actors e contains_clues sempre vuoti (c2 bloccato a 10/25)

Nessuna delle 10 PDF ha `contains_actors` popolato. Quasi nessuna ha `contains_clues` popolato (al massimo 1-2 location su quelle analizzate hanno `contains_clues` con valori legacy dell'LLM che non matchano gli ID reali). Questo blocca c2 a 10 punti (solo exits e contenuto parziale).

### Pattern 3 — FOW uniforme (tutti status="known")

Tutte le PDF hanno `status="known"` su ogni location. Manca completamente la differenziazione `hidden`/`unknown` per zone non ancora scoperte. Questo fa perdere altri 5 punti in c2.

### Pattern 4 — Playable score medio-basso per le più deboli

I file con score sotto 53 hanno playable basso (50-67/100), spesso per clock con step insufficienti, errori di compressione strutturale, o NPC senza agenda riconosciuta.

### Pattern 5 — connections_to mai popolato

Nessuna delle 10 PDF ha `connections_to` esplicito. Si affida agli `exits`, che però vengono contati nel calcolo (le exits ci sono, quindi quel punto di c2 viene assegnato).

---

## 4. Suggerimento: Ricompilare vs. Lasciare

### Vale la pena ricompilare (dati fondamentalmente buoni, solo linking rotto)

Questi file hanno location ID reali e contenuto narrativo valido — il problema è solo che il linker NPC→location e clue→location non ha funzionato. Una ricompilazione risolverebbe il c3 e porterebbe tutti sopra 70.

| File | Score attuale | Score potenziale | Priorità |
|------|--------------|------------------|----------|
| `fantasy/pdf_la_foresta_dei_sogni_impossibili.json` | 57 | ~77 | Alta |
| `fantasy/pdf_cat_nani.json` | 55 | ~75 | Alta |
| `fantasy/pdf_lupo_di_kosmar.json` | 55 | ~75 | Alta |
| `fantasy/pdf_cattedrale_luna_infernale.json` | 52 | ~72 | Alta |
| `horror/pdf_opera_unceasing.json` | 53 | ~73 | Alta |
| `action/pdf_minutes_not_hours.json` | 53 | ~73 | Alta |
| `action/pdf_the_sirens_citadel.json` | 51 | ~71 | Alta |
| `sci-fi/pdf_clear_light_of_doomsday.json` | 47 | ~67 | Media |

### Dati fondamentalmente incompleti — richiede lavoro manuale o ricompilazione profonda

| File | Score attuale | Problema critico | Strategia |
|------|--------------|-----------------|-----------|
| `fantasy/pdf_il_tempio_della_luna_piena.json` | 40 | Errore di compressione strutturale (19 stanze → 8 loc); clock con troppi pochi step; fidelity 57% sulle location | Ricompilare **con parametro di compressione più basso** (accettare più location) e verificare i clock |
| `horror/pdf_dark_wicche.json` | 48 | Playable basso (57/100); 16 warning; NPC senza agenda riconosciuta; section_N mapping sistematico | Ricompilare — il PDF potrebbe avere struttura narrativa non standard che confonde il parser NPC |

---

*Report generato da analisi diretta dei JSON compilati. Nessun file è stato modificato durante questa analisi.*
