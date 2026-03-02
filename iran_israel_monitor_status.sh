#!/bin/bash
# 伊朗 - 以色列冲突舆情监控 - 状态检查脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/logs/iran_israel_monitor.pid"
LOG_DIR="$SCRIPT_DIR/logs"
DB_FILE="$SCRIPT_DIR/sentiment_iran_israel_db.sqlite"

echo "📊 伊朗 - 以色列冲突舆情监控状态"
echo "========================================"
echo ""

# 检查进程状态
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ 运行状态：运行中"
        echo "   PID: $PID"
        
        # 获取进程运行时间
        ELAPSED=$(ps -o etime= -p $PID)
        echo "   运行时长：$ELAPSED"
    else
        echo "❌ 运行状态：异常 (进程不存在)"
        echo "   PID 文件残留：$PID"
    fi
else
    echo "❌ 运行状态：未运行"
fi

echo ""

# 检查日志文件
echo "📝 日志文件:"
if [ -d "$LOG_DIR" ]; then
    LOG_FILES=$(ls -t "$LOG_DIR"/*iran_israel*.log 2>/dev/null | head -3)
    if [ -n "$LOG_FILES" ]; then
        echo "$LOG_FILES" | while read log; do
            SIZE=$(ls -lh "$log" | awk '{print $5}')
            LINES=$(wc -l < "$log")
            echo "   - $(basename $log) ($SIZE, $LINES 行)"
        done
    else
        echo "   暂无日志文件"
    fi
else
    echo "   日志目录不存在"
fi

echo ""

# 检查数据库
echo "💾 数据库状态:"
if [ -f "$DB_FILE" ]; then
    SIZE=$(ls -lh "$DB_FILE" | awk '{print $5}')
    echo "   文件：sentiment_iran_israel_db.sqlite"
    echo "   大小：$SIZE"
    
    # 查询统计数据
    if command -v sqlite3 &> /dev/null; then
        TOTAL_RECORDS=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM sentiment_data;" 2>/dev/null || echo "N/A")
        TOTAL_ALERTS=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM alerts;" 2>/dev/null || echo "N/A")
        UNACK_ALERTS=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM alerts WHERE acknowledged=0;" 2>/dev/null || echo "N/A")
        
        echo "   舆情记录：$TOTAL_RECORDS 条"
        echo "   总警报数：$TOTAL_ALERTS 个"
        echo "   未处理警报：$UNACK_ALERTS 个"
    fi
else
    echo "   数据库文件不存在"
fi

echo ""

# 最近日志摘要
echo "📋 最近日志摘要:"
LATEST_LOG=$(ls -t "$LOG_DIR"/*iran_israel*.log 2>/dev/null | head -1)
if [ -n "$LATEST_LOG" ] && [ -f "$LATEST_LOG" ]; then
    echo "   最后 10 行日志:"
    tail -10 "$LATEST_LOG" | sed 's/^/   /'
else
    echo "   暂无日志"
fi

echo ""
echo "========================================"
echo "📊 查看报告：cat sentiment_iran_israel_analysis.md"
echo "🛑 停止监控：./iran_israel_monitor_stop.sh"
echo "📡 重启监控：./iran_israel_monitor_start.sh"
