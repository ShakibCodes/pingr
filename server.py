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


# Usernames are unique across all currently connected clients.  Store their
# case-folded form so that "Shakib" and "shakib" cannot impersonate each other.
active_usernames = set()

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


MAX_USERNAME_LENGTH = 24
MAX_MESH_NAME_LENGTH = 32
MAX_PASSWORD_LENGTH = 128
MAX_MESSAGE_LENGTH = 2_000


def validate_text(value, label, maximum_length, allow_empty=False):

    """Return a safe protocol value or a short validation error."""

    value = value.strip()


    if not value and not allow_empty:

        return None, f"{label} cannot be empty"


    if len(value) > maximum_length:

        return None, f"{label} must be {maximum_length} characters or fewer"


    if "|" in value or any(ord(character) < 32 for character in value):

        return None, f"{label} contains unsupported characters"


    return value, None


def find_mesh_name(requested_mesh):

    """Find a mesh case-insensitively while preserving its display name."""

    requested_key = requested_mesh.casefold()


    for existing_name in meshes:

        if existing_name.casefold() == requested_key:

            return existing_name


    return None


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

server.bind(
    (HOST, PORT)
)

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

def broadcast(
    mesh_name,
    message,
    exclude=None
):

    with mesh_lock:

        if mesh_name not in meshes:
            return

        clients = list(
            meshes[mesh_name]["clients"].keys()
        )

    for client in clients:

        if client == exclude:
            continue

        send(
            client,
            message
        )


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


            # =========================
            # DELETE EMPTY MESH
            # =========================

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

        send_member_count(
            mesh_name
        )

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

def handle_client(
    client,
    address
):

    print(
        "Client connected:",
        address
    )


    username = None
    mesh_name = None
    username_reserved = False


    try:

        # =========================
        # LINE READER
        # =========================

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


        username, error = validate_text(
            line.rstrip("\n"),
            "Username",
            MAX_USERNAME_LENGTH
        )


        if error:

            send(
                client,
                f"ERROR|{error}"
            )

            return


        with mesh_lock:

            username_key = username.casefold()


            if username_key in active_usernames:

                username_taken = True

            else:

                username_taken = False
                active_usernames.add(
                    username_key
                )
                username_reserved = True


        if username_taken:

            send(
                client,
                "ERROR|Username is already in use"
            )

            return


        send(
            client,
            "USERNAME_OK"
        )


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


            parts = data.split(
                "|",
                2
            )


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


                requested_mesh, mesh_error = validate_text(
                    parts[1],
                    "Mesh name",
                    MAX_MESH_NAME_LENGTH
                )

                password, password_error = validate_text(
                    parts[2],
                    "Password",
                    MAX_PASSWORD_LENGTH
                )


                if mesh_error or password_error:

                    send(
                        client,
                        f"ERROR|{mesh_error or password_error}"
                    )

                    continue


                with mesh_lock:

                    if find_mesh_name(requested_mesh):

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


                send_member_count(
                    mesh_name
                )


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


                requested_mesh, mesh_error = validate_text(
                    parts[1],
                    "Mesh name",
                    MAX_MESH_NAME_LENGTH
                )

                password, password_error = validate_text(
                    parts[2],
                    "Password",
                    MAX_PASSWORD_LENGTH
                )


                if mesh_error or password_error:

                    send(
                        client,
                        f"ERROR|{mesh_error or password_error}"
                    )

                    continue


                with mesh_lock:

                    existing_mesh_name = find_mesh_name(
                        requested_mesh
                    )


                    if existing_mesh_name is None:

                        status = "NOT_FOUND"

                    elif (
                        password
                        != meshes[existing_mesh_name]["password"]
                    ):

                        status = "WRONG_PASSWORD"

                    else:

                        status = "OK"

                        meshes[
                            existing_mesh_name
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


                mesh_name = existing_mesh_name


                print(
                    f"{username} joined mesh: {mesh_name}"
                )


                send(
                    client,
                    "SUCCESS|Joined mesh"
                )


                # =========================
                # TELL EVERYONE
                # =========================

                broadcast(
                    mesh_name,
                    f"SERVER|{username} joined the mesh"
                )


                # =========================
                # UPDATE COUNT
                # =========================

                send_member_count(
                    mesh_name
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


                if not message or len(message) > MAX_MESSAGE_LENGTH:

                    send(
                        client,
                        "ERROR|Message must be between 1 and 2000 characters"
                    )

                    continue


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


        if username_reserved and username:

            with mesh_lock:

                active_usernames.discard(
                    username.casefold()
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