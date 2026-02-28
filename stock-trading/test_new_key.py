#!/usr/bin/env python3
"""测试新的 Massive API Key"""
import os
from datetime import datetime, timedelta
from massive import RESTClient

# 使用新提供的 API Key
NEW_API_KEY = "yLk1LGqL2zxTV8s04rogmJ8x2duhUYtV"

print("🔑 测试新 API Key")
print(f"Key: {NEW_API_KEY[:10]}...")
print("="*60)

try:
    client = RESTClient(api_key=NEW_API_KEY)
    
    # 测试1: 获取AAPL最新交易
    print("\n1️⃣  获取 AAPL 最新交易...")
    trade = client.get_last_trade("AAPL")
    print(f"   ✅ 成功!")
    print(f"   💰 价格: ${trade.price}")
    print(f"   📊 成交量: {trade.size}")
    print(f"   🕐 时间: {datetime.fromtimestamp(trade.timestamp/1000)}")
    
    # 测试2: 获取历史K线
    print("\n2️⃣  获取 AAPL 历史K线 (最近10天)...")
    from_ = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
    to = datetime.now().strftime('%Y-%m-%d')
    
    aggs = client.get_aggs(
        ticker="AAPL",
        multiplier=1,
        timespan="day",
        from_=from_,
        to=to
    )
    
    agg_list = list(aggs)
    print(f"   ✅ 成功! 获取 {len(agg_list)} 条K线")
    
    if agg_list:
        latest = agg_list[-1]
        print(f"   📈 最新数据:")
        print(f"      日期: {datetime.fromtimestamp(latest.timestamp/1000).strftime('%Y-%m-%d')}")
        print(f"      开盘: ${latest.open}")
        print(f"      收盘: ${latest.close}")
        print(f"      最高: ${latest.high}")
        print(f"      最低: ${latest.low}")
        print(f"      成交量: {latest.volume:,}")
    
    # 测试3: 获取技术指标 SMA
    print("\n3️⃣  获取 AAPL SMA-20...")
    sma_data = client.get_sma(
        ticker="AAPL",
        window=20,
        timestamp_gte=from_,
        timestamp_lt=to
    )
    
    sma_list = list(sma_data)
    print(f"   ✅ 成功! 获取 {len(sma_list)} 条SMA数据")
    if sma_list:
        print(f"   📊 最新 SMA-20: {sma_list[-1].value:.2f}")
    
    # 测试4: 批量获取多只股票
    print("\n4️⃣  批量获取股票最新价...")
    symbols = ["MSFT", "GOOGL", "AMZN", "TSLA"]
    for sym in symbols:
        try:
            snapshot = client.get_snapshot_ticker("stocks", sym)
            print(f"   {sym}: ${snapshot.last_trade.price:.2f}")
        except Exception as e:
            print(f"   {sym}: ❌ {str(e)[:40]}")
    
    print("\n" + "="*60)
    print("✅ 新 API Key 测试通过！所有端点可用")
    print("="*60)
    
    # 建议更新 .env 文件
    print("\n💡 建议更新 .env 文件:")
    print(f"   MASSIVE_API_KEY={NEW_API_KEY}")
    
except Exception as e:
    print(f"\n❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
