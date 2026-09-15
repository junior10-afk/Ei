import ast
import operator
from typing import Dict, Any
from tools.registry import tool_registry

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_ALLOWED_NAMES = {"abs": abs, "round": round, "min": min, "max": max}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_BINOPS:
            raise ValueError(f"Opérateur non autorisé : {op_type.__name__}")
        return _ALLOWED_BINOPS[op_type](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.UAdd):
            return +_eval(node.operand)
        if isinstance(node.op, ast.USub):
            return -_eval(node.operand)
        raise ValueError(f"Opérateur unaire non autorisé : {type(node.op).__name__}")
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        raise ValueError("Seuls les nombres sont autorisés")
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in _ALLOWED_NAMES:
            if node.keywords:
                raise ValueError("Arguments nommés non autorisés")
            func = _ALLOWED_NAMES[node.func.id]
            return func(*[_eval(a) for a in node.args])
        raise ValueError("Fonction non autorisée")
    raise ValueError(f"Expression non autorisée : {type(node).__name__}")


@tool_registry.register(
    name="calculer",
    description="Évalue une expression mathématique simple (ex: 2*(3+4))",
    parameters={"expression": "str (expression mathématique, ex: 2*(3+4))"},
    requires_confirmation=False,
    category="local",
)
def calculer(expression: str) -> Dict[str, Any]:
    try:
        tree = ast.parse(str(expression), mode="eval")
        result = _eval(tree)
        if isinstance(result, bool) or not isinstance(result, (int, float)):
            raise ValueError("Résultat non numérique")
        return {
            "speech": f"Le résultat est {result}.",
            "data": {"expression": expression, "result": result},
        }
    except Exception as e:
        return {
            "speech": "Expression invalide, calcul impossible.",
            "data": {"error": str(e), "expression": expression},
        }
