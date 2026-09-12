import os
import secrets
import urllib.parse
import asyncio
import json
from typing import Set, Dict, Any, Optional, Callable, Coroutine
import websockets
try:
    from websockets.asyncio.server import ServerConnection as WebSocketServerProtocol
except ImportError:
    from websockets.server import WebSocketServerProtocol

from core.state import state_manager
from core.config import config

class MessageBus:
    def __init__(self):
        self.clients: Set[WebSocketServerProtocol] = set()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._handlers: Dict[str, Callable[[dict, WebSocketServerProtocol], Coroutine[Any, Any, None]]] = {}
        # Jeton d'authentification pour sécuriser l'accès localhost
        self.auth_token: str = os.getenv("EI_AUTH_TOKEN", "").strip() or secrets.token_hex(16)

        # S'abonner aux notifications d'état
        state_manager.subscribe(self._on_state_event)

    def register_handler(self, msg_type: str, handler: Callable[[dict, WebSocketServerProtocol], Coroutine[Any, Any, None]]):
        """Enregistre un handler pour un type de message entrant."""
        self._handlers[msg_type] = handler

    def _on_state_event(self, event_type: str, data: dict):
        """Reçoit les événements du StateManager et les diffuse aux clients."""
        payload = {"type": event_type, **data}
        self.broadcast_threadsafe(payload)

    async def broadcast(self, message: dict):
        """Diffuse un message JSON à tous les clients connectés."""
        if not self.clients:
            return
        data_str = json.dumps(message, ensure_ascii=False)
        disconnected = set()
        for client in list(self.clients):
            try:
                await client.send(data_str)
            except Exception:
                disconnected.add(client)
        if disconnected:
            self.clients.difference_update(disconnected)

    def broadcast_threadsafe(self, message: dict):
        """Diffuse depuis un thread synchrone de manière thread-safe avec journalisation des rejets."""
        if self.loop and self.loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(self.broadcast(message), self.loop)
            except Exception as e:
                print(f"[Bus] Abandon message ({message.get('type')}): erreur threadsafe: {e}")
        else:
            print(f"[Bus] Abandon message ({message.get('type')}): boucle asyncio inactive ou fermée.")

    async def send_to(self, client: WebSocketServerProtocol, message: dict):
        """Envoie un message à un client particulier."""
        try:
            await client.send(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            print(f"[Bus] Erreur envoi vers client: {e}")

    def _extract_token_from_path(self, path: str) -> Optional[str]:
        """Extrait le token d'authentification de la query string WebSocket."""
        try:
            parsed = urllib.parse.urlparse(path)
            query_params = urllib.parse.parse_qs(parsed.query)
            token = query_params.get("token", [None])[0]
            return token
        except Exception:
            return None

    async def ws_handler(self, websocket: WebSocketServerProtocol, path: str = ""):
        """Gestionnaire de connexion client avec validation de token d'authentification."""
        # Récupérer le chemin selon la version de websockets
        req_path = path or getattr(websocket, "path", "")
        if not req_path and hasattr(websocket, "request"):
            req_path = getattr(websocket.request, "path", "")

        token_sent = self._extract_token_from_path(req_path)
        
        # Vérification du token si configuré
        if self.auth_token:
            if token_sent != self.auth_token:
                print(f"[Bus] Connexion refusée : token d'authentification invalide ou absent.")
                await self.send_to(websocket, {
                    "type": "error",
                    "message": "Connexion WebSocket refusée : authentification requise."
                })
                await websocket.close(code=4001, reason="Unauthorized")
                return

        self.clients.add(websocket)
        print(f"[Bus] Nouveau client authentifié connecté. Total: {len(self.clients)}")

        # Envoyer l'état initial au nouveau client
        initial_state = {
            "type": "set_state",
            "state": state_manager.current_state
        }
        mic_state = {
            "type": "mic_state",
            "muted": state_manager.is_mic_muted
        }
        settings = {
            "type": "settings",
            "data": {**config.config, "api_keys_status": config.get_api_keys_status()}
        }
        await self.send_to(websocket, initial_state)
        await self.send_to(websocket, mic_state)
        await self.send_to(websocket, settings)

        try:
            async for raw_msg in websocket:
                try:
                    data = json.loads(raw_msg)
                    msg_type = data.get("type", "")
                    if msg_type in self._handlers:
                        await self._handlers[msg_type](data, websocket)
                    else:
                        print(f"[Bus] Type de message inconnu reçu: {msg_type}")
                except json.JSONDecodeError:
                    print(f"[Bus] Message JSON invalide reçu: {raw_msg}")
                except Exception as ex:
                    print(f"[Bus] Erreur traitement message: {ex}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            print(f"[Bus] Client déconnecté. Restant: {len(self.clients)}")

    async def start_server(self, host: str, port: int):
        """Démarre le serveur WebSocket."""
        self.loop = asyncio.get_running_loop()
        print(f"[Bus] Démarrage du WebSocket sur ws://{host}:{port} (Auth: active)")
        try:
            # Compatibilité websockets v13+ et versions antérieures
            server = await websockets.serve(self.ws_handler, host, port)
        except TypeError:
            # Si le wrapper n'accepte pas deux arguments websocket/path
            async def compat_handler(ws):
                await self.ws_handler(ws)
            server = await websockets.serve(compat_handler, host, port)
        return server

bus = MessageBus()
