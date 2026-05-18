from __future__ import annotations
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

from .inference import IntentInferrer, InferredIntent


class NaturalLanguageExecutor:
    def __init__(self):
        self.inferrer = IntentInferrer()
        self._history: List[Dict[str, Any]] = []

    def execute(self, input_text: str) -> Dict[str, Any]:
        intent = self.inferrer.infer(input_text)

        result = {
            "input": input_text,
            "intent": intent.to_dict(),
            "executed": False,
            "output": "",
            "error": None,
        }

        if intent.confidence >= 0.4:
            try:
                cmd_parts = intent.command.split()
                output = subprocess.run(
                    [sys.executable, "-m"] + cmd_parts,
                    capture_output=True, text=True, timeout=60,
                )
                result["executed"] = True
                result["output"] = (output.stdout + output.stderr)[:2000]
                if output.returncode != 0:
                    result["error"] = f"Exit code: {output.returncode}"
            except subprocess.TimeoutExpired:
                result["error"] = "Command timed out"
            except Exception as e:
                result["error"] = str(e)
        else:
            result["error"] = "Confidence too low to auto-execute"

        self._history.append(result)
        return result

    def suggest_execution(self, input_text: str) -> InferredIntent:
        return self.inferrer.infer(input_text)

    def print_suggestion(self, intent: InferredIntent) -> None:
        bar = "█" * int(intent.confidence * 10) + "▒" * (10 - int(intent.confidence * 10))
        print(f"\n  Intent: {intent.command}")
        print(f"  Confidence: {bar} {intent.confidence:.0%}")
        print(f"  {intent.explanation}")
        if intent.confidence >= 0.7:
            print(f"  → Auto-executing...")

    def recent_executions(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self._history[-limit:]
