import time
import sys
sys.path.append("intelligence")
sys.path.append("core")
sys.path.append("ai")
from event_bus import EventBus
from state_manager import StateManager

from llm_interface import LLMInterface

class CameraStub:
    def get_frame(self):
        return "fake_frame"

class FaceDetectorStub:
    def detect_face(self, frame):
        return True

class VisualFeaturesStub:
    def __init__(self, face_detector):
        self.face_detector = face_detector

    def extract(self, frame):
        return {
            "presence_face": self.face_detector.detect_face(frame),
            "dominant_color": "bleu",
            "brightness": "moyen",
            "contrast": "low"
        }

class RecommendationEngineStub:
    def generate(self, features):
        return {
            "summary": f"Tenue détectée: couleur {features['dominant_color']}",
            "advice": "Ajouter un accessoire clair améliorerait l'équilibre.",
            "confidence": 0.8
        }

class TTSStub:
    def speak(self, text):
        print(f"TTS: {text}")

class OverlayStub:
    def display_text(self, text):
        print(f"UI: {text}")

class AppControllerStub:
    def __init__(self):
        self.bus = EventBus()
        self.state = StateManager()

        self.camera = CameraStub()
        self.face_detector = FaceDetectorStub()
        self.visual_features = VisualFeaturesStub(self.face_detector)
        self.recommendation_engine = RecommendationEngineStub()

        self.tts = TTSStub()
        self.overlay = OverlayStub()

        self.llm = LLMInterface(self.bus)

        self._setup_events()

    def _setup_events(self):
        self.bus.subscribe("wake_word_detected", self.on_wake_word)
        self.bus.subscribe("speech_transcribed", self.on_speech)
        self.bus.subscribe("style_request", self.on_style_request)
        self.bus.subscribe("recommendation_ready", self.on_recommendation)
        self.bus.subscribe("llm_response", self.on_llm_response)

    def on_wake_word(self, data):
        print("Wake word détecté")
        self.state.set_state("listening")
        self.tts.speak("Oui, je vous écoute.")

    def on_speech(self, text):
        print(f"Speech: {text}")
        self.llm.process(text)

    def on_style_request(self, data):
        print("Analyse du style demandée")
        frame = self.camera.get_frame()
        features = self.visual_features.extract(frame)
        recommendation = self.recommendation_engine.generate(features)
        self.bus.emit("recommendation_ready", recommendation)

    def on_recommendation(self, recommendation):
        self.llm.on_recommendation(recommendation)

    def on_llm_response(self, text):
        print(f"LLM: {text}")
        self.overlay.display_text(text)
        self.tts.speak(text)
        self.state.set_state("idle")

    def run_test(self):
        self.bus.emit("wake_word_detected")
        time.sleep(0.5)

        self.bus.emit("speech_transcribed", "Bonjour, ça va ?")
        time.sleep(0.5)

        self.bus.emit("speech_transcribed", "Que penses-tu de ma tenue ?")
        time.sleep(0.5)

if __name__ == "__main__":
    app = AppControllerStub()
    app.run_test()