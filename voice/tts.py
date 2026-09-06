import os
import re
import time
import math
import random
import tempfile
import threading
import asyncio
from typing import List, Optional
import edge_tts
import pygame
from core.state import state_manager, AssistantState
from core.config import config
from core.bus import bus

class TextToSpeech:
    def __init__(self):
        self._is_stopped = False
        self._current_process_lock = threading.Lock()
        self._pygame_initialized = False
        self._init_pygame()

    def _init_pygame(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=24000)
            self._pygame_initialized = True
        except Exception as e:
            print(f"[TTS] Avertissement initialisation pygame mixer: {e}")

    def stop(self):
        """Interrompt immédiatement la parole et la lecture audio."""
        self._is_stopped = True
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception as e:
            print(f"[TTS] Erreur arrêt pygame: {e}")
        state_manager.set_volume(0.0)
        state_manager.set_speaking(False)
        print("[TTS] Parole interrompue.")

    def _split_into_sentences(self, text: str, max_len: int = 180) -> List[str]:
        """Découpe un texte long en phrases courtes et fluides."""
        # Nettoyage markdown élémentaire si résiduel
        clean = re.sub(r"[*#_`~>\[\]]", "", text)
        clean = clean.replace("\n", " ").strip()

        # Découpage sur ponctuation
        raw_parts = re.split(r"([.?!;:]+)", clean)
        chunks: List[str] = []
        current = ""

        for i in range(0, len(raw_parts), 2):
            sentence = raw_parts[i].strip()
            punct = raw_parts[i + 1] if i + 1 < len(raw_parts) else ""
            full = (sentence + punct).strip()
            if not full:
                continue

            if len(current) + len(full) + 1 <= max_len:
                current = (current + " " + full).strip()
            else:
                if current:
                    chunks.append(current)
                current = full

        if current:
            chunks.append(current)

        return chunks if chunks else [text]

    async def _generate_audio_file(self, text: str, voice: str) -> Optional[str]:
        """Génère un fichier audio MP3 temporaire avec edge-tts."""
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp_path = temp_file.name
            temp_file.close()

            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(temp_path)
            return temp_path
        except Exception as e:
            print(f"[TTS] Erreur génération audio edge-tts: {e}")
            return None

    def speak(self, text: str):
        """Lance la synthèse vocale dans un thread dédié sans bloquer."""
        if not text or not text.strip():
            return
        threading.Thread(target=self._speak_sync, args=(text,), daemon=True).start()

    def _speak_sync(self, text: str):
        """Boucle synchrone de lecture de texte avec sous-titres et modulation orbe."""
        with self._current_process_lock:
            self._is_stopped = False
            state_manager.set_speaking(True)

            voice = config.get("voice", "fr-FR-HenriNeural")
            sentences = self._split_into_sentences(text)
            if not sentences:
                state_manager.set_speaking(False)
                return

            import concurrent.futures
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

            def fetch_audio(s: str) -> Optional[str]:
                try:
                    loop = asyncio.new_event_loop()
                    res = loop.run_until_complete(self._generate_audio_file(s, voice))
                    loop.close()
                    return res
                except Exception:
                    return None

            # Pré-génération de la première phrase
            future_next_audio = executor.submit(fetch_audio, sentences[0])

            for i in range(len(sentences)):
                if self._is_stopped:
                    break

                sentence = sentences[i]
                # Attendre l'audio de la phrase courante
                try:
                    audio_path = future_next_audio.result(timeout=15.0)
                except Exception as e:
                    print(f"[TTS] Timeout ou erreur génération phrase {i}: {e}")
                    audio_path = None

                # Lancer la pré-génération de la phrase N+1 en parallèle pendant que la phrase N joue
                if i + 1 < len(sentences) and not self._is_stopped:
                    future_next_audio = executor.submit(fetch_audio, sentences[i + 1])
                else:
                    future_next_audio = None

                if self._is_stopped or not audio_path or not os.path.exists(audio_path):
                    continue

                # Envoyer le sous-titre au HUD
                bus.broadcast_threadsafe({
                    "type": "subtitle",
                    "text": sentence
                })

                try:
                    if not pygame.mixer.get_init():
                        self._init_pygame()

                    pygame.mixer.music.load(audio_path)
                    pygame.mixer.music.play()

                    # Animation synchrone du volume pour l'orbe
                    step = 0
                    while pygame.mixer.music.get_busy() and not self._is_stopped:
                        step += 1
                        # Modulation sinusoïdale pseudo-RMS pour faire battre l'orbe avec la voix
                        base_wave = 0.45 + 0.35 * math.sin(step * 0.4)
                        noise = random.uniform(-0.1, 0.15)
                        vol = max(0.1, min(1.0, base_wave + noise))
                        state_manager.set_volume(vol)
                        time.sleep(0.04)

                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload()

                except Exception as ex:
                    print(f"[TTS] Erreur lecture audio: {ex}")
                finally:
                    # Nettoyage fichier temporaire
                    try:
                        if os.path.exists(audio_path):
                            os.remove(audio_path)
                    except Exception:
                        pass

                if self._is_stopped:
                    break

            executor.shutdown(wait=False, cancel_futures=True)

            # Fin de parole
            state_manager.set_volume(0.0)
            state_manager.set_speaking(False)
            bus.broadcast_threadsafe({
                "type": "subtitle",
                "text": ""
            })

tts_engine = TextToSpeech()
