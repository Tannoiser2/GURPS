# Analisi Avventure AI-Generate — GURPS Adventure System

**Avventure analizzate:** 32  
**Generi:** 7  
**Data analisi:** 2026-05-30

---

## 1. Tabella Riassuntiva per Genere

| Genere | N. | Score medio | % Placeholder | % Ref rotti | Qualità |
|---|---|---|---|---|---|
| horror | 5 | 88.3 | 40.0% | 1.4% | MEDIA |
| sci-fi | 2 | 92.0 | 50.0% | 0.0% | MEDIA |
| investigation | 6 | 90.7 | 50.0% | 1.1% | MEDIA |
| action | 3 | 92.0 | 66.7% | 0.0% | MEDIA |
| fantasy | 8 | 91.0 | 75.0% | 1.6% | CRITICA |
| sci_fi | 5 | N/A | 100.0% | 0.0% | CRITICA |
| romance | 3 | N/A | 100.0% | 39.3% | CRITICA |

---

## 2. Report Individuale per Avventura

### Genere: HORROR

#### La Cattedrale Profanata
- **File:** `ai_cattedrale_profanata.json`
- **Genere:** horror
- **Doctor Score:** 90
- **NPC:** 3 | **Clue:** 6 | **Location:** 6 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** location: 6
- **Location con connections:** 6/6
- **Location con actors:** 2/6
- **Location con clues:** 5/6
- **FOW valori:** open, restricted (differenziato: sì)
- **Clock:** Il Pogrom di Padre Matteo (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (6/6)
- ✓ FOW differenziato: open, restricted
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (6)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ Clue con source_location non esistente (1): clue_red_herring_jewish→cathedral_nave

#### La Biblioteca che Respira
- **File:** `ai_la_biblioteca_che_respira.json`
- **Genere:** horror
- **Doctor Score:** N/A
- **NPC:** 4 | **Clue:** 6 | **Location:** 5 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** site: 5
- **Location con connections:** 5/5
- **Location con actors:** 0/5
- **Location con clues:** 0/5
- **FOW valori:** open (differenziato: NO)
- **Clock:** Catalogazione dei Vivi (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (5/5)
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (6)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ Location con ID placeholder (5/5): loc_start, loc_node2, loc_node3, loc_node4, loc_finale
- ✗ FOW non differenziato: tutte le location hanno stato 'open'
- ✗ Nessuna location ha contains_actors (NPC non collocati)
- ✗ Nessuna location ha contains_clues (clue non collocate)

#### Luci sotto il Ghiaccio
- **File:** `ai_luci_sotto_il_ghiaccio.json`
- **Genere:** horror
- **Doctor Score:** N/A
- **NPC:** 4 | **Clue:** 6 | **Location:** 5 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** site: 5
- **Location con connections:** 5/5
- **Location con actors:** 0/5
- **Location con clues:** 0/5
- **FOW valori:** open (differenziato: NO)
- **Clock:** Tempesta e Dimenticanza (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (5/5)
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (6)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ Location con ID placeholder (5/5): loc_start, loc_node2, loc_node3, loc_node4, loc_finale
- ✗ FOW non differenziato: tutte le location hanno stato 'open'
- ✗ Nessuna location ha contains_actors (NPC non collocati)
- ✗ Nessuna location ha contains_clues (clue non collocate)

#### La Miniera Abbandonata
- **File:** `ai_miniera_abbandonata.json`
- **Genere:** horror
- **Doctor Score:** 87
- **NPC:** 2 | **Clue:** 6 | **Location:** 5 | **Clock:** 1 | **Pressure:** 1 | **Finale:** 2
- **Tipi location:** location: 5
- **Location con connections:** 5/5
- **Location con actors:** 2/5
- **Location con clues:** 4/5
- **FOW valori:** locked, open (differenziato: sì)
- **Clock:** Torcia di Danny in Esaurimento (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (5/5)
- ✓ FOW differenziato: locked, open
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (6)
- ✓ Pressure systems definiti (1)
- ✓ Più finali disponibili (2)

*Nessun problema strutturale rilevato.*

#### Il Treno Maledetto
- **File:** `ai_treno_maledetto.json`
- **Genere:** horror
- **Doctor Score:** 88
- **NPC:** 2 | **Clue:** 6 | **Location:** 6 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** location: 6
- **Location con connections:** 6/6
- **Location con actors:** 2/6
- **Location con clues:** 6/6
- **FOW valori:** open (differenziato: NO)
- **Clock:** Escalation delle Manifestazioni (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (6/6)
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (6)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ FOW non differenziato: tutte le location hanno stato 'open'

### Genere: SCI-FI

#### Corsa alla Luna Nera
- **File:** `ai_corsa_alla_luna_nera.json`
- **Genere:** sci-fi
- **Doctor Score:** N/A
- **NPC:** 4 | **Clue:** 6 | **Location:** 5 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** site: 5
- **Location con connections:** 5/5
- **Location con actors:** 0/5
- **Location con clues:** 0/5
- **FOW valori:** open (differenziato: NO)
- **Clock:** Decadimento Orbitale (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (5/5)
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (6)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ Location con ID placeholder (5/5): loc_start, loc_node2, loc_node3, loc_node4, loc_finale
- ✗ FOW non differenziato: tutte le location hanno stato 'open'
- ✗ Nessuna location ha contains_actors (NPC non collocati)
- ✗ Nessuna location ha contains_clues (clue non collocate)

#### Stazione Orbit
- **File:** `ai_stazione_orbit.json`
- **Genere:** sci-fi
- **Doctor Score:** 92
- **NPC:** 3 | **Clue:** 8 | **Location:** 7 | **Clock:** 2 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** location: 7
- **Location con connections:** 7/7
- **Location con actors:** 3/7
- **Location con clues:** 5/7
- **FOW valori:** locked, open, restricted (differenziato: sì)
- **Clock:** Riserve Ossigeno Pazienti (5 step / max 10); Fuga di Vasquez (5 step / max 8)

**Punti di forza:**
- ✓ Buona rete di connections tra location (7/7)
- ✓ FOW differenziato: locked, open, restricted
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 2 clock con step completi e non duplicati
- ✓ Buon numero di clue (8)
- ✓ Più finali disponibili (2)

*Nessun problema strutturale rilevato.*

### Genere: INVESTIGATION

#### Il Mercato dei Ricordi
- **File:** `ai_il_mercato_dei_ricordi.json`
- **Genere:** investigation
- **Doctor Score:** N/A
- **NPC:** 4 | **Clue:** 6 | **Location:** 5 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** site: 5
- **Location con connections:** 5/5
- **Location con actors:** 0/5
- **Location con clues:** 0/5
- **FOW valori:** open (differenziato: NO)
- **Clock:** Riapertura del Mercato (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (5/5)
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (6)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ Location con ID placeholder (5/5): loc_start, loc_node2, loc_node3, loc_node4, loc_finale
- ✗ FOW non differenziato: tutte le location hanno stato 'open'
- ✗ Nessuna location ha contains_actors (NPC non collocati)
- ✗ Nessuna location ha contains_clues (clue non collocate)

#### Il Miglio Sommerso
- **File:** `ai_il_miglio_sommerso.json`
- **Genere:** investigation
- **Doctor Score:** N/A
- **NPC:** 4 | **Clue:** 6 | **Location:** 5 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** site: 5
- **Location con connections:** 5/5
- **Location con actors:** 0/5
- **Location con clues:** 0/5
- **FOW valori:** open (differenziato: NO)
- **Clock:** Prossima Bassa Marea (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (5/5)
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (6)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ Location con ID placeholder (5/5): loc_start, loc_node2, loc_node3, loc_node4, loc_finale
- ✗ FOW non differenziato: tutte le location hanno stato 'open'
- ✗ Nessuna location ha contains_actors (NPC non collocati)
- ✗ Nessuna location ha contains_clues (clue non collocate)

#### L'Opera delle Maschere
- **File:** `ai_opera_delle_maschere.json`
- **Genere:** investigation
- **Doctor Score:** N/A
- **NPC:** 4 | **Clue:** 6 | **Location:** 5 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** site: 5
- **Location con connections:** 5/5
- **Location con actors:** 0/5
- **Location con clues:** 0/5
- **FOW valori:** open (differenziato: NO)
- **Clock:** Secondo Atto del Rituale (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (5/5)
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (6)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ Location con ID placeholder (5/5): loc_start, loc_node2, loc_node3, loc_node4, loc_finale
- ✗ FOW non differenziato: tutte le location hanno stato 'open'
- ✗ Nessuna location ha contains_actors (NPC non collocati)
- ✗ Nessuna location ha contains_clues (clue non collocate)

#### Porto Fantasma
- **File:** `ai_porto_fantasma.json`
- **Genere:** investigation
- **Doctor Score:** 91
- **NPC:** 3 | **Clue:** 7 | **Location:** 8 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** location: 8
- **Location con connections:** 8/8
- **Location con actors:** 3/8
- **Location con clues:** 7/8
- **FOW valori:** open, restricted (differenziato: sì)
- **Clock:** Prossimo Peschereccio Intercettato (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (8/8)
- ✓ FOW differenziato: open, restricted
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (7)
- ✓ Più finali disponibili (2)

*Nessun problema strutturale rilevato.*

#### Il Quartiere Fumoso
- **File:** `ai_quartiere_fumoso.json`
- **Genere:** investigation
- **Doctor Score:** 91
- **NPC:** 3 | **Clue:** 7 | **Location:** 7 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** location: 7
- **Location con connections:** 7/7
- **Location con actors:** 3/7
- **Location con clues:** 5/7
- **FOW valori:** locked, open, restricted (differenziato: sì)
- **Clock:** Monahan Trova Berni (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (7/7)
- ✓ FOW differenziato: locked, open, restricted
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (7)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ NPC con location_id non esistente (1): actor_monahan→monahan_club

#### Villa Veleno
- **File:** `ai_villa_veleno.json`
- **Genere:** investigation
- **Doctor Score:** 90
- **NPC:** 3 | **Clue:** 8 | **Location:** 6 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** location: 6
- **Location con connections:** 6/6
- **Location con actors:** 1/6
- **Location con clues:** 5/6
- **FOW valori:** open (differenziato: NO)
- **Clock:** Fuga di Rossana (4 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (6/6)
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (8)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ FOW non differenziato: tutte le location hanno stato 'open'
- ✗ Clock 'clock_fuga': solo 4 step su max=10

### Genere: ACTION

#### Ambasciata sotto Assedio
- **File:** `ai_ambasciata_assedio.json`
- **Genere:** action
- **Doctor Score:** 92
- **NPC:** 4 | **Clue:** 8 | **Location:** 7 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** location: 7
- **Location con connections:** 7/7
- **Location con actors:** 3/7
- **Location con clues:** 6/7
- **FOW valori:** locked, open, restricted (differenziato: sì)
- **Clock:** Countdown alle Esecuzioni (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (7/7)
- ✓ FOW differenziato: locked, open, restricted
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (8)
- ✓ Più finali disponibili (2)

*Nessun problema strutturale rilevato.*

#### Autostrada dei Santi
- **File:** `ai_autostrada_dei_santi.json`
- **Genere:** action
- **Doctor Score:** N/A
- **NPC:** 4 | **Clue:** 6 | **Location:** 5 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** site: 5
- **Location con connections:** 5/5
- **Location con actors:** 0/5
- **Location con clues:** 0/5
- **FOW valori:** open (differenziato: NO)
- **Clock:** Carburante e Alba (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (5/5)
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (6)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ Location con ID placeholder (5/5): loc_start, loc_node2, loc_node3, loc_node4, loc_finale
- ✗ FOW non differenziato: tutte le location hanno stato 'open'
- ✗ Nessuna location ha contains_actors (NPC non collocati)
- ✗ Nessuna location ha contains_clues (clue non collocate)

#### Trincea 17
- **File:** `ai_trincea_17.json`
- **Genere:** action
- **Doctor Score:** N/A
- **NPC:** 4 | **Clue:** 6 | **Location:** 5 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** site: 5
- **Location con connections:** 5/5
- **Location con actors:** 0/5
- **Location con clues:** 0/5
- **FOW valori:** open (differenziato: NO)
- **Clock:** Fine della Tregua (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (5/5)
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (6)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ Location con ID placeholder (5/5): loc_start, loc_node2, loc_node3, loc_node4, loc_finale
- ✗ FOW non differenziato: tutte le location hanno stato 'open'
- ✗ Nessuna location ha contains_actors (NPC non collocati)
- ✗ Nessuna location ha contains_clues (clue non collocate)

### Genere: FANTASY

#### Il Banchetto degli Dèi Morti
- **File:** `ai_banchetto_degli_dei_morti.json`
- **Genere:** fantasy
- **Doctor Score:** N/A
- **NPC:** 4 | **Clue:** 6 | **Location:** 5 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** site: 5
- **Location con connections:** 5/5
- **Location con actors:** 0/5
- **Location con clues:** 0/5
- **FOW valori:** open (differenziato: NO)
- **Clock:** Riunificazione involontaria dei Pezzi di Voce (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (5/5)
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (6)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ Location con ID placeholder (5/5): loc_start, loc_node2, loc_node3, loc_node4, loc_finale
- ✗ FOW non differenziato: tutte le location hanno stato 'open'
- ✗ Nessuna location ha contains_actors (NPC non collocati)
- ✗ Nessuna location ha contains_clues (clue non collocate)

#### La Biblioteca dei Sogni Rubati
- **File:** `ai_biblioteca_sogni_rubati.json`
- **Genere:** fantasy
- **Doctor Score:** N/A
- **NPC:** 4 | **Clue:** 6 | **Location:** 5 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** site: 5
- **Location con connections:** 5/5
- **Location con actors:** 0/5
- **Location con clues:** 0/5
- **FOW valori:** open (differenziato: NO)
- **Clock:** Rapimento onirico del quarto studente (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (5/5)
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (6)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ Location con ID placeholder (5/5): loc_start, loc_node2, loc_node3, loc_node4, loc_finale
- ✗ FOW non differenziato: tutte le location hanno stato 'open'
- ✗ Nessuna location ha contains_actors (NPC non collocati)
- ✗ Nessuna location ha contains_clues (clue non collocate)

#### Il Castello Senza Re
- **File:** `ai_castello_senza_re.json`
- **Genere:** fantasy
- **Doctor Score:** 90
- **NPC:** 3 | **Clue:** 7 | **Location:** 5 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** location: 5
- **Location con connections:** 5/5
- **Location con actors:** 1/5
- **Location con clues:** 5/5
- **FOW valori:** open, restricted (differenziato: sì)
- **Clock:** Il Voto di Elezione (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (5/5)
- ✓ FOW differenziato: open, restricted
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (7)
- ✓ Più finali disponibili (2)

*Nessun problema strutturale rilevato.*

#### Il Festival del Sangue
- **File:** `ai_festival_del_sangue.json`
- **Genere:** fantasy
- **Doctor Score:** 92
- **NPC:** 3 | **Clue:** 9 | **Location:** 7 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** location: 7
- **Location con connections:** 7/7
- **Location con actors:** 3/7
- **Location con clues:** 6/7
- **FOW valori:** locked, open, restricted (differenziato: sì)
- **Clock:** Il Rituale dell'Alba del Terzo Giorno (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (7/7)
- ✓ FOW differenziato: locked, open, restricted
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (9)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ NPC con location_id non esistente (2): actor_vane→festival_center, actor_mira→tunnel_cells

#### Il Principe delle Sabbie
- **File:** `ai_il_principe_delle_sabbie.json`
- **Genere:** fantasy
- **Doctor Score:** N/A
- **NPC:** 4 | **Clue:** 6 | **Location:** 5 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** site: 5
- **Location con connections:** 5/5
- **Location con actors:** 0/5
- **Location con clues:** 0/5
- **FOW valori:** open (differenziato: NO)
- **Clock:** La propagazione dei semi nell'oasi (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (5/5)
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (6)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ Location con ID placeholder (5/5): loc_start, loc_node2, loc_node3, loc_node4, loc_finale
- ✗ FOW non differenziato: tutte le location hanno stato 'open'
- ✗ Nessuna location ha contains_actors (NPC non collocati)
- ✗ Nessuna location ha contains_clues (clue non collocate)

#### La Stirpe del Ferro Silente
- **File:** `ai_la_stirpe_del_ferro_silente.json`
- **Genere:** fantasy
- **Doctor Score:** N/A
- **NPC:** 4 | **Clue:** 6 | **Location:** 5 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** site: 5
- **Location con connections:** 5/5
- **Location con actors:** 0/5
- **Location con clues:** 0/5
- **FOW valori:** open (differenziato: NO)
- **Clock:** Spedizione armata del nobile Hadren verso le miniere (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (5/5)
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (6)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ Location con ID placeholder (5/5): loc_start, loc_node2, loc_node3, loc_node4, loc_finale
- ✗ FOW non differenziato: tutte le location hanno stato 'open'
- ✗ Nessuna location ha contains_actors (NPC non collocati)
- ✗ Nessuna location ha contains_clues (clue non collocate)

#### La Maledizione di Raven Hollow
- **File:** `ai_maledizione_di_raven_hollow.json`
- **Genere:** fantasy
- **Doctor Score:** N/A
- **NPC:** 4 | **Clue:** 6 | **Location:** 5 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** site: 5
- **Location con connections:** 5/5
- **Location con actors:** 0/5
- **Location con clues:** 0/5
- **FOW valori:** open (differenziato: NO)
- **Clock:** Il bambino avvelenato peggiora (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (5/5)
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (6)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ Location con ID placeholder (5/5): loc_start, loc_node2, loc_node3, loc_node4, loc_finale
- ✗ FOW non differenziato: tutte le location hanno stato 'open'
- ✗ Nessuna location ha contains_actors (NPC non collocati)
- ✗ Nessuna location ha contains_clues (clue non collocate)

#### Il Santuario delle Ceneri
- **File:** `ai_santuario_delle_ceneri.json`
- **Genere:** fantasy
- **Doctor Score:** N/A
- **NPC:** 4 | **Clue:** 6 | **Location:** 5 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** site: 5
- **Location con connections:** 5/5
- **Location con actors:** 0/5
- **Location con clues:** 0/5
- **FOW valori:** open (differenziato: NO)
- **Clock:** Cenere nei Polmoni (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (5/5)
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (6)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ Location con ID placeholder (5/5): loc_start, loc_node2, loc_node3, loc_node4, loc_finale
- ✗ FOW non differenziato: tutte le location hanno stato 'open'
- ✗ Nessuna location ha contains_actors (NPC non collocati)
- ✗ Nessuna location ha contains_clues (clue non collocate)

### Genere: SCI_FI

#### Il Codice dell'Ultimo Umano
- **File:** `ai_codice_ultimo_umano.json`
- **Genere:** sci_fi
- **Doctor Score:** N/A
- **NPC:** 4 | **Clue:** 6 | **Location:** 5 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** site: 5
- **Location con connections:** 5/5
- **Location con actors:** 0/5
- **Location con clues:** 0/5
- **FOW valori:** open (differenziato: NO)
- **Clock:** Deposito del brevetto Helixar (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (5/5)
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (6)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ Location con ID placeholder (5/5): loc_start, loc_node2, loc_node3, loc_node4, loc_finale
- ✗ FOW non differenziato: tutte le location hanno stato 'open'
- ✗ Nessuna location ha contains_actors (NPC non collocati)
- ✗ Nessuna location ha contains_clues (clue non collocate)

#### Contrabbando di Stelle
- **File:** `ai_contrabbando_di_stelle.json`
- **Genere:** sci_fi
- **Doctor Score:** N/A
- **NPC:** 4 | **Clue:** 6 | **Location:** 5 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** site: 5
- **Location con connections:** 5/5
- **Location con actors:** 0/5
- **Location con clues:** 0/5
- **FOW valori:** open (differenziato: NO)
- **Clock:** Trasferimento del container al Molo 7 (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (5/5)
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (6)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ Location con ID placeholder (5/5): loc_start, loc_node2, loc_node3, loc_node4, loc_finale
- ✗ FOW non differenziato: tutte le location hanno stato 'open'
- ✗ Nessuna location ha contains_actors (NPC non collocati)
- ✗ Nessuna location ha contains_clues (clue non collocate)

#### L'Eredità di Nova Prime
- **File:** `ai_eredita_di_nova_prime.json`
- **Genere:** sci_fi
- **Doctor Score:** N/A
- **NPC:** 4 | **Clue:** 6 | **Location:** 5 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** site: 5
- **Location con connections:** 5/5
- **Location con actors:** 0/5
- **Location con clues:** 0/5
- **FOW valori:** open (differenziato: NO)
- **Clock:** Deterioramento delle coltivazioni (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (5/5)
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (6)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ Location con ID placeholder (5/5): loc_start, loc_node2, loc_node3, loc_node4, loc_finale
- ✗ FOW non differenziato: tutte le location hanno stato 'open'
- ✗ Nessuna location ha contains_actors (NPC non collocati)
- ✗ Nessuna location ha contains_clues (clue non collocate)

#### Frequenza Fantasma
- **File:** `ai_frequenza_fantasma.json`
- **Genere:** sci_fi
- **Doctor Score:** N/A
- **NPC:** 4 | **Clue:** 6 | **Location:** 5 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** site: 5
- **Location con connections:** 5/5
- **Location con actors:** 0/5
- **Location con clues:** 0/5
- **FOW valori:** open (differenziato: NO)
- **Clock:** Protocollo di distruzione dell'agenzia (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (5/5)
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (6)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ Location con ID placeholder (5/5): loc_start, loc_node2, loc_node3, loc_node4, loc_finale
- ✗ FOW non differenziato: tutte le location hanno stato 'open'
- ✗ Nessuna location ha contains_actors (NPC non collocati)
- ✗ Nessuna location ha contains_clues (clue non collocate)

#### Protocollo Silenzio
- **File:** `ai_protocollo_silenzio.json`
- **Genere:** sci_fi
- **Doctor Score:** N/A
- **NPC:** 4 | **Clue:** 6 | **Location:** 5 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** site: 5
- **Location con connections:** 5/5
- **Location con actors:** 0/5
- **Location con clues:** 0/5
- **FOW valori:** open (differenziato: NO)
- **Clock:** Deterioramento orbitale di Kessler-9 (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (5/5)
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (6)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ Location con ID placeholder (5/5): loc_start, loc_node2, loc_node3, loc_node4, loc_finale
- ✗ FOW non differenziato: tutte le location hanno stato 'open'
- ✗ Nessuna location ha contains_actors (NPC non collocati)
- ✗ Nessuna location ha contains_clues (clue non collocate)

### Genere: ROMANCE

#### Il Ballo delle Anime Perdute
- **File:** `ai_il_ballo_delle_anime_perdute.json`
- **Genere:** romance
- **Doctor Score:** N/A
- **NPC:** 3 | **Clue:** 6 | **Location:** 5 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 1
- **Tipi location:** entry: 1, finale: 1, site: 3
- **Location con connections:** 5/5
- **Location con actors:** 0/5
- **Location con clues:** 0/5
- **FOW valori:** open (differenziato: NO)
- **Clock:** Compimento di Ballo Anime Perdute notte Gran Ballo (6 step / max 6)

**Punti di forza:**
- ✓ Buona rete di connections tra location (5/5)
- ✓ Tutti gli NPC hanno location_id validi
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (6)

**Problemi critici:**
- ✗ Location con ID placeholder (5/5): loc_ai_1, loc_ai_2, loc_ai_3, loc_ai_4, loc_ai_5
- ✗ FOW non differenziato: tutte le location hanno stato 'open'
- ✗ Nessuna location ha contains_actors (NPC non collocati)
- ✗ Nessuna location ha contains_clues (clue non collocate)
- ✗ Clue con source_location non esistente (6): clue_1→Biblioteca, scaffale delle poesie romantiche, dietro 'Sonetti d'Amore' di Petrarca, clue_2→Biblioteca, osservando Celestine da vicino, clue_3→Sulla persona di Lord Adrian, ottenibile con furto o confronto diretto, clue_4→Visibile solo se si osservano attentamente gli ospiti o se qualcuno si toglie sciarpe/colletti, clue_5→Camino della biblioteca, tra le ceneri ancora tiepide, clue_6→Hall d'ingresso, sul tavolo degli ospiti
- ✗ finale_conditions con required_clues non esistenti (3): finale_ai_main:clue_ai_1, finale_ai_main:clue_ai_2, finale_ai_main:clue_ai_3

#### Il Debito del Drago
- **File:** `ai_il_debito_del_drago.json`
- **Genere:** romance
- **Doctor Score:** N/A
- **NPC:** 4 | **Clue:** 6 | **Location:** 5 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 2
- **Tipi location:** site: 5
- **Location con connections:** 5/5
- **Location con actors:** 0/5
- **Location con clues:** 0/5
- **FOW valori:** open (differenziato: NO)
- **Clock:** Brindisi del Drago (5 step / max 10)

**Punti di forza:**
- ✓ Buona rete di connections tra location (5/5)
- ✓ Tutti gli NPC hanno location_id validi
- ✓ Tutte le clue hanno source_location validi
- ✓ Le finale_conditions referenziano clue esistenti
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di clue (6)
- ✓ Più finali disponibili (2)

**Problemi critici:**
- ✗ Location con ID placeholder (5/5): loc_start, loc_node2, loc_node3, loc_node4, loc_finale
- ✗ FOW non differenziato: tutte le location hanno stato 'open'
- ✗ Nessuna location ha contains_actors (NPC non collocati)
- ✗ Nessuna location ha contains_clues (clue non collocate)

#### L'Ultima Lettera d'Amore
- **File:** `ai_lultima_lettera_damore.json`
- **Genere:** romance
- **Doctor Score:** N/A
- **NPC:** 5 | **Clue:** 6 | **Location:** 2 | **Clock:** 1 | **Pressure:** 0 | **Finale:** 1
- **Tipi location:** location: 2
- **Location con connections:** 2/2
- **Location con actors:** 0/2
- **Location con clues:** 0/2
- **FOW valori:** open (differenziato: NO)
- **Clock:** La villa rimane sigillata per 48 ore (volontà testamentaria). Ogni 6-8 ore, la tensione emotiva cresce: i PNG iniziano ad accusarsi, vecchi rancori esplodono, e Alexandre diventa sempre più instabile. Se non si raggiunge la verità in tempo, qualcuno potrebbe compiere gesti irreparabili per proteggere i propri segreti. (8 step / max 8)

**Punti di forza:**
- ✓ 1 clock con step completi e non duplicati
- ✓ Buon numero di NPC (5)
- ✓ Buon numero di clue (6)

**Problemi critici:**
- ✗ Location con ID placeholder (2/2): loc_1, loc_2
- ✗ FOW non differenziato: tutte le location hanno stato 'open'
- ✗ Nessuna location ha contains_actors (NPC non collocati)
- ✗ Nessuna location ha contains_clues (clue non collocate)
- ✗ NPC con location_id non esistente (2): npc_3→loc_3, npc_5→loc_4
- ✗ Clue con source_location non esistente (1): clue_4→loc_3
- ✗ finale_conditions con required_clues non esistenti (3): finale_ai_main:clue_ai_1, finale_ai_main:clue_ai_2, finale_ai_main:clue_ai_3

---

## 3. Classifica Generi per Qualità Strutturale

*(dal migliore al peggiore, basato su: score medio − penalità placeholder − penalità ref rotti)*

1. **horror** — Score composito: 67.9 | Score medio: 88.3 | 5 avventure
   - Migliore: La Cattedrale Profanata (90)
   - Peggiore: La Miniera Abbandonata (87)

2. **sci-fi** — Score composito: 67.0 | Score medio: 92.0 | 2 avventure

3. **investigation** — Score composito: 65.3 | Score medio: 90.7 | 6 avventure
   - Migliore: Porto Fantasma (91)
   - Peggiore: Villa Veleno (90)

4. **action** — Score composito: 58.7 | Score medio: 92.0 | 3 avventure

5. **fantasy** — Score composito: 53.0 | Score medio: 91.0 | 8 avventure
   - Migliore: Il Festival del Sangue (92)
   - Peggiore: Il Castello Senza Re (90)

6. **sci_fi** — Score composito: 0.0 | Score medio: N/A | 5 avventure

7. **romance** — Score composito: -11.8 | Score medio: N/A | 3 avventure

---

## 4. Pattern Comuni di Bug

### FOW non differenziato
**Frequenza:** 24/32 avventure (75%)
**Affette:** Autostrada dei Santi, Trincea 17, Il Banchetto degli Dèi Morti, La Biblioteca dei Sogni Rubati, Il Principe delle Sabbie, La Stirpe del Ferro Silente, La Maledizione di Raven Hollow, Il Santuario delle Ceneri, La Biblioteca che Respira, Luci sotto il Ghiaccio, Il Treno Maledetto, Il Mercato dei Ricordi, Il Miglio Sommerso, L'Opera delle Maschere, Villa Veleno, Il Ballo delle Anime Perdute, Il Debito del Drago, L'Ultima Lettera d'Amore, Corsa alla Luna Nera, Il Codice dell'Ultimo Umano, Contrabbando di Stelle, L'Eredità di Nova Prime, Frequenza Fantasma, Protocollo Silenzio

### ID location placeholder
**Frequenza:** 22/32 avventure (69%)
**Affette:** Autostrada dei Santi, Trincea 17, Il Banchetto degli Dèi Morti, La Biblioteca dei Sogni Rubati, Il Principe delle Sabbie, La Stirpe del Ferro Silente, La Maledizione di Raven Hollow, Il Santuario delle Ceneri, La Biblioteca che Respira, Luci sotto il Ghiaccio, Il Mercato dei Ricordi, Il Miglio Sommerso, L'Opera delle Maschere, Il Ballo delle Anime Perdute, Il Debito del Drago, L'Ultima Lettera d'Amore, Corsa alla Luna Nera, Il Codice dell'Ultimo Umano, Contrabbando di Stelle, L'Eredità di Nova Prime, Frequenza Fantasma, Protocollo Silenzio

### NPC non collocati in location (contains_actors vuoto)
**Frequenza:** 22/32 avventure (69%)
**Affette:** Autostrada dei Santi, Trincea 17, Il Banchetto degli Dèi Morti, La Biblioteca dei Sogni Rubati, Il Principe delle Sabbie, La Stirpe del Ferro Silente, La Maledizione di Raven Hollow, Il Santuario delle Ceneri, La Biblioteca che Respira, Luci sotto il Ghiaccio, Il Mercato dei Ricordi, Il Miglio Sommerso, L'Opera delle Maschere, Il Ballo delle Anime Perdute, Il Debito del Drago, L'Ultima Lettera d'Amore, Corsa alla Luna Nera, Il Codice dell'Ultimo Umano, Contrabbando di Stelle, L'Eredità di Nova Prime, Frequenza Fantasma, Protocollo Silenzio

### Clue non collocate in location (contains_clues vuoto)
**Frequenza:** 22/32 avventure (69%)
**Affette:** Autostrada dei Santi, Trincea 17, Il Banchetto degli Dèi Morti, La Biblioteca dei Sogni Rubati, Il Principe delle Sabbie, La Stirpe del Ferro Silente, La Maledizione di Raven Hollow, Il Santuario delle Ceneri, La Biblioteca che Respira, Luci sotto il Ghiaccio, Il Mercato dei Ricordi, Il Miglio Sommerso, L'Opera delle Maschere, Il Ballo delle Anime Perdute, Il Debito del Drago, L'Ultima Lettera d'Amore, Corsa alla Luna Nera, Il Codice dell'Ultimo Umano, Contrabbando di Stelle, L'Eredità di Nova Prime, Frequenza Fantasma, Protocollo Silenzio

### NPC con location_id rotto
**Frequenza:** 3/32 avventure (9%)
**Affette:** Il Festival del Sangue, Il Quartiere Fumoso, L'Ultima Lettera d'Amore

### Clue con source_location rotto
**Frequenza:** 3/32 avventure (9%)
**Affette:** La Cattedrale Profanata, Il Ballo delle Anime Perdute, L'Ultima Lettera d'Amore

### Finale con required_clues rotti
**Frequenza:** 2/32 avventure (6%)
**Affette:** Il Ballo delle Anime Perdute, L'Ultima Lettera d'Amore

---

## 5. Statistiche Globali

- **Avventure totali:** 32
- **Con doctor score:** 10/32
- **Score medio globale:** 90.3
- **Score min/max:** 87 / 92
- **Avventure con problemi:** 27/32 (84%)
- **Problemi totali rilevati:** 99
- **Location placeholder totali:** 107
- **Riferimenti rotti totali:** 19/430 (4.4% se total_refs>0)