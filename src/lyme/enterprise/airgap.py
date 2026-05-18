"""AirgapMode — airgapped operation without external network access."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AirgapConfig:
    enabled: bool = False
    allow_localhost: bool = True
    blocked_hosts: List[str] = field(default_factory=lambda: [
        "api.openai.com", "api.anthropic.com", "registry.huggingface.co",
        "pypi.org", "pypi.python.org",
    ])
    allowed_hosts: List[str] = field(default_factory=list)


class AirgapMode:
    def __init__(self, config: AirgapConfig = None):
        self.config = config or AirgapConfig()

    def check_url(self, url: str) -> bool:
        if not self.config.enabled:
            return True
        from urllib.parse import urlparse
        host = urlparse(url).hostname or ""
        if host in self.config.allowed_hosts:
            return True
        if host == "localhost" or host == "127.0.0.1":
            return self.config.allow_localhost
        for blocked in self.config.blocked_hosts:
            if blocked in host:
                return False
        return True

    def verify_config(self) -> Dict[str, Any]:
        return {
            "airgap_enabled": self.config.enabled,
            "blocked_hosts": len(self.config.blocked_hosts),
            "allowed_hosts": len(self.config.allowed_hosts),
            "localhost_allowed": self.config.allow_localhost,
        }
