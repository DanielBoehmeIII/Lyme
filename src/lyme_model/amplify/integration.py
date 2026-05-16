"""Integration coordinator for all amplification strategies.

Combines compression, retrieval, memory, and prompt optimization
into a single context assembly pipeline for small models.
"""

from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path

from .assembler import SmallModelContextAssembler, ContextPacket


@dataclass
class AmplificationResult:
    context_packet: ContextPacket
    strategy: str
    token_count: int
    compression_ratio: float  # vs raw


class AmplificationLayer:
    """Coordinates all amplification strategies.
    
    The amplification layer's job: make every token that reaches the
    model count. No filler. No redundancy. No wasted context.
    """

    def __init__(self, max_tokens: int = 2048):
        self.max_tokens = max_tokens
        self.assembler = SmallModelContextAssembler(max_tokens=max_tokens)

    def amplify(
        self,
        task_type: str,
        task_description: str,
        target_files: Optional[List[str]] = None,
        compression_result: Optional[dict] = None,
    ) -> AmplificationResult:
        """Build and optimize a context packet."""
        packet = self.assembler.assemble(
            task_type=task_type,
            task_description=task_description,
            target_files=target_files,
            compression_result=compression_result,
        )

        packet = self.assembler.fit_to_budget(packet)

        return AmplificationResult(
            context_packet=packet,
            strategy="compression+retrieval+budget",
            token_count=packet.token_estimate(),
            compression_ratio=0.0,  # computed externally vs raw
        )

    def assemble_prompt(self, result: AmplificationResult) -> str:
        """Build the final prompt from a context packet."""
        packet = result.context_packet
        return (
            "You are a coding agent. Here is the context you need:\n\n"
            f"{packet.to_text()}\n\n"
            "Respond with only the necessary code or analysis."
        )
