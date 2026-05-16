#!/usr/bin/env python3
"""Lyme — Research infrastructure for local coding agent evaluation.

Usage:
    python -m lyme run --all
    python -m lyme list-scenarios
    python -m lyme replay <trace-id>
    python -m lyme compare --scenario multi-file-edit-consistency
    python -m lyme stress repo-size
    python -m lyme ui dashboard
    python -m lyme ui thought <run-id>
"""

from lyme.cli import main

if __name__ == "__main__":
    main()
