import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from vision.face_detector import FaceDetector  # noqa: E402
from vision.visual_features import VisualFeatures, name_color  # noqa: E402

FACE = (270, 60, 100, 100)  # x, y, w, h dans une image 640x480


def scene(shirt_bgr, wall_bgr=(200, 200, 200)):
    frame = np.full((480, 640, 3), wall_bgr, np.uint8)
    frame[60:160, 270:370] = (140, 170, 210)          # visage
    frame[190:480, 200:440] = shirt_bgr               # buste
    return frame


@pytest.mark.parametrize("bgr,name", [
    ((20, 20, 20), "black"), ((240, 240, 240), "white"), ((128, 128, 128), "gray"),
    ((200, 60, 20), "blue"), ((30, 30, 200), "red"), ((40, 160, 40), "green"),
    ((30, 200, 230), "yellow"), ((30, 60, 100), "brown"), ((170, 80, 200), "pink"),
    ((150, 200, 230), "beige"),
])
def test_name_color(bgr, name):
    assert name_color(bgr) == name


def test_analysis_uses_outfit_not_background():
    # Mur blanc, chemise bleue : l'ancienne version analysait toute l'image.
    f = VisualFeatures().extract_features(scene((180, 60, 20)), FACE)
    assert f["outfit_visible"] and f["dominant_color"] == "blue"
    assert f["dominant_hex"].startswith("#")


def test_dark_outfit():
    f = VisualFeatures().extract_features(scene((25, 25, 25)), FACE)
    assert f["dominant_color"] == "black" and f["brightness"] == "dark"


def test_outfit_out_of_frame():
    f = VisualFeatures().extract_features(scene((180, 60, 20)), (270, 380, 100, 100))
    assert f["presence_face"] and not f["outfit_visible"]


def test_no_face():
    f = VisualFeatures().extract_features(scene((180, 60, 20)), None)
    assert not f["presence_face"]


def test_detector_returns_empty_on_blank_image():
    detector = FaceDetector(model_path=None)
    assert detector.detect_faces(np.zeros((480, 640, 3), np.uint8)) == []
    assert detector.detect_faces(None) == []


def test_yunet_loads_when_model_present():
    import os
    from config import resolve_path
    path = resolve_path("models/face_detection_yunet_2023mar.onnx")
    if not os.path.exists(path):
        pytest.skip("modèle YuNet absent")
    assert FaceDetector(path).backend == "yunet"
