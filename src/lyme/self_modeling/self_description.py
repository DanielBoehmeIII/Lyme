"""Repository Self-Description System.

A living README for machines and humans — continuously describing:
- what the repository is
- how it is structured
- what changed recently
- what invariants matter
- what risks are growing
- what parts are unstable
- what future work is likely
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime, timezone
from enum import Enum
import json
import subprocess
import hashlib
import re


class DescriptionSection(Enum):
    IDENTITY = "identity"
    STRUCTURE = "structure"
    RECENT_CHANGES = "recent_changes"
    INVARIANTS = "invariants"
    RISKS = "risks"
    UNSTABLE = "unstable"
    FUTURE_WORK = "future_work"
    METADATA = "metadata"


class DriftSeverity(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class EvidenceLink:
    path: str
    type: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    snippet: Optional[str] = None
    last_verified: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ConfidenceScore:
    overall: float = 0.0
    per_section: Dict[str, float] = field(default_factory=dict)
    evidence_count: int = 0
    staleness_days: int = 0
    contradictory_evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DriftWarning:
    section: str
    description: str
    severity: DriftSeverity
    metric: str
    old_value: Any = None
    new_value: Any = None
    threshold: Any = None
    evidence: List[str] = field(default_factory=list)
    detected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


@dataclass
class SelfDescription:
    repo_path: str
    repo_name: str
    repo_hash: str
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    schema_version: str = "0.1.0"

    identity: Dict[str, Any] = field(default_factory=dict)
    structure: Dict[str, Any] = field(default_factory=dict)
    recent_changes: Dict[str, Any] = field(default_factory=dict)
    invariants: Dict[str, Any] = field(default_factory=dict)
    risks: Dict[str, Any] = field(default_factory=dict)
    unstable: Dict[str, Any] = field(default_factory=dict)
    future_work: Dict[str, Any] = field(default_factory=dict)

    confidence: ConfidenceScore = field(default_factory=ConfidenceScore)
    evidence_links: List[EvidenceLink] = field(default_factory=list)
    drift_warnings: List[DriftWarning] = field(default_factory=list)
    update_history: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "repo_path": self.repo_path,
            "repo_name": self.repo_name,
            "repo_hash": self.repo_hash,
            "generated_at": self.generated_at,
            "identity": self.identity,
            "structure": self.structure,
            "recent_changes": self.recent_changes,
            "invariants": self.invariants,
            "risks": self.risks,
            "unstable": self.unstable,
            "future_work": self.future_work,
            "confidence": self.confidence.to_dict(),
            "evidence_links": [e.to_dict() for e in self.evidence_links],
            "drift_warnings": [w.to_dict() for w in self.drift_warnings],
            "update_history": self.update_history[-50:],
        }

    def to_markdown(self) -> str:
        lines = []
        lines.append(f"# Self-Description: {self.repo_name}")
        lines.append(f"")
        lines.append(f"**Generated**: {self.generated_at}")
        lines.append(f"**Confidence**: {self.confidence.overall:.0%}")
        lines.append(f"**Evidence count**: {self.confidence.evidence_count}")
        if self.confidence.staleness_days > 0:
            lines.append(f"**Staleness**: {self.confidence.staleness_days} days")
        lines.append(f"")

        if self.drift_warnings:
            critical = [w for w in self.drift_warnings if w.severity == DriftSeverity.CRITICAL]
            high = [w for w in self.drift_warnings if w.severity == DriftSeverity.HIGH]
            if critical or high:
                lines.append(f"## ⚠ Drift Warnings")
                for w in critical + high:
                    lines.append(f"- **[{w.severity.value.upper()}]** {w.description}")
                    for e in w.evidence[:2]:
                        lines.append(f"  - {e}")
                lines.append(f"")

        lines.append(f"## Identity")
        for k, v in self.identity.items():
            if isinstance(v, list):
                lines.append(f"- **{k}**: {', '.join(str(x) for x in v)}")
            elif isinstance(v, dict):
                lines.append(f"- **{k}**:")
                for sk, sv in v.items():
                    lines.append(f"  - {sk}: {sv}")
            else:
                lines.append(f"- **{k}**: {v}")
        lines.append(f"")

        if self.structure:
            lines.append(f"## Structure")
            for k, v in self.structure.items():
                if isinstance(v, list):
                    lines.append(f"- **{k}**: {len(v)} items")
                    for item in v[:5]:
                        lines.append(f"  - {item}")
                    if len(v) > 5:
                        lines.append(f"  - ... and {len(v) - 5} more")
                elif isinstance(v, dict):
                    lines.append(f"- **{k}**:")
                    for sk, sv in v.items():
                        lines.append(f"  - {sk}: {sv}")
                else:
                    lines.append(f"- **{k}**: {v}")
            lines.append(f"")

        if self.recent_changes:
            lines.append(f"## Recent Changes")
            for k, v in self.recent_changes.items():
                if isinstance(v, list):
                    lines.append(f"- **{k}**:")
                    for item in v[:10]:
                        lines.append(f"  - {item}")
                else:
                    lines.append(f"- **{k}**: {v}")
            lines.append(f"")

        if self.invariants:
            lines.append(f"## Invariants")
            inv_list = self.invariants.get("invariants", [])
            for inv in inv_list[:15]:
                lines.append(f"- [{inv.get('severity', 'medium')}] {inv.get('name', '?')}: {inv.get('description', '')[:100]}")
                if inv.get('confidence'):
                    lines.append(f"  (confidence: {inv['confidence']:.2f})")
            if len(inv_list) > 15:
                lines.append(f"  ... and {len(inv_list) - 15} more")
            lines.append(f"")

        if self.risks:
            lines.append(f"## Risks")
            for k, v in self.risks.items():
                if isinstance(v, list):
                    lines.append(f"- **{k}**:")
                    for item in v[:10]:
                        if isinstance(item, dict):
                            score = item.get('score', item.get('risk_score', '?'))
                            name = item.get('name', item.get('path', item.get('description', '?')))
                            lines.append(f"  - {name} (score: {score})")
                        else:
                            lines.append(f"  - {item}")
                else:
                    lines.append(f"- **{k}**: {v}")
            lines.append(f"")

        if self.unstable:
            lines.append(f"## Unstable Areas")
            for k, v in self.unstable.items():
                lines.append(f"- **{k}**: {v}")
            lines.append(f"")

        if self.future_work:
            lines.append(f"## Future Work Likely")
            for k, v in self.future_work.items():
                if isinstance(v, list):
                    lines.append(f"- **{k}**:")
                    for item in v[:10]:
                        lines.append(f"  - {item}")
                else:
                    lines.append(f"- **{k}**: {v}")
            lines.append(f"")

        if self.evidence_links:
            lines.append(f"## Evidence Links ({len(self.evidence_links)})")
            for e in self.evidence_links[:10]:
                line_info = f":{e.line_start}" if e.line_start else ""
                lines.append(f"- `{e.path}{line_info}` ({e.type})")
            if len(self.evidence_links) > 10:
                lines.append(f"  ... and {len(self.evidence_links) - 10} more")
            lines.append(f"")

        lines.append(f"## Confidence by Section")
        for section, score in sorted(self.confidence.per_section.items()):
            bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
            lines.append(f"- {section}: {bar} {score:.0%}")
        lines.append(f"")

        return "\n".join(lines)


class SelfDescriptionSchema:
    @staticmethod
    def validate(desc: SelfDescription) -> List[str]:
        errors = []
        if not desc.repo_path:
            errors.append("Missing repo_path")
        if not desc.repo_name:
            errors.append("Missing repo_name")
        if not desc.repo_hash:
            errors.append("Missing repo_hash")
        if desc.schema_version != "0.1.0":
            errors.append(f"Unsupported schema version: {desc.schema_version}")
        if not desc.identity:
            errors.append("Identity section is empty")
        return errors

    @staticmethod
    def upgrade(desc: SelfDescription, target_version: str) -> SelfDescription:
        current = desc.schema_version
        if current == target_version:
            return desc
        return desc


class SelfDescriptionGenerator:
    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = Path(repo_path).resolve() if repo_path else Path.cwd().resolve()
        self._git_available = (self.repo_path / ".git").is_dir()

    def generate(self) -> SelfDescription:
        desc = SelfDescription(
            repo_path=str(self.repo_path),
            repo_name=self.repo_path.name,
            repo_hash=self._compute_hash(),
        )

        desc.identity = self._build_identity()
        desc.structure = self._build_structure()
        desc.recent_changes = self._build_recent_changes()
        desc.invariants = self._build_invariants()
        desc.risks = self._build_risks()
        desc.unstable = self._build_unstable_areas()
        desc.future_work = self._build_future_work()
        desc.evidence_links = self._build_evidence_links()
        desc.confidence = self._compute_confidence(desc)
        desc.drift_warnings = self._detect_drift(desc)
        desc.update_history.append(
            f"Generated at {desc.generated_at} (hash: {desc.repo_hash})"
        )

        return desc

    def _compute_hash(self) -> str:
        path_str = str(self.repo_path)
        return hashlib.sha256(path_str.encode()).hexdigest()[:16]

    def _build_identity(self) -> Dict[str, Any]:
        identity = {
            "name": self.repo_path.name,
            "path": str(self.repo_path),
        }

        pyproject = self.repo_path / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text()
            m = re.search(r'name\s*=\s*"([^"]+)"', content)
            if m:
                identity["package_name"] = m.group(1)
            m = re.search(r'version\s*=\s*"([^"]+)"', content)
            if m:
                identity["version"] = m.group(1)
            m = re.search(r'description\s*=\s*"([^"]+)"', content)
            if m:
                identity["description"] = m.group(1)
            m = re.search(r'requires-python\s*=\s*">=([^"]+)"', content)
            if m:
                identity["python_version"] = m.group(1)

        package_json = self.repo_path / "package.json"
        if package_json.exists() and "package_name" not in identity:
            try:
                data = json.loads(package_json.read_text())
                identity["package_name"] = data.get("name", identity.get("package_name", "unknown"))
                identity["version"] = data.get("version", identity.get("version", "unknown"))
                if "description" in data and "description" not in identity:
                    identity["description"] = data["description"]
            except (json.JSONDecodeError, Exception):
                pass

        identity["git_available"] = self._git_available

        if self._git_available:
            try:
                result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    capture_output=True, text=True, cwd=self.repo_path, timeout=5,
                )
                if result.returncode == 0:
                    identity["remote"] = result.stdout.strip()
            except Exception:
                pass

        return identity

    def _build_structure(self) -> Dict[str, Any]:
        structure: Dict[str, Any] = {}
        all_files = list(self.repo_path.rglob("*"))
        all_dirs = [d for d in all_files if d.is_dir()]
        all_files_only = [f for f in all_files if f.is_file()]

        structure["file_count"] = len(all_files_only)
        structure["dir_count"] = len(all_dirs)

        total_lines = 0
        for f in all_files_only:
            try:
                total_lines += sum(1 for _ in open(f, "rb"))
            except Exception:
                pass
        structure["total_lines"] = total_lines

        ext_map: Dict[str, int] = {}
        for f in all_files_only:
            ext = f.suffix.lower()
            if ext:
                ext_map[ext] = ext_map.get(ext, 0) + 1
        structure["extensions"] = dict(sorted(ext_map.items(), key=lambda x: -x[1])[:15])

        top_dirs = []
        for d in all_dirs:
            if d.parent == self.repo_path and not d.name.startswith("."):
                top_dirs.append(d.name)
        structure["top_level_dirs"] = top_dirs

        source_indicators = ["src", "lib", "app"]
        source_dirs = [d for d in top_dirs if d in source_indicators]
        structure["source_directories"] = source_dirs

        test_files = [f for f in all_files_only if "test" in f.name.lower() or "spec" in f.name.lower()]
        structure["test_file_count"] = len(test_files)
        structure["has_tests"] = len(test_files) > 0

        doc_files = [f for f in all_files_only if f.suffix.lower() in (".md", ".rst", ".txt")]
        structure["doc_file_count"] = len(doc_files)
        structure["has_docs"] = len(doc_files) > 0

        readme = self.repo_path / "README.md"
        structure["has_readme"] = readme.exists()

        if source_dirs:
            modules = []
            for sd in source_dirs:
                src_path = self.repo_path / sd
                modules.extend([
                    str(p.relative_to(self.repo_path))
                    for p in sorted(src_path.rglob("*.py"))
                    if p.is_file() and p.name != "__init__.py"
                ])
            structure["modules"] = modules[:30]

        languages = {
            ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
            ".go": "Go", ".rs": "Rust", ".java": "Java", ".rb": "Ruby",
            ".c": "C", ".cpp": "C++", ".cs": "C#", ".swift": "Swift",
        }
        lang_count: Dict[str, int] = {}
        for ext, lang in languages.items():
            count = ext_map.get(ext, 0)
            if count > 0:
                lang_count[lang] = count
        structure["languages"] = dict(sorted(lang_count.items(), key=lambda x: -x[1]))

        return structure

    def _build_recent_changes(self) -> Dict[str, Any]:
        changes: Dict[str, Any] = {}
        if not self._git_available:
            changes["note"] = "Git not available"
            return changes

        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-30"],
                capture_output=True, text=True, cwd=self.repo_path, timeout=10,
            )
            commits = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
            changes["recent_commits"] = commits[:20]
            changes["commit_count_30_days"] = len(commits)

            result2 = subprocess.run(
                ["git", "log", "--format=%an", "-30"],
                capture_output=True, text=True, cwd=self.repo_path, timeout=10,
            )
            authors = [l.strip() for l in result2.stdout.strip().split("\n") if l.strip()]
            author_counts: Dict[str, int] = {}
            for a in authors:
                author_counts[a] = author_counts.get(a, 0) + 1
            changes["authors"] = dict(sorted(author_counts.items(), key=lambda x: -x[1]))

            result3 = subprocess.run(
                ["git", "diff", "--shortstat", "@{1 week ago}", "HEAD"],
                capture_output=True, text=True, cwd=self.repo_path, timeout=10,
            )
            diff_stat = result3.stdout.strip()
            if diff_stat:
                changes["last_week_changes"] = diff_stat

            result4 = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                capture_output=True, text=True, cwd=self.repo_path, timeout=10,
            )
            if result4.returncode == 0:
                changes["total_commits"] = int(result4.stdout.strip())

            result5 = subprocess.run(
                ["git", "log", "--diff-filter=A", "--name-only", "--pretty=format:", "-10"],
                capture_output=True, text=True, cwd=self.repo_path, timeout=10,
            )
            new_files = [l.strip() for l in result5.stdout.strip().split("\n") if l.strip() and not l.startswith("--")]
            if new_files:
                changes["recently_added_files"] = new_files[:10]

            result6 = subprocess.run(
                ["git", "log", "--diff-filter=D", "--name-only", "--pretty=format:", "-10"],
                capture_output=True, text=True, cwd=self.repo_path, timeout=10,
            )
            deleted_files = [l.strip() for l in result6.stdout.strip().split("\n") if l.strip() and not l.startswith("--")]
            if deleted_files:
                changes["recently_deleted_files"] = deleted_files[:10]

        except Exception as e:
            changes["error"] = str(e)

        return changes

    def _build_invariants(self) -> Dict[str, Any]:
        invariants: Dict[str, Any] = {"invariants": []}

        try:
            from ..discovery import InvariantInferenceEngine
            engine = InvariantInferenceEngine()
            inv_set = engine.discover(self.repo_path)
            for inv in inv_set._invariants.values():
                invariants["invariants"].append({
                    "name": inv.name,
                    "description": inv.description,
                    "severity": inv.severity.value if hasattr(inv.severity, 'value') else str(inv.severity),
                    "confidence": inv.confidence,
                    "source": inv.source,
                })
            invariants["total"] = len(inv_set._invariants)
        except ImportError:
            invariants["note"] = "InvariantDiscovery unavailable"

        return invariants

    def _build_risks(self) -> Dict[str, Any]:
        risks: Dict[str, Any] = {}

        try:
            from ..doctor import RepoDoctor
            doctor = RepoDoctor()
            diagnosis = doctor.diagnose(self.repo_path)
            risks["risky_files"] = [
                {"path": f.path, "score": f.risk_score, "reasons": f.reasons}
                for f in diagnosis.risky_files[:10]
            ]
            risks["hotspots"] = [
                {"subsystem": h.subsystem, "risk_score": h.risk_score, "file_count": h.file_count}
                for h in diagnosis.architectural_hotspots
            ]
            risks["fragility_score"] = diagnosis.research.graph_quality_score
        except ImportError:
            risks["note"] = "RepoDoctor unavailable"

        large_files = []
        for f in sorted(self.repo_path.rglob("*")):
            if not f.is_file() or ".git" in f.parts:
                continue
            try:
                size = f.stat().st_size
                if size > 50000:
                    large_files.append({"path": str(f.relative_to(self.repo_path)), "size_bytes": size})
            except Exception:
                pass
        if large_files:
            risks["large_files"] = sorted(large_files, key=lambda x: -x["size_bytes"])[:10]

        return risks

    def _build_unstable_areas(self) -> Dict[str, Any]:
        unstable: Dict[str, Any] = {}
        if not self._git_available:
            unstable["note"] = "Git not available"
            return unstable

        try:
            result = subprocess.run(
                ["git", "log", "--name-only", "--pretty=format:", "-100"],
                capture_output=True, text=True, cwd=self.repo_path, timeout=10,
            )
            file_changes: Dict[str, int] = {}
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if line and not line.startswith("--"):
                    file_changes[line] = file_changes.get(line, 0) + 1

            high_churn = [(f, c) for f, c in sorted(file_changes.items(), key=lambda x: -x[1]) if c >= 5]
            if high_churn:
                unstable["high_churn_files"] = [{"path": f, "changes": c} for f, c in high_churn[:10]]

            result2 = subprocess.run(
                ["git", "log", "--format=%H", "-1", "--since=30.days"],
                capture_output=True, text=True, cwd=self.repo_path, timeout=5,
            )
            active_recently = bool(result2.stdout.strip())
            unstable["actively_developed"] = active_recently

            if high_churn:
                unstable["instability_score"] = min(1.0, len(high_churn) / 10)
            else:
                unstable["instability_score"] = 0.0

        except Exception as e:
            unstable["error"] = str(e)

        return unstable

    def _build_future_work(self) -> Dict[str, Any]:
        future: Dict[str, Any] = {}

        all_files_only = [f for f in self.repo_path.rglob("*") if f.is_file()]
        todo_count = 0
        fixme_count = 0
        hack_count = 0
        todo_items = []

        for f in all_files_only:
            if f.suffix.lower() not in (".py", ".js", ".ts", ".go", ".rs", ".java", ".md"):
                continue
            try:
                content = f.read_text(errors="ignore")
                for i, line in enumerate(content.split("\n"), 1):
                    if "TODO" in line:
                        todo_count += 1
                        if len(todo_items) < 15:
                            todo_items.append(f"{f.relative_to(self.repo_path)}:{i}: {line.strip()[:80]}")
                    if "FIXME" in line:
                        fixme_count += 1
            except Exception:
                pass

        future["todo_count"] = todo_count
        future["fixme_count"] = fixme_count
        if todo_items:
            future["todo_items"] = todo_items

        if self._git_available:
            try:
                result = subprocess.run(
                    ["git", "log", "--oneline", "-1", "--grep=TODO"],
                    capture_output=True, text=True, cwd=self.repo_path, timeout=5,
                )
                future["todo_related_commits"] = bool(result.stdout.strip())

                result2 = subprocess.run(
                    ["git", "branch", "-a"],
                    capture_output=True, text=True, cwd=self.repo_path, timeout=5,
                )
                branches = [b.strip() for b in result2.stdout.strip().split("\n") if b.strip()]
                future["branches"] = len(branches)

                feature_branches = [b for b in branches if "feature" in b.lower() or "feat" in b.lower()]
                if feature_branches:
                    future["feature_branches"] = feature_branches[:5]
            except Exception:
                pass

        return future

    def _build_evidence_links(self) -> List[EvidenceLink]:
        links = []

        identity_files = [
            self.repo_path / "pyproject.toml",
            self.repo_path / "package.json",
            self.repo_path / "Cargo.toml",
            self.repo_path / "README.md",
        ]
        for f in identity_files:
            if f.exists():
                links.append(EvidenceLink(
                    path=str(f.relative_to(self.repo_path)),
                    type="identity",
                ))

        if self._git_available:
            for f in [self.repo_path / ".git" / "HEAD"]:
                if f.exists():
                    links.append(EvidenceLink(
                        path=str(f),
                        type="git",
                    ))

        source_dirs = [d for d in (self.repo_path / "src").iterdir() if d.is_dir()] if (self.repo_path / "src").exists() else []
        source_dirs += [d for d in (self.repo_path / "lib").iterdir() if d.is_dir()] if (self.repo_path / "lib").exists() else []
        for d in source_dirs[:10]:
            py_files = list(d.rglob("*.py"))[:3]
            for pf in py_files:
                links.append(EvidenceLink(
                    path=str(pf.relative_to(self.repo_path)),
                    type="source",
                ))

        return links[:30]

    def _compute_confidence(self, desc: SelfDescription) -> ConfidenceScore:
        confidence = ConfidenceScore()

        evidence_count = len(desc.evidence_links)
        confidence.evidence_count = evidence_count

        staleness = 0
        try:
            generated = datetime.fromisoformat(desc.generated_at)
            staleness = (datetime.now(timezone.utc) - generated).days
        except Exception:
            pass
        confidence.staleness_days = staleness

        identity_conf = min(0.9, 0.3 + 0.1 * len(desc.identity))
        structure_conf = min(0.9, 0.4 + 0.05 * min(evidence_count, 10))
        changes_conf = 0.3 if not desc.recent_changes.get("note") else 0.1
        invariants_conf = 0.5 + 0.1 * min(len(desc.invariants.get("invariants", [])), 5)
        risks_conf = 0.6 + 0.05 * min(len(desc.risks.get("risky_files", [])), 5)
        unstable_conf = 0.5 + 0.1 * desc.unstable.get("instability_score", 0)
        future_conf = 0.3 + 0.05 * min(desc.future_work.get("todo_count", 0), 10)

        confidence.per_section = {
            "identity": min(identity_conf, 1.0),
            "structure": min(structure_conf, 1.0),
            "recent_changes": min(changes_conf, 1.0),
            "invariants": min(invariants_conf, 1.0),
            "risks": min(risks_conf, 1.0),
            "unstable": min(unstable_conf, 1.0),
            "future_work": min(future_conf, 1.0),
        }

        staleness_penalty = min(staleness / 30, 0.5)
        confidence.overall = max(
            0.0,
            sum(confidence.per_section.values()) / len(confidence.per_section) - staleness_penalty
        )

        return confidence

    def _detect_drift(self, desc: SelfDescription) -> List[DriftWarning]:
        warnings: List[DriftWarning] = []

        if not self._git_available:
            return warnings

        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-1", "--since=7.days"],
                capture_output=True, text=True, cwd=self.repo_path, timeout=5,
            )
            no_recent_activity = not result.stdout.strip()

            if no_recent_activity and len(desc.recent_changes.get("recent_commits", [])) < 3:
                pass

            result2 = subprocess.run(
                ["git", "log", "--oneline", "-1"],
                capture_output=True, text=True, cwd=self.repo_path, timeout=5,
            )
            if result2.stdout.strip():
                last_commit = result2.stdout.strip()
                try:
                    result3 = subprocess.run(
                        ["git", "log", "-1", "--format=%ct"],
                        capture_output=True, text=True, cwd=self.repo_path, timeout=5,
                    )
                    if result3.stdout.strip():
                        import time
                        last_ts = int(result3.stdout.strip())
                        days_since = (time.time() - last_ts) / 86400
                        if days_since > 30:
                            warnings.append(DriftWarning(
                                section="recent_changes",
                                description=f"No commits in {int(days_since)} days",
                                severity=DriftSeverity.MEDIUM if days_since < 90 else DriftSeverity.HIGH,
                                metric="days_since_last_commit",
                                old_value=None,
                                new_value=int(days_since),
                                threshold=30,
                                evidence=[f"Last commit: {last_commit}"],
                            ))
                except Exception:
                    pass

        except Exception:
            pass

        if desc.confidence.staleness_days > 7:
            warnings.append(DriftWarning(
                section="metadata",
                description=f"Self-description is {desc.confidence.staleness_days} days old",
                severity=DriftSeverity.LOW if desc.confidence.staleness_days < 30 else DriftSeverity.MEDIUM,
                metric="staleness_days",
                old_value=None,
                new_value=desc.confidence.staleness_days,
                threshold=7,
            ))

        large_file_risks = desc.risks.get("large_files", [])
        if len(large_file_risks) > 5:
            warnings.append(DriftWarning(
                section="risks",
                description=f"{len(large_file_risks)} large files detected (>50KB)",
                severity=DriftSeverity.LOW,
                metric="large_file_count",
                old_value=None,
                new_value=len(large_file_risks),
                threshold=5,
            ))

        return warnings


class SelfDescriptionUpdateTrigger:
    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = Path(repo_path).resolve() if repo_path else Path.cwd().resolve()
        self._lyme_dir = self.repo_path / ".lyme"
        self._desc_path = self._lyme_dir / "self-description.json"

    def should_update(self) -> Tuple[bool, str]:
        if not self._desc_path.exists():
            return True, "No existing self-description"

        try:
            data = json.loads(self._desc_path.read_text())
            generated = datetime.fromisoformat(data.get("generated_at", "2000-01-01"))
            days_old = (datetime.now(timezone.utc) - generated).days

            if days_old > 7:
                return True, f"Description is {days_old} days old (threshold: 7)"

            repo_hash = data.get("repo_hash", "")
            current_hash = SelfDescriptionGenerator(self.repo_path)._compute_hash()
            if repo_hash != current_hash:
                return True, "Repo path changed"

            git_dir = self.repo_path / ".git"
            if git_dir.is_dir():
                result = subprocess.run(
                    ["git", "log", "--oneline", "-1", f"--since={days_old}.days"],
                    capture_output=True, text=True, cwd=self.repo_path, timeout=5,
                )
                if result.stdout.strip():
                    return True, "New commits since last description"

        except (json.JSONDecodeError, KeyError, Exception):
            return True, "Corrupted or unreadable description"

        return False, "Up to date"

    def update(self) -> Optional[SelfDescription]:
        should, reason = self.should_update()
        if not should:
            return None

        generator = SelfDescriptionGenerator(self.repo_path)
        desc = generator.generate()
        self._lyme_dir.mkdir(parents=True, exist_ok=True)
        self._desc_path.write_text(json.dumps(desc.to_dict(), indent=2, default=str))
        return desc

    def load(self) -> Optional[SelfDescription]:
        if not self._desc_path.exists():
            return None
        try:
            data = json.loads(self._desc_path.read_text())
            desc = SelfDescription(
                repo_path=data.get("repo_path", ""),
                repo_name=data.get("repo_name", ""),
                repo_hash=data.get("repo_hash", ""),
                generated_at=data.get("generated_at", ""),
            )
            desc.identity = data.get("identity", {})
            desc.structure = data.get("structure", {})
            desc.recent_changes = data.get("recent_changes", {})
            desc.invariants = data.get("invariants", {})
            desc.risks = data.get("risks", {})
            desc.unstable = data.get("unstable", {})
            desc.future_work = data.get("future_work", {})
            return desc
        except (json.JSONDecodeError, KeyError, Exception):
            return None
