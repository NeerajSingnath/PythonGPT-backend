from httpx2 import query
from pathlib import Path
import ast


class Workspace:
    IGNORED_DIRS = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        "dist",
        "build",
    }

    IGNORED_SUFFIXES = {
        ".pyc",
        ".pyo",
        ".exe",
        ".dll",
        ".so",
        ".bin",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".ico",
        ".zip",
        ".tar",
        ".gz",
    }

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

            if not path.is_file():
                continue

            relative = path.relative_to(self.root)

            if any(part in self.IGNORED_DIRS for part in relative.parts):
                continue

            if path.suffix.lower() in (self.IGNORED_SUFFIXES):
                continue

            files.append(str(relative))

        return {
            "success": True,
            "files": sorted(files),
        }

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

    def search_code(
        self,
        query: str,
        path: str = ".",
        max_results: int = 50,
    ) -> dict:

        if not query.strip():
            return {
                "success": False,
                "error": "Search query cannot be empty.",
            }

        search_root = self._safe_path(path)

        if not search_root.exists():
            return {
                "success": False,
                "error": f"Path does not exist: {path}",
            }

        if search_root.is_file():
            candidates = [search_root]
        else:
            candidates = search_root.rglob("*")

        matches = []

        for file_path in candidates:

            if not file_path.is_file():
                continue

            relative = file_path.relative_to(self.root)

            if any(part in self.IGNORED_DIRS for part in relative.parts):
                continue

            if file_path.suffix.lower() in (self.IGNORED_SUFFIXES):
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
            except (
                UnicodeDecodeError,
                PermissionError,
                OSError,
            ):
                continue

            for line_number, line in enumerate(
                content.splitlines(),
                start=1,
            ):

                if query.lower() in line.lower():

                    matches.append(
                        {
                            "path": str(relative),
                            "line": line_number,
                            "content": line.strip(),
                        }
                    )

                    if len(matches) >= max_results:
                        return {
                            "success": True,
                            "query": query,
                            "matches": matches,
                            "truncated": True,
                        }

        return {
            "success": True,
            "query": query,
            "matches": matches,
            "truncated": False,
        }

    def python_outline(
        self,
        path: str,
    ) -> dict:

        file_path = self._safe_path(path)

        if not file_path.exists():
            return {
                "success": False,
                "error": "File not found",
            }

        if file_path.suffix != ".py":
            return {
                "success": False,
                "error": ("python_outline only supports " "Python files."),
            }

        try:
            source = file_path.read_text(encoding="utf-8")

            tree = ast.parse(
                source,
                filename=str(file_path),
            )

        except SyntaxError as exc:

            return {
                "success": False,
                "error": "Python syntax error",
                "line": exc.lineno,
                "message": exc.msg,
            }

        imports = []
        functions = []
        classes = []

        for node in tree.body:

            if isinstance(
                node,
                ast.Import,
            ):

                for alias in node.names:
                    imports.append(
                        {
                            "name": alias.name,
                            "line": node.lineno,
                        }
                    )

            elif isinstance(
                node,
                ast.ImportFrom,
            ):

                imports.append(
                    {
                        "name": (f"from {node.module}"),
                        "line": node.lineno,
                    }
                )

            elif isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):

                functions.append(
                    {
                        "name": node.name,
                        "line": node.lineno,
                        "async": isinstance(
                            node,
                            ast.AsyncFunctionDef,
                        ),
                    }
                )

            elif isinstance(
                node,
                ast.ClassDef,
            ):

                methods = []

                for item in node.body:

                    if isinstance(
                        item,
                        (
                            ast.FunctionDef,
                            ast.AsyncFunctionDef,
                        ),
                    ):

                        methods.append(
                            {
                                "name": item.name,
                                "line": item.lineno,
                                "async": isinstance(
                                    item,
                                    ast.AsyncFunctionDef,
                                ),
                            }
                        )

                classes.append(
                    {
                        "name": node.name,
                        "line": node.lineno,
                        "methods": methods,
                    }
                )

        return {
            "success": True,
            "path": path,
            "imports": imports,
            "functions": functions,
            "classes": classes,
        }
