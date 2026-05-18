#!/usr/bin/env bash
set -euo pipefail

echo "=== Lyme Developer Setup ==="
echo ""

LYME_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$LYME_DIR"

# Check Python version
PYTHON=$(command -v python3 || command -v python)
if [ -z "$PYTHON" ]; then
    echo "ERROR: Python 3.10+ is required"
    exit 1
fi

echo "Python: $($PYTHON --version)"

# Create virtual environment if not present
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON -m venv .venv
fi

source .venv/bin/activate

# Install in development mode
echo "Installing Lyme (editable)..."
pip install -e ".[dev,ml]" 2>/dev/null || pip install -e ".[dev]" 2>/dev/null || pip install -e .

# Create .lyme directory
mkdir -p "$LYME_DIR/.lyme"

# Verify installation
echo ""
echo "=== Verification ==="
python -c "import lyme; print(f'Lyme v{lyme.__version__}')" 2>/dev/null || echo "WARNING: lyme import failed"
python -c "from lyme.core import ArchitectureLayers; print(f'Layers: {[l.name for l in ArchitectureLayers().all()]}')"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Quick start:"
echo "  source .venv/bin/activate"
echo "  lyme --help"
echo "  lyme init ."
echo "  lyme doctor"
echo "  lyme run --all"
echo "  lyme plugin list"
echo ""
echo "Run tests:"
echo "  pytest tests/"
