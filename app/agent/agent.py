from pathlib import Path
from typing import Optional

from app.agent.actions import FinishAction
from app.agent.parser import parse_agent_action
from app.agent.prompt import build_messages
from app.agent.state import AgentState

from app.llm.base import LLMClient

from app.tools.registry import ToolRegistry
from app.tools.runtime import Runtime
from app.tools.workspace import Workspace


class PythonGPTAgent:

    def __init__(self, workspace_path: Path, llm: Optional[LLMClient] = None):
        self.workspace = Workspace(workspace_path)

        self.runtime = Runtime(workspace_path)

        self.tools = ToolRegistry(workspace=self.workspace, runtime=self.runtime)

        self.llm = llm

    def create_state(self, task: str) -> AgentState:

        return AgentState(task=task)

    def execute_tool(self, state: AgentState, tool: str, arguments: dict) -> dict:

        state.iteration += 1

        result = self.tools.execute(tool, arguments)

        state.add_event(
            "tool_execution", {"tool": tool, "arguments": arguments, "result": result}
        )

        return result

    def run(self, task: str) -> AgentState:

        if self.llm is None:
            raise RuntimeError("An LLM client is required to run the autonomous agent.")

        state = self.create_state(task)

        while not state.completed and state.iteration < state.max_iterations:

            state.iteration += 1

            messages = build_messages(task=state.task, history=state.history)

            raw_response = self.llm.complete(messages)

            state.add_event("llm_response", raw_response)

            try:

                action = parse_agent_action(raw_response)

            except Exception as exc:

                state.add_event(
                    "invalid_action", {"error": str(exc), "response": raw_response}
                )

                continue

            if isinstance(action, FinishAction):

                state.completed = True

                state.add_event(
                    "finished",
                    {"reasoning": action.reasoning, "summary": action.summary},
                )

                break

            result = self.tools.execute(action.tool, action.arguments)

            state.add_event(
                "tool_result",
                {"tool": action.tool, "arguments": action.arguments, "result": result},
            )

        return state
