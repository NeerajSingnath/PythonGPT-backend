import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

WORKSPACE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,100}$")


class WorkspaceManager:

    def __init__(
        self,
        root: Path | str = "workspaces",
    ):
        self.root = Path(root).resolve()

        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )

    def validate_name(
        self,
        name: str,
    ) -> str:
        if not WORKSPACE_NAME_PATTERN.fullmatch(name):
            raise ValueError(
                "Workspace name may contain only "
                "letters, numbers, hyphens and underscores."
            )

        return name

    def get_path(
        self,
        name: str,
    ) -> Path:
        self.validate_name(name)

        path = (self.root / name).resolve()

        if path != self.root and self.root not in path.parents:
            raise ValueError("Invalid workspace path.")

        return path

    def exists(
        self,
        name: str,
    ) -> bool:
        return self.get_path(name).is_dir()

    def _git_executable(
        self,
    ) -> str:
        git = shutil.which("git")

        if git is None:
            raise RuntimeError("Git is not installed " "or is not available in PATH.")

        return git

    def _run_git(
        self,
        path: Path,
        arguments: list[str],
    ) -> str:
        git = self._git_executable()

        try:
            result = subprocess.run(
                [
                    git,
                    *arguments,
                ],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=15,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Git command timed out.") from exc
        except OSError as exc:
            raise RuntimeError(f"Unable to execute Git: {exc}") from exc

        if result.returncode != 0:
            message = (
                result.stderr.strip() or result.stdout.strip() or "Git command failed."
            )

            raise RuntimeError(message)

        return result.stdout.strip()

    def _try_git(
        self,
        path: Path,
        arguments: list[str],
    ) -> tuple[bool, str]:
        git = self._git_executable()

        try:
            result = subprocess.run(
                [
                    git,
                    *arguments,
                ],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=15,
                shell=False,
            )
        except (
            subprocess.TimeoutExpired,
            OSError,
        ):
            return False, ""

        return (
            result.returncode == 0,
            result.stdout.strip(),
        )

    def _has_head(
        self,
        path: Path,
    ) -> bool:
        success, _ = self._try_git(
            path,
            [
                "rev-parse",
                "--verify",
                "HEAD",
            ],
        )

        return success

    def _is_managed_repository(
        self,
        path: Path,
    ) -> bool:
        success, value = self._try_git(
            path,
            [
                "config",
                "--local",
                "--get",
                "pythongpt.managed",
            ],
        )

        return success and value.lower() == "true"

    def _mark_legacy_managed_repository(
        self,
        path: Path,
    ) -> None:
        if self._is_managed_repository(path):
            return

        if self._has_head(path):
            return

        name_success, name = self._try_git(
            path,
            [
                "config",
                "--local",
                "--get",
                "user.name",
            ],
        )

        email_success, email = self._try_git(
            path,
            [
                "config",
                "--local",
                "--get",
                "user.email",
            ],
        )

        if (
            name_success
            and email_success
            and name == "PythonGPT"
            and email == "pythongpt@local"
        ):
            self._run_git(
                path,
                [
                    "config",
                    "pythongpt.managed",
                    "true",
                ],
            )

    def _ensure_git_repository(
        self,
        path: Path,
    ) -> None:
        git_metadata = path / ".git"

        if git_metadata.exists():
            self._mark_legacy_managed_repository(path)
            return

        self._run_git(
            path,
            [
                "init",
                "--initial-branch=main",
            ],
        )

        self._run_git(
            path,
            [
                "config",
                "user.name",
                "PythonGPT",
            ],
        )

        self._run_git(
            path,
            [
                "config",
                "user.email",
                "pythongpt@local",
            ],
        )

        self._run_git(
            path,
            [
                "config",
                "core.autocrlf",
                "false",
            ],
        )

        self._run_git(
            path,
            [
                "config",
                "core.filemode",
                "false",
            ],
        )

        self._run_git(
            path,
            [
                "config",
                "pythongpt.managed",
                "true",
            ],
        )

    def ensure_git_repository(
        self,
        name: str,
    ) -> Path:
        path = self.get_path(name)

        if not path.is_dir():
            raise FileNotFoundError(f"Workspace not found: {name}")

        self._ensure_git_repository(path)

        return path

    def prepare_run_baseline(
        self,
        name: str,
        run_id: str,
    ) -> bool:
        path = self.ensure_git_repository(name)

        if not self._is_managed_repository(path):
            return False

        self._run_git(
            path,
            [
                "add",
                "-A",
            ],
        )

        self._run_git(
            path,
            [
                "-c",
                "commit.gpgSign=false",
                "commit",
                "--allow-empty",
                "--no-verify",
                "-m",
                f"PythonGPT baseline {run_id}",
            ],
        )

        return True

    def create(
        self,
        name: str,
    ) -> Path:
        path = self.get_path(name)

        if path.exists():
            raise FileExistsError(f"Workspace already exists: {name}")

        path.mkdir(
            parents=True,
            exist_ok=False,
        )

        try:
            self._ensure_git_repository(path)
        except Exception:
            shutil.rmtree(
                path,
                onexc=self._remove_readonly,
            )
            raise

        return path

    def list_workspaces(
        self,
    ) -> list[dict]:
        workspaces = []

        for path in sorted(self.root.iterdir()):
            if not path.is_dir():
                continue

            self._ensure_git_repository(path)

            files = 0

            for item in path.rglob("*"):
                if not item.is_file():
                    continue

                if ".git" in item.parts:
                    continue

                if ".venv" in item.parts:
                    continue

                if "__pycache__" in item.parts:
                    continue

                files += 1

            workspaces.append(
                {
                    "name": path.name,
                    "files": files,
                }
            )

        return workspaces

    def delete(
        self,
        name: str,
    ) -> None:
        path = self.get_path(name)

        if not path.exists():
            raise FileNotFoundError(f"Workspace not found: {name}")

        shutil.rmtree(
            path,
            onexc=self._remove_readonly,
        )

    @staticmethod
    def _remove_readonly(
        func,
        path,
        exc,
    ) -> None:
        if isinstance(
            exc,
            PermissionError,
        ):
            os.chmod(
                path,
                stat.S_IWRITE,
            )

            func(path)
            return

        raise exc
