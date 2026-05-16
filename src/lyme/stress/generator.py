import random
import string
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple


class SyntheticRepoGenerator:
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate(self, target_dir: Path, num_files: int = 10,
                 depth: int = 2, deps_per_file: int = 3,
                 has_tests: bool = True, has_docs: bool = True) -> dict:
        target_dir.mkdir(parents=True, exist_ok=True)

        files = []
        imports = []

        (target_dir / "src").mkdir(exist_ok=True)
        if has_tests:
            (target_dir / "tests").mkdir(exist_ok=True)
        if has_docs:
            (target_dir / "docs").mkdir(exist_ok=True)

        filenames = self._generate_filenames(num_files)
        module_names = [f[:-3] for f in filenames if f.endswith(".py")]

        for i, filename in enumerate(filenames):
            subdir = self._pick_subdir(depth)
            filepath = target_dir / subdir / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)

            deps = self.rng.sample(
                [m for m in module_names if m != filename[:-3]],
                min(deps_per_file, len(module_names) - 1)
            )

            content = self._generate_module_content(
                filename[:-3], deps, i, num_files
            )
            filepath.write_text(content)
            files.append(str(filepath.relative_to(target_dir)))
            imports.append({
                "file": filename,
                "imports": deps,
                "exports": self._extract_exports(content),
            })

        if has_tests:
            for i, filename in enumerate(filenames[:max(1, num_files // 2)]):
                test_path = target_dir / "tests" / f"test_{filename}"
                test_content = self._generate_test_content(filename[:-3])
                test_path.write_text(test_content)
                files.append(str(test_path.relative_to(target_dir)))

        if has_docs:
            doc_path = target_dir / "docs" / "architecture.md"
            doc_path.write_text(self._generate_doc(filenames, imports))
            files.append(str(doc_path.relative_to(target_dir)))

        return {
            "target_dir": str(target_dir),
            "file_count": len(files),
            "files": files,
            "imports": imports,
            "complexity": self._compute_complexity(num_files, depth, deps_per_file),
        }

    def _generate_filenames(self, count: int) -> List[str]:
        prefixes = [
            "auth", "config", "database", "engine", "factory",
            "handler", "injector", "loader", "manager", "parser",
            "provider", "registry", "service", "store", "utils",
            "validator", "worker", "adapter", "builder", "controller",
        ]
        return [f"{prefix}.py" for prefix in prefixes[:count]]

    def _pick_subdir(self, depth: int) -> str:
        if depth <= 1:
            return "src"
        subdirs = ["src/core", "src/models", "src/services",
                    "src/api", "src/utils", "src/handlers"]
        return self.rng.choice(subdirs[:depth])

    def _generate_module_content(self, name: str, deps: List[str],
                                  index: int, total: int) -> str:
        lines = []
        for dep in deps:
            lines.append(f"from {dep} import *")
        lines.append("")

        exports = self._generate_exports(name)
        for func_name, func_body in exports:
            lines.append(f"def {func_name}(data: dict = None) -> dict:")
            lines.append(f"    \"\"\"Process {name} request.\"\"\"")
            if deps:
                lines.append(f"    # Delegating to dependencies")
                for dep in deps[:2]:
                    lines.append(f"    result = {self.rng.choice(['process', 'handle', 'transform', 'validate'])}_data(data)")
                lines.append(f"    return {{'status': 'ok', 'handler': '{name}', 'result': result}}")
            else:
                lines.append(f"    return {{'status': 'ok', 'handler': '{name}'}}")
            lines.append("")

        return "\n".join(lines)

    def _generate_exports(self, name: str) -> List[Tuple[str, str]]:
        actions = ["process", "handle", "get", "create", "update", "delete",
                    "validate", "transform", "load", "save"]
        action = self.rng.choice(actions)
        return [
            (f"{action}_{name}", f"Process {name}"),
            (f"{self.rng.choice(['validate', 'check', 'verify'])}_{name}", f"Validate {name}"),
        ]

    def _extract_exports(self, content: str) -> List[str]:
        exports = []
        for line in content.split("\n"):
            if line.startswith("def "):
                exports.append(line[4:].split("(")[0])
        return exports

    def _generate_test_content(self, name: str) -> str:
        return (
            f"from src.{name} import *\n\n"
            f"def test_{name}_process():\n"
            f"    result = process_{name}({{'key': 'value'}})\n"
            f"    assert result['status'] == 'ok'\n\n"
            f"def test_{name}_validation():\n"
            f"    result = validate_{name}({{}})\n"
            f"    assert result is not None\n"
        )

    def _generate_doc(self, filenames: List[str],
                      imports: List[dict]) -> str:
        lines = ["# Architecture", "", "## Module Overview", ""]
        for f in filenames:
            lines.append(f"- **{f}**: Core {f[:-3]} module")
        lines.append("")
        lines.append("## Dependencies")
        lines.append("")
        for imp in imports:
            if imp["imports"]:
                lines.append(f"- {imp['file']} depends on: {', '.join(imp['imports'])}")
        lines.append("")
        lines.append("## API Surface")
        lines.append("")
        for imp in imports:
            exports = imp["exports"]
            if exports:
                lines.append(f"- {imp['file']} exports: {', '.join(exports)}")
        return "\n".join(lines)

    def _compute_complexity(self, num_files: int, depth: int,
                            deps_per_file: int) -> float:
        return (num_files * 0.3 + depth * 0.3 + deps_per_file * 0.4) / 10.0

    def add_hidden_coupling(self, target_dir: Path, source_file: str,
                            target_file: str, coupling_type: str = "data") -> str:
        src_path = target_dir / source_file
        if not src_path.exists():
            return ""

        content = src_path.read_text()
        if coupling_type == "data":
            content += f"\n\n# HIDDEN COUPLING: this constant must match {target_file}\n"
            content += f"_INTERNAL_SHARED_STATE = {{'sync_key': '{self.rng.randint(1000, 9999)}'}}\n"
        elif coupling_type == "import":
            content += f"\nfrom {target_file.replace('.py', '')} import _INTERNAL_CONSTANT\n"
        elif coupling_type == "format":
            content += f"\n# Format must match ordering in {target_file}\n"
            content += f"_FIELD_ORDER = ['id', 'name', 'type', 'value', 'status']\n"

        src_path.write_text(content)
        return content

    def add_fragile_test(self, target_dir: Path, test_name: str,
                         depends_on: str) -> str:
        test_path = target_dir / "tests" / test_name
        content = (
            f"from src.{depends_on.replace('.py', '')} import *\n\n"
            f"def test_fragile():\n"
            f"    # TODO: this test is fragile\n"
            f"    result = process_{depends_on.replace('.py', '')}({{}})\n"
            f"    assert result == {{'status': 'ok'}}  # May fail after refactors\n"
        )
        test_path.write_text(content)
        return content
