from typing import Callable, Dict, Any, List, Optional
import json

class Tool:
    def __init__(self, name: str, description: str, parameters: Dict[str, Any], handler: Callable[..., Any]):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler

    def execute(self, **kwargs) -> Any:
        return self.handler(**kwargs)

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, name: str, description: str, parameters: Dict[str, Any]):
        """Décorateur pour enregistrer un outil."""
        def decorator(func: Callable):
            tool = Tool(name=name, description=description, parameters=parameters, handler=func)
            self._tools[name] = tool
            return func
        return decorator

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Tool]:
        return list(self._tools.values())

    def get_prompt_schemas(self) -> str:
        """Retourne la liste des outils formatée pour le System Prompt."""
        schemas = []
        for tool in self._tools.values():
            schemas.append({
                "action": tool.name,
                "description": tool.description,
                "params": tool.parameters
            })
        return json.dumps(schemas, indent=2, ensure_ascii=False)

    def execute(self, action_name: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Exécute un outil par son nom avec ses paramètres."""
        params = params or {}
        tool = self.get(action_name)
        if not tool:
            return {
                "success": False,
                "error": f"Outil inconnu: {action_name}",
                "speech": f"Désolé, je ne connais pas l'action {action_name}."
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
