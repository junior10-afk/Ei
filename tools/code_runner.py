import os
import sys
import ast
import time
import subprocess
from typing import Dict, Any, Optional
from tools.registry import tool_registry

FORBIDDEN_MODULES = {
    "subprocess", "pty", "ctypes", "winreg", "socket", "_socket",
    "multiprocessing", "threading"
}

FORBIDDEN_CALLS = {
    "system", "popen", "spawn", "spawnl", "spawnle", "spawnv", "spawnve",
    "kill", "rmdir", "removedirs", "format", "eval", "exec", "__import__"
}

def validate_python_code_ast(code_str: str) -> Optional[str]:
    """
    Analyse statique de l'AST pour détecter et bloquer le code Python dangereux ou malveillant.
    Retourne None si le code est sain, ou un message explicatif du blocage.
    """
    try:
        tree = ast.parse(code_str)
    except SyntaxError as se:
        return f"Erreur de syntaxe Python : {se}"

    for node in ast.walk(tree):
        # 1. Vérification des imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.split('.')[0]
                if mod in FORBIDDEN_MODULES:
                    return f"Import du module interdit pour des raisons de sécurité : '{mod}'"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod = node.module.split('.')[0]
                if mod in FORBIDDEN_MODULES:
                    return f"Import depuis le module interdit : '{mod}'"

        # 2. Vérification des appels de fonctions dangereuses
        elif isinstance(node, ast.Call):
            func = node.func
            # Appel direct nom() ex: eval(...)
            if isinstance(func, ast.Name) and func.id in {"eval", "exec", "__import__"}:
                return f"Appel direct de la fonction interdite : '{func.id}'"
            # Appel d'attribut obj.attr() ex: os.system(...)
            elif isinstance(func, ast.Attribute):
                if func.attr in FORBIDDEN_CALLS:
                    if isinstance(func.value, ast.Name) and func.value.id in {"os", "shutil", "builtins"}:
                        return f"Appel interdit : '{func.value.id}.{func.attr}'"

        # 3. Empêcher l'accès direct aux attributs spéciaux de réflexion
        elif isinstance(node, ast.Attribute):
            if node.attr in {"__subclasses__", "__bases__", "__globals__", "__builtins__"}:
                return f"Tentative d'évasion sandbox détectée via l'attribut spécial : '{node.attr}'"

    return None

def get_sanitized_env() -> Dict[str, str]:
    """Prépare un environnement sans secrets API ni tokens sensibles."""
    safe_env = {}
    for k, v in os.environ.items():
        uk = k.upper()
        if (
            "API_KEY" in uk
            or "SECRET" in uk
            or "TOKEN" in uk
            or "PASSWORD" in uk
            or "AUTH" in uk
        ):
            continue
        safe_env[k] = v
    return safe_env

@tool_registry.register(
    name="execute_python_code",
    description="Écrit et exécute du code Python localement pour des calculs, analyses de données ou opérations techniques",
    parameters={"code": "str (code Python complet à exécuter)", "timeout": "int (temps maximal d'exécution en secondes, défaut: 15)"},
    requires_confirmation=True,
    category="technical"
)
def execute_python_code(code: str, timeout: int = 15) -> Dict[str, Any]:
    code_str = str(code).strip()
    if not code_str:
        return {"speech": "Aucun code à exécuter.", "error": "Code vide", "success": False}

    # Validation AST de sécurité
    security_issue = validate_python_code_ast(code_str)
    if security_issue:
        return {
            "speech": "Exécution refusée pour des raisons de sécurité.",
            "error": security_issue,
            "success": False
        }

    t0 = time.time()
    try:
        max_t = max(2, min(30, int(timeout)))
        safe_env = get_sanitized_env()

        proc = subprocess.run(
            [sys.executable, "-I", "-c", code_str],
            capture_output=True,
            text=True,
            timeout=max_t,
            env=safe_env
        )
        dur = round(time.time() - t0, 2)
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        exit_code = proc.returncode

        if exit_code == 0:
            speech = f"Code exécuté avec succès en {dur} seconde{'s' if dur > 1 else ''}."
            return {
                "speech": speech,
                "success": True,
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
                "duration_sec": dur
            }
        else:
            return {
                "speech": f"Le code a généré une erreur (code {exit_code}).",
                "success": False,
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
                "error": stderr or stdout
            }
    except subprocess.TimeoutExpired:
        return {
            "speech": f"L'exécution du code a dépassé le délai de sécurité de {timeout} secondes.",
            "success": False,
            "error": "TimeoutExpired"
        }
    except Exception as e:
        return {
            "speech": f"Erreur lors de l'exécution : {str(e)[:100]}",
            "success": False,
            "error": str(e)
        }
