import io
import wave
from typing import Optional
import numpy as np
import speech_recognition as sr

class SpeechToText:
    def __init__(self, language: str = "fr-FR"):
        self.language = language
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True

    def transcribe_audio_bytes(self, audio_data: bytes, sample_rate: int = 16000) -> Optional[str]:
        """
        Transcrit un flux PCM int16 mono vers du texte avec Google STT (gratuit).
        """
        try:
            audio = sr.AudioData(audio_data, sample_rate, 2)
            text = self.recognizer.recognize_google(audio, language=self.language)
            return text.strip() if text else None
        except sr.UnknownValueError:
            # Parole inintelligible
            return None
        except sr.RequestError as e:
            print(f"[STT] Erreur service Google Speech: {e}")
            return None
        except Exception as ex:
            print(f"[STT] Erreur inattendue: {ex}")
            return None

    def transcribe_numpy(self, np_audio: np.ndarray, sample_rate: int = 16000) -> Optional[str]:
        """Convertit un tableau numpy int16 et transcrit."""
        if np_audio.dtype != np.int16:
            np_audio = (np_audio * 32767).astype(np.int16)
        audio_bytes = np_audio.tobytes()
        return self.transcribe_audio_bytes(audio_bytes, sample_rate)

stt_engine = SpeechToText()
