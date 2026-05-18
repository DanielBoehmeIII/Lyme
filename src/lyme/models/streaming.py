"""Streaming — token-by-token streaming inference support."""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generator, List, Optional, Protocol


TokenHandler = Callable[[str], None]


@dataclass
class StreamConfig:
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.95
    stop_sequences: List[str] = field(default_factory=lambda: ["\n\n", "```"])
    stream_interval: float = 0.01  # seconds between token callbacks


@dataclass
class StreamStats:
    total_tokens: int = 0
    start_time: float = 0.0
    first_token_time: float = 0.0
    end_time: float = 0.0
    tokens_per_second: float = 0.0
    time_to_first_token_ms: float = 0.0

    @property
    def elapsed(self) -> float:
        return self.end_time - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tokens": self.total_tokens,
            "tokens_per_second": round(self.tokens_per_second, 2),
            "time_to_first_token_ms": round(self.time_to_first_token_ms, 2),
            "elapsed_seconds": round(self.elapsed, 2),
        }


class TokenStream:
    def __init__(self, config: StreamConfig = None):
        self.config = config or StreamConfig()
        self.stats = StreamStats()
        self._handlers: List[TokenHandler] = []
        self._buffer: List[str] = []
        self._done = False

    def on_token(self, handler: TokenHandler) -> None:
        self._handlers.append(handler)

    def start(self) -> None:
        self.stats.start_time = time.time()
        self._buffer = []
        self._done = False

    def feed(self, token: str) -> None:
        if self.stats.first_token_time == 0:
            self.stats.first_token_time = time.time()
            self.stats.time_to_first_token_ms = (
                self.stats.first_token_time - self.stats.start_time
            ) * 1000

        self._buffer.append(token)
        self.stats.total_tokens += 1

        for handler in self._handlers:
            try:
                handler(token)
            except Exception:
                pass

    def complete(self) -> str:
        self._done = True
        self.stats.end_time = time.time()
        elapsed = self.stats.end_time - self.stats.start_time
        if elapsed > 0:
            self.stats.tokens_per_second = self.stats.total_tokens / elapsed
        return self.full_text

    @property
    def full_text(self) -> str:
        return "".join(self._buffer)

    @property
    def is_done(self) -> bool:
        return self._done


class StreamingBackend(Protocol):
    def generate_stream(self, prompt: str, config: StreamConfig) -> Generator[str, None, str]: ...


def simulate_streaming(text: str, chunk_size: int = 1) -> Generator[str, None, None]:
    """Simulate token-by-token streaming from full text."""
    words = text.split(" ")
    for i, word in enumerate(words):
        yield word + (" " if i < len(words) - 1 else "")
        time.sleep(0.01)
