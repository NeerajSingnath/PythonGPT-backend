from typing import Any, Literal

from pydantic import BaseModel, Field

ToolName = Literal[
    "write_file",
    "read_file",
    "list_files",
    "delete_file",
    "run_python",
    "run_tests",
]


class ToolAction(BaseModel):
    reasoning: str = Field(description="Short explanation for the next action.")

    tool: ToolName

    arguments: dict[str, Any]


class FinishAction(BaseModel):
    reasoning: str

    completed: bool = True

    summary: str
