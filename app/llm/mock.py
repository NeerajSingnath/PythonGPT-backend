import json

from app.llm.base import LLMClient


class MockLLMClient(LLMClient):

    def __init__(self):

        self.step = 0

    def complete(self, messages: list[dict[str, str]]) -> str:

        actions = [
            {
                "type": "tool",
                "reasoning": "Create calculator implementation.",
                "tool": "write_file",
                "arguments": {
                    "path": "calculator.py",
                    "content": """
def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")

    return a / b
""".strip(),
                },
            },
            {
                "type": "tool",
                "reasoning": "Create tests for calculator.",
                "tool": "write_file",
                "arguments": {
                    "path": "test_calculator.py",
                    "content": """
from calculator import (
    add,
    subtract,
    multiply,
    divide,
)


def test_add():
    assert add(2, 3) == 5


def test_subtract():
    assert subtract(10, 4) == 6


def test_multiply():
    assert multiply(3, 4) == 12


def test_divide():
    assert divide(10, 2) == 5
""".strip(),
                },
            },
            {
                "type": "tool",
                "reasoning": "Run the test suite.",
                "tool": "run_tests",
                "arguments": {},
            },
            {
                "type": "finish",
                "reasoning": "Calculator was implemented and tested.",
                "summary": "Created calculator.py and test_calculator.py and verified the tests.",
            },
        ]

        action = actions[min(self.step, len(actions) - 1)]

        self.step += 1

        return json.dumps(action)
