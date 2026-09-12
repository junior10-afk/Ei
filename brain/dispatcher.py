import re
import os
import json
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Optional, Dict, Any
from core.state import state_manager, AssistantState
from core.bus import bus
from core.config import config
from voice.tts import tts_engine
from voice.wake import check_wake_word, contains_stop_word
from brain.local_replies import check_local_reply, get_wake_ack
from brain.llm import llm_cascade
from brain.agent_loop import agent_engine
from brain.session_memory import session_memory
from tools.registry import tool_registry


class Dispatcher:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ei_dispatcher")
        self._cancel_event = threading.Event()
        self._current_future: Optional[Future] = None

    def cancel(self):
        """Annule immédiatement toute opération vocale, cognitive ou outil en cours."""
        self._cancel_event.set()
        agent_engine.cancel()
        tts_engine.stop()
        state_manager.set_state(AssistantState.IDLE)
        print("[Dispatcher] Annulation globale demandée par l'utilisateur.")

    def process_text_input(self, raw_text: str, is_voice: bool = False):
        """
        Point d'entrée unique pour la voix ou le clavier.
        Exécuté via le ThreadPoolExecutor pour éviter la prolifération de threads zombies.
        """
        if contains_stop_word(raw_text):
            self.cancel()
            return

        self._cancel_event.clear()
        self._current_future = self._executor.submit(self._process_sync, raw_text, is_voice)

    def _brain_available(self) -> bool:
        """True si le cerveau préféré a ce qu'il faut pour tourner (clé API)."""
        preferred = (config.get("preferred_brain", "gemini") or "gemini").lower()
        if preferred == "gemini":
            return bool(config.gemini_api_key or os.getenv("GEMINI_API_KEY"))
        return True

    def _route_query(self, text: str) -> Optional[Dict[str, Any]]:
        """Repli HORS-LINE uniquement : règles de secours définies dans config.default.json
        (agent.fallback_rules), appliquées seulement quand le cerveau est indisponible.
        Le LLM reste le point de décision principal dans tous les autres cas."""
        rules = (config.get("agent", {}) or {}).get("fallback_rules", [])
        for rule in rules:
            m = re.search(rule.get("pattern", ""), text, re.IGNORECASE)
            if not m:
                continue
            params = {}
            for k, v in (rule.get("params") or {}).items():
                if isinstance(v, str):
                    for i, group in enumerate(m.groups() or [], start=1):
                        v = v.replace("{" + str(i) + "}", group)
                    if v.isdigit():
                        v = int(v)
                params[k] = v
            return {"action": rule["action"], "params": params}
        return None

    def _process_sync(self, raw_text: str, is_voice: bool):
        if self._cancel_event.is_set():
            return

        # 1. Vérification Stop direct
        if contains_stop_word(raw_text):
            self.cancel()
            return

        query = raw_text.strip()

        # 2. Filtrage Wake Word
        if is_voice:
            has_wake, is_only, clean_query = check_wake_word(query)
            if has_wake:
                from core.utils import play_chime
                if config.get("sound_feedback", True):
                    play_chime("wake")

                if is_only:
                    ack = get_wake_ack()
                    tts_engine.speak(ack)
                    return
                query = clean_query
            else:
                state_manager.set_state(AssistantState.IDLE)
                return
        else:
            _, is_only, clean_query = check_wake_word(query)
            if is_only:
                tts_engine.speak(get_wake_ack())
                return
            query = clean_query

        if not query or self._cancel_event.is_set():
            state_manager.set_state(AssistantState.IDLE)
            return

        state_manager.set_state(AssistantState.THINKING)

        # 3. Réponses locales immédiates (0 latence, 0 coût)
        local_ans = check_local_reply(query)
        if local_ans:
            session_memory.add_user_message(query)
            session_memory.add_assistant_message(local_ans)
            tts_engine.speak(local_ans)
            return

        # 4. Repli hors-ligne : règles de secours SEULEMENT si le cerveau est indisponible
        if not self._brain_available():
            fallback = self._route_query(query)
            if fallback:
                res = tool_registry.execute(fallback["action"], fallback.get("params", {}))
                speech_text = res.get("speech", "Action effectuée.")
                session_memory.add_user_message(query)
                session_memory.add_assistant_message(speech_text)
                tts_engine.speak(speech_text)
                return

        if self._cancel_event.is_set():
            return

        # 5. Routage de modèle et exécution par le moteur d'agent autonome (ReAct)
        from core.models import route_model_for_task
        route = route_model_for_task(query)
        model = route.get("model")
        if model:
            bus.broadcast_threadsafe({
                "type": "model_used",
                "model_id": model.get("id"),
                "label": model.get("label", model.get("id")),
                "tier": route.get("tier"),
            })

        if self._cancel_event.is_set():
            return

        # Exécution de la boucle cognitive ReAct
        speech_summary, detailed_output = agent_engine.run(query, model_override=model)

        if self._cancel_event.is_set():
            return

        # Diffusion du plan complet et des résultats détaillés au chat / console du HUD
        bus.broadcast_threadsafe({
            "type": "long_response",
            "text": detailed_output,
            "model": (model or {}).get("label", "")
        })

        # Synthèse vocale concise
        tts_engine.speak(speech_summary)

dispatcher = Dispatcher()
