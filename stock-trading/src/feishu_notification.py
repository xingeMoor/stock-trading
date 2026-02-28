"""
飞书通知模块
"""
import requests
import hmac
import hashlib
import base64
import time
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

FEISHU_WEBHOOK = os.getenv('FEISHU_WEBHOOK')
FEISHU_SECRET = os.getenv('FEISHU_SECRET')


def generate_sign(secret: str) -> str:
    """生成飞书签名"""
    timestamp = str(int(time.time()))
    string_to_sign = f"{timestamp}\n{secret}"
    
    hmac_code = hmac.new(
        string_to_sign.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    
    sign = base64.b64encode(hmac_code).decode('utf-8')
    
    return timestamp, sign


def send_notification(
    message: str,
    title: str = None,
    msg_type: str = "text",
    data: Dict[str, Any] = None
) -> bool:
    """
    发送飞书通知
    
    Args:
        message: 消息内容
        title: 标题 (用于 post 类型)
        msg_type: 消息类型 (text/post/interactive)
        data: 额外的消息数据
    
    Returns:
        是否发送成功
    """
    if not FEISHU_WEBHOOK:
        print("⚠️  飞书 webhook 未配置")
        return False
    
    headers = {'Content-Type': 'application/json'}
    
    # 构建消息
    if msg_type == "text":
        payload = {
            "msg_type": "text",
            "content": {
                "text": message
            }
        }
    elif msg_type == "post":
        payload = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": title or "通知",
                        "content": [
                            [{"tag": "text", "text": message}]
                        ]
                    }
                }
            }
        }
    else:
        payload = data or {}
    
    # 添加签名 (如果配置了)
    if FEISHU_SECRET:
        timestamp, sign = generate_sign(FEISHU_SECRET)
        headers['X-Sign-Timestamp'] = timestamp
        headers['X-Sign-SHA256'] = sign
    
    try:
        response = requests.post(
            FEISHU_WEBHOOK,
            headers=headers,
            json=payload,
            timeout=10
        )
        
        result = response.json()
        
        if result.get('StatusCode') == 0 or result.get('code') == 0:
            print("✅ 飞书通知发送成功")
            return True
        else:
            print(f"❌ 飞书通知发送失败：{result}")
            return False
            
    except Exception as e:
        print(f"❌ 发送异常：{e}")
        return False


def send_trading_report(report: Dict[str, Any]) -> bool:
    """发送交易报告"""
    if not report:
        return False
    
    summary = report.get('account_summary', {})
    trades = report.get('executed_trades', [])
    
    message = f"""📊 模拟交易执行报告

💰 账户状态:
  总资产：${summary.get('total_value', 0):,.2f}
  总收益：${summary.get('total_return', 0):,.2f} ({summary.get('total_return_pct', 0):+.2f}%)
  可用现金：${summary.get('cash', 0):,.2f}
  持仓市值：${summary.get('position_value', 0):,.2f}

📝 今日交易：{len(trades)} 笔
"""
    
    for trade in trades:
        arrow = "→" if trade['trade_type'] == 'buy' else "←"
        pnl_str = f" (PnL: ${trade.get('pnl', 0):+.2f})" if trade['trade_type'] == 'sell' else ""
        message += f"  {arrow} {trade['symbol']}: {trade['shares']}股 @ ${trade['price']:.2f}{pnl_str}\n"
    
    if not trades:
        message += "  无交易"
    
    message += f"\n⏰ 更新时间：{report.get('timestamp', '')}"
    
    return send_notification(message, title="📊 交易报告", msg_type="post")


def send_alert(title: str, message: str, level: str = "warning") -> bool:
    """发送告警通知"""
    emoji = {
        "warning": "⚠️",
        "error": "❌",
        "info": "ℹ️",
        "success": "✅"
    }
    
    full_message = f"{emoji.get(level, '📢')} *{title}*\n\n{message}"
    return send_notification(full_message)


if __name__ == "__main__":
    # 测试
    print("\n🧪 测试飞书通知\n")
    
    if not FEISHU_WEBHOOK:
        print("⚠️  飞书 webhook 未配置，请在 .env 中添加 FEISHU_WEBHOOK")
    else:
        # 发送测试消息
        success = send_notification("这是一条测试消息")
        
        if success:
            print("\n✅ 测试完成")
        else:
            print("\n❌ 测试失败")
