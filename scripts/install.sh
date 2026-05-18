#!/usr/bin/env bash
set -euo pipefail

LYME_VERSION="${LYME_VERSION:-1.0.0-rc1}"
INSTALL_DIR="${LYME_DIR:-$HOME/.lyme}"
PYTHON="${PYTHON:-python3}"

echo "========================================"
echo "  Lyme v${LYME_VERSION} — One-Command Install"
echo "========================================"

# ── Diagnostics ──
FAILURES=""

check_python() {
    if ! command -v "$PYTHON" &>/dev/null; then
        echo "  ✗ Python not found at '$PYTHON'"
        FAILURES="$FAILURES python_not_found"
        return 1
    fi
    local ver
    ver=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0.0")
    local major="${ver%%.*}"
    local minor="${ver#*.}"
    echo "  Python: $ver"
    if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 10 ]; }; then
        echo "  ✗ Python 3.10+ required (got $ver)"
        FAILURES="$FAILURES python_version"
        return 1
    fi
    echo "  ✓ Python version OK"
    return 0
}

check_pip() {
    if ! $PYTHON -m pip --version &>/dev/null; then
        echo "  ✗ pip not available for $PYTHON"
        FAILURES="$FAILURES pip_not_found"
        return 1
    fi
    echo "  ✓ pip available"
    return 0
}

check_git() {
    if command -v git &>/dev/null; then
        echo "  ✓ git available"
        return 0
    fi
    echo "  ~ git not found (optional, for repo operations)"
    return 0
}

echo ""
echo "  Checking prerequisites..."
check_python || true
check_pip || true
check_git || true

if echo "$FAILURES" | grep -q "python"; then
    echo ""
    echo "  FALLBACK: Attempting to find python3 alternative..."
    for alt in python3.11 python3.12 python3.10 python; do
        if command -v "$alt" &>/dev/null; then
            local_ver=$($alt -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0.0")
            local_major="${local_ver%%.*}"
            local_minor="${local_ver#*.}"
            if [ "$local_major" -eq 3 ] && [ "$local_minor" -ge 10 ]; then
                echo "  ✓ Found alternative: $alt ($local_ver)"
                PYTHON="$alt"
                FAILURES=""
                break
            fi
        fi
    done
fi

# ── Install ──
echo ""
echo "  Installing lyme..."

$PYTHON -m pip install --quiet --upgrade pip 2>/dev/null || true

if $PYTHON -c "import lyme" 2>/dev/null; then
    echo "  Lyme already installed. Upgrading..."
    $PYTHON -m pip install --quiet --upgrade lyme 2>/dev/null || {
        echo "  Upgrading from source..."
        $PYTHON -m pip install --quiet --upgrade -e "$(dirname "$0")/.." 2>/dev/null || true
    }
else
    $PYTHON -m pip install --quiet lyme 2>/dev/null || {
        echo "  Installing from source..."
        $PYTHON -m pip install --quiet -e "$(dirname "$0")/.." 2>/dev/null || {
            echo "  ERROR: Installation failed. See diagnostics below."
            FAILURES="$FAILURES install_failed"
        }
    }
fi

# ── Verify ──
echo ""
echo "  Verifying..."
if $PYTHON -c "import lyme; print(f'Lyme v{lyme.__version__}')" 2>/dev/null; then
    INSTALLED_VERSION=$($PYTHON -c "import lyme; print(lyme.__version__)")
    echo ""
    echo "  ✓ Lyme v${INSTALLED_VERSION} installed!"
    echo ""
    echo "  Quickstart:"
    echo "    lyme doctor              # Diagnose current repo"
    echo "    lyme heal                # Fix issues in one command"
    echo "    lyme v1-audit            # Check v1 readiness"
    echo "    lyme --help              # See all commands"
    echo ""
    echo "  Next: run 'lyme start' for interactive setup"
    echo "========================================"
else
    echo "  ERROR: Verification failed."
    FAILURES="$FAILURES verify_failed"
fi

# ── Report ──
if [ -n "$FAILURES" ]; then
    echo ""
    echo "  Install Diagnostics:"
    for f in $FAILURES; do
        case "$f" in
            python_not_found) echo "  ✗ Python not found. Install Python 3.10+ from https://python.org" ;;
            python_version)   echo "  ✗ Python 3.10+ required. Upgrade your Python installation." ;;
            pip_not_found)    echo "  ✗ pip not found. Run: $PYTHON -m ensurepip" ;;
            install_failed)   echo "  ✗ pip install failed. Check network or try: pip install --user lyme" ;;
            verify_failed)    echo "  ✗ Import verification failed. Try: $PYTHON -c 'import lyme'" ;;
        esac
    done
    echo ""
    echo "  Run diagnostics: $PYTHON -m lyme doctor --install"
    exit 1
fi
