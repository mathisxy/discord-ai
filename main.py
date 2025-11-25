import asyncio
import logging
from datetime import datetime
from typing import List

import discord
from babel.dates import format_date
from discord.ext import commands
from dotenv import load_dotenv

from core.chat_history import ChatHistoryMessage
from core.config import Config
from core.discord_messages import DiscordMessage, DiscordTemporaryMessagesController, DiscordMessageReplyTmpError
from core.external_help_bot import use_help_bot
from core.instructions import get_instructions_from_discord_info
from core.logging_config import setup_logging
from core.message_handling import is_relevant_message, handle_messages, get_queue_listener, replace_instruction_patterns
from providers.azure import AzureLLM
from providers.gemini import GeminiLLM
from providers.mistral import MistralLLM
from providers.ollama import OllamaLLM
from providers.openai import OpenAILLM

load_dotenv()

setup_logging()


# Discord Intents
intents = discord.Intents.default()
intents.message_content = True  # Für Textnachrichten lesen
intents.messages = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)


match Config.AI:
    case "mistral":
        llm = MistralLLM()
    case "azure":
        llm = AzureLLM()
    case "gemini":
        llm = GeminiLLM()
    case "openai":
        llm = OpenAILLM()
    case "ollama":
        llm = OllamaLLM()
    case _:
        raise ValueError("Invalid value for AI in the configuration")


async def call_ai(history: List[ChatHistoryMessage], instructions: ChatHistoryMessage, queue: asyncio.Queue[DiscordMessage|None], channel: str, use_help_bot: bool = True):
    try:
        logging.info(llm)
        await llm.call(history, instructions, queue, channel, use_help_bot)
    except Exception as e:
        logging.exception(e, exc_info=True)
        await queue.put(DiscordMessageReplyTmpError(value=str(e)))
    finally:
        await queue.put(None)



async def handle_message(message: discord.Message):
    if message.author == bot.user:
        return

    if is_relevant_message(bot, message):

        async with message.channel.typing(), DiscordTemporaryMessagesController(channel=message.channel) as tmp_controller:

            try:

                queue = asyncio.Queue[DiscordMessage]()
                listener = get_queue_listener(bot, message)


                history = await handle_messages(bot, message)
                logging.info(history)


                channel_id = message.channel.id # message.author.display_name if isinstance(message.channel, discord.DMChannel) else message.channel.name

                instructions = ChatHistoryMessage(role="system", content="")

                instructions.content += get_instructions_from_discord_info(message)
                instructions.content += Config.INSTRUCTIONS

                instructions.content = replace_instruction_patterns(instructions.content)

                logging.info(instructions)

                task1 = asyncio.create_task(listener(queue, tmp_controller))
                task2 = asyncio.create_task(call_ai(history, instructions, queue, str(channel_id), use_help_bot(message)))

                await asyncio.gather(task1, task2)

            except Exception as e:
                logging.error(e, exc_info=True)
                await message.channel.send(str(e))


@bot.event
async def on_message(message: discord.Message):
    try:
        await handle_message(message)
    except Exception as e:
        logging.exception(e)
        await message.reply(f"Error: {e}")


@bot.event
async def on_ready():
    print(f"🤖 Bot online as {bot.user}!")
    # Alle Cogs laden
    await bot.load_extension("cogs.commands")
    await bot.tree.sync()
    print("✅ Slash-Commands synchronized")



bot.run(Config.DISCORD_TOKEN)
