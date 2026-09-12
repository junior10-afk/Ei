import os
from typing import Dict, Any
from tools.registry import tool_registry

@tool_registry.register(
    name="read_local_document",
    description="Lit le contenu d'un fichier local sur l'ordinateur (texte, code source, markdown, json, csv, etc.)",
    parameters={"file_path": "str (chemin complet ou relatif du fichier)", "max_chars": "int (nombre maximum de caractères à lire, défaut: 4000)"}
)
def read_local_document(file_path: str, max_chars: int = 4000) -> Dict[str, Any]:
    path = os.path.expanduser(os.path.expandvars(str(file_path).strip().strip('"\'')))
    if not os.path.exists(path):
        return {
            "speech": f"Le fichier {os.path.basename(path)} n'existe pas.",
            "error": "Fichier introuvable",
            "file_path": path
        }

    try:
        limit = max(500, min(20000, int(max_chars)))
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(limit)
        
        return {
            "speech": f"J'ai lu le fichier {os.path.basename(path)}.",
            "file_path": path,
            "size": os.path.getsize(path),
            "content": content
        }
    except Exception as e:
        return {
            "speech": f"Impossible de lire le fichier {os.path.basename(path)}.",
            "error": str(e),
            "file_path": path
        }

@tool_registry.register(
    name="write_local_file",
    description="Crée ou sauvegarde un fichier texte, code ou document sur l'ordinateur",
    parameters={"file_path": "str (chemin du fichier à créer)", "content": "str (contenu textuel complet à écrire)"},
    requires_confirmation=True,
    category="files"
)
def write_local_file(file_path: str, content: str) -> Dict[str, Any]:
    path = os.path.expanduser(os.path.expandvars(str(file_path).strip().strip('"\'')))
    abs_path = os.path.abspath(path)
    
    # Sécurité : interdire l'écriture dans les dossiers système Windows
    win_dir = os.environ.get("SystemRoot", r"C:\Windows").lower()
    prog_files = os.environ.get("ProgramFiles", r"C:\Program Files").lower()
    prog_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)").lower()
    low_path = abs_path.lower()
    if (
        low_path.startswith(win_dir)
        or low_path.startswith(prog_files)
        or low_path.startswith(prog_files_x86)
    ):
        return {
            "speech": "Écriture refusée dans un répertoire système protégé.",
            "error": "Accès refusé au répertoire système protégé",
            "file_path": abs_path,
            "success": False
        }

    try:
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return {
            "speech": f"Fichier {os.path.basename(abs_path)} enregistré avec succès.",
            "file_path": abs_path,
            "bytes_written": len(content.encode("utf-8")),
            "success": True
        }
    except Exception as e:
        return {
            "speech": f"Erreur lors de l'enregistrement de {os.path.basename(abs_path)}.",
            "error": str(e),
            "file_path": abs_path,
            "success": False
        }
