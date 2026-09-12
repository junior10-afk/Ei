import os
import re
import time
import math
import queue
import random
import tempfile
import threading
import asyncio
import concurrent.futures
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
        self._queue: queue.PriorityQueue = queue.PriorityQueue()
        self._counter: int = 0
        self._worker_thread = threading.Thread(target=self._queue_worker, daemon=True)
        self._worker_thread.start()
        self._init_pygame()

    def _init_pygame(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=24000)
            self._pygame_initialized = True
        except Exception as e:
            print(f"[TTS] Avertissement initialisation pygame mixer: {e}")

    def stop(self):
        """Interrompt immédiatement la parole, vide la file d'attente et coupe le son."""
        self._is_stopped = True
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception as e:
            print(f"[TTS] Erreur arrêt pygame: {e}")
        state_manager.set_volume(0.0)
        state_manager.set_speaking(False)
        bus.broadcast_threadsafe({"type": "subtitle", "text": ""})
        print("[TTS] Parole interrompue.")

    def _split_into_sentences(self, text: str, max_len: int = 180) -> List[str]:
        """Découpe un texte long en phrases courtes et fluides."""
        clean = re.sub(r"[*#_`~>\[\]]", "", text)
        clean = clean.replace("\n", " ").strip()

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
            print(f"[TTS] Erreur génération audio edge-tts ({e}).")
            return None

    def _speak_local_pyttsx3(self, text: str):
        """Synthèse vocale locale hors-ligne via pyttsx3 (SAPI5 Windows)."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            for v in voices:
                if "french" in v.name.lower() or "hortense" in v.name.lower() or "fr" in v.id.lower():
                    engine.setProperty('voice', v.id)
                    break
            engine.setProperty('rate', 170)
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"[TTS] Erreur fallback pyttsx3: {e}")

    def speak(self, text: str, priority: int = 1):
        """Met en file d'attente la synthèse vocale (priorité 1 = réponse directe, 2 = notification)."""
        if not text or not text.strip():
            return
        self._counter += 1
        self._queue.put((priority, self._counter, text.strip()))

    def _queue_worker(self):
        """Worker d'arrière-plan traitant les demandes de synthèse vocale par ordre de priorité."""
        while True:
            try:
                priority, _, text = self._queue.get()
                self._speak_sync(text)
                self._queue.task_done()
            except Exception as e:
                print(f"[TTS] Erreur dans le worker TTS: {e}")
                time.sleep(0.1)

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

            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

            def fetch_audio(s: str) -> Optional[str]:
                try:
                    loop = asyncio.new_event_loop()
                    res = loop.run_until_complete(self._generate_audio_file(s, voice))
                    loop.close()
                    return res
                except Exception:
                    return None

            future_next_audio = executor.submit(fetch_audio, sentences[0])

            for i in range(len(sentences)):
                if self._is_stopped:
                    break

                sentence = sentences[i]
                try:
                    audio_path = future_next_audio.result(timeout=10.0)
                except Exception:
                    audio_path = None

                if i + 1 < len(sentences) and not self._is_stopped:
                    future_next_audio = executor.submit(fetch_audio, sentences[i + 1])
                else:
                    future_next_audio = None

                if self._is_stopped:
                    break

                # Envoyer le sous-titre au HUD
                bus.broadcast_threadsafe({
                    "type": "subtitle",
                    "text": sentence
                })

                # Si échec de la génération en ligne, basculer sur le moteur local pyttsx3
                if not audio_path or not os.path.exists(audio_path):
                    print(f"[TTS] Repli sur la voix locale de secours (offline)...")
                    self._speak_local_pyttsx3(sentence)
                    continue

                try:
                    if not pygame.mixer.get_init():
                        self._init_pygame()

                    pygame.mixer.music.load(audio_path)
                    pygame.mixer.music.play()

                    step = 0
                    while pygame.mixer.music.get_busy() and not self._is_stopped:
                        step += 1
                        base_wave = 0.45 + 0.35 * math.sin(step * 0.4)
                        noise = random.uniform(-0.1, 0.15)
                        vol = max(0.1, min(1.0, base_wave + noise))
                        state_manager.set_volume(vol)
                        time.sleep(0.04)

                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload()

                except Exception as ex:
                    print(f"[TTS] Erreur lecture audio pygame ({ex}). Repli local.")
                    self._speak_local_pyttsx3(sentence)
                finally:
                    try:
                        if audio_path and os.path.exists(audio_path):
                            os.remove(audio_path)
                    except Exception:
                        pass

                if self._is_stopped:
                    break

            executor.shutdown(wait=False, cancel_futures=True)

            state_manager.set_volume(0.0)
            state_manager.set_speaking(False)
            bus.broadcast_threadsafe({
                "type": "subtitle",
                "text": ""
            })

tts_engine = TextToSpeech()

