from typing import Dict, List, Optional, Type
from .scenario import BenchmarkScenario


class ScenarioRegistry:
    _scenarios: Dict[str, Type[BenchmarkScenario]] = {}

    @classmethod
    def register(cls, scenario_cls: Type[BenchmarkScenario]):
        instance = scenario_cls()
        cls._scenarios[instance.name] = scenario_cls
        return scenario_cls

    @classmethod
    def get(cls, name: str) -> Optional[Type[BenchmarkScenario]]:
        return cls._scenarios.get(name)

    @classmethod
    def get_instance(cls, name: str) -> Optional[BenchmarkScenario]:
        scenario_cls = cls.get(name)
        if scenario_cls:
            return scenario_cls()
        return None

    @classmethod
    def list_scenarios(cls) -> List[dict]:
        return [
            {
                "name": name,
                "category": cls_().category,
                "description": cls_().description,
                "difficulty": cls_().difficulty,
                "tags": cls_().tags,
            }
            for name, cls_ in sorted(cls._scenarios.items())
        ]

    @classmethod
    def list_by_category(cls, category: str) -> List[str]:
        return [
            name for name, cls_ in cls._scenarios.items()
            if cls_().category == category
        ]

    @classmethod
    def clear(cls):
        cls._scenarios.clear()
