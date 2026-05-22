# GURPS Lite RPG — Note per Claude Code

## Cos'è questo progetto

Web app RPG da tavolo basata su **GURPS Lite 4ª edizione italiana** (PDF in repo root: `GURPS_Lite_Italian_Fourth_Edition.pdf`). Il Master è Claude, i giocatori interagiscono via browser. Il backend gestisce la meccanica GURPS pura; il frontend React mostra la narrativa, i dadi, la mappa, il pannello personaggi.

## Architettura

```
backend/App/          FastAPI, porta 8002
  main.py             endpoint REST, stato globale game_state (in-memory)
  engine.py           motore di gioco: tiri GURPS, mappa, combattimento, avanzamento
  claude_service.py   chiamate AI (Claude/OpenAI/Gemini), generazione bibbia, turni master
  models.py           modelli Pydantic: GameState, Player, SceneEntity, WorldNPC, ...
  combat.py           risoluzione attacco-difesa-danno GURPS Lite
  character_creation.py  validazione spesa punti personaggi custom
  data_skills.py      72 skill GURPS con attributo e difficoltà
  data_advantages.py  39 vantaggi/svantaggi con effetti meccanici
  data_roles.py       archetipi per genere e tema
  data_genres.py      pack genere (sci_fi, fantasy, mystery_horror, ww2, ...)

frontend/src/
  App.jsx             componente unico (~4000 righe): UI completa React + Vite, porta 5173
```

## Comandi frequenti

```bash
# Backend
cd /Users/stefan0/Desktop/GURPS/backend
python3 -m uvicorn App.main:app --reload --port 8002

# Frontend
cd /Users/stefan0/Desktop/GURPS/frontend
npm run dev

# Verifica import backend (senza avviare il server)
cd /Users/stefan0/Desktop/GURPS/backend
python3 -c "from App.engine import ...; print('OK')"

# Stato sessione corrente
curl -s http://127.0.0.1:8002/game/state | python3 -m json.tool | head -40
```

## Variabili d'ambiente richieste (`.env` in `backend/`)

```
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here                  # opzionale — per immagini via gpt-image-1
GOOGLE_AI_STUDIO_KEY=your_google_ai_studio_key_here  # opzionale — per immagini via Imagen 4
```

## Meccanica GURPS core

- **Risoluzione**: `3d6 ≤ abilità_effettiva` — margine = target − roll
- **Attributi**: `FO` (Forza) / `DE` (Destrezza) / `IN` (Intelligenza) / `SA` (Salute)
  - Nel codice: chiavi `forza` / `agilita` / `intelligenza` / `empatia` (alias bidirezionale via `normalize_stat`)
- **Soglie esito**: roll ≤ 4 → critico; roll ≥ 17 → fallimento critico; margine ≥ 10 → critico; margine ≤ −10 → fallimento critico
- **PF** = FO; **PF** = SA; **Schivata** = floor(basic_speed) + 3; **Velocità base** = (DE+SA)/4
- **Power level**: Eccezionale (75–100 pt) — stat 10–13, skill chiave 12–14

## Flusso di gioco principale

```
Setup → /game/setup → /game/state (candidate_pool)
Selezione team → /game/select-team
Avvio → /game/master/start-bible
Turno → /game/master/turn-bible  ← fa tiro GURPS Python PRIMA di chiamare Claude
Stato → /game/state               ← consuma last_roll_details (one-shot)
Mappa → /game/move
Combattimento → /game/combat/attack → /game/combat/defend
```

## Stato globale

`game_state: GameState` è una singola istanza in memoria in `main.py`. Il backend **non è persistente** tra riavvii — una sessione persa richiede di ricominciare dal setup. Il frontend lo gestisce con una guardia in `GameScreen.useEffect`.

## Cosa NON fare

- Non aggiungere persistenza (DB, file) senza chiederlo — il design in-memory è intenzionale.
- Non semplificare la meccanica GURPS a favore di "è più facile così" — seguire il manuale.
- Non chiamare `resolve_actions()` dai nuovi endpoint: fa parte del percorso procedurale legacy, non del percorso bibbia (`master_turn_with_bible`).
- Non rimuovere il blocco `══ ESITI DEI TIRI — VINCOLANTI ══` nel prompt Claude — è la guardia che impedisce di trasformare fallimenti in successi.
- Non usare `React.useState` senza importare `React` (l'import è `import React, { ... } from "react"`).

## File di riferimento

- `ROADMAP.md` — storia delle PR e prossimi obiettivi
- `DEAD_CODE.md` — funzioni/endpoint inutilizzati (con spiegazione del perché)
- `GURPS_REFERENCE.md` — tutte le skill, vantaggi, svantaggi con costi e effetti
- `GURPS_Lite_Italian_Fourth_Edition.pdf` — regolamento di riferimento
