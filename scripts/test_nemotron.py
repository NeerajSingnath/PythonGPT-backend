from app.llm.nvidia import NvidiaLLMClient

llm = NvidiaLLMClient(thinking=True, medium_effort=True)


response = llm.complete(
    [
        {
            "role": "system",
            "content": ("Return only JSON. " "Do not include markdown."),
        },
        {"role": "user", "content": ('Return {"status":"working"}')},
    ]
)


print(response)
