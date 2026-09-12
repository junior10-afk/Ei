import os
import shutil
import subprocess
import webbrowser
import urllib.parse
from typing import Dict, Any
from tools.registry import tool_registry

KNOWN_APPS = {
    "chrome": ["chrome.exe", r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"],
    "navigateur": ["chrome.exe", "msedge.exe", "firefox.exe"],
    "edge": ["msedge.exe", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"],
    "firefox": ["firefox.exe", r"C:\Program Files\Mozilla Firefox\firefox.exe"],
    "notepad": ["notepad.exe"],
    "bloc-notes": ["notepad.exe"],
    "calculatrice": ["calc.exe"],
    "calc": ["calc.exe"],
    "explorateur": ["explorer.exe"],
    "fichiers": ["explorer.exe"],
    "terminal": ["wt.exe", "powershell.exe", "cmd.exe"],
    "powershell": ["powershell.exe"],
    "cmd": ["cmd.exe"],
    "code": ["code.cmd", "code.exe"],
    "vscode": ["code.cmd", "code.exe"],
    "spotify": ["spotify.exe", os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe")],
    "discord": ["discord.exe", os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe --processStart Discord.exe")],
    "vlc": ["vlc.exe", r"C:\Program Files\VideoLAN\VLC\vlc.exe"],
    "word": ["winword.exe"],
    "excel": ["excel.exe"],
    "powerpoint": ["powerpnt.exe"],
    "paint": ["mspaint.exe"],
}

COMMON_SITES = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "wikipedia": "https://fr.wikipedia.org",
    "github": "https://github.com",
    "chatgpt": "https://chatgpt.com",
    "gmail": "https://mail.google.com",
    "maps": "https://maps.google.com",
    "traduction": "https://translate.google.com",
    "amazon": "https://www.amazon.fr",
    "netflix": "https://www.netflix.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "linkedin": "https://www.linkedin.com",
    "reddit": "https://www.reddit.com"
}

@tool_registry.register(
    name="open_app",
    description="Ouvre une application installée sur Windows ou un site Web",
    parameters={"app_name": "str (nom de l'application ou URL, ex: 'chrome', 'bloc-notes', 'calculatrice', 'code', 'spotify')"}
)
def open_app(app_name: str) -> Dict[str, Any]:
    query = app_name.lower().strip()

    # 1. Vérification si c'est un site ou un raccourci web
    for site_key, site_url in COMMON_SITES.items():
        if query == site_key or query == f"le site {site_key}" or query == f"site {site_key}":
            webbrowser.open(site_url)
            return {"speech": f"J'ouvre {site_key.capitalize()}.", "data": {"url": site_url}}

    if query.startswith("http://") or query.startswith("https://") or query.startswith("www."):
        url = query if query.startswith("http") else f"https://{query}"
        webbrowser.open(url)
        return {"speech": f"J'ouvre {app_name}.", "data": {"url": url}}

    # 2. Recherche dans les applications connues
    target_exec = None
    for name, exec_candidates in KNOWN_APPS.items():
        if name in query:
            for cand in exec_candidates:
                if shutil.which(cand.split()[0]) or os.path.exists(cand.split()[0]):
                    target_exec = cand
                    break
            if not target_exec:
                target_exec = exec_candidates[0]
            break

    if not target_exec:
        target_exec = query

    # Protection contre l'injection de commandes shell
    if any(c in target_exec for c in ['&', '|', ';', '`', '$', '\n', '\r']):
        return {
            "speech": "Nom d'application invalide ou non autorisé.",
            "data": {"error": "Caractères suspects interdits"}
        }

    try:
        if os.name == 'nt':
            parts = target_exec.split(maxsplit=1)
            exe_path = parts[0]
            if len(parts) > 1 and (shutil.which(exe_path) or os.path.exists(exe_path)):
                subprocess.Popen(parts, shell=False)
            elif os.path.exists(exe_path) or shutil.which(exe_path):
                os.startfile(exe_path)
            else:
                os.startfile(target_exec)
        else:
            subprocess.Popen([target_exec], shell=False)

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
    name="open_website",
    description="Ouvre une adresse Web ou lance une recherche dans le navigateur",
    parameters={"url": "str (URL du site ou mots clés, ex: 'https://github.com' ou 'actualités ia')"}
)
def open_website(url: str) -> Dict[str, Any]:
    query = url.strip()
    clean_name = query.lower().replace("le site", "").strip()
    if clean_name in COMMON_SITES:
        target = COMMON_SITES[clean_name]
    elif query.startswith("http://") or query.startswith("https://"):
        target = query
    elif "." in query and " " not in query:
        target = f"https://{query}"
    else:
        target = f"https://www.google.com/search?q={urllib.parse.quote(query)}"

    # Vérification de sécurité du protocole
    if not (target.startswith("http://") or target.startswith("https://")):
        return {
            "speech": "Protocole d'URL non autorisé.",
            "data": {"error": "Seuls http et https sont autorisés"}
        }

    try:
        webbrowser.open(target)
        return {
            "speech": "Page Web ouverte dans votre navigateur.",
            "data": {"url": target}
        }
    except Exception as e:
        return {
            "speech": "Impossible d'ouvrir le navigateur.",
            "data": {"error": str(e)}
        }

@tool_registry.register(
    name="set_system_volume",
    description="Règle le volume principal du système Windows (0 à 100)",
    parameters={"level": "int (0 à 100)"}
)
def set_system_volume(level: int) -> Dict[str, Any]:
    level = max(0, min(100, int(level)))
    try:
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
        # Fallback via commande PowerShell
        try:
            ps_cmd = f"$wsh = New-Object -ComObject WScript.Shell; $wsh.SendKeys([char]174)"
            subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)
        except Exception:
            pass
        return {
            "speech": f"Volume ajusté à {level} pour cent.",
            "data": {"level": level}
        }
