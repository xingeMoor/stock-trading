"""
执行监控系统 (Execution Monitor)

负责监控订单执行状态、处理成交回报、分析执行质量。

核心功能:
- 成交回报处理
- 异常订单处理
- 执行质量分析
- 实时监控仪表盘
"""

import asyncio
import logging
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ExecutionQuality:
    """执行质量评级"""
    EXCELLENT = "EXCELLENT"  # 滑点 < 5bps
    GOOD = "GOOD"            # 滑点 5-15bps
    FAIR = "FAIR"            # 滑点 15-30bps
    POOR = "POOR"            # 滑点 > 30bps


class AlertLevel:
    """告警级别"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ExecutionMetrics:
    """执行质量指标"""
    order_id: str
    symbol: str
    side: str
    total_quantity: Decimal
    filled_quantity: Decimal
    avg_fill_price: Decimal
    decision_price: Decimal  # 决策时市价
    arrival_price: Decimal   # 订单到达市场时价格
    
    # 核心指标
    slippage_bps: Decimal = Decimal('0')  # 滑点 (基点)
    fill_rate: Decimal = Decimal('0')      # 成交率
    market_impact_bps: Decimal = Decimal('0')  # 市场冲击
    implementation_shortfall_bps: Decimal = Decimal('0')  # 执行成本
    
    # 时间指标
    execution_time_seconds: float = 0.0
    first_fill_time_seconds: float = 0.0
    
    # 成本指标
    total_commission: Decimal = Decimal('0')
    total_cost: Decimal = Decimal('0')
    
    # 质量评级
    quality_rating: str = ""
    
    def calculate_metrics(self):
        """计算所有指标"""
        # 成交率
        if self.total_quantity > 0:
            self.fill_rate = (self.filled_quantity / self.total_quantity * 100).quantize(Decimal('0.01'))
        
        # 滑点 (相对于决策价格)
        if self.decision_price > 0 and self.avg_fill_price > 0:
            if self.side == "BUY":
                self.slippage_bps = ((self.avg_fill_price - self.decision_price) / self.decision_price * 10000).quantize(Decimal('0.01'))
            else:  # SELL
                self.slippage_bps = ((self.decision_price - self.avg_fill_price) / self.decision_price * 10000).quantize(Decimal('0.01'))
        
        # 市场冲击 (相对于到达价格)
        if self.arrival_price > 0 and self.avg_fill_price > 0:
            if self.side == "BUY":
                self.market_impact_bps = ((self.avg_fill_price - self.arrival_price) / self.arrival_price * 10000).quantize(Decimal('0.01'))
            else:
                self.market_impact_bps = ((self.arrival_price - self.avg_fill_price) / self.arrival_price * 10000).quantize(Decimal('0.01'))
        
        # 执行成本 (Implementation Shortfall)
        # IS = (实际成交金额 - 决策金额) / 决策金额
        if self.decision_price > 0 and self.total_quantity > 0:
            decision_value = self.decision_price * self.filled_quantity
            actual_value = self.avg_fill_price * self.filled_quantity + self.total_commission
            
            if self.side == "BUY":
                self.implementation_shortfall_bps = ((actual_value - decision_value) / decision_value * 10000).quantize(Decimal('0.01'))
            else:
                self.implementation_shortfall_bps = ((decision_value - actual_value) / decision_value * 10000).quantize(Decimal('0.01'))
        
        # 总成本
        self.total_cost = self.total_commission + abs(self.slippage_bps / 10000 * self.decision_price * self.filled_quantity)
        
        # 质量评级
        self.quality_rating = self._calculate_quality_rating()
    
    def _calculate_quality_rating(self) -> str:
        """计算质量评级"""
        abs_slippage = abs(self.slippage_bps)
        
        if abs_slippage < 5:
            return ExecutionQuality.EXCELLENT
        elif abs_slippage < 15:
            return ExecutionQuality.GOOD
        elif abs_slippage < 30:
            return ExecutionQuality.FAIR
        else:
            return ExecutionQuality.POOR
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'side': self.side,
            'total_quantity': str(self.total_quantity),
            'filled_quantity': str(self.filled_quantity),
            'avg_fill_price': str(self.avg_fill_price),
            'decision_price': str(self.decision_price),
            'arrival_price': str(self.arrival_price),
            'slippage_bps': str(self.slippage_bps),
            'fill_rate': str(self.fill_rate),
            'market_impact_bps': str(self.market_impact_bps),
            'implementation_shortfall_bps': str(self.implementation_shortfall_bps),
            'execution_time_seconds': self.execution_time_seconds,
            'first_fill_time_seconds': self.first_fill_time_seconds,
            'total_commission': str(self.total_commission),
            'total_cost': str(self.total_cost),
            'quality_rating': self.quality_rating,
        }


@dataclass
class Alert:
    """执行告警"""
    alert_id: str
    level: str
    category: str
    message: str
    order_id: Optional[str] = None
    symbol: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'alert_id': self.alert_id,
            'level': self.level,
            'category': self.category,
            'message': self.message,
            'order_id': self.order_id,
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
        }


@dataclass
class OrderAnomaly:
    """订单异常"""
    anomaly_id: str
    order_id: str
    anomaly_type: str
    description: str
    detected_at: datetime
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    status: str = "OPEN"  # OPEN, INVESTIGATING, RESOLVED, CLOSED
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'anomaly_id': self.anomaly_id,
            'order_id': self.order_id,
            'anomaly_type': self.anomaly_type,
            'description': self.description,
            'detected_at': self.detected_at.isoformat(),
            'severity': self.severity,
            'status': self.status,
            'resolution': self.resolution,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
        }


class AnomalyDetector:
    """
    异常检测器
    
    检测以下异常类型:
    - 延迟成交
    - 部分成交停滞
    - 价格异常
    - 重复成交
    - API 错误
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 检测阈值
        self.fill_timeout_seconds = self.config.get('fill_timeout_seconds', 300)  # 5 分钟
        self.partial_stall_seconds = self.config.get('partial_stall_seconds', 120)  # 2 分钟
        self.price_deviation_threshold = Decimal(str(self.config.get('price_deviation_threshold', 0.02)))  # 2%
        self.duplicate_window_seconds = self.config.get('duplicate_window_seconds', 60)  # 1 分钟
        
        # 最近成交记录 (用于检测重复)
        self.recent_fills: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    
    def detect_delayed_fill(self, order: Any, current_time: datetime) -> Optional[OrderAnomaly]:
        """检测延迟成交"""
        if not order.submitted_at:
            return None
        
        elapsed = (current_time - order.submitted_at).total_seconds()
        
        if elapsed > self.fill_timeout_seconds and not order.is_complete():
            return OrderAnomaly(
                anomaly_id=f"delayed_{order.order_id}",
                order_id=order.order_id,
                anomaly_type="DELAYED_FILL",
                description=f"订单提交后 {elapsed:.0f} 秒仍未完全成交",
                detected_at=current_time,
                severity="MEDIUM",
            )
        
        return None
    
    def detect_partial_stall(self, order: Any, current_time: datetime) -> Optional[OrderAnomaly]:
        """检测部分成交停滞"""
        if order.status != "PARTIALLY_FILLED":
            return None
        
        # 找到最后一次成交时间
        last_fill_time = None
        for slice in order.slices:
            if slice.fills:
                for fill in slice.fills:
                    fill_time = datetime.fromisoformat(fill['timestamp'])
                    if last_fill_time is None or fill_time > last_fill_time:
                        last_fill_time = fill_time
        
        if last_fill_time is None:
            return None
        
        stall_duration = (current_time - last_fill_time).total_seconds()
        
        if stall_duration > self.partial_stall_seconds:
            return OrderAnomaly(
                anomaly_id=f"stall_{order.order_id}",
                order_id=order.order_id,
                anomaly_type="PARTIAL_STALL",
                description=f"订单在部分成交状态停滞 {stall_duration:.0f} 秒",
                detected_at=current_time,
                severity="MEDIUM",
            )
        
        return None
    
    def detect_price_anomaly(
        self,
        order: Any,
        market_price: Decimal,
        current_time: datetime,
    ) -> Optional[OrderAnomaly]:
        """检测价格异常"""
        if order.avg_price <= 0 or market_price <= 0:
            return None
        
        # 计算价格偏离
        deviation = abs(order.avg_price - market_price) / market_price
        
        if deviation > self.price_deviation_threshold:
            return OrderAnomaly(
                anomaly_id=f"price_{order.order_id}",
                order_id=order.order_id,
                anomaly_type="PRICE_ANOMALY",
                description=f"成交价偏离市场价 {deviation:.2%} (阈值：{self.price_deviation_threshold:.2%})",
                detected_at=current_time,
                severity="HIGH",
            )
        
        return None
    
    def detect_duplicate_fill(
        self,
        order: Any,
        fill: Dict[str, Any],
        current_time: datetime,
    ) -> Optional[OrderAnomaly]:
        """检测重复成交"""
        exec_id = fill.get('exec_id')
        
        if not exec_id:
            return None
        
        # 检查是否在时间窗口内已有相同 exec_id
        cutoff_time = current_time - timedelta(seconds=self.duplicate_window_seconds)
        
        for existing_fill in self.recent_fills[order.order_id]:
            existing_time = datetime.fromisoformat(existing_fill['timestamp'])
            if existing_time > cutoff_time and existing_fill.get('exec_id') == exec_id:
                return OrderAnomaly(
                    anomaly_id=f"duplicate_{exec_id}",
                    order_id=order.order_id,
                    anomaly_type="DUPLICATE_FILL",
                    description=f"检测到重复成交：{exec_id}",
                    detected_at=current_time,
                    severity="HIGH",
                )
        
        # 记录本次成交
        self.recent_fills[order.order_id].append(fill)
        
        # 清理旧记录
        self.recent_fills[order.order_id] = [
            f for f in self.recent_fills[order.order_id]
            if datetime.fromisoformat(f['timestamp']) > cutoff_time
        ]
        
        return None


class ExecutionAnalyzer:
    """
    执行质量分析器
    
    分析维度:
    - 按策略分析
    - 按标的分析
    - 按时间段分析
    - 按算法分析
    """
    
    def __init__(self):
        # 历史执行记录
        self.execution_history: List[ExecutionMetrics] = []
        
        # 聚合统计
        self.strategy_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'total_orders': 0,
            'avg_slippage_bps': Decimal('0'),
            'avg_fill_rate': Decimal('0'),
            'total_volume': Decimal('0'),
        })
        
        self.symbol_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'total_orders': 0,
            'avg_slippage_bps': Decimal('0'),
            'avg_fill_rate': Decimal('0'),
            'total_volume': Decimal('0'),
        })
        
        self.hourly_stats: Dict[int, Dict[str, Any]] = defaultdict(lambda: {
            'total_orders': 0,
            'avg_slippage_bps': Decimal('0'),
        })
    
    def add_execution(self, metrics: ExecutionMetrics):
        """添加执行记录"""
        self.execution_history.append(metrics)
        
        # 更新策略统计
        strategy_id = metrics.order_id  # 实际应从 metadata 获取
        self._update_stats(self.strategy_stats[strategy_id], metrics)
        
        # 更新标的统计
        self._update_stats(self.symbol_stats[metrics.symbol], metrics)
        
        # 更新小时统计
        hour = metrics.decision_price.hour if hasattr(metrics.decision_price, 'hour') else datetime.now().hour
        self._update_stats(self.hourly_stats[hour], metrics)
    
    def _update_stats(self, stats: Dict[str, Any], metrics: ExecutionMetrics):
        """更新统计信息"""
        n = stats['total_orders']
        
        stats['total_orders'] += 1
        stats['avg_slippage_bps'] = (stats['avg_slippage_bps'] * n + metrics.slippage_bps) / (n + 1)
        stats['avg_fill_rate'] = (stats['avg_fill_rate'] * n + metrics.fill_rate) / (n + 1)
        stats['total_volume'] += metrics.filled_quantity
    
    def get_strategy_ranking(self, metric: str = 'avg_slippage_bps') -> List[Tuple[str, Any]]:
        """获取策略排名"""
        ranking = [
            (strategy_id, stats[metric])
            for strategy_id, stats in self.strategy_stats.items()
        ]
        return sorted(ranking, key=lambda x: x[1])
    
    def get_symbol_ranking(self, metric: str = 'avg_slippage_bps') -> List[Tuple[str, Any]]:
        """获取标的排名"""
        ranking = [
            (symbol, stats[metric])
            for symbol, stats in self.symbol_stats.items()
        ]
        return sorted(ranking, key=lambda x: x[1], reverse=True)
    
    def get_best_trading_hours(self) -> List[Tuple[int, Any]]:
        """获取最佳交易时段"""
        ranking = [
            (hour, stats['avg_slippage_bps'])
            for hour, stats in self.hourly_stats.items()
        ]
        return sorted(ranking, key=lambda x: x[1])
    
    def get_quality_distribution(self) -> Dict[str, int]:
        """获取质量评级分布"""
        distribution = defaultdict(int)
        for metrics in self.execution_history:
            distribution[metrics.quality_rating] += 1
        return dict(distribution)
    
    def generate_report(self, period: str = 'daily') -> Dict[str, Any]:
        """生成执行质量报告"""
        if not self.execution_history:
            return {'error': 'No execution data'}
        
        # 过滤时间段
        now = datetime.now()
        if period == 'daily':
            cutoff = now - timedelta(days=1)
        elif period == 'weekly':
            cutoff = now - timedelta(weeks=1)
        elif period == 'monthly':
            cutoff = now - timedelta(days=30)
        else:
            cutoff = now - timedelta(days=1)
        
        recent_executions = [
            m for m in self.execution_history
            if m.decision_price > cutoff if hasattr(m.decision_price, '__gt__') else True
        ]
        
        if not recent_executions:
            recent_executions = self.execution_history
        
        # 计算汇总统计
        total_orders = len(recent_executions)
        avg_slippage = statistics.mean([float(m.slippage_bps) for m in recent_executions])
        avg_fill_rate = statistics.mean([float(m.fill_rate) for m in recent_executions])
        total_volume = sum([m.filled_quantity for m in recent_executions])
        
        # 质量分布
        quality_dist = defaultdict(int)
        for m in recent_executions:
            quality_dist[m.quality_rating] += 1
        
        return {
            'period': period,
            'total_orders': total_orders,
            'avg_slippage_bps': round(avg_slippage, 2),
            'avg_fill_rate': round(avg_fill_rate, 2),
            'total_volume': str(total_volume),
            'quality_distribution': dict(quality_dist),
            'best_strategy': self.get_strategy_ranking()[0] if self.strategy_stats else None,
            'worst_symbol': self.get_symbol_ranking()[0] if self.symbol_stats else None,
            'best_trading_hour': self.get_best_trading_hours()[0] if self.hourly_stats else None,
        }


class ExecutionMonitor:
    """
    执行监控器
    
    核心职责:
    1. 接收并处理成交回报
    2. 监控订单执行状态
    3. 检测异常订单
    4. 分析执行质量
    5. 生成监控报告和告警
    """
    
    def __init__(
        self,
        anomaly_config: Optional[Dict[str, Any]] = None,
        alert_thresholds: Optional[Dict[str, Any]] = None,
        on_alert: Optional[Callable[[Alert], None]] = None,
    ):
        """
        初始化执行监控器
        
        Args:
            anomaly_config: 异常检测配置
            alert_thresholds: 告警阈值配置
            on_alert: 告警回调函数
        """
        self.anomaly_detector = AnomalyDetector(anomaly_config)
        self.analyzer = ExecutionAnalyzer()
        self.on_alert = on_alert
        
        # 告警阈值
        self.alert_thresholds = alert_thresholds or {
            'slippage_warning_bps': 20,
            'slippage_critical_bps': 50,
            'fill_rate_warning': 80,
            'fill_rate_critical': 50,
        }
        
        # 订单监控
        self.monitored_orders: Dict[str, Dict[str, Any]] = {}
        
        # 执行指标存储
        self.execution_metrics: Dict[str, ExecutionMetrics] = {}
        
        # 告警历史
        self.alerts: List[Alert] = []
        
        # 异常历史
        self.anomalies: List[OrderAnomaly] = []
        
        # 运行状态
        self.is_running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # 统计信息
        self.stats = {
            'total_reports_processed': 0,
            'total_alerts': 0,
            'total_anomalies': 0,
            'alerts_by_level': defaultdict(int),
        }
        
        logger.info("执行监控器初始化完成")
    
    async def start(self):
        """启动监控器"""
        self.is_running = True
        self._monitor_task = asyncio.create_task(self._continuous_monitoring())
        logger.info("执行监控器已启动")
    
    async def stop(self):
        """停止监控器"""
        self.is_running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("执行监控器已停止")
    
    async def _continuous_monitoring(self):
        """持续监控循环"""
        while self.is_running:
            try:
                await asyncio.sleep(10)  # 每 10 秒检查一次
                self._check_active_orders()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监控循环出错：{e}")
    
    def _check_active_orders(self):
        """检查活跃订单"""
        current_time = datetime.now()
        
        for order_id, order_info in list(self.monitored_orders.items()):
            order = order_info.get('order')
            if not order:
                continue
            
            # 跳过已完成的订单
            if order.status in ["FILLED", "CANCELLED", "REJECTED"]:
                continue
            
            # 检测延迟成交
            anomaly = self.anomaly_detector.detect_delayed_fill(order, current_time)
            if anomaly:
                self._handle_anomaly(anomaly)
            
            # 检测部分成交停滞
            anomaly = self.anomaly_detector.detect_partial_stall(order, current_time)
            if anomaly:
                self._handle_anomaly(anomaly)
    
    def process_execution_report(self, report: Any, order: Any, decision_price: Decimal):
        """
        处理执行回报
        
        Args:
            report: 执行报告 (ExecutionReport)
            order: 订单对象
            decision_price: 决策时价格
        """
        self.stats['total_reports_processed'] += 1
        
        logger.debug(f"处理执行回报：{report.order_id} - {report.quantity}@{report.price}")
        
        # 1. 检测重复成交
        current_time = datetime.now()
        anomaly = self.anomaly_detector.detect_duplicate_fill(
            order,
            report.to_dict() if hasattr(report, 'to_dict') else vars(report),
            current_time,
        )
        if anomaly:
            self._handle_anomaly(anomaly)
        
        # 2. 检测价格异常
        market_price = report.price  # 实际应从市场数据获取
        anomaly = self.anomaly_detector.detect_price_anomaly(order, market_price, current_time)
        if anomaly:
            self._handle_anomaly(anomaly)
        
        # 3. 计算执行指标
        if order.order_id not in self.execution_metrics:
            metrics = ExecutionMetrics(
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                total_quantity=order.total_quantity,
                filled_quantity=order.filled_quantity,
                avg_fill_price=order.avg_price,
                decision_price=decision_price,
                arrival_price=decision_price,  # 简化处理
            )
            
            if order.submitted_at:
                metrics.first_fill_time_seconds = (current_time - order.submitted_at).total_seconds()
            
            self.execution_metrics[order.order_id] = metrics
        else:
            metrics = self.execution_metrics[order.order_id]
            metrics.filled_quantity = order.filled_quantity
            metrics.avg_fill_price = order.avg_price
        
        # 4. 更新订单监控信息
        self.monitored_orders[order.order_id] = {
            'order': order,
            'decision_price': decision_price,
            'last_update': current_time,
            'reports': self.monitored_orders.get(order.order_id, {}).get('reports', []) + [report],
        }
        
        # 5. 检查告警
        self._check_alerts(metrics)
    
    def finalize_order(self, order: Any, decision_price: Decimal):
        """
        完成订单的最终处理
        
        Args:
            order: 订单对象
            decision_price: 决策时价格
        """
        if order.order_id not in self.execution_metrics:
            metrics = ExecutionMetrics(
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                total_quantity=order.total_quantity,
                filled_quantity=order.filled_quantity,
                avg_fill_price=order.avg_price,
                decision_price=decision_price,
                arrival_price=decision_price,
            )
            self.execution_metrics[order.order_id] = metrics
        else:
            metrics = self.execution_metrics[order.order_id]
        
        # 设置最终值
        metrics.filled_quantity = order.filled_quantity
        metrics.avg_fill_price = order.avg_price
        
        if order.submitted_at and order.completed_at:
            metrics.execution_time_seconds = (order.completed_at - order.submitted_at).total_seconds()
        elif order.submitted_at:
            metrics.execution_time_seconds = (datetime.now() - order.submitted_at).total_seconds()
        
        # 计算所有指标
        metrics.calculate_metrics()
        
        # 添加到分析器
        self.analyzer.add_execution(metrics)
        
        logger.info(
            f"订单执行完成：{order.order_id} - "
            f"滑点 {metrics.slippage_bps}bps, "
            f"成交率 {metrics.fill_rate}%, "
            f"质量评级：{metrics.quality_rating}"
        )
        
        # 从监控中移除
        if order.order_id in self.monitored_orders:
            del self.monitored_orders[order.order_id]
    
    def _check_alerts(self, metrics: ExecutionMetrics):
        """检查并生成告警"""
        # 滑点告警
        if abs(metrics.slippage_bps) > self.alert_thresholds['slippage_critical_bps']:
            self._generate_alert(
                level=AlertLevel.CRITICAL,
                category="SLIPPAGE",
                message=f"滑点超过临界值：{metrics.slippage_bps}bps",
                order_id=metrics.order_id,
                symbol=metrics.symbol,
                metadata={'slippage_bps': str(metrics.slippage_bps)},
            )
        elif abs(metrics.slippage_bps) > self.alert_thresholds['slippage_warning_bps']:
            self._generate_alert(
                level=AlertLevel.WARNING,
                category="SLIPPAGE",
                message=f"滑点超过警告值：{metrics.slippage_bps}bps",
                order_id=metrics.order_id,
                symbol=metrics.symbol,
                metadata={'slippage_bps': str(metrics.slippage_bps)},
            )
        
        # 成交率告警
        if metrics.fill_rate < self.alert_thresholds['fill_rate_critical']:
            self._generate_alert(
                level=AlertLevel.CRITICAL,
                category="FILL_RATE",
                message=f"成交率低于临界值：{metrics.fill_rate}%",
                order_id=metrics.order_id,
                symbol=metrics.symbol,
                metadata={'fill_rate': str(metrics.fill_rate)},
            )
        elif metrics.fill_rate < self.alert_thresholds['fill_rate_warning']:
            self._generate_alert(
                level=AlertLevel.WARNING,
                category="FILL_RATE",
                message=f"成交率低于警告值：{metrics.fill_rate}%",
                order_id=metrics.order_id,
                symbol=metrics.symbol,
                metadata={'fill_rate': str(metrics.fill_rate)},
            )
    
    def _handle_anomaly(self, anomaly: OrderAnomaly):
        """处理异常"""
        self.anomalies.append(anomaly)
        self.stats['total_anomalies'] += 1
        
        logger.warning(f"检测到订单异常：{anomaly.anomaly_type} - {anomaly.description}")
        
        # 根据严重程度生成告警
        level_map = {
            'LOW': AlertLevel.INFO,
            'MEDIUM': AlertLevel.WARNING,
            'HIGH': AlertLevel.ERROR,
            'CRITICAL': AlertLevel.CRITICAL,
        }
        
        self._generate_alert(
            level=level_map.get(anomaly.severity, AlertLevel.WARNING),
            category="ANOMALY",
            message=anomaly.description,
            order_id=anomaly.order_id,
            metadata={
                'anomaly_type': anomaly.anomaly_type,
                'severity': anomaly.severity,
            },
        )
    
    def _generate_alert(
        self,
        level: str,
        category: str,
        message: str,
        order_id: Optional[str] = None,
        symbol: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """生成告警"""
        import uuid
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            level=level,
            category=category,
            message=message,
            order_id=order_id,
            symbol=symbol,
            metadata=metadata or {},
        )
        
        self.alerts.append(alert)
        self.stats['total_alerts'] += 1
        self.stats['alerts_by_level'][level] += 1
        
        logger.log(
            self._get_log_level(level),
            f"告警 [{level}] {category}: {message}"
        )
        
        # 触发回调
        if self.on_alert:
            try:
                self.on_alert(alert)
            except Exception as e:
                logger.error(f"告警回调执行失败：{e}")
    
    def _get_log_level(self, alert_level: str) -> int:
        """将告警级别转换为 logging 级别"""
        level_map = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.ERROR: logging.ERROR,
            AlertLevel.CRITICAL: logging.CRITICAL,
        }
        return level_map.get(alert_level, logging.INFO)
    
    def get_order_metrics(self, order_id: str) -> Optional[Dict[str, Any]]:
        """获取订单执行指标"""
        metrics = self.execution_metrics.get(order_id)
        if metrics:
            return metrics.to_dict()
        return None
    
    def get_active_orders(self) -> List[Dict[str, Any]]:
        """获取活跃订单列表"""
        return [
            {
                'order_id': order_id,
                'symbol': info['order'].symbol,
                'side': info['order'].side,
                'status': info['order'].status,
                'fill_rate': str(info['order'].get_fill_rate()),
                'last_update': info['last_update'].isoformat(),
            }
            for order_id, info in self.monitored_orders.items()
        ]
    
    def get_alerts(
        self,
        level: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """获取告警列表"""
        alerts = self.alerts
        if level:
            alerts = [a for a in alerts if a.level == level]
        return [a.to_dict() for a in alerts[-limit:]]
    
    def get_anomalies(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """获取异常列表"""
        anomalies = self.anomalies
        if status:
            anomalies = [a for a in anomalies if a.status == status]
        return [a.to_dict() for a in anomalies[-limit:]]
    
    def get_quality_report(self, period: str = 'daily') -> Dict[str, Any]:
        """获取执行质量报告"""
        return self.analyzer.generate_report(period)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表盘数据"""
        return {
            'summary': {
                'total_reports_processed': self.stats['total_reports_processed'],
                'total_alerts': self.stats['total_alerts'],
                'total_anomalies': self.stats['total_anomalies'],
                'active_orders': len(self.monitored_orders),
            },
            'alerts_by_level': dict(self.stats['alerts_by_level']),
            'active_orders': self.get_active_orders(),
            'recent_alerts': self.get_alerts(limit=10),
            'recent_anomalies': self.get_anomalies(limit=10),
            'quality_report': self.get_quality_report(),
        }


# 使用示例

if __name__ == "__main__":
    import asyncio
    
    async def main():
        # 创建监控器
        monitor = ExecutionMonitor(
            alert_thresholds={
                'slippage_warning_bps': 20,
                'slippage_critical_bps': 50,
            },
            on_alert=lambda alert: print(f"🚨 告警：{alert.level} - {alert.message}"),
        )
        
        # 启动监控器
        await monitor.start()
        
        # 模拟订单和执行回报
        class MockOrder:
            order_id = "test_order_001"
            signal_id = "test_signal_001"
            symbol = "AAPL"
            side = "BUY"
            total_quantity = Decimal('100')
            filled_quantity = Decimal('100')
            avg_price = Decimal('150.50')
            status = "FILLED"
            submitted_at = datetime.now() - timedelta(seconds=30)
            completed_at = datetime.now()
            slices = []
            
            def is_complete(self):
                return self.filled_quantity >= self.total_quantity
            
            def get_fill_rate(self):
                return (self.filled_quantity / self.total_quantity * 100).quantize(Decimal('0.01'))
        
        class MockReport:
            order_id = "test_order_001"
            quantity = Decimal('100')
            price = Decimal('150.50')
            
            def to_dict(self):
                return {
                    'exec_id': 'exec_001',
                    'quantity': str(self.quantity),
                    'price': str(self.price),
                    'timestamp': datetime.now().isoformat(),
                }
        
        order = MockOrder()
        report = MockReport()
        decision_price = Decimal('150.00')
        
        # 处理执行回报
        monitor.process_execution_report(report, order, decision_price)
        
        # 完成订单
        monitor.finalize_order(order, decision_price)
        
        # 获取执行指标
        metrics = monitor.get_order_metrics(order.order_id)
        print(f"\n执行指标：{metrics}")
        
        # 获取仪表盘数据
        dashboard = monitor.get_dashboard_data()
        print(f"\n仪表盘数据：{dashboard}")
        
        # 停止监控器
        await monitor.stop()
    
    asyncio.run(main())
