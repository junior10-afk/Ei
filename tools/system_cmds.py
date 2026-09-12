import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from tools.registry import tool_registry

BASE_DIR = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = BASE_DIR / "data" / "screenshots"

@tool_registry.register(
    name="take_screenshot",
    description="Prend une capture d'écran du bureau Windows et l'enregistre.",
    parameters={"filename": "Nom optionnel du fichier de capture (sans chemin)"}
)
def take_screenshot(filename: Optional[str] = None) -> Dict[str, Any]:
    """Capture l'écran complet et l'enregistre dans data/screenshots/."""
    try:
        from PIL import ImageGrab
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_name = f"screenshot_{timestamp}.png"
        if filename:
            clean_base = Path(filename).name.replace(" ", "_")
            if not clean_base.lower().endswith((".png", ".jpg", ".jpeg")):
                clean_base += ".png"
            safe_name = f"{timestamp}_{clean_base}"

        target_path = SCREENSHOTS_DIR / safe_name
        img = ImageGrab.grab()
        img.save(str(target_path))

        return {
            "speech": f"Capture d'écran enregistrée avec succès.",
            "data": {
                "file_path": str(target_path),
                "resolution": f"{img.width}x{img.height}"
            }
        }
    except Exception as e:
        return {
            "speech": f"Impossible de capturer l'écran.",
            "data": {"error": str(e)}
        }

@tool_registry.register(
    name="clipboard_get",
    description="Récupère le texte actuellement copié dans le presse-papiers Windows.",
    parameters={}
)
def clipboard_get() -> Dict[str, Any]:
    """Lit le presse-papiers Windows."""
    text = ""
    # 1. Méthode Tkinter rapide
    try:
        import tkinter as tk
        r = tk.Tk()
        r.withdraw()
        text = r.clipboard_get()
        r.destroy()
    except Exception:
        # 2. Fallback PowerShell
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                capture_output=True,
                text=True,
                timeout=3
            )
            text = res.stdout.strip()
        except Exception as e:
            return {
                "speech": "Impossible de lire le presse-papiers.",
                "data": {"error": str(e)}
            }

    if not text:
        return {
            "speech": "Le presse-papiers est actuellement vide.",
            "data": {"text": ""}
        }

    preview = text[:80] + "…" if len(text) > 80 else text
    return {
        "speech": f"Contenu du presse-papiers récupéré.",
        "data": {"text": text, "preview": preview}
    }

@tool_registry.register(
    name="clipboard_set",
    description="Copie un texte dans le presse-papiers de Windows.",
    parameters={"text": "Texte à copier dans le presse-papiers"}
)
def clipboard_set(text: str) -> Dict[str, Any]:
    """Écrit du texte dans le presse-papiers Windows."""
    try:
        import tkinter as tk
        r = tk.Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(text)
        r.update()
        r.destroy()
        return {
            "speech": "Texte copié dans le presse-papiers.",
            "data": {"length": len(text)}
        }
    except Exception:
        try:
            process = subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", "$input | Set-Clipboard"],
                stdin=subprocess.PIPE,
                text=True
            )
            process.communicate(input=text, timeout=3)
            return {
                "speech": "Texte copié dans le presse-papiers.",
                "data": {"length": len(text)}
            }
        except Exception as e:
            return {
                "speech": "Impossible de copier dans le presse-papiers.",
                "data": {"error": str(e)}
            }

@tool_registry.register(
    name="get_system_info",
    description="Fournit les informations système matérielles (CPU, mémoire vive RAM, stockage, batterie).",
    parameters={}
)
def get_system_info() -> Dict[str, Any]:
    """Récupère l'utilisation CPU, RAM, disque et état de la batterie."""
    try:
        import psutil
        cpu_usage = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\" if os.name == "nt" else "/")

        battery_info = "Non disponible"
        if hasattr(psutil, "sensors_battery"):
            bat = psutil.sensors_battery()
            if bat:
                plugged = "en charge" if bat.power_plugged else "sur batterie"
                battery_info = f"{bat.percent}% ({plugged})"

        summary = (
            f"Processeur à {cpu_usage}%, RAM à {mem.percent}% "
            f"({round(mem.used / (1024**3), 1)} Go sur {round(mem.total / (1024**3), 1)} Go), "
            f"Disque C à {disk.percent}% ({round(disk.free / (1024**3), 1)} Go libres)."
        )

        return {
            "speech": summary,
            "data": {
                "cpu_percent": cpu_usage,
                "ram_percent": mem.percent,
                "ram_used_gb": round(mem.used / (1024**3), 1),
                "ram_total_gb": round(mem.total / (1024**3), 1),
                "disk_free_gb": round(disk.free / (1024**3), 1),
                "battery": battery_info
            }
        }
    except Exception as e:
        return {
            "speech": "Impossible de lire les données du système.",
            "data": {"error": str(e)}
        }
