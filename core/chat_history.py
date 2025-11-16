from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ChatHistoryFile:

    name: str
    type: str

@dataclass
class ChatHistoryFileSaved(ChatHistoryFile):

    save_path: str

@dataclass
class ChatHistoryFileText(ChatHistoryFile):

    text_content: str

@dataclass
class ChatHistoryMessage:

    role: Literal["system", "user", "assistant"]
    content: str
    files: [ChatHistoryFile] = field(default_factory=list)