from typing import Any, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter

ToolName = Literal[
    "write_file",
    "edit_file",
    "read_file",
    "list_files",
    "delete_file",
    "run_python",
    "run_tests",
    "run_command",
]


class ToolAction(BaseModel):
    type: Literal["tool"]

    reasoning: str = Field(description="Brief reason for taking this action.")

    tool: ToolName

    arguments: dict[str, Any]


class FinishAction(BaseModel):
    type: Literal["finish"]

    reasoning: str

    summary: str


AgentAction = Union[
    ToolAction,
    FinishAction,
]


agent_action_adapter = TypeAdapter(AgentAction)
