import docker
import requests
import json
import time
bot_token = ""
chat_id = ""
container_name_or_id = 'beelzebub'
docker_client = docker.from_env()
api_url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
last_log_message = None
rate_limit = 25
last_message_time = 0

def send_telegram_message(message_text):
    global last_message_time
    current_time = time.time()
    elapsed_time = current_time - last_message_time

    if elapsed_time < 1.0 / rate_limit:
        time.sleep(1.0 / rate_limit - elapsed_time)

    params = {
        'chat_id': chat_id,
        'text': message_text,
    }

    try:
        response = requests.post(api_url, json=params)
        response.raise_for_status()
        last_message_time = time.time()
    except requests.exceptions.HTTPError as e:
        pass
    except requests.exceptions.RequestException as e:
        pass
    except Exception as e:
        pass

def format_ssh_log(log_data):
    formatted_message = f"Time: {log_data.get('DateTime')}\n" \
                        f"Protocol: SSH\n" \
                        f"IP: {log_data.get('RemoteAddr').split(':')[0]}\n" \
                        f"User: {log_data.get('User')}\n" \
                        f"Password: {log_data.get('Password')}\n" \
                        f"Command: {log_data.get('Command')}\n" \
                        f"CommandOutput: {log_data.get('CommandOutput')}"
    return formatted_message

def format_http_log(log_data):
    formatted_message = f"Time: {log_data.get('DateTime')}\n" \
                        f"Protocol: HTTP\n" \
                        f"IP: {log_data.get('RemoteAddr').split(':')[0]}\n" \
                        f"User: {log_data.get('User')}\n" \
                        f"Password: {log_data.get('Password')}\n" \
                        f"RequestURI: {log_data.get('RequestURI')}\n" \
                        f"UserAgent: {log_data.get('UserAgent')}"
    return formatted_message

def format_tcp_log(log_data):
    formatted_message = f"Time: {log_data.get('DateTime')}\n" \
                        f"Protocol: TCP\n" \
                        f"IP: {log_data.get('RemoteAddr').split(':')[0]}\n" \
                        f"Description: {log_data.get('Description')}"
    return formatted_message

def get_new_container_logs(container):
    global last_log_message

    try:
        logs = container.logs(stdout=True, stderr=True, timestamps=False, stream=True)

        for log in logs:
            log_entry = log.decode('utf-8').strip()

            try:
                log_data = json.loads(log_entry)
                event_data = log_data.get("event")

                if event_data is not None:
                    protocol = event_data.get("Protocol")

                    format_function = None

                    if protocol == "SSH":
                        format_function = format_ssh_log
                    elif protocol == "HTTP":
                        format_function = format_http_log
                    elif protocol == "TCP":
                        format_function = format_tcp_log

                    if format_function is not None:
                        formatted_message = format_function(event_data)

                        if formatted_message != last_log_message:
                            send_telegram_message(formatted_message)
                            last_log_message = formatted_message
            except json.JSONDecodeError:
                pass

    except Exception as e:
        print(f'Error getting container logs: {e}')

if __name__ == '__main__':
    try:
        container = docker_client.containers.get(container_name_or_id)

        while True:
            get_new_container_logs(container)
    except docker.errors.NotFound:
        print(f'Container {container_name_or_id} not found.')
    except KeyboardInterrupt:
        print('Script terminated by user.')
    except Exception as e:
        print(f'An error occurred: {e}')
