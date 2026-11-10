"""
Moteur de recommandation : caractéristiques visuelles + contexte + règles de style.
"""
from intelligence.context_engine import ContextEngine
from intelligence.style_engine import StyleEngine


class RecommendationEngine:
    def __init__(self, climate="temperate", context_engine=None, style_engine=None):
        self.context_engine = context_engine or ContextEngine(climate=climate)
        self.style_engine = style_engine or StyleEngine()

    def generate(self, visual_features):
        context = self.context_engine.get_context()
        if not visual_features.get("presence_face"):
            return {
                "summary": "je ne vois personne devant le miroir",
                "advice": "Placez-vous face au miroir pour une analyse de style.",
                "confidence": 0.0,
                "features": visual_features,
                "context": context,
            }
        result = self.style_engine.analyze(visual_features, context)
        result["context"] = context
        return result
