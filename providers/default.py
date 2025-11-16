import asyncio
import json
import string
from abc import abstractmethod
import random
from typing import List, Dict

from core.chat_history import ChatHistoryMessage, ChatHistoryFile, ChatHistoryFileText
from core.config import Config
from core.discord_messages import DiscordMessage, DiscordMessageReply
from providers.base import LLMToolCall, LLMResponse, BaseLLM
from providers.utils.chat import LLMChat
from providers.utils.mcp_client import generate_with_mcp


class DefaultLLM(BaseLLM):

    async def call(self, history: List[ChatHistoryMessage], instructions: ChatHistoryMessage, queue: asyncio.Queue[DiscordMessage | None], channel: str, use_help_bot=False):

        self.chats.setdefault(channel, LLMChat())

        formatted_history = [self.format_history_entry(entry) for entry in history]
        instructions_entry = self.format_history_entry(instructions)
        self.chats[channel].update_history(formatted_history, instructions_entry)

        if Config.MCP_INTEGRATION_CLASS:
            await generate_with_mcp(self, self.chats[channel], queue, use_help_bot)
        else:
            response = await self.generate(self.chats[channel])
            await queue.put(DiscordMessageReply(value=response.text))


    @abstractmethod
    async def generate(self, chat: LLMChat, model_name: str | None = None, temperature: float | None = None, timeout: float | None = None, tools: List[Dict] | None = None) -> LLMResponse:
        pass

    @classmethod
    def format_history_entry(cls, entry: ChatHistoryMessage):
        content = entry.content
        for file in entry.files:
            if isinstance(file, ChatHistoryFile):
                if isinstance(file, ChatHistoryFileText):
                    content += f"\n<#File filename=\"{file.name}\">{file.text_content}</File>"
                else:
                    content += f"\n<#File filename=\"{file.name}\">"

        return {"role": entry.role, "content": content}

    @classmethod
    def add_tool_call_message(cls, chat: LLMChat, tool_calls: List[LLMToolCall]) -> None:

        chat.history.append(
            {"role": "system", "tool_calls": [
                {"id": t.name, "arguments": t.arguments} for t in tool_calls
            ]}
        )

    @classmethod
    def add_tool_call_results_message(cls, chat: LLMChat, tool_call: LLMToolCall, content: str) -> None:

        chat.history.append({"role": "system", "id": tool_call.name, "content": f"#{content}"})

    @classmethod
    def extract_custom_tool_call(cls, text: str) -> LLMToolCall:

        id_length = 9

        tool_call = json.loads(text)
        tool_call_id = ''.join(random.choices(string.digits, k=id_length))

        return LLMToolCall(tool_call_id, tool_call.get("name"), tool_call.get("arguments"))
