"""Training — Lyme fine-tuning and dataset pipeline infrastructure."""
from .pipeline import DatasetPipeline, TrainingExample, TrainingRun, ExampleSource
from .config import TrainingConfig, LoraConfig, DataConfig
from .dataset import StreamingDataset, StreamingDatasetConfig
from .dpo import DPOTrainer, DPOConfig, DPOResult
from .distill import DistillationPipeline, DistillConfig, DistillResult
from .synthetic import SyntheticDataEngine, SyntheticConfig, SyntheticTask
from .specialized import SpecializedModelManager, SubmodelProfile, ALL_SUBMODELS
from .inference_opt import InferenceOptimizer, InferenceOptConfig, SpeedBenchmark, QuantLevel
from .preference import HumanPreferenceLoop, PreferencePair, PreferenceStats

__all__ = [
    "DatasetPipeline", "TrainingExample", "TrainingRun",
    "TrainingConfig", "LoraConfig", "DataConfig",
    "StreamingDataset", "StreamingDatasetConfig",
    "DPOTrainer", "DPOConfig", "DPOResult",
    "DistillationPipeline", "DistillConfig", "DistillResult",
    "SyntheticDataEngine", "SyntheticConfig", "SyntheticTask",
    "SpecializedModelManager", "SubmodelProfile", "ALL_SUBMODELS",
    "InferenceOptimizer", "InferenceOptConfig", "SpeedBenchmark", "QuantLevel",
    "HumanPreferenceLoop", "PreferencePair", "PreferenceStats",
]
