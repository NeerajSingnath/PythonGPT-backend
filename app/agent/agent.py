from pathlib import Path
from typing import Optional

from app.agent.actions import FinishAction
from app.agent.parser import parse_agent_action
from app.agent.prompt import build_messages
from app.agent.state import AgentState

from app.llm.base import LLMClient

from app.tools.registry import ToolRegistry
from app.tools.runtime import Runtime
from app.tools.workspace import Workspace
from app.tools.terminal import ControlledTerminal

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
    ) -> AgentState:

        return AgentState(
            task=task,
            mode=mode,
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

    def run(
        self,
        task: str,
        mode: str = "general",
        required_quality_checks: set[str] | None = None,
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
                FinishAction,
            ):

                missing_quality_checks = (
                    state.required_quality_checks - state.passed_quality_checks
                )

                if (
                    not state.verification_passed
                    or state.changes_since_verification
                    or missing_quality_checks
                ):

                    state.add_event(
                        "finish_rejected",
                        {
                            "reason": (
                                "Required verification " "has not been completed."
                            ),
                            "tests_passed": state.verification_passed,
                            "changes_since_verification": state.changes_since_verification,
                            "missing_quality_checks": sorted(missing_quality_checks),
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
