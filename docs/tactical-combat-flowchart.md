# Flowchart combattimento tattico

Questo documento descrive come viene risolto il combattimento tattico: dalla mappa esagonale React fino alla matematica GURPS Lite.

## 1. Architettura del combattimento

```mermaid
flowchart LR
    UI["CombatMap\nfrontend/src/App.jsx"] --> API["Endpoint FastAPI\nbackend/App/main.py"]
    API --> ENG["Orchestrazione combat\nbackend/App/engine.py"]
    ENG --> RULES["Regole GURPS Lite\nbackend/App/combat.py"]
    RULES --> STATE["GameState / Player / SceneEntity\nbackend/App/models.py"]
    STATE --> API
    API --> UI
```

Ruoli principali:

- `CombatMap`: mappa esagonale, movimento, selezione bersaglio, copertura, attacco da retro.
- `main.py`: endpoint `/game/combat/*`.
- `engine.py`: crea `pending_attack`, aggiorna `last_attack_result`, gestisce NPC.
- `combat.py`: calcola attacco, difesa, danno, shock, ferite, knockdown e morte.

## 2. Attivazione del combattimento

```mermaid
flowchart TD
    A["Turno narrativo"] --> B["master_turn_with_bible"]
    B --> C{"state_updates.activate_combat?"}
    C -->|no| D["La scena resta narrativa"]
    C -->|si| E["state_updates.combat_scene"]
    E --> F["main.py arricchisce nemici\ncon stat GURPS"]
    F --> G["Frontend: applyStateUpdates"]
    G --> H["setShowCombatMap(true)"]
    H --> I["CombatMap riceve:\nplayers, enemies, activePlayerId,\npendingAttack, handler API"]
```

Il combattimento parte quando il Master AI restituisce `activate_combat=true` dentro `state_updates`. Da quel momento il frontend apre la mappa tattica e usa endpoint separati.

## 3. Turno del giocatore sulla mappa

```mermaid
flowchart TD
    A["Giocatore seleziona token PG"] --> B{"Scelta sulla mappa"}

    B -->|muovere| C["CombatMap calcola hex raggiungibili"]
    C --> D["Click su hex valido"]
    D --> E["Aggiorna posizione locale"]
    E --> F["Consuma turno PG"]
    F --> G["onFinishTurn -> /game/combat/npc-turn"]

    B -->|attaccare| H["CombatMap seleziona bersaglio"]
    H --> I["Calcola distanza"]
    I --> J{"Bersaglio valido?"}
    J -->|no| K["Log: troppo lontano/non valido"]
    J -->|si| L["Calcola geometria:\nrange penalty, copertura,\nattacco da retro"]
    L --> M["handleAttack"]
    M --> N["POST /game/combat/attack"]
```

Nota: il movimento sulla mappa e gestito localmente dal frontend; non passa oggi da un endpoint dedicato. L'attacco invece passa dal backend.

## 4. Attacco del giocatore contro un nemico

```mermaid
flowchart TD
    A["POST /game/combat/attack"] --> B["main.py: combat_attack"]
    B --> C["Trova attacker Player"]
    C --> D{"Azione esiste nella scheda?"}
    D -->|si| E["Usa Action scelta"]
    D -->|no| F["Fallback: Action combattere sintetica"]

    E --> G["engine.initiate_combat_action"]
    F --> G
    G --> H["Imposta attacker.action_type\nnormal/all_out_attack"]
    H --> I{"Bersaglio"}

    I -->|SceneEntity nemico| J["resolve_attack subito\ncon difesa automatica entita"]
    I -->|Player| K["Crea pending_attack\ne aspetta difesa"]

    J --> L["reset_action_type"]
    L --> M["last_attack_result"]
    M --> N["Risposta JSON al frontend"]
    N --> O["Frontend aggiorna log,\nHP nemico locale, narrazione"]
    O --> P["Poi chiama /game/combat/npc-turn"]
```

Quando il bersaglio e una `SceneEntity` nemica, il backend risolve subito tutto lo scambio. La difesa non viene scelta dal giocatore: usa `target_entity.active_defense`.

## 5. Attacco contro un personaggio e difesa attiva

```mermaid
flowchart TD
    A["Attacco verso Player"] --> B["engine.initiate_combat_action"]
    B --> C["Crea pending_attack:\nattacker_id, target_player_id,\nskill, danno, tipo danno,\nroll, action_type"]
    C --> D["Frontend mostra pannello difesa"]

    D --> E["Giocatore sceglie:\ndodge / parry / block\nnormal / all_out_defense"]
    E --> F["CombatMap passa anche:\ncover_bonus, rear_attack"]
    F --> G["POST /game/combat/defend"]

    G --> H["main.py: combat_defend"]
    H --> I["engine.declare_defense"]
    I --> J["Recupera pending_attack"]
    J --> K["Imposta target.action_type"]
    K --> L["combat.resolve_attack"]
    L --> M["Svuota pending_attack"]
    M --> N["reset_action_type attacker/target"]
    N --> O["last_attack_result"]
    O --> P["Frontend aggiorna PG, log, narrazione"]
    P --> Q["Poi chiama /game/combat/npc-turn"]
```

Qui il sistema permette una vera difesa attiva, ma solo quando c'e un `pending_attack`. Gli NPC nel loro turno usano invece una schivata automatica semplificata.

## 6. Matematica GURPS dello scambio

```mermaid
flowchart TD
    A["resolve_attack"] --> B{"Attaccante stordito?"}
    B -->|si| C["Non attacca\nnarrative_hint=attaccante_stordito"]
    B -->|no| D["Calcola attack_level"]

    D --> E["attack_level = skill\n+4 se all_out_attack\n- shock\n-3 se prone"]
    E --> F["Tiro attacco 3d6"]
    F --> G{"Attacco critico/fallimento/mancato?"}

    G -->|fallimento critico| H["Nessun colpo\nhint critico_fallimentare"]
    G -->|mancato| I["Nessun colpo\nhint colpo_mancato"]
    G -->|critico| J["Difesa impossibile"]
    G -->|colpito normale| K["Calcola difesa"]

    K --> L["defense_value = dodge/parry/block\n+ vantaggi\n+ all_out_defense\n+ cover\n- stunned/prone\n0 se rear_attack"]
    L --> M["Tiro difesa 3d6"]
    M --> N{"Difesa riuscita?"}
    N -->|si| O["Colpo difeso\nniente danno"]
    N -->|no| P["Tira danno"]
    J --> P

    P --> Q["raw_damage = formula danno"]
    Q --> R["Moltiplicatore tipo danno:\ncut 1.5, imp 2, cr/burn 1"]
    R --> S["net_damage = max(0,\ndanno_effettivo - DR)"]
    S --> T["Applica HP/status/condizioni"]
```

## 7. Danno, ferite e condizioni

```mermaid
flowchart TD
    A["net_damage"] --> B{"Bersaglio"}

    B -->|Player| C["hp = hp - net_damage\ncon floor morte"]
    B -->|SceneEntity| D["hp = max(0, hp - net_damage)"]

    D --> E{"hp <= 0?"}
    E -->|si| F["status = eliminato"]
    E -->|no| G["Resta vivo"]

    C --> H{"net_damage > 0?"}
    H -->|no| I["Danno assorbito da DR"]
    H -->|si| J["Shock = min(net_damage, 4)"]
    J --> K{"Major wound?\nnet > max_hp/2"}
    K -->|si| L["Tiro SA\nse fallisce: stunned"]
    K -->|no| M["Nessuna major wound"]

    L --> N{"HP scende a 0 o meno?"}
    M --> N
    N -->|si| O["Knockdown check SA\nse fallisce: prone"]
    N -->|no| P["Aggiorna status ferito"]

    O --> Q{"HP <= 0?"}
    Q -->|si| R["Death check SA\nse fallisce: morto"]
    Q -->|no| P
    R --> S["wound_threshold:\nferito_grave / fuori_combattimento / morto"]
    P --> S
```

Effetti principali:

- `shock_penalty`: malus al prossimo attacco/difesa, massimo 4.
- `major_wound`: se un colpo supera meta HP massimi.
- `stunned`: il PG deve recuperare con tiro SA prima di agire.
- `prone`: il PG e a terra, ha penalita.
- `death_check`: quando HP scende a 0 o sotto.

## 8. Turno degli NPC

```mermaid
flowchart TD
    A["Frontend chiama /game/combat/npc-turn"] --> B["engine.npc_combat_turn"]
    B --> C["Trova nemici vivi"]
    C --> D["Trova PG vivi"]
    D --> E{"Ci sono entrambi?"}
    E -->|no| F["Nessun log NPC"]
    E -->|si| G["Per ogni nemico vivo"]

    G --> H["Bersaglio = PG vivo con meno HP"]
    H --> I["Tiro attacco 3d6 vs enemy.attack_skill"]
    I --> J{"Colpisce?"}
    J -->|no| K["Log mancato"]
    J -->|si| L["Difesa automatica PG:\n3d6 vs dodge"]
    L --> M{"Difeso?"}
    M -->|si| N["Log difesa riuscita"]
    M -->|no| O["Tira danno nemico"]
    O --> P["net = raw - target.dr"]
    P --> Q["Aggiorna HP/status/shock"]
    Q --> R["Aggiunge combat_log"]
    K --> R
    N --> R
    R --> G
    R --> S["last_attack_result = ultimo log"]
```

Differenza importante: il turno NPC e piu semplificato di `resolve_attack`. Non usa tutta la stessa funzione `combat.resolve_attack`; ricalcola attacco, schivata e danno direttamente in `engine.npc_combat_turn`.

## 9. Narrazione del colpo

```mermaid
flowchart TD
    A["combat_log / last_attack_result"] --> B["Frontend: _fetchCombatNarration"]
    B --> C["POST /game/combat/narrate"]
    C --> D["claude_service.narrate_combat_result"]
    D --> E["1-2 frasi narrative"]
    E --> F["Chat Master aggiunge narrazione combattimento"]
```

La narrazione del combattimento e successiva alla matematica: riceve gia il `combat_log` e non dovrebbe cambiare il risultato.

## 10. Chiusura combattimento

```mermaid
flowchart TD
    A["Frontend monitora combatEntities"] --> B{"Tutti i nemici HP <= 0?"}
    B -->|no| C["Combattimento continua"]
    B -->|si| D["setGameStateData(in_combat=false)"]
    D --> E["setCombatEntities([])"]
    E --> F["setShowCombatMap(false)"]
    F --> G["Messaggio: combattimento terminato"]
```

Oggi la chiusura tattica e gestita soprattutto dal frontend quando vede tutti i nemici abbattuti. Il flusso narrativo puo anche chiudere con `state_updates.combat_over`, ma la mappa tattica usa questo controllo locale.

## 11. Diagramma compatto completo

```mermaid
flowchart TD
    A["CombatMap"] --> B{"Azione PG"}
    B -->|Muovi| C["Aggiorna posizione locale"]
    B -->|Attacca| D["/game/combat/attack"]

    D --> E{"Target"}
    E -->|Nemico SceneEntity| F["resolve_attack immediato"]
    E -->|Player| G["pending_attack"]

    G --> H["/game/combat/defend"]
    H --> F

    F --> I{"Esito"}
    I -->|miss/defended| J["Log senza danno"]
    I -->|hit| K["Danno - DR"]
    K --> L["HP/status/shock/knockdown/death"]
    J --> M["last_attack_result"]
    L --> M

    M --> N["/game/combat/narrate"]
    N --> O["Narrazione"]
    O --> P["/game/combat/npc-turn"]
    P --> Q["NPC attaccano PG piu ferito"]
    Q --> R{"Nemici tutti a 0 HP?"}
    R -->|si| S["Chiude CombatMap"]
    R -->|no| A
```
