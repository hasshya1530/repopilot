from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SandboxConfig:
    image: str = "repopilot-sandbox:latest"
    timeout_seconds: int = 300
    memory_limit: str = "512m"
    cpu_limit: float = 1.0
    network_disabled: bool = True
    read_only: bool = False
