"""TrialRecorder — saves and loads trial results to disk."""

from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import TrialResult, TrialRun


class TrialRecorder:
    """Persists trial results to JSON files."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.trials_dir = output_dir / "trials"
        self.runs_dir = output_dir / "runs"
        self.trials_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def save_trial(self, result: TrialResult) -> Path:
        path = self.trials_dir / f"{result.trial_id}.json"
        path.write_text(json.dumps(result.to_dict(), indent=2, default=str))
        return path

    def save_run(self, run: TrialRun) -> Path:
        run.compute_summary()
        data = {
            "run_id": run.run_id,
            "config": run.config,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "summary": run.summary,
            "results": [r.to_dict() for r in run.results],
        }
        path = self.runs_dir / f"{run.run_id}.json"
        path.write_text(json.dumps(data, indent=2, default=str))
        return path

    def load_trial(self, trial_id: str) -> Optional[dict]:
        path = self.trials_dir / f"{trial_id}.json"
        if path.exists():
            return json.loads(path.read_text())
        return None

    def load_run(self, run_id: str) -> Optional[dict]:
        path = self.runs_dir / f"{run_id}.json"
        if path.exists():
            return json.loads(path.read_text())
        return None

    def list_runs(self) -> list[dict]:
        if not self.runs_dir.exists():
            return []
        runs = []
        for path in sorted(self.runs_dir.glob("*.json")):
            data = json.loads(path.read_text())
            runs.append({
                "run_id": data.get("run_id", path.stem),
                "started_at": data.get("started_at", ""),
                "completed_at": data.get("completed_at", ""),
                "summary": data.get("summary", {}),
            })
        return sorted(runs, key=lambda r: r.get("started_at", ""), reverse=True)

    def list_trials(self) -> list[dict]:
        if not self.trials_dir.exists():
            return []
        trials = []
        for path in sorted(self.trials_dir.glob("*.json")):
            data = json.loads(path.read_text())
            trials.append({
                "trial_id": data.get("trial_id", path.stem),
                "task_id": data.get("task_id", ""),
                "title": data.get("title", ""),
                "status": data.get("status", ""),
                "verdict": data.get("verdict", ""),
                "score": data.get("score", 0),
                "duration_s": data.get("duration_s", 0),
                "timestamp": data.get("timestamp", ""),
            })
        return sorted(trials, key=lambda r: r.get("timestamp", ""), reverse=True)
