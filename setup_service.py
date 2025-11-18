import getpass
from pathlib import Path

def create_systemd_service(bot_name: str, working_dir: str):

    user = getpass.getuser()

    service_content = f"""[Unit]
Description={bot_name} Discord Bot
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={working_dir}
EnvironmentFile={working_dir}/.env.{bot_name}
ExecStart={working_dir}/venv/bin/python main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
"""

    service_file = Path(f"{bot_name}.service")
    service_file.write_text(service_content, encoding="utf-8")

    print(f"\n✅ Service file created: {service_file}")
    print("\nInstall it with:")
    print(f"  sudo cp {service_file} /etc/systemd/system/")
    print("  sudo systemctl daemon-reload")
    print(f"  sudo systemctl enable {bot_name}")
    print(f"  sudo systemctl start {bot_name}")

def main():
    print("=== Create systemd service ===\n")

    bot_name = input("Enter bot name (case-insensitive): ").lower().strip()

    env_file = Path(f".env.{bot_name}")

    if not env_file.exists():
        print(f"❌ Environment file {env_file} does not exist.")
        print("   Run setup_env.py first.")
        return

    working_dir = str(Path.cwd())
    create_systemd_service(bot_name, working_dir)

if __name__ == "__main__":
    main()
