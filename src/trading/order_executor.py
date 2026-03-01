"""
订单执行引擎 (Order Executor)

负责将交易信号转化为实际订单并执行。
支持智能订单路由、拆单算法 (TWAP/VWAP) 和滑点控制。

核心功能:
- 智能订单路由 (SOR)
- 拆单算法 (TWAP/VWAP)
- 滑点控制
- 订单状态管理
"""

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class OrderSide:
    """订单方向"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType:
    """订单类型"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus:
    """订单状态"""
    PENDING = "PENDING"              # 待提交
    SUBMITTED = "SUBMITTED"          # 已提交
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # 部分成交
    FILLED = "FILLED"                # 完全成交
    CANCELLED = "CANCELLED"          # 已取消
    REJECTED = "REJECTED"            # 已拒绝
    EXPIRED = "EXPIRED"              # 已过期
    FAILED = "FAILED"                # 执行失败


class ExecutionAlgorithm:
    """执行算法"""
    IMMEDIATE = "IMMEDIATE"  # 立即执行
    TWAP = "TWAP"            # 时间加权平均
    VWAP = "VWAP"            # 成交量加权平均


@dataclass
class OrderSlice:
    """订单切片 (用于拆单算法)"""
    slice_id: str
    order_id: str
    sequence: int
    quantity: Decimal
    price: Optional[Decimal]
    status: str = OrderStatus.PENDING
    submitted_at: Optional[datetime] = None
    filled_quantity: Decimal = Decimal('0')
    avg_price: Decimal = Decimal('0')
    fills: List[Dict[str, Any]] = field(default_factory=list)
    
    def is_complete(self) -> bool:
        """检查切片是否完成"""
        return self.filled_quantity >= self.quantity
    
    def fill(self, quantity: Decimal, price: Decimal, exec_id: str = ""):
        """记录成交"""
        self.fills.append({
            'exec_id': exec_id or str(uuid.uuid4()),
            'quantity': str(quantity),
            'price': str(price),
            'timestamp': datetime.now().isoformat(),
        })
        self.filled_quantity += quantity
        
        # 更新平均成交价
        total_value = sum(
            Decimal(f['quantity']) * Decimal(f['price'])
            for f in self.fills
        )
        self.avg_price = total_value / self.filled_quantity if self.filled_quantity > 0 else Decimal('0')
        
        if self.is_complete():
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIALLY_FILLED


@dataclass
class Order:
    """订单"""
    order_id: str
    signal_id: str
    symbol: str
    side: str
    total_quantity: Decimal
    order_type: str
    algorithm: str
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    status: str = OrderStatus.PENDING
    submitted_quantity: Decimal = Decimal('0')
    filled_quantity: Decimal = Decimal('0')
    avg_price: Decimal = Decimal('0')
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    slices: List[OrderSlice] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_slice(self, slice: OrderSlice):
        """添加订单切片"""
        self.slices.append(slice)
    
    def get_remaining_quantity(self) -> Decimal:
        """获取剩余未执行数量"""
        return self.total_quantity - self.filled_quantity
    
    def is_complete(self) -> bool:
        """检查订单是否完成"""
        return self.filled_quantity >= self.total_quantity
    
    def get_fill_rate(self) -> Decimal:
        """获取成交率"""
        if self.total_quantity == 0:
            return Decimal('0')
        return (self.filled_quantity / self.total_quantity * 100).quantize(Decimal('0.01'))
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'order_id': self.order_id,
            'signal_id': self.signal_id,
            'symbol': self.symbol,
            'side': self.side,
            'total_quantity': str(self.total_quantity),
            'order_type': self.order_type,
            'algorithm': self.algorithm,
            'limit_price': str(self.limit_price) if self.limit_price else None,
            'stop_price': str(self.stop_price) if self.stop_price else None,
            'status': self.status,
            'submitted_quantity': str(self.submitted_quantity),
            'filled_quantity': str(self.filled_quantity),
            'avg_price': str(self.avg_price),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'fill_rate': str(self.get_fill_rate()),
            'metadata': self.metadata,
        }


@dataclass
class ExecutionReport:
    """执行报告"""
    report_id: str
    order_id: str
    slice_id: Optional[str]
    exec_id: str
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    timestamp: datetime
    venue: str
    commission: Decimal = Decimal('0')
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'report_id': self.report_id,
            'order_id': self.order_id,
            'slice_id': self.slice_id,
            'exec_id': self.exec_id,
            'symbol': self.symbol,
            'side': self.side,
            'quantity': str(self.quantity),
            'price': str(self.price),
            'timestamp': self.timestamp.isoformat(),
            'venue': self.venue,
            'commission': str(self.commission),
            'metadata': self.metadata,
        }


@dataclass
class SlippageConfig:
    """滑点配置"""
    base_bps: Decimal = Decimal('5')           # 基础滑点 (基点)
    max_bps: Decimal = Decimal('50')           # 最大滑点 (基点)
    volatility_factor: Decimal = Decimal('0.5')  # 波动率调整系数
    urgency_factor: Decimal = Decimal('2')     # 紧急程度调整系数 (每级 bps)
    
    def calculate_slippage_budget(
        self,
        price: Decimal,
        volatility: Decimal,
        urgency_level: int = 5,
    ) -> Decimal:
        """
        计算滑点预算
        
        Args:
            price: 当前价格
            volatility: 波动率 (如 ATR/Price)
            urgency_level: 紧急程度 (1-10)
            
        Returns:
            滑点预算 (价格单位)
        """
        # 基础滑点
        base_slippage_bps = self.base_bps
        
        # 波动率调整
        vol_adjustment_bps = volatility * 10000 * self.volatility_factor
        
        # 紧急程度调整 (以 5 为基准，每高一级增加 urgency_factor bps)
        urgency_adjustment_bps = (urgency_level - 5) * self.urgency_factor
        
        # 总滑点 (不超过最大值)
        total_bps = min(base_slippage_bps + vol_adjustment_bps + urgency_adjustment_bps, self.max_bps)
        
        # 转换为价格单位
        return price * total_bps / 10000


class BrokerAdapter(ABC):
    """券商适配器接口"""
    
    @abstractmethod
    async def submit_order(self, order: Order) -> bool:
        """提交订单"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """获取订单状态"""
        pass
    
    @abstractmethod
    async def get_market_price(self, symbol: str) -> Optional[Decimal]:
        """获取市场价格"""
        pass
    
    @abstractmethod
    async def get_market_depth(self, symbol: str, levels: int = 5) -> Optional[Dict[str, Any]]:
        """获取市场深度"""
        pass


class MockBrokerAdapter(BrokerAdapter):
    """模拟券商适配器 (用于测试)"""
    
    def __init__(self, fill_probability: float = 0.9, fill_delay_seconds: float = 1.0):
        self.fill_probability = fill_probability
        self.fill_delay = fill_delay_seconds
        self.orders: Dict[str, Dict[str, Any]] = {}
        self.prices: Dict[str, Decimal] = {
            'AAPL': Decimal('150.00'),
            'GOOGL': Decimal('140.00'),
            'MSFT': Decimal('380.00'),
            'TSLA': Decimal('200.00'),
        }
    
    async def submit_order(self, order: Order) -> bool:
        """模拟提交订单"""
        self.orders[order.order_id] = {
            'status': OrderStatus.SUBMITTED,
            'submitted_at': datetime.now(),
        }
        
        # 模拟延迟成交
        await asyncio.sleep(self.fill_delay)
        
        import random
        if random.random() < self.fill_probability:
            # 模拟成交
            price = self.prices.get(order.symbol, Decimal('100.00'))
            # 添加一些随机波动
            price = price * Decimal(str(1 + (random.random() - 0.5) * 0.01))
            
            self.orders[order.order_id]['status'] = OrderStatus.FILLED
            self.orders[order.order_id]['filled_quantity'] = order.total_quantity
            self.orders[order.order_id]['avg_price'] = price
            self.orders[order.order_id]['completed_at'] = datetime.now()
            
            return True
        else:
            self.orders[order.order_id]['status'] = OrderStatus.REJECTED
            return False
    
    async def cancel_order(self, order_id: str) -> bool:
        if order_id in self.orders:
            self.orders[order_id]['status'] = OrderStatus.CANCELLED
            return True
        return False
    
    async def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        return self.orders.get(order_id)
    
    async def get_market_price(self, symbol: str) -> Optional[Decimal]:
        return self.prices.get(symbol)
    
    async def get_market_depth(self, symbol: str, levels: int = 5) -> Optional[Dict[str, Any]]:
        price = self.prices.get(symbol, Decimal('100.00'))
        return {
            'bids': [(price - Decimal('0.01') * i, Decimal('1000')) for i in range(levels)],
            'asks': [(price + Decimal('0.01') * i, Decimal('1000')) for i in range(levels)],
        }


class OrderRouter:
    """
    智能订单路由器 (Smart Order Router)
    
    负责选择最优的执行路径:
    - 价格最优
    - 流动性充足
    - 执行速度快
    - 费用最低
    """
    
    def __init__(self, brokers: Dict[str, BrokerAdapter]):
        """
        初始化路由器
        
        Args:
            brokers: 可用的券商适配器 {broker_id: adapter}
        """
        self.brokers = brokers
        self.broker_stats: Dict[str, Dict[str, Any]] = {
            broker_id: {
                'avg_fill_time': 0.0,
                'fill_rate': 1.0,
                'avg_commission': Decimal('0'),
                'total_orders': 0,
            }
            for broker_id in brokers
        }
    
    async def select_best_broker(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        选择最优券商
        
        Returns:
            (broker_id, broker_info)
        """
        best_broker = None
        best_score = float('-inf')
        best_info = {}
        
        for broker_id, adapter in self.brokers.items():
            try:
                # 获取市场价格和深度
                price = await adapter.get_market_price(symbol)
                depth = await adapter.get_market_depth(symbol)
                
                if not price or not depth:
                    continue
                
                # 计算评分
                score = self._calculate_broker_score(
                    broker_id=broker_id,
                    price=price,
                    depth=depth,
                    side=side,
                    quantity=quantity,
                )
                
                if score > best_score:
                    best_score = score
                    best_broker = broker_id
                    best_info = {
                        'price': price,
                        'depth': depth,
                        'score': score,
                    }
                
            except Exception as e:
                logger.error(f"评估券商 {broker_id} 时出错：{e}")
                continue
        
        if best_broker is None:
            # 默认选择第一个可用的券商
            best_broker = list(self.brokers.keys())[0]
            best_info = {'score': 0}
        
        return best_broker, best_info
    
    def _calculate_broker_score(
        self,
        broker_id: str,
        price: Decimal,
        depth: Dict[str, Any],
        side: str,
        quantity: Decimal,
    ) -> float:
        """
        计算券商评分
        
        评分因素:
        - 价格 (40%): 买单看卖一价，卖单看买一价
        - 流动性 (30%): 市场深度是否足够
        - 历史表现 (20%): 填充率和速度
        - 费用 (10%): 佣金水平
        """
        stats = self.broker_stats[broker_id]
        
        # 价格评分 (40%)
        if side == OrderSide.BUY:
            best_price = min(d[0] for d in depth['asks']) if depth['asks'] else price
        else:
            best_price = max(d[0] for d in depth['bids']) if depth['bids'] else price
        
        price_score = 1.0 / float(best_price)  # 价格越低越好 (对于买单)
        
        # 流动性评分 (30%)
        if side == OrderSide.BUY:
            available_qty = sum(d[1] for d in depth['asks'][:3]) if depth['asks'] else Decimal('0')
        else:
            available_qty = sum(d[1] for d in depth['bids'][:3]) if depth['bids'] else Decimal('0')
        
        liquidity_score = min(1.0, float(available_qty / quantity)) if quantity > 0 else 0.0
        
        # 历史表现评分 (20%)
        history_score = stats['fill_rate'] * 0.7 + (1.0 - min(1.0, stats['avg_fill_time'] / 5.0)) * 0.3
        
        # 费用评分 (10%)
        cost_score = 1.0 - float(stats['avg_commission'] / Decimal('10'))  # 假设最大佣金$10
        
        # 加权总分
        total_score = (
            price_score * 0.4 +
            liquidity_score * 0.3 +
            history_score * 0.2 +
            cost_score * 0.1
        )
        
        return total_score
    
    def update_broker_stats(
        self,
        broker_id: str,
        fill_time: float,
        filled: bool,
        commission: Decimal,
    ):
        """更新券商统计信息"""
        if broker_id not in self.broker_stats:
            return
        
        stats = self.broker_stats[broker_id]
        n = stats['total_orders']
        
        # 移动平均更新
        stats['avg_fill_time'] = (stats['avg_fill_time'] * n + fill_time) / (n + 1)
        stats['fill_rate'] = (stats['fill_rate'] * n + (1.0 if filled else 0.0)) / (n + 1)
        stats['avg_commission'] = (stats['avg_commission'] * n + commission) / (n + 1)
        stats['total_orders'] += 1


class SliceGenerator:
    """
    拆单算法生成器
    
    支持:
    - TWAP (时间加权平均价格)
    - VWAP (成交量加权平均价格)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        # 默认配置
        self.max_slice_pct = Decimal(str(self.config.get('max_slice_pct', 0.05)))  # 单笔最大占日均成交量 5%
        self.min_slice_interval = self.config.get('min_slice_interval', 30)  # 最小间隔 30 秒
        self.default_duration_minutes = self.config.get('default_duration_minutes', 60)
    
    def generate_twap_slices(
        self,
        order: Order,
        duration_minutes: Optional[int] = None,
        slice_count: Optional[int] = None,
    ) -> List[OrderSlice]:
        """
        生成 TWAP 切片
        
        Args:
            order: 原始订单
            duration_minutes: 执行时长 (分钟)
            slice_count: 切片数量 (如果不指定则根据时长计算)
            
        Returns:
            订单切片列表
        """
        if duration_minutes is None:
            duration_minutes = self.default_duration_minutes
        
        if slice_count is None:
            # 根据最小间隔计算切片数
            slice_count = max(1, int(duration_minutes * 60 / self.min_slice_interval))
        
        # 确保不超过最大切片数
        slice_count = min(slice_count, 100)
        
        # 计算每片数量
        slice_quantity = (order.total_quantity / slice_count).quantize(Decimal('1'))
        
        slices = []
        remaining = order.total_quantity
        
        for i in range(slice_count):
            # 最后一片包含剩余所有数量
            if i == slice_count - 1:
                qty = remaining
            else:
                qty = slice_quantity
                remaining -= qty
            
            slice = OrderSlice(
                slice_id=str(uuid.uuid4()),
                order_id=order.order_id,
                sequence=i,
                quantity=qty,
                price=order.limit_price,
            )
            slices.append(slice)
        
        logger.info(f"生成 TWAP 切片：{len(slices)} 片，每片约 {slice_quantity} 股，总时长 {duration_minutes} 分钟")
        return slices
    
    def generate_vwap_slices(
        self,
        order: Order,
        volume_profile: List[Tuple[datetime, Decimal]],
    ) -> List[OrderSlice]:
        """
        生成 VWAP 切片
        
        Args:
            order: 原始订单
            volume_profile: 成交量分布 [(时间，预期成交量), ...]
            
        Returns:
            订单切片列表
        """
        if not volume_profile:
            return self.generate_twap_slices(order)
        
        # 计算总成交量
        total_volume = sum(vol for _, vol in volume_profile)
        
        if total_volume == 0:
            return self.generate_twap_slices(order)
        
        slices = []
        remaining = order.total_quantity
        
        for i, (time_point, volume) in enumerate(volume_profile):
            # 按成交量比例分配
            slice_quantity = (order.total_quantity * volume / total_volume).quantize(Decimal('1'))
            
            # 确保不超过单笔最大限制
            slice_quantity = min(slice_quantity, order.total_quantity * self.max_slice_pct)
            
            # 最后一片包含剩余所有数量
            if i == len(volume_profile) - 1:
                slice_quantity = remaining
            else:
                remaining -= slice_quantity
            
            if slice_quantity > 0:
                slice = OrderSlice(
                    slice_id=str(uuid.uuid4()),
                    order_id=order.order_id,
                    sequence=i,
                    quantity=slice_quantity,
                    price=order.limit_price,
                )
                slices.append(slice)
        
        logger.info(f"生成 VWAP 切片：{len(slices)} 片，基于 {len(volume_profile)} 个时间段")
        return slices


class RiskChecker:
    """
    风控检查器
    
    执行前置风控检查:
    - 仓位限制
    - 黑名单检查
    - 资金充足检查
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 风控限制
        self.max_position_pct = Decimal(str(self.config.get('max_position_pct', 0.20)))
        self.max_single_order_qty = Decimal(str(self.config.get('max_single_order_qty', 10000)))
        self.blacklist: Set[str] = set(self.config.get('blacklist', []))
        
        # 当前仓位 (实际应用中应从仓位管理系统获取)
        self.positions: Dict[str, Decimal] = defaultdict(Decimal)
        self.total_asset = Decimal(str(self.config.get('total_asset', 1000000)))
    
    def check_order(self, order: Order, current_price: Decimal) -> Tuple[bool, Optional[str]]:
        """
        检查订单
        
        Returns:
            (通过检查，错误信息)
        """
        # 1. 黑名单检查
        if order.symbol in self.blacklist:
            return False, f"标的在黑名单中：{order.symbol}"
        
        # 2. 单笔数量限制
        if order.total_quantity > self.max_single_order_qty:
            return False, f"单笔数量超限：{order.total_quantity} > {self.max_single_order_qty}"
        
        # 3. 仓位限制检查
        current_position = self.positions[order.symbol]
        
        if order.side == OrderSide.BUY:
            new_position = current_position + order.total_quantity
        else:
            new_position = max(Decimal('0'), current_position - order.total_quantity)
        
        position_value = new_position * current_price
        position_pct = position_value / self.total_asset
        
        if position_pct > self.max_position_pct:
            return False, f"仓位超限：{position_pct:.2%} > {self.max_position_pct:.2%}"
        
        return True, None
    
    def update_position(self, symbol: str, quantity: Decimal, side: str):
        """更新仓位"""
        if side == OrderSide.BUY:
            self.positions[symbol] += quantity
        else:
            self.positions[symbol] = max(Decimal('0'), self.positions[symbol] - quantity)


class OrderExecutor:
    """
    订单执行引擎
    
    核心职责:
    1. 接收来自信号管理器的交易信号
    2. 执行风控检查
    3. 选择最优执行路径
    4. 应用拆单算法
    5. 提交订单到券商
    6. 监控订单执行状态
    7. 处理成交回报
    """
    
    def __init__(
        self,
        broker_adapters: Dict[str, BrokerAdapter],
        risk_config: Optional[Dict[str, Any]] = None,
        slice_config: Optional[Dict[str, Any]] = None,
        slippage_config: Optional[SlippageConfig] = None,
        on_execution_report: Optional[Callable[[ExecutionReport], None]] = None,
    ):
        """
        初始化订单执行引擎
        
        Args:
            broker_adapters: 券商适配器
            risk_config: 风控配置
            slice_config: 拆单配置
            slippage_config: 滑点配置
            on_execution_report: 执行回报回调
        """
        self.brokers = broker_adapters
        self.router = OrderRouter(broker_adapters)
        self.risk_checker = RiskChecker(risk_config)
        self.slice_generator = SliceGenerator(slice_config)
        self.slippage_config = slippage_config or SlippageConfig()
        self.on_execution_report = on_execution_report
        
        # 订单存储
        self.orders: Dict[str, Order] = {}
        
        # 执行任务
        self.execution_tasks: Dict[str, asyncio.Task] = {}
        
        # 运行状态
        self.is_running = False
        
        # 统计信息
        self.stats = {
            'total_orders': 0,
            'filled_orders': 0,
            'rejected_orders': 0,
            'cancelled_orders': 0,
            'total_volume': Decimal('0'),
            'total_commission': Decimal('0'),
        }
        
        logger.info("订单执行引擎初始化完成")
    
    async def start(self):
        """启动执行引擎"""
        self.is_running = True
        logger.info("订单执行引擎已启动")
    
    async def stop(self):
        """停止执行引擎"""
        self.is_running = False
        
        # 取消所有执行任务
        for task in self.execution_tasks.values():
            task.cancel()
        
        # 等待任务完成
        if self.execution_tasks:
            await asyncio.gather(*self.execution_tasks.values(), return_exceptions=True)
        
        logger.info("订单执行引擎已停止")
    
    async def execute_signal(self, signal) -> Optional[Order]:
        """
        执行交易信号
        
        Args:
            signal: 交易信号 (来自 SignalManager)
            
        Returns:
            创建的订单，如果风控失败则返回 None
        """
        from .signal_manager import SignalPriceType, SignalSide
        
        # 1. 创建订单
        order = self._create_order_from_signal(signal)
        self.orders[order.order_id] = order
        self.stats['total_orders'] += 1
        
        logger.info(f"开始执行订单：{order.order_id} - {order.symbol} {order.side} {order.total_quantity}")
        
        # 2. 获取市场价格
        broker_id, broker_info = await self.router.select_best_broker(
            symbol=order.symbol,
            side=order.side,
            quantity=order.total_quantity,
        )
        broker = self.brokers[broker_id]
        current_price = broker_info.get('price') or await broker.get_market_price(order.symbol)
        
        if not current_price:
            logger.error(f"无法获取市场价格：{order.symbol}")
            order.status = OrderStatus.FAILED
            self.stats['rejected_orders'] += 1
            return order
        
        # 3. 风控检查
        passed, error_msg = self.risk_checker.check_order(order, current_price)
        if not passed:
            logger.warning(f"风控检查失败：{order.order_id} - {error_msg}")
            order.status = OrderStatus.REJECTED
            order.metadata['reject_reason'] = error_msg
            self.stats['rejected_orders'] += 1
            return order
        
        # 4. 滑点检查
        volatility = Decimal('0.02')  # 假设波动率 2%，实际应从市场数据获取
        urgency_level = 10 - signal.priority if hasattr(signal, 'priority') else 5
        slippage_budget = self.slippage_config.calculate_slippage_budget(
            price=current_price,
            volatility=volatility,
            urgency_level=urgency_level,
        )
        
        if order.order_type == OrderType.LIMIT and order.limit_price:
            if order.side == OrderSide.BUY and order.limit_price > current_price + slippage_budget:
                logger.warning(f"限价过高，超过滑点预算：{order.limit_price} > {current_price + slippage_budget}")
            elif order.side == OrderSide.SELL and order.limit_price < current_price - slippage_budget:
                logger.warning(f"限价过低，超过滑点预算：{order.limit_price} < {current_price - slippage_budget}")
        
        # 5. 生成执行切片
        if order.algorithm == ExecutionAlgorithm.TWAP:
            slices = self.slice_generator.generate_twap_slices(order)
        elif order.algorithm == ExecutionAlgorithm.VWAP:
            # 获取成交量分布 (实际应从市场数据获取)
            volume_profile = self._get_volume_profile(order.symbol)
            slices = self.slice_generator.generate_vwap_slices(order, volume_profile)
        else:  # IMMEDIATE
            slices = [
                OrderSlice(
                    slice_id=str(uuid.uuid4()),
                    order_id=order.order_id,
                    sequence=0,
                    quantity=order.total_quantity,
                    price=order.limit_price,
                )
            ]
        
        for slice in slices:
            order.add_slice(slice)
        
        # 6. 启动异步执行任务
        order.status = OrderStatus.SUBMITTED
        order.submitted_at = datetime.now()
        order.submitted_quantity = order.total_quantity
        
        task = asyncio.create_task(self._execute_slices(order, slices, broker, broker_id))
        self.execution_tasks[order.order_id] = task
        
        return order
    
    def _create_order_from_signal(self, signal) -> Order:
        """从信号创建订单"""
        from .signal_manager import SignalPriceType
        
        # 映射价格类型
        price_type_map = {
            SignalPriceType.MARKET: OrderType.MARKET,
            SignalPriceType.LIMIT: OrderType.LIMIT,
            SignalPriceType.TWAP: OrderType.MARKET,
            SignalPriceType.VWAP: OrderType.MARKET,
        }
        
        # 映射算法
        algorithm_map = {
            SignalPriceType.MARKET: ExecutionAlgorithm.IMMEDIATE,
            SignalPriceType.LIMIT: ExecutionAlgorithm.IMMEDIATE,
            SignalPriceType.TWAP: ExecutionAlgorithm.TWAP,
            SignalPriceType.VWAP: ExecutionAlgorithm.VWAP,
        }
        
        order_type = price_type_map.get(signal.price_type, OrderType.MARKET)
        algorithm = algorithm_map.get(signal.price_type, ExecutionAlgorithm.IMMEDIATE)
        
        return Order(
            order_id=str(uuid.uuid4()),
            signal_id=signal.signal_id,
            symbol=signal.symbol,
            side=signal.side,
            total_quantity=signal.quantity,
            order_type=order_type,
            algorithm=algorithm,
            limit_price=signal.limit_price,
            metadata={
                'strategy_id': signal.strategy_id,
                'signal_priority': signal.priority,
            },
        )
    
    def _get_volume_profile(self, symbol: str) -> List[Tuple[datetime, Decimal]]:
        """
        获取成交量分布
        
        实际应用中应从历史数据计算
        这里返回简化的示例数据
        """
        now = datetime.now()
        # 假设 60 分钟执行，每小时成交量分布
        return [
            (now + timedelta(minutes=i*5), Decimal(str(100 + i * 10)))
            for i in range(12)
        ]
    
    async def _execute_slices(
        self,
        order: Order,
        slices: List[OrderSlice],
        broker: BrokerAdapter,
        broker_id: str,
    ):
        """执行订单切片"""
        start_time = time.time()
        
        try:
            for i, slice in enumerate(slices):
                if not self.is_running:
                    logger.warning(f"执行引擎已停止，取消剩余切片：{order.order_id}")
                    break
                
                if order.is_complete():
                    break
                
                # 等待间隔时间 (除了第一片)
                if i > 0:
                    await asyncio.sleep(self.slice_generator.min_slice_interval)
                
                # 检查订单是否被取消
                if order.status == OrderStatus.CANCELLED:
                    logger.info(f"订单已取消：{order.order_id}")
                    break
                
                # 提交切片
                slice.submitted_at = datetime.now()
                slice.status = OrderStatus.SUBMITTED
                
                # 创建临时订单对象用于提交
                temp_order = Order(
                    order_id=slice.slice_id,
                    signal_id=order.signal_id,
                    symbol=order.symbol,
                    side=order.side,
                    total_quantity=slice.quantity,
                    order_type=order.order_type,
                    algorithm=ExecutionAlgorithm.IMMEDIATE,
                    limit_price=slice.price,
                )
                
                success = await broker.submit_order(temp_order)
                
                if success:
                    # 模拟成交回报
                    status = await broker.get_order_status(slice.slice_id)
                    if status:
                        filled_qty = status.get('filled_quantity', slice.quantity)
                        avg_price = status.get('avg_price', slice.price or Decimal('0'))
                        
                        slice.fill(filled_qty, avg_price)
                        
                        # 更新订单状态
                        order.filled_quantity += filled_qty
                        order.avg_price = self._calculate_weighted_avg_price(order)
                        
                        # 生成执行报告
                        report = ExecutionReport(
                            report_id=str(uuid.uuid4()),
                            order_id=order.order_id,
                            slice_id=slice.slice_id,
                            exec_id=str(uuid.uuid4()),
                            symbol=order.symbol,
                            side=order.side,
                            quantity=filled_qty,
                            price=avg_price,
                            timestamp=datetime.now(),
                            venue=broker_id,
                            commission=Decimal('0'),  # 实际应从回报中获取
                        )
                        
                        slice.fills.append(report.to_dict())
                        
                        # 更新风控仓位
                        self.risk_checker.update_position(order.symbol, filled_qty, order.side)
                        
                        # 更新券商统计
                        fill_time = time.time() - start_time
                        self.router.update_broker_stats(broker_id, fill_time, True, Decimal('0'))
                        
                        # 触发回调
                        if self.on_execution_report:
                            self.on_execution_report(report)
                        
                        logger.info(f"切片成交：{slice.slice_id} - {filled_qty}@{avg_price}")
                else:
                    slice.status = OrderStatus.REJECTED
                    logger.warning(f"切片执行失败：{slice.slice_id}")
            
            # 更新订单最终状态
            if order.is_complete():
                order.status = OrderStatus.FILLED
                order.completed_at = datetime.now()
                self.stats['filled_orders'] += 1
                self.stats['total_volume'] += order.filled_quantity
                logger.info(f"订单完成：{order.order_id} - 成交 {order.filled_quantity}@{order.avg_price}")
            elif order.status != OrderStatus.CANCELLED:
                order.status = OrderStatus.PARTIALLY_FILLED
                logger.warning(f"订单部分成交：{order.order_id} - {order.filled_quantity}/{order.total_quantity}")
        
        except Exception as e:
            logger.error(f"执行订单时出错：{order.order_id} - {e}")
            order.status = OrderStatus.FAILED
            order.metadata['error'] = str(e)
        
        finally:
            # 从执行任务中移除
            if order.order_id in self.execution_tasks:
                del self.execution_tasks[order.order_id]
    
    def _calculate_weighted_avg_price(self, order: Order) -> Decimal:
        """计算加权平均成交价"""
        total_value = Decimal('0')
        total_qty = Decimal('0')
        
        for slice in order.slices:
            if slice.filled_quantity > 0:
                total_value += slice.filled_quantity * slice.avg_price
                total_qty += slice.filled_quantity
        
        return total_value / total_qty if total_qty > 0 else Decimal('0')
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        取消订单
        
        Args:
            order_id: 订单 ID
            
        Returns:
            是否成功取消
        """
        if order_id not in self.orders:
            return False
        
        order = self.orders[order_id]
        
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            return False
        
        order.status = OrderStatus.CANCELLED
        self.stats['cancelled_orders'] += 1
        
        # 取消未执行的切片
        for slice in order.slices:
            if slice.status == OrderStatus.PENDING:
                slice.status = OrderStatus.CANCELLED
        
        # 如果订单已提交到券商，尝试取消
        if order.status == OrderStatus.SUBMITTED:
            for broker in self.brokers.values():
                try:
                    await broker.cancel_order(order_id)
                except Exception as e:
                    logger.error(f"取消券商订单失败：{e}")
        
        logger.info(f"订单已取消：{order_id}")
        return True
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """获取订单"""
        return self.orders.get(order_id)
    
    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """获取订单状态"""
        order = self.orders.get(order_id)
        if order:
            return order.to_dict()
        return None
    
    def get_all_orders(self) -> List[Order]:
        """获取所有订单"""
        return list(self.orders.values())
    
    def get_active_orders(self) -> List[Order]:
        """获取活跃订单"""
        active_statuses = [
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.PARTIALLY_FILLED,
        ]
        return [
            order for order in self.orders.values()
            if order.status in active_statuses
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            'active_orders': len(self.get_active_orders()),
            'total_orders': len(self.orders),
        }


# 使用示例

if __name__ == "__main__":
    import asyncio
    from decimal import Decimal
    
    async def main():
        # 创建模拟券商
        broker = MockBrokerAdapter()
        
        # 创建执行引擎
        executor = OrderExecutor(
            broker_adapters={'mock': broker},
            risk_config={
                'max_position_pct': 0.20,
                'max_single_order_qty': 10000,
                'total_asset': 1000000,
            },
            slice_config={
                'min_slice_interval': 5,  # 测试时缩短间隔
            },
        )
        
        # 启动执行引擎
        await executor.start()
        
        # 创建测试信号 (模拟来自 SignalManager)
        class MockSignal:
            signal_id = "test_signal_001"
            strategy_id = "momentum_v1"
            symbol = "AAPL"
            side = "BUY"
            quantity = Decimal('100')
            price_type = "MARKET"
            limit_price = None
            priority = 4
        
        signal = MockSignal()
        
        # 执行信号
        order = await executor.execute_signal(signal)
        
        if order:
            print(f"订单创建：{order.order_id}")
            
            # 等待执行完成
            await asyncio.sleep(10)
            
            # 查看订单状态
            status = executor.get_order_status(order.order_id)
            print(f"订单状态：{status}")
            
            # 查看统计
            stats = executor.get_stats()
            print(f"执行统计：{stats}")
        
        # 停止执行引擎
        await executor.stop()
    
    asyncio.run(main())
