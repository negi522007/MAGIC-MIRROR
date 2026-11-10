"""
Détection du mot clé (« miroir magique ») avec Vosk.

Avec `use_grammar`, le reconnaisseur est restreint à la phrase clé (+ « [unk] »
pour tout le reste) : il ne cherche plus parmi tout le vocabulaire français, ce qui
le rend plus fiable et moins gourmand. Les résultats partiels sont examinés pour
réagir dès que la phrase est prononcée, sans attendre la fin du silence.
"""

import json
import queue
import threading
import time
import unicodedata

import vosk


def normalize(text):
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn").strip()


class WakeWord:
    def __init__(self, bus, microphone, model, wake_phrase="miroir magique",
                 cooldown=3, use_grammar=True):
        self.bus = bus
        self.mic = microphone
        self.model = model
        self.wake_phrase = normalize(wake_phrase)
        self.cooldown = cooldown
        self.grammar = json.dumps([wake_phrase.lower(), "[unk]"]) if use_grammar else None

        self.running = False
        self.paused = False
        self.thread = None
        self.last_trigger = 0.0
        self._resume_event = threading.Event()
        self._resume_event.set()

    def _new_recognizer(self):
        if self.grammar:
            return vosk.KaldiRecognizer(self.model, self.mic.sample_rate, self.grammar)
        return vosk.KaldiRecognizer(self.model, self.mic.sample_rate)

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, name="wake-word", daemon=True)
        self.thread.start()
        print(f"[WAKE] Écoute du mot clé « {self.wake_phrase} »")

    def pause(self):
        self.paused = True
        self._resume_event.clear()

    def resume(self):
        self.paused = False
        self._resume_event.set()

    def stop(self):
        self.running = False
        self._resume_event.set()
        if self.thread:
            self.thread.join(timeout=2)

    def _loop(self):
        while self.running:
            self._resume_event.wait()
            if not self.running:
                break
            q = self.mic.attach()
            rec = self._new_recognizer()
            try:
                while self.running and not self.paused:
                    try:
                        data = q.get(timeout=0.5)
                    except queue.Empty:
                        continue
                    if rec.AcceptWaveform(data):
                        text = json.loads(rec.Result()).get("text", "")
                    else:
                        text = json.loads(rec.PartialResult()).get("partial", "")
                    if self.wake_phrase in normalize(text):
                        rec.Reset()
                        self._trigger()
            finally:
                self.mic.detach(q)

    def _trigger(self):
        now = time.monotonic()
        if now - self.last_trigger < self.cooldown:
            return
        self.last_trigger = now
        print("[WAKE] Mot clé détecté !")
        # Le traitement (réponse vocale, écoute) se fait hors du thread d'écoute.
        self.pause()
        threading.Thread(target=self.bus.emit, args=("wake_word_detected", {"source": "voice"}),
                         daemon=True).start()
