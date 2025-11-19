import base64
import json
import logging
from typing import List, Dict, Any

from openai import AsyncOpenAI

from core.chat_history import ChatHistoryFileSaved, ChatHistoryMessage
from core.config import Config
from providers.base import LLMResponse, LLMToolCall
from providers.default import DefaultLLM
from providers.utils.chat import LLMChat


class GeminiLLM(DefaultLLM):


    client = AsyncOpenAI(
        api_key=Config.GEMINI_API_KEY,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    async def generate(self, chat: LLMChat, model_name: str | None = None, temperature: float | None = None,
                       timeout: float | None = None, tools: List[Dict] | None = None) -> LLMResponse:

        model_name = model_name or Config.GEMINI_MODEL

        completion = await self.client.chat.completions.create(
            model=model_name,
            messages=chat.history,
            temperature=temperature,
            tools=tools
        )

        message = completion.choices[0].message

        tool_calls = []
        if getattr(message, "tool_calls", None):
            tool_calls = [
                LLMToolCall(id=t.id, name=t.function.name, arguments=json.loads(t.function.arguments))
                for t in message.tool_calls
            ]

        return LLMResponse(message.content, tool_calls)


    @classmethod
    def format_history_entry(cls, entry: ChatHistoryMessage) -> Dict[str, Any]:
        formatted_entry = super().format_history_entry(entry)

        base64_images = []

        for file in entry.files:
            logging.info(file)
            if isinstance(file, ChatHistoryFileSaved):
                logging.info(f"Found saved file entry in history: {file}")
                if file.mime_type in Config.GEMINI_IMAGE_MODEL_TYPES:
                    logging.info(f"Is image")
                    with open(file.save_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                        base64_images.append({"base64": b64, "file": file})

        if base64_images:

            if entry.role != "user":
                formatted_entry["role"] = "user" # Because Gemini API doesnt accept images from not users

            if formatted_entry.get("content"):
                formatted_entry["content"] = [{
                    "type": "text",
                    "text": formatted_entry["content"],
                }]
            else:
                formatted_entry["content"] = []

            for image in base64_images:
                formatted_entry["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url":  f"data:{image["file"].mime_type};base64,{image["base64"]}"
                    },
                },)

        logging.info(formatted_entry)

        return formatted_entry
