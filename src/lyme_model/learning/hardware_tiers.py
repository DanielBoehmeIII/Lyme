"""Week 109 — Consumer Hardware Tiers for Lyme Model.

Defines tiers: CPU-only laptop, 8GB/16GB/32GB RAM, 8GB/12GB/24GB VRAM.
For each: recommended models, quantization, max repo size, expected latency.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class HardwareTier:
    name: str = ""
    ram_gb: int = 0
    vram_gb: int = 0
    has_gpu: bool = False
    recommended_models: List[str] = field(default_factory=list)
    quantization: str = ""
    max_repo_size_k_files: int = 0
    expected_latency_per_task_s: str = ""
    supported_features: List[str] = field(default_factory=list)
    unsupported_features: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "tier": self.name,
            "ram_gb": self.ram_gb,
            "vram_gb": self.vram_gb,
            "has_gpu": self.has_gpu,
            "recommended_models": self.recommended_models,
            "quantization": self.quantization,
            "max_repo_size_k_files": self.max_repo_size_k_files,
            "expected_latency_per_task_s": self.expected_latency_per_task_s,
            "supported": self.supported_features[:8],
            "unsupported": self.unsupported_features[:8],
        }


HARDWARE_TIERS = [
    HardwareTier(
        name="CPU-only laptop", ram_gb=8, vram_gb=0, has_gpu=False,
        recommended_models=["Qwen2.5-Coder-0.5B", "Qwen2.5-Coder-1.5B (slow)"],
        quantization="Q4_0_4_4 (GGUF)", max_repo_size_k_files=5,
        expected_latency_per_task_s="30-120s",
        supported_features=["Repo Q&A", "Simple bug location", "Code explanation"],
        unsupported_features=["Patch generation", "Tool-use policy", "Multi-candidate decoding",
                             "Real-time verification", "Large repo analysis"],
    ),
    HardwareTier(
        name="8GB RAM laptop", ram_gb=8, vram_gb=0, has_gpu=False,
        recommended_models=["Qwen2.5-Coder-1.5B (GGUF Q4)"],
        quantization="Q4_K_M", max_repo_size_k_files=10,
        expected_latency_per_task_s="15-60s",
        supported_features=["Repo Q&A", "Bug location", "Code explanation", "Simple planning"],
        unsupported_features=["7B models", "Tool-use policy", "Multi-candidate decoding"],
    ),
    HardwareTier(
        name="16GB RAM workstation", ram_gb=16, vram_gb=0, has_gpu=False,
        recommended_models=["Qwen2.5-Coder-1.5B", "Qwen2.5-Coder-7B (slow, Q4)"],
        quantization="Q4_K_M or Q5_K_M", max_repo_size_k_files=25,
        expected_latency_per_task_s="8-40s",
        supported_features=["Repo Q&A", "Bug location", "Patch planning", "Simple patch generation"],
        unsupported_features=["Real-time multi-candidate", "Large 14B models"],
    ),
    HardwareTier(
        name="32GB RAM workstation", ram_gb=32, vram_gb=0, has_gpu=False,
        recommended_models=["Qwen2.5-Coder-7B (Q4)", "CodeLlama-7B"],
        quantization="Q4_K_M or Q5_K_M", max_repo_size_k_files=50,
        expected_latency_per_task_s="5-20s",
        supported_features=["Full patch planning", "Tool policy (heuristic)", "Verification"],
        unsupported_features=["Real-time multi-candidate", "QLoRA training"],
    ),
    HardwareTier(
        name="8GB VRAM GPU", ram_gb=16, vram_gb=8, has_gpu=True,
        recommended_models=["Qwen2.5-Coder-1.5B (fp16)", "Qwen2.5-Coder-7B (Q4)"],
        quantization="Q4_K_M or fp16 (1.5B)", max_repo_size_k_files=30,
        expected_latency_per_task_s="2-10s",
        supported_features=["Tool-use policy", "Patch planning + critic", "Verification",
                           "Multi-candidate (N=2)", "LoRA inference"],
        unsupported_features=["Full 7B fp16", "QLoRA training (borderline)", "14B models"],
    ),
    HardwareTier(
        name="12GB VRAM GPU", ram_gb=32, vram_gb=12, has_gpu=True,
        recommended_models=["Qwen2.5-Coder-7B (Q4/Q5)", "CodeLlama-7B (fp16)"],
        quantization="Q5_K_M or fp16", max_repo_size_k_files=50,
        expected_latency_per_task_s="1-5s",
        supported_features=["Full tool-use policy", "Patch planning + critic",
                           "Multi-candidate (N=3)", "LoRA training", "Verification"],
        unsupported_features=["14B models fp16", "Full fine-tuning"],
    ),
    HardwareTier(
        name="24GB VRAM GPU", ram_gb=32, vram_gb=24, has_gpu=True,
        recommended_models=["Qwen2.5-Coder-7B (fp16)", "CodeLlama-13B (Q4)", "DeepSeek-Coder-7B"],
        quantization="fp16 or Q8", max_repo_size_k_files=100,
        expected_latency_per_task_s="0.5-3s",
        supported_features=["All features", "QLoRA/SFT training", "Multi-candidate (N=5)",
                           "Full model mixture", "Repo conditioning"],
        unsupported_features=["Full 70B model training", "Multi-GPU parallelism"],
    ),
    HardwareTier(
        name="High-end consumer workstation", ram_gb=64, vram_gb=24, has_gpu=True,
        recommended_models=["Qwen2.5-Coder-14B (Q4/Q5)", "DeepSeek-Coder-33B (Q4)"],
        quantization="Q4_K_M or Q5_K_M", max_repo_size_k_files=200,
        expected_latency_per_task_s="0.3-2s",
        supported_features=["All features", "Multi-candidate (N=5+)", "Model mixture",
                           "Local parity demos", "Full SFT with QLoRA"],
        unsupported_features=["Full fine-tune of 33B+ models"],
    ),
]


def get_hardware_tiers() -> List[dict]:
    return [t.to_dict() for t in HARDWARE_TIERS]


def recommend_tier(ram_gb: int = 0, vram_gb: int = 0, has_gpu: bool = False) -> HardwareTier:
    if has_gpu and vram_gb >= 24:
        return [t for t in HARDWARE_TIERS if "24GB VRAM" in t.name][-1]
    if has_gpu and vram_gb >= 12:
        return [t for t in HARDWARE_TIERS if "12GB VRAM" in t.name][0]
    if has_gpu and vram_gb >= 8:
        return [t for t in HARDWARE_TIERS if "8GB VRAM" in t.name][0]
    if ram_gb >= 32:
        return [t for t in HARDWARE_TIERS if "32GB RAM" in t.name][0]
    if ram_gb >= 16:
        return [t for t in HARDWARE_TIERS if "16GB RAM" in t.name][0]
    if ram_gb >= 8:
        return [t for t in HARDWARE_TIERS if "8GB RAM" in t.name][0]
    return HARDWARE_TIERS[0]
