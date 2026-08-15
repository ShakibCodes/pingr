import asyncio
import os
import websockets

# =========================
# SERVER CONFIG
# =========================
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 5000))

# =========================
# MESHES & STATE
# =========================
meshes = {}
active_usernames = set()
state_lock = asyncio.Lock()

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


async def send(websocket, message):
    try:
        await websocket.send(message)
    except Exception:
        pass


async def broadcast(mesh_name, message, exclude=None):
    async with state_lock:
        if mesh_name not in meshes:
            return
        clients = list(meshes[mesh_name]["clients"].keys())

    for client_ws in clients:
        if client_ws == exclude:
            continue
        await send(client_ws, message)


async def send_member_count(mesh_name):
    async with state_lock:
        if mesh_name not in meshes:
            return
        count = len(meshes[mesh_name]["clients"])

    await broadcast(mesh_name, f"COUNT|{count}")


async def remove_client(websocket, username, mesh_name):
    if mesh_name is None:
        return

    left_mesh = False
    remaining_count = 0
    mesh_deleted = False

    async with state_lock:
        if mesh_name in meshes:
            mesh = meshes[mesh_name]

            if websocket in mesh["clients"]:
                del mesh["clients"][websocket]
                left_mesh = True

            remaining_count = len(mesh["clients"])

            if remaining_count == 0:
                del meshes[mesh_name]
                mesh_deleted = True

    if left_mesh and not mesh_deleted:
        await broadcast(mesh_name, f"SERVER|{username} left the mesh")
        await send_member_count(mesh_name)
        print(f"{username} left mesh: {mesh_name}")

    elif left_mesh and mesh_deleted:
        print(f"{username} left mesh: {mesh_name}")
        print(f"Mesh deleted: {mesh_name}")


async def handle_client(websocket):
    print(f"Client connected from {websocket.remote_address}")

    username = None
    mesh_name = None
    username_reserved = False

    try:
        # =========================
        # RECEIVE USERNAME
        # =========================
        raw_username = await websocket.recv()
        username_str = raw_username.rstrip("\n")

        username, error = validate_text(
            username_str, "Username", MAX_USERNAME_LENGTH
        )

        if error:
            await send(websocket, f"ERROR|{error}")
            return

        async with state_lock:
            username_key = username.casefold()

            if username_key in active_usernames:
                username_taken = True
            else:
                username_taken = False
                active_usernames.add(username_key)
                username_reserved = True

        if username_taken:
            await send(websocket, "ERROR|Username is already in use")
            return

        await send(websocket, "USERNAME_OK")
        print("Username accepted:", username)

        # =========================
        # MESH SETUP
        # =========================
        while True:
            raw_req = await websocket.recv()
            data = raw_req.rstrip("\n")
            parts = data.split("|", 2)
            command = parts[0]

            if command == "START":
                if len(parts) < 3:
                    await send(websocket, "ERROR|Invalid start request")
                    continue

                requested_mesh, mesh_error = validate_text(
                    parts[1], "Mesh name", MAX_MESH_NAME_LENGTH
                )
                password, password_error = validate_text(
                    parts[2], "Password", MAX_PASSWORD_LENGTH
                )

                if mesh_error or password_error:
                    await send(websocket, f"ERROR|{mesh_error or password_error}")
                    continue

                async with state_lock:
                    if find_mesh_name(requested_mesh):
                        exists = True
                    else:
                        exists = False
                        meshes[requested_mesh] = {
                            "password": password,
                            "clients": {websocket: username},
                        }

                if exists:
                    await send(websocket, "ERROR|Mesh already exists")
                    continue

                mesh_name = requested_mesh
                print(f"{username} created mesh: {mesh_name}")

                await send(websocket, "SUCCESS|Mesh created")
                await send(websocket, f"SERVER|Mesh '{mesh_name}' created")
                await send_member_count(mesh_name)
                break

            elif command == "JOIN":
                if len(parts) < 3:
                    await send(websocket, "ERROR|Invalid join request")
                    continue

                requested_mesh, mesh_error = validate_text(
                    parts[1], "Mesh name", MAX_MESH_NAME_LENGTH
                )
                password, password_error = validate_text(
                    parts[2], "Password", MAX_PASSWORD_LENGTH
                )

                if mesh_error or password_error:
                    await send(websocket, f"ERROR|{mesh_error or password_error}")
                    continue

                async with state_lock:
                    existing_mesh_name = find_mesh_name(requested_mesh)

                    if existing_mesh_name is None:
                        status = "NOT_FOUND"
                    elif password != meshes[existing_mesh_name]["password"]:
                        status = "WRONG_PASSWORD"
                    else:
                        status = "OK"
                        meshes[existing_mesh_name]["clients"][websocket] = username

                if status == "NOT_FOUND":
                    await send(websocket, "ERROR|Mesh does not exist")
                    continue

                if status == "WRONG_PASSWORD":
                    await send(websocket, "ERROR|Wrong password")
                    continue

                mesh_name = existing_mesh_name
                print(f"{username} joined mesh: {mesh_name}")

                await send(websocket, "SUCCESS|Joined mesh")
                await broadcast(mesh_name, f"SERVER|{username} joined the mesh")
                await send_member_count(mesh_name)
                break

            else:
                await send(websocket, "ERROR|Unknown command")

        # =========================
        # CHAT LOOP
        # =========================
        async for raw_msg in websocket:
            data = raw_msg.rstrip("\n")

            if data.startswith("CMD|"):
                command = data[4:]

                if command == "members":
                    async with state_lock:
                        if mesh_name not in meshes:
                            continue
                        members = list(meshes[mesh_name]["clients"].values())

                    member_data = "|".join(members)
                    await send(websocket, f"MEMBERS|{len(members)}|{member_data}")

                elif command == "exit":
                    break

            elif data.startswith("MSG|"):
                message = data[4:]

                if not message or len(message) > MAX_MESSAGE_LENGTH:
                    await send(
                        websocket,
                        "ERROR|Message must be between 1 and 2000 characters",
                    )
                    continue

                print(f"{username}: {message}")
                await broadcast(mesh_name, f"CHAT|{username}|{message}")

    except websockets.ConnectionClosed:
        pass
    except Exception as e:
        print(f"Connection error for {username}: {e}")
    finally:
        await remove_client(websocket, username, mesh_name)

        if username_reserved and username:
            async with state_lock:
                active_usernames.discard(username.casefold())


async def main():
    print(f"Server listening on {HOST}:{PORT}...")
    async with websockets.serve(handle_client, HOST, PORT):
        await asyncio.Future()  # Keep running standard async event loop


if __name__ == "__main__":
    asyncio.run(main())