# Pandora Legio

Un motore di gioco di ruolo cooperativo narrativo alimentato da Claude AI. I giocatori formano un gruppo, affrontano missioni procedurali attraverso mappe esplorabili e risolvono azioni tramite un sistema di dadi integrato con generazione narrativa dinamica.

Ispirato a giochi da tavolo come ISS Vanguard e Tainted Grail.

---

## Funzionalità principali

- **5 generi giocabili** — fantascienza, fantasy, horror misterioso, horror survival, militare
- **Missioni procedurali** — Claude genera premessa, verità nascosta, ambientazione e obiettivo unici per ogni partita
- **Mappa a zone** — 6–8 nodi connessi (stile Arkham Horror) che si rivelano progressivamente
- **Sistema d6** — risoluzione azioni con d6 + stat − difficoltà − penalità, con 4 tier di esito
- **12 tipi di effetto** — investigare, combattere, negoziare, stabilizzare, e altro ancora
- **Generazione narrativa** — Claude trasforma il log meccanico in narrazione coerente ogni turno
- **Azioni contestuali** — azioni diverse per ogni personaggio in base a ruolo, scena e stato ferite
- **Diario di missione** — registro scrollabile di ogni turno con esiti e stato del gruppo
- **Upload foto personaggi** — gli avatar influenzano i prompt per illustrazioni AI (Midjourney/DALL-E/SD)
- **Stato canonico persistente** — fili narrativi, fatti scoperti, entità e elementi distrutti tracciati per tutta la missione

---

## Stack tecnologico

**Backend**
- Python 3 + FastAPI + Uvicorn
- Anthropic Claude API (Sonnet 4.5, fallback Opus)
- Pydantic, python-dotenv, python-multipart

**Frontend**
- React 19 + Vite
- JavaScript puro, CSS custom (no librerie UI)

---

## Avvio rapido

### Prerequisiti

- Python 3.10+
- Node.js 18+
- API key Anthropic

### Backend

```bash
cd backend
cp .env.example .env
# Inserisci la tua chiave reale in .env
./start.sh
# Avvia uvicorn su http://127.0.0.1:8002
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Apri http://localhost:5173
```

---

## Flusso di gioco

1. **Setup** — scegli genere e dimensione del gruppo (1–4 giocatori)
2. **Selezione team** — Claude genera 5–7 candidati; il giocatore sceglie il gruppo
3. **Missione** — Claude genera titolo, obiettivo, verità nascosta e scena iniziale
4. **Turno** — ogni giocatore sceglie un'azione → risoluzione meccanica → Claude genera la prossima scena
5. **Progressione** — 3 fasi (Entrata → Profondità → Risoluzione), nodi sbloccati superando gli obiettivi di zona
6. **Fine missione** — vittoria (obiettivo + estrazione) o sconfitta (gruppo a terra / turni esauriti)

---

## Struttura del progetto

```
Pandora-legio/
├── backend/App/
│   ├── main.py              # Server FastAPI ed endpoint
│   ├── engine.py            # Logica di stato del gioco
│   ├── claude_service.py    # Integrazione Claude API
│   ├── models.py            # Modelli Pydantic
│   ├── data_genres.py       # Pack di genere (ambienti, minacce, obiettivi)
│   ├── data_roles.py        # Archetipi personaggio per genere
│   └── data_equipment.py    # Equipaggiamento per missione/ambiente
├── frontend/src/
│   ├── App.jsx              # Intera UI in un unico componente
│   └── App.css
├── CHANGELOG.md
├── requirements.txt
└── package.json
```

---

## API endpoints

| Metodo | Path | Descrizione |
|--------|------|-------------|
| GET | `/game/state` | Stato corrente del gioco |
| GET | `/game/genres` | Generi disponibili |
| POST | `/game/setup` | Inizia la fase di selezione team |
| POST | `/game/select-team` | Conferma team e avvia missione |
| POST | `/game/resolve` | Risolve le azioni del turno corrente |
| POST | `/game/new` | Reset e nuova partita |
| POST | `/game/player/{id}/photo` | Upload foto avatar personaggio |
| GET | `/game/debug-world` | Debug stato narrativo e mappa |

---

## Sistema di risoluzione azioni

```
Risultato = d6 + stat − difficoltà − penalità_ferite

≥ 11  →  Critico   (pieno successo + bonus narrativo)
9–10  →  Successo  (obiettivo raggiunto)
6–8   →  Parziale  (successo con costo)
< 6   →  Fallimento
```

**Stato ferite**: ok → ferito → ferito grave → fuori combattimento (max 3 ferite)

---

## Variabili d'ambiente

| Variabile | Descrizione |
|-----------|-------------|
| `ANTHROPIC_API_KEY` | Chiave API Anthropic (obbligatoria) |
