from __future__ import annotations

from .base import enrich_definition, build_runtime_support, validate_shape, suggest_missing_elements


def director_bias():
    return {
        "prefer_runtime_elements": True,
        "avoid_free_expansion": True,
    }
