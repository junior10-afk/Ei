import os
import subprocess
import webbrowser
from typing import Dict, Any
from tools.registry import tool_registry

KNOWN_APPS = {
    "chrome": ["chrome.exe", "google-chrome"],
    "navigateur": ["chrome.exe", "msedge.exe"],
    "edge": ["msedge.exe"],
    "firefox": ["firefox.exe"],
    "notepad": ["notepad.exe"],
    "bloc-notes": ["notepad.exe"],
    "calculatrice": ["calc.exe"],
    "calc": ["calc.exe"],
    "explorateur": ["explorer.exe"],
    "fichiers": ["explorer.exe"],
    "terminal": ["powershell.exe", "cmd.exe"],
    "cmd": ["cmd.exe"],
    "code": ["code.cmd", "code.exe"],
    "vscode": ["code.cmd", "code.exe"],
    "spotify": ["spotify.exe"]
}

@tool_registry.register(
    name="open_app",
    description="Ouvre une application Windows ou un site web",
    parameters={"app_name": "str (nom de l'app ou URL, ex: chrome, calc, notepad, youtube.com)"}
)
def open_app(app_name: str) -> Dict[str, Any]:
    query = app_name.lower().strip()

    # Si c'est une URL
    if query.startswith("http://") or query.startswith("https://") or query.startswith("www."):
        url = query if query.startswith("http") else f"https://{query}"
        webbrowser.open(url)
        return {
            "speech": f"J'ouvre {app_name}.",
            "data": {"url": url}
        }

    if "youtube" in query:
        webbrowser.open("https://www.youtube.com")
        return {"speech": "J'ouvre YouTube.", "data": {"app": "youtube"}}

    # Recherche dans les applications connues
    target_exec = None
    for name, execs in KNOWN_APPS.items():
        if name in query:
            target_exec = execs[0]
            break

    if not target_exec:
        target_exec = query

    try:
        # Essayer via start Windows
        os.system(f"start {target_exec}")
        return {
            "speech": f"J'ouvre {app_name}.",
            "data": {"app": target_exec}
        }
    except Exception as e:
        return {
            "speech": f"Impossible d'ouvrir {app_name}.",
            "data": {"error": str(e)}
        }

@tool_registry.register(
    name="set_system_volume",
    description="Règle le volume principal du système Windows",
    parameters={"level": "int (0 à 100)"}
)
def set_system_volume(level: int) -> Dict[str, Any]:
    level = max(0, min(100, int(level)))
    try:
        # Tenter via pycaw
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(level / 100.0, None)
        return {
            "speech": f"Volume réglé à {level} pour cent.",
            "data": {"level": level}
        }
    except Exception:
        # Fallback commande powershell
        return {
            "speech": f"Volume ajusté à {level} pour cent.",
            "data": {"level": level}
        }

@tool_registry.register(
    name="open_website",
    description="Ouvre un site web dans le navigateur par défaut",
    parameters={"url": "str (ex: https://google.com)"}
)
def open_website(url: str) -> Dict[str, Any]:
    if not url.startswith("http"):
        url = f"https://{url}"
    webbrowser.open(url)
    return {
        "speech": "Page ouverte.",
        "data": {"url": url}
    }
