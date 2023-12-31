import json
from collections import Counter
import asyncio
from telegram import Bot
import schedule
import time
import docker
import datetime

bot_token = ""
chat_id = ""
hours_log = 5

client = docker.from_env()
container = client.containers.get('beelzebub')
container_id = container.id
logs_path0 = "logs.txt"
logs_path = '/var/lib/docker/containers/'+container_id+'/'+container_id+'-json.log'
def parse_custom_timestamp(timestamp_str):
    try:
        return datetime.datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%SZ')

    except ValueError:
        return None

def perform_analytics_and_send_message():
    try:
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(hours=hours_log)
        start_time_GMT7 = start_time + datetime.timedelta(hours=7)   
        end_time_GMT7 = end_time + datetime.timedelta(hours=7)  
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
                
                timestamp_str = event_data.get("DateTime")
                if not timestamp_str:
                    continue
                timestamp = parse_custom_timestamp(timestamp_str)
                if not timestamp:                    
                    continue
                if timestamp > start_time and timestamp < end_time:
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
                print(f"JSON decoding error: {e}")
            except Exception as e:
                print(f'Error getting : {e}')

        top_ssh_usernames = dict(ssh_usernames.most_common(10))
        top_ssh_passwords = dict(ssh_passwords.most_common(10))
        top_combined_credentials = dict(combined_credentials.most_common(10))
        top_ssh_commands = dict(ssh_commands.most_common(10))

        top_ips = dict(connections_per_ip.most_common(10))

        combined_output = ""
        combined_output += f"From {start_time_GMT7} to {end_time_GMT7}\n"
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
        
        #print("Analytics:\n", combined_output)
        async def send_telegram_message():
            bot = Bot(token=bot_token)
            await bot.send_message(chat_id=chat_id, text=combined_output)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(send_telegram_message())

    except Exception as e:
        print(f'Error in analytics and message sending: {e}')

perform_analytics_and_send_message()

while True:
    time.sleep(hours_log * 3600)  
    perform_analytics_and_send_message()

