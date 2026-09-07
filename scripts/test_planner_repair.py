import shutil
import subprocess
from pathlib import Path

from app.agent.agent import PythonGPTAgent
from app.llm.nvidia import NvidiaLLMClient

workspace = Path("workspaces/planner_repair")

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

- Create a clear engineering plan before using tools.
- Inspect the repository.
- Run baseline tests before modifying files.
- Diagnose failures using actual test output.
- Make minimal surgical changes.
- Do not weaken or delete tests.
- Run Ruff and fix lint problems.
- Inspect the final git diff.
- Run the full test suite after all modifications.
- Keep the plan updated as work progresses.
- Mark plan steps completed only after obtaining evidence.
- Do not finish until the plan and all verification are complete.
""",
    mode="repair",
    required_quality_checks={"ruff"},
    planning_required=True,
)

print("\n===== PythonGPT Planner Repair =====")

print("Completed:", state.completed)
print("Iterations:", state.iteration)
print("Tests verified:", state.verification_passed)
print("Quality checks:", state.passed_quality_checks)

print("\n===== Final Plan =====")

for step in state.plan:
    print(f"{step.id}. " f"[{step.status}] " f"{step.description}")

    if step.note:
        print(f"   {step.note}")

print("\n===== Agent History =====")

for event in state.history:
    print(f"\n[{event['iteration']}] " f"{event['type']}")

    print(event["data"])
