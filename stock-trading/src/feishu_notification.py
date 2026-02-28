"""
飞书通知模块
支持两种方式:
1. Webhook (简单，适合群机器人)
2. 自建应用 (需要 app_id 和 app_secret，功能更强)
"""
import requests
import hmac
import hashlib
import base64
import time
import os
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# 配置
FEISHU_WEBHOOK = os.getenv('FEISHU_WEBHOOK')
FEISHU_SECRET = os.getenv('FEISHU_SECRET')
FEISHU_APP_ID = os.getenv('FEISHU_APP_ID')
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')

# Access token 缓存
_access_token = None
_token_expires_at = 0


def get_access_token() -> Optional[str]:
    """获取飞书 access token (自建应用方式)"""
    global _access_token, _token_expires_at
    
    # 检查缓存
    if _access_token and time.time() < _token_expires_at:
        return _access_token
    
    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        return None
    
    try:
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": FEISHU_APP_ID,
            "app_secret": FEISHU_APP_SECRET
        }
        
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        
        if result.get('code') == 0:
            _access_token = result['tenant_access_token']
            _token_expires_at = time.time() + result['expire'] - 60  # 提前 60 秒过期
            print("✅ 获取飞书 access token 成功")
            return _access_token
        else:
            print(f"❌ 获取 access token 失败：{result}")
            return None
            
    except Exception as e:
        print(f"❌ 获取 token 异常：{e}")
        return None


def generate_sign(secret: str) -> str:
    """生成飞书签名 (Webhook 方式)"""
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
    receive_id: str = None,
    data: Dict[str, Any] = None
) -> bool:
    """
    发送飞书通知
    
    Args:
        message: 消息内容
        title: 标题 (用于 post 类型)
        msg_type: 消息类型 (text/post/interactive)
        receive_id: 接收者 ID (用户 ID 或群 ID，自建应用方式需要)
        data: 额外的消息数据
    
    Returns:
        是否发送成功
    """
    # 优先使用自建应用方式
    if FEISHU_APP_ID and FEISHU_APP_SECRET:
        return send_via_app(message, title, msg_type, receive_id, data)
    
    # 降级使用 Webhook 方式
    if FEISHU_WEBHOOK:
        return send_via_webhook(message, title, msg_type, data)
    
    print("⚠️  飞书通知未配置 (Webhook 或 自建应用)")
    return False


def send_via_webhook(
    message: str,
    title: str = None,
    msg_type: str = "text",
    data: Dict[str, Any] = None
) -> bool:
    """通过 Webhook 发送通知"""
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
            print("✅ 飞书通知发送成功 (Webhook)")
            return True
        else:
            print(f"❌ 飞书通知发送失败：{result}")
            return False
            
    except Exception as e:
        print(f"❌ 发送异常：{e}")
        return False


def send_via_app(
    message: str,
    title: str = None,
    msg_type: str = "text",
    receive_id: str = None,
    data: Dict[str, Any] = None
) -> bool:
    """通过自建应用发送通知"""
    token = get_access_token()
    if not token:
        return False
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    # 构建消息
    if msg_type == "text":
        content = {"text": message}
    elif msg_type == "post":
        content = {
            "post": {
                "zh_cn": {
                    "title": title or "通知",
                    "content": [
                        [{"tag": "text", "text": message}]
                    ]
                }
            }
        }
    else:
        content = data or {}
    
    # 发送消息 API
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {"receive_id_type": "chat_id"}  # 默认发送给群
    
    payload = {
        "receive_id": receive_id or "oc_123456",  # 需要替换为实际的群 ID
        "msg_type": msg_type,
        "content": json.dumps(content)
    }
    
    try:
        response = requests.post(url, headers=headers, params=params, json=payload, timeout=10)
        result = response.json()
        
        if result.get('code') == 0:
            print("✅ 飞书通知发送成功 (自建应用)")
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
