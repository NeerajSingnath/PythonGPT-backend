from pathlib import Path

from app.agent.agent import PythonGPTAgent
from app.llm.nvidia import NvidiaLLMClient

llm = NvidiaLLMClient(
    thinking=True,
    medium_effort=True,
)

agent = PythonGPTAgent(
    workspace_path=Path("workspaces/demo"),
    llm=llm,
)

state = agent.run("""
Create a production-quality Python calculator.

Requirements:
- Create calculator.py
- Addition
- Subtraction
- Multiplication
- Division
- Handle division by zero
- Create comprehensive pytest tests
- Include edge cases
- Run the tests
- Fix any failures
- Do not finish until the project has been verified
""")


print("\n===== PythonGPT =====")
print("Completed:", state.completed)
print("Iterations:", state.iteration)

print("\n===== Agent History =====")

for event in state.history:

    print(f"\n[{event['iteration']}] " f"{event['type']}")

    print(event["data"])
