"""Phase 8 — Launch Candidate Smoke Tests."""
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent


def run(cmd: str, timeout: int = 30) -> tuple[int, str]:
    result = subprocess.run(
        cmd.split(), capture_output=True, text=True, timeout=timeout, cwd=str(REPO),
    )
    return result.returncode, result.stdout + result.stderr


class TestPhase8Launch:
    """Smoke tests verifying Phase 8 features work."""

    def test_version(self):
        rc, out = run(f"{sys.executable} -m lyme --version")
        assert rc == 0, f"version failed: {out}"
        assert "1.0.0-rc1" in out

    def test_doctor_help(self):
        rc, out = run(f"{sys.executable} -m lyme doctor --help")
        assert rc == 0

    def test_ask_help(self):
        rc, out = run(f"{sys.executable} -m lyme ask --help")
        assert rc == 0

    def test_dashboard(self):
        rc, out = run(f"{sys.executable} -m lyme dashboard", timeout=30)
        assert rc == 0, f"dashboard failed: {out[:200]}"

    def test_start(self):
        rc, out = run(f"{sys.executable} -m lyme start", timeout=30)
        assert rc == 0, f"start failed: {out[:200]}"

    def test_inbox(self):
        rc, out = run(f"{sys.executable} -m lyme inbox", timeout=30)
        assert rc == 0, f"inbox failed: {out[:200]}"

    def test_diff_explain(self):
        rc, out = run(f"{sys.executable} -m lyme diff-explain", timeout=30)
        assert rc == 0, f"diff-explain failed: {out[:200]}"

    def test_branch_review(self):
        rc, out = run(f"{sys.executable} -m lyme branch-review", timeout=30)
        assert rc == 0, f"branch-review failed: {out[:200]}"

    def test_dogfood_help(self):
        rc, out = run(f"{sys.executable} -m lyme dogfood --help")
        assert rc == 0

    def test_metrics_audit_provenance(self):
        rc, out = run(f"{sys.executable} -m lyme metrics-audit provenance")
        assert rc == 0, f"metrics-audit failed: {out[:200]}"

    def test_metrics_audit_credibility(self):
        rc, out = run(f"{sys.executable} -m lyme metrics-audit credibility")
        assert rc == 0, f"credibility failed: {out[:200]}"

    def test_pricing_plans(self):
        rc, out = run(f"{sys.executable} -m lyme pricing plans")
        assert rc == 0, f"pricing failed: {out[:200]}"

    def test_pricing_check(self):
        rc, out = run(f"{sys.executable} -m lyme pricing check dashboard")
        assert rc == 0
        assert "allowed" in out.lower()

    def test_trust_defaults(self):
        rc, out = run(f"{sys.executable} -m lyme trust defaults")
        assert rc == 0, f"trust defaults failed: {out[:200]}"

    def test_trust_security(self):
        rc, out = run(f"{sys.executable} -m lyme trust security")
        assert rc == 0

    def test_beta_status(self):
        rc, out = run(f"{sys.executable} -m lyme beta status")
        assert rc == 0, f"beta status failed: {out[:200]}"

    def test_beta_weekly(self):
        rc, out = run(f"{sys.executable} -m lyme beta weekly")
        assert rc == 0, f"beta weekly failed: {out[:200]}"

    def test_continue(self):
        rc, out = run(f"{sys.executable} -m lyme continue")
        assert rc == 0

    def test_watch(self):
        rc, out = run(f"{sys.executable} -m lyme watch")
        assert rc == 0

    def test_trust_risk(self):
        rc, out = run(f"{sys.executable} -m lyme trust risk")
        assert rc == 0
