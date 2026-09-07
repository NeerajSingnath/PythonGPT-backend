import os
import random
import time

from dotenv import load_dotenv
from openai import (
    OpenAI,
    InternalServerError,
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
)

from app.llm.base import LLMClient

load_dotenv()


class NvidiaLLMClient(LLMClient):

    def __init__(
        self,
        model: str = "nvidia/nemotron-3-ultra-550b-a55b",
        thinking: bool = True,
        medium_effort: bool = True,
        max_retries: int = 5,
    ):

        api_key = os.getenv("NVIDIA_API_KEY")

        if not api_key:
            raise RuntimeError("NVIDIA_API_KEY is not configured.")

        self.model = model
        self.thinking = thinking
        self.medium_effort = medium_effort
        self.max_retries = max_retries

        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key,
            # We'll control retries ourselves
            max_retries=0,
            timeout=120.0,
        )

    def complete(self, messages: list[dict[str, str]]) -> str:

        chat_template_kwargs = {
            "enable_thinking": self.thinking,
            "force_nonempty_content": True,
        }

        if self.thinking and self.medium_effort:
            chat_template_kwargs["medium_effort"] = True

        last_error = None

        for attempt in range(1, self.max_retries + 1):

            try:

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

            except (
                InternalServerError,
                RateLimitError,
                APIConnectionError,
                APITimeoutError,
            ) as exc:

                last_error = exc

                if attempt == self.max_retries:
                    break

                # 2, 4, 8, 16... seconds
                # + small random jitter
                wait_time = 2**attempt + random.uniform(0, 1)

                print(
                    f"[Nemotron] Request failed "
                    f"(attempt {attempt}/"
                    f"{self.max_retries})."
                )

                print(f"[Nemotron] Retrying in " f"{wait_time:.1f}s...")

                time.sleep(wait_time)

        raise RuntimeError(
            "Nemotron is temporarily unavailable " f"after {self.max_retries} attempts."
        ) from last_error
