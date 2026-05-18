"""Pricing and licensing module for Lyme."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json
from pathlib import Path

from .subscriptions import PlanTier, Plan, PLANS


FEATURE_BOUNDARY = {
    "free": {
        "label": "Free Local Core",
        "price": "$0",
        "description": "Open-source core for individual developers",
        "features": [
            "lyme doctor — repo diagnostics",
            "lyme ask — evidence-grounded Q&A",
            "lyme dashboard — terminal dashboard",
            "lyme start — daily startup",
            "lyme diff-explain — diff explanation",
            "lyme inbox — task inbox",
            "Local-only telemetry",
            "Open source (MIT)",
        ],
        "limits": {
            "agents": 1,
            "tasks_per_day": 50,
            "team_members": 1,
            "model_runs_per_day": 20,
        },
    },
    "pro": {
        "label": "Pro Individual",
        "price": "$29/mo",
        "description": "For professional developers who rely on Lyme daily",
        "features": [
            "Everything in Free",
            "Up to 3 agents",
            "500 tasks per day",
            "100 model runs per day",
            "Priority CLI support",
            "Bug report generator",
            "Diagnostic bundle export",
        ],
        "limits": {
            "agents": 3,
            "tasks_per_day": 500,
            "team_members": 1,
            "model_runs_per_day": 100,
        },
    },
    "team": {
        "label": "Team Plan",
        "price": "$99/mo",
        "description": "For small teams standardizing on Lyme",
        "features": [
            "Everything in Pro",
            "Up to 10 team members",
            "Up to 10 agents",
            "2000 tasks per day",
            "Audit trail export",
            "Shared workspace metrics",
            "Team dashboard",
        ],
        "limits": {
            "agents": 10,
            "tasks_per_day": 2000,
            "team_members": 10,
            "model_runs_per_day": 500,
        },
    },
    "enterprise": {
        "label": "Enterprise Airgapped",
        "price": "$499/mo",
        "description": "For organizations with strict security requirements",
        "features": [
            "Everything in Team",
            "Unlimited team members",
            "100 agents",
            "10000 tasks per day",
            "Airgapped operation",
            "On-premise deployment",
            "Priority support",
            "Hosted evaluation runners",
            "Custom license terms",
        ],
        "limits": {
            "agents": 100,
            "tasks_per_day": 10000,
            "team_members": 100,
            "model_runs_per_day": 5000,
        },
    },
}


class LicenseGate:
    """Check if a feature is available on the current plan."""

    def __init__(self, tier: PlanTier = PlanTier.FREE):
        self.tier = tier
        self._feature_map = {
            "doctor": PlanTier.FREE,
            "ask": PlanTier.FREE,
            "dashboard": PlanTier.FREE,
            "start": PlanTier.FREE,
            "diff-explain": PlanTier.FREE,
            "inbox": PlanTier.FREE,
            "dogfood": PlanTier.FREE,
            "metrics-audit": PlanTier.FREE,
            "branch-review": PlanTier.FREE,
            "continue": PlanTier.FREE,
            "fix-latest": PlanTier.FREE,
            "watch": PlanTier.FREE,
            "bug_report": PlanTier.PRO,
            "diagnostic_bundle": PlanTier.PRO,
            "audit_trail_export": PlanTier.TEAM,
            "team_dashboard": PlanTier.TEAM,
            "airgap": PlanTier.ENTERPRISE,
            "hosted_evals": PlanTier.ENTERPRISE,
            "priority_support": PlanTier.ENTERPRISE,
        }

    def is_allowed(self, feature: str) -> bool:
        required = self._feature_map.get(feature, PlanTier.FREE)
        tiers = [PlanTier.FREE, PlanTier.PRO, PlanTier.TEAM, PlanTier.ENTERPRISE]
        return tiers.index(self.tier) >= tiers.index(required)

    def check(self, feature: str) -> dict:
        allowed = self.is_allowed(feature)
        return {
            "feature": feature,
            "allowed": allowed,
            "current_tier": self.tier.value,
            "required_tier": self._feature_map.get(feature, PlanTier.FREE).value,
        }

    def print_boundary(self):
        print(f"{'='*60}")
        print(f"  COMMERCIAL FEATURE BOUNDARY")
        print(f"{'='*60}")
        for tier_name, info in FEATURE_BOUNDARY.items():
            print(f"\n  [{info['label']}] — {info['price']}")
            print(f"  {info['description']}")
            for feat in info['features']:
                print(f"    ✓ {feat}")
        print(f"\n{'='*60}")


license_gate = LicenseGate()


class HostedEvalPackaging:
    """Hosted evaluation runner packaging."""

    def package_eval(self, eval_name: str, config: dict) -> dict:
        return {
            "eval_name": eval_name,
            "type": "hosted",
            "config": config,
            "runner": "lyme-hosted-runner",
            "requirements": ["docker", "nvidia-docker", "lyme>=0.9.0"],
        }

    def print_package(self, pkg: dict):
        print(f"Hosted eval: {pkg['eval_name']}")
        print(f"  Runner: {pkg['runner']}")
        print(f"  Requirements: {', '.join(pkg['requirements'])}")


hosted_eval = HostedEvalPackaging()
