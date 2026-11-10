"""
Surveillance de présence : détecte périodiquement les visages sur la dernière image.

- Rythme rapide (`detect_interval`) quand quelqu'un est devant le miroir, lent
  (`idle_detect_interval`) sinon : peu de CPU en veille.
- Publie `presence_changed` (bool) quand quelqu'un arrive / part, et
  `faces_updated` ({"faces": [...], "frame_size": (w, h)}) à chaque détection.
- Garde le dernier résultat pour que l'analyse de style n'ait pas à relancer une
  détection (`latest()`).
"""

import threading
import time


class PresenceMonitor:
    def __init__(self, bus, camera, detector, detect_interval=0.4,
                 idle_detect_interval=1.0, absence_grace=2.0):
        self.bus = bus
        self.camera = camera
        self.detector = detector
        self.detect_interval = detect_interval
        self.idle_detect_interval = idle_detect_interval
        self.absence_grace = absence_grace  # évite de clignoter si un visage est raté

        self._lock = threading.Lock()
        self._faces = []
        self._frame = None
        self._present = False
        self._last_seen = 0.0
        self._running = False
        self._thread = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="presence", daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    @property
    def present(self):
        return self._present

    def latest(self):
        """(image, visages) de la dernière détection."""
        with self._lock:
            return self._frame, list(self._faces)

    def detect_now(self):
        """Détection immédiate sur l'image courante (utilisée pour l'analyse de style)."""
        frame = self.camera.get_frame()
        if frame is None:
            return None, []
        faces = self.detector.detect_faces(frame)
        self._update(frame, faces)
        return frame, faces

    def _update(self, frame, faces):
        now = time.monotonic()
        with self._lock:
            self._frame = frame
            self._faces = faces
        if faces:
            self._last_seen = now
        present = bool(faces) or (now - self._last_seen < self.absence_grace)
        h, w = frame.shape[:2]
        self.bus.emit("faces_updated", {"faces": faces, "frame_size": (w, h)})
        if present != self._present:
            self._present = present
            self.bus.emit("presence_changed", present)

    def _loop(self):
        last_id = -1
        while self._running:
            start = time.monotonic()
            frame, frame_id = self.camera.get_frame_with_id()
            if frame is not None and frame_id != last_id:
                last_id = frame_id
                try:
                    self._update(frame, self.detector.detect_faces(frame))
                except Exception as e:
                    print(f"[PRESENCE] Erreur de détection : {e}")
            interval = self.detect_interval if self._present else self.idle_detect_interval
            time.sleep(max(0.05, interval - (time.monotonic() - start)))
