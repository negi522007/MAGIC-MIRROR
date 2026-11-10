"""
Webcam Windows lue depuis WSL2, sans réglage côté Windows.

Le miroir lance lui-même `ffmpeg.exe` (programme Windows, appelable depuis WSL grâce à
l'interopérabilité) qui capture la webcam avec DirectShow et écrit un flux MJPEG sur sa
sortie standard ; on découpe ce flux en images JPEG et on les décode. Pas de réseau,
pas de pare-feu, et la webcam n'a pas à être partagée par USB/IP (qui tronque les images
des webcams YUYV : voir docs/WSL.md).

Prérequis unique : ffmpeg installé sous Windows (`winget install Gyan.FFmpeg`).
"""

import glob
import os
import re
import shutil
import subprocess
import threading

import cv2
import numpy as np

SOI, EOI = b"\xff\xd8", b"\xff\xd9"


def is_wsl():
    try:
        with open("/proc/version") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        return False


def find_windows_ffmpeg():
    """Chemin de ffmpeg.exe (PATH Windows, liens winget, ou paquet winget), ou None."""
    found = shutil.which("ffmpeg.exe")
    if found:
        return found
    patterns = [
        "/mnt/c/Users/*/AppData/Local/Microsoft/WinGet/Links/ffmpeg.exe",
        "/mnt/c/Users/*/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg*/*/bin/ffmpeg.exe",
        "/mnt/c/ProgramData/chocolatey/bin/ffmpeg.exe",
        "/mnt/c/ffmpeg/bin/ffmpeg.exe",
    ]
    for pattern in patterns:
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[-1]
    return None


def list_video_devices(ffmpeg):
    """Noms des caméras DirectShow vues par Windows.

    Délai large : au tout premier lancement, l'antivirus Windows peut analyser
    ffmpeg.exe pendant plus de 15 s.
    """
    try:
        out = subprocess.run([ffmpeg, "-hide_banner", "-list_devices", "true", "-f", "dshow",
                              "-i", "dummy"], capture_output=True, timeout=45)
    except (OSError, subprocess.SubprocessError):
        return []
    text = (out.stderr + out.stdout).decode("utf-8", "replace")
    return re.findall(r'"([^"]+)"\s*\(video\)', text)


class WindowsCameraCapture:
    """Même interface minimale que cv2.VideoCapture : isOpened(), read(), release()."""

    def __init__(self, device=None, width=640, height=480, fps=15):
        self.ffmpeg = find_windows_ffmpeg()
        self.device = device
        self.proc = None
        self._buffer = b""
        self._lock = threading.Lock()
        if self.ffmpeg is None:
            print("[CAMERA] ffmpeg.exe introuvable côté Windows — `winget install Gyan.FFmpeg`")
            return
        if not self.device:
            devices = list_video_devices(self.ffmpeg)
            if not devices:
                print("[CAMERA] Aucune webcam vue par Windows (déjà utilisée, ou prêtée à WSL par usbipd ?)")
                return
            self.device = devices[0]
        for size in (f"{width}x{height}", None):  # sans taille imposée si la webcam la refuse
            self._start(size, fps)
            frame_ok, _ = self.read()
            if frame_ok:
                print(f"[CAMERA] Webcam Windows « {self.device} » via ffmpeg.exe")
                return
            self.release()

    def _start(self, size, fps):
        cmd = [self.ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "dshow"]
        if size:
            cmd += ["-video_size", size]
        cmd += ["-i", f"video={self.device}", "-vf", f"fps={fps}", "-c:v", "mjpeg", "-q:v", "5",
                "-f", "image2pipe", "-"]
        self._buffer = b""
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     stdin=subprocess.DEVNULL, bufsize=0)

    def isOpened(self):
        return self.proc is not None and self.proc.poll() is None

    def set(self, *_):
        return False

    def read(self):
        """Prochaine image complète (bloquant). (False, None) si ffmpeg s'est arrêté."""
        if self.proc is None:
            return False, None
        while True:
            start = self._buffer.find(SOI)
            end = self._buffer.find(EOI, start + 2) if start >= 0 else -1
            if start >= 0 and end >= 0:
                jpg = self._buffer[start:end + 2]
                self._buffer = self._buffer[end + 2:]
                # S'il y a déjà d'autres images en attente, on saute aux plus récentes.
                if self._buffer.count(EOI) >= 1:
                    continue
                frame = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
                return (frame is not None), frame
            chunk = self.proc.stdout.read(65536)
            if not chunk:
                return False, None
            self._buffer = self._buffer[-4_000_000:] + chunk  # borne la mémoire

    def release(self):
        if self.proc is not None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None
