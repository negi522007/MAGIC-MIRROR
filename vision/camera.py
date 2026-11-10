"""
Capture webcam dans un thread dédié.

Un seul thread lit la caméra (OpenCV n'est pas sûr si plusieurs threads appellent
`read()`) ; les autres modules récupèrent la dernière image avec `get_frame()`.
L'image est déjà retournée horizontalement (effet miroir).
"""

import threading
import time

import cv2


class Camera:
    def __init__(self, index=0, width=640, height=480, fps=15, fourcc="MJPG"):
        self.index = index
        self.fourcc = fourcc
        self.width = width
        self.height = height
        self.fps = max(1, fps)

        self._lock = threading.Lock()
        self._frame = None
        self._frame_id = 0
        self._running = False
        self._thread = None
        self._cap = None
        self.available = False

    # ── cycle de vie ──
    def start(self):
        if self._running:
            return
        self._cap = cv2.VideoCapture(self.index)
        if not self._cap.isOpened():
            print(f"[CAMERA] ⚠ Caméra {self.index} introuvable — le miroir restera noir.")
            self._cap.release()
            self._cap = None
            return
        if self.fourcc:
            # MJPG : flux compressé, indispensable pour une webcam partagée par USB/IP (WSL)
            # et moins de débit USB en général. Ignoré si la caméra ne le gère pas.
            self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*self.fourcc))
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._cap.set(cv2.CAP_PROP_FPS, self.fps)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # toujours l'image la plus récente
        self.available = True
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="camera", daemon=True)
        self._thread.start()
        print(f"[CAMERA] ✅ Caméra {self.index} démarrée ({self.width}x{self.height} @ {self.fps} fps)")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    # ── lecture ──
    def get_frame(self):
        """Dernière image (BGR, retournée) ou None. Ne pas la modifier en place."""
        with self._lock:
            return self._frame

    def get_frame_with_id(self):
        """(image, numéro) : le numéro permet de savoir si l'image a changé."""
        with self._lock:
            return self._frame, self._frame_id

    def _loop(self):
        period = 1.0 / self.fps
        failures = 0
        while self._running:
            start = time.monotonic()
            ok, frame = self._cap.read()
            if ok:
                failures = 0
                frame = cv2.flip(frame, 1)
                with self._lock:
                    self._frame = frame
                    self._frame_id += 1
            else:
                failures += 1
                if failures == 30:
                    print("[CAMERA] ⚠ La caméra ne renvoie plus d'image.")
                time.sleep(0.1)
                continue
            # La plupart des webcams imposent déjà leur cadence ; on évite juste de
            # tourner plus vite que nécessaire si le pilote ne bloque pas.
            elapsed = time.monotonic() - start
            if elapsed < period:
                time.sleep(period - elapsed)
