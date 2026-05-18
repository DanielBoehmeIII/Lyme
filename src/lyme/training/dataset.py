"""StreamingDataset — HuggingFace-integrated dataset pipeline for training."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional


@dataclass
class StreamingDatasetConfig:
    path: str = ""
    split: str = "train"
    max_examples: int = 0
    shuffle: bool = True
    seed: int = 42


class StreamingDataset:
    def __init__(self, config: StreamingDatasetConfig = None):
        self.config = config or StreamingDatasetConfig()

    def iter_jsonl(self, path: str) -> Iterator[Dict[str, Any]]:
        p = Path(path)
        if not p.exists():
            return
        with open(p) as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)

    def load_hf(self, path: str, split: str = "train") -> Any:
        try:
            from datasets import load_dataset
            return load_dataset(path, split=split)
        except ImportError:
            return None

    def to_hf_dataset(self, examples: List[Dict[str, Any]]) -> Any:
        try:
            from datasets import Dataset
            return Dataset.from_list(examples)
        except ImportError:
            return None

    def format_for_sft(self, example: Dict[str, Any]) -> Dict[str, str]:
        return {
            "prompt": example.get("prompt", example.get("instruction", "")),
            "completion": example.get("completion", example.get("output", "")),
        }

    def format_for_dpo(self, example: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "prompt": example.get("prompt", ""),
            "chosen": example.get("chosen", example.get("accepted", "")),
            "rejected": example.get("rejected", example.get("rejected", "")),
        }
