import socket
import threading

from prompt_toolkit.application import Application
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style
from prompt_toolkit.key_binding import KeyBindings


# =========================
# USERNAME
# =========================

username = input("Enter your name: ")


# =========================
# CONNECT TO SERVER
# =========================

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

client.connect(("127.0.0.1", 5000))

# Send username first
client.send(username.encode())


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

        prefix = "> " if i == menu_choice else "  "

        result.append(
            (
                "class:selected"
                if i == menu_choice
                else "",
                prefix + option
            )
        )

        if i != len(menu_options) - 1:
            result.append(("", "\n"))

    return FormattedText(result)


menu_control = FormattedTextControl(menu_text)


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
    "selected": "bold"
})


menu_app = Application(
    layout=menu_layout,
    key_bindings=menu_kb,
    style=menu_style,
    full_screen=True
)


menu_app.run()


selected_option = menu_options[menu_choice]


# =========================
# MESH INFORMATION
# =========================

print()


mesh_name = input("Name of mesh: ")
mesh_password = input("Password: ")


# =========================
# SEND MESH REQUEST
# =========================

if selected_option == "Start Mesh":

    request = f"START|{mesh_name}|{mesh_password}"

else:

    request = f"JOIN|{mesh_name}|{mesh_password}"


client.send(request.encode())


# =========================
# RECEIVE SERVER RESPONSE
# =========================

response = client.recv(1024).decode()


parts = response.split("|", 1)


status = parts[0]

message = parts[1] if len(parts) > 1 else ""


if status == "ERROR":

    print()
    print("Error:", message)

    client.close()

    exit()


print()
print(message)


# =========================
# CHAT DATA
# =========================

messages = []


# =========================
# HEADER
# =========================

def header_text():

    return FormattedText([
        ("class:title", "MSG"),
        ("class:dim", "  •  "),
        ("class:user", username),
        ("class:dim", "  •  "),
        ("class:mesh", mesh_name),
        ("class:dim", "                              "),
        ("class:online", "●"),
        ("class:dim", " Connected"),
    ])


header = Window(
    content=FormattedTextControl(header_text),
    height=2
)


# =========================
# CHAT AREA
# =========================

chat_area = TextArea(
    text="",
    scrollbar=False,
    wrap_lines=True,
    read_only=True,
    focusable=False
)


# =========================
# INPUT
# =========================

input_field = TextArea(
    height=1,
    prompt=">> ",
    multiline=False
)


# =========================
# UPDATE CHAT
# =========================

def update_chat():

    chat_area.text = "\n\n".join(messages)

    chat_area.buffer.cursor_position = (
        len(chat_area.buffer.text)
    )


# =========================
# RECEIVE MESSAGES
# =========================

def receive_messages():

    while True:

        try:

            data = client.recv(1024)

            if not data:
                break

            message = data.decode()

            messages.append(message)

            update_chat()

            app.invalidate()

        except:

            break


# =========================
# SEND MESSAGE
# =========================

def send_message():

    message = input_field.text.strip()

    if not message:
        return


    # =========================
    # EXIT
    # =========================

    if message == "/exit":

        try:
            client.send("/exit".encode())
        except:
            pass

        client.close()

        app.exit()

        return


    # =========================
    # NORMAL MESSAGE
    # =========================

    client.send(message.encode())

    input_field.text = ""


# =========================
# CHAT KEYBINDS
# =========================

chat_kb = KeyBindings()


@chat_kb.add("enter")
def _(event):

    send_message()


# =========================
# STYLE
# =========================

style = Style.from_dict({

    "title": "bold",

    "user": "bold",

    "mesh": "bold",

    "online": "bold",

})


# =========================
# CHAT LAYOUT
# =========================

root_container = HSplit([

    header,

    Window(height=1),

    chat_area,

    Window(height=1),

    input_field

])


layout = Layout(
    root_container,
    focused_element=input_field
)


# =========================
# CHAT APPLICATION
# =========================

app = Application(

    layout=layout,

    key_bindings=chat_kb,

    style=style,

    full_screen=True

)


# =========================
# RECEIVE THREAD
# =========================

threading.Thread(

    target=receive_messages,

    daemon=True

).start()


# =========================
# START CHAT
# =========================

app.run()