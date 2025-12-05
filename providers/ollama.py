import asyncio
import logging
import random
import string
from typing import List, Dict, Literal, Any, Tuple

from ollama import AsyncClient

from core.chat_history import ChatHistoryMessage, ChatHistoryFileSaved, ChatHistoryFile, ChatHistoryFileText, \
    ChatHistoryController
from core.config import Config
from core.discord_messages import DiscordMessage
from providers.default import DefaultLLM, LLMResponse, LLMToolCall
from providers.utils.vram import wait_for_vram

class ChatHistoryControllerOllama(ChatHistoryController):

    client: AsyncClient

    def __init__(self, client: AsyncClient):
        super().__init__()

        self.client = client


class OllamaLLM(DefaultLLM):

    async def call(self, history: List[ChatHistoryMessage], instructions: ChatHistoryMessage, queue: asyncio.Queue[DiscordMessage | None],
                   channel: str, use_help_bot=False):

        self.chats: Dict[str, ChatHistoryControllerOllama]

        self.chats.setdefault(channel, ChatHistoryControllerOllama(AsyncClient(host=Config.OLLAMA_URL)))

        await super().call(history, instructions, queue, channel, use_help_bot)



    async def generate(self, chat: ChatHistoryControllerOllama, model_name: str | None = None, temperature: str | None = None, think: bool | Literal["low", "medium", "high"] | None = None, keep_alive: str | float | None = None, timeout: float | None = None, tools: List[Dict] | None = None) -> LLMResponse:

        if Config.OLLAMA_REQUIRED_VRAM_IN_GB:
            await wait_for_vram(required_gb=Config.OLLAMA_REQUIRED_VRAM_IN_GB, timeout=Config.OLLAMA_WAIT_FOR_REQUIRED_VRAM)
        else:
            logging.warning("Waiting for VRAM is disabled")

        model_name = model_name if model_name else Config.OLLAMA_MODEL
        messages = [self.format_history_entry(msg) for msg in chat.history]
        temperature = temperature if temperature else Config.OLLAMA_MODEL_TEMPERATURE
        think = think if think else Config.OLLAMA_THINK
        keep_alive = keep_alive if keep_alive else Config.OLLAMA_KEEP_ALIVE
        timeout = timeout if timeout else Config.OLLAMA_TIMEOUT

        logging.info(messages)

        try:

            response = await asyncio.wait_for(
                chat.client.chat( # dynamic attribute
                    model=model_name,
                    messages=messages,
                    stream=False,
                    keep_alive=keep_alive,
                    options={
                        **({"temperature": temperature} if temperature is not None else {})
                    },
                    **({"think": think} if think is not None else {}),
                    **({"tools": tools} if tools is not None else {}),
                ),
                timeout=timeout,
            )

            logging.info(response)

            tool_calls = [LLMToolCall(id=''.join(random.choices(string.digits, k=9)), name=t.function.name, arguments=dict(t.function.arguments)) for t in response.message.tool_calls] if response.message.tool_calls else []

            return LLMResponse(text=response.message.content, tool_calls=tool_calls)


        except Exception as e:
            logging.error(e, exc_info=True)
            raise Exception(f"Ollama Error: {e}")

    @classmethod
    def add_tool_call_results_message(cls, chat: ChatHistoryController, tool_responses: [Tuple[LLMToolCall, str]]) -> None:

        for tool_response in tool_responses:
            chat.history.append(ChatHistoryMessage(role="tool", tool_response=tool_response, is_temporary=True))


    @classmethod
    def format_history_entry(cls, entry: ChatHistoryMessage) -> Dict[str, Any]:

        if entry.tool_response: # TODO adapt to API Reference of ollama
            tool_call, tool_response = entry.tool_response
            if Config.TOOL_INTEGRATION:
                return {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_response,
                }
            else:
                return {
                    "role": "system",
                    "content": f"{{\"tool\": \"{tool_call.name}\", \"response\": \"{tool_response}\"",
                }

        content = entry.content if entry.content else ""
        tool_calls = []
        images = []


        for file in entry.files:
            if isinstance(file, ChatHistoryFile):
                if isinstance(file, ChatHistoryFileText):
                    content += f"\n<#File name=\"{file.name}\">{file.text_content}</File>"
                elif isinstance(file, ChatHistoryFileSaved) and file.mime_type in Config.OLLAMA_VISION_MODEL_TYPES:
                    logging.info(f"Found saved image entry in history: {file}")
                    images.append(file.full_path)
                    content += f"\n<#Image name=\"{file.name}\">"
                else:
                    content += f"\n<#File name=\"{file.name}\">"

        for tool_call in entry.tool_calls:
            tool_calls.append({
                "id": tool_call.id, "type": "function", "function": {
                    "name": tool_call.name,
                    "arguments": tool_call.arguments
                }
            })

        return {
            "role": entry.role,
            "content": content,
            **({"tool_calls": tool_calls} if tool_calls else {}),
            **({"images": images} if images else {}),
        }