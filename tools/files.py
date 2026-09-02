import os
import subprocess
from pathlib import Path
from typing import Dict, Any
from tools.registry import tool_registry

@tool_registry.register(
    name="open_folder",
    description="Ouvre un dossier spécifique dans l'explorateur Windows",
    parameters={"path": "str (ex: Desktop, Documents, Downloads ou chemin complet)"}
)
def open_folder(path: str = "Desktop") -> Dict[str, Any]:
    home = Path.home()
    aliases = {
        "desktop": home / "Desktop",
        "bureau": home / "Desktop",
        "documents": home / "Documents",
        "téléchargements": home / "Downloads",
        "downloads": home / "Downloads",
        "images": home / "Pictures",
        "musique": home / "Music"
    }

    target = aliases.get(path.lower().strip(), Path(path))
    if not target.is_absolute():
        target = home / target

    if target.exists():
        os.startfile(str(target))
        return {
            "speech": f"J'ouvre le dossier {target.name}.",
            "data": {"path": str(target)}
        }
    else:
        return {
            "speech": f"Le dossier {path} n'existe pas.",
            "data": {"error": "Path not found"}
        }

@tool_registry.register(
    name="list_folder",
    description="Liste les fichiers dans un dossier",
    parameters={"path": "str (dossier à lister)"}
)
def list_folder(path: str = "Desktop") -> Dict[str, Any]:
    home = Path.home()
    aliases = {
        "desktop": home / "Desktop",
        "bureau": home / "Desktop",
        "documents": home / "Documents",
        "téléchargements": home / "Downloads",
        "downloads": home / "Downloads"
    }
    target = aliases.get(path.lower().strip(), Path(path))
    if not target.is_absolute():
        target = home / target

    if not target.exists() or not target.is_dir():
        return {"speech": "Dossier introuvable.", "data": {"error": "Not found"}}

    try:
        items = [f.name for f in target.iterdir()][:10]
        count = len(items)
        return {
            "speech": f"Le dossier contient {count} éléments récents.",
            "data": {"items": items, "path": str(target)}
        }
    except Exception as e:
        return {"speech": "Erreur lors de la lecture du dossier.", "data": {"error": str(e)}}
