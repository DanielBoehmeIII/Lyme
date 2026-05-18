from __future__ import annotations
from pathlib import Path
from typing import Optional
import subprocess
import re


class LatestFailureFixer:
    """Fix latest test failure automatically."""

    def find_latest_failure(self, repo_path: str = ".") -> Optional[dict]:
        repo = Path(repo_path).resolve()
        try:
            result = subprocess.run(
                ["python3", "-m", "pytest", "--tb=short", "-x"],
                capture_output=True, text=True, timeout=60,
                cwd=str(repo),
            )
            output = result.stdout + result.stderr
            if result.returncode == 0:
                return None

            failures = []
            for line in output.split("\n"):
                if "FAILED" in line or "ERROR:" in line:
                    failures.append(line.strip())

            if not failures:
                return None

            first = failures[0]
            file_match = re.search(r'(test_[a-zA-Z0-9_/]+\.py)', first)
            test_match = re.search(r'::(\w+)', first)

            return {
                "failure_line": first,
                "file": file_match.group(1) if file_match else None,
                "test": test_match.group(1) if test_match else None,
                "output_snippet": output[-1000:],
            }

        except subprocess.TimeoutExpired:
            return {"error": "test timed out"}
        except Exception as e:
            return {"error": str(e)}

    def diagnose(self, failure: dict) -> str:
        if not failure:
            return "No failures detected"
        if "error" in failure:
            return f"Error: {failure['error']}"
        output = failure.get("output_snippet", "")
        if "AssertionError" in output:
            return "Assertion failure — expected value does not match actual"
        if "SyntaxError" in output or "IndentationError" in output:
            return "Syntax error — check file for missing parens, brackets, or indentation"
        if "ImportError" in output or "ModuleNotFoundError" in output:
            return "Import error — missing dependency or circular import"
        if "TypeError" in output:
            return "Type error — wrong argument type or count"
        if "KeyError" in output:
            return "Key error — missing dictionary key"
        if "AttributeError" in output:
            return "Attribute error — missing method or property"
        return "Unknown failure — check the test output"


fixer = LatestFailureFixer()
