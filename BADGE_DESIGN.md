# GURPS — Badge Design Reference

> Tutti gli elementi interattivi e di stato dell'app, con proposta di badge visuale.
> Formato: `[icona] Label` | colore suggerito | note d'uso

---

## 1. BADGE GIÀ IMPLEMENTATI (App.jsx)

### 1.1 Skill (SkillBadge)
Mostrati nelle opzioni turno, nel log combattimento, nella scheda personaggio.

| Skill interna     | Label GURPS          | Attributo | Colore |
|-------------------|----------------------|-----------|--------|
| combattere        | Rissa                | FO        | #ef4444 (rosso) |
| lottare           | Lottare              | FO        | #ef4444 |
| forzare           | Forzare              | FO        | #f97316 |
| proteggere        | Proteggere           | FO        | #f97316 |
| trasportare       | Trasportare          | FO        | #f97316 |
| intimidire        | Intimidire           | IN        | #f59e0b |
| sopravvivere      | Sopravvivenza        | IN        | #84cc16 |
| demolire          | Demolire             | IN        | #f97316 |
| resistere         | Resistenza           | SA        | #22d3ee |
| schivare          | Schivata             | DE        | #6366f1 |
| furtivita         | Furtività            | DE        | #8b5cf6 |
| acrobazia         | Acrobazia            | DE        | #a78bfa |
| rapidita          | Scattare             | DE        | #818cf8 |
| mira              | Armi a Gittata       | DE        | #f43f5e |
| guidare           | Pilotare             | DE        | #06b6d4 |
| manualita         | Manualità            | DE        | #0ea5e9 |
| infiltrarsi       | Infiltrarsi          | DE        | #8b5cf6 |
| scassinare        | Scassinare           | IN        | #a855f7 |
| pedinare          | Pedinare             | IN        | #a78bfa |
| investigare       | Investigare          | IN        | #3b82f6 |
| analizzare        | Analisi              | IN        | #60a5fa |
| tecnologia        | Tecnologia           | IN        | #22d3ee |
| medicina          | Medicina             | IN        | #34d399 |
| cultura           | Cultura              | IN        | #a3e635 |
| strategia         | Tattica              | IN        | #fb923c |
| decifrare         | Decifrare            | IN        | #c084fc |
| osservare         | Osservare            | IN        | #38bdf8 |
| ingegneria        | Ingegneria           | IN        | #fb923c |
| scienze           | Scienze              | IN        | #4ade80 |
| persuadere        | Diplomazia           | SA        | #f472b6 |
| ingannare         | Raggiro              | SA        | #fb7185 |
| intuire           | Psicologia           | SA        | #e879f9 |
| calmare           | Calmare              | SA        | #a78bfa |
| ispirare          | Leadership           | SA        | #facc15 |
| curare            | Pronto Soccorso      | IN        | #34d399 |
| comandare         | Comandare            | SA        | #f59e0b |
| comunicare        | Comunicare           | SA        | #60a5fa |
| intrattenere      | Intrattenere         | SA        | #f472b6 |
| etichetta         | Galateo              | SA        | #c084fc |

### 1.2 Vantaggi e Svantaggi (AdvantagesBadges)
Mostrati nel log combattimento quando un vantaggio è attivo.

| Nome                        | Icona | Colore    | Tipo |
|-----------------------------|-------|-----------|------|
| Carisma                     | ✨    | #f472b6   | vantaggio |
| Riflessi da Combattimento   | ⚡    | #facc15   | vantaggio |
| Duro da Uccidere            | 🛡    | #4ade80   | vantaggio |
| Sensi Acuti                 | 👁    | #38bdf8   | vantaggio |
| Forza Aumentata             | 💪    | #f97316   | vantaggio |
| Alta Tecnologia             | 🔬    | #22d3ee   | vantaggio |
| Animo Sanguinario           | 🩸    | #ef4444   | svantaggio |
| Codardo                     | 🐔    | #facc15   | svantaggio |
| Sospettoso                  | 👀    | #a78bfa   | svantaggio |

### 1.3 Stato ferita (WoundBadge)
Mostrato nel log combattimento e sulla PlayerChip.

| Chiave               | Icona | Label        | Colore    |
|----------------------|-------|--------------|-----------|
| ferito               | 🩹    | Ferito       | #facc15 (giallo) |
| ferito_grave         | 🩸    | Ferito Grave | #f97316 (arancio) |
| fuori_combattimento  | 💀    | Abbattuto    | #ef4444 (rosso) |
| morto                | ☠     | Morto        | #7f1d1d (rosso scuro) |

### 1.4 Tipo danno (DamageTypeBadge)

| Tipo | Icona | Label        | Colore    |
|------|-------|--------------|-----------|
| cr   | 👊    | Contundente  | #94a3b8 (grigio) |
| cut  | 🗡    | Taglio       | #f87171 |
| imp  | 🏹    | Impalante    | #c084fc |
| burn | 🔥    | Fuoco        | #fb923c |

### 1.5 Difesa attiva (DefenseBadge)

| Tipo  | Icona | Label    | Colore  |
|-------|-------|----------|---------|
| dodge | 💨    | Schivata | #818cf8 |
| parry | ⚔     | Parata   | #60a5fa |
| block | 🛡    | Bloccata | #34d399 |

### 1.6 Stato NPC (NpcStatusBadge)

| Stato    | Icona | Label      | Colore    |
|----------|-------|------------|-----------|
| alive    | 🟢    | Vivo       | #4ade80   |
| dead     | 💀    | Morto      | #6b7280   |
| missing  | ❓    | Scomparso  | #f59e0b   |
| captured | ⛓     | Catturato  | #f97316   |

### 1.7 Atteggiamento NPC (NpcAttitudeBadge)

| Atteggiamento | Icona | Label       | Colore  |
|---------------|-------|-------------|---------|
| friendly      | 😊    | Amichevole  | #4ade80 |
| allied        | 🤝    | Alleato     | #60a5fa |
| neutral       | 😐    | Neutrale    | #9ca3af |
| suspicious    | 🤨    | Sospettoso  | #facc15 |
| hostile       | 😠    | Ostile      | #f87171 |

### 1.8 Esito narrativo combattimento (NarrativeHintBadge)

| Chiave                           | Icona | Label               | Colore  |
|----------------------------------|-------|---------------------|---------|
| colpo_mancato                    | 💨    | Mancato             | #6b7280 |
| critico_fallimentare_attaccante  | 💥    | Fallimento Critico  | #ef4444 |
| colpo_critico                    | ⚡    | Colpo Critico       | #facc15 |
| danno_assorbito                  | 🛡    | Danno Assorbito     | #4ade80 |
| difesa_riuscita                  | ✋    | Difesa Riuscita     | #60a5fa |
| bersaglio_abbattuto              | 💀    | Abbattuto           | #ef4444 |
| ferita_grave                     | 🩸    | Ferita Grave        | #f97316 |
| colpito                          | 🎯    | Colpito             | #f87171 |

### 1.9 Badge nodo mappa strategica (inline)

| Contenuto       | Icona | Label      | Colore  |
|-----------------|-------|------------|---------|
| contains_enemy  | ⚔     | Nemici     | #ef4444 |
| contains_loot   | 💰    | Tesoro     | #facc15 |
| contains_clue   | 🔍    | Indizio    | #60a5fa |
| special_event   | ⚡    | Evento     | #c084fc |
| is_objective    | ⭐    | Obiettivo  | #fb923c |
| is_final        | 🏁    | Finale     | #facc15 |
| blocked         | 🚫    | Bloccato   | #6b7280 |
| visited         | ✓     | Visitato   | #4ade80 |
| reachable       | →     | Raggiungi  | #22c55e |

---

## 2. BOTTONI ATTUALI (da convertire o già convertiti)

### 2.1 Header partita
| Bottone attuale        | Badge proposto                         | Stato |
|------------------------|----------------------------------------|-------|
| 🗺 Mappa               | Badge viola `🗺 Mappa Strategica`      | da fare |
| 📖 Bibbia              | Badge ambra `📖 Bibbia`               | da fare |
| 🔓 Segreti             | Badge ambra `🔓 Segreti [playtest]`   | da fare |
| ↩ Ricomincia           | Badge grigio `↩ Ricomincia`           | da fare |

### 2.2 Mappa tattica (hex grid)
| Bottone attuale              | Badge proposto                          | Stato |
|------------------------------|-----------------------------------------|-------|
| 👣 Muovi (N yd)              | Badge verde `👣 Muovi · N m`          | parziale |
| ⚔ Attacca                   | Badge rosso `⚔ Attacca`               | parziale |
| ↺ (ruota sinistra)          | Badge indaco `↺ Ruota`                | da fare |
| ↻ (ruota destra)            | Badge indaco `↻ Ruota`                | da fare |
| Schivata / Parata / Bloccata | → già DefenseBadge                     | ✅ fatto |

### 2.3 Pannello personaggio (setup / scheda)
| Bottone attuale              | Badge proposto                          | Stato |
|------------------------------|-----------------------------------------|-------|
| Aggiungi al gruppo           | Badge verde `+ Aggiungi`               | da fare |
| Rigenera                     | Badge grigio `↻ Rigenera`             | da fare |
| ← Cambia genere              | Badge grigio `← Genere`               | da fare |
| + Crea personaggio           | Badge viola `+ Crea`                   | da fare |
| Invia 🎲 (chat)             | Badge viola `Invia 🎲`                | da fare |
| ✕ (annulla opzione)         | Badge grigio `✕ Annulla`              | da fare |

### 2.4 Schermata fine storia
| Bottone attuale         | Badge proposto                          | Stato |
|-------------------------|-----------------------------------------|-------|
| 🔓 Rivela segreti       | Badge ambra `🔓 Segreti`              | da fare |
| ↩ Nuova partita         | Badge grigio `↩ Nuova partita`        | da fare |

### 2.5 Opzioni turno (OptionsBar)
| Elemento attuale          | Badge proposto                         | Stato |
|---------------------------|----------------------------------------|-------|
| [Nome · skill lvl N]      | → già SkillBadge                       | ✅ fatto |
| "Azione custom" label     | Badge grigio-viola `✏️ Azione libera` | da fare |

---

## 3. BADGE DA AGGIUNGERE (non ancora implementati)

### 3.1 Stat personaggio (StatBadge)
Attualmente mostrate come testo piano `FO:12 DE:11...`

| Stat | Icona | Label | Colore  |
|------|-------|-------|---------|
| FO   | 💪    | FO    | #f97316 |
| DE   | 🏃    | DE    | #818cf8 |
| IN   | 🧠    | IN    | #60a5fa |
| SA   | 💙    | SA    | #f472b6 |

> Formato proposto: `💪 FO 12` — pill compatta con numero incorporato

### 3.2 Derivate GURPS (DerivedStatBadge)
Mostrate nella scheda personaggio o al hover sul token.

| Derivata     | Icona | Label      | Colore  |
|--------------|-------|------------|---------|
| HP correnti  | ❤     | HP         | #f87171 |
| FP correnti  | ⚡    | FP         | #60a5fa |
| Schivata     | 💨    | Schivata   | #818cf8 |
| Movimento    | 👣    | Mov        | #4ade80 |
| Volontà      | 🧠    | Volontà    | #a78bfa |
| Percezione   | 👁    | Per        | #38bdf8 |
| Basic Speed  | ⚡    | Speed      | #facc15 |

### 3.3 Tipo nodo mappa (NodeKindBadge)
Per il tooltip hover della mappa strategica.

| Kind         | Icona | Label        | Colore  |
|--------------|-------|--------------|---------|
| entrance     | 🚪    | Ingresso     | #9ca3af |
| corridor     | 🔀    | Corridoio    | #6b7280 |
| room         | 🏠    | Stanza       | #60a5fa |
| outdoors     | 🌿    | Esterno      | #4ade80 |
| stronghold   | 🏰    | Fortezza     | #f97316 |
| objective    | ⭐    | Obiettivo    | #fb923c |
| extraction   | 🚁    | Estrazione   | #22c55e |
| trap         | ⚠     | Trappola     | #ef4444 |

### 3.4 Tipo minaccia missione (ThreatBadge)
Da mostrare nel pannello missione / SidePanel.

| Livello | Icona | Label    | Colore  |
|---------|-------|----------|---------|
| 0-2     | 🟢    | Basso    | #4ade80 |
| 3-5     | 🟡    | Medio    | #facc15 |
| 6-8     | 🟠    | Alto     | #f97316 |
| 9+      | 🔴    | Critico  | #ef4444 |

### 3.5 Outcome nodo (OutcomeBadge)
Da mostrare sui nodi visitati della mappa strategica.

| Outcome       | Icona | Label           | Colore  |
|---------------|-------|-----------------|---------|
| success_clean | ✅    | Risolto         | #4ade80 |
| success_dirty | ⚠     | Risolto a fatica| #facc15 |
| timeout       | ⏳    | Tempo scaduto   | #f97316 |
| crisis        | 💥    | Collassato      | #ef4444 |

### 3.6 Tiro reazione NPC (ReactionBadge)
Da mostrare dopo `POST /game/reaction`.

| Livello      | Icona | Label        | Colore  |
|--------------|-------|--------------|---------|
| ostile       | 😡    | Ostile       | #ef4444 |
| sfavorevole  | 😒    | Sfavorevole  | #f97316 |
| neutro       | 😐    | Neutro       | #9ca3af |
| favorevole   | 🙂    | Favorevole   | #60a5fa |
| amichevole   | 😊    | Amichevole   | #4ade80 |
| entusiasta   | 🤩    | Entusiasta   | #facc15 |

### 3.7 Fase missione (PhaseBadge)
Da mostrare nell'header durante la partita.

| Fase        | Icona | Label       | Colore  |
|-------------|-------|-------------|---------|
| Ingresso    | 🚪    | Fase 1      | #818cf8 |
| Sviluppo    | ⚔     | Fase 2      | #f97316 |
| Finale      | 🏁    | Fase 3      | #facc15 |

### 3.8 Genere narrativo (GenreBadge)
Da mostrare nell'header o nel SidePanel.

| Genere             | Icona | Label                | Colore  |
|--------------------|-------|----------------------|---------|
| sci_fi             | 🚀    | Fantascienza         | #60a5fa |
| fantasy            | 🗡    | Fantasy               | #a78bfa |
| mystery_horror     | 🔍    | Mistero / Horror     | #c084fc |
| ww2                | 🎖    | Seconda GM           | #84cc16 |
| romance            | 💕    | Romance              | #f472b6 |
| action             | 💥    | Azione               | #f97316 |
| detective_classico | 🕵    | Detective            | #facc15 |

---

## 4. PROVIDER AI (ProviderBadge)
Attualmente selettore a bottoni radio.

| Provider | Icona | Label   | Colore  |
|----------|-------|---------|---------|
| claude   | 🟣    | Claude  | #7c3aed |
| openai   | ⚫    | OpenAI  | #10b981 |
| gemini   | 🔵    | Gemini  | #3b82f6 |

---

## 5. PRIORITÀ IMPLEMENTAZIONE SUGGERITA

1. **StatBadge** — sostituisce il `StatBar` attuale, molto visibile nella scheda
2. **ReactionBadge** — dopo `POST /game/reaction`, mostrare il livello in chat
3. **OutcomeBadge** — sui nodi visitati nella mappa strategica
4. **ThreatBadge** — nel SidePanel missione (indicatore minaccia)
5. **PhaseBadge** — header partita accanto ai player chip
6. **Bottoni header** — 🗺/📖/🔓/↩ come badge-button invece di semplici pulsanti
7. **NodeKindBadge** — tooltip mappa strategica

---

## 6. COMPONENTE BASE (riferimento)

```jsx
function Badge({ icon, label, color, bg, size = "sm", title }) {
  const pad = size === "lg" ? "4px 12px" : size === "md" ? "3px 9px" : "2px 7px";
  const fs  = size === "lg" ? 13 : size === "md" ? 12 : 11;
  return (
    <span title={title} style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      padding: pad, borderRadius: 6, fontSize: fs, fontWeight: 700,
      background: bg || `${color}18`,
      border: `1px solid ${color}44`,
      color, whiteSpace: "nowrap", lineHeight: 1.3,
    }}>
      {icon && <span style={{ fontSize: fs + 1 }}>{icon}</span>}
      {label}
    </span>
  );
}
```

> Per i bottoni-badge (cliccabili) usare `<button>` con lo stesso stile + `cursor: pointer`
> e `onClick` handler. Aggiungere `onMouseEnter/Leave` per highlight border opacity.
