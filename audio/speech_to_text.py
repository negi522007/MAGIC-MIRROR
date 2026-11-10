"""
Transcription de la question posée après le mot clé (Vosk, vocabulaire complet).

Événements publiés :
    stt_partial         texte partiel, pour l'affichage en direct
    speech_transcribed  phrase complète reconnue (l'écoute s'arrête)
    stt_stopped         délai dépassé sans phrase (l'écoute s'arrête)
"""

import json
import queue
import threading
import time

import vosk


class SpeechToText:
    def __init__(self, bus, microphone, model, timeout=8, max_duration=15):
        self.bus = bus
        self.mic = microphone
        self.model = model
        self.timeout = timeout            # attente du début de la phrase
        self.max_duration = max_duration  # durée max d'une écoute
        self.running = False
        self.thread = None

    def listen(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, name="stt", daemon=True)
        self.thread.start()
        print("[STT] Écoute de la question...")

    def stop(self):
        self.running = False

    def _loop(self):
        q = self.mic.attach()
        rec = vosk.KaldiRecognizer(self.model, self.mic.sample_rate)
        start = time.monotonic()
        last_partial = ""
        text = ""
        try:
            while self.running:
                elapsed = time.monotonic() - start
                if (not last_partial and elapsed > self.timeout) or elapsed > self.max_duration:
                    text = json.loads(rec.FinalResult()).get("text", "").strip()
                    break
                try:
                    data = q.get(timeout=0.3)
                except queue.Empty:
                    continue
                if rec.AcceptWaveform(data):
                    text = json.loads(rec.Result()).get("text", "").strip()
                    if text:
                        break
                else:
                    partial = json.loads(rec.PartialResult()).get("partial", "").strip()
                    if partial and partial != last_partial:
                        last_partial = partial
                        self.bus.emit("stt_partial", partial)
        finally:
            self.mic.detach(q)
            was_running = self.running
            self.running = False

        if not was_running:
            return
        if text:
            print(f"[STT] « {text} »")
            self.bus.emit("speech_transcribed", text)
        else:
            print("[STT] Aucune phrase reconnue")
            self.bus.emit("stt_stopped", None)
