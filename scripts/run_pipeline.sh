#!/bin/zsh

# cron 环境下也能找到 opencli。
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

PROJECT="/Users/keira/CODE_CODE/hotspot-monitor"
PYTHON="$PROJECT/venv/bin/python"
LOG="$PROJECT/logs/pipeline.log"

mkdir -p "$PROJECT/logs"
cd "$PROJECT" || exit 1

{
    echo ""
    echo "===== $(date '+%Y-%m-%d %H:%M:%S') 开始执行 ====="

    "$PYTHON" "$PROJECT/fetch.py"
    fetch_status=$?

    if [ "$fetch_status" -ne 0 ]; then
        echo "抓取失败，停止分析，退出码：$fetch_status"
        exit "$fetch_status"
    fi

    "$PYTHON" "$PROJECT/analyze.py"
    analyze_status=$?

    if [ "$analyze_status" -ne 0 ]; then
        echo "分析失败，退出码：$analyze_status"
        exit "$analyze_status"
    fi

    echo "===== 本次执行完成 ====="
} >> "$LOG" 2>&1
