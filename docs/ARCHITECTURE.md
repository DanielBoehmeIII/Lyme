# Lyme Architecture

**Version:** 1.0.0  
**Architecture:** 8-layer separation with shared event bus and plugin registry

## Overview

Lyme is a local-first coding agent platform organized into eight architecture layers. Each layer has a distinct responsibility, typed interfaces, and can be extended via plugins.

```
┌──────────────────────────────────────────────────────────┐
│                         UI LAYER                         │
│            Terminal UI · Dashboards · IDE Bridge         │
├──────────────────────────────────────────────────────────┤
│                   ORCHESTRATION LAYER                    │
│           Multi-agent · Task Routing · Lifecycle         │
├──────────────────────────────────────────────────────────┤
│                     PLANNING LAYER                       │
│         Multi-step Plans · Dependency Reasoning          │
├──────────────────────────────────────────────────────────┤
│                     EXECUTION LAYER                      │
│       Safe Diffs · Sandbox · Tool Use · CI Integration   │
├──────────────────────────────────────────────────────────┤
│                    VALIDATION LAYER                      │
│       Test Intelligence · Diff Validation · Rollback     │
├──────────────────────────────────────────────────────────┤
│                   INFERENCE LAYER                        │
│      Local Models · Streaming · Batching · Spec Decode   │
├──────────────────────────────────────────────────────────┤
│                  REPO MEMORY LAYER                       │
│     AST Parsing · Dep Graphs · Semantic Indexing         │
├──────────────────────────────────────────────────────────┤
│                    TRAINING LAYER                        │
│      Fine-tuning · Datasets · Synthetic Data             │
└──────────────────────────────────────────────────────────┘
```

## Layer Map

| Layer | Module | Status | Description |
|-------|--------|--------|-------------|
| Orchestration | `src/lyme/core/` | Active | Agent orchestration, task routing, lifecycle management |
| Inference | `src/lyme/models/` | Active | Local model runtime, streaming, batching |
| Planning | `src/lyme/planning/` | Active | Multi-step planning, dependency reasoning |
| Repo Memory | `src/lyme/memory/` | Active | Repository understanding, semantic indexing |
| Validation | `src/lyme/verification/` | Active | Test intelligence, hallucination detection |
| Execution | `src/lyme/runtime/` | Active | Safe diff application, sandboxed execution |
| Training | `src/lyme/training/` | Experimental | Fine-tuning, dataset pipelines |
| UI | `src/lyme/ui/` | Active | Terminal UI, visualizations |

## Core Interfaces

Every Lyme component follows these protocols (defined in `src/lyme/core/interfaces.py`):

- **LymeComponent**: `name`, `version`, `status`, `initialize()`, `shutdown()`
- **Configurable**: `load_config(path)`, `get_config()`
- **Runnable**: `run(task: Task) -> TaskResult`
- **Stoppable**: `stop()`, `is_running()`
- **HasMetrics**: `get_metrics() -> Dict[str, float]`
- **HasStatus**: `get_status() -> ComponentStatus`

## Plugin System

Lyme uses a `PluginRegistry` (in `src/lyme/core/plugin.py`) for extensibility.

### Plugin Discovery

Plugins are auto-discovered at startup via:
1. **Entry points**: Python packages named `lyme_plugin_*`
2. **Directory scan**: Modules in plugin directories
3. **Manual registration**: `PluginRegistry.register(name, factory)`

### Writing a Plugin

```python
from lyme.core import Plugin, PluginSpec, PluginRegistry

spec = PluginSpec(
    name="my-plugin",
    version="0.1.0",
    description="My custom plugin",
    entry_point="my_plugin",
    layer="execution",
)

class MyPlugin(Plugin):
    def __init__(self):
        super().__init__(spec)
    
    def activate(self):
        print(f"{self.spec.name} activated")

PluginRegistry.register("my-plugin", lambda: MyPlugin())
```

## Event Bus

Cross-layer communication uses `EventBus` (in `src/lyme/core/events.py`):

```python
from lyme.core import EventBus, SystemEventType

# Subscribe
EventBus.subscribe(SystemEventType.TASK_COMPLETED, my_handler)

# Publish
EventBus.publish_simple(SystemEventType.INFO, {"message": "Hello"})
```

## CLI Commands

| Command | Handler | Description |
|---------|---------|-------------|
| `lyme init` | `_do_init` | Initialize Lyme on a repo |
| `lyme doctor` | `_do_doctor` | Diagnose repository health |
| `lyme run` | `_do_run` | Run benchmarks |
| `lyme plugin` | `_do_plugin` | Plugin management |
| `lyme model` | `_do_model` | Model management |
| `lyme ask` | `_do_ask` | Query repo understanding |

Full command list: `lyme --help`

## Directory Structure

```
src/lyme/
├── __init__.py          # Package root, version 0.8.0
├── cli.py               # Main CLI (4960+ lines, all commands)
├── cli_v0.py            # Legacy CLI (v0 commands)
├── doctor.py            # Repo diagnosis engine
├── ask.py               # Evidence-grounded Q&A
├── logging.py           # Structured logging
├── core/                # Orchestration layer
│   ├── __init__.py
│   ├── interfaces.py    # Component protocols
│   ├── layer.py         # Architecture layer definitions
│   ├── plugin.py        # Plugin registry & discovery
│   └── events.py        # Event bus
├── agents/              # Agent implementations
│   ├── __init__.py
│   ├── base.py          # Base agent protocol
│   └── orchestrator.py  # Multi-agent orchestration
├── evals/               # Evaluation harness
│   ├── __init__.py
│   ├── registry.py      # Eval task/suite registry
│   └── metrics.py       # Standard metrics
├── training/            # Training infrastructure
│   ├── __init__.py
│   ├── pipeline.py      # Dataset pipeline
│   └── config.py        # Training config
├── models/              # Model profiles & adapters
├── memory/              # Repo memory & distillation
├── planning/            # Architecture-aware planning
├── runtime/             # Agent runtime & orchestration
├── verification/        # Verification graph & checks
├── evaluation/          # Self-benchmark & regression
├── ui/                  # HTML renderers & dashboards
├── tools/               # Tool definitions
├── graph/               # Causal graph analysis
├── discovery/           # Invariant discovery
├── ... (60+ packages)   # Research modules
```

## Module Dependency Graph

```
core (no deps)
├── agents → core
├── planning → inference, repo_memory
├── execution → planning
├── validation → execution
├── inference (no deps)
├── repo_memory (no deps)
├── training → inference, repo_memory
└── ui (no deps)
```

## Configuration

Lyme uses typed dataclass configs:

```python
@dataclass
class Settings:
    benchmark: BenchmarkConfig
    storage: StorageConfig
    agents: List[AgentConfig]
    verbose: bool
    debug: bool
```

Config files are loaded from `lyme.yaml` or `$LYME_CONFIG`.

## Developer Quick Start

```bash
# Install
pip install -e .

# Initialize
lyme init .

# Diagnose
lyme doctor

# Run benchmarks
lyme run --all

# List plugins
lyme plugin list

# Check version
lyme --version
```
