from pathlib import Path

from app.agent.actions import ToolAction
from app.agent.agent import PythonGPTAgent
from app.agent.plan import PlanStep


def test_quality_check_rejects_edit_file(
    tmp_path: Path,
):

    agent = PythonGPTAgent(
        workspace_path=tmp_path,
    )

    step = PlanStep(
        id=1,
        description="Run Ruff",
        kind="quality_check",
    )

    action = ToolAction(
        type="tool",
        reasoning="Remove a lint issue.",
        tool="edit_file",
        arguments={
            "path": "main.py",
            "old_text": "x",
            "new_text": "y",
        },
        plan_step_id=1,
        complete_plan_step_on="tool_success",
    )

    result = {
        "success": True,
        "replacements": 1,
    }

    allowed = agent._tool_can_complete_plan_step(
        step,
        action,
        result,
    )

    assert not allowed


def test_quality_check_accepts_successful_ruff(
    tmp_path: Path,
):

    agent = PythonGPTAgent(
        workspace_path=tmp_path,
    )

    step = PlanStep(
        id=1,
        description="Run Ruff",
        kind="quality_check",
    )

    action = ToolAction(
        type="tool",
        reasoning="Run Ruff.",
        tool="run_command",
        arguments={
            "command": "ruff",
            "arguments": ["."],
        },
        plan_step_id=1,
        complete_plan_step_on="tool_success",
    )

    result = {
        "success": True,
        "return_code": 0,
    }

    allowed = agent._tool_can_complete_plan_step(
        step,
        action,
        result,
    )

    assert allowed


def test_verification_rejects_non_test_tool(
    tmp_path: Path,
):

    agent = PythonGPTAgent(
        workspace_path=tmp_path,
    )

    step = PlanStep(
        id=1,
        description="Run final tests",
        kind="verification",
    )

    action = ToolAction(
        type="tool",
        reasoning="Inspect repository status.",
        tool="run_command",
        arguments={
            "command": "git",
            "arguments": ["status"],
        },
        plan_step_id=1,
        complete_plan_step_on="tool_success",
    )

    result = {
        "success": True,
        "return_code": 0,
    }

    allowed = agent._tool_can_complete_plan_step(
        step,
        action,
        result,
    )

    assert not allowed


def test_baseline_test_accepts_failed_test_execution(
    tmp_path: Path,
):

    agent = PythonGPTAgent(
        workspace_path=tmp_path,
    )

    step = PlanStep(
        id=1,
        description="Run baseline tests",
        kind="baseline_test",
    )

    action = ToolAction(
        type="tool",
        reasoning="Reproduce existing failures.",
        tool="run_tests",
        arguments={},
        plan_step_id=1,
        complete_plan_step_on="tool_execution",
    )

    result = {
        "success": False,
        "return_code": 1,
        "stdout": "2 failed, 1 passed",
        "stderr": "",
    }

    allowed = agent._tool_can_complete_plan_step(
        step,
        action,
        result,
    )

    assert allowed
