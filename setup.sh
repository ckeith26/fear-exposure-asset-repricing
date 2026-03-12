#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment already exists at $VENV_DIR"
    echo "To recreate, delete it first: rm -rf $VENV_DIR"
    exit 1
fi

echo "Creating virtual environment..."
python3 -m venv "$VENV_DIR"

echo "Installing requirements..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
source "$VENV_DIR/bin/activate"
echo ".venv activated"
echo ""
echo "Setup complete. Activate with:"
echo "  source $VENV_DIR/bin/activate"
