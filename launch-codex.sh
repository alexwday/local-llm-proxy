#!/usr/bin/env bash
# Wrapper script to launch Codex using venv Python (which has toml package)
# Run this from the local-llm-proxy directory

# Activate venv and run launch-codex.py
source venv/bin/activate
python3 launch-codex.py
