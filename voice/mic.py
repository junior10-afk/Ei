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

    def restart(self):
        """Rouvre le flux sur le périphérique courant de la config (bascule à chaud)."""
        was_running = self._running
        self.stop()
        if was_running:
            # Laisse le flux se libérer avant réouverture
            time.sleep(0.3)
            self.start()
            print("[Microphone] Flux rouvert (nouveau périphérique).")

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

                buffer = []  # liste de (chunk, tainted) ; tainted=True = contaminé par le TTS (exclu du STT)
                is_recording_speech = False
                silence_start_time = None
                phrase_start_time = None
                speech_confirmed = False
                last_partial_time = 0.0
                self._partial_in_flight = False

                # Phase 3 : barge-in et anti-écho sans fenêtre aveugle
                # + garde anti auto-écho (Phase 3 fix coupures) : le micro capte les
                # haut-parleurs pendant le TTS. On apprend le plancher d'écho et on
                # n'interrompt que si le niveau le dépasse nettement, de façon soutenue.
                was_speaking = False
                speaking_start_time = 0.0
                last_speaking_end = 0.0
                barge_hits = 0
                echo_floor = 0.0
                GRACE_SEC = 0.15        # onset playback avant d'autoriser le barge-in
                BARGE_SUSTAIN = 5       # chunks consécutifs (≈250 ms) -> < 500 ms au pire
                ECHO_MARGIN = 1.8       # barge seulement si rms >= echo_floor x 1.8
                SILENCE_CAP_SEC = 0.7   # plafond du silence de fin (plan §Phase 3)

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
                    # Phase 3 : plafond 0.7 s (au-delà, on coupe les tours en deux)
                    if silence_limit > SILENCE_CAP_SEC:
                        silence_limit = SILENCE_CAP_SEC
                    max_phrase_time = float(config.get("max_phrase_sec", 15.0))

                    # 2. L'assistant parle : ducking + barge-in soutenu, jamais de buffer wipe
                    is_speaking = state_manager.is_speaking
                    now = time.time()

                    if is_speaking:
                        if not was_speaking:
                            was_speaking = True
                            speaking_start_time = now
                            barge_hits = 0
                            echo_floor = 0.0

                        data, _ = stream.read(CHUNK_SAMPLES)
                        chunk = data.flatten()
                        rms = self._calculate_rms(chunk)

                        if (now - speaking_start_time) > GRACE_SEC:
                            barge_level = max(sensitivity * 2.5, echo_floor * ECHO_MARGIN)
                            if rms >= barge_level:
                                barge_hits += 1
                            else:
                                barge_hits = 0
                                # Apprend le plancher d'écho (voix des haut-parleurs)
                                if rms > echo_floor:
                                    echo_floor = rms
                                else:
                                    echo_floor = echo_floor * 0.995 + rms * 0.005
                            # Voix présente mais pas d'interruption franche -> ducking
                            tts_engine.duck(rms >= sensitivity and barge_hits == 0)
                            if barge_hits >= BARGE_SUSTAIN:
                                print(f"[Microphone] Barge-In (rms={rms:.4f} >= "
                                      f"seuil={barge_level:.4f}, écho={echo_floor:.4f})")
                                tts_engine.stop()  # reset aussi le duck
                                state_manager.set_state(AssistantState.BARGE_IN)
                                state_manager.set_state(AssistantState.LISTENING)
                                is_recording_speech = True
                                phrase_start_time = now
                                speech_confirmed = True
                                buffer = [(chunk, False)]
                                silence_start_time = None
                                last_partial_time = now
                                barge_hits = 0
                                was_speaking = False
                                continue
                        time.sleep(0.02)
                        continue

                    # L'assistant vient de se taire : AUCUNE fenêtre aveugle (Phase 3).
                    # Seule la réverbération faible (< 300 ms, sous le seuil de barge)
                    # est marquée tainted ; une vraie reprise vocale reste capturée.
                    if was_speaking:
                        was_speaking = False
                        tts_engine.duck(False)
                        barge_hits = 0
                        last_speaking_end = now

                    # 3. Capture audio normale (Phase 3 : provisoire -> confirmé + partiels)
                    data, overflowed = stream.read(CHUNK_SAMPLES)
                    chunk = data.flatten()
                    rms = self._calculate_rms(chunk)

                    # Si l'utilisateur parle
                    if rms >= sensitivity:
                        # Réverbération de fin TTS : tainted sauf reprise franche
                        tail_tainted = ((now - last_speaking_end) < 0.3
                                        and rms < sensitivity * 2.5)
                        if not is_recording_speech:
                            # Début de parole : état provisoire (pas encore une phrase)
                            is_recording_speech = True
                            phrase_start_time = now
                            speech_confirmed = False
                            buffer = [(chunk, tail_tainted)]
                            last_partial_time = now
                            state_manager.set_state(AssistantState.PROVISIONAL)
                        else:
                            buffer.append((chunk, tail_tainted))
                        silence_start_time = None
                        # Parole soutenue > 0.5 s -> phrase probable
                        if not speech_confirmed and (now - phrase_start_time) >= 0.5:
                            speech_confirmed = True
                            state_manager.set_state(AssistantState.LISTENING)
                        # Transcript provisoire best-effort (throttlé, jamais bloquant)
                        if (speech_confirmed and not self._partial_in_flight
                                and (now - phrase_start_time) >= 1.5
                                and (now - last_partial_time) >= 2.0):
                            last_partial_time = now
                            self._partial_in_flight = True
                            partial_copy = [c for c, t in buffer if not t]
                            threading.Thread(target=self._partial_transcribe,
                                             args=(partial_copy,), daemon=True).start()
                    else:
                        if is_recording_speech:
                            buffer.append((chunk, False))
                            if silence_start_time is None:
                                silence_start_time = now
                            elif (now - silence_start_time) >= silence_limit:
                                # Fin de phrase après silence (plafonné à 0.7 s)
                                self._process_phrase(buffer, phrase_start_time)
                                buffer = []
                                is_recording_speech = False
                                speech_confirmed = False
                                silence_start_time = None

                    # Limite de durée max
                    if is_recording_speech and phrase_start_time and (now - phrase_start_time) >= max_phrase_time:
                        self._process_phrase(buffer, phrase_start_time)
                        buffer = []
                        is_recording_speech = False
                        speech_confirmed = False
                        silence_start_time = None

        except Exception as e:
            print(f"[Microphone] Erreur capture audio: {e}")

    def _partial_transcribe(self, chunks: list):
        """Phase 3 : transcript provisoire best-effort en background. Échec = silence."""
        try:
            if chunks:
                audio = np.concatenate(chunks)
                if len(audio) / SAMPLE_RATE >= 1.0:
                    text = stt_engine.transcribe_partial_numpy(audio, SAMPLE_RATE)
                    if text:
                        bus.broadcast_threadsafe({
                            "type": "transcript_provisional",
                            "text": text
                        })
        except Exception:
            pass
        finally:
            self._partial_in_flight = False

    def _process_phrase(self, buffer: list, start_time: Optional[float]):
        """Traite et transcrit une phrase enregistrée.
        Phase 3 : buffer = [(chunk, tainted)] ; les chunks contaminés par le TTS
        sont exclus avant transcription (plus de fenêtre aveugle)."""
        if not buffer or start_time is None:
            state_manager.set_state(AssistantState.IDLE)
            return

        # Normaliser : extraire les chunks non-tainted
        clean_chunks = []
        for item in buffer:
            if isinstance(item, tuple):
                chunk, tainted = item
                if not tainted:
                    clean_chunks.append(chunk)
            else:
                clean_chunks.append(item)  # compat ancien format
        if not clean_chunks:
            state_manager.set_state(AssistantState.IDLE)
            return

        # Ignorer les bruits trop courts (< 0.5s de parole propre)
        clean_duration = len(np.concatenate(clean_chunks)) / SAMPLE_RATE if clean_chunks else 0
        if clean_duration < 0.5:
            state_manager.set_state(AssistantState.IDLE)
            return

        full_audio = np.concatenate(clean_chunks)
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
        bus.broadcast_threadsafe({
            "type": "transcript_final",
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


def list_input_devices() -> list:
    """Énumère les périphériques d'entrée audio (pour le sélecteur du HUD).
    Jamais d'exception : [] si indisponible."""
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        try:
            default_in, _ = sd.default.device
        except Exception:
            default_in = None
        result = []
        for i, d in enumerate(devices):
            if d.get("max_input_channels", 0) > 0:
                result.append({
                    "index": i,
                    "name": d.get("name", f"Périphérique {i}"),
                    "default": (i == default_in),
                })
        return result
    except Exception as e:
        print(f"[Microphone] Énumération impossible ({e}).")
        return []
