from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SandboxExecutionResult:
    command: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    duration_seconds: float

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0 and not self.timed_out
