"""
Extraction des caractéristiques de la tenue.

L'analyse porte sur la zone du buste, sous le visage détecté (et non sur toute
l'image, ce qui mesurait surtout le mur derrière la personne). La zone est réduite
à 48x48 avant le k-means : quelques millisecondes sur un Intel N100.

Sortie (contrat attendu par intelligence/style_engine.py) :
    presence_face   bool
    outfit_visible  bool   — False si le buste sort du cadre
    dominant_color  str    — clé de couleur ("blue", "black"...), voir COLOR_NAMES
    secondary_color str|None
    dominant_hex    str    — "#rrggbb", pour l'affichage
    brightness      "dark" | "medium" | "light"
    contrast        "low" | "medium" | "high"
    lighting        "poor" | "ok"
"""

import cv2
import numpy as np

from core.colors import COLOR_NAMES  # noqa: F401  (réexporté)

ANALYSIS_SIZE = 48
K_CLUSTERS = 3


def name_color(bgr):
    """Nom (clé) d'une couleur BGR, d'après sa teinte / saturation / valeur."""
    pixel = np.uint8([[list(bgr)]])
    h, s, v = (int(c) for c in cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)[0, 0])
    # Teinte OpenCV : 0–179.
    if v < 50:
        return "black"
    if s < 45:
        if v > 200:
            return "white"
        if v < 85:
            return "black"
        return "gray"
    if 8 <= h < 30 and s < 110 and v > 150:
        return "beige"
    if (h < 22 or h >= 170) and v < 140 and s < 200:
        return "brown"
    if h < 8 or h >= 170:
        return "red"
    if h < 20:
        return "orange"
    if h < 34:
        return "yellow"
    if h < 80:
        return "green"
    if h < 95:
        return "turquoise"
    if h < 130:
        return "blue"
    if h < 150:
        return "purple"
    return "pink"


class VisualFeatures:
    def outfit_region(self, frame_shape, face_box):
        """Rectangle (x0, y0, x1, y1) du buste sous le visage, ou None s'il est hors cadre."""
        H, W = frame_shape[:2]
        x, y, w, h = face_box
        y0 = int(y + 1.3 * h)
        y1 = int(min(H, y0 + 3.0 * h))
        x0 = int(max(0, x - 0.6 * w))
        x1 = int(min(W, x + w + 0.6 * w))
        if y1 - y0 < 0.6 * h or x1 - x0 < w:
            return None
        return x0, y0, x1, y1

    def extract_features(self, frame, face_box):
        """`face_box` : (x, y, w, h) du visage principal, ou None / False si aucun."""
        if frame is None or not face_box or face_box is True:
            return self._empty(presence=bool(face_box))

        region = self.outfit_region(frame.shape, face_box)
        lighting = self._lighting(frame, face_box)
        if region is None:
            features = self._empty(presence=True)
            features["lighting"] = lighting
            return features

        x0, y0, x1, y1 = region
        crop = cv2.resize(frame[y0:y1, x0:x1], (ANALYSIS_SIZE, ANALYSIS_SIZE),
                          interpolation=cv2.INTER_AREA)

        dominant, secondary, dominant_bgr = self._colors(crop)

        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        value = float(np.mean(hsv[:, :, 2]))
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY).astype(np.float32)
        contrast = float(gray.std())

        return {
            "presence_face": True,
            "outfit_visible": True,
            "dominant_color": dominant,
            "secondary_color": secondary,
            "dominant_hex": "#{:02x}{:02x}{:02x}".format(
                int(dominant_bgr[2]), int(dominant_bgr[1]), int(dominant_bgr[0])),
            "brightness": "dark" if value < 85 else "light" if value > 170 else "medium",
            "contrast": "low" if contrast < 28 else "high" if contrast > 60 else "medium",
            "lighting": lighting,
            "region": region,
        }

    # ── détails ──
    def _colors(self, crop):
        pixels = crop.reshape(-1, 3).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        cv2.setRNGSeed(0)  # résultats reproductibles
        _, labels, centers = cv2.kmeans(pixels, K_CLUSTERS, None, criteria, 2,
                                        cv2.KMEANS_PP_CENTERS)
        counts = np.bincount(labels.flatten(), minlength=K_CLUSTERS)
        order = np.argsort(counts)[::-1]

        dominant_bgr = centers[order[0]]
        dominant = name_color(dominant_bgr)
        secondary = None
        for idx in order[1:]:
            if counts[idx] / len(labels) < 0.2:
                break
            name = name_color(centers[idx])
            if name != dominant:
                secondary = name
                break
        return dominant, secondary, dominant_bgr

    def _lighting(self, frame, face_box):
        x, y, w, h = (int(v) for v in face_box)
        face = frame[max(0, y):y + h, max(0, x):x + w]
        if face.size == 0:
            return "ok"
        return "poor" if float(np.mean(cv2.cvtColor(face, cv2.COLOR_BGR2GRAY))) < 60 else "ok"

    @staticmethod
    def _empty(presence):
        return {
            "presence_face": presence,
            "outfit_visible": False,
            "dominant_color": None,
            "secondary_color": None,
            "dominant_hex": None,
            "brightness": "medium",
            "contrast": "medium",
            "lighting": "ok",
            "region": None,
        }
