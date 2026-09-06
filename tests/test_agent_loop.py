from pathlib import Path

from app.agent.agent import PythonGPTAgent
from app.llm.mock import MockLLMClient


def test_agent_builds_calculator(tmp_path: Path):

    llm = MockLLMClient()

    agent = PythonGPTAgent(workspace_path=tmp_path, llm=llm)

    state = agent.run("Create a Python calculator " "with pytest tests.")

    assert state.completed

    assert (tmp_path / "calculator.py").exists()

    assert (tmp_path / "test_calculator.py").exists()

    assert state.iteration == 4
