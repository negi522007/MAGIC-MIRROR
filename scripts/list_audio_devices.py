import sounddevice as sd

print("=== Périphériques audio disponibles ===\n")
devices = sd.query_devices()
for i, d in enumerate(devices):
    direction = ""
    if d['max_input_channels'] > 0:
        direction += "🎤 INPUT"
    if d['max_output_channels'] > 0:
        direction += " 🔊 OUTPUT"
    print(f"  [{i}] {d['name']} {direction}")

print(f"\n  Default input:  [{sd.default.device[0]}]")
print(f"  Default output: [{sd.default.device[1]}]")