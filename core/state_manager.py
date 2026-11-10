"""
Machine à états du miroir : idle → listening → processing → speaking → idle.

Chaque changement valide est publié sur le bus (`state_changed`, avec le nom du
nouvel état) : c'est le seul endroit qui émet cet événement.
"""
import threading


class MirrorState:
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"

    VALID_TRANSITIONS = {
        IDLE: [LISTENING, PROCESSING],
        LISTENING: [PROCESSING, IDLE],
        PROCESSING: [SPEAKING, IDLE],
        SPEAKING: [IDLE, LISTENING],
    }


class StateManager:
    def __init__(self, bus=None):
        self._state = MirrorState.IDLE
        self._lock = threading.Lock()
        self.bus = bus

    @property
    def current_state(self):
        return self._state

    def set_state(self, new_state, force=False):
        with self._lock:
            old = self._state
            if new_state == old:
                return True
            if not force and new_state not in MirrorState.VALID_TRANSITIONS.get(old, []):
                print(f"[STATE] Transition invalide : {old} -> {new_state}")
                return False
            self._state = new_state
        print(f"[STATE] {old} -> {new_state}")
        if self.bus:
            self.bus.emit("state_changed", new_state)
        return True

    def try_begin(self, from_state, to_state):
        """Passe de from_state à to_state seulement si l'état courant est from_state.

        Évite qu'un second mot clé (ou une touche) relance un cycle déjà en cours.
        """
        with self._lock:
            if self._state != from_state:
                return False
            self._state = to_state
        print(f"[STATE] {from_state} -> {to_state}")
        if self.bus:
            self.bus.emit("state_changed", to_state)
        return True

    def is_idle(self):
        return self._state == MirrorState.IDLE

    def is_listening(self):
        return self._state == MirrorState.LISTENING

    def is_processing(self):
        return self._state == MirrorState.PROCESSING

    def is_speaking(self):
        return self._state == MirrorState.SPEAKING
