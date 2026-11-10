"""Test du micro — vérifie que le device_id capte du son"""

import sounddevice as sd
import vosk
import json
import sys

# Même config que ton projet
DEVICE_ID = 7
MODEL_PATH = "models/vosk-model-small-fr"

print(f"=== Test micro device [{DEVICE_ID}] ===")
print(f"Device: {sd.query_devices(DEVICE_ID)['name']}")
print("Parle maintenant... (Ctrl+C pour arrêter)\n")

model = vosk.Model(MODEL_PATH)
rec = vosk.KaldiRecognizer(model, 16000)

import queue
q = queue.Queue()

def callback(indata, frames, time_info, status):
    if status:
        print(f"⚠ Status: {status}")
    q.put(bytes(indata))

try:
    with sd.RawInputStream(
        samplerate=16000,
        blocksize=8000,
        dtype="int16",
        channels=1,
        callback=callback,
        device=DEVICE_ID
    ):
        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "").strip()
                if text:
                    print(f"✅ Reconnu: '{text}'")
            else:
                partial = json.loads(rec.PartialResult())
                partial_text = partial.get("partial", "")
                if partial_text:
                    print(f"   ... {partial_text}", end="\r")

except KeyboardInterrupt:
    print("\n\nTest terminé.")