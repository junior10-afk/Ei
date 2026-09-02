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

config = ConfigManager()
