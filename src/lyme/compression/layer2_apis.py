from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class APILayer:
    def __init__(self, max_files: int = 500):
        self.max_files = max_files

    def extract(self, repo_path: Path, **kwargs) -> Dict[str, Any]:
        repo_path = Path(repo_path).resolve()
        modules: List[Dict[str, Any]] = []
        file_count = 0

        for f in repo_path.rglob("*"):
            if not f.is_file():
                continue
            if any(p.startswith(".") or p == "__pycache__" or p == "node_modules"
                   for p in f.parts):
                continue
            if f.suffix not in (".py", ".js", ".ts", ".tsx", ".jsx"):
                continue
            if file_count >= self.max_files:
                break

            try:
                module_info = self._parse_file(f, repo_path)
                if module_info:
                    modules.append(module_info)
                    file_count += 1
            except Exception:
                pass

        return {
            "modules": modules,
            "total_modules": len(modules),
        }

    def _parse_file(self, filepath: Path, repo_root: Path) -> Optional[Dict[str, Any]]:
        text = filepath.read_text(encoding="utf-8", errors="replace")
        relative = str(filepath.relative_to(repo_root))

        if filepath.suffix == ".py":
            return self._parse_python(text, relative, filepath)
        else:
            return self._parse_js_ts(text, relative, filepath.suffix)

    def _parse_python(self, text: str, relative: str, filepath: Path) -> Dict[str, Any]:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return self._fallback_python(text, relative)

        classes: List[Dict[str, Any]] = []
        functions: List[Dict[str, Any]] = []
        imports: List[Dict[str, Any]] = []
        public_exports: List[str] = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "module": alias.name,
                        "alias": alias.asname,
                        "type": "import",
                    })
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [{"name": n.name, "alias": n.asname} for n in node.names]
                imports.append({
                    "module": module,
                    "names": names,
                    "type": "import_from",
                    "level": node.level,
                })
                for n in node.names:
                    if not n.name.startswith("_"):
                        public_exports.append(n.name)

            elif isinstance(node, ast.ClassDef):
                methods = []
                bases = [self._ast_name(b) for b in node.bases]
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) or isinstance(item, ast.AsyncFunctionDef):
                        args = self._get_args(item)
                        methods.append({
                            "name": item.name,
                            "args": args,
                            "decorators": [self._ast_name(d) for d in item.decorator_list],
                            "is_async": isinstance(item, ast.AsyncFunctionDef),
                        })
                    elif isinstance(item, (ast.Assign, ast.AnnAssign)):
                        if isinstance(item, ast.Assign):
                            for t in item.targets:
                                if isinstance(t, ast.Name):
                                    methods.append({
                                        "name": t.id,
                                        "value": "...",
                                        "is_class_var": True,
                                    })
                        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                            methods.append({
                                "name": item.target.id,
                                "annotation": self._ast_name(item.annotation) if item.annotation else None,
                                "is_class_var": True,
                            })
                classes.append({
                    "name": node.name,
                    "bases": bases,
                    "decorators": [self._ast_name(d) for d in node.decorator_list],
                    "methods": methods,
                    "line": node.lineno,
                })

            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                if node.col_offset == 0:
                    args = self._get_args(node)
                    functions.append({
                        "name": node.name,
                        "args": args,
                        "decorators": [self._ast_name(d) for d in node.decorator_list],
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "line": node.lineno,
                    })

        return {
            "file": relative,
            "language": "Python",
            "classes": classes,
            "functions": functions,
            "imports": imports,
            "public_exports": public_exports,
        }

    def _fallback_python(self, text: str, relative: str) -> Dict[str, Any]:
        classes = re.findall(r"^class\s+(\w+)\s*(?:\(|:)", text, re.MULTILINE)
        functions = re.findall(
            r"^(?:async\s+)?def\s+(\w+)\s*\(", text, re.MULTILINE
        )
        imports = re.findall(
            r"^(?:from\s+([\w.]+)\s+)?import\s+(.+)", text, re.MULTILINE
        )
        return {
            "file": relative,
            "language": "Python",
            "classes": [{"name": c, "line": 0} for c in classes],
            "functions": [{"name": f, "line": 0} for f in functions],
            "imports": [{"raw": i} for i in imports],
            "public_exports": [c for c in classes if not c.startswith("_")]
            + [f for f in functions if not f.startswith("_")],
            "parse_error": True,
        }

    def _parse_js_ts(self, text: str, relative: str, suffix: str) -> Dict[str, Any]:
        lang = "TypeScript" if suffix in (".ts", ".tsx") else "JavaScript"

        exports: List[str] = []
        classes: List[Dict[str, Any]] = []
        functions: List[Dict[str, Any]] = []
        imports: List[Dict[str, Any]] = []

        class_pattern = re.compile(
            r"(?:export\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?"
            r"(?:\s+implements\s+([\w,\s]+))?"
        )
        for m in class_pattern.finditer(text):
            classes.append({
                "name": m.group(1),
                "extends": m.group(2),
                "implements": m.group(3).split(",") if m.group(3) else [],
            })

        func_pattern = re.compile(
            r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\("
        )
        for m in func_pattern.finditer(text):
            functions.append({"name": m.group(1), "type": "function"})

        arrow_pattern = re.compile(
            r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*(?:=>|:)"
        )
        for m in arrow_pattern.finditer(text):
            functions.append({"name": m.group(1), "type": "arrow_function"})

        export_default = re.search(
            r"export\s+default\s+(?:function\s+(\w+)|class\s+(\w+)|(\w+))", text
        )
        if export_default:
            name = export_default.group(1) or export_default.group(2) or export_default.group(3) or "default"
            exports.append(f"default:{name}")

        export_named = re.findall(
            r"export\s+(?:const|let|var|function|class|interface|type)\s+(\w+)", text
        )
        exports.extend(export_named)

        import_pattern = re.compile(
            r"import\s+(?:\{([^}]+)\}|(\w+))\s*from\s+['\"]([^'\"]+)['\"]"
        )
        for m in import_pattern.finditer(text):
            names = [n.strip() for n in (m.group(1) or m.group(2)).split(",") if n.strip()]
            imports.append({
                "source": m.group(3),
                "names": names,
            })

        import_side_effect = re.findall(r"import\s+['\"]([^'\"]+)['\"]", text)
        for s in import_side_effect:
            imports.append({"source": s, "side_effect": True})

        return {
            "file": relative,
            "language": lang,
            "classes": classes,
            "functions": functions,
            "imports": imports,
            "public_exports": exports,
        }

    def _get_args(self, node: Any) -> List[Dict[str, Any]]:
        args: List[Dict[str, Any]] = []
        if not hasattr(node, "args"):
            return args
        for arg in node.args.args:
            arg_info: Dict[str, Any] = {"name": arg.arg}
            if arg.annotation:
                arg_info["annotation"] = self._ast_name(arg.annotation)
            args.append(arg_info)
        if node.args.vararg:
            args.append({"name": f"*{node.args.vararg.arg}", "vararg": True})
        if node.args.kwonlyargs:
            for arg in node.args.kwonlyargs:
                args.append({"name": arg.arg, "kwonly": True})
        if node.args.kwarg:
            args.append({"name": f"**{node.args.kwarg.arg}", "kwarg": True})
        return args

    def _ast_name(self, node: Any) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._ast_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            return f"{self._ast_name(node.value)}[{self._ast_name(node.slice)}]"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Index):
            return self._ast_name(node.value)
        elif isinstance(node, ast.Tuple):
            return ", ".join(self._ast_name(e) for e in node.elts)
        elif isinstance(node, ast.List):
            return f"[{', '.join(self._ast_name(e) for e in node.elts)}]"
        elif isinstance(node, ast.Call):
            return f"{self._ast_name(node.func)}(...)"
        elif node is None:
            return "None"
        return str(node)
