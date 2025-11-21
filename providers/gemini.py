import base64
import json
import logging
from typing import List, Dict, Any

import google.generativeai as genai
from openai import AsyncOpenAI

from core.chat_history import ChatHistoryFileSaved, ChatHistoryMessage, ChatHistoryFile, ChatHistoryFileText
from core.config import Config
from providers.base import LLMResponse, LLMToolCall
from providers.default import DefaultLLM
from core.chat import LLMChat


class GeminiLLM(DefaultLLM):


    client = AsyncOpenAI(
        api_key=Config.GEMINI_API_KEY,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    genai.configure(api_key=Config.GEMINI_API_KEY)


    async def generate(self, chat: LLMChat, model_name: str | None = None, temperature: float | None = None,
                       timeout: float | None = None, tools: List[Dict] | None = None) -> LLMResponse:

        model_name = model_name or Config.GEMINI_MODEL
        messages = [self.format_history_entry(msg) for msg in chat.history]


        model = genai.GenerativeModel(
            model_name,
            tools=tools,
            generation_config={
                **({"temperature": temperature} if temperature is not None else {})
            }
        )

        response = await model.generate_content_async(
            messages
        )

        # completion = await self.client.chat.completions.create(
        #     model=model_name,
        #     messages=chat.history,
        #     temperature=temperature,
        #     tools=tools
        # )

        message = response.text

        tool_calls = []
        for part in response.candidates[0]:
            if call := part.function_call:
                tool_calls.append(
                    LLMToolCall(id="", name=call.name, arguments=json.loads(call.arguments))
                )

        return LLMResponse(message.content, tool_calls)


    @classmethod
    def format_history_entry(cls, entry: ChatHistoryMessage) -> Dict[str, Any]:

        parts = []

        if entry.content:
            parts.append({
                "text": entry.content
            })

        for file in entry.files:
            if isinstance(file, ChatHistoryFile):
                if isinstance(file, ChatHistoryFileText):
                    parts.append({
                        "text": f"<#File filename=\"{file.name}\">{file.text_content}</File>"
                    })
                elif isinstance(file, ChatHistoryFileSaved) and file.mime_type in Config.GEMINI_VISION_MODEL_TYPES:
                    logging.info(f"Using vision for {file}")
                    with open(file.save_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")

                    parts.append({
                        "inline_data": {
                            "mime_type": file.mime_type,
                            "data": b64,
                        }
                    })
                else:
                    parts.append({
                        "text": f"<#File filename=\"{file.name}\">"
                    })

        for tool_call in entry.tool_calls:
            parts.append({
                "function_call": {
                    "name": tool_call.name,
                    "arguments": tool_call.arguments
                }
            })

        for tool_response in entry.tool_responses:
            parts.append({
                "function_response":
                    {
                        "name": tool_response.name,
                        "response": tool_response.content
                    }
            })

        formatted_entry = {
            "role": entry.role,
            "parts": parts,
        }

        logging.info(formatted_entry)

        return formatted_entry


    # @classmethod
    # def format_history_entry(cls, entry: ChatHistoryMessage) -> Dict[str, Any]:
    #     formatted_entry = super().format_history_entry(entry)
    #
    #     base64_images = []
    #
    #     for file in entry.files:
    #         logging.info(file)
    #         if isinstance(file, ChatHistoryFileSaved):
    #             logging.info(f"Found saved file entry in history: {file}")
    #             if file.mime_type in Config.GEMINI_IMAGE_MODEL_TYPES:
    #                 logging.info(f"Is image")
    #                 with open(file.save_path, "rb") as f:
    #                     b64 = base64.b64encode(f.read()).decode("utf-8")
    #                     base64_images.append({"base64": b64, "file": file})
    #
    #     if base64_images:
    #
    #         if entry.role != "user":
    #             formatted_entry["role"] = "user" # Because Gemini API doesnt accept images from not users
    #
    #         if formatted_entry.get("content"):
    #             formatted_entry["content"] = [{
    #                 "type": "text",
    #                 "text": formatted_entry["content"],
    #             }]
    #         else:
    #             formatted_entry["content"] = []
    #
    #         for image in base64_images:
    #             formatted_entry["content"].append({
    #                 "type": "image_url",
    #                 "image_url": {
    #                     "url":  f"data:{image["file"].mime_type};base64,{image["base64"]}"
    #                 },
    #             },)
    #
    #     logging.info(formatted_entry)
    #
    #     return formatted_entry
