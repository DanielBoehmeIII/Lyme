"""TrainingConfig — typed configuration for Lyme model fine-tuning."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LoraConfig:
    r: int = 16
    alpha: int = 32
    dropout: float = 0.05
    target_modules: List[str] = field(default_factory=lambda: ["q_proj", "v_proj"])
    bias: str = "none"
    task_type: str = "CAUSAL_LM"


@dataclass
class DataConfig:
    dataset_path: str = "./datasets"
    validation_split: float = 0.1
    max_seq_length: int = 4096
    shuffle: bool = True
    num_workers: int = 4


@dataclass
class TrainingConfig:
    model_name: str = ""
    output_dir: str = "./checkpoints"
    num_epochs: int = 3
    batch_size: int = 4
    gradient_accumulation_steps: int = 4
    learning_rate: float = 2e-4
    warmup_steps: int = 100
    logging_steps: int = 10
    save_steps: int = 500
    eval_steps: int = 500
    max_grad_norm: float = 1.0
    lora: LoraConfig = field(default_factory=LoraConfig)
    data: DataConfig = field(default_factory=DataConfig)
    use_flash_attention: bool = True
    fp16: bool = True
    bf16: bool = False
    deepspeed: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "output_dir": self.output_dir,
            "num_epochs": self.num_epochs,
            "batch_size": self.batch_size,
            "learning_rate": self.learning_rate,
            "lora": self.lora.__dict__,
            "data": self.data.__dict__,
            "use_flash_attention": self.use_flash_attention,
            "fp16": self.fp16,
            "bf16": self.bf16,
        }
