from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional


class RepoSummarizer:
    def __init__(self, max_summary_length: int = 4_000):
        self.max_summary_length = max_summary_length

    def summarize(
        self,
        layers: Dict[str, Any],
        context_limit: int = 128_000,
    ) -> str:
        tree = layers.get("layer1_tree", {})
        apis = layers.get("layer2_apis", {})
        subsystems = layers.get("layer3_subsystems", {})
        invariants = layers.get("layer4_invariants", {})

        sections: List[str] = [
            self._describe_purpose(tree),
            self._describe_structure(tree, subsystems),
            self._describe_architecture(tree, subsystems, apis),
            self._describe_conventions(invariants),
        ]

        summary = "\n\n".join(s for s in sections if s)
        if len(summary) > self.max_summary_length:
            summary = summary[:self.max_summary_length] + "\n[Truncated...]"

        return summary

    def _describe_purpose(self, tree: Dict[str, Any]) -> str:
        repo_name = tree.get("repo_name", "Unknown")
        languages = tree.get("languages", {})
        frameworks = tree.get("frameworks", [])
        total_files = tree.get("total_files", 0)
        entry_points = tree.get("entry_points", [])

        primary_lang = max(languages, key=languages.get) if languages else "Unknown"
        fw_str = f", uses {', '.join(frameworks)}" if frameworks else ""

        ep_lines = ""
        if entry_points:
            ep_list = "\n".join(f"  - {e['path']} ({e.get('type', 'entry')})" for e in entry_points[:5])
            ep_lines = f"\nEntry points:\n{ep_list}"

        return (
            f"Repository: {repo_name}\n"
            f"Primary language: {primary_lang} ({total_files} files total){fw_str}"
            f"{ep_lines}"
        )

    def _describe_structure(
        self, tree: Dict[str, Any], subsystems: Dict[str, Any]
    ) -> str:
        package_struct = tree.get("package_structure", [])
        sub_map = subsystems.get("subsystems", {})
        deps = subsystems.get("subsystem_dependency_graph", {})

        lines: List[str] = ["Project structure:"]
        if package_struct:
            lines.append("Packages:")
            for pkg in package_struct[:15]:
                subs = ", ".join(pkg.get("submodules", [])[:8])
                lines.append(f"  {pkg['package']}/ ({len(pkg.get('submodules', []))} modules)")
                if subs:
                    lines.append(f"    modules: {subs}")

        if sub_map:
            lines.append(f"\nSubsystems ({len(sub_map)}):")
            for sub, files in sorted(sub_map.items())[:10]:
                deps_list = deps.get(sub, [])
                dep_names = [d["target"] for d in deps_list]
                dep_str = f" → [{', '.join(dep_names)}]" if dep_names else ""
                lines.append(f"  {sub}/ ({len(files)} files){dep_str}")

        if len(package_struct) > 15 or len(sub_map) > 10:
            lines.append("  ... (truncated)")

        return "\n".join(lines)

    def _describe_architecture(
        self,
        tree: Dict[str, Any],
        subsystems: Dict[str, Any],
        apis: Dict[str, Any],
    ) -> str:
        sub_map = subsystems.get("subsystems", {})
        modules = apis.get("modules", [])
        cycles = subsystems.get("circular_dependencies", [])

        lines: List[str] = ["Architecture overview:"]

        if sub_map:
            central = self._find_central_subsystems(subsystems)
            if central:
                lines.append(f"Central subsystems (most depended-on): {', '.join(central[:5])}")

        total_classes = sum(len(m.get("classes", [])) for m in modules)
        total_functions = sum(len(m.get("functions", [])) for m in modules)
        lines.append(f"Public API surface: ~{total_classes} classes, ~{total_functions} functions across {len(modules)} files")

        if cycles:
            lines.append(f"\n⚠  {len(cycles)} circular dependenc{'y' if len(cycles) == 1 else 'ies'} detected:")
            for c in cycles[:3]:
                cycle_str = " → ".join(c.get("cycle", []))
                lines.append(f"  {cycle_str}")

        return "\n".join(lines)

    def _describe_conventions(self, invariants: Dict[str, Any]) -> str:
        risk_zones = invariants.get("risk_zones", [])
        change_patterns = invariants.get("change_patterns", {})
        large_files = invariants.get("large_files", [])
        high_import_files = invariants.get("high_import_files", [])

        lines: List[str] = ["Conventions & risks:"]

        high_risks = [z for z in risk_zones if z.get("risk") == "high"]
        if high_risks:
            lines.append(f"High-risk items ({len(high_risks)}):")
            for rz in high_risks[:5]:
                lines.append(f"  ⚠  {rz.get('file', '')} — {rz.get('reason', '')}")

        if large_files:
            lines.append(f"Largest files: {', '.join(lf['file'] for lf in large_files[:5])}")

        if high_import_files:
            lines.append(
                f"Highest-import files: {', '.join(hf['file'] for hf in high_import_files[:5])}"
            )

        if change_patterns.get("available"):
            cooccur = change_patterns.get("top_cooccurring_changes", [])
            if cooccur:
                lines.append("Change coupling patterns (files changed together):")
                for cc in cooccur[:3]:
                    lines.append(f"  {cc['file_a']} ↔ {cc['file_b']} ({cc['cooccurrences']}x)")

        return "\n".join(lines)

    def _find_central_subsystems(
        self, subsystems: Dict[str, Any]
    ) -> List[str]:
        dep_graph = subsystems.get("subsystem_dependency_graph", {})
        dependents: Dict[str, int] = {}
        for sub, deps in dep_graph.items():
            for d in deps:
                target = d["target"]
                dependents[target] = dependents.get(target, 0) + 1
        return sorted(dependents, key=dependents.get, reverse=True)

    def summarize_file(self, filepath: Path, max_lines: int = 50) -> str:
        if not filepath.is_file():
            return f"File not found: {filepath}"
        try:
            lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception as e:
            return f"Error reading {filepath}: {e}"

        prefix = lines[:max_lines]
        summary = "\n".join(prefix)
        if len(lines) > max_lines:
            summary += f"\n... ({len(lines) - max_lines} more lines)"
        return summary
