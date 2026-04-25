# TikTok Live Assistant

一个轻量级的 TikTok 直播命令行助手，实时显示评论（附中文翻译）、监听礼物事件并触发声音提醒。

> English version: [README.md](README.md)

## 功能

- **实时评论** — 在终端实时打印直播间评论，自动附上中文翻译
- **礼物监听** — 检测直播间收到的礼物并放入异步队列处理
- **声音提醒** — 收到礼物时触发系统提示音或自定义 `.wav` 文件
- **礼物过滤** — 可指定只监听特定礼物名称
- **优雅退出** — `Ctrl+C` 安全关闭，清理所有异步任务

## 项目结构

```
tiktok-assistant/
├── main.py            # 启动入口、参数解析、连接生命周期管理
├── event_handlers.py  # TikTok 事件回调（评论、礼物、连接状态）
├── gift_queue.py      # 礼物队列消费、声音播放
└── requirements.txt   # 依赖声明
```

## 依赖

- Python 3.11+
- [TikTokLive](https://github.com/isaackogan/TikTokLive) — TikTok 直播 WebSocket 连接
- [deep-translator](https://github.com/nidhaloff/deep-translator) — Google 翻译（无需 API Key）

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
```

## 使用

### 基本用法

```bash
python main.py <主播unique_id>
```

```
[system] Connecting to @some_creator...
[system] Connected to @some_creator
[14:23:01] [comment] Alice: Hello!（你好！）
[14:23:05] [gift-detected] queued -> Bob sent Rose x3 (1 diamonds each, 3 total)
[14:23:05] [gift-queue] Bob sent Rose x3 (1 diamonds each, 3 total)
```

### 只监听特定礼物

```bash
python main.py some_creator --gift-names Rose Galaxy "TikTok Universe"
```

### 使用自定义提示音

```bash
python main.py some_creator --sound alert.wav
```

### 关闭评论，只显示礼物

```bash
python main.py some_creator --no-comments
```

### 礼物处理后延迟（秒）

```bash
python main.py some_creator --queue-timeout 2.0
```

## 参数说明

| 参数 | 说明 | 默认值 |
|---|---|---|
| `unique_id` | 主播 TikTok 用户名 | 必填 |
| `--gift-names` | 监听的礼物名称列表，不传则监听全部 | 全部 |
| `--sound` | 自定义提示音 `.wav` 文件路径 | 系统提示音 |
| `--no-comments` | 禁止输出评论 | 关闭 |
| `--queue-timeout` | 每次处理礼物后的冷却时间（秒） | `0.0` |

## 注意事项

- 目标主播必须**正在直播**，否则会提示 `is not live right now` 后退出
- 声音提醒仅支持 Windows（`winsound`），其他平台会跳过播放
- 翻译通过 Google 免费接口，无需配置任何 Key，但依赖网络连通性
