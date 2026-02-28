#!/usr/bin/env python3
"""
测试 Massive API 各端点权限
找出哪些端点可用
"""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
MASSIVE_API_KEY = os.getenv('MASSIVE_API_KEY')

from massive import RESTClient
client = RESTClient(api_key=MASSIVE_API_KEY)

print("🔍 测试 Massive API 各端点权限\n")
print(f"API Key: {MASSIVE_API_KEY[:10]}...")
print("="*60)

endpoints_to_test = [
    ("市场状态", lambda: client.get_market_status()),
    ("股票列表", lambda: list(client.list_tickers(limit=5))),
    ("AAPL详情", lambda: client.get_ticker_details("AAPL")),
    ("AAPL最新交易", lambda: client.get_last_trade("AAPL")),
    ("AAPL最新报价", lambda: client.get_last_quote("AAPL")),
    ("AAPL快照", lambda: client.get_snapshot_ticker("stocks", "AAPL")),
    ("AAPL日K线", lambda: list(client.get_aggs("AAPL", 1, "day", 
        (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
        datetime.now().strftime('%Y-%m-%d')))),  
    ("AAPL小时K线", lambda: list(client.get_aggs("AAPL", 1, "hour",
        (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
        datetime.now().strftime('%Y-%m-%d')))),
]

results = []
for name, func in endpoints_to_test:
    try:
        result = func()
        print(f"✅ {name}: 可用")
        results.append((name, True, None))
    except Exception as e:
        error_msg = str(e)
        if "NOT_AUTHORIZED" in error_msg:
            print(f"❌ {name}: 需要升级订阅")
        elif "Rate limit" in error_msg:
            print(f"⚠️  {name}: 速率限制")
        else:
            print(f"❌ {name}: {error_msg[:50]}")
        results.append((name, False, error_msg))

print("\n" + "="*60)
print("📊 测试结果汇总")
print("="*60)

available = [r for r in results if r[1]]
unavailable = [r for r in results if not r[1]]

print(f"\n✅ 可用端点 ({len(available)}):")
for name, _, _ in available:
    print(f"   • {name}")

print(f"\n❌ 不可用端点 ({len(unavailable)}):")
for name, _, error in unavailable:
    if "NOT_AUTHORIZED" in error:
        print(f"   • {name} (需升级订阅)")
    else:
        print(f"   • {name} ({error[:40]})")

print("\n💡 建议:")
if len(available) == 0:
    print("   您的API Key无法访问任何数据端点")
    print("   请访问 https://massive.com/pricing 升级订阅")
elif len(available) < 3:
    print("   您的基础订阅权限有限")
    print("   考虑升级到付费计划以获取更多数据")
else:
    print("   大部分端点可用，可以开始开发")
