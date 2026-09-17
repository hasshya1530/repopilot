from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GitResult:
    command: tuple[str, ...]
    return_code: int
    stdout: str
    stderr: str


@dataclass(frozen=True, slots=True)
class WorkspaceInfo:
    path: str
    branch_name: str
    commit_sha: str
    is_clean: bool
