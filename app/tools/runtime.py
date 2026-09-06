import subprocess
import sys
from pathlib import Path


class Runtime:

    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()

    def run_python(self, file: str, timeout: int = 10) -> dict:

        file_path = (self.workspace / file).resolve()

        if file_path != self.workspace and self.workspace not in file_path.parents:
            return {"success": False, "error": "Invalid path"}

        if not file_path.exists():
            return {"success": False, "error": f"{file} does not exist"}

        try:

            result = subprocess.run(
                [sys.executable, str(file_path)],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=timeout,
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

    def run_tests(self, timeout: int = 30) -> dict:

        try:

            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q"],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=timeout,
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
