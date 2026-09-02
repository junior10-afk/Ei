# EI - Assistant Vocal Desktop & HUD 3D

Variante modulaire, moderne et épurée d'un assistant personnel Windows façon Iron Man (JARVIS), conçue à partir du guide d'architecture `GUIDE_REPRODUCTION_VARIANTE.md`.

---

## 🌟 Points Clés de l'Architecture

1. **Séparation Stricte Runtime / HUD :**
   - **Backend Python (`run.py`)** : Cerveau, micro VAD, STT (Google Speech), TTS (Edge-TTS), outils Windows, cascade LLM.
   - **HUD Three.js (`frontend/`)** : Orbe holographique 3D réactif, pupitre cyberpunk, console de bord, sous-titres en temps réel.
   - **Bus WebSocket unique (`ws://127.0.0.1:8765`)** : Synchronisation temps réel des états (`idle`, `listening`, `thinking`, `speaking`), volume audio et sous-titres.

2. **Cerveau en 3 Niveaux (Vitesse & Économie) :**
   - **Niveau 1 (0 latence, 0 coût)** : Réponses locales immédiates (salutations, heure, date, calculs arithmétiques, réveil).
   - **Niveau 2 (Outils Déterministes)** : Ouverture d'applications Windows, réglage du volume système, météo Open-Meteo temps réel, mémorisation de faits.
   - **Niveau 3 (Cascade LLM)** : Gemini 2.5, Groq, OpenAI, Mistral ou Ollama local avec injection dynamique de prompt, règles vocales strictes (sans markdown) et schéma JSON d'outils.

3. **Pipeline Vocal Intelligent :**
   - Détection VAD (RMS) avec élimination des bruits parasites (< 0.5s).
   - Anti-larsen automatique (coupure de l'écoute pendant la synthèse).
   - Détection de mots de silence immédiats ("tais-toi", "silence", "stop").
   - Wake words configurables (par défaut : *"EI"*, *"Jarvis"*, *"Assistant"*).

---

## 🚀 Démarrage Rapide

### Option 1 : Double-clic
Lancez simplement le fichier :
```
DEMARRER_EI.bat
```

### Option 2 : En ligne de commande
```bash
# Lancement direct du runtime et de l'interface
python run.py
```

L'application ouvrira la fenêtre HUD native (via WebView2) ou votre navigateur sur `http://127.0.0.1:5173`.

---

## 📁 Structure du Projet

```
Ei/
├── run.py                    # Point d'entrée unique
├── DEMARRER_EI.bat           # Lanceur Windows en 1 clic
├── config.json               # Préférences utilisateur (nom, ville, voix, wake words)
├── .env                      # Clés d'API (Gemini, Groq, OpenAI...)
├── requirements.txt          # Dépendances Python
│
├── core/                     # Cœur du système
│   ├── config.py             # Gestionnaire de configuration
│   ├── state.py              # Machine à états (idle, listening, thinking, speaking)
│   ├── protocol.py           # Schémas de messages Pydantic
│   └── bus.py                # Serveur WebSocket & diffusion thread-safe
│
├── voice/                    # Pipeline audio
│   ├── mic.py                # Capture SoundDevice + VAD + détection fin de phrase
│   ├── stt.py                # Reconnaissance vocale (SpeechRecognition)
│   ├── tts.py                # Synthèse vocale Edge-TTS + synchronisation volume orbe
│   └── wake.py               # Détection wake word & filtrage des mots d'arrêt
│
├── brain/                    # Intelligence & Décision
│   ├── local_replies.py      # Réponses locales ultra-rapides sans IA
│   ├── prompt.py             # Constructeur dynamique du system prompt
│   ├── llm.py                # Cascade multi-fournisseurs (Gemini, Groq, OpenAI, Ollama)
│   └── dispatcher.py         # Aiguillage : Stop -> Wake -> Local -> Outils -> LLM
│
├── tools/                    # Registre d'outils modulaires
│   ├── registry.py           # Système d'enregistrement par décorateur
│   ├── apps.py               # Lancement d'applications Windows & contrôle du volume
│   ├── weather.py            # Météo temps réel Open-Meteo
│   ├── files.py              # Explorateur de fichiers Windows
│   ├── memory.py             # Mémorisation & rappel de souvenirs persistants
│   └── home_assistant.py     # Contrôle domotique optionnel
│
├── ui_host/                  # Hébergement du HUD
│   ├── window.py             # Fenêtre native PyWebView (WebView2)
│   └── launcher.py           # Serveur Web statique local
│
└── frontend/                 # Interface graphique HUD 3D
    ├── package.json          # Vite + Three.js + TypeScript
    ├── index.html            # Pupitre HUD cyberpunk
    └── src/
        ├── main.ts           # Client WebSocket & gestionnaire d'événements
        ├── orb.ts            # Orbe Three.js réactif aux états & volume sonore
        ├── style.css         # Styling cyberpunk / Iron Man dark
        └── panels/           # Composants UI (Chat, Réglages, Actions)
```

---

## 🎯 Commandes Vocales & Clavier Disponibles Immédiatement

- **Wake Words :** *"EI"*, *"Jarvis"*, *"Assistant"*
- **Salutations & Identité :** *"Bonjour"*, *"Qui es-tu ?"*, *"Merci"*
- **Heure & Date :** *"Quelle heure est-il ?"*, *"Quel jour on est ?"*
- **Calculs :** *"Calcule 15 * 8"*, *"Combien font 124 plus 36 ?"*
- **Applications :** *"Ouvre Chrome"*, *"Ouvre le bloc-notes"*, *"Ouvre la calculatrice"*, *"Lance YouTube"*
- **Volume :** *"Mets le volume à 50"*, *"Règle le volume à 80"*
- **Météo :** *"Quel temps fait-il ?"*, *"Météo à Paris"*
- **Dossiers :** *"Ouvre le dossier Bureau"*, *"Ouvre les téléchargements"*
- **Mémoire :** *"Mémorise que mon code d'entrée est 4242"*, *"Quel est mon code d'entrée ?"*
- **Arrêt immédiat :** *"Silence"*, *"Stop"*, *"Tais-toi"*
