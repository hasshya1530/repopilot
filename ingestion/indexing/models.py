from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IndexingResult:
    discovered_files: int
    parsed_files: int
    chunks_created: int
    embeddings_created: int
