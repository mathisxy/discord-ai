import re
from pathlib import Path

EXAMPLE_FILE = ".env.example"

def prompt_default(prompt, default=""):
    """Prompt user with optional default value."""
    if default:
        return input(f"{prompt} [{default}]: ") or default
    return input(f"{prompt}: ")

def replace_line(lines, key, value):
    """
    Replace the line in lines that starts with key= with key=value.
    If key does not exist, append it at the end.
    """
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

    print("=== Minimal Setup for Discord Bot ===\n")

    # ----------------------------
    # General settings
    # ----------------------------
    bot_name = prompt_default("Enter bot name", "Emanuel")
    discord_token = prompt_default("Enter Discord Token")
    discord_id = prompt_default("Enter Discord Bot ID")
    language = prompt_default("Interface language (en/de)", "en")

    lines = replace_line(lines, "NAME", bot_name)
    lines = replace_line(lines, "DISCORD_TOKEN", discord_token)
    lines = replace_line(lines, "DISCORD_ID", discord_id)
    lines = replace_line(lines, "LANGUAGE", language)
    lines = replace_line(lines, "COMMAND_NAME", bot_name.lower())

    # ----------------------------
    # AI Provider choice
    # ----------------------------
    print("\nChoose AI Provider:")
    print("1) Mistral")
    print("2) Azure OpenAI")
    print("3) Ollama")
    ai_choice = ""
    while ai_choice not in ["1", "2", "3"]:
        ai_choice = input("Enter 1, 2 or 3: ")

    if ai_choice == "1":
        lines = replace_line(lines, "AI", "mistral")
        mistral_api_key = prompt_default("Enter Mistral API Key")
        lines = replace_line(lines, "MISTRAL_API_KEY", mistral_api_key)
        mistral_model = prompt_default("Enter Mistral Model", "mistral-medium-latest")
        lines = replace_line(lines, "MISTRAL_MODEL", mistral_model)

    elif ai_choice == "2":
        lines = replace_line(lines, "AI", "azure")
        azure_key = prompt_default("Enter Azure OpenAI API Key")
        lines = replace_line(lines, "AZURE_OPENAI_API_KEY", azure_key)
        azure_endpoint = prompt_default(
            "Enter Azure OpenAI Endpoint URL (e.g., https://<YOUR_AZURE_OPENAI_RESOURCE_HERE>.openai.azure.com/)")
        lines = replace_line(lines, "AZURE_OPENAI_ENDPOINT", azure_endpoint)
        azure_model = prompt_default("Enter Azure OpenAI Model", "mistral-medium-2505")
        lines = replace_line(lines, "AZURE_OPENAI_MODEL", azure_model)
        azure_version = prompt_default("Enter Azure OpenAI API Version", "2024-10-21")
        lines = replace_line(lines, "AZURE_OPENAI_API_VERSION", azure_version)

    else:  # Ollama
        lines = replace_line(lines, "AI", "ollama")
        ollama_url = prompt_default("Enter Ollama Server URL", "http://localhost:11434")
        lines = replace_line(lines, "OLLAMA_URL", ollama_url)
        ollama_model = prompt_default("Enter Ollama Model", "gemma3:12b")
        lines = replace_line(lines, "OLLAMA_MODEL", ollama_model)
        ollama_temp = prompt_default("Enter Ollama Model Temperature (leave blank for default)")
        lines = replace_line(lines, "OLLAMA_MODEL_TEMPERATURE", ollama_temp)
        ollama_timeout = prompt_default("Enter Ollama Timeout in seconds", "300")
        lines = replace_line(lines, "OLLAMA_TIMEOUT", ollama_timeout)

    # ----------------------------
    # Save new env file
    # ----------------------------
    output_file = f".env.{bot_name}"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"\n✅ Configuration saved to {output_file}")

if __name__ == "__main__":
    main()
