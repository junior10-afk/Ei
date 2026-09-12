import os
import sys
import asyncio
import threading
import time
from pathlib import Path

# Ajouter la racine du projet au sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from core.logging_config import setup_logging

verbose = "--verbose" in sys.argv or "-v" in sys.argv
logger = setup_logging(verbose=verbose)

from core.config import config
from core.state import state_manager, AssistantState
from core.bus import bus
from core.utils import free_ports, play_chime
from voice.tts import tts_engine
from voice.mic import mic_listener
from brain.dispatcher import dispatcher
from ui_host.launcher import serve_static
from ui_host.window import open_hud_window
import tools  # Charge et enregistre tous les outils

# --- Handlers WebSocket entrants ---

async def handle_user_input(data: dict, websocket):
    text = data.get("text", "").strip()
    if text:
        dispatcher.process_text_input(text, is_voice=False)

async def handle_toggle_mic(data: dict, websocket):
    muted = data.get("muted", None)
    new_status = state_manager.set_mic_muted(muted)
    print(f"[Run] État microphone modifié: {'MUTE' if new_status else 'ACTIF'}")

async def handle_stop_audio(data: dict, websocket):
    tts_engine.stop()

async def handle_get_settings(data: dict, websocket):
    await bus.send_to(websocket, {
        "type": "settings",
        "data": {**config.config, "api_keys_status": config.get_api_keys_status()}
    })

async def handle_set_api_key(data: dict, websocket):
    """Enregistre une clé API dans .env (jamais dans config.json) et confirme."""
    var = (data.get("var") or data.get("variable") or "").upper().strip()
    value = (data.get("value") or "").strip()
    if var not in config.API_KEY_VARS:
        await bus.send_to(websocket, {"type": "api_key_result", "var": var,
                                       "ok": False, "message": "Variable non autorisée."})
        return
    config.set_env_var(var, value)

    # Réinitialiser le cooldown sur ce provider pour qu'il soit utilisable immédiatement
    from brain.llm import llm_cascade
    prov_map = {
        "GEMINI_API_KEY": "gemini",
        "GROQ_API_KEY": "groq",
        "OPENAI_API_KEY": "openai",
        "MISTRAL_API_KEY": "mistral"
    }
    prov = prov_map.get(var)
    if prov:
        llm_cascade.clear_cooldown(prov)

    await bus.broadcast({
        "type": "settings",
        "data": {**config.config, "api_keys_status": config.get_api_keys_status()}
    })
    # Mettre à jour le catalogue affiché côté HUD
    from core.models import catalog_public_view
    await bus.broadcast({
        "type": "models_catalog",
        "options": catalog_public_view(),
        "tiers": config.get("models", {}).get("tiers", {}),
        "choice_mode": config.get("model_choice_mode", "auto"),
    })
    print(f"[Run] Clé {var} mise à jour ({'effacée' if not value else 'enregistrée'}).")

async def handle_test_api_key(data: dict, websocket):
    """Teste la connexion d'un fournisseur et renvoie le résultat au HUD."""
    from brain.api_test import test_api_key
    provider = (data.get("provider") or "").lower()
    result = await asyncio.get_running_loop().run_in_executor(None, test_api_key, provider)
    await bus.send_to(websocket, {"type": "api_key_result", "provider": provider, **result})

async def handle_update_settings(data: dict, websocket):
    new_settings = data.get("data", {})
    # Les clés API ne passent jamais par config.json (fichier versionné)
    new_settings.pop("api_keys_status", None)
    # Fusion profonde de "models" (pour ne pas écraser le catalog éventuel)
    if isinstance(new_settings.get("models"), dict):
        merged = {**(config.get("models") or {}), **new_settings["models"]}
        tiers_new = new_settings["models"].get("tiers")
        if isinstance(tiers_new, dict):
            merged["tiers"] = {**(merged.get("tiers") or {}), **tiers_new}
        new_settings["models"] = merged
    config.update(new_settings)
    await bus.broadcast({
        "type": "settings",
        "data": {**config.config, "api_keys_status": config.get_api_keys_status()}
    })
    # Confirmer le nouveau routage au HUD
    from core.models import catalog_public_view
    await bus.broadcast({
        "type": "models_catalog",
        "options": catalog_public_view(),
        "tiers": config.get("models", {}).get("tiers", {}),
        "choice_mode": config.get("model_choice_mode", "auto"),
    })

async def handle_model_select_response(data: dict, websocket):
    """Réponse de l'utilisateur à la fenêtre de sélection de modèle."""
    from core.models import model_choice
    model_id = data.get("model_id")
    model_choice.resolve(model_id)
    await bus.broadcast({
        "type": "model_select_closed",
        "model_id": model_id
    })

async def handle_get_models(data: dict, websocket):
    """Le HUD demande le catalogue des modèles (pour les réglages)."""
    from core.models import catalog_public_view
    await bus.send_to(websocket, {
        "type": "models_catalog",
        "options": catalog_public_view(),
        "tiers": config.get("models", {}).get("tiers", {}),
        "choice_mode": config.get("model_choice_mode", "auto"),
    })

async def handle_list_provider_models(data: dict, websocket):
    """Liste en direct les modèles réellement offerts par un fournisseur
    (Google, Groq, OpenAI, Mistral, Ollama) avec la clé enregistrée."""
    from brain.providers import list_provider_models
    provider = (data.get("provider") or "").lower()
    result = await asyncio.get_running_loop().run_in_executor(None, list_provider_models, provider)
    await bus.send_to(websocket, {
        "type": "provider_models",
        "provider": provider,
        **result,
    })

async def handle_tool_confirmation_response(data: dict, websocket):
    """Réponse de l'utilisateur à une demande de confirmation d'action sensible."""
    from tools.registry import tool_confirmation_manager
    req_id = data.get("request_id")
    confirmed = bool(data.get("confirmed", False))
    tool_confirmation_manager.resolve(req_id, confirmed)

async def handle_cancel_task(data: dict, websocket):
    from core.task_manager import task_manager
    task_id = data.get("task_id")
    if task_id:
        task_manager.cancel_task(task_id)

async def handle_get_tasks(data: dict, websocket):
    from core.task_manager import task_manager
    await bus.send_to(websocket, {
        "type": "tasks_list",
        "tasks": task_manager.list_tasks()
    })

async def handle_get_routines(data: dict, websocket):
    from core.scheduler import scheduler
    await bus.send_to(websocket, {
        "type": "routines_list",
        "routines": scheduler.list_routines()
    })

def setup_ws_handlers():
    bus.register_handler("user_input", handle_user_input)
    bus.register_handler("toggle_mic", handle_toggle_mic)
    bus.register_handler("stop_audio", handle_stop_audio)
    bus.register_handler("get_settings", handle_get_settings)
    bus.register_handler("update_settings", handle_update_settings)
    bus.register_handler("set_api_key", handle_set_api_key)
    bus.register_handler("test_api_key", handle_test_api_key)
    bus.register_handler("list_provider_models", handle_list_provider_models)
    bus.register_handler("model_select_response", handle_model_select_response)
    bus.register_handler("get_models", handle_get_models)
    bus.register_handler("tool_confirmation_response", handle_tool_confirmation_response)
    bus.register_handler("cancel_task", handle_cancel_task)
    bus.register_handler("get_tasks", handle_get_tasks)
    bus.register_handler("get_routines", handle_get_routines)

def main():
    print("=" * 60)
    print(f"   Démarrage de {config.get('assistant_name', 'EI')} - Runtime Vocal & HUD")
    print("=" * 60)

    # 0. Libération des ports pour éviter les conflits au boot (8765 / 5173)
    vite_port = int(os.getenv("VITE_PORT", "5173"))
    ws_port = config.ws_port
    free_ports([ws_port, vite_port])

    setup_ws_handlers()

    # Relier le microphone au dispatcher
    mic_listener.on_speech_recognized = lambda text: dispatcher.process_text_input(text, is_voice=True)

    # 1. Démarrer le serveur Web statique pour le frontend HUD
    serve_static(port=vite_port)

    # 2. Démarrer la boucle asyncio pour le WebSocket dans un thread séparé
    ws_host = config.host
    ws_port = config.ws_port

    def run_ws_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        server_coro = bus.start_server(ws_host, ws_port)
        loop.run_until_complete(server_coro)
        loop.run_forever()

    ws_thread = threading.Thread(target=run_ws_loop, daemon=True)
    ws_thread.start()

    # 2.b Télémétrie CPU/RAM pour le HUD central (économique si aucun client connecté)
    import psutil
    def broadcast_stats_loop():
        time.sleep(2)
        while True:
            try:
                if len(bus.clients) > 0:
                    cpu = psutil.cpu_percent(interval=1.0)
                    ram = psutil.virtual_memory().percent
                    bus.broadcast_threadsafe({
                        "type": "system_stats",
                        "cpu": cpu,
                        "ram": ram
                    })
                else:
                    time.sleep(2.0)
            except Exception:
                pass
            time.sleep(1.5)

    stats_thread = threading.Thread(target=broadcast_stats_loop, daemon=True)
    stats_thread.start()

    # 3. Démarrer l'écoute micro
    if config.get("auto_listen", True):
        mic_listener.start()

    # 4. Message de bienvenue vocal au démarrage
    assistant_name = config.get("assistant_name", "EI")
    user_name = config.get("user_name", "Monsieur")
    welcome_text = f"Système {assistant_name} initialisé et prêt. Bonjour {user_name}."
    tts_engine.speak(welcome_text)

    # 5. Ouvrir la fenêtre HUD avec le token de sécurité de session
    hud_url = f"http://127.0.0.1:{vite_port}/?token={bus.auth_token}"
    open_hud_window(hud_url, title=f"{assistant_name} - Interface HUD")

    # Arrêt propre
    mic_listener.stop()
    tts_engine.stop()
    print("[Run] Système arrêté proprement.")

if __name__ == "__main__":
    main()
