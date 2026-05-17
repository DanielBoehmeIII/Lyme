#!/usr/bin/env python3
"""Lyme Model — SFT Training Pipeline

Runs supervised fine-tuning with LoRA/QLoRA on a base model.
Supports:
- LoRA and QLoRA (4-bit/8-bit quantization)
- Gradient checkpointing
- Resume from checkpoint
- DeepSpeed ZeRO-2
- YAML config or CLI overrides
- Train/val/test splits
- Wandb/tensorboard logging
"""

import argparse
import json
import os
import sys
import time
import yaml
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any


def load_config(config_path: str) -> Dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def override_config(config: Dict, overrides: List[str]) -> Dict:
    """Override nested config keys from CLI --key value pairs."""
    for override in overrides:
        if "=" not in override:
            continue
        key, value = override.split("=", 1)
        parts = key.strip("--").split(".")
        target = config
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        # Type coercion
        if value.lower() in ("true", "false"):
            target[parts[-1]] = value.lower() == "true"
        elif value.isdigit():
            target[parts[-1]] = int(value)
        elif value.replace(".", "", 1).isdigit():
            target[parts[-1]] = float(value)
        else:
            target[parts[-1]] = value
    return config


def detect_hardware() -> Dict:
    info = {}
    try:
        import torch
        info["torch_version"] = torch.__version__
        info["cuda_available"] = torch.cuda.is_available()
        info["cuda_version"] = torch.version.cuda if info["cuda_available"] else None
        if info["cuda_available"]:
            info["device_count"] = torch.cuda.device_count()
            info["device_name"] = torch.cuda.get_device_name(0)
            info["vram_gb"] = round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1)
    except ImportError:
        info["torch_version"] = None
    return info


def load_dataset_files(train_file: str, val_file: str, test_file: str) -> Dict:
    """Load JSONL dataset files."""
    def load_jsonl(path: str) -> List[Dict]:
        p = Path(path)
        if not p.exists():
            return []
        with open(p) as f:
            return [json.loads(line) for line in f if line.strip()]

    return {
        "train": load_jsonl(train_file),
        "val": load_jsonl(val_file),
        "test": load_jsonl(test_file),
    }


def format_example(ex: Dict, instruction_template: str) -> str:
    """Format a training example using the template.
    Supports both flat format (instruction/context/output) and
    canonical LymeExample format (with nested repo_context/retrieved_files)."""
    instruction = ex.get("instruction", ex.get("task", ""))

    # Build context string from various formats
    context = ""
    rc = ex.get("repo_context")
    if isinstance(rc, dict):
        parts = []
        if rc.get("repo_name"):
            parts.append(f"Repository: {rc['repo_name']}")
        if rc.get("language"):
            parts.append(f"Language: {rc['language']}")
        if rc.get("framework"):
            parts.append(f"Framework: {rc['framework']}")
        if rc.get("architecture_summary"):
            parts.append(f"Architecture: {rc['architecture_summary']}")
        if rc.get("conventions"):
            parts.append(f"Conventions: {', '.join(rc['conventions'][:3])}")
        context = "\n".join(parts)
    else:
        context = ex.get("context", ex.get("input_context", ""))

    # Add retrieved files as context
    files = ex.get("retrieved_files", [])
    if files:
        file_lines = []
        for f in files[:5]:
            file_lines.append(f"- {f.get('file_path', '')} ({f.get('role', '')}): {f.get('content_preview', '')[:100]}")
        if file_lines:
            context += "\n\nRelevant files:\n" + "\n".join(file_lines)

    output = ex.get("output", ex.get("response", ex.get("target_output", "")))

    text = instruction_template.replace("{instruction}", instruction).replace("{context}", context)
    return text + " " + output


class SFTTrainer:
    """Supervised fine-tuning trainer with LoRA/QLoRA support."""

    def __init__(self, config: Dict):
        self.config = config
        self.model = None
        self.tokenizer = None

    def setup(self):
        import torch
        from transformers import (
            AutoModelForCausalLM, AutoTokenizer,
            BitsAndBytesConfig, TrainingArguments, Trainer,
            DataCollatorForLanguageModeling, EarlyStoppingCallback,
        )
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

        model_cfg = self.config["model"]
        quant_cfg = self.config["quantization"]
        lora_cfg = self.config["lora"]
        train_cfg = self.config["training"]

        print(f"[setup] Loading model: {model_cfg['name']}")

        # Quantization config
        bnb_config = None
        if quant_cfg["enabled"]:
            compute_dtype = getattr(torch, quant_cfg["bnb_4bit_compute_dtype"])
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=quant_cfg.get("load_in_4bit", True),
                bnb_4bit_compute_dtype=compute_dtype,
                bnb_4bit_use_double_quant=quant_cfg.get("bnb_4bit_use_double_quant", True),
                bnb_4bit_quant_type=quant_cfg.get("bnb_4bit_quant_type", "nf4"),
            )

        # Load model
        model_dtype = model_cfg.get("dtype", "bfloat16")
        dtype = getattr(torch, model_dtype, torch.bfloat16) if isinstance(model_dtype, str) else model_dtype
        load_kwargs = dict(
            quantization_config=bnb_config,
            dtype=dtype,
            device_map=model_cfg.get("device_map", "auto"),
            attn_implementation=model_cfg.get("attn_implementation") or None,
            trust_remote_code=True,
        )
        if "max_memory" in model_cfg and model_cfg["max_memory"]:
            mm = model_cfg["max_memory"]
            load_kwargs["max_memory"] = {int(k) if isinstance(k, str) and k.isdigit() else k: v for k, v in mm.items()}
        self.model = AutoModelForCausalLM.from_pretrained(
            model_cfg["name"],
            **load_kwargs,
        )

        # Gradient checkpointing
        if train_cfg.get("gradient_checkpointing", True):
            self.model.gradient_checkpointing_enable()

        # Prepare for k-bit training if using QLoRA
        if quant_cfg["enabled"]:
            self.model = prepare_model_for_kbit_training(self.model)

        # LoRA config
        lora_config = LoraConfig(
            r=lora_cfg["r"],
            lora_alpha=lora_cfg["alpha"],
            lora_dropout=lora_cfg["dropout"],
            target_modules=lora_cfg["target_modules"],
            bias=lora_cfg.get("bias", "none"),
            task_type=lora_cfg.get("task_type", "CAUSAL_LM"),
        )
        self.model = get_peft_model(self.model, lora_config)
        self.model.print_trainable_parameters()

        # Tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_cfg["name"],
            trust_remote_code=True,
            truncation_side=model_cfg.get("truncation_side", "left"),
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        print("[setup] Model and tokenizer loaded successfully")
        return self.model, self.tokenizer

    def tokenize_dataset(self, examples: List[Dict]) -> List[Dict]:
        if self.tokenizer is None:
            raise RuntimeError("Tokenizer not loaded. Call setup() first.")
        data_cfg = self.config["data"]
        template = data_cfg["instruction_template"]

        tokenized = []
        for ex in examples:
            text = format_example(ex, template)
            tokenized.append(
                self.tokenizer(
                    text,
                    truncation=True,
                    max_length=self.config["training"]["max_seq_length"],
                    padding=False,
                )
            )
        return tokenized

    def train(self, dataset: Dict):
        import torch
        from transformers import TrainingArguments, Trainer, DataCollatorForLanguageModeling, EarlyStoppingCallback
        from datasets import Dataset as HFDataset

        train_cfg = self.config["training"]
        resume_cfg = self.config["resume"]

        print(f"[train] Training examples: {len(dataset.get('train', []))}")
        print(f"[train] Validation examples: {len(dataset.get('val', []))}")

        # Tokenize
        train_tokens = self.tokenize_dataset(dataset.get("train", []))
        val_tokens = self.tokenize_dataset(dataset.get("val", [])) if dataset.get("val") else None

        train_dataset = HFDataset.from_list(train_tokens) if train_tokens else None
        val_dataset = HFDataset.from_list(val_tokens) if val_tokens else None

        if train_dataset is None:
            raise ValueError("No training data available")

        # DeepSpeed config
        deepspeed_config = None
        if self.config.get("deepseed", {}).get("enabled", False):
            ds_path = self.config["deepseed"]["config_path"]
            if Path(ds_path).exists():
                deepspeed_config = ds_path
                print(f"[train] Using DeepSpeed config: {ds_path}")

        # Training arguments
        output_dir = train_cfg.get("output_dir", "checkpoints/")
        bf16_enabled = train_cfg.get("bf16", True) and torch.cuda.is_available() and torch.cuda.is_bf16_supported()
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=train_cfg["num_train_epochs"],
            per_device_train_batch_size=train_cfg["per_device_train_batch_size"],
            per_device_eval_batch_size=train_cfg.get("per_device_eval_batch_size", 4),
            gradient_accumulation_steps=train_cfg["gradient_accumulation_steps"],
            gradient_checkpointing=train_cfg.get("gradient_checkpointing", True),
            gradient_checkpointing_kwargs=train_cfg.get("gradient_checkpointing_kwargs"),
            learning_rate=train_cfg["learning_rate"],
            warmup_ratio=train_cfg.get("warmup_ratio", 0.03),
            lr_scheduler_type=train_cfg.get("lr_scheduler_type", "cosine"),
            weight_decay=train_cfg.get("weight_decay", 0.01),
            max_grad_norm=train_cfg.get("max_grad_norm", 0.3),
            logging_steps=train_cfg.get("logging_steps", 10),
            save_steps=train_cfg.get("save_steps", 100),
            eval_steps=train_cfg.get("eval_steps", 100) if val_dataset else None,
            eval_strategy="steps" if val_dataset and train_cfg.get("eval_steps") else "no",
            save_strategy="steps",
            save_total_limit=train_cfg.get("save_total_limit", 3),
            load_best_model_at_end=train_cfg.get("load_best_model_at_end", True) and val_dataset is not None,
            metric_for_best_model=train_cfg.get("metric_for_best_model", "eval_loss"),
            greater_is_better=train_cfg.get("greater_is_better", False),
            ddp_find_unused_parameters=train_cfg.get("ddp_find_unused_parameters", False),
            report_to=train_cfg.get("report_to", "none"),
            seed=train_cfg.get("seed", 42),
            fp16=train_cfg.get("fp16", False),
            bf16=bf16_enabled,
            optim=train_cfg.get("optim", "adamw_torch"),
            deepspeed=deepspeed_config,
        )

        # Data collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False,
        )

        # Trainer
        callbacks = []
        if train_cfg.get("early_stopping_patience"):
            callbacks.append(EarlyStoppingCallback(early_stopping_patience=train_cfg["early_stopping_patience"]))

        self.trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            data_collator=data_collator,
            callbacks=callbacks if callbacks else None,
        )

        # Resume from checkpoint
        resume_from = None
        if resume_cfg.get("enabled") and resume_cfg.get("checkpoint_path"):
            resume_from = resume_cfg["checkpoint_path"]
            if Path(resume_from).exists():
                print(f"[train] Resuming from checkpoint: {resume_from}")
            else:
                print(f"[train] Checkpoint not found, starting fresh: {resume_from}")
                resume_from = None

        # Train
        print(f"[train] Starting training...")
        train_result = self.trainer.train(resume_from_checkpoint=resume_from)
        print(f"[train] Training complete!")

        # Save final model
        final_path = os.path.join(output_dir, "final")
        self.trainer.save_model(final_path)
        self.tokenizer.save_pretrained(final_path)
        print(f"[train] Final model saved to: {final_path}")

        # Save training metrics
        metrics = {
            "training_loss": float(train_result.training_loss) if hasattr(train_result, "training_loss") else None,
            "global_step": train_result.global_step if hasattr(train_result, "global_step") else None,
        }
        if val_dataset:
            eval_results = self.trainer.evaluate()
            metrics["eval_loss"] = float(eval_results.get("eval_loss", 0))
            metrics["eval_metrics"] = {k: float(v) for k, v in eval_results.items()}

        metrics_path = os.path.join(output_dir, "training_metrics.json")
        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)
        print(f"[train] Metrics saved to: {metrics_path}")

        return metrics


def main():
    parser = argparse.ArgumentParser(description="Lyme Model — SFT Training Pipeline")
    parser.add_argument("--config", default="training/configs/default.yaml", help="Path to YAML config")
    parser.add_argument("-o", "--override", action="append", default=[], help="Override config key=value (e.g., training.num_train_epochs=5)")
    parser.add_argument("--list-models", action="store_true", help="List available base models")
    parser.add_argument("--detect", action="store_true", help="Detect hardware and exit")
    parser.add_argument("--estimate-memory", action="store_true", help="Estimate memory requirements")
    args = parser.parse_args()

    # Detect hardware
    hw = detect_hardware()
    print(f"[hardware] PyTorch: {hw.get('torch_version', 'NOT INSTALLED')}")
    if hw.get("cuda_available"):
        print(f"[hardware] GPU: {hw['device_name']} ({hw['vram_gb']}GB VRAM)")
        print(f"[hardware] CUDA: {hw['cuda_version']}")
        print(f"[hardware] Devices: {hw['device_count']}")
    else:
        print(f"[hardware] CUDA not available — training on CPU (slow)")

    if args.detect:
        return

    # Load and override config
    config = load_config(args.config)
    config = override_config(config, args.override)
    print(f"[config] Loaded: {args.config}")
    print(f"[config] Model: {config['model']['name']}")
    print(f"[config] LoRA r={config['lora']['r']}, alpha={config['lora']['alpha']}")
    print(f"[config] QLoRA: {config['quantization']['enabled']}")
    print(f"[config] Epochs: {config['training']['num_train_epochs']}")
    print(f"[config] Batch: {config['training']['per_device_train_batch_size']} x grad_acc={config['training']['gradient_accumulation_steps']}")
    print(f"[config] LR: {config['training']['learning_rate']}")
    print(f"[config] Max seq: {config['training']['max_seq_length']}")

    # Estimate memory
    if args.estimate_memory:
        print(f"\n[estimate] Memory estimation for {config['model']['name']}:")
        model_name = config["model"]["name"]
        params_map = {
            "deepseek": 6.7,
            "7b": 7.0,
            "6.7b": 6.7,
            "14b": 14,
            "3b": 3.0,
            "1.5b": 1.5,
            "2b": 2.0,
            "8b": 8.0,
        }
        params_b = 7.0
        for key, val in params_map.items():
            if key in model_name.lower():
                params_b = val
                break
        quant = config["quantization"]
        use_qlora = quant.get("enabled", True)
        if use_qlora:
            model_vram = params_b * 0.5
            lora_vram = 0.3
            total = model_vram + lora_vram + 1.0
            print(f"    QLoRA mode: model={model_vram:.1f}GB + LoRA={lora_vram:.1f}GB + overhead=1.0GB = {total:.1f}GB")
        else:
            model_vram = params_b * 2
            optimizer = params_b * 8
            total = model_vram + optimizer + 1.0
            print(f"    Full mode: model={model_vram:.1f}GB + optimizer={optimizer:.1f}GB + overhead=1.0GB = {total:.1f}GB")
        print(f"    Available VRAM: {hw.get('vram_gb', '?')}GB")
        if total > hw.get("vram_gb", 99):
            print(f"    WARNING: Estimated VRAM exceeds available! Use QLoRA or smaller model.")
        return

    # Load dataset
    data_cfg = config["data"]
    dataset = load_dataset_files(
        data_cfg["train_file"],
        data_cfg["val_file"],
        data_cfg["test_file"],
    )
    print(f"\n[data] Train: {len(dataset['train'])} | Val: {len(dataset['val'])} | Test: {len(dataset['test'])}")

    if not dataset["train"]:
        print("[error] No training data found. Generate data first:")
        print("  python training/scripts/generate_dataset.py")
        sys.exit(1)

    # Train
    trainer = SFTTrainer(config)
    start = time.time()
    try:
        trainer.setup()
        metrics = trainer.train(dataset)
        elapsed = time.time() - start
        print(f"\n[train] Total time: {elapsed:.1f}s")
        print(f"[train] Final training loss: {metrics.get('training_loss', 'N/A')}")
        if "eval_loss" in metrics:
            print(f"[train] Final eval loss: {metrics['eval_loss']}")
    except Exception as e:
        print(f"\n[error] Training failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
