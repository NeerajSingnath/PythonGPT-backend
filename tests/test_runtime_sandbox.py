from pathlib import Path
from types import SimpleNamespace

import pytest

from app.tools.runtime import Runtime


def create_runtime(
    monkeypatch,
    workspace: Path,
    mode: str = "docker",
) -> Runtime:
    monkeypatch.setenv(
        "PYTHONGPT_RUNTIME_MODE",
        mode,
    )

    monkeypatch.setenv(
        "PYTHONGPT_SANDBOX_IMAGE",
        "pythongpt-sandbox:latest",
    )

    return Runtime(workspace)


def test_runtime_rejects_path_escape(
    tmp_path,
    monkeypatch,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    outside = tmp_path / "outside.py"
    outside.write_text(
        "print('outside')",
        encoding="utf-8",
    )

    runtime = create_runtime(
        monkeypatch,
        workspace,
    )

    result = runtime.run_python("../outside.py")

    assert result["success"] is False
    assert result["error"] == "Invalid path"


def test_runtime_rejects_non_python_file(
    tmp_path,
    monkeypatch,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    file_path = workspace / "notes.txt"
    file_path.write_text(
        "hello",
        encoding="utf-8",
    )

    runtime = create_runtime(
        monkeypatch,
        workspace,
    )

    result = runtime.run_python("notes.txt")

    assert result["success"] is False
    assert result["error"] == "Only Python files can be executed."


def test_runtime_rejects_unknown_module(
    tmp_path,
    monkeypatch,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    runtime = create_runtime(
        monkeypatch,
        workspace,
    )

    result = runtime.run_module(
        "pip",
        ["install", "requests"],
    )

    assert result["success"] is False
    assert result["error"] == "Python module not allowed: pip"


def test_docker_failure_does_not_fallback_to_host(
    tmp_path,
    monkeypatch,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    probe = workspace / "probe.py"
    probe.write_text(
        "print('probe')",
        encoding="utf-8",
    )

    runtime = create_runtime(
        monkeypatch,
        workspace,
    )

    monkeypatch.setattr(
        runtime,
        "_docker_executable",
        lambda: None,
    )

    result = runtime.run_python("probe.py")

    assert result["success"] is False
    assert result["return_code"] == -1

    assert "Docker is not installed" in result["stderr"]


def test_docker_command_uses_security_restrictions(
    tmp_path,
    monkeypatch,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    probe = workspace / "probe.py"
    probe.write_text(
        "print('probe')",
        encoding="utf-8",
    )

    runtime = create_runtime(
        monkeypatch,
        workspace,
    )

    monkeypatch.setattr(
        runtime,
        "_docker_executable",
        lambda: "docker",
    )

    captured = {}

    def fake_run(
        argv,
        **kwargs,
    ):
        captured["argv"] = argv
        captured["kwargs"] = kwargs

        return SimpleNamespace(
            returncode=0,
            stdout="probe\n",
            stderr="",
        )

    monkeypatch.setattr(
        "app.tools.runtime.subprocess.run",
        fake_run,
    )

    result = runtime.run_python("probe.py")

    assert result["success"] is True

    command = captured["argv"]

    assert "--network" in command
    assert command[command.index("--network") + 1] == "none"

    assert "--cpus" in command
    assert command[command.index("--cpus") + 1] == "1.0"

    assert "--memory" in command
    assert command[command.index("--memory") + 1] == "512m"

    assert "--pids-limit" in command
    assert command[command.index("--pids-limit") + 1] == "128"

    assert "--cap-drop" in command
    assert command[command.index("--cap-drop") + 1] == "ALL"

    assert "--security-opt" in command
    assert command[command.index("--security-opt") + 1] == "no-new-privileges:true"

    assert "--read-only" in command


def test_workspace_mount_is_read_only(
    tmp_path,
    monkeypatch,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    probe = workspace / "probe.py"
    probe.write_text(
        "print('probe')",
        encoding="utf-8",
    )

    runtime = create_runtime(
        monkeypatch,
        workspace,
    )

    monkeypatch.setattr(
        runtime,
        "_docker_executable",
        lambda: "docker",
    )

    captured = {}

    def fake_run(
        argv,
        **kwargs,
    ):
        captured["argv"] = argv

        return SimpleNamespace(
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(
        "app.tools.runtime.subprocess.run",
        fake_run,
    )

    runtime.run_python("probe.py")

    command = captured["argv"]

    mount_index = command.index("--mount") + 1

    mount = command[mount_index]

    assert "target=/workspace" in mount
    assert "readonly" in mount


def test_docker_uses_isolated_tmpfs(
    tmp_path,
    monkeypatch,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    probe = workspace / "probe.py"
    probe.write_text(
        "print('probe')",
        encoding="utf-8",
    )

    runtime = create_runtime(
        monkeypatch,
        workspace,
    )

    monkeypatch.setattr(
        runtime,
        "_docker_executable",
        lambda: "docker",
    )

    captured = {}

    def fake_run(
        argv,
        **kwargs,
    ):
        captured["argv"] = argv

        return SimpleNamespace(
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(
        "app.tools.runtime.subprocess.run",
        fake_run,
    )

    runtime.run_python("probe.py")

    command = captured["argv"]

    assert "--tmpfs" in command

    tmpfs = command[command.index("--tmpfs") + 1]

    assert tmpfs.startswith("/tmp:")
    assert "rw" in tmpfs
    assert "nosuid" in tmpfs
    assert "nodev" in tmpfs


@pytest.mark.parametrize(
    "module",
    [
        "pytest",
        "ruff",
        "mypy",
    ],
)
def test_approved_modules_execute_through_docker(
    tmp_path,
    monkeypatch,
    module,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    runtime = create_runtime(
        monkeypatch,
        workspace,
    )

    monkeypatch.setattr(
        runtime,
        "_docker_executable",
        lambda: "docker",
    )

    captured = {}

    def fake_run(
        argv,
        **kwargs,
    ):
        captured["argv"] = argv

        return SimpleNamespace(
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(
        "app.tools.runtime.subprocess.run",
        fake_run,
    )

    result = runtime.run_module(module)

    assert result["success"] is True

    command = captured["argv"]

    python_index = command.index("python")

    assert command[python_index + 1] == "-B"

    assert command[python_index + 2] == "-m"

    assert command[python_index + 3] == module
