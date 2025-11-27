import logging
from dataclasses import dataclass, field
from typing import Literal, Tuple, Dict, List, Type
from pathlib import Path

import tiktoken

from core.config import Config


@dataclass(kw_only=True)
class LLMToolCall:
    """Supports only calls of type function"""
    id: str
    name: str
    arguments: Dict

@dataclass
class LLMResponse:
    text: str
    tool_calls: List[LLMToolCall] = field(default_factory=list)

@dataclass
class ChatHistoryFile:

    name: str
    mime_type: str

@dataclass
class ChatHistoryFileSaved(ChatHistoryFile):

    full_path: Path
    """Full save path including the filename"""
    temporary: bool = field(default=True)
    """File gets deleted if __del__ is called"""

    def __post_init__(self):
        self.validate_path()

    def validate_path(self):
        """Checks if save_path is a File"""

        if not self.full_path.parts:
            raise ValueError(f"Invalid Filepath: '{self.full_path}'")

        if not self.full_path.name:
            raise ValueError(f"Missing Filename in Filepath: '{self.full_path}'")


    async def save(self, file_bytes) -> None:

        with open(self.full_path, "wb") as f:
            f.write(file_bytes)

    def delete(self) -> None:
        if self.full_path.exists():
            try:
                self.full_path.unlink(missing_ok=True)
                logging.info(f"Deleted '{self.full_path}'")
            except Exception as e:
                logging.exception(f"Deletion of '{self.full_path}' failed: {e}")



@dataclass
class ChatHistoryFileText(ChatHistoryFile):

    text_content: str

@dataclass(kw_only=True)
class ChatHistoryMessage:

    role: Literal["system", "user", "assistant", "tool"]
    content: str|None = None
    files: List[ChatHistoryFile] = field(default_factory=list)
    tool_calls: List[LLMToolCall] = field(default_factory=list)
    tool_response: Tuple[LLMToolCall, str] = field(default_factory=list)

    is_temporary: bool = False


class ChatHistoryController:

    history: List[ChatHistoryMessage]

    def __init__(self, history: List[ChatHistoryMessage] | None = None, max_tokens: int = Config.MAX_TOKENS, tokenizer: tiktoken = tiktoken.get_encoding("cl100k_base")):
        self.history = history if history else []
        self.max_tokens = max_tokens
        self.tokenizer = tokenizer


    @property
    def system_entry(self) -> ChatHistoryMessage | None:
        if self.history:
            return self.history[0]
        return None

    @system_entry.setter
    def system_entry(self, value: ChatHistoryMessage):
        if not self.history:
            self.history = [value]
        else:
            self.history[0] = value

    def update(self, new_history: List[ChatHistoryMessage], instructions_entry: ChatHistoryMessage | None = None, min_overlap=1, max_tokens:int|None = None, tokenizer: Type[tiktoken]|None = None):

        old_history = self.history
        old_history_without_temporary_messages = [x for x in old_history if not x.is_temporary]

        max_overlap_length = len(old_history_without_temporary_messages)
        overlap_length = None

        for length in range(max_overlap_length, min_overlap, -1):
            if old_history_without_temporary_messages[-length:] == new_history[:length]:
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

        logging.info(f"TOKEN COUNT: {self.count_tokens(tokenizer=tokenizer)}")
        logging.info(f"SYSTEM MESSAGE TOKEN COUNT: {self.count_tokens(history=[self.system_entry], tokenizer=tokenizer)}")

        if self.count_tokens(tokenizer=tokenizer) > (max_tokens if max_tokens else self.max_tokens):
            logging.info("CUTTING BECAUSE OF EXCEEDING TOKEN COUNT")
            self.history = [instructions_entry] if instructions_entry else []
            self.history.extend(new_history)
            logging.info(self.history)


        self.delete_unused_temporary_files(old_history)


    def delete_unused_temporary_files(self, old_history: List[ChatHistoryMessage], new_history: list[ChatHistoryMessage]|None = None):

        new_history = new_history if new_history else self.history

        old_files = [file for entry in old_history for file in entry.files if isinstance(file, ChatHistoryFileSaved) and file.temporary]
        new_files = [file for entry in new_history for file in entry.files if isinstance(file, ChatHistoryFileSaved) and file.temporary]

        for old_file in old_files:
            if old_file not in new_files:
                old_file.delete()



    def build_prompt(self, history: List[ChatHistoryMessage]=None) -> str:
        """Only builds role and content"""

        if history is None:
            history = self.history

        prompt_lines = []
        for msg in history:
            prompt_lines.append(f"{msg.role}: {msg.content}")
        return "\n".join(prompt_lines)

    def count_tokens(self, history: List[ChatHistoryMessage]|None=None, tokenizer: Type[tiktoken]|None = None) -> int:
        prompt = self.build_prompt(history)
        tokenizer = tokenizer if tokenizer else self.tokenizer
        return len(tokenizer.encode(prompt))