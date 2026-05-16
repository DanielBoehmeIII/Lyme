from pathlib import Path
from ..scenario import BenchmarkScenario, ScenarioResult
from ..registry import ScenarioRegistry


@ScenarioRegistry.register
class MultiFileEditConsistencyScenario(BenchmarkScenario):
    @property
    def name(self): return "multi-file-edit-consistency"

    @property
    def category(self): return "multi_file_edit"

    @property
    def description(self): return "Measure consistency of edits across interdependent files"

    @property
    def difficulty(self): return 0.7

    def setup(self, work_dir: Path) -> dict:
        files = {
            "src/types.py": "from dataclasses import dataclass\nfrom typing import Optional\n\n@dataclass\nclass User:\n    id: int\n    name: str\n    email: str\n\n@dataclass\nclass Post:\n    id: int\n    user_id: int\n    title: str\n    body: str\n\n@dataclass\nclass Comment:\n    id: int\n    post_id: int\n    author: str\n    text: str\n",
            "src/repository.py": "from typing import Optional\nfrom .types import User, Post, Comment\n\nclass UserRepository:\n    def get(self, user_id: int) -> Optional[User]:\n        return User(id=user_id, name='test', email='test@test.com')\n\nclass PostRepository:\n    def get_by_user(self, user_id: int) -> list[Post]:\n        return [Post(id=1, user_id=user_id, title='Test', body='Body')]\n\nclass CommentRepository:\n    def get_by_post(self, post_id: int) -> list[Comment]:\n        return [Comment(id=1, post_id=post_id, author='User', text='Great post!')]\n",
            "src/service.py": "from .repository import UserRepository, PostRepository, CommentRepository\nfrom .types import User, Post, Comment\n\nclass UserService:\n    def __init__(self):\n        self.user_repo = UserRepository()\n        self.post_repo = PostRepository()\n        self.comment_repo = CommentRepository()\n\n    def get_user_with_posts(self, user_id: int) -> dict:\n        user = self.user_repo.get(user_id)\n        posts = self.post_repo.get_by_user(user_id)\n        return {'user': user, 'posts': posts}\n\n    def get_user_with_all(self, user_id: int) -> dict:\n        user = self.user_repo.get(user_id)\n        posts = self.post_repo.get_by_user(user_id)\n        comments = []\n        for post in posts:\n            comments.extend(self.comment_repo.get_by_post(post.id))\n        return {'user': user, 'posts': posts, 'comments': comments}\n",
            "src/api.py": "from .service import UserService\n\nservice = UserService()\n\ndef handle_get_user(user_id: int):\n    return service.get_user_with_posts(user_id)\n\ndef handle_get_user_all(user_id: int):\n    return service.get_user_with_all(user_id)\n",
        }
        for path, content in files.items():
            p = work_dir / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)

        # Import validation
        (work_dir / "src/__init__.py").write_text("from .types import User, Post, Comment\nfrom .repository import UserRepository, PostRepository, CommentRepository\nfrom .service import UserService\nfrom .api import handle_get_user, handle_get_user_all\n")
        return {"file_count": 5}

    def task_prompt(self, context: dict) -> str:
        return ("Refactor the data layer to add a 'status' field (draft/published/archived) to Post. "
                "This change must propagate correctly across all layers:\n"
                "1. Add status to Post in types.py with default 'draft'\n"
                "2. Update PostRepository in repository.py to handle status filtering\n"
                "3. Update UserService in service.py to include status in responses\n"
                "4. Update API handlers in api.py if needed\n"
                "5. Ensure all imports remain valid\n"
                "CRITICAL: Keep backward compatibility - existing code must still work.")

    def evaluate(self, work_dir: Path, context: dict) -> ScenarioResult:
        result = ScenarioResult(scenario_name=self.name)
        errors = []

        types_file = work_dir / "src/types.py"
        if types_file.exists():
            content = types_file.read_text()
            if "status" in content and ("draft" in content or "str" in content):
                result.metrics["types_updated"] = 1.0
            else:
                errors.append("types.py: status field not added")
                result.metrics["types_updated"] = 0.0
        else:
            errors.append("types.py missing")

        repo_file = work_dir / "src/repository.py"
        if repo_file.exists():
            content = repo_file.read_text()
            if "status" in content.lower():
                result.metrics["repository_updated"] = 1.0
            else:
                errors.append("repository.py: status not referenced")
                result.metrics["repository_updated"] = 0.0
        else:
            errors.append("repository.py missing")

        svc_file = work_dir / "src/service.py"
        if svc_file.exists():
            content = svc_file.read_text()
            if "status" in content.lower():
                result.metrics["service_updated"] = 1.0
            else:
                errors.append("service.py: status not referenced")
                result.metrics["service_updated"] = 0.0

        api_file = work_dir / "src/api.py"
        if api_file.exists():
            api_content = api_file.read_text()
            for pkg in ["service", "repository", "types"]:
                if f".{pkg}" in api_content or f"from .{pkg}" in api_content:
                    pass

        init_file = work_dir / "src/__init__.py"
        if init_file.exists():
            init_content = init_file.read_text()
            try:
                compile(init_content, "__init__.py", "exec")
                result.metrics["imports_valid"] = 1.0
            except SyntaxError:
                errors.append("__init__.py has syntax errors")
                result.metrics["imports_valid"] = 0.0
        else:
            errors.append("__init__.py missing")

        updated_count = sum([
            result.metrics.get("types_updated", 0),
            result.metrics.get("repository_updated", 0),
            result.metrics.get("service_updated", 0),
        ])
        result.success = updated_count >= 2
        result.files_modified = int(updated_count)
        result.errors = errors
        result.metrics["propagation_score"] = updated_count / 3.0
        return result


@ScenarioRegistry.register
class MultiFileRefactorScenario(BenchmarkScenario):
    @property
    def name(self): return "multi-file-refactor"

    @property
    def category(self): return "multi_file_edit"

    @property
    def description(self): return "Measure ability to safely rename/move symbols across files"

    @property
    def difficulty(self): return 0.8

    def setup(self, work_dir: Path) -> dict:
        files = {
            "src/old_package/module_a.py": "class LegacyService:\n    def process(self, data):\n        return {'status': 'processed', 'data': data}\n\ndef old_helper(x):\n    return x * 2\n",
            "src/old_package/__init__.py": "from .module_a import LegacyService, old_helper\n",
            "src/consumer_a.py": "from src.old_package import LegacyService\n\ndef handle_request(data):\n    svc = LegacyService()\n    return svc.process(data)\n",
            "src/consumer_b.py": "from src.old_package import old_helper\n\ndef transform(x):\n    return old_helper(x) + 1\n",
            "src/consumer_c.py": "from src.old_package.module_a import LegacyService, old_helper\n\ndef run_pipeline(data):\n    svc = LegacyService()\n    intermediate = svc.process(data)\n    return old_helper(intermediate['data'])\n",
        }
        for path, content in files.items():
            p = work_dir / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
        return {"file_count": 5, "consumers": 3}

    def task_prompt(self, context: dict) -> str:
        return ("Refactor old_package to new_package:\n"
                "1. Rename src/old_package/ to src/new_package/\n"
                "2. Rename LegacyService to ModernService but keep the same interface\n"
                "3. Rename old_helper to transform_helper\n"
                "4. Update ALL consumers (consumer_a.py, consumer_b.py, consumer_c.py) to use the new imports\n"
                "5. Ensure no broken imports remain")

    def evaluate(self, work_dir: Path, context: dict) -> ScenarioResult:
        result = ScenarioResult(scenario_name=self.name)
        errors = []

        for consumer in ["consumer_a.py", "consumer_b.py", "consumer_c.py"]:
            p = work_dir / "src" / consumer
            if p.exists():
                content = p.read_text()
                has_old = "old_package" in content or "LegacyService" in content or "old_helper" in content
                has_new = "new_package" in content or "ModernService" in content or "transform_helper" in content
                if has_old:
                    errors.append(f"{consumer}: still references old names")
                    result.metrics[f"{consumer}_updated"] = 0.0
                elif has_new:
                    result.metrics[f"{consumer}_updated"] = 1.0

        new_pkg = work_dir / "src/new_package"
        old_pkg = work_dir / "src/old_package"

        if new_pkg.exists() or not old_pkg.exists():
            result.metrics["package_renamed"] = 1.0
        else:
            errors.append("old_package still exists, new_package missing")
            result.metrics["package_renamed"] = 0.0

        updated = sum(v for k, v in result.metrics.items() if k.endswith("_updated"))
        result.success = result.metrics.get("package_renamed", 0) >= 1 and updated >= 2
        result.errors = errors
        result.files_modified = int(updated)

        return result
