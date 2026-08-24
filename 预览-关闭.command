#!/bin/bash
# ---------------------------------------------------------------------------
# KJMD 2026 — stop the local preview.
# ---------------------------------------------------------------------------

cd "$(dirname "$0")" || exit 1
PORT=4000

printf '\033]0;KJMD 2026 preview — stop\007'
echo "════════════════════════════════════════════"
echo "  KJMD 2026 — 关闭本地预览"
echo "════════════════════════════════════════════"
echo

PIDS=$(lsof -nP -iTCP:${PORT} -sTCP:LISTEN -t 2>/dev/null)

if [ -z "$PIDS" ]; then
  echo "预览没有在运行。"
else
  echo "正在关闭 (端口 ${PORT})…"
  # Ask politely first, then insist only if needed.
  kill $PIDS 2>/dev/null
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    sleep 0.3
    STILL=$(lsof -nP -iTCP:${PORT} -sTCP:LISTEN -t 2>/dev/null)
    [ -z "$STILL" ] && break
  done
  STILL=$(lsof -nP -iTCP:${PORT} -sTCP:LISTEN -t 2>/dev/null)
  [ -n "$STILL" ] && kill -9 $STILL 2>/dev/null

  if lsof -nP -iTCP:${PORT} -sTCP:LISTEN >/dev/null 2>&1; then
    echo "关闭失败，端口仍被占用。"
  else
    echo "已关闭。"
  fi
fi

echo
read -n 1 -s -r -p "按任意键关闭本窗口…"
