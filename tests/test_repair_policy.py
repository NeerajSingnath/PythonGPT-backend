import json
from pathlib import Path

from app.agent.agent import PythonGPTAgent
from app.llm.base import LLMClient


class PrematureEditLLM(LLMClient):

    def __init__(self):
        self.step = 0

    def complete(self, messages):

        actions = [
            {
                "type": "tool",
                "reasoning": "I already know the bug.",
                "tool": "edit_file",
                "arguments": {
                    "path": "main.py",
                    "old_text": "return 1",
                    "new_text": "return 2",
                },
            },
            {
                "type": "tool",
                "reasoning": "Run baseline tests first.",
                "tool": "run_tests",
                "arguments": {},
            },
            {
                "type": "tool",
                "reasoning": "Now apply the repair.",
                "tool": "edit_file",
                "arguments": {
                    "path": "main.py",
                    "old_text": "return 1",
                    "new_text": "return 2",
                },
            },
            {
                "type": "tool",
                "reasoning": "Verify the repaired project.",
                "tool": "run_tests",
                "arguments": {},
            },
            {
                "type": "finish",
                "reasoning": "All tests pass.",
                "summary": "Repair verified.",
            },
        ]

        action = actions[min(self.step, len(actions) - 1)]

        self.step += 1

        return json.dumps(action)


def test_repair_requires_baseline_tests(tmp_path: Path):

    (tmp_path / "main.py").write_text(
        "def value():\n    return 1\n",
        encoding="utf-8",
    )

    (tmp_path / "test_main.py").write_text(
        "from main import value\n\n" "def test_value():\n" "    assert value() == 2\n",
        encoding="utf-8",
    )

    agent = PythonGPTAgent(
        workspace_path=tmp_path,
        llm=PrematureEditLLM(),
    )

    state = agent.run(
        "Fix the failing project.",
        mode="repair",
    )

    assert state.completed
    assert state.baseline_verification_run
    assert state.baseline_verification_failed
    assert state.verification_passed

    rejected = [event for event in state.history if event["type"] == "action_rejected"]

    assert len(rejected) == 1
