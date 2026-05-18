"""CircuitBreaker — prevents repeated failures by short-circuiting."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitConfig:
    failure_threshold: int = 5
    recovery_timeout_s: float = 30.0
    half_open_max_calls: int = 3
    name: str = "default"


class CircuitBreaker:
    def __init__(self, config: CircuitConfig = None):
        self.config = config or CircuitConfig()
        self.state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._half_open_calls = 0

    def call(self, fn, *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            if time.time() - self._last_failure_time > self.config.recovery_timeout_s:
                self.state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
            else:
                raise RuntimeError(f"Circuit breaker OPEN for {self.config.name}")

        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self.config.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self._failure_count = 0
        self._failure_count = 0

    def _on_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN

    def reset(self) -> None:
        self.state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0

    def get_state(self) -> Dict[str, Any]:
        return {
            "name": self.config.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "threshold": self.config.failure_threshold,
        }
