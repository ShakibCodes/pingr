import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime

import websockets
from rich.markup import escape
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Input, Label, RadioButton, RadioSet, RichLog, Static

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

__version__ = "0.2.0"
DEFAULT_SERVER_URL = "wss://tmsg.onrender.com"
USER_PALETTE = [
    "#60a5fa",  # blue
    "#34d399",  # emerald
    "#a78bfa",  # purple
    "#fbbf24",  # amber
    "#f472b6",  # rose
    "#38bdf8",  # sky
    "#fb923c",  # orange
    "#4ade80",  # green
]

PINGR_ASCII = """██████╗ ██╗███╗   ██╗ ██████╗ ██████╗ 
██╔══██╗██║████╗  ██║██╔════╝ ██╔══██╗
██████╔╝██║██╔██╗ ██║██║  ███╗██████╔╝
██╔═══╝ ██║██║╚██╗██║██║   ██║██╔══██╗
██║     ██║██║ ╚████║╚██████╔╝██║  ██║
╚═╝     ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝"""


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

    if stripped.startswith("```") and stripped.endswith("```") and len(stripped) >= 6:
        lines = stripped.split("\n")
        if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1])
        return stripped[3:-3].strip("\n")

    if (
        stripped.startswith("`")
        and stripped.endswith("`")
        and len(stripped) >= 2
        and "\n" in stripped
    ):
        return stripped[1:-1].strip("\n")

    return text


def clean_copied_text(text: str) -> str:
    """Clean copied text by stripping border markers, timestamps, and username prefixes."""
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        line = re.sub(r"^\s*\[?\d{2}:\d{2}\]?\s+", "", line)
        line = re.sub(r"^\s*[│║▎]\s?", "", line)
        line = re.sub(r"^\[[^\]]+\]:\s*", "", line)
        line = re.sub(r"^\[[^\]]+\]\s+", "", line)
        line = re.sub(r"^[✦➜←👥ℹ⚠●○]\s*(\[[^\]]+\])?\s*", "", line)
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def get_user_color_index(username: str) -> int:
    """Derive a deterministic color index from a username."""
    clean = username.split(" (You)")[0].strip("[] :@")
    return sum((i + 1) * ord(c) for i, c in enumerate(clean)) % len(USER_PALETTE)


def format_message_rich(content: str, current_user: str = "") -> str:
    """Escape and format text with clean, elegant markdown markup."""
    escaped = escape(content)
    code_char = chr(96)

    def repl_code(m):
        return f"[bold #38bdf8 on #1e293b]{m.group(1)}[/]"

    escaped = re.sub(rf"{code_char}([^{code_char}\n]+){code_char}", repl_code, escaped)
    escaped = re.sub(r"\*\*([^*\n]+)\*\*", r"[bold #f4f4f5]\1[/]", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"[italic #d4d4d8]\1[/]", escaped)
    escaped = re.sub(r"(https?://[^\s]+)", r"[underline #60a5fa]\1[/]", escaped)

    def repl_mention(m):
        name = m.group(1)
        if current_user and name.lower() == current_user.lower():
            return f"[bold #10b981 on #064e3b] @{name} [/]"
        return f"[bold #818cf8 on #1e1b4b] @{name} [/]"

    escaped = re.sub(r"@([a-zA-Z0-9_-]+)", repl_mention, escaped)
    if escaped.startswith("&gt; ") or escaped.startswith("> "):
        quote_text = escaped[5:] if escaped.startswith("&gt; ") else escaped[2:]
        escaped = f"[dim italic #94a3b8]▎ {quote_text}[/]"

    return escaped


class Message:
    def __init__(
        self,
        kind: str,
        sender: str = None,
        text: str = "",
        members: list = None,
        timestamp: str = None,
    ):
        self.kind = kind
        self.sender = sender
        self.text = text
        self.members = members or []
        self.timestamp = timestamp or datetime.now().strftime("%H:%M")


APP_CSS = """
Screen {
    background: #09090b;
    color: #f4f4f5;
}

SetupScreen {
    align: center middle;
    background: #09090b;
    overflow-y: auto;
}

#setup-card {
    width: 72;
    height: auto;
    background: #121214;
    border: round #27272a;
    padding: 1 4;
}

#setup-logo {
    text-align: center;
    color: #38bdf8;
    text-style: bold;
    margin: 0;
}

#setup-subtitle {
    text-align: center;
    color: #71717a;
    margin-top: 1;
    margin-bottom: 2;
}

.field-label {
    color: #a1a1aa;
    text-style: bold;
    margin-top: 1;
    margin-bottom: 0;
}

Input {
    background: #18181b;
    border: round #27272a;
    color: #f4f4f5;
    height: 3;
    padding: 0 1;
    margin-bottom: 1;
}

Input:focus {
    border: round #3b82f6;
}

#action-radio {
    background: transparent;
    border: none;
    height: auto;
    layout: horizontal;
    padding: 0;
    margin-top: 0;
    margin-bottom: 1;
}

#action-radio RadioButton {
    background: transparent;
    color: #a1a1aa;
    height: 1;
    padding: 0;
    width: auto;
    margin-right: 3;
}

#action-radio RadioButton:focus {
    color: #f4f4f5;
}

#visibility-radio {
    background: transparent;
    border: none;
    height: auto;
    layout: horizontal;
    padding: 0;
    margin-top: 0;
    margin-bottom: 1;
}

#visibility-radio RadioButton {
    background: transparent;
    color: #a1a1aa;
    height: 1;
    padding: 0;
    width: auto;
    margin-right: 3;
}

#visibility-radio RadioButton:focus {
    color: #f4f4f5;
}

#start-container {
    height: auto;
}

#join-container {
    height: auto;
}

#public-list-scroll {
    height: auto;
    max-height: 16;
    background: #09090b;
    border: round #27272a;
    padding: 1 2;
    margin-bottom: 1;
}

.mesh-card {
    height: auto;
    background: #18181b;
    border: round #27272a;
    padding: 1 2;
    margin-bottom: 1;
}

.mesh-card:hover {
    border: round #3b82f6;
}

.mesh-card-header {
    height: 1;
    layout: horizontal;
}

.mesh-card-name {
    width: 1fr;
    color: #60a5fa;
    text-style: bold;
}

.mesh-card-online {
    width: auto;
    color: #22c55e;
}

.mesh-card-desc {
    height: 1;
    color: #71717a;
    margin-top: 0;
}

#empty-state {
    color: #52525b;
    text-align: center;
    padding: 2 0;
}

.section-divider {
    color: #27272a;
    margin-top: 1;
    margin-bottom: 1;
    text-align: center;
}

.button-row {
    margin-top: 2;
    margin-bottom: 1;
    height: 3;
    align: right middle;
}

.public-header-row {
    height: 3;
    margin-top: 1;
    margin-bottom: 0;
    align: left middle;
}

.public-header-row Label {
    width: 1fr;
    margin: 0;
}

Button {
    height: 3;
    border: none;
    min-width: 14;
}

#connect-btn {
    background: #2563eb;
    color: #ffffff;
    text-style: bold;
}

#connect-btn:hover {
    background: #3b82f6;
}

#quit-btn, #quit-btn-join {
    background: #27272a;
    color: #a1a1aa;
    margin-right: 2;
}

#quit-btn:hover, #quit-btn-join:hover {
    background: #3f3f46;
    color: #f4f4f5;
}

#refresh-btn {
    background: #27272a;
    color: #a1a1aa;
    min-width: 12;
}

#refresh-btn:hover {
    background: #3f3f46;
    color: #f4f4f5;
}

.join-btn {
    background: #2563eb;
    color: #ffffff;
    text-style: bold;
    min-width: 10;
    height: 3;
}

.join-btn:hover {
    background: #3b82f6;
}

#join-private-btn {
    background: #2563eb;
    color: #ffffff;
    text-style: bold;
}

#join-private-btn:hover {
    background: #3b82f6;
}

#error-label {
    color: #ef4444;
    text-align: center;
    margin-top: 1;
    height: auto;
}

ChatScreen {
    background: #09090b;
    layout: vertical;
}

#chat-header {
    height: 3;
    background: #121214;
    border-bottom: solid #27272a;
    padding: 0 3;
    align: left middle;
}

#header-left {
    width: 1fr;
    height: 100%;
}

#header-right {
    width: auto;
    height: 100%;
}

#chat-log {
    height: 1fr;
    background: #09090b;
    border: none;
    padding: 1 3;
    scrollbar-gutter: stable;
    scrollbar-color: #27272a;
    scrollbar-color-hover: #3f3f46;
    scrollbar-size-vertical: 1;
}

#input-container {
    height: auto;
    padding: 1 2;
    background: #09090b;
}

#chat-input {
    background: #121214;
    border: round #27272a;
    color: #f4f4f5;
    height: 3;
    padding: 0 2;
}

#chat-input:focus {
    border: round #3b82f6;
}

#chat-footer {
    height: 1;
    background: #121214;
    border-top: solid #1c1c1f;
    color: #71717a;
    padding: 0 3;
}
"""


class SetupScreen(Screen):
    def compose(self) -> ComposeResult:
        with Container(id="setup-card"):
            yield Static(PINGR_ASCII, id="setup-logo")
            yield Static("Minimal, ephemeral terminal messaging", id="setup-subtitle")

            yield Label("Display Name", classes="field-label")
            yield Input(placeholder="your-handle", id="handle-input", max_length=24)

            yield Label("Action", classes="field-label")
            with RadioSet(id="action-radio"):
                yield RadioButton("Start a new mesh", value=True)
                yield RadioButton("Browse & join mesh")

            # === START MESH CONTAINER ===
            with Container(id="start-container"):
                yield Label("Visibility", classes="field-label")
                with RadioSet(id="visibility-radio"):
                    yield RadioButton("Public (no password)", value=True)
                    yield RadioButton("Private (password protected)")

                yield Label("Mesh Room", classes="field-label")
                yield Input(placeholder="room-name", id="mesh-input", max_length=32)

                yield Label("Description", classes="field-label")
                yield Input(placeholder="e.g. Discussing open-source TUI projects", id="desc-input", max_length=100)

                yield Label("Password", classes="field-label", id="pass-label")
                yield Input(placeholder="••••••••", password=True, id="pass-input", max_length=128)

                with Horizontal(classes="button-row"):
                    yield Button("Quit", variant="default", id="quit-btn")
                    yield Button("Create Mesh", variant="primary", id="connect-btn")

            # === JOIN MESH CONTAINER (hidden by default) ===
            with Container(id="join-container"):
                with Horizontal(classes="public-header-row"):
                    yield Label("Public Meshes", classes="field-label")
                    yield Button("↻ Refresh", variant="default", id="refresh-btn")

                with VerticalScroll(id="public-list-scroll"):
                    yield Static("[#52525b]Loading public meshes...[/]", id="empty-state")

                yield Static("[#27272a]─── or join a private mesh ───[/]", classes="section-divider")

                yield Label("Room Name", classes="field-label")
                yield Input(placeholder="private-room-name", id="private-mesh-input", max_length=32)

                yield Label("Password", classes="field-label")
                yield Input(placeholder="••••••••", password=True, id="private-pass-input", max_length=128)

                with Horizontal(classes="button-row"):
                    yield Button("Quit", variant="default", id="quit-btn-join")
                    yield Button("Join Private", variant="primary", id="join-private-btn")

            yield Label("", id="error-label")

    def on_mount(self) -> None:
        # Hide join container and password field by default
        self.query_one("#join-container").display = False
        self.query_one("#pass-label").display = False
        self.query_one("#pass-input").display = False
        self.query_one("#handle-input", Input).focus()

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == "action-radio":
            is_start = event.index == 0
            self.query_one("#start-container").display = is_start
            self.query_one("#join-container").display = not is_start
            self.query_one("#error-label", Label).update("")

            if not is_start:
                # Fetch public meshes when switching to join mode
                self.run_worker(self.fetch_public_meshes(), exclusive=True, name="fetch_public")

        elif event.radio_set.id == "visibility-radio":
            is_public = event.index == 0
            self.query_one("#pass-label").display = not is_public
            self.query_one("#pass-input").display = not is_public

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid in ("quit-btn", "quit-btn-join"):
            self.app.exit()
        elif bid == "connect-btn":
            self.run_worker(self.do_create_mesh(), exclusive=True)
        elif bid == "refresh-btn":
            self.run_worker(self.fetch_public_meshes(), exclusive=True, name="fetch_public")
        elif bid == "join-private-btn":
            self.run_worker(self.do_join_private(), exclusive=True)
        elif "join-btn" in event.button.classes:
            mesh_name = event.button.name or (bid[len("join-pub-"):] if bid and bid.startswith("join-pub-") else "")
            if mesh_name:
                self.run_worker(self.do_join_public(mesh_name), exclusive=True)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        iid = event.input.id
        if iid == "handle-input":
            if self.query_one("#start-container").display:
                self.query_one("#mesh-input", Input).focus()
            else:
                self.query_one("#private-mesh-input", Input).focus()
        elif iid == "mesh-input":
            self.query_one("#desc-input", Input).focus()
        elif iid == "desc-input":
            vis_radio = self.query_one("#visibility-radio", RadioSet)
            is_public = vis_radio.pressed_index == 0
            if is_public:
                self.run_worker(self.do_create_mesh(), exclusive=True)
            else:
                self.query_one("#pass-input", Input).focus()
        elif iid == "pass-input":
            self.run_worker(self.do_create_mesh(), exclusive=True)
        elif iid == "private-mesh-input":
            self.query_one("#private-pass-input", Input).focus()
        elif iid == "private-pass-input":
            self.run_worker(self.do_join_private(), exclusive=True)

    async def _validate_handle(self, ws):
        """Send handle and validate with server. Returns True on success."""
        handle = self.query_one("#handle-input", Input).value.strip()
        error_lbl = self.query_one("#error-label", Label)

        if not handle:
            error_lbl.update("Display name cannot be empty")
            self.query_one("#handle-input", Input).focus()
            return False

        await ws.send(handle + "\n")
        raw_resp = (await ws.recv()).strip()
        status, _, msg = raw_resp.partition("|")

        if status == "ERROR":
            error_lbl.update(msg or "Display name was rejected")
            await ws.close()
            return False

        if status != "USERNAME_OK":
            error_lbl.update("Invalid server response")
            await ws.close()
            return False

        return True

    async def do_create_mesh(self) -> None:
        handle = self.query_one("#handle-input", Input).value.strip()
        mesh = self.query_one("#mesh-input", Input).value.strip()
        desc = self.query_one("#desc-input", Input).value.strip()
        vis_radio = self.query_one("#visibility-radio", RadioSet)
        is_public = vis_radio.pressed_index == 0
        password = "" if is_public else self.query_one("#pass-input", Input).value
        error_lbl = self.query_one("#error-label", Label)
        connect_btn = self.query_one("#connect-btn", Button)

        if not handle:
            error_lbl.update("Display name cannot be empty")
            self.query_one("#handle-input", Input).focus()
            return
        if not mesh:
            error_lbl.update("Mesh room name cannot be empty")
            self.query_one("#mesh-input", Input).focus()
            return
        if not desc:
            error_lbl.update("Description cannot be empty")
            self.query_one("#desc-input", Input).focus()
            return
        if not is_public and not password:
            error_lbl.update("Password cannot be empty for private meshes")
            self.query_one("#pass-input", Input).focus()
            return

        connect_btn.disabled = True
        error_lbl.update("[#71717a]Creating mesh...[/]")

        try:
            ws = await websockets.connect(self.app.server_url)

            # 1. Send handle
            await ws.send(handle + "\n")
            raw_resp = (await ws.recv()).strip()
            status, _, msg = raw_resp.partition("|")

            if status == "ERROR":
                error_lbl.update(msg or "Display name was rejected")
                connect_btn.disabled = False
                await ws.close()
                return

            if status != "USERNAME_OK":
                error_lbl.update("Invalid server response")
                connect_btn.disabled = False
                await ws.close()
                return

            # 2. Send START with new protocol
            pub_flag = "1" if is_public else "0"
            await ws.send(f"START|{mesh}|{pub_flag}|{desc}|{password}\n")
            raw_mesh_resp = (await ws.recv()).strip()
            m_parts = raw_mesh_resp.split("|", 2)
            m_status = m_parts[0]
            m_msg = m_parts[1] if len(m_parts) > 1 else ""

            # Seamless fallback for legacy servers (e.g. production server before update)
            if m_status == "ERROR" and ("unsupported characters" in m_msg or "Invalid start request" in m_msg):
                fallback_password = password if not is_public else "public"
                await ws.send(f"START|{mesh}|{fallback_password}\n")
                raw_mesh_resp = (await ws.recv()).strip()
                m_parts = raw_mesh_resp.split("|", 2)
                m_status = m_parts[0]
                m_msg = m_parts[1] if len(m_parts) > 1 else ""

            if m_status == "ERROR":
                error_lbl.update(m_msg or "Failed to create mesh")
                connect_btn.disabled = False
                await ws.close()
                return

            # 3. Success
            self.app.username = handle
            self.app.mesh_name = mesh
            self.app.mesh_password = password
            self.app.mesh_is_public = is_public
            self.app.mesh_description = desc
            self.app.ws = ws
            self.app.switch_screen(ChatScreen())

        except Exception as e:
            error_lbl.update(f"Connection failed: {e}")
            connect_btn.disabled = False

    async def do_join_public(self, mesh_name: str) -> None:
        handle = self.query_one("#handle-input", Input).value.strip()
        error_lbl = self.query_one("#error-label", Label)

        if not handle:
            error_lbl.update("Display name cannot be empty")
            self.query_one("#handle-input", Input).focus()
            return

        error_lbl.update(f"[#71717a]Joining #{mesh_name}...[/]")

        try:
            ws = await websockets.connect(self.app.server_url)

            # 1. Send handle
            await ws.send(handle + "\n")
            raw_resp = (await ws.recv()).strip()
            status, _, msg = raw_resp.partition("|")

            if status == "ERROR":
                error_lbl.update(msg or "Display name was rejected")
                await ws.close()
                return

            if status != "USERNAME_OK":
                error_lbl.update("Invalid server response")
                await ws.close()
                return

            # 2. JOIN public mesh (no password)
            await ws.send(f"JOIN|{mesh_name}|\n")
            raw_mesh_resp = (await ws.recv()).strip()
            m_parts = raw_mesh_resp.split("|", 2)
            m_status = m_parts[0]
            m_msg = m_parts[1] if len(m_parts) > 1 else ""
            m_desc = m_parts[2] if len(m_parts) > 2 else ""

            # Seamless fallback for public meshes on legacy servers
            if m_status == "ERROR" and ("Password cannot be empty" in m_msg or "Wrong password" in m_msg):
                await ws.send(f"JOIN|{mesh_name}|public\n")
                raw_mesh_resp = (await ws.recv()).strip()
                m_parts = raw_mesh_resp.split("|", 2)
                m_status = m_parts[0]
                m_msg = m_parts[1] if len(m_parts) > 1 else ""
                m_desc = m_parts[2] if len(m_parts) > 2 else ""

            if m_status == "ERROR":
                error_lbl.update(m_msg or "Failed to join mesh")
                await ws.close()
                return

            # 3. Success
            self.app.username = handle
            self.app.mesh_name = mesh_name
            self.app.mesh_password = ""
            self.app.mesh_is_public = True
            self.app.mesh_description = m_desc
            self.app.ws = ws
            self.app.switch_screen(ChatScreen())

        except Exception as e:
            error_lbl.update(f"Connection failed: {e}")

    async def do_join_private(self) -> None:
        handle = self.query_one("#handle-input", Input).value.strip()
        mesh = self.query_one("#private-mesh-input", Input).value.strip()
        password = self.query_one("#private-pass-input", Input).value
        error_lbl = self.query_one("#error-label", Label)
        join_btn = self.query_one("#join-private-btn", Button)

        if not handle:
            error_lbl.update("Display name cannot be empty")
            self.query_one("#handle-input", Input).focus()
            return
        if not mesh:
            error_lbl.update("Room name cannot be empty")
            self.query_one("#private-mesh-input", Input).focus()
            return
        if not password:
            error_lbl.update("Password cannot be empty")
            self.query_one("#private-pass-input", Input).focus()
            return

        join_btn.disabled = True
        error_lbl.update("[#71717a]Joining private mesh...[/]")

        try:
            ws = await websockets.connect(self.app.server_url)

            # 1. Send handle
            await ws.send(handle + "\n")
            raw_resp = (await ws.recv()).strip()
            status, _, msg = raw_resp.partition("|")

            if status == "ERROR":
                error_lbl.update(msg or "Display name was rejected")
                join_btn.disabled = False
                await ws.close()
                return

            if status != "USERNAME_OK":
                error_lbl.update("Invalid server response")
                join_btn.disabled = False
                await ws.close()
                return

            # 2. JOIN private mesh
            await ws.send(f"JOIN|{mesh}|{password}\n")
            raw_mesh_resp = (await ws.recv()).strip()
            m_parts = raw_mesh_resp.split("|", 2)
            m_status = m_parts[0]
            m_msg = m_parts[1] if len(m_parts) > 1 else ""
            m_desc = m_parts[2] if len(m_parts) > 2 else ""

            if m_status == "ERROR":
                error_lbl.update(m_msg or "Failed to join mesh")
                join_btn.disabled = False
                await ws.close()
                return

            # 3. Success
            self.app.username = handle
            self.app.mesh_name = mesh
            self.app.mesh_password = password
            self.app.mesh_is_public = False
            self.app.mesh_description = m_desc
            self.app.ws = ws
            self.app.switch_screen(ChatScreen())

        except Exception as e:
            error_lbl.update(f"Connection failed: {e}")
            join_btn.disabled = False

    async def fetch_public_meshes(self) -> None:
        """Fetch live public mesh directory from the server."""
        error_lbl = self.query_one("#error-label", Label)
        scroll = self.query_one("#public-list-scroll", VerticalScroll)

        try:
            ws = await websockets.connect(self.app.server_url)

            # We need a temporary handle to authenticate
            handle = self.query_one("#handle-input", Input).value.strip()
            if not handle:
                # Set a placeholder for listing only
                handle = f"__listing_{id(self) % 9999}"

            await ws.send(handle + "\n")
            raw_resp = (await ws.recv()).strip()
            status, _, msg = raw_resp.partition("|")

            if status != "USERNAME_OK":
                # Can't authenticate, show empty state
                await scroll.remove_children()
                await scroll.mount(
                    Static("[#52525b]Enter a display name to browse public meshes[/]", id="empty-state")
                )
                try:
                    await ws.close()
                except Exception:
                    pass
                return

            # Request public list
            await ws.send("LIST_PUBLIC\n")
            raw_list = (await ws.recv()).strip()
            await ws.close()

            # Release the temporary username
            # (server will release on close)

            # Parse response: PUBLIC_LIST|[{...}, ...]
            if raw_list.startswith("PUBLIC_LIST|"):
                json_str = raw_list[len("PUBLIC_LIST|"):]
                mesh_list = json.loads(json_str)
            else:
                mesh_list = []

            # Update the scroll container
            await scroll.remove_children()

            if not mesh_list:
                await scroll.mount(
                    Static("[#52525b]No public meshes active right now.\nStart one or join a private room below.[/]", id="empty-state")
                )
            else:
                for m in mesh_list:
                    name = m.get("name", "unknown")
                    desc = m.get("desc", "")
                    online = m.get("online", 0)
                    card = Container(classes="mesh-card")
                    await scroll.mount(card)
                    header = Horizontal(classes="mesh-card-header")
                    await card.mount(header)
                    await header.mount(Label(f"[bold #60a5fa]#{name}[/]", classes="mesh-card-name"))
                    await header.mount(Label(f"[#22c55e]● {online} online[/]", classes="mesh-card-online"))
                    if desc:
                        await card.mount(Label(f"[#71717a]{desc}[/]", classes="mesh-card-desc"))
                    btn = Button("Join", variant="primary", name=name, classes="join-btn")
                    await card.mount(btn)

        except Exception as e:
            await scroll.remove_children()
            await scroll.mount(
                Static(f"[#ef4444]Failed to fetch meshes: {e}[/]", id="empty-state")
            )


class ChatScreen(Screen):
    def compose(self) -> ComposeResult:
        # Build header with public/private badge
        pub_badge = "[#22c55e]Public[/]" if self.app.mesh_is_public else "[#f59e0b]Private[/]"
        with Horizontal(id="chat-header"):
            yield Label(
                f"[bold]pingr[/]  [#71717a]•[/]  [#60a5fa]#{self.app.mesh_name}[/]  [#71717a]•[/]  {pub_badge}  [#71717a]•[/]  [bold #10b981]@{self.app.username}[/]",
                id="header-left",
            )
            yield Label("[#22c55e]●[/]  [#a1a1aa]1 online[/]", id="header-right")

        yield RichLog(id="chat-log", highlight=False, markup=True, wrap=True, auto_scroll=True)

        with Container(id="input-container"):
            yield Input(
                placeholder="Write a message... (Enter to send, /help for commands)",
                id="chat-input",
                max_length=2000,
            )

        yield Label(
            "Enter: Send  •  /copy: Copy Last  •  /help: Help  •  /members: Members  •  /clear: Clear  •  /exit: Quit",
            id="chat-footer",
        )

    def on_mount(self) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.write(f"[bold #f4f4f5]Connected to #{self.app.mesh_name}[/]")
        if self.app.mesh_description:
            log.write(f"[#71717a]{self.app.mesh_description}[/]")
        pub_label = "public" if self.app.mesh_is_public else "private"
        log.write(f"[#71717a]This {pub_label} room is ephemeral — messages exist only in memory.[/]")
        if self.app.mesh_is_public:
            log.write("[#71717a]Anyone can discover and join this mesh from the public directory.[/]")
        else:
            log.write("[#71717a]Share room name and password with friends to chat.[/]")
        log.write("[dim]──────────────────────────────────────────────────────────[/]")
        log.write("")

        self.query_one("#chat-input", Input).focus()
        self.run_worker(self.receive_loop(), exclusive=True)

    def update_members(self, count: int) -> None:
        right_lbl = self.query_one("#header-right", Label)
        unit = "member" if count == 1 else "online"
        right_lbl.update(f"[#22c55e]●[/]  [#a1a1aa]{count} {unit}[/]")

    async def receive_loop(self) -> None:
        ws = self.app.ws
        log = self.query_one("#chat-log", RichLog)

        while True:
            try:
                raw_data = await ws.recv()
                if not raw_data:
                    break

                data = raw_data.strip()
                parts = data.split("|", 2)
                msg_type = parts[0]
                now = datetime.now().strftime("%H:%M")

                if msg_type == "SERVER":
                    text = parts[1] if len(parts) > 1 else ""
                    clean_text = clean_incoming_text(text)
                    if clean_text.endswith(" joined the mesh"):
                        u = clean_text[: -len(" joined the mesh")]
                        log.write(f"[#71717a]{now}[/]  [dim italic #34d399]➜ {u} joined the mesh[/]")
                    elif clean_text.endswith(" left the mesh"):
                        u = clean_text[: -len(" left the mesh")]
                        log.write(f"[#71717a]{now}[/]  [dim italic #f87171]← {u} left the mesh[/]")
                    else:
                        log.write(f"[#71717a]{now}[/]  [dim italic #a1a1aa]— {clean_text} —[/]")
                    log.write("")
                    self.app.messages.append(Message("server", None, clean_text, timestamp=now))

                elif msg_type == "CHAT":
                    if len(parts) >= 3:
                        sender = parts[1]
                        content = clean_incoming_text(parts[2])
                        self.app.messages.append(Message("client", sender, content, timestamp=now))
                        is_self = sender == self.app.username

                        if is_self:
                            user_tag = f"[bold #10b981]{sender} (You):[/]"
                        else:
                            c_idx = get_user_color_index(sender)
                            user_tag = f"[bold {USER_PALETTE[c_idx]}]{sender}:[/]"

                        lines = content.split("\n")
                        if len(lines) == 1:
                            formatted = format_message_rich(lines[0], self.app.username)
                            log.write(f"[#71717a]{now}[/]  {user_tag}  {formatted}")
                        else:
                            log.write(f"[#71717a]{now}[/]  {user_tag}")
                            for line in lines:
                                formatted = format_message_rich(line, self.app.username)
                                log.write(f"       [#52525b]│[/] {formatted}")
                        log.write("")

                elif msg_type == "COUNT":
                    if len(parts) >= 2:
                        try:
                            count = int(parts[1])
                            self.app.member_count = count
                            self.update_members(count)
                        except Exception:
                            pass

                elif msg_type == "MEMBERS":
                    if len(parts) >= 2:
                        members = [n for n in parts[2].split("|") if n] if len(parts) >= 3 else []
                        log.write(f"[#71717a]{now}[/]  [bold #a78bfa]Online Participants ({len(members)}):[/]")
                        for m in members:
                            m_label = (
                                f"[bold #10b981]{m} (You)[/]"
                                if m == self.app.username
                                else f"[#f4f4f5]{m}[/]"
                            )
                            log.write(f"       [#71717a]•[/] {m_label}")
                        log.write("")

            except Exception:
                break

        log.write(f"[#71717a]{datetime.now().strftime('%H:%M')}[/]  [dim italic #ef4444]Disconnected from mesh.[/]")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        if not raw:
            return
        event.input.value = ""

        if raw == "/exit":
            try:
                await self.app.ws.send("CMD|exit\n")
            except Exception:
                pass
            try:
                await self.app.ws.close()
            except Exception:
                pass
            self.app.exit()
            return

        if raw == "/clear":
            self.query_one("#chat-log", RichLog).clear()
            self.notify("Chat cleared locally", title="Chat")
            return

        if raw == "/help":
            self.show_help()
            return

        if raw == "/members":
            try:
                await self.app.ws.send("CMD|members\n")
            except Exception:
                pass
            return

        if raw == "/copy":
            self.copy_latest()
            return

        if raw == "/copyall":
            self.copy_all()
            return

        try:
            clean_msg = clean_incoming_text(raw)
            await self.app.ws.send(f"MSG|{clean_msg}\n")
        except Exception as e:
            self.notify(f"Failed to send: {e}", severity="error")

    def copy_latest(self) -> None:
        client_msgs = [m for m in self.app.messages if m.kind == "client"]
        target = client_msgs[-1] if client_msgs else (self.app.messages[-1] if self.app.messages else None)
        if target and target.text:
            clean = clean_copied_text(target.text)
            if copy_to_clipboard(clean):
                self.notify(f"Copied message from {target.sender or 'Server'}", title="Clipboard")
            else:
                self.notify("Failed to copy to clipboard", severity="error")
        else:
            self.notify("No messages to copy", severity="warning")

    def copy_all(self) -> None:
        clean_lines = [clean_copied_text(m.text) for m in self.app.messages if m.text]
        transcript = "\n\n".join(clean_lines)
        if transcript and copy_to_clipboard(transcript):
            self.notify(f"Copied {len(clean_lines)} messages", title="Clipboard")
        else:
            self.notify("No messages to copy", severity="warning")

    def show_help(self) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.write("[dim]──────────────────────────────────────────────────────────[/]")
        log.write("[bold #f4f4f5]Commands & Shortcuts[/]")
        log.write("  [#60a5fa]/copy[/]      [#71717a]Copy latest message cleanly to clipboard[/]")
        log.write("  [#60a5fa]/copyall[/]   [#71717a]Copy entire chat transcript to clipboard[/]")
        log.write("  [#60a5fa]/members[/]   [#71717a]List all participants online in this mesh[/]")
        log.write("  [#60a5fa]/clear[/]     [#71717a]Clear chat log locally[/]")
        log.write("  [#60a5fa]/help[/]      [#71717a]Show this help reference[/]")
        log.write("  [#60a5fa]/exit[/]      [#71717a]Leave mesh and quit pingr[/]")
        log.write("[bold #f4f4f5]Formatting[/]")
        log.write("  [#71717a]**bold**, *italic*, `code`, > quote, @user, https://url[/]")
        log.write("[dim]──────────────────────────────────────────────────────────[/]")
        log.write("")


class PingrApp(App):
    CSS = APP_CSS
    TITLE = "pingr"

    def __init__(self, server_url: str = None):
        super().__init__()
        self.server_url = server_url or get_server_url()
        self.username = ""
        self.mesh_name = ""
        self.mesh_password = ""
        self.mesh_is_public = True
        self.mesh_description = ""
        self.ws = None
        self.messages = []
        self.member_count = 1

    def on_mount(self) -> None:
        self.push_screen(SetupScreen())


def main():
    args = sys.argv[1:]
    if "-v" in args or "--version" in args:
        print(f"pingr {__version__}")
        return
    if "-h" in args or "--help" in args:
        print("pingr - A clean, minimal, and ephemeral terminal mesh messaging client\n")
        print("Usage:")
        print("  pingr [OPTIONS]")
        print("  msg [OPTIONS]\n")
        print("Options:")
        print("  -s, --server <url>   WebSocket server URL (default: wss://tmsg.onrender.com)")
        print("  -v, --version        Show version number and exit")
        print("  -h, --help           Show this help message and exit\n")
        print("Environment Variables:")
        print("  TMSG_SERVER          Default server URL to connect to")
        print("  SERVER_URL           Fallback server URL")
        return

    app = PingrApp()
    app.run()


if __name__ == "__main__":
    main()
