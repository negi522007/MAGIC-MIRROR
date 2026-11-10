"""
Contrôleur central : crée les modules à partir de la configuration et orchestre
le cycle d'une interaction.

    mot clé ──► listening : « Oui ? » puis écoute de la question
    question ─► processing : intention → réponse (ou analyse de style)
    réponse ──► speaking : affichage + voix
            ──► idle : reprise de l'écoute du mot clé

Le travail lent (synthèse vocale, LLM, analyse) ne tourne jamais dans le thread Tk
ni dans le thread du micro.
"""

import threading

from config import resolve_path
from core.event_bus import EventBus
from core.state_manager import MirrorState, StateManager
from ai.llm_interface import LLMInterface
from ai.local_llm import LocalLLM
from audio.audio_state import AudioState
from audio.tts import TTSService
from intelligence.recommendation_engine import RecommendationEngine
from vision.camera import Camera
from vision.face_detector import FaceDetector
from vision.presence_monitor import PresenceMonitor
from vision.visual_features import VisualFeatures

ACK_PHRASE = "Oui, je vous écoute."
NOT_HEARD_PHRASE = "Je n'ai rien entendu. Redites « miroir magique » quand vous voulez."

# Raccourcis clavier (utiles sans micro, ou pour une démonstration).
KEY_COMMANDS = {
    "s": "comment est ma tenue",
    "h": "quelle heure est-il",
    "d": "quel jour sommes-nous",
    "b": "bonjour",
    "a": "que sais-tu faire",
}


class AppController:
    def __init__(self, config, audio_enabled=True):
        self.config = config
        self.bus = EventBus()
        self.state = StateManager(self.bus)
        self.audio_state = AudioState()

        cam_cfg, vis_cfg, ui_cfg = config["camera"], config["vision"], config["ui"]
        models, llm_cfg, audio_cfg = config["models"], config["llm"], config["audio"]

        # ── Vision ──
        self.camera = Camera(cam_cfg["index"], cam_cfg["width"], cam_cfg["height"], cam_cfg["fps"])
        self.face_detector = FaceDetector(resolve_path(models["face"]), vis_cfg["detect_width"])
        self.visual_features = VisualFeatures()
        self.presence = PresenceMonitor(self.bus, self.camera, self.face_detector,
                                        vis_cfg["detect_interval"], vis_cfg["idle_detect_interval"])

        # ── Intelligence + IA ──
        self.recommendation_engine = RecommendationEngine(climate=config["context"]["climate"])
        self.local_llm = None
        if llm_cfg.get("enabled"):
            self.local_llm = LocalLLM(resolve_path(models["llm"]), llm_cfg["n_threads"],
                                      llm_cfg["n_ctx"], llm_cfg["max_tokens"],
                                      llm_cfg["temperature"], llm_cfg["timeout"])
        self.llm = LLMInterface(self.bus, self.local_llm,
                                rephrase_style=llm_cfg.get("rephrase_style", False))

        # ── Audio ──
        self.tts = TTSService(self.audio_state, config["tts"]["backends"],
                              piper_voice=resolve_path(models["piper_voice"]),
                              coqui_model=models.get("coqui"),
                              output_device=audio_cfg.get("output_device_id"),
                              length_scale=config["tts"].get("length_scale", 1.0),
                              enabled=audio_enabled)
        self.mic = self.wake_word = self.stt = None
        if audio_enabled:
            self._init_listening(config)

        # ── UI (import tardif : permet de tester le reste sans affichage) ──
        from ui.assistant_overlay import AssistantOverlay
        from ui.mirror_window import MirrorWindow
        from ui.style_card import StyleCard
        self.ui = MirrorWindow(self.bus, self.camera, fullscreen=ui_cfg["fullscreen"],
                               fps=ui_cfg["fps"], sleep_after=ui_cfg["sleep_after"],
                               show_face_box=ui_cfg["show_face_box"])
        self.overlay = AssistantOverlay(self.bus, self.ui, ui_cfg["overlay_fade_delay"],
                                        ui_cfg["typing_speed"])
        self.style_card = StyleCard(self.bus, self.ui)
        self.ui.on_close = self.shutdown
        self.ui.status_provider = self._status_line
        self.ui.bind_key("space", lambda: self._spawn(self.on_wake_word, {"source": "keyboard"}))
        for key, text in KEY_COMMANDS.items():
            self.ui.bind_key(key, lambda t=text: self._spawn(self.handle_text, t))

        self._setup_events()

    def _init_listening(self, config):
        """Micro + Vosk. En cas d'échec, le miroir reste utilisable au clavier."""
        try:
            import vosk
            from audio.microphone import Microphone
            from audio.speech_to_text import SpeechToText
            from audio.wake_word import WakeWord

            vosk.SetLogLevel(-1)
            model_path = resolve_path(config["models"]["vosk"])
            model = vosk.Model(model_path)  # chargé une seule fois, partagé
            a = config["audio"]
            self.mic = Microphone(self.audio_state, a["sample_rate"], a["block_size"], a["device_id"])
            w = config["wake_word"]
            self.wake_word = WakeWord(self.bus, self.mic, model, w["phrase"], w["cooldown"],
                                      w["use_grammar"])
            self.stt = SpeechToText(self.bus, self.mic, model, timeout=config["stt"]["timeout"])
        except Exception as e:
            print(f"[AUDIO] ⚠ Écoute vocale indisponible ({e}). Utilisez le clavier : "
                  "Espace = mot clé, S = analyse de tenue.")
            self.mic = self.wake_word = self.stt = None

    def _setup_events(self):
        self.bus.subscribe("wake_word_detected", self.on_wake_word)
        self.bus.subscribe("speech_transcribed", self.on_speech)
        self.bus.subscribe("stt_stopped", self.on_stt_stopped)
        self.bus.subscribe("style_request", self.on_style_request)
        self.bus.subscribe("llm_response", self.on_llm_response)

    @staticmethod
    def _spawn(fn, *args):
        threading.Thread(target=fn, args=args, daemon=True).start()

    # ── cycle d'interaction ──
    def on_wake_word(self, data=None):
        if not self.state.try_begin(MirrorState.IDLE, MirrorState.LISTENING):
            return
        if self.wake_word:
            self.wake_word.pause()
        self.tts.speak(ACK_PHRASE)
        if self.stt:
            self.stt.listen()
        else:
            # Sans micro : on reste à l'écoute du clavier (touches S, H, D...).
            print("[CTRL] Pas de micro : choisissez une question au clavier (S, H, D, B, A)")

    def handle_text(self, text):
        """Question tapée au clavier : même traitement qu'une phrase reconnue."""
        if self.state.current_state == MirrorState.LISTENING and self.stt:
            self.stt.stop()
        self.bus.emit("speech_transcribed", text)

    def on_speech(self, text):
        if not self.state.set_state(MirrorState.PROCESSING):
            return
        self._spawn(self.llm.process, text)

    def on_stt_stopped(self, _):
        if self.state.current_state == MirrorState.LISTENING:
            self.bus.emit("llm_response", NOT_HEARD_PHRASE)

    def on_style_request(self, _):
        frame, faces = self.presence.detect_now()
        if frame is None:
            self.bus.emit("llm_response", "Je ne vois rien : la caméra n'est pas disponible.")
            return
        features = self.visual_features.extract_features(frame, faces[0] if faces else None)
        recommendation = self.recommendation_engine.generate(features)
        self.bus.emit("recommendation_ready", recommendation)

    def on_llm_response(self, text):
        self.state.set_state(MirrorState.SPEAKING, force=True)
        self.tts.speak(text)
        self.state.set_state(MirrorState.IDLE)
        if self.wake_word:
            self.wake_word.resume()

    # ── démarrage / arrêt ──
    def _status_line(self):
        parts = ["100 % hors ligne"]
        if self.local_llm is None or self.local_llm.status in ("absent", "error"):
            parts.append("réponses par règles")
        elif self.local_llm.status == "loading":
            parts.append("IA locale : chargement…")
        else:
            parts.append("IA locale prête")
        parts.append(f"voix : {self.tts.backend or 'texte seul'}")
        if not self.wake_word:
            parts.append("Espace = mot clé · S = tenue · Échap = quitter")
        return "  ·  ".join(parts)

    def run(self):
        print("[CTRL] Magic Mirror démarré")
        self.camera.start()
        self.presence.start()
        if self.local_llm:
            self.local_llm.load_async()
        self._spawn(self.tts.preload, [ACK_PHRASE, NOT_HEARD_PHRASE])
        if self.mic:
            try:
                self.mic.start()
                self.wake_word.start()
            except Exception as e:
                print(f"[AUDIO] ⚠ Micro inaccessible ({e}) — utilisez le clavier.")
                self.mic = self.wake_word = self.stt = None
        self.bus.emit("state_changed", MirrorState.IDLE)
        self.ui.start()

    def shutdown(self):
        print("[CTRL] Arrêt...")
        if self.wake_word:
            self.wake_word.stop()
        if self.stt:
            self.stt.stop()
        if self.mic:
            self.mic.stop()
        self.presence.stop()
        self.camera.stop()
