"""Tier TTS local Hugging Face (Phase 3bis).

- Primaire offline : facebook/mms-tts-fra (VITS 145 Mo, ~2.6x temps réel CPU).
- Lazy-load : rien n'est chargé tant que le tier n'est pas utilisé.
- Sortie : (pcm_float32_mono, sample_rate). Le resampling vers 24 kHz
  est fait par l'appelant (voice/tts.py).
"""
import threading
from typing import Optional, Tuple

import numpy as np

_MMS_ID = "facebook/mms-tts-fra"


class LocalTtsTier:
    def __init__(self):
        self._lock = threading.Lock()
        self._mms_model = None
        self._mms_tok = None
        self._mms_failed = False

    def _load_mms(self) -> bool:
        with self._lock:
            if self._mms_model is not None:
                return True
            if self._mms_failed:
                return False
            try:
                from transformers import VitsModel, AutoTokenizer
                print("[HF-TTS] Chargement facebook/mms-tts-fra ...")
                self._mms_tok = AutoTokenizer.from_pretrained(_MMS_ID)
                self._mms_model = VitsModel.from_pretrained(_MMS_ID)
                self._mms_model.eval()
                print("[HF-TTS] MMS-FR prêt.")
                return True
            except Exception as e:
                print(f"[HF-TTS] MMS indisponible ({e}).")
                self._mms_failed = True
                return False

    def synthesize_mms(self, text: str) -> Optional[Tuple[np.ndarray, int]]:
        """Texte FR -> (PCM float32, sr). None si indisponible. Jamais d'exception."""
        try:
            if not text or not text.strip():
                return None
            if not self._load_mms():
                return None
            import torch
            inputs = self._mms_tok(text.strip(), return_tensors="pt")
            with torch.no_grad():
                wav = self._mms_model(**inputs).waveform[0].numpy()
            if wav.ndim > 1:
                wav = np.mean(wav, axis=0)
            wav = np.asarray(wav, dtype=np.float32)
            if len(wav) == 0 or float(np.abs(wav).max()) < 1e-4:
                return None
            return wav, int(self._mms_model.config.sampling_rate)
        except Exception as e:
            print(f"[HF-TTS] Erreur synthèse MMS ({e}).")
            return None


hf_tts_tier = LocalTtsTier()
