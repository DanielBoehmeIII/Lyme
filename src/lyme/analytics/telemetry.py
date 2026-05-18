import json
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class TelemetryConsent(str, Enum):
    NONE = "none"
    PRODUCT_ONLY = "product_only"
    ANONYMIZED = "anonymized"
    FULL = "full"


@dataclass
class TelemetryConfig:
    consent: TelemetryConsent = TelemetryConsent.NONE
    user_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    install_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    first_run: float = field(default_factory=time.time)
    last_prompt: float = 0.0
    prompt_count: int = 0

    def to_dict(self) -> dict:
        return {
            "consent": self.consent.value,
            "user_id": self.user_id,
            "install_id": self.install_id,
            "first_run": self.first_run,
            "last_prompt": self.last_prompt,
            "prompt_count": self.prompt_count,
        }


class TelemetryManager:
    def __init__(self, config_dir: str = ".lyme/analytics/telemetry"):
        self._config_dir = Path(config_dir)
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._config_path = self._config_dir / "config.json"
        self._config = self._load_config()
        self._events: list = []
        self._event_queue: list = []
        self._flush_threshold = 50
        self._rate_limit_window = 60.0
        self._rate_limit_count = 0
        self._rate_limit_reset = time.time()

    def _load_config(self) -> TelemetryConfig:
        if self._config_path.exists():
            try:
                data = json.loads(self._config_path.read_text())
                return TelemetryConfig(
                    consent=TelemetryConsent(data.get("consent", "none")),
                    user_id=data.get("user_id", uuid.uuid4().hex[:12]),
                    install_id=data.get("install_id", uuid.uuid4().hex[:12]),
                    first_run=data.get("first_run", time.time()),
                    last_prompt=data.get("last_prompt", 0.0),
                    prompt_count=data.get("prompt_count", 0),
                )
            except Exception:
                pass
        config = TelemetryConfig()
        self._save_config(config)
        return config

    def _save_config(self, config: TelemetryConfig = None):
        config = config or self._config
        self._config_path.write_text(json.dumps(config.to_dict(), indent=2))

    @property
    def consent(self) -> TelemetryConsent:
        return self._config.consent

    @consent.setter
    def consent(self, level: TelemetryConsent):
        self._config.consent = level
        if level != TelemetryConsent.NONE:
            self._config.last_prompt = time.time()
            self._config.prompt_count += 1
        self._save_config()

    @property
    def can_collect(self) -> bool:
        return self._config.consent != TelemetryConsent.NONE

    def record(self, event_type: str, properties: dict = None, tags: list = None):
        if not self.can_collect:
            return
        now = time.time()
        if now - self._rate_limit_reset > self._rate_limit_window:
            self._rate_limit_count = 0
            self._rate_limit_reset = now
        if self._rate_limit_count > 100:
            return
        self._rate_limit_count += 1

        event = {
            "event_type": event_type,
            "timestamp": now,
            "properties": self._sanitize(properties or {}),
            "tags": tags or [],
        }
        if self._config.consent in (TelemetryConsent.ANONYMIZED, TelemetryConsent.FULL):
            event["user_id"] = self._config.user_id
            event["install_id"] = self._config.install_id
        self._event_queue.append(event)
        self._events.append(event)
        if len(self._event_queue) >= self._flush_threshold:
            self._flush()

    def _sanitize(self, properties: dict) -> dict:
        sensitive_keys = {"password", "secret", "token", "key", "api_key", "auth", "credential"}
        sanitized = {}
        for k, v in properties.items():
            if any(s in k.lower() for s in sensitive_keys):
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, str) and len(v) > 500:
                sanitized[k] = v[:500] + "..."
            else:
                sanitized[k] = v
        return sanitized

    def _flush(self):
        if not self._event_queue:
            return
        path = self._config_dir / f"events_{int(time.time())}.jsonl"
        try:
            with open(path, "a") as f:
                for event in self._event_queue:
                    f.write(json.dumps(event) + "\n")
            self._event_queue.clear()
        except Exception:
            pass

    def flush(self):
        self._flush()

    def get_consent_status(self) -> dict:
        return {
            "consent": self._config.consent.value,
            "can_collect": self.can_collect,
            "events_collected": len(self._events),
            "install_id": self._config.install_id[:8] + "...",
            "first_run": self._config.first_run,
            "prompt_count": self._config.prompt_count,
        }

    def prompt_for_consent(self) -> TelemetryConsent:
        self._config.prompt_count += 1
        self._save_config()
        return self._config.consent

    def get_install_id(self) -> str:
        return self._config.install_id


telemetry_manager = TelemetryManager()
