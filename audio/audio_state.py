"""
État audio partagé (anti-larsen) : tant que la synthèse vocale parle, et pendant un
court instant après, le micro ignore ce qu'il entend pour ne pas se reconnaître
lui-même.
"""

import time


class AudioState:
    ECHO_TAIL = 0.35  # s ignorées après la fin de la parole (écho de la pièce)

    def __init__(self):
        self._speaking = False
        self._mute_until = 0.0

    @property
    def tts_speaking(self):
        return self._speaking

    @tts_speaking.setter
    def tts_speaking(self, value):
        self._speaking = bool(value)
        if not value:
            self._mute_until = time.monotonic() + self.ECHO_TAIL

    def mic_muted(self):
        return self._speaking or time.monotonic() < self._mute_until
