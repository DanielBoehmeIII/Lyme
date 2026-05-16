import json
import time
import hashlib
import re
import os
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum
from pathlib import Path


class EntryType(str, Enum):
    AGENT_TRACE = "agent_trace"
    BENCHMARK_RUN = "benchmark_run"
    SEMANTIC_DIFF = "semantic_diff"
    FAILURE_CASE = "failure_case"
    VERIFICATION_GRAPH = "verification_graph"
    MEMORY_EXPERIMENT = "memory_experiment"
    COORDINATION_EXPERIMENT = "coordination_experiment"
    ABLATION_RESULT = "ablation_result"


@dataclass
class ReproducibilityMetadata:
    python_version: str = ""
    lyme_version: str = "0.7.0"
    model_name: str = ""
    model_version: str = ""
    random_seed: int = 42
    environment_hash: str = ""
    dependencies: Dict[str, str] = field(default_factory=dict)
    hardware_info: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CorpusEntry:
    entry_id: str = ""
    entry_type: str = EntryType.AGENT_TRACE
    title: str = ""
    description: str = ""
    created_at: float = field(default_factory=time.time)
    data: dict = field(default_factory=dict)
    reproducibility: ReproducibilityMetadata = field(default_factory=ReproducibilityMetadata)
    tags: List[str] = field(default_factory=list)
    source_hash: str = ""
    parent_entry_id: Optional[str] = None
    citations: List[str] = field(default_factory=list)

    def compute_hash(self) -> str:
        raw = json.dumps(self.data, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "entry_type": self.entry_type,
            "title": self.title,
            "description": self.description,
            "created_at": self.created_at,
            "data": self.data,
            "reproducibility": self.reproducibility.to_dict(),
            "tags": self.tags,
            "source_hash": self.source_hash or self.compute_hash(),
            "parent_entry_id": self.parent_entry_id,
            "citations": self.citations,
        }


@dataclass
class CorpusConfig:
    output_dir: str = "lyme-output/research-corpus"
    anonymize: bool = True
    max_entry_size_mb: int = 10
    require_opt_in: bool = True
    redact_patterns: List[str] = field(default_factory=lambda: [
        r'api[_-]?key[s]?["\']?\s*[:=]\s*["\'][^"\']+["\']',
        r'token["\']?\s*[:=]\s*["\'][^"\']+["\']',
        r'password["\']?\s*[:=]\s*["\'][^"\']+["\']',
        r'secret["\']?\s*[:=]\s*["\'][^"\']+["\']',
        r'private_key["\']?\s*[:=]\s*["\'][^"\']+["\']',
        r'ghp_[A-Za-z0-9]{36}',
        r'sk-[A-Za-z0-9]{32,}',
        r'(https?://)?github\.com/[^/\s]+/[^/\s]+',
    ])

    def to_dict(self) -> dict:
        return asdict(self)


class PrivacyRedactor:
    def __init__(self, patterns: List[str]):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in patterns]

    def redact(self, text: str) -> str:
        for pattern in self.patterns:
            text = pattern.sub("[REDACTED]", text)
        return text

    def redact_dict(self, data: dict) -> dict:
        result = {}
        for k, v in data.items():
            if isinstance(v, str):
                result[k] = self.redact(v)
            elif isinstance(v, dict):
                result[k] = self.redact_dict(v)
            elif isinstance(v, list):
                result[k] = [self.redact_dict(i) if isinstance(i, dict)
                             else self.redact(i) if isinstance(i, str) else i
                             for i in v]
            else:
                result[k] = v
        return result


class RedactionPipeline:
    def __init__(self, config: CorpusConfig):
        self.redactor = PrivacyRedactor(config.redact_patterns)
        self.config = config

    def process(self, entry: CorpusEntry) -> CorpusEntry:
        if not self.config.anonymize:
            return entry
        entry.data = self.redactor.redact_dict(entry.data)
        entry.title = self.redactor.redact(entry.title)
        entry.description = self.redactor.redact(entry.description)
        entry.tags = [self.redactor.redact(t) for t in entry.tags]
        return entry


class CitationFormatter:
    @staticmethod
    def format_for_paper(entry: CorpusEntry) -> str:
        return (f"Lyme Research Corpus, {entry.entry_id}, "
                f"\"{entry.title}\", {entry.entry_type}, "
                f"{time.strftime('%Y-%m-%d', time.gmtime(entry.created_at))}")

    @staticmethod
    def format_bibtex(entry: CorpusEntry) -> str:
        entry_id_clean = re.sub(r'[^a-zA-Z0-9]', '', entry.entry_id)[:20]
        return (
            f"@misc{{lyme:{entry_id_clean},\n"
            f"  author = {{Lyme Research Project}},\n"
            f"  title = {{{entry.title}}},\n"
            f"  howpublished = {{Lyme Research Corpus}},\n"
            f"  year = {{{time.strftime('%Y', time.gmtime(entry.created_at))}}},\n"
            f"  note = {{Entry {entry.entry_id}, type: {entry.entry_type}}}\n"
            f"}}"
        )


class ResearchCorpus:
    def __init__(self, config: Optional[CorpusConfig] = None):
        self.config = config or CorpusConfig()
        self.pipeline = RedactionPipeline(self.config)
        self.formatter = CitationFormatter()
        self.entries: List[CorpusEntry] = []

    def add_entry(self, entry: CorpusEntry) -> str:
        if self.config.require_opt_in:
            if not entry.source_hash:
                raise ValueError("opt-in required: source_hash must be set")
        entry.entry_id = entry.entry_id or f"corpus-{int(time.time())}-{len(self.entries)}"
        processed = self.pipeline.process(entry)
        self.entries.append(processed)
        self._save_entry(processed)
        return processed.entry_id

    def _save_entry(self, entry: CorpusEntry):
        output = Path(self.config.output_dir)
        output.mkdir(parents=True, exist_ok=True)
        entry_path = output / f"{entry.entry_id}.json"
        with open(entry_path, "w") as f:
            json.dump(entry.to_dict(), f, indent=2, default=str)

    def export_all(self, format: str = "json") -> str:
        if format == "jsonl":
            lines = [json.dumps(e.to_dict(), default=str) for e in self.entries]
            return "\n".join(lines)
        elif format == "citations":
            return "\n\n".join(
                self.formatter.format_for_paper(e) + "\n" + self.formatter.format_bibtex(e)
                for e in self.entries
            )
        return json.dumps([e.to_dict() for e in self.entries], indent=2, default=str)

    def get_by_type(self, entry_type: str) -> List[CorpusEntry]:
        return [e for e in self.entries if e.entry_type == entry_type]

    def get_recent(self, n: int = 10) -> List[CorpusEntry]:
        return sorted(self.entries, key=lambda e: e.created_at, reverse=True)[:n]

    def summary(self) -> dict:
        type_counts = {}
        for e in self.entries:
            type_counts[e.entry_type] = type_counts.get(e.entry_type, 0) + 1
        return {
            "total_entries": len(self.entries),
            "by_type": type_counts,
            "output_dir": self.config.output_dir,
            "anonymized": self.config.anonymize,
            "citation_count": len(set(c for e in self.entries for c in e.citations)),
        }
