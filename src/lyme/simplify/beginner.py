ESSENTIAL_COMMANDS = {
    "heal": "Diagnose + prioritize + fix + verify (flagship)",
    "doctor": "Diagnose your repository health",
    "v1-audit": "Honest v1 readiness score (A-F)",
    "v1-fix": "Track and apply v1 repairs",
    "gate": "Run v1 reliability gate check",
    "ask": "Ask questions about your codebase",
    "fix": "Fix issues with safe, auditable edits",
    "diff": "Understand what changed in your code",
    "trace": "View execution traces",
    "dashboard": "See everything at a glance",
    "start": "Start your daily workflow",
    "inbox": "See pending tasks",
    "info": "Project health and diagnostics",
    "history": "See what happened",
    "undo": "Undo a previous action",
}

BEGINNER_FLOW = {
    "new_project": ["init", "doctor", "dashboard"],
    "daily": ["start", "inbox", "dashboard"],
    "debugging": ["doctor", "ask", "fix"],
    "learning": ["diff", "trace", "history"],
}


class BeginnerMode:
    def __init__(self):
        self._active = False

    def enable(self):
        self._active = True

    def disable(self):
        self._active = False

    @property
    def active(self) -> bool:
        return self._active

    def get_essential_commands(self) -> dict[str, str]:
        return dict(ESSENTIAL_COMMANDS)

    def get_workflow_guide(self, workflow: str = "") -> dict:
        if workflow:
            steps = BEGINNER_FLOW.get(workflow, [])
            return {
                "workflow": workflow,
                "steps": steps,
                "descriptions": {s: ESSENTIAL_COMMANDS.get(s, s) for s in steps},
            }
        return {
            "available_workflows": list(BEGINNER_FLOW.keys()),
            "workflows": {
                k: {"steps": v, "descriptions": {s: ESSENTIAL_COMMANDS.get(s, s) for s in v}}
                for k, v in BEGINNER_FLOW.items()
            },
        }

    def get_mode_status(self) -> dict:
        return {
            "active": self._active,
            "available_commands": len(ESSENTIAL_COMMANDS),
            "total_commands": 83,
            "hidden_commands": 83 - len(ESSENTIAL_COMMANDS),
            "reduction": f"{round((1 - len(ESSENTIAL_COMMANDS) / 83) * 100)}%",
            "workflows": list(BEGINNER_FLOW.keys()),
        }


beginner_mode = BeginnerMode()
