import json

from app.agent.actions import (
    AgentAction,
    agent_action_adapter,
)


def parse_agent_action(raw_response: str) -> AgentAction:

    raw_response = raw_response.strip()

    if raw_response.startswith("```"):
        raw_response = raw_response.removeprefix("```json")
        raw_response = raw_response.removeprefix("```")
        raw_response = raw_response.removesuffix("```")
        raw_response = raw_response.strip()

    data = json.loads(raw_response)

    return agent_action_adapter.validate_python(data)
