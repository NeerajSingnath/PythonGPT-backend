from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.agent.plan import PlanStep

EventCallback = Callable[
    [dict[str, Any]],
    None,
]

CancellationCheck = Callable[
    [],
    bool,
]


@dataclass
class AgentState:
    task: str

    plan: list[PlanStep] = field(default_factory=list)

    history: list[dict[str, Any]] = field(default_factory=list)

    iteration: int = 0
    max_iterations: int = 50

    completed: bool = False
    cancelled: bool = False

    mode: str = "general"
    planning_required: bool = False

    baseline_verification_run: bool = False
    baseline_verification_failed: bool = False

    verification_passed: bool = False
    changes_since_verification: bool = True

    required_quality_checks: set[str] = field(default_factory=set)

    passed_quality_checks: set[str] = field(default_factory=set)

    event_callback: EventCallback | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    def add_event(
        self,
        event_type: str,
        data: Any,
    ) -> None:
        event = {
            "iteration": self.iteration,
            "type": event_type,
            "data": data,
        }

        self.history.append(event)

        if self.event_callback is not None:
            self.event_callback(event)
