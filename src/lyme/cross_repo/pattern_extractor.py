from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from enum import Enum
import json
import uuid
import hashlib


class PatternCategory(str, Enum):
    ARCHITECTURE = "architecture"
    FAILURE_MODE = "failure_mode"
    REFACTOR_PATH = "refactor_path"
    DEPENDENCY_MIGRATION = "dependency_migration"
    TESTING_STRATEGY = "testing_strategy"
    ANTI_PATTERN = "anti_pattern"
    REPAIR_MOTIF = "repair_motif"
    ECOSYSTEM_CONVENTION = "ecosystem_convention"
    CONFIGURATION = "configuration"
    ERROR_HANDLING = "error_handling"


class PatternSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class PatternSource:
    repo_id: str
    file_paths: List[str]
    occurrence_count: int
    confidence: float
    context: Dict = field(default_factory=dict)


@dataclass
class CrossRepoPattern:
    id: str
    category: PatternCategory
    name: str
    description: str
    pattern_hash: str
    sources: List[PatternSource]
    occurrences: int
    severity: PatternSeverity
    signature: Dict
    variants: List[Dict] = field(default_factory=list)
    transfer_success_rate: float = 0.0
    adaptation_required: bool = False
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "category": self.category.value,
            "name": self.name,
            "description": self.description,
            "pattern_hash": self.pattern_hash,
            "sources": [s.__dict__ for s in self.sources],
            "occurrences": self.occurrences,
            "severity": self.severity.value,
            "signature": self.signature,
            "variants": self.variants,
            "transfer_success_rate": self.transfer_success_rate,
            "adaptation_required": self.adaptation_required,
            "tags": self.tags,
        }


@dataclass
class PatternCluster:
    id: str
    patterns: List[CrossRepoPattern]
    centroid: Dict
    coherence: float
    label: str = ""
    description: str = ""

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "patterns": [p.to_dict() for p in self.patterns],
            "centroid": self.centroid,
            "coherence": self.coherence,
            "label": self.label,
            "description": self.description,
        }


class PatternExtractor:
    def __init__(self):
        self._patterns: List[CrossRepoPattern] = []

    def extract_from_fingerprints(self, fingerprints: List, existing_patterns: Optional[List[CrossRepoPattern]] = None) -> List[CrossRepoPattern]:
        if existing_patterns:
            self._patterns = list(existing_patterns)

        patterns = []
        patterns.extend(self._extract_arch_patterns(fingerprints))
        patterns.extend(self._extract_failure_patterns(fingerprints))
        patterns.extend(self._extract_testing_patterns(fingerprints))
        patterns.extend(self._extract_dependency_patterns(fingerprints))
        patterns.extend(self._extract_convention_patterns(fingerprints))
        patterns.extend(self._extract_config_patterns(fingerprints))

        deduped = self._deduplicate(patterns)
        self._patterns.extend(deduped)
        return deduped

    def _extract_arch_patterns(self, fingerprints: List) -> List[CrossRepoPattern]:
        patterns = []
        arch_counts: Dict[str, List[str]] = {}
        for fp in fingerprints:
            arch = fp.components.get("arch_patterns", {})
            for pattern, score in arch.items():
                if score > 0.4:
                    if pattern not in arch_counts:
                        arch_counts[pattern] = []
                    arch_counts[pattern].append(fp.repo_id)

        for pattern, repos in arch_counts.items():
            if len(repos) >= 2:
                pid = uuid.uuid4().hex[:12]
                sig = hashlib.sha256(pattern.encode()).hexdigest()[:12]
                sources = [
                    PatternSource(repo_id=r, file_paths=[], occurrence_count=1, confidence=0.7)
                    for r in repos
                ]
                p = CrossRepoPattern(
                    id=f"arch_{pid}",
                    category=PatternCategory.ARCHITECTURE,
                    name=f"Architecture: {pattern}",
                    description=f"Repository uses {pattern} architectural pattern",
                    pattern_hash=sig,
                    sources=sources,
                    occurrences=len(repos),
                    severity=PatternSeverity.INFO,
                    signature={"pattern": pattern, "prevalence": len(repos)},
                    tags=["architecture", pattern],
                )
                patterns.append(p)
        return patterns

    def _extract_failure_patterns(self, fingerprints: List) -> List[CrossRepoPattern]:
        patterns = []
        error_profiles: Dict[str, List[str]] = {}

        for fp in fingerprints:
            err = fp.components.get("error_handling", {})
            dominant = max(err, key=err.get) if err else None
            if dominant and err.get(dominant, 0) > 0.01:
                if dominant not in error_profiles:
                    error_profiles[dominant] = []
                error_profiles[dominant].append(fp.repo_id)

        high_risk_strategies = {"panic": "critical", "unwrap": "warning"}

        for strategy, repos in error_profiles.items():
            if len(repos) >= 2:
                pid = uuid.uuid4().hex[:12]
                sev = PatternSeverity(high_risk_strategies.get(strategy, "info"))
                sources = [
                    PatternSource(repo_id=r, file_paths=[], occurrence_count=1, confidence=0.65)
                    for r in repos
                ]
                p = CrossRepoPattern(
                    id=f"fail_{pid}",
                    category=PatternCategory.FAILURE_MODE,
                    name=f"Error Handling: {strategy}",
                    description=f"Repository predominantly uses {strategy} for error handling",
                    pattern_hash=hashlib.sha256(strategy.encode()).hexdigest()[:12],
                    sources=sources,
                    occurrences=len(repos),
                    severity=sev,
                    signature={"strategy": strategy, "prevalence": len(repos)},
                    tags=["error_handling", strategy],
                )
                patterns.append(p)
        return patterns

    def _extract_testing_patterns(self, fingerprints: List) -> List[CrossRepoPattern]:
        patterns = []
        test_profiles: Dict[str, List[Tuple[str, float]]] = {}

        for fp in fingerprints:
            test_pat = fp.components.get("testing_pattern", {})
            test_frame = fp.components.get("test_framework", {})
            dominant_frame = max(test_frame, key=test_frame.get) if test_frame else None
            for strategy, score in test_pat.items():
                if score > 0.005:
                    key = f"{dominant_frame}_{strategy}" if dominant_frame else strategy
                    if key not in test_profiles:
                        test_profiles[key] = []
                    test_profiles[key].append((fp.repo_id, score))

        for key, entries in test_profiles.items():
            if len(entries) >= 2:
                pid = uuid.uuid4().hex[:12]
                sources = [
                    PatternSource(repo_id=r, file_paths=[], occurrence_count=1, confidence=s)
                    for r, s in entries
                ]
                p = CrossRepoPattern(
                    id=f"test_{pid}",
                    category=PatternCategory.TESTING_STRATEGY,
                    name=f"Testing: {key}",
                    description=f"Testing strategy pattern: {key}",
                    pattern_hash=hashlib.sha256(key.encode()).hexdigest()[:12],
                    sources=sources,
                    occurrences=len(entries),
                    severity=PatternSeverity.INFO,
                    signature={"testing_key": key, "avg_score": sum(s for _, s in entries) / len(entries)},
                    tags=["testing", key.split("_")[0]] if "_" in key else ["testing"],
                )
                patterns.append(p)
        return patterns

    def _extract_dependency_patterns(self, fingerprints: List) -> List[CrossRepoPattern]:
        patterns = []
        dep_categories: Dict[str, List[str]] = {}

        for fp in fingerprints:
            dep_sig = fp.dependency_signature
            seen = set()
            for d in dep_sig:
                if d.category not in seen:
                    seen.add(d.category)
                    if d.category not in dep_categories:
                        dep_categories[d.category] = []
                    dep_categories[d.category].append(fp.repo_id)

        for category, repos in dep_categories.items():
            if len(repos) >= 2:
                pid = uuid.uuid4().hex[:12]
                sources = [
                    PatternSource(repo_id=r, file_paths=[], occurrence_count=1, confidence=0.7)
                    for r in repos
                ]
                p = CrossRepoPattern(
                    id=f"dep_{pid}",
                    category=PatternCategory.DEPENDENCY_MIGRATION,
                    name=f"Dependency: {category}",
                    description=f"Multiple repos share dependency category: {category}",
                    pattern_hash=hashlib.sha256(category.encode()).hexdigest()[:12],
                    sources=sources,
                    occurrences=len(repos),
                    severity=PatternSeverity.INFO,
                    signature={"category": category, "repo_count": len(repos)},
                    tags=["dependency", category],
                )
                patterns.append(p)
        return patterns

    def _extract_convention_patterns(self, fingerprints: List) -> List[CrossRepoPattern]:
        patterns = []
        conventions: Dict[str, List[Tuple[str, float]]] = {}

        for fp in fingerprints:
            conv = fp.convention_signature
            dominant = max(conv, key=conv.get) if conv else None
            if dominant and conv[dominant] > 0.3:
                if dominant not in conventions:
                    conventions[dominant] = []
                conventions[dominant].append((fp.repo_id, conv[dominant]))

        for convention, entries in conventions.items():
            if len(entries) >= 2:
                pid = uuid.uuid4().hex[:12]
                sources = [
                    PatternSource(repo_id=r, file_paths=[], occurrence_count=1, confidence=s)
                    for r, s in entries
                ]
                p = CrossRepoPattern(
                    id=f"conv_{pid}",
                    category=PatternCategory.ECOSYSTEM_CONVENTION,
                    name=f"Convention: {convention}",
                    description=f"Naming convention {convention} is dominant across multiple repos",
                    pattern_hash=hashlib.sha256(convention.encode()).hexdigest()[:12],
                    sources=sources,
                    occurrences=len(entries),
                    severity=PatternSeverity.INFO,
                    signature={"convention": convention, "avg_dominance": sum(s for _, s in entries) / len(entries)},
                    tags=["convention", convention],
                )
                patterns.append(p)
        return patterns

    def _extract_config_patterns(self, fingerprints: List) -> List[CrossRepoPattern]:
        patterns = []
        config_counts: Dict[str, List[str]] = {}

        for fp in fingerprints:
            configs = fp.components.get("configuration", {})
            for cfg, present in configs.items():
                if present:
                    if cfg not in config_counts:
                        config_counts[cfg] = []
                    config_counts[cfg].append(fp.repo_id)

        for cfg, repos in config_counts.items():
            if len(repos) >= 3:
                pid = uuid.uuid4().hex[:12]
                sources = [
                    PatternSource(repo_id=r, file_paths=[cfg], occurrence_count=1, confidence=0.8)
                    for r in repos
                ]
                p = CrossRepoPattern(
                    id=f"cfg_{pid}",
                    category=PatternCategory.CONFIGURATION,
                    name=f"Config: {cfg}",
                    description=f"Configuration file {cfg} found across {len(repos)} repos",
                    pattern_hash=hashlib.sha256(cfg.encode()).hexdigest()[:12],
                    sources=sources,
                    occurrences=len(repos),
                    severity=PatternSeverity.INFO,
                    signature={"config_file": cfg, "prevalence": len(repos)},
                    tags=["configuration", cfg],
                )
                patterns.append(p)
        return patterns

    def _deduplicate(self, patterns: List[CrossRepoPattern]) -> List[CrossRepoPattern]:
        seen: Set[str] = set()
        deduped = []
        for p in patterns:
            if p.pattern_hash not in seen:
                seen.add(p.pattern_hash)
                deduped.append(p)
            else:
                existing = next((x for x in deduped if x.pattern_hash == p.pattern_hash), None)
                if existing:
                    existing.occurrences += p.occurrences
                    existing.sources.extend(p.sources)
        return deduped

    def save(self, path: Path):
        data = [p.to_dict() for p in self._patterns]
        path.write_text(json.dumps(data, indent=2))

    def load(self, path: Path) -> List[CrossRepoPattern]:
        data = json.loads(path.read_text())
        self._patterns = [self._dict_to_pattern(d) for d in data]
        return self._patterns

    def _dict_to_pattern(self, d: Dict) -> CrossRepoPattern:
        return CrossRepoPattern(
            id=d["id"],
            category=PatternCategory(d["category"]),
            name=d["name"],
            description=d["description"],
            pattern_hash=d["pattern_hash"],
            sources=[PatternSource(**s) for s in d.get("sources", [])],
            occurrences=d["occurrences"],
            severity=PatternSeverity(d["severity"]),
            signature=d["signature"],
            variants=d.get("variants", []),
            transfer_success_rate=d.get("transfer_success_rate", 0.0),
            adaptation_required=d.get("adaptation_required", False),
            tags=d.get("tags", []),
        )

    @property
    def patterns(self) -> List[CrossRepoPattern]:
        return self._patterns
