import asyncio
import io
import logging
import os
import re
from datetime import datetime
from typing import List, Literal

import discord
from babel.dates import format_time, format_date
from discord.ext import commands

from core.chat_history import ChatHistoryMessage, ChatHistoryFile, ChatHistoryFileSaved
from core.config import Config
from core.discord_buttons import ProgressButton
from core.discord_messages import DiscordMessage, DiscordMessageReply, DiscordMessageFile, DiscordMessageTmpMixin, \
    DiscordTemporaryMessagesController


def clean_reply(reply: str) -> str:

    pattern = r'(<#.*?>)' # If the LLM replicates the used information tags
    reply = re.sub(pattern, '', reply)
    logging.info(f"REPLY: {reply}")
    return reply.strip()

def is_relevant_message(bot: commands.Bot,message: discord.Message) -> bool:
    return bot.user in message.mentions or isinstance(message.channel, discord.DMChannel)

async def handle_messages(bot: commands.Bot, message: discord.Message) -> List[ChatHistoryMessage]:

    history: List[ChatHistoryMessage] = []

    async for msg in message.channel.history(limit=Config.TOTAL_MESSAGE_SEARCH_COUNT, oldest_first=False):

        if msg.content == Config.HISTORY_RESET_TEXT:
            break

        if len(history) >= Config.MAX_MESSAGE_COUNT:
            break

        history_message = await handle_message(bot, msg)

        if not history_message:
            continue

        history.append(history_message)


    history.reverse() # Hoffentlich nicht


    return history


async def handle_message(bot: commands.Bot, message: discord.Message) -> ChatHistoryMessage|None:

    role: Literal["user", "assistant"] = "assistant" if message.author == bot.user else "user"
    timestamp = format_time(message.created_at,  format='short', tzinfo=Config.TIMEZONE, locale=Config.LANGUAGE) # Adapt Timestamp Format to Timezone and Language
    content = message.content if message.author == bot.user else f"<#Message from=\"<@{message.author.id}>\" at=\"{timestamp}\">{message.content}</Message>"
    files = []

    if message.attachments:
        logging.info("Attachments: %s", message.attachments)
        files = await handle_attachments(bot, message)


    if not content and not files:
        return None

    return ChatHistoryMessage(role=role, content=content, files=files)


async def handle_attachments(bot: commands.Bot, message: discord.Message) -> List[ChatHistoryFile]:

    files: List[ChatHistoryFile] = []

    for attachment in message.attachments:

        logging.info(attachment.content_type)

        if attachment.content_type:
            # Mapping: Welcher Provider nutzt welche Vision-Settings?
            # Format: "Provider": (Vision_Aktiviert_Flag, Erlaubte_Typen_Liste)
            vision_configs = {
                "mistral": (Config.MISTRAL_VISION, Config.MISTRAL_VISION_MODEL_TYPES),
                "azure":   (Config.AZURE_OPENAI_VISION, Config.AZURE_OPENAI_VISION_MODEL_TYPES),
                "gemini":  (Config.GEMINI_VISION, Config.GEMINI_VISION_MODEL_TYPES), # Checke deine Config-Namen hier!
                "openai":  (Config.OPENAI_VISION, Config.OPENAI_VISION_MODEL_TYPES),
                "ollama":  (Config.OLLAMA_VISION, Config.OLLAMA_VISION_MODEL_TYPES),
            }

            # Hole die Config für den aktuellen Provider (Standard: False und leere Liste)
            is_vision_enabled, allowed_types = vision_configs.get(Config.AI, (False, []))

            # Die eigentliche Logik (nur noch einmal schreiben!)
            if is_vision_enabled: # attachment.content_type in allowed_types:
                files.append(await save_file(bot, message, attachment))
            else:
                logging.info("Add only Filename: %s", attachment)
                files.append(ChatHistoryFile(attachment.filename, attachment.content_type))

        else:
            logging.exception("No content type present: %s", attachment)

    logging.info("Files: %s", files)

    return files


async def save_file(bot: commands.Bot, message: discord.Message, attachment: discord.Attachment) -> ChatHistoryFileSaved:

    path = Config.DOWNLOAD_FOLDER / str(message.channel.id)
    unique_filename = f"{message.id}-{attachment.filename}"

    os.makedirs(Config.DOWNLOAD_FOLDER / str(message.channel.id), exist_ok=True)

    file_bytes = await attachment.read()

    if not file_bytes:
        logging.exception("Empty attachment: %s", attachment)

    chat_history_file = ChatHistoryFileSaved(attachment.filename, attachment.content_type, path / unique_filename)

    await chat_history_file.save(file_bytes)

    return chat_history_file


def get_queue_listener(bot: commands.Bot, message: discord.Message):

    async def listener(queue: asyncio.Queue[DiscordMessage|None], tmp_controller: DiscordTemporaryMessagesController):

        while True:
            try:
                event = await queue.get()
                if event is None:
                    break
                if isinstance(event, DiscordMessageTmpMixin):

                    view = None
                    if event.cancelable:
                        view = ProgressButton()

                    await tmp_controller.set_message(event, view)

                elif isinstance(event, DiscordMessageFile):

                    file = discord.File(io.BytesIO(event.value), filename=event.filename)
                    await message.channel.send(file=file)

                elif isinstance(event, DiscordMessageReply):
                    reply = clean_reply(event.value)
                    if not reply:
                        return
                    if len(reply) > 2000: # Max message length for discord
                        file = discord.File(io.BytesIO(reply.encode('utf-8')), filename=f"{bot.user.name}.txt")
                        await message.channel.send(file=file)
                    else:
                        await message.channel.send(reply)

                else:
                    raise Exception("Invalid DiscordMessage Type")

            except Exception as e:
                logging.exception(e, exc_info=True)

    return listener

def replace_instruction_patterns(instructions: str) -> str:

    instructions = instructions.replace("[#NAME]", Config.NAME)
    instructions = instructions.replace("[#DISCORD_ID]", str(Config.DISCORD_ID))
    instructions = instructions.replace("[#CURRENT_DATE]", format_date(datetime.now(), format='long', locale=Config.LANGUAGE))

    return instructions