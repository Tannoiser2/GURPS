"""Verifica che lo 'scrittore' (generatore di avventure) produca varietà.

Regressione per il mode-collapse: prima _pick_narrative_frame restituiva sempre
il PRIMO frame compatibile (deterministico) → ogni archetipo dava sempre la stessa
atmosfera. Ora la scelta è casuale tra i candidati pertinenti REALMENTE esistenti.
"""
from App import claude_service as cs


def _frame_key(frame: dict) -> str:
    for k, v in cs._FAMILY_NARRATIVE_FRAMES.items():
        if v is frame:
            return k
    return "?"


def test_pick_frame_returns_only_existing_frames():
    """Nessun candidato 'fantasma' (assedio/caccia/whodunit…) deve sfuggire."""
    valid = set(cs._FAMILY_NARRATIVE_FRAMES.keys())
    for arch in cs._ADVENTURE_ARCHETYPES:
        for genre in ("fantasy", "sci_fi", "horror", "investigation", "action", "romance"):
            for _ in range(20):
                frame = cs._pick_narrative_frame(arch, genre)
                assert _frame_key(frame) in valid


def test_pick_frame_is_varied_not_deterministic():
    """Per uno stesso archetipo+genere devono comparire più frame diversi."""
    arch = {"name": "Cospirazione al vertice"}
    seen = {_frame_key(cs._pick_narrative_frame(arch, "fantasy")) for _ in range(200)}
    # Prima della fix era sempre 1 solo ('politico'). Ora attesi >= 2.
    assert len(seen) >= 2, f"Frame ancora deterministico: {seen}"


def test_every_archetype_genre_has_a_frame_pool():
    """Ogni combinazione archetipo×genere produce un frame valido (mai crash/empty)."""
    for arch in cs._ADVENTURE_ARCHETYPES:
        for genre in ("fantasy", "sci_fi", "horror", "investigation", "action",
                      "romance", "mystery_horror", "detective_classico"):
            frame = cs._pick_narrative_frame(arch, genre)
            assert isinstance(frame, dict) and frame.get("premise_style")


def test_prompt_forbids_overused_patterns():
    """Il prompt di generazione vieta esplicitamente i cliché ripetuti."""
    scale_cfg = cs._COMPLEXITY_SCALES["compact"]
    template_key = next(iter(cs._STRUCTURAL_TEMPLATES))
    arch = cs._ADVENTURE_ARCHETYPES[0]
    frame = cs._pick_narrative_frame(arch, "fantasy")
    prompt = cs._build_create_adventure_prompt(
        "Fantasy", "3 giocatori", arch, template_key, scale_cfg, frame
    )
    low = prompt.lower()
    assert "cenere" in low          # vieta i titoli "Cenere"
    assert "conto alla rovescia" in low
    assert "trattato/accordo/negoziato" in low
