"""TrialJudge — pass/fail judgment for trial results.

Judges a trial by analyzing:
- setup success
- test results (before vs after)
- failures encountered
- files changed match expectations
- acceptance criteria coverage
"""

from __future__ import annotations
from typing import Optional

from .models import TrialResult, TrialStatus, Verdict, SeededTask


class TrialJudge:
    """Determine pass/fail/ambiguous verdict for a trial."""

    def judge(self, result: TrialResult, task: SeededTask) -> Verdict:
        if result.status == TrialStatus.ERROR:
            return Verdict.FAIL

        if result.status == TrialStatus.TIMEOUT:
            return Verdict.FAIL

        score = self.compute_score(result, task)
        if score >= 0.8:
            return Verdict.PASS
        elif score >= 0.4:
            return Verdict.AMBIGUOUS
        else:
            return Verdict.FAIL

    def compute_score(self, result: TrialResult, task: SeededTask) -> float:
        score = 0.0
        checks = 0

        ac_total = len(task.acceptance_criteria)
        ac_met = 0
        if ac_total > 0:
            for criterion in task.acceptance_criteria:
                if self._check_criterion(criterion, result):
                    ac_met += 1
            ac_score = ac_met / ac_total
            score += ac_score * 0.4
            checks += 0.4

        if result.final_diff:
            diff_lines = result.final_diff.strip().split("\n")
            meaningful_changes = sum(1 for l in diff_lines if l.startswith("+") or l.startswith("-"))
            has_changes = meaningful_changes > 0
            score += 0.2 if has_changes else 0.0
            checks += 0.2

        expected_files_found = sum(
            1 for exp in task.expected_files
            if any(exp in f for f in result.files_touched)
        )
        file_coverage = expected_files_found / max(len(task.expected_files), 1)
        score += file_coverage * 0.2
        checks += 0.2

        test_before = result.test_results.get("test_before", {})
        tests_exist = bool(test_before) and not test_before.get("skipped", False)
        if tests_exist:
            test_after = result.test_results.get("test_after", {})
            before_pass = test_before.get("passed", False)
            after_pass = test_after.get("passed", True) if test_after else True
            if before_pass and after_pass:
                score += 0.15
            elif not before_pass and after_pass:
                score += 0.1
            elif not before_pass:
                score += 0.05
            checks += 0.15

        no_crashes = len(result.failures) == 0
        score += 0.05 if no_crashes else 0.0
        checks += 0.05

        total = score / checks if checks > 0 else 0.0
        return round(min(total, 1.0), 4)

    def _check_criterion(self, criterion: str, result: TrialResult) -> bool:
        cl = criterion.lower()
        combined = " ".join([
            result.final_diff.lower(),
            " ".join(f.lower() for f in result.files_touched),
            " ".join(f.lower() for f in result.failures),
            str(result.test_results).lower(),
        ])
        key_phrases = self._extract_key_phrases(cl)
        if not key_phrases:
            return True
        return any(phrase in combined for phrase in key_phrases)

    def _extract_key_phrases(self, text: str) -> list[str]:
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                      "being", "have", "has", "had", "do", "does", "did",
                      "will", "would", "can", "could", "shall", "should",
                      "may", "might", "must", "to", "of", "in", "for", "on",
                      "with", "at", "by", "from", "as", "into", "through",
                      "this", "that", "these", "those", "it", "its", "still"}
        words = text.split()
        meaningful = [w.strip(".,!?()[]{}") for w in words if w.lower() not in stop_words and len(w) > 2]
        return meaningful if meaningful else [text]
