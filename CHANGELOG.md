# Pandora Legio — Changelog

## Nuove funzionalità

### 🗺 Mappa a Zone (stile Arkham Horror)
- Claude genera automaticamente una mappa con 5-7 zone connesse all'inizio di ogni missione
- Ogni zona ha tipo (entry/corridor/room/boss/exit), nome evocativo, posizione SVG
- Stato visivo: unknown → active → cleared / danger / locked
- Le zone si rivelano progressivamente avanzando nella missione
- Token personaggi (con foto avatar) posizionati nella zona corrente
- Token minaccia (☠) posizionato nelle zone pericolose/non rivelate

### 📖 Diario di Missione
- Ogni turno viene registrato con: narrativa, azioni, esiti per giocatore, ferite
- Scrollabile, collassabile, con timeline visuale per turno
- Ogni voce mostra: azioni scelte, outcome (successo pieno/parziale/fallimento), stato ferite
- Integrato con illustrazione scena generata da Claude

### 🎨 Illustrazioni Scena + Foto Giocatori
- Ogni turno Claude genera un prompt dettagliato per generatori AI (Midjourney/DALL-E/SD)
- Se i giocatori hanno foto caricate, il prompt descrive i volti reali nell'illustrazione
- Prompt mostrato nel diario e nel pannello scena corrente
- Copia il prompt e incollalo nel tuo generatore preferito

### 📸 Upload Foto Personaggi
- Ogni personaggio ha un avatar cliccabile nella scheda
- Click sull'avatar → scegli foto dal dispositivo
- Foto usata come: avatar nella UI, riferimento per le illustrazioni, token sulla mappa
- Endpoint: POST /game/player/{id}/photo (multipart form)

### 🔒 Sicurezza
- API key rimossa dal codice sorgente
- Usa variabile d'ambiente ANTHROPIC_API_KEY
- Script `backend/start.sh` carica automaticamente `.env`
- File `.env.example` incluso come template

## Come avviare

```bash
# Backend
cd backend
cp .env.example .env
# Modifica .env con la tua chiave Anthropic
./start.sh

# Frontend (altra finestra)
cd frontend
npm install
npm run dev
```
