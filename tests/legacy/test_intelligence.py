import sys
sys.path.append("intelligence")
from recommendation_engine import RecommendationEngine

engine = RecommendationEngine()

mock_features = {
    "presence_face": True,
    "dominant_color": "black",
    "brightness": "dark",
    "contrast": "low"
}

result = engine.generate(mock_features)

print(result)