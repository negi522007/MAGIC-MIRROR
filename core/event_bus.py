"""
Bus d'événements interne (publish / subscribe), thread-safe.

Les callbacks sont appelés de façon synchrone dans le thread qui émet ; une
exception dans un callback est journalisée sans empêcher les suivants.
"""

import threading
import traceback


class EventBus:
    def __init__(self):
        self._listeners = {}
        self._lock = threading.Lock()

    def subscribe(self, event_name, callback):
        with self._lock:
            self._listeners.setdefault(event_name, []).append(callback)

    def unsubscribe(self, event_name, callback):
        with self._lock:
            if event_name in self._listeners:
                self._listeners[event_name] = [
                    cb for cb in self._listeners[event_name] if cb != callback
                ]

    def emit(self, event_name, data=None):
        with self._lock:
            callbacks = list(self._listeners.get(event_name, []))
        for callback in callbacks:
            try:
                callback(data)
            except Exception as e:
                print(f"[EventBus] Erreur dans '{event_name}' : {e}")
                traceback.print_exc()
