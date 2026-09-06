import os

from dotenv import load_dotenv
from openai import OpenAI

from app.llm.base import LLMClient

load_dotenv()


class NvidiaLLMClient(LLMClient):

    def __init__(
        self,
        model: str = "nvidia/nemotron-3-ultra-550b-a55b",
        thinking: bool = True,
        medium_effort: bool = True,
    ):
        api_key = os.getenv("NVIDIA_API_KEY")

        if not api_key:
            raise RuntimeError("NVIDIA_API_KEY is not configured.")

        self.model = model
        self.thinking = thinking
        self.medium_effort = medium_effort

        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key,
        )

    def complete(self, messages: list[dict[str, str]]) -> str:

        chat_template_kwargs = {
            "enable_thinking": self.thinking,
            "force_nonempty_content": True,
        }

        if self.thinking and self.medium_effort:
            chat_template_kwargs["medium_effort"] = True

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=1.0,
            top_p=0.95,
            max_tokens=8192,
            extra_body={"chat_template_kwargs": chat_template_kwargs},
        )

        content = response.choices[0].message.content

        if not content:
            raise RuntimeError("Nemotron returned an empty response.")

        return content
