"""Vérification manuelle : synthèse vocale (affiche le moteur choisi et le temps de synthèse).

    python scripts/check_tts.py ["texte à dire"]
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audio.audio_state import AudioState  # noqa: E402
from audio.tts import TTSService  # noqa: E402
from config import load_config, resolve_path  # noqa: E402

cfg = load_config()
text = sys.argv[1] if len(sys.argv) > 1 else "Bonjour, je suis votre miroir magique. Votre tenue est superbe !"
tts = TTSService(AudioState(), cfg["tts"]["backends"], resolve_path(cfg["models"]["piper_voice"]),
                 cfg["models"].get("coqui"), cfg["audio"].get("output_device_id"))
if tts.backend in ("piper", "coqui"):
    t = time.perf_counter()
    audio, sr = tts.synthesize(text)
    dt = time.perf_counter() - t
    print(f"Synthèse : {dt:.2f} s pour {len(audio) / sr:.2f} s d'audio "
          f"(facteur temps réel {dt / (len(audio) / sr):.2f})")
tts.speak(text)
