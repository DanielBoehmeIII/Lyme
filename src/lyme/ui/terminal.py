"""Terminal UI — rich ANSI terminal output with themes, live diff, streaming, task trees."""
from __future__ import annotations
import difflib
import shutil
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Generator, List, Optional


class Theme(str, Enum):
    DARK = "dark"
    LIGHT = "light"
    MATRIX = "matrix"
    SOLARIZED = "solarized"


THEMES = {
    Theme.DARK: {
        "primary": "\033[38;5;39m",      # blue
        "success": "\033[38;5;106m",     # green
        "warning": "\033[38;5;214m",     # yellow
        "error": "\033[38;5;196m",       # red
        "info": "\033[38;5;44m",         # cyan
        "dim": "\033[38;5;245m",         # gray
        "bold": "\033[1m",
        "reset": "\033[0m",
        "bg_success": "\033[48;5;22m",
        "bg_error": "\033[48;5;52m",
        "bg_info": "\033[48;5;24m",
    },
    Theme.LIGHT: {
        "primary": "\033[38;5;27m",
        "success": "\033[38;5;28m",
        "warning": "\033[38;5;130m",
        "error": "\033[38;5;160m",
        "info": "\033[38;5;30m",
        "dim": "\033[38;5;102m",
        "bold": "\033[1m",
        "reset": "\033[0m",
        "bg_success": "\033[48;5;42m",
        "bg_error": "\033[48;5;124m",
        "bg_info": "\033[48;5;31m",
    },
    Theme.MATRIX: {
        "primary": "\033[38;5;46m",
        "success": "\033[38;5;46m",
        "warning": "\033[38;5;226m",
        "error": "\033[38;5;196m",
        "info": "\033[38;5;47m",
        "dim": "\033[38;5;236m",
        "bold": "\033[1m",
        "reset": "\033[0m",
        "bg_success": "\033[48;5;22m",
        "bg_error": "\033[48;5;52m",
        "bg_info": "\033[48;5;17m",
    },
    Theme.SOLARIZED: {
        "primary": "\033[38;5;33m",
        "success": "\033[38;5;71m",
        "warning": "\033[38;5;136m",
        "error": "\033[38;5;160m",
        "info": "\033[38;5;37m",
        "dim": "\033[38;5;242m",
        "bold": "\033[1m",
        "reset": "\033[0m",
        "bg_success": "\033[48;5;23m",
        "bg_error": "\033[48;5;52m",
        "bg_info": "\033[48;5;18m",
    },
}


class Spinner:
    def __init__(self, message: str = ""):
        self._chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._message = message
        self._running = False
        self._i = 0

    def start(self) -> None:
        self._running = True

    def spin(self) -> None:
        if not self._running:
            return
        char = self._chars[self._i % len(self._chars)]
        sys.stdout.write(f"\r{char} {self._message}")
        sys.stdout.flush()
        self._i += 1

    def stop(self, final: str = "") -> None:
        self._running = False
        sys.stdout.write("\r" + " " * (len(self._message) + 4) + "\r")
        if final:
            print(final)
        sys.stdout.flush()


@dataclass
class TaskTree:
    """Nested task tree with status indicators."""
    name: str
    status: str = "pending"  # pending, running, success, failed, skipped
    children: List[TaskTree] = field(default_factory=list)
    parent: Optional[TaskTree] = None

    def add_child(self, child: TaskTree) -> None:
        child.parent = self
        self.children.append(child)


class TerminalRenderer:
    def __init__(self, theme: Theme = Theme.DARK):
        self.theme = THEMES.get(theme, THEMES[Theme.DARK])
        self._width = shutil.get_terminal_size().columns

    def _c(self, key: str) -> str:
        return self.theme.get(key, "")

    def ok(self, msg: str) -> None:
        print(f"{self._c('success')}✓{self._c('reset')} {msg}")

    def info(self, msg: str) -> None:
        print(f"{self._c('info')}ℹ{self._c('reset')} {msg}")

    def warn(self, msg: str) -> None:
        print(f"{self._c('warning')}⚠{self._c('reset')} {msg}")

    def err(self, msg: str) -> None:
        print(f"{self._c('error')}✗{self._c('reset')} {msg}", file=sys.stderr)

    def header(self, text: str) -> None:
        pad = (self._width - len(text) - 2) // 2
        print()
        print(f"{self._c('bold')}{'─' * max(0, pad)}{self._c('reset')} {self._c('primary')}{text}{self._c('reset')} {self._c('bold')}{'─' * max(0, pad)}{self._c('reset')}")
        print()

    def section(self, text: str) -> None:
        print(f"\n{self._c('bold')}{self._c('primary')}── {text}{self._c('reset')}")

    def render_diff(self, file_path: str, old_content: str, new_content: str) -> str:
        diff = difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=file_path, tofile=file_path,
        )
        output = [f"{self._c('bold')}{file_path}{self._c('reset')}"]
        for line in diff:
            line = line.rstrip("\n")
            if line.startswith("+++") or line.startswith("---"):
                continue
            elif line.startswith("@@"):
                output.append(f"{self._c('info')}{line}{self._c('reset')}")
            elif line.startswith("+"):
                output.append(f"{self._c('success')}{line}{self._c('reset')}")
            elif line.startswith("-"):
                output.append(f"{self._c('error')}{line}{self._c('reset')}")
            else:
                output.append(self._c('dim') + line + self._c('reset'))
        return "\n".join(output)

    def render_task_tree(self, tree: TaskTree, indent: int = 0) -> str:
        prefix = "  " * indent
        status_icons = {
            "pending": f"{self._c('dim')}○{self._c('reset')}",
            "running": f"{self._c('info')}●{self._c('reset')}",
            "success": f"{self._c('success')}●{self._c('reset')}",
            "failed": f"{self._c('error')}●{self._c('reset')}",
            "skipped": f"{self._c('dim')}─{self._c('reset')}",
        }
        icon = status_icons.get(tree.status, status_icons["pending"])
        lines = [f"{prefix}{icon} {tree.name}"]

        for child in tree.children:
            lines.append(self.render_task_tree(child, indent + 1))

        return "\n".join(lines)

    def render_thought(self, thought: str, step: int = 0) -> str:
        word_wrap = self._width - 6
        words = thought.split()
        lines = []
        current = ""
        for word in words:
            if len(current) + len(word) + 1 > word_wrap:
                lines.append(current)
                current = word
            else:
                current = f"{current} {word}" if current else word
        if current:
            lines.append(current)

        output = [f"{self._c('dim')}[step {step}]{self._c('reset')}"]
        for line in lines:
            output.append(f"  {self._c('info')}│{self._c('reset')} {line}")
        return "\n".join(output)

    def render_metrics(self, metrics: Dict[str, Any]) -> str:
        lines = []
        for key, value in metrics.items():
            key_str = key.replace("_", " ").title()
            if isinstance(value, float):
                lines.append(f"  {self._c('dim')}{key_str}:{self._c('reset')} {value:.2f}")
            else:
                lines.append(f"  {self._c('dim')}{key_str}:{self._c('reset')} {value}")
        return "\n".join(lines)

    def render_status_bar(self, label: str, current: int, total: int, width: int = 30) -> str:
        filled = int((current / max(total, 1)) * width)
        bar = "█" * filled + "░" * (width - filled)
        pct = (current / max(total, 1)) * 100
        return f"{self._c('primary')}{label}:{self._c('reset')} [{self._c('success')}{bar}{self._c('reset')}] {pct:.0f}%"

    def streaming_thoughts(self, thoughts: Generator[str, None, None]) -> None:
        step = 0
        for thought in thoughts:
            print(self.render_thought(thought, step))
            step += 1
            time.sleep(0.05)

    def print_banner(self) -> None:
        V = __import__('lyme').__version__ if hasattr(__import__('lyme'), '__version__') else '0.8.0'
        print()
        print(f"{self._c('primary')}  _                      {self._c('success')}")
        print(f"{self._c('primary')} | |                    {self._c('success')}")
        print(f"{self._c('primary')} | |    _   _ _ __ ___  {self._c('info')}  ___  ___")
        print(f"{self._c('primary')} | |   | | | | '_ ` _ \\ {self._c('info')} / _ \\/ __|")
        print(f"{self._c('primary')} | |___| |_| | | | | | |{self._c('info')}|  __/\\__ \\")
        print(f"{self._c('primary')} |______\\__, |_| |_| |_|{self._c('info')} \\___||___/")
        print(f"{self._c('primary')}         __/ |          {self._c('reset')}")
        print(f"{self._c('primary')}        |___/           {self._c('reset')}")
        print(f"{self._c('dim')}local coding agent platform{self._c('reset')}")
        print(f"{self._c('dim')}v{V}{self._c('reset')}")
        print()
