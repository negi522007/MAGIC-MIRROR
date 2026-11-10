"""
Configuration du miroir magique.

Les valeurs par défaut sont définies ici ; `config.yaml` ne surcharge que ce qu'il
contient (fusion récursive). Tout chemin relatif est résolu depuis la racine du projet.
"""

import copy
import os

import yaml

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

DEFAULTS = {
    "audio": {
        "device_id": None,          # micro (None = périphérique par défaut)
        "output_device_id": None,   # haut-parleur (None = par défaut)
        "sample_rate": 16000,
        "block_size": 4000,         # 0,25 s par bloc : bon compromis latence / CPU
    },
    "models": {
        "vosk": "models/vosk-model-small-fr-0.22",
        "face": "models/face_detection_yunet_2023mar.onnx",
        "piper_voice": "models/piper/fr_FR-siwis-medium.onnx",
        "coqui": "tts_models/fr/css10/vits",
        "llm": "models/llm/Qwen3.5-2B-Q4_K_M.gguf",
    },
    "tts": {
        # Ordre d'essai des moteurs ; le premier disponible est utilisé.
        "backends": ["piper", "coqui", "pyttsx3"],
        "length_scale": 1.0,        # Piper : >1 = plus lent
    },
    "llm": {
        "enabled": True,            # ignoré si le modèle ou llama-cpp-python est absent
        "n_threads": 3,
        "n_ctx": 1024,
        "max_tokens": 90,
        "temperature": 0.6,
        "timeout": 12,              # au-delà, on garde la réponse à base de règles
        # Reformuler aussi les conseils de style par le LLM ? Désactivé : en test, Qwen3.5-2B
        # perdait les conseils concrets et ajoutait plusieurs secondes (docs/JOURNAL.md).
        "rephrase_style": False,
    },
    "camera": {
        "index": 0,
        "width": 640,
        "height": 480,
        "fps": 15,
        "fourcc": "MJPG",           # format demandé à la webcam ("" = format par défaut)
    },
    "vision": {
        "detect_interval": 0.4,     # s entre deux détections quand quelqu'un est là
        "idle_detect_interval": 1.0,  # s entre deux détections en veille
        "detect_width": 320,        # la détection travaille sur une image réduite
    },
    "context": {
        "climate": "temperate",     # "temperate" (4 saisons) ou "tropical" (Bénin...)
    },
    "ui": {
        "fullscreen": True,
        "fps": 20,
        "overlay_fade_delay": 8000,
        "typing_speed": 25,
        "sleep_after": 60,          # s sans visage avant de masquer l'image caméra
        "show_face_box": True,
    },
    "wake_word": {
        "phrase": "miroir magique",
        "cooldown": 3,
        "use_grammar": True,        # restreint Vosk à la phrase : plus fiable et moins de CPU
    },
    "stt": {
        "timeout": 8,               # s d'attente d'une phrase après le mot clé
    },
}


def _deep_merge(base, override):
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def resolve_path(path):
    """Chemin absolu depuis la racine du projet (laisse les chemins absolus intacts)."""
    if not path:
        return path
    if os.path.isabs(path):
        return path
    return os.path.join(PROJECT_ROOT, path)


def load_config(path=None):
    """Charge config.yaml et le fusionne avec DEFAULTS."""
    config = copy.deepcopy(DEFAULTS)
    path = path or os.path.join(PROJECT_ROOT, "config.yaml")
    if not os.path.exists(path):
        print(f"[CONFIG] '{path}' introuvable, valeurs par défaut utilisées.")
        return config
    with open(path, "r", encoding="utf-8") as f:
        user_config = yaml.safe_load(f) or {}
    return _deep_merge(config, user_config)
