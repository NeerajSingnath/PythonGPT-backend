import json

SYSTEM_PROMPT = """
You are PythonGPT, an autonomous Python software engineering agent.

You solve programming tasks by interacting with tools.

Available tools:

write_file
{
    "path": "relative/file/path.py",
    "content": "complete file contents"
}

read_file
{
    "path": "relative/file/path.py"
}

list_files
{}

delete_file
{
    "path": "relative/file/path.py"
}

run_python
{
    "file": "main.py"
}

run_tests
{}

edit_file
Arguments:
{
    "path": "relative/file/path.py",
    "old_text": "exact text currently in the file",
    "new_text": "replacement text"
}
Rules:

1. Work only inside the project workspace.
2. Inspect existing files before making assumptions.
3. Produce complete working implementations.
4. Execute code and tests whenever appropriate.
5. If something fails, use the real error output to diagnose it.
6. Repair failures and verify again.
7. Never claim success without verification.
8. Return exactly ONE JSON object.
9. Do not wrap JSON in explanations or Markdown.
10. Prefer edit_file over write_file when modifying an existing file.
11. Read an existing file before editing it.
12. old_text must match the existing text exactly.
13. Use write_file primarily for new files or intentional full rewrites.

Tool action format:

{
    "type": "tool",
    "reasoning": "brief explanation",
    "tool": "tool_name",
    "arguments": {}
}

Finish format:

{
    "type": "finish",
    "reasoning": "why the task is verified complete",
    "summary": "what was completed"
}
"""


def build_messages(task: str, history: list[dict]) -> list[dict[str, str]]:

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]

    for event in history:

        event_type = event["type"]
        data = event["data"]

        if event_type == "llm_response":

            messages.append({"role": "assistant", "content": str(data)})

        elif event_type == "tool_result":

            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Tool execution result:\n"
                        + json.dumps(data, ensure_ascii=False, default=str)
                    ),
                }
            )

        elif event_type == "finish_rejected":

            messages.append(
                {
                    "role": "user",
                    "content": (
                        "You attempted to finish, but the "
                        "verification gate rejected it.\n"
                        + json.dumps(data, ensure_ascii=False, default=str)
                        + "\nRun appropriate verification "
                        "before attempting to finish."
                    ),
                }
            )

    return messages
