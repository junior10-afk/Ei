import os
import threading
import http.server
import socketserver
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

def serve_static(port: int = 5173, directory: Path = None):
    """Démarre un serveur HTTP statique local léger en arrière-plan."""
    target_dir = directory or (DIST_DIR if DIST_DIR.exists() else FRONTEND_DIR)
    
    class CustomDirectoryHandler(QuietHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(target_dir), **kwargs)

    try:
        # Autoriser la réutilisation de port
        socketserver.TCPServer.allow_reuse_address = True
        httpd = socketserver.TCPServer(("127.0.0.1", port), CustomDirectoryHandler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        print(f"[UI Host] Serveur Web statique démarré sur http://127.0.0.1:{port} (racine: {target_dir.name})")
        return httpd
    except Exception as e:
        print(f"[UI Host] Avertissement port {port} déjà utilisé ou erreur: {e}")
        return None
