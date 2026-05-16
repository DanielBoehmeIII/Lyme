from __future__ import annotations

import ast
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .intent_model import (
    IntentModel, IntentType, DesignPhilosophy, Tradeoff,
    SubsystemIntent, IntentEvidence, IntentUncertainty,
    EvolutionDirection,
)


class SubsystemPurposeAnalyzer:
    def analyze(self, repo_path: Path, model: IntentModel) -> List[SubsystemIntent]:
        subsystem_intents: Dict[str, SubsystemIntent] = {}

        subsystems = self._discover_subsystems(repo_path)
        for sub_name, files in subsystems.items():
            purpose = self._infer_purpose(sub_name, files, repo_path)
            intent = SubsystemIntent(
                subsystem=sub_name,
                purpose=purpose,
                evidence=[
                    IntentEvidence(
                        source="directory_structure",
                        evidence_type="structural",
                        content=f"Subsystem '{sub_name}' contains {len(files)} files",
                        confidence=0.6,
                    )
                ],
            )
            subsystem_intents[sub_name] = intent

        return list(subsystem_intents.values())

    def _discover_subsystems(self, repo_path: Path) -> Dict[str, List[Path]]:
        subsystems: Dict[str, List[Path]] = defaultdict(list)
        for f in repo_path.rglob("*"):
            if not f.is_file():
                continue
            if any(p.startswith(".") or p == "__pycache__" or p == "node_modules" for p in f.parts):
                continue
            parts = f.relative_to(repo_path).parts
            if len(parts) >= 2:
                subsystems[parts[0]].append(f)
            else:
                subsystems["root"].append(f)
        return dict(subsystems)

    def _infer_purpose(self, name: str, files: List[Path], repo_path: Path) -> str:
        name_lower = name.lower()
        purpose_map = {
            "controller": "Handle HTTP requests and route them to appropriate services",
            "service": "Implement business logic and orchestrate operations",
            "model": "Define data structures and database schema",
            "repository": "Abstract data access and persistence operations",
            "dao": "Provide low-level database access operations",
            "middleware": "Process requests through middleware pipeline",
            "config": "Manage application configuration and environment settings",
            "util": "Provide shared utility functions and helpers",
            "helper": "Provide supporting functionality to other modules",
            "api": "Define external API interfaces and contracts",
            "route": "Define API route handlers and endpoint mappings",
            "view": "Render and present data to users",
            "template": "Store presentation templates and view layouts",
            "migration": "Manage database schema migrations",
            "test": "Contain automated tests for verification",
            "schema": "Define data validation schemas",
            "adapter": "Implement adapters for external systems",
            "handler": "Handle specific event types or requests",
            "provider": "Provide dependency injection or service provisioning",
            "factory": "Implement factory patterns for object creation",
            "strategy": "Implement strategy pattern variants",
            "observer": "Implement observer pattern for event handling",
            "decorator": "Implement decorator pattern for augmentation",
            "command": "Implement command pattern for operations",
        }

        for keyword, purpose in purpose_map.items():
            if keyword in name_lower:
                return purpose

        py_files = [f for f in files if f.suffix == ".py"]
        if not py_files:
            return "Resource or configuration directory"

        all_text = ""
        for f in py_files[:10]:
            try:
                all_text += f.read_text(encoding="utf-8", errors="replace") + "\n"
            except Exception:
                pass

        if "class " in all_text and "def " in all_text:
            return f"Contains {all_text.count('class ')} classes and {all_text.count('def ')} functions"
        elif "def " in all_text:
            return f"Contains {all_text.count('def ')} functions"
        else:
            return "Python module collection"


class DesignPhilosophyAnalyzer:
    def analyze(self, repo_path: Path, model: IntentModel) -> DesignPhilosophy:
        scores: Dict[DesignPhilosophy, float] = defaultdict(float)

        for f in repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            if re.search(r"from\s+typing\s+import", text):
                scores[DesignPhilosophy.DOMAIN_DRIVEN] += 0.5

            if re.search(r"abc\.\s*(ABC|abstractmethod)", text):
                scores[DesignPhilosophy.HEXAGONAL] += 1.0

            if re.search(r"@(route|app\.route|bp\.route)", text) and \
               re.search(r"from\s+flask", text):
                scores[DesignPhilosophy.API_FIRST] += 1.0

            if re.search(r"from\s+dataclasses\s+import|@dataclass", text) and \
               re.search(r"from\s+pathlib\s+import", text):
                scores[DesignPhilosophy.UTILITY] += 0.5

            deps = re.findall(r"^\s*(?:from\s+[\w.]+\s+)?import\s+", text, re.MULTILINE)
            if len(deps) > 15:
                scores[DesignPhilosophy.MONOLITHIC] += 0.3

        pattern_counts: Dict[str, int] = defaultdict(int)
        for f in repo_path.rglob("*.py"):
            if not f.is_file():
                continue
            try:
                tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            if base.id in ("ABC", "Protocol", "Interface"):
                                pattern_counts["interface"] += 1
                            elif base.id in ("Enum", "IntEnum"):
                                pattern_counts["enum"] += 1

        if pattern_counts.get("interface", 0) > 3:
            scores[DesignPhilosophy.HEXAGONAL] += 2.0

        if not scores:
            return DesignPhilosophy.UNKNOWN

        return max(scores, key=scores.get)


class TradeoffAnalyzer:
    def analyze(self, repo_path: Path, model: IntentModel) -> List[Tradeoff]:
        tradeoffs: List[Tradeoff] = []

        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "log", "--format=%s%n%b",
                 "--grep=refactor|migrate|rewrite|redesign|redesign|trade.?off|optimize", "-50"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                current_msg = []
                for line in result.stdout.splitlines():
                    if re.match(r"^[a-f0-9]{40}$", line):
                        if current_msg:
                            msg = " ".join(current_msg)
                            tradeoffs.append(self._extract_tradeoff(msg))
                            current_msg = []
                    else:
                        current_msg.append(line.strip())
                if current_msg:
                    msg = " ".join(current_msg)
                    tradeoffs.append(self._extract_tradeoff(msg))
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        for f in repo_path.rglob("*.md"):
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                lines = text.split("\n")
                for i, line in enumerate(lines):
                    if any(kw in line.lower() for kw in ("trade-off", "tradeoff", "trade off")):
                        tradeoffs.append(Tradeoff(
                            description=line.strip()[:150],
                            chosen_path="",
                            rejected_path="",
                            rationale=line.strip()[:200],
                            evidence=[f"documentation in {f.name}"],
                            confidence=0.4,
                        ))
            except Exception:
                pass

        return tradeoffs[:10]

    def _extract_tradeoff(self, msg: str) -> Tradeoff:
        tradeoff_patterns = [
            (r"(?:migrate|migration)\s+from\s+(\w+)\s+to\s+(\w+)", "migration"),
            (r"(?:refactor|refactoring)\s+(\w+)", "refactor"),
            (r"(?:optimize|optimization)\s+of\s+(\w+)", "optimization"),
            (r"(?:replace|swap)\s+(\w+)\s+(?:with|for)\s+(\w+)", "replacement"),
        ]

        for pattern, kind in tradeoff_patterns:
            m = re.search(pattern, msg, re.IGNORECASE)
            if m:
                groups = m.groups()
                return Tradeoff(
                    description=msg[:150],
                    chosen_path=groups[-1] if len(groups) > 1 else groups[0],
                    rejected_path=groups[0] if len(groups) > 1 else "",
                    rationale=msg[:200],
                    evidence=[f"git commit: {msg[:100]}"],
                    confidence=0.5,
                )

        return Tradeoff(
            description=msg[:150],
            rationale=msg[:200],
            evidence=["git commit message"],
            confidence=0.3,
        )


class ConstraintAnalyzer:
    def analyze(self, repo_path: Path, model: IntentModel) -> List[str]:
        constraints: List[str] = []

        for f in repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                            for sub in ast.walk(item):
                                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                                    if sub.func.attr in ("validate", "check", "assert", "ensure"):
                                        args = [ast.unparse(a) for a in sub.args] if hasattr(ast, 'unparse') else []
                                        if args:
                                            constraints.append(f"Validation in {Path(f).name}: {args[0][:60]}")

        for f in repo_path.rglob("*.py"):
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for m in re.finditer(r"(?:must|should|shall|requires?|cannot)\s+([^.\n]+)", text, re.IGNORECASE):
                constraint = m.group(0).strip()[:100]
                if len(constraint) > 10:
                    constraints.append(constraint)

        return list(set(constraints))[:20]


class HistoricalDirectionAnalyzer:
    def analyze(self, repo_path: Path, model: IntentModel) -> List[str]:
        directions: List[str] = []

        if not (repo_path / ".git").exists():
            return ["No git history available"]

        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "log", "--format=%s", "-200"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                return ["git log failed"]

            messages = result.stdout.splitlines()
            direction_clues = {
                "migrat": "Migration toward new technology stack",
                "refactor": "Refactoring toward better structure",
                "modulariz": "Modularization effort",
                "extract": "Extraction/decoupling of components",
                "unif": "Unification/consolidation effort",
                "delet": "Removal of deprecated code",
                "simplif": "Simplification effort",
                "optimiz": "Performance optimization focus",
                "upgrade": "Technology upgrade cycle",
                "test": "Test coverage improvement",
                "feat": "Feature extension",
                "fix": "Bug fix and stabilization",
                "config": "Configuration management",
                "cleanup": "Code cleanup and debt reduction",
            }

            counts: Dict[str, int] = defaultdict(int)
            for msg in messages:
                msg_lower = msg.lower()
                for clue, direction in direction_clues.items():
                    if clue in msg_lower:
                        counts[clue] += 1

            if counts:
                top = sorted(counts.items(), key=lambda x: -x[1])[:5]
                for clue, count in top:
                    directions.append(f"{direction_clues[clue]} ({count} commits)")

            if len(messages) > 50:
                recent = messages[:50]
                recent_counts: Dict[str, int] = defaultdict(int)
                for msg in recent:
                    msg_lower = msg.lower()
                    for clue in direction_clues:
                        if clue in msg_lower:
                            recent_counts[clue] += 1
                if recent_counts:
                    top_recent = sorted(recent_counts.items(), key=lambda x: -x[1])[:3]
                    directions.append("Recent focus: " + ", ".join(
                        f"{direction_clues[c]}" for c, _ in top_recent
                    ))

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return directions or ["Direction unclear from available history"]


class RefactorPredictor:
    def predict(self, repo_path: Path, model: IntentModel) -> List[Dict[str, Any]]:
        predictions: List[Dict[str, Any]] = []

        large_files = []
        high_complexity_modules = []
        for f in repo_path.rglob("*.py"):
            if not f.is_file():
                continue
            try:
                lines = len(f.read_text(encoding="utf-8", errors="replace").splitlines())
                rel = str(f.relative_to(repo_path))
                if lines > 500:
                    large_files.append({"file": rel, "lines": lines})
            except Exception:
                pass

        for lf in large_files:
            predictions.append({
                "type": "extract_module",
                "file": lf["file"],
                "prediction": f"Likely to be split: {lf['lines']} lines exceeds maintainable threshold",
                "confidence": min(0.9, 0.3 + lf["lines"] / 1000),
                "timeframe": "medium_term",
                "evidence": ["file size > 500 lines"],
            })

        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "log", "--format=%s", "-100"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                messages = " ".join(result.stdout.splitlines()).lower()
                if "migration" in messages or "upgrade" in messages:
                    predictions.append({
                        "type": "continued_migration",
                        "prediction": "Ongoing migration/upgrade cycle will continue",
                        "confidence": 0.6,
                        "timeframe": "ongoing",
                        "evidence": ["migration/upgrade keywords in commit history"],
                    })
        except Exception:
            pass

        if not large_files:
            predictions.append({
                "type": "stability",
                "prediction": "No clear refactor signals detected",
                "confidence": 0.5,
                "timeframe": "unknown",
                "evidence": ["no large files or migration patterns found"],
            })

        return predictions[:10]


class IntentInferenceEngine:
    def __init__(self):
        self.purpose = SubsystemPurposeAnalyzer()
        self.philosophy = DesignPhilosophyAnalyzer()
        self.tradeoffs = TradeoffAnalyzer()
        self.constraints = ConstraintAnalyzer()
        self.direction = HistoricalDirectionAnalyzer()
        self.refactor = RefactorPredictor()

    def infer(self, repo_path: Path) -> IntentModel:
        repo_path = Path(repo_path).resolve()
        model = IntentModel(repo_path=str(repo_path))

        try:
            subsystem_intents = self.purpose.analyze(repo_path, model)
            for si in subsystem_intents:
                model.add_subsystem_intent(si)
        except Exception:
            pass

        try:
            philosophy = self.philosophy.analyze(repo_path, model)
            model.overall_philosophy = philosophy
        except Exception:
            pass

        try:
            tradeoffs = self.tradeoffs.analyze(repo_path, model)
            if tradeoffs and model.intents:
                model.intents[0].tradeoffs.extend(tradeoffs[:5])
        except Exception:
            pass

        try:
            constraints = self.constraints.analyze(repo_path, model)
            if constraints and model.intents:
                for si in model.intents[:3]:
                    si.constraints.extend(constraints[:5])
        except Exception:
            pass

        try:
            directions = self.direction.analyze(repo_path, model)
            if directions and model.intents:
                for si in model.intents[:3]:
                    si.evolution.extend(directions[:3])
        except Exception:
            pass

        try:
            predictions = self.refactor.predict(repo_path, model)
            model.metadata = {"refactor_predictions": predictions}
        except Exception:
            pass

        model = self._estimate_confidence(model)
        return model

    def _estimate_confidence(self, model: IntentModel) -> IntentModel:
        evidence_count = sum(len(si.evidence) for si in model.intents)
        has_philosophy = model.overall_philosophy != DesignPhilosophy.UNKNOWN
        has_direction = any(si.evolution for si in model.intents)

        base = 0.3
        evidence_bonus = min(0.4, evidence_count * 0.05)
        philosophy_bonus = 0.2 if has_philosophy else 0
        direction_bonus = 0.1 if has_direction else 0

        overall = min(1.0, base + evidence_bonus + philosophy_bonus + direction_bonus)

        for si in model.intents:
            if si.confidence == 0.0:
                si.confidence = overall
            uncertainty = 1.0 - si.confidence
            si.uncertainty = IntentUncertainty(
                overall=uncertainty,
                evidence_gap=max(0, uncertainty - 0.2),
                contradiction_level=0.1,
                staleness=0.0,
            )

        return model
