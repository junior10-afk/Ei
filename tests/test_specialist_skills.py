"""Vérifie le routage des spécialistes (domotique, bureautique + branches existantes)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from brain.multi_agents import detect_specialist_for_query


def test_domotique_query():
    assert detect_specialist_for_query("Allume la lumière du salon").name == "Domotique"


def test_bureautique_pdf_query():
    assert detect_specialist_for_query("Fusionne ce PDF en un seul fichier").name == "Bureautique"


def test_vision_branch_still_works():
    assert detect_specialist_for_query("Fais une capture d'écran s'il te plaît").name == "VisionSpecialist"


def test_code_branch_still_works():
    assert detect_specialist_for_query("Écris un script Python pour trier mes fichiers").name == "CodeSpecialist"


def test_web_branch_still_works():
    assert detect_specialist_for_query("Cherche sur le web les dernières nouvelles spatiales").name == "WebResearcher"
