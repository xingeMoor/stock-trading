#!/usr/bin/env python3
"""
测试芯片ETF数据查询
"""
import sys
sys.path.insert(0, 'src')

import akshare as ak

print("🧪 测试芯片ETF (512760)...\n")

# 测试1: ETF实时行情
print("1️⃣  ETF实时行情...")
try:
    df = ak.fund_etf_spot_em()
    chip_etf = df[df['代码'] == '512760']
    if not chip_etf.empty:
        row = chip_etf.iloc[0]
        print(f"   ✅ {row['名称']} ({row['代码']})")
        print(f"   💰 最新价: ¥{row['最新价']}")
        print(f"   📊 涨跌幅: {row['涨跌幅']}%")
        print(f"   📈 成交量: {row['成交量']}")
    else:
        print("   ⚠️ 未找到512760")
except Exception as e:
    print(f"   ❌ 错误: {e}")

# 测试2: ETF历史数据
print("\n2️⃣  芯片ETF历史数据...")
try:
    # 使用新浪财经接口
    df = ak.fund_etf_hist_sina(symbol="sh512760")
    print(f"   ✅ 获取 {len(df)} 条历史记录")
    if not df.empty:
        latest = df.iloc[-1]
        print(f"   📅 日期: {latest.get('date')}")
        print(f"   📈 收盘: ¥{latest.get('close')}")
        print(f"   📊 涨跌: {latest.get('change', 'N/A')}")
except Exception as e:
    print(f"   ❌ 错误: {e}")

# 测试3: 搜索所有芯片ETF
print("\n3️⃣  搜索所有芯片相关ETF...")
try:
    df = ak.fund_etf_spot_em()
    chip_etfs = df[df['名称'].str.contains('芯片|半导体|集成电路', na=False)]
    print(f"   ✅ 找到 {len(chip_etfs)} 个芯片相关ETF")
    for _, etf in chip_etfs.head(5).iterrows():
        print(f"      - {etf['名称']} ({etf['代码']}): ¥{etf['最新价']} ({etf['涨跌幅']}%)")
except Exception as e:
    print(f"   ❌ 错误: {e}")

print("\n✅ 测试完成")
