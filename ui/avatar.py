"""
Avatar de l'assistant : une sphère animée dont la couleur et le mouvement
reflètent l'état du miroir.

    idle        respiration lente
    listening   ondes qui s'élargissent (« je vous écoute »)
    processing  arc qui tourne (« je réfléchis »)
    speaking    pulsation rapide

L'animation ne tourne qu'à 8 images/s au repos et 25 images/s sinon : quelques
dizaines d'objets Canvas, négligeable pour le CPU.
"""

import math
import time

from ui.theme import BG, STATE_COLORS, blend


class AssistantAvatar:
    def __init__(self, canvas, x, y, radius):
        self.canvas = canvas
        self.x, self.y, self.r = x, y, radius
        self.state = "idle"
        self._t0 = time.monotonic()
        self._job = None

        c = canvas
        self.rings = [c.create_oval(0, 0, 0, 0, outline="", width=2) for _ in range(2)]
        self.halo = c.create_oval(0, 0, 0, 0, outline="", width=1)
        self.core = c.create_oval(0, 0, 0, 0, outline="", fill=STATE_COLORS["idle"])
        self.highlight = c.create_oval(0, 0, 0, 0, outline="", fill="#ffffff")
        self.arc = c.create_arc(0, 0, 0, 0, style="arc", width=3, extent=100, outline="",
                                state="hidden")
        self._animate()

    def set_state(self, state):
        if state != self.state:
            self.state = state
            self._t0 = time.monotonic()

    def move_to(self, x, y):
        self.x, self.y = x, y

    def _circle(self, item, r):
        self.canvas.coords(item, self.x - r, self.y - r, self.x + r, self.y + r)

    def _animate(self):
        t = time.monotonic() - self._t0
        color = STATE_COLORS.get(self.state, STATE_COLORS["idle"])
        r = self.r
        c = self.canvas

        if self.state == "idle":
            core_r = r * (0.9 + 0.06 * math.sin(t * 1.6))
        elif self.state == "speaking":
            core_r = r * (0.95 + 0.12 * abs(math.sin(t * 7.0)) + 0.05 * math.sin(t * 13.0))
        else:
            core_r = r

        self._circle(self.core, core_r)
        c.itemconfig(self.core, fill=color)
        hr = core_r * 0.28
        c.coords(self.highlight, self.x - core_r * 0.45 - hr, self.y - core_r * 0.45 - hr,
                 self.x - core_r * 0.45 + hr, self.y - core_r * 0.45 + hr)
        c.itemconfig(self.highlight, fill=blend("#ffffff", color, 0.35))

        self._circle(self.halo, core_r * 1.25)
        c.itemconfig(self.halo, outline=blend(color, BG, 0.55))

        for i, ring in enumerate(self.rings):
            if self.state == "listening":
                phase = (t * 0.9 + i * 0.5) % 1.0
                self._circle(ring, r * (1.2 + 1.0 * phase))
                c.itemconfig(ring, outline=blend(color, BG, phase), state="normal")
            else:
                c.itemconfig(ring, state="hidden")

        if self.state == "processing":
            ar = r * 1.55
            c.coords(self.arc, self.x - ar, self.y - ar, self.x + ar, self.y + ar)
            c.itemconfig(self.arc, start=(-t * 300) % 360, outline=color, state="normal")
        else:
            c.itemconfig(self.arc, state="hidden")

        delay = 125 if self.state == "idle" else 40
        self._job = c.after(delay, self._animate)
