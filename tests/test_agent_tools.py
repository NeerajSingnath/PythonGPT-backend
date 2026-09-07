from pathlib import Path

from app.tools.workspace import Workspace
from app.tools.runtime import Runtime
from app.tools.terminal import ControlledTerminal


def test_agent_can_create_and_run_code(tmp_path: Path):

    workspace = Workspace(tmp_path)
    runtime = Runtime(tmp_path)

    result = workspace.write_file("hello.py", 'print("Hello from PythonGPT")')

    assert result["success"]

    result = runtime.run_python("hello.py")

    assert result["success"]

    assert "Hello from PythonGPT" in result["stdout"]


def test_agent_cannot_escape_workspace(tmp_path: Path):

    workspace = Workspace(tmp_path)

    try:
        workspace.write_file("../danger.txt", "NO")

        assert False

    except ValueError:
        assert True


from app.agent.agent import PythonGPTAgent


def test_agent_tool_registry(tmp_path):

    agent = PythonGPTAgent(tmp_path)

    state = agent.create_state("Create a hello world program")

    result = agent.execute_tool(
        state, "write_file", {"path": "main.py", "content": 'print("PythonGPT Agent")'}
    )

    assert result["success"]

    result = agent.execute_tool(state, "run_python", {"file": "main.py"})

    assert result["success"]
    assert "PythonGPT Agent" in result["stdout"]

    assert state.iteration == 2
    assert len(state.history) == 2


def test_edit_file(tmp_path: Path):

    workspace = Workspace(tmp_path)

    workspace.write_file(
        "calculator.py",
        """
def divide(a, b):
    return a * b
""".strip(),
    )

    result = workspace.edit_file(
        path="calculator.py", old_text="return a * b", new_text="return a / b"
    )

    assert result["success"]

    result = workspace.read_file("calculator.py")

    assert "return a / b" in result["content"]
    assert "return a * b" not in result["content"]


def test_edit_file_rejects_multiple_matches(tmp_path: Path):

    workspace = Workspace(tmp_path)

    workspace.write_file(
        "example.py",
        """
print("hello")
print("hello")
""".strip(),
    )

    result = workspace.edit_file(
        path="example.py", old_text='print("hello")', new_text='print("PythonGPT")'
    )

    assert not result["success"]
    assert "occurs 2 times" in result["error"]


def test_controlled_terminal_allows_python_file(tmp_path: Path):

    terminal = ControlledTerminal(tmp_path)

    script = tmp_path / "hello.py"

    script.write_text(
        'print("PythonGPT terminal")',
        encoding="utf-8",
    )

    result = terminal.run_command(
        command="python",
        arguments=["hello.py"],
    )

    assert result["success"]
    assert "PythonGPT terminal" in result["stdout"]


def test_controlled_terminal_blocks_commands(tmp_path: Path):

    terminal = ControlledTerminal(tmp_path)

    result = terminal.run_command(
        command="powershell",
        arguments=["-Command", "Remove-Item *"],
    )

    assert not result["success"]
    assert "not allowed" in result["error"]


def test_controlled_terminal_runs_ruff(
    tmp_path: Path,
):

    terminal = ControlledTerminal(tmp_path)

    (tmp_path / "main.py").write_text(
        ("def add(a, b):\n" "    return a + b\n"),
        encoding="utf-8",
    )

    result = terminal.run_command(
        command="ruff",
        arguments=[],
    )

    assert result["success"], result


def test_agent_registry_runs_ruff(
    tmp_path: Path,
):

    agent = PythonGPTAgent(workspace_path=tmp_path)

    (tmp_path / "main.py").write_text(
        "def add(a, b):\n" "    return a + b\n",
        encoding="utf-8",
    )

    state = agent.create_state("Test Ruff")

    result = agent.execute_tool(
        state,
        "run_command",
        {
            "command": "ruff",
            "arguments": [],
        },
    )

    assert result["success"], result


def test_list_files_ignores_git_directory(
    tmp_path: Path,
):

    workspace = Workspace(tmp_path)

    workspace.write_file(
        "main.py",
        "print('hello')",
    )

    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    (git_dir / "config").write_text(
        "fake git config",
        encoding="utf-8",
    )

    result = workspace.list_files()

    assert result["success"]

    assert "main.py" in result["files"]

    assert not any(".git" in file for file in result["files"])


def test_search_code(
    tmp_path: Path,
):

    workspace = Workspace(tmp_path)

    workspace.write_file(
        "auth.py",
        ("def authenticate(user):\n" "    return user is not None\n"),
    )

    workspace.write_file(
        "main.py",
        ("from auth import authenticate\n"),
    )

    result = workspace.search_code("authenticate")

    assert result["success"]

    assert len(result["matches"]) == 2

    paths = {match["path"] for match in result["matches"]}

    assert "auth.py" in paths
    assert "main.py" in paths


def test_python_outline(
    tmp_path: Path,
):

    workspace = Workspace(tmp_path)

    workspace.write_file(
        "service.py",
        """
import os


class UserService:

    async def fetch_user(self):
        pass

    def create_user(self):
        pass


def helper():
    pass
""".strip(),
    )

    result = workspace.python_outline("service.py")

    assert result["success"]

    assert result["classes"][0]["name"] == "UserService"

    methods = {method["name"] for method in result["classes"][0]["methods"]}

    assert methods == {
        "fetch_user",
        "create_user",
    }

    assert result["functions"][0]["name"] == "helper"
