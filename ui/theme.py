"""
Thème graphique : couleurs, polices et petits utilitaires de dessin sur Canvas.
"""

import tkinter.font as tkfont

BG = "#000000"
TEXT = "#f5f5f7"
TEXT_DIM = "#9aa0a6"
SHADOW = "#000000"

STATE_COLORS = {
    "idle": "#8e9aaf",
    "listening": "#4fd1ff",
    "processing": "#ffc857",
    "speaking": "#c3a6ff",
}

STATE_LABELS = {
    "idle": "Dites « miroir magique »",
    "listening": "Je vous écoute…",
    "processing": "Je réfléchis…",
    "speaking": "",
}

_PREFERRED_FAMILIES = ["Inter", "Noto Sans", "Ubuntu", "Cantarell", "DejaVu Sans",
                       "Segoe UI", "Helvetica Neue", "Helvetica", "Arial", "Nimbus Sans L"]


def pick_family(root):
    available = {f.lower(): f for f in tkfont.families(root)}
    for family in _PREFERRED_FAMILIES:
        if family.lower() in available:
            return available[family.lower()]
    return "TkDefaultFont"


def blend(color, background, t):
    """Mélange linéaire : t=0 → color, t=1 → background (Tk n'a pas de transparence)."""
    c = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(background[i:i + 2], 16) for i in (1, 3, 5)]
    m = [round(c[k] + (b[k] - c[k]) * t) for k in range(3)]
    return "#{:02x}{:02x}{:02x}".format(*m)


class ShadowText:
    """Texte avec ombre portée, lisible par-dessus l'image de la caméra."""

    def __init__(self, canvas, x, y, font, fill=TEXT, anchor="center", width=0, justify="center",
                 offset=2):
        self.canvas = canvas
        self.offset = offset
        kw = dict(font=font, anchor=anchor, width=width, justify=justify, text="")
        self.shadow = canvas.create_text(x + offset, y + offset, fill=SHADOW, **kw)
        self.item = canvas.create_text(x, y, fill=fill, **kw)

    def config(self, **kw):
        shadow_kw = {k: v for k, v in kw.items() if k != "fill"}
        if shadow_kw:
            self.canvas.itemconfig(self.shadow, **shadow_kw)
        self.canvas.itemconfig(self.item, **kw)

    def move_to(self, x, y):
        self.canvas.coords(self.item, x, y)
        self.canvas.coords(self.shadow, x + self.offset, y + self.offset)

    def set_visible(self, visible):
        state = "normal" if visible else "hidden"
        self.canvas.itemconfig(self.item, state=state)
        self.canvas.itemconfig(self.shadow, state=state)

    def raise_(self):
        self.canvas.tag_raise(self.shadow)
        self.canvas.tag_raise(self.item)
