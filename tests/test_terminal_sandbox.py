from pathlib import Path

from app.tools.terminal import ControlledTerminal


def create_terminal(
    tmp_path,
    monkeypatch,
) -> ControlledTerminal:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    monkeypatch.setenv(
        "PYTHONGPT_RUNTIME_MODE",
        "docker",
    )

    monkeypatch.setenv(
        "PYTHONGPT_SANDBOX_IMAGE",
        "pythongpt-sandbox:latest",
    )

    return ControlledTerminal(workspace)


def test_python_uses_runtime_in_docker_mode(
    tmp_path,
    monkeypatch,
):
    terminal = create_terminal(
        tmp_path,
        monkeypatch,
    )

    script = terminal.workspace / "main.py"

    script.write_text(
        "print('hello')",
        encoding="utf-8",
    )

    captured = {}

    def fake_execute(
        arguments,
        timeout,
        timeout_message,
    ):
        captured["arguments"] = arguments
        captured["timeout"] = timeout
        captured["timeout_message"] = timeout_message

        return {
            "success": True,
            "return_code": 0,
            "stdout": "hello\n",
            "stderr": "",
        }

    monkeypatch.setattr(
        terminal.runtime,
        "_execute",
        fake_execute,
    )

    result = terminal.run_command(
        "python",
        ["main.py"],
    )

    assert result["success"] is True
    assert captured["arguments"] == ["main.py"]


def test_python_rejects_path_escape(
    tmp_path,
    monkeypatch,
):
    terminal = create_terminal(
        tmp_path,
        monkeypatch,
    )

    outside = tmp_path / "outside.py"

    outside.write_text(
        "print('outside')",
        encoding="utf-8",
    )

    result = terminal.run_command(
        "python",
        ["../outside.py"],
    )

    assert result["success"] is False

    assert "Path escapes workspace" in result["error"]


def test_pytest_uses_runtime_module(
    tmp_path,
    monkeypatch,
):
    terminal = create_terminal(
        tmp_path,
        monkeypatch,
    )

    captured = {}

    def fake_run_module(
        module,
        arguments=None,
        timeout=60,
    ):
        captured["module"] = module
        captured["arguments"] = arguments
        captured["timeout"] = timeout

        return {
            "success": True,
            "return_code": 0,
            "stdout": "1 passed\n",
            "stderr": "",
        }

    monkeypatch.setattr(
        terminal.runtime,
        "run_module",
        fake_run_module,
    )

    result = terminal.run_command(
        "pytest",
        ["-q"],
    )

    assert result["success"] is True

    assert captured["module"] == "pytest"

    assert "-p" in captured["arguments"]

    assert "no:cacheprovider" in captured["arguments"]

    assert "-q" in captured["arguments"]


def test_ruff_uses_runtime_module(
    tmp_path,
    monkeypatch,
):
    terminal = create_terminal(
        tmp_path,
        monkeypatch,
    )

    captured = {}

    def fake_run_module(
        module,
        arguments=None,
        timeout=60,
    ):
        captured["module"] = module
        captured["arguments"] = arguments

        return {
            "success": True,
            "return_code": 0,
            "stdout": "",
            "stderr": "",
        }

    monkeypatch.setattr(
        terminal.runtime,
        "run_module",
        fake_run_module,
    )

    result = terminal.run_command("ruff")

    assert result["success"] is True

    assert captured["module"] == "ruff"

    assert captured["arguments"] == [
        "check",
        "--no-cache",
        "--ignore",
        "EXE002",
        ".",
    ]


def test_ruff_fix_is_rejected(
    tmp_path,
    monkeypatch,
):
    terminal = create_terminal(
        tmp_path,
        monkeypatch,
    )

    result = terminal.run_command(
        "ruff",
        ["--fix"],
    )

    assert result["success"] is False

    assert "ruff --fix is not allowed" in result["error"]


def test_mypy_uses_runtime_module(
    tmp_path,
    monkeypatch,
):
    terminal = create_terminal(
        tmp_path,
        monkeypatch,
    )

    captured = {}

    def fake_run_module(
        module,
        arguments=None,
        timeout=60,
    ):
        captured["module"] = module
        captured["arguments"] = arguments

        return {
            "success": True,
            "return_code": 0,
            "stdout": "",
            "stderr": "",
        }

    monkeypatch.setattr(
        terminal.runtime,
        "run_module",
        fake_run_module,
    )

    result = terminal.run_command(
        "mypy",
        ["."],
    )

    assert result["success"] is True

    assert captured["module"] == "mypy"

    assert "--cache-dir=/tmp/mypy_cache" in captured["arguments"]


def test_mypy_rejects_custom_flags(
    tmp_path,
    monkeypatch,
):
    terminal = create_terminal(
        tmp_path,
        monkeypatch,
    )

    result = terminal.run_command(
        "mypy",
        ["--ignore-missing-imports"],
    )

    assert result["success"] is False

    assert "Custom mypy flags" in result["error"]


def test_disallowed_command_is_rejected(
    tmp_path,
    monkeypatch,
):
    terminal = create_terminal(
        tmp_path,
        monkeypatch,
    )

    result = terminal.run_command(
        "powershell",
        [
            "-Command",
            "Get-ChildItem",
        ],
    )

    assert result["success"] is False

    assert "is not allowed" in result["error"]
