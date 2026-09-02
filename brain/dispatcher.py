import re
import json
import threading
from typing import Optional, Dict, Any
from core.state import state_manager, AssistantState
from core.bus import bus
from voice.tts import tts_engine
from voice.wake import check_wake_word, contains_stop_word
from brain.local_replies import check_local_reply, get_wake_ack
from brain.llm import llm_cascade
from tools.registry import tool_registry

class Dispatcher:
    def __init__(self):
        self._lock = threading.Lock()

    def process_text_input(self, raw_text: str, is_voice: bool = False):
        """
        Point d'entrée unique pour la voix ou le clavier.
        Exécuté en tâche de fond pour ne pas bloquer.
        """
        threading.Thread(target=self._process_sync, args=(raw_text, is_voice), daemon=True).start()

    def _match_deterministic_tools(self, text: str) -> Optional[Dict[str, Any]]:
        """Détection déterministe ultra-rapide par regex avant l'appel LLM."""
        clean = text.lower().strip()

        # 1. Ouvrir une application
        open_match = re.search(r"(?:ouvre|lance|démarre)\s+(?:le\s+|la\s+|l'|l\s+|un\s+|une\s+)?(chrome|navigateur|edge|firefox|bloc-notes|notepad|calculatrice|calc|youtube|code|vscode|spotify|explorateur)", clean)
        if open_match:
            app_target = open_match.group(1)
            return {"action": "open_app", "params": {"app_name": app_target}}

        # 2. Ouvrir un site web
        site_match = re.search(r"(?:ouvre le site|va sur)\s+(https?://\S+|www\.\S+|\S+\.(?:com|fr|org|net))", clean)
        if site_match:
            return {"action": "open_website", "params": {"url": site_match.group(1)}}

        # 3. Réglage du volume Windows
        vol_match = re.search(r"(?:mets le volume à|règle le volume à|volume à)\s+(\d{1,3})", clean)
        if vol_match:
            return {"action": "set_system_volume", "params": {"level": int(vol_match.group(1))}}

        # 4. Météo
        weather_match = re.search(r"(?:météo|quel temps fait-il)(?:\s+(?:à|pour|dans)\s+([a-zA-ZÀ-ÿ\s-]+))?", clean)
        if weather_match:
            city = weather_match.group(1) if weather_match.group(1) else "Paris"
            return {"action": "get_weather", "params": {"city": city.strip()}}

        # 5. Ouvrir un dossier
        folder_match = re.search(r"(?:ouvre le dossier|dossier)\s+(?:du\s+|des\s+|de\s+)?(bureau|desktop|documents|téléchargements|downloads|images|musique)", clean)
        if folder_match:
            return {"action": "open_folder", "params": {"path": folder_match.group(1)}}

        # 6. Mémoriser une information
        memo_match = re.search(r"(?:mémorise|rappelle-toi que|note que)\s+([a-zA-ZÀ-ÿ0-9\s]+?)\s+(?:est|c'est|vaut)\s+(.+)", clean)
        if memo_match:
            return {
                "action": "remember_fact",
                "params": {"key": memo_match.group(1).strip(), "value": memo_match.group(2).strip()}
            }

        # 7. Rappeler une information
        recall_match = re.search(r"(?:quel est mon|rappelle-moi|qu'est-ce que tu sais sur)\s+([a-zA-ZÀ-ÿ0-9\s]+)", clean)
        if recall_match:
            return {
                "action": "recall_fact",
                "params": {"key": recall_match.group(1).strip()}
            }

        return None

    def _parse_llm_action(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Tente d'extraire un JSON d'action de la réponse LLM."""
        text = response_text.strip()
        # Rechercher un bloc JSON { "action": ... }
        json_match = re.search(r"\{[\s\S]*\"action\"[\s\S]*\}", text)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                if "action" in data:
                    return data
            except Exception:
                pass
        return None

    def _process_sync(self, raw_text: str, is_voice: bool):
        with self._lock:
            # 1. Vérification Stop direct
            if contains_stop_word(raw_text):
                tts_engine.stop()
                state_manager.set_state(AssistantState.IDLE)
                return

            query = raw_text.strip()

            # 2. Filtrage Wake Word
            if is_voice:
                has_wake, is_only, clean_query = check_wake_word(query)
                if has_wake:
                    if is_only:
                        # Wake word seul -> réponse rapide immédiate
                        ack = get_wake_ack()
                        tts_engine.speak(ack)
                        return
                    query = clean_query
                # Si pas de wake word à la voix, on ignore
                else:
                    state_manager.set_state(AssistantState.IDLE)
                    return
            else:
                # Saisie clavier : on nettoie aussi le wake word s'il est tapé
                _, is_only, clean_query = check_wake_word(query)
                if is_only:
                    tts_engine.speak(get_wake_ack())
                    return
                query = clean_query

            if not query:
                state_manager.set_state(AssistantState.IDLE)
                return

            state_manager.set_state(AssistantState.THINKING)

            # 3. Réponses locales immédiates (0 latence, 0 coût)
            local_ans = check_local_reply(query)
            if local_ans:
                tts_engine.speak(local_ans)
                return

            # 4. Détection déterministe d'outils
            direct_tool = self._match_deterministic_tools(query)
            if direct_tool:
                res = tool_registry.execute(direct_tool["action"], direct_tool.get("params", {}))
                # Diffuser l'action exécutée au HUD
                bus.broadcast_threadsafe({
                    "type": "action",
                    "action": direct_tool["action"],
                    "params": direct_tool.get("params", {}),
                    "result": res.get("result")
                })
                speech_text = res.get("speech", "Action effectuée.")
                tts_engine.speak(speech_text)
                return

            # 5. Appel à la cascade LLM
            llm_response = llm_cascade.ask(query)

            # Vérifier si le LLM a renvoyé un ordre d'action JSON
            action_data = self._parse_llm_action(llm_response)
            if action_data:
                action_name = action_data.get("action")
                params = action_data.get("params", {})
                res = tool_registry.execute(action_name, params)
                bus.broadcast_threadsafe({
                    "type": "action",
                    "action": action_name,
                    "params": params,
                    "result": res.get("result")
                })
                speech_text = res.get("speech", "Action accomplie.")
                tts_engine.speak(speech_text)
            else:
                # Réponse conversationnelle libre
                tts_engine.speak(llm_response)

dispatcher = Dispatcher()
