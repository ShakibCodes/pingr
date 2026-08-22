<div align="center">

```
┌───────────────────────────────────────────────────────────┐
│                                                             │
│   ██████╗ ██╗███╗   ██╗ ██████╗ ██████╗                    │
│   ██╔══██╗██║████╗  ██║██╔════╝ ██╔══██╗                   │
│   ██████╔╝██║██╔██╗ ██║██║  ███╗██████╔╝                   │
│   ██╔═══╝ ██║██║╚██╗██║██║   ██║██╔══██╗                   │
│   ██║     ██║██║ ╚████║╚██████╔╝██║  ██║                   │
│   ╚═╝     ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝                    │
│                                                             │
└───────────────────────────────────────────────────────────┘
```

### Message from your terminal. No accounts, no clutter — just a mesh and a password.

[![PyPI version](https://img.shields.io/pypi/v/pingr?color=3b82f6&label=pypi)](https://pypi.org/project/pingr/)
[![Downloads](https://img.shields.io/pypi/dm/pingr?color=38bdf8)](https://pypi.org/project/pingr/)
[![Python versions](https://img.shields.io/pypi/pyversions/pingr?color=22c55e)](https://pypi.org/project/pingr/)
[![License](https://img.shields.io/pypi/l/pingr?color=eab308)](https://pypi.org/project/pingr/)
[![Made with prompt_toolkit](https://img.shields.io/badge/TUI-prompt__toolkit-6ee7b7)](https://python-prompt-toolkit.readthedocs.io/)
[![Websockets](https://img.shields.io/badge/transport-websockets-93c5fd)](https://websockets.readthedocs.io/)

</div>

---

**Pingr** turns your terminal into a live chat room. Spin up a **mesh** (a room) with a name and a password, share the credentials, and talk in real time — colored usernames, markdown formatting, `@mentions`, and clipboard copy included. No sign-up, no app, no browser tab. Inspired by the terminal chat scenes from *Mr. Robot*.

<!--
📸 SCREENSHOT / DEMO AREA
Drop a screenshot or GIF here, e.g.:

![Pingr chat screen](docs/assets/pingr-chat.png)

Good shots to include:
1. The mesh-selection menu (Start Mesh / Join Mesh)
2. An active chat with a few messages — colored usernames, a code block, a @mention
3. Browse & Copy mode (after pressing Tab) with the footer hints visible
-->

![Pingr demo](docs/assets/pingr-demo.gif)

---

## ✨ Features

- **Zero-friction rooms** — create a mesh with a name + password, no accounts, no database
- **Real-time messaging** over WebSockets
- **Rich terminal UI** built with `prompt_toolkit` — colored, deterministic per-user names, a live member count, and a status header/footer
- **Markdown-flavored chat** — `**bold**`, `*italic*`, `` `inline code` ``, multi-line code blocks, `> quotes`, clickable-looking `https://` links, and `@mentions` (self-mentions get highlighted)
- **Browse & Copy mode** — press `Tab` to select and copy any message (clean, with no username/border clutter) without leaving the TUI
- **Cross-platform clipboard support** — uses `pyperclip` when available, with native fallbacks (`pbcopy`, `clip.exe`, `wl-copy`, `xclip`, `xsel`) and an OSC 52 terminal fallback so copy works pretty much everywhere, including over SSH
- **Slash commands** — `/help`, `/copy`, `/copyall`, `/clear`, `/members`, `/exit`
- **Toast notifications** — quick, non-blocking feedback for actions like copying
- **Configurable server** — point the client at any Pingr server via a flag or environment variable
- **Self-hosted server included** — run your own instance anywhere, or use the default hosted one
- **No local storage** — usernames and meshes live only for the session

---

## 📦 Installation

```bash
pip install pingr
```

PyPI page: **https://pypi.org/project/pingr/**

## 🚀 Usage

Start the client:

```bash
msg
```

You'll be prompted for:

1. **Your name** — your display name for the session
2. **Start Mesh** or **Join Mesh** — use the arrow keys + Enter to choose
3. **Mesh name** and **password** — create a new mesh, or join an existing one with matching credentials

Once connected, you're in the chat:

```
[ PINGR ]  •  yourname  •  mesh-name  •  [ ⌨ INPUT MODE ]  •  3 members  •  ● Connected
────────────────────────────────────────────────────────────────────────────────────
➜ [Server] alex joined the mesh
[alex] hey, anyone around? check `pip install pingr`
[you (You)] yeah, what's up
[alex] > did you see the new release
[alex] that markdown support is neat, @you

>> 
[Tab] Browse & Copy   [Enter] Send   [/copy] Copy Last   [/help] Help   [/members] Members   [/exit] Exit
```

### Slash commands

| Command    | Description                                             |
|------------|-----------------------------------------------------------|
| `/help`    | Show commands and keyboard shortcuts                       |
| `/copy`    | Copy the latest message to your clipboard                  |
| `/copyall` | Copy the entire visible chat transcript to your clipboard   |
| `/clear`   | Clear your local chat view (doesn't affect other members)  |
| `/members` | List everyone currently in the mesh                        |
| `/exit`    | Leave the mesh and close the connection                    |

### Keyboard shortcuts

| Key                  | Context       | Action                                        |
|-----------------------|--------------|------------------------------------------------|
| `Tab`                 | Anywhere      | Toggle between Input mode and Browse & Copy mode |
| `c` / `Ctrl+C` / `y`   | Browse mode   | Copy the selected text, or the message under the cursor (clean, no username/border) |
| `l`                    | Browse mode   | Copy the latest clean message                   |
| `a`                    | Browse mode   | Copy the whole visible transcript               |
| `Shift + Arrows` / mouse drag | Browse mode | Select text                              |
| `Enter` / `i` / `Esc`  | Browse mode   | Return to typing                                |
| `Page Up` / `Page Down`| Input mode    | Scroll the chat                                 |
| `Home` / `End`         | Input mode    | Jump to top / bottom of chat                    |

### Formatting

Messages support light markdown: `**bold**`, `*italic*`, `` `inline code` ``, multi-line code fences, `> quotes`, plain `https://` links, and `@username` mentions (mentioning yourself is highlighted differently).

### Connecting to a custom server

By default the client connects to a hosted Pingr server. To use your own:

```bash
msg --server wss://your-server.example.com
# or
msg -s wss://your-server.example.com
```

Or via environment variable:

```bash
export TMSG_SERVER=wss://your-server.example.com
msg
```

(`SERVER_URL` is also accepted as a fallback env var.)

---

## 🖥️ Self-hosting the server

Pingr's client talks to a WebSocket server. You can run your own instead of using the default hosted one:

```bash
python server.py
```

The server reads its port from the `PORT` environment variable (defaults to `5000`) and listens on `0.0.0.0`.

### Server-side rules

- Usernames: up to 24 characters, must be unique while connected
- Mesh names: up to 32 characters, case-insensitive
- Passwords: up to 128 characters
- Messages: 1–2000 characters
- A mesh is automatically deleted once its last member leaves

---

## 🏗️ How it works

Pingr uses a simple pipe-delimited text protocol over WebSockets:

- `START|<mesh>|<password>` — create a new mesh
- `JOIN|<mesh>|<password>` — join an existing mesh
- `MSG|<text>` — send a chat message
- `CMD|members` / `CMD|exit` — client commands
- `CHAT|<sender>|<text>`, `SERVER|<text>`, `COUNT|<n>`, `MEMBERS|<n>|<name1>|<name2>...` — server broadcasts

The **server** (`server.py`) is a single `asyncio` event loop using the [`websockets`](https://websockets.readthedocs.io/) library, with an `asyncio.Lock` guarding shared mesh state so joins, leaves, and broadcasts stay consistent under concurrent connections.

The **client** (`main.py`) connects via `websockets.sync.client`, runs a background thread to receive and render incoming messages, and uses [`prompt_toolkit`](https://python-prompt-toolkit.readthedocs.io/) to build the full-screen TUI — a custom lexer handles markdown, mentions, and colored usernames, while a separate Browse mode lets you select and copy text cleanly.

---

## 📁 Project structure

```
pingr/
├── tmsg/
│   ├── __init__.py
│   └── main.py        # CLI entrypoint (`msg`) — the terminal client
├── server.py           # WebSocket chat server
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## 🛠️ Tech stack

- Python 3
- [`websockets`](https://pypi.org/project/websockets/) — async WebSocket server & sync client
- [`prompt_toolkit`](https://pypi.org/project/prompt-toolkit/) — full-screen terminal UI
---

## 🤝 Contributing

Issues and pull requests are welcome. If you spot a bug or have an idea for a feature (DMs? message history? mesh discovery?), feel free to open an issue.

---

## 📜 License

MIT — do whatever you want with it, just don't blame me if your mesh gets raided.

---

<div align="center">

*"Hello, friend."* — built for anyone who thinks the terminal is still the best chat client.

</div>