import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, List
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Charger les variables d'environnement (.env)
load_dotenv(BASE_DIR / ".env")

DEFAULT_CONFIG_PATH = BASE_DIR / "config.default.json"
CONFIG_PATH = BASE_DIR / "config.json"

from pydantic import BaseModel, Field, ConfigDict, ValidationError

class EiConfigSchema(BaseModel):
    """Schéma de validation Pydantic pour config.json."""
    model_config = ConfigDict(extra="allow")

    assistant_name: str = "EI"
    user_name: str = "Monsieur"
    user_city: str = "Lomé"
    wake_words: list[str] = Field(default_factory=lambda: ["eve"])
    voice: str = "fr-FR-HenriNeural"
    preferred_brain: str = "gemini"
    mic_device_index: Optional[int] = None
    mic_sensitivity_rms: float = 0.015
    silence_duration_sec: float = 1.2
    max_phrase_sec: float = 15.0
    sound_feedback: bool = True
    orb_theme: str = "cyber_blue"
    orb_animation: str = "plasma"
    auto_listen: bool = True
    model_choice_mode: str = "ask"
    models: Dict[str, Any] = Field(default_factory=dict)
    orb_quality: str = "high"
    orb_preset: str = "cyber_blue"

def deep_merge(target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
    """Fusionne récursivement source dans target sans écraser les sous-dictionnaires."""
    for key, value in source.items():
        if isinstance(value, dict) and key in target and isinstance(target[key], dict):
            deep_merge(target[key], value)
        else:
            target[key] = value
    return target

class ConfigManager:
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.load()

    def _validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Valide et nettoie les données via Pydantic."""
        try:
            validated = EiConfigSchema.model_validate(data)
            return validated.model_dump()
        except ValidationError as e:
            print(f"[Config] Avertissement validation Pydantic: {e}")
            return data

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
                    deep_merge(default_data, data)
            except Exception as e:
                print(f"[Config] Erreur lecture config.json: {e}")

        self.config = self._validate(default_data)
        return self.config

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any, save: bool = True):
        self.config[key] = value
        self.config = self._validate(self.config)
        if save:
            self.save()

    def update(self, new_data: Dict[str, Any], save: bool = True):
        deep_merge(self.config, new_data)
        self.config = self._validate(self.config)
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
        return os.getenv("GEMINI_API_KEY", "").strip().strip('"\'')

    @property
    def openai_api_key(self) -> str:
        return os.getenv("OPENAI_API_KEY", "").strip().strip('"\'')

    @property
    def groq_api_key(self) -> str:
        return os.getenv("GROQ_API_KEY", "").strip().strip('"\'')

    @property
    def mistral_api_key(self) -> str:
        return os.getenv("MISTRAL_API_KEY", "").strip().strip('"\'')

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
        clean = (value or "").strip().strip('"\'')
        if not clean:
            return ""
        if len(clean) <= 12:
            return clean[:2] + "…"
        return f"{clean[:6]}…{clean[-4:]}"

    def set_env_var(self, name: str, value: str):
        """Écrit (ou remplace) une variable dans .env et met à jour os.environ."""
        clean_value = (value or "").strip().strip('"\'')
        lines: list[str] = []
        if self.ENV_PATH.exists():
            try:
                lines = self.ENV_PATH.read_text(encoding="utf-8").splitlines()
            except Exception as e:
                print(f"[Config] Erreur lecture .env: {e}")

        replaced = False
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{name}="):
                lines[i] = f"{name}={clean_value}"
                replaced = True
                break
        if not replaced:
            lines.append(f"{name}={clean_value}")

        try:
            # Nettoyer les lignes vides consécutives
            cleaned_lines = []
            prev_blank = False
            for line in lines:
                is_blank = (len(line.strip()) == 0)
                if is_blank and prev_blank:
                    continue
                cleaned_lines.append(line)
                prev_blank = is_blank
            self.ENV_PATH.write_text("\n".join(cleaned_lines) + "\n", encoding="utf-8")
        except Exception as e:
            print(f"[Config] Erreur écriture .env: {e}")

        if clean_value:
            os.environ[name] = clean_value
        else:
            os.environ.pop(name, None)

    def get_api_keys_status(self) -> Dict[str, str]:
        """État masqué des clés (sûr à envoyer au HUD)."""
        return {v: self.mask_value(os.getenv(v, "")) for v in self.API_KEY_VARS}

config = ConfigManager()
