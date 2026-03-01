"""
回测系统模块
============
新一代事件驱动回测引擎，支持日级/分钟级回测、滑点模拟、冲击成本模型和绩效分析。
"""

from .engine import (
    BacktestEngine,
    Strategy,
    Portfolio,
    Position,
    Order,
    Fill,
    Bar,
    Event,
    EventType,
    OrderSide,
    OrderType,
    SlippageModel,
    FixedSlippage,
    VolatilitySlippage,
    ImpactCostModel,
    SquareRootImpact,
    LinearImpact,
    DataAligner,
    MovingAverageStrategy,
)

from .performance import (
    PerformanceAnalyzer,
    PerformanceMetrics,
    AttributionAnalyzer,
    Trade,
    generate_performance_report,
)

__version__ = "1.0.0"
__author__ = "Q-Brain Team"

__all__ = [
    # 引擎核心
    "BacktestEngine",
    "Strategy",
    "Portfolio",
    "Position",
    
    # 订单和成交
    "Order",
    "Fill",
    "OrderSide",
    "OrderType",
    
    # 数据
    "Bar",
    "Event",
    "EventType",
    
    # 成本模型
    "SlippageModel",
    "FixedSlippage",
    "VolatilitySlippage",
    "ImpactCostModel",
    "SquareRootImpact",
    "LinearImpact",
    
    # 数据处理
    "DataAligner",
    
    # 绩效分析
    "PerformanceAnalyzer",
    "PerformanceMetrics",
    "AttributionAnalyzer",
    "Trade",
    "generate_performance_report",
    
    # 示例策略
    "MovingAverageStrategy",
]
