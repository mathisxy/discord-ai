import asyncio
import logging
import random
import string
from typing import List, Dict, Literal, Any

from ollama import AsyncClient

from core.chat_history import ChatHistoryMessage, ChatHistoryFileSaved
from core.config import Config
from core.discord_messages import DiscordMessage
from providers.default import DefaultLLM, LLMResponse, LLMToolCall
from providers.utils.chat import LLMChat
from providers.utils.vram import wait_for_vram


class OllamaLLM(DefaultLLM):

    async def call(self, history: List[ChatHistoryMessage], instructions: ChatHistoryMessage, queue: asyncio.Queue[DiscordMessage | None],
                   channel: str, use_help_bot=False):

        self.chats.setdefault(channel, LLMChat(AsyncClient(host=Config.OLLAMA_URL)))

        await super().call(history, instructions, queue, channel, use_help_bot)



    @classmethod
    async def generate(cls, chat: LLMChat, model_name: str | None = None, temperature: str | None = None, think: bool | Literal["low", "medium", "high"] | None = None, keep_alive: str | float | None = None, timeout: float | None = None, tools: List[Dict] | None = None) -> LLMResponse:

        if Config.OLLAMA_REQUIRED_VRAM_IN_GB:
            await wait_for_vram(required_gb=Config.OLLAMA_REQUIRED_VRAM_IN_GB, timeout=Config.OLLAMA_WAIT_FOR_REQUIRED_VRAM)
        else:
            logging.warning("Waiting for VRAM is disabled")

        model_name = model_name if model_name else Config.OLLAMA_MODEL
        temperature = temperature if temperature else Config.OLLAMA_MODEL_TEMPERATURE
        think = think if think else Config.OLLAMA_THINK
        keep_alive = keep_alive if keep_alive else Config.OLLAMA_KEEP_ALIVE
        timeout = timeout if timeout else Config.OLLAMA_TIMEOUT

        # async with (chat.lock):

        try:

            response = await asyncio.wait_for(
                chat.client.chat(
                    model=model_name,
                    messages=chat.history,
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

            tool_calls = [LLMToolCall(id=''.join(random.choices(string.digits, k=9)),name=t.function.name, arguments=dict(t.function.arguments)) for t in response.message.tool_calls] if response.message.tool_calls else []

            return LLMResponse(text=response.message.content, tool_calls=tool_calls)


        except Exception as e:
            logging.error(e, exc_info=True)
            raise Exception(f"Ollama Error: {e}")



    @classmethod
    def format_history_entry(cls, entry: ChatHistoryMessage) -> Dict[str, Any]:
        formatted_entry = super().format_history_entry(entry)

        for file in entry.files:
            logging.info(file)
            if isinstance(file, ChatHistoryFileSaved):
                logging.info(f"Found saved file entry in history: {file}")
                if file.type in Config.OLLAMA_IMAGE_MODEL_TYPES:
                    logging.info(f"Is image")
                    formatted_entry.setdefault("images", []).append(file.save_path)

        logging.info(formatted_entry)

        return formatted_entry