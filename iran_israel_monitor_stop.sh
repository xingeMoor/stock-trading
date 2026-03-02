#!/bin/bash
# 伊朗 - 以色列冲突舆情监控 - 停止脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/logs/iran_israel_monitor.pid"

echo "🛑 停止伊朗 - 以色列冲突舆情监控系统"
echo "========================================"

if [ ! -f "$PID_FILE" ]; then
    echo "⚠️  未找到 PID 文件，监控系统可能未运行"
    exit 0
fi

PID=$(cat "$PID_FILE")

if ps -p $PID > /dev/null 2>&1; then
    echo "📡 正在停止进程 (PID: $PID)..."
    kill $PID
    
    # 等待进程结束
    for i in {1..10}; do
        if ! ps -p $PID > /dev/null 2>&1; then
            echo "✅ 监控系统已停止"
            rm -f "$PID_FILE"
            exit 0
        fi
        sleep 1
    done
    
    # 如果还没停止，强制终止
    echo "⚠️  进程未响应，强制终止..."
    kill -9 $PID
    rm -f "$PID_FILE"
    echo "✅ 监控系统已强制停止"
else
    echo "⚠️  进程 (PID: $PID) 不存在，清理 PID 文件"
    rm -f "$PID_FILE"
fi
