import os
import time
from typing import Optional, List, Dict
import requests
from core.config import config
from brain.prompt import build_system_prompt

class LLMCascade:
    def __init__(self):
        self.cooldowns: Dict[str, float] = {}

    def _is_available(self, provider: str) -> bool:
        until = self.cooldowns.get(provider, 0.0)
        return time.time() > until

    def _set_cooldown(self, provider: str, duration_sec: float = 60.0):
        self.cooldowns[provider] = time.time() + duration_sec
        print(f"[LLM] Cooldown appliqué sur {provider} pour {duration_sec}s.")

    def clear_cooldown(self, provider: Optional[str] = None):
        if provider:
            self.cooldowns.pop(provider, None)
            print(f"[LLM] Cooldown réinitialisé pour {provider}.")
        else:
            self.cooldowns.clear()
            print("[LLM] Tous les cooldowns ont été réinitialisés.")

    @property
    def history(self) -> List[Dict[str, str]]:
        """Lit l'historique conversationnel directement depuis la session persistée en base SQLite."""
        try:
            from brain.session_memory import session_memory
            return session_memory.get_recent_pairs(limit=6)
        except Exception:
            return []

    def add_history(self, role: str, text: str):
        """Enregistre le message dans la source unique de vérité SQLite."""
        try:
            from brain.session_memory import session_memory
            if role == "user":
                session_memory.add_user_message(text)
            elif role == "assistant":
                session_memory.add_assistant_message(text)
        except Exception:
            pass

    def _call_gemini(self, user_text: str, system_prompt: str, model: str = "gemini-2.5-flash",
                     max_tokens: int = 1024) -> Optional[str]:
        api_key = (config.gemini_api_key or os.getenv("GEMINI_API_KEY", "")).strip().strip('"\'')
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
            # Gestion de la réflexion (thinking) selon le modèle :
            # - Gemini 2.5 Flash accepte thinking_budget=0 pour réduire la latence.
            # - Gemini Pro accepte thinking_budget=128 pour borner la réflexion.
            # - Gemini 3.x Flash/Lite rejette thinking_budget=0 avec 400 INVALID_ARGUMENT (non supporté).
            if "2.5-flash" in model:
                cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
            elif "pro" in model:
                cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=128)

            try:
                response = client.models.generate_content(
                    model=model,
                    contents=full_user_msg,
                    config=types.GenerateContentConfig(**cfg_kwargs)
                )
            except Exception as e:
                err_str = str(e)
                # Si erreur de paramètre (ex: thinking_config rejeté sur ce modèle), réessayer immédiatement sans thinking_config
                if "thinking_config" in cfg_kwargs and ("INVALID_ARGUMENT" in err_str or "400" in err_str):
                    cfg_kwargs.pop("thinking_config", None)
                    response = client.models.generate_content(
                        model=model,
                        contents=full_user_msg,
                        config=types.GenerateContentConfig(**cfg_kwargs)
                    )
                else:
                    raise e

            if response and response.text:
                return response.text.strip()
            print(f"[LLM] Gemini ({model}) a renvoyé une réponse vide (finishReason="
                  f"{getattr(response, 'candidates', None) and response.candidates[0].finish_reason}).")
        except Exception as e:
            err_str = str(e)
            print(f"[LLM] Erreur Gemini ({model}): {err_str[:180]}")
            # Ne bloquer Gemini en cooldown que si la clé est invalide (403) ou si le modèle de base échoue
            if "API_KEY_INVALID" in err_str or "403" in err_str:
                self._set_cooldown("gemini", 120.0)
            elif model == "gemini-2.5-flash":
                self._set_cooldown("gemini", 30.0)
        return None

    def _call_gemini_with_tools(self, messages: List[Dict], system_prompt: str,
                                 gemini_tools, model: str = "gemini-2.5-flash",
                                 max_tokens: int = 2048):
        """
        Appel Gemini avec Native Function Calling.
        Retourne le response object complet (pas juste le texte) pour que l'agent loop
        puisse inspecter les function_calls dans les candidates.

        messages: liste de dicts {"role": "user"|"model"|"function", "parts": [...]}
        gemini_tools: résultat de tool_registry.get_gemini_tools()
        """
        api_key = (config.gemini_api_key or os.getenv("GEMINI_API_KEY", "")).strip().strip('"\'')
        if not api_key:
            return None

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)

            cfg_kwargs = dict(
                system_instruction=system_prompt,
                temperature=0.4,
                max_output_tokens=max(max_tokens, 1024),
                tools=gemini_tools or [],
            )

            # Thinking config selon le modèle
            if "2.5-flash" in model:
                cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
            elif "pro" in model:
                cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=256)

            try:
                response = client.models.generate_content(
                    model=model,
                    contents=messages,
                    config=types.GenerateContentConfig(**cfg_kwargs)
                )
            except Exception as e:
                err_str = str(e)
                if "thinking_config" in cfg_kwargs and ("INVALID_ARGUMENT" in err_str or "400" in err_str):
                    cfg_kwargs.pop("thinking_config", None)
                    response = client.models.generate_content(
                        model=model,
                        contents=messages,
                        config=types.GenerateContentConfig(**cfg_kwargs)
                    )
                else:
                    raise e

            return response

        except Exception as e:
            err_str = str(e)
            print(f"[LLM] Erreur Gemini FC ({model}): {err_str[:200]}")
            if "API_KEY_INVALID" in err_str or "403" in err_str:
                self._set_cooldown("gemini", 120.0)
            elif model == "gemini-2.5-flash":
                self._set_cooldown("gemini", 30.0)
        return None

    def _call_openai_with_tools(self, provider: str, base_url: str, api_key: str,
                                 model: str, messages: List[Dict], openai_tools: List[Dict],
                                 max_tokens: int = 2048):
        """
        Appel OpenAI-compatible avec Native Function Calling.
        Retourne le dict de response complet pour inspection des tool_calls.
        """
        api_key = (api_key or "").strip().strip('"\'')
        if not api_key:
            return None

        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.4,
                "max_tokens": max(max_tokens, 512),
                "tools": openai_tools,
                "tool_choice": "auto"
            }
            res = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=60)
            if res.status_code == 200:
                return res.json()
            else:
                print(f"[LLM] Erreur {provider} FC ({res.status_code}): {res.text[:200]}")
                self._set_cooldown(provider, 60.0)
        except Exception as e:
            print(f"[LLM] Exception {provider} FC: {str(e)[:200]}")
            self._set_cooldown(provider, 60.0)
        return None


    def _call_openai_compatible(self, provider: str, base_url: str, api_key: str, model: str, user_text: str, system_prompt: str,
                                max_tokens: int = 1024) -> Optional[str]:
        api_key = (api_key or "").strip().strip('"\'')
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
                "max_tokens": max(max_tokens, 512)
            }
            res = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=45)
            if res.status_code == 200:
                data = res.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                print(f"[LLM] Erreur {provider} ({res.status_code}): {res.text[:180]}")
                self._set_cooldown(provider, 60.0)
        except Exception as e:
            print(f"[LLM] Exception {provider}: {str(e)[:180]}")
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
        max_tokens = int(model.get("max_tokens", 2048))
        key_env = model.get("key_env") or ""
        api_key = (os.getenv(key_env, "") if key_env else "").strip().strip('"\'')

        if provider == "gemini":
            ans = self._call_gemini(user_text, system_prompt, model=model_name, max_tokens=max_tokens)
            # Si un modèle spécifique (ex: preview sans quota ou expérimental) échoue, repli immédiat sur gemini-2.5-flash
            if not ans and model_name != "gemini-2.5-flash":
                print(f"[LLM] Repli automatique de {model_name} vers gemini-2.5-flash...")
                ans = self._call_gemini(user_text, system_prompt, model="gemini-2.5-flash", max_tokens=max_tokens)
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
                                               user_text, system_prompt, max_tokens=max_tokens)
        return ans

    def ask_with_system(self, user_text: str, system_prompt: str) -> Optional[str]:
        """Cascade multi-providers avec un system prompt IMPOSÉ par l'appelant."""
        pref = config.get("preferred_brain", "gemini").lower()
        if pref in ["gemini", "auto"]:
            providers = ["gemini", "groq", "openai", "mistral", "ollama"]
        elif pref == "groq":
            providers = ["groq", "gemini", "openai", "ollama"]
        elif pref == "openai":
            providers = ["openai", "gemini", "groq", "ollama"]
        elif pref == "ollama":
            providers = ["ollama", "gemini", "groq"]
        else:
            providers = ["gemini", "groq", "openai", "ollama"]

        for prov in providers:
            if not self._is_available(prov):
                continue
            if prov == "gemini":
                ans = self._call_gemini(user_text, system_prompt)
            elif prov == "ollama":
                base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
                model = os.getenv("OLLAMA_MODEL", "llama3.2")
                ans = self._call_openai_compatible("ollama", base_url, "ollama", model,
                                                   user_text, system_prompt)
            else:
                base_urls = {
                    "groq": "https://api.groq.com/openai/v1",
                    "openai": "https://api.openai.com/v1",
                    "mistral": "https://api.mistral.ai/v1",
                }
                key_envs = {"groq": "GROQ_API_KEY", "openai": "OPENAI_API_KEY", "mistral": "MISTRAL_API_KEY"}
                default_models = {"groq": "llama-3.3-70b-versatile", "openai": "gpt-4o-mini",
                                  "mistral": "mistral-small-latest"}
                api_key = os.getenv(key_envs[prov], "")
                if not api_key:
                    continue
                ans = self._call_openai_compatible(prov, base_urls[prov], api_key,
                                                   default_models[prov], user_text, system_prompt)
            if ans:
                return ans
        return None

    def ask(self, user_text: str) -> str:
        """Exécute la cascade selon le cerveau préféré et les clés disponibles."""
        ans = self.ask_with_system(user_text, build_system_prompt())
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
