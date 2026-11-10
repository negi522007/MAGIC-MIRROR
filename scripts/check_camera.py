"""Vérification manuelle : caméra + détection de visage + zone de tenue analysée.

    python scripts/check_camera.py      (q pour quitter)

Nécessite opencv-python (avec interface graphique) : opencv-python-headless n'a
pas cv2.imshow. Sinon, utiliser `python main.py --windowed`.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2  # noqa: E402

from config import load_config, resolve_path  # noqa: E402
from core.colors import COLOR_NAMES  # noqa: E402
from vision.camera import Camera  # noqa: E402
from vision.face_detector import FaceDetector  # noqa: E402
from vision.visual_features import VisualFeatures  # noqa: E402

cfg = load_config()
cam = Camera(cfg["camera"]["index"], cfg["camera"]["width"], cfg["camera"]["height"])
cam.start()
detector = FaceDetector(resolve_path(cfg["models"]["face"]))
features = VisualFeatures()
while True:
    frame = cam.get_frame()
    if frame is None:
        time.sleep(0.05)
        continue
    view = frame.copy()
    t = time.perf_counter()
    faces = detector.detect_faces(frame)
    dt = (time.perf_counter() - t) * 1000
    label = f"{detector.backend} {dt:.0f} ms - aucun visage"
    if faces:
        x, y, w, h = faces[0]
        cv2.rectangle(view, (x, y), (x + w, y + h), (0, 255, 0), 2)
        f = features.extract_features(frame, faces[0])
        if f["region"]:
            x0, y0, x1, y1 = f["region"]
            cv2.rectangle(view, (x0, y0), (x1, y1), (255, 200, 0), 2)
            label = (f"{detector.backend} {dt:.0f} ms - {COLOR_NAMES[f['dominant_color']]} "
                     f"{f['brightness']} {f['contrast']}")
        else:
            label = f"{detector.backend} {dt:.0f} ms - buste hors cadre"
    cv2.putText(view, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    cv2.imshow("check_camera", view)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break
cam.stop()
cv2.destroyAllWindows()
