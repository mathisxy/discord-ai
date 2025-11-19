import asyncio
import logging
from typing import List, Dict

import tiktoken
from GPUtil import GPUtil
from ollama import AsyncClient

from core.config import Config


class LLMChat:

    client: AsyncClient|None
    history: List[Dict[str, str]]
    tokenizer: tiktoken

    max_tokens = 3700 if len(GPUtil.getGPUs()) == 0 else Config.MAX_TOKENS
    logging.debug(f"MAX TOKENS: {max_tokens}")

    def __init__(self, client=None):

        self.client = client
        self.history = []
        self.tokenizer = tiktoken.get_encoding("cl100k_base")


    @property
    def system_entry(self) -> Dict[str, str] | None:
        if self.history:
            return self.history[0]
        return None

    @system_entry.setter
    def system_entry(self, value: Dict[str, str]):
        if not self.history:
            self.history = [value]
        else:
            self.history[0] = value

    def update_history(self, new_history: List[Dict[str, str]], instructions_entry: Dict[str, str]|None = None, min_overlap=1):

        history_without_tool_results = [x for x in self.history if not (x["role"] == "system" and x.get("content", "").startswith('#'))]

        #print("HISTORY WITHOUT TOOLS")
        #print(history_without_tool_results)
        #print(new_history)

        max_overlap_length = len(history_without_tool_results)
        overlap_length = None

        for length in range(max_overlap_length, min_overlap, -1):
            if history_without_tool_results[-length:] == new_history[:length]:
                overlap_length = length
                logging.info(f"OVERLAP LENGTH: {overlap_length}")
                break

        if not overlap_length:
            logging.info("NO OVERLAP")
            logging.info(self.history)
            logging.info(new_history)
            self.history = [instructions_entry] if instructions_entry else []
            self.history.extend(new_history)
        else:

            if instructions_entry and self.system_entry != instructions_entry:
                logging.info("UPDATING INSTRUCTIONS")
                logging.info(self.system_entry)
                logging.info(instructions_entry)
                self.system_entry = instructions_entry

            self.history = self.history + new_history[overlap_length:]

        logging.info(f"TOKEN COUNT: {self.count_tokens()}")
        logging.info(f"SYSTEM MESSAGE TOKEN COUNT: {self.count_tokens(history=[self.system_entry])}")

        if self.count_tokens() > self.max_tokens:
            logging.info("CUTTING BECAUSE OF EXCEEDING TOKEN COUNT")
            self.history = [instructions_entry] if instructions_entry else []
            self.history.extend(new_history)
            logging.info(self.history)


    def build_prompt(self, history=None) -> str:
        """Only builds role and content"""

        if history is None:
            history = self.history

        prompt_lines = []
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content")
            if isinstance(content, List): # Format {content: [{"type": "text", "text": "..."}]}
                content = [c.get("text") for c in content if c.get("type") == "text"]
                if content:
                    content = content[0]
                else:
                    content = ""
            prompt_lines.append(f"{role}: {content}")
        return "\n".join(prompt_lines)

    def count_tokens(self, history=None) -> int:
        prompt = self.build_prompt(history)
        return len(self.tokenizer.encode(prompt))