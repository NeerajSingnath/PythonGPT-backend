import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class RunStore:

    def __init__(
        self,
        root: Path | str = "runs",
    ):
        self.root = Path(root).resolve()
        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._lock = threading.RLock()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _path(
        self,
        run_id: str,
    ) -> Path:
        return self.root / f"{run_id}.json"

    def _write(
        self,
        run: dict[str, Any],
    ) -> None:

        path = self._path(run["id"])

        temporary = path.with_suffix(".tmp")

        temporary.write_text(
            json.dumps(
                run,
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )

        temporary.replace(path)

    def create(
        self,
        workspace: str,
        task: str,
        mode: str,
        planning_required: bool,
        required_quality_checks: set[str],
    ) -> dict[str, Any]:

        run_id = uuid4().hex

        run = {
            "id": run_id,
            "workspace": workspace,
            "task": task,
            "mode": mode,
            "status": "queued",
            "planning_required": planning_required,
            "required_quality_checks": sorted(required_quality_checks),
            "created_at": self._now(),
            "started_at": None,
            "finished_at": None,
            "completed": False,
            "iterations": 0,
            "tests_verified": False,
            "quality_checks": [],
            "plan": [],
            "history": [],
            "error": None,
        }

        with self._lock:
            self._write(run)

        return run

    def get(
        self,
        run_id: str,
    ) -> dict[str, Any] | None:

        path = self._path(run_id)

        if not path.exists():
            return None

        with self._lock:
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (
                json.JSONDecodeError,
                OSError,
            ):
                return None

    def list_runs(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:

        runs = []

        for path in self.root.glob("*.json"):
            try:
                run = json.loads(path.read_text(encoding="utf-8"))
            except (
                json.JSONDecodeError,
                OSError,
            ):
                continue

            runs.append(run)

        runs.sort(
            key=lambda run: run.get(
                "created_at",
                "",
            ),
            reverse=True,
        )

        return runs[:limit]

    def mark_running(
        self,
        run_id: str,
    ) -> dict[str, Any]:

        with self._lock:
            run = self.get(run_id)

            if run is None:
                raise KeyError(f"Run not found: {run_id}")

            run["status"] = "running"
            run["started_at"] = self._now()

            self._write(run)

        return run

    def complete(
        self,
        run_id: str,
        state,
    ) -> dict[str, Any]:

        with self._lock:
            run = self.get(run_id)

            if run is None:
                raise KeyError(f"Run not found: {run_id}")

            run["status"] = "completed"
            run["finished_at"] = self._now()
            run["completed"] = state.completed
            run["iterations"] = state.iteration
            run["tests_verified"] = state.verification_passed
            run["quality_checks"] = sorted(state.passed_quality_checks)

            run["plan"] = [step.model_dump() for step in state.plan]

            run["history"] = state.history

            run["error"] = None

            self._write(run)

        return run

    def fail(
        self,
        run_id: str,
        error: str,
    ) -> dict[str, Any]:

        with self._lock:
            run = self.get(run_id)

            if run is None:
                raise KeyError(f"Run not found: {run_id}")

            run["status"] = "failed"
            run["finished_at"] = self._now()
            run["completed"] = False
            run["error"] = error

            self._write(run)

        return run
