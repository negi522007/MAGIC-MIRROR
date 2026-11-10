"""
Sous-titres en bas du miroir :
    - ce que la personne dit (transcription en direct, en gris) ;
    - la réponse de l'assistant (animation de frappe, puis fondu).
"""

from ui.theme import BG, TEXT, TEXT_DIM, ShadowText, blend


class AssistantOverlay:
    def __init__(self, bus, mirror_window, fade_delay=8000, typing_speed=25):
        self.window = mirror_window
        self.canvas = mirror_window.canvas
        self.fade_delay = fade_delay
        self.typing_speed = typing_speed

        f = mirror_window.font
        # Bandeau sombre semi-transparent (stipple) derrière les sous-titres, pour la
        # lisibilité sur une image chargée. Sous Windows, stipple est ignoré (opaque).
        self.band = self.canvas.create_rectangle(0, 0, 0, 0, fill=BG, outline="",
                                                 stipple="gray50", state="hidden")
        self.user_text = ShadowText(self.canvas, 0, 0, font=f(20, slant="italic"), fill=TEXT_DIM)
        self.reply_text = ShadowText(self.canvas, 0, 0, font=f(28), fill=TEXT)

        self._typing_job = None
        self._fade_job = None
        self._full_text = ""
        self._index = 0

        mirror_window.add_layout(self._layout)
        post = mirror_window.post
        bus.subscribe("llm_response", lambda text: post(self.display_text, text))
        bus.subscribe("stt_partial", lambda text: post(self.show_user_text, text))
        bus.subscribe("speech_transcribed", lambda text: post(self.show_user_text, text))
        bus.subscribe("wake_word_detected", lambda _: post(self.clear))

    def _layout(self, w, h):
        wrap = int(w * 0.8)
        self.user_text.config(width=wrap)
        self.reply_text.config(width=wrap)
        self.canvas.coords(self.band, 0, h * 0.72, w, h)
        self.user_text.move_to(w / 2, h * 0.76)
        self.reply_text.move_to(w / 2, h * 0.87)

    # ── API (thread Tk uniquement) ──
    def show_user_text(self, text):
        self._show_band(True)
        self.user_text.config(text=f"« {text} »", fill=TEXT_DIM)

    def display_text(self, text):
        self._cancel()
        self._full_text = text
        self._index = 0
        self._show_band(True)
        self.reply_text.config(text="", fill=TEXT)
        self._type_next()

    def clear(self):
        self._cancel()
        self.user_text.config(text="")
        self.reply_text.config(text="")
        self._show_band(False)

    def _show_band(self, visible):
        self.canvas.itemconfig(self.band, state="normal" if visible else "hidden")

    @property
    def busy(self):
        return bool(self._full_text)

    # ── animations ──
    def _type_next(self):
        if self._index <= len(self._full_text):
            self.reply_text.config(text=self._full_text[:self._index])
            # Deux caractères par pas : animation fluide sans saturer la boucle Tk.
            self._index += 2
            self._typing_job = self.canvas.after(self.typing_speed, self._type_next)
        else:
            self.reply_text.config(text=self._full_text)
            self._typing_job = None
            self._fade_job = self.canvas.after(self.fade_delay, self._fade, 0)

    def _fade(self, step):
        steps = 12
        if step > steps:
            self.clear()
            self._full_text = ""
            return
        t = step / steps
        self.reply_text.config(fill=blend(TEXT, BG, t))
        self.user_text.config(fill=blend(TEXT_DIM, BG, t))
        self._fade_job = self.canvas.after(60, self._fade, step + 1)

    def _cancel(self):
        for job in (self._typing_job, self._fade_job):
            if job is not None:
                self.canvas.after_cancel(job)
        self._typing_job = self._fade_job = None
