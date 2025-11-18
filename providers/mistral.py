import json
from typing import List, Dict

from mistralai import Mistral

from core.config import Config
from providers.default import DefaultLLM, LLMResponse, LLMToolCall
from providers.utils.chat import LLMChat

class MistralLLM(DefaultLLM):

    client = Mistral(api_key=Config.MISTRAL_API_KEY)

    async def generate(self, chat: LLMChat, model_name: str | None = None, temperature: float | None = None,
                       timeout: float | None = None, tools: List[Dict] | None = None) -> LLMResponse:

        model_name = model_name if model_name else Config.MISTRAL_MODEL

        response = await self.client.chat.complete_async(
            model=model_name,
            messages=chat.history,
            temperature=temperature,
            tools=tools,
        )

        message = response.choices[0].message

        tool_calls = []
        if message.tool_calls:
            tool_calls = [LLMToolCall(id=t.id, name=t.function.name, arguments=json.loads(t.function.arguments)) for t in message.tool_calls] if message.tool_calls else []

        return LLMResponse(message.content, tool_calls)


    @classmethod
    def add_error_message(cls, chat: LLMChat, message: str):
        chat.history.append({"role": "user", "content": message})

    @classmethod
    def add_tool_call_message(cls, chat: LLMChat, tool_calls: List[LLMToolCall]) -> None:

        if Config.TOOL_INTEGRATION:
            chat.history.append({"role": "assistant", "tool_calls": [
                {"id": t.id, "type": "function", "function": {
                    "name": t.name,
                    "arguments": t.arguments
                }
            } for t in tool_calls
            ]})

    @classmethod
    def add_tool_call_results_message(cls, chat: LLMChat, tool_call: LLMToolCall, content: str) -> None:

        chat.history.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": f"#{content}"
        })