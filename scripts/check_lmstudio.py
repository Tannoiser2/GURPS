#!/usr/bin/env python3
"""
Health-check del motore LLM locale LM Studio.

Verifica, PRIMA di avviare una partita, che il server LM Studio sia raggiungibile
e che un modello sia caricato — così eviti sessioni che falliscono a metà turno
perché il server era spento o senza modello.

Uso:
    python scripts/check_lmstudio.py

Legge le stesse env del backend (LMSTUDIO_BASE_URL, LMSTUDIO_MODEL, ...).
Fa una piccola chiamata di completamento reale per confermare che il modello risponda.
Exit code 0 = ok, 1 = problema (utile in script/CI).
"""

import os
import sys

BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
MODEL = os.getenv("LMSTUDIO_MODEL", "local-model")
API_KEY = os.getenv("LMSTUDIO_API_KEY", "lm-studio")
TIMEOUT = float(os.getenv("LMSTUDIO_TIMEOUT", "60"))


def main() -> int:
    print(f"[check] LM Studio base_url = {BASE_URL}")
    try:
        import openai
    except Exception as e:  # pragma: no cover - dipende dall'ambiente
        print(f"[FAIL] SDK openai non installato: {e}")
        print("       pip install openai")
        return 1

    client = openai.OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=TIMEOUT)

    # 1) Quali modelli sono caricati?
    try:
        models = client.models.list()
        loaded = [m.id for m in getattr(models, "data", [])]
    except Exception as e:
        print(f"[FAIL] Server non raggiungibile su {BASE_URL}: {e}")
        print("       Apri LM Studio → tab Developer → Start Server.")
        return 1

    if not loaded:
        print("[FAIL] Server attivo ma nessun modello caricato.")
        print("       Carica un modello in LM Studio prima di giocare.")
        return 1
    print(f"[ok]   Modelli disponibili: {', '.join(loaded)}")

    # 2) Chiamata di completamento reale (verifica che il modello risponda).
    target = MODEL if MODEL in loaded else loaded[0]
    if MODEL not in loaded:
        print(f"[warn] LMSTUDIO_MODEL='{MODEL}' non corrisponde: uso '{target}'.")
    try:
        resp = client.chat.completions.create(
            model=target,
            max_tokens=16,
            messages=[{"role": "user", "content": "Rispondi solo con: OK"}],
        )
        text = (resp.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"[FAIL] Il modello non ha risposto: {e}")
        return 1

    print(f"[ok]   Risposta del modello: {text!r}")
    print("[✓] LM Studio pronto. Metti LMSTUDIO_ENABLED=1 e avvia il backend.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
