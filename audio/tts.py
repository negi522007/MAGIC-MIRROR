"""
Synthèse vocale offline.

Moteurs essayés dans l'ordre de `backends` :
    piper    — Piper (ONNX, voix fr_FR-siwis-medium) : temps réel sur un Intel N100,
               ~60 Mo, maintenu. Moteur recommandé.
    coqui    — Coqui TTS (VITS). Coqui a fermé fin 2023 ; le paquet `TTS` n'est plus
               maintenu (le fork `coqui-tts` l'est). Lourd : PyTorch, ~2 Go.
    pyttsx3  — voix système (espeak), robotique mais sans dépendance lourde.

`speak()` est bloquant. Le texte est découpé en phrases : la phrase suivante est
synthétisée pendant que la précédente est jouée, ce qui réduit l'attente avant le
premier mot. Les phrases courtes et fréquentes (« Oui, je vous écoute. ») sont
gardées en cache.
"""

import os
import re
import threading

import numpy as np

SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+")
CACHE_MAX_CHARS = 60
CACHE_MAX_ITEMS = 32


class TTSService:
    def __init__(self, audio_state, backends=("piper", "coqui", "pyttsx3"),
                 piper_voice=None, coqui_model="tts_models/fr/css10/vits",
                 output_device=None, length_scale=1.0, enabled=True):
        self.audio_state = audio_state
        self.output_device = output_device
        self.length_scale = length_scale
        self.backend = None
        self.engine = None
        self._sample_rate = None
        self._cache = {}
        self._lock = threading.Lock()  # une seule phrase à la fois

        if not enabled:
            print("[TTS] Désactivé (mode texte)")
            return

        loaders = {
            "piper": lambda: self._load_piper(piper_voice),
            "coqui": lambda: self._load_coqui(coqui_model),
            "pyttsx3": self._load_pyttsx3,
        }
        for name in backends:
            loader = loaders.get(name)
            if loader is None:
                continue
            try:
                loader()
                self.backend = name
                print(f"[TTS] ✅ Moteur : {name}")
                return
            except Exception as e:
                print(f"[TTS] ⚠ {name} indisponible : {e}")
        print("[TTS] ❌ Aucun moteur disponible — les réponses seront seulement affichées")

    # ── chargement ──
    def _load_piper(self, voice_path):
        if not voice_path or not os.path.exists(voice_path):
            raise FileNotFoundError(f"voix Piper absente ({voice_path}) — lancer scripts/install.sh")
        import sounddevice  # noqa: F401  (lecture ; lève OSError si PortAudio manque)
        from piper import PiperVoice
        self.engine = PiperVoice.load(voice_path)
        self._sample_rate = self.engine.config.sample_rate

    def _load_coqui(self, model_name):
        import sounddevice  # noqa: F401
        from TTS.api import TTS
        self.engine = TTS(model_name, progress_bar=False)
        self._sample_rate = self.engine.synthesizer.output_sample_rate

    def _load_pyttsx3(self):
        import pyttsx3
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 160)
        for voice in self.engine.getProperty("voices"):
            if "fr" in voice.id.lower() or "french" in (voice.name or "").lower():
                self.engine.setProperty("voice", voice.id)
                break

    # ── synthèse ──
    def synthesize(self, text):
        """Texte → (échantillons int16, fréquence). Pas pour pyttsx3."""
        cached = self._cache.get(text)
        if cached is not None:
            return cached
        if self.backend == "piper":
            audio = self._synth_piper(text)
        elif self.backend == "coqui":
            wav = np.asarray(self.engine.tts(text), dtype=np.float32)
            audio = (np.clip(wav, -1, 1) * 32767).astype(np.int16)
        else:
            raise RuntimeError("pas de moteur de synthèse")
        result = (audio, self._sample_rate)
        if len(text) <= CACHE_MAX_CHARS and len(self._cache) < CACHE_MAX_ITEMS:
            self._cache[text] = result
        return result

    def _synth_piper(self, text):
        # piper-tts ≥ 1.3 (OHF-Voice/piper1-gpl) : synthesize() renvoie des AudioChunk.
        try:
            from piper import SynthesisConfig
        except ImportError:
            SynthesisConfig = None
        if SynthesisConfig is not None:
            cfg = SynthesisConfig(length_scale=self.length_scale)
            chunks = [c.audio_int16_array for c in self.engine.synthesize(text, syn_config=cfg)]
            return np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.int16)
        # piper-tts 1.2 (ancienne API rhasspy/piper)
        raw = b"".join(self.engine.synthesize_stream_raw(text, length_scale=self.length_scale))
        return np.frombuffer(raw, dtype=np.int16)

    def preload(self, phrases):
        """Met en cache des phrases fréquentes (appelé au démarrage, en arrière-plan)."""
        if self.backend not in ("piper", "coqui"):
            return
        for phrase in phrases:
            try:
                self.synthesize(phrase)
            except Exception as e:
                print(f"[TTS] Préchargement impossible : {e}")
                return

    # ── lecture ──
    def speak(self, text):
        text = (text or "").strip()
        if not text:
            return
        if self.backend is None:
            print(f"[TTS] (muet) {text}")
            return
        with self._lock:
            self.audio_state.tts_speaking = True
            try:
                if self.backend == "pyttsx3":
                    self.engine.say(text)
                    self.engine.runAndWait()
                else:
                    self._speak_pipelined(text)
            except Exception as e:
                print(f"[TTS] Erreur : {e}")
            finally:
                self.audio_state.tts_speaking = False

    def _speak_pipelined(self, text):
        import sounddevice as sd
        sentences = [s for s in SENTENCE_SPLIT.split(text) if s.strip()] or [text]
        for sentence in sentences:
            audio, sr = self.synthesize(sentence)   # pendant ce temps, la phrase précédente joue
            sd.wait()
            if audio.size:
                sd.play(audio, sr, device=self.output_device)
        sd.wait()
