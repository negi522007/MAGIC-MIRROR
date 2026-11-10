import sys
sys.path.append("core")
sys.path.append("audio")
sys.path.append("ai")
sys.path.append("vision")
sys.path.append("intelligence")

from event_bus import EventBus
from state_manager import StateManager

from wake_word import WakeWord
from speech_to_text import SpeechToText
from tts import TTS
from audio_state import AudioState

from llm_interface import LLMInterface

from camera import Camera
from face_detector import FaceDetector
from visual_features import VisualFeatures

from recommendation_engine import RecommendationEngine
from context_engine import ContextEngine

import time

# ---------------- Setup ----------------
bus = EventBus()
state = StateManager()
audio_state = AudioState()

camera = Camera()
face_detector = FaceDetector()
visual_features = VisualFeatures(face_detector)

context_engine = ContextEngine()
recommendation_engine = RecommendationEngine()

tts = TTS(audio_state)
llm = LLMInterface(recommendation_engine)

wake_word = WakeWord(bus)
stt = SpeechToText(bus)

# ---------------- Event handlers ----------------
def on_wake_word(data):
    print("[EVENT] Wake word détecté !")
    state.set_state("listening")
    tts.speak("Oui, je vous écoute.")
    stt.listen()

def on_speech(text):
    print(f"[EVENT] Speech reçu: {text}")
    llm_response = llm.generate(text)
    tts.speak(llm_response)
    state.set_state("idle")

bus.subscribe("wake_word_detected", on_wake_word)
bus.subscribe("speech_transcribed", on_speech)

# ---------------- Start test ----------------
print("Test Magic Mirror sans UI")
wake_word.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Arrêt du test")