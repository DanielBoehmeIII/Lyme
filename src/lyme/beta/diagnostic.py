from __future__ import annotations
from pathlib import Path
from typing import Optional
import json
import time
import platform
import subprocess
import shutil


class DiagnosticBundle:
    """Send diagnostic bundle — collects system info, config, logs."""

    DIAG_DIR = Path(".lyme") / "diagnostics"

    def __init__(self):
        self.DIAG_DIR.mkdir(parents=True, exist_ok=True)

    def collect(self) -> dict:
        bundle = {
            "id": f"DIAG-{int(time.time())}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "lyme_version": self._get_version(),
            "git": self._get_git_info(),
            "lyme_config": self._get_config_files(),
            "recent_logs": self._get_recent_logs(),
            "model_runs": self._count_model_runs(),
        }

        path = self.DIAG_DIR / f"{bundle['id']}.json"
        path.write_text(json.dumps(bundle, indent=2))
        return bundle

    def _get_version(self) -> str:
        try:
            import lyme
            return getattr(lyme, "__version__", "unknown")
        except Exception:
            return "unknown"

    def _get_git_info(self) -> dict:
        try:
            log = subprocess.run(["git", "log", "--oneline", "-5"],
                                  capture_output=True, text=True, timeout=5)
            branch = subprocess.run(["git", "branch", "--show-current"],
                                     capture_output=True, text=True, timeout=5)
            return {
                "branch": branch.stdout.strip(),
                "recent_commits": log.stdout.strip(),
            }
        except Exception:
            return {"error": "not a git repo"}

    def _get_config_files(self) -> dict:
        configs = {}
        for pattern in ["pyproject.toml", ".lyme/config.json", "lyme-config.json", "config/lyme.yml"]:
            p = Path(pattern)
            if p.exists():
                try:
                    configs[pattern] = p.read_text()[:500]
                except Exception:
                    configs[pattern] = "(unreadable)"
        return configs

    def _get_recent_logs(self) -> list:
        log_dir = Path(".lyme") / "logs"
        if not log_dir.exists():
            return []
        logs = sorted(log_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
        result = []
        for l in logs:
            try:
                result.append(f"{l.name}: {l.read_text()[:200]}")
            except Exception:
                pass
        return result

    def _count_model_runs(self) -> int:
        runs_dir = Path(".lyme") / "model-runs"
        if runs_dir.exists():
            return len(list(runs_dir.glob("*.json")))
        return 0

    def print_bundle(self, bundle: dict):
        print(f"{'='*60}")
        print(f"  DIAGNOSTIC BUNDLE")
        print(f"{'='*60}")
        print(f"  ID: {bundle['id']}")
        print(f"  Time: {bundle['timestamp']}")
        print(f"  Platform: {bundle['platform']}")
        print(f"  Python: {bundle['python_version']}")
        print(f"  Lyme: {bundle['lyme_version']}")
        print(f"  Git branch: {bundle.get('git', {}).get('branch', '?')}")
        print(f"  Model runs: {bundle.get('model_runs', 0)}")
        print(f"  Config files: {len(bundle.get('lyme_config', {}))}")
        print(f"  Bundle saved: {self.DIAG_DIR / bundle['id']}.json")
        print(f"{'='*60}")


diagnostic = DiagnosticBundle()
