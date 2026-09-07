import os
import re
import shutil
import stat
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

        return path

    def list_workspaces(
        self,
    ) -> list[dict]:

        workspaces = []

        for path in sorted(self.root.iterdir()):
            if not path.is_dir():
                continue

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
