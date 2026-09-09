import json
import os
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Charger les variables d'environnement (.env)
load_dotenv(BASE_DIR / ".env")

DEFAULT_CONFIG_PATH = BASE_DIR / "config.default.json"
CONFIG_PATH = BASE_DIR / "config.json"

class ConfigManager:
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        """Charge config.json avec fallback sur config.default.json."""
        default_data = {}
        if DEFAULT_CONFIG_PATH.exists():
            try:
                with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
                    default_data = json.load(f)
            except Exception as e:
                print(f"[Config] Erreur lecture default_config: {e}")

        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    default_data.update(data)
            except Exception as e:
                print(f"[Config] Erreur lecture config.json: {e}")

        self.config = default_data
        return self.config

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any, save: bool = True):
        self.config[key] = value
        if save:
            self.save()

    def update(self, new_data: Dict[str, Any], save: bool = True):
        self.config.update(new_data)
        if save:
            self.save()

    def save(self):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print("[Config] Configuration sauvegardée.")
        except Exception as e:
            print(f"[Config] Erreur sauvegarde config.json: {e}")

    @property
    def gemini_api_key(self) -> str:
        return os.getenv("GEMINI_API_KEY", "")

    @property
    def openai_api_key(self) -> str:
        return os.getenv("OPENAI_API_KEY", "")

    @property
    def groq_api_key(self) -> str:
        return os.getenv("GROQ_API_KEY", "")

    @property
    def mistral_api_key(self) -> str:
        return os.getenv("MISTRAL_API_KEY", "")

    @property
    def ws_port(self) -> int:
        return int(os.getenv("WS_PORT", "8765"))

    @property
    def host(self) -> str:
        return os.getenv("HOST", "127.0.0.1")

    # --- Gestion des clés API dans le fichier .env --------------------------

    ENV_PATH = BASE_DIR / ".env"
    API_KEY_VARS = ["GEMINI_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY", "MISTRAL_API_KEY"]

    @staticmethod
    def mask_value(value: str) -> str:
        """Masque une clé : 6 premiers + 4 derniers caractères."""
        if not value:
            return ""
        if len(value) <= 12:
            return value[:2] + "…"
        return f"{value[:6]}…{value[-4:]}"

    def set_env_var(self, name: str, value: str):
        """Écrit (ou remplace) une variable dans .env et met à jour os.environ."""
        lines: list[str] = []
        if self.ENV_PATH.exists():
            try:
                lines = self.ENV_PATH.read_text(encoding="utf-8").splitlines()
            except Exception as e:
                print(f"[Config] Erreur lecture .env: {e}")

        replaced = False
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{name}="):
                lines[i] = f"{name}={value}"
                replaced = True
                break
        if not replaced:
            lines.append(f"{name}={value}")

        try:
            nl = chr(13) + chr(10)
            self.ENV_PATH.write_text(nl.join(lines) + nl, encoding="utf-8")
        except Exception as e:
            print(f"[Config] Erreur écriture .env: {e}")

        if value:
            os.environ[name] = value
        else:
            os.environ.pop(name, None)

    def get_api_keys_status(self) -> Dict[str, str]:
        """État masqué des clés (sûr à envoyer au HUD)."""
        return {v: self.mask_value(os.getenv(v, "")) for v in self.API_KEY_VARS}

config = ConfigManager()
