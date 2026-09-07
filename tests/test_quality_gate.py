import json
from pathlib import Path

from app.agent.agent import PythonGPTAgent
from app.llm.base import LLMClient


class QualityGateMockLLM(LLMClient):

    def __init__(self):
        self.step = 0

    def complete(self, messages):

        actions = [
            {
                "type": "tool",
                "reasoning": "Create application code.",
                "tool": "write_file",
                "arguments": {
                    "path": "main.py",
                    "content": ("def add(a, b):\n" "    return a + b\n"),
                },
            },
            {
                "type": "tool",
                "reasoning": "Create tests.",
                "tool": "write_file",
                "arguments": {
                    "path": "test_main.py",
                    "content": (
                        "from main import add\n\n\n"
                        "def test_add():\n"
                        "    assert add(2, 3) == 5\n"
                    ),
                },
            },
            {
                "type": "tool",
                "reasoning": "Run tests.",
                "tool": "run_tests",
                "arguments": {},
            },
            # Deliberately tries to finish
            # without running Ruff.
            {
                "type": "finish",
                "reasoning": "Tests pass.",
                "summary": "Finished.",
            },
            {
                "type": "tool",
                "reasoning": "Run required linting.",
                "tool": "run_command",
                "arguments": {
                    "command": "ruff",
                    "arguments": [],
                },
            },
            {
                "type": "finish",
                "reasoning": ("Tests and Ruff both pass."),
                "summary": ("Project fully verified."),
            },
        ]

        action = actions[
            min(
                self.step,
                len(actions) - 1,
            )
        ]

        self.step += 1

        return json.dumps(action)


def test_required_quality_check_blocks_finish(
    tmp_path: Path,
):

    agent = PythonGPTAgent(
        workspace_path=tmp_path,
        llm=QualityGateMockLLM(),
    )

    state = agent.run(
        "Create a verified Python project.",
        required_quality_checks={"ruff"},
    )

    print("\n===== QUALITY GATE DEBUG =====")

    for event in state.history:
        if event["iteration"] in {4, 5, 6}:
            print(f"\nIteration {event['iteration']}" f" | {event['type']}")
            print(event["data"])

    print(
        "\npassed_quality_checks =",
        state.passed_quality_checks,
    )

    assert state.completed

    assert state.verification_passed

    assert "ruff" in (state.passed_quality_checks)

    rejected = [event for event in state.history if event["type"] == "finish_rejected"]

    assert len(rejected) == 1

    assert rejected[0]["data"]["missing_quality_checks"] == ["ruff"]
