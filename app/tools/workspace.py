from pathlib import Path


class Workspace:

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, relative_path: str) -> Path:
        path = (self.root / relative_path).resolve()

        if path != self.root and self.root not in path.parents:
            raise ValueError("Path escapes workspace.")

        return path

    def write_file(self, path: str, content: str) -> dict:

        file_path = self._safe_path(path)

        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_path.write_text(content, encoding="utf-8")

        return {"success": True, "path": path}

    def read_file(self, path: str) -> dict:

        file_path = self._safe_path(path)

        if not file_path.exists():
            return {"success": False, "error": "File not found"}

        return {
            "success": True,
            "path": path,
            "content": file_path.read_text(encoding="utf-8"),
        }

    def list_files(self) -> dict:

        files = []

        for path in self.root.rglob("*"):

            if path.is_file():
                files.append(str(path.relative_to(self.root)))

        return {"success": True, "files": sorted(files)}

    def delete_file(self, path: str) -> dict:

        file_path = self._safe_path(path)

        if not file_path.exists():
            return {"success": False, "error": "File not found"}

        file_path.unlink()

        return {"success": True, "path": path}

    def edit_file(self, path: str, old_text: str, new_text: str) -> dict:

        file_path = self._safe_path(path)

        if not file_path.exists():
            return {"success": False, "error": "File not found"}

        content = file_path.read_text(encoding="utf-8")

        occurrences = content.count(old_text)

        if occurrences == 0:
            return {
                "success": False,
                "error": (
                    "Target text was not found. " "Read the file again before editing."
                ),
            }

        if occurrences > 1:
            return {
                "success": False,
                "error": (
                    f"Target text occurs {occurrences} times. "
                    "Provide a more specific old_text."
                ),
            }

        updated = content.replace(old_text, new_text, 1)

        file_path.write_text(updated, encoding="utf-8")

        return {"success": True, "path": path, "replacements": 1}
