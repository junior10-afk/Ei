import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from tools.mcp_client import mcp_appeler, mcp_call_tool, mcp_list_tools

# Faux serveur MCP stdio (~30 lignes): repond initialize / tools-list / tools-call.
FAKE_SERVER_CODE = """import sys, json
def rep(i, r):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": i, "result": r}) + "\\n")
    sys.stdout.flush()
TOOLS = [{"name": "echo", "description": "Renvoie les arguments", "inputSchema": {"type": "object"}},
    {"name": "ping", "description": "Repond pong", "inputSchema": {"type": "object"}}]
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        m = json.loads(line)
    except Exception:
        continue
    i = m.get("id")
    if i is None:
        continue
    n = m.get("method")
    p = m.get("params") or {}
    if n == "initialize":
        rep(i, {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
            "serverInfo": {"name": "fake", "version": "1.0"}})
    elif n == "tools/list":
        rep(i, {"tools": TOOLS})
    elif n == "tools/call":
        a = p.get("arguments") or {}
        rep(i, {"content": [{"type": "text", "text": json.dumps(a)}]})
    else:
        rep(i, {})
"""


class TestMCPClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.fake_path = str(Path(cls._tmp.name) / "fake_mcp_server.py")
        with open(cls.fake_path, "w", encoding="utf-8") as f:
            f.write(FAKE_SERVER_CODE)
        cls.cfg = {"name": "fake", "command": [sys.executable, cls.fake_path], "timeout": 10}

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_list_returns_two_tools(self):
        tools = mcp_list_tools(self.cfg)
        self.assertEqual(len(tools), 2)
        names = sorted(t["name"] for t in tools)
        self.assertEqual(names, ["echo", "ping"])
        for t in tools:
            self.assertIn("description", t)
            self.assertIn("inputSchema", t)

    def test_call_echoes_args(self):
        res = mcp_call_tool(self.cfg, "echo", {"msg": "bonjour"})
        self.assertNotIn("error", res)
        text = res["content"][0]["text"]
        self.assertEqual(json.loads(text), {"msg": "bonjour"})

    def test_bad_command_returns_error(self):
        bad = {"name": "bad", "command": ["__commande_inexistante_ei__"], "timeout": 5}
        res = mcp_call_tool(bad, "echo", {})
        self.assertIn("error", res)
        self.assertEqual(mcp_list_tools(bad), [])

    def test_handler_sans_serveurs(self):
        with mock.patch("tools.mcp_client._load_mcp_servers", return_value={}):
            res = mcp_appeler(serveur="fs", outil="echo", arguments="{}")
        self.assertIn("aucun serveur MCP", res["data"]["error"])
        self.assertIn("Aucun serveur MCP", res["speech"])


if __name__ == "__main__":
    unittest.main()
