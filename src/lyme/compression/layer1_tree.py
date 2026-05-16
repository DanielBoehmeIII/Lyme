from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

LANGUAGE_MAP: Dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".jsx": "JavaScript (React)",
    ".java": "Java",
    ".kt": "Kotlin",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".swift": "Swift",
    ".scala": "Scala",
    ".r": "R",
    ".m": "Objective-C",
    ".mm": "Objective-C++",
    ".ex": "Elixir",
    ".exs": "Elixir Script",
    ".clj": "Clojure",
    ".cljs": "ClojureScript",
    ".hs": "Haskell",
    ".lua": "Lua",
    ".sh": "Shell",
    ".bash": "Bash",
    ".zsh": "Zsh",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".toml": "TOML",
    ".ini": "INI",
    ".cfg": "Config",
    ".md": "Markdown",
    ".rst": "reStructuredText",
    ".sql": "SQL",
    ".graphql": "GraphQL",
    ".proto": "Protobuf",
    ".css": "CSS",
    ".scss": "SCSS",
    ".less": "Less",
    ".html": "HTML",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".dart": "Dart",
}

FRAMEWORK_PATTERNS: List[Dict[str, Any]] = [
    {"name": "Django", "files": ["manage.py", "django"]},
    {"name": "Flask", "files": ["flask"]},
    {"name": "FastAPI", "files": ["fastapi"]},
    {"name": "React", "files": [".jsx", ".tsx", "react"]},
    {"name": "Next.js", "files": ["next.config"]},
    {"name": "Vue", "files": [".vue", "vue.config"]},
    {"name": "Spring", "files": ["pom.xml", "build.gradle", "spring"]},
    {"name": "Django REST", "files": ["rest_framework", "drf"]},
    {"name": "PyTorch", "files": ["torch"]},
    {"name": "TensorFlow", "files": ["tensorflow"]},
    {"name": "Rails", "files": ["Gemfile", "rails"]},
    {"name": "Express", "files": ["express"]},
    {"name": "NestJS", "files": ["nest"]},
    {"name": "SvelteKit", "files": ["svelte.config"]},
    {"name": "Svelte", "files": [".svelte"]},
    {"name": "Node.js", "files": ["package.json"]},
]

IGNORE_DIRS: Set[str] = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", "env",
    ".tox", ".eggs", "eggs", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".hypothesis", ".coverage", "htmlcov",
    "dist", "build", ".next", ".nuxt", "target", "bin", "obj",
    ".idea", ".vscode", ".sass-cache", ".parcel-cache",
    ".yarn", ".pnpm-store", "bower_components", "vendor",
}

IGNORE_FILES: Set[str] = {
    ".DS_Store", "Thumbs.db", ".gitkeep",
}


class FileTreeLayer:
    def __init__(self, ignore_dirs: Optional[Set[str]] = None):
        self.ignore_dirs = ignore_dirs or IGNORE_DIRS

    def extract(self, repo_path: Path, **kwargs) -> Dict[str, Any]:
        repo_path = Path(repo_path).resolve()
        if not repo_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {repo_path}")

        tree = self._build_tree(repo_path)
        languages = self._detect_languages(repo_path)
        frameworks = self._detect_frameworks(repo_path)
        entry_points = self._find_entry_points(repo_path)
        package_structure = self._get_package_structure(repo_path)

        return {
            "repo_name": repo_path.name,
            "repo_path": str(repo_path),
            "file_tree": tree,
            "languages": languages,
            "frameworks": frameworks,
            "entry_points": entry_points,
            "package_structure": package_structure,
            "total_files": sum(1 for _ in repo_path.rglob("*") if _.is_file()
                               and not any(p in _.parts for p in self.ignore_dirs)),
        }

    def _build_tree(self, path: Path, max_depth: int = 6) -> List[Dict[str, Any]]:
        if max_depth <= 0:
            return []
        if path.name in self.ignore_dirs:
            return []

        entries: List[Dict[str, Any]] = []
        try:
            for child in sorted(path.iterdir()):
                if child.name in self.ignore_dirs or child.name in IGNORE_FILES:
                    continue
                if child.is_dir():
                    subtree = self._build_tree(child, max_depth - 1)
                    entries.append({
                        "name": child.name,
                        "type": "directory",
                        "children": subtree,
                    })
                elif child.is_file():
                    lang = LANGUAGE_MAP.get(child.suffix.lower(), "Unknown")
                    entries.append({
                        "name": child.name,
                        "type": "file",
                        "extension": child.suffix,
                        "language": lang,
                        "size_bytes": child.stat().st_size,
                    })
        except PermissionError:
            pass
        return entries

    def _detect_languages(self, path: Path) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for f in path.rglob("*"):
            if f.is_file() and not any(p in f.parts for p in self.ignore_dirs):
                lang = LANGUAGE_MAP.get(f.suffix.lower(), "Unknown")
                counts[lang] = counts.get(lang, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))

    def _detect_frameworks(self, path: Path) -> List[str]:
        detected: List[str] = []
        for fw in FRAMEWORK_PATTERNS:
            markers = [m for m in fw["files"] if not m.startswith(".")]
            ext_markers = [m for m in fw["files"] if m.startswith(".")]
            if ext_markers:
                for f in path.rglob("*"):
                    if f.is_file() and f.suffix.lower() in ext_markers:
                        detected.append(fw["name"])
                        break
            if fw["name"] not in detected:
                for marker in markers:
                    for f in path.rglob(f"*{marker}*"):
                        if f.is_file() and not any(p in f.parts for p in self.ignore_dirs):
                            detected.append(fw["name"])
                            break
                    if fw["name"] in detected:
                        break
        return detected

    def _find_entry_points(self, path: Path) -> List[Dict[str, str]]:
        entry_points: List[Dict[str, str]] = []
        candidates = [
            "main.py", "app.py", "manage.py", "index.py",
            "cli.py", "server.py", "wsgi.py", "asgi.py",
            "main.ts", "index.ts", "index.js", "main.jsx", "main.tsx",
            "main.go", "main.rs", "Main.java", "App.kt",
        ]
        for candidate in candidates:
            fp = path / candidate
            if fp.is_file():
                entry_points.append({
                    "path": str(fp.relative_to(path)),
                    "type": "primary",
                    "language": LANGUAGE_MAP.get(fp.suffix.lower(), "Unknown"),
                })
        for f in path.iterdir():
            if f.is_file() and f.suffix == ".py" and f.name not in candidates:
                content = f.read_text(encoding="utf-8", errors="ignore")
                if "__main__" in content or "if __name__" in content:
                    entry_points.append({
                        "path": str(f.relative_to(path)),
                        "type": "script_entry",
                        "language": "Python",
                    })
        if not entry_points:
            for f in path.rglob("package.json"):
                if not any(p in f.parts for p in self.ignore_dirs):
                    entry_points.append({
                        "path": str(f.relative_to(path)),
                        "type": "manifest",
                        "language": "JSON",
                    })
                    break
        return entry_points

    def _get_package_structure(self, path: Path) -> List[Dict[str, Any]]:
        packages: List[Dict[str, Any]] = []
        for child in path.iterdir():
            if child.is_dir() and child.name not in self.ignore_dirs:
                init = child / "__init__.py" if (child / "__init__.py").exists() else None
                submodules = [
                    f.name for f in child.iterdir()
                    if f.is_file() and f.suffix == ".py" and f.name != "__init__.py"
                ]
                packages.append({
                    "package": child.name,
                    "path": str(child.relative_to(path)),
                    "has_init": init is not None,
                    "submodules": submodules,
                })
        return packages

    def to_json(self, repo_path: Path, indent: int = 2) -> str:
        return json.dumps(self.extract(repo_path), indent=indent, default=str)
