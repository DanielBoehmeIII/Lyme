"""ModelServer — persistent model serving endpoint."""
from __future__ import annotations
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class ServerStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    ERROR = "error"


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 0
    model_name: str = ""
    backend: str = "auto"
    max_concurrent: int = 1
    timeout_s: int = 300
    keep_alive_s: int = 300
    log_file: Optional[str] = None


@dataclass
class ServerEndpoint:
    url: str = ""
    protocol: str = "unix_socket"
    pid: int = 0
    started_at: float = 0.0
    request_count: int = 0
    error_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "protocol": self.protocol,
            "pid": self.pid,
            "uptime_seconds": int(time.time() - self.started_at) if self.started_at else 0,
            "request_count": self.request_count,
            "error_count": self.error_count,
        }


class ModelServer:
    def __init__(self, config: ServerConfig):
        self.config = config
        self.status = ServerStatus.STOPPED
        self.endpoint = ServerEndpoint()
        self._logger = logging.getLogger("lyme.models.serve")
        self._handler: Optional[Callable] = None

    def set_handler(self, handler: Callable) -> None:
        self._handler = handler

    def start(self) -> bool:
        self.status = ServerStatus.STARTING
        try:
            self.endpoint.started_at = time.time()
            self.status = ServerStatus.RUNNING
            self._logger.info(f"Server started: {self.config.model_name} via {self.config.backend}")
            return True
        except Exception as e:
            self.status = ServerStatus.ERROR
            self._logger.error(f"Server failed to start: {e}")
            return False

    def stop(self) -> None:
        self.status = ServerStatus.STOPPED
        self._logger.info("Server stopped")

    def handle_request(self, prompt: str, **kwargs) -> Dict[str, Any]:
        self.endpoint.request_count += 1
        if self._handler:
            try:
                result = self._handler(prompt, **kwargs)
                return {"success": True, "text": result}
            except Exception as e:
                self.endpoint.error_count += 1
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "No handler configured"}

    def is_running(self) -> bool:
        return self.status == ServerStatus.RUNNING

    def get_info(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "config": {
                "model": self.config.model_name,
                "backend": self.config.backend,
                "host": self.config.host,
                "port": self.config.port,
            },
            "endpoint": self.endpoint.to_dict(),
        }
