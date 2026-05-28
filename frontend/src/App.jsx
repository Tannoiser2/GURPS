
import React, { useEffect, useMemo, useRef, useState } from "react";
import caricaPdfImg from "./assets/carica_pdf.png";
import caricaJsonImg from "./assets/carica_json.png";
import jsonDoctorImg from "./assets/json_doctor.png";

const API_URL = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? "https://gurps-f93w.onrender.com" : "http://127.0.0.1:8002");
const VERCEL_PDF_UPLOAD_LIMIT_BYTES = 4 * 1024 * 1024;

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

function rollTraitHighlights(r) {
  const traits = [];
  for (const t of r?.adv_breakdown || []) {
    if (!t?.name || !t?.delta) continue;
    traits.push({
      name: t.name,
      delta: t.delta,
      note: t.delta > 0 ? "bonus tratto" : "malus tratto",
      color: t.delta > 0 ? "#4ade80" : "#f87171",
    });
  }
  for (const t of r?.environmental_trait_modifiers || []) {
    if (!t?.name || !t?.delta) continue;
    traits.push({
      name: t.name,
      delta: t.delta,
      note: "riduce il malus ambientale",
      color: "#60a5fa",
    });
  }
  if (r?.luck) {
    const extra = (r.luck.extra_rolls || []).join(", ");
    traits.push({
      name: r.luck.trait || "Fortuna",
      delta: null,
      note: `ritiro: ${r.luck.original_roll} → ${r.luck.chosen_roll}${extra ? ` (${extra})` : ""}`,
      color: "#facc15",
    });
  }
  return traits;
}

function DiceFormulaRow({ r }) {
  // Costruisce la formula leggibile da un entry di roll_details
  const parts = [];
  parts.push({ label: r.skill_known ? `${r.skill} (conosciuta)` : `${r.skill} (default)`, val: r.base_skill, color: "var(--text-h)", kind: "skill" });
  // Bonus oggetto generico (requires_item) — solo se non già coperto dai bonus equipaggiamento
  const genericItemBonus = (r.item_bonus || 0) - (r.equip_bonus || 0);
  if (genericItemBonus > 0) parts.push({ label: "oggetto", val: `+${genericItemBonus}`, color: "#60a5fa", kind: "bonus" });
  // Bonus/malus equipaggiamento strutturato — espanso per nome se disponibile
  if (r.equip_breakdown?.length > 0) {
    for (const eq of r.equip_breakdown) {
      const positive = eq.delta > 0;
      parts.push({
        label: eq.name + (eq.reason ? ` (${eq.reason})` : ""),
        val: positive ? `+${eq.delta}` : `${eq.delta}`,
        color: positive ? "#38bdf8" : "#fb923c",
        kind: "equip",
      });
    }
  } else if (r.equip_bonus) {
    const positive = r.equip_bonus > 0;
    parts.push({ label: "equipaggiamento", val: positive ? `+${r.equip_bonus}` : `${r.equip_bonus}`, color: positive ? "#38bdf8" : "#fb923c", kind: "equip" });
  }
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
  const traitHighlights = rollTraitHighlights(r);

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
      {traitHighlights.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginTop: 6 }}>
          {traitHighlights.map((t, i) => (
            <span key={`${t.name}-${i}`} style={{
              padding: "2px 7px", borderRadius: 6, fontSize: 10, fontWeight: 800,
              background: `${t.color}18`, border: `1px solid ${t.color}55`, color: t.color,
            }}>
              {t.name}{t.delta !== null ? ` ${t.delta > 0 ? "+" : ""}${t.delta}` : ""} <span style={{ opacity: 0.72, fontWeight: 600 }}>· {t.note}</span>
            </span>
          ))}
        </div>
      )}
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
    const traitCount = rollDetails.reduce((acc, r) => acc + rollTraitHighlights(r).length, 0);
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
          {traitCount > 0 && (
            <span style={{
              padding: "2px 7px", borderRadius: 5, fontWeight: 800, fontSize: 10,
              background: "rgba(250,204,21,0.12)", color: "#fde68a", border: "1px solid rgba(250,204,21,0.35)",
            }}>Tratti {traitCount}</span>
          )}
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
  "Duro da Uccidere 2":        { icon: "🛡", color: "#4ade80", type: "adv" },
  "Duro da Uccidere 3":        { icon: "🛡", color: "#4ade80", type: "adv" },
  "Sensi Acuti":               { icon: "👁", color: "#38bdf8", type: "adv" },
  "Vista Acuta":               { icon: "👁", color: "#38bdf8", type: "adv" },
  "Vista Acuta 2":             { icon: "👁", color: "#38bdf8", type: "adv" },
  "Udito Acuto":               { icon: "👂", color: "#38bdf8", type: "adv" },
  "Visione Notturna":          { icon: "🌙", color: "#818cf8", type: "adv" },
  "Visione Notturna 3":        { icon: "🌙", color: "#818cf8", type: "adv" },
  "Visione Notturna 6":        { icon: "🌙", color: "#818cf8", type: "adv" },
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
  "Agilità del Gatto":         { icon: "🐾", color: "#a3e635", type: "adv" },
  "Bilanciamento Perfetto":    { icon: "⚖", color: "#22d3ee", type: "adv" },
  "Difesa Migliorata (Schivata)": { icon: "🛡", color: "#60a5fa", type: "adv" },
  "Elevata Soglia del Dolore": { icon: "🩹", color: "#fb7185", type: "adv" },
  "Empatia con gli Animali":   { icon: "🐾", color: "#84cc16", type: "adv" },
  "Flessuoso":                 { icon: "🪢", color: "#a78bfa", type: "adv" },
  "Snodato":                   { icon: "🪢", color: "#c084fc", type: "adv" },
  "Fortuna Straordinaria":     { icon: "🍀", color: "#4ade80", type: "adv" },
  "Fortuna Smodata":           { icon: "🍀", color: "#4ade80", type: "adv" },
  "Intrepido":                 { icon: "🔥", color: "#f97316", type: "adv" },
  "Intrepido 2":               { icon: "🔥", color: "#f97316", type: "adv" },
  "Resistente alle Malattie":  { icon: "🧬", color: "#34d399", type: "adv" },
  "Resistente ai Veleni":      { icon: "🧪", color: "#34d399", type: "adv" },
  "Spericolato":               { icon: "🎲", color: "#f59e0b", type: "adv" },
  "Talento (Artificiere)":     { icon: "⭐", color: "#f59e0b", type: "adv" },
  "Talento (Sopravvivenza)":   { icon: "⭐", color: "#84cc16", type: "adv" },
  "Talento (Parlantina)":      { icon: "⭐", color: "#f472b6", type: "adv" },
  "Talento Linguistico":       { icon: "🗣", color: "#a3e635", type: "adv" },
  "Viaggiatore (Tempo)":       { icon: "⏳", color: "#a78bfa", type: "adv" },
  "Viaggiatore (Dimensioni)":  { icon: "🌀", color: "#a78bfa", type: "adv" },
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
  "Vista Imperfetta":          { icon: "👓",  color: "#9ca3af", type: "dis" },
  "Animo Sanguinario":         { icon: "🩸", color: "#ef4444", type: "dis" },
  "Avidità":                   { icon: "🪙", color: "#f59e0b", type: "dis" },
  "Codice d'Onore (Pirata)":   { icon: "⚓", color: "#60a5fa", type: "dis" },
  "Codice d'Onore (Gentiluomo)": { icon: "🎩", color: "#60a5fa", type: "dis" },
  "Curiosità":                 { icon: "🔎", color: "#c084fc", type: "dis" },
  "Gelosia":                   { icon: "🟢", color: "#84cc16", type: "dis" },
  "Ghiottoneria":              { icon: "🍷", color: "#f97316", type: "dis" },
  "Illusione Minore":          { icon: "🌀", color: "#a78bfa", type: "dis" },
  "Illusione Maggiore":        { icon: "🌀", color: "#a78bfa", type: "dis" },
  "Illusione Severa":          { icon: "🌀", color: "#a78bfa", type: "dis" },
  "Fobia (Sangue)":            { icon: "🩸", color: "#ef4444", type: "dis" },
  "Fobia (Buio)":              { icon: "🌑", color: "#64748b", type: "dis" },
  "Fobia (Altezza)":           { icon: "🧗", color: "#f59e0b", type: "dis" },
  "Intolleranza Totale":       { icon: "🚫", color: "#ef4444", type: "dis" },
  "Intolleranza Specifica":    { icon: "🚫", color: "#fb7185", type: "dis" },
  "Irascibile":                { icon: "💢", color: "#ef4444", type: "dis" },
  "Libidine":                  { icon: "💋", color: "#f472b6", type: "dis" },
  "Onestà":                    { icon: "⚖", color: "#60a5fa", type: "dis" },
  "Ossessione Breve":          { icon: "🎯", color: "#f59e0b", type: "dis" },
  "Ossessione Lunga":          { icon: "🎯", color: "#f97316", type: "dis" },
  "Pacifismo (Riluttante a Uccidere)": { icon: "☮", color: "#34d399", type: "dis" },
  "Presunzione":               { icon: "👑", color: "#a78bfa", type: "dis" },
  "Sfortuna":                  { icon: "☘", color: "#9ca3af", type: "dis" },
  "Sincerità":                 { icon: "🗣", color: "#60a5fa", type: "dis" },
  "Sordità Parziale":          { icon: "👂", color: "#9ca3af", type: "dis" },
  "Vista Imperfetta Non Correggibile": { icon: "👓", color: "#9ca3af", type: "dis" },
  "Voto Minore":               { icon: "📜", color: "#facc15", type: "dis" },
  "Voto Maggiore":             { icon: "📜", color: "#f59e0b", type: "dis" },
  "Voto Superiore":            { icon: "📜", color: "#ef4444", type: "dis" },
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

// ─── Scheda personaggio espandibile ──────────────────────────────────────────

const STAT_COLOR = { forza: "#f87171", agilita: "#4ade80", intelligenza: "#60a5fa", empatia: "#c084fc" };
const STAT_SHORT = { forza: "FO", agilita: "DE", intelligenza: "IN", empatia: "SA" };
const STAT_SKILL_MAP = { forza: "forza", agilita: "agilita", intelligenza: "intelligenza", empatia: "empatia" };

// ─── EquipmentPanel — inventario strutturato PG ────────────────────────────
const EQ_CAT_ICON = { weapon: "⚔️", armor: "🛡️", ammo: "🔫", consumable: "💊", misc: "🎒" };
const EQ_CAT_LABEL = { weapon: "Arma", armor: "Armatura", ammo: "Munizioni", consumable: "Consumabile", misc: "Oggetto" };

function EquipmentPanel({ player, onPlayersUpdate }) {
  const [showAddWeapon, setShowAddWeapon] = React.useState(false);
  const [weaponList, setWeaponList] = React.useState([]);
  const [selectedWeaponId, setSelectedWeaponId] = React.useState("");
  const [ammoPacks, setAmmoPacks] = React.useState(1);
  const [loading, setLoading] = React.useState(false);
  const [msg, setMsg] = React.useState("");

  const equipment = player.equipment || [];
  const actions = player.actions || [];
  const items = player.items || [];

  // Carica lista armi quando si apre il picker
  async function loadWeapons() {
    if (weaponList.length > 0) return;
    try {
      const res = await fetch(`${API_URL}/game/combat/weapons`).then(r => r.json());
      setWeaponList([...(res.melee || []), ...(res.ranged || [])]);
      if (res.melee?.length > 0) setSelectedWeaponId(res.melee[0].id);
    } catch (_) {}
  }

  async function handleAddWeapon() {
    if (!selectedWeaponId) return;
    setLoading(true); setMsg("");
    try {
      const res = await fetch(`${API_URL}/game/player/${player.id}/add-weapon`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ weapon_id: selectedWeaponId, ammo_packs: ammoPacks }),
      }).then(r => r.json());
      if (res.error) { setMsg(`Errore: ${res.error}`); }
      else { setMsg(res.log || "Aggiunto."); onPlayersUpdate && onPlayersUpdate(res.players); setShowAddWeapon(false); }
    } catch (_) { setMsg("Errore di rete."); }
    setLoading(false);
  }

  async function handleRemoveWeapon(weaponId) {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/game/player/${player.id}/remove-weapon/${weaponId}`, { method: "DELETE" }).then(r => r.json());
      if (!res.error) onPlayersUpdate && onPlayersUpdate(res.players);
    } catch (_) {}
    setLoading(false);
  }

  async function handleRemoveItem(itemId) {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/game/player/${player.id}/equipment/${itemId}`, { method: "DELETE" }).then(r => r.json());
      if (!res.error) onPlayersUpdate && onPlayersUpdate(res.players);
    } catch (_) {}
    setLoading(false);
  }

  const weaponActions = actions.filter(a => a.attack_kind);
  const hasRanged = weaponActions.some(a => a.attack_kind === "ranged");
  const selectedW = weaponList.find(w => w.id === selectedWeaponId);

  return (
    <div style={{ marginTop: 10, borderTop: "1px solid rgba(255,255,255,0.07)", paddingTop: 10 }}>
      <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.5, color: "var(--text-secondary)", marginBottom: 7, display: "flex", alignItems: "center", gap: 8 }}>
        🎒 Equipaggiamento
        <button onClick={() => { setShowAddWeapon(v => !v); if (!showAddWeapon) loadWeapons(); }}
          style={{ fontSize: 10, padding: "1px 8px", borderRadius: 5, border: "1px solid rgba(99,102,241,0.4)", background: "rgba(99,102,241,0.12)", color: "#a5b4fc", cursor: "pointer", fontWeight: 700 }}>
          {showAddWeapon ? "✕ Chiudi" : "+ Aggiungi arma"}
        </button>
      </div>

      {/* Picker aggiungi arma */}
      {showAddWeapon && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", padding: "7px 10px", borderRadius: 8, background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.2)", marginBottom: 8 }}>
          <select value={selectedWeaponId} onChange={e => setSelectedWeaponId(e.target.value)}
            style={{ padding: "3px 8px", borderRadius: 6, border: "1px solid rgba(99,102,241,0.35)", background: "rgba(20,20,50,0.9)", color: "#c4b5fd", fontSize: 12 }}>
            {weaponList.length === 0 && <option>Caricamento…</option>}
            {weaponList.map(w => <option key={w.id} value={w.id}>{w.attack_kind === "ranged" ? "🎯" : "⚔️"} {w.name}</option>)}
          </select>
          {selectedW?.ammo > 0 && (
            <label style={{ fontSize: 11, color: "rgba(255,255,255,0.55)", display: "flex", alignItems: "center", gap: 4 }}>
              Ricariche:
              <input type="number" min={0} max={20} value={ammoPacks} onChange={e => setAmmoPacks(Math.max(0, parseInt(e.target.value) || 0))}
                style={{ width: 40, padding: "2px 6px", borderRadius: 5, border: "1px solid rgba(255,255,255,0.15)", background: "rgba(0,0,0,0.3)", color: "#fff", fontSize: 12, textAlign: "center" }} />
            </label>
          )}
          <button onClick={handleAddWeapon} disabled={loading || !selectedWeaponId}
            style={{ padding: "3px 12px", borderRadius: 6, border: "none", background: "#6366f1", color: "#fff", fontWeight: 700, fontSize: 12, cursor: "pointer" }}>
            {loading ? "…" : "Aggiungi"}
          </button>
          {msg && <span style={{ fontSize: 11, color: msg.startsWith("Errore") ? "#f87171" : "#4ade80" }}>{msg}</span>}
        </div>
      )}

      {/* Armi attive (da actions) */}
      {weaponActions.length > 0 && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 6 }}>
          {weaponActions.map((a, i) => {
            const isRanged = a.attack_kind === "ranged";
            const ammoColor = (a.ammo_current ?? a.ammo) <= 1 ? "#f87171" : "#86efac";
            return (
              <div key={i} style={{
                display: "flex", alignItems: "center", gap: 5, padding: "4px 9px", borderRadius: 7,
                background: isRanged ? "rgba(251,191,36,0.08)" : "rgba(239,68,68,0.08)",
                border: `1px solid ${isRanged ? "rgba(251,191,36,0.25)" : "rgba(239,68,68,0.2)"}`,
              }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: isRanged ? "#fde68a" : "#fca5a5" }}>
                  {isRanged ? "🎯" : "⚔️"} {a.name}
                </span>
                <span style={{ fontSize: 10, color: "rgba(255,255,255,0.4)" }}>{a.damage} {a.damage_type}</span>
                {isRanged && a.ammo > 0 && (
                  <span style={{ fontSize: 10, fontWeight: 700, color: ammoColor, background: "rgba(0,0,0,0.25)", padding: "1px 5px", borderRadius: 4 }}>
                    {a.ammo_current ?? a.ammo}/{a.ammo}
                  </span>
                )}
                {a.weapon_id && (
                  <button onClick={() => handleRemoveWeapon(a.weapon_id)} title="Rimuovi arma dall'inventario"
                    style={{ background: "none", border: "none", color: "rgba(255,255,255,0.2)", cursor: "pointer", fontSize: 11, padding: "0 2px", lineHeight: 1 }}>✕</button>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Equipment items (armor, ammo packs, misc) */}
      {equipment.length > 0 && (
        <div style={{ display: "flex", gap: 5, flexWrap: "wrap", marginBottom: 5 }}>
          {equipment.map((it, i) => (
            <div key={it.id || i} style={{
              display: "flex", alignItems: "center", gap: 4, padding: "3px 8px", borderRadius: 6,
              background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
            }}>
              <span style={{ fontSize: 10 }}>{EQ_CAT_ICON[it.category] || "📦"}</span>
              <span style={{ fontSize: 11, color: "var(--text-h)" }}>{it.name}</span>
              {it.quantity > 1 && <span style={{ fontSize: 10, color: "#86efac", fontWeight: 700 }}>×{it.quantity}</span>}
              {it.armor_dr > 0 && <span style={{ fontSize: 10, color: "#67e8f9" }}>DR {it.armor_dr}</span>}
              {it.category !== "weapon" && (
                <button onClick={() => handleRemoveItem(it.id)} title="Rimuovi dall'inventario"
                  style={{ background: "none", border: "none", color: "rgba(255,255,255,0.2)", cursor: "pointer", fontSize: 10, padding: "0 2px", lineHeight: 1 }}>✕</button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Items legacy (stringhe) */}
      {items.length > 0 && (
        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
          {items.map((it, i) => (
            <span key={i} style={{ fontSize: 11, padding: "2px 7px", borderRadius: 5, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", color: "var(--text)" }}>
              {it}
            </span>
          ))}
        </div>
      )}

      {weaponActions.length === 0 && equipment.length === 0 && items.length === 0 && (
        <span style={{ fontSize: 11, color: "rgba(255,255,255,0.3)", fontStyle: "italic" }}>Nessun oggetto nell'inventario.</span>
      )}
    </div>
  );
}


function PlayerCardPanel({ player, avatar, onClose, onPlayersUpdate }) {
  const stats = player.stats || {};
  const skills = player.skills || {};
  const advantages = player.advantages || [];
  const disadvantages = player.disadvantages || [];

  // Skill con livello > 0, ordinate per livello decrescente — max 10
  const topSkills = Object.entries(skills)
    .filter(([, v]) => v > 0)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 10);

  const hpPct = Math.max(0, Math.min(100, ((player.hp ?? player.max_hp) / Math.max(player.max_hp, 1)) * 100));
  const hpColor = hpPct > 60 ? "#4ade80" : hpPct > 30 ? "#f59e0b" : "#ef4444";

  return (
    <div style={{
      borderBottom: "1px solid var(--border)",
      background: "var(--code-bg)",
      padding: "12px 20px 14px",
      animation: "expandDown 0.18s ease",
    }}>
      <style>{`@keyframes expandDown { from { opacity: 0; transform: translateY(-8px) } to { opacity: 1; transform: translateY(0) } }`}</style>

      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        {/* Riga top: avatar + nome + HP + chiudi */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
          <AvatarCircle src={avatar} size={44} fallback="🧑" />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
              <span style={{ fontWeight: 800, fontSize: 15, color: "var(--text-h)" }}>{player.name}</span>
              <span style={{ fontSize: 12, color: "var(--text)", opacity: 0.6 }}>{player.role}</span>
              {player.motivation && (
                <span style={{ fontSize: 11, color: "#a78bfa", fontStyle: "italic", marginLeft: 4 }}>"{player.motivation}"</span>
              )}
            </div>
            {/* HP bar */}
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 5 }}>
              <span style={{ fontSize: 11, color: hpColor, fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>
                ❤️ {player.hp ?? player.max_hp}/{player.max_hp}
              </span>
              <div style={{ flex: 1, maxWidth: 120, height: 4, borderRadius: 2, background: "rgba(255,255,255,0.1)" }}>
                <div style={{ height: "100%", borderRadius: 2, width: `${hpPct}%`, background: hpColor, transition: "width 0.3s" }} />
              </div>
            </div>
          </div>
          <button onClick={onClose} style={{
            background: "none", border: "none", color: "var(--text)", opacity: 0.5,
            cursor: "pointer", fontSize: 18, padding: "0 4px", lineHeight: 1,
          }}>✕</button>
        </div>

        <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
          {/* Stats */}
          <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
            {Object.entries(stats).map(([k, v]) => (
              <div key={k} style={{
                display: "flex", flexDirection: "column", alignItems: "center",
                padding: "6px 10px", borderRadius: 8,
                background: "rgba(255,255,255,0.04)", border: `1px solid ${STAT_COLOR[k] || "var(--border)"}22`,
                minWidth: 44,
              }}>
                <span style={{ fontSize: 10, color: STAT_COLOR[k] || "var(--text)", fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.5 }}>
                  {STAT_SHORT[k] || k}
                </span>
                <span style={{ fontSize: 20, fontWeight: 800, color: STAT_COLOR[k] || "var(--text-h)", lineHeight: 1.2 }}>{v}</span>
              </div>
            ))}
          </div>

          {/* Skills top */}
          {topSkills.length > 0 && (
            <div style={{ flex: 1, minWidth: 200 }}>
              <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.5, color: "var(--text-secondary)", marginBottom: 5 }}>
                Skill principali
              </div>
              <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
                {topSkills.map(([key, level]) => {
                  const skillDef = SKILL_LIST.find(s => s.key === key);
                  const statKey = skillDef?.stat;
                  const color = STAT_COLOR[statKey] || "var(--text)";
                  return (
                    <span key={key} style={{
                      fontSize: 11, padding: "2px 8px", borderRadius: 5,
                      background: `${color}18`, border: `1px solid ${color}44`,
                      color: "var(--text-h)",
                    }}>
                      <span style={{ color, fontWeight: 700 }}>{level}</span>
                      {" "}{skillDef?.label || key}
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          {/* Vantaggi */}
          {advantages.length > 0 && (
            <div style={{ minWidth: 140 }}>
              <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.5, color: "var(--text-secondary)", marginBottom: 5 }}>
                Vantaggi
              </div>
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                {advantages.map((adv, i) => (
                  <span key={i} style={{
                    fontSize: 11, padding: "2px 7px", borderRadius: 5,
                    background: "rgba(74,222,128,0.1)", border: "1px solid rgba(74,222,128,0.25)",
                    color: "#4ade80",
                  }} title={ADVANTAGE_LIST.find(a => a.key === adv)?.desc || ""}>
                    {adv}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Svantaggi */}
          {disadvantages.length > 0 && (
            <div style={{ minWidth: 140 }}>
              <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.5, color: "var(--text-secondary)", marginBottom: 5 }}>
                Svantaggi
              </div>
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                {disadvantages.map((dis, i) => (
                  <span key={i} style={{
                    fontSize: 11, padding: "2px 7px", borderRadius: 5,
                    background: "rgba(248,113,113,0.1)", border: "1px solid rgba(248,113,113,0.25)",
                    color: "#f87171",
                  }} title={DISADV_LIST.find(d => d.key === dis)?.desc || ""}>
                    {dis}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
        {/* Inventario / Equipaggiamento */}
        <EquipmentPanel player={player} onPlayersUpdate={onPlayersUpdate} />
      </div>
    </div>
  );
}

// Mini scheda sempre visibile — cliccabile per aprire la scheda completa
function PlayerChip({ player, active, onClick, avatar, onRename, expanded }) {
  const hpPct = Math.max(0, Math.min(100, ((player.hp ?? player.max_hp) / Math.max(player.max_hp, 1)) * 100));
  const hpColor = hpPct > 60 ? "#4ade80" : hpPct > 30 ? "#f59e0b" : "#ef4444";
  const stats = player.stats || {};
  return (
    <button onClick={onClick} style={{
      display: "flex", alignItems: "center", gap: 8,
      padding: "5px 10px 5px 5px", borderRadius: 12,
      border: active
        ? `2px solid ${expanded ? "#a78bfa" : "var(--accent)"}`
        : "1px solid var(--border)",
      background: active
        ? (expanded ? "rgba(167,139,250,0.12)" : "var(--accent-bg)")
        : "var(--code-bg)",
      cursor: "pointer", color: "var(--text-h)",
      transition: "all 0.15s", minWidth: 0,
    }}>
      <AvatarCircle src={avatar} size={36} fallback="🧑" />
      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 3, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {onRename
            ? <EditableName name={player.name} onRename={onRename} style={{ fontSize: 12, fontWeight: 700, lineHeight: 1 }} />
            : <span style={{ fontSize: 12, fontWeight: 700, lineHeight: 1 }}>{player.name}</span>
          }
          <span style={{ fontSize: 10, color: "var(--text)", opacity: 0.6, lineHeight: 1 }}>{player.role}</span>
        </div>
        {/* HP bar */}
        <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <div style={{ width: 52, height: 3, borderRadius: 2, background: "rgba(255,255,255,0.12)", overflow: "hidden" }}>
            <div style={{ height: "100%", borderRadius: 2, width: `${hpPct}%`, background: hpColor, transition: "width 0.4s" }} />
          </div>
          <span style={{ fontSize: 10, color: hpColor, fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>
            {player.hp ?? player.max_hp}/{player.max_hp}
          </span>
          {/* FO/DE/IN/SA mini */}
          {(stats.forza || stats.agilita || stats.intelligenza || stats.empatia) && (
            <span style={{ fontSize: 9, color: "var(--text)", opacity: 0.55, letterSpacing: 0.2 }}>
              {[["FO", stats.forza], ["DE", stats.agilita], ["IN", stats.intelligenza], ["SA", stats.empatia]]
                .filter(([, v]) => v != null).map(([l, v]) => `${l}${v}`).join(" ")}
            </span>
          )}
        </div>
      </div>
      {expanded && <span style={{ fontSize: 10, color: "#a78bfa", marginLeft: 2 }}>▲</span>}
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
  { key: "Agilità del Gatto",          cost: 10, label: "Agilità del Gatto",          desc: "Sottrae 5 m dalle cadute; aiuta acrobazie e salti" },
  { key: "Carisma",                   cost: 5,  label: "Carisma",                   desc: "+2 tiri reazione NPC, +2 skill sociali" },
  { key: "Bilanciamento Perfetto",     cost: 15, label: "Bilanciamento Perfetto",     desc: "+6 equilibrio difficile, +1 Acrobazia/Arrampicarsi" },
  { key: "Difesa Migliorata (Schivata)", cost: 15, label: "Difesa Migliorata: Schivata", desc: "+1 Schivata" },
  { key: "Riflessi da Combattimento", cost: 15, label: "Riflessi da Combattimento", desc: "+1 schivata/parata/blocco, mai sorpreso" },
  { key: "Duro da Uccidere",          cost: 2,  label: "Duro da Uccidere",          desc: "Soglia morte raddoppiata" },
  { key: "Duro da Uccidere 2",        cost: 4,  label: "Duro da Uccidere 2",        desc: "+2 alle valutazioni SA per sopravvivere" },
  { key: "Duro da Uccidere 3",        cost: 6,  label: "Duro da Uccidere 3",        desc: "+3 alle valutazioni SA per sopravvivere" },
  { key: "Elevata Soglia del Dolore", cost: 10, label: "Elevata Soglia del Dolore", desc: "Ignora shock; +3 contro stordimento/atterramento" },
  { key: "Sensi Acuti",               cost: 2,  label: "Sensi Acuti",               desc: "+2 Percezione e osservare" },
  { key: "Vista Acuta",               cost: 2,  label: "Vista Acuta",               desc: "+1 alle valutazioni basate sulla vista" },
  { key: "Vista Acuta 2",             cost: 4,  label: "Vista Acuta 2",             desc: "+2 alle valutazioni basate sulla vista" },
  { key: "Udito Acuto",               cost: 2,  label: "Udito Acuto",               desc: "+1 alle valutazioni basate sull'udito" },
  { key: "Visione Notturna",          cost: 1,  label: "Visione Notturna",          desc: "Ignora -1 da oscurità" },
  { key: "Visione Notturna 3",        cost: 3,  label: "Visione Notturna 3",        desc: "Ignora -3 da oscurità" },
  { key: "Visione Notturna 6",        cost: 6,  label: "Visione Notturna 6",        desc: "Ignora -6 da oscurità" },
  { key: "Forza Aumentata",           cost: 10, label: "Forza Aumentata",           desc: "+1 FO effettiva, +1 danni mischia" },
  { key: "Alta Tecnologia",           cost: 5,  label: "Alta Tecnologia",           desc: "+2 tecnologia e ingegneria" },
  { key: "Ambidestrezza",             cost: 5,  label: "Ambidestrezza",             desc: "Nessuna penalità mano non dominante" },
  { key: "Bellezza",                  cost: 4,  label: "Bellezza",                  desc: "+1 tiri di reazione, bonus seduzione" },
  { key: "Empatia",                   cost: 15, label: "Empatia",                   desc: "+3 Psicologia, percepisce bugie" },
  { key: "Empatia con gli Animali",   cost: 5,  label: "Empatia con gli Animali",   desc: "Capisce animali e può influenzarli" },
  { key: "Flessuoso",                 cost: 5,  label: "Flessuoso",                 desc: "+3 Arrampicarsi/liberarsi, ignora -3 in spazi stretti" },
  { key: "Snodato",                   cost: 15, label: "Snodato",                   desc: "+5 Arrampicarsi/liberarsi, ignora -5 in spazi stretti" },
  { key: "Memoria Fotografica",       cost: 10, label: "Memoria Fotografica",       desc: "+2 skill di conoscenza" },
  { key: "Coraggio",                  cost: 10, label: "Coraggio",                  desc: "+2 Volontà contro paura e stress" },
  { key: "Intrepido",                 cost: 2,  label: "Intrepido",                 desc: "+1 contro paura/intimidazione" },
  { key: "Intrepido 2",               cost: 4,  label: "Intrepido 2",               desc: "+2 contro paura/intimidazione" },
  { key: "Sangue Freddo",             cost: 5,  label: "Sangue Freddo",             desc: "Nessuna penalità shock su tiri mira" },
  { key: "Fortuna",                   cost: 15, label: "Fortuna",                   desc: "Ritira un tiro per sessione, prende il migliore" },
  { key: "Fortuna Straordinaria",     cost: 30, label: "Fortuna Straordinaria",     desc: "Come Fortuna, più frequente" },
  { key: "Fortuna Smodata",           cost: 60, label: "Fortuna Smodata",           desc: "Come Fortuna, molto più frequente" },
  { key: "Spericolato",               cost: 15, label: "Spericolato",               desc: "+1 quando corre rischi non necessari" },
  { key: "Contatti",                  cost: 3,  label: "Contatti",                  desc: "Rete informatori, +1 reazione nel gruppo" },
  { key: "Status Sociale",            cost: 5,  label: "Status Sociale",            desc: "+1 reazione in contesti sociali" },
  { key: "Ricchezza",                 cost: 10, label: "Ricchezza",                 desc: "Risorse finanziarie significative" },
  { key: "Talento",                   cost: 5,  label: "Talento",                   desc: "+1 a un gruppo tematico di skill" },
  { key: "Talento (Artificiere)",     cost: 10, label: "Talento: Artificiere",      desc: "+1 a skill tecniche" },
  { key: "Talento (Sopravvivenza)",   cost: 10, label: "Talento: Sopravvivenza",    desc: "+1 a sopravvivenza/esplorazione" },
  { key: "Talento (Parlantina)",      cost: 15, label: "Talento: Parlantina",       desc: "+1 alle abilità di Influenza" },
  { key: "Talento Linguistico",       cost: 10, label: "Talento Linguistico",       desc: "Migliora apprendimento e uso delle lingue" },
  { key: "Voce Bella",                cost: 10, label: "Voce Bella",                desc: "+2 intrattenere/parlare in pubblico" },
  { key: "Autorità",                  cost: 5,  label: "Autorità",                  desc: "NPC di rango inferiore obbediscono" },
  { key: "Linguaggio Nativo Extra",   cost: 3,  label: "Linguaggio Nativo Extra",   desc: "Parla un'altra lingua come madrelingua" },
  { key: "Istinto di Sopravvivenza",  cost: 5,  label: "Istinto di Sopravvivenza",  desc: "+1 sopravvivere, non viene mai colto di sorpresa" },
  { key: "Resistente alle Malattie",  cost: 3,  label: "Resistente alle Malattie",  desc: "+3 a SA contro malattie" },
  { key: "Resistente ai Veleni",      cost: 5,  label: "Resistente ai Veleni",      desc: "+3 a SA contro veleni" },
  { key: "Viaggiatore (Tempo)",       cost: 100,label: "Viaggiatore: Tempo",        desc: "Viaggia nel tempo con concentrazione e tiro IN" },
  { key: "Viaggiatore (Dimensioni)",  cost: 100,label: "Viaggiatore: Dimensioni",   desc: "Viaggia tra dimensioni con concentrazione e tiro IN" },
];
const DISADV_LIST = [
  { key: "Animo Sanguinario", cost: -10, label: "Animo Sanguinario", desc: "Morale check per ritirarsi" },
  { key: "Codardo",           cost: -5,  label: "Codardo",           desc: "-2 a tutti i tiri in pericolo fisico" },
  { key: "Codice d'Onore (Pirata)", cost: -5, label: "Codice d'Onore: Pirata", desc: "Vendica insulti, sostiene amici, duelli leali tra compagni" },
  { key: "Codice d'Onore (Gentiluomo)", cost: -10, label: "Codice d'Onore: Gentiluomo", desc: "Parola, duelli, niente vantaggi sleali" },
  { key: "Codice d'Onore (Formale)", cost: -15, label: "Codice d'Onore: Formale", desc: "Codice rigido sempre vincolante" },
  { key: "Sospettoso",        cost: -5,  label: "Sospettoso",        desc: "-2 skill sociali, +1 intuire" },
  { key: "Avidità",           cost: -15, label: "Avidità",           desc: "Volontà−3 per resistere all'avidità" },
  { key: "Curiosità",         cost: -5,  label: "Curiosità",         desc: "Autocontrollo per non esaminare cose pericolose" },
  { key: "Gelosia",           cost: -10, label: "Gelosia",           desc: "Reagisce male a rivali e protagonisti" },
  { key: "Ghiottoneria",      cost: -5,  label: "Ghiottoneria",      desc: "Autocontrollo davanti a cibo/bevande desiderabili" },
  { key: "Illusione Minore",  cost: -5,  label: "Illusione Minore",  desc: "Falsa convinzione, reazioni -1" },
  { key: "Illusione Maggiore",cost: -10, label: "Illusione Maggiore",desc: "Falsa convinzione condizionante, reazioni -2" },
  { key: "Illusione Severa",  cost: -15, label: "Illusione Severa",  desc: "Falsa convinzione grave, reazioni -3" },
  { key: "Senso del Dovere",  cost: -5,  label: "Senso del Dovere",  desc: "Non abbandona mai i compagni" },
  { key: "Senso del Dovere (Individuo)", cost: -2, label: "Senso del Dovere: Individuo", desc: "Vincolo verso una persona" },
  { key: "Senso del Dovere (Squadra)", cost: -5, label: "Senso del Dovere: Squadra", desc: "Vincolo verso la squadra" },
  { key: "Senso del Dovere (Nazione)", cost: -10, label: "Senso del Dovere: Nazione", desc: "Vincolo verso gruppo ampio" },
  { key: "Nemico",            cost: -5,  label: "Nemico",            desc: "Un nemico attivo interferisce regolarmente" },
  { key: "Segreto",           cost: -10, label: "Segreto",           desc: "Se scoperto, conseguenze gravi" },
  { key: "Dipendenza",        cost: -5,  label: "Dipendenza",        desc: "-1 a tutti i tiri in astinenza" },
  { key: "Fobia",             cost: -10, label: "Fobia",             desc: "Volontà−4 quando esposto alla fobia" },
  { key: "Fobia (Sangue)",    cost: -10, label: "Fobia: Sangue",     desc: "Penalità e panico davanti al sangue" },
  { key: "Fobia (Buio)",      cost: -15, label: "Fobia: Buio",       desc: "Penalità e panico nell'oscurità" },
  { key: "Fobia (Altezza)",   cost: -10, label: "Fobia: Altezza",    desc: "Penalità su altezze e precipizi" },
  { key: "Fobia (Ragni)",     cost: -5,  label: "Fobia: Ragni",      desc: "Autocontrollo quando sono presenti ragni" },
  { key: "Impulsività",       cost: -10, label: "Impulsività",       desc: "Volontà−2 per resistere all'impulso" },
  { key: "Intolleranza Totale", cost: -10, label: "Intolleranza Totale", desc: "Pregiudizio ampio, penalità sociali" },
  { key: "Intolleranza Specifica", cost: -5, label: "Intolleranza Specifica", desc: "Pregiudizio verso un gruppo specifico" },
  { key: "Irascibile",        cost: -10, label: "Irascibile",        desc: "Autocontrollo in situazioni stressanti" },
  { key: "Libidine",          cost: -15, label: "Libidine",          desc: "Autocontrollo in contatti passionali" },
  { key: "Onestà",            cost: -10, label: "Onestà",            desc: "Deve rispettare e far rispettare la legge" },
  { key: "Ossessione Breve",  cost: -5,  label: "Ossessione Breve",  desc: "Obiettivo ossessivo a breve termine" },
  { key: "Ossessione Lunga",  cost: -10, label: "Ossessione Lunga",  desc: "Obiettivo ossessivo a lungo termine" },
  { key: "Pacifismo (Riluttante a Uccidere)", cost: -5, label: "Pacifismo: Riluttante a Uccidere", desc: "-4 ad attacchi mortali contro persone" },
  { key: "Pacifismo (Incapace di Fare del Male a Innocenti)", cost: -10, label: "Pacifismo: Innocenti", desc: "Forza letale solo contro minacce serie" },
  { key: "Presunzione",       cost: -5,  label: "Presunzione",       desc: "Cautela difficile, reazioni miste" },
  { key: "Arroganza",         cost: -5,  label: "Arroganza",         desc: "-1 reazione con sconosciuti" },
  { key: "Lealtà",            cost: -5,  label: "Lealtà",            desc: "Non può agire contro i propri alleati" },
  { key: "Poca Autostima",    cost: -10, label: "Poca Autostima",    desc: "-2 leadership, -1 Volontà nei momenti critici" },
  { key: "Amnesia",           cost: -10, label: "Amnesia",           desc: "Penalità alle skill di conoscenza pregressa" },
  { key: "Mancanza di Empatia",cost:-15, label: "Mancanza di Empatia",desc: "-3 Psicologia, -2 skill sociali empatiche" },
  { key: "Curiosità Morbosa", cost: -5,  label: "Curiosità Morbosa", desc: "Volontà−2 per evitare luoghi pericolosi" },
  { key: "Smemoratezza",      cost: -5,  label: "Smemoratezza",      desc: "Può fallire il richiamo di info critiche" },
  { key: "Pessimismo",        cost: -5,  label: "Pessimismo",        desc: "-2 Leadership, penalizza il morale del gruppo" },
  { key: "Vista Imperfetta",  cost: -10, label: "Vista Imperfetta",  desc: "-2 osservare/mira quando la vista conta" },
  { key: "Sfortuna",          cost: -10, label: "Sfortuna",          desc: "Una volta per sessione il GM peggiora qualcosa" },
  { key: "Sincerità",         cost: -5,  label: "Sincerità",         desc: "-5 a mentire/ingannare" },
  { key: "Sordità Parziale",  cost: -10, label: "Sordità Parziale",  desc: "-4 a valutazioni sull'udito" },
  { key: "Vista Imperfetta Non Correggibile", cost: -25, label: "Vista Imperfetta non correggibile", desc: "-6 vista, -2 colpire, non correggibile" },
  { key: "Voto Minore",       cost: -5,  label: "Voto Minore",       desc: "Giuramento moderatamente limitante" },
  { key: "Voto Maggiore",     cost: -10, label: "Voto Maggiore",     desc: "Giuramento fortemente limitante" },
  { key: "Voto Superiore",    cost: -15, label: "Voto Superiore",    desc: "Giuramento estremamente vincolante" },
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

function normalizeGenreKey(value, fallback = "detective_classico") {
  const raw = String(value || "").trim().toLowerCase().replace(/[-\s]+/g, "_");
  if (GENRE_META[raw]) return raw;
  const blob = raw.replaceAll("_", " ");
  if (/fantasy|medioevo|medieval|dungeon|magia|cripta|drag/.test(blob)) return "fantasy";
  if (/horror|gotic|mystery|occult|lovecraft|malediz/.test(blob)) return "mystery_horror";
  if (/sci|space|cyber|alien|futuro/.test(blob)) return "sci_fi";
  if (/war|ww2|guerra|militar/.test(blob)) return "ww2";
  if (/detective|noir|investig|giallo/.test(blob)) return "detective_classico";
  if (/romance|sentiment/.test(blob)) return "romance";
  if (/action|thriller|azione/.test(blob)) return "action";
  return GENRE_META[fallback] ? fallback : "detective_classico";
}

// ─── Setup screen ──────────────────────────────────────────────────────────

function ProviderBtn({ pkey, label, icon, selected, available, onClick }) {
  const avail = available !== false;
  const sel = selected;
  return (
    <button onClick={() => avail && onClick(pkey)}
      title={pkey}
      style={{
        display: "flex", alignItems: "center", gap: 5,
        padding: "4px 10px", borderRadius: 20,
        border: sel ? "1.5px solid #c084fc" : "1px solid rgba(255,255,255,0.18)",
        background: sel ? "rgba(170,59,255,0.35)" : "rgba(0,0,0,0.5)",
        color: sel ? "#fff" : avail ? "rgba(255,255,255,0.75)" : "rgba(255,255,255,0.3)",
        cursor: avail ? "pointer" : "default",
        backdropFilter: "blur(8px)",
        transition: "all 0.15s",
        boxShadow: sel ? "0 0 8px rgba(192,132,252,0.35)" : "none",
        fontSize: 12, fontWeight: sel ? 700 : 400,
        opacity: avail ? 1 : 0.45,
        whiteSpace: "nowrap",
      }}>
      <span style={{ fontSize: 13 }}>{icon}</span>
      <span>{label}</span>
    </button>
  );
}

function TextProviderPicker({ value, onChange, available }) {
  const options = [
    { key: "claude", label: "Claude", icon: "🤖" },
    { key: "openai", label: "OpenAI", icon: "🟢" },
  ];
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <span style={{ fontSize: 9, color: "rgba(255,255,255,0.35)", textTransform: "uppercase", letterSpacing: 1.5, fontWeight: 600 }}>Testo</span>
      <div style={{ display: "flex", gap: 4 }}>
        {options.map(p => (
          <ProviderBtn key={p.key} pkey={p.key} label={p.label} icon={p.icon}
            selected={value === p.key} available={available[p.key] !== false} onClick={onChange} />
        ))}
      </div>
    </div>
  );
}

function ImageProviderPicker({ value, onChange, available }) {
  const options = [
    { key: "auto",   label: "Auto",    icon: "✨" },
    { key: "openai", label: "OpenAI",  icon: "🟢" },
    { key: "gemini", label: "Gemini",  icon: "💫" },
    { key: "none",   label: "Nessuna", icon: "🚫" },
  ];
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <span style={{ fontSize: 9, color: "rgba(255,255,255,0.35)", textTransform: "uppercase", letterSpacing: 1.5, fontWeight: 600 }}>Immagini</span>
      <div style={{ display: "flex", gap: 4 }}>
        {options.map(p => {
          const avail = p.key === "auto" || p.key === "none" ? true : available[p.key] !== false;
          return (
            <ProviderBtn key={p.key} pkey={p.key} label={p.label} icon={p.icon}
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
  const [teamStarting, setTeamStarting] = useState(false);
  const [jsonLoading, setJsonLoading] = useState(false);
  const [jsonError, setJsonError] = useState("");
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfError, setPdfError] = useState("");
  const [preloadedAdventure, setPreloadedAdventure] = useState(null);
  const [doctorReport, setDoctorReport] = useState(null); // {score, findings, enriching}
  const [doctorEnriching, setDoctorEnriching] = useState(false);
  const [hovered, setHovered] = useState(null);
  const [showBuilder, setShowBuilder] = useState(false);
  const [avatars, setAvatars] = useState({});
  const [avatarLoading, setAvatarLoading] = useState({});
  const [serverWaking, setServerWaking] = useState(false);
  const [wakeCountdown, setWakeCountdown] = useState(0);
  const _waking = useRef(false);

  // Keep-alive: ping ogni 13 minuti per evitare che Render spenga il backend
  useEffect(() => {
    const id = setInterval(() => { fetch(`${API_URL}/health`).catch(() => {}); }, 13 * 60 * 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    fetch(`${API_URL}/game/providers-available`).then(r => r.json()).then(d => {
      setProvidersAvail(d);
      if (!d.claude && d.openai) setProvider("openai");
      else if (!d.claude && !d.openai && d.gemini) setProvider("gemini");
    }).catch(() => {});
  }, []);

  async function handleJsonLoad(file) {
    setJsonLoading(true);
    setJsonError("");
    setPreloadedAdventure(null);
    const controller = new AbortController();
    try {
      const text = await file.text();
      let parsed;
      try {
        parsed = JSON.parse(text);
      } catch {
        throw new Error("File non valido: non è un JSON leggibile.");
      }
      // Supporta sia il formato export completo che il formato compiled_adventure
      const compiled = parsed.compiled_adventure || parsed;
      const definition = compiled.adventure_definition || parsed.adventure_definition || null;
      if (!definition) throw new Error("JSON non valido: adventure_definition mancante.");

      const detectedGenre = normalizeGenreKey(
        definition.genre || compiled.genre || parsed.genre || "detective_classico",
        "detective_classico"
      );
      const adventure = {
        ...compiled,
        ...definition,  // eleva clues, actors, story_threads, locations ecc. al livello root
        id: definition.id || compiled.id,
        runtime_id: definition.id || compiled.runtime_id,
        genre: detectedGenre,
        detected_genre: detectedGenre,
        adventure_definition: definition,
        runtime_state: compiled.runtime_state || parsed.runtime_state || null,
        validation_report: compiled.validation_report || parsed.validation_report || null,
        from_json_load: true,
      };
      setPreloadedAdventure(adventure);
      setGenre(detectedGenre);

      // Doctor: audit rapido subito, poi fix in background mentre si scelgono i personaggi
      setDoctorReport(null);
      try {
        const drAudit = await fetch(`${API_URL}/game/adventure/doctor`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ adventure_definition: definition, enrich: false }),
        }).then(r => r.json());
        if (!drAudit.error) setDoctorReport({ ...drAudit, source: "json" });

        // Se ci sono problemi, avvia il fix in background (non aspettiamo)
        const needsFix = (drAudit.findings || []).some(f => f.severity !== "info");
        if (needsFix) {
          setDoctorEnriching(true);
          fetch(`${API_URL}/game/adventure/doctor`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ adventure_definition: definition, enrich: true }),
          }).then(r => r.json()).then(drFix => {
            if (!drFix.error && drFix.enriched_definition) {
              const enrichedDef = drFix.enriched_definition;
              setPreloadedAdventure(prev => ({
                ...prev,
                ...enrichedDef,
                adventure_definition: enrichedDef,
              }));
              setDoctorReport({ ...drFix, source: "enriched", enriched_definition: undefined });
            }
          }).catch(() => {}).finally(() => setDoctorEnriching(false));
        }
      } catch (_) {}

      setLoading(true);
      await fetch(`${API_URL}/game/setup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ genre: detectedGenre, provider, image_provider: imageProvider }),
      });
      const s = await fetch(`${API_URL}/game/state`).then(r => r.json());
      const rawPool = s?.team_setup?.candidate_pool || [];
      if (rawPool.length === 0) throw new Error(`JSON caricato, ma nessun personaggio generato per il genere "${detectedGenre}".`);
      let contextualPool = rawPool;
      try {
        const enriched = await fetch(`${API_URL}/game/character/enrich-backstory`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          signal: controller.signal,
          body: JSON.stringify({ characters: rawPool, adventure, genre: detectedGenre }),
        }).then(r => r.json());
        if (enriched.characters) contextualPool = enriched.characters;
      } catch (_) {}
      setPool(contextualPool);
      setSelected([]);
      setLoading(false);
      setJsonLoading(false);
      setStep("team");
    } catch (e) {
      setLoading(false);
      setJsonLoading(false);
      setJsonError(e.message || "Errore durante il caricamento del JSON.");
    }
  }

  function handleDownloadAdventureJson() {
    if (!preloadedAdventure) return;
    const payload = buildAdventureExport({ adventure: preloadedAdventure, source: "json_load" });
    downloadJsonFile(payload, `${safeFilePart(payload.title)}-compilata.json`);
  }

  async function handleDoctorEnrich() {
    if (!preloadedAdventure?.adventure_definition) return;
    setDoctorEnriching(true);
    try {
      const dr = await fetch(`${API_URL}/game/adventure/doctor`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ adventure_definition: preloadedAdventure.adventure_definition, enrich: true }),
      }).then(r => r.json());
      if (dr.error) { setDoctorEnriching(false); return; }
      if (dr.enriched_definition) {
        const enrichedDef = dr.enriched_definition;
        setPreloadedAdventure(prev => ({
          ...prev,
          ...enrichedDef,
          adventure_definition: enrichedDef,
        }));
        setDoctorReport({ score: dr.score_after ?? dr.score, findings: [], findings_count: 0, source: "enriched" });
      }
    } catch (_) {}
    setDoctorEnriching(false);
  }

  async function handlePdfUpload(file) {
    setPdfLoading(true); setPdfError(""); setPreloadedAdventure(null);
    try {
      if (file.size > VERCEL_PDF_UPLOAD_LIMIT_BYTES)
        throw new Error(`PDF troppo grande (${(file.size/1024/1024).toFixed(1)} MB). Limite: 4 MB.`);
      const fd = new FormData();
      fd.append("file", file);
      fd.append("genre", genre || "detective_classico");
      fd.append("players", "4");
      fd.append("provider", provider);
      const res = await fetch(`${API_URL}/game/adventure/from-pdf`, { method: "POST", body: fd });
      const data = await res.json();
      if (data.compilation_failed) {
        const gate = data.quality_gate || {};
        const critical = (gate.critical || []).map(c => `• ${c}`).join("\n");
        const warn = (gate.warnings || []).map(w => `⚠ ${w}`).join("\n");
        throw new Error(
          `Il PDF non ha prodotto un'avventura giocabile (score: ${gate.score ?? "??"}/100).\n\n` +
          (critical ? `Problemi critici:\n${critical}` : "") +
          (warn ? `\n\nAvvertimenti:\n${warn}` : "")
        );
      }
      if (data.error) throw new Error(data.error);
      const compiled = data.compiled_adventure || data;
      const definition = compiled.adventure_definition || null;
      if (!definition) throw new Error("Compilazione fallita: adventure_definition mancante.");
      const detectedGenre = normalizeGenreKey(definition.genre || compiled.genre || "detective_classico", "detective_classico");
      const adventure = {
        ...compiled, ...definition,
        id: definition.id || compiled.id,
        runtime_id: definition.id || compiled.runtime_id,
        genre: detectedGenre, detected_genre: detectedGenre,
        adventure_definition: definition,
        runtime_state: compiled.runtime_state || null,
        validation_report: compiled.validation_report || null,
        from_pdf_load: true,
      };
      setPreloadedAdventure(adventure); setGenre(detectedGenre);

      // Doctor report già calcolato e fix applicato dal backend durante la compilazione PDF
      if (data.doctor) {
        const src = data.doctor.auto_fixed ? "enriched" : "pdf";
        setDoctorReport({ ...data.doctor, source: src });
      } else setDoctorReport(null);

      setLoading(true);
      await fetch(`${API_URL}/game/setup`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ genre: detectedGenre, provider, image_provider: imageProvider }) });
      const s = await fetch(`${API_URL}/game/state`).then(r => r.json());
      const rawPool = s?.team_setup?.candidate_pool || [];
      const enriched = await Promise.all(rawPool.map(async p => {
        try {
          const r = await fetch(`${API_URL}/game/enrich-backstory`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ character: p, adventure_context: definition?.premise || definition?.title || "" }) });
          const d = await r.json(); return d.character || p;
        } catch { return p; }
      }));
      setPool(enriched); setStep("team");
    } catch (e) { setPdfError(e.message || "Errore caricamento PDF"); }
    finally { setPdfLoading(false); setLoading(false); }
  }

  async function handleGenreSelect(g) {
    setGenre(g);
    setLoading(true);
    setJsonError("");
    try {
      const created = await fetch(`${API_URL}/game/adventure/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ genre: g, players: [] }),
      }).then(r => r.json());
      if (created.error) throw new Error(created.error);
      const detectedGenre = normalizeGenreKey(
        created.detected_genre || created.genre || created.adventure_definition?.genre || g,
        g
      );
      created.genre = detectedGenre;
      created.detected_genre = detectedGenre;
      setPreloadedAdventure(created);
      // Doctor report già calcolato e fix applicato dal backend
      if (created.doctor) {
        const src = created.doctor.auto_fixed ? "enriched" : "ai";
        setDoctorReport({ ...created.doctor, source: src });
      }
      await fetch(`${API_URL}/game/setup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ genre: detectedGenre, provider, image_provider: imageProvider }),
      });
      const s = await fetch(`${API_URL}/game/state`).then(r => r.json());
      const rawPool = s?.team_setup?.candidate_pool || [];
      if (rawPool.length === 0) throw new Error(`Avventura creata, ma nessun personaggio generato per il genere "${detectedGenre}".`);
      let contextualPool = rawPool;
      try {
        const enriched = await fetch(`${API_URL}/game/character/enrich-backstory`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ characters: rawPool, adventure: created, genre: detectedGenre }),
        }).then(r => r.json());
        if (enriched.characters) contextualPool = enriched.characters;
      } catch (_) {}
      setGenre(detectedGenre);
      setPool(contextualPool);
      setSelected([]);
      setStep("team");
    } catch (e) {
      setJsonError(e.message || "Impossibile generare l'avventura.");
    }
    setLoading(false);
  }

  function toggleSelect(id) {
    setSelected(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : prev.length < 4 ? [...prev, id] : prev
    );
  }

  async function wakeAndRetry() {
    if (_waking.current) return;
    _waking.current = true;
    setServerWaking(true);
    setJsonError("");
    const maxAttempts = 24; // 24 × 5s = 120s
    for (let i = 0; i < maxAttempts; i++) {
      setWakeCountdown(Math.max(0, (maxAttempts - i) * 5));
      try {
        const r = await fetch(`${API_URL}/health`, { signal: AbortSignal.timeout(8000) });
        if (r.ok) {
          _waking.current = false;
          setServerWaking(false);
          setWakeCountdown(0);
          await handleStart(true);
          return;
        }
      } catch (_) {}
      await new Promise(r => setTimeout(r, 5000));
    }
    _waking.current = false;
    setServerWaking(false);
    setWakeCountdown(0);
    setJsonError("Il server non risponde dopo 2 minuti. Controlla lo stato su render.com e riprova.");
  }

  async function handleStart(skipWake = false) {
    if (selected.length < 1) return;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 180000); // 3 minuti
    const isQuickStart = !!preloadedAdventure;
    if (isQuickStart) setTeamStarting(true);
    else setLoading(true);
    setJsonError("");
    try {
      // Warmup ping: sveglia Render prima delle chiamate principali (free tier dorme dopo 15min)
      try { await fetch(`${API_URL}/health`, { signal: AbortSignal.timeout(70000) }); } catch (_) {}
      let adventureForStart = preloadedAdventure;
      let poolForStart = pool;
      if (!adventureForStart) {
        const selectedDrafts = pool.filter(p => selected.includes(p.id));
        const selectedDicts = selectedDrafts.map(p => ({
          id: p.id, name: p.name, role: p.role, archetype: p.archetype || p.role || "custom",
          stats: p.stats || {}, skills: p.skills || {},
          advantages: p.advantages || [], disadvantages: p.disadvantages || [],
          hp: p.hp, max_hp: p.max_hp, fp: p.fp, max_fp: p.max_fp,
          dr: p.dr || 0, items: p.items || [], actions: p.actions || [],
          backstory: p.backstory || "", motivation: p.motivation || "",
        }));
        const created = await fetch(`${API_URL}/game/adventure/create`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          signal: controller.signal,
          body: JSON.stringify({ genre, players: selectedDicts }),
        }).then(r => r.json());
        if (created.error) throw new Error(created.error);
        adventureForStart = created;
        setPreloadedAdventure(created);
        if (created.doctor) {
          const src = created.doctor.auto_fixed ? "enriched" : "ai";
          setDoctorReport({ ...created.doctor, source: src });
        }
        try {
          const enriched = await fetch(`${API_URL}/game/character/enrich-backstory`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            signal: controller.signal,
            body: JSON.stringify({ characters: poolForStart, adventure: created, genre }),
          }).then(r => r.json());
          if (enriched.characters) {
            poolForStart = enriched.characters;
            setPool(enriched.characters);
          }
        } catch (_) {}
      }
      const stateRes = await fetch(`${API_URL}/game/select-team`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ selected_player_ids: selected, adventure_bible: adventureForStart }),
        signal: controller.signal,
      }).then(r => r.json());
      if (stateRes.detail) throw new Error(stateRes.detail);
      clearTimeout(timeoutId);
      // Merge backend players with enriched pool data (backstory, motivation, enriched advantages/disadvantages)
      const rawPlayers = stateRes?.players || poolForStart.filter(p => selected.includes(p.id));
      const players = rawPlayers.map(p => {
        const enriched = poolForStart.find(x => x.id === p.id);
        if (!enriched) return p;
        return {
          ...p,
          backstory: enriched.backstory || "",
          motivation: enriched.motivation || "",
          advantages: enriched.advantages?.length > 0 ? enriched.advantages : (p.advantages || []),
          disadvantages: enriched.disadvantages?.length > 0 ? enriched.disadvantages : (p.disadvantages || []),
        };
      });
      setTeamStarting(false);
      setLoading(false);
      onStart(genre, players, avatars, provider, adventureForStart, imageProvider);
    } catch (e) {
      clearTimeout(timeoutId);
      setLoading(false);
      setTeamStarting(false);
      const isTimeout = e?.name === "AbortError";
      const isNetwork = e?.message === "Load failed" || e?.message === "Failed to fetch" || e?.message?.includes("NetworkError");
      let msg;
      if (isTimeout && import.meta.env.PROD && !skipWake) { wakeAndRetry(); return; }
      else if (isNetwork && import.meta.env.PROD && !skipWake) { wakeAndRetry(); return; }
      else if (isTimeout) msg = "Il server impiega troppo tempo a rispondere. Se usi Render free tier, aspetta 60s e riprova.";
      else if (isNetwork && !import.meta.env.PROD) msg = "Backend non raggiungibile su " + (typeof API_URL !== "undefined" ? API_URL : "localhost:8002") + ". Avvia il server con: cd backend && uvicorn App.main:app --port 8002";
      else if (isNetwork) msg = "Server non raggiungibile. Riprova.";
      else msg = e.message || "Errore di connessione al server.";
      setJsonError(msg);
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
        { at: 0,     pill: "Mappa",      label: "Genero la mappa strategica con nodi e connessioni..." },
        { at: 8000,  pill: "Locations",  label: "Descrivo ogni location: atmosfera, pericoli e uscite..." },
        { at: 18000, pill: "NPC",        label: "Piazzo i personaggi non giocanti nelle loro location..." },
        { at: 30000, pill: "Fazioni",    label: "Definisco agende, alleanze e conflitti tra fazioni..." },
        { at: 42000, pill: "Schede",     label: "Genero le schede GURPS con skill, stat e equipaggiamento..." },
        { at: 55000, pill: "Apertura",   label: "Preparo la scena d'apertura e il briefing iniziale..." },
      ]}
    />
  );

  // ── Avvio rapido squadra (avventura già pronta) ──
  if (teamStarting) return (
    <LoadingProgress
      icon="⚔️"
      title="Avvio la sessione..."
      steps={[
        { at: 0,    pill: "Squadra",   label: "Registro la composizione del gruppo..." },
        { at: 2000, pill: "Mondo",     label: "Sincronizo lo stato del mondo con i personaggi..." },
        { at: 5000, pill: "Pronto",    label: "Quasi tutto pronto, sto aprendo la scena..." },
      ]}
    />
  );

  // ── PDF loading a schermo intero ──
  if (pdfLoading) return (
    <LoadingProgress
      icon="📄"
      title="Compilo l'avventura dal PDF..."
      steps={[
        { at: 0,     pill: "Lettura",     label: "Estraggo il testo dal PDF..." },
        { at: 3000,  pill: "Struttura",   label: "Analizzo la struttura narrativa..." },
        { at: 10000, pill: "Personaggi",  label: "Genero attori, clue e location..." },
        { at: 25000, pill: "Runtime",     label: "Costruisco il runtime e i clock..." },
      ]}
    />
  );

  // ── JSON loading a schermo intero ──
  if (jsonLoading) return (
    <LoadingProgress
      icon="📂"
      title="Carico l'avventura e preparo i personaggi..."
      steps={[
        { at: 0,    pill: "Lettura",     label: "Leggo il file JSON..." },
        { at: 800,  pill: "Parsing",     label: "Valido adventure_definition e runtime_state..." },
        { at: 2000, pill: "Setup",       label: "Genero il pool personaggi per il genere rilevato..." },
        { at: 6000, pill: "Backstory",   label: "Contestualizzo i backstory dei personaggi all'avventura..." },
      ]}
    />
  );

  // ── Step 1: scegli genere ──
  if (step === "genre") {
    const genres = Object.keys(GENRE_META);
    return (
      <div style={{ height: "100vh", background: "#000", display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* banner full-width */}
        <img src="/Banner superiore GURPS.png" alt="GURPS Master GDR" style={{ width: "100%", display: "block", objectFit: "contain", flexShrink: 0, maxHeight: "18vh" }} />

        {/* barra provider + carica JSON */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 12, padding: "6px 16px", background: "#0a0a0a", flexWrap: "wrap", flexShrink: 0 }}>
          <TextProviderPicker value={provider} onChange={setProvider} available={providersAvail} />
          <div style={{ width: 1, height: 24, background: "rgba(255,255,255,0.12)", flexShrink: 0 }} />
          <ImageProviderPicker value={imageProvider} onChange={setImageProvider} available={providersAvail} />
          <div style={{ width: 1, height: 24, background: "rgba(255,255,255,0.12)", flexShrink: 0 }} />
          <label style={{ cursor: "pointer", flexShrink: 0 }}>
            <img
              src={caricaPdfImg}
              alt="Carica PDF"
              style={{ height: 32, display: "block", borderRadius: 7, transition: "opacity 0.15s" }}
              onMouseEnter={e => e.currentTarget.style.opacity = "0.85"}
              onMouseLeave={e => e.currentTarget.style.opacity = "1"}
            />
            <input
              type="file" accept=".pdf" style={{ display: "none" }}
              onChange={e => e.target.files[0] && handlePdfUpload(e.target.files[0])}
            />
          </label>
          <label style={{ cursor: "pointer", flexShrink: 0 }}>
            <img
              src={caricaJsonImg}
              alt="Carica JSON avventura"
              title="Carica un JSON avventura e avvia la partita"
              style={{ height: 32, display: "block", borderRadius: 7, transition: "opacity 0.15s" }}
              onMouseEnter={e => e.currentTarget.style.opacity = "0.85"}
              onMouseLeave={e => e.currentTarget.style.opacity = "1"}
            />
            <input
              type="file" accept=".json" style={{ display: "none" }}
              onChange={e => e.target.files[0] && handleJsonLoad(e.target.files[0])}
            />
          </label>

          <div style={{ width: 1, height: 24, background: "rgba(255,255,255,0.12)", flexShrink: 0 }} />

          {/* JSON Doctor standalone — analizza senza avviare la partita */}
          <label style={{ cursor: "pointer", flexShrink: 0 }} title="Analizza un JSON con il Doctor senza avviare la partita">
            <img
              src={jsonDoctorImg}
              alt="JSON Doctor — Analizza qualità"
              style={{ height: 32, display: "block", borderRadius: 7, transition: "opacity 0.15s" }}
              onMouseEnter={e => e.currentTarget.style.opacity = "0.85"}
              onMouseLeave={e => e.currentTarget.style.opacity = "1"}
            />
            <input
              type="file" accept=".json" style={{ display: "none" }}
              onChange={async e => {
                const file = e.target.files[0];
                if (!file) return;
                e.target.value = "";
                setDoctorReport(null);
                setDoctorEnriching(false);
                setJsonError("");
                try {
                  const text = await file.text();
                  const parsed = JSON.parse(text);
                  const compiled = parsed.compiled_adventure || parsed;
                  const definition = compiled.adventure_definition || parsed.adventure_definition || parsed;
                  // Salva l'avventura per abilitare il bottone "Migliora"
                  setPreloadedAdventure(adv => adv || { adventure_definition: definition, from_json_load: true });
                  if (!preloadedAdventure) {
                    setPreloadedAdventure({ adventure_definition: definition, from_json_load: true });
                  }
                  const dr = await fetch(`${API_URL}/game/adventure/doctor`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ adventure_definition: definition, enrich: false }),
                  }).then(r => r.json());
                  if (!dr.error) setDoctorReport({ ...dr, source: "json_standalone" });
                  else setJsonError("Doctor: " + (dr.error || "analisi fallita"));
                } catch (err) {
                  setJsonError("Errore Doctor: " + (err.message || "file non valido"));
                }
              }}
            />
          </label>
        </div>
        {(pdfError || jsonError) && (
          <div style={{ textAlign: "center", color: "#f87171", fontSize: 13, padding: "4px 0 6px", background: "#0a0a0a" }}>
            ❌ {pdfError || jsonError}
          </div>
        )}

        {/* ── Bottone test rapido combattimento ── */}
        <div style={{ textAlign: "center", padding: "4px 0 4px", background: "#0a0a0a", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          <button onClick={async () => {
            const res = await fetch(`${API_URL}/game/debug/start-combat`, { method: "POST" })
              .then(r => r.json()).catch(() => ({}));
            if (res.ok) {
              const minAdv = {
                id: "test_combat", title: "Test Combattimento", genre: "action",
                adventure_definition: { id: "test_combat", title: "Test Combattimento", genre: "action",
                  clues: [], actors: [], story_threads: [], locations: [], event_clocks: [] }
              };
              onStart("action", res.players || [], {}, provider, minAdv, imageProvider);
            }
          }} style={{
            padding: "5px 18px", borderRadius: 8, border: "1px solid rgba(239,68,68,0.4)",
            background: "rgba(239,68,68,0.12)", color: "#f87171",
            fontSize: 12, fontWeight: 700, cursor: "pointer", letterSpacing: 0.3,
          }}>⚔ Test rapido combattimento</button>
        </div>

        {/* Doctor report badge */}
        {doctorReport && !doctorEnriching && (
          <div style={{
            display: "flex", flexDirection: "column", gap: 6,
            padding: "6px 16px 8px", background: "#0d0d0d",
            borderTop: "1px solid rgba(255,255,255,0.07)", flexShrink: 0,
          }}>
            {(() => {
              const sc = doctorReport.score ?? 0;
              const color = sc >= 9 ? "#4ade80" : sc >= 6 ? "#facc15" : "#f87171";
              const label = sc >= 9 ? "Ottima qualità" : sc >= 6 ? "Qualità discreta" : "Qualità bassa";
              const findings = doctorReport.findings || [];
              const criticals = findings.filter(f => f.severity === "critical");
              const warnings  = findings.filter(f => f.severity === "warning");
              const infos     = findings.filter(f => f.severity === "info");
              // Raggruppa per categoria per mostrare chip
              const catIcons = {
                structure: "🏗️", npc: "🎭", clock: "⏱️", clue: "🔍",
                thread: "🧵", location: "📍", resource: "⚖️", equipment: "⚔️",
              };
              const byCat = {};
              findings.forEach(f => { byCat[f.category] = (byCat[f.category] || 0) + 1; });
              return (
                <>
                  {/* riga score + bottone */}
                  <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                    <span style={{ color, fontWeight: 700, fontSize: 13 }}>
                      ✦ Qualità: {sc}/10 — {label}
                    </span>
                    <span style={{ color: "#94a3b8", fontSize: 11 }}>
                      {criticals.length > 0 && <span style={{ color: "#f87171" }}>🔴 {criticals.length} critico{criticals.length > 1 ? "i" : ""} </span>}
                      {warnings.length > 0  && <span style={{ color: "#facc15" }}>🟡 {warnings.length} warning{warnings.length > 1 ? "s" : ""} </span>}
                      {infos.length > 0     && <span style={{ color: "#60a5fa" }}>🔵 {infos.length} info</span>}
                    </span>
                    {sc < 9.5 && (
                      <img
                        src={jsonDoctorImg}
                        alt="JSON Doctor — Migliora con AI"
                        onClick={handleDoctorEnrich}
                        title="Migliora con AI: aggiunge campi mancanti, arricchisce NPC, clock e indizi"
                        style={{ height: 28, cursor: "pointer", borderRadius: 6, marginLeft: "auto", transition: "opacity 0.15s" }}
                        onMouseEnter={e => e.currentTarget.style.opacity = "0.75"}
                        onMouseLeave={e => e.currentTarget.style.opacity = "1"}
                      />
                    )}
                    {doctorReport.source === "enriched" && (
                      <span style={{ color: "#4ade80", fontSize: 11 }}>
                        ✓ Auto-corretta
                        {doctorReport.score_after != null && doctorReport.score_after !== doctorReport.score
                          ? ` (${doctorReport.score} → ${doctorReport.score_after}/10)`
                          : ""}
                      </span>
                    )}
                  </div>
                  {/* chip per categoria */}
                  {Object.keys(byCat).length > 0 && (
                    <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
                      {Object.entries(byCat).map(([cat, n]) => (
                        <span key={cat} style={{
                          padding: "1px 7px", borderRadius: 10, fontSize: 10, fontWeight: 600,
                          background: "rgba(255,255,255,0.07)", color: "rgba(255,255,255,0.55)",
                        }}>
                          {catIcons[cat] || "•"} {cat} ×{n}
                        </span>
                      ))}
                    </div>
                  )}
                  {/* dettaglio critici visibile direttamente */}
                  {criticals.length > 0 && (
                    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                      {criticals.map((f, i) => (
                        <div key={i} style={{ fontSize: 10, color: "#fca5a5" }}>
                          🔴 {f.message}
                          {f.fix_hint && <span style={{ color: "rgba(255,255,255,0.3)", marginLeft: 4 }}>→ {f.fix_hint}</span>}
                        </div>
                      ))}
                    </div>
                  )}
                </>
              );
            })()}
          </div>
        )}
        {doctorEnriching && (
          <div style={{
            textAlign: "center", padding: "5px 16px", background: "#0d0d0d",
            borderTop: "1px solid rgba(255,255,255,0.07)", flexShrink: 0,
            color: "#a5b4fc", fontSize: 12, display: "flex", alignItems: "center",
            justifyContent: "center", gap: 8,
          }}>
            <span style={{ display: "inline-block", animation: "spin 1s linear infinite" }}>⚙️</span>
            Doctor: correzione automatica in corso...
          </div>
        )}

        {/* splash image con overlay zone cliccabili */}
        <div style={{ position: "relative", width: "100%", flex: 1, minHeight: 0 }}>
          <img
            src="/Temi_Narrativi_2.png"
            alt="Generi narrativi"
            style={{ width: "100%", height: "100%", display: "block", objectFit: "cover", objectPosition: "center" }}
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

        {(loading || jsonLoading) && (
          <div style={{ textAlign: "center", padding: 12, color: "rgba(255,255,255,0.6)", fontSize: 14, background: "#0a0a0a" }}>
            {jsonLoading ? "📂 Carico avventura dal JSON..." : "Carico personaggi..."}
          </div>
        )}
      </div>
    );
  }

  // ── Step 2: scegli personaggi ──
  const meta = GENRE_META[genre] || { emoji: "🎲", label: genre, gradient: "135deg, #1a1a1a, #2a2a2a" };
  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", alignItems: "center", overflowY: "auto", padding: "24px 16px", background: "var(--bg)", boxSizing: "border-box" }}>
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
        width: "100%", maxWidth: 860, borderRadius: 16, marginBottom: 20, overflow: "hidden",
        background: `linear-gradient(${meta.gradient})`, boxShadow: "0 4px 24px rgba(0,0,0,0.5)",
      }}>
        <div style={{ padding: "16px 24px", display: "flex", alignItems: "center", gap: 14 }}>
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

      <div style={{ width: "100%", maxWidth: 860 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
          <div style={{ fontWeight: 700, fontSize: 15, color: "var(--text-h)" }}>
            Scegli il tuo gruppo (1–4 personaggi)
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            {preloadedAdventure && (
              <button onClick={handleDownloadAdventureJson} style={{
                padding: "7px 12px", borderRadius: 8, border: "1px solid rgba(74,222,128,0.45)",
                background: "rgba(74,222,128,0.10)", color: "#bbf7d0",
                cursor: "pointer", fontSize: 13, fontWeight: 800,
              }}>Scarica JSON</button>
            )}
            <button onClick={() => setShowBuilder(true)} style={{
              padding: "7px 16px", borderRadius: 8, border: "1px solid var(--accent)",
              background: "var(--accent-bg)", color: "var(--accent)",
              cursor: "pointer", fontSize: 13, fontWeight: 700,
            }}>+ Crea personaggio</button>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 28 }}>
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
                <div style={{ padding: "10px 10px 11px", cursor: "pointer" }} onClick={() => toggleSelect(p.id)}>
                  {/* avatar cerchio + bottoni */}
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                    <div style={{ position: "relative", flexShrink: 0 }}>
                      <AvatarCircle src={av} size={76} fallback="🧑" />
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

        {serverWaking && (
          <div style={{ color: "#f59e0b", fontSize: 13, padding: "10px 14px", borderRadius: 8, background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.3)", marginBottom: 10, lineHeight: 1.5 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
              <span style={{ display: "inline-block", animation: "spin 1.2s linear infinite" }}>⏳</span>
              <strong>Server Render in avvio...</strong>
            </div>
            <div style={{ opacity: 0.8, fontSize: 12 }}>
              Render free tier si sveglia dopo inattività (30–90 secondi). Riprovo automaticamente tra <strong>{wakeCountdown}s</strong>.
            </div>
            <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
          </div>
        )}
        {!serverWaking && jsonError && (
          <div style={{ color: "#f87171", fontSize: 13, padding: "10px 14px", borderRadius: 8, background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", marginBottom: 10, lineHeight: 1.4, display: "flex", flexDirection: "column", gap: 6 }}>
            <span>❌ {jsonError}</span>
            {import.meta.env.PROD && (
              <button onClick={() => wakeAndRetry()} style={{ alignSelf: "flex-start", padding: "4px 12px", borderRadius: 6, border: "1px solid rgba(239,68,68,0.5)", background: "rgba(239,68,68,0.15)", color: "#f87171", fontSize: 12, cursor: "pointer", fontWeight: 600 }}>
                ↻ Riprova svegliare il server
              </button>
            )}
          </div>
        )}
        <button onClick={() => handleStart()} disabled={selected.length === 0 || loading || serverWaking} style={{
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

function AnimatedDots() {
  const [dots, setDots] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setDots(d => (d + 1) % 4), 500);
    return () => clearInterval(id);
  }, []);
  return <span style={{ display: "inline-block", width: 18, textAlign: "left" }}>{"...".slice(0, dots)}</span>;
}

function LoadingProgress({ steps, icon = "📖", title }) {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const timers = steps.map((s, i) =>
      setTimeout(() => setPhase(i), s.at)
    );
    return () => timers.forEach(clearTimeout);
  }, []);

  const current = steps[phase] || steps[steps.length - 1];
  const rawPct = Math.round(((phase + 1) / steps.length) * 100);
  const pct = Math.min(rawPct, 95);
  const isLast = phase === steps.length - 1;

  const shimmerStyle = isLast ? `
    @keyframes lp-shimmer {
      0%   { background-position: -400px 0; }
      100% { background-position: 400px 0; }
    }
  ` : "";

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 24, background: "var(--bg)", padding: "0 32px" }}>
      {shimmerStyle && <style>{shimmerStyle}</style>}
      <div style={{ fontSize: 56 }}>{icon}</div>
      <div style={{ fontSize: 20, fontWeight: 800, color: "var(--text-h)", textAlign: "center" }}>{title}</div>

      {/* barra progresso */}
      <div style={{ width: "100%", maxWidth: 420 }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--text)", marginBottom: 8 }}>
          <span style={{ fontStyle: "italic" }}>
            {current.label}{isLast && <AnimatedDots />}
          </span>
          <span style={{ fontWeight: 700, color: "var(--accent)" }}>{pct}%</span>
        </div>
        <div style={{ height: 6, borderRadius: 6, background: "var(--border)", overflow: "hidden" }}>
          <div style={{
            height: "100%", borderRadius: 6,
            width: `${pct}%`,
            transition: "width 0.8s ease",
            background: isLast
              ? "linear-gradient(90deg, #7c3aed 0%, #c084fc 40%, #e9d5ff 50%, #c084fc 60%, #7c3aed 100%)"
              : "linear-gradient(90deg, #7c3aed, #c084fc)",
            backgroundSize: isLast ? "800px 100%" : "auto",
            animation: isLast ? "lp-shimmer 1.6s linear infinite" : "none",
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

      {isLast && (
        <div style={{ fontSize: 11, color: "var(--text)", opacity: 0.5, textAlign: "center", maxWidth: 320 }}>
          L'IA sta elaborando — potrebbe volerci qualche secondo in più
        </div>
      )}
    </div>
  );
}

// ─── Side Panel ────────────────────────────────────────────────────────────

function deriveStoryThreads(adventure, cluesFound = [], clueProgress = {}, resolvedThreads = []) {
  const found = new Set(cluesFound || []);
  const resolvedText = new Set((resolvedThreads || []).map(x => String(x).split("→")[0].trim()));
  const cluesById = Object.fromEntries((adventure?.clues || []).map(c => [c.id, c]));
  return (adventure?.story_threads || []).map(t => {
    const required = t.required_clues || [];
    const discovered = required.filter(id => found.has(id));
    const partial = required.filter(id => !found.has(id) && (clueProgress?.[id]?.ticks || 0) > 0);
    const requiredDetails = required.map(id => ({
      id,
      clue: cluesById[id],
      found: found.has(id),
      progress: clueProgress?.[id] || null,
    }));
    const minimum = t.minimum_clues_to_deduce || Math.min(2, Math.max(1, required.length || 1));
    const isResolved = resolvedText.has(t.id) || resolvedText.has(t.question) || t.status === "resolved";
    const status = isResolved
      ? "resolved"
      : discovered.length >= minimum
      ? "ready_to_deduce"
      : (discovered.length > 0 || partial.length > 0) ? "active" : (t.status || "hidden");
    return { ...t, required_clues: required, required_details: requiredDetails, discovered_clues: discovered, partial_clues: partial, minimum_clues_to_deduce: minimum, status };
  });
}

function deriveTacticalNodes(adventure, mapState) {
  const byId = new Map();
  const makeFallbackTactical = (node, role = "hot_zone") => ({
    enabled: true,
    role: node?.is_final ? "finale" : role,
    layout: /corridoio|galleria|passaggio|tunnel/i.test(`${node?.name || ""} ${node?.description || ""}`) ? "narrow" : "room",
    cols: node?.is_final ? 12 : 10,
    rows: node?.is_final ? 8 : 7,
    features: ["coperture coerenti con la zona", "ingressi e uscite leggibili"],
    hazards: [],
    trigger: "quando la scena porta a uno scontro diretto in questa zona",
  });
  const addNode = (raw, source = "map") => {
    if (!raw) return;
    const tactical = raw.tactical_map || {};
    const isHot = tactical.enabled || raw.contains_enemy || raw.has_combat_potential || raw.is_final || raw.is_objective;
    if (!isHot) return;
    const id = raw.id || raw.location_id || raw.name;
    if (!id) return;
    byId.set(id, {
      ...raw,
      id,
      name: raw.name || raw.location_name || "Zona tattica",
      description: raw.description || raw.location_description || "",
      kind: raw.kind || raw.type || raw.environment_type || "",
      is_final: !!(raw.is_final || raw.is_objective || tactical.role === "finale" || raw.role === "finale"),
      tactical_map: tactical.enabled ? tactical : makeFallbackTactical(raw, raw.role || "hot_zone"),
      _source: source,
    });
  };
  Object.values(mapState?.nodes || {}).forEach(node => addNode(node, "map"));
  (adventure?.locations || []).forEach(loc => addNode(loc, "adventure"));
  (adventure?.adventure_canon?.tactical_locations || []).forEach((loc, i) => {
    const existing = (adventure?.locations || []).find(l =>
      l?.id === loc?.id || l?.name === loc?.name || l?.name === loc?.location_name
    );
    addNode({
      ...(existing || {}),
      ...loc,
      id: loc?.id || existing?.id || `tactical_${i + 1}`,
      name: loc?.name || loc?.location_name || existing?.name,
      is_final: loc?.role === "finale" || existing?.is_final,
      has_combat_potential: true,
      tactical_map: existing?.tactical_map || {
        enabled: true,
        role: loc?.role || "hot_zone",
        trigger: loc?.trigger || "confronto diretto",
        layout: loc?.layout || "room",
      },
    }, "canon");
  });
  return Array.from(byId.values())
    .sort((a, b) => Number(!!b.is_final) - Number(!!a.is_final) || String(a.name).localeCompare(String(b.name)));
}

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

function textValue(...values) {
  return values.find(v => typeof v === "string" && v.trim())?.trim() || "";
}

function safeFilePart(value, fallback = "avventura") {
  return String(value || fallback)
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9àèéìòù_-]+/gi, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80) || fallback;
}

function downloadJsonFile(payload, filename) {
  const json = JSON.stringify(payload, null, 2);
  const blob = new Blob([json], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.endsWith(".json") ? filename : `${filename}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function buildAdventureExport({ adventure, gameState, mapState, preparedTacticalMaps, source = "app" }) {
  const definition = adventure?.adventure_definition || null;
  const runtimeState = adventure?.runtime_state || adventure?.adventure_runtime_state || null;
  return {
    export_version: 1,
    exported_at: new Date().toISOString(),
    source,
    title: definition?.title || adventure?.title || "Avventura",
    adventure_definition: definition,
    runtime_state: runtimeState,
    validation_report: adventure?.validation_report || null,
    legacy_adventure: definition?.legacy_adventure || adventure || null,
    live_game_state: gameState || null,
    strategic_map_state: mapState || null,
    prepared_tactical_maps: preparedTacticalMaps || null,
  };
}

function clueTitle(clue) {
  return clue?.label || clue?.text || clue?.id || "Indizio";
}

function isKnownNpc(npc) {
  const agendaStatus = npc?.npc_agenda?.arc_status || npc?.arc_status;
  if (npc?._source === "world") return true;
  if (npc?.introduced || npc?.known || npc?.visible || npc?.discovered) return true;
  if (agendaStatus && !["hidden", "unintroduced"].includes(String(agendaStatus))) return true;
  return false;
}

function isKnownTacticalNode(node, mapState) {
  const mapNode = mapState?.nodes?.[node?.id];
  if (mapState?.current_node_id && node?.id === mapState.current_node_id) return true;
  if (mapNode?.visited || mapNode?.discovered || mapNode?.known || mapNode?.visible) return true;
  if (node?.visited || node?.discovered || node?.known || node?.visible) return true;
  return false;
}

// ─── Location Graph (mappa strategica) ────────────────────────────────────────

function LocationGraph({ mapState, isGM, onMove, players, avatars, npcStatuses, advNpcs, backdropImage, mapPositions }) {
  const [hoveredId, setHoveredId] = useState(null);

  if (!mapState || !mapState.nodes || Object.keys(mapState.nodes).length === 0) {
    return (
      <div style={{ fontSize: 12, color: "var(--text)", opacity: 0.5, textAlign: "center", marginTop: 40 }}>
        Nessuna mappa disponibile.<br />
        <span style={{ fontSize: 11, opacity: 0.7 }}>La mappa viene generata all'avvio dell'avventura.</span>
      </div>
    );
  }

  const nodes = mapState.nodes;
  const edges = Object.values(mapState.connections_meta || {});
  const currentId = mapState.current_node_id;
  const allNodes = Object.values(nodes);

  const visitedSet = new Set(allNodes.filter(n => n.visited).map(n => n.id));
  visitedSet.add(currentId);
  const adjacentSet = new Set();
  edges.forEach(e => {
    if (visitedSet.has(e.from_id)) adjacentSet.add(e.to_id);
    if (visitedSet.has(e.to_id)) adjacentSet.add(e.from_id);
  });
  const visibleSet = new Set([...visitedSet, ...adjacentSet]);

  function nodeStatus(id) {
    if (id === currentId) return "current";
    if (visitedSet.has(id)) return "visited";
    if (adjacentSet.has(id)) return "adjacent";
    return "unknown";
  }

  const NODE_W = 96;
  const NODE_H = 76;
  const PAD = 20;

  // Choose layout mode: geographic (backdrop + positions) or grid fallback
  const hasGeoPositions = backdropImage && mapPositions && Object.keys(mapPositions).length > 0;

  let svgW, svgH, pos;

  if (hasGeoPositions) {
    // Fixed canvas that matches the backdrop image aspect ratio (≈ 1:1 from generation)
    svgW = 800;
    svgH = 800;
    pos = {};
    const usableW = svgW - NODE_W - PAD * 2;
    const usableH = svgH - NODE_H - PAD * 2;
    allNodes.forEach(n => {
      const mp = mapPositions[n.name] || mapPositions[n.id];
      if (mp) {
        pos[n.id] = {
          x: PAD + (mp.x / 100) * usableW,
          y: PAD + (mp.y / 100) * usableH,
        };
      } else {
        // Fallback: place unmapped nodes in a row at the bottom
        const idx = allNodes.filter(x => !mapPositions[x.name] && !mapPositions[x.id]).indexOf(n);
        pos[n.id] = { x: PAD + idx * (NODE_W + 10), y: svgH - NODE_H - PAD };
      }
    });
  } else {
    // Grid layout based on grid_x / grid_y
    const COL_GAP = 32;
    const ROW_GAP = 16;
    const maxCol = Math.max(...allNodes.map(n => n.grid_x || 0), 0);
    const cols = {};
    allNodes.forEach(n => { const c = n.grid_x || 0; (cols[c] = cols[c] || []).push(n); });
    Object.values(cols).forEach(arr => arr.sort((a, b) => (a.grid_y || 0) - (b.grid_y || 0)));
    let maxColH = 0;
    for (let c = 0; c <= maxCol; c++) {
      const col = cols[c] || [];
      maxColH = Math.max(maxColH, col.length * NODE_H + Math.max(0, col.length - 1) * ROW_GAP);
    }
    pos = {};
    for (let c = 0; c <= maxCol; c++) {
      const col = cols[c] || [];
      const colH = col.length * NODE_H + Math.max(0, col.length - 1) * ROW_GAP;
      const startY = PAD + (maxColH - colH) / 2;
      col.forEach((n, i) => { pos[n.id] = { x: PAD + c * (NODE_W + COL_GAP), y: startY + i * (NODE_H + ROW_GAP) }; });
    }
    svgW = PAD * 2 + (Math.max(...allNodes.map(n => n.grid_x || 0), 0) + 1) * NODE_W + Math.max(...allNodes.map(n => n.grid_x || 0), 0) * COL_GAP;
    svgH = PAD * 2 + maxColH;
  }

  function edgePath(a, b) {
    const pa = pos[a.id], pb = pos[b.id];
    if (!pa || !pb) return "";
    const ax = pa.x + NODE_W / 2, ay = pa.y + NODE_H / 2;
    const bx = pb.x + NODE_W / 2, by = pb.y + NODE_H / 2;
    return `M${ax},${ay} C${ax + (bx-ax)*0.5},${ay} ${ax + (bx-ax)*0.5},${by} ${bx},${by}`;
  }

  const canMove = (id) => onMove && id !== currentId && (isGM ? true : adjacentSet.has(id));

  // Character tokens per node
  const PLAYER_COLORS = ["#a78bfa", "#60a5fa", "#34d399", "#f59e0b", "#f87171", "#c084fc", "#fb7185", "#38bdf8"];
  const playerList = players || [];
  // All players are at current node (party moves together)
  const tokensPerNode = {};
  if (currentId) {
    tokensPerNode[currentId] = playerList.map((p, i) => ({
      label: (p.name || "?")[0].toUpperCase(),
      color: PLAYER_COLORS[i % PLAYER_COLORS.length],
      avatar: avatars?.[p.id] || null,
    }));
  }
  // GM mode: add NPCs by location
  if (isGM && advNpcs && npcStatuses) {
    advNpcs.forEach(npc => {
      const st = npcStatuses[npc.id] || npcStatuses[npc.name] || {};
      const locId = st.location_id || st.current_node_id || npc.location_id || npc.node_id;
      if (locId && nodes[locId]) {
        if (!tokensPerNode[locId]) tokensPerNode[locId] = [];
        tokensPerNode[locId].push({ label: (npc.name || "?")[0].toUpperCase(), color: "#94a3b8", avatar: null, isNpc: true });
      }
    });
  }

  // FOW reveal data (player mode)
  const revealNodes = !isGM ? allNodes.filter(n => visitedSet.has(n.id) && pos[n.id]) : [];
  const partialRevealNodes = !isGM ? allNodes.filter(n => adjacentSet.has(n.id) && !visitedSet.has(n.id) && pos[n.id]) : [];

  return (
    <div style={{ width: "100%", height: "100%" }}>
      <svg
        viewBox={`0 0 ${svgW} ${svgH}`}
        width="100%" height="100%"
        preserveAspectRatio="xMidYMid meet"
        style={{ display: "block", borderRadius: 10 }}
      >
        <defs>
          <marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0 L0,6 L6,3 z" fill="rgba(167,139,250,0.8)" />
          </marker>
          <filter id="glow">
            <feGaussianBlur stdDeviation="4" result="coloredBlur" />
            <feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <radialGradient id="mapBg" cx="50%" cy="50%" r="70%">
            <stop offset="0%" stopColor="#1c1635" />
            <stop offset="100%" stopColor="#0f0a28" />
          </radialGradient>
          <radialGradient id="vignette" cx="50%" cy="50%" r="60%">
            <stop offset="50%" stopColor="rgba(0,0,0,0)" />
            <stop offset="100%" stopColor="rgba(0,0,0,0.6)" />
          </radialGradient>
          {/* FOW reveal gradients */}
          {revealNodes.map(n => {
            const p = pos[n.id], cx = p.x + NODE_W/2, cy = p.y + NODE_H/2;
            return <radialGradient key={`fg-${n.id}`} id={`fog-reveal-${n.id}`} gradientUnits="userSpaceOnUse" cx={cx} cy={cy} r={120}>
              <stop offset="0%" stopColor="black" /><stop offset="55%" stopColor="black" /><stop offset="100%" stopColor="white" />
            </radialGradient>;
          })}
          {partialRevealNodes.map(n => {
            const p = pos[n.id], cx = p.x + NODE_W/2, cy = p.y + NODE_H/2;
            return <radialGradient key={`fgp-${n.id}`} id={`fog-partial-${n.id}`} gradientUnits="userSpaceOnUse" cx={cx} cy={cy} r={85}>
              <stop offset="0%" stopColor="#444" /><stop offset="100%" stopColor="white" />
            </radialGradient>;
          })}
          {!isGM && (
            <mask id="fog-mask">
              <rect fill="white" width={svgW} height={svgH} />
              {revealNodes.map(n => { const p = pos[n.id]; return <ellipse key={n.id} cx={p.x+NODE_W/2} cy={p.y+NODE_H/2} rx={120} ry={100} fill={`url(#fog-reveal-${n.id})`} />; })}
              {partialRevealNodes.map(n => { const p = pos[n.id]; return <ellipse key={n.id} cx={p.x+NODE_W/2} cy={p.y+NODE_H/2} rx={85} ry={70} fill={`url(#fog-partial-${n.id})`} />; })}
            </mask>
          )}
        </defs>

        {/* Background */}
        {backdropImage ? (
          <>
            <image href={`data:image/jpeg;base64,${backdropImage}`} x={0} y={0} width={svgW} height={svgH} preserveAspectRatio="xMidYMid slice" />
            <rect x={0} y={0} width={svgW} height={svgH} fill="rgba(0,0,12,0.48)" />
          </>
        ) : (
          <rect x={0} y={0} width={svgW} height={svgH} rx={10} fill="url(#mapBg)" />
        )}
        <rect x={0} y={0} width={svgW} height={svgH} fill="url(#vignette)" />

        {/* Edges */}
        {edges.map((e, i) => {
          const a = nodes[e.from_id], b = nodes[e.to_id];
          if (!a || !b) return null;
          if (!isGM && !visibleSet.has(e.from_id) && !visibleSet.has(e.to_id)) return null;
          const known = visitedSet.has(e.from_id) && visitedSet.has(e.to_id);
          const halfKnown = visitedSet.has(e.from_id) || visitedSet.has(e.to_id);
          const edgeType = e.type || e.edge_type || "";
          const stroke = edgeType === "danger" ? "rgba(239,68,68,0.7)" : edgeType === "escalation" ? "rgba(251,191,36,0.7)" : known ? "rgba(167,139,250,0.85)" : halfKnown ? "rgba(124,58,237,0.4)" : "rgba(255,255,255,0.07)";
          return <path key={i} d={edgePath(a, b)} fill="none" stroke={stroke} strokeWidth={known ? 2.5 : 1.5}
            strokeDasharray={e.status === "locked" ? "7,4" : "none"}
            markerEnd={known ? "url(#arrow)" : "none"} opacity={halfKnown ? 1 : 0.3} />;
        })}

        {/* FOW overlay */}
        {!isGM && <rect width={svgW} height={svgH} fill="rgba(3,1,12,0.88)" mask="url(#fog-mask)" style={{ pointerEvents: "none" }} />}

        {/* Nodes */}
        {allNodes.map(n => {
          const status = isGM ? (n.id === currentId ? "current" : n.visited ? "visited" : "known") : nodeStatus(n.id);
          if (!isGM && status === "unknown") return null;
          const p = pos[n.id];
          if (!p) return null;
          const isObj = n.id === mapState.objective_node_id;
          const isCurrent = n.id === currentId;
          const moveable = canMove(n.id);
          const hovered = hoveredId === n.id;
          const isAdjacent = status === "adjacent";
          const tokens = tokensPerNode[n.id] || [];

          const borderColor = isCurrent ? "#c084fc" : isObj ? "#fbbf24" : status === "visited" ? "rgba(74,222,128,0.75)" : isAdjacent ? "rgba(96,165,250,0.5)" : "rgba(255,255,255,0.12)";
          const cardFill = isCurrent ? "rgba(124,58,237,0.55)" : status === "visited" ? "rgba(30,22,72,0.95)" : isAdjacent ? "rgba(22,18,55,0.85)" : "rgba(18,14,45,0.88)";

          // Wrap name to 2 lines
          const name = n.name || "???";
          const line1 = name.length > 14 ? name.slice(0, 13) + "…" : name;

          return (
            <g key={n.id}
              style={{ cursor: moveable ? "pointer" : "default" }}
              onMouseEnter={() => setHoveredId(n.id)}
              onMouseLeave={() => setHoveredId(null)}
              onClick={() => moveable && onMove(n.name)}
              filter={isCurrent ? "url(#glow)" : "none"}
              opacity={isAdjacent && !isGM ? 0.7 : 1}
            >
              {/* Card */}
              <rect x={p.x} y={p.y} width={NODE_W} height={NODE_H} rx={9}
                fill={cardFill}
                stroke={hovered && moveable ? "#60a5fa" : borderColor}
                strokeWidth={isCurrent ? 2.5 : isObj ? 2.5 : 1.5}
              />

              {/* Status dot + label (no rect, fits text size) */}
              <circle cx={p.x+7} cy={p.y+9} r={3.5}
                fill={isCurrent ? "#c084fc" : isObj ? "#fbbf24" : status==="visited" ? "#4ade80" : "rgba(255,255,255,0.18)"}
              />
              <text x={p.x+13} y={p.y+12} fontSize={6.5} fontWeight="800"
                fill={isCurrent ? "#e9d5ff" : isObj ? "#fbbf24" : status==="visited" ? "#4ade80" : "rgba(255,255,255,0.35)"}>
                {isCurrent ? "QUI" : isObj ? "OBJ" : status==="visited" ? "VIS" : isAdjacent ? "?" : "~"}
              </text>

              {/* Move hint top-right */}
              {moveable && <text x={p.x+NODE_W-5} y={p.y+12} fontSize={9} textAnchor="end" fill="#60a5fa" opacity={hovered?1:0.35}>→</text>}

              {/* Location name — centered */}
              <text x={p.x+NODE_W/2} y={p.y+34} textAnchor="middle" fontSize={9} fontWeight="900"
                fill={isCurrent ? "#e9d5ff" : status==="visited" ? "#f1f5f9" : "rgba(255,255,255,0.8)"}
                style={{ fontFamily: "system-ui, sans-serif" }}>
                {line1}
              </text>

              {/* Content icons */}
              <text x={p.x+NODE_W/2} y={p.y+47} textAnchor="middle" fontSize={8}>
                {n.contains_enemy ? "⚔" : ""}{n.contains_clue ? "🔍" : ""}{n.contains_loot ? "💰" : ""}
              </text>

              {/* Character tokens — centered horizontally */}
              {tokens.length > 0 && (() => {
                const visible = tokens.slice(0, 5);
                const spacing = 16;
                const totalW = visible.length * spacing - (spacing - 14);
                const startX = p.x + NODE_W / 2 - totalW / 2 + 7;
                const ty = p.y + NODE_H - 12;
                return visible.map((tok, ti) => {
                  const tx = startX + ti * spacing;
                  return (
                    <g key={ti}>
                      <circle cx={tx} cy={ty} r={7}
                        fill={tok.color} opacity={0.95}
                        stroke="rgba(0,0,0,0.6)" strokeWidth={1.2}
                      />
                      <text x={tx} y={ty+3} textAnchor="middle" fontSize={6.5} fontWeight="900" fill="#fff">{tok.label}</text>
                    </g>
                  );
                });
              })()}

              {/* Hover tooltip */}
              {hovered && moveable && (
                <>
                  <rect x={p.x} y={p.y+NODE_H+3} width={NODE_W} height={15} rx={4} fill="rgba(96,165,250,0.9)" />
                  <text x={p.x+NODE_W/2} y={p.y+NODE_H+13} textAnchor="middle" fontSize={8} fontWeight="700" fill="#000">Spostati qui</text>
                </>
              )}
            </g>
          );
        })}

        {/* Compass rose */}
        {backdropImage && (
          <g transform={`translate(${svgW-34}, 30)`} opacity={0.6}>
            <circle cx={0} cy={0} r={14} fill="rgba(0,0,0,0.55)" stroke="rgba(167,139,250,0.5)" strokeWidth={1} />
            <text x={0} y={-5} textAnchor="middle" fontSize={7} fill="#c084fc" fontWeight="700">N</text>
            <line x1={0} y1={-10} x2={0} y2={10} stroke="rgba(167,139,250,0.7)" strokeWidth={1.5} />
            <line x1={-10} y1={0} x2={10} y2={0} stroke="rgba(167,139,250,0.5)" strokeWidth={1} />
          </g>
        )}
      </svg>

      {/* Legend */}
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", padding: "6px 4px 2px", fontSize: 10, color: "var(--text)", opacity: 0.6 }}>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}><span style={{ width: 10, height: 10, borderRadius: 3, background: "#7c3aed", display: "inline-block" }} />Posizione attuale</span>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}><span style={{ width: 10, height: 10, borderRadius: 3, background: "rgba(74,222,128,0.4)", display: "inline-block" }} />Visitata</span>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}><span style={{ width: 10, height: 10, borderRadius: 3, background: "rgba(96,165,250,0.3)", display: "inline-block" }} />Raggiungibile</span>
        {!isGM && <span style={{ display: "flex", alignItems: "center", gap: 4 }}><span style={{ width: 10, height: 10, borderRadius: 3, background: "rgba(18,14,45,0.9)", border: "1px solid rgba(255,255,255,0.12)", display: "inline-block" }} />Nebbia</span>}
        {onMove && <span style={{ color: "#60a5fa" }}>→ Clicca per spostarti</span>}
      </div>
    </div>
  );
}


function ClockToastOverlay({ toasts, onDismiss }) {
  useEffect(() => {
    if (toasts.length === 0) return;
    const timer = setTimeout(() => onDismiss(toasts[0].id), 6000);
    return () => clearTimeout(timer);
  }, [toasts, onDismiss]);

  if (toasts.length === 0) return null;
  const toast = toasts[0];
  const isCompleted = toast.completed;
  const isFatal = toast.clock_type === "terminal_defeat";
  const isVictory = toast.clock_type === "terminal_victory";

  const borderColor = isCompleted
    ? (isFatal ? "#ef4444" : isVictory ? "#eab308" : "#f97316")
    : "#f59e0b";
  const bgColor = isCompleted
    ? (isFatal ? "rgba(239,68,68,0.18)" : isVictory ? "rgba(234,179,8,0.15)" : "rgba(249,115,22,0.15)")
    : "rgba(245,158,11,0.13)";
  const icon = isCompleted ? (isFatal ? "💀" : isVictory ? "👑" : "⚠️") : "⏱";
  const title = isCompleted ? "CLOCK COMPLETATO" : "CLOCK AVANZATO";

  return (
    <div style={{
      position: "fixed", top: 80, right: 16, zIndex: 9999,
      maxWidth: 320, minWidth: 240,
      background: bgColor,
      border: `1.5px solid ${borderColor}`,
      borderRadius: 12, padding: "12px 14px",
      boxShadow: `0 4px 24px rgba(0,0,0,0.5), 0 0 0 1px ${borderColor}22`,
      animation: "fadeInRight 0.25s ease",
      cursor: "pointer",
    }} onClick={() => onDismiss(toast.id)}>
      <style>{`@keyframes fadeInRight { from { opacity:0; transform:translateX(30px); } to { opacity:1; transform:translateX(0); } }`}</style>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
        <span style={{ fontSize: 16 }}>{icon}</span>
        <span style={{ fontSize: 11, fontWeight: 700, color: borderColor, letterSpacing: "0.06em" }}>{title}</span>
        <span style={{ marginLeft: "auto", fontSize: 10, opacity: 0.5 }}>✕</span>
      </div>
      <div style={{ fontSize: 13, fontWeight: 700, color: "#f8fafc", marginBottom: 4 }}>
        {toast.label}
      </div>
      <div style={{ display: "flex", gap: 2, marginBottom: 6 }}>
        {Array.from({ length: toast.max_value }, (_, i) => (
          <div key={i} style={{
            flex: 1, height: 5, borderRadius: 2,
            background: i < toast.new_value ? borderColor : "rgba(255,255,255,0.1)",
            transition: "background 0.4s",
          }} />
        ))}
      </div>
      <div style={{ fontSize: 11, color: "rgba(248,250,252,0.65)" }}>
        {toast.old_value} → {toast.new_value} / {toast.max_value}
        {isCompleted && toast.consequence && (
          <div style={{ marginTop: 4, color: borderColor, fontWeight: 600 }}>{toast.consequence}</div>
        )}
        {!isCompleted && toast.steps_crossed?.map((s, i) => (
          <div key={i} style={{ marginTop: 3, opacity: 0.85 }}>
            → {s.effect || s.world_state_change || s.label || ""}
          </div>
        ))}
      </div>
    </div>
  );
}

function NpcEventToastOverlay({ toasts, onDismiss }) {
  useEffect(() => {
    if (toasts.length === 0) return;
    const timer = setTimeout(() => onDismiss(toasts[0].id), 7000);
    return () => clearTimeout(timer);
  }, [toasts, onDismiss]);

  if (toasts.length === 0) return null;
  const toast = toasts[0];

  const actionIcon = {
    destroy_clue: "🔥",
    eliminate_npc: "💀",
    scare_npc: "😱",
    move_clue: "📦",
    create_clue: "🔍",
  }[toast.action] || "⚡";

  const actionLabel = {
    destroy_clue: "INDIZIO DISTRUTTO",
    eliminate_npc: "NPC ELIMINATO",
    scare_npc: "TESTIMONE INTIMIDITO",
    move_clue: "INDIZIO SPOSTATO",
    create_clue: "NUOVO INDIZIO",
  }[toast.action] || "EVENTO NPC";

  const borderColor = toast.action === "eliminate_npc" ? "#ef4444"
    : toast.action === "destroy_clue" ? "#f97316"
    : toast.action === "scare_npc" ? "#a855f7"
    : "#06b6d4";

  const bgColor = toast.action === "eliminate_npc" ? "rgba(239,68,68,0.15)"
    : toast.action === "destroy_clue" ? "rgba(249,115,22,0.15)"
    : toast.action === "scare_npc" ? "rgba(168,85,247,0.15)"
    : "rgba(6,182,212,0.13)";

  return (
    <div style={{
      position: "fixed", top: 80, left: 16, zIndex: 9998,
      maxWidth: 320, minWidth: 240,
      background: bgColor,
      border: `1.5px solid ${borderColor}`,
      borderRadius: 12, padding: "12px 14px",
      boxShadow: `0 4px 24px rgba(0,0,0,0.5), 0 0 0 1px ${borderColor}22`,
      animation: "fadeInLeft 0.25s ease",
      cursor: "pointer",
    }} onClick={() => onDismiss(toast.id)}>
      <style>{`@keyframes fadeInLeft { from { opacity:0; transform:translateX(-30px); } to { opacity:1; transform:translateX(0); } }`}</style>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
        <span style={{ fontSize: 16 }}>{actionIcon}</span>
        <span style={{ fontSize: 11, fontWeight: 700, color: borderColor, letterSpacing: "0.06em" }}>{actionLabel}</span>
        <span style={{ marginLeft: "auto", fontSize: 10, opacity: 0.5 }}>✕</span>
      </div>
      <div style={{ fontSize: 13, fontWeight: 700, color: "#f8fafc", marginBottom: 4 }}>
        {toast.actor_name}
      </div>
      {toast.narration && (
        <div style={{ fontSize: 11, color: "rgba(248,250,252,0.75)", fontStyle: "italic", lineHeight: 1.4 }}>
          {toast.narration}
        </div>
      )}
    </div>
  );
}

function ClockUrgencyBanner({ clocks }) {
  if (!clocks || clocks.length === 0) return null;
  const urgent = clocks.filter(c => c.discovered && c.active !== false && !c.resolved && c.max_value > 0 && (c.value / c.max_value) >= 0.5);
  if (urgent.length === 0) return null;
  const top = urgent.sort((a, b) => (b.value / b.max_value) - (a.value / a.max_value))[0];
  const pct = top.value / top.max_value;
  const isCritical = pct >= 0.85;
  const remaining = top.max_value - top.value;
  const bg = isCritical ? "rgba(239,68,68,0.12)" : "rgba(245,158,11,0.10)";
  const border = isCritical ? "rgba(239,68,68,0.45)" : "rgba(245,158,11,0.4)";
  const color = isCritical ? "#ef4444" : "#f59e0b";
  const icon = isCritical ? "🔴" : "🟡";
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 8,
      background: bg, border: `1px solid ${border}`, borderRadius: 8,
      padding: "6px 12px", margin: "0 0 6px 0", fontSize: 12,
    }}>
      <span style={{ fontSize: 14 }}>{icon}</span>
      <span style={{ flex: 1, color, fontWeight: 600 }}>
        {top.label}
        {top.clock_type === "terminal_defeat" && <span style={{ marginLeft: 6, fontSize: 10, background: "rgba(239,68,68,0.2)", color: "#ef4444", padding: "1px 5px", borderRadius: 3 }}>FATALE</span>}
      </span>
      <div style={{ display: "flex", gap: 2 }}>
        {Array.from({ length: top.max_value }).map((_, i) => (
          <div key={i} style={{
            width: 8, height: 8, borderRadius: 2,
            background: i < top.value ? color : "rgba(255,255,255,0.12)",
          }} />
        ))}
      </div>
      <span style={{ color, fontWeight: 700, fontSize: 11, minWidth: 28, textAlign: "right" }}>
        {remaining} rimasti
      </span>
    </div>
  );
}

function ClocksPanel({ clocks, isGM }) {
  if (!clocks || clocks.length === 0) return null;

  const visible = isGM ? clocks : clocks.filter(c => c.discovered && c.active !== false);
  if (visible.length === 0) {
    if (!isGM) return (
      <div style={{ fontSize: 12, color: "var(--text)", opacity: 0.45, fontStyle: "italic", padding: "10px 0" }}>
        Nessun conto alla rovescia scoperto.
      </div>
    );
    return null;
  }

  const typeIcon = (ctype) => {
    if (ctype === "terminal_defeat") return "💀";
    if (ctype === "terminal_victory") return "👑";
    if (ctype === "escalation") return "⚠️";
    return null;
  };
  const typeLabel = (ctype) => {
    if (ctype === "terminal_defeat") return "FATALE";
    if (ctype === "terminal_victory") return "OBIETTIVO";
    if (ctype === "escalation") return "ESCALATION";
    return null;
  };
  const typeBadgeColor = (ctype) => {
    if (ctype === "terminal_defeat") return { bg: "rgba(239,68,68,0.25)", color: "#ef4444" };
    if (ctype === "terminal_victory") return { bg: "rgba(234,179,8,0.2)", color: "#eab308" };
    if (ctype === "escalation") return { bg: "rgba(249,115,22,0.2)", color: "#f97316" };
    return null;
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, padding: "4px 0" }}>
      {visible.map(clock => {
        const ctype = clock.clock_type || "narrative";
        const isResolved = !!clock.resolved;
        const pct = clock.max_value > 0 ? clock.value / clock.max_value : 0;
        const remaining = clock.max_value - clock.value;
        const urgent = !isResolved && pct >= 0.66;
        const critical = !isResolved && pct >= 0.85;
        const hidden = !clock.discovered;
        const barColor = isResolved ? "#22c55e" : (critical ? "#ef4444" : urgent ? "#f59e0b" : "#60a5fa");
        const badge = typeLabel(ctype);
        const badgeStyle = typeBadgeColor(ctype);
        const icon = isResolved ? "✅" : (hidden ? "👁" : (typeIcon(ctype) || (critical ? "🔴" : urgent ? "🟡" : "🕐")));

        return (
          <div key={clock.id} style={{
            borderRadius: 10, padding: "10px 12px",
            background: isResolved ? "rgba(34,197,94,0.06)" : (hidden ? "rgba(255,255,255,0.03)" : (critical ? "rgba(239,68,68,0.07)" : urgent ? "rgba(245,158,11,0.07)" : "rgba(96,165,250,0.07)")),
            border: `1px solid ${isResolved ? "rgba(34,197,94,0.3)" : (hidden ? "rgba(255,255,255,0.08)" : (critical ? "rgba(239,68,68,0.3)" : urgent ? "rgba(245,158,11,0.3)" : "rgba(96,165,250,0.25)"))}`,
            opacity: isResolved ? 0.7 : 1,
          }}>
            {/* Header */}
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 7 }}>
              <span style={{ fontSize: 13 }}>{icon}</span>
              <span style={{ flex: 1, fontSize: 12, fontWeight: 700, color: isResolved ? "#22c55e" : (hidden ? "rgba(255,255,255,0.4)" : "var(--text-h)") }}>
                {hidden ? `[Nascosto] ${clock.label}` : clock.label}
                {isResolved && " — RISOLTO"}
              </span>
              {badge && !hidden && badgeStyle && (
                <span style={{ fontSize: 9, padding: "1px 6px", borderRadius: 4, fontWeight: 700, background: badgeStyle.bg, color: badgeStyle.color }}>
                  {badge}
                </span>
              )}
              {!hidden && !isResolved && (
                <span style={{ fontSize: 11, fontWeight: 700, color: barColor }}>
                  {remaining} {remaining === 1 ? "seg." : "seg."}
                </span>
              )}
              {isGM && hidden && (
                <span style={{ fontSize: 9, padding: "1px 6px", borderRadius: 4, background: "rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.4)" }}>
                  GM only
                </span>
              )}
            </div>

            {/* Barra segmenti */}
            {!isResolved && (
              <div style={{ display: "flex", gap: 3, marginBottom: hidden ? 0 : 6 }}>
                {Array.from({ length: clock.max_value }, (_, i) => (
                  <div key={i} style={{
                    flex: 1, height: 8, borderRadius: 3,
                    background: i < clock.value
                      ? (hidden ? "rgba(255,255,255,0.15)" : barColor)
                      : "rgba(255,255,255,0.08)",
                    transition: "background 0.3s",
                  }} />
                ))}
              </div>
            )}

            {/* Conseguenza e condizione */}
            {(clock.discovered || isGM) && clock.consequence && !isResolved && (
              <div style={{ fontSize: 11, color: hidden ? "rgba(255,255,255,0.3)" : "rgba(255,255,255,0.55)", lineHeight: 1.4, fontStyle: "italic" }}>
                {hidden ? `⚠ ${clock.consequence}` : `Se si completa: ${clock.consequence}`}
              </div>
            )}
            {(clock.discovered || isGM) && clock.resolution_condition && !isResolved && (
              <div style={{ fontSize: 10, color: "rgba(34,197,94,0.7)", lineHeight: 1.4, marginTop: 3 }}>
                🛡 {clock.resolution_condition}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function FloatingMapPanel({ mapState, onMove, isGM, backdropImage, mapPositions, players, avatars, npcStatuses, advNpcs, onClose }) {
  const [pos, setPos] = useState({ x: Math.max(10, window.innerWidth - 640), y: 60 });
  const [size, setSize] = useState({ w: 620, h: 480 });
  const dragging = useRef(false);
  const dragOff = useRef({ dx: 0, dy: 0 });
  const resizing = useRef(false);
  const resizeStart = useRef({});

  function onTitleMouseDown(e) {
    dragging.current = true;
    dragOff.current = { dx: e.clientX - pos.x, dy: e.clientY - pos.y };
    e.preventDefault();
  }
  function onResizeMouseDown(e) {
    resizing.current = true;
    resizeStart.current = { mx: e.clientX, my: e.clientY, w: size.w, h: size.h };
    e.preventDefault();
    e.stopPropagation();
  }

  useEffect(() => {
    function onMouseMove(e) {
      if (dragging.current) {
        setPos({ x: e.clientX - dragOff.current.dx, y: e.clientY - dragOff.current.dy });
      }
      if (resizing.current) {
        const dw = e.clientX - resizeStart.current.mx;
        const dh = e.clientY - resizeStart.current.my;
        setSize({
          w: Math.max(320, resizeStart.current.w + dw),
          h: Math.max(240, resizeStart.current.h + dh),
        });
      }
    }
    function onMouseUp() { dragging.current = false; resizing.current = false; }
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => { window.removeEventListener("mousemove", onMouseMove); window.removeEventListener("mouseup", onMouseUp); };
  }, []);

  return (
    <div style={{
      position: "fixed", left: pos.x, top: pos.y, width: size.w, zIndex: 1200,
      background: "var(--bg, #0f0f1a)", border: "1px solid var(--border, rgba(255,255,255,0.12))",
      borderRadius: 12, boxShadow: "0 8px 40px rgba(0,0,0,0.7)", display: "flex", flexDirection: "column",
      userSelect: dragging.current ? "none" : "auto",
    }}>
      {/* Title bar — drag handle */}
      <div onMouseDown={onTitleMouseDown} style={{
        display: "flex", alignItems: "center", gap: 8, padding: "8px 12px",
        borderBottom: "1px solid var(--border, rgba(255,255,255,0.1))",
        cursor: "grab", borderRadius: "12px 12px 0 0",
        background: "rgba(124,58,237,0.12)",
        flexShrink: 0,
      }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: "var(--accent, #a78bfa)", flex: 1 }}>🗺 Mappa Avventura</span>
        <span style={{ fontSize: 10, color: "var(--text)", opacity: 0.4, marginRight: 4 }}>⠿ trascina</span>
        <button onClick={onClose} style={{
          background: "none", border: "none", color: "var(--text)", cursor: "pointer",
          fontSize: 16, lineHeight: 1, padding: "0 2px", opacity: 0.6,
        }}>✕</button>
      </div>
      {/* Map content — no scroll, SVG scales to fit */}
      <div style={{ flex: 1, padding: "6px 8px 4px", minHeight: 200, height: size.h - 48, display: "flex", flexDirection: "column" }}>
        <LocationGraph mapState={mapState} isGM={isGM} onMove={onMove} backdropImage={backdropImage} mapPositions={mapPositions} players={players} avatars={avatars} npcStatuses={npcStatuses} advNpcs={advNpcs} />
      </div>
      {/* Resize handle */}
      <div onMouseDown={onResizeMouseDown} style={{
        position: "absolute", right: 0, bottom: 0, width: 18, height: 18,
        cursor: "se-resize", display: "flex", alignItems: "flex-end", justifyContent: "flex-end",
        padding: "2px 3px", opacity: 0.4,
      }}>
        <svg width={10} height={10} viewBox="0 0 10 10">
          <path d="M9,1 L1,9 M9,5 L5,9 M9,9 L9,9" stroke="currentColor" strokeWidth={1.5} />
        </svg>
      </div>
    </div>
  );
}

// mode: "players" = pannello giocatori (sinistra), "gm" = pannello GM (destra)
function SidePanel({ adventure, gameState, mapState, clocksData, gmEventLog, backdropImage, mapPositions, onMove, onOpenMap, preparedTacticalMaps, preparingTacticalMaps, onPrepareTacticalMap, players, avatars, npcAvatars, npcStatuses, advNpcs, onClose, defaultTab, mode, onDeduce }) {
  const isGmMode = mode === "gm";
  const [tab, setTab] = useState(defaultTab || (isGmMode ? "gm_overview" : "clues"));
  // Se arriva un nuovo defaultTab (es. click su quick-access), aggiorna la tab
  const prevDefaultTab = useRef(defaultTab);
  useEffect(() => {
    if (defaultTab && defaultTab !== prevDefaultTab.current) {
      prevDefaultTab.current = defaultTab;
      setTab(defaultTab);
    }
  }, [defaultTab]);
  const [expandedNpc, setExpandedNpc] = useState(null);
  const _def = adventure?.adventure_definition || adventure || {};
  const clues = _def.clues || [];
  const clueProgress = gameState?.clue_progress || {};
  const storyThreads = deriveStoryThreads(adventure, gameState?.clues_found || [], clueProgress, gameState?.resolved_threads || []);
  const readyThreads = storyThreads.filter(t => t.status === "ready_to_deduce");
  const resolvedThreads = storyThreads.filter(t => t.status === "resolved");
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
  const threads = storyThreads.length > 0 ? storyThreads : (gameState?.open_threads || []);
  const threatLevel = gameState?.threat_level || 0;
  const threatMax = adventure?.threat_max_turns || 8;
  const threatPct = Math.round(threatLevel / Math.max(threatMax, 1) * 100);
  const tacticalNodes = deriveTacticalNodes(adventure, mapState);
  const canon = adventure?.adventure_canon || {};
  const finaleConditions = canon?.finale_conditions || _def.finale_conditions || adventure?.finale_conditions || [];
  const _finaleLabel = finaleConditions.length > 0
    ? finaleConditions.map(f => f.label || f.id).filter(Boolean).join(" oppure ")
    : null;
  const primaryObjective = textValue(
    adventure?.win_condition,
    _def.win_condition,
    adventure?.objective,
    gameState?.mission?.objective,
    canon?.objective,
    _finaleLabel,
    "Completare l'avventura."
  );
  const hiddenTruth = textValue(adventure?.hidden_truth, canon?.core_truth);
  const runtimeQuality = adventure?.validation_report?.quality || {};
  const sourceMode = adventure?.source_mode || adventure?.adventure_definition?.source_mode || "";
  const archetypeProfile = adventure?.archetype_profile || adventure?.adventure_definition?.archetype_profile || {};
  const preservationPolicy = adventure?.preservation_policy || adventure?.adventure_definition?.preservation_policy || {};
  const preservedElements = adventure?.preserved_elements || adventure?.adventure_definition?.preserved_elements || [];
  const inferredElements = adventure?.inferred_elements || adventure?.adventure_definition?.inferred_elements || [];
  const validationWarnings = adventure?.validation_report?.warnings || [];
  const clueFoundSet = new Set(gameState?.clues_found || []);
  const knownClues = clues.filter(c => clueFoundSet.has(c.id) || (clueProgress?.[c.id]?.ticks || 0) > 0);
  const activeThreads = threads.filter(t => typeof t === "string" || ["active", "ready_to_deduce", "resolved"].includes(t.status));
  const knownNpcs = npcs.filter(isKnownNpc);
  const knownTacticalNodes = tacticalNodes.filter(node => isKnownTacticalNode(node, mapState));
  const keyLocations = canon?.key_locations || adventure?.locations?.map(l => l.name).filter(Boolean) || [];

  const tabStyle = (t) => ({
    flex: 1, padding: "8px 4px", border: "none", cursor: "pointer", fontSize: 12, fontWeight: 700,
    borderBottom: tab === t ? "2px solid var(--accent)" : "2px solid transparent",
    background: "none", color: tab === t ? "var(--accent)" : "var(--text)",
  });

  const threatColor = threatPct < 40 ? "#4ade80" : threatPct < 70 ? "#facc15" : "#f87171";
  const [liveDoctor, setLiveDoctor] = useState(null);   // {score, findings, ...}
  const [liveDoctorLoading, setLiveDoctorLoading] = useState(false);

  const handleDownloadCurrentAdventureJson = () => {
    const payload = buildAdventureExport({
      adventure,
      gameState,
      mapState,
      preparedTacticalMaps,
      source: "live_game",
    });
    downloadJsonFile(payload, `${safeFilePart(payload.title)}-live.json`);
  };

  const handleLiveDoctor = async () => {
    const def = adventure?.adventure_definition || adventure;
    if (!def || liveDoctorLoading) return;
    setLiveDoctorLoading(true);
    setLiveDoctor(null);
    try {
      const dr = await fetch(`${API_URL}/game/adventure/doctor`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ adventure_definition: def, enrich: false }),
      }).then(r => r.json());
      if (!dr.error) setLiveDoctor(dr);
    } catch (_) {}
    setLiveDoctorLoading(false);
  };

  return (
    <div style={{
      width: "100%", height: "100%",
      borderLeft: isGmMode ? "1px solid var(--border)" : "none",
      borderRight: isGmMode ? "none" : "1px solid var(--border)",
      display: "flex", flexDirection: "column", background: "var(--bg)",
      overflow: "hidden",
    }}>
      <div style={{ padding: "10px 14px 8px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 6, flexShrink: 0 }}>
        <div style={{ fontSize: 12, fontWeight: 800, color: isGmMode ? "#fbbf24" : "#93c5fd", letterSpacing: 0.4 }}>
          {isGmMode ? "📖 Bibbia GM" : "📓 Diario del gruppo"}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
          {isGmMode && (
            <>
              <button onClick={handleDownloadCurrentAdventureJson} title="Scarica JSON avventura corrente"
                style={{ padding: "3px 7px", borderRadius: 6, border: "1px solid rgba(74,222,128,0.42)", background: "rgba(74,222,128,0.10)", color: "#bbf7d0", cursor: "pointer", fontSize: 10, fontWeight: 800 }}>
                JSON
              </button>
              <button
                onClick={handleLiveDoctor}
                disabled={liveDoctorLoading}
                title="Analizza qualità JSON con il Doctor"
                style={{ padding: "3px 7px", borderRadius: 6, border: "1px solid rgba(245,158,11,0.42)", background: "rgba(245,158,11,0.10)", color: liveDoctorLoading ? "#78716c" : "#fbbf24", cursor: liveDoctorLoading ? "default" : "pointer", fontSize: 10, fontWeight: 800 }}>
                {liveDoctorLoading ? "⏳" : "🩺"}
              </button>
            </>
          )}
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text)", fontSize: 18, flexShrink: 0, lineHeight: 1 }}>×</button>
        </div>
      </div>

      {/* Doctor report inline nel pannello GM */}
      {isGmMode && liveDoctor && (() => {
        const sc = liveDoctor.score ?? 0;
        const color = sc >= 9 ? "#4ade80" : sc >= 6 ? "#facc15" : "#f87171";
        const criticals = (liveDoctor.findings || []).filter(f => f.severity === "critical");
        const warnings = (liveDoctor.findings || []).filter(f => f.severity === "warning");
        return (
          <div style={{ padding: "8px 14px", borderBottom: "1px solid var(--border)", background: "rgba(0,0,0,0.2)", flexShrink: 0 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: criticals.length + warnings.length > 0 ? 6 : 0 }}>
              <span style={{ fontSize: 12, fontWeight: 700, color }}>
                🩺 Qualità: {sc}/10
              </span>
              <button onClick={() => setLiveDoctor(null)} style={{ background: "none", border: "none", color: "var(--text)", opacity: 0.4, cursor: "pointer", fontSize: 14, lineHeight: 1 }}>×</button>
            </div>
            {criticals.length > 0 && (
              <div style={{ marginBottom: 4 }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: "#f87171", textTransform: "uppercase", marginBottom: 3 }}>Critici ({criticals.length})</div>
                {criticals.slice(0, 3).map((f, i) => (
                  <div key={i} style={{ fontSize: 11, color: "#fca5a5", lineHeight: 1.4, marginBottom: 2 }}>• {f.message || f.field}</div>
                ))}
              </div>
            )}
            {warnings.length > 0 && (
              <div>
                <div style={{ fontSize: 10, fontWeight: 700, color: "#facc15", textTransform: "uppercase", marginBottom: 3 }}>Warning ({warnings.length})</div>
                {warnings.slice(0, 3).map((f, i) => (
                  <div key={i} style={{ fontSize: 11, color: "#fde68a", lineHeight: 1.4, marginBottom: 2 }}>• {f.message || f.field}</div>
                ))}
                {warnings.length > 3 && <div style={{ fontSize: 10, color: "var(--text)", opacity: 0.5 }}>…e altri {warnings.length - 3}</div>}
              </div>
            )}
            {criticals.length === 0 && warnings.length === 0 && (
              <div style={{ fontSize: 11, color: "#4ade80" }}>✓ Nessun problema trovato</div>
            )}
          </div>
        );
      })()}

      {/* Obiettivo + Minaccia — solo panel giocatori */}
      {!isGmMode && (
        <>
          <div style={{ padding: "0 14px 8px", borderBottom: "1px solid var(--border)", flexShrink: 0 }}>
            <div style={{ padding: "7px 10px", borderRadius: 7, background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.38)" }}>
              <div style={{ fontSize: 9, fontWeight: 800, color: "var(--accent)", textTransform: "uppercase", letterSpacing: 0.6, marginBottom: 3 }}>Obiettivo</div>
              <div style={{ fontSize: 12, color: "var(--text-h)", lineHeight: 1.4 }}>{primaryObjective}</div>
            </div>
          </div>
          <div style={{ padding: "7px 14px", borderBottom: "1px solid var(--border)", flexShrink: 0 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 11, marginBottom: 3 }}>
              <span style={{ color: "var(--text)", opacity: 0.7 }}>⚠ {adventure?.threat_description || "Minaccia"}</span>
              <span style={{ color: threatColor, fontWeight: 700 }}>{threatPct}%</span>
            </div>
            <div style={{ height: 4, borderRadius: 2, background: "var(--border)", overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${threatPct}%`, background: threatColor, transition: "width 0.5s, background 0.5s" }} />
            </div>
          </div>
        </>
      )}

      {/* Tab bar */}
      <div style={{ display: "flex", borderBottom: "1px solid var(--border)", flexShrink: 0, overflowX: "auto" }}>
        {!isGmMode ? (
          <>
            <button style={tabStyle("clues")} onClick={() => setTab("clues")}>🔍 Indizi</button>
            <button style={tabStyle("threads")} onClick={() => setTab("threads")}>🧵 Piste{readyThreads.length ? ` (${readyThreads.length})` : ""}</button>
            <button style={tabStyle("npcs")} onClick={() => setTab("npcs")}>👥 PNG</button>
            {mapState && <button style={{ ...tabStyle("map"), color: "var(--accent)" }} onClick={() => onOpenMap && onOpenMap()}>🗺 Mappa</button>}
            {/* Clock solo se discovered=true: il Master ha scelto di renderlo visibile ai giocatori */}
            {(clocksData || []).some(c => c.discovered) && (
              <button style={tabStyle("clocks")} title="Timer che i giocatori conoscono esplicitamente" onClick={() => setTab("clocks")}>
                ⏱{(clocksData || []).filter(c => c.discovered && c.active !== false).length > 0 ? ` ${(clocksData || []).filter(c => c.discovered && c.active !== false).length}` : ""}
              </button>
            )}
          </>
        ) : (
          <>
            <button style={tabStyle("gm_overview")} onClick={() => setTab("gm_overview")}>Canovaccio</button>
            <button style={tabStyle("gm_threads")} onClick={() => setTab("gm_threads")}>Piste</button>
            <button style={tabStyle("gm_clues")} onClick={() => setTab("gm_clues")}>Indizi</button>
            <button style={tabStyle("gm_npcs")} onClick={() => setTab("gm_npcs")}>PNG</button>
            {mapState && <button style={{ ...tabStyle("gm_map"), color: "var(--accent)" }} onClick={() => { onOpenMap && onOpenMap(); }}>🗺 Mappa</button>}
            <button style={tabStyle("gm_clocks")} onClick={() => setTab("gm_clocks")}>
              ⏱{(clocksData || []).length > 0 ? ` ${(clocksData || []).length}` : ""}
            </button>
            <button style={tabStyle("gm_maps")} onClick={() => setTab("gm_maps")}>Tattiche{tacticalNodes.length ? ` ${tacticalNodes.length}` : ""}</button>
            <button style={tabStyle("gm_events")} onClick={() => setTab("gm_events")} title="Storico eventi di gioco">
              📜{gmEventLog?.length > 0 ? ` ${gmEventLog.length}` : ""}
            </button>
          </>
        )}
      </div>

      <div style={{ flex: 1, minHeight: 0, overflowY: "auto", padding: "10px 14px" }}>
        {isGmMode && tab === "gm_overview" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {/* ── Adventure title ── */}
            {(() => {
              const advDef = adventure?.adventure_definition || adventure || {};
              const advTitle = advDef.title || adventure?.title || "";
              if (!advTitle) return null;
              return (
                <div style={{
                  padding: "14px 14px 12px",
                  borderRadius: 10,
                  background: "linear-gradient(135deg, rgba(124,58,237,0.18) 0%, rgba(167,139,250,0.08) 100%)",
                  border: "1px solid rgba(167,139,250,0.38)",
                  textAlign: "center",
                }}>
                  <div style={{ fontSize: 9, fontWeight: 700, color: "#a78bfa", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 5, opacity: 0.75 }}>
                    Avventura
                  </div>
                  <div style={{ fontSize: 16, fontWeight: 900, color: "#e9d5ff", lineHeight: 1.2, letterSpacing: 0.3 }}>
                    {advTitle}
                  </div>
                </div>
              );
            })()}
            {/* ── Premise ── */}
            {(() => {
              const advDef = adventure?.adventure_definition || adventure || {};
              const premise = advDef.premise || advDef.initial_hook || advDef.description || "";
              return premise ? (
                <div style={{ padding: "10px 11px", borderRadius: 8, background: "rgba(124,58,237,0.08)", border: "1px solid rgba(124,58,237,0.32)" }}>
                  <div style={{ fontSize: 10, fontWeight: 900, color: "#c084fc", textTransform: "uppercase", letterSpacing: 0.7, marginBottom: 5 }}>
                    Premessa
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-h)", lineHeight: 1.55 }}>{premise}</div>
                </div>
              ) : null;
            })()}
            {(sourceMode || archetypeProfile?.primary_archetype) && (
              <div style={{ padding: "10px 11px", borderRadius: 8, background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.32)" }}>
                <div style={{ fontSize: 10, fontWeight: 900, color: "#fbbf24", textTransform: "uppercase", letterSpacing: 0.7, marginBottom: 7 }}>Origine e Struttura</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginBottom: 7 }}>
                  {sourceMode && <span style={{ fontSize: 10, color: "#fde68a", padding: "2px 7px", borderRadius: 5, border: "1px solid rgba(245,158,11,0.34)" }}>source: {sourceMode}</span>}
                  {archetypeProfile?.primary_archetype && <span style={{ fontSize: 10, color: "#bfdbfe", padding: "2px 7px", borderRadius: 5, border: "1px solid rgba(96,165,250,0.34)" }}>archetipo: {archetypeProfile.primary_archetype}</span>}
                  {preservationPolicy?.forbid_structural_compression && <span style={{ fontSize: 10, color: "#bbf7d0", padding: "2px 7px", borderRadius: 5, border: "1px solid rgba(74,222,128,0.34)" }}>PDF canon</span>}
                </div>
                {archetypeProfile?.secondary_archetypes?.length > 0 && (
                  <div style={{ fontSize: 11, color: "var(--text)", lineHeight: 1.4 }}>Secondari: {archetypeProfile.secondary_archetypes.join(", ")}</div>
                )}
                <div style={{ fontSize: 11, color: "var(--text)", lineHeight: 1.4, marginTop: 4 }}>
                  Preservati: {preservedElements.length} · Inferiti: {inferredElements.length}
                </div>
                {validationWarnings.length > 0 && (
                  <div style={{ fontSize: 10, color: "#facc15", lineHeight: 1.35, marginTop: 5 }}>
                    Warning: {validationWarnings.slice(0, 2).join(" · ")}
                  </div>
                )}
              </div>
            )}
            {Object.keys(runtimeQuality).length > 0 && (
              <div style={{ padding: "10px 11px", borderRadius: 8, background: "rgba(96,165,250,0.08)", border: "1px solid rgba(96,165,250,0.28)" }}>
                <div style={{ fontSize: 10, fontWeight: 900, color: "#93c5fd", textTransform: "uppercase", letterSpacing: 0.7, marginBottom: 8 }}>Runtime Quality</div>
                {[
                  ["fiction_density_score", "Densità fiction"],
                  ["clue_concreteness_score", "Indizi concreti"],
                  ["npc_agenda_score", "Agende PNG"],
                  ["location_playability_score", "Location giocabili"],
                  ["clock_operational_score", "Clock operativi"],
                ].map(([key, label]) => {
                  const val = runtimeQuality[key];
                  if (val === undefined || val === null) return null;
                  const color = val >= 75 ? "#4ade80" : val >= 50 ? "#facc15" : "#f87171";
                  return (
                    <div key={key} style={{ marginBottom: 6 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "var(--text)", marginBottom: 2 }}>
                        <span>{label}</span><b style={{ color }}>{val}%</b>
                      </div>
                      <div style={{ height: 4, borderRadius: 4, background: "rgba(255,255,255,0.08)", overflow: "hidden" }}>
                        <div style={{ width: `${Math.max(0, Math.min(100, val))}%`, height: "100%", background: color }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            <div style={{ padding: "10px 11px", borderRadius: 8, background: "rgba(74,222,128,0.08)", border: "1px solid rgba(74,222,128,0.28)" }}>
              <div style={{ fontSize: 10, fontWeight: 900, color: "#4ade80", textTransform: "uppercase", letterSpacing: 0.7, marginBottom: 5 }}>Soluzione missione</div>
              <div style={{ fontSize: 12, color: "var(--text-h)", lineHeight: 1.5 }}>{primaryObjective}</div>
            </div>
            <div style={{ padding: "10px 11px", borderRadius: 8, background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.32)" }}>
              <div style={{ fontSize: 10, fontWeight: 900, color: "#fbbf24", textTransform: "uppercase", letterSpacing: 0.7, marginBottom: 5 }}>Verità nascosta</div>
              <div style={{ fontSize: 12, color: "var(--text-h)", lineHeight: 1.5 }}>{hiddenTruth || "Non definita nel canovaccio."}</div>
            </div>
            {keyLocations.length > 0 && (
              <div style={{ padding: "10px 11px", borderRadius: 8, background: "var(--code-bg)", border: "1px solid var(--border)" }}>
                <div style={{ fontSize: 10, fontWeight: 900, color: "#93c5fd", textTransform: "uppercase", letterSpacing: 0.7, marginBottom: 6 }}>Luoghi chiave</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                  {keyLocations.map((loc, i) => (
                    <span key={`${loc}-${i}`} style={{ fontSize: 10, color: "#bfdbfe", padding: "2px 7px", borderRadius: 5, border: "1px solid rgba(96,165,250,0.32)", background: "rgba(96,165,250,0.08)" }}>{loc}</span>
                  ))}
                </div>
              </div>
            )}
            {finaleConditions.length > 0 && (
              <div style={{ padding: "10px 11px", borderRadius: 8, background: "rgba(239,68,68,0.07)", border: "1px solid rgba(239,68,68,0.26)" }}>
                <div style={{ fontSize: 10, fontWeight: 900, color: "#fca5a5", textTransform: "uppercase", letterSpacing: 0.7, marginBottom: 6 }}>Condizioni finale</div>
                {finaleConditions.map((f, i) => (
                  <div key={i} style={{ fontSize: 11, color: "var(--text)", lineHeight: 1.45, marginBottom: 4 }}>{typeof f === "string" ? f : f.label || f.description || JSON.stringify(f)}</div>
                ))}
              </div>
            )}
            {storyThreads.length > 0 && (
              <div style={{ padding: "10px 11px", borderRadius: 8, background: "rgba(245,158,11,0.06)", border: "1px solid rgba(245,158,11,0.22)" }}>
                <div style={{ fontSize: 10, fontWeight: 900, color: "#fbbf24", textTransform: "uppercase", letterSpacing: 0.7, marginBottom: 7 }}>Stato piste ({storyThreads.length})</div>
                {storyThreads.map((t, i) => {
                  const sc = { resolved: "#4ade80", ready_to_deduce: "#60a5fa", active: "#fbbf24" }[t.status] || "rgba(255,255,255,0.35)";
                  const label = { resolved: "✓", ready_to_deduce: "⚡", active: "◔", hidden: "☁", unintroduced: "☁" }[t.status] || "☁";
                  const answer = t.true_answer || t.answer || t.solution || "";
                  const title = t.question || t.title || t.name || t.id || "(pista)";
                  return (
                    <div key={t.id || i} style={{ marginBottom: 7, paddingBottom: 7, borderBottom: i < storyThreads.length - 1 ? "1px solid rgba(255,255,255,0.05)" : "none" }}>
                      <div style={{ display: "flex", gap: 6, alignItems: "flex-start" }}>
                        <span style={{ fontSize: 11, color: sc, flexShrink: 0, marginTop: 1 }}>{label}</span>
                        <div>
                          <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-h)", lineHeight: 1.35 }}>{title}</div>
                          {answer && <div style={{ fontSize: 10, color: "#fde68a", lineHeight: 1.4, marginTop: 2 }}>↳ {answer}</div>}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            <div style={{ padding: "10px 11px", borderRadius: 8, background: "rgba(96,165,250,0.07)", border: "1px solid rgba(96,165,250,0.24)", fontSize: 11, color: "var(--text)", lineHeight: 1.45 }}>
              Questa zona mostra tutto il canovaccio: risposte, segreti, obiettivi nascosti e mappe non ancora scoperte.
            </div>
          </div>
        )}

        {isGmMode && tab === "gm_threads" && (() => {
          // GM vede TUTTE le piste, incluse quelle non ancora scoperte dai giocatori
          const gmThreads = storyThreads.length > 0 ? storyThreads : (adventure?.story_threads || []);
          const statusLabel = s => ({ resolved: "✓ risolta", ready_to_deduce: "⚡ pronta", active: "◔ in corso", hidden: "☁ non ancora", unintroduced: "☁ non ancora" }[s] || s || "☁ non ancora");
          const statusColor = s => ({ resolved: "#4ade80", ready_to_deduce: "#60a5fa", active: "#fbbf24", hidden: "var(--text)", unintroduced: "var(--text)" }[s] || "var(--text)");
          return (
            <div>
              {gmThreads.length === 0 && <div style={{ fontSize: 12, color: "var(--text)", opacity: 0.55, textAlign: "center", marginTop: 20 }}>Nessuna pista canonica.</div>}
              {gmThreads.map((t, i) => {
                const sc = statusColor(t.status);
                return (
                  <div key={t.id || i} style={{ padding: "9px 10px", borderRadius: 8, marginBottom: 8, background: "var(--code-bg)", border: `1px solid ${sc}33`, borderLeft: `3px solid ${sc}` }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 4 }}>
                      <div style={{ fontSize: 12, fontWeight: 800, color: "var(--text-h)", lineHeight: 1.35 }}>{t.question || t.title || t.name || t.id || "(pista senza titolo)"}</div>
                      <span style={{ fontSize: 9, color: sc, textTransform: "uppercase", flexShrink: 0, fontWeight: 700 }}>{statusLabel(t.status)}</span>
                    </div>
                    {(t.true_answer || t.answer || t.solution) && <div style={{ fontSize: 11, color: "#fbbf24", lineHeight: 1.45, marginBottom: 4 }}><b>Risposta:</b> {t.true_answer || t.answer || t.solution}</div>}
                    {t.payoff && <div style={{ fontSize: 11, color: "#93c5fd", lineHeight: 1.45, marginBottom: 4 }}><b>Serve a:</b> {t.payoff}</div>}
                    {(t.required_details || []).length > 0 && (
                      <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                        {t.required_details.map(({ id, clue, found, progress }) => (
                          <div key={id} style={{ fontSize: 10, color: found ? "#4ade80" : (progress?.ticks || 0) > 0 ? "#93c5fd" : "var(--text)", opacity: found || (progress?.ticks || 0) > 0 ? 1 : 0.6, padding: "3px 6px", borderRadius: 5, background: "rgba(255,255,255,0.03)" }}>
                            {found ? "✓" : (progress?.ticks || 0) > 0 ? "◔" : "□"} {clueTitle(clue)}{clue?.location ? ` · ${clue.location}` : ""}
                          </div>
                        ))}
                        {/* thread senza required_details → mostra i required_clues grezzi */}
                        {t.required_details.length === 0 && (t.required_clues || []).map(id => (
                          <div key={id} style={{ fontSize: 10, color: "var(--text)", opacity: 0.55, padding: "3px 6px" }}>□ {id}</div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          );
        })()}

        {isGmMode && tab === "gm_clues" && (
          <div>
            {clues.length === 0 && <div style={{ fontSize: 12, color: "var(--text)", opacity: 0.55, textAlign: "center", marginTop: 20 }}>Nessun indizio canonico.</div>}
            {clues.map(c => {
              const found = clueFoundSet.has(c.id);
              const progress = clueProgress?.[c.id];
              return (
                <div key={c.id} style={{ padding: "8px 10px", borderRadius: 8, marginBottom: 6, background: "var(--code-bg)", border: `1px solid ${found ? "rgba(74,222,128,0.35)" : progress?.ticks ? "rgba(96,165,250,0.32)" : "var(--border)"}` }}>
                  <div style={{ fontSize: 12, fontWeight: 800, color: "var(--text-h)", marginBottom: 3 }}>{found ? "✓" : progress?.ticks ? "◔" : "□"} {clueTitle(c)}</div>
                  <div style={{ display: "flex", gap: 5, flexWrap: "wrap", alignItems: "center" }}>
                    {c.type && <div style={{ fontSize: 10, color: "#c4b5fd", textTransform: "uppercase", letterSpacing: 0.4 }}>{c.type}</div>}
                    {c.source_status && <span style={{ fontSize: 9, color: c.source_status === "explicit" ? "#bbf7d0" : c.source_status === "inferred" ? "#fde68a" : "#c4b5fd", border: "1px solid rgba(255,255,255,0.16)", borderRadius: 4, padding: "1px 5px", textTransform: "uppercase" }}>{c.source_status}</span>}
                    {c.is_preserved_from_pdf && <span style={{ fontSize: 9, color: "#93c5fd", border: "1px solid rgba(96,165,250,0.28)", borderRadius: 4, padding: "1px 5px" }}>PDF canon</span>}
                  </div>
                  {c.reveals && <div style={{ fontSize: 11, color: "#fbbf24", lineHeight: 1.4, marginTop: 3 }}><b>Rivela:</b> {c.reveals}</div>}
                  {c.payoff && <div style={{ fontSize: 11, color: "#93c5fd", lineHeight: 1.4, marginTop: 2 }}><b>Payoff:</b> {c.payoff}</div>}
                  {c.thread_id && <div style={{ fontSize: 10, color: "var(--text)", opacity: 0.55, marginTop: 3 }}>Pista: {c.thread_id}</div>}
                  {c.location && <div style={{ fontSize: 10, color: "var(--text)", opacity: 0.55 }}>Dove: {c.location}</div>}
                  {c.source_ref?.section && <div style={{ fontSize: 10, color: "var(--text)", opacity: 0.55 }}>Fonte: {c.source_ref.section}</div>}
                </div>
              );
            })}
          </div>
        )}

        {isGmMode && tab === "gm_npcs" && (
          <div>
            {npcs.length === 0 && <div style={{ fontSize: 12, color: "var(--text)", opacity: 0.55, textAlign: "center", marginTop: 20 }}>Nessun PNG canonico.</div>}
            {npcs.map(npc => {
              const agenda = npc.npc_agenda || {};
              const threatLevel = npc.threat_to_player ?? 0;
              const threatBorderColor = threatLevel >= 3 ? "rgba(239,68,68,0.5)" : threatLevel >= 2 ? "rgba(249,115,22,0.5)" : threatLevel >= 1 ? "rgba(250,204,21,0.4)" : "rgba(245,158,11,0.28)";
              const hasGurps = npc.gurps_fo != null || npc.gurps_de != null;
              const hasCombat = npc.combat_hp != null || npc.combat_attack_skill != null;
              return (
                <div key={npc.id || npc.name} style={{ padding: "9px 10px", borderRadius: 8, marginBottom: 8, background: "var(--code-bg)", border: `1px solid ${threatBorderColor}` }}>
                  {/* Header */}
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
                    <AvatarCircle src={(npcAvatars || {})[npc.name]} size={38} fallback="👤" />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 12, fontWeight: 800, color: "var(--text-h)" }}>{npc.name}</div>
                      <div style={{ fontSize: 10, color: "#fbbf24", textTransform: "uppercase", letterSpacing: 0.4 }}>{agenda.role || npc.role || "PNG"} · {agenda.arc_status || npc.status || "ignoto"}</div>
                    </div>
                    {threatLevel > 0 && (
                      <span style={{ fontSize: 10, padding: "2px 6px", borderRadius: 4, fontWeight: 700, flexShrink: 0,
                        background: threatLevel >= 3 ? "rgba(239,68,68,0.15)" : threatLevel >= 2 ? "rgba(249,115,22,0.15)" : "rgba(250,204,21,0.1)",
                        color: threatLevel >= 3 ? "#f87171" : threatLevel >= 2 ? "#fb923c" : "#fbbf24",
                        border: `1px solid ${threatLevel >= 3 ? "#ef444455" : threatLevel >= 2 ? "#f9731655" : "#facc1555"}`,
                      }}>
                        ⚔ T{threatLevel}
                      </span>
                    )}
                  </div>

                  {/* Stat GURPS */}
                  {hasGurps && (
                    <div style={{ display: "flex", gap: 5, flexWrap: "wrap", marginBottom: 6 }}>
                      {[["FO", npc.gurps_fo, "#f87171"], ["DE", npc.gurps_de, "#4ade80"], ["IN", npc.gurps_in, "#60a5fa"], ["SA", npc.gurps_sa, "#c084fc"]].map(([l, v, c]) =>
                        v != null ? (
                          <span key={l} style={{ fontSize: 11, padding: "2px 7px", borderRadius: 5, background: `${c}18`, border: `1px solid ${c}44`, color: "var(--text-h)" }}>
                            <b style={{ color: c }}>{l}</b> {v}
                          </span>
                        ) : null
                      )}
                      {npc.combat_hp != null && (
                        <span style={{ fontSize: 11, padding: "2px 7px", borderRadius: 5, background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", color: "#fca5a5" }}>
                          ❤️ {npc.combat_hp}
                        </span>
                      )}
                      {npc.combat_dr > 0 && (
                        <span style={{ fontSize: 11, padding: "2px 7px", borderRadius: 5, background: "rgba(96,165,250,0.1)", border: "1px solid rgba(96,165,250,0.3)", color: "#93c5fd" }}>
                          🛡 DR{npc.combat_dr}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Skill di combattimento */}
                  {(hasCombat || Object.keys(npc.gurps_skills || {}).length > 0) && (
                    <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginBottom: 5 }}>
                      {npc.combat_attack_skill != null && (
                        <span style={{ fontSize: 10, padding: "1px 6px", borderRadius: 4, background: "rgba(239,68,68,0.1)", color: "#f87171" }}>
                          Attacco {npc.combat_attack_skill} · {npc.combat_damage_dice || "1d6"} {npc.combat_damage_type || "cr"}
                        </span>
                      )}
                      {npc.combat_active_defense != null && (
                        <span style={{ fontSize: 10, padding: "1px 6px", borderRadius: 4, background: "rgba(96,165,250,0.1)", color: "#93c5fd" }}>
                          Difesa {npc.combat_active_defense}
                        </span>
                      )}
                      {Object.entries(npc.gurps_skills || {}).slice(0, 4).map(([sk, lv]) => (
                        <span key={sk} style={{ fontSize: 10, padding: "1px 6px", borderRadius: 4, background: "rgba(167,139,250,0.1)", color: "#a78bfa" }}>
                          {sk} {lv}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Agenda / segreti */}
                  {agenda.goal && <div style={{ fontSize: 11, color: "var(--text)", lineHeight: 1.4, marginBottom: 2 }}><b>Obiettivo:</b> {agenda.goal}</div>}
                  {(npc.goal && !agenda.goal) && <div style={{ fontSize: 11, color: "var(--text)", lineHeight: 1.4, marginBottom: 2 }}><b>Obiettivo:</b> {npc.goal}</div>}
                  {agenda.secret && <div style={{ fontSize: 11, color: "#fbbf24", lineHeight: 1.4, marginBottom: 2 }}><b>Segreto:</b> {agenda.secret}</div>}
                  {(npc.secret && !agenda.secret) && <div style={{ fontSize: 11, color: "#fbbf24", lineHeight: 1.4, marginBottom: 2 }}><b>Segreto:</b> {npc.secret}</div>}
                  {(agenda.methods || npc.methods)?.length > 0 && <div style={{ fontSize: 11, color: "#93c5fd", lineHeight: 1.4, marginBottom: 2 }}><b>Metodi:</b> {(agenda.methods || npc.methods).join(" · ")}</div>}
                  {(npc.location || npc.location_id) && <div style={{ fontSize: 10, color: "var(--text)", opacity: 0.55, marginTop: 3 }}>📍 {npc.location || npc.location_id}</div>}
                  {npc.description && <div style={{ fontSize: 10, color: "var(--text)", opacity: 0.6, lineHeight: 1.35, marginTop: 3, fontStyle: "italic" }}>{npc.description}</div>}
                </div>
              );
            })}
          </div>
        )}

        {isGmMode && tab === "gm_clocks" && (
          <div style={{ padding: "4px 0" }}>
            <div style={{ fontSize: 11, color: "var(--text)", opacity: 0.55, marginBottom: 10, lineHeight: 1.4 }}>
              Stato attuale di tutti i clock — compresi quelli ancora nascosti ai giocatori.
            </div>
            <ClocksPanel clocks={clocksData} isGM={true} />
            {(!clocksData || clocksData.length === 0) && (
              <div style={{ fontSize: 12, color: "var(--text)", opacity: 0.45, fontStyle: "italic" }}>
                Nessun clock attivo in questa avventura.
              </div>
            )}
          </div>
        )}

        {isGmMode && tab === "gm_events" && (
          <div style={{ padding: "4px 0" }}>
            <div style={{ fontSize: 11, color: "var(--text)", opacity: 0.55, marginBottom: 10, lineHeight: 1.4 }}>
              Cronologia degli eventi di gioco: tick clock, azioni PNG, eventi narrativi. Diverso dal tab ⏱ che mostra lo stato <em>corrente</em>.
            </div>
            {(!gmEventLog || gmEventLog.length === 0) && (
              <div style={{ fontSize: 12, color: "var(--text)", opacity: 0.45, fontStyle: "italic" }}>Nessun evento ancora.</div>
            )}
            {[...(gmEventLog || [])].reverse().map((ev, i) => {
              const isClock = ev._type === "clock";
              const borderColor = isClock ? (ev.completed ? "#ef4444" : "#f59e0b") : ev.action === "eliminate_npc" ? "#ef4444" : ev.action === "destroy_clue" ? "#f97316" : ev.action === "scare_npc" ? "#a855f7" : "#06b6d4";
              const icon = isClock ? (ev.completed ? "💀" : "⏱") : { destroy_clue: "🔥", eliminate_npc: "💀", scare_npc: "😱", move_clue: "📦", create_clue: "🔍", failforward_clue: "🛡" }[ev.action] || "⚡";
              const title = isClock ? ev.label : (ev.actor_name || ev.action);
              const detail = isClock
                ? (ev.completed ? `COMPLETATO → ${ev.consequence}` : `${ev.old_value} → ${ev.new_value}/${ev.max_value}`)
                : ev.narration;
              return (
                <div key={ev.id || i} style={{ padding: "7px 9px", borderRadius: 8, marginBottom: 5, background: "var(--code-bg)", borderLeft: `3px solid ${borderColor}` }}>
                  <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 2 }}>
                    <span style={{ fontSize: 13 }}>{icon}</span>
                    <span style={{ fontSize: 11, fontWeight: 700, color: borderColor }}>{title}</span>
                  </div>
                  {detail && <div style={{ fontSize: 11, color: "rgba(248,250,252,0.7)", lineHeight: 1.35 }}>{detail}</div>}
                </div>
              );
            })}
          </div>
        )}

        {isGmMode && tab === "gm_maps" && (
          <div>
            {tacticalNodes.length === 0 && <div style={{ fontSize: 12, color: "var(--text)", opacity: 0.55, textAlign: "center", marginTop: 20 }}>Nessuna zona calda preparata.</div>}
            {tacticalNodes.map(node => {
              const tactical = node.tactical_map || {};
              const img = preparedTacticalMaps?.[node.id];
              const loading = preparingTacticalMaps?.has?.(node.id);
              const known = isKnownTacticalNode(node, mapState);
              return (
                <div key={node.id} style={{ borderRadius: 8, marginBottom: 10, background: "var(--code-bg)", border: `1px solid ${node.is_final ? "rgba(239,68,68,0.45)" : "rgba(96,165,250,0.32)"}`, overflow: "hidden" }}>
                  <div style={{ padding: "8px 10px", display: "flex", justifyContent: "space-between", gap: 8 }}>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 850, color: "var(--text-h)" }}>{node.name}</div>
                      <div style={{ fontSize: 10, color: known ? "#4ade80" : "#fbbf24", textTransform: "uppercase", letterSpacing: 0.4 }}>
                        {known ? "scoperta" : "nascosta"} · {node.is_final ? "finale" : tactical.role || "zona calda"} · {tactical.cols || "auto"}×{tactical.rows || "auto"}
                      </div>
                    </div>
                    {!img && (
                      <button onClick={() => onPrepareTacticalMap && onPrepareTacticalMap(node)} disabled={loading} style={{ fontSize: 10, padding: "4px 7px", borderRadius: 6, border: "1px solid var(--border)", background: "rgba(255,255,255,0.05)", color: "var(--text)", cursor: loading ? "default" : "pointer" }}>
                        {loading ? "Creo..." : "Crea"}
                      </button>
                    )}
                  </div>
                  {img && <img src={`data:image/jpeg;base64,${img}`} alt="" style={{ display: "block", width: "100%", aspectRatio: "4 / 3", objectFit: "cover", borderTop: "1px solid var(--border)" }} onError={e => { e.currentTarget.src = `data:image/png;base64,${img}`; }} />}
                  {(tactical.trigger || tactical.features?.length || tactical.hazards?.length) && (
                    <div style={{ padding: "8px 10px", fontSize: 11, color: "var(--text)", lineHeight: 1.45 }}>
                      {tactical.trigger && <div><b>Trigger:</b> {tactical.trigger}</div>}
                      {tactical.features?.length > 0 && <div><b>Coperture:</b> {tactical.features.join(" · ")}</div>}
                      {tactical.hazards?.length > 0 && <div><b>Rischi:</b> {tactical.hazards.join(" · ")}</div>}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {tab === "map" && (
          <div style={{ margin: "-10px -14px", height: "100%", display: "flex", flexDirection: "column" }}>
            <LocationGraph mapState={mapState} isGM={false} onMove={onMove} backdropImage={backdropImage} mapPositions={mapPositions} players={players} avatars={avatars} npcStatuses={npcStatuses} advNpcs={advNpcs} />
          </div>
        )}

        {tab === "clocks" && (
          <div style={{ padding: "4px 0" }}>
            <ClocksPanel clocks={clocksData} isGM={false} />
          </div>
        )}

        {tab === "clues" && (
          <div>
            {/* Obiettivo sempre visibile */}
            {/* Piste pronte */}
            {readyThreads.length > 0 && (
              <div style={{
                padding: "8px 10px", borderRadius: 8, marginBottom: 10,
                background: "rgba(96,165,250,0.12)", border: "1px solid rgba(96,165,250,0.45)",
              }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: "#60a5fa", marginBottom: 3 }}>🧠 Piste pronte</div>
                <div style={{ fontSize: 11, color: "var(--text)", lineHeight: 1.4 }}>
                  {readyThreads.map(t => t.question).join(" · ")}. Formula una deduzione o verifica la pista.
                </div>
              </div>
            )}

            {resolvedThreads.length > 0 && (
              <div style={{
                padding: "8px 10px", borderRadius: 8, marginBottom: 10,
                background: "rgba(74,222,128,0.10)", border: "1px solid rgba(74,222,128,0.35)",
              }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: "#4ade80", marginBottom: 3 }}>✓ Deduzioni risolte</div>
                <div style={{ fontSize: 11, color: "var(--text)", lineHeight: 1.4 }}>
                  {resolvedThreads.map(t => t.title || t.question).join(" · ")}
                </div>
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
              {knownClues.length} elementi noti · {gameState?.clues_found?.length || 0} indizi confermati
            </div>

            {knownClues.length === 0 && (
              <div style={{ fontSize: 12, color: "var(--text)", opacity: 0.55, textAlign: "center", marginTop: 20 }}>
                Nessun indizio noto. Le prove appariranno qui solo quando vengono scoperte o iniziano a progredire.
              </div>
            )}

            {knownClues.map(c => {
              const found = gameState?.clues_found?.includes(c.id);
              const progress = clueProgress?.[c.id];
              const partial = !found && progress?.ticks > 0;
              return (
                <div key={c.id} style={{
                  padding: "8px 10px", borderRadius: 8, marginBottom: 6,
                  background: found ? "rgba(74,222,128,0.08)" : partial ? "rgba(96,165,250,0.08)" : "var(--code-bg)",
                  border: `1px solid ${found ? "rgba(74,222,128,0.3)" : partial ? "rgba(96,165,250,0.32)" : "var(--border)"}`,
                  opacity: found || partial ? 1 : 0.5,
                }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: found ? "#4ade80" : partial ? "#93c5fd" : "var(--text)", marginBottom: 2 }}>
                    {found ? "🔍" : partial ? "◔" : "⬜"} {c.text}
                  </div>
                  {partial && (
                    <div style={{ fontSize: 11, color: "#93c5fd", marginBottom: 2 }}>
                      Progresso {Math.min(2, progress.ticks)}/2: {progress.note}
                    </div>
                  )}
                  {found && c.reveals && <div style={{ fontSize: 11, color: "#4ade80", fontStyle: "italic", marginBottom: 2 }}>↳ {c.reveals}</div>}
                  {found && c.payoff && <div style={{ fontSize: 11, color: "#93c5fd", marginBottom: 2 }}>Sblocca: {c.payoff}</div>}
                  {c.thread_id && <div style={{ fontSize: 10, color: "var(--text)", opacity: 0.5 }}>Pista: {c.thread_id}</div>}
                  {c.location && <div style={{ fontSize: 11, color: "var(--text)", opacity: found ? 0.5 : 0.7 }}>📍 {c.location}</div>}
                </div>
              );
            })}
          </div>
        )}

        {tab === "maps" && (
          <div>
            {knownTacticalNodes.length === 0 && (
              <div style={{ fontSize: 12, color: "var(--text)", opacity: 0.55, textAlign: "center", marginTop: 20 }}>
                Nessuna zona calda scoperta. Le battlemap note compariranno quando il gruppo raggiunge o identifica quelle aree.
              </div>
            )}
            {knownTacticalNodes.map(node => {
              const tactical = node.tactical_map || {};
              const img = preparedTacticalMaps?.[node.id];
              const loading = preparingTacticalMaps?.has?.(node.id);
              const role = tactical.role === "finale" || node.is_final ? "Finale" : "Zona calda";
              return (
                <div key={node.id} style={{
                  borderRadius: 8, marginBottom: 10, background: "var(--code-bg)",
                  border: `1px solid ${node.is_final || tactical.role === "finale" ? "rgba(239,68,68,0.45)" : "rgba(96,165,250,0.35)"}`,
                  overflow: "hidden",
                }}>
                  <div style={{ padding: "8px 10px", display: "flex", justifyContent: "space-between", gap: 8, alignItems: "flex-start" }}>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 800, color: "var(--text-h)", lineHeight: 1.3 }}>{node.name}</div>
                      <div style={{ fontSize: 10, color: node.is_final || tactical.role === "finale" ? "#f87171" : "#93c5fd", textTransform: "uppercase", letterSpacing: 0.6 }}>
                        {role} · {tactical.layout || "stanza"} · {tactical.cols || "auto"}×{tactical.rows || "auto"}
                      </div>
                    </div>
                    {!img && (
                      <button
                        onClick={() => onPrepareTacticalMap && onPrepareTacticalMap(node)}
                        disabled={loading}
                        style={{
                          fontSize: 10, padding: "4px 7px", borderRadius: 6, cursor: loading ? "default" : "pointer",
                          border: "1px solid var(--border)", background: "rgba(255,255,255,0.05)", color: "var(--text)",
                        }}
                      >
                        {loading ? "Creo..." : "Crea"}
                      </button>
                    )}
                  </div>
                  {img ? (
                    <img
                      src={`data:image/jpeg;base64,${img}`}
                      alt=""
                      style={{ display: "block", width: "100%", aspectRatio: "4 / 3", objectFit: "cover", borderTop: "1px solid var(--border)" }}
                      onError={e => { e.currentTarget.src = `data:image/png;base64,${img}`; }}
                    />
                  ) : (
                    <div style={{
                      height: 116, borderTop: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "center",
                      background: "linear-gradient(135deg, rgba(96,165,250,0.08), rgba(15,23,42,0.35))",
                      color: "var(--text)", opacity: 0.7, fontSize: 11, textAlign: "center", padding: 12,
                    }}>
                      {loading ? "Battlemap in preparazione..." : "Battlemap pronta da generare per questa zona."}
                    </div>
                  )}
                  {(tactical.features?.length > 0 || tactical.hazards?.length > 0 || tactical.trigger) && (
                    <div style={{ padding: "8px 10px", fontSize: 11, color: "var(--text)", lineHeight: 1.45 }}>
                      {tactical.trigger && <div><b>Trigger:</b> {tactical.trigger}</div>}
                      {tactical.features?.length > 0 && <div><b>Coperture:</b> {tactical.features.join(" · ")}</div>}
                      {tactical.hazards?.length > 0 && <div><b>Rischi:</b> {tactical.hazards.join(" · ")}</div>}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {tab === "npcs" && (
          <div>
            {knownNpcs.length === 0 && <div style={{ fontSize: 12, color: "var(--text)", opacity: 0.5, textAlign: "center", marginTop: 20 }}>Nessun PNG incontrato</div>}
            {/* ── NOTA GIOCATORE: solo ciò che i pg hanno osservato ── */}
            {knownNpcs.map(npc => {
              const st = npcStatuses[npc.id] || {};
              const status = st.status || npc.status || "alive";
              const attitude = st.attitude || npc.attitude || "neutral";
              // Ruolo pubblico: mostra solo se NON è una categoria GM riservata
              const GM_ROLES = new Set(["antagonista", "villain", "antagonist", "antagonist_main", "main_villain", "antagonist_secondary"]);
              const publicRole = !GM_ROLES.has((npc.role || "").toLowerCase()) ? npc.role : null;
              // Descrizione pubblica: usa appearance o profession; MAI goal/plan/description GM
              const publicDesc = npc.appearance || npc.profession || npc.public_role || null;
              // Ultima location osservata (solo da npc_statuses — non da npc.location che può essere GM)
              const lastSeen = st.location || st.last_seen_at || null;
              // Note di interazione accumulate dal sistema (non segreti)
              const interactionNote = st.last_reaction_level
                ? `Ultima reazione: ${st.last_reaction_level}`
                : st.consulted ? "Interrogato dal gruppo" : null;
              return (
                <div key={npc.id || npc.name} style={{
                  padding: "9px 11px", borderRadius: 8, marginBottom: 6,
                  background: "var(--code-bg)", border: "1px solid var(--border)",
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
                    <AvatarCircle src={(npcAvatars || {})[npc.name]} size={42} fallback="👤" />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 6 }}>
                        <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-h)", lineHeight: 1.2 }}>{npc.name}</span>
                        <div style={{ display: "flex", gap: 4, flexShrink: 0 }}>
                          <NpcStatusBadge status={status} size="sm" />
                          <NpcAttitudeBadge attitude={attitude} size="sm" />
                        </div>
                      </div>
                      {publicRole && <div style={{ fontSize: 11, color: "var(--text)", opacity: 0.7, marginTop: 1 }}>{publicRole}</div>}
                      {publicDesc && <div style={{ fontSize: 11, color: "var(--text)", opacity: 0.65, marginTop: 1, fontStyle: "italic" }}>{publicDesc}</div>}
                      {lastSeen && <div style={{ fontSize: 10, color: "var(--text)", opacity: 0.5, marginTop: 3 }}>📍 Visto a: {lastSeen}</div>}
                      {interactionNote && <div style={{ fontSize: 10, color: "#93c5fd", opacity: 0.8, marginTop: 2 }}>↳ {interactionNote}</div>}
                      {st.pressure > 0 && (
                        <div style={{ marginTop: 5 }}>
                          <div style={{ fontSize: 9, color: "var(--text)", opacity: 0.5, marginBottom: 2 }}>
                            Pressione {st.pressure}/10
                          </div>
                          <div style={{ height: 4, borderRadius: 4, background: "rgba(255,255,255,0.08)", overflow: "hidden" }}>
                            <div style={{ height: "100%", width: `${st.pressure * 10}%`, background: st.pressure >= 7 ? "#ef4444" : st.pressure >= 4 ? "#f59e0b" : "#60a5fa", transition: "width 0.4s" }} />
                          </div>
                        </div>
                      )}
                      {st.witness_state && (
                        <div style={{ fontSize: 10, color: "#fbbf24", opacity: 0.85, marginTop: 2 }}>👁 {st.witness_state}</div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {tab === "threads" && (
          <div>
            {activeThreads.length === 0 && <div style={{ fontSize: 12, color: "var(--text)", opacity: 0.5, textAlign: "center", marginTop: 20 }}>Nessuna pista emersa</div>}
            {activeThreads.map((t, i) => {
              if (typeof t === "string") {
                return (
                  <div key={i} style={{ padding: "8px 10px", borderRadius: 8, marginBottom: 6, background: "var(--code-bg)", border: "1px solid var(--border)", borderLeft: "3px solid var(--accent)" }}>
                    <div style={{ fontSize: 12, color: "var(--text-h)", lineHeight: 1.4 }}>🧵 {t}</div>
                  </div>
                );
              }
              const partialWeight = (t.partial_clues?.length || 0) * 0.5;
              const pct = Math.min(100, Math.round((((t.discovered_clues?.length || 0) + partialWeight) / Math.max(t.minimum_clues_to_deduce || 1, 1)) * 100));
              const ready = t.status === "ready_to_deduce";
              return (
                <div key={t.id || i} style={{
                  padding: "9px 10px", borderRadius: 8, marginBottom: 8,
                  background: ready ? "rgba(96,165,250,0.10)" : "var(--code-bg)",
                  border: `1px solid ${ready ? "rgba(96,165,250,0.45)" : "var(--border)"}`,
                  borderLeft: `3px solid ${ready ? "#60a5fa" : "var(--accent)"}`,
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 4 }}>
                    <div style={{ fontSize: 12, fontWeight: 800, color: "var(--text-h)", lineHeight: 1.35 }}>{t.question}</div>
                    <span style={{ fontSize: 9, color: ready ? "#60a5fa" : "var(--text)", textTransform: "uppercase", flexShrink: 0 }}>
                      {ready ? "PRONTA" : t.status}
                    </span>
                  </div>
                  {t.payoff && <div style={{ fontSize: 11, color: "var(--text)", opacity: 0.75, lineHeight: 1.35, marginBottom: 6 }}>{t.payoff}</div>}
                  {t.required_details?.length > 0 && (
                    <div style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 7 }}>
                      {t.required_details.map(({ id, clue, found, progress }) => {
                        const partial = !found && (progress?.ticks || 0) > 0;
                        const label = clue?.label || clue?.text || id;
                        return (
                          <div key={id} style={{
                            padding: "5px 7px", borderRadius: 6,
                            background: found ? "rgba(74,222,128,0.08)" : partial ? "rgba(96,165,250,0.08)" : "rgba(255,255,255,0.035)",
                            border: `1px solid ${found ? "rgba(74,222,128,0.24)" : partial ? "rgba(96,165,250,0.25)" : "rgba(255,255,255,0.06)"}`,
                          }}>
                            <div style={{ fontSize: 10, color: found ? "#4ade80" : partial ? "#93c5fd" : "var(--text)", lineHeight: 1.35 }}>
                              {found ? "✓" : partial ? "◔" : "□"} {label}
                            </div>
                            {clue?.location && (
                              <div style={{ fontSize: 9, color: "var(--text)", opacity: 0.5, marginTop: 1 }}>
                                dove: {clue.location}
                              </div>
                            )}
                            {partial && progress?.note && (
                              <div style={{ fontSize: 9, color: "#93c5fd", opacity: 0.85, marginTop: 1 }}>
                                progresso: {progress.note}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                  <div style={{ height: 5, borderRadius: 5, background: "rgba(255,255,255,0.08)", overflow: "hidden", marginBottom: 5 }}>
                    <div style={{ height: "100%", width: `${pct}%`, background: ready ? "#60a5fa" : "var(--accent)" }} />
                  </div>
                  <div style={{ fontSize: 10, color: "var(--text)", opacity: 0.55 }}>
                    {(t.discovered_clues?.length || 0)} ottenuti
                    {(t.partial_clues?.length || 0) > 0 ? `, ${t.partial_clues.length} in progresso` : ""} / {t.minimum_clues_to_deduce || 1} per dedurre
                  </div>
                  {ready && (
                    <button
                      onClick={() => onDeduce && onDeduce(t.id, t.question)}
                      style={{ marginTop: 7, width: "100%", padding: "6px 0", borderRadius: 7, border: "1px solid rgba(96,165,250,0.5)", background: "rgba(96,165,250,0.15)", color: "#93c5fd", fontSize: 11, fontWeight: 700, cursor: "pointer" }}
                    >
                      ⚡ Fai la deduzione
                    </button>
                  )}
                </div>
              );
            })}
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

// ─── HexCombatMap ──────────────────────────────────────────────────────────
// Griglia esagonale SVG flat-top, 1 hex = 1 yard GURPS Lite.
// Terreni: 0=normale 1=copertura 2=difficile 3=muro
// Facing: 0-5 (direzioni hex, 0=nord)

const HEX_SIZE = 36; // raggio hex: pochi esagoni, ben leggibili sul tavolo tattico
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
  if (/corridoio|tunnel|passaggio|ponte|galleria|stretta|vicolo/.test(text)) return { cols: 12, rows: 6, layout: "narrow" };
  if (/foresta|radura|campo|piazza|hangar|sala grande|cortile|rovine|esterno|aperto|battlefield/.test(text) || enemyCount >= 4) return { cols: 12, rows: 8, layout: "open" };
  if (/stanza|cella|cripta|sacrario|biblioteca|oratorio|sala|laboratorio|ponte di comando/.test(text)) return { cols: 10, rows: 7, layout: "room" };
  return { cols: 10, rows: 7, layout: "room" };
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

function buildBattleMapSpec({ genre, environmentType, sceneText, locationName, enemyNames, tacticalMap }) {
  const tacticalText = tacticalMap?.enabled
    ? battleText(tacticalMap.role, tacticalMap.layout, ...(tacticalMap.features || []), ...(tacticalMap.hazards || []), tacticalMap.trigger)
    : "";
  const text = battleText(genre, environmentType, sceneText, locationName, tacticalText, ...(enemyNames || []));
  const theme = battleThemeFor(genre, text);
  const inferredSize = battleSizeFor(text, (enemyNames || []).length);
  const size = tacticalMap?.enabled
    ? {
        cols: Math.max(8, Math.min(14, Number(tacticalMap.cols) || inferredSize.cols)),
        rows: Math.max(6, Math.min(10, Number(tacticalMap.rows) || inferredSize.rows)),
        layout: tacticalMap.layout || inferredSize.layout,
      }
    : inferredSize;
  const terrain = buildBattleMapTerrain(size.cols, size.rows, size.layout, text);
  const labelBits = [theme.label];
  if (tacticalMap?.enabled) labelBits.push(tacticalMap.role === "finale" ? "finale" : "zona calda");
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
  const used = new Set();
  const place = (preferredCol, preferredRow) => {
    const candidates = [];
    for (let dc = 0; dc <= 2; dc++) {
      for (let dr = 0; dr < rows; dr++) {
        const rowUp = preferredRow - dr;
        const rowDown = preferredRow + dr;
        const colsToTry = dc === 0 ? [preferredCol] : [preferredCol + dc, preferredCol - dc];
        for (const c of colsToTry) {
          if (rowUp >= 1) candidates.push({ col: c, row: rowUp });
          if (dr > 0 && rowDown <= rows - 2) candidates.push({ col: c, row: rowDown });
        }
      }
    }
    const found = candidates.find(p =>
      p.col >= 1 && p.col <= cols - 2 && p.row >= 1 && p.row <= rows - 2 && !used.has(`${p.col},${p.row}`)
    ) || { col: Math.max(1, Math.min(cols - 2, preferredCol)), row: Math.max(1, Math.min(rows - 2, preferredRow)) };
    used.add(`${found.col},${found.row}`);
    return found;
  };
  const spacedRow = (i, total) => {
    if (total <= 1) return Math.floor(rows / 2);
    const span = Math.max(1, rows - 3);
    return 1 + Math.round((i + 1) * span / (total + 1));
  };
  players.forEach((p, i) => {
    const pos = place(2, spacedRow(i, players.length));
    positions[`p_${p.id}`] = { ...pos, facing: 0, type: "player", id: p.id };
  });
  enemies.forEach((e, i) => {
    const pos = place(Math.max(3, cols - 4), spacedRow(i, enemies.length));
    positions[`e_${e.id}`] = { ...pos, facing: 3, type: "enemy", id: e.id };
  });
  return positions;
}

function CombatMap({ players, sceneEntities, activePlayerId, pendingAttack, onAttack, onDefend, onStandUp, onNextPlayer, onFinishTurn, onRetreat, avatars, npcAvatars, bgImage, lastCombatLog, onClose, genre, environmentType, sceneText, locationName, tacticalMap, lootPool: lootPoolProp }) {
  const entities = sceneEntities || [];
  const enemies = entities.filter(e => e.type === "enemy");
  // La mappa non cambia dimensione durante il combattimento — dipendenze stabili
  const mapSpec = useMemo(() => buildBattleMapSpec({
    genre,
    environmentType,
    sceneText,
    locationName,
    enemyNames: enemies.map(e => e.name),
    tacticalMap,
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [genre, environmentType, sceneText, locationName]);
  const mapCols = mapSpec.cols;
  const mapRows = mapSpec.rows;
  // Colori hex adattivi: quando c'è un'immagine di sfondo, riduciamo l'opacità dei fill
  // così l'immagine domina visivamente e il disallineamento spaziale si nota meno.
  // I muri (tipo 3) restano semi-trasparenti ma non coprono l'immagine al 88%.
  const _baseColors = mapSpec.theme?.terrainColors || DEFAULT_TERRAIN_COLORS;
  const _baseStroke = mapSpec.theme?.terrainStroke || DEFAULT_TERRAIN_STROKE;
  const terrainColors = bgImage ? {
    0: "rgba(0,0,0,0)",           // aperto → completamente trasparente (immagine mostra tutto)
    1: "rgba(200,160,80,0.18)",   // copertura → tinta dorata leggera
    2: "rgba(160,80,60,0.20)",    // difficile → tinta rossa leggera
    3: "rgba(0,0,0,0.52)",        // muro → grigio scuro al 52% (era 88% — ora si vede l'immagine sotto)
  } : _baseColors;
  const terrainStroke = bgImage ? {
    0: "rgba(255,255,255,0.12)",  // bordo hex appena visibile sull'immagine
    1: "rgba(251,191,36,0.55)",   // copertura → bordo dorato visibile
    2: "rgba(239,100,80,0.50)",   // difficile → bordo rosso-arancio
    3: "rgba(80,80,100,0.70)",    // muro → bordo grigio-blu visibile
  } : _baseStroke;

  const [terrain, setTerrain] = useState(() => mapSpec.terrain);
  const [positions, setPositions] = useState(() => buildInitialPositions(players, enemies, mapCols, mapRows));
  const [selected, setSelected] = useState(null);       // key "p_X" o "e_X"
  const [mode, setMode] = useState("select");           // select|move|attack
  const [attackActionType, setAttackActionType] = useState("normal"); // "normal"|"all_out_attack"
  const [reachable, setReachable] = useState(new Set());
  const [combatLog, setCombatLog] = useState(["─── Round 1 — Turno giocatori ───"]);
  const [actedThisRound, setActedThisRound] = useState(new Set()); // player id già agiti
  // geometria ultimo attacco — mandati al backend con la difesa
  const [lastAttackCoverBonus, setLastAttackCoverBonus] = useState(0);
  const [lastAttackIsRear, setLastAttackIsRear] = useState(false);
  // arma a distanza selezionata e mira accumulata
  const [selectedWeaponId, setSelectedWeaponId] = useState(""); // weapon_id dell'azione selezionata
  const [aimedTurns, setAimedTurns] = useState(0);             // turni di mira accumulati (locale, UI)
  // Bottino disponibile nella scena corrente
  const [lootPool, setLootPool] = useState([]);                 // LootEntry[] (locale, aggiornato da prop)
  const effectiveLootPool = (lootPoolProp && lootPoolProp.length > 0) ? lootPoolProp : lootPool;
  // ── Manovre GURPS ────────────────────────────────────────────────────────────
  const [selectedManeuver, setSelectedManeuver] = useState(null); // manovra corrente in attesa
  const [showPostureMenu, setShowPostureMenu] = useState(false);
  const [roundCounter, setRoundCounter] = useState(1);
  const [moveAttackMode, setMoveAttackMode] = useState(false);    // true = mossa già usata per Move+Attack
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

  // Sincronizza loot pool dal parent quando cambia
  useEffect(() => {
    if (lootPoolProp && lootPoolProp.length > 0) setLootPool(lootPoolProp);
  }, [lootPoolProp]);

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
      const occupied = new Set(Object.values(next).map(p => `${p.col},${p.row}`));
      const findFree = (preferredCol, preferredRow) => {
        for (let dc = 0; dc <= 2; dc++) {
          for (let dr = 0; dr < rows; dr++) {
            const rowOptions = dr === 0 ? [preferredRow] : [preferredRow - dr, preferredRow + dr];
            const colOptions = dc === 0 ? [preferredCol] : [preferredCol + dc, preferredCol - dc];
            for (const c of colOptions) {
              for (const r of rowOptions) {
                const key = `${c},${r}`;
                if (c >= 1 && c <= cols - 2 && r >= 1 && r <= rows - 2 && !occupied.has(key)) {
                  occupied.add(key);
                  return { col: c, row: r };
                }
              }
            }
          }
        }
        return { col: Math.max(1, Math.min(cols - 2, preferredCol)), row: Math.max(1, Math.min(rows - 2, preferredRow)) };
      };
      const spacedRow = (i, total) => total <= 1
        ? Math.floor(rows / 2)
        : 1 + Math.round((i + 1) * Math.max(1, rows - 3) / (total + 1));
      players.forEach((p, i) => {
        const key = `p_${p.id}`;
        wanted.add(key);
        if (!next[key]) {
          next[key] = { ...findFree(2, spacedRow(i, players.length)), facing: 0, type: "player", id: p.id };
        }
      });
      enemies.forEach((e, i) => {
        const key = `e_${e.id}`;
        wanted.add(key);
        if (!next[key]) {
          next[key] = { ...findFree(Math.max(3, cols - 4), spacedRow(i, enemies.length)), facing: 3, type: "enemy", id: e.id };
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
    if (!lastCombatLog) return;

    // ── Movimento NPC (tattica) ───────────────────────────────────────────────
    const move = lastCombatLog?.tactical_move;
    if (move?.entity_id && move.to) {
      const enemyKey = `e_${move.entity_id}`;
      setAnimating(a => ({ ...a, [enemyKey]: "move" }));
      setTimeout(() => setAnimating(a => { const n = { ...a }; delete n[enemyKey]; return n; }), 260);
      setPositions(prev => ({ ...prev, [enemyKey]: { ...(prev[enemyKey] || {}), ...move.to } }));
    }

    // ── Mostra risultato dell'attacco nel log (solo turno giocatore, non NPC) ──
    const r = lastCombatLog?.result;
    if (r && lastCombatLog.attacker && !lastCombatLog.is_npc_turn) {
      const roll     = lastCombatLog.attack_roll ?? "?";
      const skill    = lastCombatLog.skill_level ?? "?";
      const dmgForm  = lastCombatLog.damage_formula || "";
      const hitIcon  = r.hit  ? "✅" : "❌";
      const hitTxt   = r.hit  ? "COLPO" : "MANCATO";
      const defTxt   = r.defended ? " → parato/schivato" : "";
      let dmgTxt = "";
      if (r.hit && !r.defended && r.raw_damage !== undefined) {
        dmgTxt = ` | ${dmgForm}=${r.raw_damage}`;
        if (r.dr_absorbed > 0) dmgTxt += `−${r.dr_absorbed}DR`;
        dmgTxt += `=${r.net_damage}PF`;
      }
      const woundMap = { ferita_lieve:"Lieve", ferita_seria:"Seria", ferita_grave:"Grave!", ferita_critica:"CRITICA!!" };
      const woundTxt = r.wound_threshold && r.net_damage > 0 ? ` [${woundMap[r.wound_threshold] || r.wound_threshold}]` : "";
      const shockTxt = r.shock_applied > 0 ? ` Shock−${r.shock_applied}` : "";
      const stunTxt  = r.target_stunned ? " 💫STORDITO" : "";
      const proneTxt = r.knockdown ? " ⬇ABBATTUTO" : "";
      const critTxt  = r.attacker_critical ? " ✨CRITICO" : "";
      const logLine  = `${hitIcon} 3d6=${roll} vs ${skill} → ${hitTxt}${critTxt}${defTxt}${dmgTxt}${woundTxt}${shockTxt}${stunTxt}${proneTxt}`;
      setCombatLog(prev => [...prev, logLine]);
    }

    // ── Narrazione ricevuta da NPC turn o risultato ───────────────────────────
    if (lastCombatLog?.narration) {
      setCombatLog(prev => [...prev, `💬 ${lastCombatLog.narration}`]);
    }
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

    // ── Aggiorna posizioni NPC sulla mappa ────────────────────────────────────
    if (res.positions && Object.keys(res.positions).length > 0) {
      setPositions(prev => ({ ...prev, ...res.positions }));
    }

    // ── Mostra azioni NPC nel log combattimento ───────────────────────────────
    const npcLogs = res.npc_logs || [];
    if (npcLogs.length === 0) {
      // Nessuna azione NPC (tutti morti o fuori combattimento)
      return;
    }
    for (const log of npcLogs) {
      if (log.tactical_move) {
        const m = log.tactical_move;
        const stepsTxt = m.steps > 1 ? ` ×${m.steps} hex` : "";
        const distTxt = m.distance_after !== undefined ? ` → dist. ${m.distance_after}` : "";
        const stillFar = m.distance_after > 1 ? " (fuori portata)" : " (in portata!)";
        // Anima il token NPC sulla mappa
        const enemyKey = `e_${m.entity_id}`;
        setAnimating(a => ({ ...a, [enemyKey]: "move" }));
        setTimeout(() => setAnimating(a => { const n = { ...a }; delete n[enemyKey]; return n; }), 280);
        if (m.to) setPositions(prev => ({ ...prev, [enemyKey]: { ...(prev[enemyKey] || {}), ...m.to } }));
        setCombatLog(prev => [...prev, `👣 ${log.attacker} si avvicina${stepsTxt}${distTxt}${stillFar}`]);
      } else if (log.attacker && log.result) {
        const r = log.result;
        // Se è un attacco NPC al giocatore (pending_attack verrà gestito separatamente)
        const hint = r.narrative_hint || "";
        if (hint === "npc_si_avvicina") continue;
        const roll = log.attack_roll ?? "?";
        const skill = log.skill_level ?? "?";
        const hitIcon = r.hit ? "⚠️" : "🛡";
        const hitTxt  = r.hit ? "COLPO!" : "mancato";
        const defTxt  = r.defended ? " (parato/schivato)" : "";
        let dmgTxt = "";
        if (r.hit && !r.defended && r.net_damage > 0) {
          dmgTxt = ` → ${r.raw_damage}−${r.dr_absorbed}DR=${r.net_damage}PF`;
        }
        const woundMap = { ferita_lieve:"Lieve", ferita_seria:"Seria", ferita_grave:"GRAVE!", ferita_critica:"CRITICA!!" };
        const woundTxt = r.wound_threshold && r.net_damage > 0 ? ` [${woundMap[r.wound_threshold]||r.wound_threshold}]` : "";
        const shockTxt = r.shock_applied > 0 ? ` Shock−${r.shock_applied}` : "";
        const stunTxt  = r.target_stunned ? " 💫STORDITO" : "";
        setCombatLog(prev => [...prev,
          `${hitIcon} ${log.attacker}→${log.target}: 3d6=${roll} vs ${skill} → ${hitTxt}${defTxt}${dmgTxt}${woundTxt}${shockTxt}${stunTxt}`
        ]);
      }
    }

    // ── Annuncia inizio turno giocatori ──────────────────────────────────────
    setCombatLog(prev => [...prev, "─── Turno giocatori ───"]);
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
    const roundEnded = remaining.length === 0;
    if (remaining.length === 0) {
      setActedThisRound(new Set());
      setRoundCounter(r => r + 1);
      if (onNextPlayer) onNextPlayer(alivePlayers[0]?.id);
      // Separatore fine round
      setCombatLog(prev => [...prev, `━━━ Fine Round ${roundCounter} — Turno NPC... ━━━`]);
    } else {
      setActedThisRound(newActed);
      if (onNextPlayer) onNextPlayer(remaining[0].id);
      // Indica il prossimo giocatore
      const nextName = remaining[0]?.name || "?";
      if (remaining.length < alivePlayers.length) {
        setCombatLog(prev => [...prev, `▶ Turno di ${nextName}`]);
      }
    }
    setSelected(null);
    setMode("select");
    setReachable(new Set());
    // I PNG agiscono una sola volta a fine round giocatori.
    if (roundEnded && runNpc && onFinishTurn) {
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
      const movedName = selected.startsWith("p_")
        ? players.find(x => x.id === parseInt(selected.replace("p_","")))?.name || selected
        : selected;
      if (moveAttackMode) {
        // Muovi+Attacca: dopo il movimento → passa direttamente alla fase attacco (−4 al tiro)
        setPositions(nextPositions);
        setMoveAttackMode(false);
        setAttackActionType("move_attack");
        setMode("attack");
        setReachable(new Set());
        setCombatLog(prev => [...prev, `🏃 ${movedName} si sposta (${col},${row}) — ora attacca! (−4 al tiro)`]);
        return;
      }
      setCombatLog(prev => [...prev, `👣 ${movedName} si sposta (${col},${row})`]);
      // movimento normale: fine turno
      const movedPid = selected.startsWith("p_") ? parseInt(selected.replace("p_", "")) : null;
      advanceTurn(movedPid, true, nextPositions);
      return;
    }

    if (mode === "evaluate" && canControlToken()) {
      // Click su un nemico → valuta quel bersaglio
      if (tokenOnHex && tokenOnHex[0].startsWith("e_")) {
        const targetId = tokenOnHex[0].replace("e_", "");
        const targetName = entities.find(e => e.id === targetId)?.name || targetId;
        const pid = selected?.startsWith("p_") ? parseInt(selected.replace("p_","")) : null;
        const selPlayer = pid ? players.find(p => p.id === pid) : null;
        if (selPlayer) {
          const res = await fetch(`${API_URL}/game/combat/maneuver`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ player_id: selPlayer.id, maneuver: "evaluate", evaluate_target: targetId }),
          }).then(r => r.json());
          if (res.error) { setCombatLog(prev => [...prev, `Errore valuta: ${res.error}`]); }
          else {
            const evalBonus2 = players.find(p => p.id === selPlayer.id)?.evaluate_bonus || 0;
            setCombatLog(prev => [...prev, res.log || `🔍 ${selPlayer.name} valuta ${targetName} (+${evalBonus2 + 1}/3)`]);
            advanceTurn(pid, true);
          }
        }
      } else {
        setCombatLog(prev => [...prev, "🔍 Clicca su un nemico per valutarlo."]);
      }
      setMode("select");
      setSelectedManeuver(null);
      return;
    }

    if (mode === "attack" && canControlToken()) {
      if (tokenOnHex && tokenOnHex[0] !== selected && tokenOnHex[0].startsWith("e_")) {
        const targetKey = tokenOnHex[0];
        const selPos = positions[selected];
        const tgtPos = positions[targetKey];
        if (!selPos || !tgtPos) { setMode("select"); return; }
        const dist = hexDist(selPos.col, selPos.row, tgtPos.col, tgtPos.row);

        // Identifica arma selezionata e tipo
        const pid = parseInt(selected.replace("p_", ""));
        const p = players.find(x => x.id === pid);
        if (!p) { setMode("select"); return; }
        const acts = p.actions || [];
        const weaponAction = selectedWeaponId
          ? acts.find(a => a.weapon_id === selectedWeaponId)
          : acts[0];
        const isRangedWeapon = weaponAction?.attack_kind === "ranged";
        const ammoCur = weaponAction?.ammo_current ?? weaponAction?.ammo ?? 0;
        const ammoMax = weaponAction?.ammo ?? 0;
        const noAmmo = isRangedWeapon && ammoMax > 0 && ammoCur <= 0;

        // Portata: mischia max 1 hex, distanza max range_half (default 10)
        const maxRange = isRangedWeapon ? (weaponAction?.range_half || 10) : 1;
        const isMelee = dist <= 1;
        const inRange = dist <= maxRange;

        if (noAmmo) {
          setCombatLog(prev => [...prev, `⚠ ${weaponAction?.name || "Arma"} scarica — ricarica prima di sparare!`]);
        } else if (!inRange) {
          setCombatLog(prev => [...prev,
            isRangedWeapon
              ? `🎯 Fuori portata! (dist ${dist}, max ${maxRange} hex per ${weaponAction?.name})`
              : `⚔ Troppo lontano per la mischia! (dist ${dist}, max 1 hex)`
          ]);
        } else {
          // ── Calcoli contestuali ───────────────────────────────────────────
          const isRangedAttack = isRangedWeapon && dist > 1;
          const rangePenalty = isRangedAttack ? -(dist - 1) : 0;

          // Attacco da retro: solo in mischia, controlla se l'attaccante è dietro il facing del bersaglio
          const tgtFacing = tgtPos.facing || 0;
          const dx = selPos.col - tgtPos.col;
          const dy = selPos.row - tgtPos.row;
          const attackAngle = Math.round(Math.atan2(dy, dx) / (Math.PI / 3) + 6) % 6;
          const rearHexes = [(tgtFacing + 3) % 6, (tgtFacing + 4) % 6, (tgtFacing + 2) % 6];
          const isRearAttack = isMelee && rearHexes.includes(attackAngle);

          // Copertura: bonus +2 difesa se il bersaglio è su hex copertura
          const tgtTerrain = terrain[`${tgtPos.col},${tgtPos.row}`] || 0;
          const coverBonus = tgtTerrain === 1 ? 2 : 0;

          // Salva geometria per la fase di difesa
          setLastAttackCoverBonus(coverBonus);
          setLastAttackIsRear(isRearAttack);

          // Animazione
          setAnimating(prev => ({ ...prev, [selected]: "attack" }));
          setTimeout(() => setAnimating(prev => { const n = {...prev}; delete n[selected]; return n; }), 400);

          const actionName = weaponAction?.name || "combattere";
          const weaponLabel = weaponAction?.name || "combattere";
          const atkTypeTag = attackActionType === "all_out_attack" ? " ⚔⚔" : attackActionType === "move_attack" ? " 🏃(−4)" : "";
          const atkKindTag = isRangedAttack ? "🎯" : "⚔";
          const targetEntity = enemies.find(en => en.id === targetKey.replace("e_",""));
          const penTxt = rangePenalty ? ` pen.${rangePenalty}` : "";
          const rearTxt = isRearAttack ? " 🗡RETRO" : "";
          const coverTxt = coverBonus ? ` 🛡cop.+${coverBonus}` : "";

          // Header nel log prima di aspettare la risposta
          setCombatLog(prev => [...prev,
            `${atkKindTag}${atkTypeTag} ${p.name}→${targetEntity?.name||"?"}  [${weaponLabel}]  dist:${dist}${penTxt}${rearTxt}${coverTxt}`
          ]);
          await onAttack(p, actionName, targetKey.replace("e_", ""), attackActionType, tacticalSnapshot(), dist);
          setAttackActionType("normal");
          setAimedTurns(0);
          advanceTurn(pid, true);
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

  async function handleAim(player, weaponName) {
    try {
      const res = await fetch(`${API_URL}/game/combat/aim`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ attacker_id: player.id, action_name: weaponName }),
      }).then(r => r.json());
      if (res.error) {
        setCombatLog(prev => [...prev, `Errore mira: ${res.error}`]);
        return;
      }
      const newAimed = (aimedTurns + 1);
      setAimedTurns(newAimed);
      setCombatLog(prev => [...prev, res.log || `${player.name} mira... (bonus +${newAimed})`]);
      advanceTurn(player.id, true);
    } catch (_) {}
  }

  // ── Gestione manovre GURPS ───────────────────────────────────────────────
  async function handleManeuver(maneuver, extraData = {}) {
    const pid = selected?.startsWith("p_") ? parseInt(selected.replace("p_","")) : null;
    const selPlayer = pid ? players.find(p => p.id === pid) : null;
    if (!selPlayer || !canControlToken()) return;

    setShowPostureMenu(false);

    // Manovre che entrano in modalità (richiedono click su bersaglio/hex)
    if (maneuver === "attack") {
      setAttackActionType("normal"); setSelectedManeuver("attack");
      setMoveAttackMode(false); startAttack(); return;
    }
    if (maneuver === "all_out_attack") {
      setAttackActionType("all_out_attack"); setSelectedManeuver("all_out_attack");
      setMoveAttackMode(false); startAttack(); return;
    }
    if (maneuver === "move_attack") {
      setAttackActionType("normal"); setSelectedManeuver("move_attack");
      setMoveAttackMode(true); startMove(); return; // prima muovi, poi attacca
    }
    if (maneuver === "move") {
      setSelectedManeuver("move"); setMoveAttackMode(false); startMove(); return;
    }
    if (maneuver === "evaluate") {
      // Entra in modalità "scegli bersaglio" — l'utente clicca su un nemico
      setSelectedManeuver("evaluate");
      setMode("evaluate");
      return;
    }
    if (maneuver === "aim") {
      const actions = selPlayer.actions || [];
      const rangedActions = actions.filter(a => a.attack_kind === "ranged");
      const weaponName = selectedWeaponId
        ? (actions.find(a => a.weapon_id === selectedWeaponId)?.name || rangedActions[0]?.name || "")
        : (rangedActions[0]?.name || "");
      if (!weaponName) { setCombatLog(prev => [...prev, "Nessuna arma a distanza pronta."]); return; }
      await handleAim(selPlayer, weaponName);
      setSelectedManeuver(null); return;
    }
    if (maneuver === "retreat") {
      if (onRetreat) onRetreat(tacticalSnapshot());
      setSelectedManeuver(null); return;
    }
    if (maneuver === "standup") {
      if (onStandUp) onStandUp(selPlayer.id);
      setSelectedManeuver(null);
      setCombatLog(prev => [...prev, `🧍 ${selPlayer.name} si alza da terra.`]);
      advanceTurn(pid, true); return;
    }

    // Manovre istantanee → chiama backend
    const res = await fetch(`${API_URL}/game/combat/maneuver`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player_id: selPlayer.id, maneuver, ...extraData }),
    }).then(r => r.json());

    if (res.error) { setCombatLog(prev => [...prev, `Errore: ${res.error}`]); return; }
    if (res.log) setCombatLog(prev => [...prev, res.log]);
    setSelectedManeuver(null);

    // all_out_defense: il giocatore non può attaccare MA il turno avanza e gli NPC agiscono
    advanceTurn(pid, true);
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
  const isFinalBattle = /final|boss|culmine|conclus/i.test(`${tacticalMap?.role || ""} ${tacticalMap?.purpose || ""} ${mapSpec.title || ""}`);
  const canRetreat = !isFinalBattle && !pendingAttack;

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
                width: Math.min(svgWidth + 24, window.innerWidth - 24),
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
                          style={{ width: 24, height: 24, borderRadius: "50%", objectFit: "cover", flexShrink: 0 }} />
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

        <div className="hex-map-content" style={{ overflowX: "auto", overflowY: "auto", maxHeight: "72vh" }}>
          {/* legenda terreni */}
          <div style={{ display: "flex", gap: 12, padding: "6px 14px", fontSize: 10, color: "rgba(255,255,255,0.4)", borderBottom: "1px solid rgba(255,255,255,0.06)", flexWrap: "wrap" }}>
            <span>⬡ Normale</span>
            <span style={{ color: "#fbbf24" }}>⬡ Copertura (+2 difesa)</span>
            <span style={{ color: "#f87171" }}>⬡ Difficile (×2 mov)</span>
            <span style={{ color: "#94a3b8" }}>⬡ Muro</span>
            {bgImage && (
              <span style={{ color: "rgba(255,255,255,0.25)", marginLeft: "auto", fontStyle: "italic" }}>
                🎨 immagine = atmosfera · griglia = meccanica
              </span>
            )}
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
                    objectFit: "cover", opacity: 0.65, pointerEvents: "none",
                  }}
                  onError={e => { e.currentTarget.src = `data:image/png;base64,${bgImage}`; }}
                />
                <div style={{
                  position: "absolute", inset: 0,
                  background: "rgba(8,8,16,0.22)", pointerEvents: "none",
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

              const isAOD = entity.all_out_defense_active;
              const evalBonus = entity.evaluate_bonus || 0;
              const posture = entity.posture || (entity.prone ? "prone" : "standing");
              const ringColor = isDead ? "#555" : isPlayer ? "#a855f7" : (entity.type === "ally" ? "#22c55e" : "#ef4444");

              return (
                <g key={key} style={{ cursor: "pointer", ...animStyle }} onClick={e => { e.stopPropagation(); clickHex(pos.col, pos.row); }}>
                  <defs>
                    <clipPath id={clipId}>
                      <circle cx={x} cy={y} r={r} />
                    </clipPath>
                  </defs>
                  {/* anello colorato di ruolo (sempre visibile anche con avatar) */}
                  <circle cx={x} cy={y} r={r + 2}
                    fill="none"
                    stroke={isSelected ? "#fff" : anim === "attack" ? "#facc15" : ringColor}
                    strokeWidth={isSelected ? 3.5 : 2.5}
                    opacity={isDead ? 0.3 : 1}
                  />
                  {/* cerchio sfondo token */}
                  <circle cx={x} cy={y} r={r}
                    fill={tokenImg ? "rgba(0,0,0,0.6)" : ringColor}
                    fillOpacity={isDead ? 0.3 : (tokenImg ? 0.7 : 0.85)}
                  />
                  {/* avatar circolare */}
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
                      fontSize={14} fontWeight="bold" fill="#fff" style={{ pointerEvents: "none" }}>
                      {isDead ? "💀" : label}
                    </text>
                  )}
                  {/* facing triangle */}
                  <path d={facingTriangle(x, y, pos.facing || 0, r, "#fff")}
                    fill="rgba(255,255,255,0.75)" style={{ pointerEvents: "none" }} />

                  {/* ── Badge status (angoli del token) ── */}
                  {/* Alto-sinistra: stordito / a terra / in ginocchio */}
                  {entity.stunned
                    ? <text x={x - r + 2} y={y - r + 10} fontSize={11} fill="#facc15" title="Stordito 💫">💫</text>
                    : posture === "prone"
                      ? <text x={x - r + 2} y={y - r + 10} fontSize={11} fill="#f97316" title="A terra">⬇</text>
                      : posture === "kneeling"
                        ? <text x={x - r + 2} y={y - r + 10} fontSize={10} fill="#fbbf24" title="In ginocchio">🧎</text>
                        : null
                  }
                  {/* Alto-destra: copertura / difesa totale */}
                  {isAOD
                    ? <text x={x + r - 12} y={y - r + 10} fontSize={10} fill="#34d399" title="Difesa Totale (+2)">🛡</text>
                    : inCover
                      ? <text x={x + r - 12} y={y - r + 10} fontSize={10} fill="#4ade80" title="In copertura">🛡</text>
                      : null
                  }
                  {/* Alto-centro: Valuta bonus */}
                  {evalBonus > 0 && (
                    <text x={x} y={y - r - 2} fontSize={9} fontWeight="bold" textAnchor="middle"
                      fill="#c4b5fd" title={`Bonus Valuta +${evalBonus}/3`}>🔍+{evalBonus}</text>
                  )}
                  {/* Basso-destra: shock */}
                  {entity.shock_penalty > 0 && (
                    <text x={x + r - 8} y={y + r - 2} fontSize={9} fill="#f59e0b"
                      title={`Shock −${entity.shock_penalty} al prossimo tiro`}>⚡−{entity.shock_penalty}</text>
                  )}
                  {/* Mirate */}
                  {entity.aimed && entity.aimed_turns > 0 && (
                    <text x={x - r + 2} y={y + r - 2} fontSize={9} fill="#fbbf24"
                      title={`Mira: +${entity.aimed_turns} acc.`}>🎯+{entity.aimed_turns}</text>
                  )}

                  {/* ── Indicatore attacco da retro ── */}
                  {/* Visibile in modalità attacco quando il player selezionato è dietro questo nemico */}
                  {!isPlayer && mode === "attack" && (() => {
                    const selPos2 = selected ? positions[selected] : null;
                    if (!selPos2 || !pos) return null;
                    const dist2 = hexDist(selPos2.col, selPos2.row, pos.col, pos.row);
                    if (dist2 > 1) return null; // solo mischia
                    const tgtFacing2 = pos.facing || 0;
                    const dx2 = selPos2.col - pos.col;
                    const dy2 = selPos2.row - pos.row;
                    const attackAngle2 = Math.round(Math.atan2(dy2, dx2) / (Math.PI / 3) + 6) % 6;
                    const rearHexes2 = [(tgtFacing2 + 3) % 6, (tgtFacing2 + 4) % 6, (tgtFacing2 + 2) % 6];
                    const isRear2 = rearHexes2.includes(attackAngle2);
                    if (!isRear2) return null;
                    return (
                      <text x={x} y={y + r + 14} fontSize={8} fontWeight="bold" textAnchor="middle"
                        fill="#facc15" title="Attacco da retro: la difesa attiva del nemico è ignorata!">🗡RETRO</text>
                    );
                  })()}

                  {/* ── Barre HP + FP ── */}
                  {entity.max_hp > 0 && (() => {
                    const hpPct = Math.max(0, entity.hp / entity.max_hp);
                    const fpPct = entity.max_fp > 0 ? Math.max(0, (entity.fp ?? entity.max_fp) / entity.max_fp) : -1;
                    const barY = y + r + 3;
                    return <>
                      {/* HP bar */}
                      <rect x={x - 15} y={barY} width={30} height={3.5} rx={1.5} fill="rgba(0,0,0,0.5)" />
                      <rect x={x - 15} y={barY} width={30 * hpPct} height={3.5} rx={1.5}
                        fill={hpPct > 0.5 ? "#4ade80" : hpPct > 0.25 ? "#facc15" : "#ef4444"} />
                      {/* FP bar (solo se tracciato) */}
                      {fpPct >= 0 && (
                        <>
                          <rect x={x - 15} y={barY + 5} width={30} height={2.5} rx={1} fill="rgba(0,0,0,0.4)" />
                          <rect x={x - 15} y={barY + 5} width={30 * fpPct} height={2.5} rx={1}
                            fill={fpPct > 0.5 ? "#60a5fa" : fpPct > 0.25 ? "#a78bfa" : "#f472b6"} />
                        </>
                      )}
                    </>;
                  })()}
                </g>
              );
            })}
          </svg>
          </div>{/* fine div relativo sfondo+svg */}
        </div>{/* fine hex-map-content */}

        {/* ── Pannello manovre GURPS ──────────────────────────────────────── */}
        {(() => {
          const pid2 = selected?.startsWith("p_") ? parseInt(selected.replace("p_","")) : null;
          const selPlayer = pid2 ? players.find(p => p.id === pid2) : null;
          const isStunned = !!selPlayer?.stunned;
          const isProne = !!(selPlayer?.prone || selPlayer?.posture === "prone");
          const hasRanged = (selPlayer?.actions || []).some(a => a.attack_kind === "ranged");
          const evalBonus = selPlayer?.evaluate_bonus || 0;
          const selAcc = (() => {
            if (!selPlayer) return 0;
            const acts = selPlayer.actions || [];
            const selAct = acts.find(a => a.weapon_id === selectedWeaponId) || acts.find(a => a.attack_kind === "ranged");
            return selAct?.acc || 0;
          })();
          const activeName = players.find(p => p.id === activePlayerId)?.name || "?";
          const alivePlayers2 = players.filter(p => p.hp > 0 && p.status !== "sconfitto" && p.status !== "morto");
          const remaining2 = alivePlayers2.filter(p => !actedThisRound.has(p.id));

          const MANEUVERS = [
            { id: "attack",          icon: "⚔",    label: "Attacca",    desc: "1 attacco + muovi ½ Move",           color: "#ef4444", disabled: isStunned },
            { id: "all_out_attack",  icon: "⚔⚔",   label: "Att.Totale", desc: "+4 att. o 2 att. — NESSUNA difesa",  color: "#dc2626", disabled: isStunned },
            { id: "move_attack",     icon: "🏃",    label: "Muovi+Att.", desc: "Muovi tutto + attacco a −4 (min 9)", color: "#f97316", disabled: isStunned || isProne },
            { id: "move",            icon: "👣",    label: "Muovi",      desc: "Muovi fino a Basic Move (no att.)",  color: "#6366f1", disabled: false },
            { id: "all_out_defense", icon: "🛡🛡",  label: "Dif.Totale", desc: "+2 a tutte le difese, no attacco",   color: "#0891b2", disabled: isStunned },
            { id: "evaluate",        icon: "🔍",    label: `Valuta${evalBonus > 0 ? ` +${evalBonus}` : ""}`, desc: `Accumula +1 att. vs stesso bersaglio (max +3). Ora: +${evalBonus}/3`, color: "#7c3aed", disabled: isStunned },
            { id: "aim",             icon: "🎯",    label: `Mira${aimedTurns > 0 ? ` +${aimedTurns}` : ""}`, desc: `Accumula bonus Acc armi distanza (+${aimedTurns}/${selAcc})`,   color: "#b45309", disabled: isStunned || !hasRanged },
            { id: "concentrate",     icon: "🧠",    label: "Concentra",  desc: "Azione mentale o magica",            color: "#6d28d9", disabled: isStunned },
            { id: isProne ? "standup" : "change_posture", icon: isProne ? "🧍" : "🧎", label: isProne ? "Alzati" : "Postura", desc: isProne ? "Alzati da terra — usa tutta l'azione" : "Cambia postura: piedi / ginocchio / terra", color: "#92400e", disabled: false },
            { id: "ready",           icon: "🔄",    label: "Prepara",    desc: "Ricarica o prepara arma/oggetto",    color: "#065f46", disabled: false },
            { id: "do_nothing",      icon: "✋",    label: "Aspetta",    desc: "Non fare nulla questo turno",        color: "#374151", disabled: false },
            { id: "retreat",         icon: "↩",     label: "Ritirata",   desc: "Ripiega — minaccia +1, torna alla scena", color: "#78350f", disabled: !canRetreat },
          ];

          const btnSt = (m) => ({
            display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
            gap: 2, padding: "6px 4px", borderRadius: 8,
            border: `1px solid ${m.disabled ? "rgba(255,255,255,0.05)" : `${m.color}55`}`,
            background: selectedManeuver === m.id
              ? `${m.color}45`
              : m.disabled ? "rgba(255,255,255,0.02)" : `${m.color}18`,
            color: m.disabled ? "rgba(255,255,255,0.2)" : (selectedManeuver === m.id ? "#fff" : m.color),
            cursor: m.disabled ? "not-allowed" : "pointer",
            fontWeight: 700, flex: "1 1 0",
            outline: selectedManeuver === m.id ? `2px solid ${m.color}` : "none",
            transition: "background 0.1s",
          });

          return (
            <div style={{ background: "rgba(8,9,18,0.97)", borderTop: "1px solid rgba(255,255,255,0.08)" }}>

              {/* ── Striscia round + combattenti ──────────────────────────── */}
              <div style={{ padding: "4px 10px", display: "flex", gap: 5, alignItems: "center", flexWrap: "wrap", borderBottom: "1px solid rgba(255,255,255,0.06)", background: "rgba(0,0,0,0.35)" }}>
                <span style={{ fontSize: 10, fontWeight: 800, color: "#6366f1", letterSpacing: 0.5, minWidth: 52 }}>Round {roundCounter}</span>
                <span style={{ fontSize: 10, color: "#a855f7", fontWeight: 700 }}>▶ {activeName}</span>
                <span style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", marginRight: 4 }}>({remaining2.length}/{alivePlayers2.length})</span>
                {alivePlayers2.map(p => {
                  const hpPct = p.max_hp > 0 ? p.hp / p.max_hp : 1;
                  const isActive = p.id === activePlayerId;
                  const hasActed = actedThisRound.has(p.id);
                  return (
                    <div key={p.id}
                      title={`${p.name} — HP: ${p.hp}/${p.max_hp}  FP: ${p.fp ?? p.max_fp}/${p.max_fp}${p.stunned ? " 💫" : p.prone ? " ⬇" : ""}`}
                      style={{ display: "flex", alignItems: "center", gap: 3, padding: "2px 7px", borderRadius: 5,
                        background: isActive ? "rgba(168,85,247,0.2)" : hasActed ? "rgba(255,255,255,0.02)" : "rgba(255,255,255,0.07)",
                        border: `1px solid ${isActive ? "rgba(168,85,247,0.5)" : "rgba(255,255,255,0.08)"}`,
                        opacity: hasActed ? 0.45 : 1 }}>
                      <span style={{ fontSize: 9, color: isActive ? "#c4b5fd" : "rgba(255,255,255,0.55)", fontWeight: isActive ? 700 : 400 }}>{p.name.split(" ")[0]}</span>
                      <span style={{ fontSize: 9, fontWeight: 700, color: hpPct > 0.5 ? "#4ade80" : hpPct > 0.25 ? "#facc15" : "#ef4444" }}>{p.hp}/{p.max_hp}</span>
                      {p.fp !== undefined && p.fp < p.max_fp && <span style={{ fontSize: 8, color: "#60a5fa" }}>FP{p.fp}</span>}
                      {p.stunned && <span>💫</span>}
                      {p.prone && !p.stunned && <span>⬇</span>}
                      {p.all_out_defense_active && <span title="Difesa Totale">🛡</span>}
                    </div>
                  );
                })}
                {enemies.filter(e => e.hp > 0).map(e => (
                  <div key={e.id} title={`${e.name} — HP: ${e.hp}/${e.max_hp} | Difesa: ${e.active_defense} | DR: ${e.dr}`}
                    style={{ display: "flex", alignItems: "center", gap: 3, padding: "2px 7px", borderRadius: 5,
                      background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)" }}>
                    <span style={{ fontSize: 9, color: "#f87171" }}>{e.name.split(" ")[0]}</span>
                    <span style={{ fontSize: 9, fontWeight: 700, color: e.hp/e.max_hp > 0.5 ? "#4ade80" : e.hp/e.max_hp > 0.25 ? "#facc15" : "#ef4444" }}>{e.hp}/{e.max_hp}</span>
                    {e.stunned && <span>💫</span>}
                  </div>
                ))}
              </div>

              {/* ── FASE DIFESA (attacco pendente) ────────────────────────── */}
              {pendingAttack ? (
                <div style={{ padding: "8px 12px", display: "flex", flexDirection: "column", gap: 6 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                    <span style={{ fontSize: 14, fontWeight: 900, color: "#facc15", letterSpacing: 0.5 }}>⚠ DIFENDI!</span>
                    <span style={{ fontSize: 11, color: "rgba(255,255,255,0.55)" }}>
                      {defPlayer?.name} — Schivata {defVal}{lastAttackCoverBonus > 0 ? ` +${lastAttackCoverBonus}` : ""}
                    </span>
                    {lastAttackIsRear && <span style={{ fontWeight: 800, color: "#ef4444", fontSize: 11 }}>⚠ Attacco da RETRO — difesa impossibile!</span>}
                  </div>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    {[
                      { dt: "dodge", label: "🤸 Schiva",  desc: `Schivata ${defVal}${lastAttackCoverBonus > 0 ? `+${lastAttackCoverBonus} cop.` : ""} — usa Velocità/2+3`, bg: "#7c3aed" },
                      { dt: "parry", label: "🗡 Para",    desc: "Parata con arma — skill/2+3 (solo mischia)",  bg: "#2563eb" },
                      { dt: "block", label: "🛡 Blocca",  desc: "Blocco con scudo — skill/2+3",                bg: "#0f766e" },
                    ].map(({ dt, label, desc, bg }) => (
                      <button key={dt} title={desc}
                        onClick={() => Promise.resolve(onDefend(dt, "normal", "", lastAttackCoverBonus, lastAttackIsRear, tacticalSnapshot())).then(applyNpcTurnResult)}
                        style={{ padding: "7px 16px", borderRadius: 8, border: "none", background: bg, color: "#fff", fontWeight: 800, cursor: "pointer", fontSize: 12 }}>
                        {label}
                      </button>
                    ))}
                    <button
                      onClick={() => Promise.resolve(onDefend("dodge", "all_out_defense", "", lastAttackCoverBonus, lastAttackIsRear, tacticalSnapshot())).then(applyNpcTurnResult)}
                      title="Difesa Totale: +2 a tutte le difese. Non puoi attaccare questo turno."
                      style={{ padding: "7px 16px", borderRadius: 8, border: "2px solid #34d399", background: "rgba(52,211,153,0.15)", color: "#34d399", fontWeight: 800, cursor: "pointer", fontSize: 12 }}>
                      🛡🛡 Dif.Totale +2
                    </button>
                  </div>
                  <div style={{ fontSize: 9, color: "rgba(255,255,255,0.3)" }}>
                    Schiva={defVal} | Para=skill/2+3 (solo mischia) | Blocca=scudo/2+3 | Dif.Tot.=+2 a tutto, no attacco questo turno
                  </div>
                </div>

              /* ── MANOVRE (giocatore attivo selezionato) ──────────────── */
              ) : selectedIsActivePlayer && selPlayer ? (
                <div style={{ padding: "7px 10px" }}>
                  {isStunned ? (
                    <div style={{ padding: "8px", textAlign: "center", color: "#facc15", fontSize: 12, fontWeight: 700 }}>
                      💫 {selPlayer.name} è STORDITO — tiro SA per recuperare. Fine turno automatico.
                    </div>
                  ) : (
                    <>
                      {/* Griglia 4×3 manovre GURPS */}
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 4 }}>
                        {MANEUVERS.map(m => (
                          <button key={m.id} disabled={m.disabled} title={m.desc}
                            onClick={() => {
                              if (m.disabled) return;
                              if (m.id === "change_posture") { setShowPostureMenu(p => !p); return; }
                              handleManeuver(m.id);
                            }}
                            style={btnSt(m)}>
                            <span style={{ fontSize: 15 }}>{m.icon}</span>
                            <span style={{ fontSize: 9, textAlign: "center", lineHeight: 1.2 }}>{m.label}</span>
                          </button>
                        ))}
                      </div>

                      {/* Sottomenu postura */}
                      {showPostureMenu && !isProne && (
                        <div style={{ marginTop: 5, display: "flex", gap: 4, justifyContent: "center", flexWrap: "wrap" }}>
                          {[
                            { p: "standing", icon: "🧍", label: "In piedi",    desc: "Postura normale — no penalità" },
                            { p: "kneeling", icon: "🧎", label: "In ginocchio",desc: "−2 att., −2 dif. mischia, +2 dif. ranged" },
                            { p: "prone",    icon: "⬇",  label: "A terra",     desc: "−3 att., −3 dif. mischia, +1 dif. ranged. Alzarsi costa 1 turno." },
                          ].map(({ p, icon, label, desc }) => {
                            const curPosture = selPlayer.posture || (selPlayer.prone ? "prone" : "standing");
                            return (
                              <button key={p} title={desc}
                                onClick={() => { setShowPostureMenu(false); handleManeuver("change_posture", { posture: p }); }}
                                style={{ padding: "5px 10px", borderRadius: 7,
                                  border: `1px solid ${curPosture === p ? "rgba(255,255,255,0.4)" : "rgba(255,255,255,0.12)"}`,
                                  background: curPosture === p ? "rgba(255,255,255,0.15)" : "rgba(255,255,255,0.04)",
                                  color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: curPosture === p ? 800 : 400 }}>
                                {icon} {label}
                              </button>
                            );
                          })}
                          <button onClick={() => setShowPostureMenu(false)}
                            style={{ padding: "5px 8px", borderRadius: 7, border: "none", background: "none", color: "rgba(255,255,255,0.35)", cursor: "pointer" }}>✕</button>
                        </div>
                      )}

                      {/* Selezione arma — sempre visibile */}
                      {(() => {
                        const acts = selPlayer.actions || [];
                        const selAct2 = acts.find(a => a.weapon_id === selectedWeaponId) || acts[0];
                        const ammoCur = selAct2?.ammo_current ?? selAct2?.ammo ?? 0;
                        const ammoMax = selAct2?.ammo ?? 0;
                        const isRangedWeapon = selAct2?.attack_kind === "ranged";
                        const noAmmo = isRangedWeapon && ammoMax > 0 && ammoCur <= 0;
                        const hasAmmo2 = (selPlayer.equipment || []).some(
                          it => it.category === "ammo" && (it.ammo_type === selAct2?.weapon_id || !it.ammo_type) && it.quantity > 0
                        );
                        const accentColor = isRangedWeapon ? "#60a5fa" : "#fbbf24";
                        return (
                          <div style={{ marginTop: 5 }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                              {/* Badge tipo arma */}
                              <span style={{ fontSize: 10, fontWeight: 800, color: accentColor, background: `${accentColor}22`, padding: "1px 6px", borderRadius: 4, letterSpacing: 0.3 }}>
                                {isRangedWeapon ? "🎯 DIST" : "⚔ MISCHIA"}
                              </span>
                              {acts.length > 1 ? (
                                <select value={selectedWeaponId} onChange={e => setSelectedWeaponId(e.target.value)}
                                  style={{ fontSize: 11, padding: "2px 6px", borderRadius: 5, background: "rgba(20,21,36,0.9)", color: "#fff", border: `1px solid ${accentColor}44`, cursor: "pointer" }}>
                                  {acts.map(a => (
                                    <option key={a.weapon_id || a.name} value={a.weapon_id || a.name}>
                                      {a.attack_kind === "ranged" ? "🎯" : "⚔"} {a.name}
                                      {a.attack_kind === "ranged" && a.ammo ? ` [${a.ammo_current ?? a.ammo}/${a.ammo}]` : ""}
                                    </option>
                                  ))}
                                </select>
                              ) : (
                                <span style={{ fontSize: 11, color: "#fff", fontWeight: 700 }}>{selAct2?.name || "—"}</span>
                              )}
                              {/* Munizioni */}
                              {isRangedWeapon && ammoMax > 0 && (
                                <span style={{ fontSize: 10, fontWeight: 800,
                                  color: noAmmo ? "#f87171" : ammoCur <= 2 ? "#facc15" : "#86efac",
                                  background: noAmmo ? "rgba(239,68,68,0.15)" : "rgba(0,0,0,0.25)",
                                  padding: "1px 6px", borderRadius: 4 }}>
                                  {noAmmo ? "⚠ SCARICA" : `🔫 ${ammoCur}/${ammoMax}`}
                                </span>
                              )}
                              {/* Ricarica */}
                              {isRangedWeapon && ammoMax > 0 && ammoCur < ammoMax && hasAmmo2 && (
                                <button onClick={async () => {
                                  const res = await fetch(`${API_URL}/game/combat/reload`, {
                                    method: "POST", headers: { "Content-Type": "application/json" },
                                    body: JSON.stringify({ player_id: selPlayer.id, action_name: selAct2.name }),
                                  }).then(r => r.json());
                                  if (res.error) setCombatLog(prev => [...prev, `Errore ricarica: ${res.error}`]);
                                  else { setCombatLog(prev => [...prev, `🔄 ${selPlayer.name} ricarica ${selAct2.name}`]); advanceTurn(selPlayer.id, true); }
                                }} style={{ padding: "2px 7px", borderRadius: 6, border: "1px solid rgba(134,239,172,0.4)", background: "rgba(134,239,172,0.1)", color: "#86efac", fontWeight: 700, cursor: "pointer", fontSize: 10 }}>
                                  ↺ Ricarica
                                </button>
                              )}
                            </div>
                            {/* Avviso arma scarica */}
                            {noAmmo && (
                              <div style={{ marginTop: 3, fontSize: 10, color: "#f87171", fontWeight: 700 }}>
                                ⚠ Nessuna munizione — usa Prepara per ricaricare oppure cambia arma
                              </div>
                            )}
                          </div>
                        );
                      })()}

                      {/* Hint modalità */}
                      {mode === "move" && (
                        <div style={{ marginTop: 3, fontSize: 10, color: "#818cf8", fontWeight: 700, textAlign: "center" }}>
                          {moveAttackMode
                            ? "🏃 Muovi+Att.: clicca un hex → poi clicca il nemico (−4 tiro)"
                            : "👣 Clicca un hex raggiungibile (in viola) per spostarti"}
                        </div>
                      )}
                      {mode === "attack" && (() => {
                        // Calcola se l'arma selezionata è a distanza e quante munizioni ha
                        const acts3 = selPlayer?.actions || [];
                        const selAct3 = acts3.find(a => a.weapon_id === selectedWeaponId) || acts3[0];
                        const isRng3 = selAct3?.attack_kind === "ranged";
                        const ammo3 = selAct3?.ammo_current ?? selAct3?.ammo ?? 0;
                        const noAmmo3 = isRng3 && (selAct3?.ammo ?? 0) > 0 && ammo3 <= 0;
                        // Distanza dal nemico più vicino (per dare feedback)
                        const selPos3 = selected ? positions[selected] : null;
                        const nearestEnemy = enemies.filter(e => e.hp > 0).reduce((best, e) => {
                          const ep = positions[`e_${e.id}`];
                          if (!ep || !selPos3) return best;
                          const d = hexDist(selPos3.col, selPos3.row, ep.col, ep.row);
                          return !best || d < best.d ? { e, d } : best;
                        }, null);
                        const nd = nearestEnemy?.d ?? 999;
                        let hintText, hintColor;
                        if (noAmmo3) {
                          hintText = "⚠ Arma SCARICA — cambia arma o usa Prepara per ricaricare";
                          hintColor = "#f87171";
                        } else if (attackActionType === "all_out_attack") {
                          hintText = "⚔⚔ Att.Totale: clicca il nemico (+4 al tiro, NO difesa questo turno)";
                          hintColor = "#f87171";
                        } else if (attackActionType === "move_attack") {
                          hintText = "🏃⚔ Muovi+Att.: clicca il nemico (tiro a −4, min 9)";
                          hintColor = "#f97316";
                        } else if (isRng3) {
                          const pen = nd > 1 ? ` (pen. dist. −${nd - 1})` : "";
                          const tooClose = nd <= 1 ? " ⚠ Mischia! (−4 al tiro)" : "";
                          hintText = `🎯 Clicca il nemico — distanza ${nd} hex${pen}${tooClose}`;
                          hintColor = "#60a5fa";
                        } else {
                          const inMelee = nd <= 1;
                          hintText = inMelee
                            ? "⚔ Clicca il nemico (mischia, distanza 1)"
                            : `⚔ Clicca il nemico — dist. ${nd} hex (mischia: max 1)`;
                          hintColor = inMelee ? "#4ade80" : "#facc15";
                        }
                        return (
                          <div style={{ marginTop: 3, fontSize: 10, color: hintColor, fontWeight: 700, textAlign: "center" }}>
                            {hintText}
                          </div>
                        );
                      })()}
                      {mode === "evaluate" && (
                        <div style={{ marginTop: 3, fontSize: 10, color: "#a78bfa", fontWeight: 700, textAlign: "center" }}>
                          🔍 Clicca un nemico per valutarlo (+1 al prossimo attacco vs stesso, max +3)
                        </div>
                      )}
                    </>
                  )}

                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 5 }}>
                    <div style={{ display: "flex", gap: 5, alignItems: "center" }}>
                      {/* Ruota facing — rilevante per attacchi da retro (chi è dietro ignora difesa attiva) */}
                      <span style={{ fontSize: 9, color: "rgba(255,255,255,0.25)", whiteSpace: "nowrap" }}>Fronte:</span>
                      <button onClick={() => rotateFacing(selected, -1)} title="Ruota a sinistra (il triangolo sul token indica dove guarda)"
                        style={{ padding: "3px 7px", borderRadius: 5, border: "1px solid rgba(255,255,255,0.1)", background: "none", color: "rgba(255,255,255,0.45)", cursor: "pointer", fontSize: 12 }}>↺</button>
                      <button onClick={() => rotateFacing(selected, 1)} title="Ruota a destra"
                        style={{ padding: "3px 7px", borderRadius: 5, border: "1px solid rgba(255,255,255,0.1)", background: "none", color: "rgba(255,255,255,0.45)", cursor: "pointer", fontSize: 12 }}>↻</button>
                      <button onClick={() => { setSelected(null); setMode("select"); setReachable(new Set()); }}
                        style={{ padding: "3px 7px", borderRadius: 5, border: "1px solid rgba(255,255,255,0.1)", background: "none", color: "rgba(255,255,255,0.35)", cursor: "pointer", fontSize: 11 }}>✕</button>
                    </div>
                    <button onClick={() => advanceTurn(activePlayerId)}
                      style={{ padding: "4px 13px", borderRadius: 7, border: "1px solid rgba(255,255,255,0.15)", background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.5)", fontWeight: 700, cursor: "pointer", fontSize: 11 }}>
                      Fine turno →
                    </button>
                  </div>
                </div>

              /* ── Nemico selezionato ──────────────────────────────────── */
              ) : selectedIsEnemy && !pendingAttack ? (
                <div style={{ padding: "6px 12px", display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                  <span style={{ fontSize: 12, color: "#f87171", fontWeight: 700 }}>🎯 {selName}</span>
                  {(() => {
                    const e = enemies.find(en => `e_${en.id}` === selected);
                    if (!e) return null;
                    return <span style={{ fontSize: 11, color: "rgba(255,255,255,0.45)" }}>HP {e.hp}/{e.max_hp} | Dif.{e.active_defense} | DR {e.dr}</span>;
                  })()}
                  <span style={{ fontSize: 11, color: "rgba(255,255,255,0.3)" }}>— Seleziona il token di {activeName} per agire</span>
                  <button onClick={() => { setSelected(null); setMode("select"); }} style={{ marginLeft: "auto", padding: "3px 8px", borderRadius: 5, border: "none", background: "none", color: "rgba(255,255,255,0.3)", cursor: "pointer" }}>✕</button>
                </div>

              /* ── Altro PG selezionato ────────────────────────────────── */
              ) : selectedIsOtherPlayer ? (
                <div style={{ padding: "6px 12px", display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 12, color: "rgba(255,255,255,0.55)", fontWeight: 700 }}>{selName} — non è il suo turno</span>
                  <button onClick={() => setSelected(`p_${activePlayerId}`)}
                    style={{ padding: "4px 10px", borderRadius: 6, border: "1px solid rgba(168,85,247,0.4)", background: "rgba(168,85,247,0.12)", color: "#a5b4fc", fontWeight: 700, cursor: "pointer", fontSize: 11 }}>
                    → Seleziona {activeName}
                  </button>
                </div>

              /* ── Nessuna selezione ───────────────────────────────────── */
              ) : (
                <div style={{ padding: "6px 12px" }}>
                  <span style={{ fontSize: 12, color: "#a855f7", fontWeight: 700 }}>▶ {activeName} — seleziona il tuo token sulla mappa</span>
                </div>
              )}
            </div>
          );
        })()}

        {/* ── Log combattimento ──────────────────────────────────────────── */}
        {combatLog.length > 0 && (
          <div style={{ padding: "4px 14px 6px", borderTop: "1px solid rgba(255,255,255,0.07)", background: "rgba(0,0,0,0.25)" }}>
            {combatLog.slice(-6).map((line, i, arr) => {
              const isLast = i === arr.length - 1;
              const isResult = line.startsWith("✅") || line.startsWith("❌");
              const isNarration = line.startsWith("💬");
              const color = isNarration ? "rgba(167,139,250,0.85)"
                          : isResult && line.includes("✅") ? "#86efac"
                          : isResult ? "#fca5a5"
                          : "rgba(255,255,255,0.35)";
              return (
                <div key={i} style={{
                  fontSize: isLast ? 11 : 9,
                  color: isLast ? color : "rgba(255,255,255,0.2)",
                  fontWeight: isLast ? 700 : 400,
                  lineHeight: 1.4,
                  padding: "1px 0",
                  borderLeft: isResult && isLast ? `2px solid ${color}` : "none",
                  paddingLeft: isResult && isLast ? 6 : 0,
                }}>
                  {line}
                </div>
              );
            })}
          </div>
        )}

        {/* ── Pannello bottino ────────────────────────────────────────────── */}
        {effectiveLootPool.length > 0 && (
          <div style={{
            padding: "8px 14px 10px", borderTop: "1px solid rgba(251,191,36,0.3)",
            background: "rgba(251,191,36,0.05)",
          }}>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.5, color: "#fbbf24", marginBottom: 6 }}>
              💰 Bottino disponibile
            </div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {effectiveLootPool.map(entry => {
                const item = entry.item;
                const activePlayer = players.find(p => p.id === activePlayerId);
                return (
                  <div key={item.id} style={{
                    display: "flex", alignItems: "center", gap: 6,
                    padding: "4px 10px", borderRadius: 7,
                    background: "rgba(251,191,36,0.1)", border: "1px solid rgba(251,191,36,0.3)",
                  }}>
                    <span style={{ fontSize: 11 }}>
                      {item.category === "weapon" ? "⚔️" : item.category === "ammo" ? "🔫" : item.category === "quest_item" ? "🔑" : "📦"}
                    </span>
                    <div>
                      <div style={{ fontSize: 11, fontWeight: 700, color: "#fde68a" }}>{item.name}</div>
                      {entry.source_name && (
                        <div style={{ fontSize: 9, color: "rgba(255,255,255,0.4)" }}>da {entry.source_name}</div>
                      )}
                    </div>
                    {item.quantity > 1 && (
                      <span style={{ fontSize: 10, color: "#86efac", fontWeight: 700 }}>×{item.quantity}</span>
                    )}
                    {activePlayer && (
                      <button
                        onClick={async () => {
                          const res = await fetch(`${API_URL}/game/loot/collect`, {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ player_id: activePlayer.id, item_id: item.id }),
                          }).then(r => r.json());
                          if (res.error) {
                            setCombatLog(prev => [...prev, `Errore: ${res.error}`]);
                          } else {
                            setLootPool(res.loot_pool || []);
                            setCombatLog(prev => [...prev, res.log || `${activePlayer.name} raccoglie ${item.name}.`]);
                          }
                        }}
                        style={{
                          padding: "2px 8px", borderRadius: 5, border: "none", fontSize: 11,
                          fontWeight: 700, cursor: "pointer", background: "#fbbf24", color: "#1a1a1a",
                        }}
                      >Raccogli</button>
                    )}
                  </div>
                );
              })}
            </div>
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

// ─── Game screen ───────────────────────────────────────────────────────────

function _mergeTokenStats(prev, t) {
  const newImgCount = prev.image_count + (t.image_count || 0);
  const newImgCost  = prev.image_cost_usd + (t.image_cost_usd || 0);
  const newTextCost = prev.cost_usd + (t.cost_usd || 0);
  return {
    input_tokens:   prev.input_tokens  + (t.input  || 0),
    output_tokens:  prev.output_tokens + (t.output || 0),
    total_tokens:   prev.total_tokens  + (t.input  || 0) + (t.output || 0),
    cost_usd:       newTextCost,
    calls:          prev.calls         + (t.calls  || 0),
    errors:         prev.errors        + (t.errors || 0),
    image_count:    newImgCount,
    image_cost_usd: newImgCost,
    total_cost_usd: newTextCost + newImgCost,
  };
}

function GameScreen({ genre, players: initialPlayers, avatars = {}, adventure = null, provider = "claude", imageProvider = "auto", onRestart }) {
  const [players, setPlayers] = useState(initialPlayers);
  const [messages, setMessages] = useState([]);
  const [options, setOptions] = useState([]);
  const [pendingOption, setPendingOption] = useState(null);
  const [customText, setCustomText] = useState("");
  const [activePlayerId, setActivePlayerId] = useState(initialPlayers[0]?.id);
  const [loading, setLoading] = useState(false);
  const [storyOver, setStoryOver] = useState(false);
  const [victory, setVictory] = useState(false);
  const [endReason, setEndReason] = useState("");
  const [personalVictories, setPersonalVictories] = useState({});
  const [history, setHistory] = useState([]);
  const [turnId, setTurnId] = useState("");
  const [showPanel, setShowPanel] = useState(!!adventure);
  const [showSecrets, setShowSecrets] = useState(false);
  const [startupLoading, setStartupLoading] = useState(true);
  const [gameStateData, setGameStateData] = useState({
    clues_found: [],
    clue_progress: {},
    discovered_clues: [],
    discovered_facts: [],
    resolved_threads: [],
    npc_statuses: {},
    threat_level: 0,
    open_threads: [],
    turn: 1,
    in_combat: false,
    world_npcs: [],
    allowed_escalation_tier: null,
    allowed_escalation_types: [],
    forbidden_escalation_types: [],
    blocked_major_events: [],
    downgraded_events: [],
    director_reason: "",
  });
  const [sceneState, setSceneState] = useState(null);
  const [combatEntities, setCombatEntities] = useState([]); // entity combattimento persistenti, non sovrascritte dal fetch
  const [combatBgImage, setCombatBgImage] = useState(null);
  const [preparedTacticalMaps, setPreparedTacticalMaps] = useState({});
  const preparingTacticalMapsRef = useRef(new Set());
  const [preparingTacticalMaps, setPreparingTacticalMaps] = useState(new Set());
  const [showCombatMap, setShowCombatMap] = useState(false);
  const [lastCombatLog, setLastCombatLog] = useState(null);
  const [mapState, setMapState] = useState(null);
  const [locationImages, setLocationImages] = useState({});
  const [adventureMapBackdrop, setAdventureMapBackdrop] = useState(null);
  const [adventureMapPositions, setAdventureMapPositions] = useState({});
  const [showMapPanel, setShowMapPanel] = useState(false);
  const [clocksData, setClocksData] = useState([]);
  const [clockToasts, setClockToasts] = useState([]);
  const [npcEventToasts, setNpcEventToasts] = useState([]);
  const [gmEventLog, setGmEventLog] = useState([]); // persistent GM event history
  const [tokenStats, setTokenStats] = useState({ input_tokens: 0, output_tokens: 0, total_tokens: 0, cost_usd: 0, calls: 0, errors: 0, image_count: 0, image_cost_usd: 0, total_cost_usd: 0 });
  const [pendingAttack, setPendingAttack] = useState(null);
  const [lootPool, setLootPool] = useState([]);             // bottino disponibile scena corrente
  const [combatAttacker, setCombatAttacker] = useState(null);
  const [combatTarget, setCombatTarget] = useState(null);
  const [npcAvatars, setNpcAvatars] = useState({});  // entity_id → base64
  const [devMode, setDevMode] = useState(() => new URLSearchParams(window.location.search).has("dev"));
  const [showMenu, setShowMenu] = useState(false);
  const [expandedPlayerId, setExpandedPlayerId] = useState(null);
  const [panelOpenTab, setPanelOpenTab] = useState(null);
  const [showPlayerPanel, setShowPlayerPanel] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  function openPlayerTab(tab) {
    setPanelOpenTab(tab);
    setShowPlayerPanel(true);
  }
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const messagesRef = useRef([]);
  const menuRef = useRef(null);

  // Keep-alive: ping ogni 13 minuti per evitare che Render spenga il backend durante il gioco
  useEffect(() => {
    const id = setInterval(() => { fetch(`${API_URL}/health`).catch(() => {}); }, 13 * 60 * 1000);
    return () => clearInterval(id);
  }, []);

  function hasLivingCombatEnemies(scene) {
    return Array.isArray(scene?.entities)
      && scene.entities.some(e => e.type === "enemy" && (e.hp ?? e.max_hp ?? 1) > 0);
  }

  // Chiudi hamburger menu al click fuori
  useEffect(() => {
    if (!showMenu) return;
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) setShowMenu(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [showMenu]);

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

  function buildTacticalMapPayloadForNode(node, enemyNames = []) {
    if (!node) return null;
    const tacticalMap = node.tactical_map || {};
    const layout = tacticalMap?.layout || "room";
    const tacticalDesc = tacticalMap?.enabled
      ? `Scheda tattica canonica: ${tacticalMap.role || "hot_zone"}; layout ${layout}; elementi ${(tacticalMap.features || []).join(", ")}; pericoli ${(tacticalMap.hazards || []).join(", ")}; trigger ${tacticalMap.trigger || ""}.`
      : "";
    return {
      location_name: node.name || "Zona tattica",
      location_description: [node.description, tacticalDesc].filter(Boolean).join(" "),
      genre,
      environment_type: node.kind || adventure?.environment_type || adventure?.genre || "indoor",
      scene_narrative: tacticalDesc || node.description || "",
      mission_environment: adventure?.environment_type || adventure?.genre || genre,
      enemy_names: enemyNames,
      layout,   // ← informa il backend del layout per scegliere l'aspect ratio corretto
    };
  }

  function prepareTacticalMapForNode(node, enemyNames = []) {
    if (!node?.id || imageProvider === "none") return;
    if (!node.tactical_map?.enabled && !node.contains_enemy && !node.is_final) return;
    if (preparedTacticalMaps[node.id] || preparingTacticalMapsRef.current.has(node.id)) return;
    const payload = buildTacticalMapPayloadForNode(node, enemyNames);
    if (!payload) return;
    preparingTacticalMapsRef.current.add(node.id);
    setPreparingTacticalMaps(prev => new Set([...prev, node.id]));
    fetch(`${API_URL}/game/generate-tactical-map-image`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(r => r.json()).then(r => {
      if (r.image_b64) setPreparedTacticalMaps(prev => ({ ...prev, [node.id]: r.image_b64 }));
      if (r.call_tokens) setTokenStats(prev => _mergeTokenStats(prev, r.call_tokens));
    }).catch(() => {}).finally(() => {
      preparingTacticalMapsRef.current.delete(node.id);
      setPreparingTacticalMaps(prev => {
        const next = new Set(prev);
        next.delete(node.id);
        return next;
      });
    });
  }

  function applyStateUpdates(updates) {
    if (!updates) return;
    const updateHasCombatScene = hasLivingCombatEnemies(updates.combat_scene);
    const shouldEnterCombat = !!(updates.activate_combat || updateHasCombatScene || updates.pending_attack);
    setGameStateData(prev => {
      const newClues = [...new Set([...prev.clues_found, ...(updates.clues_found || [])])];
      const progressById = { ...(prev.clue_progress || {}) };
      for (const p of (updates.clue_progress || [])) {
        const cid = p?.clue_id || p?.id;
        if (!cid || newClues.includes(cid)) continue;
        const prevEntry = progressById[cid] || { ticks: 0, notes: [] };
        const note = p.note || p.text || "";
        const nextNotes = note ? [...(prevEntry.notes || []), note].slice(-3) : (prevEntry.notes || []);
        progressById[cid] = {
          ticks: Math.min(2, (prevEntry.ticks || 0) + (p.ticks || 1)),
          note: note || prevEntry.note || "",
          notes: nextNotes,
        };
      }
      for (const cid of newClues) delete progressById[cid];
      const clueById = new Map((prev.discovered_clues || []).map(c => [c.id, c]));
      for (const c of (updates.discovered_clues || [])) {
        if (c?.id) clueById.set(c.id, c);
      }
      const newNpcStatuses = { ...prev.npc_statuses };
      for (const u of (updates.npc_updates || [])) {
        const id = u.id || u.npc_id;
        if (id) newNpcStatuses[id] = { ...newNpcStatuses[id], ...u, id };
      }
      const existing = prev.open_threads.filter(t => !(updates.closed_threads || []).includes(t));
      const newThreads = existing;
      const resolved = [...new Set([...(prev.resolved_threads || []), ...(updates.closed_threads || []), ...(updates.thread_resolved || [])])];
      const discoveredFacts = [...new Set([...(prev.discovered_facts || []), ...(updates.discovered_facts || [])])].slice(-30);
      return {
        ...prev,
        clues_found: newClues,
        clue_progress: progressById,
        discovered_clues: Array.from(clueById.values()),
        discovered_facts: discoveredFacts,
        resolved_threads: resolved,
        npc_statuses: newNpcStatuses,
        threat_level: prev.threat_level + (updates.threat_increase || 0),
        open_threads: newThreads,
        turn: prev.turn + 1,
        in_combat: updates.combat_over ? false : (shouldEnterCombat || prev.in_combat),
        allowed_escalation_tier: updates.allowed_escalation_tier ?? prev.allowed_escalation_tier,
        allowed_escalation_types: updates.allowed_escalation_types || prev.allowed_escalation_types || [],
        forbidden_escalation_types: updates.forbidden_escalation_types || prev.forbidden_escalation_types || [],
        blocked_major_events: updates.blocked_major_events || updates.blocked_state_updates || [],
        downgraded_events: updates.downgraded_events || [],
        director_reason: updates.director_reason || prev.director_reason || "",
      };
    });
    // Apre la mappa tattica automaticamente all'inizio del combattimento
    if (shouldEnterCombat) setShowCombatMap(true);
    // Chiude la mappa tattica quando il combattimento finisce e resetta l'immagine per il prossimo
    if (updates.combat_over) { setShowCombatMap(false); setCombatBgImage(null); }
  }

  async function fetchGameState() {
    try {
      const gs = await fetch(`${API_URL}/game/state`).then(r => r.json());
      if (gs.scene) {
        setSceneState(gs.scene);
        if (hasLivingCombatEnemies(gs.scene)) {
          _syncCombatEntitiesFromScene(gs.scene);
        }
      }
      if (gs.map_state) setMapState(gs.map_state);
      if (gs.pending_attack !== undefined) setPendingAttack(gs.pending_attack);
      const stateSaysCombat = !!(gs.in_combat || gs.pending_attack || hasLivingCombatEnemies(gs.scene));
      if (stateSaysCombat) {
        setGameStateData(prev => ({ ...prev, in_combat: true }));
        setShowCombatMap(true);
      }
      if (gs.world_npcs) setGameStateData(prev => ({ ...prev, world_npcs: gs.world_npcs }));
      setGameStateData(prev => ({
        ...prev,
        allowed_escalation_tier: gs.allowed_escalation_tier ?? prev.allowed_escalation_tier,
        allowed_escalation_types: gs.allowed_escalation_types || prev.allowed_escalation_types || [],
        forbidden_escalation_types: gs.forbidden_escalation_types || prev.forbidden_escalation_types || [],
        blocked_major_events: gs.blocked_major_events || prev.blocked_major_events || [],
        downgraded_events: gs.downgraded_events || prev.downgraded_events || [],
        director_reason: gs.director_reason || prev.director_reason || "",
      }));
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
        // Aggiunge in chat
        _setMessages(prev => [...prev, { role: "master", name: "Master", text: res.narrative, isCombatNarration: true }]);
        // Aggiunge anche nella mappa tattica (via lastCombatLog.narration)
        setLastCombatLog(prev => prev ? { ...prev, narration: res.narrative } : { narration: res.narrative });
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
      const npcLogs = res.npc_logs || [];
      for (const log of npcLogs) {
        _setMessages(prev => [...prev, { role: "combat", combat_log: log }]);
        setLastCombatLog(log);
        // Narrativa per ogni azione NPC (colpo, mancato, parata)
        _fetchCombatNarration(log);
      }
      // Salva ultimo round NPC in gameStateData per il contesto narrativo
      if (npcLogs.length > 0) {
        setGameStateData(prev => ({ ...prev, last_combat_round: npcLogs[npcLogs.length - 1] }));
      }
      // Avvia attacco NPC su giocatore (pending_attack) — prossimo NPC che non ha già agito
      if (res.pending_attack) setPendingAttack(res.pending_attack);
      return res;
    } catch (_) {}
    return null;
  }

  async function handleAttack(player, actionName, targetEntityId, actionType = "normal", tacticalContext = null, distance = 0) {
    // Caso speciale: "__reload__" — il reload è già avvenuto, sincronizza players
    if (actionName === "__reload__") {
      try {
        const st = await fetch(`${API_URL}/game/state`).then(r => r.json());
        if (st.players) setPlayers(st.players);
      } catch (_) {}
      return null;
    }
    try {
      const res = await fetch(`${API_URL}/game/combat/attack`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          attacker_id: player.id,
          action_name: actionName,
          target_entity_id: targetEntityId,
          action_type: actionType,
          distance: distance || 0,
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
      if (res.loot_pool !== undefined) setLootPool(res.loot_pool);
      if (res.combat_log) {
        setLastCombatLog(res.combat_log);
        _setMessages(prev => [...prev, { role: "combat", combat_log: res.combat_log }]);
        // Salva ultimo round in gameStateData per il contesto narrativo
        setGameStateData(prev => ({ ...prev, last_combat_round: res.combat_log }));
        const r = res.combat_log?.result;
        if (r?.net_damage > 0 && !res.pending_attack && !syncedEntities) {
          _applyCombatDamage(targetEntityId, r.net_damage);
        }
        if (!res.pending_attack) {
          // Narrativa per tutti gli esiti (colpo, parata, mancato)
          _fetchCombatNarration(res.combat_log);
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

  async function handleCombatRetreat(tacticalContext = null) {
    try {
      const fetchOptions = tacticalContext
        ? {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(tacticalContext),
          }
        : { method: "POST" };
      const res = await fetch(`${API_URL}/game/combat/retreat`, fetchOptions).then(r => r.json());
      if (res.players) setPlayers(res.players);
      if (res.scene) setSceneState(res.scene);
    } catch (_) {}
    const activePid = players.find(p => p.hp > 0)?.id || activePlayerId || players[0]?.id;
    setGameStateData(prev => ({ ...prev, in_combat: false, threat_level: (prev.threat_level || 0) + 1 }));
    setCombatEntities([]);
    setPendingAttack(null);
    setShowCombatMap(false);
    setCombatBgImage(null);
    setLastCombatLog(null);
    _setMessages(prev => [...prev, {
      role: "master", name: "Master",
      text: "La squadra rompe il contatto e ripiega. Non è una vittoria, ma avete ancora spazio per scegliere: riorganizzarvi, cercare una via alternativa o trasformare la ritirata in un vantaggio.",
      isCombatNarration: true,
    }]);
    setOptions([
      { text: "Riorganizzarsi, curare i feriti e capire da dove ripartire", skill: "sopravvivenza", skill_level: 10, stat: "empatia", player_id: activePid },
      { text: "Cercare una via alternativa evitando il confronto diretto", skill: "furtivita", skill_level: 10, stat: "agilita", player_id: activePid },
      { text: "Azione custom", skill: "", skill_level: 0, stat: "", player_id: activePid },
    ]);
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

  // Fetch location images for newly visible nodes
  useEffect(() => {
    if (!mapState || imageProvider === "none") return;
    const nodes = Object.values(mapState.nodes || {});
    const currentId = mapState.current_node_id;
    const visitedSet = new Set(nodes.filter(n => n.visited).map(n => n.id));
    visitedSet.add(currentId);
    const toFetch = nodes.filter(n => visitedSet.has(n.id) && !locationImages[n.id]);
    if (toFetch.length === 0) return;
    toFetch.forEach(async (node) => {
      try {
        const res = await fetch(`${API_URL}/game/adventure/location-image`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            location_id: node.id,
            location_name: node.name,
            location_description: node.description || "",
            genre: adventure?.genre || genre,
            theme: mapState.theme || "",
          }),
        }).then(r => r.json());
        if (res.image_b64) {
          setLocationImages(prev => ({ ...prev, [node.id]: res.image_b64 }));
        }
        if (res.call_tokens) setTokenStats(prev => _mergeTokenStats(prev, res.call_tokens));
      } catch (_) {}
    });
  }, [mapState?.current_node_id, JSON.stringify(Object.keys(mapState?.nodes || {}))]);

  // Generate adventure overview map backdrop once per adventure — cache in localStorage
  useEffect(() => {
    if (!adventure || !mapState || imageProvider === "none") return;
    if (adventureMapBackdrop) return; // already in memory
    const advDef = adventure?.adventure_definition || adventure || {};
    const title = advDef.title || adventure?.title || "";
    if (!title) return;
    const locations = Object.values(mapState.nodes || {}).map(n => ({ name: n.name || "" })).filter(l => l.name);
    if (locations.length === 0) return;
    const cacheKey = `gurps_map_v1_${title.slice(0, 60)}_${(adventure?.genre || genre || "fantasy")}`;
    // Try localStorage cache first (avoids re-generation on page reload)
    try {
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        const data = JSON.parse(cached);
        if (data.image_b64) {
          setAdventureMapBackdrop(data.image_b64);
          setAdventureMapPositions(data.location_positions || {});
          return;
        }
      }
    } catch (_) {}
    // Not cached: generate via API
    const setting = advDef.setting || advDef.location || advDef.world || "";
    const period = advDef.period || advDef.year || advDef.era || "";
    fetch(`${API_URL}/game/adventure/generate-overview-map`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ adventure_title: title, locations, genre: adventure?.genre || genre, setting, period }),
    }).then(r => r.json()).then(res => {
      if (res.image_b64) {
        setAdventureMapBackdrop(res.image_b64);
        const positions = res.location_positions || {};
        setAdventureMapPositions(positions);
        try { localStorage.setItem(cacheKey, JSON.stringify({ image_b64: res.image_b64, location_positions: positions })); } catch (_) {}
      }
      if (res.call_tokens) setTokenStats(prev => _mergeTokenStats(prev, res.call_tokens));
    }).catch(() => {});
  }, [adventure?.title, mapState ? Object.keys(mapState.nodes || {}).length : 0]);

  function handleMoveToLocation(locationName) {
    sendAction(`Spostarsi verso ${locationName}`, "", activePlayerId);
  }

  async function handleDeduce(threadId, question) {
    try {
      const r = await fetch(`${API_URL}/game/deduce`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ thread_id: threadId, deduction_text: question }),
      });
      const res = await r.json();
      if (r.ok) {
        _setMessages(prev => [...prev, { role: "assistant", content: "[Sistema] Deduzione confermata: \"" + question + "\". " + (res.answer || "La pista è risolta.") }]);
        setGameStateData(prev => ({ ...prev, resolved_threads: [...new Set([...(prev.resolved_threads || []), threadId])] }));
      }
    } catch (e) {
      console.error("[GURPS] handleDeduce error:", e);
    }
  }

  async function handlePreviewAction() {
    if (!customText.trim()) return;
    setPreviewLoading(true);
    try {
      const res = await fetch(`${API_URL}/game/preview-action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player_id: activePlayerId, intent: customText }),
      });
      const data = await res.json();
      setPreviewData(data);
    } catch (e) {
      setPreviewData({ available: false, reason: "network_error" });
    } finally {
      setPreviewLoading(false);
    }
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
      if (res.call_tokens) setTokenStats(prev => _mergeTokenStats(prev, res.call_tokens));
    } catch (_) {}
  }

  useEffect(() => {
    async function fetchWithTimeout(url, opts = {}, ms = 90000) {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), ms);
      try {
        const r = await fetch(url, { ...opts, signal: ctrl.signal });
        clearTimeout(timer);
        return r;
      } catch (e) {
        clearTimeout(timer);
        throw e;
      }
    }

    async function start() {
      // Sessione persa (es. backend riavviato) — torna al setup invece di avviare vuoto
      if (!initialPlayers || initialPlayers.length === 0) {
        onRestart();
        return;
      }
      setLoading(true);

      // Warmup ping: sveglia Render prima delle chiamate principali (free tier dorme dopo 15min)
      try { await fetchWithTimeout(`${API_URL}/health`, {}, 70000); } catch (_) {}

      // Prova a riprendere una sessione salvata per questa avventura
      const advId = adventure?.id || adventure?.adventure_definition_id;
      if (advId) {
        try {
          const liveRes = await fetchWithTimeout(`${API_URL}/game/adventure/runtime/${advId}/live-state`).then(r => r.json());
          const saved = liveRes?.live_game_state;
          if (saved && (saved.turn || 0) > 1) {
            // Sessione esistente: ripristina lo stato world senza chiamare l'AI
            setGameStateData(prev => ({ ...prev, ...saved }));
            const cluesCount = saved.clues_found?.length || 0;
            const threatPct = saved.threat_level && adventure?.threat_max_turns
              ? Math.round(saved.threat_level / adventure.threat_max_turns * 100)
              : saved.threat_level || 0;
            const resumeText = `Sessione ripresa al turno ${saved.turn}. `
              + `Indizi scoperti: ${cluesCount}. `
              + `Minaccia: ${saved.threat_level || 0}${adventure?.threat_max_turns ? `/${adventure.threat_max_turns}` : ""} (${threatPct}%). `
              + (saved.clues_found?.length ? `Prove raccolte: ${saved.clues_found.slice(0, 3).join(", ")}${cluesCount > 3 ? "..." : ""}. ` : "")
              + `Invia la tua prossima azione per continuare.`;
            const resumeMsg = { role: "master", name: "Master", text: resumeText };
            _setMessages([resumeMsg]);
            setHistory([{ role: "master", name: "Master", text: resumeText }]);
            setOptions([]);
            setLoading(false);
            setStartupLoading(false);
            const gs = await fetch(`${API_URL}/game/state`).then(r => r.json()).catch(() => ({}));
            if (gs.scene) setSceneState(gs.scene);
            if (gs.map_state) setMapState(gs.map_state);
            if (gs.world_npcs) setGameStateData(prev => ({ ...prev, world_npcs: gs.world_npcs }));
            return;
          }
        } catch (_) {}
      }

      // Nessuna sessione salvata: avvio normale
      if (!adventure) throw new Error("Avventura compilata mancante: riavvia dalla schermata di setup.");
      const res = await fetchWithTimeout(`${API_URL}/game/master/start-bible`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ genre, players: playerDicts, adventure }),
      }, 90000).then(r => r.json());
      if (res.detail) throw new Error(res.detail);
      const masterMsg = { role: "master", name: "Master", text: res.narrative, roll: res.roll };
      _setMessages([masterMsg]);
      setHistory([{ role: "master", name: "Master", text: res.narrative }]);
      setOptions(res.options || []);
      if (res.state_updates) applyStateUpdates(res.state_updates);
      if (res.map_state) setMapState(res.map_state);
      if (res.clocks_data) setClocksData(res.clocks_data);
      setLoading(false);
      setStartupLoading(false);
      if (imageProvider !== "none") fetchSceneImage(res.narrative, 0);
      // fetchGameState popola world_npcs — poi generiamo gli avatar
      const gs = await fetch(`${API_URL}/game/state`).then(r => r.json()).catch(() => ({}));
      if (gs.scene) setSceneState(gs.scene);
      if (gs.map_state && !res.map_state) setMapState(gs.map_state);
      if (gs.world_npcs) setGameStateData(prev => ({ ...prev, world_npcs: gs.world_npcs }));
      if (gs.players?.length > 0) setPlayers(prev => gs.players.map(gp => {
        const local = prev.find(lp => lp.id === gp.id);
        return local ? { ...gp, backstory: gp.backstory || local.backstory || "", motivation: gp.motivation || local.motivation || "" } : gp;
      }));
      // avatar NPC generati dall'useEffect che osserva world_npcs
    }
    start().catch(err => {
      console.error("[start] errore apertura scena:", err);
      setLoading(false);
      setStartupLoading(false);
      const isTimeout = err?.name === "AbortError";
      const isNetwork = err?.message === "Load failed" || err?.message === "Failed to fetch" || err?.message?.includes("NetworkError");
      let hint;
      if (isTimeout || isNetwork) {
        hint = import.meta.env.PROD
          ? " Il server (Render free tier) si sveglia in 30-90 secondi dopo inattività. Ricarica la pagina e attendi."
          : ` Backend non raggiungibile su ${API_URL}. Avvia con: cd backend && uvicorn App.main:app --port 8002`;
      } else {
        hint = " Riprova a ricaricare la pagina.";
      }
      const errMsg = { role: "master", name: "Master", text: `⚠️ Errore all'avvio: ${err.message || "il backend non ha risposto"}.${hint}` };
      _setMessages([errMsg]);
      setHistory([{ role: "master", name: "Master", text: errMsg.text }]);
      setOptions([]);
    });
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, options]);


  // Prepara in anticipo le battlemap delle zone calde/finali, una sola volta per avventura.
  useEffect(() => {
    if (imageProvider === "none") return;
    deriveTacticalNodes(adventure, mapState)
      .slice(0, 4)
      .forEach(node => prepareTacticalMapForNode(node));
  }, [adventure, mapState, imageProvider]);

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
      const activePid = players.find(p => p.hp > 0)?.id || activePlayerId || players[0]?.id;
      setGameStateData(prev => ({ ...prev, in_combat: false }));
      setCombatEntities([]);
      setShowCombatMap(false);
      setLastCombatLog(null);
      _setMessages(prev => [...prev, {
        role: "master", name: "Master",
        text: "Il combattimento è terminato. L'area torna respirabile: potete mettere in sicurezza la zona, cercare indizi o proseguire verso l'obiettivo.",
        isCombatNarration: true,
      }]);
      setOptions([
        { text: "Mettere in sicurezza l'area e cercare indizi utili", skill: "investigare", skill_level: 10, stat: "intelligenza", player_id: activePid },
        { text: "Proseguire verso l'obiettivo prima che arrivino rinforzi", skill: "sopravvivenza", skill_level: 10, stat: "agilita", player_id: activePid },
        { text: "Azione custom", skill: "", skill_level: 0, stat: "", player_id: activePid },
      ]);
    }
  }, [combatEntities, gameStateData.in_combat, players, activePlayerId]);

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
    try { return await _sendActionInner(actionText, skill, pid, player, newHistory); }
    catch (e) { console.error("[GURPS] sendAction error:", e); _setMessages(prev => [...prev, { role: "master", name: "Master", text: `⚠ Errore: ${e.message || "risposta non ricevuta"}` }]); }
    finally { setLoading(false); }
  }

  async function _sendActionInner(actionText, skill, pid, player, newHistory) {

    if (!adventure) throw new Error("Avventura compilata mancante: riavvia dalla schermata di setup.");
    const res = await fetch(`${API_URL}/game/master/turn-bible`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        genre, players: playerDicts, history: newHistory,
        player_action: actionText, active_player_id: pid,
        adventure, game_state_data: {
          ...gameStateData,
          map_state: mapState,
          // Passa entità combat live al backend per contesto narrativo e HP tracking
          live_combat_entities: gameStateData.in_combat
            ? combatEntities.filter(e => e.type === "enemy").map(e => ({
                id: e.id, name: e.name, type: e.type,
                hp: e.hp ?? e.max_hp, max_hp: e.max_hp,
                status: (e.hp ?? e.max_hp) <= 0 ? "eliminato" : "vivo",
              }))
            : undefined,
        },
      }),
    }).then(r => r.json());
    if (res.detail) throw new Error(res.detail);

    const masterMsg = { role: "master", name: "Master", text: res.narrative, roll: res.roll };
    // capture index before state update — prev.length is reliable inside the updater
    // but we also need it synchronously: use a ref snapshot
    const masterIdx = messagesRef.current.length;
    _setMessages(prev => [...prev, masterMsg]);
    // L2: se il backend ha compresso la history, usa quella come nuova base
    const historyBase = res.compressed_history || newHistory;
    setHistory([...historyBase, { role: "master", name: "Master", text: res.narrative }]);
    // R1: traccia turn_id per rilevare stati stale dopo reconnect
    if (res.turn_id) setTurnId(res.turn_id);
    setOptions(res.options || []);

    if (res.map_state) {
      setMapState(res.map_state);
    } else if (res.state_updates?.new_location_id) {
      // Fallback: aggiorna current_node_id localmente se il backend non ha restituito map_state
      const newLocId = res.state_updates.new_location_id;
      setMapState(prev => {
        if (!prev || !prev.nodes || !prev.nodes[newLocId]) return prev;
        return {
          ...prev,
          current_node_id: newLocId,
          nodes: {
            ...prev.nodes,
            [newLocId]: { ...prev.nodes[newLocId], visited: true },
          },
        };
      });
    }
    if (res.clocks_data) setClocksData(res.clocks_data);
    if (res.clock_events?.length > 0) {
      const mapped = res.clock_events.map(ev => ({
        id: `${ev.clock_id}-${Date.now()}-${Math.random()}`,
        label: ev.label, old_value: ev.old_value, new_value: ev.new_value,
        max_value: ev.max_value, steps_crossed: ev.steps_crossed || [],
        completed: ev.completed, clock_type: ev.clock_type || "narrative",
        consequence: ev.consequence || "",
      }));
      setClockToasts(prev => [...prev, ...mapped]);
      setGmEventLog(prev => [...prev, ...mapped.map(e => ({ ...e, _type: "clock", _ts: Date.now() }))]);
    }
    if (res.npc_events?.length > 0) {
      const mapped = res.npc_events.map(ev => ({
        id: `npc-${ev.actor_id}-${Date.now()}-${Math.random()}`,
        actor_name: ev.actor_name || ev.actor_id, action: ev.action,
        narration: ev.narration || "", at_pressure: ev.at_pressure,
      }));
      setNpcEventToasts(prev => [...prev, ...mapped]);
      setGmEventLog(prev => [...prev, ...mapped.map(e => ({ ...e, _type: "npc", _ts: Date.now() }))]);
    }
    if (res.call_tokens) setTokenStats(prev => _mergeTokenStats(prev, res.call_tokens));
    const updates = res.state_updates;
    console.log("[GURPS] state_updates:", JSON.stringify(updates));
    if (updates) {
      const responseHasCombatScene = hasLivingCombatEnemies(updates.combat_scene);
      applyStateUpdates(updates);
      if (updates.story_over) {
        setStoryOver(true);
        setVictory(updates.victory || false);
        if (updates.end_reason) setEndReason(updates.end_reason);
        if (updates.personal_victories) setPersonalVictories(updates.personal_victories);
      }
      // popola sceneState immediatamente dalla combat_scene nel payload
      // IMPORTANTE: inizializza solo al PRIMO ingresso (activate_combat=true o non ancora in combattimento).
      // Se già in combattimento usa merge (_syncCombatEntitiesFromScene) per non resettare HP.
      const alreadyInCombat = gameStateData.in_combat;
      if ((updates.activate_combat || responseHasCombatScene) && updates.combat_scene?.entities) {
        if (!alreadyInCombat) {
          // Primo ingresso: inizializza entità a HP pieno
          console.log("[GURPS] attivazione combattimento:", updates.combat_scene);
          setCombatEntities(updates.combat_scene.entities);
        } else {
          // Già in combattimento: merge senza resettare HP
          _syncCombatEntitiesFromScene(updates.combat_scene);
        }
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
          if (currentNode?.id && preparedTacticalMaps[currentNode.id]) return preparedTacticalMaps[currentNode.id];
          const locationName = currentNode?.name || adventure?.locations?.[0]?.name || "Luogo di combattimento";
          const enemyNames = (updates.combat_scene?.entities || [])
            .filter(e => e.type === "enemy")
            .map(e => e.name);
          if (currentNode?.id) prepareTacticalMapForNode(currentNode, enemyNames);
          const payload = currentNode
            ? buildTacticalMapPayloadForNode(currentNode, enemyNames)
            : {
                location_name: locationName,
                location_description: res.narrative.slice(0, 300),
                genre,
                environment_type: updates.combat_scene?.location_type || "indoor",
                scene_narrative: updates.combat_scene?.scene_text || updates.narrative || "",
                mission_environment: adventure?.environment_type || adventure?.genre || genre,
                enemy_names: enemyNames,
              };
          if (imageProvider !== "none") fetch(`${API_URL}/game/generate-tactical-map-image`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          }).then(r => r.json()).then(r => {
            if (r.image_b64) {
              if (currentNode?.id) setPreparedTacticalMaps(prev => ({ ...prev, [currentNode.id]: r.image_b64 }));
              setCombatBgImage(r.image_b64);
            }
          }).catch(() => {});
          return null; // placeholder finché non arriva
        });
      }
    }
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
    setPreviewData(null);
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
        { at: 0,     pill: "Connessione", label: "Connessione al server in corso..." },
        { at: 4000,  pill: "Contesto",   label: "Leggo la bibbia dell'avventura..." },
        { at: 9000,  pill: "Personaggi", label: "Analizzo il gruppo di avventurieri..." },
        { at: 16000, pill: "Location",   label: "Colloco la squadra nella prima scena..." },
        { at: 24000, pill: "Narrativa",  label: "Il Master scrive la scena d'apertura..." },
        { at: 34000, pill: "Indizi",     label: "Posiziono i primi indizi e PNG in scena..." },
        { at: 44000, pill: "Server",     label: "Il server si sta svegliando (servizio gratuito)..." },
        { at: 55000, pill: "Opzioni",    label: "Preparo le azioni disponibili per il primo turno..." },
        { at: 65000, pill: "Pronto",     label: "Quasi pronto, ancora un momento..." },
      ]}
    />
  );

  // ── Dati per HUD strip ──────────────────────────────────────────────────────
  const _def = adventure?.adventure_definition || adventure || {};
  const currentNodeName = mapState?.nodes?.[mapState?.current_node_id]?.name || null;
  const threatLevel = gameStateData.threat_level ?? 0;
  const threatMax = _def.threat_max_turns ?? adventure?.threat_max_turns ?? 8;
  const threatPct = Math.min(100, Math.round((threatLevel / Math.max(threatMax, 1)) * 100));
  const threatColor = threatPct >= 80 ? "#ef4444" : threatPct >= 50 ? "#f59e0b" : threatPct >= 25 ? "#facc15" : "#4ade80";
  const activeObjective = (_def.objectives || []).find(o => o.status === "active" || o.status === "available")
    || (_def.objectives || [])[0];
  const winLabel = activeObjective?.label || adventure?.win_condition || null;

  // ── Dati per barra Diario giocatori ─────────────────────────────────────────
  const _cluesFound = gameStateData.clues_found?.length || 0;
  const _totalClues = (_def.clues || []).length;
  const _storyThreads = adventure
    ? deriveStoryThreads(adventure, gameStateData.clues_found || [], gameStateData.clue_progress || {}, gameStateData.resolved_threads || [])
    : [];
  const _readyThreadsCount = _storyThreads.filter(t => t.status === "ready_to_deduce").length;
  const _resolvedThreadsCount = _storyThreads.filter(t => t.status === "resolved").length;
  const _knownNpcs = Object.entries(gameStateData.npc_statuses || {}).filter(([, s]) => s && s !== "unknown").length;
  const _totalNpcs = (_def.actors || _def.npcs || []).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden", position: "relative" }}>

      {/* ── Dev stats bar (nascosta per default) ───────────────────────────── */}
      {devMode && (
        <div style={{
          padding: "3px 16px", borderBottom: "1px solid var(--border)",
          display: "flex", alignItems: "center", gap: 14, flexShrink: 0,
          background: "rgba(0,0,0,0.35)", fontSize: 10, color: "#666",
          fontFamily: "monospace",
        }}>
          <span style={{ color: "#444", fontWeight: 700 }}>DEV</span>
          <span title="Token input inviati">↑ {tokenStats.input_tokens.toLocaleString()}</span>
          <span title="Token output ricevuti">↓ {tokenStats.output_tokens.toLocaleString()}</span>
          <span title="Costo testo (Claude/GPT)" style={{ color: "#9ca3af" }}>📝 ${tokenStats.cost_usd.toFixed(4)}</span>
          {tokenStats.image_count > 0 && (
            <span title={`${tokenStats.image_count} immagini generate`} style={{ color: "#c084fc" }}>
              🖼 {tokenStats.image_count} ${tokenStats.image_cost_usd.toFixed(4)}
            </span>
          )}
          <span style={{ color: tokenStats.total_cost_usd > 0.5 ? "#f87171" : tokenStats.total_cost_usd > 0.1 ? "#fb923c" : "#4ade80" }}
                title="Costo totale sessione">Σ ${tokenStats.total_cost_usd.toFixed(4)}</span>
          <span title="Chiamate LLM">{tokenStats.calls} call</span>
          {tokenStats.errors > 0 && <span style={{ color: "#f87171" }}>⚠ {tokenStats.errors} err</span>}
          <button onClick={() => setDevMode(false)} style={{ marginLeft: "auto", background: "none", border: "none", color: "#555", cursor: "pointer", fontSize: 10 }}>✕ chiudi</button>
        </div>
      )}

      {/* ── Header compatto ─────────────────────────────────────────────────── */}
      <div style={{
        padding: "8px 16px", borderBottom: "1px solid var(--border)",
        display: "flex", alignItems: "center", gap: 8, flexShrink: 0,
        background: "var(--bg)",
      }}>
        {/* Player chips — clicca per attivare, clicca ancora per espandere la scheda */}
        <div style={{ display: "flex", gap: 6, flex: 1, minWidth: 0, flexWrap: "wrap" }}>
          {players.map(p => (
            <div key={p.id}
              title={p.id === expandedPlayerId ? `Chiudi scheda ${p.name}` : `Mostra scheda ${p.name}`}
              style={{ cursor: "pointer" }}
              onClick={() => {
                setActivePlayerId(p.id);
                setExpandedPlayerId(prev => prev === p.id ? null : p.id);
              }}
            >
              <PlayerChip
                player={p}
                active={p.id === activePlayerId}
                onClick={() => {}}
                avatar={avatars[p.id]}
                onRename={newName => handleRename(p.id, newName)}
                expanded={p.id === expandedPlayerId}
              />
            </div>
          ))}
        </div>

        {/* Hamburger menu ─────────────────────────────────────── */}
        <div ref={menuRef} style={{ position: "relative", flexShrink: 0 }}>
          <button
            onClick={() => setShowMenu(v => !v)}
            title="Menu"
            style={{
              padding: "6px 10px", borderRadius: 8, border: "1px solid var(--border)",
              background: showMenu ? "var(--code-bg)" : "none",
              color: "var(--text)", cursor: "pointer", fontSize: 16, lineHeight: 1,
            }}
          >☰</button>

          {showMenu && (
            <div style={{
              position: "absolute", top: "calc(100% + 6px)", right: 0, zIndex: 200,
              background: "var(--bg)", border: "1px solid var(--border)",
              borderRadius: 10, boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
              minWidth: 180, overflow: "hidden",
            }}>
              {[
                adventure && mapState && { icon: "🗺", label: "Mappa", action: () => { setShowMapPanel(v => !v); setShowMenu(false); }, active: showMapPanel },
                { icon: "↩", label: "Nuova partita", action: () => { setShowMenu(false); onRestart(); }, danger: true },
                !devMode && { icon: "🛠", label: "Dev mode", action: () => { setDevMode(true); setShowMenu(false); } },
                { icon: "⚔", label: "Test combattimento", action: async () => {
                  setShowMenu(false);
                  const res = await fetch(`${API_URL}/game/debug/start-combat`, { method: "POST" }).then(r => r.json());
                  if (res.ok) {
                    setCombatEntities(res.combat_scene.entities);
                    setGameStateData(prev => ({ ...prev, in_combat: true }));
                    setShowCombatMap(true);
                  }
                }},
              ].filter(Boolean).map((item, i) => (
                <button key={i} onClick={item.action} style={{
                  display: "flex", alignItems: "center", gap: 10,
                  width: "100%", padding: "10px 16px", border: "none",
                  background: item.active ? "var(--accent-bg)" : "none",
                  color: item.danger ? "#f87171" : item.active ? "var(--accent)" : "var(--text-h)",
                  fontSize: 13, cursor: "pointer", textAlign: "left",
                  borderBottom: "1px solid var(--border)",
                }}>
                  <span style={{ fontSize: 15 }}>{item.icon}</span>
                  <span style={{ fontWeight: 600 }}>{item.label}</span>
                  {item.active && <span style={{ marginLeft: "auto", fontSize: 10, color: "var(--accent)" }}>●</span>}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── PlayerCardPanel — espandibile cliccando sul chip ────────────────── */}
      {expandedPlayerId && (() => {
        const liveP = players.find(pl => pl.id === expandedPlayerId);
        return liveP
          ? <PlayerCardPanel
              player={liveP}
              avatar={avatars[liveP.id]}
              onClose={() => setExpandedPlayerId(null)}
              onPlayersUpdate={updatedPlayers => updatedPlayers && setPlayers(updatedPlayers)}
            />
          : null;
      })()}

      {/* ── HUD strip — sempre visibile ─────────────────────────────────────── */}
      {!storyOver && (
        <div style={{
          display: "flex", alignItems: "center", gap: 0,
          borderBottom: "1px solid var(--border)", flexShrink: 0,
          background: "rgba(0,0,0,0.15)", fontSize: 11, overflow: "hidden",
        }}>
          {/* Location */}
          <div style={{
            display: "flex", alignItems: "center", gap: 6,
            padding: "5px 14px", borderRight: "1px solid var(--border)",
            minWidth: 0, flexShrink: 1, overflow: "hidden",
          }}>
            <span style={{ opacity: 0.6, flexShrink: 0 }}>📍</span>
            <span style={{
              color: "var(--text)", whiteSpace: "nowrap", overflow: "hidden",
              textOverflow: "ellipsis", maxWidth: 160,
            }}>{currentNodeName || "–"}</span>
          </div>

          {/* Threat bar */}
          <div style={{
            display: "flex", alignItems: "center", gap: 6,
            padding: "5px 14px", borderRight: "1px solid var(--border)", flexShrink: 0,
          }}>
            <span style={{ opacity: 0.6 }}>⚠</span>
            <div style={{
              width: 64, height: 5, borderRadius: 3,
              background: "rgba(255,255,255,0.1)", overflow: "hidden",
            }}>
              <div style={{
                height: "100%", borderRadius: 3,
                width: `${threatPct}%`,
                background: threatColor,
                transition: "width 0.4s ease, background 0.4s ease",
              }} />
            </div>
            <span style={{ color: threatColor, fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>
              {threatLevel}/{threatMax}
            </span>
          </div>

          {/* Obiettivo corrente */}
          {winLabel && (
            <div style={{
              flex: 1, padding: "5px 14px", display: "flex", alignItems: "center", gap: 6,
              minWidth: 0, borderRight: "1px solid var(--border)",
            }}>
              <span style={{ opacity: 0.6, flexShrink: 0 }}>🎯</span>
              <span style={{
                color: "var(--text)", opacity: 0.8,
                whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
              }}>{winLabel}</span>
            </div>
          )}

          {/* Turno */}
          <div style={{ padding: "5px 14px", flexShrink: 0, color: "var(--text)", opacity: 0.6 }}>
            T{gameStateData.turn ?? 1}
          </div>
        </div>
      )}

      {/* ── Barra Diario giocatori — accesso rapido a indizi/piste/png/mappa ── */}
      {!storyOver && adventure && (
        <div style={{
          display: "flex", gap: 0, borderBottom: "1px solid var(--border)",
          background: "rgba(0,0,0,0.2)", flexShrink: 0, flexWrap: "wrap",
        }}>
          {[
            {
              icon: "🔍",
              label: "Indizi",
              badge: _cluesFound > 0 ? `${_cluesFound}${_totalClues ? `/${_totalClues}` : ""}` : null,
              tab: "clues",
              color: "#60a5fa",
            },
            {
              icon: "🧵",
              label: "Piste",
              badge: _readyThreadsCount > 0 ? `${_readyThreadsCount} pronte` : _resolvedThreadsCount > 0 ? `${_resolvedThreadsCount} chiuse` : null,
              badgeAlert: _readyThreadsCount > 0,
              tab: "threads",
              color: "#a78bfa",
            },
            {
              icon: "👥",
              label: "PNG",
              badge: _knownNpcs > 0 ? `${_knownNpcs}${_totalNpcs ? `/${_totalNpcs}` : ""}` : null,
              tab: "npcs",
              color: "#4ade80",
            },
            mapState && {
              icon: "🗺",
              label: "Mappa",
              tab: "map",
              color: "#fbbf24",
            },
          ].filter(Boolean).map((item, i) => (
            <button key={i} onClick={() => openPlayerTab(item.tab)} style={{
              display: "flex", alignItems: "center", gap: 5,
              padding: "5px 14px", border: "none", borderRight: "1px solid var(--border)",
              background: "none", cursor: "pointer", fontSize: 12,
              color: "var(--text)", transition: "background 0.15s",
            }}
            onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,0.06)"}
            onMouseLeave={e => e.currentTarget.style.background = "none"}
            >
              <span style={{ fontSize: 13 }}>{item.icon}</span>
              <span style={{ color: "var(--text)", opacity: 0.75, fontWeight: 500 }}>{item.label}</span>
              {item.badge && (
                <span style={{
                  fontSize: 10, padding: "1px 6px", borderRadius: 10,
                  background: item.badgeAlert ? `${item.color}30` : "rgba(255,255,255,0.08)",
                  color: item.badgeAlert ? item.color : "var(--text)",
                  border: `1px solid ${item.badgeAlert ? item.color + "55" : "transparent"}`,
                  fontWeight: item.badgeAlert ? 700 : 400,
                  animation: item.badgeAlert ? "pulse 2s infinite" : "none",
                }}>
                  {item.badge}
                </span>
              )}
            </button>
          ))}
          {/* Bibbia GM — pannello destra */}
          <button onClick={() => setShowPanel(v => !v)} style={{
            display: "flex", alignItems: "center", gap: 5,
            padding: "5px 14px", border: "none",
            borderLeft: "1px solid var(--border)", marginLeft: "auto",
            background: "none", cursor: "pointer", fontSize: 12,
            color: "var(--text)", opacity: 0.45,
          }}>
            <span style={{ fontSize: 11 }}>📖</span>
            <span style={{ fontWeight: 500 }}>GM</span>
          </button>
        </div>
      )}

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
          onRetreat={handleCombatRetreat}
          avatars={avatars}
          npcAvatars={npcAvatars}
          bgImage={combatBgImage}
          lastCombatLog={lastCombatLog}
          genre={genre}
          environmentType={combatLocationNode?.kind || adventure?.environment_type || adventure?.genre}
          locationName={combatLocationNode?.name || adventure?.locations?.[0]?.name}
          sceneText={combatSceneText}
          tacticalMap={combatLocationNode?.tactical_map}
          lootPool={lootPool}
          onClose={() => setShowCombatMap(false)}
        />
      )}

      {/* Chat */}
      <div style={{ flex: 1, overflowY: "auto", padding: "24px 20px", maxWidth: 1100, width: "100%", margin: "0 auto", boxSizing: "border-box" }}>

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

        <ClockUrgencyBanner clocks={clocksData} />

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

      {/* Options + input — sticky bottom */}
      {!loading && !storyOver && (
        <div style={{
          padding: "10px 20px 16px", borderTop: "2px solid var(--border)", flexShrink: 0,
          maxWidth: 1100, width: "100%", margin: "0 auto", boxSizing: "border-box", alignSelf: "stretch",
          background: "var(--bg)", position: "relative",
          boxShadow: "0 -4px 24px rgba(0,0,0,0.25)",
        }}>

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
              <div style={{
                display: "flex", alignItems: "center", gap: 8, marginBottom: 10,
              }}>
                <span style={{
                  fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.8,
                  color: "var(--text-secondary)", opacity: 0.7,
                }}>Scegli l'azione di</span>
                <span style={{
                  fontSize: 12, fontWeight: 800, color: "var(--accent)",
                  padding: "2px 8px", borderRadius: 5,
                  background: "var(--accent-bg)", border: "1px solid var(--accent-border)",
                }}>{activePlayer?.name}</span>
                <span style={{ fontSize: 11, color: "var(--text-secondary)", opacity: 0.5, marginLeft: "auto" }}>
                  o scrivi sotto ↓
                </span>
              </div>
              <OptionsBar options={options} players={players} onChoose={handleOptionClick} />
            </>
          )}
          {(pendingOption || options.length === 0) && (
            <div style={{ position: "relative" }}>
              {previewData !== null && (
                <div style={{
                  position: "absolute", bottom: "calc(100% + 8px)", left: 0, right: 0,
                  background: "var(--bg)", border: "1px solid var(--border)", borderRadius: 12,
                  padding: "12px 14px", zIndex: 50, boxShadow: "0 -4px 24px rgba(0,0,0,0.4)",
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-h)" }}>
                      {previewData.available === false
                        ? "⚠ Anteprima non disponibile"
                        : `${previewData.action?.name || "Azione"} · ${previewData.action?.stat || ""} / ${previewData.action?.skill || ""}`}
                    </div>
                    <button onClick={() => setPreviewData(null)} style={{ background: "none", border: "none", color: "var(--text)", fontSize: 16, cursor: "pointer", lineHeight: 1, padding: "0 4px" }}>×</button>
                  </div>
                  {previewData.available === false ? (
                    <div style={{ fontSize: 11, color: "var(--text)", opacity: 0.7 }}>{previewData.reason || "Nessuna anteprima disponibile."}</div>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
                      {(previewData.rows || []).map(row => {
                        const colorMap = { "critico": "#f59e0b", "successo pieno": "#4ade80", "successo parziale": "#60a5fa", "fallimento": "#ef4444" };
                        const color = colorMap[row.key] || "var(--text)";
                        const pct = row.probability ?? 0;
                        return (
                          <div key={row.key} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <div style={{ width: 120, fontSize: 10, color: "var(--text)", opacity: 0.8, flexShrink: 0, textTransform: "capitalize" }}>{row.label}</div>
                            <div style={{ flex: 1, height: 6, borderRadius: 4, background: "rgba(255,255,255,0.08)", overflow: "hidden" }}>
                              <div style={{ height: "100%", width: `${pct}%`, background: color, transition: "width 0.4s" }} />
                            </div>
                            <div style={{ width: 34, fontSize: 10, color, fontWeight: 700, textAlign: "right", flexShrink: 0 }}>{pct}%</div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
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
                <button
                  type="button"
                  onClick={handlePreviewAction}
                  disabled={!customText.trim() || previewLoading}
                  style={{
                    padding: "11px 13px", borderRadius: 10, border: "1px solid var(--border)",
                    background: "var(--bg)", color: "var(--text)", fontSize: 12, cursor: customText.trim() && !previewLoading ? "pointer" : "not-allowed",
                    opacity: customText.trim() && !previewLoading ? 1 : 0.45, whiteSpace: "nowrap",
                  }}
                >{previewLoading ? "…" : "Anteprima"}</button>
                <button type="submit" disabled={!customText.trim()} style={{
                  padding: "11px 20px", borderRadius: 10, border: "none",
                  background: customText.trim() ? "var(--accent)" : "var(--border)",
                  color: "#fff", fontWeight: 700, cursor: customText.trim() ? "pointer" : "not-allowed",
                }}>Invia 🎲</button>
              </form>
            </div>
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

          {/* Spiegazione principale — perché si è vinto/perso */}
          {endReason && (
            <div style={{
              maxWidth: 480, margin: "0 auto 18px", padding: "14px 18px",
              borderRadius: 10, textAlign: "left",
              background: victory ? "rgba(74,222,128,0.08)" : "rgba(248,113,113,0.08)",
              border: `1px solid ${victory ? "rgba(74,222,128,0.25)" : "rgba(248,113,113,0.25)"}`,
            }}>
              <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1, marginBottom: 6, color: victory ? "#4ade80" : "#f87171" }}>
                {victory ? "Come avete vinto" : "Come avete perso"}
              </div>
              <div style={{ fontSize: 13, color: "var(--text)", lineHeight: 1.6 }}>{endReason}</div>
            </div>
          )}

          {adventure?.win_condition && (
            <div style={{ fontSize: 12, color: "var(--text)", maxWidth: 420, margin: "0 auto 16px", lineHeight: 1.5, opacity: 0.7 }}>
              Obiettivo: {victory ? "✅" : "❌"} {adventure.win_condition}
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

      {/* ── SidePanel come drawer overlay (non comprime la chat) ───────────── */}
      {showPanel && adventure && (
        <>
          {/* Backdrop semitrasparente */}
          <div
            onClick={() => setShowPanel(false)}
            style={{
              position: "fixed", inset: 0, zIndex: 300,
              background: "rgba(0,0,0,0.45)",
              backdropFilter: "blur(2px)",
            }}
          />
          {/* Drawer */}
          <div style={{
            position: "fixed", top: 0, right: 0, bottom: 0, zIndex: 301,
            width: "min(480px, 92vw)",
            boxShadow: "-4px 0 32px rgba(0,0,0,0.6)",
            display: "flex", flexDirection: "column",
            animation: "slideInRight 0.22s ease",
          }}>
            <style>{`@keyframes slideInRight { from { transform: translateX(100%) } to { transform: translateX(0) } } @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.55} }`}</style>
            <SidePanel
              adventure={adventure}
              gameState={gameStateData}
              mapState={mapState}
              clocksData={clocksData}
              gmEventLog={gmEventLog}
              backdropImage={adventureMapBackdrop}
              mapPositions={adventureMapPositions}
              onMove={(id) => { handleMoveToLocation(id); setShowPanel(false); }}
              onOpenMap={() => { setShowMapPanel(true); setShowPanel(false); }}
              preparedTacticalMaps={preparedTacticalMaps}
              preparingTacticalMaps={preparingTacticalMaps}
              onPrepareTacticalMap={prepareTacticalMapForNode}
              players={players}
              avatars={avatars}
              npcAvatars={npcAvatars}
              npcStatuses={gameStateData?.npc_statuses}
              advNpcs={adventure?.adventure_definition?.actors || adventure?.adventure_definition?.npcs || []}
              onClose={() => setShowPanel(false)}
              defaultTab={undefined}
              mode="gm"
              onDeduce={handleDeduce}
            />
          </div>
        </>
      )}

      {/* ── PlayerPanel — drawer SINISTRO (Diario del gruppo) ─────────────────── */}
      {showPlayerPanel && adventure && (
        <>
          <div
            onClick={() => setShowPlayerPanel(false)}
            style={{ position: "fixed", inset: 0, zIndex: 300, background: "rgba(0,0,0,0.45)", backdropFilter: "blur(2px)" }}
          />
          <div style={{
            position: "fixed", top: 0, left: 0, bottom: 0, zIndex: 301,
            width: "min(520px, 92vw)",
            boxShadow: "4px 0 32px rgba(0,0,0,0.6)",
            display: "flex", flexDirection: "column",
            animation: "slideInLeft 0.22s ease",
          }}>
            <style>{`@keyframes slideInLeft { from { transform: translateX(-100%) } to { transform: translateX(0) } }`}</style>
            <SidePanel
              adventure={adventure}
              gameState={gameStateData}
              mapState={mapState}
              clocksData={clocksData}
              gmEventLog={gmEventLog}
              backdropImage={adventureMapBackdrop}
              mapPositions={adventureMapPositions}
              onMove={(id) => { handleMoveToLocation(id); setShowPlayerPanel(false); }}
              onOpenMap={() => { setShowMapPanel(true); setShowPlayerPanel(false); }}
              preparedTacticalMaps={preparedTacticalMaps}
              preparingTacticalMaps={preparingTacticalMaps}
              onPrepareTacticalMap={prepareTacticalMapForNode}
              players={players}
              avatars={avatars}
              npcAvatars={npcAvatars}
              npcStatuses={gameStateData?.npc_statuses}
              advNpcs={adventure?.adventure_definition?.actors || adventure?.adventure_definition?.npcs || []}
              onClose={() => setShowPlayerPanel(false)}
              defaultTab={panelOpenTab}
              mode="players"
              onDeduce={handleDeduce}
            />
          </div>
        </>
      )}

      {showSecrets && adventure && (
        <SecretsPanel adventure={adventure} gameState={gameStateData} onClose={() => setShowSecrets(false)} />
      )}
      <ClockToastOverlay
        toasts={clockToasts}
        onDismiss={id => setClockToasts(prev => prev.filter(t => t.id !== id))}
      />
      <NpcEventToastOverlay
        toasts={npcEventToasts}
        onDismiss={id => setNpcEventToasts(prev => prev.filter(t => t.id !== id))}
      />
      {showMapPanel && adventure && mapState && (
        <FloatingMapPanel
          mapState={mapState}
          backdropImage={adventureMapBackdrop}
          mapPositions={adventureMapPositions}
          onMove={handleMoveToLocation}
          isGM={true}
          players={players}
          avatars={avatars}
          npcStatuses={gameStateData?.npc_statuses}
          advNpcs={adventure?.adventure_definition?.actors || adventure?.adventure_definition?.npcs || []}
          onClose={() => setShowMapPanel(false)}
        />
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

  // ── Auto-resume: se il backend ha già una partita in corso, riprendi ──────
  useEffect(() => {
    async function tryResume() {
      try {
        const gs = await fetch(`${API_URL}/game/state`).then(r => r.json());
        if (!gs.players?.length) return; // nessuna partita attiva
        const advId = gs.adventure_definition_id;
        if (!advId) return;
        // Carica la definizione avventura
        const advRes = await fetch(`${API_URL}/game/adventure/runtime`).then(r => r.json());
        const allItems = advRes.items || [];
        const found = allItems.find(a => a.id === advId);
        if (!found) return;
        // Carica la definizione completa
        const defRes = await fetch(`${API_URL}/game/adventure/runtime/${advId}`).catch(() => null);
        const defJson = defRes ? await defRes.json() : found;
        const advDef = defJson.adventure_definition || defJson;
        const detectedGenre = advDef.genre || found.genre || "action";
        setGenre(detectedGenre);
        setPlayers(gs.players);
        setAdventure(advDef);
        setScreen("game");
      } catch (_) {}
    }
    tryResume();
  }, []);

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
      throw new Error("Flusso non valido: l'avventura deve essere compilata prima dell'avvio.");
    }
  }

  function handleRestart() {
    setAdventure(null);
    setScreen("setup");
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
        onRestart={handleRestart}
      />
    );
  }
  return <SetupScreen onStart={handleSetupComplete} />;
}
