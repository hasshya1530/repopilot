from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RepositoryFile:
    path: Path
    relative_path: str
    size_bytes: int
    extension: str
