import base64
import json
import logging
from typing import List, Dict, Any

from openai import AsyncAzureOpenAI, omit

from core.chat_history import ChatHistoryMessage, ChatHistoryFileSaved
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
        tools = tools if tools else omit

        logging.info(temperature)

        completion = await self.client.chat.completions.create(
            model=model_name,
            messages=chat.history,
            temperature=temperature,
            tools=tools,
        )

        message = completion.choices[0].message

        tool_calls = []
        if hasattr(message, "tool_calls") and message.tool_calls:
            tool_calls = [
                LLMToolCall(id=t.id, name=t.function.name, arguments=json.loads(t.function.arguments))
                for t in message.tool_calls
            ]

        return LLMResponse(message.content, tool_calls)

    @classmethod
    def format_history_entry(cls, entry: ChatHistoryMessage) -> Dict[str, Any]:
        formatted_entry = super().format_history_entry(entry)

        image_urls = []

        for file in entry.files:
            logging.info(file)
            if isinstance(file, ChatHistoryFileSaved):
                logging.info(f"Found saved file entry in history: {file}")
                if file.mime_type in Config.AZURE_OPENAI_IMAGE_MODEL_TYPES:
                    logging.info(f"Is image")
                    with open(file.save_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                        image_urls.append(f"data:{file.mime_type};base64,{b64}")

        if image_urls:
            if formatted_entry.get("content"):
                formatted_entry["content"] = [{
                    "type": "text",
                    "text": formatted_entry["content"],
                }]
            else:
                formatted_entry["content"] = []

            for image_url in image_urls:
                formatted_entry["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": image_url,
                    }
                })

        logging.info(formatted_entry)

        return formatted_entry
