import re
import random
import datetime
from typing import Optional
from core.config import config

GREETINGS = [
    "Bonjour {}, comment puis-je vous aider ?",
    "Bonjour {}, je suis à votre écoute.",
    "Salutations {}, que puis-je faire pour vous ?"
]

WAKE_CONFIRMATIONS = [
    "Oui {}, je vous écoute.",
    "À vos ordres.",
    "Je suis là.",
    "Oui ?"
]

THANKS_REPLIES = [
    "Avec plaisir.",
    "À votre service {}.",
    "Toujours un honneur.",
    "Je vous en prie."
]

def check_local_reply(text: str) -> Optional[str]:
    """
    Vérifie si le texte correspond à une intention locale immédiate (0 latence, 0 coût).
    Retourne la réponse parlée ou None.
    """
    clean = text.lower().strip()
    user_name = config.get("user_name", "Monsieur")
    assistant_name = config.get("assistant_name", "EI")

    # 1. Salutations simples
    if re.fullmatch(r"(bonjour|salut|coucou|bonsoir|hey|hello)[\s!.]*", clean):
        template = random.choice(GREETINGS)
        return template.format(user_name)

    # 2. Remerciements : UNIQUEMENT si la phrase est un pur remerciement.
    # (Sinon "merci de m'expliquer X" serait capturé et X ne serait jamais répondu.)
    if re.fullmatch(r"(merci( beaucoup)?( infiniment)?|je (te|vous) (re|s)mercie( encore)?|thanks)[\s!.]*", clean):
        template = random.choice(THANKS_REPLIES)
        return template.format(user_name)

    # 3. Heure actuelle (utilitaire déterministe immédiat)
    if re.search(r"\b(quelle heure est-il|l'heure qu'il est|donne-moi l'heure|il est quelle heure)\b", clean):
        now = datetime.datetime.now()
        minute = now.minute
        minute_str = "pile" if minute == 0 else f"{minute}"
        return f"Il est {now.hour} heure{'s' if now.hour > 1 else ''} {minute_str}."

    # 5. Date du jour
    if re.search(r"\b(quel jour on est|quelle est la date|on est quel jour|date d'aujourd'hui)\b", clean):
        jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        now = datetime.datetime.now()
        jour_semaine = jours[now.weekday()]
        nom_mois = mois[now.month - 1]
        return f"Nous sommes le {jour_semaine} {now.day} {nom_mois} {now.year}."

    # 6. Calculs arithmétiques basiques (ex: calcule 25 * 4, combien font 12 + 15)
    math_match = re.search(r"(?:calcule|combien font|combien fait)\s+([0-9\s\+\-\*\/\(\)\.,]+)", clean)
    if math_match:
        expr = math_match.group(1).replace(",", ".")
        # Filtrer uniquement les caractères mathématiques sûrs
        if re.fullmatch(r"[0-9\s\+\-\*\/\(\)\.]+", expr):
            try:
                # Évaluation arithmétique sécurisée
                result = eval(expr, {"__builtins__": None}, {})
                if isinstance(result, float) and result.is_integer():
                    result = int(result)
                return f"Le résultat est {result}."
            except Exception:
                pass

    return None

def get_wake_ack() -> str:
    """Retourne un accusé de réception vocal court au réveil."""
    user_name = config.get("user_name", "Monsieur")
    template = random.choice(WAKE_CONFIRMATIONS)
    return template.format(user_name)
