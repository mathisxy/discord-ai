import asyncio
import json
import random
import string
from abc import abstractmethod
from typing import List, Dict, Any, Tuple

from core.chat_history import ChatHistoryMessage, ChatHistoryFile, ChatHistoryFileText
from core.config import Config
from core.discord_messages import DiscordMessage, DiscordMessageReply
from providers.base import LLMToolCall, LLMResponse, BaseLLM
from core.chat import LLMChat
from providers.utils.mcp_client import generate_with_mcp


class DefaultLLM(BaseLLM):

    async def call(self, history: List[ChatHistoryMessage], instructions: ChatHistoryMessage, queue: asyncio.Queue[DiscordMessage | None], channel: str, use_help_bot=False):

        self.chats.setdefault(channel, LLMChat())

        self.chats[channel].update_history(history, instructions)

        if Config.MCP_INTEGRATION_CLASS:
            await generate_with_mcp(self, self.chats[channel], queue, use_help_bot)
        else:
            response = await self.generate(self.chats[channel])
            await queue.put(DiscordMessageReply(value=response.text))


    @abstractmethod
    async def generate(self, chat: LLMChat, model_name: str | None = None, temperature: float | None = None, timeout: float | None = None, tools: List[Dict] | None = None) -> LLMResponse:
        pass

    @classmethod
    def format_history_entry(cls, entry: ChatHistoryMessage) -> Dict[str, Any]:

        parts = []

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
                        "text": f"<#File filename=\"{file.name}\">{file.text_content}</File>"
                    })
                else:
                    parts.append({
                        "type": "text",
                        "text": f"\n<#File filename=\"{file.name}\">"
                    })

        for tool_call in entry.tool_calls:
            parts.append({
                "id": tool_call.id, "type": "function", "function": {
                    "name": tool_call.name,
                    "arguments": json.dumps(tool_call.arguments)
                }
            })

        for tool_call, tool_response in entry.tool_responses:
            parts.append({
                "type": "function_call_output",
                "call_id": tool_call.id,
                "output": tool_response,
            })

        return {
            "role": entry.role,
            "content": parts,
        }


    @classmethod
    def add_assistant_message(cls, chat: LLMChat, message: str) -> None:
        # chat.history.append({"role": "assistant", "content": message})
        chat.history.append(ChatHistoryMessage(role="assistant", content=message))

    @classmethod
    def add_error_message(cls, chat: LLMChat, message: str) -> None:
        # chat.history.append({"role": "system", "content": message})
        chat.history.append(ChatHistoryMessage(role="system", content=message))

    @classmethod
    def add_tool_call_message(cls, chat: LLMChat, tool_calls: List[LLMToolCall]) -> None:
        if Config.TOOL_INTEGRATION:
            chat.history.append(ChatHistoryMessage(role="assistant", tool_calls=tool_calls, is_temporary=True))

    @classmethod
    def add_tool_call_results_message(cls, chat: LLMChat, tool_responses: [Tuple[LLMToolCall, str]]) -> None:

        chat.history.append(ChatHistoryMessage(role="tool", tool_responses=tool_responses, is_temporary=True))

    @classmethod
    def extract_custom_tool_call(cls, text: str) -> LLMToolCall:

        tool_call = json.loads(text)
        tool_call_id = ''.join(random.choices(string.digits, k=9))

        return LLMToolCall(id=tool_call_id, name=tool_call.get("name"), arguments=tool_call.get("arguments"))
