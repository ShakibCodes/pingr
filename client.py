import socket
import threading


from prompt_toolkit.application import Application

from prompt_toolkit.layout import (
    Dimension,
    Layout,
    HSplit,
    VSplit,
    Window
)

from prompt_toolkit.layout.controls import (
    FormattedTextControl
)

from prompt_toolkit.formatted_text import (
    FormattedText
)

from prompt_toolkit.widgets import (
    Frame,
    TextArea
)

from prompt_toolkit.styles import (
    Style
)

from prompt_toolkit.key_binding import (
    KeyBindings
)


# ============================================================
# USERNAME
# ============================================================

username = input(
    "Enter your name: "
)


# ============================================================
# CONNECT
# ============================================================

client = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)


client.connect(
    ("127.0.0.1", 5000)
)


# ============================================================
# SEND USERNAME
# ============================================================

client.sendall(
    (
        username + "\n"
    ).encode("utf-8")
)


# ============================================================
# MESH MENU
# ============================================================

menu_choice = 0


menu_options = [
    "Start Mesh",
    "Join Mesh"
]


def menu_text():

    result = []


    for i, option in enumerate(
        menu_options
    ):

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


    return FormattedText(
        result
    )


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


# ============================================================
# MESH INFORMATION
# ============================================================

print()


mesh_name = input(
    "Name of mesh: "
)


mesh_password = input(
    "Password: "
)


# ============================================================
# SEND MESH REQUEST
# ============================================================

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
    (
        request + "\n"
    ).encode("utf-8")
)


# ============================================================
# RECEIVE INITIAL RESPONSE
# ============================================================

reader = client.makefile(
    "r",
    encoding="utf-8"
)


response = reader.readline().rstrip(
    "\n"
)


parts = response.split(
    "|",
    1
)


status = parts[0]


message = (
    parts[1]
    if len(parts) > 1
    else ""
)


if status == "ERROR":

    print()
    print(
        "Error:",
        message
    )

    client.close()

    exit()


# ============================================================
# CHAT DATA
# ============================================================

messages = []


member_count = 1


# ============================================================
# SCROLL STATE
# ============================================================

follow_bottom = True


# ============================================================
# ADD SERVER MESSAGE
# ============================================================

def add_server_message(text):

    messages.append(
        (
            "server",
            None,
            text
        )
    )


# ============================================================
# ADD CLIENT MESSAGE
# ============================================================

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


# ============================================================
# ADD MEMBERS MESSAGE
# ============================================================

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


# ============================================================
# BUILD CHAT TEXT
# ============================================================

def build_chat_text():

    result = []


    for kind, sender, text in messages:


        # ====================================================
        # SERVER
        # ====================================================

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
                (
                    "",
                    "\n\n"
                )
            )


        # ====================================================
        # CLIENT
        # ====================================================

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
                (
                    "",
                    "\n\n"
                )
            )


        # ====================================================
        # MEMBERS
        # ====================================================

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
                (
                    "",
                    "\n"
                )
            )


            for member in text:

                result.append(
                    (
                        "class:member",
                        f"    • {member}"
                    )
                )


                result.append(
                    (
                        "",
                        "\n"
                    )
                )


            result.append(
                (
                    "",
                    "\n"
                )
            )


    return FormattedText(
        result
    )


# ============================================================
# PLAIN CHAT TEXT
#
# TextArea needs actual text so it can scroll naturally.
# ============================================================

def build_plain_chat():

    if not messages:

        return (
            "No messages yet.\n\n"
            "Send a message to start the conversation."
        )


    lines = []


    for kind, sender, text in messages:


        # ====================================================
        # SERVER
        # ====================================================

        if kind == "server":

            lines.append(
                "[Server] " + text
            )

            lines.append("")


        # ====================================================
        # CLIENT
        # ====================================================

        elif kind == "client":

            lines.append(
                f"[{sender}] {text}"
            )

            lines.append("")


        # ====================================================
        # MEMBERS
        # ====================================================

        elif kind == "members":

            lines.append(
                f"[Server] Members ({sender})"
            )

            lines.append("")


            for member in text:

                lines.append(
                    f"    • {member}"
                )


            lines.append("")


    return "\n".join(
        lines
    )


# ============================================================
# CHAT AREA
# ============================================================

chat_area = TextArea(

    text="",

    # Reserve all space not used by the header and input field.  Without an
    # expanding height, prompt_toolkit can size this area to its content.
    height=Dimension(weight=1),

    # Keep the history visibly scrollable as it grows.
    scrollbar=True,

    wrap_lines=True,

    read_only=True,

    focusable=False

)


# ============================================================
# CHAT COLORS
#
# The chat itself is displayed as plain text inside TextArea.
# We redraw the visible lines using an overlay control below.
# ============================================================

def chat_overlay():

    result = []


    for kind, sender, text in messages:


        # ====================================================
        # SERVER
        # ====================================================

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


        # ====================================================
        # CLIENT
        # ====================================================

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


        # ====================================================
        # MEMBERS
        # ====================================================

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


    return FormattedText(
        result
    )


# ============================================================
# CHAT DISPLAY
# ============================================================

chat_display = Window(

    content=FormattedTextControl(
        chat_overlay
    ),

    wrap_lines=True,

    always_hide_cursor=True

)


# ============================================================
# HEADER LEFT
# ============================================================

def header_left():

    return FormattedText([

        (
            "class:title",
            "[ MSG ]"
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


# ============================================================
# HEADER RIGHT
# ============================================================

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


# ============================================================
# NAVIGATION HELP
# ============================================================

def navigation_help():

    return FormattedText([
        ("class:help-key", "Enter"),
        ("class:help-text", " send   "),
        ("class:help-key", "PgUp/PgDn"),
        ("class:help-text", " scroll   "),
        ("class:help-key", "Home/End"),
        ("class:help-text", " top/bottom   "),
        ("class:help-key", "/members"),
        ("class:help-text", " list members   "),
        ("class:help-key", "/exit"),
        ("class:help-text", " disconnect")
    ])


help_bar = Window(

    content=FormattedTextControl(
        navigation_help
    ),

    height=1,

    align="CENTER",

    style="class:help-bar"

)


# ============================================================
# INPUT
# ============================================================

input_field = TextArea(

    height=1,

    prompt=[
        ("class:input-prompt", "Send > ")
    ],

    multiline=False,

    wrap_lines=False,

    style="class:input"

)


# ============================================================
# SEND MESSAGE
# ============================================================

def send_message():

    message = (
        input_field.text.strip()
    )


    if not message:

        return


    # ========================================================
    # /exit
    # ========================================================

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


    # ========================================================
    # /members
    # ========================================================

    if message == "/members":

        try:

            client.sendall(
                b"CMD|members\n"
            )

        except:

            pass


        input_field.text = ""

        return


    # ========================================================
    # NORMAL MESSAGE
    # ========================================================

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


# ============================================================
# SCROLL CONTROL
# ============================================================

def scroll_up():

    global follow_bottom

    follow_bottom = False

    # Move the chat buffer backwards.
    #
    # This is mainly used to tell the UI that the user
    # wants to inspect older messages.

    try:

        chat_area.buffer.cursor_position = max(
            0,
            chat_area.buffer.cursor_position - 500
        )

    except:

        pass


def scroll_down():

    global follow_bottom

    try:

        chat_area.buffer.cursor_position = min(
            len(chat_area.buffer.text),
            chat_area.buffer.cursor_position + 500
        )

    except:

        pass


    if (
        chat_area.buffer.cursor_position
        >= len(chat_area.buffer.text)
    ):

        follow_bottom = True


def scroll_top():

    global follow_bottom

    follow_bottom = False

    try:

        chat_area.buffer.cursor_position = 0

    except:

        pass


def scroll_bottom():

    global follow_bottom

    follow_bottom = True

    try:

        chat_area.buffer.cursor_position = (
            len(chat_area.buffer.text)
        )

    except:

        pass


# ============================================================
# UPDATE CHAT
# ============================================================

def update_chat():

    global follow_bottom


    chat_area.text = build_plain_chat()


    if follow_bottom:

        chat_area.buffer.cursor_position = (
            len(chat_area.buffer.text)
        )


    app.invalidate()


# ============================================================
# KEYBOARD
# ============================================================

chat_kb = KeyBindings()


@chat_kb.add("enter")
def _(event):

    send_message()


# ============================================================
# PAGE UP
# ============================================================

@chat_kb.add("pageup")
def _(event):

    scroll_up()


# ============================================================
# PAGE DOWN
# ============================================================

@chat_kb.add("pagedown")
def _(event):

    scroll_down()


# ============================================================
# HOME
# ============================================================

@chat_kb.add("home")
def _(event):

    scroll_top()


# ============================================================
# END
# ============================================================

@chat_kb.add("end")
def _(event):

    scroll_bottom()


# ============================================================
# STYLE
# ============================================================

style = Style.from_dict({

    # ========================================================
    # HEADER
    # ========================================================

    "title":
        "bold ansiwhite",

    "username":
        "bold ansicyan",

    "mesh":
        "bold ansiwhite",

    "separator":
        "ansibrightblack",

    "count":
        "ansicyan",

    "connected":
        "bold ansigreen",

    "root":
        "bg:#0b0f14",

    "frame.border":
        "ansibrightblack",

    "frame.label":
        "bold ansicyan",

    "chat":
        "bg:#10151c",

    "scrollbar.background":
        "bg:#10151c",

    "scrollbar.button":
        "bg:#3b82f6",

    "scrollbar.arrow":
        "fg:#93c5fd",


    # ========================================================
    # SERVER
    # ========================================================

    "server":
        "bold ansiyellow",

    "server-message":
        "ansiyellow",


    # ========================================================
    # CLIENTS
    # ========================================================

    "client-name":
        "bold ansicyan",

    "self-name":
        "bold ansigreen",

    "message":
        "",


    # ========================================================
    # MEMBERS
    # ========================================================

    "member":
        "ansiyellow",


    # ========================================================
    # COMPOSER AND HELP
    # ========================================================

    "input":
        "bg:#172033 fg:ansiwhite",

    "input-prompt":
        "bold ansicyan",

    "help-bar":
        "bg:#10151c",

    "help-key":
        "bold ansicyan",

    "help-text":
        "ansibrightblack"

})


# ============================================================
# LAYOUT
# ============================================================

root_container = HSplit([

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    header,


    # --------------------------------------------------------
    # SMALL GAP
    # --------------------------------------------------------

    Window(
        char="-",
        height=1,
        style="class:separator"
    ),


    # --------------------------------------------------------
    # CHAT
    # --------------------------------------------------------

    Frame(
        body=chat_area,
        title=" Messages "
    ),


    # --------------------------------------------------------
    # SMALL GAP
    # --------------------------------------------------------

    Window(height=1),


    # --------------------------------------------------------
    # INPUT
    # --------------------------------------------------------

    Frame(
        body=input_field,
        title=" Compose ",
        height=3
    ),


    # --------------------------------------------------------
    # SHORTCUTS
    # --------------------------------------------------------

    help_bar

], style="class:root")


layout = Layout(

    root_container,

    focused_element=input_field

)


# ============================================================
# APPLICATION
# ============================================================

app = Application(

    layout=layout,

    key_bindings=chat_kb,

    style=style,

    # Use the terminal's alternate screen buffer and allow mouse-wheel/
    # scrollbar interaction with the chat history.
    full_screen=True,

    mouse_support=True

)


# ============================================================
# RECEIVE MESSAGES
# ============================================================

def receive_messages():

    global member_count


    while True:

        try:

            line = reader.readline()


            if not line:

                break


            data = line.rstrip(
                "\n"
            )


            parts = data.split(
                "|",
                2
            )


            message_type = parts[0]


            # =================================================
            # SERVER MESSAGE
            # =================================================

            if message_type == "SERVER":

                text = (
                    parts[1]
                    if len(parts) > 1
                    else ""
                )


                add_server_message(
                    text
                )


            # =================================================
            # CHAT MESSAGE
            # =================================================

            elif message_type == "CHAT":

                if len(parts) < 3:

                    continue


                sender = parts[1]
                text = parts[2]


                add_client_message(
                    sender,
                    text
                )


            # =================================================
            # MEMBER COUNT
            # =================================================

            elif message_type == "COUNT":

                if len(parts) < 2:

                    continue


                try:

                    member_count = int(
                        parts[1]
                    )

                except:

                    pass


            # =================================================
            # MEMBERS
            # =================================================

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


            # =================================================
            # UPDATE UI
            # =================================================

            update_chat()


        except:

            break


# ============================================================
# START RECEIVER THREAD
# ============================================================

threading.Thread(

    target=receive_messages,

    daemon=True

).start()


# ============================================================
# START APPLICATION
# ============================================================

app.run()
