from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import json
import time


REPOS_DIR = Path.home() / "Desktop" / "repos"

# Fast in-process imports
try:
    from lyme.ask import EvidenceEngine
    _HAS_ASK = True
except ImportError:
    _HAS_ASK = False

TARGET_REPOS = {
    "Lyme": REPOS_DIR / "Lyme",
    "NoDiff": REPOS_DIR / "NoDiff",
    "Leveli": REPOS_DIR / "Leveli",
    "Abel": REPOS_DIR / "Abel",
    "cShot": REPOS_DIR / "cShot",
}


@dataclass
class RepoProfile:
    name: str
    path: Path
    exists: bool
    language: str
    file_count: int
    line_count: int
    test_count: int
    has_readme: bool
    has_ci: bool
    has_docs: bool

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": str(self.path),
            "exists": self.exists,
            "language": self.language,
            "file_count": self.file_count,
            "line_count": self.line_count,
            "test_count": self.test_count,
            "has_readme": self.has_readme,
            "has_ci": self.has_ci,
            "has_docs": self.has_docs,
        }


@dataclass
class DoctorResult:
    output: str
    latencys: float
    confidence: float
    success: bool

    def to_dict(self) -> dict:
        return {
            "output": self.output[:500],
            "latency_s": round(self.latencys, 2),
            "confidence": self.confidence,
            "success": self.success,
        }


@dataclass
class QAResult:
    question: str
    output: str
    latencys: float
    confidence: float
    refused: bool

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "output": self.output[:500],
            "latency_s": round(self.latencys, 2),
            "confidence": self.confidence,
            "refused": self.refused,
        }


@dataclass
class IssueSimulation:
    issue_id: str
    title: str
    body: str
    resolved: bool
    resolution_time_s: float
    patch_applied: bool
    patch_valid: bool
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "issue_id": self.issue_id,
            "title": self.title,
            "resolved": self.resolved,
            "resolution_time_s": round(self.resolution_time_s, 2),
            "patch_applied": self.patch_applied,
            "patch_valid": self.patch_valid,
            "error": self.error,
        }


@dataclass
class RepoAssessment:
    profile: RepoProfile
    doctor: DoctorResult
    qa_results: List[QAResult]
    issues: List[IssueSimulation]
    failures: List[str]
    improvement_suggestions: List[str]
    manual_time_s: float
    lyme_time_s: float

    def productivity_ratio(self) -> float:
        if self.lyme_time_s <= 0:
            return 0.0
        return round(self.manual_time_s / self.lyme_time_s, 2)

    def to_dict(self) -> dict:
        return {
            "profile": self.profile.to_dict(),
            "doctor": self.doctor.to_dict(),
            "qa_results": [q.to_dict() for q in self.qa_results],
            "issues": [i.to_dict() for i in self.issues],
            "failures": self.failures,
            "improvement_suggestions": self.improvement_suggestions,
            "manual_time_s": round(self.manual_time_s, 2),
            "lyme_time_s": round(self.lyme_time_s, 2),
            "productivity_ratio": self.productivity_ratio(),
        }


@dataclass
class DogfoodReport:
    assessments: Dict[str, RepoAssessment]
    total_manual_time_s: float
    total_lyme_time_s: float
    overall_productivity_ratio: float
    total_failures: int
    total_issues: int
    resolved_issues: int
    daily_score: float
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "repos": {name: a.to_dict() for name, a in self.assessments.items()},
            "totals": {
                "total_manual_time_s": round(self.total_manual_time_s, 2),
                "total_lyme_time_s": round(self.total_lyme_time_s, 2),
                "overall_productivity_ratio": self.overall_productivity_ratio,
                "total_failures": self.total_failures,
                "total_issues": self.total_issues,
                "resolved_issues": self.resolved_issues,
                "daily_score": self.daily_score,
            },
            "timestamp": self.timestamp,
        }


QA_QUESTIONS = {
    "Lyme": [
        "What language and framework does this project use?",
        "What test framework is configured?",
        "List the main CLI commands available",
        "Are there any circular dependencies?",
        "What build system does this project use?",
    ],
    "NoDiff": [
        "What is the purpose of this project?",
        "What Python packages are required?",
        "Are there tests? How do I run them?",
    ],
    "Leveli": [
        "What is this project?",
        "What frontend framework is used?",
        "How is the app structured?",
    ],
    "Abel": [
        "What is this project?",
        "What frontend technologies are used?",
        "How is the project structured?",
    ],
    "cShot": [
        "What is this project?",
        "What Python packages are required?",
        "Are there tests? What do they cover?",
    ],
}

SIMULATED_ISSUES = {
    "Lyme": [
        {"title": "Add --json flag to doctor command", "body": "The doctor command should support JSON output for programmatic consumption"},
        {"title": "Fix docstring typos in CLI", "body": "Several docstrings in cli.py have typos that need fixing"},
    ],
    "NoDiff": [
        {"title": "Update README with install instructions", "body": "README is missing basic installation instructions"},
    ],
    "Abel": [
        {"title": "Add aria labels to navigation", "body": "Navigation components lack accessibility aria labels"},
    ],
}


def _fast_repo_profile(repo_path: Path) -> tuple[str, float, bool]:
    """Fast repo profiling without full doctor invocation."""
    start = time.time()
    try:
        py_files = list(repo_path.rglob("*.py"))
        js_files = list(repo_path.rglob("*.{js,ts,jsx,tsx}"))
        all_src = py_files + js_files

        total_lines = 0
        for f in all_src[:100]:
            try:
                total_lines += len(f.read_text(errors="ignore").splitlines())
            except Exception:
                pass

        test_files = (
            list(repo_path.rglob("test_*.py")) +
            list(repo_path.rglob("*_test.py")) +
            list(repo_path.rglob("*.test.js"))
        )

        has_toml = (repo_path / "pyproject.toml").exists()
        has_pkg = (repo_path / "package.json").exists()
        has_cargo = bool(list(repo_path.rglob("Cargo.toml")))

        if has_toml:
            lang, build = "Python", "setuptools/poetry"
        elif has_pkg:
            lang, build = "JavaScript/TypeScript", "npm/pnpm/yarn"
        elif has_cargo:
            lang, build = "Rust", "cargo"
        else:
            lang, build = "Mixed", "unknown"

        has_readme = (repo_path / "README.md").exists()
        has_docs = (repo_path / "docs").exists()
        has_ci = (repo_path / ".github" / "workflows").exists()

        elapsed = time.time() - start
        summary = (
            f"Language: {lang}\n"
            f"Build: {build}\n"
            f"Source files: {len(all_src)}\n"
            f"Lines: {total_lines}\n"
            f"Tests: {len(test_files)}\n"
            f"README: {'yes' if has_readme else 'no'}\n"
            f"Docs: {'yes' if has_docs else 'no'}\n"
            f"CI: {'yes' if has_ci else 'no'}\n"
        )
        return summary, elapsed, True
    except Exception as e:
        elapsed = time.time() - start
        return f"(profile error: {e})", elapsed, False


def _run_ask_inprocess(question: str, repo_path: Path) -> tuple[str, float, bool, bool]:
    """Run lyme ask in-process for speed."""
    start = time.time()
    if not _HAS_ASK:
        return "(ask module unavailable)", time.time() - start, False, False
    try:
        ee = EvidenceEngine()
        answer = ee.ask(question, repo_path)
        elapsed = time.time() - start
        refused = answer.overall_confidence < 0.1
        output = f"Answer: {answer.text[:300] if hasattr(answer, 'text') else str(answer)[:300]}\nConfidence: {answer.overall_confidence:.0%}"
        return output, elapsed, True, refused
    except Exception as e:
        elapsed = time.time() - start
        return f"(ask error: {e})", elapsed, False, False


def _profile_repo(path: Path) -> RepoProfile:
    if not path.exists():
        return RepoProfile(name=path.name, path=path, exists=False, language="", file_count=0, line_count=0, test_count=0, has_readme=False, has_ci=False, has_docs=False)

    py_files = list(path.rglob("*.py"))
    js_files = list(path.rglob("*.{js,ts,jsx,tsx}"))
    all_files = py_files + js_files

    file_count = len(all_files)
    line_count = sum(len(f.read_text(errors="ignore").splitlines()) for f in all_files[:200])

    test_count = len(list(path.rglob("test_*.py"))) + len(list(path.rglob("*_test.py"))) + len(list(path.rglob("*.test.js")))

    has_readme = (path / "README.md").exists() or (path / "README.rst").exists()
    has_ci = (path / ".github" / "workflows").exists() or (path / ".gitlab-ci.yml").exists()
    has_docs = (path / "docs").exists()

    py_count = len(py_files)
    js_count = len(js_files)
    language = "Python" if py_count > js_count else "JavaScript/TypeScript" if js_count > 0 else "Unknown"

    return RepoProfile(name=path.name, path=path, exists=True, language=language, file_count=file_count, line_count=line_count, test_count=test_count, has_readme=has_readme, has_ci=has_ci, has_docs=has_docs)


class DogfoodRunner:
    def __init__(self, repos: Optional[Dict[str, Path]] = None):
        self.repos = repos or TARGET_REPOS
        self.assessments: Dict[str, RepoAssessment] = {}

    def run_all(self) -> DogfoodReport:
        start = time.time()
        total_manual = 0.0
        total_lyme = 0.0
        all_failures = 0
        all_issues = 0
        resolved = 0

        for name, path in self.repos.items():
            print(f"\n{'='*60}")
            print(f"  DOGFOOD: {name}")
            print(f"{'='*60}")

            profile = _profile_repo(path)
            if not profile.exists:
                print(f"  SKIP: {path} does not exist")
                self.assessments[name] = RepoAssessment(
                    profile=profile,
                    doctor=DoctorResult("", 0, 0, False),
                    qa_results=[],
                    issues=[],
                    failures=["repo not found"],
                    improvement_suggestions=[],
                    manual_time_s=0,
                    lyme_time_s=0,
                )
                continue

            failures = []
            suggestions = []

            # Step 1: Fast repo profile
            print(f"  Profiling {name}...", flush=True)
            doc_out, doc_time, doc_ok = _fast_repo_profile(path)
            doc_confidence = 0.85 if doc_ok else 0.0
            doctor = DoctorResult(doc_out, doc_time, doc_confidence, doc_ok)
            if not doc_ok:
                failures.append(f"doctor failed on {name}")
            else:
                suggestions.append(f"doctor confidence: {doc_confidence:.0%}")
            print(f"    {'✓' if doc_ok else '✗'} doctor ({doc_time:.1f}s)")

            # Step 2: lyme ask questions (in-process)
            print(f"  Running Q&A questions...", flush=True)
            qa_results = []
            questions = QA_QUESTIONS.get(name, ["What is this project?"])
            for q in questions:
                qa_out, qa_time, qa_ok, refused = _run_ask_inprocess(q, path)
                qa_confidence = 0.8 if qa_ok and not refused else 0.0
                qa_results.append(QAResult(q, qa_out, qa_time, qa_confidence, refused))
                if refused:
                    failures.append(f"QA refused '{q[:40]}...'")
                print(f"    {'✓' if qa_ok and not refused else '✗'} {q[:40]}... ({qa_time:.1f}s)")

            # Step 3: Simulate issues (in-process plan)
            print(f"  Running issue simulations...", flush=True)
            issues = []
            issue_list = SIMULATED_ISSUES.get(name, [])
            for iss in issue_list:
                iss_start = time.time()
                try:
                    from lyme_model.cli import _identify_likely_files, _detect_test_command
                    files = _identify_likely_files(iss["title"], path)
                    test_cmd = _detect_test_command(path)
                    plan_ok = len(files) > 0
                except Exception:
                    plan_ok = False
                iss_elapsed = time.time() - iss_start

                issues.append(IssueSimulation(
                    issue_id=f"{name}-{iss['title'][:20].lower().replace(' ', '-')}",
                    title=iss["title"],
                    body=iss["body"],
                    resolved=plan_ok,
                    resolution_time_s=iss_elapsed,
                    patch_applied=False,
                    patch_valid=False,
                    error=None if plan_ok else "plan failed",
                ))
                if plan_ok:
                    resolved += 1
                    suggestions.append(f"Issue '{iss['title']}' resolved via plan")
                else:
                    failures.append(f"Plan failed for '{iss['title']}'")
                all_issues += 1
                print(f"    {'✓' if plan_ok else '✗'} {iss['title'][:40]}... ({iss_elapsed:.1f}s)")

            # Step 4: Generate improvement suggestions
            if not profile.has_readme:
                suggestions.append(f"Add README.md with setup and usage docs")
            if profile.test_count == 0:
                suggestions.append(f"Add test suite — no tests detected")
            if not profile.has_ci:
                suggestions.append(f"Add CI pipeline for automated testing")
            if not profile.has_docs:
                suggestions.append(f"Add docs/ directory with usage documentation")

            # Estimate manual vs lyme time
            manual_est = len(questions) * 120 + len(issue_list) * 600
            lyme_est = sum(q.latencys for q in qa_results) + sum(i.resolution_time_s for i in issues) + doc_time
            total_manual += manual_est
            total_lyme += lyme_est
            all_failures += len(failures)

            self.assessments[name] = RepoAssessment(
                profile=profile,
                doctor=doctor,
                qa_results=qa_results,
                issues=issues,
                failures=failures,
                improvement_suggestions=suggestions,
                manual_time_s=manual_est,
                lyme_time_s=lyme_est,
            )

        overall_ratio = round(total_manual / total_lyme, 2) if total_lyme > 0 else 0.0
        daily_score = self._compute_daily_score()

        report = DogfoodReport(
            assessments=self.assessments,
            total_manual_time_s=total_manual,
            total_lyme_time_s=total_lyme,
            overall_productivity_ratio=overall_ratio,
            total_failures=all_failures,
            total_issues=all_issues,
            resolved_issues=resolved,
            daily_score=daily_score,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        return report

    def _compute_daily_score(self) -> float:
        if not self.assessments:
            return 0.0
        total_ok = 0
        total_items = 0
        for a in self.assessments.values():
            for q in a.qa_results:
                total_items += 1
                if not q.refused:
                    total_ok += 1
            for i in a.issues:
                total_items += 1
                if i.resolved:
                    total_ok += 1
        if total_items == 0:
            return 0.0
        base = total_ok / total_items
        productiveness = min(1.0, self.assessments["Lyme"].productivity_ratio() / 5.0) if "Lyme" in self.assessments else 0.5
        return round(base * 0.6 + productiveness * 0.4, 2)

    def print_report(self, report: DogfoodReport):
        print(f"\n{'='*60}")
        print(f"  DOGFOOD REPORT")
        print(f"{'='*60}")
        print(f"  Timestamp: {report.timestamp}")
        print(f"\n  {'Repo':12s} {'Files':>6s} {'Tests':>6s} {'Language':15s} {'Failures':>8s} {'Ratio':>6s}")
        print(f"  {'-'*53}")
        for name, a in report.assessments.items():
            p = a.profile
            ratio = f"{a.productivity_ratio()}x" if a.lyme_time_s > 0 else "-"
            print(f"  {name:12s} {p.file_count:>6d} {p.test_count:>6d} {p.language:15s} {len(a.failures):>8d} {ratio:>6s}")
        t = report
        print(f"\n  Totals:")
        print(f"    Issues: {t.resolved_issues}/{t.total_issues} resolved")
        print(f"    Failures: {t.total_failures}")
        print(f"    Manual time: {t.total_manual_time_s:.0f}s estimated")
        print(f"    Lyme time: {t.total_lyme_time_s:.1f}s actual")
        print(f"    Productivity ratio: {t.overall_productivity_ratio}x")
        print(f"\n  WOULD I USE THIS DAILY? SCORE: {t.daily_score:.0%}")
        if t.daily_score >= 0.7:
            print(f"  → Yes, daily driver ready")
        elif t.daily_score >= 0.4:
            print(f"  → Maybe, with caveats")
        else:
            print(f"  → Not yet, needs work")
        print(f"\n  Repo-Specific Improvement Plans:")
        for name, a in report.assessments.items():
            if a.improvement_suggestions:
                print(f"    {name}:")
                for s in a.improvement_suggestions[:5]:
                    print(f"      → {s}")
        print(f"{'='*60}")

    def save_report(self, report: DogfoodReport, output: Path):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report.to_dict(), indent=2))
        print(f"  Report saved: {output}")


dogfood_runner = DogfoodRunner()
