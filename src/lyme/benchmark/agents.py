"""Pre-configured agent entries for external coding agents."""
from __future__ import annotations
from ..config import AgentConfig


def claude_code() -> AgentConfig:
    return AgentConfig(
        name="claude-code",
        command="claude",
        agent_type="claude-code",
        timeout_s=600,
        env={"CLAUDE_CODE_OPTS": "--print"},
    )


def codex() -> AgentConfig:
    return AgentConfig(
        name="codex",
        command="codex",
        agent_type="codex",
        timeout_s=600,
    )


def opencode() -> AgentConfig:
    return AgentConfig(
        name="opencode",
        command="opencode",
        agent_type="opencode",
        timeout_s=600,
        env={"OPENCODE_OPTS": "--no-color"},
    )


def aider() -> AgentConfig:
    return AgentConfig(
        name="aider",
        command="aider",
        agent_type="aider",
        timeout_s=600,
        env={"AIDER_NO_GIT": "1", "AIDER_NO_BROWSER": "1"},
    )


def lyme() -> AgentConfig:
    return AgentConfig(
        name="lyme",
        command="lyme",
        agent_type="lyme",
        timeout_s=600,
    )


def ollama(model: str = "qwen2.5-coder:7b") -> AgentConfig:
    return AgentConfig(
        name=f"ollama-{model}",
        command=f"ollama run {model}",
        agent_type="ollama",
        timeout_s=300,
    )


AGENT_REGISTRY = {
    "claude-code": claude_code,
    "codex": codex,
    "opencode": opencode,
    "aider": aider,
    "lyme": lyme,
}

SUPPORTED_AGENTS = sorted(AGENT_REGISTRY.keys())


def get_agent(name: str) -> AgentConfig:
    factory = AGENT_REGISTRY.get(name)
    if factory:
        return factory()
    raise KeyError(f"Unknown agent: {name}. Available: {', '.join(SUPPORTED_AGENTS)}")
