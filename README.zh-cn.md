# TikTok Live Assistant

一个轻量级的 TikTok 直播命令行助手，实时显示评论（附中文翻译）、监听礼物事件并触发灵活的热键自动化。支持基于礼物名称的规则匹配、多规则并发执行和自定义按键重复次数。

> English version: [README.md](README.md)

## 功能特性

- **实时评论** — 在终端实时打印直播间评论，自动附上中文翻译
- **礼物监听** — 检测直播间收到的礼物并放入异步队列处理
- **声音提醒** — 收到礼物时触发系统提示音或自定义 `.wav` 文件
- **智能热键触发** — 基于礼物名称的 JSON 规则，支持多规则并发执行、按次数重复触发
- **礼物过滤** — 可指定只监听特定礼物名称
- **UTF-8 控制台支持** — Windows 10 内置 UTF-8 修复（黑底白字）
- **优雅退出** — `Ctrl+C` 安全关闭，清理所有异步任务

## 项目结构

```
tiktok-assistant/
├── main.py            # 启动入口、参数解析、连接生命周期管理
├── event_handlers.py  # TikTok 事件回调（评论、礼物、连接状态）
├── gift_queue.py      # 礼物队列消费、规则解析、声音播放
├── scripts/
│   └── run_win10.ps1  # Windows 10 启动脚本，内置 JSON 配置
└── requirements.txt   # 依赖声明
```

## 依赖

- Python 3.11+
- [TikTokLive](https://github.com/isaackogan/TikTokLive) — TikTok 直播 WebSocket 连接
- [deep-translator](https://github.com/nidhaloff/deep-translator) — Google 翻译（无需 API Key）
- [pynput](https://github.com/moses-palmer/pynput) — 全局键盘模拟（热键触发）

## 安装

```bash
# 克隆项目
git clone https://github.com/your-username/tiktok-assistant.git
cd tiktok-assistant

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS / Linux

# 安装依赖
pip install -r requirements.txt

# 构建可执行文件（可选，仅 Windows）
pip install pyinstaller
pyinstaller --clean --noconfirm tiktok-assistant.spec
```

## 使用方法

### 方式一：Windows 10 启动脚本（推荐用户使用）

编辑 `scripts/run_win10.ps1`，修改【用户配置区】：

```powershell
# EXE 路径（相对或绝对均可）
$exePath = "..\dist\tiktok-assistant.exe"

# 自定义配置 JSON（在这里修改）
$configJson = @'
{
  "unique_id": "your_creator_name",
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

然后运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_win10.ps1
```

或直接双击脚本（可能需要调整执行策略）。

**脚本特性：**
- ✅ 自动检测路径（相对或绝对）
- ✅ 黑底白字控制台（避免 Win10 蓝底）
- ✅ 自动 UTF-8 编码处理
- ✅ 配置和代码分离，用户只改 JSON

### 方式二：命令行直接运行

```bash
python main.py <主播unique_id>
```

## 使用示例

### 基本用法

```bash
python main.py some_creator
```

输出示例：
```
[system] Connecting to @some_creator...
[system] Connected to @some_creator
[14:23:01] [comment] Alice: Hello!（你好！）
[14:23:05] [gift-queue] Bob sent Rose x3 (1 diamonds each, 3 total)
[14:23:05] [hotkey-trigger] fired 'x' x3
```

### 只监听特定礼物

```bash
python main.py some_creator --gift-names Rosa Glasses "TikTok Universe"
```

### 使用自定义提示音

```bash
python main.py some_creator --sound alert.wav
```

### 关闭评论，只显示礼物

```bash
python main.py some_creator --no-comments
```

### 礼物处理后延迟

```bash
python main.py some_creator --queue-timeout 2.0
```

### 使用 JSON 规则触发热键

```bash
python main.py some_creator --triggers '[
  {"trigger": "[default]", "action-key": "x"},
  {"trigger": "Rosa", "action-key": "c", "repeats": 3}
]'
```

## 参数详解

| 参数 | 说明 | 默认值 |
|---|---|---|
| `unique_id` | 主播 TikTok 用户名 | 必填 |
| `--gift-names` | 监听的礼物名称列表，不传则监听全部 | 全部 |
| `--sound` | 自定义提示音 `.wav` 文件路径 | 系统提示音 |
| `--no-comments` | 禁止输出评论 | 关闭 |
| `--queue-timeout` | 每次处理礼物后的冷却时间（秒） | `0.0` |
| `--triggers` | JSON 格式的规则数组（详见下文） | 关闭 |

## JSON 触发规则详解

### 格式

`--triggers` 参数接收一个 JSON 数组，每条规则包含：

- **`trigger`** (字符串，必填)：要匹配的礼物名称（不区分大小写），或 `[default]` 作为默认规则
- **`action-key`** (字符串，必填)：要触发的按键或组合键（`x`、`ctrl-v`、`alt-s` 等）
- **`repeats`** (整数，可选)：触发按键的次数；如果不填，则默认为 `task.diamonds`（礼物钻石数）

### 匹配规则

#### 1. 命名规则（按礼物名称匹配）

```json
{"trigger": "Rosa", "action-key": "x"}
```

当收到名为 "Rosa" 的礼物时，按 `x` 键（次数 = 钻石数）。

#### 2. 默认规则（`[default]`）

```json
{"trigger": "[default]", "action-key": "x"}
```

当没有任何命名规则匹配时才触发，作为后备选项。

#### 3. 多规则并发执行

同一个礼物可配置多条规则，它们会**同时并发执行**：

```json
[
  {"trigger": "Glasses", "action-key": "x"},
  {"trigger": "Glasses", "action-key": "c", "repeats": 5},
  {"trigger": "Glasses", "action-key": "ctrl-v", "repeats": 1}
]
```

接收 "Glasses" 礼物（假设 3 钻石）时：
- 按 `x` **3 次**（默认 diamonds）
- 按 `c` **5 次**（固定值）
- 按 `ctrl+v` **1 次**（固定值）
- 这三个操作**同时发生**

### 规则优先级与互斥

- **优先级**：命名规则 > 默认规则
- **互斥逻辑**：
  - 如果某个礼物有命名规则匹配，**只执行命名规则**，默认规则不触发
  - 如果没有命名规则匹配，**执行所有默认规则**
  
**示例场景：**

```json
[
  {"trigger": "[default]", "action-key": "x"},
  {"trigger": "Rosa", "action-key": "c"},
  {"trigger": "Glasses", "action-key": "d"},
  {"trigger": "Glasses", "action-key": "a"}
]
```

- 收到 "Rosa" → 按 `c`（匹配命名规则，跳过默认规则）
- 收到 "Glasses" → 按 `d` 和 `a`（同时执行两个并发规则）
- 收到 "Rose" → 按 `x`（无命名规则，执行默认规则）

## 按键语法

支持以下按键指定方式：

```
单个按键：
  x, a, 1, space, enter, tab, esc, insert, delete, home, end, page_up, page_down

功能键：
  f1, f2, ..., f12

修饰键组合（用 - 或 + 连接）：
  ctrl-v 或 ctrl+v
  alt-s  或 alt+s
  shift-a 或 shift+a
  ctrl-alt-d 或 ctrl+alt+d
```

## 实际应用案例

### 场景 1：简单的一键应答

当有人送礼物时，自动按 `x` 键回应：

```json
[
  {"trigger": "[default]", "action-key": "x"}
]
```

### 场景 2：不同礼物不同反应

```json
[
  {"trigger": "Rosa", "action-key": "a"},
  {"trigger": "Galaxy", "action-key": "b"},
  {"trigger": "[default]", "action-key": "x"}
]
```

- Rosa → `a`
- Galaxy → `b`
- 其他 → `x`

### 场景 3：同礼物多按键并发

```json
[
  {"trigger": "Glasses", "action-key": "a"},
  {"trigger": "Glasses", "action-key": "b"},
  {"trigger": "Glasses", "action-key": "c", "repeats": 10}
]
```

收到 Glasses（3 钻石）时：
- 同时按 `a` 3 次、`b` 3 次、`c` 10 次

### 场景 4：主播用剧本

```json
[
  {"trigger": "Rosa", "action-key": "ctrl-alt-1", "repeats": 1},
  {"trigger": "Glasses", "action-key": "ctrl-alt-2", "repeats": 1},
  {"trigger": "Phoenix", "action-key": "ctrl-alt-3", "repeats": 1}
]
```

每个礼物触发一个快捷键宏（使用 AutoHotkey 之类的工具响应）。

## 故障排查

### 问题：脚本打开时闪过错误

**原因**：PowerShell 执行策略限制。

**解决**：
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
Unblock-File .\scripts\run_win10.ps1
```

### 问题：收不到礼物事件

**原因**：主播不在直播或网络问题。

**检查**：
```bash
python main.py your_creator --no-comments
```

如果显示 `is not live right now`，需要等待主播开播。

### 问题：热键不触发

**原因**：
1. 规则 JSON 格式错误 → 查看控制台 `Invalid --triggers` 错误
2. 按键组合格式不对 → 参考【按键语法】部分
3. 权限不足 → 某些应用需要以管理员身份运行

**调试**：
```bash
python main.py your_creator --no-comments --triggers '[
  {"trigger": "[default]", "action-key": "x"}
]'
```

查看控制台是否显示 `Loaded N trigger rule(s)`。

## 注意事项

- **主播必须直播** — 目标主播必须处于直播状态，否则会立即退出
- **Windows 独占功能** — 声音提醒（`winsound`）和热键触发（`pynput`）仅在 Windows 上可用，其他平台会跳过
- **翻译需要网络** — 使用 Google 免费翻译接口，需要网络连接；如果无法连接会显示原文
- **权限提升** — 某些游戏或应用可能需要以**管理员身份**运行此脚本才能响应热键
- **控制台编码** — `run_win10.ps1` 自动处理 UTF-8 编码，用户通常无需干预

