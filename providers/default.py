import asyncio
import json
import random
import string
from abc import abstractmethod
from typing import List, Dict, Any, Tuple

from core.chat_history import ChatHistoryMessage, ChatHistoryFile, ChatHistoryFileText, ChatHistoryController
from core.config import Config
from core.discord_messages import DiscordMessage, DiscordMessageReply
from providers.base import LLMToolCall, LLMResponse, BaseLLM
from providers.utils.mcp_client import generate_with_mcp


class DefaultLLM(BaseLLM):

    async def call(self, history: List[ChatHistoryMessage], instructions: ChatHistoryMessage, queue: asyncio.Queue[DiscordMessage | None], channel: str, use_help_bot=False):

        self.chats.setdefault(channel, ChatHistoryController())

        self.chats[channel].update(history, instructions)

        if Config.MCP_INTEGRATION_CLASS:
            await generate_with_mcp(self, self.chats[channel], queue, use_help_bot)
        else:
            response = await self.generate(self.chats[channel])
            await queue.put(DiscordMessageReply(value=response.text))


    @abstractmethod
    async def generate(self, chat: ChatHistoryController, model_name: str | None = None, temperature: float | None = None, timeout: float | None = None, tools: List[Dict] | None = None) -> LLMResponse:
        pass


    @classmethod
    def format_history_entry(cls, entry: ChatHistoryMessage) -> Dict[str, Any]:

        if entry.tool_response:
            tool_call, tool_response = entry.tool_response
            return {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_response,
            }

        parts = []
        tool_calls = []

        if entry.content:
            parts.append({
                "type": "text",
                "text": entry.content
            })


        for file in entry.files:
            if isinstance(file, ChatHistoryFile):
                if isinstance(file, ChatHistoryFileText):
                    parts.append({
                        "type": "text",
                        "text": f"<#File name=\"{file.name}\">{file.text_content}</File>"
                    })
                else:
                    parts.append({
                        "type": "text",
                        "text": f"\n<#File name=\"{file.name}\">"
                    })

        for tool_call in entry.tool_calls:
            tool_calls.append({
                "id": tool_call.id, "type": "function", "function": {
                    "name": tool_call.name,
                    "arguments": json.dumps(tool_call.arguments)
                }
            })

        return {
            "role": entry.role,
            "content": parts,
            **({"tool_calls": tool_calls} if tool_calls else {}),
        }


    @classmethod
    def add_assistant_message(cls, chat: ChatHistoryController, message: str) -> None:
        # chat.history.append({"role": "assistant", "content": message})
        chat.history.append(ChatHistoryMessage(role="assistant", content=message))

    @classmethod
    def add_error_message(cls, chat: ChatHistoryController, message: str) -> None:
        # chat.history.append({"role": "system", "content": message})
        chat.history.append(ChatHistoryMessage(role="system", content=message))

    @classmethod
    def add_tool_call_message(cls, chat: ChatHistoryController, tool_calls: List[LLMToolCall]) -> None:
        if Config.TOOL_INTEGRATION:
            chat.history.append(ChatHistoryMessage(role="assistant", tool_calls=tool_calls, is_temporary=True))

    @classmethod
    def add_tool_call_results_message(cls, chat: ChatHistoryController, tool_responses: [Tuple[LLMToolCall, str]]) -> None:

        for tool_response in tool_responses:
            chat.history.append(ChatHistoryMessage(role="tool", tool_response=tool_response, is_temporary=True))

    @classmethod
    def extract_custom_tool_call(cls, text: str) -> LLMToolCall:

        tool_call = json.loads(text)
        tool_call_id = ''.join(random.choices(string.digits, k=9))

        return LLMToolCall(id=tool_call_id, name=tool_call.get("name"), arguments=tool_call.get("arguments"))
