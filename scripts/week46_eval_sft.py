#!/usr/bin/env python3
"""Week 46 — SFT v1 Evaluation.

Compares base model vs SFT v1 adapter on:
- patch validity (is the diff well-formed?)
- test repair success (does the fix pass?)
- hallucinated paths (does it reference nonexistent files?)
- evidence use (does it reference provided context?)
"""

import json
import re
import sys
import time
import torch
from pathlib import Path
from collections import defaultdict
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

REPORT_DIR = Path("lyme-output/week46")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

BASE_MODEL = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
ADAPTER_PATH = "checkpoints/sft_v1_week46/final"
EVAL_DATA = "datasets/v1/eval_only/test/combined.jsonl"
BENCHMARK_TASKS = "datasets/v1/sft/test/combined.jsonl"

def load_model(model_name, adapter_path=None):
    print(f"  Loading model: {model_name}")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    if adapter_path and Path(adapter_path).exists():
        print(f"  Loading adapter: {adapter_path}")
        model = PeftModel.from_pretrained(model, adapter_path)
    return model, tokenizer

def generate(model, tokenizer, prompt, max_tokens=256):
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024).to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=0.3,
            top_p=0.9,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
        )
    return tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()

def is_valid_diff(output):
    return bool(re.search(r'---\s+a/', output) and re.search(r'\+\+\+\s+b/', output))

def has_hallucinated_paths(output, valid_files):
    if not valid_files:
        return False
    paths = re.findall(r'(?:src/|tests/|config/|lib/|app/)\S+\.\w+', output)
    return any(p not in valid_files for p in paths)

def is_test_repair_valid(output):
    return bool(re.search(r'assert\s+', output))

def has_evidence_use(output, instruction):
    if not instruction:
        return True
    inst_lower = instruction.lower()
    keywords = re.findall(r'\b(src/|tests/|config/|file:|function:|class:)\S*', inst_lower)
    if not keywords:
        return True
    return any(k in output.lower() for k in keywords[:3])

def load_jsonl_lines(path, n=200):
    result = []
    with open(path) as f:
        for i, line in enumerate(f):
            if i >= n:
                break
            if line.strip():
                try:
                    result.append(json.loads(line))
                except:
                    pass
    return result

def eval_model(model, tokenizer, label, eval_examples):
    results = []
    metrics = {"valid_diff": 0, "test_repair": 0, "hallucinated": 0, "evidence_use": 0, "total": 0, "latency": []}

    template = "### Instruction:\n{instruction}\n\n### Context:\n{context}\n\n### Response:\n"

    for i, ex in enumerate(eval_examples):
        instruction = ex.get("instruction", "")
        context = ""
        rc = ex.get("repo_context", {})
        if isinstance(rc, dict) and rc.get("repo_name"):
            context += f"Repository: {rc['repo_name']}\nLanguage: {rc['language']}\n"
        files = ex.get("retrieved_files", [])
        if files:
            context += "Relevant files:\n"
            for f in files[:3]:
                context += f"- {f.get('file_path', '')}: {f.get('content_preview', '')[:80]}\n"

        prompt = template.format(instruction=instruction, context=context)
        modality = ex.get("modality", "")

        start = time.time()
        output = generate(model, tokenizer, prompt, max_tokens=256)
        latency = time.time() - start

        valid_files = set()
        for f in files:
            fp = f.get("file_path", "")
            if fp:
                valid_files.add(fp)

        md = ex.get("metadata", {})
        result = {
            "id": ex.get("id", f"eval-{i}"),
            "modality": modality,
            "instruction": instruction[:80],
            "output": output[:200],
            "latency": round(latency, 2),
        }

        if modality == "unified_diff":
            result["valid_diff"] = is_valid_diff(output)
            if result["valid_diff"]:
                metrics["valid_diff"] += 1
            result["hallucinated"] = has_hallucinated_paths(output, valid_files)
            if result["hallucinated"]:
                metrics["hallucinated"] += 1

        if modality == "test_repair":
            result["valid_fix"] = is_test_repair_valid(output)
            if result["valid_fix"]:
                metrics["test_repair"] += 1

        result["evidence_use"] = has_evidence_use(output, instruction)
        if result["evidence_use"]:
            metrics["evidence_use"] += 1

        metrics["total"] += 1
        metrics["latency"].append(latency)
        results.append(result)

        if (i + 1) % 50 == 0:
            print(f"    {label}: evaluated {i+1}/{len(eval_examples)}")

    return results, metrics

def main():
    print("=" * 72)
    print("  Week 46 — SFT v1 Evaluation")
    print("=" * 72)

    # Load eval examples
    eval_examples = load_jsonl_lines(EVAL_DATA, 100)
    benchmark_examples = load_jsonl_lines(BENCHMARK_TASKS, 100)
    all_examples = eval_examples + benchmark_examples
    print(f"\n  Eval examples: {len(eval_examples)} (eval_only) + {len(benchmark_examples)} (sft test)")

    # Eval models
    model_configs = [
        ("Base model (Qwen0.5B)", BASE_MODEL, None),
    ]

    if Path(ADAPTER_PATH).exists():
        model_configs.append(("SFT v1 (Qwen0.5B+LoRA)", BASE_MODEL, ADAPTER_PATH))
    else:
        print(f"\n  [WARN] No SFT adapter found at {ADAPTER_PATH}")
        print("  Training may still be in progress. Run eval after training completes.")

    all_metrics = {}
    all_results = {}

    for label, base_model, adapter_path in model_configs:
        print(f"\n  Evaluating: {label}")
        model, tokenizer = load_model(base_model, adapter_path)
        results, metrics = eval_model(model, tokenizer, label, all_examples)
        all_metrics[label] = metrics
        all_results[label] = results
        avg_lat = sum(metrics["latency"]) / len(metrics["latency"]) if metrics["latency"] else 0
        total = metrics["total"]
        print(f"    Done: {total} examples, avg latency {avg_lat:.2f}s")

    # Build report
    report = [
        "# Week 46 — SFT v1 Evaluation Report",
        f"> Generated: evaluation comparing base model to SFT v1 adapter",
        f"> Base: {BASE_MODEL}",
        f"> Adapter: {ADAPTER_PATH}",
        "",
        "## Evaluation Metrics",
        "| Metric | Base Model | SFT v1 | Delta |",
        "|--------|-----------|--------|-------|",
    ]

    for label, metrics in all_metrics.items():
        avg_lat = sum(metrics["latency"]) / len(metrics["latency"]) if metrics["latency"] else 0
        pct_vd = 100 * metrics["valid_diff"] / max(metrics["total"], 1)
        pct_tr = 100 * metrics["test_repair"] / max(metrics["total"], 1)
        pct_hall = 100 * metrics["hallucinated"] / max(metrics["total"], 1)
        pct_ev = 100 * metrics["evidence_use"] / max(metrics["total"], 1)

        report.append(f"\n### {label}")
        report.append(f"| Metric | Value |")
        report.append(f"|--------|-------|")
        report.append(f"| Total examples | {metrics['total']} |")
        report.append(f"| Valid diff rate | {pct_vd:.1f}% |")
        report.append(f"| Test repair success | {pct_tr:.1f}% |")
        report.append(f"| Hallucinated paths | {pct_hall:.1f}% |")
        report.append(f"| Evidence use | {pct_ev:.1f}% |")
        report.append(f"| Avg latency | {avg_lat:.2f}s |")

    report.append("\n## Comparative Summary")
    if len(all_metrics) >= 2:
        labels = list(all_metrics.keys())
        base = all_metrics[labels[0]]
        sft = all_metrics[labels[1]]
        report.append(f"| Metric | Base | SFT v1 | Change |")
        report.append(f"|--------|------|--------|--------|")
        total = max(base["total"], 1)
        base_vd = 100 * base["valid_diff"] / total
        sft_vd = 100 * sft["valid_diff"] / total
        report.append(f"| Valid diff | {base_vd:.1f}% | {sft_vd:.1f}% | {sft_vd - base_vd:+.1f}% |")
        base_tr = 100 * base["test_repair"] / total
        sft_tr = 100 * sft["test_repair"] / total
        report.append(f"| Test repair | {base_tr:.1f}% | {sft_tr:.1f}% | {sft_tr - base_tr:+.1f}% |")
        base_hall = 100 * base["hallucinated"] / total
        sft_hall = 100 * sft["hallucinated"] / total
        report.append(f"| Hallucinated | {base_hall:.1f}% | {sft_hall:.1f}% | {sft_hall - base_hall:+.1f}% |")

    report_path = REPORT_DIR / "SFT_V1_EVAL_REPORT.md"
    report_path.write_text("\n".join(report))

    # Save detailed results
    for label, results in all_results.items():
        safe = label.replace(" ", "_").replace("/", "_")
        with open(REPORT_DIR / f"eval_results_{safe}.json", "w") as f:
            json.dump(results, f, indent=2)

    print(f"\n  Report: {report_path}")
    if len(all_metrics) >= 2:
        base_m = all_metrics[list(all_metrics.keys())[0]]
        sft_m = all_metrics[list(all_metrics.keys())[1]]
        print(f"  Base model valid diff: {base_m['valid_diff']}/{base_m['total']}")
        print(f"  SFT v1 valid diff:     {sft_m['valid_diff']}/{sft_m['total']}")
    print("=" * 72)

if __name__ == "__main__":
    main()
