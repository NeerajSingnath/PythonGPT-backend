from pathlib import Path

from app.agent.state import AgentState
from app.tools.workspace import Workspace
from app.tools.runtime import Runtime


class PythonGPTAgent:

    def __init__(self, workspace_path: Path):

        self.workspace = Workspace(workspace_path)

        self.runtime = Runtime(workspace_path)

    def create_state(self, task: str) -> AgentState:

        return AgentState(task=task)
