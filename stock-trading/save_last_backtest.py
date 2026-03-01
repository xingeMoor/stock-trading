#!/usr/bin/env python3
"""
将最后一次回测结果保存到数据库
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import json
from datetime import datetime
from backtest_db import BacktestDatabase

# 读取最新的回测结果文件 (live_backtest开头的)
results_dir = os.path.join(os.path.dirname(__file__), 'data', 'backtest_results')
json_files = [f for f in os.listdir(results_dir) if f.startswith('live_backtest') and f.endswith('.json')]
json_files.sort(reverse=True)

if not json_files:
    print("❌ 未找到回测结果文件")
    exit(1)

latest_file = os.path.join(results_dir, json_files[0])
print(f"📂 读取文件: {latest_file}")

with open(latest_file, 'r') as f:
    report = json.load(f)

# 保存到数据库
db = BacktestDatabase()

batch_id = f"live_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

success = db.save_backtest_batch(
    batch_id=batch_id,
    name="美股大规模回测-真实数据",
    strategy_name="MA_Crossover_RSI",
    market="US",
    start_date=report['meta']['start_date'],
    end_date=report['meta']['end_date'],
    results=report['all_results'],
    description="使用Massive API真实数据，110只美股，2024-2026两年回测",
    strategy_params={
        "ma_fast": 5,
        "ma_slow": 20,
        "rsi_period": 14,
        "rsi_buy_threshold": 70,
        "rsi_sell_threshold": 80
    }
)

if success:
    print(f"\n✅ 回测结果已保存到数据库")
    print(f"   批次ID: {batch_id}")
    print(f"\n💡 启动前端查看:")
    print(f"   python backtest_dashboard_v2.py")
else:
    print("❌ 保存失败")
