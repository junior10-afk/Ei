import os
import re
import socket
import ipaddress
import urllib.parse
from html import unescape
from typing import Dict, Any, List, Optional, Tuple
import requests
from tools.registry import tool_registry

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"
}

def is_safe_public_url(url_str: str) -> Tuple[bool, Optional[str]]:
    """
    Vérifie rigoureusement qu'une URL ne pointe pas vers une adresse locale, privée ou de métadonnées (anti-SSRF).
    """
    try:
        parsed = urllib.parse.urlparse(url_str)
        if parsed.scheme not in ("http", "https"):
            return False, f"Protocole non supporté : '{parsed.scheme}' (seuls http et https sont autorisés)"

        hostname = parsed.hostname
        if not hostname:
            return False, "Nom d'hôte manquant dans l'URL"

        # Vérifier si c'est un localhost évident
        if hostname.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            return False, "Accès à localhost interdit"

        # Résolution DNS
        addr_infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
        for family, _, _, _, sockaddr in addr_infos:
            ip_str = sockaddr[0]
            ip_obj = ipaddress.ip_address(ip_str)

            # Bloquer adresses privées, loopback, link-local, broadcast, multicast
            if (
                ip_obj.is_private
                or ip_obj.is_loopback
                or ip_obj.is_link_local
                or ip_obj.is_reserved
                or ip_obj.is_multicast
            ):
                return False, f"Accès refusé vers une adresse réseau interne/protégée ({ip_str})"

            # Protection spécifique Cloud Metadata (ex: AWS, GCP, Azure 169.254.169.254)
            if str(ip_obj) == "169.254.169.254":
                return False, "Accès au service de métadonnées Cloud interdit"

        return True, None
    except Exception as e:
        return False, f"Impossible de résoudre l'hôte : {e}"

@tool_registry.register(
    name="web_search",
    description="Effectue une recherche Web en temps réel pour obtenir des informations récentes, actualités, faits ou réponses précises",
    parameters={"query": "str (termes de recherche en français ou anglais)", "max_results": "int (nombre de résultats souhaités, défaut: 5)"}
)
def web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    query_str = str(query).strip()
    if not query_str:
        return {"speech": "Aucun terme de recherche spécifié.", "error": "Requête vide", "results": []}

    max_r = max(1, min(10, int(max_results)))

    # 1. Tentative API Tavily si configurée
    tavily_key = os.getenv("TAVILY_API_KEY", "").strip()
    if tavily_key:
        try:
            res = requests.post(
                "https://api.tavily.com/search",
                json={"query": query_str, "api_key": tavily_key, "max_results": max_r},
                timeout=7
            )
            if res.status_code == 200:
                data = res.json()
                results = [
                    {"title": item.get("title", ""), "url": item.get("url", ""), "snippet": item.get("content", "")}
                    for item in data.get("results", [])[:max_r]
                ]
                if results:
                    return {
                        "speech": f"J'ai trouvé des informations récentes sur le Web pour « {query_str} ».",
                        "query": query_str,
                        "count": len(results),
                        "results": results,
                        "preview": results[0]["snippet"][:150]
                    }
        except Exception:
            pass

    # 2. Tentative DuckDuckGo JSON Instant Answer API
    try:
        ddg_api_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query_str)}&format=json&no_html=1&skip_disambig=1"
        resp = requests.get(ddg_api_url, headers=HEADERS, timeout=6)
        if resp.status_code == 200:
            ddg_data = resp.json()
            abstract = ddg_data.get("AbstractText", "")
            source_url = ddg_data.get("AbstractURL", "")
            results = []
            if abstract:
                results.append({
                    "title": ddg_data.get("Heading", "Résumé DuckDuckGo"),
                    "url": source_url or "https://duckduckgo.com",
                    "snippet": abstract
                })
            for topic in ddg_data.get("RelatedTopics", []):
                if len(results) >= max_r:
                    break
                if isinstance(topic, dict) and "Text" in topic:
                    results.append({
                        "title": topic.get("FirstURL", "").split("/")[-1].replace("_", " ") or "Info liée",
                        "url": topic.get("FirstURL", ""),
                        "snippet": topic.get("Text", "")
                    })

            if results:
                return {
                    "speech": f"J'ai trouvé des données encyclopédiques pour « {query_str} ».",
                    "query": query_str,
                    "count": len(results),
                    "results": results,
                    "preview": results[0]["snippet"][:150]
                }
    except Exception:
        pass

    # 3. Repli résilient DuckDuckGo HTML / Lite
    try:
        url = "https://html.duckduckgo.com/html/"
        resp = requests.post(url, data={"q": query_str}, headers=HEADERS, timeout=8)
        if resp.status_code == 200:
            matches = re.findall(
                r'<a\s+class="result__snippet[^"]*"\s+href="([^"]+)"[^>]*>(.*?)</a>',
                resp.text,
                re.DOTALL
            )
            results: List[Dict[str, str]] = []
            for i, (href, snippet) in enumerate(matches[:max_r]):
                text = re.sub(r'<[^>]+>', '', snippet)
                text = unescape(text).strip()
                actual_url = href
                if "uddg=" in href:
                    try:
                        actual_url = urllib.parse.unquote(href.split("uddg=")[1].split("&")[0])
                    except Exception:
                        actual_url = href

                results.append({
                    "title": f"Source {i+1}",
                    "url": actual_url,
                    "snippet": text
                })

            if results:
                return {
                    "speech": f"J'ai trouvé des informations sur le Web pour « {query_str} ».",
                    "query": query_str,
                    "count": len(results),
                    "results": results,
                    "preview": results[0]["snippet"][:150]
                }
    except Exception as e:
        return {
            "speech": "Désolé, la recherche Web a rencontré une difficulté technique.",
            "error": str(e),
            "results": []
        }

    return {
        "speech": f"Aucun résultat trouvé pour « {query_str} ».",
        "query": query_str,
        "results": []
    }

@tool_registry.register(
    name="fetch_webpage",
    description="Récupère et extrait le contenu textuel propre d'une page Web (article, documentation, fiche)",
    parameters={"url": "str (URL complète de la page web)", "max_chars": "int (nombre maximum de caractères à extraire, défaut: 3000)"}
)
def fetch_webpage(url: str, max_chars: int = 3000) -> Dict[str, Any]:
    target_url = str(url).strip()
    if not (target_url.startswith("http://") or target_url.startswith("https://")):
        target_url = f"https://{target_url}"

    # Vérification stricte anti-SSRF
    is_safe, error_msg = is_safe_public_url(target_url)
    if not is_safe:
        return {
            "speech": "Accès à cette page refusé pour des raisons de sécurité.",
            "error": f"Sécurité SSRF : {error_msg}",
            "content": ""
        }

    try:
        limit = max(500, min(10000, int(max_chars)))
        # Téléchargement limité en taille pour éviter les attaques DoS / memory exhaustion
        with requests.get(target_url, headers=HEADERS, timeout=7, stream=True) as resp:
            if resp.status_code != 200:
                return {
                    "speech": f"Impossible d'accéder à la page (statut {resp.status_code}).",
                    "error": f"HTTP {resp.status_code}",
                    "content": ""
                }

            # Lecture maximale de 500 Ko
            content_chunks = []
            total_bytes = 0
            for chunk in resp.iter_content(chunk_size=16384, decode_unicode=True):
                if chunk:
                    content_chunks.append(chunk)
                    total_bytes += len(chunk.encode('utf-8', errors='ignore'))
                    if total_bytes > 500_000:
                        break

            raw_html = "".join(content_chunks)

        # Nettoyage HTML
        clean = re.sub(r'<script[\s\S]*?</script>', '', raw_html, flags=re.I)
        clean = re.sub(r'<style[\s\S]*?</style>', '', clean, flags=re.I)
        clean = re.sub(r'<nav[\s\S]*?</nav>', '', clean, flags=re.I)
        clean = re.sub(r'<footer[\s\S]*?</footer>', '', clean, flags=re.I)
        clean = re.sub(r'<header[\s\S]*?</header>', '', clean, flags=re.I)
        clean = re.sub(r'<[^>]+>', ' ', clean)
        clean = unescape(clean)

        lines = [line.strip() for line in clean.splitlines() if line.strip()]
        text = "\n".join(lines)
        truncated = text[:limit]

        return {
            "speech": f"J'ai lu la page {urllib.parse.urlparse(target_url).netloc}.",
            "url": target_url,
            "length": len(truncated),
            "content": truncated
        }
    except requests.Timeout:
        return {
            "speech": "Le délai de chargement de la page a expiré.",
            "error": "Timeout",
            "content": ""
        }
    except Exception as e:
        return {
            "speech": f"Erreur lors de la lecture de la page : {str(e)[:80]}.",
            "error": str(e),
            "content": ""
        }
