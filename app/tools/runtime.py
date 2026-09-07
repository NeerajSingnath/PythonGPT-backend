import os
import shutil
import subprocess
import sys
from pathlib import Path


class Runtime:

    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()

    def _clear_python_cache(self) -> None:
        """
        Remove Python bytecode caches from the workspace.

        This prevents stale .pyc files from being reused after
        PythonGPT makes very fast source-code modifications.
        """

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

    def _execution_env(self) -> dict[str, str]:

        env = os.environ.copy()

        # Prevent new bytecode cache files from being written
        # during PythonGPT verification runs.
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        return env

    def run_python(
        self,
        file: str,
        timeout: int = 10,
    ) -> dict:

        file_path = (self.workspace / file).resolve()

        if file_path != self.workspace and self.workspace not in file_path.parents:
            return {
                "success": False,
                "error": "Invalid path",
            }

        if not file_path.exists():
            return {
                "success": False,
                "error": (f"{file} does not exist"),
            }

        self._clear_python_cache()

        try:

            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(file_path),
                ],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self._execution_env(),
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
                "stderr": "Execution timed out.",
            }

        except Exception as exc:

            return {
                "success": False,
                "return_code": -1,
                "stdout": "",
                "stderr": str(exc),
            }

    def run_tests(
        self,
        timeout: int = 30,
    ) -> dict:

        # Always verify against fresh source code.
        self._clear_python_cache()

        try:

            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "pytest",
                    "-q",
                ],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self._execution_env(),
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
                "stderr": "Tests timed out.",
            }

        except Exception as exc:

            return {
                "success": False,
                "return_code": -1,
                "stdout": "",
                "stderr": str(exc),
            }
