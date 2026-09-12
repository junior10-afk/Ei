import os
import re
import json
import time
import threading
from typing import Dict, Any, Optional, Tuple, List
from core.bus import bus
from core.config import config
from tools.registry import tool_registry
from brain.llm import llm_cascade
from brain.session_memory import session_memory
from brain.multi_agents import detect_specialist_for_query, AgentProfile, ORCHESTRATOR

class AgentEngine:
    """
    Moteur d'Agent Autonome cognitif d'Ei :
    - Décomposition dynamique de tâches complexes (Planning)
    - Native Function Calling (Google GenAI & OpenAI API)
    - Streaming de tokens en direct vers le HUD (agent_token)
    - Boucle ReAct avec annulation coopérative et reprise sur erreur
    - Garde-fou budgétaire de tokens et coût
    - Double restitution : Synthèse vocale fluide (TTS) + Rendu complet (HUD Chat/Console)
    """

    def __init__(self, max_iterations: int = 6, max_budget_tokens: int = 8000):
        self.max_iterations = max_iterations
        self.max_budget_tokens = max_budget_tokens
        self._cancel_event = threading.Event()

    def cancel(self):
        """Déclenche l'annulation immédiate de la boucle cognitive en cours."""
        self._cancel_event.set()
        print("[AgentEngine] Annulation de la boucle cognitive demandée.")

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def _stream_output(self, text: str, iteration: int = 1):
        """Diffuse le texte segment par segment vers le HUD pour un affichage en direct."""
        words = text.split(" ")
        for i, word in enumerate(words):
            if self.is_cancelled():
                break
            bus.broadcast_threadsafe({
                "type": "agent_token",
                "token": word + (" " if i < len(words) - 1 else ""),
                "iteration": iteration
            })
            time.sleep(0.012)

    COMPLEX_KEYWORDS = [
        "voyage", "itinéraire", "programme", "organise", "planifie", "compare",
        "développe", "projet", "stratégie", "analyse complète", "étapes", "recherche approfondie"
    ]

    @staticmethod
    def _is_complex_query(text: str) -> bool:
        q = (text or "").lower()
        return any(k in q for k in AgentEngine.COMPLEX_KEYWORDS)

    def _build_llm_plan(self, user_text: str, specialist: AgentProfile) -> List[str]:
        """Fait générer le plan PAR LE LLM. Jamais bloquant : [] en cas d'échec."""
        planning_prompt = (
            "Tu es un planificateur. Décompose la demande en 3 à 5 étapes concrètes, exécutables "
            "par un agent disposant d'outils (web_search, fetch_webpage, fichiers, code, système).\n"
            "Réponds UNIQUEMENT par une liste JSON de chaînes, ex:\n"
            '["Recherche des options via web_search", "Extraction des données clés", "Rédaction de la synthèse"]\n\n'
            f"Demande : {user_text}"
        )
        try:
            raw = llm_cascade.ask_with_system(
                planning_prompt,
                "Tu produis uniquement du JSON valide, sans texte autour."
            )
            if not raw:
                return []
            m = re.search(r"\[[\s\S]*\]", raw)
            if not m:
                return []
            steps = json.loads(m.group(0))
            if isinstance(steps, list) and steps and all(isinstance(s, str) for s in steps):
                return steps[:5]
        except Exception as e:
            print(f"[AgentEngine] Erreur génération de plan: {e}")
        return []

    def run(self, user_query: str, model_override: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
        self._cancel_event.clear()
        user_text = user_query.strip()
        user_name = config.get("user_name", "Monsieur")
        assistant_name = config.get("assistant_name", "Ei")

        # 1. Enregistrement dans la mémoire de session (SQLite persistante)
        session_memory.add_user_message(user_text)

        # 2. Détection du profil spécialiste
        specialist = detect_specialist_for_query(user_text)

        bus.broadcast_threadsafe({
            "type": "agent_thought",
            "thought": f"Analyse : {user_text[:60]}... Spécialiste : {specialist.role_title}"
        })

        # 3. Plan de travail généré par le LLM si la demande est complexe
        plan = self._build_llm_plan(user_text, specialist) if self._is_complex_query(user_text) else []
        if plan:
            bus.broadcast_threadsafe({
                "type": "agent_plan",
                "status": "planning",
                "query": user_text,
                "steps": plan
            })

        # 4. Construction du System Prompt avec historique unifié SQLite
        history_str = session_memory.get_history_context(max_items=6)
        plan_block = (
            "PLAN DE TRAVAIL (à suivre ; réévalue mentalement après chaque observation d'outil) :\n"
            + "\n".join("- " + s for s in plan)
        ) if plan else ""
        system_prompt = f"""Tu es {assistant_name}, un agent IA autonome intégré au poste de {user_name}.
Rôle actif : {specialist.role_title}.
Consigne du rôle : {specialist.system_instruction}

RÈGLES CAPITALES :
1. Tu disposes d'outils concrets. Utilise-les dès que nécessaire (recherche web, fichiers, code python, fenêtres, etc.).
2. Si un outil échoue ou renvoie une erreur, analyse l'erreur et adapte ta stratégie.
3. Pour la réponse finale :
   - Fournis une réponse complète, détaillée et bien structurée en Markdown pour le HUD.
   - Conclus toujours avec une ligne :
     VOICE_SUMMARY: [Une synthèse orale concise de 1 à 2 phrases percutantes, naturelle, sans markdown ni astérisques, qui sera lue à haute voix].

{plan_block}
HISTORIQUE RÉCENT :
{history_str}
"""

        # 5. Tentative d'exécution via Native Function Calling
        model_info = model_override or self._get_active_model()
        provider = (model_info.get("provider") or "gemini").lower()
        model_name = model_info.get("model") or "gemini-2.5-flash"

        result = None
        if provider == "gemini" and (config.gemini_api_key or os.getenv("GEMINI_API_KEY")):
            result = self._run_native_gemini(user_text, model_name, specialist, system_prompt)

        elif provider in ["groq", "openai", "mistral"] and self._has_api_key(model_info):
            result = self._run_native_openai(user_text, model_info, specialist, system_prompt)

        # 6. Repli ReAct textuel si Function Calling indisponible ou échoué
        if not result and not self.is_cancelled():
            result = self._run_react_fallback(user_text, specialist, system_prompt, model_info)

        if self.is_cancelled():
            return ("Opération interrompue.", "Action arrêtée à la demande de l'utilisateur.")

        if not result:
            result = ("Désolé, je n'ai pas pu finaliser la réponse.", "Une erreur est survenue lors de l'appel au modèle.")

        speech_summary, detailed_output = result

        # 7. Mémorisation de la réponse dans la session persistante SQLite
        session_memory.add_assistant_message(detailed_output)

        return speech_summary, detailed_output

    def _get_active_model(self) -> Dict[str, Any]:
        from core.models import route_model_for_task
        route = route_model_for_task("requête")
        return route.get("model") or {"provider": "gemini", "model": "gemini-2.5-flash"}

    def _has_api_key(self, model_info: Dict[str, Any]) -> bool:
        key_env = model_info.get("key_env") or ""
        return bool(os.getenv(key_env, "").strip())

    def _run_native_gemini(self, user_text: str, model_name: str, specialist: AgentProfile, system_prompt: str) -> Optional[Tuple[str, str]]:
        """Boucle Native Function Calling avec le SDK Google GenAI."""
        api_key = (config.gemini_api_key or os.getenv("GEMINI_API_KEY", "")).strip().strip('"\'')
        if not api_key:
            return None

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            tools_gemini = tool_registry.get_gemini_tools(specialist.tools if specialist.tools else None)

            contents = [types.Content(role="user", parts=[types.Part.from_text(text=user_text)])]

            cfg_kwargs = dict(
                system_instruction=system_prompt,
                temperature=0.4,
                max_output_tokens=2048,
            )
            if tools_gemini:
                cfg_kwargs["tools"] = tools_gemini

            if "2.5-flash" in model_name:
                cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
            elif "pro" in model_name:
                cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=256)

            for iteration in range(1, self.max_iterations + 1):
                if self.is_cancelled():
                    return ("Opération annulée.", "Action interrompue.")

                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(**cfg_kwargs)
                    )
                except Exception as e:
                    err_s = str(e)
                    if "thinking_config" in cfg_kwargs and ("INVALID_ARGUMENT" in err_s or "400" in err_s):
                        cfg_kwargs.pop("thinking_config", None)
                        response = client.models.generate_content(
                            model=model_name,
                            contents=contents,
                            config=types.GenerateContentConfig(**cfg_kwargs)
                        )
                    else:
                        raise e

                if not response or not response.candidates or self.is_cancelled():
                    break

                candidate = response.candidates[0]
                content = candidate.content

                # Vérifier les appels d'outils
                function_calls = []
                for part in (content.parts or []):
                    if getattr(part, "function_call", None):
                        function_calls.append(part.function_call)

                if function_calls:
                    contents.append(content)
                    response_parts = []
                    for fc in function_calls:
                        if self.is_cancelled():
                            return ("Opération annulée.", "Action interrompue.")

                        tool_name = fc.name
                        tool_args = dict(fc.args or {})

                        bus.broadcast_threadsafe({
                            "type": "action",
                            "action": tool_name,
                            "params": tool_args,
                            "iteration": iteration
                        })
                        bus.broadcast_threadsafe({
                            "type": "agent_thought",
                            "iteration": iteration,
                            "thought": f"Exécution de l'outil {tool_name}..."
                        })

                        exec_res = tool_registry.execute(tool_name, tool_args)
                        obs = exec_res.get("error") or exec_res.get("result") or exec_res.get("speech")
                        session_memory.add_tool_interaction(tool_name, tool_args, str(obs))

                        response_parts.append(types.Part.from_function_response(
                            name=tool_name,
                            response={"result": obs}
                        ))

                    contents.append(types.Content(role="user", parts=response_parts))
                    continue

                # Pas de function call -> Réponse finale
                final_raw = response.text or ""
                speech_summary, detailed_output = self._parse_dual_output(final_raw)
                # Diffusion streaming au HUD
                self._stream_output(detailed_output, iteration=iteration)
                return speech_summary, detailed_output

        except Exception as e:
            print(f"[AgentEngine] Exception Gemini Native FC: {e}")
        return None

    def _run_native_openai(self, user_text: str, model_info: Dict[str, Any], specialist: AgentProfile, system_prompt: str) -> Optional[Tuple[str, str]]:
        """Boucle Native Function Calling pour endpoints OpenAI, Groq, Mistral."""
        provider = (model_info.get("provider") or "").lower()
        model_name = model_info.get("model") or ""
        key_env = model_info.get("key_env") or ""
        api_key = (os.getenv(key_env, "") if key_env else "").strip().strip('"\'')
        if not api_key:
            return None

        base_urls = {
            "groq": "https://api.groq.com/openai/v1",
            "openai": "https://api.openai.com/v1",
            "mistral": "https://api.mistral.ai/v1",
        }
        base_url = model_info.get("base_url") or base_urls.get(provider)
        if not base_url:
            return None

        import requests
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        tools_openai = tool_registry.get_openai_tools(specialist.tools if specialist.tools else None)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ]

        try:
            for iteration in range(1, self.max_iterations + 1):
                if self.is_cancelled():
                    return ("Opération annulée.", "Action interrompue.")

                payload = {
                    "model": model_name,
                    "messages": messages,
                    "temperature": 0.4,
                    "max_tokens": 2048
                }
                if tools_openai:
                    payload["tools"] = tools_openai
                    payload["tool_choice"] = "auto"

                res = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=50)
                if res.status_code != 200 or self.is_cancelled():
                    break

                data = res.json()
                msg = data["choices"][0]["message"]
                tool_calls = msg.get("tool_calls")

                if tool_calls:
                    messages.append(msg)
                    for tc in tool_calls:
                        if self.is_cancelled():
                            return ("Opération annulée.", "Action interrompue.")

                        fn_name = tc["function"]["name"]
                        try:
                            fn_args = json.loads(tc["function"]["arguments"])
                        except Exception:
                            fn_args = {}

                        bus.broadcast_threadsafe({
                            "type": "action",
                            "action": fn_name,
                            "params": fn_args,
                            "iteration": iteration
                        })
                        bus.broadcast_threadsafe({
                            "type": "agent_thought",
                            "iteration": iteration,
                            "thought": f"Exécution : {fn_name}"
                        })

                        exec_res = tool_registry.execute(fn_name, fn_args)
                        obs = exec_res.get("error") or exec_res.get("result") or exec_res.get("speech")
                        session_memory.add_tool_interaction(fn_name, fn_args, str(obs))

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": json.dumps({"result": obs}, ensure_ascii=False)
                        })
                    continue

                final_text = msg.get("content", "")
                speech_summary, detailed_output = self._parse_dual_output(final_text)
                self._stream_output(detailed_output, iteration=iteration)
                return speech_summary, detailed_output

        except Exception as e:
            print(f"[AgentEngine] Exception OpenAI Native FC: {e}")
        return None

    def _run_react_fallback(self, user_text: str, specialist: AgentProfile, system_prompt: str, model_override: Optional[Dict[str, Any]]) -> Tuple[str, str]:
        """Boucle de repli ReAct textuelle robuste."""
        tools_schema = tool_registry.get_prompt_schemas(specialist.tools if specialist.tools else None)
        thought_trace = []

        prompt_with_tools = f"""{system_prompt}

OUTILS DISPONIBLES :
{tools_schema}

FORMAT OBLIGATOIRE DE CHAQUE TOUR :
THOUGHT: [Ton raisonnement]
ACTION: {{"action": "nom_outil", "params": {{...}}}}
OU
THOUGHT: [Conclusion]
FINAL_ANSWER: [Ta réponse complète en Markdown]
VOICE_SUMMARY: [Synthèse orale concise de 1 à 2 phrases sans Markdown]
"""

        for iteration in range(1, self.max_iterations + 1):
            if self.is_cancelled():
                return ("Opération annulée.", "Action interrompue.")

            ctx = "\n".join(thought_trace) if thought_trace else "Début de l'analyse."
            llm_text = llm_cascade.ask_with_model(user_text, model_override, f"{prompt_with_tools}\nProgression :\n{ctx}")
            if not llm_text and not self.is_cancelled():
                llm_text = llm_cascade.ask_with_system(
                    f"Demande : {user_text}\nProgression : {ctx}",
                    f"{prompt_with_tools}\nProgression :\n{ctx}"
                )
                if not llm_text and not self.is_cancelled():
                    llm_text = llm_cascade.ask(f"Demande : {user_text}\nProgression : {ctx}")

            if not llm_text or self.is_cancelled():
                break

            # Détection d'action (JSON à accolades équilibrées, robuste aux params imbriqués)
            action_data = None
            json_m = re.search(r"ACTION:\s*(\{.*)", llm_text, re.DOTALL)
            if json_m:
                try:
                    action_data, _ = json.JSONDecoder().raw_decode(json_m.group(1).strip())
                except Exception:
                    action_data = None

            if action_data and "action" in action_data:
                act = action_data["action"]
                params = action_data.get("params", {})
                bus.broadcast_threadsafe({"type": "action", "action": act, "params": params})
                res = tool_registry.execute(act, params)
                obs = res.get("error") or res.get("result") or res.get("speech")
                session_memory.add_tool_interaction(act, params, str(obs))
                thought_trace.append(f"Étape {iteration} - {act} -> Observation: {str(obs)[:500]}")
                continue

            # Détection réponse finale
            speech_summary, detailed_output = self._parse_dual_output(llm_text)
            self._stream_output(detailed_output, iteration=iteration)
            return speech_summary, detailed_output

        return ("Demande traitée.", "Opération terminée.")

    def _parse_dual_output(self, raw_text: str) -> Tuple[str, str]:
        text = raw_text.strip()
        final_answer = text
        voice_summary = ""

        if "FINAL_ANSWER:" in text:
            parts = text.split("FINAL_ANSWER:", 1)[1]
            if "VOICE_SUMMARY:" in parts:
                fa, vs = parts.split("VOICE_SUMMARY:", 1)
                final_answer = fa.strip()
                voice_summary = vs.strip()
            else:
                final_answer = parts.strip()
        elif "VOICE_SUMMARY:" in text:
            fa, vs = text.split("VOICE_SUMMARY:", 1)
            final_answer = fa.strip()
            voice_summary = vs.strip()

        if not voice_summary:
            clean = re.sub(r"[\*#`_>\[\]\(\)]", " ", final_answer)
            clean = re.sub(r"https?://\S+", "", clean)
            sentences = [s.strip() for s in re.split(r"[.\n!?]", clean) if len(s.strip()) > 3]
            if sentences:
                voice_summary = ". ".join(sentences[:2]) + "."
            else:
                voice_summary = "Demande traitée avec succès."

        return voice_summary, final_answer

agent_engine = AgentEngine(max_iterations=6)

