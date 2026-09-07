import asyncio
from typing import Literal

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from app.agent.agent import PythonGPTAgent
from app.llm.nvidia import NvidiaLLMClient
from app.workspace_manager import WorkspaceManager

app = FastAPI(
    title="PythonGPT API",
    version="0.1.0",
)

workspace_manager = WorkspaceManager()


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100,
    )


class WorkspaceResponse(BaseModel):
    name: str
    files: int


class WorkspaceCreateResponse(BaseModel):
    name: str
    path: str


class AgentRunRequest(BaseModel):
    task: str = Field(
        min_length=1,
        max_length=20_000,
    )

    workspace: str = Field(
        min_length=1,
        max_length=100,
    )

    mode: Literal[
        "general",
        "repair",
    ] = "general"

    planning_required: bool = True

    required_quality_checks: set[str] = Field(default_factory=set)


class PlanStepResponse(BaseModel):
    id: int
    description: str
    kind: str
    status: str
    note: str | None


class AgentRunResponse(BaseModel):
    completed: bool
    iterations: int
    tests_verified: bool
    quality_checks: list[str]
    plan: list[PlanStepResponse]
    history: list[dict]


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "pythongpt",
    }


@app.get(
    "/workspaces",
    response_model=list[WorkspaceResponse],
)
async def list_workspaces():

    return workspace_manager.list_workspaces()


@app.post(
    "/workspaces",
    response_model=WorkspaceCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace(
    request: WorkspaceCreateRequest,
):

    try:
        path = workspace_manager.create(request.name)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except FileExistsError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    return WorkspaceCreateResponse(
        name=request.name,
        path=str(path),
    )


@app.delete(
    "/workspaces/{name}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_workspace(
    name: str,
):

    try:
        workspace_manager.delete(name)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@app.post(
    "/agent/run",
    response_model=AgentRunResponse,
)
async def run_agent(
    request: AgentRunRequest,
):

    try:
        workspace = workspace_manager.get_path(request.workspace)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if not workspace.exists():
        raise HTTPException(
            status_code=404,
            detail=(f"Workspace not found: " f"{request.workspace}"),
        )

    try:
        llm = NvidiaLLMClient(
            thinking=True,
            medium_effort=True,
        )

        agent = PythonGPTAgent(
            workspace_path=workspace,
            llm=llm,
        )

        state = await asyncio.to_thread(
            agent.run,
            request.task,
            request.mode,
            request.required_quality_checks,
            request.planning_required,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    return AgentRunResponse(
        completed=state.completed,
        iterations=state.iteration,
        tests_verified=state.verification_passed,
        quality_checks=sorted(state.passed_quality_checks),
        plan=[
            PlanStepResponse(
                id=step.id,
                description=step.description,
                kind=step.kind,
                status=step.status,
                note=step.note,
            )
            for step in state.plan
        ],
        history=state.history,
    )
