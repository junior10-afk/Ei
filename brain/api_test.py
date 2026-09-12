"""Test de validité des clés API sans redémarrer Ei.

Chaque fournisseur reçoit une requête minimale ("ping") ; le résultat
(ok / erreur + message court) est renvoyé au HUD.
"""
import os
from typing import Optional

import requests
from core.config import config


def test_api_key(provider: str) -> dict:
    provider = (provider or "").lower()
    try:
        if provider == "gemini":
            return _test_gemini()
        if provider == "groq":
            return _test_openai_compat("groq", config.groq_api_key or os.getenv("GROQ_API_KEY", ""),
                                       "https://api.groq.com/openai/v1/models")
        if provider == "openai":
            return _test_openai_compat("openai", config.openai_api_key or os.getenv("OPENAI_API_KEY", ""),
                                        "https://api.openai.com/v1/models")
        if provider == "mistral":
            return _test_openai_compat("mistral", config.mistral_api_key or os.getenv("MISTRAL_API_KEY", ""),
                                        "https://api.mistral.ai/v1/models")
        if provider == "ollama":
            return _test_ollama()
        return {"provider": provider, "ok": False, "message": "Fournisseur inconnu."}
    except Exception as e:
        return {"provider": provider, "ok": False, "message": str(e)[:160]}


def _test_gemini() -> dict:
    key = (config.gemini_api_key or os.getenv("GEMINI_API_KEY", "")).strip().strip('"\'')
    if not key:
        return {"provider": "gemini", "ok": False, "message": "Clé vide."}
    url = "https://generativelanguage.googleapis.com/v1beta/models?key=" + key
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return {"provider": "gemini", "ok": True, "message": "Connexion réussie."}
        return {"provider": "gemini", "ok": False,
                "message": f"HTTP {res.status_code} — clé invalide ?"}
    except Exception as e:
        return {"provider": "gemini", "ok": False, "message": str(e)[:160]}


def _test_openai_compat(provider: str, key: str, models_url: str) -> dict:
    if not key:
        return {"provider": provider, "ok": False, "message": "Clé vide."}
    try:
        res = requests.get(models_url, headers={"Authorization": f"Bearer {key}"}, timeout=10)
        if res.status_code == 200:
            return {"provider": provider, "ok": True, "message": "Connexion réussie."}
        return {"provider": provider, "ok": False,
                "message": f"HTTP {res.status_code} — clé invalide ?"}
    except Exception as e:
        return {"provider": provider, "ok": False, "message": str(e)[:160]}


def _test_ollama() -> dict:
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").replace("/v1", "")
    try:
        res = requests.get(f"{base}/api/tags", timeout=5)
        if res.status_code == 200:
            models = [m.get("name", "") for m in res.json().get("models", [])]
            return {"provider": "ollama", "ok": True,
                    "message": f"Local OK — {len(models)} modèle(s): {', '.join(models[:4])}"}
        return {"provider": "ollama", "ok": False, "message": f"HTTP {res.status_code}"}
    except Exception:
        return {"provider": "ollama", "ok": False,
                "message": "Ollama injoignable (lancez « ollama serve »)."}
