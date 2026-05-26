# JSON Doctor

CLI tool per auditare e arricchire i file JSON delle avventure GURPS.

## Installazione

```bash
# Dal root del progetto GURPS:
pip install anthropic   # solo per il comando enrich
```

Variabile d'ambiente richiesta per `enrich`:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## Comandi

Tutti i comandi si eseguono dal root del progetto GURPS:

```bash
python3 -m tools.json_doctor <comando> [opzioni]
```

### `validate` — Controlla la validità JSON e lo schema

```bash
python3 -m tools.json_doctor validate
python3 -m tools.json_doctor validate data/compiled_adventures/ai_porto_fantasma.json
```

Verifica che ogni file sia JSON valido e contenga i campi obbligatori (id, title, genre, actors, locations, clues, event_clocks).

---

### `audit` — Analizza la qualità delle avventure

```bash
python3 -m tools.json_doctor audit
python3 -m tools.json_doctor audit --brief
python3 -m tools.json_doctor audit data/compiled_adventures/pdf_gotham39.json
```

Produce un report con score 0-10 e findings categorizzati in:
- **critical** — campi mancanti che rendono l'avventura incompleta
- **warning** — NPC senza pressure_response/reaction_table, clock piatti, antagonisti senza pressione
- **info** — campi migliorabili (payoff, hidden_implication, wrong_interpretations)

---

### `report` — Genera un report markdown

```bash
python3 -m tools.json_doctor report
python3 -m tools.json_doctor report -o mio_report.md
```

Produce un file `.md` con tabella riassuntiva e dettaglio per ogni avventura.

---

### `enrich` — Arricchisce con Claude AI

```bash
# File singolo
python3 -m tools.json_doctor enrich data/compiled_adventures/pdf_gotham39.json

# Tutte le avventure con score < 9
python3 -m tools.json_doctor enrich --all

# Anteprima senza modificare i file
python3 -m tools.json_doctor enrich --all --dry-run

# Forza enrichment anche con score alto
python3 -m tools.json_doctor enrich --all --force
```

Per ogni avventura che ne ha bisogno, chiama Claude per:
- Completare `pressure_response` e `reaction_table` degli NPC
- Aggiungere `steps` narrativi ai clock e `resolution_condition`
- Generare `resources` appropriate al genere
- Completare `payoff`, `hidden_implication`, `wrong_interpretations` degli indizi

Crea automaticamente backup `.json.bak` prima di modificare i file.

---

## Struttura

```
tools/json_doctor/
  cli.py         # Entry point, comandi argparse
  rules.py       # Regole di audit (Finding, audit(), score())
  enricher.py    # Enrichment AI con Claude
  validator.py   # Validazione schema JSON
  README.md
  report.md      # Report generato (non versionare)
```

## Regole di audit

### NPC
- `pressure_response` deve avere ≥ 2 livelli (low/medium/high/extreme)
- `reaction_table` deve avere ≥ 2 situazioni
- Antagonisti: `agenda_pressure` ≥ 5
- `goal`, `current_plan`, `fallback_plan` non devono essere vuoti

### Clock
- `steps` deve avere ≥ 3 elementi
- `ticks_per_failure` ≥ 2 per tensione realistica
- `resolution_condition` e `discovery_hint` richiesti

### Risorse
- Avventure horror/thriller senza `resources` ricevono warning

### Indizi
- `payoff`, `hidden_implication`, `wrong_interpretations` non devono essere vuoti

### Struttura
- `premise`, `initial_hook`, `actors`, `locations`, `event_clocks` richiesti
