import json
import logging
from typing import List, Dict

from openai import AsyncAzureOpenAI, omit

from core.config import Config
from providers.default import DefaultLLM, LLMResponse, LLMToolCall
from providers.utils.chat import LLMChat


class AzureLLM(DefaultLLM):

    client = AsyncAzureOpenAI(
        azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
        api_key=Config.AZURE_OPENAI_API_KEY,
        api_version=Config.AZURE_OPENAI_API_VERSION,
    )

    async def generate(self, chat: LLMChat, model_name: str | None = None, temperature: float | None = None,
                       timeout: float | None = None, tools: List[Dict] | None = None) -> LLMResponse:

        model_name = model_name if model_name else Config.AZURE_OPENAI_MODEL
        temperature = temperature if temperature else omit

        logging.info(temperature)

        completion = await self.client.chat.completions.create(
            model=model_name,
            messages=chat.history,
            temperature=temperature,
            # tools=tools  # Optional, falls Tools unterstützt werden
        )

        message = completion.choices[0].message

        tool_calls = []
        if hasattr(message, "tool_calls") and message.tool_calls:
            tool_calls = [
                LLMToolCall(name=t.function.name, arguments=json.loads(t.function.arguments))
                for t in message.tool_calls
            ]

        return LLMResponse(message.content, tool_calls)
