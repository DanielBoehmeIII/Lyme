"""SyntheticDataEngine — generates bugs, PRs, failing tests, and code tasks automatically."""
from __future__ import annotations
import hashlib
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional

from .pipeline import DatasetPipeline, TrainingExample, ExampleSource


class SyntheticTask(Enum):
    BUG_FIX = "bug_fix"
    ADD_TEST = "add_test"
    REFACTOR = "refactor"
    ADD_FEATURE = "add_feature"
    FIX_TYPOS = "fix_typos"
    IMPLEMENT_STUB = "implement_stub"


@dataclass
class SyntheticConfig:
    task_types: List[SyntheticTask] = field(default_factory=lambda: list(SyntheticTask))
    examples_per_task: int = 100
    output_dir: str = "./datasets/generated"
    seed: int = 42


class SyntheticDataEngine:
    def __init__(self, config: SyntheticConfig = None, model_fn: Callable = None):
        self.config = config or SyntheticConfig()
        self._model_fn = model_fn
        self.pipeline = DatasetPipeline()
        random.seed(self.config.seed)

    def generate(self, repo_path: str = ".") -> int:
        count = 0
        for task_type in self.config.task_types:
            for _ in range(self.config.examples_per_task // len(self.config.task_types)):
                ex = self._generate_example(task_type, repo_path)
                if ex:
                    self.pipeline.add_example(ex)
                    count += 1
        return count

    def _generate_example(self, task_type: SyntheticTask, repo_path: str) -> Optional[TrainingExample]:
        task_descriptions = {
            SyntheticTask.BUG_FIX: "Fix the bug where {component} fails when {condition}",
            SyntheticTask.ADD_TEST: "Add test coverage for {component} edge cases",
            SyntheticTask.REFACTOR: "Refactor {component} to improve {quality}",
            SyntheticTask.ADD_FEATURE: "Implement {feature} in {component}",
            SyntheticTask.FIX_TYPOS: "Fix typos and formatting in {component}",
            SyntheticTask.IMPLEMENT_STUB: "Implement the stub function {stub} in {component}",
        }

        components = ["parser", "memory", "runtime", "agent", "models"]
        template = task_descriptions.get(task_type, "Implement {component}")
        prompt = template.format(
            component=random.choice(components),
            condition="input is empty",
            quality="maintainability",
            feature="error handling",
            stub="process_data",
        )

        completion = self._generate_completion(task_type, prompt)
        if not completion:
            return None

        eid = hashlib.md5(f"{prompt}{time.time()}".encode()).hexdigest()[:12]
        return TrainingExample(
            id=eid, prompt=prompt, completion=completion,
            source=ExampleSource.SYNTHETIC,
            score=random.uniform(0.5, 1.0),
        )

    def _generate_completion(self, task_type: SyntheticTask, prompt: str) -> Optional[str]:
        if self._model_fn:
            return self._model_fn(prompt)
        return _FALLBACK_COMPLETIONS.get(task_type, "def solution():\n    pass\n")


_FALLBACK_COMPLETIONS = {
    SyntheticTask.BUG_FIX: """def validate_input(data):
    if data is None:
        return []
    if not isinstance(data, list):
        raise TypeError("Expected list")
    return [x for x in data if x is not None]
""",
    SyntheticTask.ADD_TEST: """def test_validate_input():
    assert validate_input(None) == []
    assert validate_input([1, None, 3]) == [1, 3]
    try:
        validate_input("bad")
    except TypeError:
        pass
""",
    SyntheticTask.REFACTOR: """def process_items(items):
    return [transform(item) for item in items]
""",
}
