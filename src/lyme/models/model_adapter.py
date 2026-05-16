from __future__ import annotations

import abc
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Protocol


class ModelBackend(str, Enum):
    OLLAMA = "ollama"
    LLAMA_CPP = "llama.cpp"
    TRANSFORMERS = "transformers"


@dataclass
class AdapterStats:
    total_requests: int = 0
    total_tokens_generated: int = 0
    total_tokens_prompt: int = 0
    total_time_s: float = 0.0
    errors: int = 0
    last_error: Optional[str] = None

    def tokens_per_second(self) -> float:
        if self.total_time_s > 0:
            return self.total_tokens_generated / self.total_time_s
        return 0.0

    def error_rate(self) -> float:
        if self.total_requests > 0:
            return self.errors / self.total_requests
        return 0.0


class PromptTemplate:
    """Simple prompt templating with common chat formats."""

    FORMATS = {
        "chatml": "<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n",
        "llama2": "[INST] <<SYS>>\n{system}\n<</SYS>>\n\n{prompt} [/INST]",
        "llama3": "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{system}<|eot_id|>\n<|start_header_id|>user<|end_header_id|>\n{prompt}<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>",
        "deepseek": "system: {system}\n\nuser: {prompt}\n\nassistant:",
        "qwen": "<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n",
        "phi3": "<s><|system|>\n{system}<|end|>\n<|user|>\n{prompt}<|end|>\n<|assistant|>\n",
    }

    @staticmethod
    def format(prompt: str, system: str = "", fmt: str = "chatml") -> str:
        template = PromptTemplate.FORMATS.get(fmt)
        if template is None:
            return prompt
        return template.format(system=system, prompt=prompt)

    @staticmethod
    def detect_format(model_name: str) -> str:
        name = model_name.lower()
        if "qwen" in name:
            return "qwen"
        if "deepseek" in name:
            return "deepseek"
        if "llama-3" in name or "llama3" in name:
            return "llama3"
        if "llama" in name or "codellama" in name:
            return "llama2"
        if "phi-3" in name or "phi3" in name:
            return "phi3"
        return "chatml"


def count_tokens(text: str, model_prefix: str = "") -> int:
    """Rough token count estimation using word-piece heuristics."""
    if not text:
        return 0
    if "gpt-4" in model_prefix or "gpt-3.5" in model_prefix:
        return len(text) // 4
    text = re.sub(r"\s+", " ", text)
    tokens = len(re.findall(r"\w+|[^\w\s]", text))
    subword_penalty = max(0, len(text) - tokens * 5) // 3
    return tokens + subword_penalty


class ModelAdapter(abc.ABC):
    """Abstract base for all model backends."""

    def __init__(self, model_name: str, backend: ModelBackend) -> None:
        self.model_name = model_name
        self.backend = backend
        self.stats: AdapterStats = AdapterStats()
        self._aborted: bool = False

    def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        system: str = "",
    ) -> str:
        self._aborted = False
        prompt_tokens = count_tokens(prompt)
        start = time.perf_counter()
        try:
            result = self._generate_impl(prompt, max_tokens, temperature, system)
            elapsed = time.perf_counter() - start
            generated_tokens = count_tokens(result)
            self.stats.total_requests += 1
            self.stats.total_tokens_generated += generated_tokens
            self.stats.total_tokens_prompt += prompt_tokens
            self.stats.total_time_s += elapsed
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start
            self.stats.total_requests += 1
            self.stats.total_tokens_prompt += prompt_tokens
            self.stats.total_time_s += elapsed
            self.stats.errors += 1
            self.stats.last_error = str(e)
            raise ModelLoadError(f"{self.backend.value}/{self.model_name}: {e}") from e

    @abc.abstractmethod
    def _generate_impl(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system: str,
    ) -> str:
        ...

    def embed(self, text: str) -> List[float]:
        return self._embed_impl(text)

    def _embed_impl(self, text: str) -> List[float]:
        raise NotImplementedError(f"{self.backend.value} does not support embeddings")

    def token_count(self, text: str) -> int:
        return count_tokens(text, self.model_name)

    def abort(self) -> None:
        self._aborted = True

    def get_stats(self) -> AdapterStats:
        return self.stats

    def reset_stats(self) -> None:
        self.stats = AdapterStats()


class ModelLoadError(Exception):
    """Raised when a model fails to load or generate."""


class OllamaAdapter(ModelAdapter):
    """Adapter for Ollama HTTP API."""

    def __init__(self, model_name: str, base_url: str = "http://localhost:11434") -> None:
        super().__init__(model_name, ModelBackend.OLLAMA)
        self.base_url = base_url.rstrip("/")

    def _generate_impl(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system: str,
    ) -> str:
        import urllib.request
        import json

        fmt = PromptTemplate.detect_format(self.model_name)
        formatted = PromptTemplate.format(prompt, system=system, fmt=fmt)

        payload = json.dumps({
            "model": self.model_name,
            "prompt": formatted,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
            "stream": False,
        }).encode()

        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read())
        return data.get("response", "")

    def _embed_impl(self, text: str) -> List[float]:
        import urllib.request
        import json

        payload = json.dumps({"model": self.model_name, "prompt": text}).encode()
        req = urllib.request.Request(
            f"{self.base_url}/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        return data.get("embedding", [])


class LlamaCppAdapter(ModelAdapter):
    """Adapter for llama.cpp server or local python binding."""

    def __init__(
        self,
        model_name: str,
        model_path: str,
        n_ctx: int = 4096,
        n_gpu_layers: int = 0,
    ) -> None:
        super().__init__(model_name, ModelBackend.LLAMA_CPP)
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self._model = None

    def _load_model(self) -> None:
        if self._model is not None:
            return
        try:
            from llama_cpp import Llama
            self._model = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_gpu_layers=self.n_gpu_layers,
            )
        except ImportError:
            raise ModelLoadError("llama-cpp-python not installed. Install with: pip install llama-cpp-python")

    def _generate_impl(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system: str,
    ) -> str:
        self._load_model()
        fmt = PromptTemplate.detect_format(self.model_name)
        formatted = PromptTemplate.format(prompt, system=system, fmt=fmt)
        output = self._model(
            formatted,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=["</s>", "<|im_end|>", "<|eot_id|>"],
        )
        return output["choices"][0]["text"].strip()

    def _embed_impl(self, text: str) -> List[float]:
        self._load_model()
        return self._model.embed(text)


class TransformersAdapter(ModelAdapter):
    """Adapter for HuggingFace transformers."""

    def __init__(
        self,
        model_name: str,
        device: str = "auto",
        load_in_4bit: bool = True,
    ) -> None:
        super().__init__(model_name, ModelBackend.TRANSFORMERS)
        self.device = device
        self.load_in_4bit = load_in_4bit
        self._tokenizer = None
        self._model = None

    def _load_model(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map=self.device,
                load_in_4bit=self.load_in_4bit,
                torch_dtype=torch.float16 if not self.load_in_4bit else None,
            )
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token
        except ImportError:
            raise ModelLoadError(
                "transformers or torch not installed. Install with: pip install transformers torch"
            )
        except Exception as e:
            raise ModelLoadError(f"Failed to load {self.model_name} from HuggingFace: {e}")

    def _generate_impl(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system: str,
    ) -> str:
        self._load_model()
        fmt = PromptTemplate.detect_format(self.model_name)
        formatted = PromptTemplate.format(prompt, system=system, fmt=fmt)
        inputs = self._tokenizer(formatted, return_tensors="pt").to(self._model.device)
        outputs = self._model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=temperature > 0,
            pad_token_id=self._tokenizer.pad_token_id,
        )
        decoded = self._tokenizer.decode(outputs[0], skip_special_tokens=True)
        return decoded[len(formatted):].strip()

    def _embed_impl(self, text: str) -> List[float]:
        self._load_model()
        import torch
        inputs = self._tokenizer(text, return_tensors="pt").to(self._model.device)
        with torch.no_grad():
            outputs = self._model(**inputs)
        return outputs.last_hidden_state.mean(dim=1).squeeze().tolist()


def create_adapter(
    model_name: str,
    backend: ModelBackend = ModelBackend.OLLAMA,
    **kwargs: str,
) -> ModelAdapter:
    if backend == ModelBackend.OLLAMA:
        return OllamaAdapter(model_name, **kwargs)
    if backend == ModelBackend.LLAMA_CPP:
        model_path = kwargs.get("model_path", f"models/{model_name}.gguf")
        n_ctx = int(kwargs.get("n_ctx", "4096"))
        n_gpu_layers = int(kwargs.get("n_gpu_layers", "0"))
        return LlamaCppAdapter(model_name, model_path, n_ctx, n_gpu_layers)
    if backend == ModelBackend.TRANSFORMERS:
        device = kwargs.get("device", "auto")
        load_in_4bit = kwargs.get("load_in_4bit", "true").lower() == "true"
        return TransformersAdapter(model_name, device, load_in_4bit)
    raise ValueError(f"Unknown backend: {backend}")
