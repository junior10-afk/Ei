import re
import json
import time
import threading
from typing import Callable, Dict, Any, List, Optional

def normalize_to_json_schema(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Convertit un dictionnaire de paramètres (format string simple ou dict) en JSON Schema standard."""
    if not parameters:
        return {"type": "object", "properties": {}, "required": []}
    if parameters.get("type") == "object" and "properties" in parameters:
        return parameters

    properties = {}
    required = []
    for param_name, spec in parameters.items():
        if isinstance(spec, dict):
            properties[param_name] = spec
            if spec.get("required", False):
                required.append(param_name)
        elif isinstance(spec, str):
            spec_str = spec.strip()
            p_type = "string"
            desc = spec_str
            m = re.match(r"^(str|int|float|bool|list|dict)(?:\s*\((.*?)\))?$", spec_str, re.I)
            if m:
                t_str = m.group(1).lower()
                desc = m.group(2) if m.group(2) else ""
                type_map = {
                    "str": "string",
                    "int": "integer",
                    "float": "number",
                    "bool": "boolean",
                    "list": "array",
                    "dict": "object"
                }
                p_type = type_map.get(t_str, "string")
            properties[param_name] = {
                "type": p_type,
                "description": desc or param_name
            }
            if "défaut" not in desc.lower() and "optionnel" not in desc.lower() and "optional" not in desc.lower():
                required.append(param_name)
        else:
            properties[param_name] = {"type": "string", "description": str(spec)}

    return {
        "type": "object",
        "properties": properties,
        "required": required
    }

class Tool:
    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable[..., Any],
        requires_confirmation: bool = False,
        category: str = "general"
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.json_schema = normalize_to_json_schema(parameters)
        self.handler = handler
        self.requires_confirmation = requires_confirmation
        self.category = category

    def execute(self, **kwargs) -> Any:
        return self.handler(**kwargs)

    def to_openai_schema(self) -> Dict[str, Any]:
        """Format fonction OpenAI / Groq / Mistral / Ollama."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.json_schema
            }
        }

class ToolConfirmationManager:
    """Gestionnaire de confirmation interactive pour les outils sensibles (code_runner, écriture, etc.)."""
    def __init__(self):
        self._lock = threading.Lock()
        self._pending: Dict[str, Dict[str, Any]] = {}
        self.bypass_all: bool = False

    def request_confirmation(self, action_name: str, params: Dict[str, Any], description: str, timeout_sec: float = 30.0) -> bool:
        if self.bypass_all:
            return True

        from core.bus import bus
        if not bus.clients:
            print(f"[ToolRegistry] Action sensible '{action_name}' : aucun HUD connecté pour autoriser. Exécution bloquée par sécurité.")
            return False

        import uuid
        import time
        req_id = f"conf_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        event = threading.Event()
        with self._lock:
            self._pending[req_id] = {
                "event": event,
                "confirmed": False
            }

        bus.broadcast_threadsafe({
            "type": "tool_confirmation_request",
            "request_id": req_id,
            "action": action_name,
            "params": params,
            "description": description
        })
        print(f"[ToolRegistry] Demande de confirmation envoyée au HUD pour '{action_name}' (ID: {req_id}).")

        got = event.wait(timeout_sec)
        with self._lock:
            req = self._pending.pop(req_id, None)

        if not got or not req:
            print(f"[ToolRegistry] Délai de confirmation expiré pour '{action_name}'.")
            return False

        return req.get("confirmed", False)

    def resolve(self, request_id: str, confirmed: bool):
        with self._lock:
            req = self._pending.get(request_id)
            if req:
                req["confirmed"] = confirmed
                req["event"].set()

tool_confirmation_manager = ToolConfirmationManager()

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        requires_confirmation: bool = False,
        category: str = "general"
    ):
        """Décorateur pour enregistrer un outil."""
        def decorator(func: Callable):
            tool = Tool(
                name=name,
                description=description,
                parameters=parameters,
                handler=func,
                requires_confirmation=requires_confirmation,
                category=category
            )
            self._tools[name] = tool
            return func
        return decorator

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Tool]:
        return list(self._tools.values())

    def get_prompt_schemas(self, names: Optional[List[str]] = None) -> str:
        """Retourne la liste des outils formatée pour le System Prompt (mode texte/fallback)."""
        schemas = []
        tools_to_list = [self._tools[n] for n in names if n in self._tools] if names else self._tools.values()
        for tool in tools_to_list:
            schemas.append({
                "action": tool.name,
                "description": tool.description,
                "params": tool.parameters
            })
        return json.dumps(schemas, indent=2, ensure_ascii=False)

    def get_openai_tools(self, names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Retourne les outils au format standard OpenAI function-calling."""
        tools_to_list = [self._tools[n] for n in names if n in self._tools] if names else self._tools.values()
        return [tool.to_openai_schema() for tool in tools_to_list]

    def get_gemini_tools(self, names: Optional[List[str]] = None) -> Optional[Any]:
        """Convertit les outils pour le SDK Google GenAI."""
        try:
            from google.genai import types
            tools_to_list = [self._tools[n] for n in names if n in self._tools] if names else self._tools.values()
            declarations = []
            for tool in tools_to_list:
                declarations.append(types.FunctionDeclaration(
                    name=tool.name,
                    description=tool.description,
                    parameters=tool.json_schema
                ))
            if declarations:
                return [types.Tool(function_declarations=declarations)]
            return None
        except Exception as e:
            print(f"[ToolRegistry] Erreur conversion schéma Gemini: {e}")
            return None

    def execute(self, action_name: str, params: Optional[Dict[str, Any]] = None, bypass_confirmation: bool = False) -> Dict[str, Any]:
        """Exécute un outil par son nom avec ses paramètres et vérifie la confirmation si requise."""
        params = params or {}
        tool = self.get(action_name)
        if not tool:
            return {
                "success": False,
                "error": f"Outil inconnu: {action_name}",
                "speech": f"Désolé, je ne connais pas l'action {action_name}."
            }

        # Vérification de sécurité confirmation interactive
        if tool.requires_confirmation and not bypass_confirmation:
            is_confirmed = tool_confirmation_manager.request_confirmation(
                action_name, params, tool.description
            )
            if not is_confirmed:
                return {
                    "success": False,
                    "action": action_name,
                    "error": "Confirmation refusée ou délai d'attente dépassé.",
                    "speech": f"L'exécution de {action_name} a été refusée ou le délai a expiré."
                }

        try:
            result = tool.execute(**params)
            return {
                "success": True,
                "action": action_name,
                "params": params,
                "result": result.get("data", result) if isinstance(result, dict) else result,
                "speech": result.get("speech", "Action effectuée.") if isinstance(result, dict) else "Action effectuée."
            }
        except Exception as e:
            print(f"[ToolRegistry] Erreur lors de l'exécution de {action_name}: {e}")
            return {
                "success": False,
                "action": action_name,
                "error": str(e),
                "speech": f"Une erreur est survenue lors de l'exécution de l'action."
            }

tool_registry = ToolRegistry()

