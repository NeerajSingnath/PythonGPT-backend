from pathlib import Path

from app.tools.workspace import Workspace
from app.tools.runtime import Runtime


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
