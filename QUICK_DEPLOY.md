# Q脑系统 - 快速部署命令
# 复制以下命令到阿里云服务器终端执行

# 1. 进入部署目录
mkdir -p /opt/qbrain && cd /opt/qbrain

# 2. 拉取最新代码
if [ ! -d .git ]; then
    git clone https://github.com/xingeMoor/stock-trading.git .
else
    git pull origin main
fi

# 3. 创建并激活conda环境
conda create -n qbrain python=3.10 -y
source $(conda info --base)/etc/profile.d/conda.sh
conda activate qbrain

# 4. 安装依赖
pip install flask pandas numpy requests python-dotenv apscheduler plotly akshare yfinance beautifulsoup4 lxml schedule

# 5. 创建日志目录
mkdir -p logs

# 6. 启动所有服务
cd /opt/qbrain

# 5001: 模拟交易监控
cd stock-trading && nohup python3 web_dashboard.py > ../logs/web_dashboard.log 2>&1 &
cd ..

# 5002: 策略管理
nohup python3 strategy_manager.py > logs/strategy_manager.log 2>&1 &

# 5005: 回测分析
cd stock-trading && nohup python3 backtest_dashboard_v2.py > ../logs/backtest_dashboard.log 2>&1 &
cd ..

# 5006: 系统状态监控
cd stock-trading && nohup python3 system_status_dashboard.py > ../logs/system_status_dashboard.log 2>&1 &
cd ..

# 5007: Agent管理面板
nohup python3 agent_dashboard_v2.py > logs/agent_dashboard.log 2>&1 &

# 5008: 项目管理Dashboard
nohup python3 project_dashboard.py > logs/project_dashboard.log 2>&1 &

# 5009: 舆情监控
nohup python3 sentiment_dashboard.py > logs/sentiment_dashboard.log 2>&1 &

# 7. 等待服务启动
sleep 5

# 8. 检查服务状态
echo "🔍 检查服务状态..."
for port in 5001 5002 5005 5006 5007 5008 5009; do
    if curl -s http://localhost:$port > /dev/null 2>&1; then
        echo "✅ 端口 $port - 运行正常"
    else
        echo "❌ 端口 $port - 未响应"
    fi
done

echo ""
echo "🎉 部署完成!"
echo "访问地址:"
echo "  http://47.253.133.165:5001 - 模拟交易"
echo "  http://47.253.133.165:5002 - 策略管理"
echo "  http://47.253.133.165:5005 - 回测分析"
echo "  http://47.253.133.165:5006 - 系统监控"
echo "  http://47.253.133.165:5007 - Agent管理"
echo "  http://47.253.133.165:5008 - 项目管理"
echo "  http://47.253.133.165:5009 - 舆情监控"
