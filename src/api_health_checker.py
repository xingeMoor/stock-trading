"""
API 定时检测脚本
每 5 分钟自动检测所有 API 端点
异常时记录日志并告警

功能:
- 定时检测所有 Web 服务和 API 端点
- 记录检测结果到日志文件
- 异常时发送告警通知
- 生成健康状态报告

使用方式:
    python src/api_health_checker.py
    
或作为后台服务运行:
    nohup python src/api_health_checker.py &
"""
import os
import sys
import time
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import threading


# ============ 配置 ============
@dataclass
class Config:
    """配置类"""
    # 服务配置
    SERVICES = {
        "trading_monitor": {
            "url": "http://localhost:5001",
            "name": "模拟交易监控",
            "endpoints": ["/", "/api/health"],
        },
        "backtest_dashboard": {
            "url": "http://localhost:5005",
            "name": "回测分析面板",
            "endpoints": ["/", "/api/batches"],
        },
        "system_status": {
            "url": "http://localhost:5006",
            "name": "系统状态监控",
            "endpoints": ["/", "/api/status"],
        },
    }
    
    # 检测间隔（秒）
    CHECK_INTERVAL = 300  # 5 分钟
    
    # 超时时间（秒）
    TIMEOUT = 10
    
    # 日志配置
    LOG_DIR = "logs"
    LOG_FILE = "api_health_check.log"
    LOG_LEVEL = logging.INFO
    
    # 告警配置
    ALERT_THRESHOLD = 2  # 连续失败次数达到阈值时告警
    ALERT_COOLDOWN = 600  # 告警冷却时间（秒）
    
    # 状态报告
    REPORT_FILE = "api_health_status.json"


# ============ 数据类 ============
@dataclass
class CheckResult:
    """检测结果"""
    service_name: str
    endpoint: str
    status_code: int
    response_time: float  # ms
    success: bool
    error: Optional[str]
    timestamp: str


@dataclass
class ServiceStatus:
    """服务状态"""
    name: str
    url: str
    available: bool
    last_check: str
    consecutive_failures: int
    avg_response_time: float
    last_error: Optional[str]


# ============ 日志配置 ============
def setup_logging(config: Config) -> logging.Logger:
    """设置日志"""
    # 创建日志目录
    os.makedirs(config.LOG_DIR, exist_ok=True)
    
    log_path = os.path.join(config.LOG_DIR, config.LOG_FILE)
    
    # 配置日志
    logging.basicConfig(
        level=config.LOG_LEVEL,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger("APIHealthChecker")


# ============ 健康检查器 ============
class APIHealthChecker:
    """API 健康检查器"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.logger = setup_logging(self.config)
        self.session = requests.Session()
        
        # 状态跟踪
        self.service_status: Dict[str, ServiceStatus] = {}
        self.failure_counts: Dict[str, int] = {}
        self.last_alert_time: Dict[str, float] = {}
        
        # 历史响应时间（用于计算平均值）
        self.response_times: Dict[str, List[float]] = {
            service: [] for service in self.config.SERVICES
        }
        
        # 初始化状态
        for service_key, service_info in self.config.SERVICES.items():
            self.service_status[service_key] = ServiceStatus(
                name=service_info["name"],
                url=service_info["url"],
                available=False,
                last_check="",
                consecutive_failures=0,
                avg_response_time=0.0,
                last_error=None
            )
            self.failure_counts[service_key] = 0
        
        self.logger.info("API 健康检查器初始化完成")
    
    def check_endpoint(self, url: str, timeout: int = None) -> CheckResult:
        """
        检查单个端点
        
        Args:
            url: 端点 URL
            timeout: 超时时间
        
        Returns:
            CheckResult: 检测结果
        """
        timeout = timeout or self.config.TIMEOUT
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        result = CheckResult(
            service_name="",
            endpoint=url,
            status_code=0,
            response_time=0.0,
            success=False,
            error=None,
            timestamp=timestamp
        )
        
        try:
            start_time = time.time()
            response = self.session.get(url, timeout=timeout)
            elapsed = (time.time() - start_time) * 1000  # ms
            
            result.status_code = response.status_code
            result.response_time = elapsed
            result.success = response.status_code == 200
            
        except requests.exceptions.ConnectionError as e:
            result.error = f"ConnectionError: {str(e)}"
        except requests.exceptions.Timeout:
            result.error = "Timeout"
        except Exception as e:
            result.error = f"Unexpected error: {str(e)}"
        
        return result
    
    def check_service(self, service_key: str) -> ServiceStatus:
        """
        检查服务健康状态
        
        Args:
            service_key: 服务标识
        
        Returns:
            ServiceStatus: 服务状态
        """
        service_info = self.config.SERVICES.get(service_key)
        if not service_info:
            raise ValueError(f"未知服务：{service_key}")
        
        base_url = service_info["url"]
        endpoints = service_info["endpoints"]
        
        # 检查所有端点
        results = []
        for endpoint in endpoints:
            url = f"{base_url}{endpoint}"
            result = self.check_endpoint(url)
            result.service_name = service_info["name"]
            results.append(result)
            
            if result.success:
                break  # 有一个端点成功即可
        
        # 更新状态
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = self.service_status[service_key]
        
        # 判断服务是否可用
        any_success = any(r.success for r in results)
        status.available = any_success
        status.last_check = timestamp
        
        if any_success:
            # 成功：重置失败计数
            self.failure_counts[service_key] = 0
            status.consecutive_failures = 0
            status.last_error = None
            
            # 记录响应时间
            successful_results = [r for r in results if r.success]
            if successful_results:
                avg_time = sum(r.response_time for r in successful_results) / len(successful_results)
                self.response_times[service_key].append(avg_time)
                # 保留最近 10 次
                if len(self.response_times[service_key]) > 10:
                    self.response_times[service_key] = self.response_times[service_key][-10:]
                status.avg_response_time = sum(self.response_times[service_key]) / len(self.response_times[service_key])
        else:
            # 失败：增加失败计数
            self.failure_counts[service_key] += 1
            status.consecutive_failures = self.failure_counts[service_key]
            status.last_error = results[0].error if results else "Unknown error"
            
            self.logger.warning(
                f"服务 {service_info['name']} 检查失败 "
                f"(连续失败 {status.consecutive_failures} 次): {status.last_error}"
            )
            
            # 检查是否需要告警
            self._check_alert(service_key, status, results)
        
        return status
    
    def _check_alert(self, service_key: str, status: ServiceStatus, results: List[CheckResult]):
        """
        检查是否需要发送告警
        
        Args:
            service_key: 服务标识
            status: 服务状态
            results: 检测结果列表
        """
        # 检查是否达到告警阈值
        if status.consecutive_failures < self.config.ALERT_THRESHOLD:
            return
        
        # 检查冷却时间
        now = time.time()
        last_alert = self.last_alert_time.get(service_key, 0)
        if now - last_alert < self.config.ALERT_COOLDOWN:
            return
        
        # 发送告警
        self._send_alert(service_key, status, results)
        self.last_alert_time[service_key] = now
    
    def _send_alert(self, service_key: str, status: ServiceStatus, results: List[CheckResult]):
        """
        发送告警通知
        
        Args:
            service_key: 服务标识
            status: 服务状态
            results: 检测结果列表
        """
        alert_message = (
            f"🚨 API 服务告警\n"
            f"服务：{status.name}\n"
            f"URL: {status.url}\n"
            f"状态：不可用\n"
            f"连续失败：{status.consecutive_failures} 次\n"
            f"错误：{status.last_error}\n"
            f"时间：{status.last_check}"
        )
        
        self.logger.error(alert_message)
        
        # TODO: 集成飞书告警
        # self._send_feishu_alert(alert_message)
    
    def _send_feishu_alert(self, message: str):
        """
        发送飞书告警（待实现）
        
        Args:
            message: 告警消息
        """
        # 这里可以集成飞书 Webhook
        # webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
        # if webhook_url:
        #     requests.post(webhook_url, json={"msg_type": "text", "content": {"text": message}})
        pass
    
    def check_all_services(self) -> Dict[str, ServiceStatus]:
        """
        检查所有服务
        
        Returns:
            dict: 服务状态字典
        """
        self.logger.info("开始检查所有服务...")
        
        for service_key in self.config.SERVICES:
            try:
                status = self.check_service(service_key)
                self.service_status[service_key] = status
                
                status_str = "✓" if status.available else "✗"
                self.logger.info(
                    f"{status_str} {status.name}: "
                    f"{'可用' if status.available else '不可用'} "
                    f"(响应时间：{status.avg_response_time:.2f}ms)"
                )
            except Exception as e:
                self.logger.error(f"检查服务 {service_key} 时出错：{e}")
        
        return self.service_status
    
    def generate_report(self) -> Dict[str, Any]:
        """
        生成健康状态报告
        
        Returns:
            dict: 报告数据
        """
        report = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "services": {},
            "summary": {
                "total": len(self.config.SERVICES),
                "available": sum(1 for s in self.service_status.values() if s.available),
                "unavailable": sum(1 for s in self.service_status.values() if not s.available),
            }
        }
        
        for service_key, status in self.service_status.items():
            report["services"][service_key] = asdict(status)
        
        return report
    
    def save_report(self, report: Dict[str, Any] = None):
        """
        保存报告到文件
        
        Args:
            report: 报告数据（可选，不传则自动生成）
        """
        if report is None:
            report = self.generate_report()
        
        report_path = os.path.join(self.config.LOG_DIR, self.config.REPORT_FILE)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"报告已保存：{report_path}")
    
    def run_once(self):
        """运行一次检查"""
        self.check_all_services()
        report = self.generate_report()
        self.save_report(report)
    
    def run_continuous(self):
        """持续运行检查"""
        self.logger.info(f"启动持续检查模式（间隔：{self.config.CHECK_INTERVAL}秒）")
        
        try:
            while True:
                self.run_once()
                time.sleep(self.config.CHECK_INTERVAL)
        except KeyboardInterrupt:
            self.logger.info("收到中断信号，停止检查")
        finally:
            self.session.close()


# ============ 主函数 ============
def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="API 健康检查器")
    parser.add_argument(
        "--once",
        action="store_true",
        help="只运行一次检查"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="检查间隔（秒），默认 300"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="请求超时时间（秒），默认 10"
    )
    
    args = parser.parse_args()
    
    # 创建配置
    config = Config()
    config.CHECK_INTERVAL = args.interval
    config.TIMEOUT = args.timeout
    
    # 创建检查器
    checker = APIHealthChecker(config)
    
    if args.once:
        # 只运行一次
        checker.run_once()
        print("\n检查结果:")
        for service_key, status in checker.service_status.items():
            status_str = "✓ 可用" if status.available else "✗ 不可用"
            print(f"  {status.name}: {status_str}")
    else:
        # 持续运行
        checker.run_continuous()


if __name__ == "__main__":
    main()
