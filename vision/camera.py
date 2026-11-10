"""
Capture webcam dans un thread dédié.

Un seul thread lit la caméra (OpenCV n'est pas sûr si plusieurs threads appellent
`read()`) ; les autres modules récupèrent la dernière image avec `get_frame()`.
L'image est déjà retournée horizontalement (effet miroir).

`index` peut être :
    - un numéro de périphérique (0 = /dev/video0) ;
    - une URL de flux (MJPEG / RTSP…), par exemple la webcam Windows diffusée par
      ffmpeg pour WSL (voir docs/WSL.md). Dans l'URL, `WINDOWS_HOST` est remplacé par
      l'adresse de l'hôte Windows vue depuis WSL (passerelle par défaut).
Un flux réseau coupé est rouvert automatiquement.
"""

import subprocess
import threading
import time

import cv2

WINDOWS_HOST = "WINDOWS_HOST"


def windows_host_ip():
    """Adresse de l'hôte Windows depuis WSL2 (mode réseau NAT) : la passerelle par défaut."""
    try:
        out = subprocess.run(["ip", "route", "show", "default"], capture_output=True,
                             text=True, timeout=2).stdout.split()
        return out[out.index("via") + 1]
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return "127.0.0.1"


def resolve_source(index):
    """Numéro de caméra (int) ou URL avec WINDOWS_HOST résolu."""
    if isinstance(index, str):
        if index.isdigit():
            return int(index)
        if WINDOWS_HOST in index:
            return index.replace(WINDOWS_HOST, windows_host_ip())
    return index


class Camera:
    def __init__(self, index=0, width=640, height=480, fps=15, fourcc="MJPG"):
        self.index = index
        self.source = resolve_source(index)
        self.is_stream = isinstance(self.source, str)
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
    def _open(self):
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            cap.release()
            return None
        if not self.is_stream:
            if self.fourcc:
                # MJPG : moins de débit USB. Ignoré si la caméra ne le gère pas.
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*self.fourcc))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_FPS, self.fps)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # toujours l'image la plus récente
        return cap

    def start(self):
        if self._running:
            return
        self._cap = self._open()
        if self._cap is None:
            print(f"[CAMERA] ⚠ Caméra {self.source} introuvable — le miroir restera noir.")
            return
        self.available = True
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="camera", daemon=True)
        self._thread.start()
        print(f"[CAMERA] ✅ Caméra {self.source} démarrée")

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
            ok, frame = self._cap.read() if self._cap is not None else (False, None)
            if ok:
                failures = 0
                if frame.shape[1] > self.width * 1.5:  # flux plus grand que nécessaire
                    frame = cv2.resize(frame, (self.width, int(frame.shape[0] * self.width / frame.shape[1])),
                                       interpolation=cv2.INTER_AREA)
                frame = cv2.flip(frame, 1)
                with self._lock:
                    self._frame = frame
                    self._frame_id += 1
            else:
                failures += 1
                if failures == 30:
                    print("[CAMERA] ⚠ La caméra ne renvoie plus d'image.")
                if self.is_stream and failures % 20 == 0:
                    # Flux réseau coupé (ffmpeg relancé, Wi-Fi…) : on le rouvre.
                    if self._cap is not None:
                        self._cap.release()
                    self._cap = self._open()
                    if self._cap is not None:
                        print("[CAMERA] Flux réseau rouvert")
                time.sleep(0.1)
                continue
            # Un flux réseau impose sa cadence (read() bloque) : attendre en plus ferait
            # prendre du retard. Pour une webcam locale, on évite de tourner trop vite.
            if not self.is_stream:
                elapsed = time.monotonic() - start
                if elapsed < period:
                    time.sleep(period - elapsed)
