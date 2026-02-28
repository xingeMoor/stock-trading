# 模拟交易系统 - 完整使用指南

## 📋 目录

1. [快速开始](#快速开始)
2. [网页监控](#网页监控)
3. [定时任务](#定时任务)
4. [飞书通知](#飞书通知)
5. [API 测试](#api 测试)
6. [常见问题](#常见问题)

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd /Users/gexin/.openclaw/workspace/stock-trading
pip3 install -r requirements.txt
```

### 2. 配置环境变量

编辑 `.env` 文件:

```bash
nano .env
```

添加配置:

```ini
# Massive API Key
MASSIVE_API_KEY=EK2fpVUTnN02JruqyKAPkD5YPPZe7XJW

# 飞书通知 (可选)
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
FEISHU_SECRET=你的签名密钥
```

### 3. 执行模拟交易

```bash
# 单次执行
python3 main.py paper GOOGL,META,AAPL --capital 100000 --strategy optimized_v2

# 显示报告
python3 main.py paper GOOGL,META,AAPL --show-report
```

---

## 🖥️ 网页监控

### 启动服务

```bash
python3 web_dashboard.py
```

### 访问地址

打开浏览器访问：**http://localhost:5000**

### 功能

- 📊 实时资产曲线
- 💰 持仓盈亏
- 📝 交易记录
- 📈 每日收益

### 后台运行

```bash
# 使用 nohup
nohup python3 web_dashboard.py > logs/web.log 2>&1 &

# 查看日志
tail -f logs/web.log

# 停止服务
pkill -f web_dashboard.py
```

---

## ⏰ 定时任务

### 方案 1: 使用脚本循环模式

```bash
# 每小时执行一次 (交易时间内)
python3 scheduled_trading.py --interval 60
```

### 方案 2: 使用系统 cron

编辑 crontab:

```bash
crontab -e
```

添加任务 (美股交易时间，每小时):

```cron
# 美股交易时段 (北京时间 21:30 - 次日 4:00)
30 21 * * 1-5 cd /Users/gexin/.openclaw/workspace/stock-trading && python3 scheduled_trading.py --once >> logs/scheduled.log 2>&1
0 22 * * 1-5 cd /Users/gexin/.openclaw/workspace/stock-trading && python3 scheduled_trading.py --once >> logs/scheduled.log 2>&1
0 23 * * 1-5 cd /Users/gexin/.openclaw/workspace/stock-trading && python3 scheduled_trading.py --once >> logs/scheduled.log 2>&1
0 0 * * 1-5 cd /Users/gexin/.openclaw/workspace/stock-trading && python3 scheduled_trading.py --once >> logs/scheduled.log 2>&1
0 1 * * 1-5 cd /Users/gexin/.openclaw/workspace/stock-trading && python3 scheduled_trading.py --once >> logs/scheduled.log 2>&1
0 2 * * 1-5 cd /Users/gexin/.openclaw/workspace/stock-trading && python3 scheduled_trading.py --once >> logs/scheduled.log 2>&1
0 3 * * 1-5 cd /Users/gexin/.openclaw/workspace/stock-trading && python3 scheduled_trading.py --once >> logs/scheduled.log 2>&1
```

### 查看定时任务日志

```bash
tail -f logs/scheduled.log
```

---

## 📱 飞书通知

### 配置步骤

详见 [FEISHU_SETUP.md](FEISHU_SETUP.md)

### 快速配置

1. 飞书群 → 设置 → 群机器人 → 添加自定义机器人
2. 复制 webhook 地址
3. 编辑 `.env` 文件，添加 `FEISHU_WEBHOOK`

### 测试通知

```bash
python3 src/feishu_notification.py
```

---

## 🧪 API 测试

### 测试所有 Massive API

```bash
python3 test_massive_api.py
```

### 测试实时股价查询

```bash
python3 src/realtime_price.py
```

### 测试数据库

```bash
python3 src/trading_db.py
```

---

## 📁 目录结构

```
stock-trading/
├── main.py                      # 主入口
├── web_dashboard.py             # 网页监控服务
├── scheduled_trading.py         # 定时交易任务
├── test_massive_api.py          # API 测试脚本
├── requirements.txt             # Python 依赖
├── .env                         # 环境变量 (不提交)
├── .env.example                 # 环境变量模板
├── data/
│   ├── trading.db              # SQLite 数据库
│   └── scheduled_runs/         # 定时任务报告
├── src/
│   ├── massive_api.py          # Massive API 封装
│   ├── paper_trading.py        # 模拟交易运行器
│   ├── trading_db.py           # 数据库管理
│   ├── realtime_price.py       # 实时股价查询
│   └── feishu_notification.py  # 飞书通知
└── strategies/
    ├── relaxed_strategy.py     # 宽松策略
    └── optimized_v2_strategy.py # 优化策略 V2
```

---

## 🎯 典型使用流程

### 盘前准备 (21:00)

```bash
# 1. 启动网页监控
python3 web_dashboard.py &

# 2. 检查市场状态
python3 main.py status

# 3. 测试 API
python3 test_massive_api.py
```

### 盘中执行 (21:30 - 04:00)

```bash
# 自动定时任务 (已配置 cron)
# 或使用循环模式
python3 scheduled_trading.py --interval 60
```

### 盘后复盘 (次日)

```bash
# 1. 查看网页报告
# 访问 http://localhost:5000

# 2. 导出交易记录
sqlite3 data/trading.db "SELECT * FROM trades ORDER BY trade_date DESC;"

# 3. 查看定时任务日志
tail -f logs/scheduled.log
```

---

## 📊 数据库查询示例

### 查看所有交易

```bash
sqlite3 data/trading.db "SELECT * FROM trades ORDER BY trade_date DESC LIMIT 20;"
```

### 查看持仓

```bash
sqlite3 data/trading.db "SELECT * FROM positions;"
```

### 查看每日快照

```bash
sqlite3 data/trading.db "SELECT * FROM daily_snapshots ORDER BY snapshot_date DESC LIMIT 30;"
```

### 导出 CSV

```bash
sqlite3 -header -csv data/trading.db "SELECT * FROM trades;" > trades.csv
```

---

## ⚠️ 注意事项

### 1. Massive API 限制

- **数据延迟**: 15 分钟
- **解决方案**: 使用 `realtime_price.py` 查询实时股价作为参考

### 2. 数据库备份

```bash
# 每周备份
cp data/trading.db data/trading.db.backup.$(date +%Y%m%d)
```

### 3. 日志轮转

```bash
# 防止日志文件过大
find logs/ -name "*.log" -size +10M -exec mv {} {}.old \;
```

### 4. 服务监控

```bash
# 检查网页服务是否运行
ps aux | grep web_dashboard

# 检查定时任务
crontab -l
```

---

## 🔧 故障排查

### 网页无法访问

```bash
# 检查端口
lsof -i :5000

# 重启服务
pkill -f web_dashboard
python3 web_dashboard.py &
```

### 定时任务未执行

```bash
# 检查 cron 日志
grep CRON /var/log/system.log | tail -20

# 手动执行测试
python3 scheduled_trading.py --once
```

### 飞书通知失败

```bash
# 测试 webhook
curl -X POST "你的 webhook 地址" \
  -H "Content-Type: application/json" \
  -d '{"msg_type":"text","content":{"text":"test"}}'
```

---

## 📞 支持

- **GitHub**: https://github.com/xingeMoor/stock-trading
- **文档**: 查看各模块的注释和说明

---

**版本**: 5.0.0  
**更新时间**: 2026-02-28  
**初始资金**: $100,000
