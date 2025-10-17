#!/bin/bash
# Setup script for OpenAI-Compatible LLM Proxy

set -e

echo "========================================="
echo "  LLM Proxy Setup"
echo "========================================="
echo ""

# Create venv
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate venv
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if we're on a work computer (has rbc_security)
echo ""
echo "Checking for rbc_security..."
if python3 -c "import rbc_security" 2>/dev/null; then
    echo "✓ rbc_security is installed"
else
    echo "⚠️  rbc_security not available (OK for local development)"
    echo "   On RBC work computers, run: pip install rbc_security"
fi

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created - please configure it"
else
    echo ""
    echo "✓ .env file already exists"
fi

echo ""
echo "========================================="
echo "  Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env with your configuration"
echo "  2. Run: ./run.sh (production)"
echo "  3. Or:  ./run-dev.sh (development)"
echo ""
