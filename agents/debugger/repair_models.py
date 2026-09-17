from dataclasses import dataclass

from agents.implementer.models import CodeChange


@dataclass(frozen=True, slots=True)
class RepairProposal:
    diagnosis: str
    changes: tuple[CodeChange, ...]
