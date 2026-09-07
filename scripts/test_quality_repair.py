import shutil
import subprocess
from pathlib import Path

from app.agent.agent import PythonGPTAgent
from app.llm.nvidia import NvidiaLLMClient

workspace = Path("workspaces/quality_repair")


if workspace.exists():
    shutil.rmtree(workspace)

workspace.mkdir(
    parents=True,
    exist_ok=True,
)


(workspace / "calculator.py").write_text(
    """
import os


def add(a, b):
    return a + b


def divide(a, b):
    return a * b
""".strip(),
    encoding="utf-8",
)


(workspace / "test_calculator.py").write_text(
    """
import pytest

from calculator import add, divide


def test_add():
    assert add(2, 3) == 5


def test_divide():
    assert divide(10, 2) == 5


def test_divide_zero():
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)
""".strip(),
    encoding="utf-8",
)


subprocess.run(
    ["git", "init"],
    cwd=workspace,
    check=True,
    capture_output=True,
)

subprocess.run(
    [
        "git",
        "add",
        "calculator.py",
        "test_calculator.py",
    ],
    cwd=workspace,
    check=True,
    capture_output=True,
)


llm = NvidiaLLMClient(
    thinking=True,
    medium_effort=True,
)


agent = PythonGPTAgent(
    workspace_path=workspace,
    llm=llm,
)


state = agent.run(
    """
Repair this existing Python project.

Requirements:

- Inspect the repository.
- Run the baseline test suite before modifying files.
- Diagnose failures using actual test output.
- Make minimal surgical edits.
- Do not delete or weaken existing tests.
- Run Ruff and fix all lint issues.
- Inspect git diff before completion.
- Run the complete test suite after all modifications.
- Do not finish until all required verification passes.
""",
    mode="repair",
    required_quality_checks={"ruff"},
)


print("\n===== PythonGPT Quality Repair =====")

print("Completed:", state.completed)
print("Iterations:", state.iteration)
print("Tests verified:", state.verification_passed)
print("Quality checks:", state.passed_quality_checks)

print("\n===== Agent History =====")

for event in state.history:

    print(f"\n[{event['iteration']}] " f"{event['type']}")

    print(event["data"])
