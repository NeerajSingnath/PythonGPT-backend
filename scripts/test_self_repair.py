from pathlib import Path
import shutil

from app.agent.agent import PythonGPTAgent
from app.llm.nvidia import NvidiaLLMClient

workspace = Path("workspaces/broken_calculator")

# Clean previous run
if workspace.exists():
    shutil.rmtree(workspace)

workspace.mkdir(parents=True, exist_ok=True)


# Intentionally broken implementation
(workspace / "calculator.py").write_text(
    """
def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    return a * b
""".strip(),
    encoding="utf-8",
)


# Existing tests
(workspace / "test_calculator.py").write_text(
    """
import pytest

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


def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)
""".strip(),
    encoding="utf-8",
)


llm = NvidiaLLMClient(
    thinking=True,
    medium_effort=True,
)


agent = PythonGPTAgent(
    workspace_path=workspace,
    llm=llm,
)


state = agent.run("""
Fix this existing Python project.

Requirements:

- Inspect the existing repository.
- Run the tests to identify the actual failures.
- Diagnose the root cause from the test output.
- Modify only what is necessary.
- Do not weaken or delete the existing tests.
- Run the full test suite again after fixing the code.
- Do not finish until all tests pass.
""")


print("\n===== PythonGPT Self Repair =====")
print("Completed:", state.completed)
print("Iterations:", state.iteration)


print("\n===== Agent History =====")

for event in state.history:

    print(f"\n[{event['iteration']}] " f"{event['type']}")

    print(event["data"])
