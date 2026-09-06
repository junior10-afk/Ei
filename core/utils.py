import os
import psutil
import numpy as np
import pygame
from typing import List

def free_ports(ports: List[int]):
    """
    Libère les ports spécifiés en terminant les processus qui les occupent,
    en évitant de terminer le processus actuel.
    """
    current_pid = os.getpid()
    for port in ports:
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr and conn.laddr.port == port:
                    pid = conn.pid
                    if pid and pid != current_pid:
                        try:
                            proc = psutil.Process(pid)
                            print(f"[Core] Libération du port {port} (arrêt du processus {proc.name()} [PID: {pid}])...")
                            proc.terminate()
                            proc.wait(timeout=1.5)
                        except Exception as ex:
                            print(f"[Core] Impossible d'arrêter le processus PID {pid}: {ex}")
        except Exception as e:
            print(f"[Core] Erreur lors de la vérification du port {port}: {e}")

def play_chime(sound_type: str = "wake"):
    """
    Génère et joue un signal sonore futuriste court (sans fichier audio externe)
    via pygame.mixer et numpy.
    """
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2)

        sample_rate = 44100
        if sound_type == "wake":
            # Bip futuriste montant court (880Hz -> 1760Hz en 120ms)
            duration = 0.12
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            freq = np.linspace(880, 1760, len(t))
            envelope = np.exp(-3 * t / duration)
            wave = 0.3 * np.sin(2 * np.pi * freq * t) * envelope

        elif sound_type == "timer":
            # Signal d'alerte / réveil carillon (3 bips rapides)
            duration = 0.35
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            wave = 0.35 * (np.sin(2 * np.pi * 1200 * t) + 0.5 * np.sin(2 * np.pi * 1600 * t))
            envelope = np.sin(np.pi * 6 * t / duration) ** 2
            wave = wave * envelope

        elif sound_type == "ack":
            # Bip de confirmation doux (523Hz -> 659Hz)
            duration = 0.10
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            freq = np.linspace(523, 659, len(t))
            envelope = np.exp(-4 * t / duration)
            wave = 0.25 * np.sin(2 * np.pi * freq * t) * envelope

        else:
            return

        # Stéréo 16-bit
        audio_data = (wave * 32767).astype(np.int16)
        stereo_data = np.column_stack((audio_data, audio_data))
        sound = pygame.sndarray.make_sound(stereo_data)
        sound.play()
    except Exception as e:
        print(f"[Chime] Erreur lecture signal sonore: {e}")
