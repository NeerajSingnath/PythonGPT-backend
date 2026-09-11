import subprocess

from app.workspace_manager import WorkspaceManager


def run_git(
    workspace,
    *arguments,
):
    result = subprocess.run(
        [
            "git",
            *arguments,
        ],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=True,
    )

    return result.stdout.strip()


def test_new_workspace_is_git_managed(
    tmp_path,
):
    manager = WorkspaceManager(tmp_path / "workspaces")

    workspace = manager.create("demo")

    assert (workspace / ".git").exists()

    assert (
        run_git(
            workspace,
            "config",
            "--local",
            "--get",
            "pythongpt.managed",
        )
        == "true"
    )


def test_baseline_commits_current_workspace_state(
    tmp_path,
):
    manager = WorkspaceManager(tmp_path / "workspaces")

    workspace = manager.create("demo")

    file_path = workspace / "main.py"

    file_path.write_text(
        "print('before')\n",
        encoding="utf-8",
    )

    created = manager.prepare_run_baseline(
        "demo",
        "run-123",
    )

    assert created is True

    assert (
        run_git(
            workspace,
            "log",
            "-1",
            "--pretty=%s",
        )
        == "PythonGPT baseline run-123"
    )

    assert (
        run_git(
            workspace,
            "status",
            "--short",
        )
        == ""
    )


def test_agent_edit_appears_after_baseline(
    tmp_path,
):
    manager = WorkspaceManager(tmp_path / "workspaces")

    workspace = manager.create("demo")

    file_path = workspace / "main.py"

    file_path.write_text(
        "print('before')\n",
        encoding="utf-8",
    )

    manager.prepare_run_baseline(
        "demo",
        "run-123",
    )

    file_path.write_text(
        "print('after')\n",
        encoding="utf-8",
    )

    status = run_git(
        workspace,
        "status",
        "--short",
    )

    diff = run_git(
        workspace,
        "diff",
        "--",
        ".",
    )

    assert "M main.py" in status
    assert "-print('before')" in diff
    assert "+print('after')" in diff


def test_existing_external_repository_is_not_auto_committed(
    tmp_path,
):
    root = tmp_path / "workspaces"
    root.mkdir()

    workspace = root / "external"
    workspace.mkdir()

    run_git(
        workspace,
        "init",
        "--initial-branch=main",
    )

    run_git(
        workspace,
        "config",
        "user.name",
        "External User",
    )

    run_git(
        workspace,
        "config",
        "user.email",
        "external@example.com",
    )

    file_path = workspace / "main.py"

    file_path.write_text(
        "print('external')\n",
        encoding="utf-8",
    )

    manager = WorkspaceManager(root)

    created = manager.prepare_run_baseline(
        "external",
        "run-456",
    )

    assert created is False

    result = subprocess.run(
        [
            "git",
            "rev-parse",
            "--verify",
            "HEAD",
        ],
        cwd=workspace,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0

    assert (
        run_git(
            workspace,
            "config",
            "--local",
            "--get",
            "user.name",
        )
        == "External User"
    )
