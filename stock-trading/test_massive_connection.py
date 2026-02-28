#!/usr/bin/env python3
"""
测试 Massive API 连接
排查数据获取问题
"""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

MASSIVE_API_KEY = os.getenv('MASSIVE_API_KEY')
print(f"🔑 API Key: {MASSIVE_API_KEY[:10]}..." if MASSIVE_API_KEY else "❌ API Key 未设置")

# 尝试不同的导入方式
print("\n📦 尝试导入 Massive/Polygon 库...")

try:
    # 方式1: polygon (最常见的)
    from polygon import RESTClient
    print("✅ 成功导入: from polygon import RESTClient")
    CLIENT_TYPE = "polygon"
except ImportError as e1:
    print(f"❌ polygon 导入失败: {e1}")
    
    try:
        # 方式2: massive
        from massive import RESTClient
        print("✅ 成功导入: from massive import RESTClient")
        CLIENT_TYPE = "massive"
    except ImportError as e2:
        print(f"❌ massive 导入失败: {e2}")
        
        try:
            # 方式3: polygon-api-client
            from polygon_api_client import RESTClient
            print("✅ 成功导入: from polygon_api_client import RESTClient")
            CLIENT_TYPE = "polygon_api_client"
        except ImportError as e3:
            print(f"❌ 所有导入方式都失败")
            print("\n💡 请安装正确的库:")
            print("   pip install polygon-api-client")
            exit(1)

# 测试 API 连接
print(f"\n🌐 测试 API 连接 ({CLIENT_TYPE})...")

try:
    client = RESTClient(api_key=MASSIVE_API_KEY)
    
    # 测试1: 获取AAPL最新交易
    print("\n1️⃣  获取 AAPL 最新交易...")
    trade = client.get_last_trade("AAPL")
    print(f"   ✅ 价格: ${trade.price}, 时间: {datetime.fromtimestamp(trade.timestamp/1000)}")
    
    # 测试2: 获取历史K线
    print("\n2️⃣  获取 AAPL 历史K线 (最近30天)...")
    from_ = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    to = datetime.now().strftime('%Y-%m-%d')
    
    aggs = client.get_aggs(
        ticker="AAPL",
        multiplier=1,
        timespan="day",
        from_=from_,
        to=to
    )
    
    agg_list = list(aggs)
    print(f"   ✅ 获取 {len(agg_list)} 条K线数据")
    if agg_list:
        latest = agg_list[-1]
        print(f"   📊 最新: 开${latest.open} 收${latest.close} 量{latest.volume}")
    
    # 测试3: 获取技术指标 SMA
    print("\n3️⃣  获取 AAPL SMA-20...")
    sma_data = client.get_sma(
        ticker="AAPL",
        window=20,
        timestamp_gte=from_,
        timestamp_lt=to
    )
    
    sma_list = list(sma_data)
    print(f"   ✅ 获取 {len(sma_list)} 条SMA数据")
    if sma_list:
        print(f"   📈 最新SMA-20: {sma_list[-1].value:.2f}")
    
    # 测试4: 获取多只股票
    print("\n4️⃣  批量获取多只股票最新价...")
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    for sym in symbols:
        try:
            snapshot = client.get_snapshot_ticker("stocks", sym)
            print(f"   {sym}: ${snapshot.last_trade.price:.2f}")
        except Exception as e:
            print(f"   {sym}: ❌ {e}")
    
    print("\n" + "="*60)
    print("✅ 所有测试通过！Massive API 连接正常")
    print("="*60)
    
except Exception as e:
    print(f"\n❌ API 测试失败: {e}")
    import traceback
    traceback.print_exc()
