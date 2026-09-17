from pathlib import Path

import pytest

from agents.sandbox.config import SandboxConfig
from agents.sandbox.errors import SandboxConfigurationError
from agents.sandbox.executor import DockerSandboxExecutor


def test_rejects_missing_workspace(tmp_path: Path) -> None:
    executor = DockerSandboxExecutor()

    with pytest.raises(SandboxConfigurationError):
        executor.execute(
            tmp_path / "missing",
            ["python", "-c", "print('hello')"],
        )


def test_rejects_empty_command(tmp_path: Path) -> None:
    executor = DockerSandboxExecutor()

    with pytest.raises(SandboxConfigurationError):
        executor.execute(tmp_path, [])


def test_rejects_null_byte(tmp_path: Path) -> None:
    executor = DockerSandboxExecutor()

    with pytest.raises(SandboxConfigurationError):
        executor.execute(
            tmp_path,
            ["python", "-c", "print('\x00')"],
        )


def test_builds_network_disabled_command(tmp_path: Path) -> None:
    executor = DockerSandboxExecutor(
        SandboxConfig(
            image="test-image",
            timeout_seconds=10,
            memory_limit="256m",
            cpu_limit=0.5,
            network_disabled=True,
        )
    )

    command = executor._build_docker_command(
        tmp_path,
        ["python", "-c", "print('hello')"],
    )

    assert "--network" in command
    assert command[command.index("--network") + 1] == "none"
    assert "--memory" in command
    assert "256m" in command
    assert "--cpus" in command
    assert "0.5" in command
    assert "--pids-limit" in command
    assert "256" in command
    assert "--security-opt" in command
    assert "no-new-privileges" in command


def test_builds_read_only_command(tmp_path: Path) -> None:
    executor = DockerSandboxExecutor(
        SandboxConfig(
            image="test-image",
            read_only=True,
        )
    )

    command = executor._build_docker_command(
        tmp_path,
        ["python", "--version"],
    )

    assert "--read-only" in command
