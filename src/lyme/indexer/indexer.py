"""RepoIndexer — incremental repo indexer with snapshots and delta tracking."""
from __future__ import annotations
import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from lyme.parser import SymbolIndex, Symbol
from lyme.parser.python import PythonParser
from lyme.parser.js import JSParser
from lyme.parser.imports import ImportResolver, ImportGraph


@dataclass
class IndexConfig:
    repo_root: str = "."
    include_extensions: Set[str] = field(default_factory=lambda: {
        ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    })
    exclude_dirs: Set[str] = field(default_factory=lambda: {
        ".git", "__pycache__", "node_modules", ".venv", "venv",
        ".tox", "build", "dist", ".egg-info", ".lyme",
    })
    snapshot_dir: str = ".lyme/index"
    auto_snapshot: bool = True
    max_file_size: int = 1024 * 1024  # 1MB


@dataclass
class IndexSnapshot:
    version: str = "1.0.0"
    timestamp: float = 0.0
    file_count: int = 0
    symbol_count: int = 0
    file_hashes: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "file_count": self.file_count,
            "symbol_count": self.symbol_count,
            "file_hashes": self.file_hashes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> IndexSnapshot:
        return cls(
            version=data.get("version", "1.0.0"),
            timestamp=data.get("timestamp", 0.0),
            file_count=data.get("file_count", 0),
            symbol_count=data.get("symbol_count", 0),
            file_hashes=data.get("file_hashes", {}),
        )


@dataclass
class IndexDelta:
    added_files: List[str] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)
    removed_files: List[str] = field(default_factory=list)
    total_changes: int = 0

    @property
    def has_changes(self) -> bool:
        return self.total_changes > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "added": len(self.added_files),
            "modified": len(self.modified_files),
            "removed": len(self.removed_files),
            "total": self.total_changes,
        }


class RepoIndexer:
    def __init__(self, config: IndexConfig = None):
        self.config = config or IndexConfig()
        self.symbol_index = SymbolIndex()
        self.import_graph = ImportGraph()
        self.import_resolver = ImportResolver(self.config.repo_root)
        self._python_parser = PythonParser()
        self._js_parser = JSParser()
        self._file_hashes: Dict[str, str] = {}
        self._last_snapshot: Optional[IndexSnapshot] = None

    def index(self, repo_path: Optional[str] = None) -> IndexDelta:
        repo_path = repo_path or self.config.repo_root
        root = Path(repo_path).resolve()

        if not root.exists():
            raise FileNotFoundError(f"Repository path does not exist: {root}")

        self.config.repo_root = str(root)
        self.import_resolver = ImportResolver(str(root))

        # Find files
        files = self._discover_files(root)
        delta = IndexDelta()

        for file_path in files:
            rel_path = str(Path(file_path).relative_to(root))
            current_hash = self._file_hash(file_path)
            prev_hash = self._file_hashes.get(rel_path)

            if rel_path not in self._file_hashes:
                delta.added_files.append(rel_path)
            elif current_hash != prev_hash:
                delta.modified_files.append(rel_path)
            self._file_hashes[rel_path] = current_hash

        # Detect removed files
        old_files = set(self._file_hashes.keys())
        new_files = {str(Path(f).relative_to(root)) for f in files}
        delta.removed_files = list(old_files - new_files)

        # Remove deleted files from index
        for f in delta.removed_files:
            self.symbol_index.remove_file(f)
            del self._file_hashes[f]

        # Parse files
        file_imports: Dict[str, List[str]] = {}
        for file_path in files:
            rel_path = str(Path(file_path).relative_to(root))

            if rel_path in delta.removed_files:
                continue

            if delta.added_files or delta.modified_files:
                if rel_path in delta.added_files or rel_path in delta.modified_files:
                    self.symbol_index.remove_file(rel_path)

            if rel_path not in delta.removed_files:
                index = self._parse_file(file_path, rel_path)
                if index:
                    self.symbol_index.add_file(index)
                    file_imports[rel_path] = index.imports

        # Build import graph
        self.import_graph = self.import_resolver.build_graph(file_imports)

        delta.total_changes = len(delta.added_files) + len(delta.modified_files) + len(delta.removed_files)

        # Snapshot
        if self.config.auto_snapshot:
            self.save_snapshot()

        return delta

    def _discover_files(self, root: Path) -> List[str]:
        files = []
        for f in root.rglob("*"):
            if not f.is_file():
                continue
            if any(d in f.parts for d in self.config.exclude_dirs):
                continue
            if f.suffix in self.config.include_extensions:
                if f.stat().st_size <= self.config.max_file_size:
                    files.append(str(f))
        files.sort()
        return files

    def _parse_file(self, file_path: str, rel_path: str):
        ext = Path(file_path).suffix
        if ext in (".py", ".pyi"):
            return self._python_parser.parse_file(file_path)
        elif ext in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"):
            return self._js_parser.parse_file(file_path)
        return None

    def _file_hash(self, file_path: str) -> str:
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""

    def incremental_index(self, repo_path: Optional[str] = None) -> IndexDelta:
        self.load_latest_snapshot()
        return self.index(repo_path)

    def save_snapshot(self, name: Optional[str] = None) -> str:
        snap_dir = Path(self.config.repo_root) / self.config.snapshot_dir
        snap_dir.mkdir(parents=True, exist_ok=True)

        snapshot = IndexSnapshot(
            timestamp=time.time(),
            file_count=len(self._file_hashes),
            symbol_count=self.symbol_index.symbol_count(),
            file_hashes=self._file_hashes,
        )

        filename = name or f"snapshot_{int(time.time())}.json"
        path = snap_dir / filename
        path.write_text(json.dumps(snapshot.to_dict(), indent=2))

        self._last_snapshot = snapshot
        return str(path)

    def load_latest_snapshot(self) -> Optional[IndexSnapshot]:
        snap_dir = Path(self.config.repo_root) / self.config.snapshot_dir
        if not snap_dir.exists():
            return None

        snaps = sorted(snap_dir.glob("snapshot_*.json"), reverse=True)
        if not snaps:
            return None

        data = json.loads(snaps[0].read_text())
        snapshot = IndexSnapshot.from_dict(data)
        self._file_hashes = snapshot.file_hashes
        self._last_snapshot = snapshot
        return snapshot

    def list_snapshots(self) -> List[Dict[str, Any]]:
        snap_dir = Path(self.config.repo_root) / self.config.snapshot_dir
        if not snap_dir.exists():
            return []
        snaps = []
        for path in sorted(snap_dir.glob("snapshot_*.json"), reverse=True):
            try:
                data = json.loads(path.read_text())
                snaps.append({
                    "path": str(path),
                    "timestamp": datetime.fromtimestamp(data.get("timestamp", 0)).isoformat(),
                    "files": data.get("file_count", 0),
                    "symbols": data.get("symbol_count", 0),
                })
            except Exception:
                continue
        return snaps

    def compute_delta(self, since_snapshot: Optional[str] = None) -> IndexDelta:
        snap_dir = Path(self.config.repo_root) / self.config.snapshot_dir

        if since_snapshot:
            path = snap_dir / since_snapshot
            if not path.exists():
                return IndexDelta()
            data = json.loads(path.read_text())
            old_hashes = data.get("file_hashes", {})
        elif self._last_snapshot:
            old_hashes = self._last_snapshot.file_hashes
        else:
            return IndexDelta()

        new_hashes = self._file_hashes
        delta = IndexDelta()

        for fp in set(list(new_hashes.keys()) + list(old_hashes.keys())):
            if fp in new_hashes and fp not in old_hashes:
                delta.added_files.append(fp)
            elif fp in old_hashes and fp not in new_hashes:
                delta.removed_files.append(fp)
            elif new_hashes.get(fp) != old_hashes.get(fp):
                delta.modified_files.append(fp)

        delta.total_changes = len(delta.added_files) + len(delta.modified_files) + len(delta.removed_files)
        return delta

    def get_stats(self) -> Dict[str, Any]:
        return {
            "files_indexed": self.symbol_index.file_count(),
            "symbols_indexed": self.symbol_index.symbol_count(),
            "import_graph_nodes": len(self.import_graph.nodes),
            "import_graph_edges": len(self.import_graph.edges),
            "import_cycles": len(self.import_graph.cycles),
            "snapshots_available": len(self.list_snapshots()),
        }

    def clear(self) -> None:
        self.symbol_index.clear()
        self.import_graph = ImportGraph()
        self._file_hashes.clear()
