from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
from collections import defaultdict
import json
import math
import hashlib


class AbstractionType(str, Enum):
    AUTHENTICATION_PATTERN = "authentication_pattern"
    API_STRUCTURE = "api_structure"
    DEPLOYMENT_WORKFLOW = "deployment_workflow"
    FRONTEND_STATE_CONVENTION = "frontend_state_convention"
    TESTING_STRATEGY = "testing_strategy"
    CACHING_ARCHITECTURE = "caching_architecture"
    ERROR_HANDLING = "error_handling"
    DATA_FLOW = "data_flow"
    CONFIGURATION_MANAGEMENT = "configuration_management"
    LOGGING_PATTERN = "logging_pattern"


@dataclass
class CompressedAbstraction:
    abstraction_type: AbstractionType
    name: str
    description: str
    template: str
    parameters: Dict[str, str]
    invariant_constraints: List[str]
    adaptation_rules: List[str]
    source_repositories: List[str]
    compression_ratio: float
    confidence: float
    generalization_score: float

    def to_dict(self) -> Dict:
        return {
            "abstraction_type": self.abstraction_type.value,
            "name": self.name,
            "description": self.description,
            "template": self.template,
            "parameters": self.parameters,
            "invariant_constraints": self.invariant_constraints,
            "adaptation_rules": self.adaptation_rules,
            "source_repositories": self.source_repositories,
            "compression_ratio": self.compression_ratio,
            "confidence": self.confidence,
            "generalization_score": self.generalization_score,
        }


@dataclass
class AbstractionHierarchy:
    root: CompressedAbstraction
    children: List[CompressedAbstraction]
    specialization_depth: int
    coverage: float

    def to_dict(self) -> Dict:
        return {
            "root": self.root.to_dict(),
            "children": [c.to_dict() for c in self.children],
            "specialization_depth": self.specialization_depth,
            "coverage": self.coverage,
        }


class SemanticCompressionEngine:
    def __init__(self):
        self._abstractions: Dict[str, CompressedAbstraction] = {}
        self._hierarchies: List[AbstractionHierarchy] = []
        self._known_patterns = self._init_known_patterns()

    def _init_known_patterns(self) -> Dict[AbstractionType, Dict]:
        return {
            AbstractionType.AUTHENTICATION_PATTERN: {
                "template": """
class AuthHandler:
    def __init__(self, {backend}):
        self.backend = {backend}

    async def authenticate(self, request):
        token = {extract_token}(request)
        if not token:
            return None
        return await self.backend.validate(token)

    async def authorize(self, user, {scope}):
        return self.backend.check_permissions(user, {scope})
""",
                "parameters": {"backend": "AuthBackend", "extract_token": "extract_token_func", "scope": "permission_scope"},
                "invariants": ["Token extraction before validation", "Authentication before authorization", "Stateless token validation"],
            },
            AbstractionType.API_STRUCTURE: {
                "template": """
router = APIRouter(prefix="/{resource}", tags=["{resource}"])

@router.get("/", response_model=List[{response_type}])
async def list_{resource}({dependencies}):
    return await service.get_all()

@router.get("/{id}", response_model={response_type})
async def get_{resource}(id: int, {dependencies}):
    result = await service.get(id)
    if not result:
        raise HTTPException(status_code=404)
    return result

@router.post("/", response_model={response_type}, status_code=201)
async def create_{resource}(data: {input_type}, {dependencies}):
    return await service.create(data)

@router.put("/{id}", response_model={response_type})
async def update_{resource}(id: int, data: {input_type}, {dependencies}):
    return await service.update(id, data)

@router.delete("/{id}", status_code=204)
async def delete_{resource}(id: int, {dependencies}):
    await service.delete(id)
""",
                "parameters": {"resource": "str", "response_type": "Type", "input_type": "Type", "dependencies": "Depends()"},
                "invariants": ["CRUD operations follow resource pattern", "Consistent status codes", "Dependency injection for services"],
            },
            AbstractionType.TESTING_STRATEGY: {
                "template": """
class Test{resource}:
    async def test_create_{resource}(self, client):
        response = await client.post("/{resource}", json={test_data})
        assert response.status_code == 201
        data = response.json()
        assert data["{key_field}"]

    async def test_get_{resource}(self, client, created_{resource}):
        response = await client.get(f"/{{resource}}/{{created_{resource}['id']}}")
        assert response.status_code == 200

    async def test_list_{resource}(self, client):
        response = await client.get("/{resource}")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_update_{resource}(self, client, created_{resource}):
        response = await client.put(f"/{{resource}}/{{created_{resource}['id']}}", json={update_data})
        assert response.status_code == 200

    async def test_delete_{resource}(self, client, created_{resource}):
        response = await client.delete(f"/{{resource}}/{{created_{resource}['id']}}")
        assert response.status_code == 204
""",
                "parameters": {"resource": "str", "test_data": "dict", "update_data": "dict", "key_field": "str"},
                "invariants": ["Test per CRUD operation", "Status code validation", "Response structure validation"],
            },
            AbstractionType.CACHING_ARCHITECTURE: {
                "template": """
class {cache_name}Cache:
    def __init__(self, {backend}, ttl: int = {default_ttl}):
        self.backend = {backend}
        self.ttl = ttl

    async def get(self, key: str) -> Optional[Any]:
        return await self.backend.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        await self.backend.set(key, value, ttl or self.ttl)

    async def invalidate(self, pattern: str):
        await self.backend.delete_pattern(pattern)

    async def get_or_compute(self, key: str, compute_fn, ttl: Optional[int] = None):
        cached = await self.get(key)
        if cached:
            return cached
        value = await compute_fn()
        await self.set(key, value, ttl)
        return value
""",
                "parameters": {"cache_name": "str", "backend": "Redis/Memory", "default_ttl": "int"},
                "invariants": ["Cache-aside pattern", "TTL-based expiration", "Cache invalidation by pattern"],
            },
            AbstractionType.ERROR_HANDLING: {
                "template": """
class AppError(Exception):
    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}

class NotFoundError(AppError):
    def __init__(self, resource: str, id: Any):
        super().__init__(f"{resource} not found: {id}", status_code=404)

class ValidationError(AppError):
    def __init__(self, message: str, errors: dict = None):
        super().__init__(message, status_code=422, details=errors)

@app.exception_handler(AppError)
async def app_error_handler(request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={{"error": exc.message, "details": exc.details}},
    )
""",
                "parameters": {},
                "invariants": ["Custom exception hierarchy", "Centralized error handler", "Consistent error response format"],
            },
        }

    def discover_abstractions(self, code_samples: List[Dict[str, str]]) -> List[CompressedAbstraction]:
        discovered = []
        for ab_type, pattern in self._known_patterns.items():
            matches = self._find_matches(pattern["template"], code_samples)
            if len(matches) >= 2:
                compression_ratio = self._compute_compression_ratio(pattern["template"], matches)
                generalization = min(1.0, len(matches) / 10)

                abstraction = CompressedAbstraction(
                    abstraction_type=ab_type,
                    name=ab_type.value.replace("_", " ").title(),
                    description=f"Compressed {ab_type.value} from {len(matches)} samples",
                    template=pattern["template"],
                    parameters=pattern["parameters"],
                    invariant_constraints=pattern["invariants"],
                    adaptation_rules=self._generate_adaptation_rules(ab_type),
                    source_repositories=[m.get("repo", "unknown") for m in matches[:5]],
                    compression_ratio=round(compression_ratio, 3),
                    confidence=round(min(1.0, len(matches) * 0.15), 3),
                    generalization_score=round(generalization, 3),
                )
                discovered.append(abstraction)
                self._abstractions[abstraction.name] = abstraction

        return discovered

    def _find_matches(self, template: str, code_samples: List[Dict[str, str]]) -> List[Dict]:
        matches = []
        template_normalized = template.lower().strip()
        for sample in code_samples:
            code = sample.get("code", "").lower().strip()
            overlap = len(set(template_normalized.split()) & set(code.split()))
            similarity = overlap / max(1, len(set(template_normalized.split()) | set(code.split())))
            if similarity > 0.2:
                matches.append(sample)
        return matches

    def _compute_compression_ratio(self, template: str, matches: List[Dict]) -> float:
        template_len = len(template)
        if not matches or template_len == 0:
            return 0
        total_code_len = sum(len(m.get("code", "")) for m in matches)
        return min(1.0, template_len * len(matches) / max(1, total_code_len))

    def _generate_adaptation_rules(self, ab_type: AbstractionType) -> List[str]:
        rules = {
            AbstractionType.AUTHENTICATION_PATTERN: [
                "Replace {backend} with specific auth provider", "Update token extraction for request format",
                "Add rate limiting for authentication endpoints",
            ],
            AbstractionType.API_STRUCTURE: [
                "Replace {resource} with entity name", "Customize response models for entity",
                "Add pagination for list endpoints",
            ],
            AbstractionType.TESTING_STRATEGY: [
                "Replace {resource} with target entity", "Update test data fixtures",
                "Add edge case tests per entity",
            ],
        }
        return rules.get(ab_type, ["Adapt template parameters to local context"])

    def compress(self, code_samples: List[Dict[str, str]], 
                  target_abstraction: AbstractionType) -> Optional[CompressedAbstraction]:
        discovered = self.discover_abstractions(code_samples)
        for a in discovered:
            if a.abstraction_type == target_abstraction:
                return a
        return None

    def transfer(self, abstraction: CompressedAbstraction, target_context: Dict) -> str:
        adapted = abstraction.template
        for param, default in abstraction.parameters.items():
            value = target_context.get(param, default)
            adapted = adapted.replace("{" + param + "}", str(value))
        return adapted

    def detect_mismatch(self, abstraction: CompressedAbstraction, code: str) -> List[str]:
        mismatches = []
        code_lower = code.lower()
        for constraint in abstraction.invariant_constraints:
            constraint_keywords = constraint.lower().split()
            matches = sum(1 for kw in constraint_keywords if kw in code_lower)
            if matches < 2:
                mismatches.append(f"Invariant violated: {constraint}")
        return mismatches

    def build_hierarchy(self, abstractions: List[CompressedAbstraction]) -> List[AbstractionHierarchy]:
        hierarchies = []
        by_type = defaultdict(list)
        for ab in abstractions:
            by_type[ab.abstraction_type].append(ab)

        for ab_type, group in by_type.items():
            if len(group) >= 2:
                group.sort(key=lambda x: -x.generalization_score)
                hierarchy = AbstractionHierarchy(
                    root=group[0], children=group[1:],
                    specialization_depth=len(group),
                    coverage=round(len(group) / 10, 3),
                )
                hierarchies.append(hierarchy)
                self._hierarchies.append(hierarchy)

        return hierarchies

    def get_statistics(self) -> Dict:
        return {
            "total_abstractions": len(self._abstractions),
            "hierarchies": len(self._hierarchies),
            "types": list(self._abstractions.keys()),
            "avg_compression_ratio": round(
                sum(a.compression_ratio for a in self._abstractions.values()) / max(1, len(self._abstractions)), 3
            ) if self._abstractions else 0,
            "avg_confidence": round(
                sum(a.confidence for a in self._abstractions.values()) / max(1, len(self._abstractions)), 3
            ) if self._abstractions else 0,
        }

    def save(self, path: str):
        data = {
            "abstractions": {k: v.to_dict() for k, v in self._abstractions.items()},
            "hierarchies": [h.to_dict() for h in self._hierarchies],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> SemanticCompressionEngine:
        with open(path) as f:
            data = json.load(f)
        engine = cls()
        for name, ad in data.get("abstractions", {}).items():
            engine._abstractions[name] = CompressedAbstraction(
                abstraction_type=AbstractionType(ad["abstraction_type"]),
                name=ad["name"], description=ad["description"], template=ad["template"],
                parameters=ad["parameters"], invariant_constraints=ad["invariant_constraints"],
                adaptation_rules=ad["adaptation_rules"], source_repositories=ad["source_repositories"],
                compression_ratio=ad["compression_ratio"], confidence=ad["confidence"],
                generalization_score=ad["generalization_score"],
            )
        for hd in data.get("hierarchies", []):
            root = engine._abstractions.get(hd["root"]["name"])
            children = [engine._abstractions.get(c["name"]) for c in hd["children"] if c["name"] in engine._abstractions]
            if root:
                engine._hierarchies.append(AbstractionHierarchy(
                    root=root, children=[c for c in children if c], 
                    specialization_depth=hd["specialization_depth"], coverage=hd["coverage"],
                ))
        return engine
