import logging

from openai import AsyncAzureOpenAI, omit
import asyncio
import json
from typing import List, Dict

from core.config import Config
from core.discord_messages import DiscordMessage, DiscordMessageReply
from providers.base import BaseLLM, LLMResponse, LLMToolCall
from providers.utils.chat import LLMChat
from providers.utils.mcp_client import generate_with_mcp

# ------------------------------
# Azure OpenAI Client
# ------------------------------
client = AsyncAzureOpenAI(
    azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
    api_key=Config.AZURE_OPENAI_API_KEY,
    api_version=Config.AZURE_OPENAI_API_VERSION,
)

class AzureLLM(BaseLLM):

    async def call(self, history: List[Dict], instructions: str, queue: asyncio.Queue[DiscordMessage | None],
                   channel: str, use_help_bot=False):

        await super().call(history, instructions, queue, channel)

        instructions_entry = {"role": "system", "content": instructions}
        self.chats[channel].update_history(history, instructions_entry)

        if Config.MCP_INTEGRATION_CLASS:
            await generate_with_mcp(self, self.chats[channel], queue, self.mcp_client_integration_module(queue))
        else:
            response = await self.generate(self.chats[channel])
            await queue.put(DiscordMessageReply(value=response.text))


    async def generate(self, chat: LLMChat, model_name: str | None = None, temperature: float | None = None,
                       timeout: float | None = None, tools: List[Dict] | None = None) -> LLMResponse:

        model_name = model_name if model_name else Config.AZURE_OPENAI_MODEL
        temperature = temperature if temperature else omit

        logging.info(temperature)

        completion = await client.chat.completions.create(
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
