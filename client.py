import socket
import threading

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style


client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

client.connect(("127.0.0.1", 5000))

username = input("Enter your username: ")

client.send(username.encode())


style = Style.from_dict({
    "prompt": "bold",
})


def receive_messages():
    while True:
        try:
            message = client.recv(1024)

            if not message:
                break

            message = message.decode()

            print(f"\n{message}")

        except:
            break


print()
print(f"MSG — connected as {username}")
print()

threading.Thread(
    target=receive_messages,
    daemon=True
).start()


session = PromptSession()

with patch_stdout():
    while True:
        try:
            message = session.prompt(
                HTML("<prompt><b>&gt;&gt;</b> </prompt>"),
                style=style
            )

            if message.strip():
                client.send(message.encode())

        except (KeyboardInterrupt, EOFError):
            break