import json
import random
import string
from abc import abstractmethod
from typing import List, Dict, Any

from core.chat_history import ChatHistoryMessage, ChatHistoryFile, ChatHistoryFileText
from core.config import Config
from providers.base import LLMToolCall, LLMResponse, BaseLLM
from providers.utils.chat import LLMChat


class DefaultLLM(BaseLLM):


    @abstractmethod
    async def generate(self, chat: LLMChat, model_name: str | None = None, temperature: float | None = None, timeout: float | None = None, tools: List[Dict] | None = None) -> LLMResponse:
        pass
        #model_name = model_name if model_name else Config.GEMINI_MODEL

    @classmethod
    def format_history_entry(cls, entry: ChatHistoryMessage) -> Dict[str, Any]:
        content = entry.content
        for file in entry.files:
            if isinstance(file, ChatHistoryFile):
                if isinstance(file, ChatHistoryFileText):
                    content += f"\n<#File filename=\"{file.name}\">{file.text_content}</File>"
                else:
                    content += f"\n<#File filename=\"{file.name}\">"

        return {"role": entry.role, "content": content}

    @classmethod
    def add_assistant_message(cls, chat: LLMChat, message: str) -> None:
        chat.history.append({"role": "assistant", "content": message})

    @classmethod
    def add_error_message(cls, chat: LLMChat, message: str) -> None:
        chat.history.append({"role": "system", "content": message})

    @classmethod
    def add_tool_call_message(cls, chat: LLMChat, tool_calls: List[LLMToolCall]) -> None:
        if Config.TOOL_INTEGRATION:
            chat.history.append({"role": "system", "tool_calls": [
                {"id": t.id, "type": "function", "function": {
                    "name": t.name,
                    "arguments": t.arguments
                }
                 } for t in tool_calls
            ]})

    @classmethod
    def add_tool_call_results_message(cls, chat: LLMChat, tool_call: LLMToolCall, content: str) -> None:

        chat.history.append({"role": "system", "tool_call_id": tool_call.id, "content": f"#{content}"})

    @classmethod
    def extract_custom_tool_call(cls, text: str) -> LLMToolCall:

        tool_call = json.loads(text)
        tool_call_id = ''.join(random.choices(string.digits, k=9))

        return LLMToolCall(id=tool_call_id, name=tool_call.get("name"), arguments=tool_call.get("arguments"))
