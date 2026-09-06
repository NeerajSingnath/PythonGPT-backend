import json
from pathlib import Path

from app.agent.agent import PythonGPTAgent
from app.llm.base import LLMClient


class VerificationMockLLM(LLMClient):

    def __init__(self):
        self.step = 0

    def complete(self, messages):

        actions = [
            {
                "type": "tool",
                "reasoning": "Create application.",
                "tool": "write_file",
                "arguments": {
                    "path": "main.py",
                    "content": "def add(a, b): return a + b",
                },
            },
            {
                "type": "tool",
                "reasoning": "Create tests.",
                "tool": "write_file",
                "arguments": {
                    "path": "test_main.py",
                    "content": (
                        "from main import add\n\n"
                        "def test_add():\n"
                        "    assert add(2, 3) == 5\n"
                    ),
                },
            },
            # Deliberately try to cheat
            {
                "type": "finish",
                "reasoning": "Code looks correct.",
                "summary": "Finished.",
            },
            {
                "type": "tool",
                "reasoning": "Verify project.",
                "tool": "run_tests",
                "arguments": {},
            },
            {
                "type": "finish",
                "reasoning": "Tests passed.",
                "summary": "Project verified.",
            },
        ]

        action = actions[min(self.step, len(actions) - 1)]

        self.step += 1

        return json.dumps(action)


def test_agent_cannot_finish_without_verification(tmp_path: Path):

    agent = PythonGPTAgent(workspace_path=tmp_path, llm=VerificationMockLLM())

    state = agent.run("Create and verify a simple project.")

    assert state.completed
    assert state.verification_passed

    rejected = [event for event in state.history if event["type"] == "finish_rejected"]

    assert len(rejected) == 1
