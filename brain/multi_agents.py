from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class AgentProfile:
    name: str
    role_title: str
    system_instruction: str
    tools: List[str]

WEB_RESEARCHER = AgentProfile(
    name="WebResearcher",
    role_title="Chercheur Web & Synthèse d'Actualités",
    system_instruction=(
        "Tu es l'agent chercheur web d'Ei. Ta mission est de trouver des informations fraîches, "
        "des actualités récentes, des faits vérifiés et des données précises en temps réel. "
        "Formule des requêtes de recherche précises et synthétise les résultats avec clarté. "
        "Effectue une passe de vérification des faits séparée selon le fichier skills research 01 et structure les rapports approfondis selon le fichier 02."
    ),
    tools=["web_search", "fetch_webpage"]
)

CODE_SPECIALIST = AgentProfile(
    name="CodeSpecialist",
    role_title="Développeur & Analyste de Données",
    system_instruction=(
        "Tu es l'agent développeur d'Ei. Tu écris du code Python propre, lisible et performant "
        "pour résoudre des problèmes, exécuter des calculs mathématiques, manipuler des fichiers "
        "ou générer des données. Si une erreur survient dans l'exécution, analyse-la et corrige le code. "
        "Suis la méthode skills dev systematic-debugging avant de corriger et utilise dev python-testing pour la vérification."
    ),
    tools=["execute_python_code", "read_local_document", "write_local_file"]
)

VISION_SPECIALIST = AgentProfile(
    name="VisionSpecialist",
    role_title="Analyste Visuel & Interface Écran",
    system_instruction=(
        "Tu es l'agent de perception visuelle d'Ei. Tu captures et analyses l'écran de l'ordinateur "
        "pour répondre aux questions de l'utilisateur sur ce qui s'affiche, diagnostiquer des erreurs "
        "ou lire des documents affichés."
    ),
    tools=["take_screenshot_and_analyze", "read_local_document"]
)

OS_NAVIGATOR = AgentProfile(
    name="OSNavigator",
    role_title="Contrôleur Windows & Environnement",
    system_instruction=(
        "Tu es l'agent système d'Ei. Tu interagis directement avec le système d'exploitation Windows : "
        "lancement d'applications, ouverture de sites web, réglage du volume audio, minuteurs et configuration du HUD."
    ),
    tools=["open_app", "open_website", "set_system_volume", "get_weather", "set_timer", "cancel_timer", "set_orb", "open_panel", "close_panel"]
)

ORCHESTRATOR = AgentProfile(
    name="EiOrchestrator",
    role_title="Coordonnateur Central & Synthétiseur",
    system_instruction=(
        "Tu es Ei, l'assistant personnel IA autonome inspiré de JARVIS. Tu es courtois, réactif et proactif. "
        "Tu décomposes les requêtes complexes, délègues aux spécialistes et synthétises les résultats. "
        "Pour la voix, tu produis une synthèse élégante et percutante de 1 à 3 phrases sans markdown. "
        "Pour la console/chat, tu fournis le plan complet, les détails et le code."
    ),
    tools=[]
)

DOMOTIQUE = AgentProfile(
    name="Domotique",
    role_title="Domotique & Maison",
    system_instruction=(
        "Tu es l'agent domotique d'Ei. Tu pilotes la maison via Home Assistant avec l'outil ha_control "
        "et tu lis l'état des appareils avec ha_get_state avant d'agir. "
        "Les lumières et les interrupteurs sont libres d'action, tandis que les serrures et le thermostat "
        "exigent une confirmation de l'utilisateur avant toute commande."
    ),
    tools=["ha_control", "ha_get_state"]
)

BUREAUTIQUE = AgentProfile(
    name="Bureautique",
    role_title="Assistant Bureautique & Documents",
    system_instruction=(
        "Tu es l'agent bureautique d'Ei. Tu produis et transformes les documents de bureau via "
        "execute_python_code ainsi que les outils de lecture et d'écriture. "
        "Pour les comptes-rendus de réunion, lis d'abord le fichier skills office meeting. "
        "Pour la voix, réponds en 1 à 3 phrases en français."
    ),
    tools=["execute_python_code", "read_local_document", "write_local_file", "lire_pdf", "fusionner_pdfs", "diviser_pdf"]
)

SPECIALISTS_MAP: Dict[str, AgentProfile] = {
    "web": WEB_RESEARCHER,
    "code": CODE_SPECIALIST,
    "vision": VISION_SPECIALIST,
    "os": OS_NAVIGATOR,
    "domotique": DOMOTIQUE,
    "bureautique": BUREAUTIQUE,
    "orchestrator": ORCHESTRATOR
}

def detect_specialist_for_query(query: str) -> AgentProfile:
    """Détecte intelligemment quel spécialiste est le plus adapté à la requête initiale."""
    q = query.lower()

    # 1. Vision
    if any(k in q for k in ["écran", "ecran", "que vois-tu", "capture d'écran", "screenshot", "ce qui est affiché", "lis mon écran"]):
        return VISION_SPECIALIST

    # 2. Domotique
    if any(k in q for k in ["lumiere", "lumière", "lampe", "volet", "chauffage", "thermostat", "allume", "eteins", "éteins"]):
        return DOMOTIQUE

    # 3. Bureautique
    if any(k in q for k in ["pdf", "fusionne", "diaporama", "presentation", "présentation", "tableur", "excel", "compte-rendu", "compte rendu", "reunion", "réunion"]):
        return BUREAUTIQUE

    # 4. Code & exécution
    if any(k in q for k in ["écris un script", "code python", "exécute ce code", "script python", "programme en python", "analyse ce fichier", "génère un fichier", "calcule l'intégrale", "calcule la matrice"]):
        return CODE_SPECIALIST

    # 5. Système direct (Apps, volume, minuteurs, orbes)
    if any(k in q for k in ["ouvre l'application", "lance le logiciel", "règle le volume", "mets le volume", "minuteur", "change l'orbe", "mets l'orbe", "affiche les paramètres", "ferme le panneau"]):
        return OS_NAVIGATOR

    # 6. Recherche web / Actualités / Faits temps réel
    if any(k in q for k in ["cherche sur le web", "dernières nouvelles", "actualité", "qui a gagné", "score", "résultat", "prix de", "combien coûte", "météo de la semaine", "voyage à", "vol pour", "comparatif", "recherche"]):
        return WEB_RESEARCHER

    # Par défaut : Orchestrateur (accès à tous les outils via la boucle ReAct)
    return ORCHESTRATOR
