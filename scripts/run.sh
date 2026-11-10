#!/usr/bin/env bash
# Lance le miroir avec l'environnement du projet. Les options sont transmises à main.py :
#   ./scripts/run.sh --windowed --no-audio
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
[[ -x "$PY" ]] || PY=python3
exec "$PY" main.py "$@"
