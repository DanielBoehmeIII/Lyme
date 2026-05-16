from __future__ import annotations

import ast
import math
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .risk_model import (
    RiskModel, RiskFactor, RiskScore, FileRiskProfile,
    FailurePrediction, RiskCategory,
)


class HistoricalBreakageAnalyzer:
    def analyze(self, repo_path: Path, risk_model: RiskModel) -> List[FileRiskProfile]:
        profiles: Dict[str, FileRiskProfile] = {}
        breakage_counts: Counter = Counter()
        fix_counts: Counter = Counter()
        file_sequences: Dict[str, List[int]] = defaultdict(list)
        seq = 0

        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "log", "--format=%H|%s", "--name-only",
                 "--diff-filter=AM", "-500"],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                return []

            current_msg = ""
            current_files: List[str] = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                if re.match(r"^[a-f0-9]{40}", line):
                    if current_files:
                        seq += 1
                        if any(kw in current_msg.lower() for kw in ("fix", "bug", "error", "crash", "regression")):
                            for f in current_files:
                                breakage_counts[f] += 1
                                file_sequences[f].append(seq)
                        else:
                            for f in current_files:
                                fix_counts[f] += 1
                                file_sequences[f].append(seq)
                    parts = line.split("|", 1)
                    current_msg = parts[1] if len(parts) > 1 else ""
                    current_files = []
                else:
                    current_files.append(line)

            if current_files:
                seq += 1
                if any(kw in current_msg.lower() for kw in ("fix", "bug", "error", "crash", "regression")):
                    for f in current_files:
                        breakage_counts[f] += 1
                else:
                    for f in current_files:
                        fix_counts[f] += 1

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

        for f, breaks in breakage_counts.most_common(50):
            total_changes = fix_counts.get(f, 0) + breaks
            breakage_ratio = breaks / max(total_changes, 1)

            factors = [
                RiskFactor(
                    name="historical_breakage",
                    category=RiskCategory.BREAKAGE,
                    score=min(1.0, breakage_ratio * 2),
                    weight=0.8,
                    evidence=f"Failed {breaks} out of {total_changes} changes",
                    confidence=min(0.9, total_changes * 0.05),
                )
            ]

            risk_score = RiskScore(
                overall=min(1.0, breakage_ratio * 1.5),
                factors=factors,
                confidence=min(0.9, total_changes * 0.05),
            )

            parts = Path(f).parts
            subsystem = parts[0] if len(parts) >= 2 else "/"

            profile = FileRiskProfile(
                file_path=f,
                subsystem=subsystem,
                risk_score=risk_score,
                previous_failures=breaks,
                change_frequency=total_changes / max(seq, 1),
            )
            profiles[f] = profile

        return list(profiles.values())


class CausalCouplingAnalyzer:
    def analyze(self, repo_path: Path, risk_model: RiskModel) -> List[RiskFactor]:
        factors: List[RiskFactor] = []
        co_change_pairs: Dict[Tuple[str, str], int] = defaultdict(int)

        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "log", "--format=%H", "--name-only",
                 "--diff-filter=AM", "-300"],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                return factors

            current_files: List[str] = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                if re.match(r"^[a-f0-9]{40}$", line):
                    if current_files:
                        for i, f1 in enumerate(current_files):
                            for f2 in current_files[i + 1:]:
                                key = (f1, f2) if f1 < f2 else (f2, f1)
                                co_change_pairs[key] += 1
                    current_files = []
                else:
                    current_files.append(line)
            if current_files:
                for i, f1 in enumerate(current_files):
                    for f2 in current_files[i + 1:]:
                        key = (f1, f2) if f1 < f2 else (f2, f1)
                        co_change_pairs[key] += 1
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return factors

        for (f1, f2), count in co_change_pairs.items():
            if count >= 5:
                factors.append(RiskFactor(
                    name=f"causal_coupling: {Path(f1).name} <-> {Path(f2).name}",
                    category=RiskCategory.HIDDEN_COUPLING,
                    score=min(1.0, count * 0.1),
                    weight=0.6,
                    evidence=f"Co-changed {count} times together",
                    confidence=min(0.8, count * 0.1),
                ))

        return factors[:30]


class UnstableAbstractionDetector:
    def detect(self, repo_path: Path) -> List[RiskFactor]:
        factors: List[RiskFactor] = []

        for f in repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
            except Exception:
                continue

            rel = str(f.relative_to(repo_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    is_abstract = any(
                        isinstance(base, ast.Name) and base.id in ("ABC", "Protocol", "Interface")
                        for base in node.bases
                    )
                    if is_abstract:
                        implementations = self._find_implementations(repo_path, node.name)
                        if len(implementations) > 5:
                            factors.append(RiskFactor(
                                name=f"unstable_abstraction: {node.name}",
                                category=RiskCategory.ARCHITECTURAL_INSTABILITY,
                                score=min(1.0, len(implementations) * 0.1),
                                weight=0.5,
                                evidence=f"Interface '{node.name}' has {len(implementations)} implementations in {rel}",
                                confidence=0.6,
                            ))

        return factors[:10]

    def _find_implementations(self, repo_path: Path, class_name: str) -> List[str]:
        impls = []
        for f in repo_path.rglob("*.py"):
            if not f.is_file():
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                if class_name in text:
                    tree = ast.parse(text)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            for base in node.bases:
                                if isinstance(base, ast.Name) and base.id == class_name:
                                    impls.append(str(f.relative_to(repo_path)))
            except Exception:
                pass
        return impls


class RepairPatternAnalyzer:
    def analyze(self, repo_path: Path) -> List[RiskFactor]:
        factors: List[RiskFactor] = []
        repair_patterns: Dict[str, int] = defaultdict(int)

        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "log", "--format=%s", "--grep=fix|bug|error",
                 "-200"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    msg = line.lower()
                    if "null" in msg or "none" in msg or "empty" in msg:
                        repair_patterns["null_handling"] += 1
                    if "timeout" in msg or "time_out" in msg:
                        repair_patterns["timeout"] += 1
                    if "race" in msg or "concurr" in msg:
                        repair_patterns["concurrency"] += 1
                    if "config" in msg or "setting" in msg:
                        repair_patterns["configuration"] += 1
                    if "migrat" in msg:
                        repair_patterns["migration"] += 1
                    if "type" in msg or "cast" in msg:
                        repair_patterns["type_error"] += 1
                    if "perf" in msg or "slow" in msg:
                        repair_patterns["performance"] += 1
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return factors

        for pattern, count in repair_patterns.items():
            if count >= 3:
                factors.append(RiskFactor(
                    name=f"repair_pattern: {pattern}",
                    category=RiskCategory.REGRESSION,
                    score=min(1.0, count * 0.1),
                    weight=0.4,
                    evidence=f"'{pattern}' pattern appeared in {count} fix commits",
                    confidence=min(0.7, count * 0.1),
                ))

        return factors


class TestFragilityAnalyzer:
    def analyze(self, repo_path: Path) -> List[RiskFactor]:
        factors: List[RiskFactor] = []

        test_files = []
        for f in repo_path.rglob("*"):
            if f.is_file() and ("test" in f.stem.lower() or f.stem.startswith("test_")):
                test_files.append(f)

        flaky_tests = 0
        slow_tests = 0
        for tf in test_files[:50]:
            try:
                text = tf.read_text(encoding="utf-8", errors="replace")
                lines = text.splitlines()
                for line in lines:
                    if "sleep(" in line:
                        slow_tests += 1
                    if "try:" in line and "except" in text:
                        pass
            except Exception:
                pass

        fragile_count = test_files.count(True) if test_files else 0

        if test_files:
            async_tests = 0
            for tf in test_files[:30]:
                try:
                    text = tf.read_text(encoding="utf-8", errors="replace")
                    async_tests += text.count("async def test_")
                except Exception:
                    pass

        if slow_tests > 5:
            factors.append(RiskFactor(
                name="test_fragility: slow_tests",
                category=RiskCategory.TEST_FRAGILITY,
                score=min(1.0, slow_tests * 0.15),
                weight=0.3,
                evidence=f"{slow_tests} tests use sleep() calls",
                confidence=0.5,
            ))

        return factors


class ComplexityAccumulationAnalyzer:
    def analyze(self, repo_path: Path) -> List[RiskFactor]:
        factors: List[RiskFactor] = []
        file_complexities: List[Tuple[str, float]] = []

        for f in repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
                lines = len(text.splitlines())

                func_count = sum(1 for _ in ast.walk(tree) if isinstance(_, ast.FunctionDef))
                class_count = sum(1 for _ in ast.walk(tree) if isinstance(_, ast.ClassDef))
                branch_count = sum(
                    1 for _ in ast.walk(tree)
                    if isinstance(_, (ast.If, ast.For, ast.While, ast.Try))
                )

                complexity = lines * 0.01 + func_count * 0.3 + class_count * 0.5 + branch_count * 0.4
                rel_path = str(f.relative_to(repo_path))
                file_complexities.append((rel_path, complexity))
            except Exception:
                pass

        file_complexities.sort(key=lambda x: -x[1])

        for file_path, complexity in file_complexities[:10]:
            if complexity > 20:
                factors.append(RiskFactor(
                    name=f"complexity: {Path(file_path).name}",
                    category=RiskCategory.COMPLEXITY,
                    score=min(1.0, complexity / 50),
                    weight=0.5,
                    evidence=f"Complexity score {complexity:.1f} in {file_path}",
                    confidence=0.7,
                ))

        return factors


class FailurePredictor:
    def __init__(self):
        self.historical = HistoricalBreakageAnalyzer()
        self.causal = CausalCouplingAnalyzer()
        self.unstable = UnstableAbstractionDetector()
        self.repair = RepairPatternAnalyzer()
        self.test = TestFragilityAnalyzer()
        self.complexity = ComplexityAccumulationAnalyzer()

    def predict(self, repo_path: Path) -> FailurePrediction:
        repo_path = Path(repo_path).resolve()
        risk_model = RiskModel()
        prediction = FailurePrediction()

        historical_profiles = self.historical.analyze(repo_path, risk_model)
        for profile in historical_profiles:
            risk_model.add_profile(profile)
            prediction.file_profiles.append(profile)

        causal_factors = self.causal.analyze(repo_path, risk_model)
        for profile in prediction.file_profiles:
            profile.risk_score.factors.extend(causal_factors[:3])

        unstable_factors = self.unstable.detect(repo_path)
        repair_factors = self.repair.analyze(repo_path)
        test_factors = self.test.analyze(repo_path)
        complexity_factors = self.complexity.analyze(repo_path)

        all_factors = causal_factors + unstable_factors + repair_factors + test_factors + complexity_factors

        for profile in prediction.file_profiles:
            relevant = [
                f for f in all_factors
                if profile.file_path in f.evidence
            ]
            profile.risk_score.factors.extend(relevant)

            all_profile_factors = profile.risk_score.factors
            if all_profile_factors:
                overall = sum(f.weighted_score for f in all_profile_factors) / sum(f.weight for f in all_profile_factors)
                profile.risk_score.overall = min(1.0, overall)
                profile.risk_score.confidence = sum(f.confidence for f in all_profile_factors) / len(all_profile_factors)

                if profile.risk_score.overall >= 0.7:
                    profile.predicted_breakpoints = [
                        f.name for f in all_profile_factors
                        if f.score >= 0.5
                    ]

        top_risks = sorted(
            [f for p in prediction.file_profiles for f in p.risk_score.factors],
            key=lambda f: -f.score
        )[:10]
        prediction.top_risks = [f.to_dict() for f in top_risks]

        prediction.evidence_trail = [
            f"Analyzed {len(historical_profiles)} files with breakage history",
            f"Found {len(causal_factors)} causal coupling relationships",
            f"Detected {len(unstable_factors)} unstable abstractions",
            f"Identified {len(repair_factors)} recurring repair patterns",
            f"Assessed test fragility across {len(test_factors)} dimensions",
            f"Measured complexity accumulation in {len(complexity_factors)} files",
        ]

        if all_factors:
            avg_conf = sum(f.confidence for f in all_factors) / len(all_factors)
            prediction.pipeline_confidence = min(1.0, avg_conf + 0.1)

        prediction.alternative_strategies = self._generate_strategies(top_risks)

        return prediction

    def _generate_strategies(self, top_risks: List[RiskFactor]) -> List[str]:
        strategies = []
        for risk in top_risks:
            if risk.category == RiskCategory.COMPLEXITY:
                strategies.append(f"Refactor high-complexity areas: {risk.name}")
            elif risk.category == RiskCategory.HIDDEN_COUPLING:
                strategies.append(f"Decouple hidden coupling: {risk.name}")
            elif risk.category == RiskCategory.TEST_FRAGILITY:
                strategies.append(f"Stabilize flaky tests: {risk.name}")
            elif risk.category == RiskCategory.BREAKAGE:
                strategies.append(f"Add regression protection: {risk.name}")
        return strategies[:5]
