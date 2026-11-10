"""
Fenêtre principale du miroir (Tkinter, un seul Canvas).

- Image caméra en plein écran (recadrée pour remplir l'écran sans déformation).
- Horloge, date et salutation en haut à droite ; avatar et état en haut à gauche.
- Mise en veille : sans visage pendant `sleep_after` s, l'image caméra est masquée
  (effet vrai miroir) et n'est plus redimensionnée, ce qui économise le CPU.

Fil d'exécution : Tk n'est pas thread-safe. Les autres threads n'appellent jamais
Tk directement ; ils passent par `post(fn, *args)`, vidé par la boucle Tk.

Performances (Intel N100) : l'image est d'abord recadrée à la taille utile puis
redimensionnée par OpenCV (INTER_LINEAR) ; la PhotoImage Tk est réutilisée
(`paste`) au lieu d'être recréée ; une image n'est redessinée que si la caméra en a
produit une nouvelle.
"""

import queue
import time
import tkinter as tk
from datetime import datetime

import cv2
from PIL import Image, ImageTk

from core.french import format_date, greeting
from ui.avatar import AssistantAvatar
from ui.theme import BG, STATE_COLORS, STATE_LABELS, TEXT, TEXT_DIM, ShadowText, pick_family


class MirrorWindow:
    def __init__(self, bus, camera, fullscreen=True, fps=20, sleep_after=60,
                 show_face_box=True, windowed_size=(1280, 720)):
        self.bus = bus
        self.camera = camera
        self.fps = max(1, fps)
        self.sleep_after = sleep_after
        self.show_face_box = show_face_box

        self.root = tk.Tk()
        self.root.title("TEKBOT Magic Mirror")
        self.root.configure(bg=BG)
        if fullscreen:
            self.root.attributes("-fullscreen", True)
            self.root.config(cursor="none")
            w, h = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        else:
            w, h = windowed_size
            self.root.geometry(f"{w}x{h}")
        self.width, self.height = w, h
        self.scale = h / 1080.0
        self.family = pick_family(self.root)

        self.canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0, width=w, height=h)
        self.canvas.pack(fill="both", expand=True)

        self._queue = queue.Queue()
        self._layouts = []
        self._keys = {}
        self.on_close = None
        self.status_provider = None
        self.running = False

        # ── caméra ──
        self._photo = None
        self._last_frame_id = -1
        self._crop = None            # (échelle, x0, y0) : image caméra → écran
        self.camera_item = self.canvas.create_image(0, 0, anchor="nw")
        self.face_items = [self.canvas.create_line(0, 0, 0, 0, fill=STATE_COLORS["listening"],
                                                   width=3, capstyle="round", state="hidden")
                           for _ in range(8)]

        # ── veille ──
        self.state = "idle"
        self.present = False
        self._last_presence = time.monotonic()
        self.asleep = False

        # ── textes ──
        f = self.font
        self.clock = ShadowText(self.canvas, 0, 0, font=f(64, "bold"), anchor="ne")
        self.date = ShadowText(self.canvas, 0, 0, font=f(20), fill=TEXT_DIM, anchor="ne")
        self.greeting = ShadowText(self.canvas, 0, 0, font=f(24), fill=TEXT, anchor="ne")
        self.state_text = ShadowText(self.canvas, 0, 0, font=f(18), fill=TEXT, anchor="w")
        self.status_text = ShadowText(self.canvas, 0, 0, font=f(11), fill=TEXT_DIM, anchor="sw",
                                      offset=1)
        self.no_camera = ShadowText(self.canvas, 0, 0, font=f(16), fill=TEXT_DIM)
        self.avatar = AssistantAvatar(self.canvas, 0, 0, 22 * self.scale)

        self.add_layout(self._layout)
        self.canvas.bind("<Configure>", self._on_configure)
        self.root.bind("<Escape>", lambda e: self.stop())
        self.root.bind("<F11>", lambda e: self._toggle_fullscreen())
        self.root.bind("<Key>", self._on_key)
        self.root.protocol("WM_DELETE_WINDOW", self.stop)

        bus.subscribe("state_changed", lambda s: self.post(self._on_state, s))
        bus.subscribe("presence_changed", lambda p: self.post(self._on_presence, p))
        bus.subscribe("faces_updated", lambda d: self.post(self._on_faces, d))

    # ── utilitaires publics ──
    def font(self, size, weight="normal", slant="roman"):
        """Police à l'échelle de l'écran (tailles exprimées pour un écran 1080p)."""
        return (self.family, -max(8, int(size * 1.33 * self.scale)), weight, slant)

    def post(self, fn, *args):
        """Exécute fn(*args) dans le thread Tk (appelable depuis n'importe quel thread)."""
        self._queue.put((fn, args))

    def add_layout(self, callback):
        self._layouts.append(callback)
        callback(self.width, self.height)

    def bind_key(self, key, callback):
        self._keys[key] = callback

    def get_root(self):
        return self.root

    # ── cycle de vie ──
    def start(self):
        self.running = True
        self._tick_clock()
        self._drain()
        self._render_camera()
        self.root.mainloop()

    def stop(self):
        if not self.running:
            return
        self.running = False
        if self.on_close:
            self.on_close()
        self.root.destroy()

    # ── boucles ──
    def _drain(self):
        if not self.running:
            return
        try:
            while True:
                fn, args = self._queue.get_nowait()
                try:
                    fn(*args)
                except Exception as e:
                    print(f"[UI] Erreur : {e}")
        except queue.Empty:
            pass
        self.root.after(30, self._drain)

    def _tick_clock(self):
        if not self.running:
            return
        now = datetime.now()
        self.clock.config(text=now.strftime("%H:%M"))
        self.date.config(text=format_date(now).capitalize())
        self.greeting.config(text=greeting(now) if self.present or self.state != "idle" else "")
        if self.status_provider:
            self.status_text.config(text=self.status_provider())
        self._update_sleep()
        self.root.after(1000, self._tick_clock)

    def _render_camera(self):
        if not self.running:
            return
        start = time.monotonic()
        frame, frame_id = self.camera.get_frame_with_id()
        if frame is None:
            self.no_camera.config(text="Caméra indisponible" if not self.camera.available else "")
        elif not self.asleep and frame_id != self._last_frame_id:
            self._last_frame_id = frame_id
            self._draw_frame(frame)
        delay = int(1000 / self.fps - (time.monotonic() - start) * 1000)
        self.root.after(max(5, delay), self._render_camera)

    def _draw_frame(self, frame):
        W, H = self.width, self.height
        fh, fw = frame.shape[:2]
        s = max(W / fw, H / fh)
        cw, ch = W / s, H / s
        x0, y0 = (fw - cw) / 2, (fh - ch) / 2
        crop = frame[int(y0):int(y0 + ch), int(x0):int(x0 + cw)]
        rgb = cv2.cvtColor(cv2.resize(crop, (W, H), interpolation=cv2.INTER_LINEAR),
                           cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        if self._photo is None or self._photo.width() != W or self._photo.height() != H:
            self._photo = ImageTk.PhotoImage(image)
            self.canvas.itemconfig(self.camera_item, image=self._photo)
        else:
            self._photo.paste(image)
        self._crop = (s, int(x0), int(y0))

    # ── événements ──
    def _on_state(self, state):
        self.state = state
        self.avatar.set_state(state)
        self.state_text.config(text=STATE_LABELS.get(state, ""),
                               fill=TEXT if state == "idle" else STATE_COLORS.get(state, TEXT))
        if state != "idle":
            self._wake_display()
        if state == "idle":
            self._hide_face_box()

    def _on_presence(self, present):
        self.present = present
        if present:
            self._wake_display()

    def _on_faces(self, data):
        faces = data.get("faces") or []
        if not (self.show_face_box and faces and self._crop and self.state in ("listening", "processing")):
            self._hide_face_box()
            return
        s, x0, y0 = self._crop
        x, y, w, h = faces[0]
        X0, Y0 = (x - x0) * s, (y - y0) * s
        X1, Y1 = X0 + w * s, Y0 + h * s
        L = min(X1 - X0, Y1 - Y0) * 0.22
        color = STATE_COLORS.get(self.state, TEXT)
        corners = [
            (X0, Y0 + L, X0, Y0), (X0, Y0, X0 + L, Y0),
            (X1 - L, Y0, X1, Y0), (X1, Y0, X1, Y0 + L),
            (X0, Y1 - L, X0, Y1), (X0, Y1, X0 + L, Y1),
            (X1 - L, Y1, X1, Y1), (X1, Y1, X1, Y1 - L),
        ]
        for item, coords in zip(self.face_items, corners):
            self.canvas.coords(item, *coords)
            self.canvas.itemconfig(item, fill=color, state="normal")

    def _hide_face_box(self):
        for item in self.face_items:
            self.canvas.itemconfig(item, state="hidden")

    def _on_key(self, event):
        callback = self._keys.get(event.keysym) or self._keys.get(event.char)
        if callback:
            callback()

    # ── veille ──
    def _wake_display(self):
        self._last_presence = time.monotonic()
        if self.asleep:
            self.asleep = False
            self.canvas.itemconfig(self.camera_item, state="normal")
            self._last_frame_id = -1

    def _update_sleep(self):
        if self.present or self.state != "idle":
            self._last_presence = time.monotonic()
            return
        if not self.asleep and self.sleep_after and \
                time.monotonic() - self._last_presence > self.sleep_after:
            self.asleep = True
            self.canvas.itemconfig(self.camera_item, state="hidden")
            print("[UI] Veille : image caméra masquée")

    # ── mise en page ──
    def _on_configure(self, event):
        if (event.width, event.height) != (self.width, self.height) and event.width > 1:
            self.width, self.height = event.width, event.height
            self._photo = None
            for callback in self._layouts:
                callback(self.width, self.height)

    def _layout(self, w, h):
        s = self.scale
        m = 40 * s
        self.clock.move_to(w - m, m * 0.6)
        self.date.move_to(w - m, m * 0.6 + 95 * s)
        self.greeting.move_to(w - m, m * 0.6 + 135 * s)
        self.avatar.move_to(m + 22 * s, m + 22 * s)
        self.state_text.move_to(m + 100 * s, m + 22 * s)  # au-delà des ondes de l'avatar
        self.status_text.move_to(m * 0.5, h - m * 0.4)
        self.no_camera.move_to(w / 2, h / 2)

    def _toggle_fullscreen(self):
        fs = not bool(self.root.attributes("-fullscreen"))
        self.root.attributes("-fullscreen", fs)
