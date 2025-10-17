#!/bin/bash
# Run the proxy in development mode (bypasses OAuth and rbc_security)

source venv/bin/activate
DEV_MODE=true python proxy.py
