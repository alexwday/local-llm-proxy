#!/bin/bash
# Wrapper script to launch Codex using venv Python (which has toml package)

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate venv and run launch-codex.py
source "$SCRIPT_DIR/venv/bin/activate"
python3 "$SCRIPT_DIR/launch-codex.py"
