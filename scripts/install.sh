#!/usr/bin/env bash
# Installation du miroir magique (Linux, testé sous Ubuntu / Debian).
#
#   ./scripts/install.sh              # dépendances + modèles (Vosk, YuNet, voix Piper)
#   ./scripts/install.sh --with-llm   # + IA locale (llama-cpp-python + Qwen3.5-2B, ~1,3 Go)
#
# Idempotent : un modèle déjà présent n'est pas retéléchargé.
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
WITH_LLM=0
[[ "${1:-}" == "--with-llm" ]] && WITH_LLM=1

VOSK_URL="https://alphacephei.com/vosk/models/vosk-model-small-fr-0.22.zip"
YUNET_URL="https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
PIPER_BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium"
LLM_URL="https://huggingface.co/unsloth/Qwen3.5-2B-GGUF/resolve/main/Qwen3.5-2B-Q4_K_M.gguf"

echo "== Paquets système (portaudio pour le micro, tkinter pour l'interface)"
if command -v apt-get >/dev/null; then
    sudo apt-get install -y python3-venv python3-tk libportaudio2 unzip wget
fi

echo "== Environnement Python (.venv)"
if [[ ! -d .venv ]]; then
    python3 -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

download() {  # download <url> <destination>
    if [[ -s "$2" ]]; then
        echo "   déjà présent : $2"
    else
        mkdir -p "$(dirname "$2")"
        wget -q --show-progress -O "$2.part" "$1" && mv "$2.part" "$2"
    fi
}

echo "== Modèle de reconnaissance vocale (Vosk FR small 0.22, 41 Mo)"
if [[ ! -d models/vosk-model-small-fr-0.22 ]]; then
    download "$VOSK_URL" models/vosk-model-small-fr-0.22.zip
    (cd models && unzip -q vosk-model-small-fr-0.22.zip)
fi

echo "== Détecteur de visage (YuNet 2023mar, 230 Ko)"
download "$YUNET_URL" models/face_detection_yunet_2023mar.onnx

echo "== Voix française Piper (siwis medium, 63 Mo)"
download "$PIPER_BASE/fr_FR-siwis-medium.onnx" models/piper/fr_FR-siwis-medium.onnx
download "$PIPER_BASE/fr_FR-siwis-medium.onnx.json" models/piper/fr_FR-siwis-medium.onnx.json

if [[ $WITH_LLM -eq 1 ]]; then
    echo "== IA locale : llama-cpp-python (compilation CPU, quelques minutes)"
    .venv/bin/python -m pip install -r requirements-llm.txt
    echo "== Modèle Qwen3.5-2B Q4_K_M (1,3 Go)"
    download "$LLM_URL" models/llm/Qwen3.5-2B-Q4_K_M.gguf
fi

echo
echo "✅ Installation terminée dans $ROOT"
echo "   Trouver le micro :   .venv/bin/python scripts/find_micro.py  (puis audio.device_id dans config.yaml)"
echo "   Lancer le miroir :   ./scripts/run.sh"
