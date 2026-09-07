from typing import Any

from app.tools.workspace import Workspace
from app.tools.runtime import Runtime
from app.tools.terminal import ControlledTerminal


class ToolRegistry:

    def __init__(
        self,
        workspace: Workspace,
        runtime: Runtime,
        terminal: ControlledTerminal,
    ):
        self.workspace = workspace
        self.runtime = runtime
        self.terminal = terminal

    def execute(
        self,
        tool: str,
        arguments: dict[str, Any],
    ) -> dict:

        tools = {
            "write_file": self.workspace.write_file,
            "edit_file": self.workspace.edit_file,
            "read_file": self.workspace.read_file,
            "list_files": self.workspace.list_files,
            "search_code": self.workspace.search_code,
            "python_outline": self.workspace.python_outline,
            "delete_file": self.workspace.delete_file,
            "run_python": self.runtime.run_python,
            "run_tests": self.runtime.run_tests,
            "run_command": self.terminal.run_command,
        }

        function = tools.get(tool)

        if function is None:
            return {
                "success": False,
                "error": f"Unknown tool: {tool}",
            }

        try:
            return function(**arguments)

        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
            }
