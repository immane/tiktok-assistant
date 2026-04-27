# TikTok Live Assistant

A lightweight TikTok LIVE command-line assistant that streams comments with Chinese translation, monitors gift events, triggers sound alerts, and supports flexible hotkey automation with concurrent rule execution.

> 中文文档：[README.zh-cn.md](README.zh-cn.md)

## Features

- **Live comments** — Print incoming comments in real time, each automatically followed by a Chinese translation
- **Gift monitoring** — Detect gifts received in the live room and push them into an async processing queue
- **Sound alerts** — Play the system notification sound (or a custom `.wav` file) when a gift is queued
- **Smart hotkey trigger** — Fire hotkeys based on gift name and diamond count with concurrent rule execution and optional repeat counts
- **Gift filtering** — Optionally watch only specific gift names
- **UTF-8 console support** — Built-in Windows 10 UTF-8 console fix (black background + white text)
- **Graceful shutdown** — `Ctrl+C` cleanly cancels all async tasks

## Project structure

```
tiktok-assistant/
├── main.py            # Entry point, argument parsing, connection lifecycle
├── event_handlers.py  # TikTok event callbacks (comments, gifts, connect/disconnect)
├── gift_queue.py      # Gift queue consumer, trigger rule parsing, and sound playback
├── scripts/
│   └── run_win10.ps1  # Windows 10 launcher with built-in JSON config
└── requirements.txt   # Python dependencies
```

## Requirements

- Python 3.11+
- [TikTokLive](https://github.com/isaackogan/TikTokLive) — TikTok LIVE WebSocket client
- [deep-translator](https://github.com/nidhaloff/deep-translator) — Google Translate wrapper (no API key needed)
- [pynput](https://github.com/moses-palmer/pynput) — Global keyboard simulation for hotkey trigger

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/tiktok-assistant.git
cd tiktok-assistant

# Create a virtual environment
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Build executable (optional, Windows only)
pip install pyinstaller
pyinstaller --clean --noconfirm tiktok-assistant.spec
```

## Usage

### Option 1: Windows 10 Launcher (Recommended for Users)

Edit `scripts/run_win10.ps1` and modify the **【用户配置区】** section:

```powershell
$exePath = "..\dist\tiktok-assistant.exe"
$configJson = @'
{
  "unique_id": "some_creator",
  "sound": "",
  "queue_timeout": 0,
  "no_comments": false,
  "triggers": [
    {"trigger": "[default]", "action-key": "x"},
    {"trigger": "Rosa", "action-key": "x"},
    {"trigger": "Glasses", "action-key": "x"},
    {"trigger": "Glasses", "action-key": "c", "repeats": 5},
    {"trigger": "Glasses", "action-key": "ctrl-v", "repeats": 1}
  ]
}
'@
```

Then run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_win10.ps1
```

Or double-click the script directly (may require execution policy adjustment).

### Option 2: Command Line (Direct)

```bash
python main.py <creator_unique_id>
```

### Examples

**Basic usage:**

```bash
python main.py some_creator
```

**Watch specific gifts only:**

```bash
python main.py some_creator --gift-names Rosa Galaxy "TikTok Universe"
```

**Custom alert sound:**

```bash
python main.py some_creator --sound alert.wav
```

**Hide comments, gifts only:**

```bash
python main.py some_creator --no-comments
```

**Cooldown between gift events:**

```bash
python main.py some_creator --queue-timeout 2.0
```

**Hotkey trigger with JSON rules:**

```bash
python main.py some_creator --triggers '[
  {"trigger": "[default]", "action-key": "x"},
  {"trigger": "Rosa", "action-key": "c", "repeats": 3}
]'
```

## Arguments

| Argument | Description | Default |
|---|---|---|
| `unique_id` | Creator's TikTok username | required |
| `--gift-names` | Gift names to watch; omit to queue every gift | all gifts |
| `--sound` | Path to a custom `.wav` alert file | system beep |
| `--no-comments` | Suppress comment output | off |
| `--queue-timeout` | Seconds to wait after processing each gift | `0.0` |
| `--triggers` | JSON array of trigger rules (see below) | disabled |

### `--triggers` JSON Format

The `--triggers` parameter accepts a JSON array where each rule has:

- **`trigger`** (string, required): Gift name to match (case-insensitive), or `[default]` for fallback rule
- **`action-key`** (string, required): Key or combo to fire (`x`, `ctrl-v`, `ctrl+v`, `alt-s`, etc.)
- **`repeats`** (int, optional): Number of times to fire the key; if omitted, defaults to `task.diamonds`

#### Matching Rules

- **Named rules** (e.g., `"Rosa"`, `"Glasses"`) trigger when that gift is received
- **Multiple rules for same gift** execute **concurrently**
  - Example: Receiving "Glasses" with 3 diamonds → fires `x` 3 times, `c` 5 times (fixed), `ctrl-v` 1 time (fixed) **simultaneously**
- **Default rule** (`"[default]"`) acts as a fallback
  - Only triggers when NO named rule matched the gift name
  - Mutually exclusive with named rules

#### Example

```json
[
  {"trigger": "[default]", "action-key": "x"},
  {"trigger": "Rosa", "action-key": "x"},
  {"trigger": "Glasses", "action-key": "x"},
  {"trigger": "Glasses", "action-key": "c", "repeats": 5},
  {"trigger": "Glasses", "action-key": "ctrl-v", "repeats": 1}
]
```

Behavior:
- Rosa gift → fires `x` 3 times (example: 3 diamonds)
- Glasses gift → fires `x` 3 times, `c` 5 times (fixed), `ctrl-v` 1 time (fixed) **at the same time**
- Other gifts → fires `x` N times (where N = diamond count)

## Notes

- The target creator must be **live** when you run the script; otherwise the program exits with an `is not live right now` message.
- Sound alerts use `winsound` and are **Windows only**; the alert step is skipped silently on other platforms.
- Translation uses the free Google Translate endpoint — no API key required, but an internet connection is needed.
- `run_win10.ps1` automatically sets console to black background with white text to avoid Windows 10's default blue console theme.

