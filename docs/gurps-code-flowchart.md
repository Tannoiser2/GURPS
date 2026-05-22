# Flowchart del codice GURPS

Questo documento riassume il flusso reale dell'app: frontend React, backend FastAPI, motore GURPS, generazione narrativa AI, stato missione e combattimento.

## 1. Architettura generale

```mermaid
flowchart LR
    U["Giocatore / Facilitatore"] --> FE["Frontend React\nfrontend/src/App.jsx"]

    FE -->|fetch HTTP| API["Backend FastAPI\nbackend/App/main.py"]

    API --> ENG["Motore di gioco\nbackend/App/engine.py"]
    API --> AI["Servizi AI / canovaccio / scene\nbackend/App/claude_service.py"]
    API --> COMBAT["Combattimento GURPS\nbackend/App/combat.py"]
    API --> DATA["Tabelle dati\nskills, ruoli, equip, generi"]

    ENG --> STATE["GameState\nmodels.py"]
    AI --> STATE
    COMBAT --> STATE
    DATA --> ENG

    STATE --> API
    API -->|JSON| FE
    FE --> UI["Chat Master, mappa,\ncanovaccio, diario, schede PG"]
```

In pratica:

- `App.jsx` decide cosa mostrare e chiama le API.
- `main.py` espone gli endpoint e conserva il `game_state` globale.
- `engine.py` applica regole, tiri, missione, mappa e stato.
- `claude_service.py` crea missione, canovaccio, scene e aggiornamenti narrativi.
- `combat.py` gestisce attacchi, difese, danni e turni NPC in combattimento.

## 2. Avvio partita

```mermaid
flowchart TD
    A["Setup iniziale\nscelta genere/provider/PG"] --> B{"Percorso usato"}

    B -->|Nuovo flusso narrativo| C["/game/adventure/create"]
    C --> D["create_adventure"]
    D --> E["Genera bibbia avventura:\npremessa, obiettivo, NPC,\ncanovaccio, piste, oggetti"]
    E --> F["AdventureScreen mostra riepilogo"]
    F --> G["Inizia avventura"]
    G --> H["/game/master/start-bible"]
    H --> I["master_start_with_bible"]
    I --> L["Prima scena + opzioni + state_updates"]

    B -->|Flusso legacy| M["/game/setup"]
    M --> N["prepare_team_setup"]
    N --> O["Pool personaggi"]
    O --> P["/game/select-team"]
    P --> Q["start_game_from_selection"]
    Q --> R["Missione, mappa, canon, scena iniziale"]

    L --> S["GameScreen"]
    R --> S
```

Nota importante: oggi il flusso piu usato e quello "bibbia avventura", cioe `adventure/create` -> `master/start-bible` -> `master/turn-bible`. Il ramo `setup/select-team` resta nel codice come parte storica/legacy e per alcune schermate.

## 3. Turno narrativo principale

```mermaid
flowchart TD
    A["Giocatore scrive o sceglie un'azione"] --> B["App.jsx: sendAction"]
    B --> C["POST /game/master/turn-bible"]

    C --> D["main.py trova il PG attivo"]
    D --> E["roll_for_player_action\nTiro GURPS 3d6"]
    E --> F["Salva last_roll_details\nnel GameState"]

    F --> G["master_turn_with_bible"]
    G --> H["Claude riceve:\n- bibbia avventura\n- storia chat\n- azione PG\n- tiro gia deciso\n- stato partita"]

    H --> I["Risposta Master:\nnarrative, options, state_updates"]

    I --> J{"state_updates"}
    J -->|indizi/fatti| K["Aggiorna diario e canovaccio visibile"]
    J -->|threat_increase| L["Aumenta minaccia"]
    J -->|activate_combat| M["Prepara combat_scene"]
    J -->|story_over| N["Valuta vittoria e vittorie personali"]

    K --> O["Frontend aggiorna UI"]
    L --> O
    M --> P["Apre mappa tattica"]
    N --> Q["Mostra finale"]
```

Il punto chiave e questo: il tiro viene fatto prima della chiamata narrativa. L'AI non decide se il tiro riesce; riceve gia il risultato meccanico e deve raccontare coerentemente quello.

## 4. Canovaccio, piste e verita nascosta

```mermaid
flowchart TD
    A["generate_story_canon"] --> B["StoryState"]

    B --> C["Soluzione missione"]
    B --> D["Piste / domande"]
    B --> E["Cast / entita chiave"]
    B --> F["Oggetti chiave"]
    B --> G["Verita nascosta"]
    B --> H["Regole di rivelazione"]

    D --> I["Ogni pista dovrebbe avere:\nrisposta, indizi, quando si rivela"]
    E --> J["Ogni entita dovrebbe avere:\ntipo, ruolo, dove, segreto, effetto"]
    F --> K["Ogni oggetto dovrebbe avere:\na cosa serve, dove si trova,\ncome si usa, costo/rischio"]

    I --> L["Scene successive"]
    J --> L
    K --> L
    G --> L

    L --> M["generate_scene_package"]
    M --> N["story_updates"]
    N --> O["Fatti scoperti / indizi scoperti"]
    O --> P["Frontend:\ncolonna destra visibile ai giocatori"]
    B --> Q["Frontend:\ncolonna sinistra facilitatore/playtest"]
```

Qui c'e il problema che stavamo correggendo: il canovaccio deve essere chiuso e leggibile, non generare ogni volta nuovi nomi o piste scollegate. Le scene dovrebbero rivelare o modificare elementi gia definiti.

## 5. Combattimento

```mermaid
flowchart TD
    A["Una scena attiva combat_scene"] --> B["Frontend apre CombatMap"]
    B --> C["Giocatore muove o attacca sulla griglia"]

    C -->|attacco| D["POST /game/combat/attack"]
    D --> E["initiate_combat_action"]
    E --> F{"Colpo richiede difesa?"}

    F -->|si| G["pending_attack"]
    G --> H["Frontend mostra scelta difesa"]
    H --> I["POST /game/combat/defend"]
    I --> J["resolve_defense"]

    F -->|no| K["Danno applicato subito"]
    J --> L["Aggiorna HP/status"]
    K --> L

    L --> M["POST /game/combat/narrate"]
    M --> N["Narrazione breve del colpo"]
    N --> O["POST /game/combat/npc-turn"]
    O --> P["NPC attaccano o cambiano stato"]
    P --> Q{"Nemici sconfitti?"}
    Q -->|si| R["Chiude mappa tattica"]
    Q -->|no| B
```

Il combattimento e separato dal turno narrativo: usa endpoint dedicati, ma continua ad aggiornare lo stesso `GameState`.

## 6. Mappe e immagini

```mermaid
flowchart LR
    FE["Frontend"] --> A["/game/generate-avatar"]
    FE --> B["/game/generate-npc-avatars"]
    FE --> C["/game/generate-scene-image"]
    FE --> D["/game/generate-strategic-map-image"]
    FE --> E["/game/generate-tile-image"]

    A --> AI["claude_service.py\nprovider immagini"]
    B --> AI
    C --> AI
    D --> AI
    E --> AI

    AI --> F{"Provider disponibile?"}
    F -->|si| G["OpenAI/Gemini/etc.\nimmagine base64"]
    F -->|no| H["Fallback/null"]

    G --> FE
    H --> FE
```

Le tile della mappa passano anche da `frontend/src/mapTiles/tileCatalog.js`, che prova ad associare tema, tipo stanza e descrizione a una tile coerente.

## 7. Ciclo dati semplificato

```mermaid
sequenceDiagram
    participant P as Giocatore
    participant R as React App.jsx
    participant F as FastAPI main.py
    participant E as engine.py
    participant C as claude_service.py
    participant S as GameState

    P->>R: sceglie/scrive azione
    R->>F: POST /game/master/turn-bible
    F->>E: roll_for_player_action
    E-->>F: risultato tiro meccanico
    F->>C: master_turn_with_bible con tiro fissato
    C-->>F: narrativa + aggiornamenti stato
    F->>S: salva dettagli tiro / stato globale
    F-->>R: JSON risposta
    R->>R: aggiorna chat, pannelli, mappa, combat
    R->>F: GET /game/state
    F-->>R: snapshot GameState
```

## 8. Lettura rapida del codice

Se devi seguire il codice a mano, l'ordine piu utile e:

1. `frontend/src/App.jsx`: parti da `AdventureScreen`, `GameScreen`, `sendAction`, `applyStateUpdates`.
2. `backend/App/main.py`: guarda gli endpoint `/game/adventure/create`, `/game/master/start-bible`, `/game/master/turn-bible`, `/game/combat/*`.
3. `backend/App/engine.py`: guarda `roll_for_player_action`, `start_game_from_selection`, `resolve_actions`.
4. `backend/App/claude_service.py`: guarda `generate_story_canon`, `generate_mission_package`, `generate_scene_package`, `master_turn_with_bible`.
5. `backend/App/models.py`: controlla `GameState`, `StoryState`, `SceneState`, `Player`.

Per il dettaglio specifico della risoluzione scene, vedi anche `docs/scene-resolution-flowchart.md`.

Per il dettaglio del combattimento tattico, vedi anche `docs/tactical-combat-flowchart.md`.
