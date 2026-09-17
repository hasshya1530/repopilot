from pathlib import Path

import pytest

from agents.sandbox.config import SandboxConfig
from agents.sandbox.executor import DockerSandboxExecutor


@pytest.mark.integration
def test_executes_command_in_docker(tmp_path: Path) -> None:
    executor = DockerSandboxExecutor(
        SandboxConfig(
            image="repopilot-sandbox:latest",
            timeout_seconds=30,
            memory_limit="256m",
            cpu_limit=1.0,
            network_disabled=True,
        )
    )

    result = executor.execute(
        tmp_path,
        ["python", "-c", "print('RepoPilot sandbox works')"],
    )

    assert result.succeeded
    assert result.exit_code == 0
    assert result.stdout.strip() == "RepoPilot sandbox works"
    assert result.stderr == ""
    assert result.timed_out is False


@pytest.mark.integration
def test_captures_failed_command(tmp_path: Path) -> None:
    executor = DockerSandboxExecutor(
        SandboxConfig(
            image="repopilot-sandbox:latest",
            timeout_seconds=30,
            network_disabled=True,
        )
    )

    result = executor.execute(
        tmp_path,
        [
            "python",
            "-c",
            "import sys; print('failure', file=sys.stderr); sys.exit(7)",
        ],
    )

    assert not result.succeeded
    assert result.exit_code == 7
    assert "failure" in result.stderr
    assert result.timed_out is False


@pytest.mark.integration
def test_enforces_timeout(tmp_path: Path) -> None:
    executor = DockerSandboxExecutor(
        SandboxConfig(
            image="repopilot-sandbox:latest",
            timeout_seconds=2,
            network_disabled=True,
        )
    )

    result = executor.execute(
        tmp_path,
        [
            "python",
            "-c",
            "import time; time.sleep(10)",
        ],
    )

    assert result.timed_out is True
    assert result.succeeded is False


@pytest.mark.integration
def test_network_is_disabled(tmp_path: Path) -> None:
    executor = DockerSandboxExecutor(
        SandboxConfig(
            image="repopilot-sandbox:latest",
            timeout_seconds=10,
            network_disabled=True,
        )
    )

    result = executor.execute(
        tmp_path,
        [
            "python",
            "-c",
            (
                "import socket; "
                "socket.create_connection(('example.com', 80), timeout=2)"
            ),
        ],
    )

    assert result.succeeded is False
    assert result.exit_code != 0
