"""Il doctor deve sviluppare i PNG "piatti" anche se hanno già i campi tattici.

Prima, _enrich_npc scattava solo per gli attori segnalati dall'audit (pressure/
reaction/goal mancanti). Un PNG importato con i campi tattici già presenti ma
descrizione/movente/segreto vuoti non veniva mai approfondito. Ora _npc_needs_depth
lo intercetta, e il merge riempie solo i campi narrativi scarni senza toccare
quelli già ricchi.
"""
import json

import App.adventure_doctor as doc


def test_npc_needs_depth_detects_thin_only():
    thin = {"id": "a1", "description": "", "motivation": "breve"}
    rich = {
        "id": "a2",
        "description": "Un veterano sfregiato dalla guerra, parla piano ma con autorità glaciale.",
        "motivation": "Vendetta contro chi ha bruciato il suo villaggio molti anni fa.",
        "secret": "È il fratello perduto del duca, creduto morto in battaglia.",
    }
    assert doc._npc_needs_depth(thin) is True
    assert doc._npc_needs_depth(rich) is False


def test_enrich_npc_fills_thin_but_preserves_rich(monkeypatch):
    fake = json.dumps({
        "pressure_response": {"low": "a", "medium": "b", "high": "c", "extreme": "d"},
        "reaction_table": {"se_minacciato": "x", "se_alleato": "y"},
        "current_plan": "piano concreto",
        "fallback_plan": "piano di riserva",
        "description": "NUOVA descrizione generata dall'AI, abbastanza lunga da contare.",
        "motivation": "NUOVO movente profondo generato dall'AI.",
        "secret": "NUOVO segreto sfruttabile generato dall'AI.",
    })
    monkeypatch.setattr(doc, "_llm", lambda *a, **k: fake)

    # PNG magro → i campi narrativi vengono riempiti
    thin = {"id": "a1", "name": "Tizio", "description": "", "motivation": "", "secret": ""}
    out = doc._enrich_npc(thin, "ctx")
    assert "NUOVA descrizione" in out["description"]
    assert out["current_plan"] == "piano concreto"
    assert out["llm_enriched"] is True

    # PNG già ricco → descrizione/movente/segreto originali NON sovrascritti…
    orig_desc = "Un veterano sfregiato dalla guerra, parla piano ma con autorità glaciale."
    rich = {"id": "a2", "name": "Caio", "description": orig_desc,
            "motivation": "m" * 60, "secret": "s" * 60}
    out2 = doc._enrich_npc(rich, "ctx")
    assert out2["description"] == orig_desc
    assert out2["motivation"] == "m" * 60
    # …ma i campi tattici mancanti vengono comunque aggiunti
    assert out2["current_plan"] == "piano concreto"
