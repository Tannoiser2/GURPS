# JSON Doctor — Report

**Avventure analizzate:** 20
**Score medio:** 7.7/10

| File | Titolo | Genere | Score | Critici | Warning | Info |
|------|--------|--------|-------|---------|---------|------|
| `pdf_gotham39.json` | Gotham '39: The Mirror Eternal | mystery_horror | 0.0 | 1 | 11 | 30 |
| `pdf_never_forget.json` | Never Forget to Die | action | 0.0 | 1 | 11 | 30 |
| `pdf_uzrah.json` | The Third Hall of Uzrah | fantasy | 0.0 | 1 | 12 | 30 |
| `pdf_spectral_tides.json` | Spectral Tides: The Goblin-Thing | mystery_horror | 1.3 | 1 | 9 | 27 |
| `ai_ambasciata_assedio.json` | Ambasciata sotto Assedio | action | 9.2 | 0 | 0 | 8 |
| `ai_quartiere_fumoso.json` | Il Quartiere Fumoso | investigation | 9.3 | 0 | 0 | 7 |
| `ai_festival_del_sangue.json` | Il Festival del Sangue | fantasy | 9.4 | 0 | 0 | 6 |
| `ai_stazione_orbit.json` | Stazione Orbit | sci-fi | 9.4 | 0 | 0 | 6 |
| `ai_castello_senza_re.json` | Il Castello Senza Re | fantasy | 9.5 | 0 | 0 | 5 |
| `ai_cattedrale_profanata.json` | La Cattedrale Profanata | horror | 9.5 | 0 | 0 | 5 |
| `ai_porto_fantasma.json` | Porto Fantasma | investigation | 9.5 | 0 | 0 | 5 |
| `pdf_railgun_road.json` | Railgun Road | action | 9.5 | 0 | 0 | 5 |
| `ai_miniera_abbandonata.json` | La Miniera Abbandonata | horror | 9.6 | 0 | 0 | 4 |
| `ai_treno_maledetto.json` | Il Treno Maledetto | horror | 9.6 | 0 | 0 | 4 |
| `ai_villa_veleno.json` | Villa Veleno | investigation | 9.6 | 0 | 0 | 4 |
| `pdf_scourge_triton.json` | Scourge of Triton | mythic | 9.7 | 0 | 0 | 3 |
| `pdf_flaw_lens.json` | Flaw in the Lens | horror | 9.8 | 0 | 0 | 2 |
| `pdf_beast_keep.json` | Beast of Black Keep | fantasy | 9.9 | 0 | 0 | 1 |
| `pdf_thrusher_manor.json` | Thrusher Manor | horror | 9.9 | 0 | 0 | 1 |
| `pdf_mound_yard.json` | The Mound in the Yard | horror | 10.0 | 0 | 0 | 0 |

---

## Gotham '39: The Mirror Eternal — 0.0/10

**CRITICAL**
- [structure] initial_hook mancante
  - *Fix:* Aggiungi il gancio iniziale per i giocatori
**WARNING**
- [npc] NPC 'Victor Crane': pressure_response assente o insufficiente (<2 livelli)
  - *Fix:* Aggiungi chiavi 'low'/'medium'/'high'/'extreme' con comportamenti specifici
- [npc] NPC 'Victor Crane': reaction_table assente o insufficiente
  - *Fix:* Aggiungi modificatori situazionali (es. 'se_minacciato', 'se_corrotto', ecc.)
- [npc] NPC 'Victor Crane' (antagonista): agenda_pressure=0 troppo basso
  - *Fix:* Imposta agenda_pressure 7-9 per antagonisti
- [npc] NPC 'Tommy Moran': pressure_response assente o insufficiente (<2 livelli)
  - *Fix:* Aggiungi chiavi 'low'/'medium'/'high'/'extreme' con comportamenti specifici
- [npc] NPC 'Tommy Moran': reaction_table assente o insufficiente
  - *Fix:* Aggiungi modificatori situazionali (es. 'se_minacciato', 'se_corrotto', ecc.)
- [npc] NPC 'Detective Loretta Hayes': pressure_response assente o insufficiente (<2 livelli)
  - *Fix:* Aggiungi chiavi 'low'/'medium'/'high'/'extreme' con comportamenti specifici
- [npc] NPC 'Detective Loretta Hayes': reaction_table assente o insufficiente
  - *Fix:* Aggiungi modificatori situazionali (es. 'se_minacciato', 'se_corrotto', ecc.)
- [npc] NPC 'Edna Vayne': pressure_response assente o insufficiente (<2 livelli)
  - *Fix:* Aggiungi chiavi 'low'/'medium'/'high'/'extreme' con comportamenti specifici
- [npc] NPC 'Edna Vayne': reaction_table assente o insufficiente
  - *Fix:* Aggiungi modificatori situazionali (es. 'se_minacciato', 'se_corrotto', ecc.)
- [npc] NPC 'Big Joe Stone': pressure_response assente o insufficiente (<2 livelli)
  - *Fix:* Aggiungi chiavi 'low'/'medium'/'high'/'extreme' con comportamenti specifici
- [npc] NPC 'Big Joe Stone': reaction_table assente o insufficiente
  - *Fix:* Aggiungi modificatori situazionali (es. 'se_minacciato', 'se_corrotto', ecc.)
**INFO**
- [npc] NPC 'Victor Crane': goal mancante
  - *Fix:* Aggiungi un obiettivo narrativo esplicito
- [npc] NPC 'Victor Crane': current_plan mancante
  - *Fix:* Aggiungi il piano attuale dell'NPC
- [npc] NPC 'Victor Crane': fallback_plan mancante
  - *Fix:* Aggiungi cosa fa l'NPC se il piano principale fallisce
- [npc] NPC 'Tommy Moran': goal mancante
  - *Fix:* Aggiungi un obiettivo narrativo esplicito
- [npc] NPC 'Tommy Moran': current_plan mancante
  - *Fix:* Aggiungi il piano attuale dell'NPC
- [npc] NPC 'Tommy Moran': fallback_plan mancante
  - *Fix:* Aggiungi cosa fa l'NPC se il piano principale fallisce
- [npc] NPC 'Detective Loretta Hayes': goal mancante
  - *Fix:* Aggiungi un obiettivo narrativo esplicito
- [npc] NPC 'Detective Loretta Hayes': current_plan mancante
  - *Fix:* Aggiungi il piano attuale dell'NPC
- [npc] NPC 'Detective Loretta Hayes': fallback_plan mancante
  - *Fix:* Aggiungi cosa fa l'NPC se il piano principale fallisce
- [npc] NPC 'Edna Vayne': goal mancante
  - *Fix:* Aggiungi un obiettivo narrativo esplicito
- [npc] NPC 'Edna Vayne': current_plan mancante
  - *Fix:* Aggiungi il piano attuale dell'NPC
- [npc] NPC 'Edna Vayne': fallback_plan mancante
  - *Fix:* Aggiungi cosa fa l'NPC se il piano principale fallisce
- [npc] NPC 'Big Joe Stone': goal mancante
  - *Fix:* Aggiungi un obiettivo narrativo esplicito
- [npc] NPC 'Big Joe Stone': current_plan mancante
  - *Fix:* Aggiungi il piano attuale dell'NPC
- [npc] NPC 'Big Joe Stone': fallback_plan mancante
  - *Fix:* Aggiungi cosa fa l'NPC se il piano principale fallisce
- [clock] Clock 'Escalation degli omicidi': discovery_hint mancante
  - *Fix:* Aggiungi un indizio narrativo che presagisce il clock
- [clue] Indizio 'Frammento di specchio sulla scena del crimine': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Frammento di specchio sulla scena del crimine': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Diari di Karl Vayne': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Diari di Karl Vayne': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Registro dei pagamenti del club Moran': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Registro dei pagamenti del club Moran': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Lista bersagli di Stone': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Lista bersagli di Stone': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Confessione di Detective Hayes': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Confessione di Detective Hayes': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Costume del 'demone' nel teatro': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Costume del 'demone' nel teatro': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Contratto di Crane con le famiglie': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Contratto di Crane con le famiglie': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense

## Never Forget to Die — 0.0/10

**CRITICAL**
- [structure] initial_hook mancante
  - *Fix:* Aggiungi il gancio iniziale per i giocatori
**WARNING**
- [npc] NPC 'Wernher Nachtnebel 'The Night Fog'': pressure_response assente o insufficiente (<2 livelli)
  - *Fix:* Aggiungi chiavi 'low'/'medium'/'high'/'extreme' con comportamenti specifici
- [npc] NPC 'Wernher Nachtnebel 'The Night Fog'': reaction_table assente o insufficiente
  - *Fix:* Aggiungi modificatori situazionali (es. 'se_minacciato', 'se_corrotto', ecc.)
- [npc] NPC 'Wernher Nachtnebel 'The Night Fog'' (antagonista): agenda_pressure=0 troppo basso
  - *Fix:* Imposta agenda_pressure 7-9 per antagonisti
- [npc] NPC 'Célia Nachtnebel': pressure_response assente o insufficiente (<2 livelli)
  - *Fix:* Aggiungi chiavi 'low'/'medium'/'high'/'extreme' con comportamenti specifici
- [npc] NPC 'Célia Nachtnebel': reaction_table assente o insufficiente
  - *Fix:* Aggiungi modificatori situazionali (es. 'se_minacciato', 'se_corrotto', ecc.)
- [npc] NPC 'Colonnello Petrov': pressure_response assente o insufficiente (<2 livelli)
  - *Fix:* Aggiungi chiavi 'low'/'medium'/'high'/'extreme' con comportamenti specifici
- [npc] NPC 'Colonnello Petrov': reaction_table assente o insufficiente
  - *Fix:* Aggiungi modificatori situazionali (es. 'se_minacciato', 'se_corrotto', ecc.)
- [npc] NPC 'Handler M (voce radio)': pressure_response assente o insufficiente (<2 livelli)
  - *Fix:* Aggiungi chiavi 'low'/'medium'/'high'/'extreme' con comportamenti specifici
- [npc] NPC 'Handler M (voce radio)': reaction_table assente o insufficiente
  - *Fix:* Aggiungi modificatori situazionali (es. 'se_minacciato', 'se_corrotto', ecc.)
- [npc] NPC 'Boris Ivankov': pressure_response assente o insufficiente (<2 livelli)
  - *Fix:* Aggiungi chiavi 'low'/'medium'/'high'/'extreme' con comportamenti specifici
- [npc] NPC 'Boris Ivankov': reaction_table assente o insufficiente
  - *Fix:* Aggiungi modificatori situazionali (es. 'se_minacciato', 'se_corrotto', ecc.)
**INFO**
- [npc] NPC 'Wernher Nachtnebel 'The Night Fog'': goal mancante
  - *Fix:* Aggiungi un obiettivo narrativo esplicito
- [npc] NPC 'Wernher Nachtnebel 'The Night Fog'': current_plan mancante
  - *Fix:* Aggiungi il piano attuale dell'NPC
- [npc] NPC 'Wernher Nachtnebel 'The Night Fog'': fallback_plan mancante
  - *Fix:* Aggiungi cosa fa l'NPC se il piano principale fallisce
- [npc] NPC 'Célia Nachtnebel': goal mancante
  - *Fix:* Aggiungi un obiettivo narrativo esplicito
- [npc] NPC 'Célia Nachtnebel': current_plan mancante
  - *Fix:* Aggiungi il piano attuale dell'NPC
- [npc] NPC 'Célia Nachtnebel': fallback_plan mancante
  - *Fix:* Aggiungi cosa fa l'NPC se il piano principale fallisce
- [npc] NPC 'Colonnello Petrov': goal mancante
  - *Fix:* Aggiungi un obiettivo narrativo esplicito
- [npc] NPC 'Colonnello Petrov': current_plan mancante
  - *Fix:* Aggiungi il piano attuale dell'NPC
- [npc] NPC 'Colonnello Petrov': fallback_plan mancante
  - *Fix:* Aggiungi cosa fa l'NPC se il piano principale fallisce
- [npc] NPC 'Handler M (voce radio)': goal mancante
  - *Fix:* Aggiungi un obiettivo narrativo esplicito
- [npc] NPC 'Handler M (voce radio)': current_plan mancante
  - *Fix:* Aggiungi il piano attuale dell'NPC
- [npc] NPC 'Handler M (voce radio)': fallback_plan mancante
  - *Fix:* Aggiungi cosa fa l'NPC se il piano principale fallisce
- [npc] NPC 'Boris Ivankov': goal mancante
  - *Fix:* Aggiungi un obiettivo narrativo esplicito
- [npc] NPC 'Boris Ivankov': current_plan mancante
  - *Fix:* Aggiungi il piano attuale dell'NPC
- [npc] NPC 'Boris Ivankov': fallback_plan mancante
  - *Fix:* Aggiungi cosa fa l'NPC se il piano principale fallisce
- [clock] Clock 'Distribuzione della lethepoxide': discovery_hint mancante
  - *Fix:* Aggiungi un indizio narrativo che presagisce il clock
- [clue] Indizio 'Campione di lethepoxide dalla cabina di Petrov': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Campione di lethepoxide dalla cabina di Petrov': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Dossier nascosto di Petrov': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Dossier nascosto di Petrov': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Informazione di Célia sul divorzio e la fuga': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Informazione di Célia sul divorzio e la fuga': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Documenti del debito di Célia con Ivankov': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Documenti del debito di Célia con Ivankov': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Formula completa della lethepoxide': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Formula completa della lethepoxide': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Lista agenti KGB con campioni': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Lista agenti KGB con campioni': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Canale di fuga di Ivankov': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Canale di fuga di Ivankov': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense

## The Third Hall of Uzrah — 0.0/10

**CRITICAL**
- [structure] initial_hook mancante
  - *Fix:* Aggiungi il gancio iniziale per i giocatori
**WARNING**
- [npc] NPC 'Surrat al-Risha': pressure_response assente o insufficiente (<2 livelli)
  - *Fix:* Aggiungi chiavi 'low'/'medium'/'high'/'extreme' con comportamenti specifici
- [npc] NPC 'Surrat al-Risha': reaction_table assente o insufficiente
  - *Fix:* Aggiungi modificatori situazionali (es. 'se_minacciato', 'se_corrotto', ecc.)
- [npc] NPC 'Il Guardiano d'Ottone': pressure_response assente o insufficiente (<2 livelli)
  - *Fix:* Aggiungi chiavi 'low'/'medium'/'high'/'extreme' con comportamenti specifici
- [npc] NPC 'Il Guardiano d'Ottone': reaction_table assente o insufficiente
  - *Fix:* Aggiungi modificatori situazionali (es. 'se_minacciato', 'se_corrotto', ecc.)
- [npc] NPC 'Il Guardiano d'Ottone' (antagonista): agenda_pressure=0 troppo basso
  - *Fix:* Imposta agenda_pressure 7-9 per antagonisti
- [npc] NPC 'Al-Jarrakh il Re Stregone (voce dal libro)': pressure_response assente o insufficiente (<2 livelli)
  - *Fix:* Aggiungi chiavi 'low'/'medium'/'high'/'extreme' con comportamenti specifici
- [npc] NPC 'Al-Jarrakh il Re Stregone (voce dal libro)': reaction_table assente o insufficiente
  - *Fix:* Aggiungi modificatori situazionali (es. 'se_minacciato', 'se_corrotto', ecc.)
- [npc] NPC 'Al-Jarrakh il Re Stregone (voce dal libro)' (antagonista): agenda_pressure=0 troppo basso
  - *Fix:* Imposta agenda_pressure 7-9 per antagonisti
- [npc] NPC 'Djinn del Vento Secco': pressure_response assente o insufficiente (<2 livelli)
  - *Fix:* Aggiungi chiavi 'low'/'medium'/'high'/'extreme' con comportamenti specifici
- [npc] NPC 'Djinn del Vento Secco': reaction_table assente o insufficiente
  - *Fix:* Aggiungi modificatori situazionali (es. 'se_minacciato', 'se_corrotto', ecc.)
- [npc] NPC 'Miriam al-Khamis': pressure_response assente o insufficiente (<2 livelli)
  - *Fix:* Aggiungi chiavi 'low'/'medium'/'high'/'extreme' con comportamenti specifici
- [npc] NPC 'Miriam al-Khamis': reaction_table assente o insufficiente
  - *Fix:* Aggiungi modificatori situazionali (es. 'se_minacciato', 'se_corrotto', ecc.)
**INFO**
- [npc] NPC 'Surrat al-Risha': goal mancante
  - *Fix:* Aggiungi un obiettivo narrativo esplicito
- [npc] NPC 'Surrat al-Risha': current_plan mancante
  - *Fix:* Aggiungi il piano attuale dell'NPC
- [npc] NPC 'Surrat al-Risha': fallback_plan mancante
  - *Fix:* Aggiungi cosa fa l'NPC se il piano principale fallisce
- [npc] NPC 'Il Guardiano d'Ottone': goal mancante
  - *Fix:* Aggiungi un obiettivo narrativo esplicito
- [npc] NPC 'Il Guardiano d'Ottone': current_plan mancante
  - *Fix:* Aggiungi il piano attuale dell'NPC
- [npc] NPC 'Il Guardiano d'Ottone': fallback_plan mancante
  - *Fix:* Aggiungi cosa fa l'NPC se il piano principale fallisce
- [npc] NPC 'Al-Jarrakh il Re Stregone (voce dal libro)': goal mancante
  - *Fix:* Aggiungi un obiettivo narrativo esplicito
- [npc] NPC 'Al-Jarrakh il Re Stregone (voce dal libro)': current_plan mancante
  - *Fix:* Aggiungi il piano attuale dell'NPC
- [npc] NPC 'Al-Jarrakh il Re Stregone (voce dal libro)': fallback_plan mancante
  - *Fix:* Aggiungi cosa fa l'NPC se il piano principale fallisce
- [npc] NPC 'Djinn del Vento Secco': goal mancante
  - *Fix:* Aggiungi un obiettivo narrativo esplicito
- [npc] NPC 'Djinn del Vento Secco': current_plan mancante
  - *Fix:* Aggiungi il piano attuale dell'NPC
- [npc] NPC 'Djinn del Vento Secco': fallback_plan mancante
  - *Fix:* Aggiungi cosa fa l'NPC se il piano principale fallisce
- [npc] NPC 'Miriam al-Khamis': goal mancante
  - *Fix:* Aggiungi un obiettivo narrativo esplicito
- [npc] NPC 'Miriam al-Khamis': current_plan mancante
  - *Fix:* Aggiungi il piano attuale dell'NPC
- [npc] NPC 'Miriam al-Khamis': fallback_plan mancante
  - *Fix:* Aggiungi cosa fa l'NPC se il piano principale fallisce
- [clock] Clock 'Influenza di Al-Jarrakh sui PG': discovery_hint mancante
  - *Fix:* Aggiungi un indizio narrativo che presagisce il clock
- [clue] Indizio 'Il foglio strappato con i tre indizi': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Il foglio strappato con i tre indizi': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Racconto del Djinn sulla battaglia dei maghi': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Racconto del Djinn sulla battaglia dei maghi': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'La parola di sigillo del libro': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'La parola di sigillo del libro': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Mappa parziale di Miriam': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Mappa parziale di Miriam': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Iscrizione sulla base del Guardiano': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Iscrizione sulla base del Guardiano': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Voce di Al-Jarrakh dal libro': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Voce di Al-Jarrakh dal libro': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Registro del tesoro di Uzrah': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Registro del tesoro di Uzrah': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense

## Spectral Tides: The Goblin-Thing — 1.3/10

**CRITICAL**
- [structure] initial_hook mancante
  - *Fix:* Aggiungi il gancio iniziale per i giocatori
**WARNING**
- [npc] NPC 'Conroy Biggins': pressure_response assente o insufficiente (<2 livelli)
  - *Fix:* Aggiungi chiavi 'low'/'medium'/'high'/'extreme' con comportamenti specifici
- [npc] NPC 'Conroy Biggins': reaction_table assente o insufficiente
  - *Fix:* Aggiungi modificatori situazionali (es. 'se_minacciato', 'se_corrotto', ecc.)
- [npc] NPC 'Conroy Biggins' (antagonista): agenda_pressure=0 troppo basso
  - *Fix:* Imposta agenda_pressure 7-9 per antagonisti
- [npc] NPC 'Jake Samson': pressure_response assente o insufficiente (<2 livelli)
  - *Fix:* Aggiungi chiavi 'low'/'medium'/'high'/'extreme' con comportamenti specifici
- [npc] NPC 'Jake Samson': reaction_table assente o insufficiente
  - *Fix:* Aggiungi modificatori situazionali (es. 'se_minacciato', 'se_corrotto', ecc.)
- [npc] NPC 'Zacharias Biggins': pressure_response assente o insufficiente (<2 livelli)
  - *Fix:* Aggiungi chiavi 'low'/'medium'/'high'/'extreme' con comportamenti specifici
- [npc] NPC 'Zacharias Biggins': reaction_table assente o insufficiente
  - *Fix:* Aggiungi modificatori situazionali (es. 'se_minacciato', 'se_corrotto', ecc.)
- [npc] NPC 'Sceriffo Dale Pruitt': pressure_response assente o insufficiente (<2 livelli)
  - *Fix:* Aggiungi chiavi 'low'/'medium'/'high'/'extreme' con comportamenti specifici
- [npc] NPC 'Sceriffo Dale Pruitt': reaction_table assente o insufficiente
  - *Fix:* Aggiungi modificatori situazionali (es. 'se_minacciato', 'se_corrotto', ecc.)
**INFO**
- [npc] NPC 'Conroy Biggins': goal mancante
  - *Fix:* Aggiungi un obiettivo narrativo esplicito
- [npc] NPC 'Conroy Biggins': current_plan mancante
  - *Fix:* Aggiungi il piano attuale dell'NPC
- [npc] NPC 'Conroy Biggins': fallback_plan mancante
  - *Fix:* Aggiungi cosa fa l'NPC se il piano principale fallisce
- [npc] NPC 'Jake Samson': goal mancante
  - *Fix:* Aggiungi un obiettivo narrativo esplicito
- [npc] NPC 'Jake Samson': current_plan mancante
  - *Fix:* Aggiungi il piano attuale dell'NPC
- [npc] NPC 'Jake Samson': fallback_plan mancante
  - *Fix:* Aggiungi cosa fa l'NPC se il piano principale fallisce
- [npc] NPC 'Zacharias Biggins': goal mancante
  - *Fix:* Aggiungi un obiettivo narrativo esplicito
- [npc] NPC 'Zacharias Biggins': current_plan mancante
  - *Fix:* Aggiungi il piano attuale dell'NPC
- [npc] NPC 'Zacharias Biggins': fallback_plan mancante
  - *Fix:* Aggiungi cosa fa l'NPC se il piano principale fallisce
- [npc] NPC 'Sceriffo Dale Pruitt': goal mancante
  - *Fix:* Aggiungi un obiettivo narrativo esplicito
- [npc] NPC 'Sceriffo Dale Pruitt': current_plan mancante
  - *Fix:* Aggiungi il piano attuale dell'NPC
- [npc] NPC 'Sceriffo Dale Pruitt': fallback_plan mancante
  - *Fix:* Aggiungi cosa fa l'NPC se il piano principale fallisce
- [clock] Clock 'La notte scende su Sitka Island': discovery_hint mancante
  - *Fix:* Aggiungi un indizio narrativo che presagisce il clock
- [clue] Indizio 'Tracce di Jake nella foresta': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Tracce di Jake nella foresta': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Lo zaino di Jake con le fotografie': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Lo zaino di Jake con le fotografie': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Documenti della guardia costiera nel bunker': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Documenti della guardia costiera nel bunker': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Articolo di giornale su Conroy Biggins': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Articolo di giornale su Conroy Biggins': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Siringa usata vicino a Jake': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Siringa usata vicino a Jake': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Segni di gas tossici nella miniera': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Segni di gas tossici nella miniera': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Radio funzionante nel bunker': hidden_implication mancante
  - *Fix:* Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)
- [clue] Indizio 'Radio funzionante nel bunker': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense

## Ambasciata sotto Assedio — 9.2/10

**INFO**
- [clue] Indizio 'Log di accesso al sistema elettronico': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Documento d'identità siriano di Aquila': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Testimonianza dell'ambasciatore sulla cassaforte': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Il custode Lorenzo e il suo segreto': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Planimetrie originali degli anni '60': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Radio nascosta nella sala comunicazioni': payoff mancante
  - *Fix:* Specifica cosa rivela narrativamente questo indizio
- [clue] Indizio 'Radio nascosta nella sala comunicazioni': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Comportamento sospetto dell'autista': payoff mancante
  - *Fix:* Specifica cosa rivela narrativamente questo indizio

## Il Quartiere Fumoso — 9.3/10

**INFO**
- [clue] Indizio 'Pistola non registrata a Ferretti': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Lettera di minaccia anonima a Ferretti': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Testimonianza di Concetta Ferretti': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Appartamento del contabile Berni': payoff mancante
  - *Fix:* Specifica cosa rivela narrativamente questo indizio
- [clue] Indizio 'Appartamento del contabile Berni': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Il Libro Mastro di Monahan': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Nota di 'suicidio' scritta a macchina': payoff mancante
  - *Fix:* Specifica cosa rivela narrativamente questo indizio

## Il Festival del Sangue — 9.4/10

**INFO**
- [clue] Indizio 'Testimonianza storica di Horace il Gioielliere': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Registro segreto del culto': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Accesso ai tunnel sotto la fontana': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Testo antico nelle biblioteche del culto': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Comunicazione diretta con il Guardiano delle Acque': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Rivalità commerciale tra mercanti': payoff mancante
  - *Fix:* Specifica cosa rivela narrativamente questo indizio

## Stazione Orbit — 9.4/10

**INFO**
- [clue] Indizio 'File classificati FTL mancanti': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Log di trasmissione dati esterna': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Dispositivo personale di Vasquez': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Log medici pre-incidente': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Picco di radiazioni anomalo': payoff mancante
  - *Fix:* Specifica cosa rivela narrativamente questo indizio
- [clue] Indizio 'Comportamento sospetto di Sorokin': payoff mancante
  - *Fix:* Specifica cosa rivela narrativamente questo indizio

## Il Castello Senza Re — 9.5/10

**INFO**
- [clue] Indizio 'Accordo segreto di Mira con Keldara': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Codice cifrato di Voss con Keldara': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Fonte magica della tempesta': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Mago nascosto nei sotterranei': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Lettera di minacce tra casate rivali': payoff mancante
  - *Fix:* Specifica cosa rivela narrativamente questo indizio

## La Cattedrale Profanata — 9.5/10

**INFO**
- [clue] Indizio 'Grimori nascosti nella cella di Godfrey': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Registro delle reliquie false': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Lettere del mercante allo studio del vescovo': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Testimonianza del mercante di Colonia': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Simbolo pseudo-ebraico sulla parete': payoff mancante
  - *Fix:* Specifica cosa rivela narrativamente questo indizio

## Porto Fantasma — 9.5/10

**INFO**
- [clue] Indizio 'Tracce di eroina sul molo est': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Bonifici mensili al sindaco Corsetti': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Registro chiamate del maresciallo': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Casse di rifornimento sull'isola': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Relazione meteorologica sulle tempeste': payoff mancante
  - *Fix:* Specifica cosa rivela narrativamente questo indizio

## Railgun Road — 9.5/10

**INFO**
- [clue] Indizio 'Informazioni degli ostaggi sul leader': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Cartella medica della figlia di Chen': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Carico Medcross nel bunker': payoff mancante
  - *Fix:* Specifica cosa rivela narrativamente questo indizio
- [clue] Indizio 'Carico Medcross nel bunker': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Relitto di veicolo pesante al km 350': payoff mancante
  - *Fix:* Specifica cosa rivela narrativamente questo indizio

## La Miniera Abbandonata — 9.6/10

**INFO**
- [clue] Indizio 'Osservazione diretta della reazione alla luce': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Mappa della miniera nell'ufficio del guardiano': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Segnali luminosi intermittenti dal livello 3': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Rilevatore di gas che scatta': payoff mancante
  - *Fix:* Specifica cosa rivela narrativamente questo indizio

## Il Treno Maledetto — 9.6/10

**INFO**
- [clue] Indizio 'Documenti storici del tunnel nelle carte del capotreno': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Borsa rituale di Elspeth Crane': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Segni rituali sotto il tappeto nel corridoio': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Flacone di arsenico nella borsa di un passeggero': payoff mancante
  - *Fix:* Specifica cosa rivela narrativamente questo indizio

## Villa Veleno — 9.6/10

**INFO**
- [clue] Indizio 'Testimonianza del notaio Calvetti': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Bozza del nuovo testamento': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Libro di botanica con pagine piegate': payoff mancante
  - *Fix:* Specifica cosa rivela narrativamente questo indizio
- [clue] Indizio 'Vino adulterato di qualità scadente': payoff mancante
  - *Fix:* Specifica cosa rivela narrativamente questo indizio

## Scourge of Triton — 9.7/10

**INFO**
- [clue] Indizio 'Lysander il Collezionista a Corinto': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'La Conchiglia di Anfitrite': payoff mancante
  - *Fix:* Specifica cosa rivela narrativamente questo indizio
- [clue] Indizio 'Testimonianza di Theron il Rivale': payoff mancante
  - *Fix:* Specifica cosa rivela narrativamente questo indizio

## Flaw in the Lens — 9.8/10

**INFO**
- [clue] Indizio 'Manuale tecnico del telescopio con annotazioni': wrong_interpretations mancante
  - *Fix:* Aggiungi 1-2 false interpretazioni possibili per creare suspense
- [clue] Indizio 'Valori anomali di CO2 nell'osservatorio': payoff mancante
  - *Fix:* Specifica cosa rivela narrativamente questo indizio

## Beast of Black Keep — 9.9/10

**INFO**
- [clue] Indizio 'Tracce di grande bestia verso nord': payoff mancante
  - *Fix:* Specifica cosa rivela narrativamente questo indizio

## Thrusher Manor — 9.9/10

**INFO**
- [clue] Indizio 'Diario medico: epidemia di febbre': payoff mancante
  - *Fix:* Specifica cosa rivela narrativamente questo indizio
