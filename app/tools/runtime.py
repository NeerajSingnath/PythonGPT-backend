import os
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4


class Runtime:

    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()

        self.mode = (
            os.getenv(
                "PYTHONGPT_RUNTIME_MODE",
                "local",
            )
            .strip()
            .lower()
        )

        self.sandbox_image = os.getenv(
            "PYTHONGPT_SANDBOX_IMAGE",
            "pythongpt-sandbox:latest",
        ).strip()

        if self.mode not in {
            "local",
            "docker",
        }:
            raise ValueError("PYTHONGPT_RUNTIME_MODE must be " "'local' or 'docker'.")

    def _safe_file(
        self,
        file: str,
    ) -> Path:
        file_path = (self.workspace / file).resolve()

        if file_path != self.workspace and self.workspace not in file_path.parents:
            raise ValueError("Invalid path")

        return file_path

    def _clear_python_cache(
        self,
    ) -> None:
        for cache_dir in self.workspace.rglob("__pycache__"):
            if cache_dir.is_dir():
                shutil.rmtree(
                    cache_dir,
                    ignore_errors=True,
                )

        for pyc_file in self.workspace.rglob("*.pyc"):
            try:
                pyc_file.unlink()
            except OSError:
                pass

    def _execution_env(
        self,
    ) -> dict[str, str]:
        env = os.environ.copy()

        env["PYTHONDONTWRITEBYTECODE"] = "1"

        env["PYTHONUNBUFFERED"] = "1"

        return env

    def _local_command(
        self,
        arguments: list[str],
        timeout: int,
        timeout_message: str,
    ) -> dict:
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    *arguments,
                ],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self._execution_env(),
                shell=False,
            )

            return {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "return_code": -1,
                "stdout": "",
                "stderr": timeout_message,
            }

        except Exception as exc:
            return {
                "success": False,
                "return_code": -1,
                "stdout": "",
                "stderr": str(exc),
            }

    def _docker_executable(
        self,
    ) -> str | None:
        return shutil.which("docker")

    def _cleanup_container(
        self,
        docker: str,
        container_name: str,
    ) -> None:
        try:
            subprocess.run(
                [
                    docker,
                    "rm",
                    "-f",
                    container_name,
                ],
                capture_output=True,
                text=True,
                timeout=5,
                shell=False,
            )
        except Exception:
            pass

    def _docker_command(
        self,
        arguments: list[str],
        timeout: int,
        timeout_message: str,
    ) -> dict:
        docker = self._docker_executable()

        if docker is None:
            return {
                "success": False,
                "return_code": -1,
                "stdout": "",
                "stderr": ("Docker is not installed " "or is not available in PATH."),
            }

        container_name = "pythongpt-" f"{uuid4().hex[:16]}"

        mount = "type=bind," f"source={self.workspace}," "target=/workspace," "readonly"

        command = [
            docker,
            "run",
            "--rm",
            "--name",
            container_name,
            "--network",
            "none",
            "--cpus",
            "1.0",
            "--memory",
            "512m",
            "--pids-limit",
            "128",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,nosuid,nodev,size=64m",
            "--mount",
            mount,
            "--workdir",
            "/workspace",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            "--env",
            "PYTHONUNBUFFERED=1",
            self.sandbox_image,
            "python",
            "-B",
            *arguments,
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )

            return {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except subprocess.TimeoutExpired:
            self._cleanup_container(
                docker,
                container_name,
            )

            return {
                "success": False,
                "return_code": -1,
                "stdout": "",
                "stderr": timeout_message,
            }

        except Exception as exc:
            self._cleanup_container(
                docker,
                container_name,
            )

            return {
                "success": False,
                "return_code": -1,
                "stdout": "",
                "stderr": str(exc),
            }

    def _execute(
        self,
        arguments: list[str],
        timeout: int,
        timeout_message: str,
    ) -> dict:
        if self.mode == "docker":
            return self._docker_command(
                arguments,
                timeout,
                timeout_message,
            )

        return self._local_command(
            arguments,
            timeout,
            timeout_message,
        )

    def run_python(
        self,
        file: str,
        timeout: int = 10,
    ) -> dict:
        try:
            file_path = self._safe_file(file)

        except ValueError as exc:
            return {
                "success": False,
                "error": str(exc),
            }

        if not file_path.exists():
            return {
                "success": False,
                "error": f"{file} does not exist",
            }

        if not file_path.is_file():
            return {
                "success": False,
                "error": f"{file} is not a file",
            }

        if file_path.suffix.lower() != ".py":
            return {
                "success": False,
                "error": ("Only Python files " "can be executed."),
            }

        self._clear_python_cache()

        relative_path = file_path.relative_to(self.workspace)

        container_path = relative_path.as_posix()

        if self.mode == "docker":
            target = container_path
        else:
            target = str(file_path)

        return self._execute(
            [
                target,
            ],
            timeout,
            "Execution timed out.",
        )

    def run_tests(
        self,
        timeout: int = 30,
    ) -> dict:
        self._clear_python_cache()

        return self._execute(
            [
                "-m",
                "pytest",
                "-q",
            ],
            timeout,
            "Tests timed out.",
        )
