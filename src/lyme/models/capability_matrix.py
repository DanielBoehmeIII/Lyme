from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class Quantization(str, Enum):
    NONE = "none"
    Q4_0 = "q4_0"
    Q4_K_M = "q4_k_m"
    Q5_K_M = "q5_k_m"
    Q8_0 = "q8_0"
    F16 = "f16"


class Backend(str, Enum):
    OLLAMA = "ollama"
    LLAMA_CPP = "llama.cpp"
    TRANSFORMERS = "transformers"
    LITGPT = "litgpt"
    EXLLAMA = "exllama"


@dataclass
class ModelProfile:
    name: str
    family: str
    parameters_b: float
    context_window: int
    vram_gb: float
    quantizations: List[Quantization] = field(default_factory=list)
    available_backends: List[Backend] = field(default_factory=list)

    def estimated_vram(self, quantization: Quantization = Quantization.Q4_K_M) -> float:
        multiplier = {"none": 1.0, "q4_0": 0.3, "q4_k_m": 0.32, "q5_k_m": 0.38, "q8_0": 0.55, "f16": 0.75}
        return self.vram_gb * multiplier.get(quantization.value, 0.5)

    def fits_in_vram(self, vram_gb: float, quantization: Quantization = Quantization.Q4_K_M) -> bool:
        return self.estimated_vram(quantization) <= vram_gb


@dataclass
class BenchmarkResult:
    model: str
    scores: Dict[str, float]
    total: float = 0.0

    def __post_init__(self) -> None:
        self.total = sum(self.scores.values())


DIMENSIONS = [
    "repo_navigation",
    "multi_file_editing",
    "patch_quality",
    "compile_repair",
    "instruction_following",
    "latency_score",
    "memory_efficiency",
    "context_handling",
    "hallucination_rate",
    "cost_to_quality",
]

PRESET_MODELS: Dict[str, ModelProfile] = {
    "qwen2.5-coder-32b": ModelProfile(
        name="Qwen 2.5 Coder 32B",
        family="qwen",
        parameters_b=32.0,
        context_window=131072,
        vram_gb=64.0,
        quantizations=[Quantization.Q4_K_M, Quantization.Q5_K_M, Quantization.Q8_0, Quantization.F16],
        available_backends=[Backend.OLLAMA, Backend.LLAMA_CPP, Backend.TRANSFORMERS],
    ),
    "qwen2.5-coder-14b": ModelProfile(
        name="Qwen 2.5 Coder 14B",
        family="qwen",
        parameters_b=14.0,
        context_window=131072,
        vram_gb=28.0,
        quantizations=[Quantization.Q4_K_M, Quantization.Q5_K_M, Quantization.Q8_0],
        available_backends=[Backend.OLLAMA, Backend.LLAMA_CPP, Backend.TRANSFORMERS],
    ),
    "qwen2.5-coder-7b": ModelProfile(
        name="Qwen 2.5 Coder 7B",
        family="qwen",
        parameters_b=7.0,
        context_window=131072,
        vram_gb=14.0,
        quantizations=[Quantization.Q4_0, Quantization.Q4_K_M, Quantization.Q5_K_M, Quantization.Q8_0],
        available_backends=[Backend.OLLAMA, Backend.LLAMA_CPP, Backend.TRANSFORMERS],
    ),
    "deepseek-coder-33b": ModelProfile(
        name="DeepSeek Coder 33B",
        family="deepseek",
        parameters_b=33.0,
        context_window=16384,
        vram_gb=66.0,
        quantizations=[Quantization.Q4_K_M, Quantization.Q5_K_M, Quantization.Q8_0],
        available_backends=[Backend.OLLAMA, Backend.LLAMA_CPP, Backend.TRANSFORMERS],
    ),
    "deepseek-coder-6.7b": ModelProfile(
        name="DeepSeek Coder 6.7B",
        family="deepseek",
        parameters_b=6.7,
        context_window=16384,
        vram_gb=14.0,
        quantizations=[Quantization.Q4_0, Quantization.Q4_K_M, Quantization.Q8_0],
        available_backends=[Backend.OLLAMA, Backend.LLAMA_CPP, Backend.TRANSFORMERS],
    ),
    "deepseek-coder-1.3b": ModelProfile(
        name="DeepSeek Coder 1.3B",
        family="deepseek",
        parameters_b=1.3,
        context_window=16384,
        vram_gb=3.0,
        quantizations=[Quantization.Q4_0, Quantization.Q4_K_M, Quantization.Q8_0],
        available_backends=[Backend.OLLAMA, Backend.LLAMA_CPP, Backend.TRANSFORMERS],
    ),
    "codellama-34b": ModelProfile(
        name="Code Llama 34B",
        family="codellama",
        parameters_b=34.0,
        context_window=16384,
        vram_gb=68.0,
        quantizations=[Quantization.Q4_K_M, Quantization.Q5_K_M, Quantization.Q8_0],
        available_backends=[Backend.OLLAMA, Backend.LLAMA_CPP],
    ),
    "codellama-13b": ModelProfile(
        name="Code Llama 13B",
        family="codellama",
        parameters_b=13.0,
        context_window=16384,
        vram_gb=26.0,
        quantizations=[Quantization.Q4_K_M, Quantization.Q5_K_M, Quantization.Q8_0],
        available_backends=[Backend.OLLAMA, Backend.LLAMA_CPP, Backend.TRANSFORMERS],
    ),
    "codellama-7b": ModelProfile(
        name="Code Llama 7B",
        family="codellama",
        parameters_b=7.0,
        context_window=16384,
        vram_gb=14.0,
        quantizations=[Quantization.Q4_0, Quantization.Q4_K_M, Quantization.Q8_0],
        available_backends=[Backend.OLLAMA, Backend.LLAMA_CPP, Backend.TRANSFORMERS],
    ),
    "starcoder2-15b": ModelProfile(
        name="StarCoder2 15B",
        family="starcoder",
        parameters_b=15.0,
        context_window=16384,
        vram_gb=30.0,
        quantizations=[Quantization.Q4_K_M, Quantization.Q5_K_M, Quantization.Q8_0],
        available_backends=[Backend.OLLAMA, Backend.TRANSFORMERS],
    ),
    "starcoder2-7b": ModelProfile(
        name="StarCoder2 7B",
        family="starcoder",
        parameters_b=7.0,
        context_window=16384,
        vram_gb=14.0,
        quantizations=[Quantization.Q4_0, Quantization.Q4_K_M, Quantization.Q8_0],
        available_backends=[Backend.OLLAMA, Backend.TRANSFORMERS],
    ),
    "starcoder2-3b": ModelProfile(
        name="StarCoder2 3B",
        family="starcoder",
        parameters_b=3.0,
        context_window=16384,
        vram_gb=6.0,
        quantizations=[Quantization.Q4_0, Quantization.Q4_K_M],
        available_backends=[Backend.OLLAMA, Backend.TRANSFORMERS],
    ),
    "phi-3-mini-4k": ModelProfile(
        name="Phi-3 Mini 4K",
        family="phi",
        parameters_b=3.8,
        context_window=4096,
        vram_gb=8.0,
        quantizations=[Quantization.Q4_0, Quantization.Q4_K_M, Quantization.Q8_0],
        available_backends=[Backend.OLLAMA, Backend.LLAMA_CPP, Backend.TRANSFORMERS],
    ),
    "phi-3-small-8k": ModelProfile(
        name="Phi-3 Small 8K",
        family="phi",
        parameters_b=7.0,
        context_window=8192,
        vram_gb=14.0,
        quantizations=[Quantization.Q4_K_M, Quantization.Q8_0],
        available_backends=[Backend.OLLAMA, Backend.LLAMA_CPP, Backend.TRANSFORMERS],
    ),
}


@dataclass
class CapabilityMatrix:
    models: Dict[str, ModelProfile] = field(default_factory=lambda: dict(PRESET_MODELS))
    scores: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.scores:
            self.scores = self._default_scores()

    def _default_scores(self) -> Dict[str, Dict[str, float]]:
        return {
            "qwen2.5-coder-32b": {
                "repo_navigation": 9.0, "multi_file_editing": 9.0, "patch_quality": 8.5,
                "compile_repair": 8.5, "instruction_following": 9.0, "latency_score": 5.0,
                "memory_efficiency": 4.5, "context_handling": 9.5, "hallucination_rate": 8.5,
                "cost_to_quality": 7.0,
            },
            "qwen2.5-coder-14b": {
                "repo_navigation": 8.0, "multi_file_editing": 7.5, "patch_quality": 7.5,
                "compile_repair": 7.5, "instruction_following": 8.0, "latency_score": 6.5,
                "memory_efficiency": 6.0, "context_handling": 8.5, "hallucination_rate": 7.5,
                "cost_to_quality": 8.5,
            },
            "qwen2.5-coder-7b": {
                "repo_navigation": 6.5, "multi_file_editing": 6.0, "patch_quality": 6.5,
                "compile_repair": 6.0, "instruction_following": 7.0, "latency_score": 8.0,
                "memory_efficiency": 7.5, "context_handling": 7.0, "hallucination_rate": 6.5,
                "cost_to_quality": 9.0,
            },
            "deepseek-coder-33b": {
                "repo_navigation": 8.5, "multi_file_editing": 8.0, "patch_quality": 8.0,
                "compile_repair": 8.0, "instruction_following": 8.5, "latency_score": 4.5,
                "memory_efficiency": 4.0, "context_handling": 7.0, "hallucination_rate": 8.0,
                "cost_to_quality": 6.5,
            },
            "deepseek-coder-6.7b": {
                "repo_navigation": 6.0, "multi_file_editing": 5.5, "patch_quality": 6.0,
                "compile_repair": 5.5, "instruction_following": 6.5, "latency_score": 8.5,
                "memory_efficiency": 8.0, "context_handling": 6.0, "hallucination_rate": 6.0,
                "cost_to_quality": 9.5,
            },
            "deepseek-coder-1.3b": {
                "repo_navigation": 3.0, "multi_file_editing": 2.5, "patch_quality": 3.0,
                "compile_repair": 2.5, "instruction_following": 4.0, "latency_score": 9.5,
                "memory_efficiency": 9.5, "context_handling": 4.0, "hallucination_rate": 4.0,
                "cost_to_quality": 10.0,
            },
            "codellama-34b": {
                "repo_navigation": 7.5, "multi_file_editing": 7.0, "patch_quality": 7.5,
                "compile_repair": 7.0, "instruction_following": 7.5, "latency_score": 4.0,
                "memory_efficiency": 3.5, "context_handling": 6.5, "hallucination_rate": 7.5,
                "cost_to_quality": 5.5,
            },
            "codellama-13b": {
                "repo_navigation": 6.5, "multi_file_editing": 6.0, "patch_quality": 6.5,
                "compile_repair": 6.0, "instruction_following": 6.5, "latency_score": 7.0,
                "memory_efficiency": 6.5, "context_handling": 6.0, "hallucination_rate": 6.5,
                "cost_to_quality": 7.5,
            },
            "codellama-7b": {
                "repo_navigation": 5.0, "multi_file_editing": 4.5, "patch_quality": 5.0,
                "compile_repair": 4.5, "instruction_following": 5.5, "latency_score": 8.0,
                "memory_efficiency": 7.5, "context_handling": 5.0, "hallucination_rate": 5.5,
                "cost_to_quality": 8.5,
            },
            "starcoder2-15b": {
                "repo_navigation": 6.0, "multi_file_editing": 5.5, "patch_quality": 6.0,
                "compile_repair": 5.5, "instruction_following": 6.0, "latency_score": 6.5,
                "memory_efficiency": 6.0, "context_handling": 5.5, "hallucination_rate": 6.0,
                "cost_to_quality": 7.0,
            },
            "starcoder2-7b": {
                "repo_navigation": 5.0, "multi_file_editing": 4.5, "patch_quality": 5.0,
                "compile_repair": 4.5, "instruction_following": 5.0, "latency_score": 8.0,
                "memory_efficiency": 7.5, "context_handling": 5.0, "hallucination_rate": 5.0,
                "cost_to_quality": 8.5,
            },
            "starcoder2-3b": {
                "repo_navigation": 3.5, "multi_file_editing": 3.0, "patch_quality": 3.5,
                "compile_repair": 3.0, "instruction_following": 3.5, "latency_score": 9.0,
                "memory_efficiency": 9.0, "context_handling": 4.0, "hallucination_rate": 3.5,
                "cost_to_quality": 9.5,
            },
            "phi-3-mini-4k": {
                "repo_navigation": 4.0, "multi_file_editing": 3.5, "patch_quality": 4.0,
                "compile_repair": 3.5, "instruction_following": 6.0, "latency_score": 9.0,
                "memory_efficiency": 8.5, "context_handling": 3.0, "hallucination_rate": 6.0,
                "cost_to_quality": 9.0,
            },
            "phi-3-small-8k": {
                "repo_navigation": 5.0, "multi_file_editing": 4.5, "patch_quality": 5.0,
                "compile_repair": 4.5, "instruction_following": 6.5, "latency_score": 8.0,
                "memory_efficiency": 7.5, "context_handling": 4.5, "hallucination_rate": 6.5,
                "cost_to_quality": 8.5,
            },
        }

    def evaluate(self, model_key: str, overrides: Optional[Dict[str, float]] = None) -> BenchmarkResult:
        if model_key not in self.scores:
            raise KeyError(f"Unknown model: {model_key}")
        scores = dict(self.scores[model_key])
        if overrides:
            scores.update(overrides)
        return BenchmarkResult(model=model_key, scores=scores)

    def compare(self, *model_keys: str) -> List[BenchmarkResult]:
        return [self.evaluate(k) for k in model_keys]

    def filter_by_vram(self, vram_gb: float, quantization: Quantization = Quantization.Q4_K_M) -> List[str]:
        return [k for k, p in self.models.items() if p.fits_in_vram(vram_gb, quantization)]

    def filter_by_backend(self, backend: Backend) -> List[str]:
        return [k for k, p in self.models.items() if backend in p.available_backends]

    def filter_by_family(self, family: str) -> List[str]:
        return [k for k, p in self.models.items() if p.family == family]

    def top_n(self, n: int = 3, dimension: Optional[str] = None) -> List[BenchmarkResult]:
        results = [self.evaluate(k) for k in self.models]
        if dimension:
            results.sort(key=lambda r: r.scores.get(dimension, 0), reverse=True)
        else:
            results.sort(key=lambda r: r.total, reverse=True)
        return results[:n]

    def to_markdown(self, model_keys: Optional[List[str]] = None) -> str:
        keys = model_keys or list(self.models.keys())
        header = "| Model | " + " | ".join(d.replace("_", " ") for d in DIMENSIONS) + " | Total |"
        sep = "|" + "---|" * (len(DIMENSIONS) + 2)
        rows: List[str] = []
        for k in keys:
            result = self.evaluate(k)
            scores_str = " | ".join(f"{result.scores[d]:.1f}" for d in DIMENSIONS)
            rows.append(f"| {self.models[k].name} | {scores_str} | {result.total:.1f} |")
        return "\n".join([header, sep] + rows + [""])
