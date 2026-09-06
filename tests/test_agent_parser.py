from app.agent.actions import ToolAction
from app.agent.parser import parse_agent_action


def test_parser_handles_nemotron_thinking():

    response = """
<think>
I should inspect the project first.
</think>
{
    "type": "tool",
    "reasoning": "Inspect existing files.",
    "tool": "list_files",
    "arguments": {}
}
"""

    action = parse_agent_action(response)

    assert isinstance(action, ToolAction)
    assert action.tool == "list_files"
