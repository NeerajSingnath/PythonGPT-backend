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

    def add_event(self, event_type: str, data: Any) -> None:

        self.history.append(
            {"iteration": self.iteration, "type": event_type, "data": data}
        )
