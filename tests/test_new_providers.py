"""Tests nouveaux providers : xAI, Anthropic, OpenRouter, customs. Zero réseau réel."""
import os
import sys

for k in ["XAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY", "CUSTOM_ENDPOINTS_JSON"]:
    os.environ.pop(k, None)

sys.path.insert(0, "C:/Users/lemou/OneDrive/Desktop/ESpace work IA/Ei")

# 1. Refs dynamiques parsees
from core.models import parse_tier_ref
for ref, prov, mod in [("xai/grok-4", "xai", "grok-4"),
                       ("anthropic/claude-sonnet-4-5", "anthropic", "claude-sonnet-4-5"),
                       ("openrouter/openai/gpt-4o-mini", "openrouter", "openai/gpt-4o-mini")]:
    m = parse_tier_ref(ref)
    assert m and m["provider"] == prov and m["model"] == mod, (ref, m)
print("REFS_OK")

# 2. Sans cles -> None (aucun appel reseau)
from brain.llm import llm_cascade
for model in [{"provider": "xai", "model": "grok-4", "key_env": "XAI_API_KEY"},
              {"provider": "anthropic", "model": "claude-sonnet-4-5", "key_env": "ANTHROPIC_API_KEY"},
              {"provider": "openrouter", "model": "openai/gpt-4o-mini", "key_env": "OPENROUTER_API_KEY"}]:
    assert llm_cascade.ask_with_model("bonjour", model, "sys") is None
print("NOKEY_OK")

# 3. Endpoint resolver : builtins + custom via env JSON
os.environ["CUSTOM_ENDPOINTS_JSON"] = '{"monextra": {"base_url": "https://mon-serveur/v1", "key_env": "MONEXTRA_API_KEY"}}'
os.environ["MONEXTRA_API_KEY"] = "sk-test"
bu, ak = llm_cascade._openai_compat_endpoint("xai", {})
assert bu == "https://api.x.ai/v1" and ak == "", (bu, ak)
bu, ak = llm_cascade._openai_compat_endpoint("monextra", {})
assert bu == "https://mon-serveur/v1" and ak == "sk-test", (bu, ak)
bu, ak = llm_cascade._openai_compat_endpoint("inconnu", {})
assert bu == "" and ak == "", (bu, ak)
print("ENDPOINT_OK")
del os.environ["CUSTOM_ENDPOINTS_JSON"]
del os.environ["MONEXTRA_API_KEY"]

# 4. Anthropic : payload + parsing via mock (pas de reseau)
import brain.llm as llm_mod


class FakeResp:
    status_code = 200

    def json(self):
        return {"content": [{"type": "text", "text": "Bonjour !"}]}


captured = {}
orig_post = llm_mod.requests.post


def fake_post(url, headers=None, json=None, timeout=None):
    captured.update(url=url, headers=headers, body=json)
    return FakeResp()


llm_mod.requests.post = fake_post
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
try:
    out = llm_cascade._call_anthropic("salut", "sys-test", model="claude-sonnet-4-5")
finally:
    llm_mod.requests.post = orig_post
    del os.environ["ANTHROPIC_API_KEY"]
assert out == "Bonjour !", out
assert captured["url"] == "https://api.anthropic.com/v1/messages"
assert captured["headers"]["anthropic-version"] == "2023-06-01"
assert captured["headers"]["x-api-key"] == "sk-ant-test"
assert captured["body"]["model"] == "claude-sonnet-4-5"
assert captured["body"]["messages"][-1] == {"role": "user", "content": "salut"}
print("ANTHROPIC_MOCK_OK")

# 5. Listage + test sans cle -> echec propre, sans reseau
from brain.providers import list_provider_models
from brain.api_test import test_api_key
for prov in ["xai", "anthropic", "openrouter", "nimporte"]:
    r = list_provider_models(prov)
    assert r["ok"] is False and r["models"] == [], (prov, r)
    t = test_api_key(prov)
    assert t["ok"] is False, (prov, t)
print("LIST_TEST_OK")

# 6. Catalogue : nouvelles entrees presentes
from core.models import catalog_public_view
opts = catalog_public_view()
provs = {o.get("provider") for o in opts}
assert {"xai", "anthropic", "openrouter"} <= provs, provs
print("CATALOG_OK")

print("ALL_NEW_PROVIDERS_TESTS_PASSED")
