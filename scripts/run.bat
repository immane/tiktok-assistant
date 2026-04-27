@echo off
setlocal EnableExtensions EnableDelayedExpansion

:: ============================================================================
:: 【用户配置区】可以修改以下内容
:: ============================================================================

:: EXE 路径（修改这里）
:: 可选：绝对路径 或 相对路径（相对于本脚本所在目录）
:: 例子：绝对路径 "D:\Development\Python\tiktok-assistant\dist\tiktok-assistant.exe"
::      相对路径 "..\dist\tiktok-assistant.exe"
set TTA_EXE_PATH=..\dist\tiktok-assistant.exe

:: 自定义规则配置 JSON（修改这里）
::
:: 字段说明：
:: 1) unique_id
::    - 直播间用户名（不带 @），例如: "some_creator_id"
::
:: 2) triggers (规则数组)
::    每条规则包含：
::    - trigger: 要匹配的礼物名；使用 "[default]" 表示默认兜底规则
::    - action-key: 要触发的按键，支持：
::      x / enter / tab / esc / f1~f12 / ctrl-v / ctrl+v / ctrl-alt-d 等
::    - repeats (可选): 固定触发次数；不写时默认使用“礼物钻石数”
::
:: 匹配逻辑（非常重要）：
:: - 命名规则（如 "Rose" / "Glasses"）优先级高于 [default]
:: - 如果某个礼物匹配到命名规则：只执行命名规则（可多条并发）
:: - 如果没匹配到命名规则：执行 [default] 规则
::
:: 下面示例含义：
:: - Rose 到来：按 x、c、ctrl-v（并发执行）
:: - Rosa / Glasses 到来：按 v（固定 5 次）
:: - 其他礼物：按 x（由 [default] 兜底）
::
:: 其他配置：
:: - sound: 留空使用系统提示音；填写 .wav 路径使用自定义声音
:: - queue_timeout: 每个礼物处理完后的延迟秒数，0 表示不延迟
:: - no_comments: true=不显示评论，false=显示评论

set TTA_UNIQUE_ID=some_creator_id

:: 多行规则配置（下面这一段就是标准 JSON，普通用户可直接编辑）
:: 注意：
:: 1) 除最后一条规则外，其它规则行末尾保留逗号
:: 2) 只修改 JSON 内容，不要删除 BEGIN/END 标记行

goto after_triggers_json
:: TTA_TRIGGERS_JSON_BEGIN
[
  {"trigger":"Rose","action-key":"x"},
  {"trigger":"Rose","action-key":"c"},
  {"trigger":"Rose","action-key":"ctrl-v","repeats":2},
  {"trigger":"Rosa","action-key":"v","repeats":5},
  {"trigger":"Glasses","action-key":"v","repeats":5},
  {"trigger":"[default]","action-key":"x"}
]
:: TTA_TRIGGERS_JSON_END
:after_triggers_json

set TTA_SOUND=
set TTA_QUEUE_TIMEOUT=0
set TTA_NO_COMMENTS=false

:: ============================================================================
:: ❌ 不要修改以下代码
:: ============================================================================

set "SCRIPT_DIR=%~dp0"
set "EXE_PATH=%TTA_EXE_PATH%"

if /I "%EXE_PATH:~0,2%"=="\\" goto exe_resolved
if "%EXE_PATH:~1,1%"==":" goto exe_resolved
set "EXE_PATH=%SCRIPT_DIR%%EXE_PATH%"

:exe_resolved
chcp 65001 >nul
color 0F
cls

if not exist "%EXE_PATH%" (
  echo [system] Executable not found: "%EXE_PATH%"
  exit /b 1
)

if "%TTA_UNIQUE_ID%"=="" (
  echo [system] Config requires unique_id
  exit /b 1
)

set "TTA_TRIGGERS_JSON="
set "TTA_CAPTURE="
for /f "usebackq delims=" %%L in ("%~f0") do (
  set "TTA_LINE=%%L"
  if defined TTA_CAPTURE (
    if "!TTA_LINE!"==":: TTA_TRIGGERS_JSON_END" (
      set "TTA_CAPTURE="
    ) else (
      if defined TTA_TRIGGERS_JSON (
        set "TTA_TRIGGERS_JSON=!TTA_TRIGGERS_JSON!!TTA_LINE!"
      ) else (
        set "TTA_TRIGGERS_JSON=!TTA_LINE!"
      )
    )
  ) else (
    if "!TTA_LINE!"==":: TTA_TRIGGERS_JSON_BEGIN" set "TTA_CAPTURE=1"
  )
)

if "%TTA_TRIGGERS_JSON%"=="" (
  echo [system] Config requires triggers array
  exit /b 1
)

set "TTA_TRIGGERS_ARG=!TTA_TRIGGERS_JSON:"=\"!"

echo [system] Running with embedded JSON config...

if /I "%TTA_NO_COMMENTS%"=="true" (
  if "%TTA_SOUND%"=="" (
    "%EXE_PATH%" "%TTA_UNIQUE_ID%" --queue-timeout "%TTA_QUEUE_TIMEOUT%" --triggers "%TTA_TRIGGERS_ARG%" --no-comments %*
  ) else (
    "%EXE_PATH%" "%TTA_UNIQUE_ID%" --queue-timeout "%TTA_QUEUE_TIMEOUT%" --triggers "%TTA_TRIGGERS_ARG%" --no-comments --sound "%TTA_SOUND%" %*
  )
) else (
  if "%TTA_SOUND%"=="" (
    "%EXE_PATH%" "%TTA_UNIQUE_ID%" --queue-timeout "%TTA_QUEUE_TIMEOUT%" --triggers "%TTA_TRIGGERS_ARG%" %*
  ) else (
    "%EXE_PATH%" "%TTA_UNIQUE_ID%" --queue-timeout "%TTA_QUEUE_TIMEOUT%" --triggers "%TTA_TRIGGERS_ARG%" --sound "%TTA_SOUND%" %*
  )
)

exit /b %ERRORLEVEL%
