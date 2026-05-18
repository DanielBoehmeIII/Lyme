#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-python3}"

echo "========================================"
echo "  Lyme Uninstall"
echo "========================================"

# Uninstall package
echo "  Removing lyme package..."
$PYTHON -m pip uninstall -y lyme 2>/dev/null || echo "  ~ Lyme not installed via pip"

# Remove .lyme directory
LYME_DIR="${LYME_DIR:-$HOME/.lyme}"
if [ -d "$LYME_DIR" ]; then
    echo "  Removing $LYME_DIR..."
    rm -rf "$LYME_DIR"
fi

# Remove config files
for dir in "$HOME/.config/lyme" "$HOME/.local/share/lyme"; do
    if [ -d "$dir" ]; then
        echo "  Removing $dir..."
        rm -rf "$dir"
    fi
done

echo ""
echo "  ✓ Lyme uninstalled."
echo "========================================"
