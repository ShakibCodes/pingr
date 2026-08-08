import socket
import threading

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

client.connect(("127.0.0.1", 5000))

username = input("Enter your username: ")

client.send(username.encode())

print("Connected to server!")


def receive_messages():
    while True:
        try:
            message = client.recv(1024)

            if not message:
                break

            print("\n" + message.decode())

        except:
            break


threading.Thread(
    target=receive_messages,
    daemon=True
).start()


while True:
    message = input("> ")

    client.send(message.encode())