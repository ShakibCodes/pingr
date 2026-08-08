import socket
import threading

from prompt_toolkit.application import Application
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style


# =========================
# CONNECTION
# =========================

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

client.connect(("127.0.0.1", 5000))

username = input("Enter your username: ")

client.send(username.encode())


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
        ("class:dim", "                                      "),
        ("class:online", "●"),
        ("class:dim", " Connected"),
    ])


header = Window(
    content=FormattedTextControl(header_text),
    height=2,
)


# =========================
# CHAT AREA
# =========================

chat_area = TextArea(
    text="",
    scrollbar=False,
    wrap_lines=True,
    read_only=True,
    focusable=False,
    style="class:chat",
)


# =========================
# INPUT
# =========================

input_field = TextArea(
    height=1,
    prompt=">> ",
    multiline=False,
    wrap_lines=False,
    style="class:input",
)


# =========================
# UI UPDATE
# =========================

def update_chat():
    chat_area.text = "\n\n".join(messages)

    # Move chat view to the newest message
    chat_area.buffer.cursor_position = len(chat_area.buffer.text)


# =========================
# RECEIVE MESSAGES
# =========================

def receive_messages():
    while True:
        try:
            message = client.recv(1024)

            if not message:
                break

            message = message.decode()

            # Extract username from:
            # [Shakib]: Hello
            if message.startswith("[") and "]:" in message:
                name_end = message.find("]:")
                sender = message[1:name_end]
                text = message[name_end + 2:].strip()

                messages.append(
                    f"[{sender}]  {text}"
                )

            else:
                messages.append(message)

            update_chat()

            app.invalidate()

        except:
            break


# =========================
# SEND MESSAGES
# =========================

def send_message():
    message = input_field.text.strip()

    if not message:
        return

    if message == "/exit":
        client.close()
        app.exit()
        return

    client.send(message.encode())

    input_field.text = ""


# =========================
# KEYBOARD
# =========================

from prompt_toolkit.key_binding import KeyBindings

kb = KeyBindings()


@kb.add("enter")
def _(event):
    send_message()


# =========================
# STYLE
# =========================

style = Style.from_dict({
    # Header
    "title": "bold",
    "user": "bold",
    "online": "bold",

    # Main chat
    "chat": "",

    # Input
    "input": "bold",
})


# =========================
# LAYOUT
# =========================

root_container = HSplit([
    header,

    Window(height=1),

    chat_area,

    Window(height=1),

    input_field,
])


layout = Layout(
    root_container,
    focused_element=input_field,
)


# =========================
# APPLICATION
# =========================

app = Application(
    layout=layout,
    key_bindings=kb,
    style=style,
    full_screen=True,
    mouse_support=False,
)


# Start receiver thread
threading.Thread(
    target=receive_messages,
    daemon=True
).start()


# Start UI
app.run()