"""VRAM and compute budgeting for hardware-aware scheduling."""
from dataclasses import dataclass
from typing import List
from .detector import HardwareProfile


@dataclass
class BudgetEstimate:
    model_size_b: float = 0.0
    quantization_bits: int = 4
    vram_model_gb: float = 0.0
    vram_kv_cache_per_token_mb: float = 0.0
    max_context_tokens: int = 0
    recommended_batch: int = 1


def estimate_vram(model_size_b: float, bits: int) -> float:
    """Estimate VRAM needed for a model in GB."""
    params_gb = model_size_b * bits / 8.0
    overhead = 1.1
    return round(params_gb * overhead, 2)


def estimate_context_limit(
    vram_total_mb: int,
    model_size_b: float,
    bits: int,
    kv_overhead_per_token_mb: float = 0.002,
    os_overhead_mb: int = 512,
) -> int:
    """Estimate max context length for a model/hardware combination."""
    model_vram = estimate_vram(model_size_b, bits) * 1024
    available = vram_total_mb - model_vram - os_overhead_mb
    if available <= 0:
        return 0
    return int(available / kv_overhead_per_token_mb)


def suggest_models(profile: HardwareProfile) -> List[dict]:
    """Return recommended models and quants for this hardware."""
    suggestions = []
    vram = profile.gpu.vram_total_mb

    candidates = [
        {"name": "qwen2.5-coder:1.5b", "size_b": 1.5, "role": "draft"},
        {"name": "qwen2.5-coder:3b",   "size_b": 3.0, "role": "light"},
        {"name": "qwen2.5-coder:7b",   "size_b": 7.0, "role": "primary"},
        {"name": "deepseek-coder:6.7b", "size_b": 6.7, "role": "primary"},
        {"name": "codegemma:7b",        "size_b": 7.0, "role": "primary"},
        {"name": "codellama:7b",        "size_b": 7.0, "role": "primary"},
        {"name": "llama3:8b",           "size_b": 8.0, "role": "general"},
    ]

    for cand in candidates:
        for bits in [4, 5, 6, 8]:
            needed = estimate_vram(cand["size_b"], bits) * 1024
            feasible = (vram >= needed) if vram > 0 else False
            context = estimate_context_limit(vram, cand["size_b"], bits) if vram > 0 else 4096
            suggestions.append({
                "model": cand["name"],
                "params_b": cand["size_b"],
                "quant": f"Q{bits}",
                "vram_needed_mb": int(needed),
                "vram_available_mb": vram,
                "feasible": feasible,
                "est_context": context,
                "role": cand["role"],
                "priority": "high" if feasible else "no",
            })

    suggestions.sort(key=lambda s: (0 if s["feasible"] else 1, -s["params_b"]))
    return suggestions
