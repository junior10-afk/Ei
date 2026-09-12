import time
import threading
from typing import Optional, Callable
import numpy as np
import sounddevice as sd
from core.state import state_manager, AssistantState
from core.config import config
from core.bus import bus
from voice.stt import stt_engine
from voice.wake import check_wake_word, contains_stop_word
from voice.tts import tts_engine

SAMPLE_RATE = 16000
CHUNK_DURATION = 0.05  # 50 ms par chunk
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_DURATION)

class MicrophoneListener:
    def __init__(self, on_speech_recognized: Optional[Callable[[str], None]] = None):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.on_speech_recognized = on_speech_recognized

    def start(self):
        """Démarre le thread d'écoute continue."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        print("[Microphone] Écoute micro démarrée.")

    def stop(self):
        """Arrête le thread d'écoute."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        print("[Microphone] Écoute micro arrêtée.")

    def _calculate_rms(self, audio_chunk: np.ndarray) -> float:
        """Calcule l'énergie RMS normalisée (0.0 à 1.0)."""
        if len(audio_chunk) == 0:
            return 0.0
        float_chunk = audio_chunk.astype(np.float32) / 32768.0
        return float(np.sqrt(np.mean(float_chunk ** 2)))

    def _listen_loop(self):
        """Boucle de détection VAD et enregistrement de phrases avec calibration et anti-écho."""
        device_index = config.get("mic_device_index", None)

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype='int16',
                blocksize=CHUNK_SAMPLES,
                device=device_index
            ) as stream:
                # 0. Calibration initiale du bruit ambiant (1 seconde)
                print("[Microphone] Calibration du bruit ambiant (1s)...")
                calib_samples = []
                for _ in range(int(1.0 / CHUNK_DURATION)):
                    if not self._running:
                        return
                    data, _ = stream.read(CHUNK_SAMPLES)
                    calib_samples.append(self._calculate_rms(data.flatten()))
                
                ambient_rms = float(np.mean(calib_samples)) if calib_samples else 0.01
                auto_thresh = max(0.010, min(0.06, ambient_rms * 1.8))
                print(f"[Microphone] Bruit ambiant: {ambient_rms:.4f} -> Seuil VAD calculé: {auto_thresh:.4f}")

                buffer = []
                is_recording_speech = False
                silence_start_time = None
                phrase_start_time = None
                
                # Gestion anti-écho et barge-in
                was_speaking = False
                speaking_start_time = 0.0
                last_speaking_end_time = 0.0
                ANTI_ECHO_WINDOW = 0.35  # 350ms après la parole TTS

                while self._running:
                    # 1. Anti-larsen & Mute
                    if state_manager.is_mic_muted:
                        time.sleep(0.1)
                        continue

                    # Lecture dynamique de la configuration à chaque itération
                    cfg_sens = config.get("mic_sensitivity_rms", None)
                    if cfg_sens is not None and float(cfg_sens) > 0:
                        sensitivity = max(float(cfg_sens), auto_thresh)
                    else:
                        sensitivity = auto_thresh
                    
                    silence_limit = float(config.get("silence_duration_sec", 1.2))
                    max_phrase_time = float(config.get("max_phrase_sec", 15.0))

                    # 2. Gestion état TTS (parole de l'assistant)
                    is_speaking = state_manager.is_speaking
                    now = time.time()

                    if is_speaking:
                        if not was_speaking:
                            was_speaking = True
                            speaking_start_time = now
                            # Si on était en train d'enregistrer, annuler pour ne pas capturer le TTS
                            buffer = []
                            is_recording_speech = False
                            silence_start_time = None

                        data, _ = stream.read(CHUNK_SAMPLES)
                        chunk = data.flatten()
                        rms = self._calculate_rms(chunk)

                        # Fenêtre de grâce initiale de 350ms avant d'autoriser le barge-in
                        if (now - speaking_start_time) > ANTI_ECHO_WINDOW:
                            # Détection d'interruption vocale distincte
                            if rms >= sensitivity * 2.5:
                                print("[Microphone] Interruption vocale (Barge-In) détectée !")
                                tts_engine.stop()
                                state_manager.set_state(AssistantState.LISTENING)
                                is_recording_speech = True
                                phrase_start_time = now
                                buffer = [chunk]
                                silence_start_time = None
                                was_speaking = False
                                continue
                        time.sleep(0.02)
                        continue

                    # Si l'assistant vient de se taire, appliquer la fenêtre anti-écho (réverbération pièce)
                    if was_speaking:
                        was_speaking = False
                        last_speaking_end_time = now

                    if (now - last_speaking_end_time) < ANTI_ECHO_WINDOW:
                        # Vider le buffer matériel sans déclencher de transcription
                        stream.read(CHUNK_SAMPLES)
                        time.sleep(0.02)
                        continue

                    # 3. Capture audio normale
                    data, overflowed = stream.read(CHUNK_SAMPLES)
                    chunk = data.flatten()
                    rms = self._calculate_rms(chunk)

                    # Si l'utilisateur parle
                    if rms >= sensitivity:
                        if not is_recording_speech:
                            # Début de la parole détecté
                            is_recording_speech = True
                            phrase_start_time = now
                            buffer = [chunk]
                            state_manager.set_state(AssistantState.LISTENING)
                        else:
                            buffer.append(chunk)
                        silence_start_time = None
                    else:
                        if is_recording_speech:
                            buffer.append(chunk)
                            if silence_start_time is None:
                                silence_start_time = now
                            elif (now - silence_start_time) >= silence_limit:
                                # Fin de phrase après silence
                                self._process_phrase(buffer, phrase_start_time)
                                buffer = []
                                is_recording_speech = False
                                silence_start_time = None

                    # Limite de durée max
                    if is_recording_speech and phrase_start_time and (now - phrase_start_time) >= max_phrase_time:
                        self._process_phrase(buffer, phrase_start_time)
                        buffer = []
                        is_recording_speech = False
                        silence_start_time = None

        except Exception as e:
            print(f"[Microphone] Erreur capture audio: {e}")

    def _process_phrase(self, buffer: list, start_time: Optional[float]):
        """Traite et transcrit une phrase enregistrée."""
        if not buffer or start_time is None:
            state_manager.set_state(AssistantState.IDLE)
            return

        duration = time.time() - start_time
        # Ignorer les bruits trop courts (< 0.5s)
        if duration < 0.5:
            state_manager.set_state(AssistantState.IDLE)
            return

        full_audio = np.concatenate(buffer)
        state_manager.set_state(AssistantState.THINKING)

        text = stt_engine.transcribe_numpy(full_audio, SAMPLE_RATE)
        if not text:
            state_manager.set_state(AssistantState.IDLE)
            return

        print(f"[STT] Reconnu: « {text} »")
        bus.broadcast_threadsafe({
            "type": "user_speech",
            "text": text
        })

        # Vérifier si c'est un ordre de silence direct
        if contains_stop_word(text):
            tts_engine.stop()
            state_manager.set_state(AssistantState.IDLE)
            return

        # Appeler le callback de dispatch (cerveau)
        if self.on_speech_recognized:
            self.on_speech_recognized(text)

mic_listener = MicrophoneListener()
