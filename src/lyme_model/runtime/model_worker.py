"""Shared model loading and generation — used by both worker.py and server_worker.py.

Uses lazy imports so that test mocking via sys.modules patching works correctly.
"""

import json
import sys
import traceback
import re
import os
import shutil
import gc
from typing import Optional


def check_bitsandbytes(required: str = None):
    try:
        import bitsandbytes  # noqa: F401
    except ImportError:
        msg = (
            "bitsandbytes is required for quantized loading.\n"
            "  Install with:  pip install bitsandbytes\n"
        )
        if required == "4bit":
            msg += "  Minimum version: bitsandbytes>=0.41.0"
        elif required == "8bit":
            msg += "  Minimum version: bitsandbytes>=0.37.0"
        raise RuntimeError(msg)


def resolve_dtype(dtype_str: str = None):
    import torch
    if dtype_str is None:
        return torch.float16 if torch.cuda.is_available() else torch.float32
    mapping = {
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
        "float32": torch.float32,
    }
    if dtype_str not in mapping:
        raise ValueError(f"Unsupported dtype: {dtype_str}. Choose: float16, bfloat16, float32")
    return mapping[dtype_str]


def load_model(init_data: dict):
    """Load model and tokenizer from init data dict. Returns (model, tokenizer)."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    model_name = init_data["model_name"]
    adapter_path = init_data.get("adapter_path")
    device = init_data.get("device", "auto")
    offload_dir = init_data.get("offload_dir")
    debug = init_data.get("debug", False)
    safe_mode = init_data.get("safe_mode", False)
    load_in_4bit = init_data.get("load_in_4bit", False)
    load_in_8bit = init_data.get("load_in_8bit", False)
    dtype_str = init_data.get("dtype")

    _clear_offload_dir(offload_dir)

    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=True)
    except Exception as exc:
        raise RuntimeError(f"tokenizer_load_failed: {type(exc).__name__}: {exc}")

    torch_dtype = resolve_dtype(dtype_str)

    if load_in_4bit:
        check_bitsandbytes("4bit")
        from transformers import BitsAndBytesConfig
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
        model_kwargs = {
            "quantization_config": quant_config,
            "device_map": "auto",
            "torch_dtype": torch.float16,
        }
    elif load_in_8bit:
        check_bitsandbytes("8bit")
        model_kwargs = {
            "load_in_8bit": True,
            "device_map": "auto",
        }
    else:
        model_kwargs = {
            "torch_dtype": torch_dtype,
            "device_map": "auto" if device == "auto" else device,
            "offload_folder": offload_dir,
            "offload_state_dict": True,
        }

    try:
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            local_files_only=True,
            **model_kwargs,
        )
    except Exception as exc:
        raise RuntimeError(f"base_load_failed: {type(exc).__name__}: {exc}")

    if adapter_path:
        try:
            if safe_mode:
                model = PeftModel.from_pretrained(model, adapter_path)
                model = model.eval()
            else:
                model = PeftModel.from_pretrained(
                    model,
                    adapter_path,
                    offload_folder=offload_dir,
                    offload_state_dict=True,
                )
        except KeyError as exc:
            key_str = str(exc)
            if re.search(r"base_model\.model\.model\.layers\.\d+\.\S+", key_str) and not safe_mode:
                _clear_offload_dir(offload_dir)
                del model
                torch.cuda.empty_cache()
                gc.collect()
                try:
                    model = AutoModelForCausalLM.from_pretrained(
                        model_name,
                        local_files_only=True,
                        **model_kwargs,
                    )
                    model = PeftModel.from_pretrained(model, adapter_path)
                    model = model.eval()
                except Exception as exc2:
                    raise RuntimeError(f"adapter_load_failed: {type(exc2).__name__}: {exc2}")
            else:
                raise RuntimeError(f"adapter_load_failed: {type(exc).__name__}: {exc}")
        except Exception as exc:
            raise RuntimeError(f"adapter_load_failed: {type(exc).__name__}: {exc}")

    model.eval()
    return model, tokenizer


def generate_text(model, tokenizer, prompt: str, gen_kwargs: dict) -> dict:
    """Generate text. Returns dict with output, prompt_tokens, generated_tokens."""
    import torch
    inputs = tokenizer(prompt, return_tensors="pt")
    input_len = int(inputs["input_ids"].shape[1])
    device = next(model.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model.generate(**inputs, **gen_kwargs)

    generated = int(outputs.shape[1]) - input_len
    output_text = tokenizer.decode(
        outputs[0][input_len:], skip_special_tokens=True
    ).strip()

    return {
        "output": output_text,
        "prompt_tokens": input_len,
        "generated_tokens": generated,
    }


def cleanup(model=None, tokenizer=None):
    import torch
    if model is not None:
        try:
            del model
        except Exception:
            pass
    if tokenizer is not None:
        try:
            del tokenizer
        except Exception:
            pass
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _clear_offload_dir(offload_dir):
    if offload_dir and os.path.isdir(offload_dir):
        shutil.rmtree(offload_dir)
    if offload_dir:
        os.makedirs(offload_dir, exist_ok=True)
