#!/bin/bash
# 量化交易系统部署脚本

echo "🚀 开始部署 Quant Trading Pro"
echo "================================"

# 检查Python环境
echo "📦 检查Python环境..."
python3 --version || exit 1

# 安装依赖
echo "📦 安装依赖..."
pip3 install -q flask pandas numpy akshare requests python-dotenv

# 创建数据目录
echo "📁 创建数据目录..."
mkdir -p data/cache data/backtest_results logs

# 测试核心模块
echo "🧪 测试核心模块..."
python3 -c "
import sys
sys.path.insert(0, 'src')

# 测试数据接口
try:
    from data_provider import DataProvider
    print('✅ DataProvider 加载成功')
except Exception as e:
    print(f'⚠️  DataProvider: {e}')

# 测试选股引擎
try:
    from stock_selector import StockSelector
    print('✅ StockSelector 加载成功')
except Exception as e:
    print(f'⚠️  StockSelector: {e}')

# 测试Polymarket
try:
    from polymarket_sentiment import PolymarketSentiment
    print('✅ PolymarketSentiment 加载成功')
except Exception as e:
    print(f'⚠️  PolymarketSentiment: {e}')
"

# 启动Web服务
echo ""
echo "🌐 启动Web服务..."
echo "访问地址:"
echo "  - 模拟交易: http://localhost:5001"
echo "  - 回测分析: http://localhost:5002"
echo "  - 实盘持仓: http://localhost:5003"
echo "  - 定时任务: http://localhost:5004"
echo ""

# 后台启动所有服务
nohup python3 web_dashboard.py > logs/web.log 2>&1 &
nohup python3 backtest_dashboard.py > logs/backtest.log 2>&1 &
nohup python3 real_positions_dashboard.py > logs/positions.log 2>&1 &
nohup python3 schedule_dashboard.py > logs/schedule.log 2>&1 &

echo "✅ 所有服务已启动"
echo ""
echo "查看日志: tail -f logs/*.log"
echo "停止服务: pkill -f dashboard.py"
