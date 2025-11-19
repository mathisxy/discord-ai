import logging
from pathlib import Path

import pytz
from dotenv import load_dotenv
import os

from typing import Literal, List

from pytimeparse.timeparse import timeparse

load_dotenv()

class Config:

    @staticmethod
    def extract_loglevel(value: str) -> int:
        level = value.upper()
        numeric_level: int = getattr(logging, level)

        if not isinstance(numeric_level, int):
            raise ValueError(f"Ungültiger Loglevel Wert: {value}")

        return numeric_level

    @staticmethod
    def extract_ollama_think(value: str|None) -> bool|Literal["low", "medium", "high"]|None:

        if not value:
            return None

        value = value.lower().strip()

        match value.lower():
            case "low" | "medium" | "high":
                return value
            case "true":
                return True
            case "false":
                return False
            case "true":
                return True
            case _:
                raise Exception(f"Ungültiger Wert für Ollama Think Parameter: {value}")

    @staticmethod
    def extract_csv_tags(value: str | None) -> List[str]:
        if not value:
            return []
        return [tag.strip() for tag in value.split(",") if tag.strip()]

    @staticmethod
    def extract_duration(value: str | None) -> int|float | None:
        """Returns seconds"""

        if not value:
            return None

        return timeparse(value)


    @staticmethod
    def require_env(name: str) -> str:
        value = os.getenv(name)
        if value is None or value == "":
            raise RuntimeError(f"Environment variable '{name}' is required but not set.")
        return value




    LOGLEVEL: int = extract_loglevel(require_env("LOGLEVEL"))

    DISCORD_TOKEN: str|None = os.getenv("DISCORD_TOKEN")

    DOWNLOAD_FOLDER: Path = Path(require_env("DOWNLOAD_FOLDER"))

    AI: Literal["ollama", "mistral"] = require_env("AI")

    MISTRAL_API_KEY: str|None = os.getenv("MISTRAL_API_KEY")
    MISTRAL_MODEL: str = require_env("MISTRAL_MODEL")
    MISTRAL_IMAGE_MODEL: bool = os.getenv("MISTRAL_IMAGE_MODEL", "").lower() == "true"
    MISTRAL_IMAGE_MODEL_TYPES: List[str] = extract_csv_tags(require_env("MISTRAL_IMAGE_MODEL_TYPES"))

    AZURE_OPENAI_API_KEY: str|None = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_API_VERSION: str = require_env("AZURE_OPENAI_API_VERSION")
    AZURE_OPENAI_ENDPOINT: str = require_env("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_MODEL: str = require_env("AZURE_OPENAI_MODEL")

    GEMINI_API_KEY: str|None = os.getenv("GEMINI_API_KEY")
    GEMINI_ENDPOINT: str = require_env("GEMINI_ENDPOINT")
    GEMINI_MODEL: str = require_env("GEMINI_MODEL")

    OPENAI_API_KEY: str|None = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = require_env("OPENAI_MODEL")

    OLLAMA_URL: str = require_env("OLLAMA_URL")
    OLLAMA_MODEL: str = require_env("OLLAMA_MODEL")
    OLLAMA_MODEL_TEMPERATURE: float|None = float(value) if (value := os.getenv("OLLAMA_MODEL_TEMPERATURE")) else None
    OLLAMA_THINK: bool|Literal["low", "medium", "high"]|None = extract_ollama_think(os.getenv("OLLAMA_THINK"))
    OLLAMA_KEEP_ALIVE: float | int | None = extract_duration(os.getenv("OLLAMA_KEEP_ALIVE"))
    OLLAMA_TIMEOUT: float | int | None = extract_duration(os.getenv("OLLAMA_TIMEOUT"))
    OLLAMA_IMAGE_MODEL: bool = os.getenv("OLLAMA_IMAGE_MODEL", "").lower() == "true"
    OLLAMA_IMAGE_MODEL_TYPES: List[str] = extract_csv_tags(require_env("OLLAMA_IMAGE_MODEL_TYPES"))
    OLLAMA_REQUIRED_VRAM_IN_GB: float | int | None = int(value) if (value := os.getenv("OLLAMA_REQUIRED_VRAM_IN_GB")) else None
    OLLAMA_WAIT_FOR_REQUIRED_VRAM: float | int = extract_duration(require_env("OLLAMA_WAIT_FOR_REQUIRED_VRAM"))

    TOOL_INTEGRATION: bool = os.getenv("TOOL_INTEGRATION", "").lower() == "true"
    MCP_SERVER_URL: str|None = os.getenv("MCP_SERVER_URL")
    MCP_INTEGRATION_CLASS: str = require_env("MCP_INTEGRATION_CLASS")
    MCP_TOOL_TAGS: List[str] = extract_csv_tags(os.getenv("MCP_TOOL_TAGS"))
    MCP_ERROR_HELP_DISCORD_ID: int | None = int(value) if (value := os.getenv("MCP_ERROR_HELP_DISCORD_ID")) else None

    MAX_TOKENS: int = int(require_env("MAX_TOKENS"))
    MAX_MESSAGE_COUNT: int = int(require_env("MAX_MESSAGE_COUNT"))
    TOTAL_MESSAGE_SEARCH_COUNT: int = int(require_env("TOTAL_MESSAGE_SEARCH_COUNT"))
    MAX_TOOL_CALLS: int = int(require_env("MAX_TOOL_CALLS"))
    DENY_RECURSIVE_TOOL_CALLING: bool = os.getenv("DENY_RECURSIVE_TOOL_CALLING", "").lower() == "true"

    NAME: str = require_env("NAME")
    INSTRUCTIONS: str = os.getenv("INSTRUCTIONS", "")
    LANGUAGE: Literal["de", "en"] = require_env("LANGUAGE")
    TIMEZONE: pytz.BaseTzInfo = pytz.timezone(require_env("TIMEZONE"))
    DISCORD_ID: int|None = int(value) if (value := os.getenv("DISCORD_ID")) else None
    USERNAMES_CSV_FILE_PATH: str|None = os.getenv("USERNAMES_PATH")
    HISTORY_RESET_TEXT: str = require_env("HISTORY_RESET_TEXT")

    COMMAND_NAME: str = require_env("COMMAND_NAME")


