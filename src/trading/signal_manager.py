"""
信号管理系统 (Signal Manager)

负责交易信号的接收、验证、优先级排序、去重和合并。
将策略层产生的信号转化为可执行的标准化信号。

核心功能:
- 信号接收和验证
- 信号优先级排序
- 信号去重和合并
- 信号队列管理
"""

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict
import heapq

logger = logging.getLogger(__name__)


class SignalPriority(IntEnum):
    """信号优先级 (数值越小优先级越高)"""
    EMERGENCY_CLOSE = 1      # 紧急平仓 (风控触发)
    STOP_LOSS = 2            # 止损
    TAKE_PROFIT = 3          # 止盈
    STRATEGY_ENTRY = 4       # 策略开仓
    STRATEGY_EXIT = 5        # 策略平仓
    REBALANCE = 6            # 组合再平衡


class SignalSide:
    """交易方向"""
    BUY = "BUY"
    SELL = "SELL"


class SignalPriceType:
    """价格类型"""
    MARKET = "MARKET"        # 市价单
    LIMIT = "LIMIT"          # 限价单
    TWAP = "TWAP"            # TWAP 算法
    VWAP = "VWAP"            # VWAP 算法


class SignalStatus:
    """信号状态"""
    PENDING = "PENDING"          # 待处理
    VALIDATED = "VALIDATED"      # 已验证
    QUEUED = "QUEUED"            # 已入队
    PROCESSING = "PROCESSING"    # 处理中
    SENT_TO_EXECUTOR = "SENT_TO_EXECUTOR"  # 已发送执行
    REJECTED = "REJECTED"        # 已拒绝
    EXPIRED = "EXPIRED"          # 已过期
    CANCELLED = "CANCELLED"      # 已取消


@dataclass
class Signal:
    """交易信号"""
    signal_id: str
    strategy_id: str
    symbol: str
    side: str  # BUY/SELL
    quantity: Decimal
    price_type: str  # MARKET/LIMIT/TWAP/VWAP
    priority: int
    timestamp: datetime
    status: str = SignalStatus.PENDING
    limit_price: Optional[Decimal] = None
    expire_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if isinstance(self.quantity, (int, float)):
            self.quantity = Decimal(str(self.quantity))
        if isinstance(self.limit_price, (int, float)):
            self.limit_price = Decimal(str(self.limit_price))
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)
        if isinstance(self.expire_at, str):
            self.expire_at = datetime.fromisoformat(self.expire_at)
    
    def is_expired(self) -> bool:
        """检查信号是否过期"""
        if self.expire_at is None:
            return False
        return datetime.now() > self.expire_at
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'signal_id': self.signal_id,
            'strategy_id': self.strategy_id,
            'symbol': self.symbol,
            'side': self.side,
            'quantity': str(self.quantity),
            'price_type': self.price_type,
            'priority': self.priority,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status,
            'limit_price': str(self.limit_price) if self.limit_price else None,
            'expire_at': self.expire_at.isoformat() if self.expire_at else None,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Signal':
        """从字典创建"""
        return cls(
            signal_id=data['signal_id'],
            strategy_id=data['strategy_id'],
            symbol=data['symbol'],
            side=data['side'],
            quantity=Decimal(data['quantity']),
            price_type=data['price_type'],
            priority=data['priority'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            status=data.get('status', SignalStatus.PENDING),
            limit_price=Decimal(data['limit_price']) if data.get('limit_price') else None,
            expire_at=datetime.fromisoformat(data['expire_at']) if data.get('expire_at') else None,
            metadata=data.get('metadata', {}),
        )


@dataclass
class SignalValidationResult:
    """信号验证结果"""
    is_valid: bool
    signal: Optional[Signal] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class SignalValidator:
    """信号验证器"""
    
    def __init__(
        self,
        allowed_symbols: Optional[Set[str]] = None,
        blacklist: Optional[Set[str]] = None,
        min_quantity: Decimal = Decimal('1'),
        max_quantity: Decimal = Decimal('1000000'),
    ):
        self.allowed_symbols = allowed_symbols
        self.blacklist = blacklist or set()
        self.min_quantity = min_quantity
        self.max_quantity = max_quantity
    
    def validate(self, signal: Signal) -> SignalValidationResult:
        """验证信号"""
        # 1. 必需字段检查
        if not signal.symbol:
            return SignalValidationResult(
                is_valid=False,
                error_code='MISSING_SYMBOL',
                error_message='缺少交易标的'
            )
        
        if not signal.side or signal.side not in [SignalSide.BUY, SignalSide.SELL]:
            return SignalValidationResult(
                is_valid=False,
                error_code='INVALID_SIDE',
                error_message=f'无效的交易方向：{signal.side}'
            )
        
        if signal.quantity <= 0:
            return SignalValidationResult(
                is_valid=False,
                error_code='INVALID_QUANTITY',
                error_message=f'数量必须大于 0: {signal.quantity}'
            )
        
        # 2. 数量范围检查
        if signal.quantity < self.min_quantity:
            return SignalValidationResult(
                is_valid=False,
                error_code='QUANTITY_TOO_SMALL',
                error_message=f'数量小于最小值：{signal.quantity} < {self.min_quantity}'
            )
        
        if signal.quantity > self.max_quantity:
            return SignalValidationResult(
                is_valid=False,
                error_code='QUANTITY_TOO_LARGE',
                error_message=f'数量大于最大值：{signal.quantity} > {self.max_quantity}'
            )
        
        # 3. 价格类型检查
        valid_price_types = [SignalPriceType.MARKET, SignalPriceType.LIMIT, 
                            SignalPriceType.TWAP, SignalPriceType.VWAP]
        if signal.price_type not in valid_price_types:
            return SignalValidationResult(
                is_valid=False,
                error_code='INVALID_PRICE_TYPE',
                error_message=f'无效的价格类型：{signal.price_type}'
            )
        
        # 4. 限价单价格检查
        if signal.price_type == SignalPriceType.LIMIT and not signal.limit_price:
            return SignalValidationResult(
                is_valid=False,
                error_code='MISSING_LIMIT_PRICE',
                error_message='限价单必须指定限价'
            )
        
        if signal.limit_price and signal.limit_price <= 0:
            return SignalValidationResult(
                is_valid=False,
                error_code='INVALID_LIMIT_PRICE',
                error_message=f'限价必须大于 0: {signal.limit_price}'
            )
        
        # 5. 黑名单检查
        if signal.symbol in self.blacklist:
            return SignalValidationResult(
                is_valid=False,
                error_code='BLACKLISTED_SYMBOL',
                error_message=f'标的在黑名单中：{signal.symbol}'
            )
        
        # 6. 允许列表检查 (如果配置了)
        if self.allowed_symbols and signal.symbol not in self.allowed_symbols:
            return SignalValidationResult(
                is_valid=False,
                error_code='SYMBOL_NOT_ALLOWED',
                error_message=f'标的不在允许列表中：{signal.symbol}'
            )
        
        # 7. 过期检查
        if signal.is_expired():
            return SignalValidationResult(
                is_valid=False,
                error_code='SIGNAL_EXPIRED',
                error_message=f'信号已过期：{signal.expire_at}'
            )
        
        # 8. 优先级范围检查
        valid_priorities = [p.value for p in SignalPriority]
        if signal.priority not in valid_priorities:
            return SignalValidationResult(
                is_valid=False,
                error_code='INVALID_PRIORITY',
                error_message=f'无效的优先级：{signal.priority}'
            )
        
        return SignalValidationResult(is_valid=True, signal=signal)


class SignalDeduplicator:
    """信号去重器"""
    
    def __init__(self, dedup_window_seconds: int = 60):
        """
        初始化去重器
        
        Args:
            dedup_window_seconds: 去重时间窗口 (秒)
        """
        self.dedup_window = timedelta(seconds=dedup_window_seconds)
        # 记录最近接收的信号：key = (symbol, side, strategy_id), value = List[Signal]
        self.recent_signals: Dict[tuple, List[Signal]] = defaultdict(list)
        # 已处理的信号 ID
        self.processed_signal_ids: Set[str] = set()
    
    def _generate_dedup_key(self, signal: Signal) -> tuple:
        """生成去重键"""
        return (signal.symbol, signal.side, signal.strategy_id)
    
    def _cleanup_old_signals(self, current_time: datetime):
        """清理过期信号"""
        cutoff_time = current_time - self.dedup_window
        for key in list(self.recent_signals.keys()):
            self.recent_signals[key] = [
                s for s in self.recent_signals[key]
                if s.timestamp > cutoff_time
            ]
            if not self.recent_signals[key]:
                del self.recent_signals[key]
    
    def is_duplicate(self, signal: Signal) -> bool:
        """检查信号是否重复"""
        # 检查信号 ID 是否已处理
        if signal.signal_id in self.processed_signal_ids:
            return True
        
        return False
    
    def add_and_merge(self, signal: Signal) -> Optional[Signal]:
        """
        添加信号并合并同方向信号
        
        Returns:
            合并后的信号，如果是重复信号则返回 None
        """
        # 检查是否重复
        if self.is_duplicate(signal):
            logger.debug(f"信号重复，跳过：{signal.signal_id}")
            return None
        
        current_time = datetime.now()
        self._cleanup_old_signals(current_time)
        
        dedup_key = self._generate_dedup_key(signal)
        recent = self.recent_signals[dedup_key]
        
        # 查找是否有可合并的信号 (同方向)
        for existing in recent:
            if existing.side == signal.side:
                # 合并信号：累加数量，更新价格为最新
                merged_signal = self._merge_signals(existing, signal)
                # 从队列中移除旧信号
                recent.remove(existing)
                recent.append(merged_signal)
                self.processed_signal_ids.add(signal.signal_id)
                logger.info(f"合并信号：{existing.signal_id} + {signal.signal_id} -> {merged_signal.signal_id}")
                return merged_signal
        
        # 没有可合并的信号，直接添加
        recent.append(signal)
        self.processed_signal_ids.add(signal.signal_id)
        return signal
    
    def _merge_signals(self, signal1: Signal, signal2: Signal) -> Signal:
        """合并两个信号"""
        # 生成新的信号 ID
        merged_id = hashlib.md5(
            f"{signal1.signal_id}:{signal2.signal_id}".encode()
        ).hexdigest()[:16]
        
        # 同方向：累加数量
        # 反方向：抵消数量
        if signal1.side == signal2.side:
            merged_quantity = signal1.quantity + signal2.quantity
        else:
            merged_quantity = abs(signal1.quantity - signal2.quantity)
        
        # 使用较新的价格
        if signal2.timestamp > signal1.timestamp:
            merged_price = signal2.limit_price
            merged_priority = signal2.priority
            merged_price_type = signal2.price_type
        else:
            merged_price = signal1.limit_price
            merged_priority = signal1.priority
            merged_price_type = signal1.price_type
        
        return Signal(
            signal_id=merged_id,
            strategy_id=signal1.strategy_id,
            symbol=signal1.symbol,
            side=signal1.side if merged_quantity > 0 else signal2.side,
            quantity=abs(merged_quantity),
            price_type=merged_price_type,
            priority=merged_priority,
            timestamp=datetime.now(),
            limit_price=merged_price,
            expire_at=min(signal1.expire_at, signal2.expire_at) if (signal1.expire_at and signal2.expire_at) else None,
            metadata={
                'merged_from': [signal1.signal_id, signal2.signal_id],
                'original_quantity_1': str(signal1.quantity),
                'original_quantity_2': str(signal2.quantity),
            }
        )


class SignalManager:
    """
    信号管理器
    
    核心职责:
    1. 接收来自策略层的交易信号
    2. 验证信号的有效性
    3. 对信号进行优先级排序
    4. 去重和合并相似信号
    5. 维护待执行信号队列
    6. 将信号发送给订单执行引擎
    """
    
    def __init__(
        self,
        validator: Optional[SignalValidator] = None,
        deduplicator: Optional[SignalDeduplicator] = None,
        on_signal_ready: Optional[Callable[[Signal], None]] = None,
        max_queue_size: int = 10000,
        allowed_symbols: Optional[Set[str]] = None,
        blacklist: Optional[Set[str]] = None,
    ):
        """
        初始化信号管理器
        
        Args:
            validator: 信号验证器，如果为 None 则使用默认配置
            deduplicator: 信号去重器，如果为 None 则使用默认配置
            on_signal_ready: 信号准备就绪回调函数
            max_queue_size: 最大队列大小
            allowed_symbols: 允许交易的标的列表
            blacklist: 黑名单标的列表
        """
        self.validator = validator or SignalValidator(
            allowed_symbols=allowed_symbols,
            blacklist=blacklist,
        )
        self.deduplicator = deduplicator or SignalDeduplicator()
        self.on_signal_ready = on_signal_ready
        
        self.max_queue_size = max_queue_size
        
        # 优先级队列：(priority, timestamp, signal)
        # 使用 (priority, timestamp) 确保优先级相同时按时间顺序处理
        self.signal_queue: List[tuple] = []
        
        # 信号存储：signal_id -> Signal
        self.signals: Dict[str, Signal] = {}
        
        # 统计信息
        self.stats = {
            'total_received': 0,
            'total_validated': 0,
            'total_rejected': 0,
            'total_duplicates': 0,
            'total_merged': 0,
            'total_sent': 0,
        }
        
        # 运行状态
        self.is_running = False
        self._cleanup_task: Optional[asyncio.Task] = None
        
        logger.info("信号管理器初始化完成")
    
    async def start(self):
        """启动信号管理器"""
        self.is_running = True
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        logger.info("信号管理器已启动")
    
    async def stop(self):
        """停止信号管理器"""
        self.is_running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("信号管理器已停止")
    
    async def _periodic_cleanup(self):
        """定期清理过期信号"""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # 每分钟清理一次
                self._cleanup_expired_signals()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理过期信号时出错：{e}")
    
    def _cleanup_expired_signals(self):
        """清理过期信号"""
        current_time = datetime.now()
        expired_count = 0
        
        # 从队列中移除过期信号
        new_queue = []
        for item in self.signal_queue:
            priority, timestamp, signal_id = item
            signal = self.signals.get(signal_id)
            if signal and not signal.is_expired():
                new_queue.append(item)
            else:
                expired_count += 1
                if signal:
                    signal.status = SignalStatus.EXPIRED
        
        self.signal_queue = new_queue
        heapq.heapify(self.signal_queue)
        
        if expired_count > 0:
            logger.info(f"清理了 {expired_count} 个过期信号")
    
    def receive_signal(self, signal: Signal) -> SignalValidationResult:
        """
        接收交易信号
        
        Args:
            signal: 交易信号
            
        Returns:
            验证结果
        """
        self.stats['total_received'] += 1
        logger.debug(f"接收信号：{signal.signal_id} - {signal.symbol} {signal.side} {signal.quantity}")
        
        # 1. 验证信号
        validation_result = self.validator.validate(signal)
        
        if not validation_result.is_valid:
            self.stats['total_rejected'] += 1
            signal.status = SignalStatus.REJECTED
            logger.warning(f"信号验证失败：{signal.signal_id} - {validation_result.error_message}")
            return validation_result
        
        signal = validation_result.signal
        signal.status = SignalStatus.VALIDATED
        self.stats['total_validated'] += 1
        
        # 2. 去重和合并
        merged_signal = self.deduplicator.add_and_merge(signal)
        
        if merged_signal is None:
            # 重复信号
            self.stats['total_duplicates'] += 1
            return SignalValidationResult(
                is_valid=False,
                error_code='DUPLICATE_SIGNAL',
                error_message='信号重复'
            )
        
        if merged_signal.signal_id != signal.signal_id:
            # 发生了合并
            self.stats['total_merged'] += 1
            signal = merged_signal
        
        # 3. 加入队列
        self._add_to_queue(signal)
        
        logger.info(f"信号已加入队列：{signal.signal_id} - 优先级 {signal.priority}")
        return SignalValidationResult(is_valid=True, signal=signal)
    
    def _add_to_queue(self, signal: Signal):
        """将信号加入优先级队列"""
        if len(self.signals) >= self.max_queue_size:
            logger.warning(f"信号队列已满 ({self.max_queue_size})，丢弃最低优先级信号")
            self._remove_lowest_priority_signal()
        
        # 使用 (priority, timestamp) 作为排序键
        # priority 越小优先级越高，timestamp 越早越优先
        heapq.heappush(self.signal_queue, (signal.priority, signal.timestamp, signal.signal_id))
        self.signals[signal.signal_id] = signal
        signal.status = SignalStatus.QUEUED
    
    def _remove_lowest_priority_signal(self):
        """移除最低优先级的信号"""
        if not self.signal_queue:
            return
        
        # 找到优先级最低 (数值最大) 的信号
        worst_idx = max(range(len(self.signal_queue)), key=lambda i: self.signal_queue[i][0])
        _, _, signal_id = self.signal_queue[worst_idx]
        
        # 从队列中移除
        self.signal_queue.pop(worst_idx)
        heapq.heapify(self.signal_queue)
        
        # 从存储中移除
        if signal_id in self.signals:
            signal = self.signals.pop(signal_id)
            signal.status = SignalStatus.CANCELLED
            logger.warning(f"因队列已满取消信号：{signal_id}")
    
    def get_next_signal(self) -> Optional[Signal]:
        """
        获取下一个待执行的信号 (优先级最高)
        
        Returns:
            信号，如果队列为空则返回 None
        """
        while self.signal_queue:
            priority, timestamp, signal_id = heapq.heappop(self.signal_queue)
            
            # 检查信号是否还存在且未过期
            signal = self.signals.get(signal_id)
            if signal and signal.status == SignalStatus.QUEUED:
                if signal.is_expired():
                    signal.status = SignalStatus.EXPIRED
                    continue
                
                signal.status = SignalStatus.PROCESSING
                return signal
        
        return None
    
    def mark_signal_sent(self, signal_id: str):
        """标记信号已发送给执行引擎"""
        if signal_id in self.signals:
            self.signals[signal_id].status = SignalStatus.SENT_TO_EXECUTOR
            self.signals[signal_id].timestamp = datetime.now()
            self.stats['total_sent'] += 1
            logger.debug(f"信号已发送：{signal_id}")
            
            # 触发回调
            if self.on_signal_ready:
                try:
                    self.on_signal_ready(self.signals[signal_id])
                except Exception as e:
                    logger.error(f"信号回调执行失败：{e}")
    
    def cancel_signal(self, signal_id: str, reason: str = "") -> bool:
        """
        取消信号
        
        Args:
            signal_id: 信号 ID
            reason: 取消原因
            
        Returns:
            是否成功取消
        """
        if signal_id not in self.signals:
            return False
        
        signal = self.signals[signal_id]
        if signal.status in [SignalStatus.SENT_TO_EXECUTOR, SignalStatus.EXPIRED, SignalStatus.CANCELLED]:
            return False
        
        signal.status = SignalStatus.CANCELLED
        signal.metadata['cancel_reason'] = reason
        
        # 从队列中移除
        self.signal_queue = [
            item for item in self.signal_queue
            if item[2] != signal_id
        ]
        heapq.heapify(self.signal_queue)
        
        logger.info(f"信号已取消：{signal_id} - {reason}")
        return True
    
    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        # 按优先级统计
        priority_counts = defaultdict(int)
        for _, _, signal_id in self.signal_queue:
            signal = self.signals.get(signal_id)
            if signal:
                priority_counts[signal.priority] += 1
        
        # 按标的统计
        symbol_counts = defaultdict(int)
        for _, _, signal_id in self.signal_queue:
            signal = self.signals.get(signal_id)
            if signal:
                symbol_counts[signal.symbol] += 1
        
        return {
            'queue_size': len(self.signal_queue),
            'max_queue_size': self.max_queue_size,
            'priority_distribution': dict(priority_counts),
            'symbol_distribution': dict(symbol_counts),
            'stats': self.stats.copy(),
        }
    
    def get_signal(self, signal_id: str) -> Optional[Signal]:
        """获取指定信号"""
        return self.signals.get(signal_id)
    
    def get_all_pending_signals(self) -> List[Signal]:
        """获取所有待处理信号"""
        return [
            signal for signal in self.signals.values()
            if signal.status in [SignalStatus.QUEUED, SignalStatus.PROCESSING]
        ]
    
    def clear_queue(self):
        """清空队列"""
        for signal in self.signals.values():
            if signal.status == SignalStatus.QUEUED:
                signal.status = SignalStatus.CANCELLED
        
        self.signal_queue.clear()
        logger.info("信号队列已清空")


# 工具函数

def generate_signal_id(strategy_id: str, symbol: str, timestamp: datetime) -> str:
    """生成信号 ID"""
    content = f"{strategy_id}:{symbol}:{timestamp.isoformat()}"
    return hashlib.md5(content.encode()).hexdigest()[:16]


def create_signal(
    strategy_id: str,
    symbol: str,
    side: str,
    quantity: Decimal,
    price_type: str = SignalPriceType.MARKET,
    limit_price: Optional[Decimal] = None,
    priority: int = SignalPriority.STRATEGY_ENTRY,
    expire_seconds: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Signal:
    """
    创建交易信号
    
    Args:
        strategy_id: 策略 ID
        symbol: 交易标的
        side: 交易方向 (BUY/SELL)
        quantity: 数量
        price_type: 价格类型
        limit_price: 限价 (限价单必需)
        priority: 优先级
        expire_seconds: 过期时间 (秒)
        metadata: 元数据
        
    Returns:
        Signal 对象
    """
    timestamp = datetime.now()
    signal_id = generate_signal_id(strategy_id, symbol, timestamp)
    
    expire_at = None
    if expire_seconds:
        expire_at = timestamp + timedelta(seconds=expire_seconds)
    
    return Signal(
        signal_id=signal_id,
        strategy_id=strategy_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        price_type=price_type,
        limit_price=limit_price,
        priority=priority,
        timestamp=timestamp,
        expire_at=expire_at,
        metadata=metadata or {},
    )


# 使用示例

if __name__ == "__main__":
    import asyncio
    
    async def main():
        # 创建信号管理器
        manager = SignalManager(
            allowed_symbols={'AAPL', 'GOOGL', 'MSFT', 'TSLA'},
            blacklist={'STOCK_X'},  # 黑名单
        )
        
        # 启动管理器
        await manager.start()
        
        # 创建测试信号
        signal1 = create_signal(
            strategy_id='momentum_v1',
            symbol='AAPL',
            side=SignalSide.BUY,
            quantity=Decimal('100'),
            price_type=SignalPriceType.LIMIT,
            limit_price=Decimal('150.00'),
            priority=SignalPriority.STRATEGY_ENTRY,
            expire_seconds=300,  # 5 分钟过期
        )
        
        signal2 = create_signal(
            strategy_id='momentum_v1',
            symbol='AAPL',
            side=SignalSide.BUY,
            quantity=Decimal('50'),  # 同方向，应该合并
            price_type=SignalPriceType.LIMIT,
            limit_price=Decimal('151.00'),  # 新价格
            priority=SignalPriority.STRATEGY_ENTRY,
            expire_seconds=300,
        )
        
        signal3 = create_signal(
            strategy_id='risk_control',
            symbol='TSLA',
            side=SignalSide.SELL,
            quantity=Decimal('200'),
            price_type=SignalPriceType.MARKET,
            priority=SignalPriority.STOP_LOSS,  # 高优先级
        )
        
        # 接收信号
        result1 = manager.receive_signal(signal1)
        print(f"信号 1 验证结果：{result1.is_valid}")
        
        result2 = manager.receive_signal(signal2)
        print(f"信号 2 验证结果：{result2.is_valid} (应该被合并)")
        
        result3 = manager.receive_signal(signal3)
        print(f"信号 3 验证结果：{result3.is_valid}")
        
        # 查看队列状态
        status = manager.get_queue_status()
        print(f"\n队列状态：{status}")
        
        # 获取下一个信号 (应该是高优先级的止损信号)
        next_signal = manager.get_next_signal()
        if next_signal:
            print(f"\n下一个执行信号：{next_signal.symbol} {next_signal.side} - 优先级 {next_signal.priority}")
            manager.mark_signal_sent(next_signal.signal_id)
        
        # 停止管理器
        await manager.stop()
    
    asyncio.run(main())
