"""Mappatura azione-di-viaggio → location_id (puro, senza dipendenze pesanti).

Estratto da claude_service così da essere testabile senza la catena di import
del motore. Usato sia dal director ("bible" engine) sia da _update_map_position
in main.py per aggiornare la posizione del gruppo.
"""
from __future__ import annotations

import re

# Verbi che esprimono un INTENTO DI VIAGGIO: solo se l'azione inizia con uno di
# questi proviamo a cambiare la location. Evita falsi spostamenti su azioni come
# "Consultare gli articoli su Corbitt" o "Osservare la dimora" (che condividono
# parole coi nomi delle location ma NON sono movimenti).
_TRAVEL_INTENT_RE = re.compile(
    r"^\s*(?:spostars[it]\w*|spostati|recars[it]\w*|recati|tornare|ritornare|"
    r"andare|vai|vado|dirigers[it]\w*|raggiunger\w*|entrare|entra|visitare|visita|"
    r"muovers[it]\w*|portars[it]\w*|avvicinars[it]\w*|prosegui\w*|proseguire|recarsi)\b",
    re.IGNORECASE,
)

_DEST_STOPWORDS = {
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "di", "del", "della",
    "dello", "dei", "degli", "delle", "a", "al", "allo", "alla", "ai", "agli",
    "alle", "da", "dal", "in", "nel", "nella", "con", "su", "sul", "per", "e",
    "the", "of", "to", "vecchia", "vecchio", "old", "casa",
}


def _significant_words(s: str) -> list[str]:
    return [w for w in re.findall(r"[a-zà-ÿ0-9]+", (s or "").lower())
            if w not in _DEST_STOPWORDS and len(w) > 2]


def match_destination(action_text: str, candidates: list[tuple[str, str]]) -> str | None:
    """Mappa un'azione di viaggio in prosa al location_id di destinazione.

    candidates: lista di (location_id, location_name).
    Ritorna l'id della location il cui NOME ha la massima sovrapposizione di
    parole significative con l'azione — ma solo se l'azione esprime un intento
    di viaggio (vedi _TRAVEL_INTENT_RE). Ritorna None se nessuna corrisponde,
    così il chiamante può lasciare invariata la posizione corrente.

    Robusto alle frasi lunghe ("Tornare alla dimora di Corbitt armato delle
    informazioni — è tempo di esplorare la cantina") perché lavora per
    sovrapposizione di parole, non per substring dell'intera coda. A parità,
    privilegia la location nominata PRIMA (la meta è di norma il primo nome
    dopo il verbo: "Visitare il Vicinato della dimora di Corbitt" → il Vicinato).
    """
    if not _TRAVEL_INTENT_RE.search(action_text or ""):
        return None
    tokens = re.findall(r"[a-zà-ÿ0-9]+", (action_text or "").lower())
    action_words = {w for w in tokens if w not in _DEST_STOPWORDS and len(w) > 2}
    if not action_words:
        return None
    best_id: str | None = None
    best_key: tuple[int, int] | None = None
    for cid, name in candidates:
        name_words = set(_significant_words(name))
        if not name_words:
            continue
        overlap = sum(1 for w in name_words if w in action_words)
        if overlap == 0:
            continue
        # Accetta solo match consistenti: o almeno 2 parole in comune, o tutte
        # le parole del nome compaiono (location a parola singola tipo "Municipio").
        if overlap < 2 and overlap < len(name_words):
            continue
        first_pos = min(i for i, w in enumerate(tokens) if w in name_words)
        key = (-first_pos, overlap)  # first_pos più piccolo e overlap più alto = meglio
        if best_key is None or key > best_key:
            best_id, best_key = cid, key
    return best_id
