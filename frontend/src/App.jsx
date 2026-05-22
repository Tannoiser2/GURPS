
import React, { useEffect, useMemo, useRef, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8002";

const STAT_ICON = { forza: "💪", agilita: "🏃", intelligenza: "🧠", empatia: "💙" };
const STAT_LABEL = { forza: "FO", agilita: "DE", intelligenza: "IN", empatia: "SA" };

const GENRE_LABELS = {
  sci_fi: "Fantascienza",
  fantasy: "Fantasy",
  mystery_horror: "Mistero / Horror",
  ww2: "Seconda Guerra Mondiale",
  romance: "Romance",
  action: "Azione",
  detective_classico: "Detective Classico",
};

// ─── Helpers ───────────────────────────────────────────────────────────────

function StatBar({ stats }) {
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      {Object.entries(stats).map(([k, v]) => (
        <span key={k} style={{ fontSize: 13, background: "var(--code-bg)", padding: "2px 7px", borderRadius: 6 }}>
          {STAT_ICON[k] || ""} <b>{STAT_LABEL[k] || k}</b>:{v}
        </span>
      ))}
    </div>
  );
}

function DiceFormulaRow({ r }) {
  // Costruisce la formula leggibile da un entry di roll_details
  const parts = [];
  parts.push({ label: r.skill_known ? `${r.skill} (conosciuta)` : `${r.skill} (default)`, val: r.base_skill, color: "var(--text-h)", kind: "skill" });
  if (r.item_bonus)   parts.push({ label: "oggetto",    val: `+${r.item_bonus}`,   color: "#60a5fa", kind: "bonus" });
  // vantaggi/svantaggi espansi per nome se disponibili, altrimenti aggregati
  if (r.adv_bonus && r.adv_breakdown?.length > 0) {
    for (const t of r.adv_breakdown) {
      const positive = t.delta > 0;
      parts.push({ label: t.name, val: t.delta > 0 ? `+${t.delta}` : `${t.delta}`, color: positive ? "#4ade80" : "#f87171", kind: "trait" });
    }
  } else if (r.adv_bonus) {
    parts.push({ label: "tratti", val: r.adv_bonus > 0 ? `+${r.adv_bonus}` : `${r.adv_bonus}`, color: "#4ade80", kind: "bonus" });
  }
  if (r.coord_bonus)  parts.push({ label: "coord.",     val: `+${r.coord_bonus}`,  color: "#a78bfa", kind: "bonus" });
  if (r.difficulty)   parts.push({ label: "difficoltà", val: `−${r.difficulty}`,   color: "#f87171", kind: "malus" });
  if (r.status_malus) parts.push({ label: "ferite",     val: `−${r.status_malus}`, color: "#f87171", kind: "malus" });
  if (r.threat_malus) parts.push({ label: "minaccia",   val: `−${r.threat_malus}`, color: "#f87171", kind: "malus" });

  const outcomeColor = r.outcome?.includes("CRITICO") && r.success ? "#22c55e"
    : r.outcome?.includes("CRITICO") ? "#ef4444"
    : r.success ? "#4ade80" : "#f87171";

  return (
    <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: 6, marginTop: 4 }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 6, flexWrap: "wrap", fontSize: 12 }}>
        <span style={{ fontWeight: 700, color: "var(--text-h)", minWidth: 60 }}>{r.name}</span>
        <span style={{ color: "var(--text)", opacity: 0.7, fontSize: 11, flex: "0 0 auto" }}>{r.action?.slice(0, 30)}</span>
        <span style={{ marginLeft: "auto", fontWeight: 800, color: outcomeColor, fontSize: 11 }}>{r.outcome}</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 4, flexWrap: "wrap", marginTop: 3, fontSize: 11 }}>
        <span style={{ color: "#94a3b8" }}>3d6 =</span>
        <span style={{ fontWeight: 900, color: outcomeColor, fontSize: 14, textShadow: `0 0 7px ${outcomeColor}88` }}>{r.rolled}</span>
        <span style={{ color: "#94a3b8" }}>vs</span>
        {parts.map((p, i) => (
          <React.Fragment key={i}>
            {i > 0 && <span style={{ color: "#475569", fontSize: 10 }}>+</span>}
            <span style={{
              padding: "1px 6px", borderRadius: 4, fontWeight: 700, fontSize: 10,
              background: `${p.color}18`, border: `1px solid ${p.color}44`, color: p.color,
              display: "inline-flex", alignItems: "center", gap: 3,
            }}>
              {p.kind === "skill" ? (
                <><span style={{ opacity: 0.75 }}>{p.label}</span> <b>{p.val}</b></>
              ) : (
                <><span style={{ opacity: 0.75 }}>{p.label}</span> <b>{p.val}</b></>
              )}
            </span>
          </React.Fragment>
        ))}
        <span style={{ color: "#94a3b8", fontWeight: 700 }}> = {r.effective_skill}</span>
        <span style={{ color: "#94a3b8" }}>→ margine</span>
        <span style={{ fontWeight: 700, color: r.margin >= 0 ? "#4ade80" : "#f87171" }}>{r.margin >= 0 ? "+" : ""}{r.margin}</span>
      </div>
    </div>
  );
}

function DiceResult({ roll, rollDetails }) {
  const [open, setOpen] = React.useState(false);

  // Flusso engine (bibbia): usa rollDetails; flusso narrativo: usa roll
  if (rollDetails?.length > 0) {
    const first = rollDetails[0];
    const allOk = rollDetails.every(r => r.success);
    const anyFail = rollDetails.some(r => !r.success);
    const anyCrit = rollDetails.some(r => r.critical);
    const summaryColor = anyCrit && allOk ? "#22c55e" : anyFail ? "#f87171" : "#4ade80";
    const firstOutcomeLabel = anyCrit && allOk ? "CRITICO!" : anyCrit && anyFail ? "FALLIMENTO CRITICO!" : allOk ? "Successo" : "Fallimento";
    return (
      <div style={{ background: "rgba(0,0,0,0.18)", border: `1px solid ${summaryColor}33`, borderLeft: `3px solid ${summaryColor}`, borderRadius: 8, overflow: "hidden", fontSize: 12 }}>
        <div onClick={() => setOpen(v => !v)} style={{ display: "flex", alignItems: "center", gap: 8, padding: "7px 12px", cursor: "pointer", userSelect: "none" }}>
          <span style={{ fontSize: 15 }}>🎲</span>
          {/* skill badge */}
          <span style={{
            padding: "2px 8px", borderRadius: 5, fontWeight: 700, fontSize: 11,
            background: `${summaryColor}22`, color: summaryColor, border: `1px solid ${summaryColor}55`,
          }}>{first.skill}</span>
          {/* dado colorato */}
          <span style={{ color: "#94a3b8", fontSize: 11 }}>3d6 =</span>
          <span style={{
            fontWeight: 900, fontSize: 15,
            color: summaryColor,
            textShadow: `0 0 8px ${summaryColor}88`,
          }}>{first.rolled}</span>
          <span style={{ color: "#94a3b8", fontSize: 11 }}>vs {first.effective_skill}</span>
          <span style={{ fontWeight: 800, color: summaryColor, fontSize: 11 }}>{firstOutcomeLabel}</span>
          <span style={{ marginLeft: "auto", fontSize: 10, color: "#94a3b8", opacity: 0.7 }}>{open ? "▲ chiudi" : "▼ formula"}</span>
        </div>
        {open && (
          <div style={{ padding: "0 12px 10px" }}>
            {rollDetails.map((r, i) => <DiceFormulaRow key={i} r={r} />)}
          </div>
        )}
      </div>
    );
  }

  if (!roll) return null;
  const ok = roll.success;
  const crit = roll.critical;
  const color = crit && ok ? "#22c55e" : crit && !ok ? "#ef4444" : ok ? "#4ade80" : "#f87171";
  const label = crit && ok ? "CRITICO!" : crit && !ok ? "FALLIMENTO CRITICO!" : ok ? "Successo" : "Fallimento";
  const skillLabel = roll.skill_name || roll.skill || "";
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap",
      background: "rgba(0,0,0,0.15)", border: `1px solid ${color}40`,
      borderLeft: `3px solid ${color}`,
      borderRadius: 8, padding: "7px 12px", fontSize: 13,
    }}>
      <span style={{ fontSize: 16 }}>🎲</span>
      {skillLabel && (
        <span style={{
          padding: "2px 9px", borderRadius: 5, fontWeight: 700, fontSize: 12,
          background: `${color}22`, color, border: `1px solid ${color}55`,
        }}>{skillLabel}</span>
      )}
      <span style={{ color: "var(--text)", fontSize: 12 }}>
        3d6 = <b style={{
          color,
          fontWeight: 900, fontSize: 16,
          textShadow: `0 0 8px ${color}88`,
        }}>{roll.rolled}</b>
        <span style={{ color: "#94a3b8" }}> ≤ </span>
        <b style={{ color: "var(--text-h)" }}>{roll.target}</b>
      </span>
      <span style={{ fontWeight: 800, color }}>{label}</span>
      {roll.margin !== undefined && (
        <span style={{ color: "var(--text)", fontSize: 12, marginLeft: "auto" }}>margine {roll.margin >= 0 ? "+" : ""}{roll.margin}</span>
      )}
    </div>
  );
}

// ─── Badge System ──────────────────────────────────────────────────────────

const SKILL_META = {
  // ── FO (Forza) ──────────────────────────────────────────────────────────
  combattere:          { label: "Rissa",             attr: "FO", color: "#ef4444" },
  lottare:             { label: "Lottare",            attr: "FO", color: "#ef4444" },
  forzare:             { label: "Forzare",            attr: "FO", color: "#f97316" },
  proteggere:          { label: "Scudo",              attr: "FO", color: "#f97316" },
  trasportare:         { label: "Trasportare",        attr: "FO", color: "#f97316" },
  intimidire:          { label: "Intimidire",         attr: "IN", color: "#f59e0b" },
  sopravvivere:        { label: "Sopravvivenza",      attr: "IN", color: "#84cc16" },
  demolire:            { label: "Esplosivi",          attr: "IN", color: "#f97316" },
  resistere:           { label: "Resistenza",         attr: "SA", color: "#22d3ee" },
  nuotare:             { label: "Nuotare",            attr: "SA", color: "#22d3ee" },
  arrampicarsi:        { label: "Arrampicarsi",       attr: "DE", color: "#fb923c" },
  lanciare:            { label: "Lanciare",           attr: "DE", color: "#ef4444" },
  sollevare:           { label: "Sollevare",          attr: "FO", color: "#f97316" },
  saltare:             { label: "Saltare",            attr: "DE", color: "#818cf8" },
  // ── DE (Destrezza) ──────────────────────────────────────────────────────
  schivare:            { label: "Schivata",           attr: "DE", color: "#6366f1" },
  furtivita:           { label: "Furtività",          attr: "DE", color: "#8b5cf6" },
  acrobazia:           { label: "Acrobazia",          attr: "DE", color: "#a78bfa" },
  rapidita:            { label: "Scattare",           attr: "DE", color: "#818cf8" },
  mira:                { label: "Armi a Gittata",     attr: "DE", color: "#f43f5e" },
  guidare:             { label: "Pilotare",           attr: "DE", color: "#06b6d4" },
  manualita:           { label: "Manualità",          attr: "DE", color: "#0ea5e9" },
  infiltrarsi:         { label: "Infiltrarsi",        attr: "DE", color: "#8b5cf6" },
  scassinare:          { label: "Scassinare",         attr: "IN", color: "#a855f7" },
  pedinare:            { label: "Sorvegliare",        attr: "IN", color: "#a78bfa" },
  cavalcare:           { label: "Cavalcare",          attr: "DE", color: "#fb923c" },
  mimetizzare:         { label: "Mimetizzarsi",       attr: "IN", color: "#6b7280" },
  equilibrio:          { label: "Equilibrio",         attr: "DE", color: "#818cf8" },
  borseggiare:         { label: "Borseggio",          attr: "DE", color: "#a855f7" },
  // ── IN (Intelligenza) ───────────────────────────────────────────────────
  investigare:         { label: "Investigare",        attr: "IN", color: "#3b82f6" },
  analizzare:          { label: "Analisi",            attr: "IN", color: "#60a5fa" },
  tecnologia:          { label: "Tecnologia",         attr: "IN", color: "#22d3ee" },
  medicina:            { label: "Medicina",           attr: "IN", color: "#34d399" },
  cultura:             { label: "Cultura",            attr: "IN", color: "#a3e635" },
  strategia:           { label: "Tattica",            attr: "IN", color: "#fb923c" },
  decifrare:           { label: "Decifrare",          attr: "IN", color: "#c084fc" },
  osservare:           { label: "Osservare",          attr: "IN", color: "#38bdf8" },
  ingegneria:          { label: "Ingegneria",         attr: "IN", color: "#fb923c" },
  scienze:             { label: "Scienze",            attr: "IN", color: "#4ade80" },
  legge:               { label: "Legge",              attr: "IN", color: "#60a5fa" },
  occultismo:          { label: "Occultismo",         attr: "IN", color: "#c084fc" },
  seguire_tracce:      { label: "Seguire Tracce",     attr: "IN", color: "#84cc16" },
  navigare:            { label: "Navigazione",        attr: "IN", color: "#38bdf8" },
  sopravvivenza_urbana:{ label: "Soprav. Urbana",     attr: "IN", color: "#84cc16" },
  storia:              { label: "Storia",             attr: "IN", color: "#a3e635" },
  economia:            { label: "Economia",           attr: "IN", color: "#facc15" },
  meccanica:           { label: "Meccanica",          attr: "IN", color: "#fb923c" },
  elettronica:         { label: "Elettronica",        attr: "IN", color: "#22d3ee" },
  informatica:         { label: "Informatica",        attr: "IN", color: "#06b6d4" },
  astronomia:          { label: "Astronomia",         attr: "IN", color: "#818cf8" },
  biologia:            { label: "Biologia",           attr: "IN", color: "#4ade80" },
  chimica:             { label: "Chimica",            attr: "IN", color: "#fb923c" },
  fisica:              { label: "Fisica",             attr: "IN", color: "#60a5fa" },
  linguistica:         { label: "Linguistica",        attr: "IN", color: "#a3e635" },
  filosofia:           { label: "Filosofia",          attr: "IN", color: "#c084fc" },
  teologia:            { label: "Teologia",           attr: "IN", color: "#f59e0b" },
  politica:            { label: "Politica",           attr: "IN", color: "#f472b6" },
  // ── SA (Salute/Empatia) ─────────────────────────────────────────────────
  persuadere:          { label: "Diplomazia",         attr: "SA", color: "#f472b6" },
  ingannare:           { label: "Raggiro",            attr: "IN", color: "#fb7185" },
  intuire:             { label: "Psicologia",         attr: "IN", color: "#e879f9" },
  calmare:             { label: "Calmare",            attr: "SA", color: "#a78bfa" },
  ispirare:            { label: "Leadership",         attr: "SA", color: "#facc15" },
  curare:              { label: "Pronto Soccorso",    attr: "IN", color: "#34d399" },
  comandare:           { label: "Comandare",          attr: "SA", color: "#f59e0b" },
  comunicare:          { label: "Comunicare",         attr: "SA", color: "#60a5fa" },
  intrattenere:        { label: "Intrattenere",       attr: "SA", color: "#f472b6" },
  etichetta:           { label: "Galateo",            attr: "IN", color: "#c084fc" },
  recitazione:         { label: "Recitazione",        attr: "SA", color: "#f472b6" },
  parlare_in_pubblico: { label: "Parlare in Pubblico",attr: "SA", color: "#facc15" },
  interrogare:         { label: "Interrogatorio",     attr: "IN", color: "#f59e0b" },
  seduzione:           { label: "Seduzione",          attr: "SA", color: "#f472b6" },
};

const ADVANTAGE_META = {
  // ── Vantaggi ────────────────────────────────────────────────────────────
  "Carisma":                   { icon: "✨", color: "#f472b6", type: "adv" },
  "Riflessi da Combattimento": { icon: "⚡", color: "#facc15", type: "adv" },
  "Duro da Uccidere":          { icon: "🛡", color: "#4ade80", type: "adv" },
  "Sensi Acuti":               { icon: "👁", color: "#38bdf8", type: "adv" },
  "Forza Aumentata":           { icon: "💪", color: "#f97316", type: "adv" },
  "Alta Tecnologia":           { icon: "🔬", color: "#22d3ee", type: "adv" },
  "Ambidestrezza":             { icon: "🤲", color: "#a78bfa", type: "adv" },
  "Bellezza":                  { icon: "💎", color: "#f472b6", type: "adv" },
  "Empatia":                   { icon: "💜", color: "#e879f9", type: "adv" },
  "Memoria Fotografica":       { icon: "🧠", color: "#60a5fa", type: "adv" },
  "Coraggio":                  { icon: "🦁", color: "#f59e0b", type: "adv" },
  "Sangue Freddo":             { icon: "🧊", color: "#38bdf8", type: "adv" },
  "Istinto di Sopravvivenza":  { icon: "🌿", color: "#84cc16", type: "adv" },
  "Fortuna":                   { icon: "🍀", color: "#4ade80", type: "adv" },
  "Contatti":                  { icon: "🔗", color: "#60a5fa", type: "adv" },
  "Status Sociale":            { icon: "👑", color: "#facc15", type: "adv" },
  "Ricchezza":                 { icon: "💰", color: "#facc15", type: "adv" },
  "Talento":                   { icon: "⭐", color: "#f59e0b", type: "adv" },
  "Voce Bella":                { icon: "🎙", color: "#f472b6", type: "adv" },
  "Autorità":                  { icon: "⚖",  color: "#fb923c", type: "adv" },
  "Linguaggio Nativo Extra":   { icon: "🗣",  color: "#a3e635", type: "adv" },
  // ── Svantaggi ───────────────────────────────────────────────────────────
  "Animo Sanguinario":         { icon: "🩸", color: "#ef4444", type: "dis" },
  "Codardo":                   { icon: "🐔", color: "#facc15", type: "dis" },
  "Sospettoso":                { icon: "👀", color: "#a78bfa", type: "dis" },
  "Avidità":                   { icon: "🪙", color: "#f59e0b", type: "dis" },
  "Senso del Dovere":          { icon: "⚓", color: "#60a5fa", type: "dis" },
  "Nemico":                    { icon: "⚔",  color: "#ef4444", type: "dis" },
  "Segreto":                   { icon: "🔒", color: "#6b7280", type: "dis" },
  "Dipendenza":                { icon: "💊", color: "#f97316", type: "dis" },
  "Fobia":                     { icon: "😱", color: "#f43f5e", type: "dis" },
  "Impulsività":               { icon: "💢", color: "#ef4444", type: "dis" },
  "Arroganza":                 { icon: "🦚", color: "#a78bfa", type: "dis" },
  "Lealtà":                    { icon: "🤝", color: "#60a5fa", type: "dis" },
  "Poca Autostima":            { icon: "😔", color: "#6b7280", type: "dis" },
  "Amnesia":                   { icon: "🌫",  color: "#9ca3af", type: "dis" },
  "Mancanza di Empatia":       { icon: "🧱", color: "#6b7280", type: "dis" },
  "Curiosità Morbosa":         { icon: "🔍", color: "#c084fc", type: "dis" },
  "Smemoratezza":              { icon: "📭", color: "#9ca3af", type: "dis" },
  "Pessimismo":                { icon: "🌧",  color: "#6b7280", type: "dis" },
};

const WOUND_META = {
  ferito:               { icon: "🩹", label: "Ferito",       color: "#facc15", bg: "rgba(250,204,21,0.12)" },
  ferito_grave:         { icon: "🩸", label: "Ferito Grave", color: "#f97316", bg: "rgba(249,115,22,0.12)" },
  fuori_combattimento:  { icon: "💀", label: "Abbattuto",    color: "#ef4444", bg: "rgba(239,68,68,0.12)" },
  morto:                { icon: "☠",  label: "Morto",        color: "#7f1d1d", bg: "rgba(127,29,29,0.2)"  },
};

const DAMAGE_TYPE_META = {
  cr:   { icon: "👊", label: "Contundente", color: "#94a3b8" },
  cut:  { icon: "🗡",  label: "Taglio",      color: "#f87171" },
  imp:  { icon: "🏹", label: "Impalante",   color: "#c084fc" },
  burn: { icon: "🔥", label: "Fuoco",       color: "#fb923c" },
};

const DEFENSE_META = {
  dodge: { icon: "💨", label: "Schivata", color: "#818cf8" },
  parry: { icon: "⚔",  label: "Parata",   color: "#60a5fa" },
  block: { icon: "🛡", label: "Bloccata", color: "#34d399" },
};

const NPC_STATUS_META = {
  alive:    { icon: "🟢", label: "Vivo",     color: "#4ade80" },
  dead:     { icon: "💀", label: "Morto",    color: "#6b7280" },
  missing:  { icon: "❓", label: "Scomparso",color: "#f59e0b" },
  captured: { icon: "⛓",  label: "Catturato",color: "#f97316" },
};

const NPC_ATTITUDE_META = {
  friendly:   { icon: "😊", label: "Amichevole",  color: "#4ade80" },
  allied:     { icon: "🤝", label: "Alleato",      color: "#60a5fa" },
  neutral:    { icon: "😐", label: "Neutrale",     color: "#9ca3af" },
  suspicious: { icon: "🤨", label: "Sospettoso",   color: "#facc15" },
  hostile:    { icon: "😠", label: "Ostile",        color: "#f87171" },
};

const NARRATIVE_HINT_META = {
  colpo_mancato:                    { icon: "💨", label: "Mancato",          color: "#6b7280" },
  critico_fallimentare_attaccante:  { icon: "💥", label: "Fallimento Critico",color: "#ef4444" },
  colpo_critico:                    { icon: "⚡", label: "Colpo Critico",     color: "#facc15" },
  danno_assorbito:                  { icon: "🛡", label: "Danno Assorbito",   color: "#4ade80" },
  difesa_riuscita:                  { icon: "✋", label: "Difesa Riuscita",   color: "#60a5fa" },
  bersaglio_abbattuto:              { icon: "💀", label: "Abbattuto",         color: "#ef4444" },
  ferita_grave:                     { icon: "🩸", label: "Ferita Grave",      color: "#f97316" },
  colpito:                          { icon: "🎯", label: "Colpito",           color: "#f87171" },
  npc_si_avvicina:                  { icon: "👣", label: "Si avvicina",      color: "#f59e0b" },
};

// ─── GURPS tooltip rules ─────────────────────────────────────────────────────
const SKILL_TOOLTIP = {
  combattere:    "FO/M · Attacca in mischia (spada, ascia, rissa). Default FO−5.",
  lottare:       "FO/M · Corpo a corpo senza armi. Default FO−5.",
  forzare:       "FO/E · Sfondare porte, sollevare ostacoli. Default FO−4.",
  proteggere:    "FO/M · Usare uno scudo attivamente. Default FO−5.",
  intimidire:    "IN/M · Spaventare con minacce. Default IN−5.",
  sopravvivere:  "IN/M · Trovare cibo, rifugio, orientarsi. Default IN−5.",
  demolire:      "IN/M · Usare esplosivi. Default IN−5.",
  resistere:     "SA/E · Tiro di Salute per resistere a condizioni fisiche.",
  nuotare:       "SA/E · Nuotare senza annegare. Default SA−4.",
  arrampicarsi:  "DE/M · Scalare pareti e ostacoli. Default DE−5.",
  lanciare:      "DE/E · Lanciare oggetti con precisione. Default DE−4.",
  schivare:      "DE/E · Schivata attiva = DE/2+3. Sempre disponibile.",
  furtivita:     "DE/M · Muoversi senza farsi sentire. Default DE−5.",
  acrobazia:     "DE/D · Capriole, equilibrio estremo. Default DE−6.",
  rapidita:      "DE/E · Scattare, correre veloce. Default DE−4.",
  mira:          "DE/E · Sparare con armi a distanza. Default DE−4.",
  guidare:       "DE/M · Pilotare veicoli. Default DE−5.",
  manualita:     "DE/M · Lavori manuali fini. Default DE−5.",
  infiltrarsi:   "DE/M · Muoversi non visti. Default DE−5.",
  scassinare:    "IN/M · Aprire serrature senza chiave. Default IN−5.",
  pedinare:      "IN/M · Seguire qualcuno senza essere scoperti. Default IN−5.",
  cavalcare:     "DE/M · Cavalcare animali. Default DE−5.",
  mimetizzare:   "IN/M · Nascondersi nell'ambiente. Default IN−5.",
  borseggiare:   "DE/M · Rubare oggetti inosservati. Default DE−5.",
  investigare:   "IN/M · Raccogliere prove e indizi. Default IN−5.",
  analizzare:    "IN/D · Analisi tecnica approfondita. Default IN−6.",
  tecnologia:    "IN/M · Usare apparecchiature tecnologiche. Default IN−5.",
  medicina:      "IN/D · Curare ferite gravi, diagnosi. Default IN−6.",
  cultura:       "IN/M · Conoscere usi e costumi. Default IN−5.",
  strategia:     "IN/D · Pianificare tattiche militari. Default IN−6.",
  decifrare:     "IN/D · Crittografia, codici segreti. Default IN−6.",
  osservare:     "IN/E · Notare dettagli. Default IN−4.",
  ingegneria:    "IN/D · Progettare e costruire strutture. Default IN−6.",
  scienze:       "IN/D · Conoscenze scientifiche. Default IN−6.",
  legge:         "IN/M · Conoscere e applicare la legge. Default IN−5.",
  occultismo:    "IN/M · Conoscere miti e rituali. Default IN−5.",
  seguire_tracce:"IN/M · Seguire tracce e impronte. Default IN−5.",
  navigare:      "IN/M · Orientarsi via mare o aria. Default IN−5.",
  storia:        "IN/M · Conoscenza storica. Default IN−5.",
  economia:      "IN/M · Commercio e finanza. Default IN−5.",
  meccanica:     "IN/M · Riparare e costruire meccanismi. Default IN−5.",
  elettronica:   "IN/M · Elettronica e circuiti. Default IN−5.",
  informatica:   "IN/M · Computer e software. Default IN−5.",
  politica:      "IN/M · Manovre politiche e diplomatiche. Default IN−5.",
  persuadere:    "SA/M · Convincere con argomenti razionali. Default SA−5.",
  ingannare:     "IN/M · Mentire, bluffare. Default IN−5.",
  intuire:       "IN/M · Leggere le intenzioni altrui. Default IN−5.",
  calmare:       "SA/M · Tranquillizzare persone agitate. Default SA−5.",
  ispirare:      "SA/M · Motivare e guidare un gruppo. Default SA−5.",
  curare:        "IN/M · Pronto soccorso base (1d6 PF). Default IN−5.",
  comandare:     "SA/M · Dare ordini efficaci in combattimento. Default SA−5.",
  comunicare:    "SA/E · Trasmettere informazioni chiaramente. Default SA−4.",
  intrattenere:  "SA/M · Recitare, suonare, ballare. Default SA−5.",
  etichetta:     "IN/E · Galateo e protocollo sociale. Default IN−4.",
  recitazione:   "SA/M · Fingere identità o emozioni. Default SA−5.",
  parlare_in_pubblico: "SA/M · Discorsi persuasivi di gruppo. Default SA−5.",
  interrogare:   "IN/M · Estrarre informazioni da un interrogato. Default IN−5.",
  seduzione:     "SA/M · Sedurre romanticamente. Default SA−5.",
};

const ADVANTAGE_TOOLTIP = {
  "Carisma":                   "+2 ai tiri di reazione NPC, +2 alle skill sociali. 5pt/livello.",
  "Riflessi da Combattimento": "+1 schivata/parata/blocco, +2 iniziativa, mai sorpreso. 15pt.",
  "Duro da Uccidere":          "Soglia morte raddoppiata: muore solo sotto −2×PF. 2pt/livello.",
  "Sensi Acuti":               "+2 Percezione e osservare. 2pt/livello.",
  "Forza Aumentata":           "+1 FO effettiva, +1 danni mischia. 10pt.",
  "Alta Tecnologia":           "+2 tecnologia e ingegneria con strumenti avanzati. 5pt.",
  "Ambidestrezza":             "Nessuna penalità per la mano non dominante. 5pt.",
  "Bellezza":                  "+1 tiri di reazione, bonus skill di seduzione. 4pt.",
  "Empatia":                   "+3 Psicologia, percepisce bugie. 15pt.",
  "Memoria Fotografica":       "Ricorda tutto ciò che ha visto. +2 skill di conoscenza. 10pt.",
  "Coraggio":                  "+2 Volontà contro paura e stress. 10pt.",
  "Sangue Freddo":             "Nessuna penalità shock su tiri mira. 5pt.",
  "Fortuna":                   "Una volta per sessione ritira un tiro e prende il migliore. 15pt.",
  "Contatti":                  "Rete di informatori. +1 reazione nel gruppo. 3pt.",
  "Status Sociale":            "+1 reazione in contesti sociali. 5pt/livello.",
  "Ricchezza":                 "Risorse finanziarie significative; sblocca opzioni costose. 10pt.",
  "Talento":                   "+1 a un gruppo tematico di skill per livello. 5-10pt/livello.",
  "Voce Bella":                "+2 intrattenere e parlare in pubblico, +1 reazione. 10pt.",
  "Autorità":                  "Potere legale/militare; NPC di rango inferiore obbediscono. 5pt.",
  "Linguaggio Nativo Extra":   "Parla fluentemente un'altra lingua come madrelingua. 3pt.",
  "Animo Sanguinario":         "Morale check per ritirarsi. −10pt.",
  "Codardo":                   "−2 a tutti i tiri in pericolo fisico diretto. −5pt.",
  "Sospettoso":                "−2 skill sociali, +1 a intuire. −5pt.",
  "Avidità":                   "Volontà−3 per resistere all'avidità. −15pt.",
  "Senso del Dovere":          "Non abbandona mai i compagni. −5pt.",
  "Nemico":                    "Un nemico attivo interferisce regolarmente. −5 a −30pt.",
  "Segreto":                   "Se scoperto, conseguenze gravi. +1 ingannare. −10pt.",
  "Dipendenza":                "−1 a tutti i tiri in astinenza. −5pt.",
  "Fobia":                     "Volontà−4 quando esposto alla fobia specifica. −10pt.",
  "Impulsività":               "Volontà−2 per resistere all'impulso immediato. −10pt.",
  "Arroganza":                 "−1 reazione con sconosciuti; sfida il comando altrui. −5pt.",
  "Lealtà":                    "Non può agire contro i propri alleati. −5pt.",
  "Poca Autostima":            "−2 skill di leadership, −1 Volontà nei momenti critici. −10pt.",
  "Amnesia":                   "Penalità alle skill di conoscenza pregressa. −10pt.",
  "Mancanza di Empatia":       "−3 Psicologia, −2 skill sociali empatiche. −15pt.",
  "Curiosità Morbosa":         "Volontà−2 per evitare luoghi/oggetti pericolosi. −5pt.",
  "Smemoratezza":              "Può fallire il richiamo di info critiche. −5pt.",
  "Pessimismo":                "−2 Leadership, penalizza il morale del gruppo. −5pt.",
};

// Tooltip flottante per badge
function BadgeTooltip({ text, color }) {
  return (
    <div style={{
      position: "absolute", bottom: "calc(100% + 6px)", left: "50%",
      transform: "translateX(-50%)",
      background: "#1a1b2e", border: `1px solid ${color}55`,
      borderRadius: 8, padding: "6px 10px", fontSize: 11, lineHeight: 1.5,
      color: "#e2e8f0", whiteSpace: "nowrap", zIndex: 9999,
      boxShadow: "0 4px 20px rgba(0,0,0,0.7)",
      pointerEvents: "none",
      maxWidth: 260, whiteSpace: "normal",
    }}>
      {text}
      <div style={{
        position: "absolute", top: "100%", left: "50%", transform: "translateX(-50%)",
        borderLeft: "5px solid transparent", borderRight: "5px solid transparent",
        borderTop: `5px solid ${color}55`,
      }} />
    </div>
  );
}

function Badge({ icon, label, color, bg, size = "sm", title, tooltip }) {
  const [showTip, setShowTip] = useState(false);
  const pad = size === "lg" ? "4px 12px" : size === "md" ? "3px 9px" : "2px 7px";
  const fs = size === "lg" ? 13 : size === "md" ? 12 : 11;
  return (
    <span
      title={title}
      onMouseEnter={() => tooltip && setShowTip(true)}
      onMouseLeave={() => setShowTip(false)}
      style={{
        position: "relative",
        display: "inline-flex", alignItems: "center", gap: 4,
        padding: pad, borderRadius: 6, fontSize: fs, fontWeight: 700,
        background: bg || `${color}18`,
        border: `1px solid ${color}44`,
        color, whiteSpace: "nowrap", lineHeight: 1.3,
        cursor: tooltip ? "help" : "default",
      }}>
      {icon && <span style={{ fontSize: fs + 1 }}>{icon}</span>}
      {label}
      {showTip && tooltip && <BadgeTooltip text={tooltip} color={color} />}
    </span>
  );
}

function SkillBadge({ skill, level, size }) {
  const meta = SKILL_META[skill] || { label: skill, attr: "—", color: "#9ca3af" };
  const tip = SKILL_TOOLTIP[skill];
  return (
    <Badge
      icon={<span style={{ fontSize: 9, opacity: 0.7, fontWeight: 900 }}>{meta.attr}</span>}
      label={`${meta.label}${level !== undefined ? ` ${level}` : ""}`}
      color={meta.color}
      size={size}
      tooltip={tip}
    />
  );
}

function AdvantagesBadges({ list = [], size = "sm" }) {
  if (!list || list.length === 0) return null;
  return (
    <span style={{ display: "inline-flex", flexWrap: "wrap", gap: 4 }}>
      {list.map((name, i) => {
        const meta = ADVANTAGE_META[name];
        if (!meta) return <Badge key={i} label={name} color="#9ca3af" size={size} />;
        const tip = ADVANTAGE_TOOLTIP[name];
        return (
          <Badge key={i}
            icon={meta.icon}
            label={name}
            color={meta.color}
            bg={meta.type === "dis" ? `${meta.color}10` : undefined}
            size={size}
            title={meta.type === "adv" ? "Vantaggio" : "Svantaggio"}
            tooltip={tip}
          />
        );
      })}
    </span>
  );
}

function WoundBadge({ threshold, size = "md" }) {
  const meta = WOUND_META[threshold];
  if (!meta) return null;
  return <Badge icon={meta.icon} label={meta.label} color={meta.color} bg={meta.bg} size={size} />;
}

function DamageTypeBadge({ type, size = "sm" }) {
  const meta = DAMAGE_TYPE_META[type] || { icon: "⚔", label: type, color: "#9ca3af" };
  return <Badge icon={meta.icon} label={meta.label} color={meta.color} size={size} />;
}

function DefenseBadge({ type, size = "sm" }) {
  const meta = DEFENSE_META[type] || { icon: "🛡", label: type, color: "#9ca3af" };
  return <Badge icon={meta.icon} label={meta.label} color={meta.color} size={size} />;
}

function NpcStatusBadge({ status, size = "sm" }) {
  const meta = NPC_STATUS_META[status] || { icon: "🟢", label: status, color: "#9ca3af" };
  return <Badge icon={meta.icon} label={meta.label} color={meta.color} size={size} />;
}

function NpcAttitudeBadge({ attitude, size = "sm" }) {
  const meta = NPC_ATTITUDE_META[attitude] || { icon: "😐", label: attitude, color: "#9ca3af" };
  return <Badge icon={meta.icon} label={meta.label} color={meta.color} size={size} />;
}

function NarrativeHintBadge({ hint, size = "sm" }) {
  const meta = NARRATIVE_HINT_META[hint];
  if (!meta) return null;
  return <Badge icon={meta.icon} label={meta.label} color={meta.color} size={size} />;
}

// Componente nome editabile inline — doppio click per modificare, Enter/blur per confermare
function EditableName({ name, onRename, style = {}, inputStyle = {} }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(name);
  const inputRef = useRef();

  function startEdit(e) {
    e.stopPropagation();
    setDraft(name);
    setEditing(true);
    setTimeout(() => inputRef.current?.select(), 0);
  }

  function confirm(e) {
    e?.stopPropagation();
    setEditing(false);
    const trimmed = draft.trim();
    if (trimmed && trimmed !== name) onRename(trimmed);
    else setDraft(name);
  }

  function onKey(e) {
    if (e.key === "Enter") confirm(e);
    if (e.key === "Escape") { setEditing(false); setDraft(name); }
    e.stopPropagation();
  }

  if (editing) {
    return (
      <input
        ref={inputRef}
        value={draft}
        onChange={e => setDraft(e.target.value)}
        onBlur={confirm}
        onKeyDown={onKey}
        onClick={e => e.stopPropagation()}
        style={{
          background: "rgba(255,255,255,0.08)", border: "1px solid var(--accent)",
          borderRadius: 5, padding: "1px 6px", fontSize: "inherit",
          color: "var(--text-h)", fontWeight: "inherit", outline: "none",
          width: Math.max(80, draft.length * 9),
          ...inputStyle,
        }}
      />
    );
  }

  return (
    <span
      onDoubleClick={startEdit}
      title="Doppio clic per modificare il nome"
      style={{ cursor: "text", borderBottom: "1px dashed rgba(255,255,255,0.2)", ...style }}
    >
      {name}
    </span>
  );
}

function PlayerChip({ player, active, onClick, avatar, onRename }) {
  return (
    <button onClick={onClick} style={{
      display: "flex", alignItems: "center", gap: 8,
      padding: "5px 12px 5px 5px", borderRadius: 20,
      border: active ? "2px solid var(--accent)" : "1px solid var(--border)",
      background: active ? "var(--accent-bg)" : "var(--bg)",
      cursor: "pointer", fontSize: 13, color: "var(--text-h)",
      transition: "all 0.15s",
    }}>
      <AvatarCircle src={avatar} size={28} fallback="🧑" />
      {onRename
        ? <EditableName name={player.name} onRename={onRename} style={{ fontSize: 13, fontWeight: 600 }} />
        : <span>{player.name}</span>
      }
      <span style={{ fontSize: 11, color: "var(--text)", opacity: 0.7 }}>{player.role}</span>
      <span style={{ fontSize: 11, background: "var(--code-bg)", borderRadius: 4, padding: "1px 5px" }}>
        ❤️ {player.hp}/{player.max_hp}
      </span>
    </button>
  );
}

// ─── Dati skill per builder manuale ────────────────────────────────────────

const SKILL_LIST = [
  // ── FO ──
  { key: "combattere",   label: "Combattere",   stat: "forza" },
  { key: "lottare",      label: "Lottare",       stat: "forza" },
  { key: "forzare",      label: "Forzare",       stat: "forza" },
  { key: "proteggere",   label: "Scudo",         stat: "forza" },
  { key: "trasportare",  label: "Trasportare",   stat: "forza" },
  { key: "lanciare",     label: "Lanciare",      stat: "forza" },
  { key: "sollevare",    label: "Sollevare",     stat: "forza" },
  { key: "nuotare",      label: "Nuotare",       stat: "forza" },
  { key: "resistere",    label: "Resistere",     stat: "forza" },
  // ── DE ──
  { key: "schivare",     label: "Schivare",      stat: "agilita" },
  { key: "furtivita",    label: "Furtività",     stat: "agilita" },
  { key: "acrobazia",    label: "Acrobazia",     stat: "agilita" },
  { key: "mira",         label: "Mira",          stat: "agilita" },
  { key: "guidare",      label: "Guidare",       stat: "agilita" },
  { key: "scassinare",   label: "Scassinare",    stat: "agilita" },
  { key: "infiltrarsi",  label: "Infiltrarsi",   stat: "agilita" },
  { key: "pedinare",     label: "Pedinare",      stat: "agilita" },
  { key: "arrampicarsi", label: "Arrampicarsi",  stat: "agilita" },
  { key: "saltare",      label: "Saltare",       stat: "agilita" },
  { key: "rapidita",     label: "Scattare",      stat: "agilita" },
  { key: "manualita",    label: "Manualità",     stat: "agilita" },
  { key: "cavalcare",    label: "Cavalcare",     stat: "agilita" },
  { key: "equilibrio",   label: "Equilibrio",    stat: "agilita" },
  { key: "borseggiare",  label: "Borseggio",     stat: "agilita" },
  // ── IN ──
  { key: "investigare",  label: "Investigare",   stat: "intelligenza" },
  { key: "analizzare",   label: "Analizzare",    stat: "intelligenza" },
  { key: "tecnologia",   label: "Tecnologia",    stat: "intelligenza" },
  { key: "medicina",     label: "Medicina",      stat: "intelligenza" },
  { key: "strategia",    label: "Strategia",     stat: "intelligenza" },
  { key: "osservare",    label: "Osservare",     stat: "intelligenza" },
  { key: "decifrare",    label: "Decifrare",     stat: "intelligenza" },
  { key: "scienze",      label: "Scienze",       stat: "intelligenza" },
  { key: "sopravvivere", label: "Sopravvivere",  stat: "intelligenza" },
  { key: "intimidire",   label: "Intimidire",    stat: "intelligenza" },
  { key: "demolire",     label: "Esplosivi",     stat: "intelligenza" },
  { key: "mimetizzare",  label: "Mimetizzarsi",  stat: "intelligenza" },
  { key: "ingegneria",   label: "Ingegneria",    stat: "intelligenza" },
  { key: "legge",        label: "Legge",         stat: "intelligenza" },
  { key: "occultismo",   label: "Occultismo",    stat: "intelligenza" },
  { key: "seguire_tracce",label:"Seguire Tracce",stat: "intelligenza" },
  { key: "navigare",     label: "Navigazione",   stat: "intelligenza" },
  { key: "storia",       label: "Storia",        stat: "intelligenza" },
  { key: "economia",     label: "Economia",      stat: "intelligenza" },
  { key: "meccanica",    label: "Meccanica",     stat: "intelligenza" },
  { key: "elettronica",  label: "Elettronica",   stat: "intelligenza" },
  { key: "informatica",  label: "Informatica",   stat: "intelligenza" },
  { key: "cultura",      label: "Cultura",       stat: "intelligenza" },
  { key: "sopravvivenza_urbana", label: "Soprav. Urbana", stat: "intelligenza" },
  { key: "astronomia",   label: "Astronomia",    stat: "intelligenza" },
  { key: "biologia",     label: "Biologia",      stat: "intelligenza" },
  { key: "chimica",      label: "Chimica",       stat: "intelligenza" },
  { key: "fisica",       label: "Fisica",        stat: "intelligenza" },
  { key: "linguistica",  label: "Linguistica",   stat: "intelligenza" },
  { key: "filosofia",    label: "Filosofia",     stat: "intelligenza" },
  { key: "teologia",     label: "Teologia",      stat: "intelligenza" },
  { key: "politica",     label: "Politica",      stat: "intelligenza" },
  // ── SA ──
  { key: "persuadere",   label: "Persuadere",    stat: "empatia" },
  { key: "ingannare",    label: "Ingannare",     stat: "empatia" },
  { key: "intuire",      label: "Intuire",       stat: "empatia" },
  { key: "calmare",      label: "Calmare",       stat: "empatia" },
  { key: "ispirare",     label: "Ispirare",      stat: "empatia" },
  { key: "curare",       label: "Curare",        stat: "empatia" },
  { key: "comandare",    label: "Comandare",     stat: "empatia" },
  { key: "comunicare",   label: "Comunicare",    stat: "empatia" },
  { key: "intrattenere", label: "Intrattenere",  stat: "empatia" },
  { key: "recitazione",  label: "Recitazione",   stat: "empatia" },
  { key: "parlare_in_pubblico", label: "Parlare in Pubblico", stat: "empatia" },
  { key: "etichetta",    label: "Galateo",       stat: "empatia" },
  { key: "interrogare",  label: "Interrogatorio",stat: "empatia" },
  { key: "seduzione",    label: "Seduzione",     stat: "empatia" },
];

const ADVANTAGE_LIST = [
  { key: "Carisma",                   cost: 5,  label: "Carisma",                   desc: "+2 tiri reazione NPC, +2 skill sociali" },
  { key: "Riflessi da Combattimento", cost: 15, label: "Riflessi da Combattimento", desc: "+1 schivata/parata/blocco, mai sorpreso" },
  { key: "Duro da Uccidere",          cost: 2,  label: "Duro da Uccidere",          desc: "Soglia morte raddoppiata" },
  { key: "Sensi Acuti",               cost: 2,  label: "Sensi Acuti",               desc: "+2 Percezione e osservare" },
  { key: "Forza Aumentata",           cost: 10, label: "Forza Aumentata",           desc: "+1 FO effettiva, +1 danni mischia" },
  { key: "Alta Tecnologia",           cost: 5,  label: "Alta Tecnologia",           desc: "+2 tecnologia e ingegneria" },
  { key: "Ambidestrezza",             cost: 5,  label: "Ambidestrezza",             desc: "Nessuna penalità mano non dominante" },
  { key: "Bellezza",                  cost: 4,  label: "Bellezza",                  desc: "+1 tiri di reazione, bonus seduzione" },
  { key: "Empatia",                   cost: 15, label: "Empatia",                   desc: "+3 Psicologia, percepisce bugie" },
  { key: "Memoria Fotografica",       cost: 10, label: "Memoria Fotografica",       desc: "+2 skill di conoscenza" },
  { key: "Coraggio",                  cost: 10, label: "Coraggio",                  desc: "+2 Volontà contro paura e stress" },
  { key: "Sangue Freddo",             cost: 5,  label: "Sangue Freddo",             desc: "Nessuna penalità shock su tiri mira" },
  { key: "Fortuna",                   cost: 15, label: "Fortuna",                   desc: "Ritira un tiro per sessione, prende il migliore" },
  { key: "Contatti",                  cost: 3,  label: "Contatti",                  desc: "Rete informatori, +1 reazione nel gruppo" },
  { key: "Status Sociale",            cost: 5,  label: "Status Sociale",            desc: "+1 reazione in contesti sociali" },
  { key: "Ricchezza",                 cost: 10, label: "Ricchezza",                 desc: "Risorse finanziarie significative" },
  { key: "Talento",                   cost: 5,  label: "Talento",                   desc: "+1 a un gruppo tematico di skill" },
  { key: "Voce Bella",                cost: 10, label: "Voce Bella",                desc: "+2 intrattenere/parlare in pubblico" },
  { key: "Autorità",                  cost: 5,  label: "Autorità",                  desc: "NPC di rango inferiore obbediscono" },
  { key: "Linguaggio Nativo Extra",   cost: 3,  label: "Linguaggio Nativo Extra",   desc: "Parla un'altra lingua come madrelingua" },
  { key: "Istinto di Sopravvivenza",  cost: 5,  label: "Istinto di Sopravvivenza",  desc: "+1 sopravvivere, non viene mai colto di sorpresa" },
];
const DISADV_LIST = [
  { key: "Animo Sanguinario", cost: -10, label: "Animo Sanguinario", desc: "Morale check per ritirarsi" },
  { key: "Codardo",           cost: -5,  label: "Codardo",           desc: "-2 a tutti i tiri in pericolo fisico" },
  { key: "Sospettoso",        cost: -5,  label: "Sospettoso",        desc: "-2 skill sociali, +1 intuire" },
  { key: "Avidità",           cost: -15, label: "Avidità",           desc: "Volontà−3 per resistere all'avidità" },
  { key: "Senso del Dovere",  cost: -5,  label: "Senso del Dovere",  desc: "Non abbandona mai i compagni" },
  { key: "Nemico",            cost: -5,  label: "Nemico",            desc: "Un nemico attivo interferisce regolarmente" },
  { key: "Segreto",           cost: -10, label: "Segreto",           desc: "Se scoperto, conseguenze gravi" },
  { key: "Dipendenza",        cost: -5,  label: "Dipendenza",        desc: "-1 a tutti i tiri in astinenza" },
  { key: "Fobia",             cost: -10, label: "Fobia",             desc: "Volontà−4 quando esposto alla fobia" },
  { key: "Impulsività",       cost: -10, label: "Impulsività",       desc: "Volontà−2 per resistere all'impulso" },
  { key: "Arroganza",         cost: -5,  label: "Arroganza",         desc: "-1 reazione con sconosciuti" },
  { key: "Lealtà",            cost: -5,  label: "Lealtà",            desc: "Non può agire contro i propri alleati" },
  { key: "Poca Autostima",    cost: -10, label: "Poca Autostima",    desc: "-2 leadership, -1 Volontà nei momenti critici" },
  { key: "Amnesia",           cost: -10, label: "Amnesia",           desc: "Penalità alle skill di conoscenza pregressa" },
  { key: "Mancanza di Empatia",cost:-15, label: "Mancanza di Empatia",desc: "-3 Psicologia, -2 skill sociali empatiche" },
  { key: "Curiosità Morbosa", cost: -5,  label: "Curiosità Morbosa", desc: "Volontà−2 per evitare luoghi pericolosi" },
  { key: "Smemoratezza",      cost: -5,  label: "Smemoratezza",      desc: "Può fallire il richiamo di info critiche" },
  { key: "Pessimismo",        cost: -5,  label: "Pessimismo",        desc: "-2 Leadership, penalizza il morale del gruppo" },
];

const STAT_COST = { forza: 10, agilita: 20, intelligenza: 20, empatia: 10 };
const SKILL_DIFF_OFFSET = { forza: 0, agilita: 0, intelligenza: -1, empatia: -1 };
const SKILL_COSTS = [1, 1, 2, 4, 4, 4, 4, 4];

function calcSkillCost(skillKey, level, stats) {
  const sk = SKILL_LIST.find(s => s.key === skillKey);
  if (!sk) return 0;
  const base = (stats[sk.stat] || 10) + (SKILL_DIFF_OFFSET[sk.stat] ?? -1);
  const above = Math.max(0, level - base);
  let total = 0;
  for (let i = 0; i < above; i++) total += (i < SKILL_COSTS.length ? SKILL_COSTS[i] : 4);
  return total;
}

function calcPoints(stats, skills, advantages, disadvantages) {
  const sc = Object.entries(stats).reduce((s, [k, v]) => s + (v - 10) * (STAT_COST[k] || 10), 0);
  const skc = Object.entries(skills).reduce((s, [k, v]) => s + calcSkillCost(k, v, stats), 0);
  const avc = advantages.reduce((s, a) => s + (ADVANTAGE_LIST.find(x => x.key === a)?.cost || 0), 0);
  const dvc = disadvantages.reduce((s, d) => s + (DISADV_LIST.find(x => x.key === d)?.cost || 0), 0);
  return { total: sc + skc + avc + dvc, sc, skc, avc, dvc };
}

// ─── Modal creazione personaggio ───────────────────────────────────────────

function CharacterBuilderModal({ genre, archetypes, onAdd, onClose }) {
  const [tab, setTab] = useState("ai"); // "ai" | "manual" | "archetype"

  // AI state
  const [aiDesc, setAiDesc] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState(null);
  const [aiError, setAiError] = useState("");

  // Manual state
  const [mName, setMName] = useState("");
  const [mRole, setMRole] = useState("");
  const [mStats, setMStats] = useState({ forza: 10, agilita: 10, intelligenza: 10, empatia: 10 });
  const [mSkills, setMSkills] = useState({});
  const [mAdvantages, setMAdvantages] = useState([]);
  const [mDisadvantages, setMDisadvantages] = useState([]);
  const mPts = calcPoints(mStats, mSkills, mAdvantages, mDisadvantages);

  // Archetype state
  const [baseArch, setBaseArch] = useState(archetypes[0] || null);
  const [archName, setArchName] = useState(archetypes[0]?.name || "");

  async function handleAiGenerate() {
    if (!aiDesc.trim()) return;
    setAiLoading(true); setAiError(""); setAiResult(null);
    const res = await fetch(`${API_URL}/game/character/generate-ai`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ genre, description: aiDesc }),
    }).then(r => r.json());
    setAiLoading(false);
    if (res.error) { setAiError(res.error); return; }
    setAiResult(res);
  }

  async function handleAiConfirm() {
    const draft = aiResult.draft;
    const res = await fetch(`${API_URL}/game/character/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(draft),
    }).then(r => r.json());
    if (res.player) onAdd(res.player);
  }

  async function handleManualAdd() {
    if (!mName.trim()) return;
    const draft = { name: mName, role: mRole || "Avventuriero", archetype: mRole || "custom",
      stats: mStats, skills: mSkills, advantages: mAdvantages, disadvantages: mDisadvantages, dr: 0, items: [] };
    const res = await fetch(`${API_URL}/game/character/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(draft),
    }).then(r => r.json());
    if (res.player) onAdd(res.player);
  }

  async function handleArchAdd() {
    if (!baseArch) return;
    const draft = { ...baseArch, name: archName || baseArch.name,
      archetype: baseArch.archetype || baseArch.role, items: baseArch.base_items || [] };
    const res = await fetch(`${API_URL}/game/character/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(draft),
    }).then(r => r.json());
    if (res.player) onAdd(res.player);
  }

  const tabStyle = (t) => ({
    padding: "8px 18px", border: "none", cursor: "pointer", fontSize: 14, fontWeight: 700,
    borderBottom: tab === t ? "2px solid var(--accent)" : "2px solid transparent",
    background: "none", color: tab === t ? "var(--accent)" : "var(--text)",
  });

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 1000,
      background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center",
      padding: 16,
    }} onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{
        background: "var(--bg)", borderRadius: 16, width: "100%", maxWidth: 580,
        maxHeight: "90vh", display: "flex", flexDirection: "column",
        border: "1px solid var(--border)", boxShadow: "0 24px 64px rgba(0,0,0,0.6)",
      }}>
        {/* header */}
        <div style={{ padding: "20px 24px 0", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ fontSize: 18, fontWeight: 800, color: "var(--text-h)" }}>Crea personaggio</div>
          <button onClick={onClose} style={{ background: "none", border: "none", fontSize: 22, cursor: "pointer", color: "var(--text)", lineHeight: 1 }}>×</button>
        </div>

        {/* tabs */}
        <div style={{ display: "flex", borderBottom: "1px solid var(--border)", padding: "0 16px", marginTop: 8 }}>
          <button style={tabStyle("ai")} onClick={() => setTab("ai")}>✨ AI</button>
          <button style={tabStyle("manual")} onClick={() => setTab("manual")}>🔧 Manuale</button>
          <button style={tabStyle("archetype")} onClick={() => setTab("archetype")}>📋 Archetipo</button>
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px 24px" }}>

          {/* ── TAB AI ── */}
          {tab === "ai" && (
            <div>
              <p style={{ fontSize: 14, color: "var(--text)", marginTop: 0, marginBottom: 12 }}>
                Descrivi il personaggio in linguaggio libero. Claude genera stats e skill GURPS.
              </p>
              <textarea
                value={aiDesc}
                onChange={e => setAiDesc(e.target.value)}
                placeholder="Es: Un ex detective alcolizzato che non si fida di nessuno ma sa leggere le persone come libri aperti. Ha una cicatrice sul viso e porta sempre una pistola nascosta."
                rows={4}
                style={{
                  width: "100%", boxSizing: "border-box", padding: "10px 14px",
                  borderRadius: 8, border: "1px solid var(--border)",
                  background: "var(--code-bg)", color: "var(--text-h)", fontSize: 14,
                  resize: "vertical", lineHeight: 1.5, fontFamily: "inherit",
                }}
              />
              <button onClick={handleAiGenerate} disabled={!aiDesc.trim() || aiLoading} style={{
                marginTop: 10, padding: "10px 20px", borderRadius: 8, border: "none",
                background: aiDesc.trim() ? "var(--accent)" : "var(--border)",
                color: "#fff", fontWeight: 700, cursor: aiDesc.trim() ? "pointer" : "not-allowed", fontSize: 14,
              }}>
                {aiLoading ? "Generazione in corso..." : "✨ Genera personaggio"}
              </button>

              {aiError && <div style={{ marginTop: 10, color: "#f87171", fontSize: 13 }}>{aiError}</div>}

              {aiResult && (
                <div style={{ marginTop: 16, padding: 16, borderRadius: 10, background: "var(--code-bg)", border: "1px solid var(--border)" }}>
                  <div style={{ fontWeight: 800, fontSize: 16, color: "var(--text-h)", marginBottom: 2 }}>{aiResult.draft.name}</div>
                  <div style={{ fontSize: 12, color: "var(--accent)", marginBottom: 10 }}>{aiResult.draft.role}</div>
                  <StatBar stats={aiResult.draft.stats} />
                  <div style={{ marginTop: 8, display: "flex", gap: 5, flexWrap: "wrap" }}>
                    {Object.entries(aiResult.draft.skills || {}).map(([sk, lv]) => (
                      <span key={sk} style={{ fontSize: 11, background: "var(--bg)", border: "1px solid var(--border)", borderRadius: 5, padding: "1px 6px" }}>{sk} {lv}</span>
                    ))}
                  </div>
                  {(aiResult.draft.advantages?.length > 0 || aiResult.draft.disadvantages?.length > 0) && (
                    <div style={{ marginTop: 6, fontSize: 12, color: "var(--text)" }}>
                      {aiResult.draft.advantages?.join(", ")} {aiResult.draft.disadvantages?.length > 0 && `· ${aiResult.draft.disadvantages.join(", ")}`}
                    </div>
                  )}
                  {aiResult.draft.point_breakdown && (
                    <div style={{ marginTop: 6, fontSize: 11, color: "var(--text)", opacity: 0.7 }}>{aiResult.draft.point_breakdown}</div>
                  )}
                  {aiResult.validation && !aiResult.validation.valid && (
                    <div style={{ marginTop: 6, fontSize: 12, color: "#f87171" }}>
                      ⚠ {aiResult.validation.errors?.join("; ")}
                    </div>
                  )}
                  <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                    <button onClick={handleAiConfirm} style={{
                      flex: 1, padding: "10px 0", borderRadius: 8, border: "none",
                      background: "var(--accent)", color: "#fff", fontWeight: 700, cursor: "pointer",
                    }}>Aggiungi al gruppo</button>
                    <button onClick={() => setAiResult(null)} style={{
                      padding: "10px 14px", borderRadius: 8, border: "1px solid var(--border)",
                      background: "var(--bg)", color: "var(--text)", cursor: "pointer",
                    }}>Rigenera</button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── TAB MANUALE ── */}
          {tab === "manual" && (
            <div>
              {/* punti */}
              <div style={{
                padding: "8px 14px", borderRadius: 8, marginBottom: 16,
                background: mPts.total > 100 ? "rgba(239,68,68,0.1)" : "var(--code-bg)",
                border: `1px solid ${mPts.total > 100 ? "#ef4444" : "var(--border)"}`,
                fontSize: 13, fontWeight: 700, color: mPts.total > 100 ? "#f87171" : "var(--text-h)",
                display: "flex", justifyContent: "space-between",
              }}>
                <span>Punti spesi: {mPts.total} / 100</span>
                <span style={{ fontWeight: 400, fontSize: 12, color: "var(--text)" }}>
                  stat {mPts.sc} + skill {mPts.skc} + adv {mPts.avc + mPts.dvc}
                </span>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 14 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text)" }}>Nome</label>
                  <input value={mName} onChange={e => setMName(e.target.value)} placeholder="Nome personaggio"
                    style={{ display: "block", width: "100%", boxSizing: "border-box", marginTop: 4, padding: "8px 10px", borderRadius: 7, border: "1px solid var(--border)", background: "var(--code-bg)", color: "var(--text-h)", fontSize: 14 }} />
                </div>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text)" }}>Ruolo</label>
                  <input value={mRole} onChange={e => setMRole(e.target.value)} placeholder="Es: Cecchino, Strega..."
                    style={{ display: "block", width: "100%", boxSizing: "border-box", marginTop: 4, padding: "8px 10px", borderRadius: 7, border: "1px solid var(--border)", background: "var(--code-bg)", color: "var(--text-h)", fontSize: 14 }} />
                </div>
              </div>

              {/* stat sliders */}
              <div style={{ marginBottom: 14 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text)", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 }}>Attributi</div>
                {[["forza","FO","💪"],["agilita","DE","🏃"],["intelligenza","IN","🧠"],["empatia","SA","💙"]].map(([key, label, icon]) => (
                  <div key={key} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                    <span style={{ width: 60, fontSize: 13, fontWeight: 600, color: "var(--text-h)" }}>{icon} {label}</span>
                    <input type="range" min={6} max={16} value={mStats[key]}
                      onChange={e => setMStats(s => ({ ...s, [key]: +e.target.value }))}
                      style={{ flex: 1 }} />
                    <span style={{ width: 28, textAlign: "right", fontWeight: 700, color: "var(--text-h)", fontSize: 15 }}>{mStats[key]}</span>
                    <span style={{ width: 50, fontSize: 11, color: mPts.sc > 0 ? "var(--accent)" : "var(--text)", textAlign: "right" }}>
                      {(mStats[key]-10) * STAT_COST[key] > 0 ? "+" : ""}{(mStats[key]-10) * STAT_COST[key]}pt
                    </span>
                  </div>
                ))}
              </div>

              {/* skill */}
              <div style={{ marginBottom: 14 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text)", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 }}>Skill (0 = non acquistata)</div>
                {[
                  { group: "forza",        label: "💪 FO — Forza" },
                  { group: "agilita",      label: "🏃 DE — Destrezza" },
                  { group: "intelligenza", label: "🧠 IN — Intelligenza" },
                  { group: "empatia",      label: "💙 SA — Salute/Empatia" },
                ].map(({ group, label }) => (
                  <div key={group} style={{ marginBottom: 10 }}>
                    <div style={{ fontSize: 11, fontWeight: 600, color: "var(--accent)", marginBottom: 4, marginTop: 2 }}>{label}</div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4 }}>
                      {SKILL_LIST.filter(sk => sk.stat === group).map(sk => (
                        <div key={sk.key} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <span style={{ fontSize: 12, flex: 1, color: "var(--text)" }}>{sk.label}</span>
                          <input type="number" min={0} max={18}
                            value={mSkills[sk.key] || 0}
                            onChange={e => {
                              const v = +e.target.value;
                              setMSkills(s => v === 0 ? Object.fromEntries(Object.entries(s).filter(([k]) => k !== sk.key)) : { ...s, [sk.key]: v });
                            }}
                            style={{ width: 44, padding: "3px 6px", borderRadius: 5, border: "1px solid var(--border)", background: "var(--code-bg)", color: "var(--text-h)", fontSize: 13, textAlign: "center" }}
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              {/* vantaggi */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text)", marginBottom: 6, textTransform: "uppercase", letterSpacing: 0.5 }}>Vantaggi</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginBottom: 10 }}>
                  {ADVANTAGE_LIST.map(a => {
                    const sel = mAdvantages.includes(a.key);
                    return <button key={a.key} title={a.desc} onClick={() => setMAdvantages(p => sel ? p.filter(x=>x!==a.key) : [...p, a.key])} style={{
                      padding: "4px 9px", borderRadius: 20, fontSize: 11, cursor: "pointer",
                      border: sel ? "1px solid var(--accent)" : "1px solid var(--border)",
                      background: sel ? "var(--accent-bg)" : "var(--bg)", color: sel ? "var(--accent)" : "var(--text)",
                    }}>{a.label} +{a.cost}pt</button>;
                  })}
                </div>
                <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text)", marginBottom: 6, textTransform: "uppercase", letterSpacing: 0.5 }}>Svantaggi</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                  {DISADV_LIST.map(d => {
                    const sel = mDisadvantages.includes(d.key);
                    return <button key={d.key} title={d.desc} onClick={() => setMDisadvantages(p => sel ? p.filter(x=>x!==d.key) : [...p, d.key])} style={{
                      padding: "4px 9px", borderRadius: 20, fontSize: 11, cursor: "pointer",
                      border: sel ? "1px solid #f87171" : "1px solid var(--border)",
                      background: sel ? "rgba(239,68,68,0.1)" : "var(--bg)", color: sel ? "#f87171" : "var(--text)",
                    }}>{d.label} {d.cost}pt</button>;
                  })}
                </div>
              </div>

              <button onClick={handleManualAdd} disabled={!mName.trim() || mPts.total > 100} style={{
                width: "100%", padding: "11px 0", borderRadius: 8, border: "none",
                background: mName.trim() && mPts.total <= 100 ? "var(--accent)" : "var(--border)",
                color: "#fff", fontWeight: 700, cursor: mName.trim() && mPts.total <= 100 ? "pointer" : "not-allowed",
              }}>Aggiungi al gruppo</button>
            </div>
          )}

          {/* ── TAB ARCHETIPO ── */}
          {tab === "archetype" && (
            <div>
              <p style={{ fontSize: 14, color: "var(--text)", marginTop: 0, marginBottom: 12 }}>
                Parti da un archetipo e personalizza solo il nome.
              </p>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 16 }}>
                {archetypes.map(a => (
                  <div key={a.id} onClick={() => { setBaseArch(a); setArchName(a.name); }} style={{
                    padding: 12, borderRadius: 10, cursor: "pointer",
                    border: baseArch?.id === a.id ? "2px solid var(--accent)" : "1px solid var(--border)",
                    background: baseArch?.id === a.id ? "var(--accent-bg)" : "var(--code-bg)",
                  }}>
                    <div style={{ fontWeight: 700, fontSize: 13, color: "var(--text-h)" }}>{a.name}</div>
                    <div style={{ fontSize: 11, color: "var(--accent)", marginBottom: 6 }}>{a.role}</div>
                    <StatBar stats={a.stats} />
                  </div>
                ))}
              </div>

              {baseArch && (
                <>
                  <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text)" }}>Nome personalizzato</label>
                  <input value={archName} onChange={e => setArchName(e.target.value)}
                    style={{ display: "block", width: "100%", boxSizing: "border-box", marginTop: 4, marginBottom: 14, padding: "9px 12px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--code-bg)", color: "var(--text-h)", fontSize: 14 }} />
                  <button onClick={handleArchAdd} style={{
                    width: "100%", padding: "11px 0", borderRadius: 8, border: "none",
                    background: "var(--accent)", color: "#fff", fontWeight: 700, cursor: "pointer",
                  }}>Aggiungi al gruppo</button>
                </>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  );
}

// ─── Genre data ────────────────────────────────────────────────────────────

const GENRE_META = {
  sci_fi:           { emoji: "🚀", label: "Sci-Fi",           sub: "Stazioni, frontiere, anomalie, diplomazia e esplorazione.", color: "#00cfff",  gradient: "135deg, #0f0c29, #302b63, #24243e" },
  fantasy:          { emoji: "⚔️",  label: "Fantasy",          sub: "Regni, rovine, magie antiche, giuramenti e creature leggendarie.", color: "#22ff44", gradient: "135deg, #1a1a2e, #16213e, #0f3460" },
  mystery_horror:   { emoji: "🕯️", label: "Mystery Horror",   sub: "Indizi sporchi, case sbagliate, simboli e paura nell'ombra.", color: "#cccccc", gradient: "135deg, #1c1c1c, #2d1b2e, #1a0a0a" },
  ww2:              { emoji: "🪖",  label: "WW2",              sub: "Operazioni sporche, linee nemiche, sacrificio e strategia bellica.", color: "#ffd700", gradient: "135deg, #1a1a00, #2d2d00, #1a0d00" },
  romance:          { emoji: "💌",  label: "Romance",          sub: "Tensioni emotive, occasioni mancate, legami profondi.", color: "#ff6eb4", gradient: "135deg, #2d0030, #4a0040, #200020" },
  action:           { emoji: "💥",  label: "Action",           sub: "Assalti, fughe, blitz, inseguimenti e finestre di opportunità.", color: "#ff7700", gradient: "135deg, #1a0000, #3d0000, #1a0a00" },
  detective_classico: { emoji: "🔍", label: "Detective",      sub: "Moventi, alibi, stanze chiuse e verità che nessuno vuole.", color: "#88aaff", gradient: "135deg, #0a0a0a, #1a1a1a, #0d0d1a" },
};

// ─── Setup screen ──────────────────────────────────────────────────────────

function ProviderBtn({ pkey, label, icon, desc, selected, available, onClick }) {
  const avail = available !== false;
  const sel = selected;
  return (
    <button onClick={() => avail && onClick(pkey)}
      style={{
        display: "flex", flexDirection: "column", alignItems: "center", gap: 3,
        padding: "8px 16px", borderRadius: 10,
        border: sel ? "2px solid #c084fc" : "1px solid rgba(255,255,255,0.18)",
        background: sel ? "rgba(170,59,255,0.35)" : "rgba(0,0,0,0.5)",
        color: sel ? "#fff" : avail ? "rgba(255,255,255,0.75)" : "rgba(255,255,255,0.3)",
        cursor: avail ? "pointer" : "default",
        backdropFilter: "blur(8px)",
        transition: "all 0.15s",
        boxShadow: sel ? "0 0 14px rgba(192,132,252,0.4)" : "none",
        minWidth: 72,
        opacity: avail ? 1 : 0.5,
      }}>
      <span style={{ fontSize: 20 }}>{icon}</span>
      <span style={{ fontSize: 12, fontWeight: sel ? 800 : 500 }}>{label}</span>
      <span style={{ fontSize: 9, opacity: 0.6 }}>{avail ? desc : "non config."}</span>
    </button>
  );
}

function TextProviderPicker({ value, onChange, available }) {
  const options = [
    { key: "claude", label: "Claude", icon: "🤖", desc: "Anthropic" },
    { key: "openai", label: "OpenAI", icon: "🟢", desc: "GPT-4o" },
  ];
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
      <span style={{ fontSize: 10, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: 2, fontWeight: 600 }}>AI Narrativa</span>
      <div style={{ display: "flex", gap: 8 }}>
        {options.map(p => (
          <ProviderBtn key={p.key} pkey={p.key} label={p.label} icon={p.icon} desc={p.desc}
            selected={value === p.key} available={available[p.key] !== false} onClick={onChange} />
        ))}
      </div>
    </div>
  );
}

function ImageProviderPicker({ value, onChange, available }) {
  const options = [
    { key: "auto",   label: "Auto",   icon: "✨", desc: "primo disponibile" },
    { key: "openai", label: "OpenAI", icon: "🟢", desc: "gpt-image-1" },
    { key: "gemini", label: "Gemini", icon: "💫", desc: "Imagen 4" },
    { key: "none",   label: "Nessuna",icon: "🚫", desc: "solo testo" },
  ];
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
      <span style={{ fontSize: 10, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: 2, fontWeight: 600 }}>AI Grafica</span>
      <div style={{ display: "flex", gap: 8 }}>
        {options.map(p => {
          const avail = p.key === "auto" || p.key === "none" ? true : available[p.key] !== false;
          return (
            <ProviderBtn key={p.key} pkey={p.key} label={p.label} icon={p.icon} desc={p.desc}
              selected={value === p.key} available={avail} onClick={onChange} />
          );
        })}
      </div>
    </div>
  );
}

function SetupScreen({ onStart }) {
  const [step, setStep] = useState("genre"); // "genre" | "team"
  const [genre, setGenre] = useState(null);
  const [provider, setProvider] = useState("claude");
  const [imageProvider, setImageProvider] = useState("auto");
  const [providersAvail, setProvidersAvail] = useState({ claude: true, openai: false, gemini: false });
  const [pool, setPool] = useState([]);
  const [selected, setSelected] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfError, setPdfError] = useState("");
  const [pdfMapPage, setPdfMapPage] = useState("");
  const [preloadedAdventure, setPreloadedAdventure] = useState(null);
  const [hovered, setHovered] = useState(null);
  const [showBuilder, setShowBuilder] = useState(false);
  const [avatars, setAvatars] = useState({});
  const [avatarLoading, setAvatarLoading] = useState({});

  useEffect(() => {
    fetch(`${API_URL}/game/providers-available`).then(r => r.json()).then(d => {
      setProvidersAvail(d);
      if (!d.claude && d.openai) setProvider("openai");
      else if (!d.claude && !d.openai && d.gemini) setProvider("gemini");
    }).catch(() => {});
  }, []);

  async function handlePdfUpload(file) {
    setPdfLoading(true); setPdfError(""); setPreloadedAdventure(null);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 240000); // 4 minuti
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("genre", "auto");
      form.append("players", JSON.stringify([]));
      if (pdfMapPage.trim()) form.append("map_page", pdfMapPage.trim());
      const res = await fetch(`${API_URL}/game/adventure/from-pdf`, {
        method: "POST", body: form, signal: controller.signal,
      }).then(r => r.json());
      clearTimeout(timeoutId);
      if (res.error) { setPdfError(res.error); setPdfLoading(false); return; }
      const detectedGenre = res.detected_genre || "detective_classico";
      setPreloadedAdventure(res);
      // Carica pool personaggi per il genere rilevato
      setLoading(true);
      await fetch(`${API_URL}/game/setup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ genre: detectedGenre, provider, image_provider: imageProvider }),
      });
      const s = await fetch(`${API_URL}/game/state`).then(r => r.json());
      setGenre(detectedGenre);
      const rawPool = s?.team_setup?.candidate_pool || [];
      setPool(rawPool);
      setSelected([]);
      setLoading(false);
      setPdfLoading(false);
      setStep("team");
      // Arricchisce i personaggi con backstory legati all'avventura (in background)
      if (res && rawPool.length > 0) {
        fetch(`${API_URL}/game/character/enrich-backstory`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ characters: rawPool, adventure: res, genre: detectedGenre }),
        }).then(r => r.json()).then(data => {
          if (data.characters) setPool(data.characters);
        }).catch(() => {});
      }
    } catch (e) {
      clearTimeout(timeoutId);
      setLoading(false);
      setPdfLoading(false);
      const msg = e.name === "AbortError"
        ? "Il server ha impiegato troppo tempo. Riprova o usa un PDF più corto."
        : "Errore di rete durante il caricamento del PDF. Controlla che il backend sia attivo.";
      setPdfError(msg);
    }
  }

  async function handleGenreSelect(g) {
    setGenre(g);
    setLoading(true);
    await fetch(`${API_URL}/game/setup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ genre: g, provider, image_provider: imageProvider }),
    });
    const s = await fetch(`${API_URL}/game/state`).then(r => r.json());
    const rawPool = s?.team_setup?.candidate_pool || [];
    setPool(rawPool);
    setSelected([]);
    setLoading(false);
    setStep("team");
  }

  function toggleSelect(id) {
    setSelected(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : prev.length < 4 ? [...prev, id] : prev
    );
  }

  async function handleStart() {
    if (selected.length < 1) return;
    setLoading(true);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 180000); // 3 minuti
    try {
      const stateRes = await fetch(`${API_URL}/game/select-team`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ selected_player_ids: selected, adventure_bible: preloadedAdventure || null }),
        signal: controller.signal,
      }).then(r => r.json());
      clearTimeout(timeoutId);
      // Merge backend players with enriched pool data (backstory, motivation, enriched advantages/disadvantages)
      const rawPlayers = stateRes?.players || pool.filter(p => selected.includes(p.id));
      const players = rawPlayers.map(p => {
        const enriched = pool.find(x => x.id === p.id);
        if (!enriched) return p;
        return {
          ...p,
          backstory: enriched.backstory || "",
          motivation: enriched.motivation || "",
          advantages: enriched.advantages?.length > 0 ? enriched.advantages : (p.advantages || []),
          disadvantages: enriched.disadvantages?.length > 0 ? enriched.disadvantages : (p.disadvantages || []),
        };
      });
      onStart(genre, players, avatars, provider, preloadedAdventure, imageProvider);
    } catch (e) {
      clearTimeout(timeoutId);
      setLoading(false);
      alert("Il server sta impiegando troppo tempo. Riprova tra qualche secondo.");
    }
  }

  async function handleRenameInPool(playerId, newName) {
    // Aggiorna localmente subito per feedback immediato
    setPool(prev => prev.map(p => p.id === playerId ? { ...p, name: newName } : p));
    // Sincronizza col backend
    try {
      await fetch(`${API_URL}/game/player/rename`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player_id: playerId, name: newName }),
      });
    } catch (_) {}
  }

  async function handleAvatarGenerate(player) {
    setAvatarLoading(prev => ({ ...prev, [player.id]: "Generazione..." }));
    try {
      const res = await fetch(`${API_URL}/game/generate-avatar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ photo_b64: "", genre, role: player.role, archetype: player.archetype || player.role, name: player.name, description: player.backstory || player.description || "" }),
      }).then(r => r.json());
      if (res.avatar_b64) {
        setAvatars(prev => ({ ...prev, [player.id]: res.avatar_b64 }));
        setAvatarLoading(prev => ({ ...prev, [player.id]: null }));
      } else {
        setAvatarLoading(prev => ({ ...prev, [player.id]: `❌ ${res.error || "Errore"}` }));
        setTimeout(() => setAvatarLoading(prev => ({ ...prev, [player.id]: null })), 4000);
      }
    } catch {
      setAvatarLoading(prev => ({ ...prev, [player.id]: "❌ Errore di rete" }));
      setTimeout(() => setAvatarLoading(prev => ({ ...prev, [player.id]: null })), 4000);
    }
  }

  async function handleAvatarUpload(player, file) {
    setAvatarLoading(prev => ({ ...prev, [player.id]: "Generazione..." }));
    const reader = new FileReader();
    reader.onload = async e => {
      const b64 = e.target.result.split(",")[1];
      try {
        const res = await fetch(`${API_URL}/game/generate-avatar`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ photo_b64: b64, genre, role: player.role, archetype: player.archetype || player.role }),
        }).then(r => r.json());
        if (res.avatar_b64) {
          setAvatars(prev => ({ ...prev, [player.id]: res.avatar_b64 }));
          setAvatarLoading(prev => ({ ...prev, [player.id]: null }));
        } else {
          setAvatarLoading(prev => ({ ...prev, [player.id]: `❌ ${res.error || "Errore"}` }));
          setTimeout(() => setAvatarLoading(prev => ({ ...prev, [player.id]: null })), 4000);
        }
      } catch (err) {
        setAvatarLoading(prev => ({ ...prev, [player.id]: "❌ Errore di rete" }));
        setTimeout(() => setAvatarLoading(prev => ({ ...prev, [player.id]: null })), 4000);
      }
    };
    reader.readAsDataURL(file);
  }

  // ── Select-team loading a schermo intero ──
  if (loading) return (
    <LoadingProgress
      icon="⚔️"
      title="Preparo il mondo di gioco..."
      steps={[
        { at: 0,     pill: "Mappa",      label: "Genero la mappa strategica..." },
        { at: 8000,  pill: "Canon",      label: "Costruisco la narrativa dell'avventura..." },
        { at: 20000, pill: "PNG",        label: "Creo i personaggi non giocanti..." },
        { at: 35000, pill: "Schede",     label: "Genero le schede GURPS degli NPC..." },
        { at: 55000, pill: "Finale",     label: "Quasi pronto, ancora un momento..." },
      ]}
    />
  );

  // ── PDF loading a schermo intero ──
  if (pdfLoading) return (
    <LoadingProgress
      icon="📄"
      title="Leggo il PDF e preparo la bibbia..."
      steps={[
        { at: 0,     pill: "Lettura",     label: "Estraggo il testo dal PDF..." },
        { at: 3000,  pill: "Analisi",     label: "Analizzo la struttura dell'avventura..." },
        { at: 8000,  pill: "Genere",      label: "Determino il genere narrativo..." },
        { at: 12000, pill: "PNG",         label: "Identifico i personaggi non giocanti..." },
        { at: 17000, pill: "Indizi",      label: "Mappo gli indizi e le rivelazioni..." },
        { at: 22000, pill: "Bibbia",      label: "Struttura la bibbia finale..." },
      ]}
    />
  );

  // ── Step 1: scegli genere ──
  if (step === "genre") {
    const genres = Object.keys(GENRE_META);
    return (
      <div style={{ minHeight: "100vh", background: "#000", display: "flex", flexDirection: "column" }}>
        {/* banner full-width */}
        <img src="/Banner superiore GURPS.png" alt="GURPS Master GDR" style={{ width: "100%", display: "block", objectFit: "cover", maxHeight: 100, marginTop: 12 }} />

        {/* barra provider + carica pdf */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 20, padding: "12px 24px", background: "#0a0a0a", flexWrap: "wrap" }}>
          <TextProviderPicker value={provider} onChange={setProvider} available={providersAvail} />
          <div style={{ width: 1, height: 64, background: "rgba(255,255,255,0.1)", flexShrink: 0 }} />
          <ImageProviderPicker value={imageProvider} onChange={setImageProvider} available={providersAvail} />
          <div style={{ width: 1, height: 64, background: "rgba(255,255,255,0.1)", flexShrink: 0 }} />
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 5, flexShrink: 0 }}>
            <label style={{ cursor: "pointer", opacity: pdfLoading ? 0.6 : 1, lineHeight: 0 }}>
              {pdfLoading
                ? <span style={{ color: "#fff", fontSize: 13, fontWeight: 600, padding: "10px 16px", background: "rgba(255,255,255,0.08)", borderRadius: 10, display: "inline-block" }}>⏳ Leggo PDF...</span>
                : <img src="/Carica PDF.png" alt="Carica PDF" style={{ height: 52, objectFit: "contain", display: "block" }} />
              }
              <input type="file" accept=".pdf" style={{ display: "none" }} disabled={pdfLoading}
                onChange={e => e.target.files[0] && handlePdfUpload(e.target.files[0])} />
            </label>
            <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
              <span style={{ fontSize: 10, color: "rgba(255,255,255,0.4)" }}>pag. mappa:</span>
              <input
                type="number" min="1" placeholder="—"
                value={pdfMapPage}
                onChange={e => setPdfMapPage(e.target.value)}
                style={{
                  width: 44, padding: "2px 5px", borderRadius: 5, fontSize: 11,
                  background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.15)",
                  color: "#fff", textAlign: "center",
                }}
              />
            </div>
          </div>
        </div>
        {pdfError && (
          <div style={{ textAlign: "center", color: "#f87171", fontSize: 13, padding: "4px 0 6px", background: "#0a0a0a" }}>
            ❌ {pdfError}
          </div>
        )}

        {/* splash image con overlay zone cliccabili */}
        <div style={{ position: "relative", width: "100%" }}>
          <img
            src="/Temi_Narrativi_2.png"
            alt="Generi narrativi"
            style={{ width: "100%", display: "block", objectFit: "contain" }}
          />

          {/* zone cliccabili — 7 colonne uguali */}
          <div style={{
            position: "absolute", inset: 0,
            display: "grid", gridTemplateColumns: "repeat(7, 1fr)",
          }}>
            {genres.map((key, i) => {
              const meta = GENRE_META[key];
              const isHov = hovered === key;
              return (
                <button
                  key={key}
                  onClick={() => handleGenreSelect(key)}
                  onMouseEnter={() => setHovered(key)}
                  onMouseLeave={() => setHovered(null)}
                  style={{
                    border: "none", background: isHov ? "rgba(255,255,255,0.08)" : "transparent",
                    cursor: "pointer",
                    transition: "background 0.2s",
                    outline: isHov ? `2px solid ${meta.color}` : "none",
                    outlineOffset: -2,
                  }}
                />
              );
            })}
          </div>
        </div>

        {(loading || pdfLoading) && (
          <div style={{ textAlign: "center", padding: 12, color: "rgba(255,255,255,0.6)", fontSize: 14, background: "#0a0a0a" }}>
            {pdfLoading ? "📄 Analizzo il PDF e preparo la bibbia..." : "Carico personaggi..."}
          </div>
        )}
      </div>
    );
  }

  // ── Step 2: scegli personaggi ──
  const meta = GENRE_META[genre] || { emoji: "🎲", label: genre, gradient: "135deg, #1a1a1a, #2a2a2a" };
  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", padding: "40px 24px", background: "var(--bg)" }}>
      {showBuilder && (
        <CharacterBuilderModal
          genre={genre}
          archetypes={pool}
          onAdd={p => { setPool(prev => [...prev, p]); setShowBuilder(false); }}
          onClose={() => setShowBuilder(false)}
        />
      )}

      {/* header genere */}
      <div style={{
        width: "100%", maxWidth: 720, borderRadius: 16, marginBottom: 32, overflow: "hidden",
        background: `linear-gradient(${meta.gradient})`, boxShadow: "0 4px 24px rgba(0,0,0,0.5)",
      }}>
        <div style={{ padding: "28px 32px", display: "flex", alignItems: "center", gap: 18 }}>
          <span style={{ fontSize: 48 }}>{meta.emoji}</span>
          <div>
            <div style={{ fontSize: 22, fontWeight: 900, color: "#fff" }}>{meta.label}</div>
            <div style={{ fontSize: 14, color: "rgba(255,255,255,0.6)", marginTop: 2 }}>{meta.sub}</div>
          </div>
          <button onClick={() => setStep("genre")} style={{
            marginLeft: "auto", padding: "7px 16px", borderRadius: 8,
            border: "1px solid rgba(255,255,255,0.2)", background: "rgba(255,255,255,0.08)",
            color: "rgba(255,255,255,0.7)", cursor: "pointer", fontSize: 13,
          }}>← Cambia</button>
        </div>
      </div>

      <div style={{ width: "100%", maxWidth: 720 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
          <div style={{ fontWeight: 700, fontSize: 15, color: "var(--text-h)" }}>
            Scegli il tuo gruppo (1–4 personaggi)
          </div>
          <button onClick={() => setShowBuilder(true)} style={{
            padding: "7px 16px", borderRadius: 8, border: "1px solid var(--accent)",
            background: "var(--accent-bg)", color: "var(--accent)",
            cursor: "pointer", fontSize: 13, fontWeight: 700,
          }}>+ Crea personaggio</button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, marginBottom: 28 }}>
          {pool.map(p => {
            const sel = selected.includes(p.id);
            const topSkills = Object.entries(p.skills || {}).sort((a,b) => b[1]-a[1]).slice(0,2);
            const av = avatars[p.id];
            const avLoading = avatarLoading[p.id];
            return (
              <div key={p.id} style={{
                borderRadius: 10, overflow: "hidden",
                border: sel ? "2px solid var(--accent)" : "1px solid var(--border)",
                background: sel ? "var(--accent-bg)" : "var(--code-bg)",
                transition: "all 0.15s", position: "relative",
              }}>
                {/* card body */}
                <div style={{ padding: "8px 9px 9px", cursor: "pointer" }} onClick={() => toggleSelect(p.id)}>
                  {/* avatar cerchio + bottoni */}
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                    <div style={{ position: "relative", flexShrink: 0 }}>
                      <AvatarCircle src={av} size={56} fallback="🧑" />
                      {avLoading && (
                        <div style={{ position: "absolute", inset: 0, borderRadius: "50%", background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 9, color: "#fff", textAlign: "center", padding: 2 }}>
                          {avLoading}
                        </div>
                      )}
                      {sel && <div style={{ position: "absolute", top: -2, right: -2, fontSize: 13, textShadow: "0 1px 4px rgba(0,0,0,0.9)", lineHeight: 1 }}>✓</div>}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 800, fontSize: 12, color: "var(--text-h)", marginBottom: 1 }}>
                        <EditableName
                          name={p.name}
                          onRename={newName => handleRenameInPool(p.id, newName)}
                          style={{ fontWeight: 800, fontSize: 12 }}
                        />
                      </div>
                      <div style={{ fontSize: 10, color: "var(--accent)", fontWeight: 600, marginBottom: 3 }}>{p.role}</div>
                      <div style={{ display: "flex", gap: 4 }}>
                        <button onClick={e => { e.stopPropagation(); handleAvatarGenerate(p); }}
                          disabled={!!avLoading}
                          style={{ background: "rgba(0,0,0,0.4)", borderRadius: 4, padding: "2px 6px", fontSize: 10, color: "#fff", cursor: "pointer", border: "1px solid rgba(255,255,255,0.12)" }}>🎨</button>
                        <label onClick={e => e.stopPropagation()}
                          style={{ background: "rgba(0,0,0,0.4)", borderRadius: 4, padding: "2px 6px", fontSize: 10, color: "#fff", cursor: "pointer", border: "1px solid rgba(255,255,255,0.12)" }}>
                          📷<input type="file" accept="image/*" style={{ display: "none" }}
                            onChange={e => e.target.files[0] && handleAvatarUpload(p, e.target.files[0])} />
                        </label>
                      </div>
                    </div>
                  </div>
                  <StatBar stats={p.stats} />
                  {topSkills.length > 0 && (
                    <div style={{ marginTop: 4, display: "flex", gap: 4, flexWrap: "wrap" }}>
                      {topSkills.map(([sk, lv]) => (
                        <span key={sk} style={{ fontSize: 10, background: "var(--bg)", border: "1px solid var(--border)", borderRadius: 4, padding: "1px 4px", color: "var(--text)" }}>
                          {sk} {lv}
                        </span>
                      ))}
                    </div>
                  )}
                  {p.advantages?.length > 0 && (
                    <div style={{ fontSize: 10, marginTop: 3, color: "var(--accent)", opacity: 0.8, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      ★ {p.advantages.slice(0,2).join(", ")}
                    </div>
                  )}
                  {p.disadvantages?.length > 0 && (
                    <div style={{ fontSize: 10, marginTop: 1, color: "#f87171", opacity: 0.8, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      ✖ {p.disadvantages.slice(0,2).join(", ")}
                    </div>
                  )}
                  {p.motivation && (
                    <div style={{ fontSize: 10, marginTop: 3, color: "var(--accent)", fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      🎯 {p.motivation}
                    </div>
                  )}
                  {p.backstory && (
                    <div style={{ fontSize: 10, marginTop: 4, color: "var(--text)", lineHeight: 1.4, opacity: 0.75, fontStyle: "italic" }}>
                      {p.backstory}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        <button onClick={handleStart} disabled={selected.length === 0 || loading} style={{
          width: "100%", padding: "14px 0", borderRadius: 12, border: "none",
          background: selected.length > 0 ? "var(--accent)" : "var(--border)",
          color: "#fff", fontWeight: 800, fontSize: 17, cursor: selected.length > 0 ? "pointer" : "not-allowed",
          transition: "opacity 0.15s",
        }}>
          {loading ? "Avvio storia..." : selected.length > 0 ? `⚔️ Inizia con ${selected.length} personagg${selected.length === 1 ? "io" : "i"}` : "Seleziona almeno un personaggio"}
        </button>
      </div>
    </div>
  );
}

// ─── Chat message components ───────────────────────────────────────────────

// Pulisce testo da eventuali parentesi di roll residue
function stripRollText(text) {
  return text
    .replace(/\s*\(Tiro su [^)]+\)/gi, "")
    .replace(/\s*\[Tiro su [^\]]+\]/gi, "")
    .replace(/\s*\(Roll[^)]+\)/gi, "")
    .replace(/\s*\(3d6[^)]+\)/gi, "")
    .trim();
}

function MasterMessage({ msg }) {
  const rawText = stripRollText(msg.text || "");
  // Normalizza varianti del marker che Claude può generare
  const normalizedText = rawText
    .replace(/\{\s*\{\s*ROLL\s*\}\s*\}/g, "{ROLL}")  // {{ROLL}}
    .replace(/\[\s*ROLL\s*\]/g, "{ROLL}");             // [ROLL]
  const MARKER = "{ROLL}";
  const parts = normalizedText.split(MARKER);
  const hasMarker = parts.length > 1;
  const isCombatNarration = msg.isCombatNarration;

  if (isCombatNarration) {
    return (
      <div style={{
        display: "flex", gap: 10, alignItems: "flex-start", marginBottom: 10, marginTop: 2,
        paddingLeft: 50,
      }}>
        <div style={{
          flex: 1, borderLeft: "2px solid rgba(239,68,68,0.5)",
          paddingLeft: 12, fontSize: 14, lineHeight: 1.55,
          color: "rgba(255,255,255,0.75)", fontStyle: "italic",
        }}>
          {normalizedText}
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", gap: 12, alignItems: "flex-start", marginBottom: 20 }}>
      <div style={{
        width: 38, height: 38, borderRadius: "50%", background: "linear-gradient(135deg,#7c3aed,#a855f7)",
        display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, flexShrink: 0,
      }}>🎲</div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: "var(--accent)", marginBottom: 4, textTransform: "uppercase", letterSpacing: 1 }}>Master</div>
        <div style={{
          background: "var(--code-bg)", borderRadius: "0 12px 12px 12px",
          padding: "12px 16px", fontSize: 15, lineHeight: 1.6, color: "var(--text-h)",
        }}>
          {hasMarker ? (
            <>
              {parts[0] && <span style={{ whiteSpace: "pre-wrap" }}>{parts[0].trim()}</span>}
              {(msg.roll || msg.roll_details) && <div style={{ margin: "10px 0" }}><DiceResult roll={msg.roll} rollDetails={msg.roll_details} /></div>}
              {parts.slice(1).join("").trim() && <span style={{ whiteSpace: "pre-wrap" }}>{parts.slice(1).join("").trim()}</span>}
            </>
          ) : (
            <>
              {msg.roll && <div style={{ marginBottom: 10 }}><DiceResult roll={msg.roll} /></div>}
              <span style={{ whiteSpace: "pre-wrap" }}>{normalizedText}</span>
            </>
          )}
        </div>
        {msg.image && (
          <div style={{ marginTop: 8, borderRadius: "0 12px 12px 12px", overflow: "hidden" }}>
            <img
              src={`data:image/jpeg;base64,${msg.image}`}
              alt="Scena"
              style={{ width: "100%", display: "block", objectFit: "cover", maxHeight: 300 }}
            />
          </div>
        )}
        {msg.imageLoading && (
          <div style={{ marginTop: 8, fontSize: 12, color: "var(--text)", opacity: 0.5 }}>🖼 Generazione immagine...</div>
        )}
      </div>
    </div>
  );
}

function PlayerMessage({ msg }) {
  return (
    <div style={{ display: "flex", gap: 12, alignItems: "flex-start", justifyContent: "flex-end", marginBottom: 20 }}>
      <div style={{ flex: 1, maxWidth: 480, textAlign: "right" }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text)", marginBottom: 4, textTransform: "uppercase", letterSpacing: 1 }}>
          {msg.name}
        </div>
        <div style={{
          background: "var(--accent)", color: "#fff",
          borderRadius: "12px 0 12px 12px",
          padding: "12px 16px", fontSize: 15, lineHeight: 1.6,
          display: "inline-block", textAlign: "left",
        }}>
          {msg.text}
        </div>
      </div>
      <div style={{
        width: 38, height: 38, borderRadius: "50%", background: "var(--border)",
        display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, flexShrink: 0,
      }}>🧑</div>
    </div>
  );
}

function CombatDie({ roll, target, success, critical }) {
  const color = critical ? "#fbbf24" : success ? "#4ade80" : "#ef4444";
  const resultLabel = critical ? "CRITICO" : success ? "✓" : "✗";
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      background: `${color}18`, border: `1px solid ${color}55`,
      borderRadius: 6, padding: "3px 9px", fontSize: 12, fontWeight: 700,
    }}>
      <span style={{ fontSize: 14 }}>🎲</span>
      <span style={{ color: "var(--text-h)" }}>{roll}</span>
      <span style={{ color: "rgba(255,255,255,0.25)" }}>≤</span>
      <span style={{ color: "var(--text-h)" }}>{target}</span>
      <span style={{ color, marginLeft: 2 }}>{resultLabel}</span>
    </span>
  );
}

function CombatLogMessage({ msg }) {
  const log = msg.combat_log;
  if (!log) return null;
  const r = log.result || {};
  const move = log.tactical_move;

  return (
    <div style={{
      marginBottom: 16, borderRadius: 10,
      background: "rgba(239,68,68,0.05)", border: "1px solid rgba(239,68,68,0.18)",
      padding: "10px 14px",
    }}>
      {/* header: attaccante → bersaglio + skill badge */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
        <span style={{ fontSize: 13 }}>⚔</span>
        <span style={{ fontWeight: 800, color: "var(--text-h)", fontSize: 13 }}>{log.attacker}</span>
        <span style={{ color: "var(--text)", opacity: 0.4 }}>→</span>
        <span style={{ fontWeight: 800, color: "#f87171", fontSize: 13 }}>{log.target}</span>
        <span style={{ marginLeft: "auto" }}><SkillBadge skill={log.skill} level={log.skill_level} /></span>
      </div>

      {move && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", fontSize: 12, color: "var(--text)", opacity: 0.85 }}>
          <Badge icon="👣" label="Movimento tattico" color="#f59e0b" size="sm" />
          <span>
            {log.attacker} si avvicina a {log.target}
            {move.distance_after != null ? ` (distanza ${move.distance_after})` : ""}.
          </span>
        </div>
      )}

      {/* tiri dado */}
      {!move && <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 8, alignItems: "flex-end" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
          <span style={{ fontSize: 9, color: "var(--text)", opacity: 0.45, textTransform: "uppercase", letterSpacing: 1 }}>Attacco</span>
          <CombatDie roll={log.attack_roll} target={log.skill_level} success={r.hit} critical={r.attacker_critical} />
        </div>
        {log.defense_type && (r.hit || r.defended) && (
          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <span style={{ fontSize: 9, color: "var(--text)", opacity: 0.45, textTransform: "uppercase", letterSpacing: 1 }}>
              <DefenseBadge type={log.defense_type} size="sm" />
            </span>
            <CombatDie
              roll={log.defense_roll ?? "—"} target={log.defense_value ?? "—"}
              success={r.defended} critical={r.defense_critical_fail}
            />
          </div>
        )}
        {/* esito narrativo */}
        <span style={{ marginLeft: 4 }}>
          <NarrativeHintBadge hint={r.narrative_hint} size="sm" />
        </span>
      </div>}

      {/* danno */}
      {r.hit && !r.defended && (
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 6 }}>
          <DamageTypeBadge type={log.damage_type} />
          <span style={{ fontSize: 12, color: "var(--text)", opacity: 0.5 }}>{log.damage_formula}:</span>
          <span style={{ fontWeight: 700, color: "var(--text-h)", fontSize: 13 }}>{r.raw_damage}</span>
          {r.dr_absorbed > 0 && <>
            <span style={{ fontSize: 11, color: "var(--text)", opacity: 0.4 }}>−</span>
            <Badge icon="🛡" label={`${r.dr_absorbed} DR`} color="#94a3b8" size="sm" />
          </>}
          <span style={{ fontSize: 11, color: "var(--text)", opacity: 0.4 }}>=</span>
          <span style={{ fontWeight: 900, color: "#f87171", fontSize: 15 }}>{r.net_damage} PF</span>
          <WoundBadge threshold={r.wound_threshold} size="md" />
        </div>
      )}

      {/* difesa riuscita */}
      {r.defended && (
        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
          <DefenseBadge type={log.defense_type} size="md" />
          <span style={{ color: "#4ade80", fontWeight: 700 }}>riuscita</span>
          <span style={{ color: "var(--text)", opacity: 0.5 }}>— nessun danno (margine +{r.defense_margin})</span>
        </div>
      )}

      {/* condizioni secondarie GURPS */}
      {r.hit && !r.defended && (() => {
        const conds = [];
        if (r.shock_applied > 0)
          conds.push(<Badge key="shock" icon="⚡" label={`Shock −${r.shock_applied}`} color="#f59e0b" size="sm" />);
        if (r.major_wound)
          conds.push(<Badge key="mw" icon="🩸" label={r.major_wound_check_passed ? "Ferita Grave (SA ok)" : "Ferita Grave → STORDITO"} color={r.major_wound_check_passed ? "#f87171" : "#dc2626"} size="sm" />);
        if (r.knockdown)
          conds.push(<Badge key="kd" icon="💥" label={r.knockdown_check_passed ? "Caduta (SA ok)" : "Caduta → A TERRA"} color={r.knockdown_check_passed ? "#f97316" : "#ea580c"} size="sm" />);
        if (r.death_check)
          conds.push(<Badge key="dc" icon="💀" label={r.death_check_passed ? "Tiro morte (SA ok)" : "Tiro morte FALLITO"} color={r.death_check_passed ? "#a3a3a3" : "#7f1d1d"} size="sm" />);
        if (r.fp_cost > 0)
          conds.push(<Badge key="fp" icon="🔋" label={`−${r.fp_cost} PF`} color="#6366f1" size="sm" />);
        if (conds.length === 0) return null;
        return <div style={{ marginTop: 6, display: "flex", flexWrap: "wrap", gap: 6 }}>{conds}</div>;
      })()}

      {/* All-Out Attack / Defense tags */}
      {(log.action_type === "all_out_attack" || log.defense_action_type === "all_out_defense") && (
        <div style={{ marginTop: 5, display: "flex", gap: 6, flexWrap: "wrap" }}>
          {log.action_type === "all_out_attack" && <Badge icon="⚔" label="Attacco Totale +4" color="#dc2626" size="sm" />}
          {log.defense_action_type === "all_out_defense" && <Badge icon="🛡" label="Difesa Totale +2" color="#2563eb" size="sm" />}
        </div>
      )}

      {/* vantaggi/svantaggi attivi */}
      {((log.advantages_attacker?.length > 0) || (log.advantages_active?.length > 0)) && (
        <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 4, alignItems: "center" }}>
          <span style={{ fontSize: 10, color: "var(--text)", opacity: 0.4 }}>att:</span>
          <AdvantagesBadges list={log.advantages_attacker || log.advantages_active} />
        </div>
      )}
      {log.advantages_defender?.length > 0 && (
        <div style={{ marginTop: 4, display: "flex", flexWrap: "wrap", gap: 4, alignItems: "center" }}>
          <span style={{ fontSize: 10, color: "var(--text)", opacity: 0.4 }}>dif:</span>
          <AdvantagesBadges list={log.advantages_defender} />
        </div>
      )}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div style={{ display: "flex", gap: 12, alignItems: "flex-start", marginBottom: 20 }}>
      <div style={{
        width: 38, height: 38, borderRadius: "50%", background: "linear-gradient(135deg,#7c3aed,#a855f7)",
        display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, flexShrink: 0,
      }}>🎲</div>
      <div style={{
        background: "var(--code-bg)", borderRadius: "0 12px 12px 12px",
        padding: "14px 18px", display: "flex", gap: 5, alignItems: "center",
      }}>
        {[0, 1, 2].map(i => (
          <span key={i} style={{
            width: 8, height: 8, borderRadius: "50%", background: "var(--accent)",
            animation: "bounce 1s infinite", animationDelay: `${i * 0.2}s`,
          }} />
        ))}
      </div>
    </div>
  );
}

// ─── Options bar ───────────────────────────────────────────────────────────

function OptionsBar({ options, players, onChoose }) {
  // Colori per distinguere i personaggi nelle opzioni
  const PLAYER_COLORS = ["#818cf8", "#34d399", "#f59e0b", "#f472b6"];
  const playerColorMap = {};
  players.forEach((p, i) => { playerColorMap[p.id] = PLAYER_COLORS[i % PLAYER_COLORS.length]; });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {options.map((opt, i) => {
        const player = players.find(p => p.id === opt.player_id) || players[0];
        const isCustom = !opt.skill;
        const playerColor = playerColorMap[player?.id] || "var(--accent)";
        const multiPlayer = players.length > 1;
        return (
          <button key={i} onClick={() => onChoose(opt)} style={{
            padding: "10px 16px", borderRadius: 10, border: "1px solid var(--border)",
            background: isCustom ? "var(--bg)" : "var(--code-bg)",
            color: "var(--text-h)", cursor: "pointer", textAlign: "left",
            fontSize: 14, lineHeight: 1.4, transition: "all 0.15s",
            borderLeft: `3px solid ${isCustom ? "var(--accent)" : playerColor}`,
          }}
            onMouseEnter={e => e.currentTarget.style.borderColor = playerColor}
            onMouseLeave={e => e.currentTarget.style.borderColor = isCustom ? "var(--accent)" : "var(--border)"}
          >
            {multiPlayer && player && (
              <span style={{ fontSize: 11, fontWeight: 700, color: playerColor, marginRight: 6, textTransform: "uppercase", letterSpacing: 0.5 }}>
                {player.name}
              </span>
            )}
            <span style={{ fontWeight: 600 }}>{opt.text}</span>
            {opt.skill && (
              <span style={{ marginLeft: 8 }}>
                <SkillBadge skill={opt.skill} level={opt.skill_level} size="sm" />
              </span>
            )}
            {isCustom && (
              <span style={{ fontSize: 12, color: "var(--accent)", marginLeft: 8 }}>✏️ scrivi tu</span>
            )}
          </button>
        );
      })}
    </div>
  );
}

// ─── Loading progress bar ──────────────────────────────────────────────────

function LoadingProgress({ steps, icon = "📖", title }) {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const timers = steps.map((s, i) =>
      setTimeout(() => setPhase(i), s.at)
    );
    return () => timers.forEach(clearTimeout);
  }, []);

  const current = steps[phase] || steps[steps.length - 1];
  const pct = Math.round(((phase + 1) / steps.length) * 100);

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 24, background: "var(--bg)", padding: "0 32px" }}>
      <div style={{ fontSize: 56 }}>{icon}</div>
      <div style={{ fontSize: 20, fontWeight: 800, color: "var(--text-h)", textAlign: "center" }}>{title}</div>

      {/* barra progresso */}
      <div style={{ width: "100%", maxWidth: 420 }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--text)", marginBottom: 8 }}>
          <span style={{ fontStyle: "italic" }}>{current.label}</span>
          <span style={{ fontWeight: 700, color: "var(--accent)" }}>{pct}%</span>
        </div>
        <div style={{ height: 6, borderRadius: 6, background: "var(--border)", overflow: "hidden" }}>
          <div style={{
            height: "100%", borderRadius: 6,
            background: "linear-gradient(90deg, #7c3aed, #c084fc)",
            width: `${pct}%`,
            transition: "width 0.8s ease",
          }} />
        </div>
      </div>

      {/* step pills */}
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", justifyContent: "center", maxWidth: 480 }}>
        {steps.map((s, i) => (
          <span key={i} style={{
            fontSize: 11, padding: "3px 10px", borderRadius: 20,
            background: i <= phase ? "var(--accent-bg)" : "var(--code-bg)",
            border: `1px solid ${i <= phase ? "var(--accent-border)" : "var(--border)"}`,
            color: i <= phase ? "var(--accent)" : "var(--text)",
            transition: "all 0.4s",
          }}>{s.pill}</span>
        ))}
      </div>
    </div>
  );
}

// ─── Side Panel ────────────────────────────────────────────────────────────

function AvatarCircle({ src, size = 32, fallback = "👤" }) {
  const [err, setErr] = React.useState(false);
  if (!src || err) return (
    <div style={{ width: size, height: size, borderRadius: "50%", background: "var(--border)", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: size * 0.45 }}>
      {fallback}
    </div>
  );
  return (
    <img
      src={`data:image/png;base64,${src}`}
      onError={e => { e.currentTarget.src = `data:image/jpeg;base64,${src}`; setErr(false); }}
      style={{ width: size, height: size, borderRadius: "50%", objectFit: "cover", flexShrink: 0 }}
    />
  );
}

function SidePanel({ adventure, gameState, players, avatars, npcAvatars, onClose }) {
  const [tab, setTab] = useState("clues");
  const [expandedNpc, setExpandedNpc] = useState(null);
  const [expandedPlayer, setExpandedPlayer] = useState(null);
  const clues = adventure?.clues || [];
  const advNpcs = adventure?.npcs || [];
  const worldNpcs = gameState?.world_npcs || [];
  // Merge: world_npcs prende il sopravvento per nomi corrispondenti
  const npcMap = new Map();
  advNpcs.forEach(n => npcMap.set(n.name?.toLowerCase(), { ...n, _source: "adv" }));
  worldNpcs.forEach(n => {
    const key = n.name?.toLowerCase();
    const existing = npcMap.get(key);
    npcMap.set(key, existing ? { ...existing, ...n, _source: "world" } : { ...n, _source: "world" });
  });
  const npcs = Array.from(npcMap.values());
  const threads = gameState?.open_threads || [];
  const threatLevel = gameState?.threat_level || 0;
  const threatMax = adventure?.threat_max_turns || 8;
  const threatPct = Math.round(threatLevel / Math.max(threatMax, 1) * 100);
  const npcStatuses = gameState?.npc_statuses || {};

  const tabStyle = (t) => ({
    flex: 1, padding: "8px 4px", border: "none", cursor: "pointer", fontSize: 12, fontWeight: 700,
    borderBottom: tab === t ? "2px solid var(--accent)" : "2px solid transparent",
    background: "none", color: tab === t ? "var(--accent)" : "var(--text)",
  });

  const threatColor = threatPct < 40 ? "#4ade80" : threatPct < 70 ? "#facc15" : "#f87171";

  return (
    <div style={{
      width: 280, flexShrink: 0, borderLeft: "1px solid var(--border)",
      display: "flex", flexDirection: "column", background: "var(--bg)",
    }}>
      <div style={{ padding: "12px 14px 8px", display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 6 }}>
        <div style={{ fontSize: 13, fontWeight: 800, color: "var(--text-h)", lineHeight: 1.4 }}>
          {adventure?.title || "Avventura"}
        </div>
        <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text)", fontSize: 18, flexShrink: 0, lineHeight: 1, marginTop: 1 }}>×</button>
      </div>

      {/* minaccia */}
      <div style={{ padding: "10px 14px", borderBottom: "1px solid var(--border)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", fontSize: 11, marginBottom: 4, gap: 6 }}>
          <span style={{ color: "var(--text)", fontWeight: 600, lineHeight: 1.4 }}>⚠ {adventure?.threat_description || "Minaccia"}</span>
          <span style={{ color: threatColor, fontWeight: 700, flexShrink: 0 }}>{threatPct}%</span>
        </div>
        <div style={{ height: 5, borderRadius: 3, background: "var(--border)", overflow: "hidden" }}>
          <div style={{ height: "100%", width: `${threatPct}%`, background: threatColor, transition: "width 0.5s, background 0.5s" }} />
        </div>
      </div>

      {/* tabs */}
      <div style={{ display: "flex", borderBottom: "1px solid var(--border)" }}>
        <button style={tabStyle("clues")} onClick={() => setTab("clues")}>🔍 Indizi</button>
        <button style={tabStyle("npcs")} onClick={() => setTab("npcs")}>👤 PNG</button>
        <button style={tabStyle("players")} onClick={() => setTab("players")}>🧑‍🤝‍🧑 Gruppo</button>
        <button style={tabStyle("threads")} onClick={() => setTab("threads")}>🧵 Fili</button>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "10px 14px" }}>
        {tab === "clues" && (
          <div>
            {/* Obiettivo sempre visibile */}
            {adventure?.win_condition && (
              <div style={{
                padding: "8px 10px", borderRadius: 8, marginBottom: 10,
                background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.4)",
              }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: "var(--accent)", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 4 }}>🎯 Obiettivo</div>
                <div style={{ fontSize: 12, color: "var(--text-h)", lineHeight: 1.45 }}>{adventure.win_condition}</div>
              </div>
            )}

            {/* Banner "pronti a concludere" quando tutti gli indizi sono trovati */}
            {clues.length > 0 && clues.every(c => gameState?.clues_found?.includes(c.id)) && (
              <div style={{
                padding: "8px 10px", borderRadius: 8, marginBottom: 10,
                background: "rgba(74,222,128,0.12)", border: "1px solid rgba(74,222,128,0.5)",
              }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: "#4ade80", marginBottom: 3 }}>✅ Tutti gli indizi trovati</div>
                <div style={{ fontSize: 11, color: "var(--text)", lineHeight: 1.4 }}>
                  Hai tutto quello che ti serve. Descrivi la tua azione finale per risolvere il caso e concludere l'avventura.
                </div>
              </div>
            )}

            {/* Contatore indizi */}
            <div style={{ fontSize: 11, color: "var(--text)", opacity: 0.6, marginBottom: 8 }}>
              {gameState?.clues_found?.length || 0} / {clues.length} indizi trovati
            </div>

            {clues.map(c => {
              const found = gameState?.clues_found?.includes(c.id);
              return (
                <div key={c.id} style={{
                  padding: "8px 10px", borderRadius: 8, marginBottom: 6,
                  background: found ? "rgba(74,222,128,0.08)" : "var(--code-bg)",
                  border: `1px solid ${found ? "rgba(74,222,128,0.3)" : "var(--border)"}`,
                  opacity: found ? 1 : 0.5,
                }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: found ? "#4ade80" : "var(--text)", marginBottom: 2 }}>
                    {found ? "🔍" : "⬜"} {c.text}
                  </div>
                  {found && c.reveals && <div style={{ fontSize: 11, color: "#4ade80", fontStyle: "italic", marginBottom: 2 }}>↳ {c.reveals}</div>}
                  {c.location && <div style={{ fontSize: 11, color: "var(--text)", opacity: found ? 0.5 : 0.7 }}>📍 {c.location}</div>}
                </div>
              );
            })}
          </div>
        )}

        {tab === "npcs" && (
          <div>
            {npcs.length === 0 && <div style={{ fontSize: 12, color: "var(--text)", opacity: 0.5, textAlign: "center", marginTop: 20 }}>Nessun PNG</div>}
            {npcs.map(npc => {
              const st = npcStatuses[npc.id] || {};
              const status = st.status || npc.status || "alive";
              const attitude = st.attitude || npc.attitude || "neutral";
              const hasGurps = npc.gurps_fo != null;
              const isExpanded = expandedNpc === (npc.id || npc.name);
              const threatColor = npc.threat_to_player >= 3 ? "#ef4444" : npc.threat_to_player >= 2 ? "#f97316" : npc.threat_to_player >= 1 ? "#facc15" : "#4ade80";
              return (
                <div key={npc.id || npc.name} style={{
                  borderRadius: 8, marginBottom: 6, background: "var(--code-bg)",
                  border: `1px solid ${hasGurps ? threatColor + "55" : "var(--border)"}`,
                  overflow: "hidden",
                }}>
                  <div
                    onClick={() => hasGurps && setExpandedNpc(isExpanded ? null : (npc.id || npc.name))}
                    style={{ padding: "8px 10px", cursor: hasGurps ? "pointer" : "default" }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                      <AvatarCircle src={(npcAvatars || {})[npc.name]} size={28} fallback="👤" />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-h)" }}>
                            {npc.name}
                            {hasGurps && <span style={{ fontSize: 10, color: threatColor, marginLeft: 5, fontWeight: 400 }}>★</span>}
                          </span>
                          <div style={{ display: "flex", gap: 4 }}>
                            <NpcStatusBadge status={status} size="sm" />
                            <NpcAttitudeBadge attitude={attitude} size="sm" />
                          </div>
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text)" }}>{npc.role}</div>
                      </div>
                    </div>
                    {npc.description && <div style={{ fontSize: 11, color: "var(--text)", opacity: 0.7, marginTop: 2, lineHeight: 1.4 }}>{npc.description}</div>}
                    {st.location && <div style={{ fontSize: 11, color: "var(--text)", opacity: 0.6, marginTop: 2 }}>📍 {st.location}</div>}
                  </div>
                  {hasGurps && isExpanded && (
                    <div style={{ padding: "8px 10px", borderTop: `1px solid ${threatColor}33`, background: "rgba(0,0,0,0.15)" }}>
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 6 }}>
                        {[["FO", npc.gurps_fo], ["DE", npc.gurps_de], ["IN", npc.gurps_in], ["SA", npc.gurps_sa]].map(([label, val]) => (
                          <span key={label} style={{ fontSize: 11, background: "var(--bg)", padding: "2px 7px", borderRadius: 5, border: "1px solid var(--border)" }}>
                            <b style={{ color: "var(--text-h)" }}>{label}</b> {val}
                          </span>
                        ))}
                        {npc.combat_hp != null && (
                          <span style={{ fontSize: 11, background: "var(--bg)", padding: "2px 7px", borderRadius: 5, border: "1px solid #ef444455" }}>
                            <b style={{ color: "#f87171" }}>PF</b> {npc.combat_hp}
                          </span>
                        )}
                        {npc.combat_dr > 0 && (
                          <span style={{ fontSize: 11, background: "var(--bg)", padding: "2px 7px", borderRadius: 5, border: "1px solid #60a5fa55" }}>
                            <b style={{ color: "#60a5fa" }}>DR</b> {npc.combat_dr}
                          </span>
                        )}
                      </div>
                      {npc.gurps_skills && Object.keys(npc.gurps_skills).length > 0 && (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 6 }}>
                          {Object.entries(npc.gurps_skills).map(([sk, lv]) => (
                            <span key={sk} style={{ fontSize: 10, padding: "1px 6px", borderRadius: 4, background: "rgba(99,102,241,0.18)", color: "#a78bfa" }}>
                              {SKILL_META[sk]?.label || sk} {lv}
                            </span>
                          ))}
                        </div>
                      )}
                      {(npc.gurps_advantages?.length > 0 || npc.gurps_disadvantages?.length > 0) && (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                          {(npc.gurps_advantages || []).map(a => (
                            <span key={a} style={{ fontSize: 10, padding: "1px 6px", borderRadius: 4, background: "rgba(74,222,128,0.15)", color: "#4ade80" }}>{a}</span>
                          ))}
                          {(npc.gurps_disadvantages || []).map(d => (
                            <span key={d} style={{ fontSize: 10, padding: "1px 6px", borderRadius: 4, background: "rgba(239,68,68,0.15)", color: "#f87171" }}>{d}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {tab === "players" && (
          <div>
            {(!players || players.length === 0) && (
              <div style={{ fontSize: 12, color: "var(--text)", opacity: 0.5, textAlign: "center", marginTop: 20 }}>Nessun personaggio</div>
            )}
            {(players || []).map(p => {
              const liveP = gameState?.players?.find(x => x.id === p.id) || p;
              const isExpanded = expandedPlayer === p.id;
              const hpPct = Math.max(0, Math.round((liveP.hp / liveP.max_hp) * 100));
              const hpColor = hpPct > 60 ? "#4ade80" : hpPct > 30 ? "#facc15" : "#ef4444";
              const acquiredSkills = Object.entries(liveP.skills || {}).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]);
              return (
                <div key={p.id} style={{
                  borderRadius: 8, marginBottom: 8, background: "var(--code-bg)",
                  border: "1px solid var(--accent)44", overflow: "hidden",
                }}>
                  <div onClick={() => setExpandedPlayer(isExpanded ? null : p.id)}
                    style={{ padding: "8px 10px", cursor: "pointer" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                      <AvatarCircle src={(avatars || {})[p.id]} size={32} fallback="🧑" />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-h)" }}>{liveP.name}</span>
                          <span style={{ fontSize: 11, color: "var(--accent)", opacity: 0.8 }}>{liveP.role}</span>
                        </div>
                        {/* HP bar */}
                        <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 4 }}>
                          <div style={{ flex: 1, height: 5, borderRadius: 3, background: "var(--border)", overflow: "hidden" }}>
                            <div style={{ height: "100%", width: `${hpPct}%`, background: hpColor, transition: "width 0.4s" }} />
                          </div>
                          <span style={{ fontSize: 11, color: hpColor, fontWeight: 700, minWidth: 36, textAlign: "right" }}>
                            ❤️ {liveP.hp}/{liveP.max_hp}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                  {isExpanded && (
                    <div style={{ padding: "8px 10px", borderTop: "1px solid var(--accent)22", background: "rgba(0,0,0,0.15)" }}>
                      {/* attributi */}
                      <div style={{ display: "flex", gap: 5, flexWrap: "wrap", marginBottom: 8 }}>
                        {[["FO", liveP.stats?.forza], ["DE", liveP.stats?.agilita], ["IN", liveP.stats?.intelligenza], ["SA", liveP.stats?.empatia]].map(([label, val]) => (
                          <span key={label} style={{ fontSize: 11, background: "var(--bg)", padding: "2px 8px", borderRadius: 5, border: "1px solid var(--border)" }}>
                            <b style={{ color: "var(--text-h)" }}>{label}</b> {val ?? "—"}
                          </span>
                        ))}
                        <span style={{ fontSize: 11, background: "var(--bg)", padding: "2px 8px", borderRadius: 5, border: "1px solid #ef444455" }}>
                          <b style={{ color: "#f87171" }}>PF</b> {liveP.max_hp}
                        </span>
                        {liveP.dr > 0 && (
                          <span style={{ fontSize: 11, background: "var(--bg)", padding: "2px 8px", borderRadius: 5, border: "1px solid #60a5fa55" }}>
                            <b style={{ color: "#60a5fa" }}>DR</b> {liveP.dr}
                          </span>
                        )}
                      </div>
                      {/* skill acquisite */}
                      {acquiredSkills.length > 0 && (
                        <div style={{ marginBottom: 7 }}>
                          <div style={{ fontSize: 10, fontWeight: 600, color: "var(--text)", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 4 }}>Skill</div>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: 3 }}>
                            {acquiredSkills.map(([sk, lv]) => (
                              <span key={sk} style={{ fontSize: 10, padding: "1px 6px", borderRadius: 4, background: "rgba(99,102,241,0.18)", color: "#a78bfa" }}>
                                {SKILL_META[sk]?.label || sk} {lv}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {/* vantaggi / svantaggi */}
                      {((liveP.advantages?.length > 0) || (liveP.disadvantages?.length > 0)) && (
                        <div style={{ marginBottom: 7 }}>
                          <div style={{ fontSize: 10, fontWeight: 600, color: "var(--text)", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 4 }}>Tratti</div>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: 3 }}>
                            {(liveP.advantages || []).map(a => (
                              <span key={a} style={{ fontSize: 10, padding: "1px 6px", borderRadius: 4, background: "rgba(74,222,128,0.15)", color: "#4ade80" }}>★ {a}</span>
                            ))}
                            {(liveP.disadvantages || []).map(d => (
                              <span key={d} style={{ fontSize: 10, padding: "1px 6px", borderRadius: 4, background: "rgba(239,68,68,0.15)", color: "#f87171" }}>✖ {d}</span>
                            ))}
                          </div>
                        </div>
                      )}
                      {/* backstory / motivazione */}
                      {liveP.backstory && (
                        <div style={{ marginBottom: 6 }}>
                          <div style={{ fontSize: 10, fontWeight: 600, color: "var(--text)", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 3 }}>Storia</div>
                          <div style={{ fontSize: 11, color: "var(--text)", lineHeight: 1.45, fontStyle: "italic", opacity: 0.85 }}>{liveP.backstory}</div>
                        </div>
                      )}
                      {liveP.motivation && (
                        <div>
                          <div style={{ fontSize: 10, fontWeight: 600, color: "var(--text)", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 3 }}>Obiettivo</div>
                          <div style={{ fontSize: 11, color: "#a78bfa", lineHeight: 1.45 }}>{liveP.motivation}</div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {tab === "threads" && (
          <div>
            {threads.length === 0 && <div style={{ fontSize: 12, color: "var(--text)", opacity: 0.5, textAlign: "center", marginTop: 20 }}>Nessun filo narrativo aperto</div>}
            {threads.map((t, i) => (
              <div key={i} style={{ padding: "8px 10px", borderRadius: 8, marginBottom: 6, background: "var(--code-bg)", border: "1px solid var(--border)", borderLeft: "3px solid var(--accent)" }}>
                <div style={{ fontSize: 12, color: "var(--text-h)", lineHeight: 1.4 }}>🧵 {t}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── SecretsPanel — rivelazione segreti per playtest ──────────────────────

function SecretsPanel({ adventure, gameState, onClose }) {
  const [tab, setTab] = useState("truth");
  const tabStyle = (t) => ({
    flex: 1, padding: "10px 4px", border: "none", cursor: "pointer", fontSize: 12, fontWeight: 700,
    borderBottom: tab === t ? "2px solid #f59e0b" : "2px solid transparent",
    background: "none", color: tab === t ? "#f59e0b" : "var(--text)",
  });

  const clues = adventure?.clues || [];
  const npcs = adventure?.npcs || [];
  const twists = adventure?.twists || [];

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", zIndex: 100,
      display: "flex", alignItems: "center", justifyContent: "center",
    }} onClick={onClose}>
      <div style={{
        background: "var(--bg)", borderRadius: 16, width: "min(700px, 95vw)", maxHeight: "85vh",
        display: "flex", flexDirection: "column", overflow: "hidden",
        border: "2px solid #f59e0b", boxShadow: "0 0 40px rgba(245,158,11,0.3)",
      }} onClick={e => e.stopPropagation()}>

        {/* header */}
        <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "space-between", background: "rgba(245,158,11,0.08)" }}>
          <div>
            <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 2, color: "#f59e0b", fontWeight: 700, marginBottom: 2 }}>Modalità Playtest</div>
            <div style={{ fontSize: 17, fontWeight: 800, color: "var(--text-h)" }}>🔓 Segreti dell'avventura</div>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text)", fontSize: 22 }}>×</button>
        </div>

        {/* tabs */}
        <div style={{ display: "flex", borderBottom: "1px solid var(--border)" }}>
          <button style={tabStyle("truth")} onClick={() => setTab("truth")}>🕵️ Verità</button>
          <button style={tabStyle("clues")} onClick={() => setTab("clues")}>🔍 Indizi</button>
          <button style={tabStyle("npcs")} onClick={() => setTab("npcs")}>👤 PNG</button>
          <button style={tabStyle("twists")} onClick={() => setTab("twists")}>🌀 Twist</button>
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>
          {tab === "truth" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div style={{ padding: "14px 16px", borderRadius: 10, background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.3)" }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "#f59e0b", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>Verità nascosta</div>
                <div style={{ fontSize: 14, color: "var(--text-h)", lineHeight: 1.6 }}>{adventure?.hidden_truth || "—"}</div>
              </div>
              <div style={{ padding: "14px 16px", borderRadius: 10, background: "var(--code-bg)", border: "1px solid var(--border)" }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text)", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>Premessa</div>
                <div style={{ fontSize: 14, color: "var(--text-h)", lineHeight: 1.6 }}>{adventure?.premise || "—"}</div>
              </div>
              <div style={{ padding: "14px 16px", borderRadius: 10, background: "rgba(74,222,128,0.06)", border: "1px solid rgba(74,222,128,0.25)" }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "#4ade80", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>Condizione di vittoria</div>
                <div style={{ fontSize: 14, color: "var(--text-h)", lineHeight: 1.6 }}>{adventure?.win_condition || "—"}</div>
              </div>
              {adventure?.threat_description && (
                <div style={{ padding: "14px 16px", borderRadius: 10, background: "rgba(248,113,113,0.06)", border: "1px solid rgba(248,113,113,0.25)" }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "#f87171", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>Minaccia</div>
                  <div style={{ fontSize: 14, color: "var(--text-h)", lineHeight: 1.6 }}>{adventure.threat_description}</div>
                </div>
              )}
            </div>
          )}

          {tab === "clues" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {clues.length === 0 && <div style={{ color: "var(--text)", opacity: 0.5, textAlign: "center", marginTop: 20 }}>Nessun indizio</div>}
              {clues.map(c => {
                const found = gameState?.clues_found?.includes(c.id);
                return (
                  <div key={c.id} style={{
                    padding: "10px 14px", borderRadius: 10,
                    background: found ? "rgba(74,222,128,0.08)" : "var(--code-bg)",
                    border: `1px solid ${found ? "rgba(74,222,128,0.35)" : "var(--border)"}`,
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                      <span style={{ fontSize: 13 }}>{found ? "🔍" : "⬜"}</span>
                      <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-h)" }}>{c.text}</span>
                      {found && <span style={{ fontSize: 11, background: "rgba(74,222,128,0.2)", color: "#4ade80", borderRadius: 4, padding: "1px 6px", fontWeight: 600 }}>Trovato</span>}
                    </div>
                    {c.reveals && <div style={{ fontSize: 12, color: "var(--text)", fontStyle: "italic", marginBottom: 2 }}>{c.reveals}</div>}
                    {c.location && <div style={{ fontSize: 11, color: "var(--text)", opacity: 0.6 }}>📍 {c.location}</div>}
                  </div>
                );
              })}
            </div>
          )}

          {tab === "npcs" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {npcs.length === 0 && <div style={{ color: "var(--text)", opacity: 0.5, textAlign: "center", marginTop: 20 }}>Nessun PNG</div>}
              {npcs.map(npc => (
                <div key={npc.id} style={{ padding: "10px 14px", borderRadius: 10, background: "var(--code-bg)", border: "1px solid var(--border)" }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-h)", marginBottom: 4 }}>{npc.name} <span style={{ fontSize: 11, color: "var(--text)", fontWeight: 400 }}>— {npc.role}</span></div>
                  {npc.secret && <div style={{ fontSize: 12, color: "#f59e0b", fontStyle: "italic", marginBottom: 2 }}>🔒 {npc.secret}</div>}
                  {npc.motivation && <div style={{ fontSize: 12, color: "var(--text)", lineHeight: 1.4 }}>{npc.motivation}</div>}
                  {npc.knowledge && <div style={{ fontSize: 11, color: "var(--text)", opacity: 0.7, marginTop: 4 }}>Sa: {npc.knowledge}</div>}
                </div>
              ))}
            </div>
          )}

          {tab === "twists" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {twists.length === 0 && <div style={{ color: "var(--text)", opacity: 0.5, textAlign: "center", marginTop: 20 }}>Nessun twist</div>}
              {twists.map((t, i) => (
                <div key={i} style={{ padding: "10px 14px", borderRadius: 10, background: "rgba(192,132,252,0.08)", border: "1px solid rgba(192,132,252,0.25)" }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "var(--accent)", textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>Twist {i + 1}</div>
                  <div style={{ fontSize: 13, color: "var(--text-h)", lineHeight: 1.5 }}>{typeof t === "string" ? t : t.description || t.text || JSON.stringify(t)}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Adventure screen (generazione bibbia) ─────────────────────────────────

function AdventureScreen({ genre, players, avatars, onStart, onBack }) {
  const [loading, setLoading] = useState(false);
  const [adventure, setAdventure] = useState(null);
  const [error, setError] = useState("");

  const playerDicts = players.map(p => ({
    id: p.id, name: p.name, role: p.role, archetype: p.archetype || p.role || "custom",
    stats: p.stats, skills: p.skills,
    advantages: p.advantages || [], disadvantages: p.disadvantages || [],
    hp: p.hp, max_hp: p.max_hp, fp: p.fp, max_fp: p.max_fp,
    dr: p.dr || 0, items: p.items || [], actions: p.actions || [],
  }));

  async function generate() {
    setLoading(true); setError(""); setAdventure(null);
    const res = await fetch(`${API_URL}/game/adventure/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ genre, players: playerDicts }),
    }).then(r => r.json());
    setLoading(false);
    if (res.error) { setError(res.error); return; }
    setAdventure(res);
  }

  const meta = GENRE_META[genre] || { emoji: "🎲", gradient: "135deg,#1a1a1a,#2a2a2a" };

  useEffect(() => { generate(); }, []);

  if (loading) return (
    <LoadingProgress
      icon="📖"
      title="Il Master prepara l'avventura..."
      steps={[
        { at: 0,     pill: "Premessa",   label: "Costruisco la premessa dell'avventura..." },
        { at: 3000,  pill: "PNG",        label: "Creo i personaggi non giocanti..." },
        { at: 7000,  pill: "Indizi",     label: "Nascondo gli indizi nelle location..." },
        { at: 11000, pill: "Misteri",    label: "Tesso i fili narrativi segreti..." },
        { at: 15000, pill: "Minaccia",   label: "Calibro la minaccia e il timer..." },
        { at: 19000, pill: "Finale",     label: "Definisco le condizioni di vittoria..." },
        { at: 23000, pill: "Rifinitura", label: "Rileggo e rifinisco la bibbia..." },
      ]}
    />
  );

  if (error) return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 16, background: "var(--bg)" }}>
      <div style={{ fontSize: 14, color: "#f87171" }}>{error}</div>
      <button onClick={generate} style={{ padding: "10px 24px", borderRadius: 8, border: "none", background: "var(--accent)", color: "#fff", cursor: "pointer", fontWeight: 700 }}>Riprova</button>
      <button onClick={onBack} style={{ fontSize: 13, color: "var(--text)", background: "none", border: "none", cursor: "pointer" }}>← Torna indietro</button>
    </div>
  );

  if (!adventure) return null;

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", padding: "32px 24px", background: "var(--bg)" }}>
      {/* header genere */}
      <div style={{ width: "100%", maxWidth: 720, borderRadius: 16, marginBottom: 28, overflow: "hidden", background: `linear-gradient(${meta.gradient})`, boxShadow: "0 4px 24px rgba(0,0,0,0.5)" }}>
        <div style={{ padding: "24px 28px" }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "rgba(255,255,255,0.5)", letterSpacing: 2, textTransform: "uppercase", marginBottom: 4 }}>
            {adventure.from_pdf ? "📄 Da PDF" : "✨ Generata con AI"}
          </div>
          <div style={{ fontSize: 24, fontWeight: 900, color: "#fff", marginBottom: 6 }}>{adventure.title}</div>
          <div style={{ fontSize: 14, color: "rgba(255,255,255,0.7)", lineHeight: 1.5 }}>{adventure.premise}</div>
        </div>
      </div>

      <div style={{ width: "100%", maxWidth: 720, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 20 }}>
        {/* PNG */}
        <div style={{ background: "var(--code-bg)", borderRadius: 12, padding: 16, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: 12, fontWeight: 800, color: "var(--accent)", marginBottom: 10, textTransform: "uppercase", letterSpacing: 1 }}>👤 Personaggi Non Giocanti</div>
          {adventure.npcs?.map(npc => (
            <div key={npc.id} style={{ marginBottom: 8, paddingBottom: 8, borderBottom: "1px solid var(--border)" }}>
              <div style={{ fontWeight: 700, fontSize: 13, color: "var(--text-h)" }}>{npc.name}</div>
              <div style={{ fontSize: 11, color: "var(--accent)", marginBottom: 2 }}>{npc.role}</div>
              <div style={{ fontSize: 11, color: "var(--text)" }}>{npc.description}</div>
            </div>
          ))}
        </div>

        {/* Indizi + Minaccia */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ background: "var(--code-bg)", borderRadius: 12, padding: 16, border: "1px solid var(--border)" }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: "var(--accent)", marginBottom: 10, textTransform: "uppercase", letterSpacing: 1 }}>🔍 Indizi nascosti</div>
            {adventure.clues?.map(c => (
              <div key={c.id} style={{ fontSize: 12, color: "var(--text)", marginBottom: 5, paddingLeft: 8, borderLeft: "2px solid var(--border)" }}>
                📍 {c.location}
              </div>
            ))}
          </div>
          <div style={{ background: "var(--code-bg)", borderRadius: 12, padding: 16, border: "1px solid var(--border)" }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: "#f87171", marginBottom: 6, textTransform: "uppercase", letterSpacing: 1 }}>⚠ Minaccia</div>
            <div style={{ fontSize: 12, color: "var(--text)", marginBottom: 4 }}>{adventure.threat_description}</div>
            {adventure.has_time_pressure !== false && (
              <div style={{ fontSize: 11, color: "var(--text)", opacity: 0.6 }}>Timer: {adventure.threat_max_turns} turni</div>
            )}
            {adventure.has_time_pressure === false && (
              <div style={{ fontSize: 11, color: "#4ade80", opacity: 0.8 }}>Nessun limite di tempo</div>
            )}
          </div>
        </div>
      </div>

      {/* vittoria */}
      <div style={{ width: "100%", maxWidth: 720, background: "var(--code-bg)", borderRadius: 12, padding: "14px 18px", border: "1px solid var(--border)", marginBottom: 24 }}>
        <div style={{ fontSize: 12, fontWeight: 800, color: "#4ade80", marginBottom: 4, textTransform: "uppercase", letterSpacing: 1 }}>🏆 Condizione vittoria</div>
        <div style={{ fontSize: 13, color: "var(--text-h)" }}>{adventure.win_condition}</div>
      </div>

      <div style={{ width: "100%", maxWidth: 720, display: "flex", gap: 12 }}>
        <button onClick={generate} style={{ padding: "11px 20px", borderRadius: 10, border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text)", cursor: "pointer", fontWeight: 600, fontSize: 14 }}>
          🔄 Rigenera
        </button>
        <button onClick={() => onStart(adventure)} style={{ flex: 1, padding: "13px 0", borderRadius: 10, border: "none", background: "var(--accent)", color: "#fff", fontWeight: 800, fontSize: 16, cursor: "pointer" }}>
          ⚔️ Inizia l'avventura
        </button>
      </div>
    </div>
  );
}

// ─── HexCombatMap ──────────────────────────────────────────────────────────
// Griglia esagonale SVG flat-top, 1 hex = 1 yard GURPS Lite.
// Terreni: 0=normale 1=copertura 2=difficile 3=muro
// Facing: 0-5 (direzioni hex, 0=nord)

const HEX_SIZE = 28; // raggio hex (apotema orizzontale)
const HEX_W = HEX_SIZE * 2;
const HEX_H = Math.sqrt(3) * HEX_SIZE;
const HEX_OFFSET_X = HEX_W * 0.75;

// Pixel center of hex (col, row) — flat-top offset grid
function hexCenter(col, row) {
  const x = col * HEX_OFFSET_X + HEX_SIZE;
  const y = row * HEX_H + (col % 2 === 1 ? HEX_H / 2 : 0) + HEX_H / 2;
  return { x, y };
}

// SVG path for a flat-top hex centered at (cx,cy)
function hexPath(cx, cy, r) {
  const pts = Array.from({ length: 6 }, (_, i) => {
    const a = (Math.PI / 180) * (60 * i);
    return `${cx + r * Math.cos(a)},${cy + r * Math.sin(a)}`;
  });
  return `M${pts.join("L")}Z`;
}

// Hex distance (cube coords)
function hexDist(c1, r1, c2, r2) {
  // convert offset→cube
  function toCube(col, row) {
    const x = col;
    const z = row - (col - (col & 1)) / 2;
    return { x, y: -x - z, z };
  }
  const a = toCube(c1, r1), b = toCube(c2, r2);
  return Math.max(Math.abs(a.x - b.x), Math.abs(a.y - b.y), Math.abs(a.z - b.z));
}

// Facing triangle: direction 0=E 1=SE 2=SW 3=W 4=NW 5=NE
function facingTriangle(cx, cy, facing, r, color) {
  const angle = (Math.PI / 3) * facing - Math.PI / 6;
  const tip = { x: cx + (r - 4) * Math.cos(angle), y: cy + (r - 4) * Math.sin(angle) };
  const l = { x: cx + 6 * Math.cos(angle + 2), y: cy + 6 * Math.sin(angle + 2) };
  const rp = { x: cx + 6 * Math.cos(angle - 2), y: cy + 6 * Math.sin(angle - 2) };
  return `M${tip.x},${tip.y}L${l.x},${l.y}L${rp.x},${rp.y}Z`;
}

const DEFAULT_TERRAIN_COLORS = {
  0: "rgba(255,255,255,0.015)",  // normale
  1: "rgba(74,222,128,0.20)",    // copertura
  2: "rgba(180,130,60,0.24)",    // difficile
  3: "rgba(30,30,40,0.78)",      // muro
};
const DEFAULT_TERRAIN_STROKE = {
  0: "rgba(255,255,255,0.09)",
  1: "rgba(74,222,128,0.55)",
  2: "rgba(180,130,60,0.55)",
  3: "rgba(120,120,145,0.85)",
};

const BATTLEMAP_THEMES = {
  fantasy: {
    label: "Dungeon fantasy",
    base: "#17130f",
    floor: "#2a241d",
    floorAlt: "#342b21",
    grid: "rgba(222,184,121,0.16)",
    wall: "rgba(21,18,16,0.9)",
    wallStroke: "rgba(183,134,72,0.75)",
    cover: "rgba(127,91,48,0.52)",
    difficult: "rgba(91,59,31,0.50)",
    accent: "#d6a855",
    terrainColors: { 0: "rgba(255,244,210,0.025)", 1: "rgba(166,113,52,0.35)", 2: "rgba(105,74,44,0.36)", 3: "rgba(19,16,14,0.88)" },
    terrainStroke: { 0: "rgba(238,205,145,0.13)", 1: "rgba(236,178,91,0.65)", 2: "rgba(176,124,70,0.58)", 3: "rgba(228,173,83,0.72)" },
  },
  sci_fi: {
    label: "Installazione sci-fi",
    base: "#07111a",
    floor: "#0d2230",
    floorAlt: "#123349",
    grid: "rgba(83,201,255,0.14)",
    wall: "rgba(4,10,18,0.9)",
    wallStroke: "rgba(87,208,255,0.65)",
    cover: "rgba(59,130,246,0.32)",
    difficult: "rgba(37,99,235,0.20)",
    accent: "#60d5ff",
    terrainColors: { 0: "rgba(96,213,255,0.025)", 1: "rgba(59,130,246,0.28)", 2: "rgba(20,184,166,0.22)", 3: "rgba(3,7,18,0.85)" },
    terrainStroke: { 0: "rgba(125,211,252,0.13)", 1: "rgba(96,165,250,0.65)", 2: "rgba(45,212,191,0.58)", 3: "rgba(147,197,253,0.72)" },
  },
  mystery_horror: {
    label: "Scenario gotico",
    base: "#100f14",
    floor: "#1f1b25",
    floorAlt: "#292230",
    grid: "rgba(248,113,113,0.13)",
    wall: "rgba(10,9,13,0.9)",
    wallStroke: "rgba(248,113,113,0.48)",
    cover: "rgba(127,29,29,0.38)",
    difficult: "rgba(86,62,52,0.34)",
    accent: "#f87171",
    terrainColors: { 0: "rgba(255,255,255,0.018)", 1: "rgba(127,29,29,0.30)", 2: "rgba(120,80,60,0.30)", 3: "rgba(11,10,14,0.86)" },
    terrainStroke: { 0: "rgba(248,113,113,0.11)", 1: "rgba(248,113,113,0.56)", 2: "rgba(180,130,90,0.50)", 3: "rgba(190,100,100,0.62)" },
  },
  ww2: {
    label: "Teatro bellico",
    base: "#15170f",
    floor: "#26301b",
    floorAlt: "#313b23",
    grid: "rgba(190,212,120,0.12)",
    wall: "rgba(18,20,13,0.88)",
    wallStroke: "rgba(148,163,90,0.62)",
    cover: "rgba(120,92,50,0.42)",
    difficult: "rgba(78,65,42,0.36)",
    accent: "#c6d67a",
    terrainColors: { 0: "rgba(221,244,180,0.02)", 1: "rgba(132,104,60,0.32)", 2: "rgba(91,76,48,0.34)", 3: "rgba(20,22,14,0.84)" },
    terrainStroke: { 0: "rgba(214,232,160,0.11)", 1: "rgba(198,166,100,0.56)", 2: "rgba(154,132,88,0.50)", 3: "rgba(178,194,124,0.62)" },
  },
  action: {
    label: "Zona d'azione",
    base: "#101418",
    floor: "#202a32",
    floorAlt: "#2b3540",
    grid: "rgba(148,163,184,0.14)",
    wall: "rgba(11,15,20,0.88)",
    wallStroke: "rgba(148,163,184,0.62)",
    cover: "rgba(234,179,8,0.24)",
    difficult: "rgba(100,116,139,0.28)",
    accent: "#facc15",
    terrainColors: { 0: "rgba(255,255,255,0.018)", 1: "rgba(234,179,8,0.25)", 2: "rgba(100,116,139,0.26)", 3: "rgba(12,15,20,0.84)" },
    terrainStroke: { 0: "rgba(203,213,225,0.12)", 1: "rgba(250,204,21,0.55)", 2: "rgba(148,163,184,0.48)", 3: "rgba(203,213,225,0.60)" },
  },
};

function battleText(...parts) {
  return parts.filter(Boolean).join(" ").toLowerCase();
}

function battleThemeFor(genre, text) {
  if (genre === "fantasy") return BATTLEMAP_THEMES.fantasy;
  if (genre === "sci_fi") return BATTLEMAP_THEMES.sci_fi;
  if (genre === "mystery_horror" || /cripta|catacomb|cimiter|spettr|sangue|malediz|gotic|horror/.test(text)) return BATTLEMAP_THEMES.mystery_horror;
  if (genre === "ww2") return BATTLEMAP_THEMES.ww2;
  return BATTLEMAP_THEMES.action;
}

function battleSizeFor(text, enemyCount = 0) {
  if (/corridoio|tunnel|passaggio|ponte|galleria|stretta|vicolo/.test(text)) return { cols: 18, rows: 8, layout: "narrow" };
  if (/foresta|radura|campo|piazza|hangar|sala grande|cortile|rovine|esterno|aperto|battlefield/.test(text) || enemyCount >= 4) return { cols: 18, rows: 12, layout: "open" };
  if (/stanza|cella|cripta|sacrario|biblioteca|oratorio|sala|laboratorio|ponte di comando/.test(text)) return { cols: 15, rows: 10, layout: "room" };
  return { cols: 15, rows: 10, layout: "room" };
}

function buildBattleMapTerrain(cols, rows, layout, text) {
  const terrain = {};
  for (let c = 0; c < cols; c++) {
    for (let r = 0; r < rows; r++) terrain[`${c},${r}`] = 0;
  }

  const set = (c, r, t) => {
    if (c >= 0 && c < cols && r >= 0 && r < rows) terrain[`${c},${r}`] = t;
  };
  const rect = (c1, r1, c2, r2, t) => {
    for (let c = c1; c <= c2; c++) for (let r = r1; r <= r2; r++) set(c, r, t);
  };

  for (let c = 0; c < cols; c++) { set(c, 0, 3); set(c, rows - 1, 3); }
  for (let r = 0; r < rows; r++) { set(0, r, 3); set(cols - 1, r, 3); }

  if (layout === "narrow") {
    for (let c = 1; c < cols - 1; c++) {
      if (c % 5 === 0) set(c, 2, 1);
      if (c % 5 === 2) set(c, rows - 3, 1);
      if (c % 6 === 3) set(c, Math.floor(rows / 2), 2);
    }
    rect(Math.floor(cols / 2) - 1, 1, Math.floor(cols / 2), 2, 3);
    rect(Math.floor(cols / 2) - 1, rows - 3, Math.floor(cols / 2), rows - 2, 3);
  } else if (layout === "open") {
    [[4, 3], [7, 7], [11, 4], [14, 8], [3, rows - 4]].forEach(([c, r]) => set(c, r, 1));
    rect(Math.floor(cols / 2) - 1, Math.floor(rows / 2) - 1, Math.floor(cols / 2) + 1, Math.floor(rows / 2), 2);
    for (let c = 2; c < cols - 2; c += 4) set(c, rows - 3, 2);
  } else {
    rect(Math.floor(cols / 2) - 1, 0, Math.floor(cols / 2) + 1, 1, 0);
    rect(Math.floor(cols / 2) - 1, rows - 2, Math.floor(cols / 2) + 1, rows - 1, 0);
    [[4, 3], [cols - 5, 3], [4, rows - 4], [cols - 5, rows - 4]].forEach(([c, r]) => set(c, r, 1));
    rect(Math.floor(cols / 2) - 1, Math.floor(rows / 2) - 1, Math.floor(cols / 2) + 1, Math.floor(rows / 2), 2);
  }

  if (/biblioteca|archiv|scriptorium/.test(text)) {
    rect(3, 2, 3, rows - 3, 1);
    rect(cols - 4, 2, cols - 4, rows - 3, 1);
  }
  if (/altare|ritual|sacrario|cripta|catacomb/.test(text)) {
    rect(Math.floor(cols / 2) - 1, Math.floor(rows / 2), Math.floor(cols / 2) + 1, Math.floor(rows / 2) + 1, 1);
  }
  if (/acqua|sommers|marea|palude|fiume/.test(text)) {
    for (let c = 2; c < cols - 2; c++) set(c, Math.floor(rows / 2), 2);
  }
  if (/macerie|crollo|rovine|frana/.test(text)) {
    [[2, 2], [3, 3], [cols - 3, rows - 3], [cols - 4, rows - 4]].forEach(([c, r]) => set(c, r, 2));
  }
  return terrain;
}

function buildBattleMapSpec({ genre, environmentType, sceneText, locationName, enemyNames }) {
  const text = battleText(genre, environmentType, sceneText, locationName, ...(enemyNames || []));
  const theme = battleThemeFor(genre, text);
  const size = battleSizeFor(text, (enemyNames || []).length);
  const terrain = buildBattleMapTerrain(size.cols, size.rows, size.layout, text);
  const labelBits = [theme.label];
  if (/biblioteca|archiv|scriptorium/.test(text)) labelBits.push("libreria");
  else if (/cripta|catacomb|cimiter/.test(text)) labelBits.push("cripta");
  else if (/foresta|radura/.test(text)) labelBits.push("esterno");
  else if (/laboratorio|terminal|ponte di comando|hangar/.test(text)) labelBits.push("tecnico");
  else if (environmentType) labelBits.push(String(environmentType).replaceAll("_", " "));
  return { ...size, terrain, theme, title: labelBits.join(" · ") };
}

function renderBattleMapDecor(mapSpec) {
  const { cols, rows, theme, terrain } = mapSpec;
  const w = cols * HEX_OFFSET_X + HEX_SIZE * 0.5 + 4;
  const h = rows * HEX_H + HEX_H / 2 + 4;
  const cells = Object.entries(terrain);
  return (
    <g pointerEvents="none">
      <rect x="0" y="0" width={w} height={h} fill={theme.base} />
      <rect x="10" y="10" width={w - 20} height={h - 20} rx="18" fill={theme.floor} opacity="0.92" />
      {Array.from({ length: 14 }, (_, i) => (
        <line
          key={`floor-line-${i}`}
          x1={(i * 73) % w}
          y1="0"
          x2={(i * 73 + w * 0.35) % w}
          y2={h}
          stroke={i % 2 ? theme.floorAlt : theme.grid}
          strokeWidth={i % 2 ? 18 : 1}
          opacity={i % 2 ? 0.12 : 0.35}
        />
      ))}
      {cells.filter(([, t]) => t === 3).map(([key]) => {
        const [c, r] = key.split(",").map(Number);
        const { x, y } = hexCenter(c, r);
        return <path key={`wall-${key}`} d={hexPath(x, y, HEX_SIZE - 2)} fill={theme.wall} stroke={theme.wallStroke} strokeWidth="1.2" />;
      })}
      {cells.filter(([, t]) => t === 2).map(([key]) => {
        const [c, r] = key.split(",").map(Number);
        const { x, y } = hexCenter(c, r);
        return (
          <g key={`diff-${key}`}>
            <path d={hexPath(x, y, HEX_SIZE - 4)} fill={theme.difficult} />
            <circle cx={x - 8} cy={y - 5} r="3" fill={theme.accent} opacity="0.25" />
            <circle cx={x + 7} cy={y + 5} r="4" fill="#000" opacity="0.20" />
          </g>
        );
      })}
      {cells.filter(([, t]) => t === 1).map(([key], i) => {
        const [c, r] = key.split(",").map(Number);
        const { x, y } = hexCenter(c, r);
        return (
          <g key={`cover-${key}`} transform={`rotate(${(i % 6) * 17} ${x} ${y})`}>
            <rect x={x - 14} y={y - 7} width="28" height="14" rx="3" fill={theme.cover} stroke={theme.accent} strokeWidth="1" opacity="0.85" />
            <line x1={x - 10} y1={y} x2={x + 10} y2={y} stroke="#000" strokeWidth="1" opacity="0.22" />
          </g>
        );
      })}
      <rect x="0" y="0" width={w} height={h} fill="url(#battle-vignette)" opacity="0.7" />
    </g>
  );
}

function buildInitialPositions(players, enemies, cols = 15, rows = 10) {
  const positions = {};
  players.forEach((p, i) => {
    positions[`p_${p.id}`] = { col: 2, row: Math.min(rows - 2, 2 + i * 2), facing: 0, type: "player", id: p.id };
  });
  enemies.forEach((e, i) => {
    positions[`e_${e.id}`] = { col: Math.max(3, cols - 4), row: Math.min(rows - 2, 2 + i * 2), facing: 3, type: "enemy", id: e.id };
  });
  return positions;
}

function CombatMap({ players, sceneEntities, activePlayerId, pendingAttack, onAttack, onDefend, onStandUp, onNextPlayer, onFinishTurn, avatars, npcAvatars, bgImage, lastCombatLog, onClose, genre, environmentType, sceneText, locationName }) {
  const entities = sceneEntities || [];
  const enemies = entities.filter(e => e.type === "enemy");
  // La mappa non cambia dimensione durante il combattimento — dipendenze stabili
  const mapSpec = useMemo(() => buildBattleMapSpec({
    genre,
    environmentType,
    sceneText,
    locationName,
    enemyNames: enemies.map(e => e.name),
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [genre, environmentType, sceneText, locationName]);
  const mapCols = mapSpec.cols;
  const mapRows = mapSpec.rows;
  const terrainColors = mapSpec.theme?.terrainColors || DEFAULT_TERRAIN_COLORS;
  const terrainStroke = mapSpec.theme?.terrainStroke || DEFAULT_TERRAIN_STROKE;

  const [terrain, setTerrain] = useState(() => mapSpec.terrain);
  const [positions, setPositions] = useState(() => buildInitialPositions(players, enemies, mapCols, mapRows));
  const [selected, setSelected] = useState(null);       // key "p_X" o "e_X"
  const [mode, setMode] = useState("select");           // select|move|attack
  const [attackActionType, setAttackActionType] = useState("normal"); // "normal"|"all_out_attack"
  const [reachable, setReachable] = useState(new Set());
  const [combatLog, setCombatLog] = useState([]);
  const [actedThisRound, setActedThisRound] = useState(new Set()); // player id già agiti
  // geometria ultimo attacco — mandati al backend con la difesa
  const [lastAttackCoverBonus, setLastAttackCoverBonus] = useState(0);
  const [lastAttackIsRear, setLastAttackIsRear] = useState(false);
  // animazioni token
  const [animating, setAnimating] = useState({});       // key → "move"|"hit"
  const [dragPos, setDragPos] = useState({ x: 40, y: 80 });
  const [dragging, setDragging] = useState(false);
  const [dragStart, setDragStart] = useState(null);
  const svgRef = useRef();

  const svgWidth = mapCols * HEX_OFFSET_X + HEX_SIZE * 0.5 + 4;
  const svgHeight = mapRows * HEX_H + HEX_H / 2 + 4;

  useEffect(() => {
    setTerrain(mapSpec.terrain);
  }, [mapSpec]);

  // Dimensioni mappa congelate al mount — non cambiano durante il combattimento
  const frozenCols = React.useRef(mapCols);
  const frozenRows = React.useRef(mapRows);

  // Aggiorna posizioni SOLO per entità nuove — non toccare quelle già posizionate
  useEffect(() => {
    const cols = frozenCols.current;
    const rows = frozenRows.current;
    setPositions(prev => {
      const next = { ...prev };
      const wanted = new Set();
      players.forEach((p, i) => {
        const key = `p_${p.id}`;
        wanted.add(key);
        if (!next[key]) {
          next[key] = { col: 2, row: Math.min(rows - 2, 2 + i * 2), facing: 0, type: "player", id: p.id };
        }
      });
      enemies.forEach((e, i) => {
        const key = `e_${e.id}`;
        wanted.add(key);
        if (!next[key]) {
          next[key] = { col: Math.max(3, cols - 4), row: Math.min(rows - 2, 2 + i * 2), facing: 3, type: "enemy", id: e.id };
        }
        // Se l'entità è morta, rimuovila
        if ((e.hp ?? 1) <= 0) delete next[key];
      });
      // Rimuovi entità non più in scena
      for (const key of Object.keys(next)) {
        if (!wanted.has(key)) delete next[key];
      }
      return next;
    });
  }, [players, sceneEntities]);

  useEffect(() => {
    const move = lastCombatLog?.tactical_move;
    if (!move?.entity_id || !move.to) return;
    const enemyKey = `e_${move.entity_id}`;
    setAnimating(a => ({ ...a, [enemyKey]: "move" }));
    setTimeout(() => setAnimating(a => { const n = { ...a }; delete n[enemyKey]; return n; }), 260);
    setPositions(prev => ({
      ...prev,
      [enemyKey]: { ...(prev[enemyKey] || {}), ...move.to },
    }));
  }, [lastCombatLog]);

  // basic move di chi è selezionato
  function getBasicMove(tokenKey) {
    if (!tokenKey) return 5;
    if (tokenKey.startsWith("p_")) {
      const pid = parseInt(tokenKey.replace("p_", ""));
      const p = players.find(x => x.id === pid);
      return p ? Math.floor(((p.stats?.agilita || 10) + (p.stats?.forza || 10)) / 4) || 5 : 5;
    }
    return 4; // default nemici
  }

  function computeReachable(tokenKey) {
    const pos = positions[tokenKey];
    if (!pos) return new Set();
    const move = getBasicMove(tokenKey);
    const reachSet = new Set();
    for (let c = 0; c < mapCols; c++) {
      for (let r = 0; r < mapRows; r++) {
        const t = terrain[`${c},${r}`] || 0;
        if (t === 3) continue; // muro
        const cost = t === 2 ? 2 : 1;
        const d = hexDist(pos.col, pos.row, c, r);
        if (d > 0 && d * cost <= move) reachSet.add(`${c},${r}`);
      }
    }
    return reachSet;
  }

  function selectToken(key) {
    setSelected(key);
    setMode("select");
    setReachable(new Set());
  }

  function canControlToken(key = selected) {
    return !!key
      && key.startsWith("p_")
      && parseInt(key.replace("p_", "")) === activePlayerId
      && !pendingAttack;
  }

  function tacticalSnapshot(overridePositions = positions) {
    return { positions: overridePositions, terrain, cols: mapCols, rows: mapRows };
  }

  function applyNpcTurnResult(res) {
    if (!res) return;
    if (res.positions && Object.keys(res.positions).length > 0) {
      setPositions(prev => ({ ...prev, ...res.positions }));
    }
  }

  function startMove() {
    if (!canControlToken()) return;
    setMode("move");
    setReachable(computeReachable(selected));
  }

  function startAttack() {
    if (!canControlToken()) return;
    setMode("attack");
    setReachable(new Set());
  }

  function advanceTurn(actedId, runNpc = true, positionsOverride = positions) {
    const newActed = new Set(actedThisRound);
    if (actedId != null) newActed.add(actedId);
    const alivePlayers = players.filter(p => p.hp > 0 && p.status !== "sconfitto" && p.status !== "morto");
    const remaining = alivePlayers.filter(p => !newActed.has(p.id));
    if (remaining.length === 0) {
      setActedThisRound(new Set());
      if (onNextPlayer) onNextPlayer(alivePlayers[0]?.id);
    } else {
      setActedThisRound(newActed);
      if (onNextPlayer) onNextPlayer(remaining[0].id);
    }
    setSelected(null);
    setMode("select");
    setReachable(new Set());
    // Fa agire gli NPC dopo ogni azione del giocatore (tranne dopo un attacco — li fa già handleAttack)
    if (runNpc && onFinishTurn) {
      Promise.resolve(onFinishTurn(tacticalSnapshot(positionsOverride))).then(applyNpcTurnResult);
    }
  }

  async function clickHex(col, row) {
    const key = `${col},${row}`;
    // trova token su questo hex
    const tokenOnHex = Object.entries(positions).find(([k, p]) => p.col === col && p.row === row);

    if (mode === "move" && canControlToken() && reachable.has(key)) {
      // animazione spostamento
      const nextPositions = { ...positions, [selected]: { ...positions[selected], col, row } };
      setAnimating(prev => ({ ...prev, [selected]: "move" }));
      setTimeout(() => {
        setPositions(nextPositions);
        setAnimating(prev => { const n = {...prev}; delete n[selected]; return n; });
      }, 180);
      setCombatLog(prev => [...prev, `${selected} si sposta in (${col},${row})`]);
      // movimento consuma il turno — avanza al prossimo giocatore
      const movedPid = selected.startsWith("p_") ? parseInt(selected.replace("p_", "")) : null;
      advanceTurn(movedPid, true, nextPositions);
      return;
    }

    if (mode === "attack" && canControlToken()) {
      if (tokenOnHex && tokenOnHex[0] !== selected) {
        const targetKey = tokenOnHex[0];
        const selPos = positions[selected];
        const tgtPos = positions[targetKey];
        const dist = hexDist(selPos.col, selPos.row, tgtPos.col, tgtPos.row);
        const isMelee = dist <= 1;
        const isRanged = dist > 1 && dist <= 10;
        if (isMelee || isRanged) {
          const rangePenalty = isRanged ? -(dist - 1) : 0;

          // Attacco da retro: calcola angolo relativo rispetto al facing del bersaglio
          // Se l'attaccante è negli hex 3-4-5 del bersaglio (dietro) → ignora difesa attiva
          const tgtFacing = tgtPos.facing || 0;
          const dx = selPos.col - tgtPos.col;
          const dy = selPos.row - tgtPos.row;
          const attackAngle = Math.round(Math.atan2(dy, dx) / (Math.PI / 3) + 6) % 6;
          const rearHexes = [(tgtFacing + 3) % 6, (tgtFacing + 4) % 6, (tgtFacing + 2) % 6];
          const isRearAttack = isMelee && rearHexes.includes(attackAngle);

          // Copertura: bonus +2 difesa se il bersaglio è su hex copertura
          const tgtTerrain = terrain[`${tgtPos.col},${tgtPos.row}`] || 0;
          const coverBonus = tgtTerrain === 1 ? 2 : 0;

          const logParts = [`dist ${dist}`];
          if (rangePenalty) logParts.push(`pen distanza ${rangePenalty}`);
          if (isRearAttack) logParts.push("ATTACCO DA RETRO — difesa ignorata!");
          if (coverBonus) logParts.push(`copertura +${coverBonus} difesa`);

          if (selected.startsWith("p_")) {
            const pid = parseInt(selected.replace("p_", ""));
            const p = players.find(x => x.id === pid);
            if (p) {
              // Salva geometria per mandarla con la difesa
              setLastAttackCoverBonus(coverBonus);
              setLastAttackIsRear(isRearAttack);
              // Animazione attacco sul token attaccante
              setAnimating(prev => ({ ...prev, [selected]: "attack" }));
              setTimeout(() => setAnimating(prev => { const n = {...prev}; delete n[selected]; return n; }), 400);
              // Usa sempre "combattere" — il backend ha il fallback sintetico
              const npcTurnResult = await onAttack(p, "combattere", targetKey.replace("e_", ""), attackActionType, tacticalSnapshot());
              applyNpcTurnResult(npcTurnResult);
              setAttackActionType("normal");
              setCombatLog(prev => [...prev, `${p.name} attacca${attackActionType === "all_out_attack" ? " [TOTALE]" : ""} (${logParts.join(", ")})`]);
              // attacco consuma il turno — handleAttack chiama già _runNpcTurn, non duplicare
              advanceTurn(pid, false);
            }
          }
        } else {
          setCombatLog(prev => [...prev, `Troppo lontano! (dist ${dist}, max 10 yd)`]);
        }
      }
      setMode("select");
      return;
    }

    // click su token → seleziona
    if (tokenOnHex) {
      selectToken(tokenOnHex[0]);
    }
  }

  function rotateFacing(key, dir) {
    setPositions(prev => ({
      ...prev,
      [key]: { ...prev[key], facing: ((prev[key].facing || 0) + dir + 6) % 6 },
    }));
  }

  // drag finestra
  function onMouseDown(e) {
    if (e.target.closest(".hex-map-content")) return;
    setDragging(true);
    setDragStart({ mx: e.clientX, my: e.clientY, ox: dragPos.x, oy: dragPos.y });
  }
  function onMouseMove(e) {
    if (!dragging || !dragStart) return;
    setDragPos({ x: dragStart.ox + e.clientX - dragStart.mx, y: dragStart.oy + e.clientY - dragStart.my });
  }
  function onMouseUp() { setDragging(false); setDragStart(null); }

  const selPos = selected ? positions[selected] : null;
  const selName = selected
    ? (selected.startsWith("p_")
        ? players.find(p => p.id === parseInt(selected.replace("p_", "")))?.name
        : enemies.find(e => e.id === selected.replace("e_", ""))?.name)
    : null;

  const defPlayer = players.find(p => p.id === activePlayerId) || players[0];
  const defVal = defPlayer ? Math.floor((defPlayer.stats?.agilita || 10) / 2) + 3 : 8;
  const selectedIsActivePlayer = canControlToken();
  const selectedIsEnemy = selected?.startsWith("e_");
  const selectedIsOtherPlayer = selected?.startsWith("p_") && !selectedIsActivePlayer;

  return (
    <div
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      style={{ position: "fixed", inset: 0, pointerEvents: "none", zIndex: 50 }}
    >
      <div
        onMouseDown={onMouseDown}
        style={{
          position: "absolute", left: dragPos.x, top: dragPos.y,
          width: Math.min(svgWidth + 24, window.innerWidth - 60),
          background: "rgba(16,17,26,0.97)", border: "1px solid rgba(239,68,68,0.5)",
          borderRadius: 14, boxShadow: "0 8px 40px rgba(0,0,0,0.7)",
          pointerEvents: "auto", userSelect: "none",
          display: "flex", flexDirection: "column", overflow: "hidden",
        }}
      >
        {/* header drag */}
        <div style={{
          padding: "8px 14px", display: "flex", alignItems: "center", justifyContent: "space-between",
          background: "rgba(239,68,68,0.12)", borderBottom: "1px solid rgba(239,68,68,0.2)",
          cursor: "grab", flexWrap: "wrap", gap: 6,
        }}>
          <span style={{ fontSize: 13, fontWeight: 800, color: "#ef4444", letterSpacing: 1 }}>⚔ COMBATTIMENTO</span>

          {/* Riepilogo ultimo scambio — integrazione con chat */}
          {lastCombatLog?.result && (() => {
            const r = lastCombatLog.result;
            if (!r.hit) return <span style={{ fontSize: 11, color: "rgba(255,255,255,0.4)" }}>Ultimo: colpo mancato</span>;
            if (r.defended) return <span style={{ fontSize: 11, color: "#60a5fa" }}>Ultimo: difesa riuscita (+{r.defense_margin})</span>;
            const wound = { ferito: "🩸ferito", ferito_grave: "🩸🩸ferito grave", fuori_combattimento: "💀abbattuto", morto: "💀morto" }[r.wound_threshold] || "";
            return (
              <span style={{ fontSize: 11, color: "#fca5a5" }}>
                Ultimo: {lastCombatLog.attacker}→{lastCombatLog.target} {r.net_damage}PF {wound}
                {r.shock_applied > 0 && <span style={{ color: "#f59e0b" }}> ⚡−{r.shock_applied}</span>}
              </span>
            );
          })()}

          <div style={{ display: "flex", gap: 6, alignItems: "center", marginLeft: "auto" }}>
            <span style={{ fontSize: 10, color: "rgba(255,255,255,0.38)", textTransform: "uppercase", letterSpacing: 0.7 }}>
              {mapSpec.title} · {mapCols}×{mapRows}
            </span>
            {selected && (
              <span style={{ fontSize: 11, color: "var(--accent)" }}>
                {selName} {mode === "move" ? "→ scegli hex" : mode === "attack" ? "→ scegli bersaglio" : ""}
              </span>
            )}
            <button onClick={onClose} title="Nascondi mappa" style={{ background: "none", border: "none", color: "rgba(255,255,255,0.5)", cursor: "pointer", fontSize: 16, lineHeight: 1, padding: "0 4px" }}>×</button>
          </div>
        </div>

        {/* barra iniziativa — Basic Speed = (DE+SA)/4 */}
        {(() => {
          const allCombatants = [
            ...players.map(p => ({
              key: `p_${p.id}`,
              name: p.name,
              speed: ((p.stats?.agilita || 10) + (p.stats?.empatia || 10)) / 4,
              color: "var(--accent,#a855f7)",
              isActive: p.id === activePlayerId,
            })),
            ...enemies.filter(e => e.hp > 0).map(e => ({
              key: `e_${e.id}`,
              name: e.name,
              speed: (e.attack_skill || 10) / 4,
              color: "#ef4444",
              isActive: false,
            })),
          ].sort((a, b) => b.speed - a.speed);
          const isPlayerTurn = !pendingAttack; // se non c'è attacco pendente, tocca ai giocatori
          return (
            <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "5px 14px", background: "rgba(0,0,0,0.3)", borderBottom: "1px solid rgba(255,255,255,0.06)", overflowX: "auto" }}>
              <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: 1, flexShrink: 0 }}>Iniziativa</span>
              {allCombatants.map((c, i) => {
                const isActivePlayer = c.key === `p_${activePlayerId}`;
                const hasActed = c.key.startsWith("p_") && actedThisRound.has(parseInt(c.key.replace("p_","")));
                const isMyTurn = isPlayerTurn ? isActivePlayer : !c.key.startsWith("p_");
                return (
                  <div key={c.key} style={{
                    display: "flex", alignItems: "center", gap: 4, flexShrink: 0,
                    padding: "2px 8px", borderRadius: 5, fontSize: 11, fontWeight: 700,
                    background: isMyTurn ? `${c.color}33` : "rgba(255,255,255,0.05)",
                    border: `1px solid ${isMyTurn ? c.color : "rgba(255,255,255,0.1)"}`,
                    color: isMyTurn ? c.color : hasActed ? "rgba(255,255,255,0.25)" : "rgba(255,255,255,0.5)",
                    boxShadow: isMyTurn ? `0 0 6px ${c.color}66` : "none",
                    opacity: hasActed ? 0.5 : 1,
                  }}>
                    {isMyTurn && <span style={{ fontSize: 9 }}>▶</span>}
                    {hasActed && <span style={{ fontSize: 9 }}>✓</span>}
                    {(() => {
                      const img = c.key.startsWith("p_")
                        ? avatars[parseInt(c.key.replace("p_",""))]
                        : ((npcAvatars || {})[c.name] || (npcAvatars || {})[c.key.replace("e_","")]);
                      return img ? (
                        <img src={`data:image/png;base64,${img}`}
                          style={{ width: 16, height: 16, borderRadius: "50%", objectFit: "cover", flexShrink: 0 }} />
                      ) : null;
                    })()}
                    <span style={{ opacity: 0.5 }}>{i + 1}.</span>
                    <span>{c.name}</span>
                    <span style={{ opacity: 0.4, fontSize: 10 }}>({c.speed.toFixed(2)})</span>
                  </div>
                );
              })}
              <span style={{
                marginLeft: "auto", fontSize: 10, fontWeight: 800, flexShrink: 0,
                color: isPlayerTurn ? "var(--accent,#a855f7)" : "#ef4444",
                textTransform: "uppercase", letterSpacing: 0.5,
              }}>
                {isPlayerTurn ? "▶ Turno giocatori" : "⚔ Turno nemici"}
              </span>
            </div>
          );
        })()}

        <div className="hex-map-content" style={{ overflowX: "auto", overflowY: "auto", maxHeight: "55vh" }}>
          {/* legenda terreni */}
          <div style={{ display: "flex", gap: 12, padding: "6px 14px", fontSize: 10, color: "rgba(255,255,255,0.4)", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
            <span>⬡ Normale</span>
            <span style={{ color: "#4ade80" }}>⬡ Copertura (+2 difesa)</span>
            <span style={{ color: "#b4823c" }}>⬡ Difficile (×2 mov)</span>
            <span style={{ color: "#888" }}>⬡ Muro</span>
          </div>

          {/* contenitore relativo per sovrapporre img + svg */}
          <div style={{ position: "relative", width: svgWidth, height: svgHeight, flexShrink: 0 }}>
            {/* sfondo immagine — fuori dall'SVG così il browser gestisce qualsiasi formato */}
            {bgImage ? (
              <>
                <img
                  src={`data:image/jpeg;base64,${bgImage}`}
                  alt=""
                  style={{
                    position: "absolute", inset: 0, width: "100%", height: "100%",
                    objectFit: "cover", opacity: 0.5, pointerEvents: "none",
                  }}
                  onError={e => { e.currentTarget.src = `data:image/png;base64,${bgImage}`; }}
                />
                <div style={{
                  position: "absolute", inset: 0,
                  background: "rgba(8,8,16,0.4)", pointerEvents: "none",
                }} />
              </>
            ) : (
              <div style={{
                position: "absolute", inset: 0,
                background: mapSpec.theme?.base || "#0e0f18", pointerEvents: "none",
              }} />
            )}

          <svg
            ref={svgRef}
            width={svgWidth}
            height={svgHeight}
            style={{ position: "absolute", inset: 0, display: "block" }}
            onClick={e => {
              const rect = svgRef.current.getBoundingClientRect();
              const mx = e.clientX - rect.left;
              const my = e.clientY - rect.top;
              let best = null, bestD = Infinity;
              for (let c = 0; c < mapCols; c++) {
                for (let r = 0; r < mapRows; r++) {
                  const { x, y } = hexCenter(c, r);
                  const d = Math.hypot(mx - x, my - y);
                  if (d < bestD) { bestD = d; best = { c, r }; }
                }
              }
              if (best && bestD < HEX_SIZE * 1.2) clickHex(best.c, best.r);
            }}
          >
            <defs>
              <radialGradient id="battle-vignette" cx="50%" cy="50%" r="70%">
                <stop offset="0%" stopColor="#000" stopOpacity="0" />
                <stop offset="72%" stopColor="#000" stopOpacity="0.08" />
                <stop offset="100%" stopColor="#000" stopOpacity="0.55" />
              </radialGradient>
            </defs>
            {!bgImage && renderBattleMapDecor(mapSpec)}

            {/* hex grid */}
            {Array.from({ length: mapCols }, (_, col) =>
              Array.from({ length: mapRows }, (_, row) => {
                const { x, y } = hexCenter(col, row);
                const t = terrain[`${col},${row}`] || 0;
                const inReach = reachable.has(`${col},${row}`);
                return (
                  <path
                    key={`${col},${row}`}
                    d={hexPath(x, y, HEX_SIZE - 1)}
                    fill={inReach ? "rgba(99,102,241,0.25)" : terrainColors[t]}
                    stroke={inReach ? "#818cf8" : terrainStroke[t]}
                    strokeWidth={inReach ? 1.5 : 1}
                  />
                );
              })
            )}

            {/* token */}
            {Object.entries(positions).map(([key, pos]) => {
              const { x, y } = hexCenter(pos.col, pos.row);
              const isPlayer = key.startsWith("p_");
              const pid = isPlayer ? parseInt(key.replace("p_", "")) : null;
              const eid = !isPlayer ? key.replace("e_", "") : null;
              const entity = isPlayer
                ? players.find(p => p.id === pid)
                : enemies.find(e => e.id === eid);
              if (!entity) return null;
              const isSelected = selected === key;
              const isDead = entity.hp <= 0 || entity.status === "sconfitto";
              const color = isDead ? "#555" : isPlayer ? "var(--accent,#a855f7)" : "#ef4444";
              const label = (entity.name || "?")[0].toUpperCase();
              const inCover = (terrain[`${pos.col},${pos.row}`] || 0) === 1;

              const anim = animating[key];
              const animStyle = anim === "move"
                ? { transform: `scale(1.18)`, transition: "transform 0.18s ease-out" }
                : anim === "attack"
                  ? { transform: `scale(1.25)`, transition: "transform 0.12s ease-in-out", filter: "brightness(1.6)" }
                  : {};

              // cerca per nome (chiave usata al momento della generazione)
              const entityName = entity?.name || "";
              const tokenImg = isPlayer ? avatars[pid] : ((npcAvatars || {})[entityName] || (npcAvatars || {})[eid]);
              const clipId = `clip-${key}`;
              const r = HEX_SIZE * 0.55;

              return (
                <g key={key} style={{ cursor: "pointer", ...animStyle }} onClick={e => { e.stopPropagation(); selectToken(key); }}>
                  <defs>
                    <clipPath id={clipId}>
                      <circle cx={x} cy={y} r={r} />
                    </clipPath>
                  </defs>
                  {/* cerchio base */}
                  <circle cx={x} cy={y} r={r}
                    fill={tokenImg ? "none" : color} fillOpacity={isDead ? 0.3 : 0.85}
                    stroke={isSelected ? "#fff" : anim === "attack" ? "#facc15" : color}
                    strokeWidth={isSelected ? 3 : anim === "attack" ? 3 : 2}
                  />
                  {/* foto circolare se disponibile */}
                  {tokenImg ? (
                    <image
                      href={`data:image/png;base64,${tokenImg}`}
                      x={x - r} y={y - r} width={r * 2} height={r * 2}
                      clipPath={`url(#${clipId})`}
                      opacity={isDead ? 0.3 : 1}
                      style={{ pointerEvents: "none" }}
                    />
                  ) : (
                    <text x={x} y={y + 1} textAnchor="middle" dominantBaseline="middle"
                      fontSize={13} fontWeight="bold" fill="#fff" style={{ pointerEvents: "none" }}>
                      {label}
                    </text>
                  )}
                  {/* facing */}
                  <path d={facingTriangle(x, y, pos.facing || 0, r, "#fff")}
                    fill="rgba(255,255,255,0.8)" style={{ pointerEvents: "none" }} />
                  {/* copertura badge */}
                  {inCover && (
                    <text x={x + HEX_SIZE * 0.4} y={y - HEX_SIZE * 0.4} fontSize={10} fill="#4ade80">🛡</text>
                  )}
                  {/* stordito / prone */}
                  {entity.stunned && (
                    <text x={x - HEX_SIZE * 0.45} y={y - HEX_SIZE * 0.4} fontSize={11} fill="#facc15" title="Stordito">💫</text>
                  )}
                  {entity.prone && !entity.stunned && (
                    <text x={x - HEX_SIZE * 0.45} y={y - HEX_SIZE * 0.4} fontSize={11} fill="#f97316" title="A terra">⬇</text>
                  )}
                  {/* shock badge */}
                  {entity.shock_penalty > 0 && (
                    <text x={x + HEX_SIZE * 0.4} y={y + HEX_SIZE * 0.4} fontSize={9} fill="#f59e0b" title={`Shock −${entity.shock_penalty}`}>⚡</text>
                  )}
                  {/* hp bar sotto */}
                  {entity.max_hp > 0 && (
                    <>
                      <rect x={x - 14} y={y + HEX_SIZE * 0.6} width={28} height={3} rx={1.5}
                        fill="rgba(0,0,0,0.5)" />
                      <rect x={x - 14} y={y + HEX_SIZE * 0.6}
                        width={28 * Math.max(0, entity.hp / entity.max_hp)} height={3} rx={1.5}
                        fill={entity.hp / entity.max_hp > 0.5 ? "#4ade80" : entity.hp / entity.max_hp > 0.25 ? "#facc15" : "#ef4444"} />
                    </>
                  )}
                </g>
              );
            })}
          </svg>
          </div>{/* fine div relativo sfondo+svg */}
        </div>{/* fine hex-map-content */}

        {/* barra azioni */}
        <div style={{ padding: "8px 12px", borderTop: "1px solid rgba(255,255,255,0.07)", display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
          {selected && selPos && selectedIsActivePlayer && (
            <>
              <button onClick={startMove} style={{
                padding: "5px 12px", borderRadius: 7, border: "none", fontSize: 12, fontWeight: 700, cursor: "pointer",
                background: mode === "move" ? "#6366f1" : "rgba(99,102,241,0.2)", color: mode === "move" ? "#fff" : "#818cf8",
              }}>👣 Muovi ({getBasicMove(selected)} yd)</button>
              {(() => {
                const pid = selected?.startsWith("p_") ? parseInt(selected.replace("p_","")) : null;
                const selPlayer = pid ? players.find(p => p.id === pid) : null;
                return <>
                  {/* Attacca normale */}
                  <button onClick={() => { setAttackActionType("normal"); startAttack(); }} style={{
                    padding: "5px 12px", borderRadius: 7, border: "none", fontSize: 12, fontWeight: 700, cursor: "pointer",
                    background: mode === "attack" && attackActionType === "normal" ? "#ef4444" : "rgba(239,68,68,0.2)",
                    color: mode === "attack" && attackActionType === "normal" ? "#fff" : "#f87171",
                  }}>⚔ Attacca</button>
                  {/* Attacco Totale: +4 attacco, no difesa */}
                  {selPlayer && (
                    <button onClick={() => { setAttackActionType("all_out_attack"); startAttack(); }}
                      title="Attacco Totale: +4 al tiro, ma non puoi difenderti questo turno"
                      style={{
                        padding: "5px 12px", borderRadius: 7, border: "1px solid #dc2626", fontSize: 12, fontWeight: 700, cursor: "pointer",
                        background: mode === "attack" && attackActionType === "all_out_attack" ? "#dc2626" : "rgba(220,38,38,0.15)",
                        color: mode === "attack" && attackActionType === "all_out_attack" ? "#fff" : "#fca5a5",
                      }}>⚔⚔ Totale</button>
                  )}
                  {/* Alzati se prone */}
                  {selPlayer?.prone && (
                    <button onClick={() => onStandUp && onStandUp(selPlayer.id)}
                      title="Usa l'azione per alzarsi da terra"
                      style={{ padding: "5px 11px", borderRadius: 7, border: "1px solid #f97316", background: "rgba(249,115,22,0.15)", color: "#fb923c", fontWeight: 700, cursor: "pointer", fontSize: 12 }}>
                      ⬆ Alzati
                    </button>
                  )}
                  {/* Stordito: no attacco */}
                  {selPlayer?.stunned && (
                    <span style={{ fontSize: 11, color: "#facc15", fontWeight: 700 }}>💫 Stordito — tiro SA per recuperare</span>
                  )}
                  {/* Azioni extra GURPS */}
                  <button onClick={() => {
                    setCombatLog(prev => [...prev, `${selPlayer?.name || "?"} si mette in copertura (+2 difesa fino al prossimo turno).`]);
                    advanceTurn(pid, true);
                  }} title="Concentra tutte le energie sulla difesa (+2 a tutte le difese, nessun attacco)"
                    style={{ padding: "5px 11px", borderRadius: 7, border: "1px solid #0891b2", background: "rgba(8,145,178,0.15)", color: "#67e8f9", fontWeight: 700, cursor: "pointer", fontSize: 12 }}>
                    🛡 Copertura
                  </button>
                  {selPlayer && (selPlayer.items || []).some(it => /medkit|kit|benda|pronto soccorso|medikit/i.test(it)) && (
                    <button onClick={async () => {
                      const injured = players.filter(p => p.hp < p.max_hp && p.hp > 0);
                      const target = injured.find(p => p.id !== selPlayer.id) || injured[0];
                      if (!target) { setCombatLog(prev => [...prev, "Nessun alleato ferito nelle vicinanze."]); return; }
                      const result = await onAttack(selPlayer, "curare", null, "normal");
                      if (result) setCombatLog(prev => [...prev, `${selPlayer.name} cura ${target.name}.`]);
                      advanceTurn(pid, true);
                    }} title="Usa medkit per curare un alleato ferito (richiede medkit negli oggetti)"
                      style={{ padding: "5px 11px", borderRadius: 7, border: "1px solid #16a34a", background: "rgba(22,163,74,0.15)", color: "#4ade80", fontWeight: 700, cursor: "pointer", fontSize: 12 }}>
                      💊 Cura
                    </button>
                  )}
                  <button onClick={() => {
                    const ally = players.find(p => p.id !== selPlayer?.id && p.hp > 0);
                    const msg = ally ? `${selPlayer?.name} supporta ${ally.name} (+1 al prossimo tiro).` : `${selPlayer?.name} si prepara.`;
                    setCombatLog(prev => [...prev, msg]);
                    advanceTurn(pid, true);
                  }} title="Aiuta un alleato vicino (+1 al suo prossimo tiro) o si prepara"
                    style={{ padding: "5px 11px", borderRadius: 7, border: "1px solid #7c3aed", background: "rgba(124,58,237,0.15)", color: "#c4b5fd", fontWeight: 700, cursor: "pointer", fontSize: 12 }}>
                    🤝 Aiuta
                  </button>
                </>;
              })()}
              <button onClick={() => rotateFacing(selected, -1)} style={{ padding: "5px 9px", borderRadius: 7, border: "1px solid rgba(255,255,255,0.1)", background: "none", color: "rgba(255,255,255,0.5)", cursor: "pointer", fontSize: 12 }}>↺</button>
              <button onClick={() => rotateFacing(selected, 1)} style={{ padding: "5px 9px", borderRadius: 7, border: "1px solid rgba(255,255,255,0.1)", background: "none", color: "rgba(255,255,255,0.5)", cursor: "pointer", fontSize: 12 }}>↻</button>
              <button onClick={() => { setSelected(null); setMode("select"); setReachable(new Set()); }} style={{ padding: "5px 9px", borderRadius: 7, border: "1px solid rgba(255,255,255,0.1)", background: "none", color: "rgba(255,255,255,0.4)", cursor: "pointer", fontSize: 12 }}>✕</button>
            </>
          )}
          {selected && selPos && selectedIsEnemy && !pendingAttack && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <span style={{ fontSize: 12, color: "#fca5a5", fontWeight: 700 }}>
                Bersaglio selezionato: {selName}
              </span>
              <span style={{ fontSize: 11, color: "rgba(255,255,255,0.45)" }}>
                Seleziona il token di {players.find(p => p.id === activePlayerId)?.name || "chi agisce"} per muovere o attaccare.
              </span>
              <button onClick={() => { setSelected(null); setMode("select"); setReachable(new Set()); }} style={{ padding: "5px 9px", borderRadius: 7, border: "1px solid rgba(255,255,255,0.1)", background: "none", color: "rgba(255,255,255,0.4)", cursor: "pointer", fontSize: 12 }}>✕</button>
            </div>
          )}
          {selected && selPos && selectedIsOtherPlayer && !pendingAttack && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <span style={{ fontSize: 12, color: "rgba(255,255,255,0.65)", fontWeight: 700 }}>
                {selName} non è il personaggio attivo.
              </span>
              <button onClick={() => setSelected(`p_${activePlayerId}`)} style={{ padding: "5px 11px", borderRadius: 7, border: "1px solid rgba(99,102,241,0.45)", background: "rgba(99,102,241,0.16)", color: "#a5b4fc", fontWeight: 700, cursor: "pointer", fontSize: 12 }}>
                Seleziona personaggio attivo
              </button>
            </div>
          )}
          {!selected && !pendingAttack && (() => {
            const alivePlayers = players.filter(p => p.hp > 0 && p.status !== "sconfitto" && p.status !== "morto");
            const activeName = players.find(p => p.id === activePlayerId)?.name || "?";
            const remaining = alivePlayers.filter(p => !actedThisRound.has(p.id));
            return (
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 12, color: "var(--accent,#a855f7)", fontWeight: 700 }}>
                  ▶ {activeName} — seleziona il tuo token
                </span>
                {alivePlayers.length > 1 && (
                  <span style={{ fontSize: 10, color: "rgba(255,255,255,0.35)" }}>
                    ({remaining.length}/{alivePlayers.length} da agire)
                  </span>
                )}
              </div>
            );
          })()}

          {/* Fine turno — appare dopo aver selezionato un token del giocatore attivo */}
          {selected?.startsWith("p_") && parseInt(selected.replace("p_","")) === activePlayerId && !pendingAttack && (
            <button
              onClick={() => advanceTurn(activePlayerId)}
              style={{
                marginLeft: "auto", padding: "5px 14px", borderRadius: 7,
                border: "1px solid rgba(255,255,255,0.2)", background: "rgba(255,255,255,0.08)",
                color: "rgba(255,255,255,0.6)", fontWeight: 700, cursor: "pointer", fontSize: 12,
              }}
            >Fine turno →</button>
          )}

          {/* difesa */}
          {pendingAttack && (
            <div style={{ marginLeft: "auto", display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: "#facc15" }}>
                🛡 Difendi! ({defVal}{lastAttackCoverBonus > 0 ? ` +${lastAttackCoverBonus} cop.` : ""}{lastAttackIsRear ? " [RETRO!]" : ""})
              </span>
              {lastAttackIsRear && (
                <span style={{ fontSize: 11, color: "#ef4444", fontWeight: 700 }}>⚠ Attacco da retro — difesa annullata!</span>
              )}
              {[["dodge","Schiva","#7c3aed"],["parry","Para","#2563eb"],["block","Blocca","#0f766e"]].map(([dt, label, bg]) => (
                <button key={dt}
                  onClick={() => Promise.resolve(onDefend(dt, "normal", "", lastAttackCoverBonus, lastAttackIsRear, tacticalSnapshot())).then(applyNpcTurnResult)}
                  style={{ padding: "5px 11px", borderRadius: 7, border: "none", background: bg, color: "#fff", fontWeight: 700, cursor: "pointer", fontSize: 12 }}
                >{label}</button>
              ))}
              <button
                onClick={() => Promise.resolve(onDefend("dodge", "all_out_defense", "", lastAttackCoverBonus, lastAttackIsRear, tacticalSnapshot())).then(applyNpcTurnResult)}
                title="Difesa Totale: +2 difesa ma non puoi attaccare questo turno"
                style={{ padding: "5px 11px", borderRadius: 7, border: "1px solid #4ade80", background: "rgba(74,222,128,0.15)", color: "#4ade80", fontWeight: 700, cursor: "pointer", fontSize: 12 }}
              >🛡🛡 Difesa Totale</button>
            </div>
          )}
        </div>

        {/* log ultimo movimento */}
        {combatLog.length > 0 && (
          <div style={{ padding: "4px 14px 8px", fontSize: 10, color: "rgba(255,255,255,0.3)", borderTop: "1px solid rgba(255,255,255,0.05)" }}>
            {combatLog[combatLog.length - 1]}
          </div>
        )}
      </div>
    </div>
  );
}

function HpBar({ hp, maxHp }) {
  const pct = maxHp > 0 ? Math.max(0, Math.min(100, Math.round((hp / maxHp) * 100))) : 0;
  const color = pct > 60 ? "#4ade80" : pct > 30 ? "#facc15" : "#ef4444";
  return (
    <div style={{ height: 4, borderRadius: 2, background: "rgba(0,0,0,0.35)", marginTop: 3, width: "100%", overflow: "hidden" }}>
      <div style={{ height: "100%", width: `${pct}%`, background: color, transition: "width 0.3s" }} />
    </div>
  );
}

// ─── StrategicMapPanel ─────────────────────────────────────────────────────

function StrategicMapPanel({ mapState, onClose, onMove, bgImage, onRequestImage, loadingImage, adventure, cluesFound }) {
  const [hovered, setHovered] = useState(null); // node id

  if (!mapState || !mapState.nodes) return null;

  const nodes = Object.values(mapState.nodes);
  const currentId = mapState.current_node_id;
  const currentNode = mapState.nodes[currentId];

  // reachable from current node (direct connections that aren't blocked/destroyed)
  const reachable = new Set((currentNode?.connections || []).filter(cid => {
    const n = mapState.nodes[cid];
    return n && !n.blocked && !n.destroyed;
  }));

  // compute SVG layout — use a fixed canvas of 680×320 with padding
  const CANVAS_W = 680;
  const CANVAS_H = 320;
  const PAD = 44;
  const maxGX = Math.max(...nodes.map(n => n.grid_x), 1);
  const maxGY = Math.max(...nodes.map(n => n.grid_y), 1);
  const cellW = (CANVAS_W - PAD * 2) / Math.max(maxGX, 1);
  const cellH = (CANVAS_H - PAD * 2) / Math.max(maxGY, 1);

  function nodeX(n) { return PAD + n.grid_x * cellW; }
  function nodeY(n) { return PAD + n.grid_y * cellH; }

  // build deduplicated connection lines
  const lines = [];
  const seen = new Set();
  nodes.forEach(n => {
    (n.connections || []).forEach(cid => {
      const key = [n.id, cid].sort().join("|");
      if (!seen.has(key)) {
        seen.add(key);
        const t = mapState.nodes[cid];
        if (t) lines.push({ x1: nodeX(n), y1: nodeY(n), x2: nodeX(t), y2: nodeY(t), key });
      }
    });
  });

  const hoveredNode = hovered ? mapState.nodes[hovered] : null;

  return (
    <div style={{
      position: "relative", border: "1px solid var(--border)",
      borderRadius: 10, margin: "0 16px 10px", overflow: "hidden",
      background: "#0a0a12",
    }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "8px 12px", background: "rgba(0,0,0,0.7)", zIndex: 4,
        borderBottom: "1px solid var(--border)",
      }}>
        <span style={{ fontSize: 13, fontWeight: 800, color: "var(--text-h)" }}>🗺 Mappa Strategica</span>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {!bgImage && (
            <button onClick={onRequestImage} disabled={loadingImage} style={{
              fontSize: 11, padding: "3px 9px", borderRadius: 6, cursor: loadingImage ? "default" : "pointer",
              background: "var(--accent-bg)", border: "1px solid var(--accent-border)",
              color: "var(--accent)", opacity: loadingImage ? 0.6 : 1,
            }}>
              {loadingImage ? "⏳ Generazione..." : "🎨 Genera immagine"}
            </button>
          )}
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text)", fontSize: 18, lineHeight: 1 }}>×</button>
        </div>
      </div>

      {/* Map canvas */}
      <div style={{ position: "relative", height: CANVAS_H, overflowX: "auto" }}>
        {/* Background image */}
        {bgImage && (
          <img src={`data:image/png;base64,${bgImage}`} alt="mappa" style={{
            position: "absolute", inset: 0, width: "100%", height: "100%",
            objectFit: "cover", opacity: 0.45, pointerEvents: "none",
          }} />
        )}
        {/* Dark overlay for readability */}
        <div style={{
          position: "absolute", inset: 0,
          background: bgImage
            ? "linear-gradient(180deg, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0.55) 100%)"
            : "linear-gradient(135deg, #0d0d1a 0%, #1a0a2e 100%)",
          pointerEvents: "none",
        }} />

        {/* SVG overlay */}
        <svg width={CANVAS_W} height={CANVAS_H} style={{ position: "absolute", inset: 0, display: "block" }}>
          <defs>
            <filter id="glow">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
          </defs>

          {/* Connection lines */}
          {lines.map((l, i) => (
            <line key={i} x1={l.x1} y1={l.y1} x2={l.x2} y2={l.y2}
              stroke="rgba(124,58,237,0.35)" strokeWidth={1.5} strokeDasharray="4 3" />
          ))}

          {/* Nodes */}
          {nodes.map(n => {
            const cx = nodeX(n);
            const cy = nodeY(n);
            const isCurrent = n.id === currentId;
            const isReachable = reachable.has(n.id);
            const isVisited = n.visited;
            const isObjective = n.is_objective;
            const isFinal = n.is_final;
            const hasEnemy = n.contains_enemy;
            const isBlocked = n.blocked || n.destroyed;
            const isHovered = n.id === hovered;

            // Node appearance
            let fill = isBlocked ? "rgba(127,29,29,0.5)"
              : isCurrent ? "rgba(124,58,237,0.85)"
              : isReachable ? "rgba(34,197,94,0.25)"
              : isVisited ? "rgba(55,65,81,0.7)"
              : "rgba(17,24,39,0.7)";
            let stroke = isFinal ? "#facc15"
              : isObjective ? "#fb923c"
              : hasEnemy ? "#ef4444"
              : isReachable ? "#22c55e"
              : isCurrent ? "#a78bfa"
              : "rgba(75,85,99,0.8)";
            let strokeW = isCurrent || isReachable || isObjective || isFinal ? 2.5 : 1.5;
            const r = isCurrent ? 20 : 15;

            return (
              <g key={n.id}
                onClick={() => !isBlocked && isReachable && onMove(n.id)}
                onMouseEnter={() => setHovered(n.id)}
                onMouseLeave={() => setHovered(null)}
                style={{ cursor: isReachable && !isBlocked ? "pointer" : "default" }}
                filter={isCurrent ? "url(#glow)" : undefined}
              >
                {/* Reachable pulse ring */}
                {isReachable && (
                  <circle cx={cx} cy={cy} r={r + 5} fill="none"
                    stroke="#22c55e" strokeWidth={1} opacity={0.4} />
                )}
                <circle cx={cx} cy={cy} r={r} fill={fill} stroke={stroke} strokeWidth={strokeW} />

                {/* Icons inside node */}
                {isCurrent && (
                  <text x={cx} y={cy + 5} textAnchor="middle" fontSize={14} fill="#fff">◉</text>
                )}
                {!isCurrent && isFinal && (
                  <text x={cx} y={cy + 5} textAnchor="middle" fontSize={12} fill="#facc15">🏁</text>
                )}
                {!isCurrent && isObjective && !isFinal && (
                  <text x={cx} y={cy + 5} textAnchor="middle" fontSize={12} fill="#fb923c">⭐</text>
                )}
                {!isCurrent && hasEnemy && !isObjective && !isFinal && (
                  <text x={cx} y={cy + 5} textAnchor="middle" fontSize={11} fill="#ef4444">⚔</text>
                )}
                {isBlocked && (
                  <text x={cx} y={cy + 5} textAnchor="middle" fontSize={11} fill="#ef4444">✕</text>
                )}

                {/* Label */}
                <text x={cx} y={cy + r + 14} textAnchor="middle" fontSize={9}
                  fill={isCurrent ? "#e9d5ff" : isReachable ? "#86efac" : "rgba(156,163,175,0.9)"}
                  style={{ userSelect: "none", fontWeight: isCurrent ? 700 : 400 }}>
                  {(n.name || n.id).slice(0, 14)}
                </text>

                {/* Hover highlight */}
                {isHovered && !isCurrent && (
                  <circle cx={cx} cy={cy} r={r + 2} fill="none" stroke="white" strokeWidth={1} opacity={0.5} />
                )}
              </g>
            );
          })}

          {/* Team token on current node */}
          {currentNode && (() => {
            const cx = nodeX(currentNode);
            const cy = nodeY(currentNode);
            return (
              <g>
                <circle cx={cx} cy={cy - 28} r={10} fill="#7c3aed" stroke="#c4b5fd" strokeWidth={2} />
                <text x={cx} y={cy - 24} textAnchor="middle" fontSize={11} fill="#fff">👥</text>
              </g>
            );
          })()}
        </svg>
      </div>

      {/* Hover tooltip */}
      {hoveredNode && (() => {
        const nodeName = hoveredNode.name || "";
        // Indizi trovabili in questa location
        const nodeClues = (adventure?.clues || []).filter(c =>
          c.location && c.location.toLowerCase().includes(nodeName.toLowerCase().slice(0, 6))
        );
        // NPC presenti in questa location
        const nodeNpcs = (adventure?.npcs || []).filter(n =>
          n.location && n.location.toLowerCase().includes(nodeName.toLowerCase().slice(0, 6))
        );
        const isReachableNode = reachable.has(hoveredNode.id);
        return (
          <div style={{
            padding: "10px 14px", background: "rgba(0,0,0,0.92)",
            borderTop: "1px solid var(--border)",
          }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 4 }}>
              <span style={{ fontWeight: 700, fontSize: 13, color: "var(--text-h)" }}>{hoveredNode.name}</span>
              {hoveredNode.kind && <span style={{ fontSize: 10, color: "var(--text)", opacity: 0.6 }}>{hoveredNode.kind}</span>}
              <div style={{ display: "flex", gap: 4, marginLeft: "auto", flexWrap: "wrap" }}>
                {hoveredNode.contains_enemy && <Badge icon="⚔" label="Nemici" color="#ef4444" size="sm" />}
                {hoveredNode.contains_clue && <Badge icon="🔍" label="Indizio" color="#60a5fa" size="sm" />}
                {hoveredNode.is_objective && <Badge icon="⭐" label="Obiettivo" color="#fb923c" size="sm" />}
                {hoveredNode.is_final && <Badge icon="🏁" label="Finale" color="#facc15" size="sm" />}
                {hoveredNode.blocked && <Badge icon="🚫" label="Bloccato" color="#6b7280" size="sm" />}
                {hoveredNode.visited && <Badge icon="✓" label="Visitato" color="#4ade80" size="sm" />}
              </div>
            </div>
            {hoveredNode.description && (
              <div style={{ fontSize: 11, color: "var(--text)", opacity: 0.8, marginBottom: 6, lineHeight: 1.4 }}>{hoveredNode.description}</div>
            )}
            {nodeNpcs.length > 0 && (
              <div style={{ fontSize: 11, color: "#c4b5fd", marginBottom: 3 }}>
                👤 {nodeNpcs.map(n => n.name).join(", ")}
              </div>
            )}
            {nodeClues.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                {nodeClues.map(c => {
                  const found = (cluesFound || []).includes(c.id);
                  return (
                    <div key={c.id} style={{ fontSize: 11, color: found ? "#4ade80" : "#93c5fd" }}>
                      {found ? "🔍" : "⬜"} {found ? c.text : c.text}
                    </div>
                  );
                })}
              </div>
            )}
            {isReachableNode && !hoveredNode.blocked && (
              <div style={{ fontSize: 11, color: "#22c55e", marginTop: 6, fontWeight: 700 }}>
                → Click per spostarsi qui (genera scena)
              </div>
            )}
          </div>
        );
      })()}

      {/* Legend */}
      <div style={{
        padding: "6px 12px", background: "rgba(0,0,0,0.5)", borderTop: "1px solid var(--border)",
        display: "flex", gap: 12, flexWrap: "wrap",
      }}>
        <span style={{ fontSize: 10, color: "rgba(167,139,250,0.9)" }}>◉ Posizione attuale</span>
        <span style={{ fontSize: 10, color: "rgba(34,197,94,0.9)" }}>○ Raggiungibile (click per muoversi)</span>
        <span style={{ fontSize: 10, color: "rgba(251,146,60,0.9)" }}>⭐ Obiettivo</span>
        <span style={{ fontSize: 10, color: "rgba(239,68,68,0.9)" }}>⚔ Nemici presenti</span>
      </div>
    </div>
  );
}

// ─── Game screen ───────────────────────────────────────────────────────────

function GameScreen({ genre, players: initialPlayers, avatars = {}, adventure = null, provider = "claude", imageProvider = "auto", preloadedMapImage = null, onRestart }) {
  const [players, setPlayers] = useState(initialPlayers);
  const [messages, setMessages] = useState([]);
  const [options, setOptions] = useState([]);
  const [pendingOption, setPendingOption] = useState(null);
  const [customText, setCustomText] = useState("");
  const [activePlayerId, setActivePlayerId] = useState(initialPlayers[0]?.id);
  const [loading, setLoading] = useState(false);
  const [storyOver, setStoryOver] = useState(false);
  const [victory, setVictory] = useState(false);
  const [personalVictories, setPersonalVictories] = useState({});
  const [history, setHistory] = useState([]);
  const [showPanel, setShowPanel] = useState(!!adventure);
  const [showSecrets, setShowSecrets] = useState(false);
  const [startupLoading, setStartupLoading] = useState(true);
  const [gameStateData, setGameStateData] = useState({
    clues_found: [],
    npc_statuses: {},
    threat_level: 0,
    open_threads: [],
    turn: 1,
    in_combat: false,
    world_npcs: [],
  });
  const [sceneState, setSceneState] = useState(null);
  const [combatEntities, setCombatEntities] = useState([]); // entity combattimento persistenti, non sovrascritte dal fetch
  const [combatBgImage, setCombatBgImage] = useState(null);
  const [showCombatMap, setShowCombatMap] = useState(false);
  const [lastCombatLog, setLastCombatLog] = useState(null);
  const [mapState, setMapState] = useState(null);
  const [showMap, setShowMap] = useState(false);
  const [strategicMapImage, setStrategicMapImage] = useState(preloadedMapImage);
  const [loadingStrategicImage, setLoadingStrategicImage] = useState(false);
  const [pendingAttack, setPendingAttack] = useState(null);
  const [combatAttacker, setCombatAttacker] = useState(null);
  const [combatTarget, setCombatTarget] = useState(null);
  const [npcAvatars, setNpcAvatars] = useState({});  // entity_id → base64
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const messagesRef = useRef([]);

  // keep ref in sync
  const _setMessages = (updater) => {
    setMessages(prev => {
      const next = typeof updater === "function" ? updater(prev) : updater;
      messagesRef.current = next;
      return next;
    });
  };

  const playerDicts = players.map(p => ({
    id: p.id, name: p.name, role: p.role,
    stats: p.stats, skills: p.skills,
    advantages: p.advantages || [], disadvantages: p.disadvantages || [],
  }));

  function applyStateUpdates(updates) {
    if (!updates) return;
    setGameStateData(prev => {
      const newClues = [...new Set([...prev.clues_found, ...(updates.clues_found || [])])];
      const newNpcStatuses = { ...prev.npc_statuses };
      for (const u of (updates.npc_updates || [])) {
        newNpcStatuses[u.id] = { ...newNpcStatuses[u.id], ...u };
      }
      const existing = prev.open_threads.filter(t => !(updates.closed_threads || []).includes(t));
      const existingSet = new Set(existing.map(t => t.trim().toLowerCase()));
      const added = (updates.new_threads || []).filter(t => !existingSet.has(t.trim().toLowerCase()));
      const newThreads = [...existing, ...added];
      return {
        ...prev,
        clues_found: newClues,
        npc_statuses: newNpcStatuses,
        threat_level: prev.threat_level + (updates.threat_increase || 0),
        open_threads: newThreads,
        turn: prev.turn + 1,
        in_combat: updates.combat_over ? false : (updates.activate_combat || prev.in_combat),
      };
    });
    // Apre la mappa tattica automaticamente all'inizio del combattimento
    if (updates.activate_combat) setShowCombatMap(true);
    // Chiude la mappa tattica quando il combattimento finisce e resetta l'immagine per il prossimo
    if (updates.combat_over) { setShowCombatMap(false); setCombatBgImage(null); }
  }

  async function fetchGameState() {
    try {
      const gs = await fetch(`${API_URL}/game/state`).then(r => r.json());
      if (gs.scene) setSceneState(gs.scene);
      if (gs.map_state) setMapState(gs.map_state);
      if (gs.pending_attack !== undefined) setPendingAttack(gs.pending_attack);
      if (gs.world_npcs) setGameStateData(prev => ({ ...prev, world_npcs: gs.world_npcs }));
      if (gs.players?.length > 0) setPlayers(prev => gs.players.map(gp => {
        const local = prev.find(lp => lp.id === gp.id);
        return local ? { ...gp, backstory: gp.backstory || local.backstory || "", motivation: gp.motivation || local.motivation || "" } : gp;
      }));
      if (gs.last_roll_details?.length > 0) {
        _setMessages(prev => {
          const lastMasterIdx = [...prev].reverse().findIndex(m => m.role === "master");
          if (lastMasterIdx === -1) return prev;
          const idx = prev.length - 1 - lastMasterIdx;
          const updated = [...prev];
          updated[idx] = { ...updated[idx], roll_details: gs.last_roll_details };
          return updated;
        });
      }
    } catch (_) {}
  }

  // Aggiorna HP di una entity nelle combatEntities dopo un colpo
  function _applyCombatDamage(entityId, netDamage) {
    if (!entityId || netDamage <= 0) return;
    setCombatEntities(prev => prev.map(e =>
      e.id === entityId ? { ...e, hp: Math.max(0, (e.hp || e.max_hp || 10) - netDamage) } : e
    ));
  }

  function _syncCombatEntitiesFromScene(scene) {
    const sceneEntities = scene?.entities;
    if (!Array.isArray(sceneEntities)) return false;
    const enemies = sceneEntities.filter(e => e.type === "enemy");
    if (enemies.length === 0) return false;
    // Merge: aggiorna HP/status dal backend ma non sovrascrive entità non presenti
    setCombatEntities(prev => {
      const byId = Object.fromEntries(enemies.map(e => [e.id, e]));
      // Aggiorna entità esistenti con dati freschi; aggiungi nuove; rimuovi morte
      const merged = prev
        .map(e => byId[e.id] ? { ...e, ...byId[e.id] } : e)
        .filter(e => byId[e.id] !== undefined || e.hp > 0);
      // Aggiungi entità nuove non ancora in prev
      const prevIds = new Set(prev.map(e => e.id));
      for (const e of enemies) {
        if (!prevIds.has(e.id)) merged.push(e);
      }
      return merged;
    });
    return true;
  }

  async function _fetchCombatNarration(combat_log) {
    try {
      const res = await fetch(`${API_URL}/game/combat/narrate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ combat_log, genre, adventure: adventure || {} }),
      }).then(r => r.json());
      if (res.narrative) {
        _setMessages(prev => [...prev, { role: "master", name: "Master", text: res.narrative, isCombatNarration: true }]);
      }
    } catch (_) {}
  }

  async function _runNpcTurn(tacticalContext = null) {
    try {
      const fetchOptions = tacticalContext
        ? {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(tacticalContext),
          }
        : { method: "POST" };
      const res = await fetch(`${API_URL}/game/combat/npc-turn`, fetchOptions).then(r => r.json());
      if (res.players) setPlayers(prev => res.players.map(rp => {
        const local = prev.find(lp => lp.id === rp.id);
        return local ? { ...rp, backstory: rp.backstory || local.backstory || "", motivation: rp.motivation || local.motivation || "" } : rp;
      }));
      if (res.error) {
        _setMessages(prev => [...prev, { role: "master", name: "Sistema", text: `Errore turno NPC: ${res.error}`, isCombatNarration: true }]);
        return;
      }
      if (res.scene) {
        setSceneState(res.scene);
        _syncCombatEntitiesFromScene(res.scene);
      }
      for (const log of (res.npc_logs || [])) {
        _setMessages(prev => [...prev, { role: "combat", combat_log: log }]);
        setLastCombatLog(log);
        // Narrativa per ogni azione NPC (colpo, mancato, parata)
        _fetchCombatNarration(log);
      }
      // Avvia attacco NPC su giocatore (pending_attack) — prossimo NPC che non ha già agito
      if (res.pending_attack) setPendingAttack(res.pending_attack);
      return res;
    } catch (_) {}
    return null;
  }

  async function handleAttack(player, actionName, targetEntityId, actionType = "normal", tacticalContext = null) {
    try {
      const res = await fetch(`${API_URL}/game/combat/attack`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          attacker_id: player.id,
          action_name: actionName,
          target_entity_id: targetEntityId,
          action_type: actionType,
        }),
      }).then(r => r.json());
      if (res.error) {
        _setMessages(prev => [...prev, { role: "master", name: "Sistema", text: `Azione non riuscita: ${res.error}`, isCombatNarration: true }]);
        return;
      }
      const syncedEntities = res.scene ? _syncCombatEntitiesFromScene(res.scene) : false;
      if (res.scene) setSceneState(res.scene);
      if (res.pending_attack !== undefined) setPendingAttack(res.pending_attack);
      if (res.players) setPlayers(res.players);
      setCombatAttacker(null);
      setCombatTarget(null);
      if (res.combat_log) {
        setLastCombatLog(res.combat_log);
        _setMessages(prev => [...prev, { role: "combat", combat_log: res.combat_log }]);
        const r = res.combat_log?.result;
        if (r?.net_damage > 0 && !res.pending_attack && !syncedEntities) {
          _applyCombatDamage(targetEntityId, r.net_damage);
        }
        if (!res.pending_attack) {
          // Narrativa per tutti gli esiti (colpo, parata, mancato)
          _fetchCombatNarration(res.combat_log);
          // Turno NPC dopo che il giocatore ha attaccato un'entità
          if (targetEntityId) return await _runNpcTurn(tacticalContext);
        }
      }
    } catch (_) {}
    return null;
  }

  async function handleDefend(defenseType, defenseActionType = "normal", defenseSkill = "", coverBonus = 0, rearAttack = false, tacticalContext = null) {
    try {
      const defender = players.find(p => p.id === activePlayerId) || players[0];
      const res = await fetch(`${API_URL}/game/combat/defend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          player_id: defender.id,
          defense_type: defenseType,
          defense_skill: defenseSkill,
          defense_action_type: defenseActionType,
          cover_bonus: coverBonus,
          rear_attack: rearAttack,
        }),
      }).then(r => r.json());
      if (res.error) {
        _setMessages(prev => [...prev, { role: "master", name: "Sistema", text: `Difesa non riuscita: ${res.error}`, isCombatNarration: true }]);
        return;
      }
      setPendingAttack(null);
      if (res.scene) {
        setSceneState(res.scene);
        _syncCombatEntitiesFromScene(res.scene);
      }
      if (res.players) setPlayers(res.players);
      if (res.combat_log) {
        setLastCombatLog(res.combat_log);
        _setMessages(prev => [...prev, { role: "combat", combat_log: res.combat_log }]);
        _fetchCombatNarration(res.combat_log);
      }
      // Turno degli altri NPC dopo che il giocatore ha risposto all'attacco
      return await _runNpcTurn(tacticalContext);
    } catch (_) {}
    return null;
  }

  async function handleStandUp(playerId) {
    try {
      const res = await fetch(`${API_URL}/game/combat/standup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player_id: playerId }),
      }).then(r => r.json());
      if (res.players) setPlayers(res.players);
      if (res.message) _setMessages(prev => [...prev, {
        role: "master", name: "Master", text: res.message, isCombatNarration: true,
      }]);
    } catch (_) {}
  }

  async function handleRename(playerId, newName) {
    // Aggiornamento locale immediato
    setPlayers(prev => prev.map(p => p.id === playerId ? { ...p, name: newName } : p));
    try {
      await fetch(`${API_URL}/game/player/rename`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player_id: playerId, name: newName }),
      });
    } catch (_) {}
  }

  async function handleMove(nodeId) {
    // 1. Sposta il nodo nel backend (aggiorna map_state)
    try {
      const moveRes = await fetch(`${API_URL}/game/move`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ node_id: nodeId }),
      }).then(r => r.json());
      if (moveRes.map_state) setMapState(moveRes.map_state);
    } catch (_) {}

    // 2. Genera la scena della nuova location tramite turno Master
    const node = mapState?.nodes?.[nodeId];
    const locationName = node?.name || "nuova location";
    const locationDesc = node?.description || "";
    const activePid = players.find(p => p.hp > 0)?.id || players[0]?.id;
    const actionText = `Il gruppo si sposta verso ${locationName}. ${locationDesc ? `(${locationDesc.slice(0,80)})` : ""}`.trim();

    setLoading(true);
    const playerDicts = players.map(p => ({
      id: p.id, name: p.name, role: p.role, archetype: p.archetype || p.role,
      stats: p.stats, skills: p.skills || {}, advantages: p.advantages || [],
      disadvantages: p.disadvantages || [], hp: p.hp, max_hp: p.max_hp,
      fp: p.fp, max_fp: p.max_fp, dr: p.dr || 0, items: p.items || [],
      actions: p.actions || [], backstory: p.backstory || "", motivation: p.motivation || "",
    }));
    const newHistory = [...history, { role: "player", name: players.find(p=>p.id===activePid)?.name || "Gruppo", text: actionText }];
    try {
      const res = await fetch(`${API_URL}/game/master/turn-bible`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          genre, players: playerDicts, history: newHistory,
          player_action: actionText, active_player_id: activePid,
          adventure, game_state_data: { ...gameStateData, map_state: mapState },
        }),
      }).then(r => r.json());

      const masterMsg = { role: "master", name: "Master", text: res.narrative, roll: res.roll };
      const masterIdx = messagesRef.current.length;
      _setMessages(prev => [...prev, { role: "player", name: "Gruppo", text: actionText }, masterMsg]);
      setHistory([...newHistory, { role: "master", name: "Master", text: res.narrative }]);
      setOptions(res.options || []);
      if (res.state_updates) applyStateUpdates(res.state_updates);
      if (imageProvider !== "none") fetchSceneImage(res.narrative, masterIdx + 1);
      setShowMap(false); // chiude la mappa dopo lo spostamento
    } catch (_) {}
    setLoading(false);
  }

  async function handleRequestStrategicImage() {
    if (loadingStrategicImage) return;
    setLoadingStrategicImage(true);
    try {
      const res = await fetch(`${API_URL}/game/generate-strategic-map-image`, {
        method: "POST",
      }).then(r => r.json());
      if (res.image_b64) setStrategicMapImage(res.image_b64);
    } catch (_) {}
    setLoadingStrategicImage(false);
  }

  async function fetchSceneImage(narrative, msgIndex) {
    try {
      const res = await fetch(`${API_URL}/game/generate-scene-image`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scene_text: narrative.slice(0, 500),
          genre,
          environment_type: adventure?.locations?.[0]?.type || "outdoor",
        }),
      }).then(r => r.json());
      if (res.image_base64) {
        _setMessages(prev => prev.map((m, i) => i === msgIndex ? { ...m, image: res.image_base64 } : m));
      }
    } catch (_) {}
  }

  useEffect(() => {
    async function start() {
      // Sessione persa (es. backend riavviato) — torna al setup invece di avviare vuoto
      if (!initialPlayers || initialPlayers.length === 0) {
        onRestart();
        return;
      }
      setLoading(true);
      let res;
      if (adventure) {
        res = await fetch(`${API_URL}/game/master/start-bible`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ genre, players: playerDicts, adventure }),
        }).then(r => r.json());
      } else {
        res = await fetch(`${API_URL}/game/master/start`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ genre, players: playerDicts }),
        }).then(r => r.json());
      }
      const masterMsg = { role: "master", name: "Master", text: res.narrative, roll: res.roll };
      _setMessages([masterMsg]);
      setHistory([{ role: "master", name: "Master", text: res.narrative }]);
      setOptions(res.options || []);
      if (res.state_updates) applyStateUpdates(res.state_updates);
      setLoading(false);
      setStartupLoading(false);
      if (imageProvider !== "none") fetchSceneImage(res.narrative, 0);
      // fetchGameState popola world_npcs — poi generiamo gli avatar
      const gs = await fetch(`${API_URL}/game/state`).then(r => r.json()).catch(() => ({}));
      if (gs.scene) setSceneState(gs.scene);
      if (gs.map_state) setMapState(gs.map_state);
      if (gs.world_npcs) setGameStateData(prev => ({ ...prev, world_npcs: gs.world_npcs }));
      if (gs.players?.length > 0) setPlayers(prev => gs.players.map(gp => {
        const local = prev.find(lp => lp.id === gp.id);
        return local ? { ...gp, backstory: gp.backstory || local.backstory || "", motivation: gp.motivation || local.motivation || "" } : gp;
      }));
      // avatar NPC generati dall'useEffect che osserva world_npcs
    }
    start();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, options]);

  // Genera avatar per world_npcs non ancora presenti in npcAvatars
  useEffect(() => {
    if (imageProvider === "none") return;
    const npcs = (gameStateData.world_npcs || []).filter(n => n.name && !npcAvatars[n.name]);
    if (npcs.length === 0) return;
    const entities = npcs.map(n => ({
      id: n.name, name: n.name,
      description: n.description || n.role || "",
      type: n.disposition === "hostile" ? "enemy" : "npc",
    }));
    fetch(`${API_URL}/game/generate-npc-avatars`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ entities, genre }),
    }).then(r => r.json()).then(r => {
      if (r.avatars) setNpcAvatars(prev => ({ ...prev, ...r.avatars }));
    }).catch(() => {});
  }, [gameStateData.world_npcs]);

  // Chiude il combattimento quando tutti i nemici sono abbattuti
  useEffect(() => {
    if (!gameStateData.in_combat) return;
    const enemies = combatEntities.filter(e => e.type === "enemy");
    if (enemies.length > 0 && enemies.every(e => (e.hp ?? e.max_hp ?? 1) <= 0)) {
      setGameStateData(prev => ({ ...prev, in_combat: false }));
      setCombatEntities([]);
      setShowCombatMap(false);
      setLastCombatLog(null);
      _setMessages(prev => [...prev, {
        role: "master", name: "Master",
        text: "Il combattimento è terminato. Tutti i nemici sono stati neutralizzati.",
        isCombatNarration: true,
      }]);
    }
  }, [combatEntities, gameStateData.in_combat]);

  async function sendAction(actionText, skill = "", playerId = null) {
    const pid = playerId || activePlayerId;
    const player = players.find(p => p.id === pid) || players[0];
    const playerMsg = { role: "player", name: player.name, text: actionText };
    _setMessages(prev => [...prev, playerMsg]);
    const newHistory = [...history, { role: "player", name: player.name, text: actionText }];
    setHistory(newHistory);
    setOptions([]);
    setPendingOption(null);
    setCustomText("");
    setLoading(true);

    let res;
    if (adventure) {
      res = await fetch(`${API_URL}/game/master/turn-bible`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          genre, players: playerDicts, history: newHistory,
          player_action: actionText, active_player_id: pid,
          adventure, game_state_data: { ...gameStateData, map_state: mapState },
        }),
      }).then(r => r.json());
    } else {
      res = await fetch(`${API_URL}/game/master/turn`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ genre, players: playerDicts, history: newHistory, player_action: actionText, active_player_id: pid }),
      }).then(r => r.json());
    }

    const masterMsg = { role: "master", name: "Master", text: res.narrative, roll: res.roll };
    // capture index before state update — prev.length is reliable inside the updater
    // but we also need it synchronously: use a ref snapshot
    const masterIdx = messagesRef.current.length;
    _setMessages(prev => [...prev, masterMsg]);
    setHistory([...newHistory, { role: "master", name: "Master", text: res.narrative }]);
    setOptions(res.options || []);

    const updates = res.state_updates;
    console.log("[GURPS] state_updates:", JSON.stringify(updates));
    if (updates) {
      applyStateUpdates(updates);
      if (updates.story_over) {
        setStoryOver(true);
        setVictory(updates.victory || false);
        if (updates.personal_victories) setPersonalVictories(updates.personal_victories);
      }
      // popola sceneState immediatamente dalla combat_scene nel payload
      if (updates.activate_combat && updates.combat_scene?.entities) {
        console.log("[GURPS] attivazione combattimento:", updates.combat_scene);
        setCombatEntities(updates.combat_scene.entities);
        // Genera avatar per entità di combattimento non ancora note
        if (imageProvider !== "none") {
          const newEntities = updates.combat_scene.entities.filter(e => e.name);
          if (newEntities.length > 0) {
            fetch(`${API_URL}/game/generate-npc-avatars`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              // chiave = nome, così il lookup in CombatMap funziona per nome
              body: JSON.stringify({ entities: newEntities.map(e => ({ id: e.name, name: e.name, description: e.description || "", type: e.type })), genre }),
            }).then(r => r.json()).then(r => {
              if (r.avatars) setNpcAvatars(prev => ({ ...prev, ...r.avatars }));
            }).catch(() => {});
          }
        }
        // genera mappa tattica solo al primo ingresso in combattimento (non rigenera se esiste già)
        setCombatBgImage(prev => {
          if (prev) return prev; // già presente — non toccare
          // Usa mappa PDF come sfondo tattico se disponibile e imageProvider è none
          if (imageProvider === "none" && adventure?.map_image_b64) return adventure.map_image_b64;
          // avvia fetch in background
          const currentNode = mapState?.nodes?.[mapState?.current_node_id];
          const locationName = currentNode?.name || adventure?.locations?.[0]?.name || "Luogo di combattimento";
          const locationDesc = currentNode?.description || res.narrative.slice(0, 300);
          const envType = currentNode?.kind || adventure?.locations?.[0]?.type || updates.combat_scene?.location_type || "indoor";
          const missionEnv = adventure?.environment_type || adventure?.genre || genre;
          const sceneNarrative = updates.combat_scene?.scene_text || updates.narrative || "";
          const enemyNames = (updates.combat_scene?.entities || [])
            .filter(e => e.type === "enemy")
            .map(e => e.name);
          if (imageProvider !== "none") fetch(`${API_URL}/game/generate-tactical-map-image`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              location_name: locationName,
              location_description: locationDesc,
              genre,
              environment_type: envType,
              scene_narrative: sceneNarrative,
              mission_environment: missionEnv,
              enemy_names: enemyNames,
            }),
          }).then(r => r.json()).then(r => { if (r.image_b64) setCombatBgImage(r.image_b64); }).catch(() => {});
          return null; // placeholder finché non arriva
        });
      }
    }
    setLoading(false);

    const idx = players.findIndex(p => p.id === pid);
    setActivePlayerId(players[(idx + 1) % players.length].id);
    if (imageProvider !== "none") fetchSceneImage(res.narrative, masterIdx);
    fetchGameState();
  }

  function handleOptionClick(opt) {
    if (!opt.skill) {
      setPendingOption(opt);
      setCustomText("");
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      sendAction(opt.text, opt.skill, opt.player_id);
    }
  }

  function handleCustomSubmit(e) {
    e.preventDefault();
    if (!customText.trim()) return;
    sendAction(customText.trim(), "", activePlayerId);
  }

  const activePlayer = players.find(p => p.id === activePlayerId) || players[0];
  const combatLocationNode = mapState?.nodes?.[mapState?.current_node_id];
  const combatSceneText = [
    sceneState?.scene_text,
    sceneState?.description,
    combatLocationNode?.description,
    messages?.slice?.(-2)?.map(m => m.text).join(" "),
  ].filter(Boolean).join(" ");

  if (startupLoading) return (
    <LoadingProgress
      icon="🎲"
      title="Il Master apre la scena..."
      steps={[
        { at: 0,    pill: "Contesto",  label: "Leggo la bibbia dell'avventura..." },
        { at: 4000, pill: "Personaggi", label: "Analizzo il gruppo di avventurieri..." },
        { at: 9000, pill: "Scena",     label: "Costruisco la scena d'apertura..." },
        { at: 14000, pill: "Opzioni",  label: "Preparo le opzioni per il primo turno..." },
        { at: 18000, pill: "Finale",   label: "Quasi pronto..." },
      ]}
    />
  );

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      {/* Main column */}
      <div style={{ display: "flex", flexDirection: "column", flex: 1, minWidth: 0 }}>
      {/* Header */}
      <div style={{
        padding: "12px 20px", borderBottom: "1px solid var(--border)",
        display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0,
      }}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", flex: 1, minWidth: 0 }}>
          {players.map(p => (
            <PlayerChip key={p.id} player={p} active={p.id === activePlayerId} onClick={() => setActivePlayerId(p.id)} avatar={avatars[p.id]} onRename={newName => handleRename(p.id, newName)} />
          ))}
        </div>
        <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
          {mapState && !gameStateData.in_combat && (
            <button onClick={() => {
              setShowMap(v => {
                if (!v && !strategicMapImage && !loadingStrategicImage && imageProvider !== "none") {
                  setTimeout(handleRequestStrategicImage, 0);
                }
                return !v;
              });
            }} style={{
              fontSize: 12, color: showMap ? "var(--accent)" : "var(--text)",
              background: showMap ? "var(--accent-bg)" : "none",
              border: `1px solid ${showMap ? "var(--accent-border)" : "var(--border)"}`,
              borderRadius: 6, padding: "4px 10px", cursor: "pointer",
            }}>🗺 Mappa</button>
          )}
          {adventure && (
            <button onClick={() => setShowPanel(v => !v)} style={{
              fontSize: 12, color: showPanel ? "var(--accent)" : "var(--text)",
              background: showPanel ? "var(--accent-bg)" : "none",
              border: `1px solid ${showPanel ? "var(--accent-border)" : "var(--border)"}`,
              borderRadius: 6, padding: "4px 10px", cursor: "pointer",
            }}>📖 Bibbia</button>
          )}
          {adventure && (
            <button onClick={() => setShowSecrets(true)} style={{
              fontSize: 12, color: "#f59e0b", background: "rgba(245,158,11,0.1)",
              border: "1px solid rgba(245,158,11,0.4)",
              borderRadius: 6, padding: "4px 10px", cursor: "pointer",
            }}>🔓 Segreti</button>
          )}
          <button onClick={onRestart} style={{
            fontSize: 12, color: "var(--text)", background: "none", border: "1px solid var(--border)",
            borderRadius: 6, padding: "4px 10px", cursor: "pointer",
          }}>↩ Ricomincia</button>
        </div>
      </div>

      {/* CombatMap — si apre automaticamente all'inizio del combattimento, togglabile */}
      {gameStateData.in_combat && showCombatMap && (
        <CombatMap
          players={players}
          sceneEntities={combatEntities}
          activePlayerId={activePlayerId}
          pendingAttack={pendingAttack}
          onAttack={handleAttack}
          onDefend={handleDefend}
          onStandUp={handleStandUp}
          onNextPlayer={id => { if (id != null) setActivePlayerId(id); }}
          onFinishTurn={_runNpcTurn}
          avatars={avatars}
          npcAvatars={npcAvatars}
          bgImage={combatBgImage}
          lastCombatLog={lastCombatLog}
          genre={genre}
          environmentType={combatLocationNode?.kind || adventure?.environment_type || adventure?.genre}
          locationName={combatLocationNode?.name || adventure?.locations?.[0]?.name}
          sceneText={combatSceneText}
          onClose={() => setShowCombatMap(false)}
        />
      )}

      {/* Chat */}
      <div style={{ flex: 1, overflowY: "auto", padding: "24px 20px", maxWidth: 760, width: "100%", margin: "0 auto", boxSizing: "border-box" }}>

        {/* Banner combattimento attivo — collega chat e mappa */}
        {gameStateData.in_combat && (
          <div style={{
            display: "flex", alignItems: "center", gap: 10, padding: "8px 14px",
            background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)",
            borderRadius: 10, marginBottom: 16, flexWrap: "wrap",
          }}>
            <span style={{ fontSize: 16 }}>⚔</span>
            <span style={{ fontWeight: 700, color: "#f87171", fontSize: 13 }}>Combattimento in corso</span>
            {combatEntities.filter(e => e.type === "enemy" && (e.hp ?? 1) > 0).map(e => (
              <span key={e.id} style={{
                fontSize: 11, padding: "2px 8px", borderRadius: 5,
                background: "rgba(239,68,68,0.15)", color: "#fca5a5", border: "1px solid rgba(239,68,68,0.2)",
              }}>
                {e.name} ❤️{e.hp}/{e.max_hp}
              </span>
            ))}
            <button
              onClick={() => setShowCombatMap(v => !v)}
              style={{
                marginLeft: "auto", fontSize: 11, padding: "3px 10px", borderRadius: 6,
                border: "1px solid rgba(239,68,68,0.4)", cursor: "pointer",
                background: showCombatMap ? "rgba(239,68,68,0.2)" : "none",
                color: "#f87171", fontWeight: 700,
              }}
            >
              {showCombatMap ? "↙ Nascondi mappa" : "↗ Mostra mappa"}
            </button>
          </div>
        )}

        {messages.map((msg, i) =>
          msg.role === "combat"
            ? <CombatLogMessage key={i} msg={msg} />
            : msg.role === "master"
            ? <MasterMessage key={i} msg={msg} players={players} />
            : <PlayerMessage key={i} msg={msg} />
        )}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* StrategicMapPanel */}
      {showMap && mapState && (
        <StrategicMapPanel
          mapState={mapState}
          onClose={() => setShowMap(false)}
          onMove={handleMove}
          bgImage={strategicMapImage}
          onRequestImage={handleRequestStrategicImage}
          loadingImage={loadingStrategicImage}
          adventure={adventure}
          cluesFound={gameStateData.clues_found}
        />
      )}

      {/* Options + input */}
      {!loading && !storyOver && (
        <div style={{ padding: "12px 20px 20px", borderTop: "1px solid var(--border)", flexShrink: 0, maxWidth: 760, width: "100%", margin: "0 auto", boxSizing: "border-box", alignSelf: "stretch" }}>

          {/* Blocco chat durante combattimento */}
          {gameStateData.in_combat ? (
            <div style={{
              display: "flex", flexDirection: "column", alignItems: "center", gap: 10,
              padding: "14px 20px", borderRadius: 12,
              background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)",
            }}>
              <div style={{ fontSize: 13, color: "#f87171", fontWeight: 700 }}>
                ⚔ Combattimento in corso — usa la mappa tattica
              </div>
              <div style={{ fontSize: 12, color: "var(--text)", textAlign: "center", lineHeight: 1.6, opacity: 0.8 }}>
                {pendingAttack
                  ? "⚠ Attacco in arrivo — scegli come difenderti nella mappa"
                  : "Seleziona un personaggio sulla mappa → scegli Muovi o Attacca"}
              </div>
              {!showCombatMap && (
                <button onClick={() => setShowCombatMap(true)} style={{
                  padding: "8px 20px", borderRadius: 8, border: "1px solid rgba(239,68,68,0.5)",
                  background: "rgba(239,68,68,0.15)", color: "#f87171", fontWeight: 700,
                  fontSize: 13, cursor: "pointer",
                }}>↗ Apri mappa tattica</button>
              )}
            </div>
          ) : (
            <>
          {options.length > 0 && !pendingOption && (
            <>
              <div style={{ fontSize: 12, color: "var(--text)", marginBottom: 8, fontWeight: 600 }}>
                Turno di <span style={{ color: "var(--accent)" }}>{activePlayer?.name}</span> — cosa fai?
              </div>
              <OptionsBar options={options} players={players} onChoose={handleOptionClick} />
            </>
          )}
          {(pendingOption || options.length === 0) && (
            <form onSubmit={handleCustomSubmit} style={{ display: "flex", gap: 8, marginTop: pendingOption ? 10 : 0 }}>
              <input
                ref={inputRef}
                value={customText}
                onChange={e => setCustomText(e.target.value)}
                placeholder={`${activePlayer?.name || "Personaggio"}: cosa fa? Scrivi liberamente...`}
                style={{
                  flex: 1, padding: "11px 16px", borderRadius: 10,
                  border: "1px solid var(--border)", background: "var(--bg)",
                  color: "var(--text-h)", fontSize: 15, outline: "none",
                }}
              />
              {pendingOption && (
                <button type="button" onClick={() => setPendingOption(null)} style={{
                  padding: "11px 14px", borderRadius: 10, border: "1px solid var(--border)",
                  background: "var(--bg)", color: "var(--text)", cursor: "pointer", fontSize: 14,
                }}>✕</button>
              )}
              <button type="submit" disabled={!customText.trim()} style={{
                padding: "11px 20px", borderRadius: 10, border: "none",
                background: customText.trim() ? "var(--accent)" : "var(--border)",
                color: "#fff", fontWeight: 700, cursor: customText.trim() ? "pointer" : "not-allowed",
              }}>Invia 🎲</button>
            </form>
          )}
            </>
          )}
        </div>
      )}

      {storyOver && (
        <div style={{ padding: "28px 24px", textAlign: "center", borderTop: "1px solid var(--border)", background: victory ? "rgba(74,222,128,0.04)" : "rgba(248,113,113,0.04)" }}>
          <div style={{ fontSize: 52, marginBottom: 10 }}>{victory ? "🏆" : "💀"}</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: "var(--text-h)", marginBottom: 6 }}>
            {victory ? "Vittoria di gruppo!" : "Fine dell'avventura"}
          </div>
          {adventure?.win_condition && (
            <div style={{ fontSize: 13, color: "var(--text)", maxWidth: 420, margin: "0 auto 16px", lineHeight: 1.5 }}>
              {victory ? "✅" : "❌"} {adventure.win_condition}
            </div>
          )}

          {/* Risultati individuali */}
          {players.length > 0 && (
            <div style={{ margin: "18px auto 20px", maxWidth: 480 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: 1, marginBottom: 10 }}>
                Obiettivi personali
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {players.map(p => {
                  const achieved = personalVictories[p.id];
                  const hasResult = p.id in personalVictories;
                  return (
                    <div key={p.id} style={{
                      display: "flex", alignItems: "flex-start", gap: 10,
                      padding: "10px 14px", borderRadius: 10, textAlign: "left",
                      background: hasResult
                        ? (achieved ? "rgba(74,222,128,0.08)" : "rgba(248,113,113,0.08)")
                        : "rgba(255,255,255,0.04)",
                      border: `1px solid ${hasResult ? (achieved ? "rgba(74,222,128,0.3)" : "rgba(248,113,113,0.3)") : "rgba(255,255,255,0.08)"}`,
                    }}>
                      <div style={{ fontSize: 20, lineHeight: 1, flexShrink: 0, marginTop: 1 }}>
                        {hasResult ? (achieved ? "✅" : "❌") : "⬜"}
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-h)", marginBottom: 2 }}>{p.name}</div>
                        {p.motivation && (
                          <div style={{ fontSize: 11, color: "#a78bfa", marginBottom: 2, fontStyle: "italic" }}>{p.motivation}</div>
                        )}
                        {!hasResult && (
                          <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>In valutazione...</div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div style={{ display: "flex", gap: 10, justifyContent: "center", flexWrap: "wrap" }}>
            {adventure && (
              <button onClick={() => setShowSecrets(true)} style={{
                padding: "11px 24px", borderRadius: 10, border: "1px solid rgba(245,158,11,0.5)",
                background: "rgba(245,158,11,0.1)", color: "#f59e0b", fontWeight: 700, fontSize: 14, cursor: "pointer",
              }}>🔓 Rivela segreti</button>
            )}
            <button onClick={onRestart} style={{
              padding: "11px 24px", borderRadius: 10, border: "none",
              background: "var(--accent)", color: "#fff", fontWeight: 700, fontSize: 14, cursor: "pointer",
            }}>↩ Nuova partita</button>
          </div>
        </div>
      )}
      </div>{/* end main column */}
      {showPanel && adventure && (
        <SidePanel adventure={adventure} gameState={gameStateData} players={players} avatars={avatars} npcAvatars={npcAvatars} onClose={() => setShowPanel(false)} />
      )}
      {showSecrets && adventure && (
        <SecretsPanel adventure={adventure} gameState={gameStateData} onClose={() => setShowSecrets(false)} />
      )}
    </div>
  );
}

// ─── Root ──────────────────────────────────────────────────────────────────

export default function App() {
  const [screen, setScreen] = useState("setup");
  const [genre, setGenre] = useState("sci_fi");
  const [players, setPlayers] = useState([]);
  const [avatars, setAvatars] = useState({});
  const [adventure, setAdventure] = useState(null);
  const [provider, setProvider] = useState("claude");
  const [imageProvider, setImageProvider] = useState("auto");

  function handleSetupComplete(g, p, av = {}, prov = "claude", preloaded = null, imgProv = "auto") {
    setGenre(g);
    setPlayers(p);
    setAvatars(av);
    setProvider(prov);
    setImageProvider(imgProv);
    if (preloaded) {
      setAdventure(preloaded);
      setScreen("game");
    } else {
      setAdventure(null);
      setScreen("adventure");
    }
  }

  function handleAdventureStart(adv) {
    setAdventure(adv);
    setScreen("game");
  }

  function handleRestart() {
    setAdventure(null);
    setScreen("setup");
  }

  if (screen === "adventure") {
    return (
      <AdventureScreen
        genre={genre}
        players={players}
        avatars={avatars}
        provider={provider}
        onStart={handleAdventureStart}
        onBack={() => setScreen("setup")}
      />
    );
  }
  if (screen === "game") {
    return (
      <GameScreen
        genre={genre}
        players={players}
        avatars={avatars}
        adventure={adventure}
        provider={provider}
        imageProvider={imageProvider}
        preloadedMapImage={adventure?.map_image_b64 || null}
        onRestart={handleRestart}
      />
    );
  }
  return <SetupScreen onStart={handleSetupComplete} />;
}
