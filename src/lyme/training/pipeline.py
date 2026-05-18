"""DatasetPipeline — training data pipeline for Lyme agent fine-tuning."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ExampleSource(Enum):
    TRACE = "trace"
    SYNTHETIC = "synthetic"
    HUMAN = "human"
    CROSS_REPO = "cross_repo"


@dataclass
class TrainingExample:
    id: str
    prompt: str
    completion: str
    source: ExampleSource = ExampleSource.SYNTHETIC
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "completion": self.completion,
            "source": self.source.value,
            "metadata": self.metadata,
            "score": self.score,
        }


@dataclass
class TrainingRun:
    id: str
    model_name: str
    examples: List[TrainingExample] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    status: str = "pending"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "model_name": self.model_name,
            "example_count": len(self.examples),
            "config": self.config,
            "metrics": self.metrics,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
        }


class DatasetPipeline:
    def __init__(self):
        self._examples: List[TrainingExample] = []

    def add_example(self, example: TrainingExample) -> None:
        self._examples.append(example)

    def add_examples(self, examples: List[TrainingExample]) -> None:
        self._examples.extend(examples)

    def filter_by_source(self, source: ExampleSource) -> List[TrainingExample]:
        return [e for e in self._examples if e.source == source]

    def filter_by_score(self, min_score: float) -> List[TrainingExample]:
        return [e for e in self._examples if e.score >= min_score]

    def export_json(self, path: str) -> None:
        import json
        data = [e.to_dict() for e in self._examples]
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def import_json(self, path: str) -> int:
        import json
        with open(path) as f:
            data = json.load(f)
        count = 0
        for item in data:
            self._examples.append(TrainingExample(
                id=item["id"],
                prompt=item["prompt"],
                completion=item["completion"],
                source=ExampleSource(item.get("source", "synthetic")),
                metadata=item.get("metadata", {}),
                score=item.get("score", 0.0),
            ))
            count += 1
        return count

    @property
    def count(self) -> int:
        return len(self._examples)

    def clear(self) -> None:
        self._examples.clear()
