"""
Règles stylistiques : caractéristiques de la tenue + contexte → conseils pondérés.

Le résultat est volontairement court (2 conseils) car il est lu à voix haute.
Les conseils d'une même catégorie (couleur, contraste, saison...) ne se cumulent pas.
"""

from core.colors import COLOR_NAMES, COLOR_NAMES_FEM

BRIGHTNESS_LABELS = {"dark": "plutôt sombre", "medium": "équilibrée", "light": "plutôt claire"}
CONTRAST_LABELS = {"low": "faible", "medium": "modéré", "high": "fort"}

COLOR_ADVICE = {
    "blue": ("Des accents beiges, camel ou marron compléteraient bien le bleu.", 0.75),
    "red": ("Des tons neutres comme le blanc, le gris ou le marine équilibreraient le rouge.", 0.75),
    "green": ("Des teintes terreuses, beige ou marron, s'associent harmonieusement au vert.", 0.7),
    "white": ("Un accessoire de couleur vive ferait ressortir votre tenue blanche.", 0.7),
    "black": ("Une touche de couleur vive, une écharpe ou un bijou, dynamiserait le noir.", 0.8),
    "gray": ("Le gris se marie avec presque tout : osez une couleur franche en accent.", 0.7),
    "beige": ("Le beige gagne à être relevé par du blanc, du marine ou du bordeaux.", 0.7),
    "brown": ("Le marron s'accorde bien avec le crème, le vert olive ou le bleu.", 0.7),
    "orange": ("Avec l'orange, restez sur des neutres ou un bleu pour l'équilibre.", 0.7),
    "yellow": ("Le jaune ressort bien avec du gris, du blanc ou du bleu marine.", 0.7),
    "turquoise": ("Le turquoise s'accorde avec le blanc, le beige ou le corail.", 0.7),
    "purple": ("Le violet se marie bien avec le gris, le blanc ou une touche dorée.", 0.7),
    "pink": ("Le rose se marie très bien avec le gris, le blanc ou le marine.", 0.7),
}

# Associations dominante + secondaire jugées délicates.
CLASHES = {
    frozenset(("red", "pink")), frozenset(("red", "orange")), frozenset(("green", "red")),
    frozenset(("purple", "orange")), frozenset(("brown", "black")),
}

SEASON_ADVICE = {
    "summer": ("Des matières légères et respirantes comme le lin conviennent à la saison.", 0.6),
    "winter": ("Superposer les couches améliorerait à la fois le confort et le style.", 0.75),
    "spring": ("Les couleurs pastel et une veste légère sont idéales au printemps.", 0.55),
    "autumn": ("Les tons chauds, bordeaux, moutarde ou camel, sont parfaits pour l'automne.", 0.6),
    "harmattan": ("Avec l'harmattan, une couche légère et des tissus couvrants protègent de la poussière.", 0.65),
    "dry": ("Privilégiez le coton et le lin, clairs et amples, contre la chaleur.", 0.6),
    "rainy": ("Pensez à des matières qui sèchent vite et à des chaussures adaptées à la pluie.", 0.6),
}

TIME_ADVICE = {
    "morning": ("Des touches fraîches et dynamiques correspondent bien à l'énergie du matin.", 0.5),
    "evening": ("Des pièces plus raffinées ou plus sombres s'accordent bien avec la soirée.", 0.6),
    "night": ("Pour une sortie de nuit, une pièce brillante ou satinée fera la différence.", 0.5),
}


class StyleEngine:
    def __init__(self, max_tips=2):
        self.max_tips = max_tips

    def analyze(self, features, context):
        if not features.get("outfit_visible", True):
            return {
                "summary": "Je ne vois pas bien votre tenue.",
                "advice": "Reculez un peu pour que votre buste soit dans le miroir.",
                "confidence": 0.3,
                "features": features,
            }

        dominant = features.get("dominant_color")
        secondary = features.get("secondary_color")
        brightness = features.get("brightness", "medium")
        contrast = features.get("contrast", "medium")

        rules = []  # (catégorie, message, poids)

        if features.get("lighting") == "poor":
            rules.append(("lighting", "La pièce est sombre : avec plus de lumière, mon analyse sera plus fiable.", 0.9))

        if dominant and secondary and frozenset((dominant, secondary)) in CLASHES:
            rules.append(("color", f"L'association {COLOR_NAMES[dominant]} et {COLOR_NAMES[secondary]} "
                                   "est audacieuse : un accessoire neutre l'apaiserait.", 0.85))
        elif dominant in COLOR_ADVICE:
            msg, weight = COLOR_ADVICE[dominant]
            rules.append(("color", msg, weight))

        if contrast == "low":
            rules.append(("contrast", "Plus de contraste entre le haut et le bas améliorerait l'équilibre visuel.", 0.8))
        elif contrast == "high":
            rules.append(("contrast", "Votre tenue est déjà très contrastée : gardez des accessoires discrets.", 0.6))

        if brightness == "dark" and dominant != "black":
            rules.append(("brightness", "Un accessoire plus clair mettrait davantage votre tenue en valeur.", 0.7))
        elif brightness == "light":
            rules.append(("brightness", "Une touche plus foncée apporterait de la profondeur.", 0.65))

        season = context.get("season")
        if season in SEASON_ADVICE:
            msg, weight = SEASON_ADVICE[season]
            rules.append(("season", msg, weight))

        time_of_day = context.get("time_of_day")
        if time_of_day in TIME_ADVICE:
            msg, weight = TIME_ADVICE[time_of_day]
            rules.append(("time", msg, weight))

        if not rules:
            rules.append(("default", "Votre tenue semble équilibrée et bien adaptée.", 0.6))

        # Un seul conseil par catégorie, les plus importants d'abord.
        seen, top = set(), []
        for category, msg, weight in sorted(rules, key=lambda r: r[2], reverse=True):
            if category in seen:
                continue
            seen.add(category)
            top.append((msg, weight))
            if len(top) == self.max_tips:
                break

        confidence = round(sum(w for _, w in top) / len(top), 2)
        return {
            "summary": self._summary(dominant, secondary, brightness, contrast),
            "advice": " ".join(msg for msg, _ in top),
            "confidence": confidence,
            "features": features,
        }

    @staticmethod
    def _summary(dominant, secondary, brightness, contrast):
        if dominant in COLOR_NAMES:
            colors = f"à dominante {COLOR_NAMES_FEM[dominant]}"
            if secondary in COLOR_NAMES:
                colors += f" et {COLOR_NAMES_FEM[secondary]}"
        else:
            colors = "aux couleurs variées"
        return (f"votre tenue {colors} est {BRIGHTNESS_LABELS.get(brightness, 'équilibrée')}, "
                f"avec un contraste {CONTRAST_LABELS.get(contrast, 'modéré')}")
