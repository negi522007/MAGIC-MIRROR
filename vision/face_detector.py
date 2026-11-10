"""
Détection de visage.

Utilise YuNet (réseau ONNX intégré à OpenCV ≥ 4.8, plus précis et plus robuste aux
visages de profil / mal éclairés que Haar) si le modèle est présent, sinon retombe
sur la cascade de Haar (seulement avec OpenCV 4.x : OpenCV 5 l'a retirée).

La détection tourne sur une image réduite (`detect_width`) ; les boîtes sont
renvoyées dans les coordonnées de l'image d'origine, la plus grande en premier.
"""

import os

import cv2


class FaceDetector:
    def __init__(self, model_path=None, detect_width=320, score_threshold=0.7):
        self.detect_width = detect_width
        self.score_threshold = score_threshold
        self._yunet = None
        self._yunet_size = None
        self._haar = None
        self.backend = None

        if model_path and os.path.exists(model_path) and hasattr(cv2, "FaceDetectorYN"):
            try:
                self._yunet = cv2.FaceDetectorYN.create(
                    model_path, "", (320, 240), score_threshold, 0.3, 5000
                )
                self.backend = "yunet"
            except cv2.error as e:
                print(f"[FACE] ⚠ YuNet indisponible : {e}")

        if self._yunet is None and hasattr(cv2, "CascadeClassifier"):
            # Haar a été retiré d'OpenCV 5 : ce repli n'existe qu'avec OpenCV 4.x.
            self._haar = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            self.backend = "haar"
        if self.backend is None:
            self.backend = "none"
            print("[FACE] ❌ Aucun détecteur : modèle YuNet absent (scripts/install.sh) "
                  "et OpenCV sans Haar. L'analyse de tenue sera indisponible.")
        print(f"[FACE] Détecteur : {self.backend}")

    def detect_faces(self, frame):
        """Liste de boîtes (x, y, w, h), la plus grande en premier."""
        if frame is None:
            return []
        h, w = frame.shape[:2]
        scale = min(1.0, self.detect_width / float(w))
        small = frame if scale == 1.0 else cv2.resize(
            frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA
        )

        if self._yunet is not None:
            boxes = self._detect_yunet(small)
        elif self._haar is not None:
            boxes = self._detect_haar(small)
        else:
            boxes = []

        inv = 1.0 / scale
        boxes = [
            (int(x * inv), int(y * inv), int(bw * inv), int(bh * inv))
            for (x, y, bw, bh) in boxes
        ]
        boxes.sort(key=lambda b: b[2] * b[3], reverse=True)
        return boxes

    def detect_face(self, frame):
        """Compatibilité : True si au moins un visage."""
        return len(self.detect_faces(frame)) > 0

    def _detect_yunet(self, img):
        size = (img.shape[1], img.shape[0])
        if size != self._yunet_size:
            self._yunet.setInputSize(size)
            self._yunet_size = size
        _, faces = self._yunet.detect(img)
        if faces is None:
            return []
        return [tuple(map(float, f[:4])) for f in faces if f[-1] >= self.score_threshold]

    def _detect_haar(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        faces = self._haar.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=5, minSize=(30, 30))
        return [tuple(map(float, f)) for f in faces]
