"""TTS non-bloquant Phase 1 (PLAN_FINAL_VOICE_EI §1.1+1.2).

- Zéro fichier sur disque sur le chemin nominal : edge-tts -> MP3 en mémoire
  -> décodage soundfile (libsndfile, MP3 supporté) -> PCM float32 24 kHz
  -> sounddevice.OutputStream via buffer circulaire (deque).
- Lecture non-bloquante : le worker synthèse pousse du PCM, le callback audio
  consomme en continu. stop()/flush_now() vident le buffer instantanément
  (barge-in, préemption filler -> résultat lourd).
- Repli pygame (ancien chemin, fichier temporaire) UNIQUEMENT si sounddevice
  indisponible. Repli pyttsx3 hors-ligne conservé.
- API publique inchangée : speak(text, priority=1), stop().
  Nouveautés : feed_sentence() (= speak, alias streaming), flush_now().
"""
import asyncio
import collections
import concurrent.futures
import io
import math
import os
import queue
import random
import re
import tempfile
import threading
import time
from typing import List, Optional

import numpy as np

from core.state import state_manager, AssistantState
from core.config import config
from core.bus import bus

TARGET_SR = 24000  # edge-tts sort du 24 kHz ; on normalise tout à ce taux
_CB_BLOCK = 2048


class TextToSpeech:
    def __init__(self):
        self._is_stopped = False
        self._lock = threading.Lock()
        self._queue: queue.PriorityQueue = queue.PriorityQueue()
        self._counter: int = 0
        # Buffer circulaire PCM (float32 mono @ TARGET_SR), consommé par le callback audio
        self._pcm: collections.deque = collections.deque()
        self._pcm_lock = threading.Lock()
        self._pending_sentences = 0
        self._stream = None
        self._sd = None
        self._sd_ok = self._init_output_stream()
        self._monitor = threading.Thread(target=self._speaking_monitor, daemon=True)
        self._monitor.start()
        self._fetch_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="ei_tts_fetch")
        self._worker_thread = threading.Thread(target=self._queue_worker, daemon=True)
        self._worker_thread.start()
        self._vol_tick = 0
        self._duck = False  # Phase 3 : atténuation pendant parole utilisateur simultanée

    def duck(self, on: bool):
        """Phase 3 : baisse (True) ou restaure (False) le volume de lecture
        sans couper la file — alternative douce au stop() sec."""
        self._duck = bool(on)

    # ---------- backend audio ----------
    def _init_output_stream(self) -> bool:
        try:
            import sounddevice as sd
            self._sd = sd
            self._stream = sd.OutputStream(
                samplerate=TARGET_SR, channels=1, dtype="float32",
                blocksize=_CB_BLOCK, callback=self._audio_callback,
            )
            self._stream.start()
            print("[TTS] Sortie audio non-bloquante (sounddevice 24 kHz).")
            return True
        except Exception as e:
            print(f"[TTS] sounddevice indisponible ({e}) -> repli pygame.")
            self._init_pygame_fallback()
            return False

    def _init_pygame_fallback(self):
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=TARGET_SR)
        except Exception as e:
            print(f"[TTS] Avertissement init pygame mixer: {e}")

    def _audio_callback(self, outdata, frames, time_info, status):
        """Consomme le buffer PCM ; silence si vide. Jamais bloquant."""
        with self._pcm_lock:
            buf = self._pcm
            n = len(buf)
            take = min(frames, n)
            if take:
                chunk = np.array([buf.popleft() for _ in range(take)], dtype=np.float32)
            else:
                chunk = None
        if chunk is None:
            outdata.fill(0)
            return
        if len(chunk) < frames:
            pad = np.zeros(frames - len(chunk), dtype=np.float32)
            chunk = np.concatenate([chunk, pad])
        if self._duck:
            chunk = chunk * 0.25
        outdata[:, 0] = chunk
        # Volume orbe (RMS), MAJ throttlée (~toutes les 4 callbacks ≈ 350 ms)
        self._vol_tick += 1
        if self._vol_tick % 4 == 0:
            rms = float(np.sqrt(np.mean(chunk ** 2)))
            state_manager.set_volume(max(0.1, min(1.0, 0.3 + rms * 4)))

    def _speaking_monitor(self):
        """Remet l'état IDLE quand synthèse + lecture sont vraiment terminées."""
        while True:
            time.sleep(0.2)
            with self._pcm_lock:
                empty = not self._pcm
            if empty and self._queue.empty():
                if state_manager.is_speaking:
                    state_manager.set_volume(0.0)
                    state_manager.set_speaking(False)
                    bus.broadcast_threadsafe({"type": "subtitle", "text": ""})

    # ---------- API publique ----------
    def feed_sentence(self, text: str, priority: int = 1):
        """Enqueue une phrase pour synthèse immédiate (chemin streaming LLM)."""
        self.speak(text, priority=priority)

    def speak(self, text: str, priority: int = 1):
        if not text or not text.strip():
            return
        with self._lock:
            self._counter += 1
            self._queue.put((priority, self._counter, text.strip()))

    def flush_now(self):
        """Vide le PCM en cours (coupe le son en < 100 ms) sans toucher la file texte."""
        with self._pcm_lock:
            self._pcm.clear()
        try:
            if self._stream is not None:
                pass  # le callback émettra du silence dès le prochain bloc
        except Exception:
            pass

    def stop(self):
        """Interrompt parole + file d'attente (barge-in / préemption / stop-word)."""
        self._is_stopped = True
        self._duck = False
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        self.flush_now()
        try:
            if not self._sd_ok:
                import pygame
                if pygame.mixer.get_init():
                    pygame.mixer.music.stop()
        except Exception as e:
            print(f"[TTS] Erreur arrêt pygame: {e}")
        state_manager.set_volume(0.0)
        state_manager.set_speaking(False)
        bus.broadcast_threadsafe({"type": "subtitle", "text": ""})
        print("[TTS] Parole interrompue.")

    # ---------- segmentation ----------
    def _split_into_sentences(self, text: str, max_len: int = 180) -> List[str]:
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

    # ---------- synthèse edge-tts en mémoire ----------
    async def _fetch_mp3_bytes(self, text: str, voice: str) -> Optional[bytes]:
        try:
            import edge_tts
            communicate = edge_tts.Communicate(text, voice)
            parts = []
            async for chunk in communicate.stream():
                if chunk.get("type") == "audio":
                    parts.append(chunk.get("data"))
            return b"".join(parts) or None
        except Exception as e:
            print(f"[TTS] Erreur génération audio edge-tts ({e}).")
            return None

    def _to_target_sr(self, pcm: np.ndarray, sr: int) -> np.ndarray:
        """Normalise n'importe quel PCM float32 mono vers TARGET_SR."""
        data = np.asarray(pcm, dtype=np.float32)
        if data.ndim > 1:
            data = np.mean(data, axis=1).astype(np.float32)
        if sr != TARGET_SR and len(data):
            n_out = int(len(data) * TARGET_SR / sr)
            data = np.interp(
                np.linspace(0, len(data), n_out),
                np.arange(len(data)), data,
            ).astype(np.float32)
        return data

    def _mp3_to_pcm(self, mp3: bytes) -> Optional[np.ndarray]:
        """Décode MP3 (mémoire) -> float32 mono @ TARGET_SR. Aucun fichier."""
        try:
            import soundfile as sf
            data, sr = sf.read(io.BytesIO(mp3), dtype="float32", always_2d=False)
            return self._to_target_sr(data, sr)
        except Exception as e:
            print(f"[TTS] Erreur décodage MP3 en mémoire ({e}).")
            return None

    def _synth_mms(self, text: str) -> Optional[np.ndarray]:
        """Phase 3bis : synthèse locale MMS-FR -> PCM @ TARGET_SR. None si indispo."""
        try:
            from voice.hf_tts import hf_tts_tier
            res = hf_tts_tier.synthesize_mms(text)
            if not res:
                return None
            pcm, sr = res
            out = self._to_target_sr(pcm, sr)
            return out if len(out) else None
        except Exception as e:
            print(f"[TTS] Tier MMS indisponible ({e}).")
            return None

    def _speak_local_pyttsx3(self, text: str):
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

    # ---------- worker ----------
    def _queue_worker(self):
        executor = self._fetch_executor
        while True:
            try:
                priority, _, text = self._queue.get()
                self._synthesize_text(text, executor)
                self._queue.task_done()
            except Exception as e:
                print(f"[TTS] Erreur dans le worker TTS: {e}")
                time.sleep(0.1)

    def _synthesize_text(self, text: str, executor) -> None:
        with self._lock:
            self._is_stopped = False
            state_manager.set_speaking(True)
        voice = config.get("voice", "fr-FR-HenriNeural")
        sentences = self._split_into_sentences(text)
        if not sentences:
            return

        def fetch_mp3(s: str) -> Optional[bytes]:
            try:
                loop = asyncio.new_event_loop()
                res = loop.run_until_complete(self._fetch_mp3_bytes(s, voice))
                loop.close()
                return res
            except Exception:
                return None

        future_next = executor.submit(fetch_mp3, sentences[0])
        # Phase 3bis : ordre des tiers configurable (edge = qualité cloud par défaut,
        # mms = 100 % offline). Le tier non prioritaire sert de repli automatique.
        provider = str(config.get("tts_provider", "edge") or "edge").lower()
        for i, sentence in enumerate(sentences):
            if self._is_stopped:
                break
            try:
                mp3 = future_next.result(timeout=15.0)
            except Exception:
                mp3 = None
            if i + 1 < len(sentences) and not self._is_stopped:
                future_next = executor.submit(fetch_mp3, sentences[i + 1])
            if self._is_stopped:
                break
            bus.broadcast_threadsafe({"type": "subtitle", "text": sentence})
            pcm = None
            if provider == "mms":
                pcm = self._synth_mms(sentence)
                if (pcm is None or not len(pcm)) and mp3:
                    pcm = self._mp3_to_pcm(mp3)
            else:
                if mp3:
                    pcm = self._mp3_to_pcm(mp3)
                if pcm is None or not len(pcm):
                    print("[TTS] Edge indisponible, repli MMS local (offline)...")
                    pcm = self._synth_mms(sentence)
            if pcm is None or not len(pcm):
                print("[TTS] Repli voix locale de secours (pyttsx3)...")
                self._speak_local_pyttsx3(sentence)
                continue
            if self._sd_ok:
                # Pousse à plat ; le callback consomme en continu
                with self._pcm_lock:
                    self._pcm.extend(float(x) for x in pcm)
            else:
                self._play_pygame_fallback(mp3, sentence, pcm_fallback=pcm)

    def _play_pygame_fallback(self, mp3: Optional[bytes], sentence: str,
                              pcm_fallback: Optional[np.ndarray] = None):
        """Repli avec fichier temporaire UNIQUEMENT si sounddevice indisponible."""
        import pygame
        path = None
        try:
            if mp3:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                    f.write(mp3)
                    path = f.name
            elif pcm_fallback is not None:
                import soundfile as sf
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                    path = f.name
                sf.write(path, np.asarray(pcm_fallback, dtype=np.float32), TARGET_SR)
            else:
                self._speak_local_pyttsx3(sentence)
                return
            if not pygame.mixer.get_init():
                self._init_pygame_fallback()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            step = 0
            while pygame.mixer.music.get_busy() and not self._is_stopped:
                step += 1
                vol = max(0.1, min(1.0, 0.45 + 0.35 * math.sin(step * 0.4) + random.uniform(-0.1, 0.15)))
                state_manager.set_volume(vol)
                time.sleep(0.04)
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
        except Exception as ex:
            print(f"[TTS] Erreur lecture pygame ({ex}). Repli local.")
            self._speak_local_pyttsx3(sentence)
        finally:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass


tts_engine = TextToSpeech()
