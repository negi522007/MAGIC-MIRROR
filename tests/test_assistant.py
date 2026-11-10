from datetime import datetime

from ai.llm_interface import LLMInterface
from ai.local_llm import LocalLLM
from core.event_bus import EventBus

CLOCK = lambda: datetime(2026, 11, 10, 14, 5)  # noqa: E731


def make(llm=None):
    bus = EventBus()
    out = {"responses": [], "style": []}
    bus.subscribe("llm_response", out["responses"].append)
    bus.subscribe("style_request", out["style"].append)
    return bus, LLMInterface(bus, llm, clock=CLOCK), out


def test_intents():
    _, a, _ = make()
    cases = {
        "comment est ma tenue": "style",
        "bonjour tu trouves que je suis bien habillé": "style",
        "quelle heure est-il": "time",
        "quel jour sommes-nous": "date",
        "salut": "greeting",
        "merci beaucoup": "thanks",
        "qui es-tu": "identity",
        "quel temps fait-il demain": "weather",
        "raconte une blague": "general",
        "": None,
    }
    for text, intent in cases.items():
        assert a.detect_intent(text) == intent, text


def test_time_and_date_in_french():
    _, a, _ = make()
    assert a.respond("time") == "Il est 14 heures 5."
    assert a.respond("date") == "Nous sommes le mardi 10 novembre 2026."


def test_style_request_goes_through_bus():
    bus, a, out = make()
    a.process("que penses-tu de mon look")
    assert out["style"] and not out["responses"]


def test_recommendation_template_without_llm():
    bus, a, out = make()
    bus.emit("recommendation_ready", {
        "summary": "votre tenue à dominante bleue est équilibrée, avec un contraste modéré",
        "advice": "Des accents beiges compléteraient bien le bleu.",
        "confidence": 0.8, "features": {"outfit_visible": True}})
    assert out["responses"] == ["Je trouve que votre tenue à dominante bleue est équilibrée, "
                                "avec un contraste modéré. Des accents beiges compléteraient bien le bleu."]


def test_no_face_message():
    bus, a, out = make()
    bus.emit("recommendation_ready", {"summary": "je ne vois personne devant le miroir",
                                      "advice": "Placez-vous face au miroir.", "confidence": 0.0,
                                      "features": {}})
    assert out["responses"] == ["Je ne vois personne devant le miroir. Placez-vous face au miroir."]


class FakeLLM:
    ready = True

    def __init__(self, answer):
        self.answer, self.calls = answer, []

    def generate(self, system, user):
        self.calls.append(user)
        return self.answer


def test_general_question_uses_llm_and_falls_back():
    llm = FakeLLM("Une blague ? Pourquoi le miroir sourit-il toujours ?")
    _, a, out = make(llm)
    a.process("raconte une blague")
    assert out["responses"] == [llm.answer]
    llm.answer = None
    a.process("raconte une blague")
    assert "style" in out["responses"][-1]


def test_llm_output_cleaning():
    clean = LocalLLM._clean
    assert clean("<think>hmm</think>**Superbe** tenue ! 😀") == "Superbe tenue !"
    assert clean("Très belle tenue. Le bleu vous va bien. Et puis le") == \
        "Très belle tenue. Le bleu vous va bien."
    assert clean("") is None


def test_missing_model_is_not_fatal(tmp_path):
    llm = LocalLLM(str(tmp_path / "absent.gguf"))
    llm.load_async()
    assert not llm.ready and llm.generate("s", "u") is None


def test_style_rephrased_only_when_enabled():
    rec = {"summary": "votre tenue à dominante bleue est équilibrée, avec un contraste modéré",
           "advice": "Des accents beiges compléteraient bien le bleu.", "confidence": 0.8,
           "features": {"outfit_visible": True}}
    llm = FakeLLM("Le bleu vous va à merveille.")
    bus, a, out = make(llm)
    a.on_recommendation(rec)
    assert out["responses"][-1].startswith("Je trouve que") and not llm.calls
    a.rephrase_style = True
    a.on_recommendation(rec)
    assert out["responses"][-1] == "Le bleu vous va à merveille."
