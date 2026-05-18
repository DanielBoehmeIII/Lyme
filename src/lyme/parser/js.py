"""JSParser — regex-based parser for JavaScript and TypeScript."""
from __future__ import annotations
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .symbols import FileIndex, Symbol, SymbolKind, SymbolLocation


class JSParser:
    LANGUAGE = "javascript"

    _CLASS_PATTERN = re.compile(
        r'(?:export\s+)?(?:default\s+)?class\s+(\w+)'
    )
    _FUNCTION_PATTERN = re.compile(
        r'(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)'
    )
    _ARROW_FN_PATTERN = re.compile(
        r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(?.*?\)?\s*=>'
    )
    _IMPORT_PATTERN = re.compile(
        r'(?:import\s+(?:\{[^}]*\}\s*from\s+)?["\']([^"\']+)["\']|require\(["\']([^"\']+)["\']\))'
    )
    _EXPORT_PATTERN = re.compile(
        r'export\s+(?:default\s+)?(?:function|class|const|let|var)\s+(\w+)'
    )
    _INTERFACE_PATTERN = re.compile(
        r'(?:export\s+)?interface\s+(\w+)'
    )
    _TYPE_PATTERN = re.compile(
        r'(?:export\s+)?type\s+(\w+)\s*='
    )

    def parse_file(self, file_path: str) -> Optional[FileIndex]:
        path = Path(file_path)
        if not path.exists() or path.suffix not in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"):
            return None

        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

        lines = source.splitlines()
        file_hash = hashlib.sha256(source.encode()).hexdigest()

        index = FileIndex(
            file_path=str(path),
            language=self._detect_lang(path.suffix),
            lines=len(lines),
            hash=file_hash,
        )

        symbols: List[Symbol] = []
        imports: List[str] = []
        exports: List[str] = []

        for lineno, line in enumerate(lines, 1):
            # Classes
            m = self._CLASS_PATTERN.search(line)
            if m:
                symbols.append(Symbol(
                    name=m.group(1),
                    kind=SymbolKind.CLASS,
                    location=SymbolLocation(file_path=file_path, line=lineno),
                    is_public=True,
                ))

            # Functions
            m = self._FUNCTION_PATTERN.search(line)
            if m:
                symbols.append(Symbol(
                    name=m.group(1),
                    kind=SymbolKind.FUNCTION,
                    location=SymbolLocation(file_path=file_path, line=lineno),
                    is_public=not m.group(1).startswith("_"),
                ))

            # Arrow functions
            m = self._ARROW_FN_PATTERN.search(line)
            if m:
                symbols.append(Symbol(
                    name=m.group(1),
                    kind=SymbolKind.FUNCTION,
                    location=SymbolLocation(file_path=file_path, line=lineno),
                    is_public=not m.group(1).startswith("_"),
                ))

            # Interfaces (TypeScript)
            m = self._INTERFACE_PATTERN.search(line)
            if m:
                symbols.append(Symbol(
                    name=m.group(1),
                    kind=SymbolKind.INTERFACE,
                    location=SymbolLocation(file_path=file_path, line=lineno),
                    is_public=True,
                ))

            # Type aliases (TypeScript)
            m = self._TYPE_PATTERN.search(line)
            if m:
                symbols.append(Symbol(
                    name=m.group(1),
                    kind=SymbolKind.TYPE_ALIAS,
                    location=SymbolLocation(file_path=file_path, line=lineno),
                    is_public=True,
                ))

            # Imports
            for m in self._IMPORT_PATTERN.finditer(line):
                module = m.group(1) or m.group(2)
                if module:
                    imports.append(module)

            # Exports
            m = self._EXPORT_PATTERN.search(line)
            if m:
                exports.append(m.group(1))

        index.symbols = symbols
        index.imports = imports
        index.exports = exports
        index.complexity = min(1.0, (len(imports) * 0.02 + len(symbols) * 0.05 + index.lines * 0.001))

        return index

    def _detect_lang(self, suffix: str) -> str:
        if suffix in (".ts", ".tsx"):
            return "typescript"
        return "javascript"
