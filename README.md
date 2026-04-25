# TikTok Live Assistant

A lightweight TikTok LIVE command-line assistant that streams comments with Chinese translation, monitors gift events, and triggers sound alerts.

> 中文文档：[README.zh-cn.md](README.zh-cn.md)

## Features

- **Live comments** — Print incoming comments in real time, each automatically followed by a Chinese translation
- **Gift monitoring** — Detect gifts received in the live room and push them into an async processing queue
- **Sound alerts** — Play the system notification sound (or a custom `.wav` file) when a gift is queued
- **Gift filtering** — Optionally watch only specific gift names
- **Graceful shutdown** — `Ctrl+C` cleanly cancels all async tasks

## Project structure

```
tiktok-assistant/
├── main.py            # Entry point, argument parsing, connection lifecycle
├── event_handlers.py  # TikTok event callbacks (comments, gifts, connect/disconnect)
├── gift_queue.py      # Gift queue consumer and sound playback
└── requirements.txt   # Python dependencies
```

## Requirements

- Python 3.11+
- [TikTokLive](https://github.com/isaackogan/TikTokLive) — TikTok LIVE WebSocket client
- [deep-translator](https://github.com/nidhaloff/deep-translator) — Google Translate wrapper (no API key needed)

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
```

## Usage

### Basic

```bash
python main.py <creator_unique_id>
```

```
[system] Connecting to @some_creator...
[system] Connected to @some_creator
[14:23:01] [comment] Alice: Hello!（你好！）
[14:23:05] [gift-detected] queued -> Bob sent Rose x3 (1 diamonds each, 3 total)
[14:23:05] [gift-queue] Bob sent Rose x3 (1 diamonds each, 3 total)
```

### Watch specific gifts only

```bash
python main.py some_creator --gift-names Rose Galaxy "TikTok Universe"
```

### Custom alert sound

```bash
python main.py some_creator --sound alert.wav
```

### Hide comments, gifts only

```bash
python main.py some_creator --no-comments
```

### Cooldown between gift events

```bash
python main.py some_creator --queue-timeout 2.0
```

## Arguments

| Argument | Description | Default |
|---|---|---|
| `unique_id` | Creator's TikTok username | required |
| `--gift-names` | Gift names to watch; omit to queue every gift | all gifts |
| `--sound` | Path to a custom `.wav` alert file | system beep |
| `--no-comments` | Suppress comment output | off |
| `--queue-timeout` | Seconds to wait after processing each gift | `0.0` |

## Notes

- The target creator must be **live** when you run the script; otherwise the program exits with an `is not live right now` message.
- Sound alerts use `winsound` and are **Windows only**; the alert step is skipped silently on other platforms.
- Translation uses the free Google Translate endpoint — no API key required, but an internet connection is needed.
