"""Quick hardware benchmark for Lyme Model.
Tests token latency and throughput for available local models.
"""

import time, json, sys, subprocess
sys.path.insert(0, "src")
from lyme_model.hardware.detector import detect_all
from lyme_model.hardware.monitor import HardwareMonitor

SHORT_PROMPT = "Write a Python function to read a file and find all TODOs."


def benchmark_ollama(model_name: str) -> dict:
    result = {"model": model_name}
    prompt = SHORT_PROMPT + "\nReturn only the code, no explanation."
    try:
        start = time.time()
        proc = subprocess.run(
            ["ollama", "run", model_name, prompt],
            capture_output=True, text=True, timeout=60
        )
        elapsed = time.time() - start
        output = proc.stdout
        # Count words as approximation of token count
        word_count = len(output.split())
        result["generation_time_s"] = round(elapsed, 2)
        result["estimated_tokens"] = word_count
        result["tokens_per_second"] = round(word_count / elapsed, 1) if elapsed > 0 else 0.0
        result["output_length_chars"] = len(output)
    except subprocess.TimeoutExpired:
        result["error"] = "timeout"
    except Exception as e:
        result["error"] = str(e)
    return result


profile = detect_all()
print("=" * 60)
print("HARDWARE REALITY BASELINE")
print("=" * 60)
print(f"CPU: {profile.cpu.model} ({profile.cpu.cores} cores)")
print(f"RAM: {profile.ram.total_gb} GB")
if profile.gpu.present:
    print(f"GPU: {profile.gpu.name} ({profile.gpu.vram_total_mb} MB VRAM)")
print(f"Disk: {profile.disk.total_gb:.0f} GB")
print()

results = []
for m in profile.ollama_models:
    name = m["name"]
    if "-cloud" in name:
        continue  # skip cloud-only models
    print(f"Benchmarking: {name}...")
    r = benchmark_ollama(name)
    results.append(r)
    status = f"{r.get('tokens_per_second', 'ERR')} tok/s"
    if r.get("error"):
        status = f"ERROR: {r['error']}"
    print(f"  {status}")
    print()

print("=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"{'Model':30s} {'Tok/s':8s} {'Time':8s} {'Chars':8s}")
print("-" * 60)
for r in results:
    print(f"{r['model']:30s} "
          f"{str(r.get('tokens_per_second', '?')):8s} "
          f"{str(r.get('generation_time_s', '?')):8s} "
          f"{str(r.get('output_length_chars', '?')):8s}")

output = {"hardware_profile": profile.to_dict(), "results": results}
with open("lyme-output/sprint-weeks-53-72/hardware-baseline-results.json", "w") as f:
    json.dump(output, f, indent=2)
print("\nSaved to lyme-output/sprint-weeks-53-72/hardware-baseline-results.json")
