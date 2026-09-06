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
