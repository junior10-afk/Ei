"""Listage en direct des modèles offerts par chaque fournisseur d'API.

Au lieu d'un catalogue figé dans le code, on interroge l'API du fournisseur
avec la clé enregistrée : la liste renvoyée est celle, officielle et à jour,
des modèles que Google/Groq/OpenAI/Mistral proposent réellement aujourd'hui.
Les modèles non-textuels (embedding, vidéo, image, TTS, temps réel...) sont
filtrés pour ne garder que ce qui peut dialoguer.
"""
import os
import re
from typing import Dict, List

import requests
from core.config import config

PROVIDER_KEY_ENV: Dict[str, str] = {
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "openai": "OPENAI_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "xai": "XAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}

# Endpoints /models des APIs compatibles OpenAI (+ customs via config custom_endpoints)
OPENAI_COMPAT_MODELS_URLS: Dict[str, str] = {
    "groq": "https://api.groq.com/openai/v1/models",
    "openai": "https://api.openai.com/v1/models",
    "mistral": "https://api.mistral.ai/v1/models",
    "xai": "https://api.x.ai/v1/models",
    "openrouter": "https://openrouter.ai/api/v1/models",
}

# Modèles qui ne savent pas tenir une conversation (multimodal pur / utilitaires)
_NON_CHAT = re.compile(
    r"embedding|veo|tts|transcribe|\blive\b|image|nano-banana|omni|computer-use|"
    r"robotics|lyria|^aqa$|antigravity|deep-research|translate|rerank|shield",
    re.IGNORECASE,
)


def list_provider_models(provider: str) -> dict:
    """Retourne {ok, models: [{id, label, model}], message}.

    id est une référence dynamique 'provider/nom-du-modele' comprise par
    core.models (parse_tier_ref) et brain.llm (ask_with_model).
    """
    provider = (provider or "").lower()
    try:
        if provider == "gemini":
            return _list_gemini()
        if provider == "anthropic":
            return _list_anthropic()
        if provider == "ollama":
            return _list_ollama()
        return _list_openai_compat(provider)
    except Exception as e:
        return {"ok": False, "models": [], "message": str(e)[:180]}


def _list_gemini() -> dict:
    key = config.gemini_api_key or os.getenv("GEMINI_API_KEY", "").strip().strip('"\'')
    if not key:
        return {"ok": False, "models": [], "message": "Aucune clé Gemini enregistrée."}
    models: List[dict] = []
    page_token = ""
    for _ in range(6):  # garde-fou pagination
        params = {"key": key, "pageSize": 200}
        if page_token:
            params["pageToken"] = page_token
        res = requests.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params=params, timeout=15,
        )
        if res.status_code != 200:
            return {"ok": False, "models": [],
                    "message": f"HTTP {res.status_code} — clé invalide ou réseau ?"}
        data = res.json()
        for m in data.get("models", []):
            name = m.get("name", "").replace("models/", "")
            methods = m.get("supported_generation_methods") or m.get("supportedGenerationMethods") or []
            if "generateContent" not in methods:
                continue
            if _NON_CHAT.search(name):
                continue
            label = m.get("displayName") or name
            models.append({"id": f"gemini/{name}", "label": label, "model": name})
        page_token = data.get("nextPageToken") or ""
        if not page_token:
            break
    return {"ok": True, "models": models, "message": f"{len(models)} modèle(s) disponibles."}


def _list_openai_compat(provider: str) -> dict:
    key_env = PROVIDER_KEY_ENV.get(provider)
    if not key_env:
        # Endpoint custom déclaré en config (custom_endpoints: {nom: {base_url, key_env}})
        custom = config.get("custom_endpoints", {}) or {}
        entry = custom.get(provider) or {}
        key_env = str(entry.get("key_env", "")).strip()
        base = str(entry.get("base_url", "")).strip().rstrip("/")
        if not key_env or not base:
            return {"ok": False, "models": [], "message": "Fournisseur inconnu."}
        models_url = base + "/models"
    else:
        models_url = OPENAI_COMPAT_MODELS_URLS.get(provider, "")
        if not models_url:
            return {"ok": False, "models": [], "message": "Fournisseur inconnu."}
    key = os.getenv(key_env, "").strip().strip(chr(34) + chr(39))
    if not key:
        return {"ok": False, "models": [], "message": f"Aucune clé {provider} enregistrée."}
    res = requests.get(models_url, headers={"Authorization": f"Bearer {key}"}, timeout=15)
    if res.status_code != 200:
        return {"ok": False, "models": [],
                "message": f"HTTP {res.status_code} — clé invalide ou réseau ?"}
    models = []
    for m in res.json().get("data", []):
        name = m.get("id") or ""
        if not name or _NON_CHAT.search(name):
            continue
        models.append({"id": f"{provider}/{name}", "label": name, "model": name})
    models.sort(key=lambda x: x["id"])
    return {"ok": True, "models": models, "message": f"{len(models)} modèle(s) disponibles."}


def _list_anthropic() -> dict:
    key = (config.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")).strip()
    if not key:
        return {"ok": False, "models": [], "message": "Aucune clé anthropic enregistrée."}
    res = requests.get(
        "https://api.anthropic.com/v1/models",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
        timeout=15,
    )
    if res.status_code != 200:
        return {"ok": False, "models": [],
                "message": f"HTTP {res.status_code} — clé invalide ou réseau ?"}
    models = []
    for m in res.json().get("data", []):
        name = m.get("id") or ""
        if not name or _NON_CHAT.search(name):
            continue
        models.append({"id": f"anthropic/{name}", "label": name, "model": name})
    models.sort(key=lambda x: x["id"])
    return {"ok": True, "models": models, "message": f"{len(models)} modèle(s) disponibles."}


def _list_ollama() -> dict:
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").replace("/v1", "")
    try:
        res = requests.get(f"{base}/api/tags", timeout=5)
    except Exception:
        return {"ok": False, "models": [], "message": "Ollama injoignable (lancez « ollama serve »)."}
    if res.status_code != 200:
        return {"ok": False, "models": [], "message": f"HTTP {res.status_code}"}
    models = []
    for m in res.json().get("models", []):
        name = m.get("name", "")
        if name:
            models.append({"id": f"ollama/{name}", "label": f"{name} (local)", "model": name})
    return {"ok": True, "models": models, "message": f"{len(models)} modèle(s) locaux."}
