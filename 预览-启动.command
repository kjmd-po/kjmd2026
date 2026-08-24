#!/bin/bash
# ---------------------------------------------------------------------------
# KJMD 2026 — start a local preview.
# Double-click this file in Finder. Close it with 预览-关闭.command
# ---------------------------------------------------------------------------

cd "$(dirname "$0")" || exit 1
PORT=4000
URL="http://localhost:${PORT}/kjmd2026/"

printf '\033]0;KJMD 2026 preview\007'
echo "════════════════════════════════════════════"
echo "  KJMD 2026 — 本地预览"
echo "════════════════════════════════════════════"
echo

# --- already running? ------------------------------------------------------
if lsof -nP -iTCP:${PORT} -sTCP:LISTEN >/dev/null 2>&1; then
  echo "预览已经在运行了。"
  echo "地址: ${URL}"
  open "${URL}"
  echo
  echo "（要重启，请先运行 预览-关闭.command）"
  echo
  read -n 1 -s -r -p "按任意键关闭本窗口…"
  exit 0
fi

# --- find a Ruby new enough for Jekyll -------------------------------------
# The system Ruby is 2.6, which modern Jekyll no longer supports.
RUBY_BIN=""
for candidate in /opt/homebrew/opt/ruby/bin /usr/local/opt/ruby/bin; do
  if [ -x "$candidate/ruby" ]; then RUBY_BIN="$candidate"; break; fi
done

if [ -z "$RUBY_BIN" ]; then
  echo "本地还没有可用于 Jekyll 的 Ruby（系统自带的 2.6 版本太旧）。"
  echo
  echo "  [1] 安装 Ruby + Jekyll，跑真正的 Jekyll 预览"
  echo "      —— 与 GitHub Pages 完全一致，首次约需 5-10 分钟"
  echo "  [2] 用简易预览（立即可用）"
  echo "      —— 页面外观一致，但由脚本渲染，非 Jekyll 本身"
  echo
  read -r -p "请选择 [1/2]: " choice
  echo

  if [ "$choice" = "1" ]; then
    echo "正在安装 Ruby（通过 Homebrew）…"
    if ! brew install ruby; then
      echo "Ruby 安装失败，改用简易预览。"
      choice=2
    else
      for candidate in /opt/homebrew/opt/ruby/bin /usr/local/opt/ruby/bin; do
        if [ -x "$candidate/ruby" ]; then RUBY_BIN="$candidate"; break; fi
      done
    fi
  fi
fi

# --- Jekyll path -----------------------------------------------------------
if [ -n "$RUBY_BIN" ] && [ "$choice" != "2" ]; then
  export PATH="$RUBY_BIN:$PATH"
  export GEM_HOME="$HOME/.gem/kjmd"
  export PATH="$GEM_HOME/bin:$PATH"

  if ! command -v bundle >/dev/null 2>&1; then
    echo "正在安装 bundler…"
    gem install bundler --no-document || exit 1
  fi

  if [ ! -f Gemfile.lock ] || [ Gemfile -nt Gemfile.lock ]; then
    echo "正在安装依赖（首次较慢，请耐心等待）…"
    bundle install || {
      echo
      echo "依赖安装失败。可以改用简易预览：重新运行本脚本并选择 [2]。"
      read -n 1 -s -r -p "按任意键关闭…"
      exit 1
    }
  fi

  echo
  echo "启动 Jekyll…  地址: ${URL}"
  echo "关闭预览：运行 预览-关闭.command，或在本窗口按 Control-C"
  echo "────────────────────────────────────────────"
  echo

  ( sleep 4; open "${URL}" ) &
  exec bundle exec jekyll serve --port ${PORT} --livereload --host 127.0.0.1
fi

# --- Fallback: lightweight renderer ---------------------------------------
echo "使用简易预览。"
echo

if ! python3 -c "import liquid, yaml" >/dev/null 2>&1; then
  echo "正在安装渲染所需的 Python 组件…"
  python3 -m pip install --quiet python-liquid pyyaml || {
    echo "安装失败。"
    read -n 1 -s -r -p "按任意键关闭…"
    exit 1
  }
fi

python3 preview/render.py || {
  echo
  echo "渲染失败，请把上面的错误信息发给 Claude。"
  read -n 1 -s -r -p "按任意键关闭…"
  exit 1
}

echo
echo "地址: ${URL}"
echo "关闭预览：运行 预览-关闭.command，或在本窗口按 Control-C"
echo "────────────────────────────────────────────"
echo
( sleep 1; open "${URL}" ) &
cd preview/_site || exit 1
exec python3 -m http.server ${PORT} --bind 127.0.0.1
