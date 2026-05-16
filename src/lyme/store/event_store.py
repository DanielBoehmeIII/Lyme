import json
import os
import gzip
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone


class EventStore:
    def __init__(self, base_dir: str = "./lyme-output"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "runs").mkdir(exist_ok=True)
        (self.base_dir / "traces").mkdir(exist_ok=True)
        (self.base_dir / "metrics").mkdir(exist_ok=True)
        (self.base_dir / "replays").mkdir(exist_ok=True)
        (self.base_dir / "cognition").mkdir(exist_ok=True)

    def save_run(self, run_id: str, data: dict):
        path = self.base_dir / "runs" / f"{run_id}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def load_run(self, run_id: str) -> Optional[dict]:
        path = self.base_dir / "runs" / f"{run_id}.json"
        if not path.exists():
            return None
        with open(path) as f:
            return json.load(f)

    def save_trace(self, trace_id: str, data: dict, compress: bool = False):
        path = self.base_dir / "traces" / f"{trace_id}.json"
        if compress:
            path = path.with_suffix(".json.gz")
            with gzip.open(path, "wt") as f:
                json.dump(data, f, default=str)
        else:
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)

    def load_trace(self, trace_id: str) -> Optional[dict]:
        path = self.base_dir / "traces" / f"{trace_id}.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        gz_path = path.with_suffix(".json.gz")
        if gz_path.exists():
            with gzip.open(gz_path, "rt") as f:
                return json.load(f)
        return None

    def save_metrics(self, run_id: str, metrics: list):
        path = self.base_dir / "metrics" / f"{run_id}.json"
        with open(path, "w") as f:
            json.dump(metrics, f, indent=2, default=str)

    def save_cognitive_trace(self, trace_id: str, data: dict):
        path = self.base_dir / "cognition" / f"{trace_id}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def load_cognitive_trace(self, trace_id: str) -> Optional[dict]:
        path = self.base_dir / "cognition" / f"{trace_id}.json"
        if not path.exists():
            return None
        with open(path) as f:
            return json.load(f)

    def list_runs(self) -> List[str]:
        return sorted([p.stem for p in (self.base_dir / "runs").glob("*.json")])

    def list_traces(self) -> List[str]:
        return sorted([p.stem for p in (self.base_dir / "traces").glob("*.json")])

    def get_run_path(self, run_id: str) -> Path:
        return self.base_dir / "runs" / f"{run_id}.json"
