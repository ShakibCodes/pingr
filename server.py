import socket
import threading


# =========================
# SERVER CONFIG
# =========================

HOST = "0.0.0.0"
PORT = 5000


# =========================
# MESHES
# =========================

meshes = {}

# Structure:
#
# meshes = {
#     "Brother": {
#         "password": "1234",
#         "clients": {
#             socket1: "Shakib",
#             socket2: "Tabish"
#         }
#     }
# }


mesh_lock = threading.Lock()


# =========================
# SOCKET
# =========================

server = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)

server.setsockopt(
    socket.SOL_SOCKET,
    socket.SO_REUSEADDR,
    1
)

server.bind((HOST, PORT))
server.listen()


print("Server is running")
print("Waiting for connections...")


# =========================
# SEND
# =========================

def send(client, message):

    try:
        client.sendall(
            (message + "\n").encode("utf-8")
        )

    except:
        pass


# =========================
# BROADCAST
# =========================

def broadcast(mesh_name, message, exclude=None):

    with mesh_lock:

        if mesh_name not in meshes:
            return

        clients = list(
            meshes[mesh_name]["clients"].keys()
        )

    for client in clients:

        if client == exclude:
            continue

        send(client, message)


# =========================
# SEND MEMBER COUNT
# =========================

def send_member_count(mesh_name):

    with mesh_lock:

        if mesh_name not in meshes:
            return

        count = len(
            meshes[mesh_name]["clients"]
        )

    broadcast(
        mesh_name,
        f"COUNT|{count}"
    )


# =========================
# REMOVE CLIENT
# =========================

def remove_client(
    client,
    username,
    mesh_name
):

    if mesh_name is None:

        try:
            client.close()
        except:
            pass

        return


    left_mesh = False
    remaining_count = 0
    mesh_deleted = False


    with mesh_lock:

        if mesh_name in meshes:

            mesh = meshes[mesh_name]

            if client in mesh["clients"]:

                del mesh["clients"][client]

                left_mesh = True

            remaining_count = len(
                mesh["clients"]
            )


            # Delete empty mesh
            if remaining_count == 0:

                del meshes[mesh_name]

                mesh_deleted = True


    # =========================
    # NOTIFY EVERYONE
    # =========================

    if left_mesh and not mesh_deleted:

        broadcast(
            mesh_name,
            f"SERVER|{username} left the mesh"
        )

        send_member_count(mesh_name)

        print(
            f"{username} left mesh: {mesh_name}"
        )

    elif left_mesh and mesh_deleted:

        print(
            f"{username} left mesh: {mesh_name}"
        )

        print(
            f"Mesh deleted: {mesh_name}"
        )


    try:
        client.close()

    except:
        pass


# =========================
# HANDLE CLIENT
# =========================

def handle_client(client, address):

    print(
        "Client connected:",
        address
    )

    username = None
    mesh_name = None

    try:

        # Create a line-based reader.
        # Every message ends with \n.
        reader = client.makefile(
            "r",
            encoding="utf-8"
        )


        # =========================
        # USERNAME
        # =========================

        line = reader.readline()

        if not line:
            return

        username = line.rstrip("\n")

        print(
            "Username:",
            username
        )


        # =========================
        # MESH SETUP
        # =========================

        while True:

            line = reader.readline()

            if not line:
                return

            data = line.rstrip("\n")

            parts = data.split("|", 2)

            command = parts[0]


            # =========================
            # START MESH
            # =========================

            if command == "START":

                if len(parts) < 3:

                    send(
                        client,
                        "ERROR|Invalid start request"
                    )

                    continue


                requested_mesh = parts[1]
                password = parts[2]


                with mesh_lock:

                    if requested_mesh in meshes:

                        exists = True

                    else:

                        exists = False

                        meshes[requested_mesh] = {
                            "password": password,
                            "clients": {
                                client: username
                            }
                        }


                if exists:

                    send(
                        client,
                        "ERROR|Mesh already exists"
                    )

                    continue


                mesh_name = requested_mesh

                print(
                    f"{username} created mesh: {mesh_name}"
                )


                send(
                    client,
                    "SUCCESS|Mesh created"
                )


                send(
                    client,
                    f"SERVER|Mesh '{mesh_name}' created"
                )


                send_member_count(mesh_name)

                break


            # =========================
            # JOIN MESH
            # =========================

            elif command == "JOIN":

                if len(parts) < 3:

                    send(
                        client,
                        "ERROR|Invalid join request"
                    )

                    continue


                requested_mesh = parts[1]
                password = parts[2]


                with mesh_lock:

                    if requested_mesh not in meshes:

                        status = "NOT_FOUND"

                    elif (
                        password
                        != meshes[requested_mesh]["password"]
                    ):

                        status = "WRONG_PASSWORD"

                    else:

                        status = "OK"

                        meshes[
                            requested_mesh
                        ]["clients"][client] = username


                if status == "NOT_FOUND":

                    send(
                        client,
                        "ERROR|Mesh does not exist"
                    )

                    continue


                if status == "WRONG_PASSWORD":

                    send(
                        client,
                        "ERROR|Wrong password"
                    )

                    continue


                mesh_name = requested_mesh


                print(
                    f"{username} joined mesh: {mesh_name}"
                )


                send(
                    client,
                    "SUCCESS|Joined mesh"
                )


                # Tell everyone
                broadcast(
                    mesh_name,
                    f"SERVER|{username} joined the mesh"
                )


                # Update count
                send_member_count(mesh_name)

                break


            else:

                send(
                    client,
                    "ERROR|Unknown command"
                )


        # =========================
        # CHAT
        # =========================

        while True:

            line = reader.readline()

            if not line:
                break

            data = line.rstrip("\n")


            # =========================
            # COMMAND
            # =========================

            if data.startswith("CMD|"):

                command = data[4:]


                # =========================
                # /members
                # =========================

                if command == "members":

                    with mesh_lock:

                        if mesh_name not in meshes:
                            continue

                        members = list(
                            meshes[
                                mesh_name
                            ]["clients"].values()
                        )


                    # Send ONLY to this client
                    member_data = "|".join(
                        members
                    )

                    send(
                        client,
                        f"MEMBERS|{len(members)}|{member_data}"
                    )


                # =========================
                # /exit
                # =========================

                elif command == "exit":

                    break


            # =========================
            # NORMAL MESSAGE
            # =========================

            elif data.startswith("MSG|"):

                message = data[4:]


                print(
                    f"{username}: {message}"
                )


                broadcast(
                    mesh_name,
                    f"CHAT|{username}|{message}"
                )


    except Exception as e:

        print(
            "Connection error:",
            username,
            e
        )


    finally:

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