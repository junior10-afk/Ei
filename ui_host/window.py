import sys
import webbrowser
from typing import Optional

def open_hud_window(url: str, title: str = "EI - Assistant Vocal", width: int = 1280, height: int = 800):
    """
    Ouvre l'interface HUD avec pywebview (WebView2), ou bascule sur le navigateur par défaut.
    """
    try:
        import webview
        print(f"[Window] Démarrage de la fenêtre HUD WebView2 ({url})...")
        window = webview.create_window(
            title=title,
            url=url,
            width=width,
            height=height,
            resizable=True,
            frameless=False,
            easy_drag=True,
            background_color='#050508'
        )
        webview.start(debug=False)
    except Exception as e:
        print(f"[Window] pywebview non disponible ou erreur ({e}). Ouverture du navigateur...")
        webbrowser.open(url)
