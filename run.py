import os
import sys
import asyncio
import threading
import time
from pathlib import Path

# Ajouter la racine du projet au sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from core.config import config
from core.state import state_manager, AssistantState
from core.bus import bus
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
        "data": config.config
    })

async def handle_update_settings(data: dict, websocket):
    new_settings = data.get("data", {})
    config.update(new_settings)
    await bus.broadcast({
        "type": "settings",
        "data": config.config
    })

def setup_ws_handlers():
    bus.register_handler("user_input", handle_user_input)
    bus.register_handler("toggle_mic", handle_toggle_mic)
    bus.register_handler("stop_audio", handle_stop_audio)
    bus.register_handler("get_settings", handle_get_settings)
    bus.register_handler("update_settings", handle_update_settings)

def main():
    print("=" * 60)
    print(f"   Démarrage de {config.get('assistant_name', 'EI')} - Runtime Vocal & HUD")
    print("=" * 60)

    setup_ws_handlers()

    # Relier le microphone au dispatcher
    mic_listener.on_speech_recognized = lambda text: dispatcher.process_text_input(text, is_voice=True)

    # 1. Démarrer le serveur Web statique pour le frontend HUD
    vite_port = int(os.getenv("VITE_PORT", "5173"))
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

    # 3. Démarrer l'écoute micro
    if config.get("auto_listen", True):
        mic_listener.start()

    # 4. Message de bienvenue vocal au démarrage
    assistant_name = config.get("assistant_name", "EI")
    user_name = config.get("user_name", "Monsieur")
    welcome_text = f"Système {assistant_name} initialisé et prêt. Bonjour {user_name}."
    tts_engine.speak(welcome_text)

    # 5. Ouvrir la fenêtre HUD (bloquant jusqu'à la fermeture de la fenêtre)
    hud_url = f"http://127.0.0.1:{vite_port}"
    open_hud_window(hud_url, title=f"{assistant_name} - Interface HUD")

    # Arrêt propre
    mic_listener.stop()
    tts_engine.stop()
    print("[Run] Système arrêté proprement.")

if __name__ == "__main__":
    main()
