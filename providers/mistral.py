import base64
import json
import logging
from typing import List, Dict, Any

from mistralai import Mistral

from core.chat_history import ChatHistoryMessage, ChatHistoryFileSaved
from core.config import Config
from providers.default import DefaultLLM, LLMResponse, LLMToolCall
from core.chat import LLMChat


class MistralLLM(DefaultLLM):

    client = Mistral(api_key=Config.MISTRAL_API_KEY)

    async def generate(self, chat: LLMChat, model_name: str | None = None, temperature: float | None = None,
                       timeout: float | None = None, tools: List[Dict] | None = None) -> LLMResponse:

        model_name = model_name if model_name else Config.MISTRAL_MODEL
        messages = [self.format_history_entry(msg) for msg in chat.history]


        response = await self.client.chat.complete_async(
            model=model_name,
            messages=messages,
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
        chat.history.append(ChatHistoryMessage(role="user", content=message))

    @classmethod
    def format_history_entry(cls, entry: ChatHistoryMessage) -> Dict[str, Any]:
        formatted_entry = super().format_history_entry(entry)

        for file in entry.files:
            logging.info(file)
            if isinstance(file, ChatHistoryFileSaved):
                logging.info(f"Found saved file entry in history: {file}")
                if file.mime_type in Config.AZURE_OPENAI_VISION_MODEL_TYPES:
                    logging.info(f"Is image")
                    with open(file.save_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")

                        formatted_entry["content"].append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{file.mime_type};base64,{b64}",
                            }
                        })

        logging.info(formatted_entry)

        return formatted_entry