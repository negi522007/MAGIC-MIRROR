"""
Assistant : détection d'intention + réponses.

- Les intentions simples (heure, date, salutations...) sont traitées par des règles :
  réponse instantanée, fiable, aucun calcul.
- « Comment est ma tenue ? » publie `style_request` ; le contrôleur renvoie
  `recommendation_ready`, que l'assistant met en phrase avec un gabarit (ou, si
  `llm.rephrase_style` est activé, fait reformuler par le LLM local).
- Les questions libres vont au LLM local s'il est prêt, sinon à une réponse de repli.

Toutes les réponses finissent en `llm_response` (texte à afficher et à lire).
"""

import unicodedata
from datetime import datetime

from core.french import format_date, greeting, spoken_time

SYSTEM_PROMPT = (
    "Tu es le miroir magique de TEKBOT, un assistant de style vestimentaire bienveillant "
    "et élégant. Tu réponds toujours en français, en une ou deux phrases courtes, sans "
    "liste, sans emoji et sans mise en forme, car ta réponse est lue à voix haute. "
    "Tu fonctionnes hors ligne : tu n'as accès ni à internet, ni à la météo, ni aux actualités."
)

STYLE_PROMPT = (
    "Voici l'analyse de la tenue de la personne devant toi : {summary}. Conseils retenus : "
    "{advice} Reformule ces informations pour la personne, en deux phrases chaleureuses "
    "maximum, sans rien inventer d'autre."
)

INTENT_KEYWORDS = [
    # (intention, mots-clés sans accents) — l'ordre compte : la première trouvée gagne.
    ("style", ["tenue", "habill", "style", "apparence", "look", "vetement", "habit",
               "je porte", "comment je suis", "je suis comment", "de quoi j'ai l'air",
               "suis-je", "suis je", "comment tu me trouve", "elegant", "tu me trouve"]),
    ("time", ["quelle heure", "l'heure", "il est quelle", "heure est"]),
    ("date", ["quel jour", "la date", "on est le", "quelle date", "nous sommes le"]),
    ("weather", ["meteo", "temps fait", "pleuvoir", "pluie", "temperature"]),
    ("identity", ["qui es-tu", "qui es tu", "tu es qui", "ton nom", "t'appelle", "qui est tu"]),
    ("help", ["aide", "sais faire", "peux faire", "sais-tu faire", "fonctionne"]),
    ("thanks", ["merci"]),
    ("goodbye", ["au revoir", "bonne nuit", "a plus", "a bientot", "ciao", "bye"]),
    ("howareyou", ["ca va", "comment vas", "tu vas bien", "vas-tu"]),
    ("greeting", ["bonjour", "salut", "bonsoir", "coucou", "hello", "bonne journee"]),
]


def normalize(text):
    text = unicodedata.normalize("NFD", (text or "").lower().replace("’", "'"))
    return "".join(c for c in text if unicodedata.category(c) != "Mn").strip()


class LLMInterface:
    def __init__(self, bus, llm=None, clock=None, rephrase_style=False):
        self.bus = bus
        self.llm = llm
        self.rephrase_style = rephrase_style
        self._clock = clock or datetime.now
        self.bus.subscribe("recommendation_ready", self.on_recommendation)

    # ── entrée ──
    def process(self, user_input):
        intent = self.detect_intent(user_input)
        print(f"[ASSISTANT] Intention : {intent}")
        if intent == "style":
            self.bus.emit("style_request", {"query": user_input})
            return
        self.bus.emit("llm_response", self.respond(intent, user_input))

    def detect_intent(self, user_input):
        text = normalize(user_input)
        if not text:
            return None
        for intent, keywords in INTENT_KEYWORDS:
            if any(k in text for k in keywords):
                return intent
        return "general"

    def respond(self, intent, user_input=""):
        now = self._clock()
        if intent == "time":
            return f"Il est {spoken_time(now)}."
        if intent == "date":
            return f"Nous sommes le {format_date(now)}."
        if intent == "greeting":
            return f"{greeting(now)} ! Demandez-moi « comment est ma tenue ? » et je vous donne mon avis."
        if intent == "thanks":
            return "Avec plaisir !"
        if intent == "goodbye":
            return "À bientôt, passez une belle journée !" if now.hour < 18 else "Bonne soirée, à bientôt !"
        if intent == "howareyou":
            return "Je vais très bien, merci ! Et vous, prêt pour une analyse de style ?"
        if intent == "identity":
            return "Je suis le miroir magique de TEKBOT, votre conseiller de style personnel."
        if intent == "help":
            return ("Je peux analyser votre tenue, vous donner l'heure et la date. "
                    "Dites « miroir magique », puis « comment est ma tenue ? ».")
        if intent == "weather":
            return "Je fonctionne hors ligne, je n'ai donc pas accès à la météo."
        if intent is None:
            return "Je n'ai pas bien entendu, pouvez-vous répéter ?"

        # Question libre
        if self.llm is not None and self.llm.ready:
            answer = self.llm.generate(SYSTEM_PROMPT, user_input)
            if answer:
                return answer
        return "Je suis spécialisé dans le style : demandez-moi ce que je pense de votre tenue !"

    # ── style ──
    def on_recommendation(self, recommendation):
        self.bus.emit("llm_response", self.format_style_response(recommendation))

    def format_style_response(self, recommendation):
        summary = recommendation.get("summary", "")
        advice = recommendation.get("advice", "")
        confidence = recommendation.get("confidence", 0.7)
        features = recommendation.get("features") or {}

        # L'analyse n'a pas pu se faire : on transmet le message tel quel.
        if confidence <= 0.3 or not features.get("outfit_visible", False):
            sep = " " if summary.rstrip().endswith((".", "!", "?")) else ". "
            return _sentence(f"{summary}{sep}{advice}")

        if self.rephrase_style and self.llm is not None and self.llm.ready:
            answer = self.llm.generate(SYSTEM_PROMPT, STYLE_PROMPT.format(summary=summary, advice=advice))
            if answer:
                return answer

        tone = "Je trouve que" if confidence > 0.75 else "Selon moi,"
        return _sentence(f"{tone} {summary}. {advice}")


def _sentence(text):
    text = " ".join(text.split())
    return text[:1].upper() + text[1:] if text else text
