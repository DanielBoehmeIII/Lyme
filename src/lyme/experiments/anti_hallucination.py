import re
import ast
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class EvidenceClaim:
    claim_text: str
    source_file: Optional[str] = None
    source_line: Optional[int] = None
    evidence_text: Optional[str] = None
    confidence: float = 0.0
    verified: bool = False
    contradiction: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "claim_text": self.claim_text,
            "source_file": self.source_file,
            "source_line": self.source_line,
            "evidence_text": self.evidence_text,
            "confidence": self.confidence,
            "verified": self.verified,
            "contradiction": self.contradiction,
        }


@dataclass
class VerificationReport:
    output_text: str = ""
    verified_claims: List[EvidenceClaim] = field(default_factory=list)
    rejected_claims: List[EvidenceClaim] = field(default_factory=list)
    uncertain_claims: List[EvidenceClaim] = field(default_factory=list)
    overall_confidence: float = 0.0

    @property
    def total_claims(self) -> int:
        return len(self.verified_claims) + len(self.rejected_claims) + len(self.uncertain_claims)

    @property
    def verification_rate(self) -> float:
        if self.total_claims == 0:
            return 0.0
        return len(self.verified_claims) / self.total_claims

    def to_dict(self) -> dict:
        return {
            "output_text": self.output_text,
            "verified_claims": [c.to_dict() for c in self.verified_claims],
            "rejected_claims": [c.to_dict() for c in self.rejected_claims],
            "uncertain_claims": [c.to_dict() for c in self.uncertain_claims],
            "overall_confidence": self.overall_confidence,
            "total_claims": self.total_claims,
            "verification_rate": self.verification_rate,
        }


CLAIM_PATTERNS = [
    r"(?:function|class|method|def)\s+(\w+)",
    r"(?:file|module)\s+(?:is|contains|defines|has)\s+(\w+)",
    r"(?:the|this)\s+code\s+(?:does|uses|calls|imports)\s+(\w+)",
    r"(?:line|lines?)\s+(\d+)",
    r"import\s+(\w+(?:\.\w+)*)",
    r"(?:raises?|throws?|returns?)\s+(\w+(?:Error|Exception)?)",
]


class AntiHallucinationProtocol:
    def __init__(self):
        self._claim_cache: dict = {}

    def extract_claims(self, output: str) -> List[EvidenceClaim]:
        claims = []
        seen = set()
        for pattern in CLAIM_PATTERNS:
            for match in re.finditer(pattern, output, re.IGNORECASE):
                claim_text = match.group(0).strip()
                if claim_text not in seen:
                    seen.add(claim_text)
                    claims.append(EvidenceClaim(claim_text=claim_text))
        return claims

    def verify_code_explanation(self, output: str, repo_path: str) -> VerificationReport:
        report = VerificationReport(output_text=output)
        claims = self.extract_claims(output)
        for claim in claims:
            result = self._verify_claim_in_codebase(claim, repo_path)
            if result.verified:
                report.verified_claims.append(result)
            else:
                contradiction = self._find_contradiction(claim, repo_path)
                if contradiction:
                    result.contradiction = contradiction
                    result.verified = False
                    report.rejected_claims.append(result)
                else:
                    report.uncertain_claims.append(result)
        report.overall_confidence = self._compute_confidence(report)
        return report

    def verify_bug_diagnosis(self, output: str, repo_path: str) -> VerificationReport:
        report = VerificationReport(output_text=output)
        claims = self.extract_claims(output)
        bug_claims = [c for c in claims if any(w in c.claim_text.lower() for w in
                      ("bug", "error", "fix", "wrong", "incorrect", "issue", "crash"))]
        for claim in bug_claims:
            result = self._verify_claim_in_codebase(claim, repo_path)
            evidence = self._check_for_error_patterns(claim, repo_path)
            if result.verified and evidence:
                result.evidence_text = evidence
                result.verified = True
                report.verified_claims.append(result)
            else:
                contradiction = self._find_contradiction(claim, repo_path)
                if contradiction:
                    result.contradiction = contradiction
                    result.verified = False
                    report.rejected_claims.append(result)
                else:
                    report.uncertain_claims.append(result)
        report.overall_confidence = self._compute_confidence(report)
        return report

    def verify_refactor_plan(self, output: str, repo_path: str) -> VerificationReport:
        report = VerificationReport(output_text=output)
        claims = self.extract_claims(output)
        for claim in claims:
            result = self._verify_claim_in_codebase(claim, repo_path)
            if result.verified:
                report.verified_claims.append(result)
            else:
                result.verified = False
                report.uncertain_claims.append(result)
        report.overall_confidence = self._compute_confidence(report)
        return report

    def verify_architecture_summary(self, output: str, repo_path: str) -> VerificationReport:
        report = VerificationReport(output_text=output)
        claims = self.extract_claims(output)
        arch_claims = [c for c in claims if any(w in c.claim_text.lower() for w
                       in ("module", "package", "class", "depends", "imports", "inherits"))]
        for claim in arch_claims:
            result = self._verify_claim_in_codebase(claim, repo_path)
            if result.verified:
                report.verified_claims.append(result)
            else:
                contradiction = self._find_contradiction(claim, repo_path)
                if contradiction:
                    result.contradiction = contradiction
                    result.verified = False
                    report.rejected_claims.append(result)
                else:
                    report.uncertain_claims.append(result)
        report.overall_confidence = self._compute_confidence(report)
        return report

    def _verify_claim_in_codebase(self, claim: EvidenceClaim, repo_path: str) -> EvidenceClaim:
        root = Path(repo_path)
        if not root.is_dir():
            claim.verified = False
            claim.confidence = 0.0
            return claim

        identifier = self._extract_identifier(claim.claim_text)
        if not identifier:
            claim.verified = False
            claim.confidence = 0.0
            return claim

        cache_key = (str(root), identifier)
        if cache_key in self._claim_cache:
            cached = self._claim_cache[cache_key]
            claim.verified = cached["verified"]
            claim.source_file = cached["source_file"]
            claim.source_line = cached["source_line"]
            claim.evidence_text = cached["evidence_text"]
            claim.confidence = cached["confidence"]
            return claim

        for py_file in root.rglob("*.py"):
            try:
                tree = ast.parse(py_file.read_text())
                for node in ast.walk(tree):
                    if self._matches_identifier(node, identifier):
                        line = getattr(node, "lineno", 0)
                        claim.verified = True
                        claim.source_file = str(py_file)
                        claim.source_line = line
                        claim.evidence_text = ast.get_source_segment(
                            py_file.read_text(), node
                        ) or identifier
                        claim.confidence = 0.95
                        self._claim_cache[cache_key] = {
                            "verified": True,
                            "source_file": claim.source_file,
                            "source_line": claim.source_line,
                            "evidence_text": claim.evidence_text,
                            "confidence": 0.95,
                        }
                        return claim
            except SyntaxError:
                continue

        grep_result = self._grep_codebase(identifier, root)
        if grep_result:
            file_path, line_num, line_text = grep_result
            claim.verified = True
            claim.source_file = file_path
            claim.source_line = line_num
            claim.evidence_text = line_text
            claim.confidence = 0.85
            self._claim_cache[cache_key] = {
                "verified": True,
                "source_file": file_path,
                "source_line": line_num,
                "evidence_text": line_text,
                "confidence": 0.85,
            }
            return claim

        claim.verified = False
        claim.confidence = 0.0
        self._claim_cache[cache_key] = {
            "verified": False, "source_file": None,
            "source_line": None, "evidence_text": None, "confidence": 0.0,
        }
        return claim

    def _extract_identifier(self, claim_text: str) -> Optional[str]:
        patterns = [
            r"(?:function|class|method|def)\s+(\w+)",
            r"(?:import\s+)(\w+)",
            r"(?:calls?|uses?|imports?)\s+(\w+)",
            r"(\w+(?:Error|Exception))",
        ]
        for pat in patterns:
            m = re.search(pat, claim_text, re.IGNORECASE)
            if m:
                return m.group(1)
        words = claim_text.split()
        for w in words:
            w_clean = w.strip(".,;:!?()[]{}\"'")
            if w_clean and w_clean[0].isupper() and not w_clean.isupper():
                return w_clean
        return None

    def _matches_identifier(self, node: ast.AST, identifier: str) -> bool:
        if isinstance(node, ast.FunctionDef) and node.name == identifier:
            return True
        if isinstance(node, ast.ClassDef) and node.name == identifier:
            return True
        if isinstance(node, ast.Name) and node.id == identifier:
            return True
        if isinstance(node, ast.Attribute) and node.attr == identifier:
            return True
        if isinstance(node, ast.Import) and any(
            alias.name == identifier or (alias.asname and alias.asname == identifier)
            for alias in node.names
        ):
            return True
        if isinstance(node, ast.ImportFrom) and any(
            alias.name == identifier or (alias.asname and alias.asname == identifier)
            for alias in node.names
        ):
            return True
        return False

    def _grep_codebase(self, identifier: str, root: Path) -> Optional[Tuple[str, int, str]]:
        for py_file in root.rglob("*.py"):
            try:
                lines = py_file.read_text().splitlines()
                for i, line in enumerate(lines, 1):
                    if identifier in line:
                        return (str(py_file), i, line.strip())
            except Exception:
                continue
        return None

    def _find_contradiction(self, claim: EvidenceClaim, repo_path: str) -> Optional[str]:
        identifier = self._extract_identifier(claim.claim_text)
        if not identifier:
            return None
        root = Path(repo_path)
        mismatch = re.search(r"(?:is|are|was|were)\s+(?:a|an|not\s+a|not\s+an)?\s*(\w+)",
                             claim.claim_text, re.IGNORECASE)
        if mismatch:
            claimed_type = mismatch.group(1).lower()
            for py_file in root.rglob("*.py"):
                try:
                    tree = ast.parse(py_file.read_text())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef) and node.name == identifier:
                            bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
                            if claimed_type not in [b.lower() for b in bases]:
                                return (f"Claim says {identifier} is {claimed_type}, "
                                        f"but its bases are {bases}")
                except SyntaxError:
                    continue
        return None

    def _check_for_error_patterns(self, claim: EvidenceClaim, repo_path: str) -> Optional[str]:
        identifier = self._extract_identifier(claim.claim_text)
        if not identifier:
            return None
        root = Path(repo_path)
        for py_file in root.rglob("*.py"):
            try:
                lines = py_file.read_text().splitlines()
                for i, line in enumerate(lines, 1):
                    if identifier in line and any(kw in line.lower()
                       for kw in ("raise", "except", "error", "exception", "try", "bug")):
                        return line.strip()
            except Exception:
                continue
        return None

    def _compute_confidence(self, report: VerificationReport) -> float:
        total = report.total_claims
        if total == 0:
            return 1.0
        weighted = (
            len(report.verified_claims) * 1.0
            + len(report.uncertain_claims) * 0.3
        )
        return weighted / total

    def refuse_invention(self, api_name: str, repo_path: str) -> bool:
        root = Path(repo_path)
        for py_file in root.rglob("*.py"):
            try:
                tree = ast.parse(py_file.read_text())
                for node in ast.walk(tree):
                    if self._matches_identifier(node, api_name):
                        return False
            except SyntaxError:
                continue
        return True

    def flag_uncertain(self, claim: EvidenceClaim) -> bool:
        return claim.confidence < 0.5 and not claim.verified

    def require_citation(self, claim: EvidenceClaim) -> bool:
        return not claim.source_file or not claim.source_line
