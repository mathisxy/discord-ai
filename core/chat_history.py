from dataclasses import dataclass, field
from typing import Literal
from pathlib import Path


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

@dataclass
class ChatHistoryMessage:

    role: Literal["system", "user", "assistant"]
    content: str
    files: [ChatHistoryFile] = field(default_factory=list)