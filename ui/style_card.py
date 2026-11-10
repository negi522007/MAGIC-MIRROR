"""
Fiche « Analyse de la tenue » affichée à droite après une analyse de style :
pastille de la couleur dominante, luminosité, contraste et saison.
"""

from core.colors import COLOR_NAMES
from intelligence.style_engine import BRIGHTNESS_LABELS, CONTRAST_LABELS
from ui.theme import TEXT, TEXT_DIM

PANEL = "#101114"
PANEL_EDGE = "#2a2d34"
HIDE_AFTER_MS = 20000


class StyleCard:
    def __init__(self, bus, mirror_window):
        self.window = mirror_window
        self.canvas = c = mirror_window.canvas
        f = mirror_window.font
        self._hide_job = None
        self._x = self._y = 0

        self.bg = c.create_rectangle(0, 0, 0, 0, fill=PANEL, outline=PANEL_EDGE, stipple="gray75")
        self.title = c.create_text(0, 0, text="ANALYSE DE LA TENUE", font=f(13, "bold"),
                                   fill=TEXT_DIM, anchor="nw")
        self.swatch = c.create_oval(0, 0, 0, 0, fill="#000000", outline="#ffffff", width=2)
        self.color_text = c.create_text(0, 0, font=f(22, "bold"), fill=TEXT, anchor="w")
        self.lines = [c.create_text(0, 0, font=f(16), fill=TEXT, anchor="nw") for _ in range(3)]
        self.items = [self.bg, self.title, self.swatch, self.color_text, *self.lines]
        self._set_visible(False)

        mirror_window.add_layout(self._layout)
        bus.subscribe("recommendation_ready", lambda rec: mirror_window.post(self.show, rec))
        bus.subscribe("wake_word_detected", lambda _: mirror_window.post(self.hide))

    def _layout(self, w, h):
        s = self.window.scale
        cw, ch = 330 * s, 220 * s
        x0, y0 = w - cw - 40 * s, h * 0.38
        c = self.canvas
        c.coords(self.bg, x0, y0, x0 + cw, y0 + ch)
        c.coords(self.title, x0 + 20 * s, y0 + 18 * s)
        sw = 46 * s
        c.coords(self.swatch, x0 + 20 * s, y0 + 50 * s, x0 + 20 * s + sw, y0 + 50 * s + sw)
        c.coords(self.color_text, x0 + 20 * s + sw + 16 * s, y0 + 50 * s + sw / 2)
        for i, line in enumerate(self.lines):
            c.coords(line, x0 + 20 * s, y0 + (115 + 32 * i) * s)

    def show(self, recommendation):
        features = recommendation.get("features") or {}
        if not features.get("outfit_visible"):
            return
        c = self.canvas
        dominant = COLOR_NAMES.get(features.get("dominant_color"), "—")
        secondary = COLOR_NAMES.get(features.get("secondary_color"))
        c.itemconfig(self.swatch, fill=features.get("dominant_hex") or "#000000")
        c.itemconfig(self.color_text, text=dominant.capitalize() + (f" & {secondary}" if secondary else ""))
        context = recommendation.get("context") or {}
        values = [
            f"Luminosité : {BRIGHTNESS_LABELS.get(features.get('brightness'), '—')}",
            f"Contraste : {CONTRAST_LABELS.get(features.get('contrast'), '—')}",
            f"Saison : {context.get('season_label', '—')}",
        ]
        for line, value in zip(self.lines, values):
            c.itemconfig(line, text=value)
        self._set_visible(True)
        if self._hide_job is not None:
            c.after_cancel(self._hide_job)
        self._hide_job = c.after(HIDE_AFTER_MS, self.hide)

    def hide(self):
        self._hide_job = None
        self._set_visible(False)

    def _set_visible(self, visible):
        for item in self.items:
            self.canvas.itemconfig(item, state="normal" if visible else "hidden")
