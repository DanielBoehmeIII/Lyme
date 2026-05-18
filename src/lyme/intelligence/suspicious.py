from __future__ import annotations
import json
import re
import subprocess
import time
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class CommitFinding:
    commit_hash: str
    author: str
    message: str
    finding_type: str
    severity: str
    description: str
    lines_changed: int = 0
    files_changed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "commit_hash": self.commit_hash[:12],
            "author": self.author,
            "message": self.message[:80],
            "finding_type": self.finding_type,
            "severity": self.severity,
            "description": self.description,
            "lines_changed": self.lines_changed,
            "files_changed": self.files_changed[:5],
        }


@dataclass
class SuspiciousReport:
    findings: List[CommitFinding] = field(default_factory=list)
    commits_analyzed: int = 0
    suspicious_count: int = 0
    blocked: int = 0
    large: int = 0
    keyword: int = 0
    untested: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "commits_analyzed": self.commits_analyzed,
            "suspicious_count": self.suspicious_count,
            "blocked": self.blocked,
            "large": self.large,
            "keyword": self.keyword,
            "untested": self.untested,
        }

    def to_markdown(self) -> str:
        if not self.findings:
            return "No suspicious commits detected."
        lines = [f"## Suspicious Commit Report\n"]
        lines.append(f"Analyzed {self.commits_analyzed} commits, found {self.suspicious_count} suspicious:\n")
        for f in sorted(self.findings, key=lambda x: x.lines_changed, reverse=True)[:10]:
            icon = "🔴" if f.severity == "critical" else "🟡"
            lines.append(f"{icon} `{f.commit_hash[:8]}` **{f.finding_type}**: {f.description}")
            lines.append(f"   - {f.author}: _{f.message[:100]}_")
            lines.append(f"   - {f.lines_changed} lines in {len(f.files_changed)} files")
            lines.append("")
        return "\n".join(lines)


class SuspiciousCommitDetector:
    SUSPICIOUS_KEYWORDS = [
        "TODO", "FIXME", "HACK", "XXX", "TEMP", "hacky", "workaround",
        "temporary", "quick fix", "do not merge", "WIP", "debug", "testing",
        "revert", "rollback", "fix later",
    ]

    BLOCKED_KEYWORDS = [
        "print(", "console.log(", "debugger", "logger.debug(", "logger.info(",
        "os.system(", "subprocess.call(", "eval(", "exec(",
    ]

    def __init__(self, repo_path: str = "."):
        self._repo = Path(repo_path).resolve()
        self._db_path = self._repo / ".lyme" / "intel" / "suspicious_db.json"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._history: Dict[str, CommitFinding] = {}
        self._load()

    def _load(self) -> None:
        if self._db_path.exists():
            try:
                data = json.loads(self._db_path.read_text())
                for h, d in data.items():
                    self._history[h] = CommitFinding(**d)
            except Exception:
                pass

    def _save(self) -> None:
        data = {f.commit_hash: f.to_dict() for f in self._history.values()}
        self._db_path.write_text(json.dumps(data, indent=2))

    def analyze(self, since_commits: int = 30) -> SuspiciousReport:
        report = SuspiciousReport()
        findings = []
        try:
            log = subprocess.run(
                ["git", "log", f"-{since_commits}", "--format=%H|%an|%s", "--stat"],
                capture_output=True, text=True, timeout=15,
                cwd=str(self._repo),
            )
            commits = self._parse_log(log.stdout)
            report.commits_analyzed = len(commits)

            for chash, author, msg, files_changed, lines_changed in commits:
                if chash in self._history:
                    continue

                # Check for large commits
                if lines_changed > 200:
                    findings.append(CommitFinding(
                        commit_hash=chash, author=author, message=msg,
                        finding_type="large_commit",
                        severity="warning",
                        description=f"Large commit: {lines_changed} lines changed",
                        lines_changed=lines_changed, files_changed=files_changed,
                    ))
                    report.large += 1

                # Check for suspicious keywords
                for kw in self.SUSPICIOUS_KEYWORDS:
                    if kw.lower() in msg.lower():
                        findings.append(CommitFinding(
                            commit_hash=chash, author=author, message=msg,
                            finding_type="suspicious_keyword",
                            severity="warning",
                            description=f"Contains '{kw}' in commit message",
                            lines_changed=lines_changed, files_changed=files_changed,
                        ))
                        report.keyword += 1
                        break

                # Check for blocked patterns in diff
                blocked_findings = self._check_diff_for_blocked(chash, author, msg, files_changed, lines_changed)
                findings.extend(blocked_findings)
                report.blocked += len(blocked_findings)

                # Check for untested code
                has_tests = any("test" in f.lower() for f in files_changed)
                has_source = any(not f.startswith("test") and f.endswith(".py") for f in files_changed)
                if has_source and not has_tests and lines_changed > 50:
                    findings.append(CommitFinding(
                        commit_hash=chash, author=author, message=msg,
                        finding_type="untested_code",
                        severity="info",
                        description=f"Source changed without tests ({lines_changed} lines)",
                        lines_changed=lines_changed, files_changed=files_changed,
                    ))
                    report.untested += 1

        except Exception:
            pass

        for f in findings:
            self._history[f.commit_hash] = f

        report.findings = findings
        report.suspicious_count = len(findings)
        self._save()
        return report

    def _parse_log(self, log_text: str) -> List[Tuple[str, str, str, List[str], int]]:
        commits = []
        current = None
        files = []
        total_lines = 0

        for line in log_text.splitlines():
            if not line.strip():
                continue
            if "|" in line and len(line.split("|")) == 3:
                if current:
                    commits.append((current[0], current[1], current[2], files, total_lines))
                parts = line.split("|")
                current = (parts[0].strip(), parts[1].strip(), parts[2].strip())
                files = []
                total_lines = 0
            elif current and "changed" in line:
                m = re.search(r"(\d+) insertion", line)
                if m:
                    total_lines += int(m.group(1))
                m = re.search(r"(\d+) deletion", line)
                if m:
                    total_lines += int(m.group(1))
                if ".py" in line or ".ts" in line or ".js" in line:
                    file_part = line.split("|")[0].strip()
                    if file_part:
                        files.append(file_part)

        if current:
            commits.append((current[0], current[1], current[2], files, total_lines))
        return commits

    def _check_diff_for_blocked(self, chash: str, author: str, msg: str,
                                 files_changed: List[str], lines_changed: int) -> List[CommitFinding]:
        findings = []
        try:
            diff = subprocess.run(
                ["git", "diff", f"{chash}^..{chash}",
                 "--", "*.py", "*.ts", "*.js"],
                capture_output=True, text=True, timeout=10,
                cwd=str(self._repo),
            )
            for kw in self.BLOCKED_KEYWORDS:
                if kw in diff.stdout:
                    findings.append(CommitFinding(
                        commit_hash=chash, author=author, message=msg,
                        finding_type="blocked_pattern",
                        severity="critical",
                        description=f"Contains '{kw}' in diff",
                        lines_changed=lines_changed, files_changed=files_changed,
                    ))
        except Exception:
            pass
        return findings

    def known_suspicious(self) -> List[CommitFinding]:
        return list(self._history.values())
