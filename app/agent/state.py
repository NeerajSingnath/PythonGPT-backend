from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentState:

    task: str

    plan: list[str] = field(default_factory=list)

    history: list[dict[str, Any]] = field(default_factory=list)

    iteration: int = 0

    max_iterations: int = 20

    completed: bool = False

    mode: str = "general"

    baseline_verification_run: bool = False

    baseline_verification_failed: bool = False

    verification_passed: bool = False

    changes_since_verification: bool = True

    required_quality_checks: set[str] = field(default_factory=set)

    passed_quality_checks: set[str] = field(default_factory=set)

    def add_event(
        self,
        event_type: str,
        data: Any,
    ) -> None:

        self.history.append(
            {
                "iteration": self.iteration,
                "type": event_type,
                "data": data,
            }
        )
