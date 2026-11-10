"""
Flux micro unique, partagé entre le mot clé et la transcription.

Avant, WakeWord et SpeechToText ouvraient chacun leur propre flux sur le même
périphérique, ce qui échouait (« device busy ») ou nécessitait des pauses fragiles.
Ici un seul `RawInputStream` reste ouvert et envoie les blocs audio au consommateur
actif (au plus un à la fois). Les blocs captés pendant que le miroir parle sont
jetés.
"""

import queue
import threading

import sounddevice as sd


class Microphone:
    def __init__(self, audio_state, sample_rate=16000, block_size=4000, device_id=None):
        self.audio_state = audio_state
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.device_id = device_id
        self._stream = None
        self._consumer = None
        self._lock = threading.Lock()

    def start(self):
        kwargs = dict(samplerate=self.sample_rate, blocksize=self.block_size,
                      dtype="int16", channels=1, callback=self._callback)
        if self.device_id is not None:
            kwargs["device"] = self.device_id
        self._stream = sd.RawInputStream(**kwargs)
        self._stream.start()
        name = sd.query_devices(self.device_id if self.device_id is not None else sd.default.device[0])["name"]
        print(f"[MIC] ✅ Micro ouvert : {name}")

    def stop(self):
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def attach(self):
        """Devient le consommateur actif ; renvoie une file de blocs audio (bytes)."""
        q = queue.Queue(maxsize=200)
        with self._lock:
            self._consumer = q
        return q

    def detach(self, q):
        with self._lock:
            if self._consumer is q:
                self._consumer = None

    def _callback(self, indata, frames, time_info, status):
        if status:
            print(f"[MIC] {status}")
        if self.audio_state.mic_muted():
            return
        consumer = self._consumer
        if consumer is not None:
            try:
                consumer.put_nowait(bytes(indata))
            except queue.Full:
                pass  # consommateur trop lent : on perd ce bloc plutôt que de bloquer
