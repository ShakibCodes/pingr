import socket

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server.bind(("0.0.0.0", 5000))

server.listen()

print("Server is running")
print("Waiting for connection...")

client, address = server.accept()

print("Client connected", address)

while True:
    message = client.recv(1024)

    if not message:
        break

    print("Client:", message.decode())

    client.send(message)