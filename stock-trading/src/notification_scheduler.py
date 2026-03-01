"""
通知调度器
使用APScheduler:
- 每天早上8点发送系统状态日报
- 当检测到工具异常时立即发送告警
- 飞书不可用时，尝试备用通知方式(如有)
"""
import os
import sys
import time
import json
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('NotificationScheduler')

# 尝试导入APScheduler
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
    APSCHEDULER_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ APScheduler未安装,使用简单定时器替代")
    APSCHEDULER_AVAILABLE = False

# 导入自定义模块
try:
    from src.feishu_notification import (
        send_notification,
        send_system_alert,
        send_daily_status_report,
        send_tool_down_alert,
        test_feishu_connection
    )
    FEISHU_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ 飞书通知模块导入失败: {e}")
    FEISHU_AVAILABLE = False

try:
    from src.alert_manager import get_alert_manager, AlertManager
    ALERT_MANAGER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ 告警管理器导入失败: {e}")
    ALERT_MANAGER_AVAILABLE = False


class NotificationScheduler:
    """通知调度器"""
    
    def __init__(self):
        """初始化调度器"""
        self.scheduler = None
        self.running = False
        self._alert_manager: Optional[AlertManager] = None
        self._tool_checkers: Dict[str, Callable[[], Dict[str, Any]]] = {}
        self._fallback_handlers: List[Callable[[str, str], bool]] = []
        
        # 配置
        self.daily_report_time = os.getenv('DAILY_REPORT_TIME', '08:00')
        self.alert_enabled = os.getenv('ALERT_ENABLED', 'true').lower() == 'true'
        
        # 工具状态缓存
        self._tool_status_cache: Dict[str, Dict[str, Any]] = {}
        self._last_check_time: Optional[datetime] = None
        
        if ALERT_MANAGER_AVAILABLE:
            self._alert_manager = get_alert_manager()
            # 注册飞书通知处理器
            if FEISHU_AVAILABLE:
                self._alert_manager.add_notification_handler(self._handle_alert_notification)
        
        self._init_scheduler()
    
    def _init_scheduler(self):
        """初始化调度器"""
        if APSCHEDULER_AVAILABLE:
            self.scheduler = BackgroundScheduler()
            self.scheduler.add_listener(
                self._job_listener,
                EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
            )
        else:
            self.scheduler = SimpleScheduler()
    
    def _job_listener(self, event):
        """任务执行监听器"""
        if event.exception:
            logger.error(f"❌ 任务执行失败: {event.job_id}, 错误: {event.exception}")
        else:
            logger.info(f"✅ 任务执行成功: {event.job_id}")
    
    def _handle_alert_notification(self, alert) -> bool:
        """
        处理告警通知
        
        Args:
            alert: 告警对象
        
        Returns:
            是否发送成功
        """
        if not FEISHU_AVAILABLE or not self.alert_enabled:
            return False
        
        try:
            success = send_system_alert(
                level=alert.level,
                title=alert.title,
                message=alert.message,
                details=json.loads(alert.metadata) if alert.metadata else {}
            )
            return success
        except Exception as e:
            logger.error(f"❌ 发送告警通知失败: {e}")
            # 尝试备用通知方式
            return self._try_fallback_notification(alert.title, alert.message)
    
    def _try_fallback_notification(self, title: str, message: str) -> bool:
        """
        尝试备用通知方式
        
        Args:
            title: 标题
            message: 内容
        
        Returns:
            是否有任何方式成功
        """
        if not self._fallback_handlers:
            logger.warning("⚠️ 没有配置备用通知方式")
            return False
        
        success = False
        for handler in self._fallback_handlers:
            try:
                if handler(title, message):
                    success = True
                    logger.info("✅ 备用通知方式成功")
                    break
            except Exception as e:
                logger.error(f"❌ 备用通知方式失败: {e}")
        
        return success
    
    def add_fallback_handler(self, handler: Callable[[str, str], bool]):
        """
        添加备用通知处理器
        
        Args:
            handler: 处理函数,接收title和message,返回是否成功
        """
        self._fallback_handlers.append(handler)
        logger.info("✅ 已添加备用通知处理器")
    
    def register_tool_checker(self, name: str, checker: Callable[[], Dict[str, Any]]):
        """
        注册工具检查器
        
        Args:
            name: 工具名称
            checker: 检查函数,返回包含status等信息的字典
        """
        self._tool_checkers[name] = checker
        logger.info(f"✅ 已注册工具检查器: {name}")
    
    def check_tools_health(self) -> Dict[str, Any]:
        """
        检查所有工具健康状态
        
        Returns:
            检查结果
        """
        results = {
            "checked_at": datetime.now().isoformat(),
            "tools": {},
            "failed_tools": [],
            "all_healthy": True
        }
        
        for name, checker in self._tool_checkers.items():
            try:
                status = checker()
                is_healthy = status.get("status") == "up"
                
                results["tools"][name] = {
                    "status": status.get("status", "unknown"),
                    "latency_ms": status.get("latency_ms"),
                    "message": status.get("message", ""),
                    "last_success": status.get("last_success")
                }
                
                if not is_healthy:
                    results["failed_tools"].append(name)
                    results["all_healthy"] = False
                    
                    # 发送宕机告警
                    if self.alert_enabled and FEISHU_AVAILABLE:
                        send_tool_down_alert(
                            tool_name=name,
                            error=status.get("message", "未知错误"),
                            last_success_time=status.get("last_success")
                        )
                    
                    # 同时记录到告警管理器
                    if self._alert_manager:
                        self._alert_manager.create_alert(
                            level="error",
                            title=f"工具宕机: {name}",
                            message=status.get("message", ""),
                            source=name,
                            immediate=True
                        )
                
            except Exception as e:
                logger.error(f"❌ 检查工具 {name} 时出错: {e}")
                results["tools"][name] = {
                    "status": "error",
                    "message": str(e)
                }
                results["failed_tools"].append(name)
                results["all_healthy"] = False
        
        self._tool_status_cache = results["tools"]
        self._last_check_time = datetime.now()
        
        return results
    
    def send_daily_report(self):
        """发送每日状态报告"""
        logger.info("📤 开始生成每日状态报告...")
        
        if not FEISHU_AVAILABLE:
            logger.error("❌ 飞书通知模块不可用")
            return False
        
        try:
            # 获取系统运行时间(简化版)
            uptime = "未知"
            if self._last_check_time:
                delta = datetime.now() - self._last_check_time
                uptime = f"{delta.days}天 {delta.seconds // 3600}小时"
            
            # 构建工具状态
            tools_status = {}
            for name, status in self._tool_status_cache.items():
                tools_status[name] = status.get("status", "unknown")
            
            # 如果没有缓存,执行一次检查
            if not tools_status and self._tool_checkers:
                health = self.check_tools_health()
                for name, status in health["tools"].items():
                    tools_status[name] = status.get("status", "unknown")
            
            # 获取告警统计
            alert_summary = None
            if self._alert_manager:
                stats = self._alert_manager.get_stats(hours=24)
                alert_summary = {
                    "total_alerts": stats.get("total", 0),
                    "by_level": stats.get("by_level", {})
                }
            
            # 发送报告
            success = send_daily_status_report(
                system_status={
                    "uptime": uptime,
                    "tools_status": tools_status,
                    "data_freshness": "实时",
                    "last_trade_time": "--"
                },
                trading_summary=None,  # 可以从交易数据库获取
                alert_summary=alert_summary
            )
            
            if success:
                logger.info("✅ 每日状态报告发送成功")
            else:
                logger.error("❌ 每日状态报告发送失败")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 生成每日报告时出错: {e}")
            return False
    
    def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("⚠️ 调度器已在运行中")
            return
        
        logger.info("🚀 启动通知调度器...")
        
        # 解析每日报告时间
        try:
            hour, minute = map(int, self.daily_report_time.split(':'))
        except ValueError:
            logger.warning(f"⚠️ 无效的DAILY_REPORT_TIME格式: {self.daily_report_time}, 使用默认值08:00")
            hour, minute = 8, 0
        
        if APSCHEDULER_AVAILABLE:
            # 添加每日报告任务
            self.scheduler.add_job(
                self.send_daily_report,
                trigger=CronTrigger(hour=hour, minute=minute),
                id='daily_report',
                name='每日状态报告',
                replace_existing=True
            )
            
            # 添加工具健康检查任务(每5分钟)
            if self._tool_checkers:
                self.scheduler.add_job(
                    self.check_tools_health,
                    trigger='interval',
                    minutes=5,
                    id='health_check',
                    name='工具健康检查',
                    replace_existing=True
                )
            
            self.scheduler.start()
        else:
            # 使用简单调度器
            self.scheduler.schedule_daily(hour, minute, self.send_daily_report)
            if self._tool_checkers:
                self.scheduler.schedule_interval(300, self.check_tools_health)  # 5分钟
            self.scheduler.start()
        
        self.running = True
        logger.info(f"✅ 调度器已启动")
        logger.info(f"   📅 每日报告时间: {hour:02d}:{minute:02d}")
        logger.info(f"   🔔 告警功能: {'启用' if self.alert_enabled else '禁用'}")
        logger.info(f"   🔧 监控工具数: {len(self._tool_checkers)}")
    
    def stop(self):
        """停止调度器"""
        if not self.running:
            return
        
        logger.info("🛑 停止通知调度器...")
        
        if APSCHEDULER_AVAILABLE and self.scheduler:
            self.scheduler.shutdown()
        elif hasattr(self.scheduler, 'stop'):
            self.scheduler.stop()
        
        self.running = False
        logger.info("✅ 调度器已停止")
    
    def get_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        return {
            "running": self.running,
            "alert_enabled": self.alert_enabled,
            "daily_report_time": self.daily_report_time,
            "tools_registered": list(self._tool_checkers.keys()),
            "last_check_time": self._last_check_time.isoformat() if self._last_check_time else None,
            "tool_status_cache": self._tool_status_cache,
            "apscheduler_available": APSCHEDULER_AVAILABLE,
            "feishu_available": FEISHU_AVAILABLE,
            "alert_manager_available": ALERT_MANAGER_AVAILABLE
        }


class SimpleScheduler:
    """简单调度器(APScheduler的替代品)"""
    
    def __init__(self):
        self._jobs = []
        self._running = False
        self._thread = None
    
    def schedule_daily(self, hour: int, minute: int, func: Callable):
        """调度每日任务"""
        self._jobs.append({
            'type': 'daily',
            'hour': hour,
            'minute': minute,
            'func': func,
            'last_run': None
        })
    
    def schedule_interval(self, seconds: int, func: Callable):
        """调度间隔任务"""
        self._jobs.append({
            'type': 'interval',
            'interval': seconds,
            'func': func,
            'last_run': None
        })
    
    def start(self):
        """启动调度器"""
        import threading
        self._running = True
        self._thread = threading.Thread(target=self._run)
        self._thread.daemon = True
        self._thread.start()
    
    def stop(self):
        """停止调度器"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def _run(self):
        """主循环"""
        while self._running:
            now = datetime.now()
            
            for job in self._jobs:
                should_run = False
                
                if job['type'] == 'daily':
                    # 检查是否是目标时间且今天未运行过
                    if (now.hour == job['hour'] and 
                        now.minute == job['minute'] and
                        (job['last_run'] is None or 
                         job['last_run'].date() != now.date())):
                        should_run = True
                
                elif job['type'] == 'interval':
                    # 检查是否达到间隔时间
                    if (job['last_run'] is None or 
                        (now - job['last_run']).total_seconds() >= job['interval']):
                        should_run = True
                
                if should_run:
                    try:
                        job['func']()
                        job['last_run'] = now
                    except Exception as e:
                        logger.error(f"❌ 任务执行失败: {e}")
            
            time.sleep(30)  # 每30秒检查一次


# ==================== 便捷函数 ====================

_scheduler_instance: Optional[NotificationScheduler] = None


def get_scheduler() -> NotificationScheduler:
    """获取全局调度器实例"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = NotificationScheduler()
    return _scheduler_instance


def start_notification_service():
    """启动通知服务"""
    scheduler = get_scheduler()
    scheduler.start()
    return scheduler


def stop_notification_service():
    """停止通知服务"""
    global _scheduler_instance
    if _scheduler_instance:
        _scheduler_instance.stop()
        _scheduler_instance = None


def register_tool(name: str, checker: Callable[[], Dict[str, Any]]):
    """
    注册工具检查器(便捷函数)
    
    Args:
        name: 工具名称
        checker: 检查函数
    """
    scheduler = get_scheduler()
    scheduler.register_tool_checker(name, checker)


def send_immediate_alert(
    level: str,
    title: str,
    message: str,
    source: str = ""
):
    """
    发送即时告警(便捷函数)
    
    Args:
        level: 告警级别
        title: 标题
        message: 内容
        source: 来源
    """
    scheduler = get_scheduler()
    if scheduler._alert_manager:
        scheduler._alert_manager.create_alert(
            level=level,
            title=title,
            message=message,
            source=source,
            immediate=True
        )
    elif FEISHU_AVAILABLE:
        send_system_alert(level, title, message)


if __name__ == "__main__":
    # 测试
    print("\n🧪 测试通知调度器\n")
    
    # 创建调度器
    scheduler = NotificationScheduler()
    
    # 注册测试工具检查器
    def test_checker_1():
        return {
            "status": "up",
            "latency_ms": 150,
            "message": "正常",
            "last_success": datetime.now().isoformat()
        }
    
    def test_checker_2():
        # 模拟故障
        return {
            "status": "down",
            "latency_ms": None,
            "message": "Connection refused",
            "last_success": (datetime.now() - timedelta(hours=2)).isoformat()
        }
    
    scheduler.register_tool_checker("test_tool_1", test_checker_1)
    scheduler.register_tool_checker("test_tool_2", test_checker_2)
    
    # 添加备用通知处理器(打印到控制台)
    def console_fallback(title: str, message: str) -> bool:
        print(f"\n[备用通知] {title}")
        print(f"{message}\n")
        return True
    
    scheduler.add_fallback_handler(console_fallback)
    
    # 检查工具健康状态
    print("1. 测试工具健康检查")
    health = scheduler.check_tools_health()
    print(f"   检查结果: {json.dumps(health, indent=2, default=str)}")
    
    # 测试发送每日报告
    print("\n2. 测试发送每日报告")
    scheduler.send_daily_report()
    
    # 获取状态
    print("\n3. 获取调度器状态")
    status = scheduler.get_status()
    print(f"   状态: {json.dumps(status, indent=2, default=str)}")
    
    # 测试启动调度器(10秒后自动停止)
    print("\n4. 测试启动调度器(10秒后停止)")
    scheduler.start()
    
    try:
        time.sleep(10)
    except KeyboardInterrupt:
        pass
    finally:
        scheduler.stop()
    
    print("\n✅ 测试完成")
