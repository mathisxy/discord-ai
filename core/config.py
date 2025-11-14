import logging

import pytz
from dotenv import load_dotenv
import os

from typing import Literal, List

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
    def extract_ollama_keep_alive(value: str|None) -> str|float|None:
        if not value:
            return None

        value = value.lower().strip()

        try:
            number = float(value)
            return number
        except ValueError:
            return value

    @staticmethod
    def extract_csv_tags(value: str | None) -> List[str]:
        if not value:
            return []
        return [tag.strip() for tag in value.split(",") if tag.strip()]

    @staticmethod
    def require_env(name: str) -> str:
        value = os.getenv(name)
        if value is None or value == "":
            raise RuntimeError(f"Environment variable '{name}' is required but not set.")
        return value




    LOGLEVEL: int = extract_loglevel(require_env("LOGLEVEL"))

    DISCORD_TOKEN: str|None = os.getenv("DISCORD_TOKEN")

    AI: Literal["ollama", "mistral"] = require_env("AI")

    MISTRAL_API_KEY: str|None = os.getenv("MISTRAL_API_KEY")
    MISTRAL_MODEL: str = require_env("MISTRAL_MODEL")

    AZURE_OPENAI_API_KEY: str|None = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_API_VERSION: str = require_env("AZURE_OPENAI_API_VERSION")
    AZURE_OPENAI_ENDPOINT: str = require_env("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_MODEL: str = require_env("AZURE_OPENAI_MODEL")

    OLLAMA_URL: str = require_env("OLLAMA_URL")
    OLLAMA_MODEL: str = require_env("OLLAMA_MODEL")
    OLLAMA_MODEL_TEMPERATURE: float|None = float(value) if (value := os.getenv("OLLAMA_MODEL_TEMPERATURE")) else None
    OLLAMA_THINK: bool|Literal["low", "medium", "high"]|None = extract_ollama_think(os.getenv("OLLAMA_THINK"))
    OLLAMA_KEEP_ALIVE: str|float|None = os.getenv("OLLAMA_KEEP_ALIVE")
    OLLAMA_TIMEOUT: float|None = float(value) if (value := os.getenv("OLLAMA_TIMEOUT")) else None
    OLLAMA_IMAGE_MODEL: bool = os.getenv("OLLAMA_IMAGE_MODEL", "").lower() == "true"
    OLLAMA_IMAGE_MODEL_TYPES: List[str] = extract_csv_tags(require_env("OLLAMA_IMAGE_MODEL_TYPES"))

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


