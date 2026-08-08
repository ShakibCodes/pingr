import socket
import threading

clients = []
users = {}

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server.bind(("0.0.0.0", 5000))

server.listen()

print("Server is running")
print("Waiting for connections...")


def broadcast(message):
    for client in clients:
        client.send(message)


def handle_client(client, address):
    print("Client connected", address)

    username = client.recv(1024).decode()

    users[client] = username

    print("Username:", username)

    while True:
        try:
            message = client.recv(1024)

            if not message:
                break

            message = message.decode()

            print(username + ":", message)

            full_message = f"[{username}]: {message}"

            broadcast(full_message.encode())

        except:
            break

    clients.remove(client)
    del users[client]

    client.close()

    print("Client disconnected", username)


while True:
    client, address = server.accept()

    clients.append(client)

    thread = threading.Thread(
        target=handle_client,
        args=(client, address),
        daemon=True
    )

    thread.start()