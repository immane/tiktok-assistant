param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PassthroughArgs
)
$ErrorActionPreference = "Stop"

# ============================================================================
# 【用户配置区】可以修改以下内容
# ============================================================================

# EXE 路径（修改这里）
# 可选：绝对路径 或 相对路径（相对于本脚本所在目录）
# 例子：绝对路径 "D:\Development\Python\tiktok-assistant\dist\tiktok-assistant.exe"
#      相对路径 "..\dist\tiktok-assistant.exe"
$exePath = "..\dist\tiktok-assistant.exe"

# 自定义规则配置 JSON（修改这里）
$configJson = @'
{
  "unique_id": "some_creator_id",
  "triggers": [
    {"trigger": "Rose", "action-key": "x"},
    {"trigger": "Rose", "action-key": "c"},
    {"trigger": "Rose", "action-key": "ctrl-v", "repeats": 2},
    {"trigger": "Rosa", "action-key": "v", "repeats": 5},
    {"trigger": "Glasses", "action-key": "v", "repeats": 5},

    {"trigger": "[default]", "action-key": "x"}
  ],

  "sound": "",
  "queue_timeout": 0,
  "no_comments": false
}
'@

# ============================================================================
# ❌ 不要修改以下代码
# ============================================================================

# Resolve exe path: handle both absolute and relative paths
if (-not [System.IO.Path]::IsPathRooted($exePath)) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $exePath = Join-Path $scriptDir $exePath
}
$exePath = Resolve-Path -LiteralPath $exePath -ErrorAction Stop

# Set console to black background with white text (not Win10 default blue).
$Host.UI.RawUI.BackgroundColor = "Black"
$Host.UI.RawUI.ForegroundColor = "White"
Clear-Host

# Improve UTF-8 behavior on Windows console without changing application code.
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

if (-not (Test-Path -LiteralPath $exePath)) {
    throw "Executable not found: $exePath"
}

$cfg = $configJson | ConvertFrom-Json

if (-not $cfg.unique_id) {
    throw "Config requires unique_id"
}
if (-not $cfg.triggers) {
    throw "Config requires triggers array"
}

$triggersJson = $cfg.triggers | ConvertTo-Json -Compress
# PowerShell strips inner quotes for native commands unless they are escaped.
$triggersArg = $triggersJson.Replace('"', '\"')

$exeArgs = @(
    [string]$cfg.unique_id,
    "--queue-timeout", [string]$cfg.queue_timeout,
    "--triggers", $triggersArg
)
if ($cfg.no_comments) {
    $exeArgs += "--no-comments"
}
if ($cfg.sound -and $cfg.sound.Trim().Length -gt 0) {
    $exeArgs += @("--sound", [string]$cfg.sound)
}
if ($PassthroughArgs -and $PassthroughArgs.Count -gt 0) {
    $exeArgs += $PassthroughArgs
}

Write-Host "[system] Running with embedded JSON config..."
& $exePath @exeArgs
exit $LASTEXITCODE
