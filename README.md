<div align="center">

```
  ██████╗ ██╗███╗   ██╗ ██████╗ ██████╗ 
  ██╔══██╗██║████╗  ██║██╔════╝ ██╔══██╗
  ██████╔╝██║██╔██╗ ██║██║  ███╗██████╔╝
  ██╔═══╝ ██║██║╚██╗██║██║   ██║██╔══██╗
  ██║     ██║██║ ╚████║╚██████╔╝██║  ██║
  ╚═╝     ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝
```

### Clean, minimal, and ephemeral terminal mesh messaging. No accounts, no clutter — just a mesh and a password.

[![PyPI version](https://img.shields.io/pypi/v/pingr?color=3b82f6&label=pypi)](https://pypi.org/project/pingr/)
[![Downloads](https://img.shields.io/pypi/dm/pingr?color=38bdf8)](https://pypi.org/project/pingr/)
[![Python versions](https://img.shields.io/pypi/pyversions/pingr?color=22c55e)](https://pypi.org/project/pingr/)
[![License](https://img.shields.io/pypi/l/pingr?color=eab308)](https://pypi.org/project/pingr/)
[![Made with Textual](https://img.shields.io/badge/TUI-Textual-38bdf8)](https://textual.textualize.io/)
[![Websockets](https://img.shields.io/badge/transport-websockets-93c5fd)](https://websockets.readthedocs.io/)

</div>

---

**Pingr** turns your terminal into a sleek, real-time messaging client. Spin up a **mesh** (a room) with a name and a password, share the credentials, and talk in real time — colored usernames, markdown formatting, `@mentions`, and instant clipboard export included. No sign-up, no telemetry, no browser tabs.

---

## ✨ Features

- **Zero-friction rooms** — create a mesh with a name + password, no accounts, no database
- **Modern Textual TUI** — sleek zinc dark theme (`#09090b`), centered modal dialog with ASCII branding, clean hairline borders, and responsive form controls
- **Real-time messaging** over WebSockets with automatic member tracking
- **Subtle message spacing** — readable, uncrowded message stream with clear separation between speakers and system events
- **Markdown-flavored chat** — `**bold**`, `*italic*`, `` `inline code` ``, `> quotes`, styled `https://` links, and `@mentions` (self-mentions highlighted)
- **Instant clipboard tools** — copy the latest message cleanly via `/copy` or export the full conversation transcript via `/copyall`
- **Cross-platform clipboard support** — uses `pyperclip` when available, with native fallbacks (`clip.exe`, `pbcopy`, `wl-copy`, `xclip`, `xsel`) and OSC 52 terminal sequences for SSH sessions
- **Built-in slash commands** — `/help`, `/copy`, `/copyall`, `/clear`, `/members`, `/exit`
- **Self-hosted server included** — host your own WebSocket server anywhere with `python server.py`, or use the default hosted cluster
- **100% ephemeral** — messages exist strictly in memory; leaving the mesh leaves no trace behind

---

## 📦 Installation

```bash
pip install -U pingr
```

PyPI package: **https://pypi.org/project/pingr/**

---

## 🚀 Quick Start

Start Pingr using either command:

```bash
pingr
# or
msg
```

### 1. Connection Dialog
When Pingr starts, you'll be presented with the setup dialog:
1. **Display Name** — your handle for the session (up to 24 characters)
2. **Action** — select **Start a new mesh** or **Join existing mesh**
3. **Mesh Room** — the room name (case-insensitive)
4. **Password** — room protection key (masked input)

Press **Enter** to jump between fields or hit **Connect**.

---

### 2. Chatting & Commands

```
pingr  •  #general  •  @shakib                                             ● 3 online
──────────────────────────────────────────────────────────────────────────────────────
12:00  ➜ alex joined the mesh

12:01  alex:  Hey everyone! Have you installed `pip install pingr` yet?

12:01  shakib (You):  Yes, the new Textual UI looks super clean!

12:02  alex:  > markdown quotes and @mentions are working great too

──────────────────────────────────────────────────────────────────────────────────────
[ Write a message... (Enter to send, /help for commands)                             ]
Enter: Send  •  /copy: Copy Last  •  /help: Help  •  /members: Members  •  /exit: Quit
```

#### Slash Commands

| Command    | Description |
|------------|-------------|
| `/copy`    | Copy the latest chat message cleanly to your system clipboard |
| `/copyall` | Copy the entire chat transcript to your system clipboard |
| `/members` | List all participants currently active in the mesh |
| `/clear`   | Clear the message stream locally |
| `/help`    | Show built-in command and formatting reference |
| `/exit`    | Disconnect and exit Pingr |

#### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Submit current field / send message / trigger button |
| `Tab` / `Shift+Tab` | Navigate between inputs and buttons |
| `Mouse Wheel` / `Page Up` / `Page Down` | Scroll message history smoothly |
| `Ctrl+C` / `Ctrl+Q` | Quit Pingr |

---

### 🌐 Custom & Self-Hosted Servers

By default, Pingr connects to the hosted cluster. To connect to your own server:

```bash
pingr --server wss://chat.example.com
# or shorthand
pingr -s wss://chat.example.com
```

Or set the environment variable:

```bash
export TMSG_SERVER=wss://chat.example.com
pingr
```

---

## 🖥️ Running the Server

Pingr includes a self-contained, high-performance WebSocket server:

```bash
python server.py
```

- Port configuration: reads `PORT` environment variable (defaults to `5000`)
- Single `asyncio` event loop with per-mesh locks guaranteeing atomic join/leave state transitions
- Automatic cleanup: empty meshes are immediately freed from memory

---

## 📁 Project Structure

```
pingr/
├── tmsg/
│   ├── __init__.py    # Package version & metadata
│   └── main.py        # Textual TUI client (`pingr` / `msg`)
├── server.py          # Ephemeral WebSocket chat server
├── pyproject.toml     # Packaging configuration (PEP 621)
├── requirements.txt   # Runtime dependencies
└── README.md          # Documentation & guide
```

---

## 🛠️ Tech Stack

- **[Textual](https://textual.textualize.io/)** — modern, reactive terminal UI framework
- **[Rich](https://rich.readthedocs.io/)** — rich text, markdown rendering, and syntax styling
- **[websockets](https://websockets.readthedocs.io/)** — asynchronous WebSocket protocol
- **Python 3.8+** — clean, cross-platform architecture

---

## 🤝 Contributing

Contributions, issues, and feature suggestions are always welcome! Feel free to check the [issues page](https://github.com/ShakibCodes/tmsg/issues).

---

## 📜 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) or project files for details.