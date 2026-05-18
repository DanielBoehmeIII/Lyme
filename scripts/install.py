#!/usr/bin/env python3
"""Cross-platform one-command install for Lyme."""
import subprocess
import sys
import platform


def main():
    print("=" * 56)
    print(f"  Lyme Installer — {platform.system()} / Python {sys.version_info.major}.{sys.version_info.minor}")
    print("=" * 56)

    if sys.version_info < (3, 10):
        print("ERROR: Python 3.10+ required.")
        sys.exit(1)

    # Install/upgrade
    print("  Installing lyme...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", "lyme"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"ERROR: Installation failed: {result.stderr}")
        sys.exit(1)

    # Verify
    try:
        import lyme
        print(f"\n  ✓ Lyme v{lyme.__version__} installed!")
        print(f"\n  Quickstart:")
        print(f"    lyme doctor")
        print(f"    lyme ask 'What is this project?'")
        print(f"    lyme dashboard")
        print(f"    lyme start")
        print(f"\n  Docs: https://lyme.ai/docs")
    except ImportError:
        print("ERROR: Installation verification failed.")
        sys.exit(1)

    print("=" * 56)


if __name__ == "__main__":
    main()
