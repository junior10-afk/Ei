# Reproduire une variante de JARVIS

Guide de conception pour **refaire le même type de produit** (assistant vocal desktop + HUD 3D + actions locales), sans cloner le monolithe actuel.

Le dépôt de référence est un assistant personnel Windows façon Iron Man : voix in / voix out, orbe Three.js, commandes JSON vers le PC et la maison. Le fichier `ARCHITECTURE_JARVIS_DETAILLEE.md` décrit **cette** implémentation (milliers de lignes dans `main2.py` et `frontend/src/main.ts`). Ce document décrit **le modèle** à réimplémenter proprement.

---

## 1. Ce que c’est vraiment

Ce n’est pas un chatbot web. C’est un **runtime local** qui :

1. Écoute le micro (wake word + session).
2. Transcrit (STT cloud ou local).
3. Décide : raccourci local, outil, ou LLM.
4. Exécute une **action structurée** (JSON) ou parle un texte.
5. Diffuse l’état à une UI HUD (orbe, panneaux, sous-titres).
6. Synthétise la voix (TTS) en parallèle de l’animation.

Le HUD n’est pas le cerveau. Le cerveau est le backend Python. Le frontend est un **visualiseur + télécommande** branché en WebSocket.

```
┌─────────────┐     ws://:8765      ┌──────────────────┐
│ HUD Vite    │ ◄─────────────────► │ Runtime Python   │
│ Three.js    │   JSON messages      │ STT / LLM / TTS  │
│ panneaux    │                      │ outils / HA / OS │
└─────────────┘                      └────────┬─────────┘
                                              │
                               ┌──────────────┼──────────────┐
                               ▼              ▼              ▼
                          APIs LLM      Home Assistant    Windows
                          Google STT    Spotify/Deezer    fichiers
                          Edge-TTS      Ollama optionnel  pywebview
```

Ports de référence : **5173** (Vite / dist), **8765** (WebSocket), **8000** (PWA mobile). Fenêtre : **pywebview** (WebView2) autour de `http://localhost:5173`.

---

## 2. Ce qu’il faut copier vs ce qu’il ne faut pas

### Copier (le type)

| Idée | Pourquoi |
|---|---|
| Séparation **runtime vocal** / **HUD** | L’UI peut crasher ; la voix continue. Le mobile se branche au même bus. |
| **Un seul bus WebSocket** | Tous les clients (desktop, téléphone) reçoivent `set_state`, sous-titres, panneaux. |
| États orbe : `idle` → `listening` → `thinking` → `speaking` (+ `searching`) | Le « feeling » JARVIS tient à ça, plus qu’aux 8000 lignes CSS. |
| LLM qui répond **texte OU JSON d’action** | C’est le vrai agent, pas un chat. |
| **Cascade multi-LLM + quotas** | Un fournisseur tombe, le suivant prend. |
| Réponses **locales** avant l’API | Salutations, maths, wake word seul = 0 latence, 0 coût. |
| Prompt système **injecté dynamiquement** | Pièces HA, ville, mémoire, règles vocales (phrases courtes, pas de markdown). |
| TTS **pipeliné par phrases** | Générer la phrase N+1 pendant que N joue. |
| Config utilisateur JSON + secrets `.env` | Personnalisation vs clés. |
| Plugins métier dans des **fichiers à part** | `ha_config.py`, `memory_manager.py`, `app_launcher.py` — pas tout dans le handler. |

### Ne pas copier (dette de cette version)

- Un seul fichier `main2.py` (~9500 lignes) + `main.ts` (~6300) + `index.html` (~2100) + `style.css` (~7200).
- Un `if/elif` géant sur `data["type"]` (50+ messages).
- État global Python partagé entre threads vocaux, asyncio et GUI, collé avec `run_coroutine_threadsafe`.
- Frontend **sans framework** : 200 `getElementById` au boot.
- Fonctionnalités « OS complet » (antivirus live, VPN, désinstalleur, JARVIS OS Docker, IPTV, génération de sites, rap IA) **dans le MVP**. Ce sont des modules optionnels.

Une variante saine = **même produit perçu**, architecture **modulaire**.

---

## 3. Cible produit (MVP vs deluxe)

### MVP (la variante minimale qui « fait JARVIS »)

- Fenêtre desktop sombre + orbe 3D réactif au volume.
- Micro : wake word, mute, états visuels.
- Un LLM (Gemini ou Groq) + fallback texte d’erreur.
- TTS gratuit (Edge-TTS) + lecture pygame / équivalent.
- 8–15 actions JSON : parler, ouvrir une app, volume, météo, timer HUD, mémoriser une info.
- Saisie clavier qui emprunte le même pipeline que la voix.
- Fichier `config.json` (nom, ville, wake word, voix).

### Phase 2 (ce que ce dépôt a déjà)

- Cascade Gemini / Claude / Groq / Grok / OpenAI / Mistral / Ollama.
- Home Assistant (lumières, prises, scènes) via mapping vocal → `entity_id`.
- Vision (capture écran / caméra → modèle vision).
- Mémoire persistante + historique conversation.
- PWA mobile sur le LAN.
- Panneaux HUD (settings, liste, dashboard HA).

### Phase 3 (optionnel, très coûteux)

- ASR local GPU (Nemotron).
- Musique générée, sites générés, IPTV, VPN, antivirus, sous-OS Docker, tracking mains MediaPipe.

Pour une **variante**, arrête-toi volontairement à MVP ou phase 2.

---

## 4. Arborescence recommandée (à créer from scratch)

```
assistant/
  pyproject.toml / requirements.txt
  .env.example
  config.default.json
  run.py                      # point d’entrée court
  core/
    config.py
    bus.py                    # WebSocket + broadcast thread-safe
    state.py                  # idle/listening/thinking/speaking
    protocol.py               # schémas Pydantic des messages
  voice/
    mic.py                    # capture + filtres RMS / durée
    stt.py                    # Google / Whisper / Nemotron
    tts.py                    # Edge + option Gemini
    wake.py
  brain/
    prompt.py
    local_replies.py
    llm.py                    # cascade + quotas
    dispatcher.py             # texte vs JSON action
  tools/
    registry.py               # nom d’action → handler
    files.py
    apps.py
    weather.py
    home_assistant.py         # optionnel
  ui_host/
    window.py                 # pywebview
    launcher.py               # démarre Vite ou sert dist/
  frontend/
    package.json              # vite + three
    src/
      main.ts                 # WS client + applyState
      orb.ts
      protocol.ts
      panels/                 # un module par panneau
      style.css
  mobile/                     # plus tard : même WS
```

Règle : **ajouter une compétence** = un handler dans `tools/` + une entrée dans le prompt + éventuellement un panneau. Jamais un nouveau `elif` de 80 lignes au milieu du serveur.

---

## 5. Protocole WebSocket (le contrat)

Tout message : JSON `{ "type": "...", ... }`.

### Runtime → HUD (minimum)

| `type` | Rôle |
|---|---|
| `set_state` | `{ state: "idle"\|"listening"\|"thinking"\|"speaking" }` — pilote l’orbe |
| `volume` | `{ value: 0..1 }` — amplitude TTS pour pulser l’orbe |
| `user_speech` | transcription affichée |
| `subtitle` | texte parlé (sous-titres) |
| `mic_state` | muted / actif |
| `error` | toast |
| `action` | ouvrir un panneau, timer, météo, image, etc. |

### HUD → Runtime (minimum)

| `type` | Rôle |
|---|---|
| `user_input` | texte clavier = même pipeline que la voix |
| `toggle_mic` | mute |
| `stop_audio` | coupe le TTS (`STOP_PARLER`) |
| `get_settings` / `update_settings` | config |
| `screen_frame` | réponse à une demande de capture (phase 2) |

Dans ce dépôt, il y a ~54 types montants et ~58 descendants. Pour une variante, commence à **~12**. Factorise ensuite par domaine (`ha.*`, `av.*`) plutôt que d’aplatir.

Broadcast : une boucle asyncio unique ; les threads vocaux poussent via `asyncio.run_coroutine_threadsafe(loop, coro)`. Tous les clients (desktop + mobile) sont dans un `set`.

---

## 6. Pipeline vocal (à reproduire tel quel)

```
micro
  → ignore si TTS en cours (anti-larsen) ou mute
  → listen(timeout court, phrase_time_limit ~15s)
  → jeter si durée < 0,5 s ou énergie RMS trop faible
  → STT
  → « tais-toi » pendant la parole → stop TTS
  → mots de fin de session → idle
  → wake word en mot entier (\bjarvis\b), pas une sous-chaîne
  → retirer le wake word
  → raccourcis PC (regex) OU dispatcher IA
  → à chaque étape : set_state sur le bus
```

Wake word seul → réponse courte locale (« Oui, je vous écoute »), sans LLM.

TTS :

1. Remplacer le nom utilisateur.
2. Couper en phrases, regrouper jusqu’à ~180 caractères.
3. `speaking` + pré-génération de la phrase suivante.
4. Edge-TTS par défaut ; Gemini TTS si quota OK.
5. Envoyer le volume (ou analyser le PCM) vers l’orbe.

STT de départ : `SpeechRecognition` + `recognize_google(fr-FR)`. ASR local = option GPU, pas un prérequis.

---

## 7. Cerveau : locale → outils → cascade LLM

Ordre qui rend le produit **rapide** :

1. **`reponse_locale`** — salut, heure, maths, conversions.
2. **Outils déterministes** — « ouvre Chrome », « mets pause », chemins fichiers.
3. **`demander_ia`** — prompt système + mémoire + historique court.
4. Parser : texte libre → TTS ; JSON → exécuter l’outil puis confirmer à voix haute.
5. Si tous les LLM échouent : fallback métier (météo Open-Meteo, etc.).

Prompt vocal (règles d’or de cette app) :

- Identité courte, tutoiement / vouvoiement choisi.
- Réponses **très courtes**, zéro markdown (lu à voix haute).
- Nombres arrondis (« 20 degrés », pas « 20.4 »).
- Connaissance interne d’abord ; web seulement si demandé ou temps réel.
- Schéma JSON **strict** pour chaque outil (ex. `{ "action": "ha_lumiere", "piece": "salon", "etat": "on" }`).
- Injecter la liste réelle des pièces / apps / souvenirs.

Cascade (idée, pas les 6 fournisseurs dès le jour 1) :

```
preferred_brain = auto | gemini | grok | ...
auto + question code → Grok d’abord
sinon ordre configuré
chaque appel : timeout ~12s + cooldown si quota
```

Quota manager : marquer un provider `unavailable_until`, persister le quota TTS journalier dans un JSON.

Mémoire : dict `{ clé: { valeur, timestamp } }` dans un fichier, injecté dans le prompt. Historique : N derniers tours sur disque (ici 200 stockés, ~30 rechargés).

---

## 8. HUD : recette visuelle

Stack minimale : **Vite 6 + TypeScript + Three.js**. Pas de React obligatoire. pywebview charge l’URL locale.

### Orbe

- Canvas plein écran, fond transparent, blending additif.
- Nuage de particules (ce projet : 2000 points, lignes entre voisins, « électrons »).
- Shader / paramètres **lerpés** vers une cible par état (idle calme, thinking dense, speaking vortex + respiration).
- `setVolume` branché sur le TTS.
- Thèmes (bleu, iron_man, nvidia…) = palettes, pas un nouvel orbe.

Inspiration d’origine notée dans `orb.ts` : visualiseur type [ethanplusai/jarvis](https://github.com/ethanplusai/jarvis), largement étendu.

### Chrome HUD

- Fond `#050508`, accent cyan `#00e5ff`, scanlines, coins lumineux.
- Un **pattern de panneau** réutilisable : header draggable, body, footer versionné, classe `.hidden`.
- Orbe en `pointer-events: none` ; les boutons (micro, settings) au-dessus.
- Boot sequence : attendre le WS avant l’intro.

### Pour ajouter un panneau (dans une variante propre)

1. Composant TS isolé.
2. CSS scoped ou fichier du panneau.
3. Handler `protocol` du message.
4. Pas de 400 lignes de HTML statique dans `index.html`.

Mobile : même WS, `mobile_command` au lieu de `user_input`, orbe allégé. Servir un dossier statique sur `:8000`.

---

## 9. Outils (plugins) — catalogue de ce dépôt

Utile pour choisir **quoi porter** dans ta variante.

| Module | Rôle | MVP ? |
|---|---|---|
| `memory_manager.py` | souvenirs + journal conversations | oui |
| `app_launcher.py` | ouvrir apps Windows (registre / PATH) | oui |
| `file_manager.py` | dossiers, tri, recherche | phase 2 |
| `ha_config.py` | mapping vocal → entités HA + météo | phase 2 si tu as HA |
| `google_services.py` | Gmail, Calendar, Docs (OAuth `credentials.json`) | optionnel |
| `spotify_controller.py` / `deezer_controller.py` | lecture musique | optionnel |
| `youtube_api.py` | YouTube | optionnel |
| `vision_module.py` | analyse image | phase 2 |
| `obsidian_helper.py` | notes vault | optionnel |
| `project_builder.py` / sites dans `sites_internet/` | générer un site | non MVP |
| `jarvis_music.py` / `jarvis_rap.py` | composition | non MVP |
| `iptv_player.py` | TV / ffmpeg | non MVP |
| `antivirus_scanner.py` / `vpn.py` / `uninstaller_helper.py` | « OS » | non MVP |
| `nemotron_asr.py` | STT local NVIDIA | non MVP |
| `local_agent_manager.py` | Ollama | nice-to-have |
| `agent_model_manager.py` | choix de modèles par agent | phase 2 |
| `secure_browser.py` | navigateur docké | non MVP |
| `developer_gui.py` | outils dev CustomTkinter | hors produit |

Domotique : **ne pas** durcir les `entity_id` dans le dispatcher. Un fichier de mapping (`ha_config.py`) est le bon pattern.

---

## 10. Secrets et config

**`.env`** (jamais commit) — clés vues dans ce projet :

```
GEMINI_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GROQ_API_KEY=
XAI_API_KEY=
MISTRAL_API_KEY=
YOUTUBE_API_KEY=
SERPAPI_API_KEY=
HA_URL=
HA_TOKEN=
SPOTIFY_MUSIQUE_URI=
YOUTUBE_MUSIQUE_URL=
JARVIS_OLLAMA_BASE_URL=http://localhost:11434/v1
JARVIS_OLLAMA_MODEL=ornith:9b
```

**`config.json`** (utilisateur) : `user_name`, `user_city`, `wake_word`, `voice`, `preferred_brain`, `mic_device_index`, `mic_sensitivity`, `custom_apps[]`, `orb_style`, `obsidian_vault_path`, flags HA / antivirus.

Google Workspace : OAuth desktop → `credentials.json` à côté du runtime (voir `credentials_LISEZ_MOI.txt`). Sans fichier, le cœur vocal doit quand même démarrer.

Dépendances Python de base : `websockets`, `python-dotenv`, `SpeechRecognition`, `PyAudio`, `edge-tts`, `pygame`, `google-genai` (ou un seul SDK LLM), `pywebview`, `psutil`, `numpy`, `pywin32` (Windows). Frontend : `three`, `vite`, `typescript`.

Lancement type : venv + `python run.py` qui (1) libère les ports, (2) lance Vite ou sert `frontend/dist`, (3) démarre le WS, (4) ouvre pywebview, fallback navigateur `--app=`.

---

## 11. Plan de reproduction (ordre d’implémentation)

Faire dans cet ordre. Chaque palier est **démoable**.

### Semaine 1 — Bus + HUD mort

- Serveur WS echo + `set_state` manuel.
- Canvas orbe : 3 états, lerp.
- pywebview sur Vite.
- Bouton mute qui envoie `toggle_mic`.

### Semaine 2 — Voix

- Boucle micro + Google STT + wake word.
- Edge-TTS + `volume` → orbe `speaking`.
- Clavier → `user_input`.

### Semaine 3 — Agent

- Un LLM, prompt court, réponses parlées.
- 5 outils JSON (ouvrir app, timer, météo, mémoire, volume).
- Réponses locales (salut / heure).

### Semaine 4 — Produit

- Settings (nom, micro, voix) persistés.
- Cascade 2e fournisseur + timeout.
- Historique + mémoire fichier.
- Packaging : `install.bat` / venv / un `.bat` de lancement.

### Ensuite seulement

Home Assistant, vision, mobile, Google APIs, thèmes orbe, panneaux métier.

---

## 12. Idées de variantes (même architecture, autre skin)

| Variante | Ce que tu changes | Ce que tu gardes |
|---|---|---|
| **FRIDAY / assistant bureau** | Identité, voix, thème gris | Pipeline + 10 outils PC |
| **Poste domotique mural** | Pas d’apps Windows ; dashboard HA plein écran | WS + états + TTS |
| **Copilote code** | Ollama obligatoire, panneau diff, pas de wake word | Bus + orbe thinking |
| **Kiosque magasin** | Pas de micro always-on ; bouton poussoir | HUD + un LLM |
| **Linux / Mac** | Remplacer pywin32, winget, registre | Protocole + frontend |
| **Multilingue** | STT locale + voix Edge par langue | Dispatcher |

Ne reproduis pas le lore « Theron / JARVIS » : wake word, nom user et prompt d’identité sont des **paramètres**.

---

## 13. Pièges observés sur ce code

1. **Larsen** : couper l’écoute pendant le TTS, ou utiliser un casque.
2. **Wake word trop large** : matcher un mot entier.
3. **Markdown à l’oral** : l’interdire dans le system prompt.
4. **Timeouts LLM** trop longs = orbe bloqué en `thinking`.
5. **Un seul thread asyncio** pour le WS ; le `listen()` micro est bloquant → thread dédié.
6. **WebView2 cache** : invalider quand tu changes le frontend (ce projet a un fichier version cache).
7. **Ports** : tuer l’ancienne instance au boot (8765 / 5173 / 8000).
8. **Sécurité** : le WS est `0.0.0.0` pour le mobile = n’importe qui sur le LAN peut envoyer `user_input`. Pour une variante, authentifie (token local) ou bind `127.0.0.1` si pas de mobile.
9. **Ne pas** coller des clés dans `jarvis_config.json` ; rester sur `.env`.
10. Qualité orbe : prévoir `setQuality("low")` sur machine faible (8000 lignes + bloom = GPU).

---

## 14. Critère de succès

Ta variante est du « même type » si, en 30 secondes, un utilisateur peut :

1. Dire le wake word et voir l’orbe passer en *listening*.
2. Poser une question et voir *thinking* puis *speaking*.
3. Faire exécuter **une action réelle** (lumière, fichier, app, timer) sans retyper dans un chat.
4. Couper la voix et muter le micro depuis le HUD.

Tout le reste (IPTV, antivirus, OS Docker, rap) est du bonus de ce dépôt, pas le cœur du genre.

---

## 15. Fichiers de ce dépôt à relire en priorité

| Fichier | Pourquoi |
|---|---|
| `ARCHITECTURE_JARVIS_DETAILLEE.md` | Carte ligne à ligne de **cette** version |
| `main2.py` | `ws_handler`, `ecouter`, `parler`, `demander_ia`, `traiter_reponse_ia`, `main` |
| `frontend/src/orb.ts` | États et lerp — à extraire / réécrire, pas à gonfler |
| `frontend/src/main.ts` | Contrat WS côté client |
| `ha_config.py` | Pattern plugin config vs moteur |
| `memory_manager.py` | Persistance minimale |
| `requirements.txt` / `frontend/package.json` | Stack |
| `DEMARRER_JARVIS.bat` | Lancement venv |

Tu n’as pas besoin de porter `main2.py`. Tu as besoin de **reproduire ces cinq boucles** : micro, STT, décision, outils, TTS, chacune branchée sur le même bus d’états.
