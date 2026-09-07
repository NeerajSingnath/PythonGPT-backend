from typing import Any, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter

from app.agent.plan import PlanStatus

ToolName = Literal[
    "write_file",
    "edit_file",
    "read_file",
    "list_files",
    "search_code",
    "python_outline",
    "delete_file",
    "run_python",
    "run_tests",
    "run_command",
]


class PlanAction(BaseModel):
    type: Literal["plan"]

    reasoning: str

    steps: list[str] = Field(
        min_length=1,
        max_length=20,
    )


class PlanStepAction(BaseModel):
    type: Literal["plan_step"]

    reasoning: str

    step_id: int

    status: PlanStatus

    note: str | None = None


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
    PlanAction,
    PlanStepAction,
    ToolAction,
    FinishAction,
]


agent_action_adapter = TypeAdapter(AgentAction)
