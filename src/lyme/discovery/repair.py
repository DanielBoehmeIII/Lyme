from __future__ import annotations

from typing import Any, Dict, List, Optional

from .invariant import InvariantSet, InvariantType, InvariantSeverity, Violation


class RepairSuggester:
    def suggest(self, inv_set: InvariantSet, violation: Violation) -> List[Dict[str, str]]:
        suggestions = []

        type_handlers = {
            InvariantType.LAYER_VIOLATION: self._fix_layer_violation,
            InvariantType.AUTH_REQUIRED: self._fix_auth_missing,
            InvariantType.RESOURCE_CLEANUP: self._fix_resource_cleanup,
            InvariantType.STATELESS_REQUIREMENT: self._fix_stateless,
            InvariantType.CONFIG_SCHEMA: self._fix_config,
            InvariantType.ERROR_HANDLING: self._fix_error_handling,
            InvariantType.CO_EVOLUTION: self._fix_co_evolution,
            InvariantType.VERSION_COUPLING: self._fix_version_coupling,
        }

        inv = inv_set.get_invariant(violation.invariant_id)
        if inv and inv.invariant_type in type_handlers:
            handler = type_handlers[inv.invariant_type]
            suggestions.extend(handler(violation, inv))

        if not suggestions:
            suggestions.append({
                "type": "review",
                "action": "Manual review recommended",
                "rationale": "No automated fix pattern available for this violation type",
                "effort": "medium",
            })

        return suggestions

    def generate_repair_plan(self, inv_set: InvariantSet) -> Dict[str, Any]:
        violations = inv_set.get_violations()
        plans = []

        for v in violations:
            suggestions = self.suggest(inv_set, v)
            plans.append({
                "violation_id": v.id,
                "violation_description": v.description,
                "file": v.file_path,
                "severity": v.severity.value,
                "suggestions": suggestions,
            })

        return {
            "total_violations": len(violations),
            "critical_count": sum(
                1 for v in violations if v.severity == InvariantSeverity.CRITICAL
            ),
            "high_count": sum(
                1 for v in violations if v.severity == InvariantSeverity.HIGH
            ),
            "repair_plans": plans,
        }

    def _fix_layer_violation(self, v: Violation, inv) -> List[Dict[str, str]]:
        return [{
            "type": "refactor",
            "action": f"Move import from 'controllers' to use service layer abstraction in {v.file_path}",
            "rationale": "Direct controller-to-model imports violate layered architecture",
            "effort": "medium",
        }]

    def _fix_auth_missing(self, v: Violation, inv) -> List[Dict[str, str]]:
        return [{
            "type": "add_decorator",
            "action": f"Add @login_required decorator to the function at {v.file_path}:{v.line_number}",
            "rationale": "Admin/delete/update operations require authentication",
            "effort": "low",
        }]

    def _fix_resource_cleanup(self, v: Violation, inv) -> List[Dict[str, str]]:
        return [{
            "type": "refactor",
            "action": f"Wrap file open in 'with' statement at {v.file_path}:{v.line_number}",
            "rationale": "Files must be properly closed to avoid resource leaks",
            "effort": "low",
        }]

    def _fix_stateless(self, v: Violation, inv) -> List[Dict[str, str]]:
        return [{
            "type": "refactor",
            "action": f"Move state mutation out of service class to dedicated state manager",
            "rationale": f"Service in {v.file_path} should maintain statelessness",
            "effort": "high",
        }]

    def _fix_config(self, v: Violation, inv) -> List[Dict[str, str]]:
        return [{
            "type": "config_extract",
            "action": f"Extract hardcoded URL to environment variable or config file",
            "rationale": "Hardcoded URLs reduce portability and create security risks",
            "effort": "low",
        }]

    def _fix_error_handling(self, v: Violation, inv) -> List[Dict[str, str]]:
        return [{
            "type": "refactor",
            "action": f"Replace bare 'except:' with specific exception types at {v.file_path}:{v.line_number}",
            "rationale": "Bare except clauses hide unexpected errors",
            "effort": "low",
        }]

    def _fix_co_evolution(self, v: Violation, inv) -> List[Dict[str, str]]:
        return [{
            "type": "refactor",
            "action": f"Create shared abstraction for co-evolving files: {inv.scope}",
            "rationale": "Frequently co-changing files should share an abstraction layer",
            "effort": "high",
        }]

    def _fix_version_coupling(self, v: Violation, inv) -> List[Dict[str, str]]:
        return [{
            "type": "sync",
            "action": f"Synchronize dependency versions between {inv.scope}",
            "rationale": "Version-coupled files must maintain compatible dependency versions",
            "effort": "medium",
        }]
