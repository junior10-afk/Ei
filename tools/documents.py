import os
from typing import Dict, Any
from tools.registry import tool_registry

def _clean(s: str) -> str:
    return os.path.expanduser(os.path.expandvars(str(s).strip().strip("\"'")))

@tool_registry.register(
    name="read_local_document",
    description="Lit le contenu d'un fichier local sur l'ordinateur (texte, code source, markdown, json, csv, etc.)",
    parameters={"file_path": "str (chemin complet ou relatif du fichier)", "max_chars": "int (nombre maximum de caractères à lire, défaut: 4000)"}
)
def read_local_document(file_path: str, max_chars: int = 4000) -> Dict[str, Any]:
    path = _clean(file_path)
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
    path = _clean(file_path)
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


def _parse_page_spec(pages: str, total: int):
    """Convertit une spec comme '1-3,7' en indices 0-based validés."""
    indices = []
    for part in str(pages).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            bounds = part.split("-")
            if len(bounds) != 2:
                raise ValueError(f"Plage invalide : {part}")
            try:
                start = int(bounds[0].strip())
                end = int(bounds[1].strip())
            except ValueError:
                raise ValueError(f"Plage invalide : {part}")
            if start < 1 or end < 1 or start > end or end > total:
                raise ValueError(f"Plage hors limites : {part} (document : {total} pages)")
            indices.extend(range(start - 1, end))
        else:
            try:
                n = int(part)
            except ValueError:
                raise ValueError(f"Page invalide : {part}")
            if n < 1 or n > total:
                raise ValueError(f"Page hors limites : {part} (document : {total} pages)")
            indices.append(n - 1)
    if not indices:
        raise ValueError("Aucune page spécifiée")
    return indices


@tool_registry.register(
    name="lire_pdf",
    description="Lit le texte d'un fichier PDF local (20 premières pages par défaut)",
    parameters={
        "chemin": "str (chemin du fichier PDF)",
        "pages_max": "int (nombre maximum de pages à lire, défaut: 20)"
    },
    requires_confirmation=False,
    category="files",
)
def lire_pdf(chemin: str, pages_max: int = 20) -> Dict[str, Any]:
    from pypdf import PdfReader
    path = _clean(chemin)
    if not os.path.exists(path):
        return {"speech": "Le fichier PDF n'existe pas.", "data": {"error": "Fichier introuvable", "chemin": path}}
    try:
        reader = PdfReader(path)
        total = len(reader.pages)
        n = max(1, min(total, int(pages_max)))
        texts = []
        for i in range(n):
            texts.append(reader.pages[i].extract_text() or "")
        content = "\n".join(texts)
        return {
            "speech": f"J'ai lu {n} page(s) du PDF {os.path.basename(path)}.",
            "data": {"chemin": path, "pages_lues": n, "pages_total": total, "texte": content},
        }
    except Exception as e:
        return {"speech": "Impossible de lire ce fichier PDF.", "data": {"error": str(e), "chemin": path}}


@tool_registry.register(
    name="fusionner_pdfs",
    description="Fusionne plusieurs fichiers PDF en un seul",
    parameters={
        "entrees": "list (chemins des fichiers PDF à fusionner)",
        "sortie": "str (chemin du fichier PDF de sortie)"
    },
    requires_confirmation=True,
    category="files",
)
def fusionner_pdfs(entrees: list, sortie: str) -> Dict[str, Any]:
    from pypdf import PdfWriter
    try:
        if not entrees or len(entrees) < 2:
            return {"speech": "Il faut au moins deux fichiers PDF à fusionner.", "data": {"error": "Moins de deux entrées"}}
        for e in entrees:
            if not os.path.exists(e):
                return {"speech": f"Le fichier {os.path.basename(str(e))} n'existe pas.", "data": {"error": f"Fichier introuvable : {e}"}}
        out = os.path.abspath(_clean(sortie))
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        writer = PdfWriter()
        for e in entrees:
            writer.append(e)
        with open(out, "wb") as f:
            writer.write(f)
        writer.close()
        return {
            "speech": f"PDF fusionné enregistré sous {os.path.basename(out)}.",
            "data": {"sortie": out, "fichiers": len(entrees)},
        }
    except Exception as e:
        return {"speech": "Impossible de fusionner ces fichiers PDF.", "data": {"error": str(e)}}


@tool_registry.register(
    name="diviser_pdf",
    description="Extrait des pages d'un PDF vers un nouveau fichier (ex: 1-3,7)",
    parameters={
        "chemin": "str (chemin du fichier PDF source)",
        "pages": "str (pages à extraire, ex: 1-3,7)",
        "sortie": "str (chemin du fichier PDF de sortie)"
    },
    requires_confirmation=True,
    category="files",
)
def diviser_pdf(chemin: str, pages: str, sortie: str) -> Dict[str, Any]:
    from pypdf import PdfReader, PdfWriter
    path = _clean(chemin)
    if not os.path.exists(path):
        return {"speech": "Le fichier PDF n'existe pas.", "data": {"error": "Fichier introuvable", "chemin": path}}
    try:
        reader = PdfReader(path)
        total = len(reader.pages)
        indices = _parse_page_spec(pages, total)
        writer = PdfWriter()
        for i in indices:
            writer.add_page(reader.pages[i])
        out = os.path.abspath(_clean(sortie))
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        with open(out, "wb") as f:
            writer.write(f)
        return {
            "speech": f"{len(indices)} page(s) extraite(s) vers {os.path.basename(out)}.",
            "data": {"sortie": out, "pages_extraites": len(indices), "pages_total": total},
        }
    except ValueError as e:
        return {"speech": "Spécification de pages invalide.", "data": {"error": str(e)}}
    except Exception as e:
        return {"speech": "Impossible de diviser ce fichier PDF.", "data": {"error": str(e)}}
