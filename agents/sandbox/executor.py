from __future__ import annotations

import subprocess
import time
from pathlib import Path

from agents.sandbox.config import SandboxConfig
from agents.sandbox.errors import (
    SandboxConfigurationError,
    SandboxExecutionError,
)
from agents.sandbox.models import SandboxExecutionResult


class DockerSandboxExecutor:
    """Execute repository commands inside an isolated Docker container."""

    def __init__(self, config: SandboxConfig | None = None) -> None:
        self._config = config or SandboxConfig()

    def execute(
        self,
        workspace_path: Path,
        command: list[str],
    ) -> SandboxExecutionResult:
        workspace = workspace_path.resolve()

        self._validate_workspace(workspace)
        self._validate_command(command)

        docker_command = self._build_docker_command(
            workspace,
            command,
        )

        started = time.monotonic()

        try:
            completed = subprocess.run(
                docker_command,
                capture_output=True,
                text=True,
                timeout=self._config.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.monotonic() - started

            return SandboxExecutionResult(
                command=tuple(command),
                exit_code=-1,
                stdout=(
                    exc.stdout.decode()
                    if isinstance(exc.stdout, bytes)
                    else (exc.stdout or "")
                ),
                stderr=(
                    exc.stderr.decode()
                    if isinstance(exc.stderr, bytes)
                    else (exc.stderr or "")
                ),
                timed_out=True,
                duration_seconds=duration,
            )
        except OSError as exc:
            raise SandboxExecutionError(
                f"Failed to start Docker sandbox: {exc}"
            ) from exc

        duration = time.monotonic() - started

        return SandboxExecutionResult(
            command=tuple(command),
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            timed_out=False,
            duration_seconds=duration,
        )

    def _build_docker_command(
        self,
        workspace: Path,
        command: list[str],
    ) -> list[str]:
        docker_command = [
            "docker",
            "run",
            "--rm",
            "--init",
            "--memory",
            self._config.memory_limit,
            "--cpus",
            str(self._config.cpu_limit),
            "--pids-limit",
            "256",
            "--security-opt",
            "no-new-privileges",
        ]

        if self._config.network_disabled:
            docker_command.extend(["--network", "none"])

        if self._config.read_only:
            docker_command.append("--read-only")

        docker_command.extend(
            [
                "--mount",
                (
                    f"type=bind,source={workspace},"
                    "target=/workspace"
                ),
                "--workdir",
                "/workspace",
                self._config.image,
                *command,
            ]
        )

        return docker_command

    @staticmethod
    def _validate_workspace(workspace: Path) -> None:
        if not workspace.exists():
            raise SandboxConfigurationError(
                f"Workspace does not exist: {workspace}"
            )

        if not workspace.is_dir():
            raise SandboxConfigurationError(
                f"Workspace is not a directory: {workspace}"
            )

    @staticmethod
    def _validate_command(command: list[str]) -> None:
        if not command:
            raise SandboxConfigurationError(
                "Sandbox command cannot be empty."
            )

        for argument in command:
            if "\x00" in argument:
                raise SandboxConfigurationError(
                    "Sandbox command contains a null byte."
                )
