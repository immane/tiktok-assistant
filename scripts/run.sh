#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# User Config Section
# ============================================================================

# Python executable. Examples:
# - python3
# - /home/user/.pyenv/shims/python
# - ../.venv/bin/python
TTA_PYTHON="python3"

# Entry script path.
# Usually keep this as ../main.py when run.sh is in scripts/.
TTA_ENTRY="../main.py"

# TikTok unique_id (without @)
TTA_UNIQUE_ID="some_creator_id"

# Other options
TTA_SOUND=""
TTA_QUEUE_TIMEOUT="0"
TTA_NO_COMMENTS="false"
TTA_LIKES_THRESHOLD="500"
TTA_LIKES_TRIGGER_KEY="z"

# Embedded JSON rules. Edit only JSON content between BEGIN/END markers.
# Keep valid JSON array format.
# Example behavior:
# - Rose: triggers x, c, ctrl-v (concurrently)
# - Rosa / Glasses: triggers v fixed 5 times
# - Other gifts: default x

# TTA_TRIGGERS_JSON_BEGIN
# [
#   {"trigger":"Rose","action-key":"x"},
#   {"trigger":"Rose","action-key":"c"},
#   {"trigger":"Rose","action-key":"ctrl-v","repeats":2},
#   {"trigger":"Rosa","action-key":"v","repeats":5},
#   {"trigger":"Glasses","action-key":"v","repeats":5},
#   {"trigger":"[default]","action-key":"x"}
# ]
# TTA_TRIGGERS_JSON_END

# ============================================================================
# Do not modify below unless needed
# ============================================================================

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

resolve_path() {
  local p="$1"
  if [[ "$p" = /* ]]; then
    printf "%s" "$p"
  else
    printf "%s/%s" "$SCRIPT_DIR" "$p"
  fi
}

ENTRY_PATH="$(resolve_path "$TTA_ENTRY")"
PYTHON_CMD="$TTA_PYTHON"
if [[ "$TTA_PYTHON" == */* && "$TTA_PYTHON" != /* ]]; then
  PYTHON_CMD="$(resolve_path "$TTA_PYTHON")"
fi

if [[ ! -f "$ENTRY_PATH" ]]; then
  echo "[system] Entry script not found: $ENTRY_PATH"
  exit 1
fi

if [[ -z "${TTA_UNIQUE_ID}" ]]; then
  echo "[system] Config requires unique_id"
  exit 1
fi

TTA_TRIGGERS_JSON="$({
  awk '
    /^# TTA_TRIGGERS_JSON_BEGIN$/ {capture=1; next}
    /^# TTA_TRIGGERS_JSON_END$/ {capture=0}
    capture {
      sub(/^#[[:space:]]?/, "", $0)
      print $0
    }
  ' "$0"
})"

if [[ -z "$TTA_TRIGGERS_JSON" ]]; then
  echo "[system] Config requires triggers array"
  exit 1
fi

echo "[system] Running with embedded JSON config..."

cmd=(
  "$PYTHON_CMD" "$ENTRY_PATH" "$TTA_UNIQUE_ID"
  "--queue-timeout" "$TTA_QUEUE_TIMEOUT"
  "--triggers" "$TTA_TRIGGERS_JSON"
  "--likes-threshold" "$TTA_LIKES_THRESHOLD"
)

if [[ -n "$TTA_LIKES_TRIGGER_KEY" ]]; then
  cmd+=("--likes-trigger-key" "$TTA_LIKES_TRIGGER_KEY")
fi

if [[ "${TTA_NO_COMMENTS,,}" == "true" ]]; then
  cmd+=("--no-comments")
fi

if [[ -n "$TTA_SOUND" ]]; then
  cmd+=("--sound" "$TTA_SOUND")
fi

cmd+=("$@")

"${cmd[@]}"
