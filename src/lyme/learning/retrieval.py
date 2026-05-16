from __future__ import annotations

import math
import re
import subprocess
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .memory import (
    HistoricalMemory, MemoryItem, MemoryType, MemoryRetrievalResult,
    RefactorMotif, BugPattern, RepairStrategy, MigrationPattern,
)


class SimilarityScorer:
    def score(self, query: str, item: MemoryItem) -> float:
        query_lower = query.lower()
        item_text = f"{item.description} {item.pattern} {item.context} {item.outcome}".lower()
        query_tokens = set(query_lower.split())
        item_tokens = set(item_text.split())

        if not query_tokens or not item_tokens:
            return 0.0

        overlap = len(query_tokens & item_tokens)
        jaccard = overlap / len(query_tokens | item_tokens) if query_tokens | item_tokens else 0

        keyword_match = sum(1 for kw in query_tokens if kw in item_text)
        keyword_ratio = keyword_match / max(len(query_tokens), 1)

        return jaccard * 0.4 + keyword_ratio * 0.6


class MemoryRetrievalSystem:
    def __init__(self, memory: HistoricalMemory):
        self.memory = memory
        self.scorer = SimilarityScorer()

    def retrieve(self, query: str, limit: int = 10, min_score: float = 0.1) -> MemoryRetrievalResult:
        scored: List[Tuple[float, MemoryItem]] = []

        for item in self.memory._items.values():
            score = self.scorer.score(query, item)
            if score >= min_score:
                scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        result = MemoryRetrievalResult(
            items=[s[1] for s in scored[:limit]],
            similarity_scores={s[1].id: s[0] for s in scored[:limit]},
            total_found=len(scored),
            query=query,
        )
        return result

    def find_similar_to(self, item: MemoryItem, limit: int = 5) -> List[MemoryItem]:
        scored: List[Tuple[float, MemoryItem]] = []
        for other in self.memory._items.values():
            if other.id == item.id:
                continue
            score = self.scorer.score(item.description, other)
            scored.append((score, other))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:limit]]


class StrategySynthesizer:
    def synthesize(self, results: MemoryRetrievalResult) -> List[Dict[str, Any]]:
        if not results.items:
            return []

        strategies = []
        by_type: Dict[str, List[MemoryItem]] = defaultdict(list)
        for item in results.items:
            by_type[item.memory_type.value].append(item)

        for mtype, items in by_type.items():
            if len(items) >= 2:
                combined_steps = []
                seen_steps: Set[str] = set()
                for item in items:
                    for step in item.steps:
                        if step not in seen_steps:
                            combined_steps.append(step)
                            seen_steps.add(step)

                avg_success = sum(i.success_score for i in items) / len(items)
                avg_confidence = sum(i.confidence for i in items) / len(items)

                strategies.append({
                    "type": mtype,
                    "synthesized_steps": combined_steps[:7],
                    "avg_success_rate": avg_success,
                    "confidence": avg_confidence,
                    "source_count": len(items),
                    "derived_from": [i.id for i in items[:3]],
                })

        return strategies


class CompatibilityScorer:
    def score(self, item: MemoryItem, repo_path: Path) -> float:
        score = 0.0
        reasons = []

        if item.source_repo and str(repo_path).endswith(item.source_repo):
            score += 0.3
            reasons.append("same repository")

        if item.tags:
            repo_tags = self._extract_repo_tags(repo_path)
            tag_overlap = len(set(item.tags) & set(repo_tags))
            score += tag_overlap * 0.1
            if tag_overlap > 0:
                reasons.append(f"shared tags: {tag_overlap}")

        score += item.confidence * 0.3
        item_age = time.time() - item.timestamp
        recency_bonus = max(0, 1.0 - item_age / (86400 * 90))
        score += recency_bonus * 0.2

        return {
            "compatibility": min(1.0, score),
            "reasons": reasons[:3],
        }

    def _extract_repo_tags(self, repo_path: Path) -> List[str]:
        tags = []
        if (repo_path / "pyproject.toml").exists():
            tags.append("python")
        if (repo_path / "package.json").exists():
            tags.append("javascript")
        if (repo_path / "Cargo.toml").exists():
            tags.append("rust")
        if (repo_path / "Gemfile").exists():
            tags.append("ruby")
        if (repo_path / "requirements.txt").exists():
            tags.append("python")
        if any(f.name.endswith(".ts") for f in repo_path.rglob("*.ts")):
            tags.append("typescript")
        return tags


class HistoricalLearningEngine:
    def __init__(self):
        self.memory = HistoricalMemory()
        self.retrieval = MemoryRetrievalSystem(self.memory)
        self.synthesizer = StrategySynthesizer()
        self.compatibility = CompatibilityScorer()

    def learn_from_git_history(self, repo_path: Path):
        repo_path = Path(repo_path).resolve()
        motifs = self._extract_refactor_motifs(repo_path)
        for motif in motifs:
            self.memory.add(motif)

        patterns = self._extract_bug_patterns(repo_path)
        for pattern in patterns:
            self.memory.add(pattern)

        strategies = self._extract_repair_strategies(repo_path)
        for strategy in strategies:
            self.memory.add(strategy)

    def _extract_refactor_motifs(self, repo_path: Path) -> List[MemoryItem]:
        items = []
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "log", "--format=%H|%an|%at|%s",
                 "--name-only", "--grep=refactor|restructure|extract|modulariz|clean", "-100"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                return items

            lines = result.stdout.splitlines()
            current_msg = ""
            current_files: List[str] = []
            for line in lines:
                if re.match(r"^[a-f0-9]{40}", line):
                    if current_msg and current_files:
                        item = MemoryItem(
                            memory_type=MemoryType.REFACTOR_MOTIF,
                            description=f"Refactor: {current_msg[:150]}",
                            pattern=self._extract_pattern_from_msg(current_msg),
                            context=f"Files: {', '.join(current_files[:5])}",
                            steps=[],
                            outcome=f"Refactored {len(current_files)} files",
                            success_score=0.5,
                            confidence=0.4,
                            source_repo=str(repo_path),
                            tags=["refactor", "git_history"],
                        )
                        items.append(item)
                    parts = line.split("|", 3)
                    current_msg = parts[3] if len(parts) > 3 else ""
                    current_files = []
                else:
                    current_files.append(line)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return items[:30]

    def _extract_bug_patterns(self, repo_path: Path) -> List[MemoryItem]:
        items = []
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "log", "--format=%H|%an|%at|%s",
                 "--name-only", "--grep=fix|bug|error|crash|regression", "-100"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                return items

            lines = result.stdout.splitlines()
            current_msg = ""
            current_files: List[str] = []
            for line in lines:
                if re.match(r"^[a-f0-9]{40}", line):
                    if current_msg and current_files:
                        item = MemoryItem(
                            memory_type=MemoryType.BUG_PATTERN,
                            description=f"Bug fix: {current_msg[:150]}",
                            pattern=self._extract_pattern_from_msg(current_msg),
                            context=f"Files affected: {', '.join(current_files[:5])}",
                            triggers=[self._extract_trigger(current_msg)],
                            steps=[],
                            outcome="Fixed",
                            success_score=0.7,
                            confidence=0.3,
                            recurrence_count=1,
                            source_repo=str(repo_path),
                            tags=["bug", "fix"],
                        )
                        items.append(item)
                    parts = line.split("|", 3)
                    current_msg = parts[3] if len(parts) > 3 else ""
                    current_files = []
                else:
                    current_files.append(line)
        except Exception:
            pass

        return items[:30]

    def _extract_repair_strategies(self, repo_path: Path) -> List[MemoryItem]:
        items = []
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "log", "--format=%H|%an|%at|%s",
                 "--name-only", "--grep=fix|hotfix|patch|resolve", "-50"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                return items

            seen = set()
            lines = result.stdout.splitlines()
            current_msg = ""
            current_files: List[str] = []
            for line in lines:
                if re.match(r"^[a-f0-9]{40}", line):
                    if current_msg and current_files and current_msg not in seen:
                        seen.add(current_msg)
                        item = MemoryItem(
                            memory_type=MemoryType.REPAIR_STRATEGY,
                            description=f"Repair strategy: {current_msg[:150]}",
                            pattern=self._extract_pattern_from_msg(current_msg),
                            context=f"Scope: {', '.join(current_files[:5])}",
                            triggers=[],
                            steps=[],
                            outcome="Applied repair across {len(current_files)} files",
                            success_score=0.6,
                            confidence=0.35,
                            source_repo=str(repo_path),
                            tags=["repair"],
                        )
                        items.append(item)
                    parts = line.split("|", 3)
                    current_msg = parts[3] if len(parts) > 3 else ""
                    current_files = []
                else:
                    current_files.append(line)
        except Exception:
            pass

        return items[:20]

    def _extract_pattern_from_msg(self, msg: str) -> str:
        patterns = [
            (r"extract\s+(\w+)", "Pattern: Extract {}"),
            (r"move\s+(\w+)", "Pattern: Move {}"),
            (r"rename\s+(\w+)", "Pattern: Rename {}"),
            (r"split\s+(\w+)", "Pattern: Split {}"),
            (r"merge\s+(\w+)", "Pattern: Merge {}"),
            (r"remove\s+(\w+)", "Pattern: Remove {}"),
            (r"simplif", "Pattern: Simplify"),
            (r"migrat", "Pattern: Migration"),
            (r"upgrade", "Pattern: Upgrade"),
            (r"clean", "Pattern: Cleanup"),
        ]
        for regex, template in patterns:
            m = re.search(regex, msg, re.IGNORECASE)
            if m:
                return template.format(m.group(1))
        return f"Pattern: {msg[:80]}"

    def _extract_trigger(self, msg: str) -> str:
        triggers = [
            (r"null|none|empty", "null/none/empty check"),
            (r"timeout", "timeout handling"),
            (r"race|concurr", "concurrency issue"),
            (r"type|cast", "type error"),
            (r"config|setting", "configuration issue"),
            (r"bound|limit|max", "boundary condition"),
            (r"perf|slow|latency", "performance issue"),
        ]
        msg_lower = msg.lower()
        for regex, trigger in triggers:
            if re.search(regex, msg_lower):
                return trigger
        return "general error"

    def query(self, query: str, limit: int = 10) -> MemoryRetrievalResult:
        return self.retrieval.retrieve(query, limit=limit)

    def recommend(self, repo_path: Path, query: str) -> List[Dict[str, Any]]:
        results = self.query(query)
        synthesized = self.synthesizer.synthesize(results)

        recommendations = []
        for strategy in synthesized:
            recommendations.append({
                "type": strategy["type"],
                "steps": strategy["synthesized_steps"],
                "confidence": strategy["confidence"],
                "source_count": strategy["source_count"],
            })

        for item in results.items[:5]:
            comp = self.compatibility.score(item, repo_path)
            if comp["compatibility"] > 0.3:
                recommendations.append({
                    "type": "historical_pattern",
                    "pattern": item.pattern[:100],
                    "description": item.description[:100],
                    "compatibility": comp["compatibility"],
                    "confidence": item.confidence,
                })

        return recommendations[:10]
