from pathlib import Path

from app.agent.state import AgentState
from app.tools.registry import ToolRegistry
from app.tools.runtime import Runtime
from app.tools.workspace import Workspace


class PythonGPTAgent:

    def __init__(self, workspace_path: Path):
        self.workspace = Workspace(workspace_path)
        self.runtime = Runtime(workspace_path)

        self.tools = ToolRegistry(workspace=self.workspace, runtime=self.runtime)

    def create_state(self, task: str) -> AgentState:
        return AgentState(task=task)

    def execute_tool(self, state: AgentState, tool: str, arguments: dict) -> dict:

        state.iteration += 1

        result = self.tools.execute(tool, arguments)

        state.add_event(
            "tool_execution", {"tool": tool, "arguments": arguments, "result": result}
        )

        return result
