import os
import platform
import re
import subprocess
import sys
import threading
from websockets.sync.client import connect

from prompt_toolkit.application import Application
from prompt_toolkit.document import Document
from prompt_toolkit.filters import has_focus
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Dimension, HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Frame, TextArea

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_SERVER_URL = "wss://tmsg.onrender.com"
PALETTE_COUNT = 8


def get_server_url() -> str:
    """Read server URL from CLI arguments (--server / -s) or environment variable."""
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg in ("--server", "-s") and i + 1 < len(args):
            return args[i + 1]
        if arg.startswith("--server="):
            return arg.split("=", 1)[1]
    return os.environ.get(
        "TMSG_SERVER", os.environ.get("SERVER_URL", DEFAULT_SERVER_URL)
    )


def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard across Windows, macOS, Linux, and OSC 52."""
    if not text:
        return False

    try:
        import pyperclip

        pyperclip.copy(text)
        return True
    except Exception:
        pass

    system = platform.system()
    try:
        if system == "Windows":
            subprocess.run(
                ["clip.exe"],
                input=text.encode("utf-16le"),
                check=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return True
        elif system == "Darwin":
            subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
            return True
        else:
            for cmd in [
                ["wl-copy"],
                ["xclip", "-selection", "clipboard"],
                ["xsel", "--clipboard", "--input"],
            ]:
                try:
                    subprocess.run(cmd, input=text.encode("utf-8"), check=True)
                    return True
                except FileNotFoundError:
                    continue
    except Exception:
        pass

    try:
        import base64

        b64_data = base64.b64encode(text.encode("utf-8")).decode("ascii")
        sys.stdout.write(f"\x1b]52;c;{b64_data}\x07")
        sys.stdout.flush()
        return True
    except Exception:
        pass

    return False


def clean_incoming_text(text: str) -> str:
    """Expand tabs to 4 spaces, normalize line endings, and strip outer fences for multiline."""
    text = text.expandtabs(4)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    stripped = text.strip()

    # Strip multiline code fence ``` ... ```
    if stripped.startswith("```") and stripped.endswith("```") and len(stripped) >= 6:
        lines = stripped.split("\n")
        if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1])
        return stripped[3:-3].strip("\n")

    # Strip multiline single backticks ` ... `
    if (
        stripped.startswith("`")
        and stripped.endswith("`")
        and len(stripped) >= 2
        and "\n" in stripped
    ):
        return stripped[1:-1].strip("\n")

    return text


def clean_copied_text(text: str) -> str:
    """Clean copied text by stripping border markers and username prefixes."""
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        # Strip code border prefixes
        line = re.sub(r"^\s*[│║]\s?", "", line)
        # Strip leading username tags: e.g. "[Shakib (You)] ", "[tabish] "
        line = re.sub(r"^\[[^\]]+\]:\s*", "", line)
        line = re.sub(r"^\[[^\]]+\]\s+", "", line)
        line = re.sub(r"^[✦➜←👥ℹ⚠]\s*\[[^\]]+\]\s*", "", line)
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def get_user_color_index(username: str) -> int:
    """Derive a deterministic color index from a username."""
    clean = username.split(" (You)")[0].strip("[] :")
    return sum((i + 1) * ord(c) for i, c in enumerate(clean)) % PALETTE_COUNT


def tokenize_message_content(content: str, current_user: str = ""):
    """Tokenize message content for Markdown formatting (bold, italic, code, URLs, mentions)."""
    tokens = []
    code_char = chr(96)
    pattern = re.compile(
        rf"({code_char}[^{code_char}\n]+{code_char}|\*\*[^*\n]+\*\*|\*[^*\n]+\*|https?://[^\s]+|@[a-zA-Z0-9_-]+)"
    )
    last_idx = 0
    for match in pattern.finditer(content):
        start, end = match.span()
        if start > last_idx:
            tokens.append(("class:message", content[last_idx:start]))
        t = match.group(0)
        if t.startswith(code_char) and t.endswith(code_char) and len(t) >= 2:
            tokens.append(("class:inline-code", t))
        elif t.startswith("**") and t.endswith("**") and len(t) >= 4:
            tokens.append(("class:markdown-bold", t))
        elif t.startswith("*") and t.endswith("*") and len(t) >= 2:
            tokens.append(("class:markdown-italic", t))
        elif t.startswith(("http://", "https://")):
            tokens.append(("class:url", t))
        elif t.startswith("@"):
            is_self_mention = bool(
                current_user and t[1:].lower() == current_user.lower()
            )
            tokens.append(
                ("class:self-mention" if is_self_mention else "class:mention", t)
            )
        else:
            tokens.append(("class:message", t))
        last_idx = end
    if last_idx < len(content):
        tokens.append(("class:message", content[last_idx:]))
    return tokens


class ChatLexer(Lexer):
    """Custom Lexer that highlights badges, colored users, code blocks, and markdown without timestamps."""

    def __init__(self, current_user: str):
        self.current_user = current_user

    def lex_document(self, document: Document):
        def get_line(lineno: int):
            line = document.lines[lineno]
            if not line:
                return [("", "")]

            frags = []
            rest = line

            if rest.startswith("✦ [Server] "):
                frags.append(("class:server-icon", "✦ "))
                frags.append(("class:server-tag", "[Server] "))
                frags.extend(tokenize_message_content(rest[11:], self.current_user))
                return frags

            if rest.startswith("➜ [Server] "):
                frags.append(("class:server-join-icon", "➜ "))
                frags.append(("class:server-join", rest[2:]))
                return frags

            if rest.startswith("← [Server] "):
                frags.append(("class:server-leave-icon", "← "))
                frags.append(("class:server-leave", rest[2:]))
                return frags

            if rest.startswith("👥 [Server] "):
                frags.append(("class:server-icon", "👥 "))
                frags.append(("class:server-tag", "[Server] "))
                frags.append(("class:server-message", rest[11:]))
                return frags

            if rest.startswith("ℹ [Help] "):
                frags.append(("class:help-icon", "ℹ "))
                frags.append(("class:help-tag", "[Help] "))
                frags.append(("class:help-message", rest[9:]))
                return frags

            if rest.startswith("⚠ [Error] "):
                frags.append(("class:error-icon", "⚠ "))
                frags.append(("class:error-tag", "[Error] "))
                frags.append(("class:error-message", rest[10:]))
                return frags

            client_match = re.match(r"^(\[[^\]]+\](:?))(\s*)", rest)
            if client_match:
                name_bracketed = client_match.group(1)
                space = client_match.group(3)
                raw_name = name_bracketed.rstrip(":")

                if "(You)" in raw_name or raw_name[1:-1] == self.current_user:
                    name_style = "class:self-name"
                else:
                    color_idx = get_user_color_index(raw_name)
                    name_style = f"class:user-color-{color_idx}"

                frags.append((name_style, name_bracketed))
                if space:
                    frags.append(("", space))

                content = rest[len(name_bracketed) + len(space) :]
                if content.startswith("> "):
                    frags.append(("class:quote-bar", "> "))
                    frags.append(("class:blockquote", content[2:]))
                else:
                    frags.extend(tokenize_message_content(content, self.current_user))
                return frags

            if rest.startswith("  │ ") or rest.startswith("  ║ "):
                frags.append(("class:code-border", rest[:4]))
                frags.append(("class:code-block", rest[4:]))
                return frags

            if rest.startswith("    • "):
                frags.append(("class:member-bullet", "    • "))
                member_name = rest[6:]
                if "(You)" in member_name:
                    frags.append(("class:self-name", member_name))
                else:
                    color_idx = get_user_color_index(member_name)
                    frags.append((f"class:user-color-{color_idx}", member_name))
                return frags

            if rest.startswith("> "):
                frags.append(("class:quote-bar", "> "))
                frags.append(("class:blockquote", rest[2:]))
                return frags

            frags.extend(tokenize_message_content(rest, self.current_user))
            return frags

        return get_line


class Message:
    def __init__(
        self,
        kind: str,
        sender: str = None,
        text: str = "",
        members: list = None,
    ):
        self.kind = kind  # server, join, leave, client, members, help, error
        self.sender = sender
        self.text = text
        self.members = members or []


def main():
    server_url = get_server_url()
    username = input("Enter your name: ").strip()

    try:
        client = connect(server_url)
    except Exception as e:
        print(f"Could not connect to server at {server_url}: {e}")
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
    line_to_message_map = {}
    member_count = 1
    follow_bottom = True
    toast_text = ""
    toast_timer = None

    def show_toast(text: str, duration: float = 3.0):
        nonlocal toast_text, toast_timer
        toast_text = text
        try:
            app.invalidate()
        except Exception:
            pass

        if toast_timer:
            toast_timer.cancel()

        def clear_toast():
            nonlocal toast_text
            toast_text = ""
            try:
                app.invalidate()
            except Exception:
                pass

        toast_timer = threading.Timer(duration, clear_toast)
        toast_timer.daemon = True
        toast_timer.start()

    def add_server_message(text):
        clean_text = clean_incoming_text(text)
        if clean_text.endswith(" joined the mesh"):
            user = clean_text[: -len(" joined the mesh")]
            messages.append(Message("join", user, clean_text))
        elif clean_text.endswith(" left the mesh"):
            user = clean_text[: -len(" left the mesh")]
            messages.append(Message("leave", user, clean_text))
        else:
            messages.append(Message("server", None, clean_text))

    def add_client_message(sender, text):
        clean_text = clean_incoming_text(text)
        messages.append(Message("client", sender, clean_text))

    def add_members_message(count, members):
        messages.append(Message("members", None, f"Members online ({count})", members=members))

    def add_help_message():
        help_text = (
            "Pingr Commands & Keyboard Shortcuts:\n"
            "    • [Tab] : Toggle focus between Input and Chat Browse/Copy mode\n"
            "    • [c] / [Ctrl+C] : In Browse mode, copy pure message/code at cursor (no usernames)\n"
            "    • [l] : In Browse mode, copy latest clean message\n"
            "    • [a] : In Browse mode, copy chat messages\n"
            "    • [Shift + Arrows] or [Mouse Drag] : Select text in Browse mode\n"
            "    • [Enter] / [i] / [Esc] : Return to typing from Browse mode\n"
            "    • [/copy] : Copy latest message text to clipboard\n"
            "    • [/copyall] : Copy all messages to clipboard\n"
            "    • [/clear] : Clear local chat history\n"
            "    • [/members] : List all online mesh participants\n"
            "    • [/exit] : Leave mesh and close connection\n"
            "    • Formatting: **bold**, *italic*, `code`, > quote, @user, https://link"
        )
        messages.append(Message("help", None, help_text))

    def build_plain_chat():
        nonlocal line_to_message_map
        if not messages:
            line_to_message_map.clear()
            return "No messages yet.\n\nType a message below to start chatting, or press [Tab] to browse/copy."

        lines = []
        line_to_message_map.clear()

        for msg in messages:
            start_lineno = len(lines)

            if msg.kind == "server":
                lines.append(f"✦ [Server] {msg.text}")
            elif msg.kind == "join":
                lines.append(f"➜ [Server] {msg.text}")
            elif msg.kind == "leave":
                lines.append(f"← [Server] {msg.text}")
            elif msg.kind == "members":
                lines.append(f"👥 [Server] {msg.text}:")
                for member in msg.members:
                    m_label = f"{member} (You)" if member == username else member
                    lines.append(f"    • {m_label}")
            elif msg.kind == "help":
                lines.append(f"ℹ [Help] {msg.text}")
            elif msg.kind == "error":
                lines.append(f"⚠ [Error] {msg.text}")
            elif msg.kind == "client":
                user_tag = (
                    f"[{msg.sender} (You)]"
                    if msg.sender == username
                    else f"[{msg.sender}]"
                )
                content_lines = msg.text.split("\n")
                if len(content_lines) == 1:
                    lines.append(f"{user_tag} {content_lines[0]}")
                else:
                    lines.append(f"{user_tag}:")
                    for cl in content_lines:
                        lines.append(f"  │ {cl}")

            end_lineno = len(lines)
            for lno in range(start_lineno, end_lineno):
                line_to_message_map[lno] = msg

            lines.append("")  # Blank separator line

        return "\n".join(lines)

    chat_area = TextArea(
        text="",
        height=Dimension(weight=1),
        scrollbar=True,
        lexer=ChatLexer(username),
        wrap_lines=True,
        read_only=True,
        focusable=True,
    )

    def header_content():
        is_focused_chat = app.layout.has_focus(chat_area) if "app" in globals() else False
        mode_tuple = (
            ("class:mode.browse", " [ 📋 CHAT BROWSE & COPY MODE ] ")
            if is_focused_chat
            else ("class:mode.input", " [ ⌨ INPUT MODE ] ")
        )
        return FormattedText(
            [
                ("class:title", "[ PINGR ]"),
                ("class:separator", "  •  "),
                ("class:self-name", username),
                ("class:separator", "  •  "),
                ("class:mesh", mesh_name),
                ("class:separator", "  •  "),
                mode_tuple,
                ("class:separator", "  •  "),
                (
                    "class:count",
                    f"{member_count} {'member' if member_count == 1 else 'members'}",
                ),
                ("class:separator", "  •  "),
                ("class:connected", "● Connected"),
            ]
        )

    def footer_content():
        if toast_text:
            return FormattedText([("class:toast", f"  {toast_text}  ")])

        if app.layout.has_focus(chat_area):
            return FormattedText(
                [
                    ("class:footer.key", "[c/Ctrl+C] "),
                    ("class:footer.desc", "Copy Pure Text/Code  "),
                    ("class:footer.key", "[l] "),
                    ("class:footer.desc", "Copy Last  "),
                    ("class:footer.key", "[a] "),
                    ("class:footer.desc", "Copy All  "),
                    ("class:footer.key", "[Shift+Arrows] "),
                    ("class:footer.desc", "Select  "),
                    ("class:footer.key", "[Enter/i/Tab] "),
                    ("class:footer.desc", "Type Message"),
                ]
            )
        else:
            return FormattedText(
                [
                    ("class:footer.key", "[Tab] "),
                    ("class:footer.desc", "Browse & Copy  "),
                    ("class:footer.key", "[Enter] "),
                    ("class:footer.desc", "Send  "),
                    ("class:footer.key", "[/copy] "),
                    ("class:footer.desc", "Copy Last  "),
                    ("class:footer.key", "[/help] "),
                    ("class:footer.desc", "Help  "),
                    ("class:footer.key", "[/members] "),
                    ("class:footer.desc", "Members  "),
                    ("class:footer.key", "[/exit] "),
                    ("class:footer.desc", "Exit"),
                ]
            )

    header = Window(content=FormattedTextControl(header_content), height=1)
    footer = Window(content=FormattedTextControl(footer_content), height=1)
    input_field = TextArea(height=1, prompt=">> ", multiline=False, wrap_lines=False)

    def copy_latest_message_action():
        client_msgs = [m for m in messages if m.kind == "client"]
        if client_msgs:
            target = client_msgs[-1]
            text_to_copy = target.text
            if copy_to_clipboard(text_to_copy):
                show_toast(f"✓ Copied clean message from {target.sender} to clipboard!")
            else:
                show_toast("⚠ Failed to copy to clipboard")
        else:
            all_msgs = [m for m in messages if m.text]
            if all_msgs:
                target = all_msgs[-1]
                if copy_to_clipboard(target.text):
                    show_toast("✓ Copied clean message to clipboard!")
                else:
                    show_toast("⚠ Failed to copy to clipboard")
            else:
                show_toast("⚠ No messages to copy")

    def copy_all_messages_action():
        clean_lines = []
        for m in messages:
            if m.kind == "client":
                clean_lines.append(m.text)
            elif m.text:
                clean_lines.append(m.text)
        transcript = "\n\n".join(clean_lines)
        if transcript and copy_to_clipboard(transcript):
            show_toast(f"✓ Copied clean messages ({len(transcript)} chars)!")
        else:
            show_toast("⚠ Failed to copy messages")

    def copy_chat_selection_or_current():
        buf = chat_area.buffer
        if buf.selection_state:
            clip_data = buf.copy_selection()
            text_to_copy = clip_data.text if clip_data else ""
            if text_to_copy:
                clean_text = clean_copied_text(text_to_copy)
                if copy_to_clipboard(clean_text):
                    show_toast(f"✓ Copied selection ({len(clean_text)} chars)!")
                    return

        # If no selection, copy message at cursor
        cursor_row = buf.document.cursor_position_row
        target_msg = line_to_message_map.get(cursor_row)
        if target_msg and target_msg.text:
            text_to_copy = target_msg.text
            if copy_to_clipboard(text_to_copy):
                sender_label = target_msg.sender or "Server"
                show_toast(f"✓ Copied clean message from {sender_label} ({len(text_to_copy)} chars)!")
                return

        # Fallback to current line cleaned
        current_line = buf.document.current_line
        if current_line.strip():
            clean_line = clean_copied_text(current_line)
            if copy_to_clipboard(clean_line):
                show_toast("✓ Copied line to clipboard!")
                return

        copy_latest_message_action()

    def send_message():
        raw_msg = input_field.text.strip()
        if not raw_msg:
            return

        if raw_msg == "/exit":
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

        if raw_msg == "/members":
            try:
                client.send("CMD|members\n")
            except Exception:
                pass
            input_field.text = ""
            return

        if raw_msg == "/help":
            add_help_message()
            update_chat()
            input_field.text = ""
            return

        if raw_msg == "/copy":
            copy_latest_message_action()
            input_field.text = ""
            return

        if raw_msg == "/copyall":
            copy_all_messages_action()
            input_field.text = ""
            return

        if raw_msg == "/clear":
            messages.clear()
            messages.append(Message("server", None, "Chat history cleared locally."))
            update_chat()
            input_field.text = ""
            show_toast("✦ Local chat screen cleared")
            return

        message = clean_incoming_text(raw_msg)
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
        try:
            app.invalidate()
        except Exception:
            pass

    kb = KeyBindings()

    @kb.add("tab")
    def _(event):
        if event.app.layout.has_focus(input_field):
            event.app.layout.focus(chat_area)
            show_toast("📋 Browse Mode: [c] Copy Clean Message | [l] Copy Last | [Enter] Type", duration=4.0)
        else:
            event.app.layout.focus(input_field)

    @kb.add("s-tab")
    def _(event):
        if event.app.layout.has_focus(input_field):
            event.app.layout.focus(chat_area)
        else:
            event.app.layout.focus(input_field)

    # Input Field Keybindings
    @kb.add("enter", filter=has_focus(input_field))
    def _(event):
        send_message()

    @kb.add("pageup", filter=has_focus(input_field))
    def _(event):
        scroll_up()

    @kb.add("pagedown", filter=has_focus(input_field))
    def _(event):
        scroll_down()

    @kb.add("home", filter=has_focus(input_field))
    def _(event):
        scroll_top()

    @kb.add("end", filter=has_focus(input_field))
    def _(event):
        scroll_bottom()

    # Chat Area Keybindings
    @kb.add("escape", filter=has_focus(chat_area))
    @kb.add("enter", filter=has_focus(chat_area))
    @kb.add("i", filter=has_focus(chat_area))
    def _(event):
        event.app.layout.focus(input_field)

    @kb.add("c", filter=has_focus(chat_area))
    @kb.add("c-c", filter=has_focus(chat_area))
    @kb.add("y", filter=has_focus(chat_area))
    def _(event):
        copy_chat_selection_or_current()

    @kb.add("l", filter=has_focus(chat_area))
    def _(event):
        copy_latest_message_action()

    @kb.add("a", filter=has_focus(chat_area))
    def _(event):
        copy_all_messages_action()

    style = Style.from_dict(
        {
            "title": "bold ansiwhite",
            "self-name": "bold ansigreen",
            "mesh": "bold ansicyan",
            "separator": "ansibrightblack",
            "count": "ansicyan",
            "connected": "bold ansigreen",
            "mode.input": "bg:#1e3a8a fg:#93c5fd bold",
            "mode.browse": "bg:#065f46 fg:#6ee7b7 bold",
            "root": "bg:#0b0f14",
            "frame.border": "ansibrightblack",
            "frame.label": "bold ansicyan",
            "chat": "bg:#0e131b",
            "server-icon": "bold ansiyellow",
            "server-tag": "bold ansiyellow",
            "server-join-icon": "bold ansigreen",
            "server-join": "bold ansigreen",
            "server-leave-icon": "bold ansired",
            "server-leave": "bold ansired",
            "server-message": "ansiyellow",
            "help-icon": "bold ansicyan",
            "help-tag": "bold ansicyan",
            "help-message": "ansicyan",
            "error-icon": "bold ansired",
            "error-tag": "bold ansired",
            "error-message": "bold ansired",
            "user-color-0": "bold ansicyan",
            "user-color-1": "bold ansimagenta",
            "user-color-2": "bold ansiyellow",
            "user-color-3": "bold ansibrightblue",
            "user-color-4": "bold ansibrightmagenta",
            "user-color-5": "bold ansibrightcyan",
            "user-color-6": "bold ansibrightyellow",
            "user-color-7": "bold ansibrightgreen",
            "message": "ansiwhite",
            "markdown-bold": "bold ansiwhite",
            "markdown-italic": "italic ansiwhite",
            "inline-code": "bold bg:#1e293b fg:#38bdf8",
            "code-fence": "ansibrightblack",
            "code-border": "bold ansicyan",
            "code-block": "ansiwhite",
            "quote-bar": "bold ansicyan",
            "blockquote": "italic ansibrightblack",
            "url": "underline ansicyan",
            "mention": "bold bg:#3730a3 fg:#c7d2fe",
            "self-mention": "bold bg:#065f46 fg:#86efac",
            "member-bullet": "bold ansiyellow",
            "toast": "bold bg:#065f46 fg:#ffffff",
            "footer.key": "bold ansicyan",
            "footer.desc": "ansibrightblack",
            "scrollbar.background": "bg:#0e131b",
            "scrollbar.button": "bg:#3b82f6",
            "scrollbar.arrow": "fg:#93c5fd",
        }
    )

    root_container = HSplit(
        [
            header,
            Window(height=1),
            Frame(body=chat_area, title=" Messages "),
            Window(height=1),
            input_field,
            footer,
        ],
        style="class:root",
    )

    layout = Layout(root_container, focused_element=input_field)

    app = Application(
        layout=layout,
        key_bindings=kb,
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