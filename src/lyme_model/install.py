"""Week 131 — Installation and Hardware Setup for Lyme Model.

Support:
- CPU-only
- Ollama
- llama.cpp
- GPU if available
- low-RAM mode
- recommended model download
- hardware profile test
- sanity benchmark

Deliver: setup wizard, troubleshooting guide, model recommendations, first-run benchmark.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json
import sys
import subprocess
import platform


@dataclass
class HardwareProfile:
    os: str
    cpu_cores: int
    ram_gb: int
    has_gpu: bool
    gpu_name: str
    vram_gb: int
    has_ollama: bool
    has_llama_cpp: bool
    tier: str

    def to_dict(self) -> dict:
        return {
            "os": self.os,
            "cpu_cores": self.cpu_cores,
            "ram_gb": self.ram_gb,
            "has_gpu": self.has_gpu,
            "gpu_name": self.gpu_name,
            "vram_gb": self.vram_gb,
            "has_ollama": self.has_ollama,
            "has_llama_cpp": self.has_llama_cpp,
            "tier": self.tier,
        }


@dataclass
class ModelRecommendation:
    name: str
    size_gb: float
    backend: str
    quantization: str
    tier: str
    ram_required_gb: int
    vram_required_gb: int
    quality: str
    download_command: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "size_gb": self.size_gb,
            "backend": self.backend,
            "quantization": self.quantization,
            "tier": self.tier,
            "ram_required_gb": self.ram_required_gb,
            "vram_required_gb": self.vram_required_gb,
            "quality": self.quality,
            "download_command": self.download_command,
        }


MODEL_RECOMMENDATIONS = [
    ModelRecommendation(
        name="Qwen2.5-Coder-1.5B", size_gb=0.9, backend="Ollama",
        quantization="Q4_K_M", tier="cpu_only", ram_required_gb=4,
        vram_required_gb=0, quality="fair",
        download_command="ollama pull qwen2.5-coder:1.5b",
    ),
    ModelRecommendation(
        name="Qwen2.5-Coder-1.5B-Q4", size_gb=0.9, backend="llama.cpp",
        quantization="Q4_K_M", tier="budget_gpu", ram_required_gb=4,
        vram_required_gb=2, quality="fair",
        download_command="huggingface-cli download Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF qwen2.5-coder-1.5b-instruct-q4_k_m.gguf",
    ),
    ModelRecommendation(
        name="Qwen2.5-Coder-7B-Q4", size_gb=4.1, backend="Ollama",
        quantization="Q4_K_M", tier="standard_gpu", ram_required_gb=8,
        vram_required_gb=6, quality="good",
        download_command="ollama pull qwen2.5-coder:7b",
    ),
    ModelRecommendation(
        name="DeepSeek-Coder-V2-Lite-Q4", size_gb=5.5, backend="llama.cpp",
        quantization="Q4_K_M", tier="high_end", ram_required_gb=16,
        vram_required_gb=8, quality="very good",
        download_command="huggingface-cli download deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct-GGUF deepseek-coder-v2-lite-instruct-q4_k_m.gguf",
    ),
    ModelRecommendation(
        name="Qwen2.5-Coder-14B-Q4", size_gb=8.2, backend="Ollama",
        quantization="Q4_K_M", tier="high_end", ram_required_gb=16,
        vram_required_gb=10, quality="excellent",
        download_command="ollama pull qwen2.5-coder:14b",
    ),
]


class InstallWizard:
    """Install and setup wizard for Lyme Model."""

    TROUBLESHOOTING_GUIDE = """
# Lyme Model Troubleshooting Guide

## Ollama not found
Install Ollama: https://ollama.com/download
After install: `ollama serve` in one terminal, then retry.

## Model not found
Run the recommended download command:
  ollama pull qwen2.5-coder:1.5b

## Out of memory
Try low-RAM mode: `export LYME_LOW_RAM=1`
Or use a smaller model: qwen2.5-coder:0.5b

## GPU not detected
Ensure NVIDIA drivers are installed: `nvidia-smi`
If on Linux: `sudo apt install nvidia-driver-xxx`
Ollama uses GPU automatically if available.

## Slow inference
Try a smaller quantized model (Q4 instead of Q8).
Close other GPU-intensive applications.
Use CPU-only if GPU is shared.

## Python version
Lyme Model requires Python >= 3.10.
Check: `python3 --version`
    """

    @staticmethod
    def detect_hardware() -> HardwareProfile:
        os_name = platform.system().lower()
        cpu_count = os.cpu_count() or 4
        ram_gb = 8  # default estimate
        try:
            if os_name == "linux":
                mem = Path("/proc/meminfo").read_text()
                for line in mem.splitlines():
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        ram_gb = kb // (1024 * 1024)
                        break
        except Exception:
            pass

        has_gpu = False
        gpu_name = ""
        vram_gb = 0
        try:
            result = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total",
                                      "--format=csv,noheader"],
                                     capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(",")
                gpu_name = parts[0].strip() if len(parts) > 0 else ""
                vram_str = parts[1].strip() if len(parts) > 1 else "0 MiB"
                vram_gb = int(vram_str.split()[0]) // 1024 if "MiB" in vram_str else 0
                has_gpu = True
        except Exception:
            pass

        has_ollama = False
        try:
            result = subprocess.run(["ollama", "--version"], capture_output=True, text=True, timeout=3)
            has_ollama = result.returncode == 0
        except Exception:
            pass

        has_llama_cpp = False
        try:
            result = subprocess.run(["llama-cli", "--version"], capture_output=True, text=True, timeout=3)
            has_llama_cpp = result.returncode == 0
        except Exception:
            pass

        # Determine tier
        if has_gpu and vram_gb >= 10:
            tier = "high_end"
        elif has_gpu and vram_gb >= 6:
            tier = "standard_gpu"
        elif has_gpu and vram_gb >= 2:
            tier = "budget_gpu"
        elif ram_gb >= 8:
            tier = "cpu_only"
        elif ram_gb >= 4:
            tier = "minimal"
        else:
            tier = "minimal"

        return HardwareProfile(
            os=os_name, cpu_cores=cpu_count, ram_gb=ram_gb,
            has_gpu=has_gpu, gpu_name=gpu_name, vram_gb=vram_gb,
            has_ollama=has_ollama, has_llama_cpp=has_llama_cpp,
            tier=tier,
        )

    @staticmethod
    def recommend_model(hw: HardwareProfile) -> List[ModelRecommendation]:
        tier_map = {
            "minimal": ["Qwen2.5-Coder-1.5B"],
            "cpu_only": ["Qwen2.5-Coder-1.5B"],
            "budget_gpu": ["Qwen2.5-Coder-1.5B-Q4"],
            "standard_gpu": ["Qwen2.5-Coder-7B-Q4"],
            "high_end": ["Qwen2.5-Coder-14B-Q4", "DeepSeek-Coder-V2-Lite-Q4"],
        }
        names = tier_map.get(hw.tier, ["Qwen2.5-Coder-1.5B"])
        return [m for m in MODEL_RECOMMENDATIONS if m.name in names]

    @staticmethod
    def run_sanity_benchmark(hw: HardwareProfile) -> dict:
        results = {
            "platform": f"{hw.os} ({hw.cpu_cores} cores, {hw.ram_gb}GB RAM)",
            "gpu": f"{hw.gpu_name} ({hw.vram_gb}GB VRAM)" if hw.has_gpu else "None",
            "ollama": "available" if hw.has_ollama else "not found",
            "llama.cpp": "available" if hw.has_llama_cpp else "not found",
            "tier": hw.tier,
            "recommended_setup": InstallWizard._setup_instructions(hw),
        }
        return results

    @staticmethod
    def _setup_instructions(hw: HardwareProfile) -> str:
        if hw.tier == "minimal":
            return "Low-RAM mode: export LYME_LOW_RAM=1. Use static analysis only (no LLM)."
        if hw.tier == "cpu_only":
            return "Install Ollama: https://ollama.com. Then: ollama pull qwen2.5-coder:1.5b"
        if hw.tier == "budget_gpu":
            return "Install Ollama with GPU support. Then: ollama pull qwen2.5-coder:7b"
        if hw.tier == "standard_gpu":
            return "Full setup ready. ollama pull qwen2.5-coder:7b for best quality."
        if hw.tier == "high_end":
            return "High-end setup. ollama pull qwen2.5-coder:14b or use llama.cpp for optimal performance."
        return "Unknown hardware tier. Install Ollama and pull qwen2.5-coder:1.5b"

    @staticmethod
    def first_run_wizard() -> dict:
        print("=" * 56)
        print("  Lyme Model — First Run Setup")
        print("=" * 56)

        hw = InstallWizard.detect_hardware()
        print(f"\nDetected Hardware:")
        print(f"  OS: {hw.os}")
        print(f"  CPU: {hw.cpu_cores} cores")
        print(f"  RAM: {hw.ram_gb}GB")
        print(f"  GPU: {hw.gpu_name} ({hw.vram_gb}GB VRAM)" if hw.has_gpu else "  GPU: None")
        print(f"  Ollama: {'✓' if hw.has_ollama else '✗'}")
        print(f"  Tier: {hw.tier}")

        recommendations = InstallWizard.recommend_model(hw)
        print(f"\nRecommended Model{'s' if len(recommendations) > 1 else ''}:")
        for rec in recommendations:
            print(f"  {rec.name:30s} {rec.size_gb:.1f}GB  {rec.backend:10s}  {rec.quality}")
            print(f"    Download: {rec.download_command}")

        print(f"\nSetup Instructions:")
        print(f"  {InstallWizard._setup_instructions(hw)}")

        if not hw.has_ollama and hw.tier not in ("minimal",):
            print(f"\n  → Install Ollama: https://ollama.com/download")
            print(f"  → Then run recommended download command")

        print(f"\nQuick sanity check:")
        print(f"  lyme model hardware    # Verify detection")
        print(f"  lyme model ask --report # Show Repo Q&A capability")

        return hw.to_dict()

    @staticmethod
    def print_troubleshooting():
        print(InstallWizard.TROUBLESHOOTING_GUIDE)


wizard = InstallWizard()
