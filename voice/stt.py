import io
import wave
import threading
from typing import Optional
import numpy as np
import speech_recognition as sr

class SpeechToText:
    def __init__(self, language: str = "fr-FR"):
        self.language = language
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self._whisper_model = None
        self._whisper_failed = False
        self._whisper_lock = threading.Lock()

    def _get_local_whisper(self):
        """Chargement paresseux du modèle local faster-whisper."""
        with self._whisper_lock:
            if self._whisper_model is None and not self._whisper_failed:
                try:
                    from faster_whisper import WhisperModel
                    print("[STT] Chargement du modèle de secours local faster-whisper (tiny)...")
                    self._whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
                    print("[STT] Modèle local faster-whisper prêt.")
                except Exception as e:
                    print(f"[STT] Modèle local faster-whisper non disponible: {e}")
                    self._whisper_failed = True
            return self._whisper_model

    def _transcribe_local_whisper(self, np_audio: np.ndarray) -> Optional[str]:
        """Transcription 100% hors-ligne via faster-whisper."""
        model = self._get_local_whisper()
        if not model:
            return None
        try:
            if np_audio.dtype == np.int16:
                float_audio = np_audio.astype(np.float32) / 32768.0
            else:
                float_audio = np_audio.astype(np.float32)

            segments, _ = model.transcribe(float_audio, language="fr", beam_size=2)
            texts = [s.text.strip() for s in segments if s.text.strip()]
            full_text = " ".join(texts).strip()
            if full_text:
                print(f"[STT-Offline] Reconnu localement: « {full_text} »")
                return full_text
            return None
        except Exception as e:
            print(f"[STT] Erreur transcription locale faster-whisper: {e}")
            return None

    def transcribe_audio_bytes(self, audio_data: bytes, sample_rate: int = 16000) -> Optional[str]:
        """
        Transcrit un flux PCM int16 mono vers du texte avec Google STT (gratuit).
        """
        try:
            audio = sr.AudioData(audio_data, sample_rate, 2)
            text = self.recognizer.recognize_google(audio, language=self.language)
            return text.strip() if text else None
        except sr.UnknownValueError:
            return None
        except (sr.RequestError, Exception) as e:
            # Erreur de connexion ou réseau indisponible -> fallback local
            print(f"[STT] Service Cloud indisponible ({e}). Bascule vers faster-whisper local...")
            np_arr = np.frombuffer(audio_data, dtype=np.int16)
            return self._transcribe_local_whisper(np_arr)

    def transcribe_numpy(self, np_audio: np.ndarray, sample_rate: int = 16000) -> Optional[str]:
        """Convertit un tableau numpy int16 et transcrit avec double étage Cloud / Local."""
        if np_audio.dtype != np.int16:
            np_audio = (np_audio * 32767).astype(np.int16)
        audio_bytes = np_audio.tobytes()
        return self.transcribe_audio_bytes(audio_bytes, sample_rate)

stt_engine = SpeechToText()

