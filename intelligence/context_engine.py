"""
Contexte offline : saison et moment de la journée, déduits de l'horloge locale.

`climate` :
    "temperate" — hiver / printemps / été / automne (hémisphère nord)
    "tropical"  — calendrier du sud du Bénin : grande saison sèche (avec harmattan
                  de décembre à février), grande saison des pluies (avril–juillet),
                  petite saison sèche (août), petite saison des pluies (sept.–nov.)
"""

from datetime import datetime

SEASON_LABELS = {
    "winter": "l'hiver",
    "spring": "le printemps",
    "summer": "l'été",
    "autumn": "l'automne",
    "harmattan": "l'harmattan",
    "dry": "la saison sèche",
    "rainy": "la saison des pluies",
}

TIME_LABELS = {
    "morning": "ce matin",
    "afternoon": "cet après-midi",
    "evening": "ce soir",
    "night": "cette nuit",
}

# Profil de température approximatif associé à chaque saison.
SEASON_TEMPERATURE = {
    "winter": "cold",
    "spring": "mild",
    "summer": "hot",
    "autumn": "mild",
    "harmattan": "dry_hot",
    "dry": "hot",
    "rainy": "humid",
}


class ContextEngine:
    def __init__(self, climate="temperate", clock=None):
        self.climate = climate
        self._clock = clock or datetime.now

    def get_context(self):
        now = self._clock()
        season = self._get_season(now.month)
        time_of_day = self._get_time_of_day(now.hour)
        return {
            "season": season,
            "season_label": SEASON_LABELS[season],
            "temperature": SEASON_TEMPERATURE[season],
            "time_of_day": time_of_day,
            "time_label": TIME_LABELS[time_of_day],
        }

    def _get_season(self, month):
        if self.climate == "tropical":
            if month in (12, 1, 2):
                return "harmattan"
            if month == 3 or month == 8:
                return "dry"
            return "rainy"  # avril–juillet, septembre–novembre
        if month in (12, 1, 2):
            return "winter"
        if month in (3, 4, 5):
            return "spring"
        if month in (6, 7, 8):
            return "summer"
        return "autumn"

    @staticmethod
    def _get_time_of_day(hour):
        if 5 <= hour < 12:
            return "morning"
        if 12 <= hour < 18:
            return "afternoon"
        if 18 <= hour < 22:
            return "evening"
        return "night"
