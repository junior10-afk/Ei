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
    prev.pop("__test_perm__", None)
    prev_default = config.get("tools_default_permission", "ask")
    perms = dict(prev)
    perms.pop("__test_perm__", None)
    perms.update({"__test_perm__": "ask"})
    config.update({"tool_permissions": perms, "tools_default_permission": "ask"})

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
    assert set(row) == {"name", "label", "description", "category", "needs_confirmation", "permission"}
    assert row["label"] == row["name"], "outil inconnu : repli sur nom brut attendu"
    web = [d for d in desc if d["name"] == "web_search"][0]
    assert web["label"] == "Rechercher sur le web", web

    # 6. Validators protocol
    from core.protocol import VALIDATORS
    VALIDATORS["list_tools"](type="list_tools")
    VALIDATORS["set_tool_permission"](type="set_tool_permission", tool="x", permission="allow")
    print("ALL_PERMISSIONS_TESTS_PASSED")
finally:
    del tool_registry._tools["__test_perm__"]
    perms = dict(config.get("tool_permissions", {}) or {})
    perms.pop("__test_perm__", None)
    for k, v in prev.items():
        perms[k] = v
    config.set("tool_permissions", perms)
    config.set("tools_default_permission", prev_default)
