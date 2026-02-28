#!/usr/bin/env python3
"""
测试飞书通知
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.feishu_notification import send_notification, get_access_token, send_trading_report

print("\n" + "="*60)
print("🧪 飞书通知测试")
print("="*60)

# 测试 1: 获取 access token
print("\n1️⃣  测试获取 access token...")
token = get_access_token()
if token:
    print(f"✅ Token 获取成功：{token[:20]}...")
else:
    print("⚠️  Token 获取失败 (可能未配置 Webhook 方式)")

# 测试 2: 发送简单消息
print("\n2️⃣  发送测试消息...")
message = """📊 量化交易系统测试

这是一条测试消息，确认飞书通知功能正常工作。

时间：2026-02-28
版本：V5.0
"""

success = send_notification(message, title="🤖 量化交易测试", msg_type="post")

if success:
    print("✅ 消息发送成功！")
else:
    print("❌ 消息发送失败")
    print("\n💡 提示:")
    print("  - 如果使用 Webhook 方式，请配置 FEISHU_WEBHOOK")
    print("  - 如果使用自建应用，请配置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
    print("  - 查看 FEISHU_CONFIG.md 获取详细配置指南")

# 测试 3: 模拟交易报告
print("\n3️⃣  模拟交易报告测试...")
mock_report = {
    'account_summary': {
        'total_value': 102350.00,
        'total_return': 2350.00,
        'total_return_pct': 2.35,
        'cash': 50000.00,
        'position_value': 52350.00
    },
    'executed_trades': [
        {'symbol': 'GOOGL', 'trade_type': 'buy', 'shares': 50, 'price': 185.50},
        {'symbol': 'META', 'trade_type': 'sell', 'shares': 30, 'price': 520.25, 'pnl': 450.00},
        {'symbol': 'AAPL', 'trade_type': 'buy', 'shares': 40, 'price': 178.30}
    ],
    'timestamp': '2026-02-28 10:30:00'
}

# success = send_trading_report(mock_report)
print("⏭️  跳过 (需要先配置飞书)")

print("\n" + "="*60)
print("测试完成")
print("="*60 + "\n")
