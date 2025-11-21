import asyncio
import json
import logging
import re
from typing import List

from fastmcp import Client
from mcp.types import CallToolResult

from core.config import Config
from core.discord_messages import DiscordMessage, DiscordMessageReplyTmp, \
    DiscordMessageRemoveTmp, DiscordMessageReply, DiscordMessageReplyTmpError
from providers.base import BaseLLM, LLMToolCall
from core.chat import LLMChat
from providers.utils.error_reasoning import error_reasoning
from providers.utils.response_filtering import filter_response
from providers.utils.tool_calls import mcp_to_dict_tools, get_custom_tools_system_prompt, get_tools_system_prompt


async def generate_with_mcp(llm: BaseLLM, chat: LLMChat, queue: asyncio.Queue[DiscordMessage | None], use_help_bot: bool = False):

    if not Config.MCP_SERVER_URL:
        raise Exception("Kein MCP Server URL verfügbar")

    integration = llm.mcp_client_integration_module(llm, queue)
    client = Client(Config.MCP_SERVER_URL, log_handler=integration.log_handler, progress_handler=integration.progress_handler)

    async with client:

        mcp_tools = await client.list_tools()

        mcp_tools = integration.filter_tool_list(mcp_tools)
        mcp_dict_tools = mcp_to_dict_tools(mcp_tools)

        logging.info(mcp_tools)
        logging.info(mcp_dict_tools)

        if not Config.TOOL_INTEGRATION:
            chat.system_entry.content += get_custom_tools_system_prompt(mcp_tools)
        else:
            chat.system_entry.content += get_tools_system_prompt()

        tool_call_errors = False


        for i in range(Config.MAX_TOOL_CALLS):

            logging.info(f"Tool Call Errors: {tool_call_errors}")

            deny_tools = Config.DENY_RECURSIVE_TOOL_CALLING and not tool_call_errors and i > 0

            use_integrated_tools = Config.TOOL_INTEGRATION and not deny_tools

            logging.info(f"Use integrated tools: {use_integrated_tools}")

            response = await llm.generate(chat, tools= mcp_to_dict_tools(mcp_tools) if use_integrated_tools else None)

            logging.info(f"RESPONSE: {response}")


            if response.text:

                filtered_text = filter_response(response.text, Config.OLLAMA_MODEL)

                llm.add_assistant_message(chat, filtered_text)
                await queue.put(DiscordMessageReply(value=filtered_text))

            if deny_tools:
                break


            try:
                if Config.TOOL_INTEGRATION and response.tool_calls:
                    tool_calls = response.tool_calls
                else:
                    tool_calls = extract_custom_tool_calls(llm, response.text)

                tool_call_errors = False

            except Exception as e:

                logging.exception(e, exc_info=True)

                if Config.MCP_ERROR_HELP_DISCORD_ID and use_help_bot:
                    await queue.put(DiscordMessageReplyTmpError(
                        value=f"<@{Config.MCP_ERROR_HELP_DISCORD_ID}> {e}",
                        embed=False
                    ))
                    break

                try:
                    await queue.put(DiscordMessageReplyTmp(
                        key="reasoning",
                        value="Analyzing Error..."
                    ))
                    reasoning = await error_reasoning(str(e), llm, chat)

                except Exception as f:
                    logging.error(f, exc_info=True)
                    reasoning = str(e)

                finally:
                    await queue.put(DiscordMessageRemoveTmp(key="reasoning"))

                llm.add_error_message(chat, reasoning)
                tool_call_errors = True

                continue


            if tool_calls:

                run_again = False

                for tool_call in tool_calls:

                    logging.info(f"TOOL CALL: {tool_call}")
                    llm.add_tool_call_message(chat, [tool_call])

                    try:

                        result = await handle_tool_call(queue, client, tool_call)

                        if not result.content:
                            logging.warning("Empty Tool Result Content, asserting manual break")
                            continue

                        run_again = await integration.process_tool_result(tool_call, result, chat) or run_again

                    except Exception as e:
                        logging.exception(e, exc_info=True)

                        if Config.MCP_ERROR_HELP_DISCORD_ID and use_help_bot:
                            await queue.put(DiscordMessageReplyTmpError(
                                value=f"<@{Config.MCP_ERROR_HELP_DISCORD_ID}> {e}",
                                embed=False
                            ))
                            break

                        try:
                            await queue.put(DiscordMessageReplyTmp(key="reasoning", value="Analyzing Error..."))
                            reasoning = await error_reasoning(str(e), llm, chat)

                        except Exception as f:
                            logging.error(f, exc_info=True)
                            reasoning = str(e)

                        finally:
                            await queue.put(DiscordMessageRemoveTmp(key="reasoning"))

                        llm.add_tool_call_results_message(chat, tool_call, reasoning)

                        tool_call_errors = True
                        run_again = True


                logging.info(chat.history)

                if not run_again:
                    logging.info("The LLM is not instructed to run again on tool results")
                    break

            else:
                break


async def handle_tool_call(queue: asyncio.Queue[DiscordMessage | None], client: Client, tool_call: LLMToolCall) -> CallToolResult:

    message = f"Das Tool **{tool_call.name}** wird aufgerufen"
    formatted_args = "\n".join(f" - **{k}:** {v}" for k, v in tool_call.arguments.items())
    if formatted_args:
        message += f":\n{formatted_args}"
    await queue.put(DiscordMessageReplyTmp(key=tool_call.id, value=message))

    result = await client.call_tool(tool_call.name, tool_call.arguments)

    logging.info(f"Tool Call Result bekommen für {tool_call}")

    return result


def extract_custom_tool_calls(llm: BaseLLM, text: str) -> List[LLMToolCall]:
    tool_calls = []
    pattern = r'```tool(.*?)```'

    matches = re.findall(pattern, text, flags=re.DOTALL)
    for raw in matches:
        raw_json = raw.strip()
        try:
            llm_tool_call = llm.extract_custom_tool_call(raw_json)
            tool_calls.append(llm_tool_call)
        except json.JSONDecodeError as e:
            raise Exception(f"Error JSON-decoding Tool Call: {raw_json}\n{e}")

    return tool_calls


