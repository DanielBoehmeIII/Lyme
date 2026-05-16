import os
import yaml
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass
class AgentConfig:
    name: str
    command: str
    env: dict = field(default_factory=dict)
    timeout_s: int = 300
    max_tokens: int = 128000
    agent_type: str = "claude-code"

    @classmethod
    def claude_code(cls) -> "AgentConfig":
        return cls(name="claude-code", command="claude", agent_type="claude-code")

    @classmethod
    def opencode(cls) -> "AgentConfig":
        return cls(name="opencode", command="opencode", agent_type="opencode")

    @classmethod
    def codex(cls) -> "AgentConfig":
        return cls(name="codex", command="codex", agent_type="codex")

    @classmethod
    def ollama(cls, model: str = "codellama") -> "AgentConfig":
        return cls(name=f"ollama-{model}", command=f"ollama run {model}", agent_type="ollama")


@dataclass
class BenchmarkConfig:
    output_dir: str = "./lyme-output"
    replay_dir: str = "./lyme-replays"
    experiments_dir: str = "./lyme-experiments"
    max_parallel: int = 1
    fail_fast: bool = False
    capture_stdout: bool = True
    record_thoughts: bool = True
    record_diffs: bool = True
    record_tool_calls: bool = True
    timeline_enabled: bool = True


@dataclass
class StorageConfig:
    backend: str = "json"  # json, parquet, sqlite
    compress_traces: bool = True
    retention_days: int = 90
    max_trace_size_mb: int = 50


@dataclass
class Settings:
    benchmark: BenchmarkConfig = field(default_factory=BenchmarkConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    agents: list = field(default_factory=list)
    verbose: bool = False
    debug: bool = False


def load_config(path: Optional[str] = None) -> Settings:
    if path is None:
        path = os.environ.get("LYME_CONFIG", "lyme.yaml")
    p = Path(path)
    if not p.exists():
        return Settings(agents=[AgentConfig.claude_code(), AgentConfig.opencode()])
    with open(p) as f:
        data = yaml.safe_load(f) or {}
    agents = []
    for a in data.get("agents", []):
        agents.append(AgentConfig(**a))
    return Settings(
        benchmark=BenchmarkConfig(**(data.get("benchmark", {}))),
        storage=StorageConfig(**(data.get("storage", {}))),
        agents=agents or [AgentConfig.claude_code(), AgentConfig.opencode()],
        verbose=data.get("verbose", False),
        debug=data.get("debug", False),
    )
