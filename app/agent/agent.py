from pathlib import Path
from typing import Optional

from app.agent.actions import (
    FinishAction,
    PlanAction,
    PlanStepAction,
)
from app.agent.parser import parse_agent_action
from app.agent.plan import PlanStep
from app.agent.prompt import build_messages
from app.agent.state import AgentState

from app.llm.base import LLMClient

from app.tools.registry import ToolRegistry
from app.tools.runtime import Runtime
from app.tools.terminal import ControlledTerminal
from app.tools.workspace import Workspace

SUPPORTED_QUALITY_CHECKS = {
    "ruff",
    "mypy",
}


class PythonGPTAgent:

    def __init__(
        self,
        workspace_path: Path,
        llm: Optional[LLMClient] = None,
    ):
        self.workspace = Workspace(workspace_path)

        self.runtime = Runtime(workspace_path)

        self.terminal = ControlledTerminal(workspace_path)

        self.tools = ToolRegistry(
            workspace=self.workspace,
            runtime=self.runtime,
            terminal=self.terminal,
        )

        self.llm = llm

    def create_state(
        self,
        task: str,
        mode: str = "general",
        required_quality_checks: set[str] | None = None,
        planning_required: bool = False,
    ) -> AgentState:

        return AgentState(
            task=task,
            mode=mode,
            planning_required=planning_required,
            required_quality_checks=set(required_quality_checks or ()),
        )

    def execute_tool(
        self,
        state: AgentState,
        tool: str,
        arguments: dict,
    ) -> dict:

        state.iteration += 1

        result = self.tools.execute(
            tool,
            arguments,
        )

        state.add_event(
            "tool_execution",
            {
                "tool": tool,
                "arguments": arguments,
                "result": result,
            },
        )

        return result

    def _create_plan(
        self,
        state: AgentState,
        steps: list[str],
    ) -> None:

        state.plan = [
            PlanStep(
                id=index,
                description=description,
            )
            for index, description in enumerate(
                steps,
                start=1,
            )
        ]

        state.add_event(
            "plan_created",
            {"steps": [step.model_dump() for step in state.plan]},
        )

    def _update_plan_step(
        self,
        state: AgentState,
        step_id: int,
        status: str,
        note: str | None = None,
    ) -> bool:

        for step in state.plan:

            if step.id == step_id:

                step.status = status
                step.note = note

                state.add_event(
                    "plan_updated",
                    {"step": step.model_dump()},
                )

                return True

        state.add_event(
            "plan_update_rejected",
            {
                "step_id": step_id,
                "reason": "Unknown plan step.",
            },
        )

        return False

    def run(
        self,
        task: str,
        mode: str = "general",
        required_quality_checks: set[str] | None = None,
        planning_required: bool = False,
    ) -> AgentState:

        if self.llm is None:
            raise RuntimeError(
                "An LLM client is required to " "run the autonomous agent."
            )

        checks = set(required_quality_checks or ())

        unsupported_checks = checks - SUPPORTED_QUALITY_CHECKS

        if unsupported_checks:
            raise ValueError(
                "Unsupported quality checks: " + ", ".join(sorted(unsupported_checks))
            )

        if mode not in {
            "general",
            "repair",
        }:
            raise ValueError(f"Unsupported agent mode: {mode}")

        state = self.create_state(
            task=task,
            mode=mode,
            required_quality_checks=checks,
            planning_required=planning_required,
        )

        while not state.completed and state.iteration < state.max_iterations:

            state.iteration += 1

            messages = build_messages(
                task=state.task,
                history=state.history,
            )

            raw_response = self.llm.complete(messages)

            state.add_event(
                "llm_response",
                raw_response,
            )

            try:
                action = parse_agent_action(raw_response)

            except Exception as exc:

                state.add_event(
                    "invalid_action",
                    {
                        "error": str(exc),
                        "response": raw_response,
                    },
                )

                continue

            if isinstance(
                action,
                PlanAction,
            ):

                self._create_plan(
                    state=state,
                    steps=action.steps,
                )

                continue

            if isinstance(
                action,
                PlanStepAction,
            ):

                if not state.plan:

                    state.add_event(
                        "plan_update_rejected",
                        {"reason": "No plan exists yet."},
                    )

                    continue

                self._update_plan_step(
                    state=state,
                    step_id=action.step_id,
                    status=action.status,
                    note=action.note,
                )

                continue

            if isinstance(
                action,
                FinishAction,
            ):

                missing_quality_checks = (
                    state.required_quality_checks - state.passed_quality_checks
                )

                incomplete_plan_steps = [
                    step for step in state.plan if step.status != "completed"
                ]

                plan_missing = state.planning_required and not state.plan

                if (
                    not state.verification_passed
                    or state.changes_since_verification
                    or missing_quality_checks
                    or plan_missing
                    or (state.planning_required and incomplete_plan_steps)
                ):

                    state.add_event(
                        "finish_rejected",
                        {
                            "reason": (
                                "Required verification "
                                "or planning has not "
                                "been completed."
                            ),
                            "tests_passed": state.verification_passed,
                            "changes_since_verification": state.changes_since_verification,
                            "missing_quality_checks": sorted(missing_quality_checks),
                            "plan_missing": plan_missing,
                            "incomplete_plan_steps": [
                                {
                                    "id": step.id,
                                    "description": step.description,
                                    "status": step.status,
                                }
                                for step in incomplete_plan_steps
                            ],
                        },
                    )

                    continue

                state.completed = True

                state.add_event(
                    "finished",
                    {
                        "reasoning": action.reasoning,
                        "summary": action.summary,
                    },
                )

                break

            if state.planning_required and not state.plan:

                state.add_event(
                    "action_rejected",
                    {
                        "tool": action.tool,
                        "reason": (
                            "A plan must be created " "before tools can be used."
                        ),
                    },
                )

                continue

            mutation_tools = {
                "write_file",
                "edit_file",
                "delete_file",
            }

            if (
                state.mode == "repair"
                and action.tool in mutation_tools
                and not state.baseline_verification_run
            ):

                state.add_event(
                    "action_rejected",
                    {
                        "tool": action.tool,
                        "reason": (
                            "Repair mode requires "
                            "a baseline test run "
                            "before modifying files."
                        ),
                    },
                )

                continue

            result = self.tools.execute(
                action.tool,
                action.arguments,
            )

            state.add_event(
                "tool_result",
                {
                    "tool": action.tool,
                    "arguments": action.arguments,
                    "result": result,
                },
            )

            if action.tool == "run_tests":

                if not state.baseline_verification_run:

                    state.baseline_verification_run = True

                    state.baseline_verification_failed = not result.get(
                        "success",
                        False,
                    )

                if result.get(
                    "success",
                    False,
                ):

                    state.verification_passed = True

                    state.changes_since_verification = False

                else:

                    state.verification_passed = False

            elif (
                result.get(
                    "success",
                    False,
                )
                and action.tool in mutation_tools
            ):

                state.changes_since_verification = True

                state.verification_passed = False

                state.passed_quality_checks.clear()

            if action.tool == "run_command":

                command = action.arguments.get("command")

                if command in {
                    "ruff",
                    "mypy",
                }:

                    if result.get(
                        "success",
                        False,
                    ):

                        state.passed_quality_checks.add(command)

                    else:

                        state.passed_quality_checks.discard(command)

        if not state.completed and state.iteration >= state.max_iterations:

            state.add_event(
                "max_iterations_reached",
                {
                    "max_iterations": state.max_iterations,
                },
            )

        return state
