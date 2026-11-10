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


def test_camera_source_resolution(monkeypatch):
    import vision.camera as cam
    monkeypatch.setattr(cam, "windows_host_ip", lambda: "172.29.128.1")
    assert cam.resolve_source(0) == 0
    assert cam.resolve_source("1") == 1
    assert cam.resolve_source("http://WINDOWS_HOST:8090") == "http://172.29.128.1:8090"
    assert cam.Camera("http://WINDOWS_HOST:8090").is_stream
    assert not cam.Camera(0).is_stream


def test_windows_pipe_parser_returns_latest_complete_frame():
    import io
    from vision.windows_camera import WindowsCameraCapture

    def jpeg(value):
        return cv2.imencode(".jpg", np.full((48, 64, 3), value, np.uint8))[1].tobytes()

    class FakeProc:
        stdout = io.BytesIO(jpeg(10) + jpeg(120) + jpeg(240)[:50])  # 3e image incomplète

        def poll(self):
            return None

    cap = WindowsCameraCapture.__new__(WindowsCameraCapture)
    cap.proc, cap._buffer = FakeProc(), b""
    ok, frame = cap.read()
    assert ok and abs(int(frame.mean()) - 120) < 5   # saute la 1re, ignore la 3e tronquée
    ok, frame = cap.read()
    assert not ok                                      # flux terminé sans image complète


def test_auto_source_off_wsl(monkeypatch):
    import vision.camera as cam
    monkeypatch.setattr(cam, "is_wsl", lambda: False)
    assert cam.resolve_source("auto") == 0
    monkeypatch.setattr(cam, "is_wsl", lambda: True)
    monkeypatch.setattr(cam.os.path, "exists", lambda p: False)
    monkeypatch.setattr(cam, "find_windows_ffmpeg", lambda: "/mnt/c/ffmpeg.exe")
    assert cam.resolve_source("auto") == "windows"
