import os
import time
from typing import Optional, List, Dict
import requests
from core.config import config
from brain.prompt import build_system_prompt

class LLMCascade:
    def __init__(self):
        self.cooldowns: Dict[str, float] = {}
        self.history: List[Dict[str, str]] = []

    def _is_available(self, provider: str) -> bool:
        until = self.cooldowns.get(provider, 0.0)
        return time.time() > until

    def _set_cooldown(self, provider: str, duration_sec: float = 60.0):
        self.cooldowns[provider] = time.time() + duration_sec
        print(f"[LLM] Cooldown appliqué sur {provider} pour {duration_sec}s.")

    def add_history(self, role: str, text: str):
        self.history.append({"role": role, "text": text})
        if len(self.history) > 10:
            self.history.pop(0)

    def _call_gemini(self, user_text: str, system_prompt: str, model: str = "gemini-2.5-flash",
                     max_tokens: int = 1024) -> Optional[str]:
        api_key = config.gemini_api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            contents = []
            for item in self.history[-4:]:
                contents.append(f"{item['role'].capitalize()}: {item['text']}")
            contents.append(f"User: {user_text}")
            full_user_msg = "\n".join(contents)

            cfg_kwargs = dict(
                system_instruction=system_prompt,
                temperature=0.4,
                max_output_tokens=max(max_tokens, 1024),
            )
            # Gemini 2.5 "réfléchit" avant de répondre : ces tokens de réflexion
            # sont comptés dans max_output_tokens et peuvent vider la réponse
            # (texte vide -> faux échec -> message "renseignez une clé API").
            # On coupe la réflexion pour les modèles flash, et on la borne
            # pour les pro (budget minimal autorisé).
            if "pro" in model:
                cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=128)
            else:
                cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

            response = client.models.generate_content(
                model=model,
                contents=full_user_msg,
                config=types.GenerateContentConfig(**cfg_kwargs)
            )
            if response and response.text:
                return response.text.strip()
            print(f"[LLM] Gemini ({model}) a renvoyé une réponse vide (finishReason="
                  f"{getattr(response, 'candidates', None) and response.candidates[0].finish_reason}).")
        except Exception as e:
            print(f"[LLM] Erreur Gemini: {e}")
            self._set_cooldown("gemini", 60.0)
        return None

    def _call_openai_compatible(self, provider: str, base_url: str, api_key: str, model: str, user_text: str, system_prompt: str) -> Optional[str]:
        if not api_key:
            return None

        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            messages = [{"role": "system", "content": system_prompt}]
            for item in self.history[-4:]:
                role = "assistant" if item["role"] == "assistant" else "user"
                messages.append({"role": role, "content": item["text"]})
            messages.append({"role": "user", "content": user_text})

            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.4,
                "max_tokens": 250
            }
            res = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=10)
            if res.status_code == 200:
                data = res.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                print(f"[LLM] Erreur {provider} ({res.status_code}): {res.text}")
                self._set_cooldown(provider, 60.0)
        except Exception as e:
            print(f"[LLM] Exception {provider}: {e}")
            self._set_cooldown(provider, 60.0)
        return None

    def _call_ollama(self, user_text: str, system_prompt: str) -> Optional[str]:
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        try:
            return self._call_openai_compatible("ollama", base_url, "ollama", model, user_text, system_prompt)
        except Exception:
            return None

    def ask_with_model(self, user_text: str, model: Optional[Dict], system_prompt: str) -> Optional[str]:
        """Exécute une requête sur un modèle précis du catalogue (dict: provider/model/key_env).

        Retourne None si le modèle est indisponible (clé manquante, erreur API) :
        l'appelant doit alors replier sur ask() (cascade).
        """
        if not model:
            return None
        provider = (model.get("provider") or "").lower()
        model_name = model.get("model") or ""
        max_tokens = int(model.get("max_tokens", 300))
        key_env = model.get("key_env") or ""
        api_key = os.getenv(key_env, "") if key_env else ""

        if provider == "gemini":
            ans = self._call_gemini(user_text, system_prompt, model=model_name, max_tokens=max_tokens)
        elif provider == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            ans = self._call_openai_compatible("ollama", base_url, "ollama", model_name or "llama3.2",
                                               user_text, system_prompt)
        else:
            base_urls = {
                "groq": "https://api.groq.com/openai/v1",
                "openai": "https://api.openai.com/v1",
                "mistral": "https://api.mistral.ai/v1",
            }
            base_url = model.get("base_url") or base_urls.get(provider)
            if not base_url or not api_key:
                print(f"[LLM] Modèle {model.get('id')} indisponible (clé {key_env or 'N/A'} manquante).")
                return None
            ans = self._call_openai_compatible(provider, base_url, api_key, model_name,
                                               user_text, system_prompt)
        if ans:
            self.add_history("user", user_text)
            self.add_history("assistant", ans)
        return ans

    def ask(self, user_text: str) -> str:
        """Exécute la cascade selon le cerveau préféré et les clés disponibles."""
        system_prompt = build_system_prompt()
        pref = config.get("preferred_brain", "gemini").lower()

        # Liste des providers à tester dans l'ordre
        providers = []
        if pref in ["gemini", "auto"]:
            providers.extend(["gemini", "groq", "openai", "mistral", "ollama"])
        elif pref == "groq":
            providers.extend(["groq", "gemini", "openai", "ollama"])
        elif pref == "openai":
            providers.extend(["openai", "gemini", "groq", "ollama"])
        elif pref == "ollama":
            providers.extend(["ollama", "gemini", "groq"])
        else:
            providers = ["gemini", "groq", "openai", "ollama"]

        for prov in providers:
            if not self._is_available(prov):
                continue

            if prov == "gemini":
                ans = self._call_gemini(user_text, system_prompt)
                if ans:
                    self.add_history("user", user_text)
                    self.add_history("assistant", ans)
                    return ans

            elif prov == "groq":
                groq_key = config.groq_api_key or os.getenv("GROQ_API_KEY")
                if groq_key:
                    ans = self._call_openai_compatible("groq", "https://api.groq.com/openai/v1", groq_key, "llama-3.3-70b-versatile", user_text, system_prompt)
                    if ans:
                        self.add_history("user", user_text)
                        self.add_history("assistant", ans)
                        return ans

            elif prov == "openai":
                openai_key = config.openai_api_key or os.getenv("OPENAI_API_KEY")
                if openai_key:
                    ans = self._call_openai_compatible("openai", "https://api.openai.com/v1", openai_key, "gpt-4o-mini", user_text, system_prompt)
                    if ans:
                        self.add_history("user", user_text)
                        self.add_history("assistant", ans)
                        return ans

            elif prov == "mistral":
                mistral_key = config.mistral_api_key or os.getenv("MISTRAL_API_KEY")
                if mistral_key:
                    ans = self._call_openai_compatible("mistral", "https://api.mistral.ai/v1", mistral_key, "mistral-small-latest", user_text, system_prompt)
                    if ans:
                        self.add_history("user", user_text)
                        self.add_history("assistant", ans)
                        return ans

            elif prov == "ollama":
                ans = self._call_ollama(user_text, system_prompt)
                if ans:
                    self.add_history("user", user_text)
                    self.add_history("assistant", ans)
                    return ans

        # Fallback gracieux si aucune clé ou indisponible
        has_any_key = any([config.gemini_api_key, config.groq_api_key,
                           config.openai_api_key, config.mistral_api_key])
        if has_any_key:
            return "Les commandes locales fonctionnent, mais le modèle distant est momentanément indisponible (erreur API ou quota dépassé). Réessayez dans une minute."
        return "Toutes les commandes locales et outils fonctionnent. Pour les questions libres, veuillez renseigner une clé API dans le fichier .env."

llm_cascade = LLMCascade()
