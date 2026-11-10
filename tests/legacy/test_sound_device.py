import sounddevice as sd

device = 5

print(sd.query_devices(device))

duration = 3
fs = 48000

print("Parle maintenant")

recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, device=device)
sd.wait()

print("OK enregistrement terminé")