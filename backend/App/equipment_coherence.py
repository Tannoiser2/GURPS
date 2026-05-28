"""
Coerenza equipaggiamento/armi per genere avventura.
- validate_gear_for_genre: avvisa se un item/arma non è coerente col genere
- assign_starter_items:    suggerisce l'equipaggiamento iniziale per archetipo + genere
"""

from __future__ import annotations

from .data_weapons import (
    GENRE_ERA_MAP, WEAPON_BY_ID, item_to_weapon_id,
    default_weapon_for_archetype,
)
from .data_items import ITEM_CATALOG, _ALIAS_TO_ITEM_ID


# ─── Equipaggiamento di base per genere ──────────────────────────────────────
# Ogni lista usa item_id dal catalogo.
_GENRE_BASE_ITEMS: dict[str, list[str]] = {
    "fantasy":            ["kit_medico", "torcia", "corda"],
    "medievale":          ["kit_medico", "torcia", "corda"],
    "storico":            ["kit_medico", "torcia", "corda"],
    "horror":             ["kit_medico", "torcia"],
    "detective_classico": ["kit_medico", "torcia", "binocolo"],
    "western":            ["kit_medico", "torcia", "corda"],
    "sci_fi":             ["kit_medico", "scanner", "radio_tattica"],
    "cyberpunk":          ["kit_medico", "computer_portatile", "radio_tattica"],
    "steampunk":          ["kit_medico", "torcia", "corda"],
    "post_apocalypse":    ["kit_medico", "torcia", "radio_tattica"],
    "spy":                ["kit_medico", "binocolo", "radio_tattica"],
    "action":             ["kit_medico", "radio_tattica"],
    "thriller":           ["kit_medico", "torcia"],
    "militare":           ["kit_medico", "radio_tattica", "maschera_antigas"],
    "romance":            ["kit_medico"],
}

# Extra item per archetipo (in aggiunta al base-kit del genere).
# Armature e scudi vengono filtrati per era prima di essere assegnati.
_ARCHETYPE_EXTRA: dict[str, list[str]] = {
    "warrior":    ["cotta_maglia"],
    "knight":     ["corazza_piastre", "scudo_medio"],
    "ranger":     ["armatura_cuoio"],
    "rogue":      ["armatura_cuoio", "grimaldelli"],
    "mage":       [],
    "cleric":     ["armatura_cuoio"],
    "penitent":   [],
    "barbarian":  [],
    "pikeman":    ["cotta_maglia"],
    "halberdier": ["cotta_maglia"],
    "detective":  ["binocolo"],
    "inspector":  ["binocolo"],
    "journalist": [],
    "forensic":   ["kit_medico"],
    "marine":     ["giubbotto_tattico", "radio_tattica"],
    "soldier":    ["giubbotto_antiproiettile", "radio_tattica"],
    "medic":      ["kit_medico"],
    "field_medic":["kit_medico"],
    "sniper":     ["occhiali_notturni"],
    "sharpshooter":["occhiali_notturni"],
    "scout":      ["occhiali_notturni"],
    "hacker":     ["computer_portatile"],
    "agent":      ["radio_tattica", "binocolo", "documento_falso"],
    "operative":  ["radio_tattica", "binocolo"],
    "pilot":      ["scanner", "radio_tattica"],
    "partisan":   ["kit_medico"],
    "rifleman":   ["giubbotto_antiproiettile"],
    "hunter":     ["armatura_cuoio"],
    "gunslinger": [],
    "cowboy":     [],
    "thug":       [],
    "guard":      ["giubbotto_antiproiettile"],
    "boss":       [],
    "antagonist": [],
    "antagonista":[],
    "shaman":     [],
    "archer":     ["armatura_cuoio"],
}


def _item_name_to_id(name: str) -> str | None:
    """Risolve un nome libero in un item_id tramite l'indice alias."""
    return _ALIAS_TO_ITEM_ID.get(name.lower().strip())


# ─── Controllo coerenza ───────────────────────────────────────────────────────

def validate_gear_for_genre(item_names: list[str], genre: str) -> list[str]:
    """
    Controlla se ogni item/arma è compatibile col genere dell'avventura.
    Ritorna lista di stringhe di warning (vuota = tutto OK).

    Regola:
    - Weapons: le 'eras' del weapon devono avere almeno un overlap con le eras del genere.
    - Items: se l'item ha 'eras' non vuoto, almeno una era deve matchare il genere.
      Se 'eras' è vuoto/assente, l'item è universale → nessun warning.
    """
    warnings: list[str] = []
    era_set = set(GENRE_ERA_MAP.get(genre, []))
    if not era_set:
        return warnings  # genere sconosciuto, non possiamo validare

    for raw in item_names:
        # Prova come arma
        wid = item_to_weapon_id(raw)
        if wid:
            weapon = WEAPON_BY_ID.get(wid)
            if weapon:
                w_eras = set(weapon.get("eras", []))
                if w_eras and not (w_eras & era_set):
                    warnings.append(
                        f"⚠ '{raw}' ({weapon['name']}) non è coerente col genere '{genre}' "
                        f"(era {list(w_eras)} vs {list(era_set)})"
                    )
            continue

        # Prova come item catalogo
        iid = _item_name_to_id(raw) or (raw if raw in ITEM_CATALOG else None)
        if iid:
            item = ITEM_CATALOG.get(iid, {})
            i_eras = item.get("eras", [])
            if i_eras and not (set(i_eras) & era_set):
                warnings.append(
                    f"⚠ '{raw}' ({item.get('name', iid)}) non è coerente col genere '{genre}'"
                )

    return warnings


# ─── Assegnazione equipaggiamento iniziale ────────────────────────────────────

def assign_starter_items(archetype: str, genre: str) -> list[str]:
    """
    Restituisce la lista di item_id appropriati per l'archetipo nel genere dato.
    - Base kit dal genere
    - Extra items per archetipo, filtrati per coerenza con il genere
    Ogni item_id appare al massimo una volta.
    """
    era_set = set(GENRE_ERA_MAP.get(genre, []))
    base = list(_GENRE_BASE_ITEMS.get(genre, ["kit_medico", "torcia"]))
    extras = list(_ARCHETYPE_EXTRA.get(archetype.lower(), []))

    # Filtra gli extra per coerenza di era
    filtered_extras: list[str] = []
    for iid in extras:
        item = ITEM_CATALOG.get(iid, {})
        i_eras = item.get("eras", [])
        if not i_eras or not era_set or (set(i_eras) & era_set):
            filtered_extras.append(iid)

    # Deduplica preservando l'ordine
    seen: set[str] = set()
    result: list[str] = []
    for iid in base + filtered_extras:
        if iid not in seen:
            seen.add(iid)
            result.append(iid)

    return result


def starter_item_names(archetype: str, genre: str) -> list[str]:
    """
    Come assign_starter_items ma ritorna i nomi italiani (per inserire in Player.items).
    """
    ids = assign_starter_items(archetype, genre)
    names: list[str] = []
    for iid in ids:
        item = ITEM_CATALOG.get(iid)
        if item:
            names.append(item["name"])
    return names
