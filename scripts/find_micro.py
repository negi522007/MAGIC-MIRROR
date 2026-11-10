"""Trouve le bon micro en testant le volume sur chaque device input"""

import sounddevice as sd
import numpy as np
import time

print("=== Recherche du micro actif ===\n")

devices = sd.query_devices()
input_devices = []

for i, d in enumerate(devices):
    if d['max_input_channels'] > 0:
        input_devices.append(i)
        print(f"  [{i}] {d['name']} ({d['max_input_channels']} ch)")

print(f"\n  Default input: [{sd.default.device[0]}]")
print("\n--- Test de volume sur chaque micro (parle pendant le test !) ---\n")

for dev_id in input_devices:
    name = devices[dev_id]['name']
    try:
        # Enregistre 2 secondes
        print(f"  [{dev_id}] {name} ... ", end="", flush=True)
        recording = sd.rec(
            frames=32000,
            samplerate=16000,
            channels=1,
            dtype="int16",
            device=dev_id
        )
        sd.wait()

        volume = np.abs(recording).mean()
        peak = np.abs(recording).max()

        if volume > 100:
            status = "✅ SIGNAL DÉTECTÉ"
        elif volume > 10:
            status = "⚠️  signal faible"
        else:
            status = "❌ silence"

        print(f"volume={volume:.0f}  peak={peak}  {status}")

    except Exception as e:
        print(f"❌ erreur: {e}")

print("\n=== Utilise le device_id avec ✅ dans config.yaml ===")