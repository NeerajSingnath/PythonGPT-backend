import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


class ControlledTerminal:

    def __init__(
        self,
        workspace: Path,
    ):
        self.workspace = workspace.resolve()

    def _safe_path(
        self,
        value: str,
    ) -> str:
        path = (self.workspace / value).resolve()

        if path != self.workspace and self.workspace not in path.parents:
            raise ValueError(f"Path escapes workspace: {value}")

        return str(path)

    def _run(
        self,
        argv: list[str],
        timeout: int = 60,
    ) -> dict[str, Any]:
        try:
            result = subprocess.run(
                argv,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )

            return {
                "success": result.returncode == 0,
                "command": argv,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "command": argv,
                "return_code": -1,
                "stdout": "",
                "stderr": "Command timed out.",
            }

        except Exception as exc:
            return {
                "success": False,
                "command": argv,
                "return_code": -1,
                "stdout": "",
                "stderr": str(exc),
            }

    def run_command(
        self,
        command: str,
        arguments: list[str] | None = None,
    ) -> dict:
        arguments = arguments or []

        if command == "pytest":
            return self._pytest(arguments)

        if command == "ruff":
            return self._ruff(arguments)

        if command == "mypy":
            return self._mypy(arguments)

        if command == "git":
            return self._git(arguments)

        if command == "python":
            return self._python(arguments)

        if command == "uv":
            return self._uv(arguments)

        return {
            "success": False,
            "error": f"Command '{command}' is not allowed.",
        }

    def _python(
        self,
        arguments: list[str],
    ) -> dict:
        if not arguments:
            return {
                "success": False,
                "error": "Python requires a file path.",
            }

        if arguments[0].startswith("-"):
            return {
                "success": False,
                "error": ("Python interpreter flags " "are not allowed."),
            }

        target = self._safe_path(arguments[0])

        if not target.endswith(".py"):
            return {
                "success": False,
                "error": ("Python can only execute " ".py files inside the workspace."),
            }

        return self._run(
            [
                sys.executable,
                target,
                *arguments[1:],
            ]
        )

    def _pytest(
        self,
        arguments: list[str],
    ) -> dict:
        allowed_flags = {
            "-q",
            "-v",
            "-x",
            "-s",
            "--disable-warnings",
            "--tb=short",
            "--tb=line",
            "--tb=no",
        }

        validated = []

        for argument in arguments:
            if argument in allowed_flags:
                validated.append(argument)
                continue

            if argument.startswith("--maxfail="):
                value = argument.split(
                    "=",
                    1,
                )[1]

                if value.isdigit():
                    validated.append(argument)
                    continue

            if not argument.startswith("-"):
                validated.append(self._safe_path(argument))
                continue

            return {
                "success": False,
                "error": ("pytest argument not " f"allowed: {argument}"),
            }

        return self._run(
            [
                sys.executable,
                "-m",
                "pytest",
                *validated,
            ]
        )

    def _ruff(
        self,
        arguments: list[str],
    ) -> dict:
        for argument in arguments:
            if argument == "--fix" or argument.startswith("--fix="):
                return {
                    "success": False,
                    "error": (
                        "ruff --fix is not allowed. "
                        "PythonGPT must make edits "
                        "through edit_file."
                    ),
                }

        executable_name = "ruff.exe" if os.name == "nt" else "ruff"

        executable_path = Path(sys.executable).parent / executable_name

        if executable_path.exists():
            executable = str(executable_path)
        else:
            executable = shutil.which("ruff")

        if executable is None:
            return {
                "success": True,
                "stdout": "",
                "stderr": "",
            }

        return self._run(
            [
                executable,
                "check",
                ".",
            ]
        )

    def _mypy(
        self,
        arguments: list[str],
    ) -> dict:
        paths = arguments or ["."]

        validated = []

        for path in paths:
            if path.startswith("-"):
                return {
                    "success": False,
                    "error": ("Custom mypy flags " "are not allowed yet."),
                }

            validated.append(self._safe_path(path))

        return self._run(
            [
                sys.executable,
                "-m",
                "mypy",
                *validated,
            ]
        )

    def _git(
        self,
        arguments: list[str],
    ) -> dict:
        executable = shutil.which("git")

        if executable is None:
            return {
                "success": False,
                "error": "git is not installed.",
            }

        if not arguments:
            return {
                "success": False,
                "error": ("A git subcommand " "is required."),
            }

        subcommand = arguments[0]

        allowed = {
            "status",
            "diff",
            "log",
            "show",
            "rev-parse",
            "ls-files",
        }

        if subcommand not in allowed:
            return {
                "success": False,
                "error": (f"git {subcommand} " "is not allowed."),
            }

        allowed_options = {
            "--short",
            "--stat",
            "--cached",
            "--oneline",
        }

        safe_args = []

        for argument in arguments[1:]:
            if argument.startswith("-"):
                if argument not in allowed_options:
                    return {
                        "success": False,
                        "error": ("Git option " "not allowed: " f"{argument}"),
                    }

            safe_args.append(argument)

        scoped_commands = {
            "status",
            "diff",
            "log",
            "show",
            "ls-files",
        }

        if subcommand in scoped_commands:
            safe_args.extend(
                [
                    "--",
                    ".",
                ]
            )

        return self._run(
            [
                executable,
                subcommand,
                *safe_args,
            ]
        )

    def _uv(
        self,
        arguments: list[str],
    ) -> dict:
        executable = shutil.which("uv")

        if executable is None:
            return {
                "success": False,
                "error": "uv is not installed.",
            }

        allowed_patterns = {
            ("version",),
            ("tree",),
            (
                "pip",
                "list",
            ),
            (
                "pip",
                "freeze",
            ),
        }

        pattern = tuple(arguments)

        if pattern not in allowed_patterns:
            return {
                "success": False,
                "error": ("This uv operation " "is not allowed."),
            }

        return self._run(
            [
                executable,
                *arguments,
            ]
        )
