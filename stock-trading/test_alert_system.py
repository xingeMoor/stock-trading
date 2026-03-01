"""
飞书通知和告警系统测试脚本

运行方式:
    python test_alert_system.py

测试内容:
    1. 告警管理器 (alert_manager.py)
    2. 飞书通知增强功能 (feishu_notification.py)
    3. 通知调度器 (notification_scheduler.py)
"""
import os
import sys
import json
import time
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

def test_alert_manager():
    """测试告警管理器"""
    print("\n" + "="*60)
    print("🧪 测试 1: 告警管理器 (alert_manager.py)")
    print("="*60)
    
    from src.alert_manager import AlertManager, AlertLevel
    
    # 创建临时数据库
    test_db = "/tmp/test_alerts.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    manager = AlertManager(db_path=test_db, suppression_minutes=1)
    
    # 添加测试通知处理器
    notifications_sent = []
    def test_handler(alert):
        notifications_sent.append({
            "level": alert.level,
            "title": alert.title,
            "message": alert.message
        })
        print(f"   📤 通知发送: [{alert.level}] {alert.title}")
        return True
    
    manager.add_notification_handler(test_handler)
    
    # 测试1: 创建普通告警
    print("\n   1.1 创建不同级别的告警")
    for level in ["info", "warning", "error", "critical"]:
        alert = manager.create_alert(
            level=level,
            title=f"{level.upper()} 测试告警",
            message=f"这是一个 {level} 级别的测试告警",
            source="test"
        )
        status = "✅ 已创建" if alert else "🔇 被抑制"
        print(f"      {level}: {status}")
    
    # 测试2: 告警抑制
    print("\n   1.2 测试告警抑制(重复告警应被抑制)")
    alert_dup = manager.create_alert(
        level="warning",
        title="WARNING 测试告警",
        message="这是一个 warning 级别的测试告警",
        source="test"
    )
    print(f"      重复告警: {'🔇 被抑制' if alert_dup is None else '❌ 未被抑制'}")
    
    # 测试3: 获取统计
    print("\n   1.3 获取告警统计")
    stats = manager.get_stats(hours=1)
    print(f"      统计结果:")
    print(f"        - 总数: {stats['total']}")
    print(f"        - 按级别: {stats['by_level']}")
    print(f"        - 按状态: {stats['by_status']}")
    
    # 测试4: 确认告警
    print("\n   1.4 测试确认告警")
    pending = manager.get_pending_alerts()
    if pending:
        ack_result = manager.acknowledge_alert(pending[0].id, "test_user")
        print(f"      确认告警ID {pending[0].id}: {'✅ 成功' if ack_result else '❌ 失败'}")
    
    # 清理
    if os.path.exists(test_db):
        os.remove(test_db)
    
    print("\n   ✅ 告警管理器测试完成")
    return True


def test_feishu_notification():
    """测试飞书通知"""
    print("\n" + "="*60)
    print("🧪 测试 2: 飞书通知增强功能 (feishu_notification.py)")
    print("="*60)
    
    from src.feishu_notification import (
        test_feishu_connection,
        send_system_alert,
        send_daily_status_report,
        send_tool_down_alert,
        send_batch_alerts
    )
    
    # 测试1: 连接配置检查
    print("\n   2.1 检查飞书连接配置")
    conn_result = test_feishu_connection()
    print(f"      Webhook配置: {'✅' if conn_result['webhook_configured'] else '❌'}")
    print(f"      App配置: {'✅' if conn_result['app_configured'] else '❌'}")
    
    if not conn_result['webhook_configured'] and not conn_result['app_configured']:
        print("\n      ⚠️ 飞书未配置,跳过实际发送测试")
        print("      请在 .env 文件中配置以下环境变量之一:")
        print("        - FEISHU_WEBHOOK (Webhook方式)")
        print("        - FEISHU_APP_ID + FEISHU_APP_SECRET (自建应用方式)")
        return False
    
    # 测试2: 发送系统告警
    print("\n   2.2 测试 send_system_alert()")
    try:
        success = send_system_alert(
            level="warning",
            title="系统测试告警",
            message="这是通过 send_system_alert() 发送的测试消息",
            details={"测试项": "值", "环境": "开发测试", "时间": datetime.now().isoformat()}
        )
        print(f"      结果: {'✅ 成功' if success else '❌ 失败'}")
    except Exception as e:
        print(f"      错误: {e}")
    
    # 测试3: 发送每日报告
    print("\n   2.3 测试 send_daily_status_report()")
    try:
        success = send_daily_status_report(
            system_status={
                "uptime": "24小时",
                "tools_status": {"yahoo_finance": "up", "akshare": "up", "test_tool": "down"},
                "data_freshness": "实时",
                "last_trade_time": "2024-01-15 15:30:00"
            },
            trading_summary={
                "total_trades": 15,
                "profit_loss": 1250.50,
                "positions_count": 8
            },
            alert_summary={
                "total_alerts": 5,
                "by_level": {"warning": 3, "error": 1, "info": 1}
            }
        )
        print(f"      结果: {'✅ 成功' if success else '❌ 失败'}")
    except Exception as e:
        print(f"      错误: {e}")
    
    # 测试4: 发送工具宕机告警
    print("\n   2.4 测试 send_tool_down_alert()")
    try:
        success = send_tool_down_alert(
            tool_name="yahoo_finance",
            error="Connection timeout after 30 seconds. Unable to fetch data from API.",
            last_success_time="2024-01-15 08:30:00"
        )
        print(f"      结果: {'✅ 成功' if success else '❌ 失败'}")
    except Exception as e:
        print(f"      错误: {e}")
    
    # 测试5: 批量告警
    print("\n   2.5 测试 send_batch_alerts()")
    try:
        test_alerts = [
            {"level": "critical", "title": "数据库连接失败", "message": "无法连接到主数据库"},
            {"level": "error", "title": "API限流", "message": "请求频率超过限制"},
            {"level": "warning", "title": "数据延迟", "message": "数据更新延迟5分钟"},
            {"level": "warning", "title": "缓存未命中", "message": "Redis缓存命中率低于80%"},
            {"level": "info", "title": "任务完成", "message": "定时任务执行成功"},
        ]
        success = send_batch_alerts(test_alerts, title="系统自检告警汇总")
        print(f"      结果: {'✅ 成功' if success else '❌ 失败'}")
    except Exception as e:
        print(f"      错误: {e}")
    
    print("\n   ✅ 飞书通知测试完成")
    return True


def test_notification_scheduler():
    """测试通知调度器"""
    print("\n" + "="*60)
    print("🧪 测试 3: 通知调度器 (notification_scheduler.py)")
    print("="*60)
    
    from src.notification_scheduler import NotificationScheduler
    
    # 创建调度器
    scheduler = NotificationScheduler()
    
    # 测试1: 注册工具检查器
    print("\n   3.1 注册工具检查器")
    
    check_count = {"tool1": 0, "tool2": 0}
    
    def checker_1():
        check_count["tool1"] += 1
        return {
            "status": "up",
            "latency_ms": 150,
            "message": "正常",
            "last_success": datetime.now().isoformat()
        }
    
    def checker_2():
        check_count["tool2"] += 1
        # 模拟偶发故障
        if check_count["tool2"] % 3 == 0:
            return {
                "status": "down",
                "latency_ms": None,
                "message": "Service temporarily unavailable",
                "last_success": (datetime.now() - timedelta(minutes=10)).isoformat()
            }
        return {
            "status": "up",
            "latency_ms": 200,
            "message": "正常",
            "last_success": datetime.now().isoformat()
        }
    
    scheduler.register_tool_checker("test_service_1", checker_1)
    scheduler.register_tool_checker("test_service_2", checker_2)
    print(f"      已注册 2 个工具检查器")
    
    # 测试2: 健康检查
    print("\n   3.2 执行健康检查")
    health = scheduler.check_tools_health()
    print(f"      检查结果:")
    print(f"        - 检查时间: {health['checked_at']}")
    print(f"        - 工具状态:")
    for name, status in health['tools'].items():
        emoji = "🟢" if status['status'] == 'up' else "🔴"
        print(f"          {emoji} {name}: {status['status']}")
    print(f"        - 故障工具: {health['failed_tools'] if health['failed_tools'] else '无'}")
    
    # 测试3: 获取状态
    print("\n   3.3 获取调度器状态")
    status = scheduler.get_status()
    print(f"      状态信息:")
    print(f"        - 运行中: {status['running']}")
    print(f"        - 告警启用: {status['alert_enabled']}")
    print(f"        - 每日报告时间: {status['daily_report_time']}")
    print(f"        - 监控工具: {', '.join(status['tools_registered'])}")
    print(f"        - APScheduler可用: {status['apscheduler_available']}")
    print(f"        - 飞书可用: {status['feishu_available']}")
    print(f"        - 告警管理器可用: {status['alert_manager_available']}")
    
    # 测试4: 发送每日报告(不依赖调度器)
    print("\n   3.4 测试生成每日报告")
    # 这里只是测试函数调用,实际发送可能因未配置而失败
    try:
        scheduler.send_daily_report()
        print("      报告生成完成")
    except Exception as e:
        print(f"      报告生成: {e}")
    
    print("\n   ✅ 通知调度器测试完成")
    return True


def main():
    """主函数"""
    print("\n" + "="*60)
    print("🚀 飞书通知和告警系统测试")
    print("="*60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # 测试1: 告警管理器
    try:
        results.append(("告警管理器", test_alert_manager()))
    except Exception as e:
        print(f"\n❌ 告警管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("告警管理器", False))
    
    # 测试2: 飞书通知
    try:
        results.append(("飞书通知", test_feishu_notification()))
    except Exception as e:
        print(f"\n❌ 飞书通知测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("飞书通知", False))
    
    # 测试3: 通知调度器
    try:
        results.append(("通知调度器", test_notification_scheduler()))
    except Exception as e:
        print(f"\n❌ 通知调度器测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("通知调度器", False))
    
    # 汇总结果
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"   {name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\n总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过!")
    else:
        print("\n⚠️ 部分测试未通过,请检查配置或代码")
    
    print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)


if __name__ == "__main__":
    main()
