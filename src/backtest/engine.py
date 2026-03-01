"""
回测引擎核心模块
================
事件驱动架构，支持日级/分钟级回测，包含滑点模拟和冲击成本模型。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, List, Optional, Callable, Any, Tuple
import numpy as np
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class EventType(Enum):
    """事件类型枚举"""
    MARKET_OPEN = auto()      # 市场开盘
    MARKET_CLOSE = auto()     # 市场收盘
    BAR = auto()              # K 线数据 (日级/分钟级)
    SIGNAL = auto()           # 交易信号
    ORDER = auto()            # 订单事件
    FILL = auto()             # 成交事件
    CUSTOM = auto()           # 自定义事件


class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"         # 市价单
    LIMIT = "limit"           # 限价单
    STOP = "stop"             # 止损单


@dataclass
class Event:
    """基础事件类"""
    event_type: EventType
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    
    def __repr__(self):
        return f"Event({self.event_type.name}, {self.timestamp})"


@dataclass
class Bar:
    """K 线数据"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    freq: str = "1d"  # 频率：1d(日级), 1m(分钟级) 等
    
    @property
    def typical_price(self) -> float:
        """典型价格 (高 + 低 + 收)/3"""
        return (self.high + self.low + self.close) / 3
    
    @property
    def vwap(self) -> float:
        """成交量加权平均价 (简化版)"""
        return (self.open + self.high + self.low + self.close) / 4


@dataclass
class Order:
    """订单类"""
    order_id: str
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: int
    price: Optional[float] = None  # 限价单价格
    stop_price: Optional[float] = None  # 止损单触发价
    timestamp: datetime = field(default_factory=datetime.now)
    commission: float = 0.0  # 手续费
    slippage: float = 0.0    # 滑点成本
    impact_cost: float = 0.0 # 冲击成本
    
    @property
    def total_cost(self) -> float:
        """总成本 (包含手续费、滑点、冲击成本)"""
        return self.commission + self.slippage + self.impact_cost


@dataclass
class Fill:
    """成交类"""
    fill_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    timestamp: datetime
    commission: float = 0.0
    slippage: float = 0.0
    impact_cost: float = 0.0
    
    @property
    def notional_value(self) -> float:
        """名义价值"""
        return self.price * self.quantity
    
    @property
    def total_cost(self) -> float:
        """总成本"""
        return self.commission + self.slippage + self.impact_cost


class SlippageModel(ABC):
    """滑点模型抽象基类"""
    
    @abstractmethod
    def calculate_slippage(self, order: Order, bar: Bar) -> float:
        """计算滑点成本"""
        pass


class FixedSlippage(SlippageModel):
    """固定滑点模型"""
    
    def __init__(self, slippage_per_share: float = 0.01):
        """
        Args:
            slippage_per_share: 每股滑点成本
        """
        self.slippage_per_share = slippage_per_share
    
    def calculate_slippage(self, order: Order, bar: Bar) -> float:
        return self.slippage_per_share * order.quantity


class VolatilitySlippage(SlippageModel):
    """波动率相关滑点模型"""
    
    def __init__(self, slippage_factor: float = 0.0001):
        """
        Args:
            slippage_factor: 滑点系数 (基于波动率)
        """
        self.slippage_factor = slippage_factor
    
    def calculate_slippage(self, order: Order, bar: Bar) -> float:
        # 基于价格波动率计算滑点
        daily_range = (bar.high - bar.low) / bar.close
        slippage_per_share = self.slippage_factor * daily_range * bar.close
        return slippage_per_share * order.quantity


class ImpactCostModel(ABC):
    """冲击成本模型抽象基类"""
    
    @abstractmethod
    def calculate_impact(self, order: Order, bar: Bar, avg_volume: float) -> float:
        """计算冲击成本"""
        pass


class SquareRootImpact(ImpactCostModel):
    """平方根冲击成本模型 (Almgren-Chriss 简化版)"""
    
    def __init__(self, impact_factor: float = 0.1):
        """
        Args:
            impact_factor: 冲击系数
        """
        self.impact_factor = impact_factor
    
    def calculate_impact(self, order: Order, bar: Bar, avg_volume: float) -> float:
        # 冲击成本 = 系数 * 价格 * sqrt(订单量 / 平均成交量)
        if avg_volume <= 0:
            return 0.0
        
        participation_rate = order.quantity / avg_volume
        impact_per_share = self.impact_factor * bar.close * np.sqrt(participation_rate)
        return impact_per_share * order.quantity


class LinearImpact(ImpactCostModel):
    """线性冲击成本模型"""
    
    def __init__(self, impact_factor: float = 0.001):
        """
        Args:
            impact_factor: 冲击系数
        """
        self.impact_factor = impact_factor
    
    def calculate_impact(self, order: Order, bar: Bar, avg_volume: float) -> float:
        if avg_volume <= 0:
            return 0.0
        
        participation_rate = order.quantity / avg_volume
        impact_per_share = self.impact_factor * bar.close * participation_rate
        return impact_per_share * order.quantity


class DataAligner:
    """数据对齐器 - 处理多数据源时间对齐、前复权、停牌"""
    
    def __init__(self):
        self.adjustment_factors: Dict[str, Dict[datetime, float]] = defaultdict(dict)
        self.suspended_dates: Dict[str, set] = defaultdict(set)
    
    def add_adjustment_factor(self, symbol: str, date: datetime, factor: float):
        """添加前复权因子"""
        self.adjustment_factors[symbol][date] = factor
    
    def add_suspension(self, symbol: str, date: datetime):
        """添加停牌日期"""
        self.suspended_dates[symbol].add(date.date())
    
    def is_suspended(self, symbol: str, date: datetime) -> bool:
        """检查是否停牌"""
        return date.date() in self.suspended_dates[symbol]
    
    def adjust_price(self, symbol: str, price: float, date: datetime) -> float:
        """应用前复权调整"""
        factor = 1.0
        for adj_date, adj_factor in self.adjustment_factors[symbol].items():
            if adj_date <= date:
                factor *= adj_factor
        return price * factor
    
    def align_bars(self, bars_dict: Dict[str, List[Bar]], freq: str = "1d") -> List[Dict[str, Optional[Bar]]]:
        """
        对齐多个标的的 K 线数据
        
        Args:
            bars_dict: {symbol: [Bar, ...]}
            freq: 频率
            
        Returns:
            对齐后的时间序列，每个时间点包含所有标的的 K 线 (缺失为 None)
        """
        # 收集所有时间点
        all_timestamps = set()
        for symbol, bars in bars_dict.items():
            for bar in bars:
                all_timestamps.add(bar.timestamp)
        
        # 排序
        sorted_timestamps = sorted(all_timestamps)
        
        # 创建索引
        bar_index = {}
        for symbol, bars in bars_dict.items():
            bar_index[symbol] = {bar.timestamp: bar for bar in bars}
        
        # 对齐
        aligned = []
        for ts in sorted_timestamps:
            row = {}
            for symbol in bars_dict.keys():
                bar = bar_index[symbol].get(ts)
                # 检查停牌
                if bar and self.is_suspended(symbol, ts):
                    bar = None
                # 应用前复权
                if bar:
                    bar = Bar(
                        symbol=bar.symbol,
                        timestamp=bar.timestamp,
                        open=self.adjust_price(symbol, bar.open, ts),
                        high=self.adjust_price(symbol, bar.high, ts),
                        low=self.adjust_price(symbol, bar.low, ts),
                        close=self.adjust_price(symbol, bar.close, ts),
                        volume=bar.volume,
                        freq=bar.freq
                    )
                row[symbol] = bar
            aligned.append(row)
        
        return aligned


class EventQueue:
    """事件队列 - 优先级队列实现"""
    
    def __init__(self):
        self._queue: List[Event] = []
    
    def put(self, event: Event):
        """添加事件"""
        self._queue.append(event)
        self._queue.sort(key=lambda e: e.timestamp)
    
    def get(self) -> Optional[Event]:
        """获取下一个事件"""
        if self._queue:
            return self._queue.pop(0)
        return None
    
    def empty(self) -> bool:
        """队列是否为空"""
        return len(self._queue) == 0
    
    def __len__(self):
        return len(self._queue)


class Position:
    """持仓类"""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.quantity = 0
        self.avg_cost = 0.0
        self.realized_pnl = 0.0
    
    @property
    def is_long(self) -> bool:
        return self.quantity > 0
    
    @property
    def is_short(self) -> bool:
        return self.quantity < 0
    
    def update(self, fill: Fill):
        """根据成交更新持仓"""
        if fill.side == OrderSide.BUY:
            if self.quantity >= 0:
                # 买入加仓
                total_cost = self.avg_cost * self.quantity + fill.price * fill.quantity + fill.total_cost
                self.quantity += fill.quantity
                self.avg_cost = total_cost / self.quantity if self.quantity > 0 else 0
            else:
                # 买入平仓
                close_qty = min(fill.quantity, abs(self.quantity))
                pnl = (self.avg_cost - fill.price) * close_qty - fill.total_cost
                self.realized_pnl += pnl
                self.quantity += fill.quantity
                if self.quantity > 0:
                    self.avg_cost = fill.price
        else:  # SELL
            if self.quantity <= 0:
                # 卖出加仓 (做空)
                total_cost = self.avg_cost * abs(self.quantity) + fill.price * fill.quantity + fill.total_cost
                self.quantity -= fill.quantity
                self.avg_cost = total_cost / abs(self.quantity) if self.quantity < 0 else 0
            else:
                # 卖出平仓
                close_qty = min(fill.quantity, self.quantity)
                pnl = (fill.price - self.avg_cost) * close_qty - fill.total_cost
                self.realized_pnl += pnl
                self.quantity -= fill.quantity
                if self.quantity < 0:
                    self.avg_cost = fill.price
    
    @property
    def market_value(self, current_price: float) -> float:
        """市值"""
        return abs(self.quantity) * current_price


class Portfolio:
    """投资组合类"""
    
    def __init__(self, initial_cash: float = 1000000.0):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: Dict[str, Position] = {}
        self.fills: List[Fill] = []
    
    def get_position(self, symbol: str) -> Position:
        """获取或创建持仓"""
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol)
        return self.positions[symbol]
    
    def process_fill(self, fill: Fill):
        """处理成交"""
        self.fills.append(fill)
        
        # 更新持仓
        position = self.get_position(fill.symbol)
        position.update(fill)
        
        # 更新现金
        if fill.side == OrderSide.BUY:
            self.cash -= fill.notional_value + fill.total_cost
        else:
            self.cash += fill.notional_value - fill.total_cost
    
    @property
    def total_value(self) -> float:
        """总权益 (需要当前价格)"""
        # 由外部计算
        return self.cash
    
    def get_all_positions(self) -> Dict[str, Position]:
        """获取所有持仓"""
        return self.positions.copy()


class Strategy(ABC):
    """策略抽象基类"""
    
    def __init__(self, name: str = "Strategy"):
        self.name = name
        self.portfolio: Optional[Portfolio] = None
        self.data: Dict[str, List[Bar]] = {}
    
    @abstractmethod
    def on_bar(self, symbol: str, bar: Bar, portfolio: Portfolio):
        """K 线事件处理"""
        pass
    
    def on_init(self, portfolio: Portfolio):
        """初始化回调"""
        self.portfolio = portfolio
    
    def generate_order(self, symbol: str, side: OrderSide, quantity: int, 
                       order_type: OrderType = OrderType.MARKET, 
                       price: Optional[float] = None) -> Order:
        """生成订单"""
        order_id = f"{self.name}_{symbol}_{datetime.now().timestamp()}"
        return Order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            type=order_type,
            quantity=quantity,
            price=price
        )


class BacktestEngine:
    """回测引擎核心"""
    
    def __init__(self, 
                 initial_cash: float = 1000000.0,
                 slippage_model: Optional[SlippageModel] = None,
                 impact_model: Optional[ImpactCostModel] = None,
                 commission_rate: float = 0.0003,  # 万三手续费
                 freq: str = "1d"):
        """
        Args:
            initial_cash: 初始资金
            slippage_model: 滑点模型
            impact_model: 冲击成本模型
            commission_rate: 手续费率
            freq: 回测频率 (1d=日级，1m=分钟级)
        """
        self.initial_cash = initial_cash
        self.portfolio = Portfolio(initial_cash)
        self.event_queue = EventQueue()
        self.data_aligner = DataAligner()
        
        self.slippage_model = slippage_model or FixedSlippage()
        self.impact_model = impact_model or SquareRootImpact()
        self.commission_rate = commission_rate
        self.freq = freq
        
        self.strategies: List[Strategy] = []
        self.current_bar: Dict[str, Bar] = {}
        self.avg_volumes: Dict[str, float] = {}  # 平均成交量
        
        self._running = False
        self._event_handlers: Dict[EventType, List[Callable]] = defaultdict(list)
    
    def add_strategy(self, strategy: Strategy):
        """添加策略"""
        strategy.on_init(self.portfolio)
        self.strategies.append(strategy)
        logger.info(f"添加策略：{strategy.name}")
    
    def set_data(self, bars_dict: Dict[str, List[Bar]]):
        """设置数据"""
        for symbol, bars in bars_dict.items():
            # 计算平均成交量
            if bars:
                self.avg_volumes[symbol] = np.mean([b.volume for b in bars])
        
        # 对齐数据
        self.aligned_data = self.data_aligner.align_bars(bars_dict, self.freq)
        logger.info(f"设置数据完成，共 {len(self.aligned_data)} 个时间点，{len(bars_dict)} 个标的")
    
    def add_adjustment_factor(self, symbol: str, date: datetime, factor: float):
        """添加复权因子"""
        self.data_aligner.add_adjustment_factor(symbol, date, factor)
    
    def add_suspension(self, symbol: str, date: datetime):
        """添加停牌日期"""
        self.data_aligner.add_suspension(symbol, date)
    
    def register_handler(self, event_type: EventType, handler: Callable):
        """注册事件处理器"""
        self._event_handlers[event_type].append(handler)
    
    def _emit_event(self, event: Event):
        """触发事件"""
        for handler in self._event_handlers.get(event.event_type, []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"事件处理器错误：{e}")
    
    def _process_order(self, order: Order, bar: Bar) -> Optional[Fill]:
        """处理订单，生成成交"""
        # 检查停牌
        if self.data_aligner.is_suspended(order.symbol, bar.timestamp):
            logger.debug(f"{order.symbol} 停牌，订单跳过")
            return None
        
        # 计算滑点
        slippage = self.slippage_model.calculate_slippage(order, bar)
        
        # 计算冲击成本
        avg_vol = self.avg_volumes.get(order.symbol, bar.volume)
        impact = self.impact_model.calculate_impact(order, bar, avg_vol)
        
        # 计算手续费
        commission = order.quantity * bar.close * self.commission_rate
        
        # 计算成交价格
        if order.side == OrderSide.BUY:
            fill_price = bar.close + slippage / order.quantity + impact / order.quantity
        else:
            fill_price = bar.close - slippage / order.quantity - impact / order.quantity
        
        # 创建成交
        fill = Fill(
            fill_id=f"fill_{order.order_id}_{bar.timestamp.timestamp()}",
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            timestamp=bar.timestamp,
            commission=commission,
            slippage=slippage,
            impact_cost=impact
        )
        
        return fill
    
    def run(self) -> Dict[str, Any]:
        """运行回测"""
        logger.info("开始回测...")
        self._running = True
        
        # 初始化
        for strategy in self.strategies:
            strategy.on_init(self.portfolio)
        
        # 发送开盘事件
        self._emit_event(Event(
            event_type=EventType.MARKET_OPEN,
            timestamp=datetime.now()
        ))
        
        # 处理每个时间点
        for i, bar_dict in enumerate(self.aligned_data):
            self.current_bar = {k: v for k, v in bar_dict.items() if v is not None}
            
            if not self.current_bar:
                continue
            
            # 发送 K 线事件
            for symbol, bar in self.current_bar.items():
                bar_event = Event(
                    event_type=EventType.BAR,
                    timestamp=bar.timestamp,
                    data={"symbol": symbol, "bar": bar}
                )
                self._emit_event(bar_event)
                
                # 调用策略
                for strategy in self.strategies:
                    try:
                        strategy.on_bar(symbol, bar, self.portfolio)
                    except Exception as e:
                        logger.error(f"策略 {strategy.name} 错误：{e}")
            
            # 处理订单队列 (简化：假设订单在当前 bar 成交)
            # 实际应用中应有独立的订单队列管理
        
        # 发送收盘事件
        self._emit_event(Event(
            event_type=EventType.MARKET_CLOSE,
            timestamp=datetime.now()
        ))
        
        self._running = False
        logger.info("回测完成")
        
        return self.get_results()
    
    def get_results(self) -> Dict[str, Any]:
        """获取回测结果"""
        return {
            "initial_cash": self.initial_cash,
            "final_cash": self.portfolio.cash,
            "positions": {
                symbol: {
                    "quantity": pos.quantity,
                    "avg_cost": pos.avg_cost,
                    "realized_pnl": pos.realized_pnl
                }
                for symbol, pos in self.portfolio.positions.items()
            },
            "fills": self.portfolio.fills,
            "total_fills": len(self.portfolio.fills),
            "total_slippage": sum(f.slippage for f in self.portfolio.fills),
            "total_impact": sum(f.impact_cost for f in self.portfolio.fills),
            "total_commission": sum(f.commission for f in self.portfolio.fills)
        }
    
    def stop(self):
        """停止回测"""
        self._running = False


# 示例策略
class MovingAverageStrategy(Strategy):
    """双均线策略示例"""
    
    def __init__(self, short_window: int = 5, long_window: int = 20):
        super().__init__(f"MA_{short_window}_{long_window}")
        self.short_window = short_window
        self.long_window = long_window
        self.price_history: Dict[str, List[float]] = defaultdict(list)
    
    def on_bar(self, symbol: str, bar: Bar, portfolio: Portfolio):
        # 记录价格
        self.price_history[symbol].append(bar.close)
        
        if len(self.price_history[symbol]) < self.long_window:
            return
        
        # 计算均线
        prices = self.price_history[symbol][-self.long_window:]
        short_ma = np.mean(prices[-self.short_window:])
        long_ma = np.mean(prices)
        
        # 获取持仓
        position = portfolio.get_position(symbol)
        
        # 交易逻辑
        if short_ma > long_ma and not position.is_long:
            # 金叉，买入
            order = self.generate_order(symbol, OrderSide.BUY, 100)
            # 实际应用中应提交到引擎
        elif short_ma < long_ma and not position.is_short:
            # 死叉，卖出
            order = self.generate_order(symbol, OrderSide.SELL, 100)
            # 实际应用中应提交到引擎
