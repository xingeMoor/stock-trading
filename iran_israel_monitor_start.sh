#!/bin/bash
# 伊朗 - 以色列冲突舆情监控 - 后台启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/logs/iran_israel_monitor_$(date +%Y%m%d_%H%M%S).log"
PID_FILE="$SCRIPT_DIR/logs/iran_israel_monitor.pid"

echo "🚀 伊朗 - 以色列冲突舆情监控系统启动"
echo "========================================"
echo "工作目录：$SCRIPT_DIR"
echo "日志文件：$LOG_FILE"
echo "PID 文件：$PID_FILE"
echo ""

# 检查是否已在运行
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "⚠️  监控系统已在运行 (PID: $OLD_PID)"
        echo "   如需重启，先执行：kill $OLD_PID"
        exit 1
    else
        echo "⚠️  发现残留 PID 文件，清理中..."
        rm -f "$PID_FILE"
    fi
fi

# 确保日志目录存在
mkdir -p "$SCRIPT_DIR/logs"

# 启动监控进程
echo "📡 启动监控进程..."
cd "$SCRIPT_DIR"
nohup python3 iran_israel_sentiment_monitor.py > "$LOG_FILE" 2>&1 &
NEW_PID=$!

echo $NEW_PID > "$PID_FILE"

echo ""
echo "✅ 监控系统已启动"
echo "   PID: $NEW_PID"
echo "   日志：tail -f $LOG_FILE"
echo ""
echo "📊 查看状态：./iran_israel_monitor_status.sh"
echo "🛑 停止监控：./iran_israel_monitor_stop.sh"
echo ""

# 等待 3 秒检查进程是否正常
sleep 3
if ps -p $NEW_PID > /dev/null 2>&1; then
    echo "✅ 进程运行正常"
else
    echo "❌ 进程启动失败，请检查日志：$LOG_FILE"
    exit 1
fi
