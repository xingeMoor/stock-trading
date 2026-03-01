"""
Q 脑交易执行系统

交易执行系统负责将策略信号转化为实际订单，包含:
- 信号管理 (SignalManager)
- 订单执行 (OrderExecutor)
- 执行监控 (ExecutionMonitor)
"""

from .signal_manager import (
    Signal,
    SignalPriority,
    SignalSide,
    SignalPriceType,
    SignalStatus,
    SignalManager,
    SignalValidator,
    SignalDeduplicator,
    create_signal,
    generate_signal_id,
)

from .order_executor import (
    Order,
    OrderSide,
    OrderType,
    OrderStatus,
    ExecutionAlgorithm,
    OrderExecutor,
    OrderRouter,
    SliceGenerator,
    RiskChecker,
    BrokerAdapter,
    ExecutionReport,
)

from .execution_monitor import (
    ExecutionMonitor,
    ExecutionMetrics,
    ExecutionQuality,
    Alert,
    AlertLevel,
    OrderAnomaly,
    ExecutionAnalyzer,
    AnomalyDetector,
)

__version__ = '1.0.0'
__all__ = [
    # Signal Manager
    'Signal',
    'SignalPriority',
    'SignalSide',
    'SignalPriceType',
    'SignalStatus',
    'SignalManager',
    'SignalValidator',
    'SignalDeduplicator',
    'create_signal',
    'generate_signal_id',
    
    # Order Executor
    'Order',
    'OrderSide',
    'OrderType',
    'OrderStatus',
    'ExecutionAlgorithm',
    'OrderExecutor',
    'OrderRouter',
    'SliceGenerator',
    'RiskChecker',
    'BrokerAdapter',
    'ExecutionReport',
    
    # Execution Monitor
    'ExecutionMonitor',
    'ExecutionMetrics',
    'ExecutionQuality',
    'Alert',
    'AlertLevel',
    'OrderAnomaly',
    'ExecutionAnalyzer',
    'AnomalyDetector',
]
