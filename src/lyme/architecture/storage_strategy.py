"""Local storage strategy for Lyme's dual architecture.

Versioned, portable, privacy-first data format that supports both
product operations and research analysis from the same store.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timezone
import json
import gzip


SCHEMA_VERSION = "0.1.0"
SCHEMA_URL = "https://lyme.dev/schema/v0.1.0"


class SchemaVersion:
    MAJOR = 0
    MINOR = 1
    PATCH = 0

    @classmethod
    def string(cls) -> str:
        return f"{cls.MAJOR}.{cls.MINOR}.{cls.PATCH}"

    @classmethod
    def compatibility(cls, version: str) -> bool:
        try:
            parts = version.split(".")
            return int(parts[0]) == cls.MAJOR
        except (IndexError, ValueError):
            return False


@dataclass
class StorageManifest:
    schema_version: str = SCHEMA_VERSION
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    lyme_version: str = "0.1.0"
    repo_identifier: Optional[str] = None
    repo_hash: Optional[str] = None
    privacy_level: str = "internal"
    total_actions: int = 0
    data_types: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "lyme_version": self.lyme_version,
            "repo_identifier": self.repo_identifier,
            "repo_hash": self.repo_hash,
            "privacy_level": self.privacy_level,
            "total_actions": self.total_actions,
            "data_types": self.data_types,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StorageManifest":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class StorageBackend:
    """Abstract storage backend for project data."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _ensure_dir(self, *parts: str) -> Path:
        path = self.root.joinpath(*parts)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_json(self, path: Path, data: dict, compress: bool = False):
        if compress:
            path = path.with_suffix(".json.gz")
            with gzip.open(path, "wt") as f:
                json.dump(data, f, default=str)
        else:
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)

    def read_json(self, path: Path) -> Optional[dict]:
        if path.suffix == ".gz":
            with gzip.open(path, "rt") as f:
                return json.load(f)
        elif path.exists():
            with open(path) as f:
                return json.load(f)
        return None

    def list_files(self, *parts: str, suffix: str = ".json") -> List[Path]:
        target_dir = self.root.joinpath(*parts)
        if not target_dir.exists():
            return []
        return sorted(target_dir.glob(f"*{suffix}"))


class ProjectCollection:
    """A named data collection within a Lyme project."""

    def __init__(self, backend: StorageBackend, collection_name: str):
        self.backend = backend
        self.collection_name = collection_name
        self._dir = backend._ensure_dir(collection_name)

    def save(self, key: str, data: dict, compress: bool = False):
        path = self._dir / f"{key}.json"
        self.backend.write_json(path, data, compress=compress)

    def load(self, key: str) -> Optional[dict]:
        path = self._dir / f"{key}.json"
        if not path.exists():
            gz_path = path.with_suffix(".json.gz")
            if gz_path.exists():
                path = gz_path
            else:
                return None
        return self.backend.read_json(path)

    def list_keys(self) -> List[str]:
        return sorted([p.stem for p in self._dir.glob("*.json")] +
                     [p.stem.replace(".json", "") for p in self._dir.glob("*.json.gz")])

    def delete(self, key: str) -> bool:
        path = self._dir / f"{key}.json"
        if path.exists():
            path.unlink()
            return True
        gz_path = path.with_suffix(".json.gz")
        if gz_path.exists():
            gz_path.unlink()
            return True
        return False


@dataclass
class StorageStrategy:
    """Canonical storage layout for a Lyme project."""

    root: Path
    backend: StorageBackend = field(init=False)
    manifest: StorageManifest = field(default_factory=StorageManifest)

    def __post_init__(self):
        self.backend = StorageBackend(self.root)

    @property
    def graph(self) -> ProjectCollection:
        return ProjectCollection(self.backend, "graph")

    @property
    def traces(self) -> ProjectCollection:
        return ProjectCollection(self.backend, "traces")

    @property
    def runs(self) -> ProjectCollection:
        return ProjectCollection(self.backend, "runs")

    @property
    def diffs(self) -> ProjectCollection:
        return ProjectCollection(self.backend, "diffs")

    @property
    def memories(self) -> ProjectCollection:
        return ProjectCollection(self.backend, "memories")

    @property
    def benchmarks(self) -> ProjectCollection:
        return ProjectCollection(self.backend, "benchmarks")

    @property
    def invariants(self) -> ProjectCollection:
        return ProjectCollection(self.backend, "invariants")

    @property
    def causal(self) -> ProjectCollection:
        return ProjectCollection(self.backend, "causal")

    @property
    def temporal(self) -> ProjectCollection:
        return ProjectCollection(self.backend, "temporal")

    @property
    def interventions(self) -> ProjectCollection:
        return ProjectCollection(self.backend, "interventions")

    @property
    def experiments(self) -> ProjectCollection:
        return ProjectCollection(self.backend, "experiments")

    @property
    def telemetry(self) -> ProjectCollection:
        return ProjectCollection(self.backend, "telemetry")

    def save_manifest(self):
        self.backend.write_json(
            self.root / "lyme-manifest.json",
            self.manifest.to_dict(),
        )

    def load_manifest(self) -> Optional[StorageManifest]:
        data = self.backend.read_json(self.root / "lyme-manifest.json")
        if data:
            return StorageManifest.from_dict(data)
        return None

    def get_storage_summary(self) -> dict:
        return {
            "root": str(self.root),
            "schema_version": self.manifest.schema_version,
            "collections": {
                "graph": len(self.graph.list_keys()),
                "traces": len(self.traces.list_keys()),
                "runs": len(self.runs.list_keys()),
                "diffs": len(self.diffs.list_keys()),
                "memories": len(self.memories.list_keys()),
                "benchmarks": len(self.benchmarks.list_keys()),
                "invariants": len(self.invariants.list_keys()),
                "causal": len(self.causal.list_keys()),
                "temporal": len(self.temporal.list_keys()),
                "interventions": len(self.interventions.list_keys()),
                "experiments": len(self.experiments.list_keys()),
                "telemetry": len(self.telemetry.list_keys()),
            },
        }

    @staticmethod
    def init_project(path: Path, repo_identifier: Optional[str] = None) -> "StorageStrategy":
        strategy = StorageStrategy(root=path)
        strategy.manifest.repo_identifier = repo_identifier
        strategy.manifest.data_types = [
            "graph", "traces", "runs", "diffs", "memories",
            "benchmarks", "invariants", "causal", "temporal",
            "interventions", "experiments", "telemetry",
        ]
        strategy.save_manifest()

        for collection_name in strategy.manifest.data_types:
            ProjectCollection(strategy.backend, collection_name)

        return strategy


def get_default_storage(repo_path: Optional[Path] = None) -> StorageStrategy:
    root = Path("./lyme-project")
    if repo_path:
        root = repo_path / ".lyme"
    return StorageStrategy(root=root)
