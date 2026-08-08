import socket
import threading

# =========================
# MESH DATA
# =========================

meshes = {}

# Example:
#
# meshes = {
#     "Friends": {
#         "password": "1234",
#         "clients": {
#             client_socket: "Shakib",
#             client_socket2: "Tabish"
#         }
#     }
# }


# =========================
# SERVER
# =========================

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server.bind(("0.0.0.0", 5000))

server.listen()

print("Server is running")
print("Waiting for connections...")


# =========================
# SEND MESSAGE
# =========================

def send(client, message):
    client.send(message.encode())


# =========================
# BROADCAST
# =========================

def broadcast(mesh_name, message):
    mesh = meshes[mesh_name]

    for client in mesh["clients"]:
        client.send(message.encode())


# =========================
# REMOVE CLIENT
# =========================

def remove_client(client, username, mesh_name):

    if mesh_name in meshes:

        mesh = meshes[mesh_name]

        if client in mesh["clients"]:
            del mesh["clients"][client]

            print(username, "left", mesh_name)

        # If mesh becomes empty, delete it
        if len(mesh["clients"]) == 0:
            del meshes[mesh_name]

            print("Mesh deleted:", mesh_name)

    client.close()


# =========================
# HANDLE CLIENT
# =========================

def handle_client(client, address):

    print("Client connected:", address)

    mesh_name = None
    username = None

    try:

        # =========================
        # USERNAME
        # =========================

        username = client.recv(1024).decode()

        print("Username:", username)

        # =========================
        # WAIT FOR MESH COMMAND
        # =========================

        while True:

            data = client.recv(1024)

            if not data:
                break

            data = data.decode()

            parts = data.split("|")

            command = parts[0]


            # =========================
            # START MESH
            # =========================

            if command == "START":

                if len(parts) < 3:
                    send(client, "ERROR|Invalid start request")
                    continue

                requested_mesh = parts[1]
                password = parts[2]

                # Mesh already exists
                if requested_mesh in meshes:

                    send(
                        client,
                        "ERROR|Mesh already exists"
                    )

                    continue

                # Create mesh
                meshes[requested_mesh] = {
                    "password": password,
                    "clients": {
                        client: username
                    }
                }

                mesh_name = requested_mesh

                print(
                    username,
                    "created mesh:",
                    mesh_name
                )

                send(
                    client,
                    "SUCCESS|Mesh created"
                )

                break


            # =========================
            # JOIN MESH
            # =========================

            elif command == "JOIN":

                if len(parts) < 3:
                    send(client, "ERROR|Invalid join request")
                    continue

                requested_mesh = parts[1]
                password = parts[2]

                # Mesh doesn't exist
                if requested_mesh not in meshes:

                    send(
                        client,
                        "ERROR|Mesh does not exist"
                    )

                    continue

                mesh = meshes[requested_mesh]

                # Wrong password
                if password != mesh["password"]:

                    send(
                        client,
                        "ERROR|Wrong password"
                    )

                    continue

                # Add user
                mesh["clients"][client] = username

                mesh_name = requested_mesh

                print(
                    username,
                    "joined mesh:",
                    mesh_name
                )

                send(
                    client,
                    "SUCCESS|Joined mesh"
                )

                # Tell everyone in the mesh
                broadcast(
                    mesh_name,
                    f"[Server]: {username} joined the mesh"
                )

                break


            else:

                send(
                    client,
                    "ERROR|Unknown command"
                )


        # =========================
        # CHAT
        # =========================

        if mesh_name is None:
            return

        while True:

            data = client.recv(1024)

            if not data:
                break

            message = data.decode()

            # EXIT
            if message == "/exit":
                break

            print(
                username + ":",
                message
            )

            full_message = f"[{username}]: {message}"

            broadcast(
                mesh_name,
                full_message
            )


    except Exception as e:

        print(
            "Connection error:",
            username,
            e
        )


    finally:

        if username is not None:

            remove_client(
                client,
                username,
                mesh_name
            )


# =========================
# ACCEPT CONNECTIONS
# =========================

while True:

    client, address = server.accept()

    thread = threading.Thread(
        target=handle_client,
        args=(client, address),
        daemon=True
    )

    thread.start()