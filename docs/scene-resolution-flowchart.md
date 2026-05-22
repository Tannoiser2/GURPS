# Flowchart risoluzione scene

Questo documento spiega come il codice calcola la risoluzione di una scena. Al momento esistono due flussi:

- **Flusso attivo nel gioco attuale**: `/game/master/turn-bible`, usato da `GameScreen.sendAction`.
- **Flusso engine multi-personaggio**: `resolve_actions`, piu strutturato, ancora presente in `engine.py`.

## 1. Flusso attivo: turno Master con bibbia

```mermaid
flowchart TD
    A["Frontend: il giocatore invia un'azione"] --> B["App.jsx: sendAction"]
    B --> C["POST /game/master/turn-bible"]

    C --> D["main.py: trova active_player"]
    D --> E["engine.roll_for_player_action"]

    E --> F["Inferisce skill dal testo azione"]
    F --> G["Calcola target effettivo"]
    G --> H["Tira 3d6"]
    H --> I["Determina esito GURPS"]

    I --> J["Salva last_roll_details nel GameState"]
    J --> K["claude_service.master_turn_with_bible"]

    K --> L["Prompt AI con:\n- bibbia avventura\n- storia recente\n- azione PG\n- tiro gia fissato\n- stato partita"]
    L --> M["AI produce JSON:\nnarrative, roll, options, state_updates"]

    M --> N{"state_updates"}
    N -->|clues_found| O["Frontend aggiunge indizi"]
    N -->|npc_updates| P["Aggiorna stato PNG"]
    N -->|threat_increase| Q["Aumenta minaccia"]
    N -->|activate_combat| R["Apre combattimento tattico"]
    N -->|story_over| S["Chiude avventura"]

    O --> T["React aggiorna schermata"]
    P --> T
    Q --> T
    R --> T
    S --> T
```

### Formula del tiro nel flusso attivo

```mermaid
flowchart TD
    A["Testo azione"] --> B["Tokenizzazione parole"]
    B --> C{"Parole riconosciute?"}

    C -->|si| D["Sceglie skill candidata\nes. investigare, combattere,\ntecnologia, medicina"]
    C -->|no| E["Usa migliore skill del PG\no investigare di default"]

    D --> F{"PG possiede skill?"}
    F -->|si| G["base_skill = valore skill"]
    F -->|no| H["base_skill = attributo - penalita default"]
    E --> G

    G --> I["Bonus vantaggi/svantaggi"]
    H --> I
    I --> J["Bonus oggetto +1\nse l'azione cita un item posseduto"]
    J --> K["Difficolta da scene_tags"]
    K --> L["Malus status/ferite"]
    L --> M["Malus minaccia"]

    M --> N["effective_skill = base + item + vantaggi\n- difficolta - status - minaccia"]
    N --> O["roll = 3d6"]
    O --> P["margin = effective_skill - roll"]

    P --> Q{"Esito"}
    Q -->|"critico RAW o margin >= 10"| R["CRITICO"]
    Q -->|"margin >= 5"| S["SUCCESSO PIENO"]
    Q -->|"margin >= 0"| T["SUCCESSO PARZIALE"]
    Q -->|"fallimento critico RAW o margin <= -10"| U["FALLIMENTO CRITICO"]
    Q -->|"altrimenti"| V["FALLIMENTO"]
```

Il punto delicato: in questo flusso il motore calcola bene il tiro, ma non calcola direttamente `progresso scena`, `tempo` e `minaccia` con una tabella deterministica. Questi aggiornamenti arrivano soprattutto dal JSON prodotto da `master_turn_with_bible`.

## 2. Flusso engine multi-personaggio: `resolve_actions`

Questo e il flusso piu vicino all'idea "ogni personaggio fa qualcosa nella scena".

```mermaid
flowchart TD
    A["Azioni selezionate dai PG"] --> B["resolve_actions"]
    B --> C{"Partita valida?"}
    C -->|setup o missione chiusa| D["Blocca risoluzione"]
    C -->|ok| E["Per ogni player"]

    E --> F{"PG puo agire?"}
    F -->|HP <= 0| G["Salta: fuori combattimento"]
    F -->|si| H["Ricava Action"]

    H --> I{"Origine azione"}
    I -->|structured_intent| J["_action_from_structured_intent"]
    I -->|testo libero| K["_infer_action_from_intent"]
    I -->|azione scelta| L["Azione dalla scheda PG"]

    J --> M{"Requisito oggetto ok?"}
    K --> M
    L --> M
    M -->|no| N["Azione non valida"]
    M -->|si| O["Calcola coordinamento"]

    O --> P["3d6"]
    P --> Q["_resolve_action_roll"]
    Q --> R["Ottiene effect:\nprogress, threat, heal,\nself_damage, time_bonus,\nstory_hint"]

    R --> S["Accumula totali scena"]
    S --> T["Applica danni/cure al PG"]
    T --> U["Registra outcome vincolante\nper la narrativa AI"]
    U --> E

    E --> V["Finito giro PG"]
    V --> W["Aggiorna thread investigativi"]
    W --> X["Aggiorna tempo, progresso, minaccia"]
    X --> Y{"Transizione scena"}
```

## 3. Come viene deciso l'esito globale della scena

Nel flusso `resolve_actions`, dopo aver sommato gli effetti dei personaggi:

```mermaid
flowchart TD
    A["Totali del turno:\ntotal_progress,\ntotal_threat_change,\ntotal_time_bonus"] --> B["scene.objective_progress += total_progress"]
    B --> C["scene.threat_level += total_threat_change"]
    C --> D["time_left diminuisce solo se\nnon c'e progresso"]
    D --> E{"Controlli soglia"}

    E -->|"objective_progress >= objective_target"| F["scene_transition = success"]
    E -->|"time_left == 0"| G["scene_transition = timeout"]
    E -->|"threat_level >= 9"| H["scene_transition = crisis"]
    E -->|altrimenti| I["scene_transition = continue"]

    F --> J["success_clean se threat <= 4\nsuccess_dirty se threat > 4"]
    G --> K["timeout:\nconseguenza e danni"]
    H --> L["crisis:\nminaccia critica e danni"]
    I --> M["La scena continua"]

    J --> N["Aggiorna nodo/mappa/missione"]
    K --> N
    L --> N
    M --> O["Genera nuova descrizione\nsenza cambiare zona"]
```

## 4. Effetti narrativi e canovaccio

```mermaid
flowchart TD
    A["Esiti dei tiri dei PG"] --> B["action_results_summary"]
    B --> C["Blocco vincolante per Claude:\nnon puo cambiare fallimento in successo"]

    C --> D["build_scene_seed_with_canon"]
    D --> E["Seed contiene:\nmissione, fase, scena,\ncanovaccio, mappa, NPC,\nstoria recente, ferite, esito globale"]

    E --> F["generate_scene_package"]
    F --> G["JSON scena nuova:\nscene_text, scene_problem,\nscene_actions, story_updates"]

    G --> H["apply_story_updates"]
    H --> I["discovered_facts"]
    H --> J["thread clue progress"]
    H --> K["resolved_threads"]
    H --> L["destroyed_elements / removed_clues"]

    I --> M["Diario giocatori"]
    J --> N["Piste passano da non emerse\na active/ready/resolved"]
    K --> N
```

`apply_story_updates` e il punto dove il canovaccio viene effettivamente aggiornato:

- aggiunge fatti scoperti;
- collega gli indizi ai thread tramite `clue_for_thread`;
- porta un thread a `ready` quando ha abbastanza indizi;
- chiude automaticamente thread pronti se l'AI non li chiude;
- ignora i `new_threads` generati a runtime, per mantenere il canovaccio chiuso.

## 5. Diagramma completo della risoluzione scena

```mermaid
flowchart TD
    A["Scena corrente"] --> B["PG dichiarano azioni"]
    B --> C["Sistema sceglie skill/azione"]
    C --> D["Tiro 3d6"]
    D --> E["Calcolo margine"]
    E --> F["Esito individuale"]

    F --> G["Effetti meccanici:\nprogresso, minaccia,\ntempo, danni, cure"]
    F --> H["Effetti narrativi:\nstory_hint, indizi,\nconseguenze fiction"]

    G --> I["Somma effetti di gruppo"]
    I --> J{"Soglia scena"}
    J -->|progresso pieno| K["Successo scena"]
    J -->|tempo finito| L["Timeout"]
    J -->|minaccia critica| M["Crisi"]
    J -->|nessuna soglia| N["Continua"]

    K --> O["Aggiorna missione/mappa/fase"]
    L --> O
    M --> O
    N --> P["Aggiorna la stessa scena"]

    H --> Q["Aggiorna canovaccio:\nfatti, indizi, piste"]
    O --> R["Genera prossima scena"]
    P --> R
    Q --> R
    R --> S["Frontend mostra nuova situazione"]
```

## 6. Osservazione di design

Oggi la parte piu solida come calcolo GDR e in `resolve_actions`, perche aggrega piu personaggi e produce progresso/minaccia/tempo. Il flusso realmente usato da `GameScreen` invece passa da `master_turn_with_bible`: e piu semplice da giocare in chat, ma lascia piu decisione all'AI sullo stato scena.

Se vogliamo rendere il gioco piu GDR, il prossimo passo naturale e portare il flusso attivo verso questa forma:

```mermaid
flowchart LR
    A["Ogni PG sceglie azione + skill + oggetto"] --> B["Motore calcola tutti i tiri"]
    B --> C["Motore aggrega progresso/minaccia/tempo"]
    C --> D["AI riceve esiti gia decisi"]
    D --> E["AI narra, ma non decide la matematica"]
```
