#!/usr/bin/env python3
"""
TEKBOT Magic Mirror — point d'entrée.

    python main.py                # plein écran, micro + caméra
    python main.py --windowed     # fenêtre (développement)
    python main.py --no-audio     # sans micro ni voix : utiliser le clavier (voir README)
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_config  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description="TEKBOT Magic Mirror")
    parser.add_argument("--config", default=None, help="chemin d'un autre config.yaml")
    parser.add_argument("--windowed", action="store_true", help="désactive le plein écran")
    parser.add_argument("--no-audio", action="store_true", help="ni micro ni synthèse vocale")
    parser.add_argument("--no-llm", action="store_true", help="réponses à base de règles uniquement")
    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config(args.config)
    if args.windowed:
        config["ui"]["fullscreen"] = False
    if args.no_llm:
        config["llm"]["enabled"] = False

    from core.app_controller import AppController
    controller = AppController(config, audio_enabled=not args.no_audio)
    controller.run()


if __name__ == "__main__":
    main()
