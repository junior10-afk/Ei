"""Client MCP minimal (stdio, JSON-RPC) pour Ei. Stdlib uniquement."""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.registry import tool_registry

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"

PROTOCOL_VERSION = "2024-11-05"
DEFAULT_TIMEOUT = 10.0


def _normalize_command(server_config: Dict[str, Any]) -> List[str]:
    """Normalise la config serveur -> liste de commande argv.

    Accepte ``command`` comme liste (ex: ["cmd", "/c", "npx", ...])
    ou comme chaine + ``args`` (ex: command="cmd", args=["/c", "npx", ...]).
    """
    cmd = server_config.get("command")
    args = server_config.get("args", []) or []
    if isinstance(cmd, list) and cmd:
        return [str(c) for c in cmd]
    if isinstance(cmd, str) and cmd:
        if args:
            return [cmd] + [str(a) for a in args]
        return [cmd]
    raise ValueError("config serveur MCP invalide: cle 'command' manquante")


class MCPConnection:
    """Connexion stdio a un serveur MCP (JSON-RPC, une requete a la fois)."""

    def __init__(self, command: List[str], timeout: float = DEFAULT_TIMEOUT):
        self.command = command
        self.timeout = float(timeout or DEFAULT_TIMEOUT)
        self.proc: Optional[asyncio.subprocess.Process] = None
        self._next_id = 0

    async def connect(self) -> None:
        self.proc = await asyncio.create_subprocess_exec(
            self.command[0],
            *self.command[1:],
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )

    async def request(
        self, method: str, params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Envoie une requete JSON-RPC et attend la reponse matchee par id."""
        if self.proc is None or self.proc.stdin is None or self.proc.stdout is None:
            return {"error": {"code": -32000, "message": "serveur MCP non connecte"}}
        self._next_id += 1
        req_id = self._next_id
        msg: Dict[str, Any] = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            msg["params"] = params
        try:
            self.proc.stdin.write((json.dumps(msg) + "\n").encode("utf-8"))
            await self.proc.stdin.drain()
        except Exception as e:
            return {"error": {"code": -32000, "message": f"ecriture stdin: {e}"}}
        deadline = float(timeout or self.timeout)
        try:
            async with asyncio.timeout(deadline):
                while True:
                    line = await self.proc.stdout.readline()
                    if not line:
                        return {"error": {"code": -32000, "message": "serveur MCP ferme (EOF)"}}
                    try:
                        resp = json.loads(line.decode("utf-8"))
                    except Exception:
                        continue
                    if resp.get("id") != req_id:
                        continue  # notification ou reponse d'une autre requete
                    if "error" in resp and resp["error"] is not None:
                        return {"error": resp["error"]}
                    result = resp.get("result", {})
                    return result if isinstance(result, dict) else {"result": result}
        except TimeoutError:
            return {"error": {"code": -32000, "message": f"timeout MCP ({deadline}s) sur {method}"}}

    async def initialize(self) -> Dict[str, Any]:
        return await self.request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "Ei", "version": "1.0"},
        })

    async def notify_initialized(self) -> None:
        if self.proc is not None and self.proc.stdin is not None:
            try:
                self.proc.stdin.write(
                    (json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n").encode("utf-8")
                )
                await self.proc.stdin.drain()
            except Exception:
                pass

    async def list_tools(self) -> Dict[str, Any]:
        return await self.request("tools/list")

    async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return await self.request("tools/call", {"name": name, "arguments": arguments or {}})

    async def close(self) -> None:
        if self.proc is None:
            return
        try:
            try:
                if self.proc.stdin is not None:
                    self.proc.stdin.close()
            except Exception:
                pass
            try:
                self.proc.terminate()
                await asyncio.wait_for(self.proc.wait(), timeout=3)
            except TimeoutError:
                try:
                    self.proc.kill()
                except Exception:
                    pass
        finally:
            self.proc = None


async def _open_session(server_config: Dict[str, Any]) -> MCPConnection:
    command = _normalize_command(server_config)
    timeout = float(server_config.get("timeout", DEFAULT_TIMEOUT))
    conn = MCPConnection(command, timeout)
    try:
        await conn.connect()
    except Exception as e:
        raise RuntimeError(f"impossible de lancer le serveur MCP: {e}")
    try:
        res = await conn.initialize()
        if isinstance(res, dict) and "error" in res:
            raise RuntimeError(f"echec initialize: {res['error']}")
        await conn.notify_initialized()
        return conn
    except Exception:
        await conn.close()
        raise


async def _alist(server_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    conn = await _open_session(server_config)
    try:
        res = await conn.list_tools()
        if "error" in res:
            raise RuntimeError(f"erreur tools/list: {res['error']}")
        out = []
        for t in res.get("tools", []):
            out.append({
                "name": t.get("name", ""),
                "description": t.get("description", ""),
                "inputSchema": t.get("inputSchema", {}),
            })
        return out
    finally:
        await conn.close()


async def _acall(server_config: Dict[str, Any], tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    conn = await _open_session(server_config)
    try:
        res = await conn.call_tool(tool_name, args)
        if "error" in res:
            raise RuntimeError(f"erreur tools/call: {res['error']}")
        return res
    finally:
        await conn.close()


def _run(coro):
    """asyncio.run survivable depuis une boucle deja active (via thread dedie)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


def mcp_list_tools(server_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Liste les outils d'un serveur MCP. Retourne [] en cas d'erreur."""
    try:
        return _run(_alist(server_config))
    except Exception:
        return []


def mcp_call_tool(
    server_config: Dict[str, Any], tool_name: str, args: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Appelle un outil MCP. En cas d'erreur retourne un dict avec cle 'error'."""
    try:
        return _run(_acall(server_config, tool_name, args or {}))
    except Exception as e:
        return {"isError": True, "error": str(e)}


def _load_mcp_servers() -> Dict[str, Any]:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        servers = data.get("mcp_servers", {})
        return servers if isinstance(servers, dict) else {}
    except Exception:
        return {}


@tool_registry.register(
    name="mcp_appeler",
    description="Appelle un outil d'un serveur MCP declare dans config.json (cle mcp_servers)",
    parameters={
        "serveur": "str (nom du serveur MCP declare dans config.json, cle mcp_servers)",
        "outil": "str (nom de l'outil MCP a appeler sur ce serveur)",
        "arguments": "optional str (arguments JSON de l'outil, objet JSON en texte, defaut: {})",
    },
    requires_confirmation=True,
    category="mcp",
)
def mcp_appeler(serveur: str, outil: str, arguments: str = "{}") -> Dict[str, Any]:
    servers = _load_mcp_servers()
    if not servers:
        return {
            "speech": "Aucun serveur MCP configuré dans config.json.",
            "data": {"error": "aucun serveur MCP configuré"},
        }
    if serveur not in servers:
        return {
            "speech": f"Serveur MCP inconnu: {serveur}. Serveurs connus: {', '.join(sorted(servers))}.",
            "data": {"error": f"serveur inconnu: {serveur}", "connus": sorted(servers)},
        }
    cfg = dict(servers[serveur])
    cfg.setdefault("name", serveur)
    if isinstance(arguments, dict):
        args = arguments
    else:
        raw = (arguments or "").strip() if isinstance(arguments, str) else ""
        if not raw:
            args = {}
        else:
            try:
                args = json.loads(raw)
            except Exception:
                return {
                    "speech": "Arguments JSON invalides pour l'appel MCP.",
                    "data": {"error": "arguments JSON invalides"},
                }
            if not isinstance(args, dict):
                return {
                    "speech": "Les arguments MCP doivent être un objet JSON.",
                    "data": {"error": "arguments non-objet"},
                }
    res = mcp_call_tool(cfg, outil, args)
    if isinstance(res, dict) and ("error" in res or res.get("isError")):
        return {
            "speech": f"Erreur du serveur MCP {serveur} lors de l'appel à {outil}.",
            "data": {"serveur": serveur, "outil": outil, "error": res.get("error")},
        }
    return {
        "speech": f"Outil {outil} exécuté sur le serveur {serveur}.",
        "data": {"serveur": serveur, "outil": outil, "result": res},
    }
