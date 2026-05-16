"""Context packet builder for small local models.

Transforms raw codebase data into tiny, high-value context packets
optimized for 3-8B parameter models. Each packet is:
- Natural language (not JSON)
- Task-specific (not full repo dump)
- Prioritized (most important content first)
- Bounded (fits within the model's limited context window)
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict
from pathlib import Path


@dataclass
class APICard:
    """Natural language summary of a module's public API surface."""
    module_path: str
    purpose: str = ""
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    key_imports: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)

    def to_text(self) -> str:
        lines = [f"Module: {self.module_path}"]
        if self.purpose:
            lines.append(f"  Purpose: {self.purpose}")
        for cls in self.classes:
            lines.append(f"  Class: {cls}")
        for func in self.functions:
            lines.append(f"  Function: {func}")
        if self.key_imports:
            lines.append(f"  Imports: {', '.join(self.key_imports)}")
        if self.depends_on:
            lines.append(f"  Depends on: {', '.join(self.depends_on)}")
        return "\n".join(lines)


@dataclass
class DependencyCard:
    """Natural language summary of dependency relationships."""
    module: str
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    external_packages: List[str] = field(default_factory=list)

    def to_text(self) -> str:
        lines = [f"Dependencies for {self.module}:"]
        if self.dependencies:
            lines.append(f"  Imports from: {', '.join(self.dependencies)}")
        if self.dependents:
            lines.append(f"  Imported by: {', '.join(self.dependents)}")
        if self.external_packages:
            lines.append(f"  External packages: {', '.join(self.external_packages)}")
        return "\n".join(lines)


@dataclass
class TestCard:
    """Natural language summary of test coverage and test results."""
    module_under_test: str
    test_files: List[str] = field(default_factory=list)
    test_count: int = 0
    last_result: str = ""
    coverage_notes: str = ""

    def to_text(self) -> str:
        lines = [f"Tests for {self.module_under_test}:"]
        if self.test_files:
            lines.append(f"  Test files: {', '.join(self.test_files)}")
        lines.append(f"  Test count: {self.test_count}")
        if self.last_result:
            lines.append(f"  Last result: {self.last_result}")
        if self.coverage_notes:
            lines.append(f"  Coverage: {self.coverage_notes}")
        return "\n".join(lines)


@dataclass
class ContextPacket:
    """A complete context packet optimized for small models.
    
    Designed to fit in <2K tokens for 3B models or <4K tokens for 7B models.
    """
    task_type: str  # "bugfix", "feature", "refactor", "qa", "test"
    target_files: List[str] = field(default_factory=list)
    api_cards: List[APICard] = field(default_factory=list)
    dependency_cards: List[DependencyCard] = field(default_factory=list)
    test_cards: List[TestCard] = field(default_factory=list)
    repo_structure: str = ""
    architecture_notes: str = ""
    invariants: List[str] = field(default_factory=list)
    task_instructions: str = ""

    def to_text(self) -> str:
        """Render the packet as natural language text."""
        sections = []

        if self.repo_structure:
            sections.append("REPOSITORY STRUCTURE")
            sections.append(self.repo_structure[:500])

        if self.architecture_notes:
            sections.append("ARCHITECTURE NOTES")
            sections.append(self.architecture_notes[:300])

        if self.api_cards:
            sections.append("API SURFACE")
            for card in self.api_cards:
                sections.append(card.to_text())

        if self.dependency_cards:
            sections.append("DEPENDENCIES")
            for card in self.dependency_cards:
                sections.append(card.to_text())

        if self.test_cards:
            sections.append("TESTS")
            for card in self.test_cards:
                sections.append(card.to_text())

        if self.invariants:
            sections.append("INVARIANTS")
            for inv in self.invariants[:8]:
                sections.append(f"  - {inv}")

        if self.task_instructions:
            sections.append("TASK")
            sections.append(self.task_instructions)

        return "\n\n".join(sections)

    def token_estimate(self) -> int:
        """Rough token count (words * 1.3 for code)."""
        text = self.to_text()
        return len(text.split())


class SmallModelContextAssembler:
    """Builds task-specific context packets for small models.
    
    Wraps the Lyme Audit compression pipeline and converts its output
    into LLM-friendly natural language packets.
    """

    def __init__(self, max_tokens: int = 2048):
        self.max_tokens = max_tokens

    def assemble(
        self,
        task_type: str,
        task_description: str,
        target_files: Optional[List[str]] = None,
        compression_result: Optional[Dict] = None,
    ) -> ContextPacket:
        """Build a context packet from task info and optional compression data."""
        packet = ContextPacket(
            task_type=task_type,
            target_files=target_files or [],
            task_instructions=task_description,
        )

        if compression_result:
            self._add_compression_to_packet(packet, compression_result)

        return packet

    def _add_compression_to_packet(self, packet: ContextPacket, result: Dict):
        """Convert Lyme compression output to natural language cards."""
        layer1 = result.get("layer1_tree", {})
        layer2 = result.get("layer2_apis", {})
        layer3 = result.get("layer3_subsystems", {})
        layer4 = result.get("layer4_invariants", {})

        # Repo structure from L1
        tree = layer1.get("tree", layer1.get("structure", {}))
        if tree:
            if isinstance(tree, dict):
                name = tree.get("name", tree.get("repo_name", "unknown"))
                total = tree.get("total_files", tree.get("file_count", 0))
                languages = tree.get("languages", {})
                frameworks = tree.get("frameworks", [])
                packet.repo_structure = (
                    f"Project: {name} ({total} files)\n"
                    f"Languages: {', '.join(f'{k}: {v}' for k, v in languages.items())}\n"
                    f"Frameworks: {', '.join(frameworks) if frameworks else 'none detected'}"
                )

        # API surface from L2
        modules = layer2.get("modules", [])
        for mod in modules:
            mod_path = mod.get("path", mod.get("file", "unknown"))
            functions = mod.get("functions", [])
            classes = mod.get("classes", [])
            imports = mod.get("imports", [])

            if functions or classes:
                card = APICard(
                    module_path=mod_path,
                    purpose=mod.get("docstring", "")[:100],
                    classes=[c.get("name", "?") for c in classes],
                    functions=[f.get("name", "?") for f in functions],
                    key_imports=[i.get("name", str(i)[:30]) for i in imports[:5]],
                )
                packet.api_cards.append(card)

        # Dependencies from L3
        subsystems = layer3.get("subsystems", layer3.get("clusters", []))
        if isinstance(subsystems, list):
            for sub in subsystems:
                name = sub.get("name", "?")
                files = sub.get("files", [])
                if files:
                    card = DependencyCard(
                        module=name,
                        dependencies=list(sub.get("dependencies", []))[:10],
                        dependents=list(sub.get("dependents", []))[:5],
                    )
                    packet.dependency_cards.append(card)

        # Invariants from L4
        invariants = layer4.get("invariants", [])
        for inv in invariants:
            desc = inv.get("description", str(inv)[:100])
            if desc:
                packet.invariants.append(desc)

        # Architecture notes
        if packet.dependency_cards or packet.api_cards:
            notes = []
            if packet.dependency_cards:
                notes.append(f"{len(packet.dependency_cards)} subsystems identified")
            if packet.api_cards:
                notes.append(f"{len(packet.api_cards)} modules with public API")
            packet.architecture_notes = ". ".join(notes)

    def fit_to_budget(self, packet: ContextPacket, max_tokens: int = None) -> ContextPacket:
        """Truncate packet to fit within token budget."""
        budget = max_tokens or self.max_tokens
        current = packet.token_estimate()

        if current <= budget:
            return packet

        # Truncation strategy: remove least important content
        if packet.architecture_notes:
            packet.architecture_notes = ""
            if packet.token_estimate() <= budget:
                return packet

        if len(packet.invariants) > 3:
            packet.invariants = packet.invariants[:3]
            if packet.token_estimate() <= budget:
                return packet

        if len(packet.dependency_cards) > 2:
            packet.dependency_cards = packet.dependency_cards[:2]
            if packet.token_estimate() <= budget:
                return packet

        if len(packet.test_cards) > 1:
            packet.test_cards = packet.test_cards[:1]
            if packet.token_estimate() <= budget:
                return packet

        if packet.repo_structure:
            packet.repo_structure = packet.repo_structure[:200]
            if packet.token_estimate() <= budget:
                return packet

        return packet
