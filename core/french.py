"""
Dates et heures en français, sans dépendre de la locale du système
(`strftime("%A")` renvoie « Tuesday » sur une installation en anglais).
"""

DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
          "août", "septembre", "octobre", "novembre", "décembre"]


def format_date(dt):
    """« mardi 10 novembre 2026 »"""
    day = "1er" if dt.day == 1 else str(dt.day)
    return f"{DAYS[dt.weekday()]} {day} {MONTHS[dt.month - 1]} {dt.year}"


def spoken_time(dt):
    """« 14 heures 5 » : forme que la synthèse vocale lit correctement."""
    word = "heure" if dt.hour <= 1 else "heures"
    text = f"{dt.hour} {word}"
    return f"{text} {dt.minute}" if dt.minute else text


def greeting(dt):
    if 5 <= dt.hour < 12:
        return "Bonjour"
    if 12 <= dt.hour < 18:
        return "Bon après-midi"
    return "Bonsoir"
