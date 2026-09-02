import re
from typing import Tuple, List, Optional
from core.config import config

STOP_WORDS = ["stop", "tais-toi", "silence", "ferme-la", "chut", "arrête", "annule"]

def contains_stop_word(text: str) -> bool:
    """Vérifie si la phrase contient un ordre de silence direct."""
    cleaned = text.lower().strip()
    for sw in STOP_WORDS:
        if re.search(rf"\b{re.escape(sw)}\b", cleaned):
            return True
    return False

def check_wake_word(text: str, custom_wake_words: Optional[List[str]] = None) -> Tuple[bool, bool, str]:
    """
    Vérifie si le texte contient le wake word.
    Retourne:
      (has_wake_word, is_wake_word_only, clean_query)
    """
    wake_words = custom_wake_words or config.get("wake_words", ["ei", "jarvis", "assistant"])
    if not isinstance(wake_words, list):
        wake_words = [str(wake_words)]

    cleaned = text.strip()
    lower_text = cleaned.lower()

    for word in wake_words:
        pattern = rf"\b{re.escape(word.lower())}\b"
        match = re.search(pattern, lower_text)
        if match:
            # Retirer le wake word du texte
            remaining = re.sub(pattern, "", cleaned, count=1, flags=re.IGNORECASE).strip()
            # Nettoyer ponctuation résiduelle (virgules, tirets en début de phrase)
            remaining = re.sub(r"^[\s,;:!?.-]+", "", remaining).strip()
            is_only = (len(remaining) == 0)
            return True, is_only, remaining

    return False, False, cleaned
