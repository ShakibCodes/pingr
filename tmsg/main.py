import sys
import threading
from websockets.sync.client import connect

from prompt_toolkit.application import Application
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Dimension, HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.processors import Processor, Transformation
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Frame, TextArea

SERVER_URL = "wss://tmsg.onrender.com"


def main():
    username = input("Enter your name: ").strip()

    try:
        client = connect(SERVER_URL)
    except Exception as e:
        print(f"Could not connect to server at {SERVER_URL}: {e}")
        sys.exit(1)

    client.send(username + "\n")

    username_response = client.recv().rstrip("\n")
    username_status, _, username_message = username_response.partition("|")

    if username_status == "ERROR":
        print("\nError:", username_message)
        client.close()
        sys.exit()

    if username_status != "USERNAME_OK":
        print("\nError: Invalid server response")
        client.close()
        sys.exit()

    menu_choice = 0
    menu_options = ["Start Mesh", "Join Mesh"]

    def menu_text():
        result = []
        for i, option in enumerate(menu_options):
            prefix = "> " if i == menu_choice else "  "
            result.append(
                (
                    "class:selected" if i == menu_choice else "",
                    prefix + option,
                )
            )
            if i != len(menu_options) - 1:
                result.append(("", "\n"))
        return FormattedText(result)

    menu_control = FormattedTextControl(menu_text)
    menu_window = Window(content=menu_control)
    menu_kb = KeyBindings()

    @menu_kb.add("up")
    def _(event):
        nonlocal menu_choice
        menu_choice = (menu_choice - 1) % len(menu_options)
        event.app.invalidate()

    @menu_kb.add("down")
    def _(event):
        nonlocal menu_choice
        menu_choice = (menu_choice + 1) % len(menu_options)
        event.app.invalidate()

    @menu_kb.add("enter")
    def _(event):
        event.app.exit()

    menu_layout = Layout(HSplit([Window(height=2), menu_window]))
    menu_style = Style.from_dict({"selected": "bold ansicyan"})

    menu_app = Application(
        layout=menu_layout,
        key_bindings=menu_kb,
        style=menu_style,
        full_screen=True,
    )
    menu_app.run()

    selected_option = menu_options[menu_choice]

    print()
    mesh_name = input("Name of mesh: ").strip()
    mesh_password = input("Password: ")

    if selected_option == "Start Mesh":
        request = f"START|{mesh_name}|{mesh_password}"
    else:
        request = f"JOIN|{mesh_name}|{mesh_password}"

    client.send(request + "\n")

    response = client.recv().rstrip("\n")
    parts = response.split("|", 1)
    status = parts[0]
    message = parts[1] if len(parts) > 1 else ""

    if status == "ERROR":
        print("\nError:", message)
        client.close()
        sys.exit()

    messages = []
    member_count = 1
    follow_bottom = True

    def add_server_message(text):
        messages.append(("server", None, text))

    def add_client_message(sender, text):
        messages.append(("client", sender, text))

    def add_members_message(count, members):
        messages.append(("members", count, members))

    def build_plain_chat():
        if not messages:
            return "No messages yet.\n\nSend a message to start the conversation."

        lines = []
        for kind, sender, text in messages:
            if kind == "server":
                lines.append("[Server] " + text)
                lines.append("")
            elif kind == "client":
                lines.append(f"[{sender}] {text}")
                lines.append("")
            elif kind == "members":
                lines.append(f"[Server] Members ({sender})")
                lines.append("")
                for member in text:
                    lines.append(f"    • {member}")
                lines.append("")
        return "\n".join(lines)

    class ChatColorProcessor(Processor):
        def apply_transformation(self, transformation_input):
            document = transformation_input.document

            if transformation_input.lineno >= len(document.lines):
                return Transformation(transformation_input.fragments)

            line = document.lines[transformation_input.lineno]

            if line.startswith("[Server] "):
                return Transformation([("class:server-message", line)])

            if line.startswith("[") and "] " in line:
                name_end = line.find("]") + 1
                sender = line[1 : name_end - 1]
                name_style = (
                    "class:self-name" if sender == username else "class:client-name"
                )
                return Transformation(
                    [
                        (name_style, line[:name_end]),
                        ("class:message", line[name_end:]),
                    ]
                )

            if line.startswith("    "):
                return Transformation([("class:server-message", line)])

            return Transformation(transformation_input.fragments)

    chat_area = TextArea(
        text="",
        height=Dimension(weight=1),
        scrollbar=True,
        input_processors=[ChatColorProcessor()],
        wrap_lines=True,
        read_only=True,
        focusable=False,
    )

    def chat_overlay():
        result = []
        for kind, sender, text in messages:
            if kind == "server":
                result.append(("class:server", "[Server] "))
                result.append(("class:server-message", text))
                result.append(("", "\n\n"))
            elif kind == "client":
                name_style = (
                    "class:self-name" if sender == username else "class:client-name"
                )
                result.append((name_style, f"[{sender}] "))
                result.append(("class:message", text))
                result.append(("", "\n\n"))
            elif kind == "members":
                result.append(("class:server", "[Server] "))
                result.append(("class:server-message", f"Members ({sender})"))
                result.append(("", "\n"))
                for member in text:
                    result.append(("class:member", f"    • {member}"))
                    result.append(("", "\n"))
                result.append(("", "\n"))
        return FormattedText(result)

    chat_display = Window(
        content=FormattedTextControl(chat_overlay),
        wrap_lines=True,
        always_hide_cursor=True,
    )

    def header_left():
        return FormattedText(
            [
                ("class:title", "[ MSG ]"),
                ("class:separator", "  •  "),
                ("class:username", username),
                ("class:separator", "  •  "),
                ("class:mesh", mesh_name),
            ]
        )

    def header_right():
        return FormattedText(
            [
                (
                    "class:count",
                    f"{member_count} {'member' if member_count == 1 else 'members'}",
                ),
                ("class:separator", "  •  "),
                ("class:connected", "● Connected"),
            ]
        )

    header = Window(content=FormattedTextControl(header_left), height=1)
    input_field = TextArea(height=1, prompt=">> ", multiline=False, wrap_lines=False)

    def send_message():
        message = input_field.text.strip()
        if not message:
            return

        if message == "/exit":
            try:
                client.send("CMD|exit\n")
            except Exception:
                pass
            try:
                client.close()
            except Exception:
                pass
            app.exit()
            return

        if message == "/members":
            try:
                client.send("CMD|members\n")
            except Exception:
                pass
            input_field.text = ""
            return

        try:
            client.send("MSG|" + message + "\n")
        except Exception:
            pass

        input_field.text = ""

    def scroll_up():
        nonlocal follow_bottom
        follow_bottom = False
        try:
            chat_area.buffer.cursor_position = max(
                0, chat_area.buffer.cursor_position - 500
            )
        except Exception:
            pass

    def scroll_down():
        nonlocal follow_bottom
        try:
            chat_area.buffer.cursor_position = min(
                len(chat_area.buffer.text), chat_area.buffer.cursor_position + 500
            )
        except Exception:
            pass

        if chat_area.buffer.cursor_position >= len(chat_area.buffer.text):
            follow_bottom = True

    def scroll_top():
        nonlocal follow_bottom
        follow_bottom = False
        try:
            chat_area.buffer.cursor_position = 0
        except Exception:
            pass

    def scroll_bottom():
        nonlocal follow_bottom
        follow_bottom = True
        try:
            chat_area.buffer.cursor_position = len(chat_area.buffer.text)
        except Exception:
            pass

    def update_chat():
        nonlocal follow_bottom
        chat_area.text = build_plain_chat()
        if follow_bottom:
            chat_area.buffer.cursor_position = len(chat_area.buffer.text)
        app.invalidate()

    chat_kb = KeyBindings()

    @chat_kb.add("enter")
    def _(event):
        send_message()

    @chat_kb.add("pageup")
    def _(event):
        scroll_up()

    @chat_kb.add("pagedown")
    def _(event):
        scroll_down()

    @chat_kb.add("home")
    def _(event):
        scroll_top()

    @chat_kb.add("end")
    def _(event):
        scroll_bottom()

    style = Style.from_dict(
        {
            "title": "bold ansiwhite",
            "username": "bold ansicyan",
            "mesh": "bold ansiwhite",
            "separator": "ansibrightblack",
            "count": "ansicyan",
            "connected": "bold ansigreen",
            "root": "bg:#0b0f14",
            "frame.border": "ansibrightblack",
            "frame.label": "bold ansicyan",
            "chat": "bg:#10151c",
            "scrollbar.background": "bg:#10151c",
            "scrollbar.button": "bg:#3b82f6",
            "scrollbar.arrow": "fg:#93c5fd",
            "server": "bold ansiyellow",
            "server-message": "ansiyellow",
            "client-name": "bold ansicyan",
            "self-name": "bold ansigreen",
            "message": "",
            "member": "ansiyellow",
        }
    )

    root_container = HSplit(
        [
            header,
            Window(height=1),
            Frame(body=chat_area, title=" Messages "),
            Window(height=1),
            input_field,
        ],
        style="class:root",
    )

    layout = Layout(root_container, focused_element=input_field)

    app = Application(
        layout=layout,
        key_bindings=chat_kb,
        style=style,
        full_screen=True,
        mouse_support=True,
    )

    def receive_messages():
        nonlocal member_count

        while True:
            try:
                raw_data = client.recv()
                if not raw_data:
                    break

                data = raw_data.rstrip("\n")
                parts = data.split("|", 2)
                message_type = parts[0]

                if message_type == "SERVER":
                    text = parts[1] if len(parts) > 1 else ""
                    add_server_message(text)

                elif message_type == "CHAT":
                    if len(parts) < 3:
                        continue
                    sender = parts[1]
                    text = parts[2]
                    add_client_message(sender, text)

                elif message_type == "COUNT":
                    if len(parts) < 2:
                        continue
                    try:
                        member_count = int(parts[1])
                    except Exception:
                        pass

                elif message_type == "MEMBERS":
                    if len(parts) < 2:
                        continue
                    try:
                        count = int(parts[1])
                    except Exception:
                        count = 0

                    members = []
                    if len(parts) >= 3:
                        members = [name for name in parts[2].split("|") if name]

                    add_members_message(count, members)

                update_chat()

            except Exception:
                break

    threading.Thread(target=receive_messages, daemon=True).start()
    app.run()


if __name__ == "__main__":
    main()