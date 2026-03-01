"""
交易执行器 - Order Executor
负责订单生成、发送、执行监控和成交回报

核心功能:
- 订单生成和验证
- 订单发送和执行
- 成交回报处理
- 执行质量分析
- 支持 A 股 T+1 和美股 T+0

Author: Q 脑 Risk-Agent
Date: 2026-03-01
"""

import uuid
import asyncio
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
import yaml


class OrderType(Enum):
    """订单类型"""
    MARKET = "MARKET"          # 市价单
    LIMIT = "LIMIT"            # 限价单
    STOP_LOSS = "STOP_LOSS"    # 止损单
    STOP_LIMIT = "STOP_LIMIT"  # 止损限价单


class OrderSide(Enum):
    """订单方向"""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"        # 待提交
    SUBMITTED = "submitted"    # 已提交
    PARTIALLY_FILLED = "partially_filled"  # 部分成交
    FILLED = "filled"          # 完全成交
    CANCELLED = "cancelled"    # 已取消
    REJECTED = "rejected"      # 已拒绝
    EXPIRED = "expired"        # 已过期


class MarketType(Enum):
    """市场类型"""
    A_SHARE = "A_SHARE"        # A 股 (T+1)
    US_STOCK = "US_STOCK"      # 美股 (T+0)


class TimeInForce(Enum):
    """订单有效期"""
    DAY = "DAY"                # 当日有效
    GTC = "GTC"                # 撤单前有效
    IOC = "IOC"                # 立即成交或取消
    FOK = "FOK"                # 全部成交或取消


@dataclass
class ExecutionConfig:
    """执行配置"""
    # 滑点控制
    max_slippage_pct: float = 0.01      # 最大滑点 1%
    limit_price_buffer: float = 0.005   # 限价单缓冲 0.5%
    
    # 分批执行
    batch_execution: bool = True
    max_batch_size: int = 5             # 每批最多 5 个订单
    batch_interval_sec: float = 2.0     # 批次间隔 2 秒
    
    # 最小交易金额
    min_trade_amount: Dict[str, float] = field(default_factory=lambda: {
        'A_SHARE': 100.0,
        'US_STOCK': 1.0
    })
    
    # 交易时间检查
    trading_time_check: bool = True
    
    # 重试配置
    max_retries: int = 3
    retry_delay_sec: float = 1.0
    
    @classmethod
    def from_yaml(cls, config_path: str) -> 'ExecutionConfig':
        """从 YAML 配置文件加载"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        exec_cfg = config.get('execution', {})
        slippage_cfg = exec_cfg.get('slippage', {})
        batch_cfg = exec_cfg.get('batch_execution', {})
        min_trade_cfg = exec_cfg.get('min_trade_amount', {})
        
        return cls(
            max_slippage_pct=slippage_cfg.get('max_slippage_pct', 0.01),
            limit_price_buffer=slippage_cfg.get('limit_price_buffer', 0.005),
            batch_execution=batch_cfg.get('enabled', True),
            max_batch_size=batch_cfg.get('max_batch_size', 5),
            batch_interval_sec=batch_cfg.get('batch_interval_sec', 2.0),
            min_trade_amount={
                'A_SHARE': min_trade_cfg.get('A_SHARE', 100.0),
                'US_STOCK': min_trade_cfg.get('US_STOCK', 1.0)
            },
            trading_time_check=exec_cfg.get('trading_time_check', True)
        )


@dataclass
class Order:
    """订单对象"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.DAY
    market: MarketType = MarketType.US_STOCK
    status: OrderStatus = OrderStatus.PENDING
    
    # 执行信息
    filled_quantity: int = 0
    avg_fill_price: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    # 元数据
    strategy_id: str = ""
    risk_check_id: str = ""
    notes: str = ""
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'side': self.side.value,
            'order_type': self.order_type.value,
            'quantity': self.quantity,
            'price': self.price,
            'stop_price': self.stop_price,
            'time_in_force': self.time_in_force.value,
            'market': self.market.value,
            'status': self.status.value,
            'filled_quantity': self.filled_quantity,
            'avg_fill_price': self.avg_fill_price,
            'commission': self.commission,
            'slippage': self.slippage,
            'created_at': self.created_at.isoformat(),
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'filled_at': self.filled_at.isoformat() if self.filled_at else None
        }


@dataclass
class Fill:
    """成交回报"""
    fill_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    commission: float
    timestamp: datetime = field(default_factory=datetime.now)
    exchange: str = ""
    fill_type: str = "partial"  # partial or full
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'fill_id': self.fill_id,
            'order_id': self.order_id,
            'symbol': self.symbol,
            'side': self.side.value,
            'quantity': self.quantity,
            'price': self.price,
            'commission': self.commission,
            'timestamp': self.timestamp.isoformat(),
            'exchange': self.exchange,
            'fill_type': self.fill_type
        }


@dataclass
class ExecutionReport:
    """执行报告"""
    total_orders: int = 0
    filled_orders: int = 0
    cancelled_orders: int = 0
    rejected_orders: int = 0
    pending_orders: int = 0
    
    total_quantity: int = 0
    filled_quantity: int = 0
    
    total_value: float = 0.0
    total_commission: float = 0.0
    total_slippage: float = 0.0
    
    avg_slippage_pct: float = 0.0
    fill_rate: float = 0.0
    
    execution_time_ms: float = 0.0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'total_orders': self.total_orders,
            'filled_orders': self.filled_orders,
            'cancelled_orders': self.cancelled_orders,
            'rejected_orders': self.rejected_orders,
            'pending_orders': self.pending_orders,
            'total_quantity': self.total_quantity,
            'filled_quantity': self.filled_quantity,
            'total_value': self.total_value,
            'total_commission': self.total_commission,
            'total_slippage': self.total_slippage,
            'avg_slippage_pct': self.avg_slippage_pct,
            'fill_rate': self.fill_rate,
            'execution_time_ms': self.execution_time_ms
        }


class OrderExecutor:
    """
    订单执行器
    
    负责订单的生成、验证、发送和执行监控
    """
    
    def __init__(self, config: Optional[ExecutionConfig] = None):
        self.config = config or ExecutionConfig()
        
        # 订单存储
        self.orders: Dict[str, Order] = {}
        self.fills: List[Fill] = []
        self.pending_orders: Dict[str, Order] = {}
        
        # 回调函数
        self.on_order_submitted: Optional[Callable[[Order], None]] = None
        self.on_order_filled: Optional[Callable[[Fill], None]] = None
        self.on_order_cancelled: Optional[Callable[[Order], None]] = None
        self.on_order_rejected: Optional[Callable[[Order, str], None]] = None
        
        # 执行统计
        self.execution_history: List[ExecutionReport] = []
        
        # T+1 持仓限制 (A 股)
        self.t1_positions: Dict[str, int] = {}  # symbol -> quantity (当日买入不可卖)
    
    # ==================== 订单生成 ====================
    
    def create_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: TimeInForce = TimeInForce.DAY,
        market: MarketType = MarketType.US_STOCK,
        strategy_id: str = "",
        risk_check_id: str = ""
    ) -> Order:
        """
        创建订单
        
        Args:
            symbol: 标的代码
            side: 买卖方向
            quantity: 数量
            order_type: 订单类型
            price: 限价 (限价单需要)
            stop_price: 止损价 (止损单需要)
            time_in_force: 有效期
            market: 市场类型
            strategy_id: 策略 ID
            risk_check_id: 风控检查 ID
            
        Returns:
            Order 对象
        """
        # 生成订单 ID
        order_id = f"ORD_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8].upper()}"
        
        # 创建订单
        order = Order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            time_in_force=time_in_force,
            market=market,
            strategy_id=strategy_id,
            risk_check_id=risk_check_id
        )
        
        # 验证订单
        is_valid, reason = self._validate_order(order)
        if not is_valid:
            order.status = OrderStatus.REJECTED
            order.notes = reason
            if self.on_order_rejected:
                self.on_order_rejected(order, reason)
        
        self.orders[order_id] = order
        return order
    
    def _validate_order(self, order: Order) -> Tuple[bool, str]:
        """
        验证订单
        
        Returns:
            (是否有效，原因)
        """
        # 检查数量
        if order.quantity <= 0:
            return False, "订单数量必须大于 0"
        
        # 检查价格
        if order.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT]:
            if order.price is None or order.price <= 0:
                return False, "限价单必须指定有效价格"
        
        # 检查止损价
        if order.order_type in [OrderType.STOP_LOSS, OrderType.STOP_LIMIT]:
            if order.stop_price is None or order.stop_price <= 0:
                return False, "止损单必须指定有效止损价"
        
        # 检查最小交易金额
        min_amount = self.config.min_trade_amount.get(order.market.value, 1.0)
        estimated_value = order.quantity * (order.price or 0)
        if estimated_value < min_amount:
            return False, f"订单金额低于最小交易金额 ({min_amount} {order.market.value})"
        
        # A 股 T+1 检查
        if order.market == MarketType.A_SHARE:
            if order.side == OrderSide.SELL:
                t1_qty = self.t1_positions.get(order.symbol, 0)
                if t1_qty > 0:
                    return False, f"A 股 T+1 限制：当日买入 {t1_qty} 股不可卖出"
        
        # 检查交易时间
        if self.config.trading_time_check:
            if not self._is_trading_time(order.market):
                return False, f"非交易时间 ({order.market.value})"
        
        return True, "验证通过"
    
    def _is_trading_time(self, market: MarketType) -> bool:
        """检查是否在交易时间"""
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        current_time = hour * 100 + minute
        
        if market == MarketType.A_SHARE:
            # A 股：9:30-11:30, 13:00-15:00
            morning = 930 <= current_time <= 1130
            afternoon = 1300 <= current_time <= 1500
            return morning or afternoon
        
        elif market == MarketType.US_STOCK:
            # 美股 (北京时间): 21:30-04:00
            if hour >= 21 or hour < 4:
                return True
            # 夏令时
            if hour >= 20 or hour < 3:
                return True
            return False
        
        return True
    
    # ==================== 订单发送 ====================
    
    async def submit_order(self, order: Order) -> bool:
        """
        提交订单
        
        Args:
            order: 订单对象
            
        Returns:
            是否成功提交
        """
        if order.status != OrderStatus.PENDING:
            return False
        
        # 更新状态
        order.status = OrderStatus.SUBMITTED
        order.submitted_at = datetime.now()
        
        # 移动到待成交队列
        self.pending_orders[order.order_id] = order
        
        # 触发回调
        if self.on_order_submitted:
            self.on_order_submitted(order)
        
        # 模拟执行 (实际应用中替换为真实 API 调用)
        success = await self._execute_order(order)
        
        return success
    
    async def _execute_order(self, order: Order) -> bool:
        """
        执行订单 (模拟)
        
        实际应用中需要替换为真实券商 API 调用
        """
        # 模拟网络延迟
        await asyncio.sleep(0.1)
        
        # 模拟执行结果 (90% 成功率)
        import random
        if random.random() < 0.9:
            # 模拟成交
            fill_price = self._simulate_fill_price(order)
            fill_quantity = order.quantity  # 假设全部成交
            
            # 计算滑点
            if order.price:
                slippage = abs(fill_price - order.price) / order.price
            else:
                slippage = 0.0
            
            # 检查滑点限制
            if slippage > self.config.max_slippage_pct:
                order.status = OrderStatus.REJECTED
                order.notes = f"滑点超限 ({slippage:.2%} > {self.config.max_slippage_pct:.2%})"
                return False
            
            # 创建成交回报
            self._create_fill(order, fill_price, fill_quantity)
            
            # 更新订单状态
            order.status = OrderStatus.FILLED
            order.filled_quantity = fill_quantity
            order.avg_fill_price = fill_price
            order.filled_at = datetime.now()
            
            # A 股 T+1 记录
            if order.market == MarketType.A_SHARE and order.side == OrderSide.BUY:
                self.t1_positions[order.symbol] = self.t1_positions.get(order.symbol, 0) + fill_quantity
            
            # 移除待成交队列
            if order.order_id in self.pending_orders:
                del self.pending_orders[order.order_id]
            
            return True
        else:
            # 模拟拒绝
            order.status = OrderStatus.REJECTED
            order.notes = "券商拒绝订单"
            if self.on_order_rejected:
                self.on_order_rejected(order, "券商拒绝订单")
            return False
    
    def _simulate_fill_price(self, order: Order) -> float:
        """模拟成交价格"""
        import random
        
        if order.order_type == OrderType.MARKET:
            # 市价单：模拟市场价格 ± 滑点
            base_price = order.price or 100.0
            slippage = random.uniform(-0.005, 0.005)  # ±0.5% 滑点
            return base_price * (1 + slippage)
        
        elif order.order_type == OrderType.LIMIT:
            # 限价单：以限价或更好价格成交
            if order.side == OrderSide.BUY:
                return order.price * (1 - random.uniform(0, 0.002))
            else:
                return order.price * (1 + random.uniform(0, 0.002))
        
        return order.price or 100.0
    
    def _create_fill(self, order: Order, price: float, quantity: int):
        """创建成交回报"""
        fill_id = f"FILL_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6].upper()}"
        
        commission = price * quantity * 0.001  # 假设 0.1% 佣金
        
        fill = Fill(
            fill_id=fill_id,
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=quantity,
            price=price,
            commission=commission,
            exchange="SIMULATED",
            fill_type="full" if quantity == order.quantity else "partial"
        )
        
        self.fills.append(fill)
        order.commission = commission
        
        # 计算滑点
        if order.price:
            order.slippage = abs(price - order.price) / order.price
        
        # 触发回调
        if self.on_order_filled:
            self.on_order_filled(fill)
    
    # ==================== 批量执行 ====================
    
    async def submit_batch(
        self,
        orders: List[Order],
        sequential: bool = True
    ) -> ExecutionReport:
        """
        批量提交订单
        
        Args:
            orders: 订单列表
            sequential: 是否顺序执行
            
        Returns:
            执行报告
        """
        start_time = datetime.now()
        
        report = ExecutionReport(
            total_orders=len(orders),
            total_quantity=sum(o.quantity for o in orders),
            total_value=sum((o.price or 0) * o.quantity for o in orders)
        )
        
        if sequential:
            # 顺序执行
            for i, order in enumerate(orders):
                success = await self.submit_order(order)
                
                if success:
                    report.filled_orders += 1
                    report.filled_quantity += order.filled_quantity
                    report.total_value += order.avg_fill_price * order.filled_quantity
                    report.total_commission += order.commission
                    report.total_slippage += order.slippage
                else:
                    if order.status == OrderStatus.REJECTED:
                        report.rejected_orders += 1
                    elif order.status == OrderStatus.CANCELLED:
                        report.cancelled_orders += 1
                    else:
                        report.pending_orders += 1
                
                # 批次间隔
                if i < len(orders) - 1 and self.config.batch_execution:
                    await asyncio.sleep(self.config.batch_interval_sec)
        else:
            # 并发执行
            tasks = [self.submit_order(order) for order in orders]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for order, result in zip(orders, results):
                if isinstance(result, bool) and result:
                    report.filled_orders += 1
                    report.filled_quantity += order.filled_quantity
                else:
                    report.rejected_orders += 1
        
        # 计算统计
        end_time = datetime.now()
        report.execution_time_ms = (end_time - start_time).total_seconds() * 1000
        
        if report.total_orders > 0:
            report.fill_rate = report.filled_orders / report.total_orders
        
        if report.filled_orders > 0:
            report.avg_slippage_pct = report.total_slippage / report.filled_orders
        
        # 保存执行历史
        self.execution_history.append(report)
        
        return report
    
    # ==================== 订单管理 ====================
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        if order_id not in self.orders:
            return False
        
        order = self.orders[order_id]
        
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            return False
        
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = datetime.now()
        
        if order_id in self.pending_orders:
            del self.pending_orders[order_id]
        
        if self.on_order_cancelled:
            self.on_order_cancelled(order)
        
        return True
    
    def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """
        取消所有待成交订单
        
        Args:
            symbol: 可选，只取消指定标的的订单
            
        Returns:
            取消的订单数量
        """
        cancelled = 0
        
        for order_id in list(self.pending_orders.keys()):
            order = self.pending_orders[order_id]
            
            if symbol is None or order.symbol == symbol:
                if self.cancel_order(order_id):
                    cancelled += 1
        
        return cancelled
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """获取订单"""
        return self.orders.get(order_id)
    
    def get_orders_by_status(self, status: OrderStatus) -> List[Order]:
        """按状态获取订单"""
        return [o for o in self.orders.values() if o.status == status]
    
    def get_orders_by_symbol(self, symbol: str) -> List[Order]:
        """按标的获取订单"""
        return [o for o in self.orders.values() if o.symbol == symbol]
    
    def get_fills(self, symbol: Optional[str] = None) -> List[Fill]:
        """获取成交回报"""
        if symbol:
            return [f for f in self.fills if f.symbol == symbol]
        return self.fills
    
    # ==================== 执行分析 ====================
    
    def get_execution_quality(self, window_hours: int = 24) -> Dict:
        """
        获取执行质量分析
        
        Args:
            window_hours: 分析窗口 (小时)
            
        Returns:
            执行质量指标
        """
        cutoff = datetime.now() - timedelta(hours=window_hours)
        recent_orders = [
            o for o in self.orders.values()
            if o.created_at > cutoff
        ]
        
        if not recent_orders:
            return {
                'total_orders': 0,
                'fill_rate': 0.0,
                'avg_slippage_pct': 0.0,
                'avg_execution_time_ms': 0.0,
                'rejection_rate': 0.0
            }
        
        filled = [o for o in recent_orders if o.status == OrderStatus.FILLED]
        rejected = [o for o in recent_orders if o.status == OrderStatus.REJECTED]
        
        avg_slippage = sum(o.slippage for o in filled) / len(filled) if filled else 0.0
        
        exec_times = []
        for order in filled:
            if order.submitted_at and order.filled_at:
                exec_time = (order.filled_at - order.submitted_at).total_seconds() * 1000
                exec_times.append(exec_time)
        
        avg_exec_time = sum(exec_times) / len(exec_times) if exec_times else 0.0
        
        return {
            'total_orders': len(recent_orders),
            'fill_rate': len(filled) / len(recent_orders) if recent_orders else 0.0,
            'avg_slippage_pct': avg_slippage,
            'avg_execution_time_ms': avg_exec_time,
            'rejection_rate': len(rejected) / len(recent_orders) if recent_orders else 0.0,
            'total_commission': sum(o.commission for o in filled)
        }
    
    def get_execution_report(self) -> ExecutionReport:
        """获取汇总执行报告"""
        report = ExecutionReport()
        
        for order in self.orders.values():
            report.total_orders += 1
            report.total_quantity += order.quantity
            
            if order.status == OrderStatus.FILLED:
                report.filled_orders += 1
                report.filled_quantity += order.filled_quantity
                report.total_value += order.avg_fill_price * order.filled_quantity
                report.total_commission += order.commission
                report.total_slippage += order.slippage
            elif order.status == OrderStatus.CANCELLED:
                report.cancelled_orders += 1
            elif order.status == OrderStatus.REJECTED:
                report.rejected_orders += 1
            else:
                report.pending_orders += 1
        
        if report.total_orders > 0:
            report.fill_rate = report.filled_orders / report.total_orders
        
        if report.filled_orders > 0:
            report.avg_slippage_pct = report.total_slippage / report.filled_orders
        
        return report
    
    # ==================== T+1 管理 (A 股) ====================
    
    def clear_t1_positions(self):
        """清空 T+1 持仓记录 (每日收盘后调用)"""
        self.t1_positions.clear()
    
    def get_t1_restrictions(self, symbol: str) -> int:
        """获取 T+1 限制数量"""
        return self.t1_positions.get(symbol, 0)
    
    # ==================== 日志和导出 ====================
    
    def export_orders(self, filepath: str, format: str = 'json'):
        """导出订单数据"""
        import json
        
        orders_data = [o.to_dict() for o in self.orders.values()]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            if format == 'json':
                json.dump(orders_data, f, indent=2, ensure_ascii=False)
    
    def export_fills(self, filepath: str, format: str = 'json'):
        """导出成交数据"""
        import json
        
        fills_data = [f.to_dict() for f in self.fills]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            if format == 'json':
                json.dump(fills_data, f, indent=2, ensure_ascii=False)


# ==================== 使用示例 ====================

async def main():
    # 创建执行器
    config = ExecutionConfig(
        max_slippage_pct=0.01,
        batch_execution=True,
        max_batch_size=5
    )
    executor = OrderExecutor(config)
    
    # 创建订单
    order1 = executor.create_order(
        symbol="AAPL",
        side=OrderSide.BUY,
        quantity=100,
        order_type=OrderType.LIMIT,
        price=150.0,
        market=MarketType.US_STOCK
    )
    
    order2 = executor.create_order(
        symbol="GOOGL",
        side=OrderSide.BUY,
        quantity=50,
        order_type=OrderType.MARKET,
        market=MarketType.US_STOCK
    )
    
    # 批量提交
    report = await executor.submit_batch([order1, order2])
    
    print(f"执行报告:")
    print(f"  总订单：{report.total_orders}")
    print(f"  成交：{report.filled_orders}")
    print(f"  成交率：{report.fill_rate:.1%}")
    print(f"  平均滑点：{report.avg_slippage_pct:.2%}")
    print(f"  执行时间：{report.execution_time_ms:.0f}ms")
    
    # 获取执行质量
    quality = executor.get_execution_quality()
    print(f"\n执行质量:")
    print(f"  平均滑点：{quality['avg_slippage_pct']:.2%}")
    print(f"  平均执行时间：{quality['avg_execution_time_ms']:.0f}ms")


if __name__ == "__main__":
    asyncio.run(main())
