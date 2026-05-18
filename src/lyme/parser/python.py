"""PythonParser — unified AST walker for Python source code."""
from __future__ import annotations
import ast
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .symbols import FileIndex, Symbol, SymbolKind, SymbolLocation


class PythonParser:
    LANGUAGE = "python"

    def parse_file(self, file_path: str) -> Optional[FileIndex]:
        path = Path(file_path)
        if not path.exists() or path.suffix not in (".py", ".pyi"):
            return None

        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=file_path)
        except SyntaxError:
            return None

        lines = source.splitlines()
        file_hash = hashlib.sha256(source.encode()).hexdigest()

        index = FileIndex(
            file_path=str(path),
            language=self.LANGUAGE,
            lines=len(lines),
            hash=file_hash,
        )

        imports: List[str] = []
        symbols: List[Symbol] = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
                    symbols.append(self._import_symbol(alias, file_path))

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    full_import = f"{module}.{alias.name}" if module else alias.name
                    imports.append(full_import)
                    symbols.append(self._import_from_symbol(alias, module, file_path, node.lineno or 0))

            elif isinstance(node, ast.ClassDef):
                symbols.extend(self._parse_class(node, file_path, lines))

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols.append(self._parse_function(node, file_path, None, lines))

        index.symbols = symbols
        index.imports = imports
        self._detect_test_file(index)
        self._compute_complexity(index)

        return index

    def _parse_class(self, node: ast.ClassDef, file_path: str,
                     lines: List[str]) -> List[Symbol]:
        symbols: List[Symbol] = []
        end_line = self._find_end_line(node, lines)

        loc = SymbolLocation(
            file_path=file_path, line=node.lineno or 0, end_line=end_line,
        )

        cls_sym = Symbol(
            name=node.name,
            kind=SymbolKind.CLASS,
            location=loc,
            docstring=ast.get_docstring(node) or "",
            decorators=[self._decorator_name(d) for d in node.decorator_list],
            is_public=not node.name.startswith("_"),
        )
        symbols.append(cls_sym)

        for item in ast.iter_child_nodes(node):
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_sym = self._parse_function(item, file_path, node.name, lines)
                symbols.append(method_sym)

            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        sym = Symbol(
                            name=target.id,
                            kind=SymbolKind.VARIABLE,
                            location=SymbolLocation(
                                file_path=file_path, line=item.lineno or 0,
                            ),
                            parent=node.name,
                            is_public=not target.id.startswith("_"),
                        )
                        symbols.append(sym)

        return symbols

    def _parse_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef,
                        file_path: str, parent: Optional[str],
                        lines: List[str]) -> Symbol:
        end_line = self._find_end_line(node, lines)
        params: List[str] = []
        for arg in node.args.args:
            params.append(arg.arg)

        returns = None
        if node.returns:
            try:
                returns = ast.dump(node.returns)[:100]
            except Exception:
                returns = None

        loc = SymbolLocation(
            file_path=file_path, line=node.lineno or 0, end_line=end_line,
        )

        is_test = node.name.startswith("test_") or node.name.endswith("_test")

        return Symbol(
            name=node.name,
            kind=SymbolKind.FUNCTION if parent is None else SymbolKind.METHOD,
            location=loc,
            parent=parent,
            docstring=ast.get_docstring(node) or "",
            decorators=[self._decorator_name(d) for d in node.decorator_list],
            params=params,
            returns=str(returns) if returns else None,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_public=not node.name.startswith("_"),
            is_test=is_test,
        )

    def _import_symbol(self, alias: ast.alias, file_path: str) -> Symbol:
        return Symbol(
            name=alias.name,
            kind=SymbolKind.IMPORT,
            location=SymbolLocation(file_path=file_path, line=0),
            is_public=True,
            metadata={"asname": alias.asname} if alias.asname else {},
        )

    def _import_from_symbol(self, alias: ast.alias, module: str,
                            file_path: str, lineno: int) -> Symbol:
        return Symbol(
            name=alias.name,
            kind=SymbolKind.IMPORT,
            location=SymbolLocation(file_path=file_path, line=lineno),
            is_public=True,
            parent=module,
            metadata={"asname": alias.asname} if alias.asname else {},
        )

    def _decorator_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._decorator_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._decorator_name(node.func)
        return ast.dump(node)[:50]

    def _find_end_line(self, node: ast.AST, lines: List[str]) -> int:
        try:
            end = node.end_lineno or node.lineno or 0
        except Exception:
            end = node.lineno or 0
        return end

    def _detect_test_file(self, index: FileIndex) -> None:
        name = Path(index.file_path).name
        if name.startswith("test_") or name.endswith("_test.py") or name.endswith("_test.go"):
            for sym in index.symbols:
                sym.is_test = True

    def _compute_complexity(self, index: FileIndex) -> None:
        if index.lines == 0:
            index.complexity = 0.0
            return
        imports = len(index.imports)
        symbols = len(index.symbols)
        index.complexity = min(1.0, (imports * 0.02 + symbols * 0.05 + index.lines * 0.001))
