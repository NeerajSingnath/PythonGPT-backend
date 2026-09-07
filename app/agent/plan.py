from typing import Literal

from pydantic import BaseModel

PlanStatus = Literal[
    "pending",
    "in_progress",
    "completed",
    "blocked",
]


PlanKind = Literal[
    "general",
    "inspection",
    "baseline_test",
    "diagnosis",
    "implementation",
    "quality_check",
    "verification",
    "review",
]


class PlanStep(BaseModel):
    id: int
    description: str
    kind: PlanKind = "general"
    status: PlanStatus = "pending"
    note: str | None = None
