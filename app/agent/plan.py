from typing import Literal

from pydantic import BaseModel

PlanStatus = Literal[
    "pending",
    "in_progress",
    "completed",
    "blocked",
]


class PlanStep(BaseModel):
    id: int
    description: str
    status: PlanStatus = "pending"
    note: str | None = None
