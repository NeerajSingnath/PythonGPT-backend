import json
from pathlib import Path

from app.agent.agent import PythonGPTAgent
from app.llm.base import LLMClient


class PlannerMockLLM(LLMClient):

    def __init__(self):
        self.step = 0

    def complete(self, messages):

        actions = [
            {
                "type": "plan",
                "reasoning": "Create implementation and verify it.",
                "steps": [
                    "Create implementation",
                    "Create tests and verify",
                ],
            },
            {
                "type": "plan_step",
                "reasoning": "Begin implementation.",
                "step_id": 1,
                "status": "in_progress",
            },
            {
                "type": "tool",
                "reasoning": "Create application.",
                "tool": "write_file",
                "arguments": {
                    "path": "main.py",
                    "content": ("def add(a, b):\n" "    return a + b\n"),
                },
            },
            {
                "type": "plan_step",
                "reasoning": "Implementation completed.",
                "step_id": 1,
                "status": "completed",
            },
            {
                "type": "plan_step",
                "reasoning": "Begin verification.",
                "step_id": 2,
                "status": "in_progress",
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
                "reasoning": "Verify project.",
                "tool": "run_tests",
                "arguments": {},
            },
            {
                "type": "plan_step",
                "reasoning": "Tests passed.",
                "step_id": 2,
                "status": "completed",
            },
            {
                "type": "finish",
                "reasoning": "Plan and verification are complete.",
                "summary": "Project created and verified.",
            },
        ]

        action = actions[min(self.step, len(actions) - 1)]

        self.step += 1

        return json.dumps(action)


class SkipPlanMockLLM(LLMClient):

    def __init__(self):
        self.step = 0

    def complete(self, messages):

        actions = [
            {
                "type": "tool",
                "reasoning": "Skip planning.",
                "tool": "write_file",
                "arguments": {
                    "path": "main.py",
                    "content": "print('bad')",
                },
            },
            {
                "type": "plan",
                "reasoning": "Create proper plan.",
                "steps": [
                    "Create project",
                    "Verify project",
                ],
            },
        ]

        action = actions[min(self.step, len(actions) - 1)]

        self.step += 1

        return json.dumps(action)


def test_agent_executes_persistent_plan(
    tmp_path: Path,
):

    agent = PythonGPTAgent(
        workspace_path=tmp_path,
        llm=PlannerMockLLM(),
    )

    state = agent.run(
        "Create an add function with tests.",
        planning_required=True,
    )

    assert state.completed
    assert len(state.plan) == 2

    assert all(step.status == "completed" for step in state.plan)

    assert state.verification_passed


def test_planning_required_blocks_tools(
    tmp_path: Path,
):

    agent = PythonGPTAgent(
        workspace_path=tmp_path,
        llm=SkipPlanMockLLM(),
    )

    state = agent.run(
        "Build project.",
        planning_required=True,
    )

    rejected = [event for event in state.history if event["type"] == "action_rejected"]

    assert rejected

    assert not (tmp_path / "main.py").exists()
