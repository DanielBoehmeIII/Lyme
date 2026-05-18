"""TestGenerator — basic test generation from function signatures."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class GeneratedTest:
    file_path: str
    test_code: str = ""
    test_name: str = ""
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "test_name": self.test_name,
            "confidence": round(self.confidence, 4),
        }


class TestGenerator:
    def __init__(self, model_fn=None):
        self._model_fn = model_fn

    def generate_for_file(self, file_path: str) -> List[GeneratedTest]:
        path = Path(file_path)
        if not path.exists():
            return []

        try:
            content = path.read_text(errors="replace")
        except Exception:
            return []

        tests: List[GeneratedTest] = []
        lines = content.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("def ") and not stripped.startswith("def test_"):
                func_name = stripped.split("(")[0].replace("def ", "").strip()
                test_name = f"test_{func_name}"
                test_code = self._make_test(func_name, file_path)
                tests.append(GeneratedTest(
                    file_path=file_path,
                    test_code=test_code,
                    test_name=test_name,
                    confidence=0.3,
                ))

            elif stripped.startswith("class "):
                class_name = stripped.split("(")[0].replace("class ", "").strip()
                if not class_name.startswith("Test"):
                    test_name = f"Test{class_name}"
                    test_code = self._make_class_test(class_name, file_path)
                    tests.append(GeneratedTest(
                        file_path=file_path,
                        test_code=test_code,
                        test_name=f"test_{class_name.lower()}",
                        confidence=0.2,
                    ))

        return tests[:10]

    def _make_test(self, func_name: str, file_path: str) -> str:
        return f"""def test_{func_name}():
    # TODO: auto-generated test for {func_name}
    result = {func_name}()
    assert result is not None
"""

    def _make_class_test(self, class_name: str, file_path: str) -> str:
        return f"""class Test{class_name}:
    def test_init(self):
        # TODO: auto-generated test
        pass
"""
