"""Tests permissions outils : deny bloque, allow contourne la confirmation, persistance."""
import sys

sys.path.insert(0, "C:/Users/lemou/OneDrive/Desktop/ESpace work IA/Ei")

from core.config import config
from tools.registry import tool_registry, Tool

# Outil factice avec confirmation requise (aucun effet de bord)
ran = []
tool_registry._tools["__test_perm__"] = Tool(
    name="__test_perm__", description="outil de test",
    parameters={}, handler=lambda: ran.append(1) or {"speech": "ok", "data": {}},
    requires_confirmation=True, category="test")
try:
    prev = dict(config.get("tool_permissions", {}) or {})

    # 1. Défaut = ask
    assert tool_registry.get_permission("__test_perm__") == "ask"

    # 2. deny -> bloqué sans exécution, sans confirmation
    assert tool_registry.set_permission("__test_perm__", "deny") is True
    r = tool_registry.execute("__test_perm__", {})
    assert r["success"] is False and "bloqu" in r["speech"], r
    assert ran == [], "handler exécuté malgré deny !"

    # 3. allow -> exécute SANS demander (pas de blocage 30s)
    assert tool_registry.set_permission("__test_perm__", "allow") is True
    r = tool_registry.execute("__test_perm__", {})
    assert r["success"] is True and ran == [1], r

    # 4. Valeurs invalides refusées
    assert tool_registry.set_permission("__test_perm__", "nimporte") is False
    assert tool_registry.set_permission("outil_inexistant_xyz", "allow") is False

    # 5. describe_all : forme tableau de bord
    desc = tool_registry.describe_all()
    assert isinstance(desc, list) and len(desc) >= 10, len(desc)
    row = [d for d in desc if d["name"] == "__test_perm__"][0]
    assert row["permission"] == "allow" and row["needs_confirmation"] is True, row
    assert set(row) == {"name", "description", "category", "needs_confirmation", "permission"}

    # 6. Validators protocol
    from core.protocol import VALIDATORS
    VALIDATORS["list_tools"](type="list_tools")
    VALIDATORS["set_tool_permission"](type="set_tool_permission", tool="x", permission="allow")
    print("ALL_PERMISSIONS_TESTS_PASSED")
finally:
    del tool_registry._tools["__test_perm__"]
    config.update({"tool_permissions": prev})
