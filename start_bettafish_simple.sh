#!/bin/bash
# BettaFish 简化启动脚本
# 用于快速启动舆情报告生成服务

cd /Users/gexin/.openclaw/workspace/BettaFish

echo "🐠 BettaFish 舆情分析系统"
echo "=========================="
echo ""

# 检查 Python 版本
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python 版本：$PYTHON_VERSION"

# 检查配置文件
if [ ! -f .env ]; then
    echo "⚠️  .env 配置文件不存在，从示例创建..."
    cp .env.example .env
    echo "✅ 已创建 .env 文件，请编辑配置 API Key"
fi

# 尝试启动服务
echo ""
echo "🚀 启动 BettaFish 服务..."
echo "服务地址：http://localhost:5000"
echo "日志文件：logs/bettafish.log"
echo ""

# 后台运行
nohup python3 app.py > logs/bettafish.log 2>&1 &
PID=$!

echo "✅ BettaFish 服务已启动"
echo "进程 PID: $PID"
echo ""
echo "使用以下命令查看状态:"
echo "  ps aux | grep $PID"
echo "  tail -f logs/bettafish.log"
echo ""
echo "停止服务:"
echo "  kill $PID"
