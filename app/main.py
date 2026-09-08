import asyncio
import re
from pathlib import Path
from typing import Literal

from fastapi import (
    BackgroundTasks,
    FastAPI,
    HTTPException,
    Query,
    status,
)
from pydantic import BaseModel, Field

from app.agent.agent import PythonGPTAgent
from app.llm.nvidia import NvidiaLLMClient
from app.run_store import RunStore
from app.tools.workspace import Workspace
from app.workspace_manager import WorkspaceManager

app = FastAPI(
    title="PythonGPT API",
    version="0.1.0",
)

workspace_manager = WorkspaceManager()
run_store = RunStore()

RUN_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


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


class FileWriteRequest(BaseModel):
    content: str


class FileContentResponse(BaseModel):
    path: str
    content: str


class FileListResponse(BaseModel):
    files: list[str]


class FileWriteResponse(BaseModel):
    success: bool
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


class AgentRunCreateResponse(BaseModel):
    id: str
    status: str


class AgentRunSummaryResponse(BaseModel):
    id: str
    workspace: str
    task: str
    mode: str
    status: str
    created_at: str
    started_at: str | None
    finished_at: str | None
    completed: bool
    iterations: int
    tests_verified: bool
    quality_checks: list[str]
    error: str | None


class AgentRunDetailResponse(AgentRunSummaryResponse):
    planning_required: bool
    required_quality_checks: list[str]
    plan: list[dict]
    history: list[dict]


def get_workspace_path(
    name: str,
) -> Path:

    try:
        path = workspace_manager.get_path(name)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Workspace not found: {name}",
        )

    return path


def validate_run_id(
    run_id: str,
) -> str:

    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid run ID.",
        )

    return run_id


async def execute_agent_run(
    run_id: str,
    workspace_name: str,
    task: str,
    mode: str,
    planning_required: bool,
    required_quality_checks: set[str],
) -> None:

    try:
        run_store.mark_running(run_id)

        workspace = workspace_manager.get_path(workspace_name)

        if not workspace.exists():
            raise RuntimeError(f"Workspace not found: " f"{workspace_name}")

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
            task,
            mode,
            required_quality_checks,
            planning_required,
        )

        run_store.complete(
            run_id,
            state,
        )

    except Exception as exc:
        run_store.fail(
            run_id,
            str(exc),
        )


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


@app.get(
    "/workspaces/{name}/files",
    response_model=FileListResponse,
)
async def list_workspace_files(
    name: str,
):

    workspace_path = get_workspace_path(name)

    workspace = Workspace(workspace_path)

    result = workspace.list_files()

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get(
                "error",
                "Unable to list files.",
            ),
        )

    return FileListResponse(
        files=result["files"],
    )


@app.get(
    "/workspaces/{name}/files/{file_path:path}",
    response_model=FileContentResponse,
)
async def read_workspace_file(
    name: str,
    file_path: str,
):

    workspace_path = get_workspace_path(name)

    workspace = Workspace(workspace_path)

    try:
        result = workspace.read_file(file_path)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if not result.get("success"):

        error = result.get(
            "error",
            "Unable to read file.",
        )

        status_code = 404 if "not found" in error.lower() else 400

        raise HTTPException(
            status_code=status_code,
            detail=error,
        )

    return FileContentResponse(
        path=result["path"],
        content=result["content"],
    )


@app.put(
    "/workspaces/{name}/files/{file_path:path}",
    response_model=FileWriteResponse,
)
async def write_workspace_file(
    name: str,
    file_path: str,
    request: FileWriteRequest,
):

    workspace_path = get_workspace_path(name)

    workspace = Workspace(workspace_path)

    try:
        result = workspace.write_file(
            file_path,
            request.content,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get(
                "error",
                "Unable to write file.",
            ),
        )

    return FileWriteResponse(
        success=True,
        path=result["path"],
    )


@app.post(
    "/agent/runs",
    response_model=AgentRunCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_agent_run(
    request: AgentRunRequest,
    background_tasks: BackgroundTasks,
):

    get_workspace_path(request.workspace)

    if request.required_quality_checks - {"ruff", "mypy"}:
        raise HTTPException(
            status_code=400,
            detail=("Supported quality checks are " "ruff and mypy."),
        )

    run = run_store.create(
        workspace=request.workspace,
        task=request.task,
        mode=request.mode,
        planning_required=request.planning_required,
        required_quality_checks=request.required_quality_checks,
    )

    background_tasks.add_task(
        execute_agent_run,
        run["id"],
        request.workspace,
        request.task,
        request.mode,
        request.planning_required,
        request.required_quality_checks,
    )

    return AgentRunCreateResponse(
        id=run["id"],
        status=run["status"],
    )


@app.get(
    "/agent/runs",
    response_model=list[AgentRunSummaryResponse],
)
async def list_agent_runs(
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
):

    runs = run_store.list_runs(limit=limit)

    return [
        AgentRunSummaryResponse(
            id=run["id"],
            workspace=run["workspace"],
            task=run["task"],
            mode=run["mode"],
            status=run["status"],
            created_at=run["created_at"],
            started_at=run["started_at"],
            finished_at=run["finished_at"],
            completed=run["completed"],
            iterations=run["iterations"],
            tests_verified=run["tests_verified"],
            quality_checks=run["quality_checks"],
            error=run["error"],
        )
        for run in runs
    ]


@app.get(
    "/agent/runs/{run_id}",
    response_model=AgentRunDetailResponse,
)
async def get_agent_run(
    run_id: str,
):

    validate_run_id(run_id)

    run = run_store.get(run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Agent run not found.",
        )

    return AgentRunDetailResponse(
        id=run["id"],
        workspace=run["workspace"],
        task=run["task"],
        mode=run["mode"],
        status=run["status"],
        created_at=run["created_at"],
        started_at=run["started_at"],
        finished_at=run["finished_at"],
        completed=run["completed"],
        iterations=run["iterations"],
        tests_verified=run["tests_verified"],
        quality_checks=run["quality_checks"],
        error=run["error"],
        planning_required=run["planning_required"],
        required_quality_checks=run["required_quality_checks"],
        plan=run["plan"],
        history=run["history"],
    )
