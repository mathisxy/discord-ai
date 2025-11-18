import re
from pathlib import Path

EXAMPLE_FILE = ".env.example"

def prompt_default(prompt, default=""):
    if default:
        return input(f"{prompt} [{default}]: ") or default
    return input(f"{prompt}: ")

def replace_line(lines, key, value):
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    replaced = False
    for i, line in enumerate(lines):
        if pattern.match(line):
            lines[i] = f"{key}={value}\n"
            replaced = True
            break
    if not replaced:
        lines.append(f"{key}={value}\n")
    return lines

def main():
    if not Path(EXAMPLE_FILE).exists():
        print(f"❌ {EXAMPLE_FILE} not found in current directory.")
        return

    with open(EXAMPLE_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    print("=== Discord Bot Environment Setup ===\n")

    bot_name = prompt_default("Enter bot name", "Emanuel")
    discord_token = prompt_default("Enter Discord Token")
    discord_id = prompt_default("Enter Discord Bot Application ID")
    language = prompt_default("Language (en/de)", "en")

    lines = replace_line(lines, "NAME", bot_name)
    lines = replace_line(lines, "DISCORD_TOKEN", discord_token)
    lines = replace_line(lines, "DISCORD_ID", discord_id)
    lines = replace_line(lines, "LANGUAGE", language)
    lines = replace_line(lines, "COMMAND_NAME", bot_name.lower())

    print("\nChoose AI Provider:")
    print("1) Mistral")
    print("2) Azure OpenAI")
    print("3) Ollama")

    ai_choice = ""
    while ai_choice not in ["1", "2", "3"]:
        ai_choice = input("Enter 1, 2 or 3: ")

    if ai_choice == "1":
        lines = replace_line(lines, "AI", "mistral")
        api_key = prompt_default("Enter Mistral API Key")
        model = prompt_default("Enter Mistral Model", "mistral-medium-latest")
        lines = replace_line(lines, "MISTRAL_API_KEY", api_key)
        lines = replace_line(lines, "MISTRAL_MODEL", model)

    elif ai_choice == "2":
        lines = replace_line(lines, "AI", "azure")
        key = prompt_default("Enter Azure OpenAI API Key")
        endpoint = prompt_default("Enter Azure Endpoint URL")
        model = prompt_default("Enter Azure OpenAI Model", "mistral-medium-2505")
        version = prompt_default("Enter Azure API Version", "2024-10-21")

        lines = replace_line(lines, "AZURE_OPENAI_API_KEY", key)
        lines = replace_line(lines, "AZURE_OPENAI_ENDPOINT", endpoint)
        lines = replace_line(lines, "AZURE_OPENAI_MODEL", model)
        lines = replace_line(lines, "AZURE_OPENAI_API_VERSION", version)

    else:
        lines = replace_line(lines, "AI", "ollama")
        url = prompt_default("Enter Ollama URL", "http://localhost:11434")
        model = prompt_default("Enter Ollama Model", "gemma3:12b")

        lines = replace_line(lines, "OLLAMA_URL", url)
        lines = replace_line(lines, "OLLAMA_MODEL", model)

    env_filename = f".env.{bot_name.lower()}"

    with open(env_filename, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"\n✅ Environment file written: {env_filename}")

if __name__ == "__main__":
    main()
