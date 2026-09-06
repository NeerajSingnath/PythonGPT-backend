import json
import re

from app.agent.actions import (
    AgentAction,
    agent_action_adapter,
)


def parse_agent_action(raw_response: str) -> AgentAction:

    text = raw_response.strip()

    # Remove Nemotron reasoning blocks
    text = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL,
    ).strip()

    # Handle case where only closing tag appears
    if "</think>" in text:
        text = text.split("</think>", 1)[1].strip()

    # Remove markdown code fences
    text = text.replace("```json", "")
    text = text.replace("```", "")
    text = text.strip()

    # Find the first valid JSON object
    decoder = json.JSONDecoder()

    for index, char in enumerate(text):

        if char != "{":
            continue

        try:
            data, _ = decoder.raw_decode(text[index:])

            return agent_action_adapter.validate_python(data)

        except json.JSONDecodeError:
            continue

    raise ValueError(f"No valid JSON action found in LLM response: {raw_response}")
