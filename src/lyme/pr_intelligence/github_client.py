import json
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class GitHubPRData:
    number: int = 0
    title: str = ""
    url: str = ""
    repository: str = ""
    branch: str = ""
    author: str = ""
    files: List[dict] = field(default_factory=list)
    diff: str = ""
    description: str = ""
    labels: List[str] = field(default_factory=list)
    reviewers: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "number": self.number,
            "title": self.title,
            "url": self.url,
            "repository": self.repository,
            "branch": self.branch,
            "author": self.author,
            "files": self.files,
            "diff": self.diff,
            "description": self.description,
            "labels": self.labels,
            "reviewers": self.reviewers,
        }


class GitHubPRClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self._base_url = "https://api.github.com"

    def fetch_pr(self, repo: str, pr_number: int) -> Optional[GitHubPRData]:
        if not self.token:
            return self._mock_pr(repo, pr_number)
        return self._fetch_real_pr(repo, pr_number)

    def _fetch_real_pr(self, repo: str, pr_number: int) -> Optional[GitHubPRData]:
        import urllib.request
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "lyme-pr-intelligence",
        }

        pr_url = f"{self._base_url}/repos/{repo}/pulls/{pr_number}"
        files_url = f"{pr_url}/files"
        diff_url = f"https://github.com/{repo}/pull/{pr_number}.diff"

        try:
            req = urllib.request.Request(pr_url, headers=headers)
            with urllib.request.urlopen(req) as resp:
                pr_data = json.loads(resp.read().decode())

            req_files = urllib.request.Request(files_url, headers=headers)
            with urllib.request.urlopen(req_files) as resp:
                files_data = json.loads(resp.read().decode())

            req_diff = urllib.request.Request(diff_url, headers=headers)
            with urllib.request.urlopen(req_diff) as resp:
                diff = resp.read().decode()

            return GitHubPRData(
                number=pr_data.get("number", pr_number),
                title=pr_data.get("title", ""),
                url=pr_data.get("html_url", ""),
                repository=repo,
                branch=pr_data.get("head", {}).get("ref", ""),
                author=pr_data.get("user", {}).get("login", ""),
                files=[{
                    "filename": f.get("filename", ""),
                    "status": f.get("status", "modified"),
                    "additions": f.get("additions", 0),
                    "deletions": f.get("deletions", 0),
                    "patch": f.get("patch", ""),
                } for f in files_data],
                diff=diff,
                description=pr_data.get("body", ""),
                labels=[l.get("name", "") for l in pr_data.get("labels", [])],
            )
        except Exception as e:
            print(f"GitHub API error: {e}")
            return None

    def _mock_pr(self, repo: str, pr_number: int) -> GitHubPRData:
        return GitHubPRData(
            number=pr_number,
            title="Mock PR for testing",
            url=f"https://github.com/{repo}/pull/{pr_number}",
            repository=repo,
            branch="feature/test-branch",
            author="lyme-bot",
            files=[
                {"filename": "src/payment/processor.py", "status": "modified",
                 "additions": 120, "deletions": 40,
                 "patch": "@@ -50,12 +50,45 @@ def process_payment(method, amount):\n+from .strategies import CreditCardStrategy\n+STRATEGIES = {'credit': CreditCardStrategy()}"},
                {"filename": "src/payment/strategies/__init__.py", "status": "added",
                 "additions": 3, "deletions": 0,
                 "patch": "@@ -0,0 +1,3 @@\n+from .credit_card import CreditCardStrategy\n+from .paypal import PayPalStrategy\n"},
                {"filename": "tests/test_payment.py", "status": "modified",
                 "additions": 45, "deletions": 10,
                 "patch": "@@ -10,5 +10,30 @@ def test_process_credit():\n+    strategy = CreditCardStrategy()"},
            ],
            diff="diff --git a/src/payment/processor.py b/src/payment/processor.py\n...",
            description="Refactor payment processing to use strategy pattern",
            labels=["enhancement"],
            reviewers=["senior-dev"],
        )

    def post_comment(self, repo: str, pr_number: int, body: str) -> bool:
        if not self.token:
            print(f"[mock] Posted review comment on {repo}#{pr_number}")
            return True
        return self._post_real_comment(repo, pr_number, body)

    def _post_real_comment(self, repo: str, pr_number: int, body: str) -> bool:
        import urllib.request
        url = f"{self._base_url}/repos/{repo}/issues/{pr_number}/comments"
        data = json.dumps({"body": body}).encode()
        headers = {
            "Authorization": f"token {self.token}",
            "Content-Type": "application/json",
            "User-Agent": "lyme-pr-intelligence",
        }
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req):
                return True
        except Exception as e:
            print(f"GitHub comment error: {e}")
            return False
