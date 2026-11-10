"""Vérification manuelle : le micro configuré + Vosk reconnaissent-ils la parole ?

    python scripts/check_micro.py [device_id]      (Ctrl+C pour arrêter)
"""
import json
import os
import queue
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sounddevice as sd  # noqa: E402
import vosk  # noqa: E402

from config import load_config, resolve_path  # noqa: E402

cfg = load_config()
device = int(sys.argv[1]) if len(sys.argv) > 1 else cfg["audio"]["device_id"]
print(f"Micro : {sd.query_devices(device if device is not None else sd.default.device[0])['name']}")
vosk.SetLogLevel(-1)
rec = vosk.KaldiRecognizer(vosk.Model(resolve_path(cfg["models"]["vosk"])), 16000)
q = queue.Queue()
with sd.RawInputStream(samplerate=16000, blocksize=4000, dtype="int16", channels=1,
                       device=device, callback=lambda d, f, t, s: q.put(bytes(d))):
    print("Parlez... (Ctrl+C pour arrêter)")
    try:
        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                text = json.loads(rec.Result()).get("text", "")
                if text:
                    print(f"\n✅ « {text} »")
            else:
                print("   ... " + json.loads(rec.PartialResult()).get("partial", ""), end="\r")
    except KeyboardInterrupt:
        print("\nFin.")
