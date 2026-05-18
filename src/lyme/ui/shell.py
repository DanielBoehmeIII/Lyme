"""Interactive shell for Lyme with readline support."""
from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


try:
    import readline
    HAS_READLINE = True
except ImportError:
    HAS_READLINE = False


class InteractiveShell:
    def __init__(self, prompt: str = "lyme> "):
        self.prompt = prompt
        self.history_file = os.path.expanduser("~/.lyme_history")
        self._commands: Dict[str, str] = {}
        self._running = False

        if HAS_READLINE:
            self._setup_readline()

    def _setup_readline(self) -> None:
        try:
            readline.read_history_file(self.history_file)
        except (FileNotFoundError, PermissionError):
            pass
        readline.set_completer(self._complete)
        readline.parse_and_bind("tab: complete")

    def register(self, name: str, help_text: str) -> None:
        self._commands[name] = help_text

    def _complete(self, text: str, state: int) -> Optional[str]:
        matches = [c for c in self._commands if c.startswith(text)]
        try:
            return matches[state]
        except IndexError:
            return None

    def run(self, handler) -> None:
        self._running = True
        print("Lyme interactive shell. Type 'help' for commands, 'exit' to quit.")
        print()

        while self._running:
            try:
                line = input(self.prompt).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not line:
                continue

            if line == "exit" or line == "quit":
                break

            if line == "help":
                self._print_help()
                continue

            handler(line)

        if HAS_READLINE:
            try:
                readline.write_history_file(self.history_file)
            except (PermissionError, FileNotFoundError):
                pass

    def _print_help(self) -> None:
        print("Commands:")
        for name, help_text in sorted(self._commands.items()):
            print(f"  {name:20s} {help_text}")
        print()
