import socket
import threading

from prompt_toolkit.application import Application
from prompt_toolkit.layout import (
    Layout,
    HSplit,
    VSplit,
    Window,
    ScrollOffsets
)
from prompt_toolkit.layout.controls import (
    FormattedTextControl,
    BufferControl
)

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.formatted_text import (
    FormattedText
)
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.styles import Style
from prompt_toolkit.key_binding import KeyBindings


# =========================
# USERNAME
# =========================

username = input("Enter your name: ")


# =========================
# CONNECT
# =========================

client = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)

client.connect(
    ("127.0.0.1", 5000)
)


# Send username
client.sendall(
    (username + "\n").encode("utf-8")
)


# =========================
# MESH MENU
# =========================

menu_choice = 0

menu_options = [
    "Start Mesh",
    "Join Mesh"
]


def menu_text():

    result = []

    for i, option in enumerate(menu_options):

        prefix = (
            "> "
            if i == menu_choice
            else "  "
        )

        result.append(
            (
                "class:selected"
                if i == menu_choice
                else "",
                prefix + option
            )
        )

        if i != len(menu_options) - 1:

            result.append(
                ("", "\n")
            )

    return FormattedText(result)


menu_control = FormattedTextControl(
    menu_text
)


menu_window = Window(
    content=menu_control
)


menu_kb = KeyBindings()


@menu_kb.add("up")
def _(event):

    global menu_choice

    menu_choice = (
        menu_choice - 1
    ) % len(menu_options)

    event.app.invalidate()


@menu_kb.add("down")
def _(event):

    global menu_choice

    menu_choice = (
        menu_choice + 1
    ) % len(menu_options)

    event.app.invalidate()


@menu_kb.add("enter")
def _(event):

    event.app.exit()


menu_layout = Layout(
    HSplit([
        Window(height=2),
        menu_window
    ])
)


menu_style = Style.from_dict({

    "selected":
        "bold ansicyan"

})


menu_app = Application(

    layout=menu_layout,

    key_bindings=menu_kb,

    style=menu_style,

    full_screen=True

)


menu_app.run()


selected_option = menu_options[
    menu_choice
]


# =========================
# MESH INFORMATION
# =========================

print()

mesh_name = input(
    "Name of mesh: "
)

mesh_password = input(
    "Password: "
)


# =========================
# SEND MESH REQUEST
# =========================

if selected_option == "Start Mesh":

    request = (
        f"START|"
        f"{mesh_name}|"
        f"{mesh_password}"
    )

else:

    request = (
        f"JOIN|"
        f"{mesh_name}|"
        f"{mesh_password}"
    )


client.sendall(
    (request + "\n").encode("utf-8")
)


# =========================
# RECEIVE INITIAL RESPONSE
# =========================

reader = client.makefile(
    "r",
    encoding="utf-8"
)


response = reader.readline().rstrip("\n")


parts = response.split("|", 1)


status = parts[0]

message = (
    parts[1]
    if len(parts) > 1
    else ""
)


if status == "ERROR":

    print()
    print("Error:", message)

    client.close()

    exit()


# =========================
# CHAT DATA
# =========================

messages = []

member_count = 1


# =========================
# ADD SERVER MESSAGE
# =========================

def add_server_message(text):

    messages.append(
        (
            "server",
            None,
            text
        )
    )


# =========================
# ADD CLIENT MESSAGE
# =========================

def add_client_message(
    sender,
    text
):

    messages.append(
        (
            "client",
            sender,
            text
        )
    )


# =========================
# ADD MEMBERS MESSAGE
# =========================

def add_members_message(
    count,
    members
):

    messages.append(
        (
            "members",
            count,
            members
        )
    )


# =========================
# CHAT FORMATTING
# =========================

def chat_text():

    result = []

    for kind, sender, text in messages:


        # =========================
        # SERVER
        # =========================

        if kind == "server":

            result.append(
                (
                    "class:server",
                    "[Server] "
                )
            )

            result.append(
                (
                    "class:server-message",
                    text
                )
            )

            result.append(
                ("", "\n\n")
            )


        # =========================
        # CLIENT
        # =========================

        elif kind == "client":

            if sender == username:

                name_style = (
                    "class:self-name"
                )

            else:

                name_style = (
                    "class:client-name"
                )


            result.append(
                (
                    name_style,
                    f"[{sender}] "
                )
            )

            result.append(
                (
                    "class:message",
                    text
                )
            )

            result.append(
                ("", "\n\n")
            )


        # =========================
        # MEMBERS
        # =========================

        elif kind == "members":

            result.append(
                (
                    "class:server",
                    "[Server] "
                )
            )

            result.append(
                (
                    "class:server-message",
                    f"Members ({sender})"
                )
            )

            result.append(
                ("", "\n")
            )


            for member in text:

                result.append(
                    (
                        "class:member",
                        f"    • {member}"
                    )
                )

                result.append(
                    ("", "\n")
                )


            result.append(
                ("", "\n")
            )


    return FormattedText(result)


# =========================
# CHAT WINDOW
# =========================

# =========================
# CHAT BUFFER
# =========================

chat_buffer = Buffer(
    read_only=True
)


# =========================
# CHAT CONTROL
# =========================

chat_control = BufferControl(
    buffer=chat_buffer,
    focusable=False,
    show_cursor=False
)


# =========================
# CHAT WINDOW
# =========================

chat_window = Window(
    content=chat_control,
    wrap_lines=True,
    always_hide_cursor=True,
    scroll_offsets=ScrollOffsets(
        top=2,
        bottom=2
    )
)


# =========================
# HEADER LEFT
# =========================

def header_left():

    return FormattedText([

        (
            "class:title",
            "MSG"
        ),

        (
            "class:separator",
            "  •  "
        ),

        (
            "class:username",
            username
        ),

        (
            "class:separator",
            "  •  "
        ),

        (
            "class:mesh",
            mesh_name
        )

    ])


# =========================
# HEADER RIGHT
# =========================

def header_right():

    return FormattedText([

        (
            "class:count",
            f"{member_count} "
            f"{'member' if member_count == 1 else 'members'}"
        ),

        (
            "class:separator",
            "  •  "
        ),

        (
            "class:connected",
            "● Connected"
        )

    ])


header = VSplit([

    Window(
        content=FormattedTextControl(
            header_left
        )
    ),

    Window(
        content=FormattedTextControl(
            header_right
        ),
        align="RIGHT"
    )

])


# =========================
# INPUT
# =========================

input_field = TextArea(

    height=1,

    prompt=">> ",

    multiline=False

)


# =========================
# SEND
# =========================

def send_message():

    message = input_field.text.strip()


    if not message:
        return


    # =========================
    # /exit
    # =========================

    if message == "/exit":

        try:

            client.sendall(
                b"CMD|exit\n"
            )

        except:

            pass


        try:
            client.close()

        except:

            pass


        app.exit()

        return


    # =========================
    # /members
    # =========================

    if message == "/members":

        try:

            client.sendall(
                b"CMD|members\n"
            )

        except:

            pass


        input_field.text = ""

        return


    # =========================
    # NORMAL MESSAGE
    # =========================

    try:

        client.sendall(
            (
                "MSG|"
                + message
                + "\n"
            ).encode("utf-8")
        )

    except:

        pass


    input_field.text = ""


# =========================
# KEYBINDINGS
# =========================

chat_kb = KeyBindings()


@chat_kb.add("enter")
def _(event):

    send_message()


# =========================
# STYLE
# =========================

style = Style.from_dict({

    # Header
    "title":
        "bold",

    "username":
        "bold ansicyan",

    "mesh":
        "bold",

    "separator":
        "ansibrightblack",

    "count":
        "ansicyan",

    "connected":
        "bold ansigreen",


    # Server
    "server":
        "bold ansiyellow",

    "server-message":
        "ansiyellow",


    # Clients
    "client-name":
        "bold ansicyan",

    "self-name":
        "bold ansigreen",

    "message":
        "",


    # Members
    "member":
        "ansiyellow",

})


# =========================
# LAYOUT
# =========================

root_container = HSplit([

    # Header
    header,

    Window(height=1),

    # Messages
    chat_window,

    Window(height=1),

    # Input
    input_field

])


layout = Layout(

    root_container,

    focused_element=input_field

)


# =========================
# APPLICATION
# =========================

app = Application(

    layout=layout,

    key_bindings=chat_kb,

    style=style,

    full_screen=True

)


# =========================
# RECEIVE MESSAGES
# =========================

def receive_messages():

    global member_count


    while True:

        try:

            line = reader.readline()

            if not line:
                break


            data = line.rstrip("\n")

            parts = data.split("|", 2)

            message_type = parts[0]


            # =========================
            # SERVER MESSAGE
            # =========================

            if message_type == "SERVER":

                text = (
                    parts[1]
                    if len(parts) > 1
                    else ""
                )

                add_server_message(text)


            # =========================
            # CHAT MESSAGE
            # =========================

            elif message_type == "CHAT":

                if len(parts) < 3:
                    continue

                sender = parts[1]
                text = parts[2]

                add_client_message(
                    sender,
                    text
                )


            # =========================
            # MEMBER COUNT
            # =========================

            elif message_type == "COUNT":

                if len(parts) < 2:
                    continue

                try:

                    member_count = int(
                        parts[1]
                    )

                except:

                    pass


            # =========================
            # MEMBERS
            # =========================

            elif message_type == "MEMBERS":

                if len(parts) < 2:
                    continue

                try:

                    count = int(
                        parts[1]
                    )

                except:

                    count = 0


                members = []


                if len(parts) >= 3:

                    members = [
                        name
                        for name
                        in parts[2].split("|")
                        if name
                    ]


                add_members_message(
                    count,
                    members
                )


            # Redraw UI
            app.invalidate()


        except:

            break


# =========================
# START RECEIVER
# =========================

threading.Thread(

    target=receive_messages,

    daemon=True

).start()


# =========================
# START APP
# =========================

app.run()