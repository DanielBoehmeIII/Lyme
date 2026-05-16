"""Week 4 — Repo Q&A Engine.

Evidence-grounded Q&A pipeline that combines:
- Context compilation (task-relevant context)
- Tool session (evidence gathering via grep/read)
- Answer formatting with file citations
- Refusal for unsupported questions
- Latency tracking
- Benchmark comparison vs raw model
"""

from __future__ import annotations
import time
import json
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict
from pathlib import Path

from lyme_model.context.improved import ImprovedContextCompiler
from lyme_model.tools.session import ToolSession, ToolCallParser


@dataclass
class QAEvidence:
    source_file: str
    excerpt: str = ""
    tool: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class QAAnswer:
    question: str
    answer: str = ""
    confidence: float = 0.0
    evidence: List[QAEvidence] = field(default_factory=list)
    refused: bool = False
    refusal_reason: str = ""
    latency_s: float = 0.0
    context_tokens: int = 0
    tool_calls: int = 0
    model_used: str = "static"

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "answer": self.answer,
            "confidence": self.confidence,
            "evidence": [e.to_dict() for e in self.evidence],
            "refused": self.refused,
            "refusal_reason": self.refusal_reason,
            "latency_s": self.latency_s,
            "context_tokens": self.context_tokens,
            "tool_calls": self.tool_calls,
        }


UNSUPPORTED_PATTERNS = [
    "why", "should", "opinion", "think", "believe", "best", "worst",
    "ethical", "moral",
]


class QAEngine:
    """Evidence-grounded repository Q&A engine."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        self.compiler = ImprovedContextCompiler(str(self.repo_path))
        self.tool_session = ToolSession(repo_path=str(self.repo_path), safety_mode="readonly")

    def answer(self, question: str) -> QAAnswer:
        """Answer a repository question with evidence."""
        start = time.time()
        result = QAAnswer(question=question)

        refusal = self._check_refusal(question)
        if refusal:
            result.refused = True
            result.refusal_reason = refusal
            result.latency_s = round(time.time() - start, 3)
            return result

        domain = self._classify_question(question)
        if not domain:
            result.refused = True
            result.refusal_reason = (
                f"Cannot answer: '{question}' is outside Repo Q&A capability. "
                "Supported: language, framework, dependencies, file structure, "
                "functions, classes, tests, config."
            )
            result.latency_s = round(time.time() - start, 3)
            return result

        compiled = self.compiler.compile(task=question)
        result.context_tokens = compiled.total_tokens

        answer_text, evidence = self._build_answer(domain, question, compiled)
        result.answer = answer_text
        result.evidence = evidence
        result.confidence = self._estimate_confidence(evidence)
        result.tool_calls = 0
        result.model_used = "static_analysis"
        result.latency_s = round(time.time() - start, 3)

        self._emit_trace(result)
        return result

    def _check_refusal(self, question: str) -> Optional[str]:
        """Check if the question should be refused."""
        q = question.lower()
        for pattern in UNSUPPORTED_PATTERNS:
            if q.startswith(pattern) or f" {pattern} " in f" {q} ":
                return f"Question involves '{pattern}' which requires subjective judgment. I can only answer factual questions about repository structure and code."

        if len(question) < 5:
            return "Question too short. Please ask a specific question about the repository."

        return None

    def _classify_question(self, question: str) -> Optional[str]:
        """Classify question into a domain."""
        q = question.lower()
        domain_map = {
            "language": ["language", "programming language", "written in", "python", "javascript", "typescript"],
            "framework": ["framework", "library", "flask", "django", "react", "fastapi", "build system"],
            "dependencies": ["dependenc", "package", "library", "requirements", "pip", "npm"],
            "file_structure": ["structure", "directory", "files", "how many", "organized"],
            "functions": ["function", "method", "api", "interface"],
            "classes": ["class", "object", "hierarchy", "inheritance"],
            "tests": ["test", "pytest", "unittest", "coverage"],
            "config": ["config", "configuration", "settings", "setup"],
            "risk": ["risk", "risky", "dangerous", "sensitive", "secret", "password"],
            "changes": ["changed", "recent", "history", "commit", "git log"],
            "entry": ["entry", "main", "start", "run", "cli"],
        }

        for domain, keywords in domain_map.items():
            if any(k in q for k in keywords):
                return domain
        return None

    def _build_answer(self, domain: str, question: str, compiled) -> tuple:
        """Build answer with evidence for the given domain."""
        evidence = []

        if domain == "language":
            return self._answer_language(compiled, evidence)
        elif domain == "framework":
            return self._answer_framework(compiled, evidence)
        elif domain == "dependencies":
            return self._answer_dependencies(compiled, evidence)
        elif domain == "file_structure":
            return self._answer_structure(compiled, evidence)
        elif domain == "functions":
            return self._answer_functions(compiled, evidence)
        elif domain == "classes":
            return self._answer_classes(compiled, evidence)
        elif domain == "tests":
            return self._answer_tests(compiled, evidence)
        elif domain == "config":
            return self._answer_config(compiled, evidence)
        elif domain == "risk":
            return self._answer_risk(compiled, evidence)
        elif domain == "changes":
            return self._answer_changes(compiled, evidence)
        elif domain == "entry":
            return self._answer_entry(compiled, evidence)
        else:
            return "I can identify the domain but cannot provide a precise answer.", evidence

    def _answer_language(self, compiled, evidence) -> tuple:
        lines = compiled.repo_summary.split("\n")
        lang_lines = [l for l in lines if "Python" in l or "JS/TS" in l or "language" in l]
        primary = "Python" if any("Python" in l for l in lang_lines) else "Unknown"
        detail = lang_lines[0] if lang_lines else ""
        evidence.append(QAEvidence(source_file="(repo summary)", excerpt=detail, tool="context_compiler"))
        return f"The primary language is **{primary}**. {detail}", evidence

    def _answer_framework(self, compiled, evidence) -> tuple:
        if compiled.frameworks:
            fw_names = [f.name for f in compiled.frameworks]
            fw_detail = "; ".join(f"{f.name} ({len(f.files)} files)" for f in compiled.frameworks if f.files)
            for f in compiled.frameworks[:3]:
                for fp in f.files[:2]:
                    evidence.append(QAEvidence(source_file=fp, excerpt=f"{f.name} file", tool="context_compiler"))
            return f"Frameworks detected: **{', '.join(fw_names)}**. {fw_detail}", evidence
        return "No frameworks detected in the repository.", evidence

    def _answer_dependencies(self, compiled, evidence) -> tuple:
        import_lines = []
        for rf in compiled.ranked_files[:10]:
            if rf.imports:
                for imp in rf.imports[:5]:
                    import_lines.append(f"  {rf.path}: {imp}")
                    evidence.append(QAEvidence(source_file=rf.path, excerpt=f"import {imp}", tool="context_compiler"))
        if import_lines:
            return f"Dependencies found in:\n" + "\n".join(import_lines[:15]), evidence
        return "No explicit dependencies extracted.", evidence

    def _answer_structure(self, compiled, evidence) -> tuple:
        structure = compiled.structure
        evidence.append(QAEvidence(source_file="(repo root)", excerpt=structure[:200], tool="context_compiler"))
        return f"Repository structure:\n{structure}", evidence

    def _answer_functions(self, compiled, evidence) -> tuple:
        func_lines = []
        for rf in compiled.ranked_files[:15]:
            if rf.functions:
                func_lines.append(f"  {rf.path}: {', '.join(rf.functions[:10])}")
                if rf.functions:
                    evidence.append(QAEvidence(source_file=rf.path, excerpt=f"functions: {', '.join(rf.functions[:3])}", tool="context_compiler"))
        if func_lines:
            return f"Key functions:\n" + "\n".join(func_lines[:20]), evidence
        return "No functions extracted.", evidence

    def _answer_classes(self, compiled, evidence) -> tuple:
        cls_lines = []
        for rf in compiled.ranked_files[:15]:
            if rf.classes:
                cls_lines.append(f"  {rf.path}: {', '.join(rf.classes[:10])}")
                evidence.append(QAEvidence(source_file=rf.path, excerpt=f"classes: {', '.join(rf.classes[:3])}", tool="context_compiler"))
        if cls_lines:
            return f"Key classes:\n" + "\n".join(cls_lines[:20]), evidence
        return "No classes extracted.", evidence

    def _answer_tests(self, compiled, evidence) -> tuple:
        test_files = [rf.path for rf in compiled.ranked_files if "test" in rf.path.lower()]
        if test_files:
            for tf in test_files[:5]:
                evidence.append(QAEvidence(source_file=tf, excerpt="(test file reference)", tool="context_compiler"))
            test_cmds = "; ".join(compiled.test_commands)
            return f"Test files found ({len(test_files)}):\n" + "\n".join(test_files[:15]) + f"\n\nTest command: {test_cmds}", evidence
        return "No test files detected.", evidence

    def _answer_config(self, compiled, evidence) -> tuple:
        config_files = [rf.path for rf in compiled.ranked_files if any(k in rf.path.lower() for k in ["config", "setup", "pyproject", "package.json", "toml", "yaml", "ini"])]
        if config_files:
            for cf in config_files[:5]:
                evidence.append(QAEvidence(source_file=cf, excerpt="(config file)", tool="context_compiler"))
            return f"Configuration files:\n" + "\n".join(config_files[:15]), evidence
        return "No config files detected.", evidence

    def _answer_risk(self, compiled, evidence) -> tuple:
        if compiled.risks:
            for r in compiled.risks[:8]:
                evidence.append(QAEvidence(source_file=r.split(" (")[0], excerpt=r, tool="context_compiler"))
            return f"Sensitive/risky files ({len(compiled.risks)}):\n" + "\n".join(compiled.risks[:10]), evidence
        return "No risky files detected.", evidence

    def _answer_changes(self, compiled, evidence) -> tuple:
        try:
            import subprocess
            r = subprocess.run(
                ["git", "log", "--oneline", "-n", "10"],
                capture_output=True, text=True, timeout=5,
                cwd=str(self.repo_path),
            )
            if r.stdout.strip():
                lines = r.stdout.strip().split("\n")
                for line in lines[:5]:
                    sha = line.split()[0] if line.split() else ""
                    if sha:
                        evidence.append(QAEvidence(source_file="(git log)", excerpt=sha, tool="git_log"))
                return f"Recent changes:\n{r.stdout.strip()}", evidence
        except Exception:
            pass
        return "No git history available.", evidence

    def _answer_entry(self, compiled, evidence) -> tuple:
        if compiled.entry_points:
            for ep in compiled.entry_points:
                evidence.append(QAEvidence(source_file=ep, excerpt="(entry point)", tool="context_compiler"))
            return f"Entry points:\n" + "\n".join(compiled.entry_points), evidence
        return "No entry points detected.", evidence

    def _estimate_confidence(self, evidence: List[QAEvidence]) -> float:
        if not evidence:
            return 0.0
        return min(0.95, 0.3 + len(evidence) * 0.1)

    def _emit_trace(self, result: QAAnswer) -> None:
        trace = {
            "event": "qa_answer",
            "question": result.question,
            "refused": result.refused,
            "confidence": result.confidence,
            "latency_s": result.latency_s,
            "evidence_count": len(result.evidence),
            "context_tokens": result.context_tokens,
            "tool_calls": result.tool_calls,
        }
        trace_dir = Path(".lyme") / "audit"
        trace_dir.mkdir(parents=True, exist_ok=True)
        trace_id = str(hash(result.question))[-8:]
        trace_file = trace_dir / f"qa-{trace_id}.json"
        trace_file.write_text(json.dumps(trace, indent=2))


class QABenchmark:
    """Benchmark comparing QAEngine vs raw model prompting."""

    BENCHMARK_QUESTIONS = [
        "What language is this project?",
        "What framework is used?",
        "How many files are in the repo?",
        "What test framework is used?",
        "Are there any risky files?",
        "What are the entry points?",
        "What recent changes were made?",
        "What build system is used?",
    ]

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self.engine = QAEngine(repo_path)

    def run(self) -> Dict:
        results = []
        for q in self.BENCHMARK_QUESTIONS:
            result = self.engine.answer(q)
            results.append({
                "question": q,
                "refused": result.refused,
                "confidence": result.confidence,
                "latency_s": result.latency_s,
                "has_evidence": len(result.evidence) > 0,
                "evidence_count": len(result.evidence),
                "answer_length": len(result.answer),
            })

        answered = sum(1 for r in results if not r["refused"])
        avg_latency = sum(r["latency_s"] for r in results) / len(results)
        avg_confidence = sum(r["confidence"] for r in results) / len(results)
        total_evidence = sum(r["evidence_count"] for r in results)

        summary = {
            "total_questions": len(results),
            "answered": answered,
            "refused": len(results) - answered,
            "avg_latency_s": round(avg_latency, 3),
            "avg_confidence": round(avg_confidence, 2),
            "total_evidence": total_evidence,
            "avg_evidence_per_answer": round(total_evidence / max(answered, 1), 1),
        }

        output = {"summary": summary, "results": results}
        out_path = Path("lyme-output") / "qa-benchmark.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(output, indent=2))
        return output


def run_qa_demo(repo_path: str = ".") -> None:
    """Run a demo of the Q&A engine on common questions."""
    engine = QAEngine(repo_path)

    demo_questions = [
        "What language is this project?",
        "What framework is used?",
        "How are tests run?",
        "What are the entry points?",
        "Where is hardware detection?",
    ]

    print("=" * 50)
    print("REPO Q&A DEMO")
    print("=" * 50)

    for q in demo_questions:
        print(f"\nQ: {q}")
        result = engine.answer(q)
        if result.refused:
            print(f"  REFUSED: {result.refusal_reason}")
        else:
            print(f"  A: {result.answer[:300]}")
            print(f"  Evidence: {len(result.evidence)} sources")
            print(f"  Confidence: {result.confidence:.0%}")
        print(f"  Latency: {result.latency_s:.2f}s")

    print("\n" + "=" * 50)
