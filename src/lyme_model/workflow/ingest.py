"""IssueIngester — ingest GitHub issues and parse acceptance criteria."""

from __future__ import annotations
import re
from typing import Optional
from .models import IssueTicket, AcceptanceCriterion


class IssueIngester:
    """Ingest issues from GitHub or manual input."""

    def from_url(self, url: str, token: Optional[str] = None) -> Optional[IssueTicket]:
        pattern = r"github\.com/([^/]+)/([^/]+)/issues/(\d+)"
        match = re.search(pattern, url)
        if not match:
            return None
        owner, repo, issue_num = match.group(1), match.group(2), match.group(3)
        ticket = self._fetch_github_issue(owner, repo, int(issue_num), token)
        if ticket:
            ticket.url = url
            ticket.source = "github"
        return ticket

    def from_text(self, text: str, ticket_id: str = "manual-001") -> IssueTicket:
        lines = text.strip().split("\n")
        title = lines[0] if lines else "Untitled"
        body = "\n".join(lines[1:]) if len(lines) > 1 else text
        criteria = self._parse_acceptance_criteria(body)
        requirements = self._parse_requirements(body)
        return IssueTicket(
            id=ticket_id,
            title=title,
            body=body,
            repo_url=".",
            author="manual",
            labels=[],
            acceptance_criteria=criteria,
            parsed_requirements=requirements,
            source="manual",
        )

    def _fetch_github_issue(self, owner: str, repo: str, issue_number: int,
                            token: Optional[str] = None) -> Optional[IssueTicket]:
        try:
            import urllib.request
            import json
            url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
            headers = {"Accept": "application/vnd.github.v3+json"}
            if token:
                headers["Authorization"] = f"token {token}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            body = data.get("body", "")
            criteria = self._parse_acceptance_criteria(body)
            requirements = self._parse_requirements(body)

            return IssueTicket(
                id=str(data["number"]),
                title=data["title"],
                body=body,
                repo_url=f"https://github.com/{owner}/{repo}",
                author=data["user"]["login"] if data.get("user") else "unknown",
                labels=[l["name"] for l in data.get("labels", [])],
                acceptance_criteria=criteria,
                parsed_requirements=requirements,
                source="github",
            )
        except Exception as e:
            # Return a synthetic ticket if GitHub API fails
            return IssueTicket(
                id=str(issue_number),
                title=f"Issue #{issue_number}: {owner}/{repo}",
                body=f"Could not fetch issue {issue_number} from GitHub. Using placeholder.",
                repo_url=f"https://github.com/{owner}/{repo}",
                author="github",
                labels=[],
                acceptance_criteria=[AcceptanceCriterion("Implement the issue requirements")],
                parsed_requirements=[f"Fix issue {issue_number} in {owner}/{repo}"],
                source="github_fallback",
            )

    def _parse_acceptance_criteria(self, body: str) -> list[AcceptanceCriterion]:
        criteria = []
        patterns = [
            r"- \[ \] (.+)",
            r"- \[x\] (.+)",
            r"- \[X\] (.+)",
            r"\* \[ \] (.+)",
            r"acceptance[- ]criteria?:?\s*\n((?:\s*[-*].+\n?)+)",
            r"definition of done:?\s*\n((?:\s*[-*].+\n?)+)",
        ]
        seen = set()
        for pattern in patterns:
            matches = re.finditer(pattern, body, re.IGNORECASE)
            for match in matches:
                if pattern.startswith("acceptance") or pattern.startswith("definition"):
                    block = match.group(1)
                    items = re.findall(r"[-*]\s+(.+)", block)
                    for item in items:
                        stripped = item.strip()
                        if stripped and stripped not in seen:
                            criteria.append(AcceptanceCriterion(stripped))
                            seen.add(stripped)
                else:
                    stripped = match.group(1).strip()
                    if stripped and stripped not in seen:
                        criteria.append(AcceptanceCriterion(stripped))
                        seen.add(stripped)

        if not criteria:
            sentences = re.split(r'[.?!]\s+', body)
            for s in sentences[:3]:
                stripped = s.strip()
                if len(stripped) > 15 and stripped not in seen:
                    criteria.append(AcceptanceCriterion(stripped))
                    seen.add(stripped)

        return criteria

    def _parse_requirements(self, body: str) -> list[str]:
        requirements = []
        patterns = [
            r"requires?:?\s*(.+)",
            r"needed:?\s*(.+)",
            r"should\s+(.+?)[.\n]",
            r"must\s+(.+?)[.\n]",
        ]
        for pattern in patterns:
            matches = re.finditer(pattern, body, re.IGNORECASE)
            for m in matches:
                req = m.group(1).strip().rstrip(".")
                if req and len(req) > 10:
                    requirements.append(req)
        return requirements[:10]
