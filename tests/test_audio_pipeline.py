"""
Test de bout en bout de l'écoute, sans micro : Piper prononce « miroir magique » puis
une question, l'audio est injecté dans WakeWord et SpeechToText via un faux micro.
Ignoré si Vosk, Piper ou leurs modèles sont absents.
"""
import os
import queue
import threading
import time

import numpy as np
import pytest

from config import load_config, resolve_path
from core.event_bus import EventBus

vosk = pytest.importorskip("vosk")
piper = pytest.importorskip("piper")

CFG = load_config()
VOSK_PATH = resolve_path(CFG["models"]["vosk"])
VOICE_PATH = resolve_path(CFG["models"]["piper_voice"])
pytestmark = pytest.mark.skipif(
    not (os.path.isdir(VOSK_PATH) and os.path.exists(VOICE_PATH)), reason="modèles absents")


def speech(text, voice):
    audio = np.concatenate([c.audio_int16_array for c in voice.synthesize(text)])
    sr = voice.config.sample_rate
    # rééchantillonnage linéaire vers 16 kHz + silence avant / après
    n = int(len(audio) * 16000 / sr)
    audio = np.interp(np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio).astype(np.int16)
    pad = np.zeros(16000, np.int16)
    return np.concatenate([pad, audio, pad, pad])


class FakeMic:
    sample_rate = 16000

    def __init__(self):
        self.consumer = None

    def attach(self):
        self.consumer = queue.Queue()
        return self.consumer

    def detach(self, q):
        if self.consumer is q:
            self.consumer = None

    def feed(self, samples, timeout=5):
        deadline = time.time() + timeout
        while self.consumer is None and time.time() < deadline:
            time.sleep(0.01)
        for i in range(0, len(samples), 4000):
            self.consumer.put(samples[i:i + 4000].tobytes())


@pytest.fixture(scope="module")
def models():
    vosk.SetLogLevel(-1)
    return vosk.Model(VOSK_PATH), piper.PiperVoice.load(VOICE_PATH)


def test_wake_word_then_question(models):
    from audio.speech_to_text import SpeechToText
    from audio.wake_word import WakeWord

    model, voice = models
    bus, mic = EventBus(), FakeMic()
    woke, heard = threading.Event(), []
    bus.subscribe("wake_word_detected", lambda _: woke.set())
    bus.subscribe("speech_transcribed", heard.append)

    ww = WakeWord(bus, mic, model, "miroir magique", cooldown=0)
    ww.start()
    mic.feed(speech("Miroir magique.", voice))
    assert woke.wait(5), "mot clé non détecté"
    assert ww.paused

    stt = SpeechToText(bus, mic, model, timeout=5)
    stt.listen()
    mic.feed(speech("Comment est ma tenue ?", voice))
    stt.thread.join(10)
    ww.stop()
    assert heard and "tenue" in heard[0], heard


def test_wake_word_ignores_other_speech(models):
    from audio.wake_word import WakeWord

    model, voice = models
    bus, mic = EventBus(), FakeMic()
    woke = threading.Event()
    bus.subscribe("wake_word_detected", lambda _: woke.set())
    ww = WakeWord(bus, mic, model, "miroir magique", cooldown=0)
    ww.start()
    mic.feed(speech("Bonjour, il fait beau aujourd'hui à Cotonou.", voice))
    time.sleep(1.5)
    ww.stop()
    assert not woke.is_set()
