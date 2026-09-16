from abc import ABC, abstractmethod

from ingestion.graph.models import SymbolRelationship


class RelationshipParser(ABC):
    """Extract source-level relationships from source code."""

    @abstractmethod
    def parse(
        self,
        source: bytes,
        file_path: str,
    ) -> list[SymbolRelationship]:
        """Parse source code and return extracted relationships."""
