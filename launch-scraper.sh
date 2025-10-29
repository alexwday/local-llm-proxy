#!/bin/bash
# Quick launcher for Web Scraping Agent

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Use the venv python
"$SCRIPT_DIR/venv/bin/python3" "$SCRIPT_DIR/launch-scraper.py"
