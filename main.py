import asyncio
import io
import logging
import os
from typing import List, Literal

import discord
from babel.dates import format_time
from discord.ext import commands
from dotenv import load_dotenv

from core.chat_history import ChatHistoryFile, ChatHistoryMessage, ChatHistoryFileSaved, ChatHistoryFileText
from core.config import Config
from core.discord_buttons import ProgressButton
from core.discord_messages import DiscordMessage, DiscordMessageFile, DiscordMessageReply, \
    DiscordMessageTmpMixin, DiscordTemporaryMessagesController, DiscordMessageReplyTmpError
from core.external_help_bot import use_help_bot
from core.instructions import get_instructions_from_discord_info
from core.logging_config import setup_logging
from core.message_handling import clean_reply
from providers.azure import AzureLLM
from providers.mistral import MistralLLM
from providers.ollama import OllamaLLM

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
    case "ollama":
        llm = OllamaLLM()


async def call_ai(history: List[ChatHistoryMessage], instructions: ChatHistoryMessage, queue: asyncio.Queue[DiscordMessage|None], channel: str, use_help_bot: bool = True):
    try:
        await llm.call(history, instructions, queue, channel, use_help_bot)
    except Exception as e:
        logging.exception(e, exc_info=True)
        await queue.put(DiscordMessageReplyTmpError(value=str(e)))
    finally:
        await queue.put(None)



def is_relevant_message(message: discord.Message) -> bool:
    return bot.user in message.mentions or isinstance(message.channel, discord.DMChannel)


async def handle_message(message):
    if message.author == bot.user:
        return

    if is_relevant_message(message):

        async with message.channel.typing(), DiscordTemporaryMessagesController(channel=message.channel) as tmp_controller:

            try:

                queue = asyncio.Queue[DiscordMessage]()

                async def listener(queue: asyncio.Queue[DiscordMessage|None]):

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


                history = []
                async for msg in message.channel.history(limit=Config.TOTAL_MESSAGE_SEARCH_COUNT, oldest_first=False):

                    if msg.content == Config.HISTORY_RESET_TEXT:
                        break

                    if len(history) >= Config.MAX_MESSAGE_COUNT:
                        break

                    role: Literal["user", "assistant"] = "assistant" if msg.author == bot.user else "user"
                    timestamp = format_time(msg.created_at,  format='short', tzinfo=Config.TIMEZONE, locale=Config.LANGUAGE) # Adapt Timestamp Format to Timezone and Language
                    content = msg.content if msg.author == bot.user else f"<#Message from=\"<@{msg.author.id}>\" at=\"{timestamp}\"> {msg.content}"
                    files = []

                    if msg.attachments:
                        for attachment in msg.attachments:

                            if attachment.content_type and Config.OLLAMA_IMAGE_MODEL and attachment.content_type in Config.OLLAMA_IMAGE_MODEL_TYPES: # TODO Modularize
                                image_bytes = await attachment.read()

                                save_path = os.path.join("downloads", attachment.filename)
                                os.makedirs("downloads", exist_ok=True)

                                with open(save_path, "wb") as f:
                                    f.write(image_bytes)

                                files.append(ChatHistoryFileSaved(attachment.filename, attachment.content_type, save_path))

                                # content += f"\n<#Imagename: {attachment.filename}>"
                            elif attachment.content_type and "text" in attachment.content_type:
                                text_bytes = await attachment.read()
                                text_content = text_bytes.decode("utf-8")

                                files.append(ChatHistoryFileText(attachment.filename, attachment.content_type, text_content))

                                # content += f"\n<#Filename: {attachment.filename}, content follows:>\n{text_content}"
                            else:
                                files.append(ChatHistoryFile(attachment.filename, attachment.content_type))
                                # content += f"\n<#Filename: {attachment.filename}>"

                    if not content and not files:
                        continue

                    history.append(ChatHistoryMessage(role=role, content=content, files=files))
                    # history.append({"role": role, "content": content, **({"images": images} if images else {})})

                history.reverse() # Hoffentlich nicht

                logging.info(history)


                channel_name = message.author.display_name if isinstance(message.channel, discord.DMChannel) else message.channel.name

                instructions = ChatHistoryMessage(role="system", content="")

                instructions.content += get_instructions_from_discord_info(message)
                instructions.content += Config.INSTRUCTIONS

                instructions.content = instructions.content.replace("[#NAME]", Config.NAME)
                instructions.content = instructions.content.replace("[#DISCORD_ID]", str(Config.DISCORD_ID))

                logging.info(instructions)

                task1 = asyncio.create_task(listener(queue))
                task2 = asyncio.create_task(call_ai(history, instructions, queue, channel_name, use_help_bot(message)))

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
