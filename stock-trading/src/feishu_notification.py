"""
飞书通知模块
支持两种方式:
1. Webhook (简单，适合群机器人)
2. 自建应用 (需要 app_id 和 app_secret，功能更强)

新增功能:
- send_system_alert() - 发送系统告警
- send_daily_status_report() - 发送每日状态报告
- send_tool_down_alert() - 工具宕机告警
"""
import requests
import hmac
import hashlib
import base64
import time
import os
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# 配置
FEISHU_WEBHOOK = os.getenv('FEISHU_WEBHOOK')
FEISHU_SECRET = os.getenv('FEISHU_SECRET')
FEISHU_APP_ID = os.getenv('FEISHU_APP_ID')
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_RECEIVE_ID = os.getenv('FEISHU_RECEIVE_ID', 'oc_123456')  # 默认接收者ID

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


def generate_sign(secret: str) -> tuple:
    """生成飞书签名 (Webhook 方式)"""
    timestamp = str(int(time.time()))
    string_to_sign = f"{timestamp}\n{secret}"
    
    hmac_code = hmac.new(
        secret.encode('utf-8'),
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
        payload["timestamp"] = timestamp
        payload["sign"] = sign
    
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


def get_chat_list(token: str) -> List[Dict]:
    """获取用户所在的群聊列表"""
    try:
        url = "https://open.feishu.cn/open-apis/im/v1/chats"
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(url, headers=headers, timeout=10)
        result = response.json()
        
        if result.get('code') == 0:
            return result.get('data', {}).get('items', [])
        else:
            print(f"⚠️ 获取群聊列表失败：{result}")
            return []
    except Exception as e:
        print(f"⚠️ 获取群聊列表异常：{e}")
        return []


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
    
    # 如果没有提供receive_id，尝试获取可用的群聊
    target_id = receive_id or FEISHU_RECEIVE_ID
    if not target_id or target_id == 'oc_123456':
        print("🔍 未配置有效的FEISHU_RECEIVE_ID，尝试获取群聊列表...")
        chats = get_chat_list(token)
        if chats:
            target_id = chats[0].get('chat_id')
            print(f"✅ 使用群聊ID: {target_id}")
        else:
            print("❌ 未能获取到可用的群聊ID")
            print("💡 请执行以下操作之一：")
            print("   1. 在.env中设置 FEISHU_RECEIVE_ID=你的实际群聊ID")
            print("   2. 配置 FEISHU_WEBHOOK 使用Webhook方式发送")
            print("   3. 确保机器人已被添加到目标群聊")
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
        "receive_id": target_id,
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
        "success": "✅",
        "critical": "🚨"
    }
    
    full_message = f"{emoji.get(level, '📢')} *{title}*\n\n{message}"
    return send_notification(full_message)


# ==================== 新增功能 ====================


def send_system_alert(
    level: str,
    title: str,
    message: str,
    details: Dict[str, Any] = None
) -> bool:
    """
    发送系统告警
    
    Args:
        level: 告警级别 (info/warning/error/critical)
        title: 告警标题
        message: 告警内容
        details: 详细信息的字典
    
    Returns:
        是否发送成功
    """
    emoji_map = {
        "info": "ℹ️",
        "warning": "⚠️",
        "error": "❌",
        "critical": "🚨"
    }
    
    emoji = emoji_map.get(level, "📢")
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 构建富文本消息
    content = [
        [{"tag": "text", "text": f"{emoji} ", "style": {"bold": True}},
         {"tag": "text", "text": f"【{level.upper()}】", "style": {"bold": True}},
         {"tag": "text", "text": title, "style": {"bold": True}}],
        [{"tag": "text", "text": ""}],
        [{"tag": "text", "text": message}]
    ]
    
    # 添加详细信息
    if details:
        content.append([{"tag": "text", "text": ""}])
        content.append([{"tag": "text", "text": "📋 详细信息:", "style": {"bold": True}}])
        for key, value in details.items():
            content.append([{"tag": "text", "text": f"  • {key}: {value}"}])
    
    # 添加时间戳
    content.append([{"tag": "text", "text": ""}])
    content.append([{"tag": "text", "text": f"⏰ {current_time}", "style": {"italic": True}}])
    
    payload = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": f"{emoji} 系统告警",
                    "content": content
                }
            }
        }
    }
    
    # 根据级别决定是否使用更醒目的颜色
    if level == "critical":
        # critical级别尝试使用卡片消息(如果支持)
        pass
    
    return send_notification("", msg_type="post", data=payload)


def send_daily_status_report(
    system_status: Dict[str, Any],
    trading_summary: Dict[str, Any] = None,
    alert_summary: Dict[str, Any] = None
) -> bool:
    """
    发送每日状态报告
    
    Args:
        system_status: 系统状态信息
            {
                "uptime": "系统运行时间",
                "tools_status": {"tool_name": "up/down", ...},
                "data_freshness": "数据新鲜度",
                "last_trade_time": "最后交易时间"
            }
        trading_summary: 交易摘要
            {
                "total_trades": 总交易数,
                "profit_loss": 盈亏,
                "positions_count": 持仓数量
            }
        alert_summary: 告警摘要
            {
                "total_alerts": 总告警数,
                "by_level": {"warning": x, "error": y}
            }
    
    Returns:
        是否发送成功
    """
    today = datetime.now().strftime("%Y年%m月%d日")
    current_time = datetime.now().strftime("%H:%M:%S")
    
    # 构建工具状态部分
    tools_section = []
    tools_status = system_status.get("tools_status", {})
    for tool_name, status in tools_status.items():
        emoji = "🟢" if status == "up" else "🔴"
        tools_section.append(f"  {emoji} {tool_name}")
    
    if not tools_section:
        tools_section = ["  ℹ️ 暂无工具状态信息"]
    
    # 构建交易摘要部分
    trading_section = []
    if trading_summary:
        total_trades = trading_summary.get("total_trades", 0)
        profit_loss = trading_summary.get("profit_loss", 0)
        positions_count = trading_summary.get("positions_count", 0)
        
        pl_emoji = "📈" if profit_loss >= 0 else "📉"
        trading_section = [
            f"  📊 总交易: {total_trades}笔",
            f"  {pl_emoji} 盈亏: ${profit_loss:+.2f}",
            f"  💼 持仓: {positions_count}只"
        ]
    else:
        trading_section = ["  ℹ️ 暂无交易信息"]
    
    # 构建告警摘要部分
    alert_section = []
    if alert_summary:
        total_alerts = alert_summary.get("total_alerts", 0)
        by_level = alert_summary.get("by_level", {})
        
        alert_section.append(f"  📢 总告警: {total_alerts}条")
        if by_level.get("critical", 0) > 0:
            alert_section.append(f"    🚨 Critical: {by_level['critical']}")
        if by_level.get("error", 0) > 0:
            alert_section.append(f"    ❌ Error: {by_level['error']}")
        if by_level.get("warning", 0) > 0:
            alert_section.append(f"    ⚠️ Warning: {by_level['warning']}")
    else:
        alert_section = ["  ✅ 过去24小时无告警"]
    
    # 组装完整消息
    message = f"""🌅 每日系统状态报告

📅 日期: {today}
⏱️ 系统运行: {system_status.get("uptime", "未知")}
📊 数据新鲜度: {system_status.get("data_freshness", "未知")}

🔧 工具状态:
{chr(10).join(tools_section)}

💰 交易摘要:
{chr(10).join(trading_section)}

🔔 告警统计(24h):
{chr(10).join(alert_section)}

⏰ 报告生成时间: {current_time}
"""
    
    return send_notification(message, title=f"🌅 每日状态报告 - {today}", msg_type="post")


def send_tool_down_alert(tool_name: str, error: str, last_success_time: str = None) -> bool:
    """
    发送工具宕机告警
    
    Args:
        tool_name: 工具名称
        error: 错误信息
        last_success_time: 上次成功时间
    
    Returns:
        是否发送成功
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    content = [
        [{"tag": "text", "text": "🚨 ", "style": {"bold": True}},
         {"tag": "text", "text": "工具宕机告警", "style": {"bold": True}}],
        [{"tag": "text", "text": ""}],
        [{"tag": "text", "text": f"🔧 工具名称: ", "style": {"bold": True}},
         {"tag": "text", "text": tool_name}],
        [{"tag": "text", "text": ""}],
        [{"tag": "text", "text": "❌ 错误信息:", "style": {"bold": True}}],
        [{"tag": "text", "text": error}]
    ]
    
    if last_success_time:
        content.append([{"tag": "text", "text": ""}])
        content.append([
            {"tag": "text", "text": "⏮️ 上次成功: ", "style": {"bold": True}},
            {"tag": "text", "text": last_success_time}
        ])
    
    content.append([{"tag": "text", "text": ""}])
    content.append([
        {"tag": "text", "text": "⏰ 检测时间: ", "style": {"bold": True}},
        {"tag": "text", "text": current_time}
    ])
    
    content.append([{"tag": "text", "text": ""}])
    content.append([
        {"tag": "text", "text": "💡 建议操作:", "style": {"bold": True}}
    ])
    content.append([
        {"tag": "text", "text": "  1. 检查工具服务状态"}
    ])
    content.append([
        {"tag": "text", "text": "  2. 查看相关日志"}
    ])
    content.append([
        {"tag": "text", "text": "  3. 确认网络连接"}
    ])
    
    payload = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": "🚨 工具宕机告警",
                    "content": content
                }
            }
        }
    }
    
    return send_notification("", msg_type="post", data=payload)


def send_batch_alerts(alerts: List[Dict[str, Any]], title: str = "批量告警") -> bool:
    """
    发送批量告警汇总
    
    Args:
        alerts: 告警列表,每个告警包含level, title, message
        title: 汇总标题
    
    Returns:
        是否发送成功
    """
    if not alerts:
        return True
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 按级别分组统计
    level_counts = {}
    for alert in alerts:
        level = alert.get("level", "info")
        level_counts[level] = level_counts.get(level, 0) + 1
    
    # 构建统计行
    stats_parts = []
    for level in ["critical", "error", "warning", "info"]:
        if level in level_counts:
            emoji = {"critical": "🚨", "error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(level, "📢")
            stats_parts.append(f"{emoji} {level.upper()}: {level_counts[level]}")
    
    # 构建告警详情(最多显示5条)
    detail_lines = []
    for i, alert in enumerate(alerts[:5]):
        level = alert.get("level", "info")
        alert_title = alert.get("title", "无标题")
        emoji = {"critical": "🚨", "error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(level, "📢")
        detail_lines.append(f"{i+1}. {emoji} {alert_title}")
    
    if len(alerts) > 5:
        detail_lines.append(f"... 还有 {len(alerts) - 5} 条告警")
    
    message = f"""📦 {title}

📊 告警统计:
  {' | '.join(stats_parts)}

📝 告警详情:
{chr(10).join(detail_lines)}

💡 共 {len(alerts)} 条告警,请及时处理

⏰ {current_time}
"""
    
    return send_notification(message, title=f"📦 {title}", msg_type="post")


def test_feishu_connection() -> Dict[str, Any]:
    """
    测试飞书连接
    
    Returns:
        测试结果
    """
    result = {
        "webhook_configured": bool(FEISHU_WEBHOOK),
        "app_configured": bool(FEISHU_APP_ID and FEISHU_APP_SECRET),
        "webhook_test": False,
        "app_test": False,
        "errors": []
    }
    
    # 测试 Webhook
    if FEISHU_WEBHOOK:
        try:
            test_payload = {
                "msg_type": "text",
                "content": {"text": "连接测试"}
            }
            if FEISHU_SECRET:
                timestamp, sign = generate_sign(FEISHU_SECRET)
                test_payload["timestamp"] = timestamp
                test_payload["sign"] = sign
            
            response = requests.post(
                FEISHU_WEBHOOK,
                json=test_payload,
                timeout=10
            )
            resp_data = response.json()
            if resp_data.get('StatusCode') == 0 or resp_data.get('code') == 0:
                result["webhook_test"] = True
            else:
                result["errors"].append(f"Webhook测试失败: {resp_data}")
        except Exception as e:
            result["errors"].append(f"Webhook连接异常: {e}")
    
    # 测试 App
    if FEISHU_APP_ID and FEISHU_APP_SECRET:
        try:
            token = get_access_token()
            if token:
                result["app_test"] = True
            else:
                result["errors"].append("App Token获取失败")
        except Exception as e:
            result["errors"].append(f"App连接异常: {e}")
    
    return result


if __name__ == "__main__":
    # 测试
    print("\n🧪 测试飞书通知模块\n")
    
    # 测试连接
    print("1. 测试连接配置")
    conn_result = test_feishu_connection()
    print(f"   Webhook配置: {'✅' if conn_result['webhook_configured'] else '❌'}")
    print(f"   App配置: {'✅' if conn_result['app_configured'] else '❌'}")
    
    if not conn_result['webhook_configured'] and not conn_result['app_configured']:
        print("\n⚠️  飞书未配置,请在 .env 中添加相关配置")
        print("   支持的配置项:")
        print("   - FEISHU_WEBHOOK: Webhook地址")
        print("   - FEISHU_SECRET: Webhook密钥(可选)")
        print("   - FEISHU_APP_ID / FEISHU_APP_SECRET: 自建应用凭证")
    else:
        # 测试普通消息
        print("\n2. 测试普通消息")
        success = send_notification("这是一条测试消息")
        print(f"   结果: {'✅ 成功' if success else '❌ 失败'}")
        
        # 测试系统告警
        print("\n3. 测试系统告警")
        success = send_system_alert(
            level="warning",
            title="测试告警",
            message="这是一个测试的系统告警消息",
            details={"测试项": "值", "环境": "开发"}
        )
        print(f"   结果: {'✅ 成功' if success else '❌ 失败'}")
        
        # 测试每日报告
        print("\n4. 测试每日状态报告")
        success = send_daily_status_report(
            system_status={
                "uptime": "24小时",
                "tools_status": {"yahoo_finance": "up", "akshare": "up"},
                "data_freshness": "实时"
            },
            trading_summary={
                "total_trades": 10,
                "profit_loss": 150.50,
                "positions_count": 5
            },
            alert_summary={
                "total_alerts": 3,
                "by_level": {"warning": 2, "info": 1}
            }
        )
        print(f"   结果: {'✅ 成功' if success else '❌ 失败'}")
        
        # 测试工具宕机告警
        print("\n5. 测试工具宕机告警")
        success = send_tool_down_alert(
            tool_name="yahoo_finance",
            error="Connection timeout after 30 seconds",
            last_success_time="2024-01-15 08:30:00"
        )
        print(f"   结果: {'✅ 成功' if success else '❌ 失败'}")
    
    print("\n✅ 测试完成")
