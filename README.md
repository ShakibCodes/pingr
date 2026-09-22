# <div align="center">

```
  ██████╗ ██╗███╗   ██╗ ██████╗ ██████╗ 
  ██╔══██╗██║████╗  ██║██╔════╝ ██╔══██╗
  ██████╔╝██║██╔██╗ ██║██║  ███╗██████╔╝
  ██╔═══╝ ██║██║╚██╗██║██║   ██║██╔══██╗
  ██║     ██║██║ ╚████║╚██████╔╝██║  ██║
  ╚═╝     ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝
```

# Pingr

**Clean, minimal, and ephemeral terminal mesh messaging** – no accounts, no clutter, just a mesh and a password.

[![PyPI version](https://img.shields.io/pypi/v/pingr?color=3b82f6&label=pypi)](https://pypi.org/project/pingr/)
[![Downloads](https://img.shields.io/pypi/dm/pingr?color=38bdf8)](https://pypi.org/project/pingr/)
[![Python versions](https://img.shields.io/pypi/pyversions/pingr?color=22c55e)](https://pypi.org/project/pingr/)
[![License](https://img.shields.io/pypi/l/pingr?color=eab308)](https://pypi.org/project/pingr/)
[![Made with Textual](https://img.shields.io/badge/TUI-Textual-38bdf8)](https://textual.textualize.io/)
[![Websockets](https://img.shields.io/badge/transport-websockets-93c5fd)](https://websockets.readthedocs.io/)

---

Pingr turns your terminal into a sleek, real‑time messaging client. Create a **mesh** (a room) with a name and a password, share the credentials, and start chatting – usernames are colour‑coded, markdown is supported, `@mentions` work, and you can instantly copy messages to the clipboard. Everything lives only in memory; once you leave the mesh, the conversation disappears.

---

## ✨ Features

- **Zero‑friction rooms** – start a mesh with just a name and password; no accounts or databases.
- **Modern Textual TUI** – dark zinc theme, centred modal with ASCII branding, hairline borders, and responsive controls.
- **Real‑time messaging** via WebSockets with automatic member tracking.
- **Markdown‑flavoured chat** – `**bold**`, `*italic*`, `` `inline code` ``, `> quotes`, auto‑linked URLs, and `@mentions`.
- **Instant clipboard tools** – copy the latest message (`/copy`) or the full transcript (`/copyall`).
- **Cross‑platform clipboard** – uses `pyperclip` when available, falls back to native commands (`clip.exe`, `pbcopy`, `wl-copy`, `xclip`, `xsel`) and OSC‑52 for SSH.
- **Built‑in slash commands** – `/help`, `/copy`, `/copyall`, `/clear`, `/members`, `/exit`.
- **Self‑hosted server** – run `python server.py` anywhere, or use the default hosted cluster.
- **100 % Ephemeral** – messages are stored only in RAM; leaving the mesh erases all history.

---

## 📦 Installation

```bash
pip install -U pingr
```

The package is published on PyPI: <https://pypi.org/project/pingr/>

---

## 🚀 Quick Start

```bash
# Launch the client (alias `msg` is also provided)
pingr
# or
msg
```

### 1️⃣ Connection dialog
When the program starts you’ll see a setup dialog:
1. **Display Name** – your handle (max 24 characters).
2. **Action** – *Start a new mesh* or *Join existing mesh*.
3. **Mesh Room** – case‑insensitive room name.
4. **Password** – secret key (masked input).

Press **Enter** to move between fields and **Connect** to join.

### 2️⃣ Chatting & commands
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

#### Slash commands
| Command    | Description |
|------------|-------------|
| `/copy`    | Copy the latest chat message to the clipboard |
| `/copyall` | Copy the entire transcript to the clipboard |
| `/members` | List currently connected participants |
| `/clear`   | Clear the local message stream |
| `/help`    | Show built‑in command reference |
| `/exit`    | Disconnect and quit |

#### Keyboard shortcuts
| Shortcut | Action |
|----------|--------|
| `Enter` | Submit field / send message |
| `Tab` / `Shift+Tab` | Navigate inputs and buttons |
| Mouse wheel / `Page Up` / `Page Down` | Scroll history |
| `Ctrl+C` / `Ctrl+Q` | Quit |

---

## 🌐 Custom & Self‑hosted servers

By default Pingr connects to the public cluster. To use your own server:

```bash
pingr --server wss://chat.example.com
# or short form
pingr -s wss://chat.example.com
```

Or set the environment variable:

```bash
export TMSG_SERVER=wss://chat.example.com   # Linux/macOS
set TMSG_SERVER=wss://chat.example.com      # Windows PowerShell
pingr
```

---

## 🖥️ Running the server

Pingr ships with a lightweight WebSocket server:

```bash
python server.py
```

- **Port** – reads the `PORT` environment variable (default `5000`).
- **Concurrency** – single `asyncio` loop with per‑mesh locks ensures atomic join/leave operations.
- **Cleanup** – empty meshes are freed immediately from memory.

---

## 📁 Project Structure

```
pingr/
├─ tmsg/
│  ├─ __init__.py      # package metadata
│  └─ main.py          # Textual TUI client (`pingr` / `msg`)
├─ server.py            # Ephemeral WebSocket server
├─ pyproject.toml       # Packaging config (PEP 621)
├─ requirements.txt     # Runtime dependencies
└─ README.md            # Documentation (this file)
```

---

## 🛠️ Tech Stack

- **[Textual](https://textual.textualize.io/)** – modern reactive terminal UI framework
- **[Rich](https://rich.readthedocs.io/)** – colourised text, markdown rendering, and styling
- **[websockets](https://websockets.readthedocs.io/)** – async WebSocket protocol implementation
- **Python 3.8+** – cross‑platform, clean architecture

---

## 🤝 Contributing

Contributions, issues, and feature suggestions are welcome! Please check the
[issues page](https://github.com/ShakibCodes/tmsg/issues) and feel free to submit pull requests.

---

## 📜 License

Distributed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

*Happy chatting!*