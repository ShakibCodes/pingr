import socket
import threading

clients = []

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

    while True:
        message = client.recv(1024)

        if not message:
            break

        print("Client:", message.decode())

        broadcast(message)


while True:
    client, address = server.accept()

    clients.append(client)

    thread = threading.Thread(
        target=handle_client,
        args=(client, address),
        daemon=True
    )

    thread.start()