"""Hardware detection and profiling for Lyme Model.

Detects available hardware (CPU, GPU, RAM, VRAM, disk) and produces
a hardware profile used by the rest of the Lyme Model runtime.
"""

import os
import re
import shutil
import json
import subprocess
import platform
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict


@dataclass
class CPUInfo:
    model: str = ""
    cores: int = 0
    architecture: str = ""

@dataclass
class RAMInfo:
    total_gb: float = 0.0
    available_gb: float = 0.0

@dataclass
class GPUInfo:
    present: bool = False
    name: str = ""
    vram_total_mb: int = 0
    driver_version: str = ""
    backend: str = ""  # cuda, rocm, metal, none

@dataclass
class DiskInfo:
    total_gb: float = 0.0
    free_gb: float = 0.0
    path: str = ""

@dataclass
class HardwareProfile:
    cpu: CPUInfo = field(default_factory=CPUInfo)
    ram: RAMInfo = field(default_factory=RAMInfo)
    gpu: GPUInfo = field(default_factory=GPUInfo)
    disk: DiskInfo = field(default_factory=DiskInfo)
    platform: str = ""
    ollama_available: bool = False
    ollama_models: List[Dict] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)

    def model_feasibility(self) -> List[Dict]:
        """Return model size recommendations based on hardware."""
        results = []
        vram = self.gpu.vram_total_mb
        ram = self.ram.total_gb

        configs = [
            {"size": "3B",   "quant": "Q8",  "vram_needed": 4000, "ram_needed": 8,  "feasible": False},
            {"size": "3B",   "quant": "Q4",  "vram_needed": 2500, "ram_needed": 8,  "feasible": False},
            {"size": "7B",   "quant": "Q8",  "vram_needed": 8000, "ram_needed": 16, "feasible": False},
            {"size": "7B",   "quant": "Q6",  "vram_needed": 6000, "ram_needed": 16, "feasible": False},
            {"size": "7B",   "quant": "Q4",  "vram_needed": 4500, "ram_needed": 12, "feasible": False},
            {"size": "14B",  "quant": "Q4",  "vram_needed": 9000, "ram_needed": 24, "feasible": False},
            {"size": "20B",  "quant": "Q4",  "vram_needed": 14000,"ram_needed": 32, "feasible": False},
            {"size": "32B",  "quant": "Q4",  "vram_needed": 20000,"ram_needed": 48, "feasible": False},
        ]

        for cfg in configs:
            vram_ok = vram >= cfg["vram_needed"] if vram > 0 else False
            ram_ok = (ram * 1024) >= cfg["ram_needed"] * 1024
            cfg["feasible"] = vram_ok and ram_ok
            results.append(cfg)

        return results

    def latency_estimate(self, model_size: str) -> Dict:
        """Return estimated latency bands."""
        gpu_present = self.gpu.present
        gpu_name = self.gpu.name.lower()

        gpu_tier = "low"
        if gpu_present:
            if "4090" in gpu_name or "4080" in gpu_name or "a100" in gpu_name or "h100" in gpu_name:
                gpu_tier = "high"
            elif "4060" in gpu_name or "4070" in gpu_name or "3080" in gpu_name or "3090" in gpu_name:
                gpu_tier = "medium"
            elif "3060" in gpu_name or "3070" in gpu_name:
                gpu_tier = "medium-low"

        size_speeds = {
            "3B":  {"high": 40, "medium": 25, "medium-low": 18, "low": 8},
            "7B":  {"high": 25, "medium": 15, "medium-low": 10, "low": 4},
            "14B": {"high": 15, "medium": 8,  "medium-low": 5,  "low": 2},
            "32B": {"high": 8,  "medium": 4,  "medium-low": 2,  "low": 1},
        }

        tokens_per_sec = size_speeds.get(model_size, {}).get(gpu_tier, 5)
        return {
            "gpu_tier": gpu_tier,
            "tokens_per_sec_estimate": tokens_per_sec,
            "gpu": gpu_name if gpu_present else "none",
        }


def detect_cpu() -> CPUInfo:
    info = CPUInfo()
    try:
        with open("/proc/cpuinfo") as f:
            data = f.read()
        models = set(re.findall(r"model name\s+:\s+(.*)", data))
        info.model = models.pop() if models else platform.processor()
        info.cores = len(re.findall(r"processor\s+:\s+(\d+)", data))
    except Exception:
        info.model = platform.processor()
        info.cores = os.cpu_count() or 0
    info.architecture = platform.machine()
    return info


def detect_ram() -> RAMInfo:
    info = RAMInfo()
    try:
        import psutil
        mem = psutil.virtual_memory()
        info.total_gb = round(mem.total / 1e9, 1)
        info.available_gb = round(mem.available / 1e9, 1)
    except ImportError:
        try:
            with open("/proc/meminfo") as f:
                data = f.read()
            total_kb = re.search(r"MemTotal:\s+(\d+)", data)
            avail_kb = re.search(r"MemAvailable:\s+(\d+)", data)
            if total_kb:
                info.total_gb = round(int(total_kb.group(1)) / 1e6, 1)
            if avail_kb:
                info.available_gb = round(int(avail_kb.group(1)) / 1e6, 1)
        except Exception:
            info.total_gb = 0.0
    return info


def detect_gpu() -> GPUInfo:
    info = GPUInfo()
    # Check nvidia-smi
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        try:
            result = subprocess.run(
                [nvidia_smi, "--query-gpu=name,memory.total,driver_version",
                 "--format=csv,noheader"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = [p.strip() for p in result.stdout.strip().split(", ")]
                info.present = True
                info.name = parts[0] if len(parts) > 0 else "unknown"
                mem_str = parts[1] if len(parts) > 1 else "0 MiB"
                info.vram_total_mb = int(mem_str.replace(" MiB", "").replace(" MB", ""))
                info.driver_version = parts[2] if len(parts) > 2 else ""
                info.backend = "cuda"
        except Exception:
            pass
    return info


def detect_disk(path: str = "/home") -> DiskInfo:
    info = DiskInfo(path=path)
    try:
        stat = os.statvfs(path)
        info.total_gb = round(stat.f_frsize * stat.f_blocks / 1e9, 0)
        info.free_gb = round(stat.f_frsize * stat.f_bfree / 1e9, 0)
    except Exception:
        pass
    return info


def detect_ollama() -> tuple:
    """Returns (available: bool, models: list)."""
    ollama = shutil.which("ollama")
    if not ollama:
        return False, []
    try:
        result = subprocess.run([ollama, "list"], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return True, []
        models = []
        for line in result.stdout.strip().split("\n")[1:]:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 3:
                models.append({"name": parts[0], "size": parts[2] + " " + parts[3] if len(parts) > 3 else ""})
        return True, models
    except Exception:
        return True, []


def detect_all() -> HardwareProfile:
    """Detect all hardware and return a complete profile."""
    profile = HardwareProfile(
        cpu=detect_cpu(),
        ram=detect_ram(),
        gpu=detect_gpu(),
        disk=detect_disk(),
        platform=platform.platform(),
    )
    ollama_avail, ollama_models = detect_ollama()
    profile.ollama_available = ollama_avail
    profile.ollama_models = ollama_models
    return profile


def profile_to_json(profile: HardwareProfile) -> str:
    return json.dumps(profile.to_dict(), indent=2)
