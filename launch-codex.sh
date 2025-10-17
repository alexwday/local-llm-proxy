#!/usr/bin/env bash
# Wrapper script to launch Codex using venv Python (which has toml package)
# Can be run from any directory

# Get the directory where this script is located (works on macOS)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Activate venv and run launch-codex.py
source "$SCRIPT_DIR/venv/bin/activate"
python3 "$SCRIPT_DIR/launch-codex.py"
