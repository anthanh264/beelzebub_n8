import json
from collections import Counter
import asyncio
from telegram import Bot
import schedule
import time
import docker

TELEGRAM_BOT_TOKEN = "6428255299:AAGK42E7h-a4625uN_HTm_gN8RVdxzjky2Q"
chat_id = "-4015337273"
time_receive = "08:00"

client = docker.from_env()
container = client.containers.get('beelzebub')
container_id = container.id
logs_path = '/var/lib/docker/containers/'+container_id+'/'+container_id+'-json.log'

def perform_analytics_and_send_message():
    with open(logs_path, "r", encoding="utf-8") as file:
        log_entries = file.readlines()

    ssh_usernames = Counter()
    ssh_passwords = Counter()
    combined_credentials = Counter()
    connections_per_ip = Counter()
    ssh_commands = Counter()

    for log_entry in log_entries:
        try:
            log_data = json.loads(log_entry)
            log_content = json.loads(log_data.get("log", "{}"))

            event_data = log_content.get("event")
            if event_data is None:
                continue

            protocol = event_data.get("Protocol")

            remote_addr = event_data.get("RemoteAddr").split(":")[0]
            if remote_addr:
                connections_per_ip[remote_addr] += 1

            if protocol == "SSH":
                username = event_data.get("User")
                password = event_data.get("Password")
                command = event_data.get("Command")

                if username:
                    ssh_usernames[username] += 1

                if password:
                    ssh_passwords[password] += 1

                if username and password:
                    combined_credentials[(username, password)] += 1

                if command:
                    ssh_commands[command] += 1

        except json.JSONDecodeError as e:
            pass
        except Exception as e:
            pass

    top_ssh_usernames = dict(ssh_usernames.most_common(10))
    top_ssh_passwords = dict(ssh_passwords.most_common(10))
    top_combined_credentials = dict(combined_credentials.most_common(10))
    top_ssh_commands = dict(ssh_commands.most_common(10))

    top_ips = dict(connections_per_ip.most_common(10))

    combined_output = ""

    combined_output += "Top 10 SSH Usernames:\n"
    for username, count in top_ssh_usernames.items():
        combined_output += f"{username}: {count}\n"

    combined_output += "\nTop 10 SSH Passwords:\n"
    for password, count in top_ssh_passwords.items():
        combined_output += f"{password}: {count}\n"

    combined_output += "\nTop 10 Combined SSH Credentials:\n"
    for (username, password), count in top_combined_credentials.items():
        combined_output += f"{username} / {password}: {count}\n"

    combined_output += "\nTop 10 SSH Commands:\n"
    for command, count in top_ssh_commands.items():
        combined_output += f"{command}: {count}\n"

    combined_output += "\nTop 10 IPs by Connection Count (All Protocols):\n"
    for ip, count in top_ips.items():
        combined_output += f"{ip}: {count}\n"

    print("Analytics:\n", combined_output)

    async def send_telegram_message():
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=chat_id, text=combined_output)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(send_telegram_message())

schedule.every().day.at(time_receive).do(perform_analytics_and_send_message)

while True:
    schedule.run_pending()
    time.sleep(1)
