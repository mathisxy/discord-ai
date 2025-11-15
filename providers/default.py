import asyncio
from abc import abstractmethod
from typing import List, Dict, Any

from core.config import Config
from core.discord_messages import DiscordMessage, DiscordMessageReply
from providers.base import LLMToolCall, LLMResponse, BaseLLM
from providers.utils.chat import LLMChat
from providers.utils.mcp_client import generate_with_mcp


class DefaultLLM(BaseLLM):

    async def call(self, history: List[Dict], instructions: str, queue: asyncio.Queue[DiscordMessage | None], channel: str, use_help_bot=False):

        self.chats.setdefault(channel, LLMChat())

        instructions_entry = {"role": "system", "content": instructions}
        self.chats[channel].update_history(history, instructions_entry)

        if Config.MCP_INTEGRATION_CLASS:
            await generate_with_mcp(self, self.chats[channel], queue, use_help_bot)
        else:
            response = await self.generate(self.chats[channel])
            await queue.put(DiscordMessageReply(value=response.text))


    @abstractmethod
    async def generate(self, chat: LLMChat, model_name: str | None = None, temperature: float | None = None, timeout: float | None = None, tools: List[Dict] | None = None) -> LLMResponse:
        pass


    @staticmethod
    def add_tool_call_message( chat: LLMChat, tool_calls: List[LLMToolCall]) -> None:

        chat.history.append(
            {"role": "system", "tool_calls": [
                {"id": t.name, "arguments": t.arguments} for t in tool_calls
            ]}
        )

    @staticmethod
    def add_tool_call_results_message(chat: LLMChat, tool_call: LLMToolCall, content: str) -> None:

        chat.history.append({"role": "system", "id": tool_call.name, "content": f"#{content}"})