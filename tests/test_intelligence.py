from datetime import datetime

from intelligence.context_engine import ContextEngine
from intelligence.recommendation_engine import RecommendationEngine
from intelligence.style_engine import StyleEngine

FEATURES = {"presence_face": True, "outfit_visible": True, "dominant_color": "blue",
            "secondary_color": None, "brightness": "dark", "contrast": "low", "lighting": "ok"}


def ctx(month, hour, climate="temperate"):
    return ContextEngine(climate, clock=lambda: datetime(2026, month, 10, hour)).get_context()


def test_seasons():
    assert ctx(1, 9)["season"] == "winter"
    assert ctx(10, 9)["season"] == "autumn"
    assert ctx(1, 9, "tropical")["season"] == "harmattan"
    assert ctx(6, 9, "tropical")["season"] == "rainy"
    assert ctx(8, 9, "tropical")["season"] == "dry"
    assert ctx(11, 20)["time_of_day"] == "evening"


def test_color_rule_fires_with_named_color():
    # Bug d'origine : la vision renvoyait "#rrggbb" et ce conseil n'apparaissait jamais.
    result = StyleEngine(max_tips=5).analyze(FEATURES, ctx(10, 15))
    assert "bleu" in result["advice"]


def test_summary_is_french_and_agreed():
    result = StyleEngine().analyze(FEATURES, ctx(10, 15))
    assert result["summary"] == "votre tenue à dominante bleue est plutôt sombre, avec un contraste faible"
    for english in ("dark", "low", "autumn", "blue"):
        assert english not in result["summary"] + result["advice"]


def test_one_tip_per_category_and_limit():
    result = StyleEngine(max_tips=2).analyze(FEATURES, ctx(1, 20))
    assert len([s for s in result["advice"].split(". ") if s]) <= 3
    assert 0 < result["confidence"] <= 1


def test_clash_detected():
    f = dict(FEATURES, dominant_color="red", secondary_color="pink")
    assert "audacieuse" in StyleEngine().analyze(f, ctx(10, 15))["advice"]


def test_outfit_not_visible():
    result = StyleEngine().analyze(dict(FEATURES, outfit_visible=False), ctx(10, 15))
    assert "Reculez" in result["advice"]


def test_recommendation_without_face():
    result = RecommendationEngine().generate({"presence_face": False})
    assert result["confidence"] == 0.0
