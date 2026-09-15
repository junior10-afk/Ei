import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"
LOG_FILE = LOGS_DIR / "ei.log"

def log_exception(context: str, exc: BaseException) -> None:
    """Journalise une exception interceptée (remplace les 'except Exception: pass' silencieux)."""
    logging.getLogger("ei").error("%s: %s\n%s", context, exc, traceback.format_exc())


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure la journalisation centralisée avec fichier tournant et console."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    level = logging.DEBUG if verbose else logging.INFO

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler Fichier Tournant (5 Mo x 3 fichiers)
    file_handler = RotatingFileHandler(
        filename=str(LOG_FILE),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Handler Console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # Logger racine
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Éviter les doublons de handlers si setup_logging est appelé plusieurs fois
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Réduire le bruit des bibliothèques tierces
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.INFO)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    ei_logger = logging.getLogger("ei")
    ei_logger.info(f"Logging initialisé. Fichier: {LOG_FILE} (Verbose={verbose})")
    return ei_logger

logger = logging.getLogger("ei")
