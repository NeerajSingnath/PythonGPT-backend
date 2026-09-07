import json
from pathlib import Path

from app.agent.agent import PythonGPTAgent
from app.llm.base import LLMClient


class AutoCompleteSuccessLLM(LLMClient):

    def __init__(self):
        self.step = 0

    def complete(self, messages):

        actions = [
            {
                "type": "plan",
                "reasoning": "Create and verify a small project.",
                "steps": [
                    "Create implementation",
                    "Run final tests",
                ],
            },
            {
                "type": "tool",
                "reasoning": "Create the implementation.",
                "tool": "write_file",
                "arguments": {
                    "path": "main.py",
                    "content": ("def add(a, b):\n" "    return a + b\n"),
                },
                "plan_step_id": 1,
                "complete_plan_step_on": "tool_success",
                "completion_note": "Implementation created.",
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
                "reasoning": "Run final tests.",
                "tool": "run_tests",
                "arguments": {},
                "plan_step_id": 2,
                "complete_plan_step_on": "tool_success",
                "completion_note": "Final tests passed.",
            },
            {
                "type": "finish",
                "reasoning": "All plan steps and verification completed.",
                "summary": "Project created and verified.",
            },
        ]

        action = actions[min(self.step, len(actions) - 1)]

        self.step += 1

        return json.dumps(action)


class AutoCompleteExecutionLLM(LLMClient):

    def __init__(self):
        self.step = 0

    def complete(self, messages):

        actions = [
            {
                "type": "plan",
                "reasoning": "Reproduce the existing failure.",
                "steps": [
                    "Run baseline tests",
                ],
            },
            {
                "type": "tool",
                "reasoning": "Run baseline tests.",
                "tool": "run_tests",
                "arguments": {},
                "plan_step_id": 1,
                "complete_plan_step_on": "tool_execution",
                "completion_note": "Baseline tests executed.",
            },
        ]

        action = actions[min(self.step, len(actions) - 1)]

        self.step += 1

        return json.dumps(action)


def test_tool_success_completes_plan_step(
    tmp_path: Path,
):

    agent = PythonGPTAgent(
        workspace_path=tmp_path,
        llm=AutoCompleteSuccessLLM(),
    )

    state = agent.run(
        "Create an add function and verify it.",
        planning_required=True,
    )

    assert state.completed
    assert state.verification_passed

    assert state.plan[0].status == "completed"
    assert state.plan[1].status == "completed"

    assert state.plan[0].note == "Implementation created."

    assert state.plan[1].note == "Final tests passed."


def test_tool_execution_completes_failed_baseline_step(
    tmp_path: Path,
):

    (tmp_path / "test_failure.py").write_text(
        """
def test_failure():
    assert False
""".strip(),
        encoding="utf-8",
    )

    agent = PythonGPTAgent(
        workspace_path=tmp_path,
        llm=AutoCompleteExecutionLLM(),
    )

    state = agent.run(
        "Run the baseline tests.",
        planning_required=True,
    )

    assert state.baseline_verification_run
    assert state.baseline_verification_failed

    assert state.plan[0].status == "completed"

    assert state.plan[0].note == "Baseline tests executed."
