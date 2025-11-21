from dataclasses import dataclass, field
from typing import Literal, Tuple
from pathlib import Path

from providers.base import LLMToolCall


@dataclass
class ChatHistoryFile:

    name: str
    mime_type: str

@dataclass
class ChatHistoryFileSaved(ChatHistoryFile):

    save_path: Path

@dataclass
class ChatHistoryFileText(ChatHistoryFile):

    text_content: str

@dataclass(kw_only=True)
class ChatHistoryMessage:

    role: Literal["system", "user", "assistant", "tool"]
    content: str|None = None
    files: [ChatHistoryFile] = field(default_factory=list)
    tool_calls: [LLMToolCall] = field(default_factory=list)
    tool_responses: [Tuple[LLMToolCall, str]] = field(default_factory=list)

    is_temporary: bool = False