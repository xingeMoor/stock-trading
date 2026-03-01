"""
回测引擎单元测试
测试模块：backtest_engine.py, batch_backtester.py
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'backtest'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestEventTypes(unittest.TestCase):
    """测试事件类型"""
    
    def test_event_type_enum(self):
        """测试事件类型枚举"""
        from engine import EventType
        
        self.assertEqual(EventType.MARKET_OPEN.name, 'MARKET_OPEN')
        self.assertEqual(EventType.BAR.name, 'BAR')
        self.assertEqual(EventType.FILL.name, 'FILL')


class TestOrderSide(unittest.TestCase):
    """测试订单方向"""
    
    def test_order_side_enum(self):
        """测试订单方向枚举"""
        from engine import OrderSide
        
        self.assertEqual(OrderSide.BUY.value, 'buy')
        self.assertEqual(OrderSide.SELL.value, 'sell')


class TestOrderType(unittest.TestCase):
    """测试订单类型"""
    
    def test_order_type_enum(self):
        """测试订单类型枚举"""
        from engine import OrderType
        
        self.assertEqual(OrderType.MARKET.value, 'market')
        self.assertEqual(OrderType.LIMIT.value, 'limit')


class TestEvent(unittest.TestCase):
    """测试事件类"""
    
    def test_event_creation(self):
        """测试事件创建"""
        from engine import Event, EventType
        
        event = Event(
            event_type=EventType.BAR,
            timestamp=datetime.now(),
            data={'symbol': 'AAPL', 'price': 150.0}
        )
        
        self.assertEqual(event.event_type, EventType.BAR)
        self.assertIn('symbol', event.data)
    
    def test_event_repr(self):
        """测试事件字符串表示"""
        from engine import Event, EventType
        
        event = Event(event_type=EventType.BAR, timestamp=datetime.now())
        repr_str = repr(event)
        
        self.assertIn('BAR', repr_str)


class TestBar(unittest.TestCase):
    """测试 K 线数据类"""
    
    def test_bar_creation(self):
        """测试 K 线创建"""
        from engine import Bar
        
        bar = Bar(
            symbol='AAPL',
            timestamp=datetime.now(),
            open=150.0,
            high=152.0,
            low=149.0,
            close=151.0,
            volume=1000000,
            freq='1d'
        )
        
        self.assertEqual(bar.symbol, 'AAPL')
        self.assertEqual(bar.close, 151.0)
    
    def test_typical_price(self):
        """测试典型价格计算"""
        from engine import Bar
        
        bar = Bar(
            symbol='AAPL',
            timestamp=datetime.now(),
            open=150.0,
            high=153.0,
            low=149.0,
            close=151.0,
            volume=1000000
        )
        
        # (153 + 149 + 151) / 3 = 151
        self.assertAlmostEqual(bar.typical_price, 151.0, places=2)
    
    def test_vwap(self):
        """测试成交量加权平均价"""
        from engine import Bar
        
        bar = Bar(
            symbol='AAPL',
            timestamp=datetime.now(),
            open=150.0,
            high=152.0,
            low=149.0,
            close=151.0,
            volume=1000000
        )
        
        # (150 + 152 + 149 + 151) / 4 = 150.5
        self.assertAlmostEqual(bar.vwap, 150.5, places=2)


class TestOrder(unittest.TestCase):
    """测试订单类"""
    
    def test_order_creation(self):
        """测试订单创建"""
        from engine import Order, OrderSide, OrderType
        
        order = Order(
            order_id='ORD001',
            symbol='AAPL',
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=100
        )
        
        self.assertEqual(order.order_id, 'ORD001')
        self.assertEqual(order.side, OrderSide.BUY)
    
    def test_order_total_cost(self):
        """测试订单总成本"""
        from engine import Order, OrderSide, OrderType
        
        order = Order(
            order_id='ORD001',
            symbol='AAPL',
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=100,
            commission=5.0,
            slippage=2.0,
            impact_cost=1.0
        )
        
        self.assertEqual(order.total_cost, 8.0)


class TestFill(unittest.TestCase):
    """测试成交类"""
    
    def test_fill_creation(self):
        """测试成交创建"""
        from engine import Fill, OrderSide
        
        fill = Fill(
            fill_id='FILL001',
            order_id='ORD001',
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=100,
            price=150.0,
            timestamp=datetime.now()
        )
        
        self.assertEqual(fill.fill_id, 'FILL001')
        self.assertEqual(fill.notional_value, 15000.0)
    
    def test_fill_total_cost(self):
        """测试成交总成本"""
        from engine import Fill, OrderSide
        
        fill = Fill(
            fill_id='FILL001',
            order_id='ORD001',
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=100,
            price=150.0,
            timestamp=datetime.now(),
            commission=5.0,
            slippage=2.0,
            impact_cost=1.0
        )
        
        self.assertEqual(fill.total_cost, 8.0)


class TestSlippageModels(unittest.TestCase):
    """测试滑点模型"""
    
    def test_fixed_slippage(self):
        """测试固定滑点模型"""
        from engine import FixedSlippage, Order, OrderSide, OrderType, Bar
        
        model = FixedSlippage(slippage_per_share=0.01)
        
        order = Order(
            order_id='ORD001',
            symbol='AAPL',
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=100
        )
        
        bar = Bar(
            symbol='AAPL',
            timestamp=datetime.now(),
            open=150.0,
            high=152.0,
            low=149.0,
            close=151.0,
            volume=1000000
        )
        
        slippage = model.calculate_slippage(order, bar)
        
        self.assertEqual(slippage, 1.0)  # 0.01 * 100
    
    def test_volatility_slippage(self):
        """测试波动率滑点模型"""
        from engine import VolatilitySlippage, Order, OrderSide, OrderType, Bar
        
        model = VolatilitySlippage(slippage_factor=0.0001)
        
        order = Order(
            order_id='ORD001',
            symbol='AAPL',
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=100
        )
        
        bar = Bar(
            symbol='AAPL',
            timestamp=datetime.now(),
            open=150.0,
            high=153.0,
            low=149.0,
            close=151.0,
            volume=1000000
        )
        
        slippage = model.calculate_slippage(order, bar)
        
        self.assertGreater(slippage, 0)


class TestImpactCostModels(unittest.TestCase):
    """测试冲击成本模型"""
    
    def test_square_root_impact(self):
        """测试平方根冲击成本模型"""
        from engine import SquareRootImpact, Order, OrderSide, OrderType, Bar
        
        model = SquareRootImpact(impact_factor=0.1)
        
        order = Order(
            order_id='ORD001',
            symbol='AAPL',
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=1000
        )
        
        bar = Bar(
            symbol='AAPL',
            timestamp=datetime.now(),
            open=150.0,
            high=152.0,
            low=149.0,
            close=151.0,
            volume=1000000
        )
        
        impact = model.calculate_impact(order, bar, avg_volume=1000000)
        
        self.assertGreater(impact, 0)
    
    def test_linear_impact(self):
        """测试线性冲击成本模型"""
        from engine import LinearImpact, Order, OrderSide, OrderType, Bar
        
        model = LinearImpact(impact_factor=0.001)
        
        order = Order(
            order_id='ORD001',
            symbol='AAPL',
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=1000
        )
        
        bar = Bar(
            symbol='AAPL',
            timestamp=datetime.now(),
            open=150.0,
            high=152.0,
            low=149.0,
            close=151.0,
            volume=1000000
        )
        
        impact = model.calculate_impact(order, bar, avg_volume=1000000)
        
        self.assertGreater(impact, 0)
    
    def test_zero_volume_impact(self):
        """测试零成交量时的冲击成本"""
        from engine import SquareRootImpact, Order, OrderSide, OrderType, Bar
        
        model = SquareRootImpact(impact_factor=0.1)
        
        order = Order(
            order_id='ORD001',
            symbol='AAPL',
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=1000
        )
        
        bar = Bar(
            symbol='AAPL',
            timestamp=datetime.now(),
            open=150.0,
            high=152.0,
            low=149.0,
            close=151.0,
            volume=1000000
        )
        
        impact = model.calculate_impact(order, bar, avg_volume=0)
        
        self.assertEqual(impact, 0.0)


class TestBacktestEngine(unittest.TestCase):
    """测试回测引擎"""
    
    def setUp(self):
        """测试前准备"""
        from engine import BacktestEngine, FixedSlippage, SquareRootImpact
        
        self.engine = BacktestEngine(
            initial_capital=1000000,
            commission_rate=0.0003,
            slippage_model=FixedSlippage(0.01),
            impact_model=SquareRootImpact(0.1)
        )
    
    def test_init(self):
        """测试初始化"""
        from engine import BacktestEngine
        
        engine = BacktestEngine(initial_capital=100000)
        
        self.assertEqual(engine.initial_capital, 100000)
        self.assertEqual(engine.cash, 100000)
    
    def test_submit_order(self):
        """测试提交订单"""
        from engine import OrderSide, OrderType
        
        order_id = self.engine.submit_order(
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )
        
        self.assertIsNotNone(order_id)
        self.assertIn(order_id, self.engine.pending_orders)
    
    def test_cancel_order(self):
        """测试取消订单"""
        from engine import OrderSide, OrderType
        
        order_id = self.engine.submit_order(
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )
        
        self.engine.cancel_order(order_id)
        
        self.assertNotIn(order_id, self.engine.pending_orders)
    
    def test_process_fill(self):
        """测试处理成交"""
        from engine import OrderSide, OrderType, Fill
        
        order_id = self.engine.submit_order(
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )
        
        fill = Fill(
            fill_id='FILL001',
            order_id=order_id,
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=100,
            price=150.0,
            timestamp=datetime.now()
        )
        
        self.engine.process_fill(fill)
        
        self.assertIn('AAPL', self.engine.positions)
        self.assertEqual(self.engine.positions['AAPL'], 100)
    
    def test_get_position(self):
        """测试获取持仓"""
        from engine import OrderSide, OrderType, Fill
        
        # 先买入
        order_id = self.engine.submit_order(
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )
        
        fill = Fill(
            fill_id='FILL001',
            order_id=order_id,
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=100,
            price=150.0,
            timestamp=datetime.now()
        )
        self.engine.process_fill(fill)
        
        position = self.engine.get_position('AAPL')
        
        self.assertEqual(position, 100)
    
    def test_get_portfolio_value(self):
        """测试获取组合价值"""
        value = self.engine.get_portfolio_value()
        
        self.assertEqual(value, self.engine.initial_capital)


class TestBatchBacktester(unittest.TestCase):
    """测试批量回测引擎"""
    
    def setUp(self):
        """测试前准备"""
        from batch_backtester import BacktestConfig, BatchBacktester
        
        self.config = BacktestConfig(
            symbol='AAPL',
            start_date='2024-01-01',
            end_date='2024-12-31',
            initial_capital=100000
        )
        
        self.batch = BatchBacktester(max_workers=2)
    
    def test_backtest_config(self):
        """测试回测配置"""
        from batch_backtester import BacktestConfig
        
        config = BacktestConfig(
            symbol='AAPL',
            name='Apple Inc.',
            start_date='2024-01-01',
            end_date='2024-12-31',
            initial_capital=100000,
            commission_rate=0.0003
        )
        
        self.assertEqual(config.symbol, 'AAPL')
        self.assertEqual(config.initial_capital, 100000)
    
    def test_backtest_config_to_dict(self):
        """测试配置转字典"""
        config_dict = self.config.to_dict()
        
        self.assertIn('symbol', config_dict)
        self.assertIn('start_date', config_dict)
        self.assertEqual(config_dict['symbol'], 'AAPL')
    
    def test_backtest_config_from_dict(self):
        """测试从字典创建配置"""
        from batch_backtester import BacktestConfig
        
        data = {
            'symbol': 'GOOGL',
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'initial_capital': 200000
        }
        
        config = BacktestConfig.from_dict(data)
        
        self.assertEqual(config.symbol, 'GOOGL')
        self.assertEqual(config.initial_capital, 200000)
    
    @patch('batch_backtester.BacktestEngine')
    def test_run_single_backtest(self, mock_engine_class):
        """测试单个回测"""
        from batch_backtester import BatchBacktester, BacktestResult
        
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.run.return_value = {
            'metrics': {'total_return': 0.15},
            'trades': []
        }
        
        batch = BatchBacktester()
        result = batch.run_single(self.config, mock_engine)
        
        self.assertIsInstance(result, BacktestResult)
        self.assertEqual(result.symbol, 'AAPL')
    
    def test_cache_manager_init(self):
        """测试缓存管理器初始化"""
        from batch_backtester import CacheManager
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_mgr = CacheManager(cache_dir=tmpdir)
            
            self.assertIsNotNone(cache_mgr.cache_dir)
    
    def test_cache_key_generation(self):
        """测试缓存键生成"""
        from batch_backtester import CacheManager
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_mgr = CacheManager(cache_dir=tmpdir)
            
            key = cache_mgr._get_cache_key(self.config, 'strategy_hash_123')
            
            self.assertIsInstance(key, str)
            self.assertEqual(len(key), 32)  # MD5 哈希长度


class TestPerformanceMetrics(unittest.TestCase):
    """测试绩效指标"""
    
    def test_total_return(self):
        """测试总收益率"""
        from backtest.performance import PerformanceMetrics
        
        metrics = PerformanceMetrics(
            total_return=0.15,
            annualized_return=0.18,
            sharpe_ratio=1.5,
            max_drawdown=0.10
        )
        
        self.assertEqual(metrics.total_return, 0.15)
    
    def test_metrics_from_trades(self):
        """测试从交易计算指标"""
        from backtest.performance import PerformanceAnalyzer, Trade
        
        trades = [
            Trade(
                symbol='AAPL',
                entry_date=datetime.now() - timedelta(days=30),
                exit_date=datetime.now(),
                entry_price=150.0,
                exit_price=165.0,
                quantity=100,
                side='buy',
                pnl=1500.0,
                pnl_pct=0.10,
                commission=5.0,
                slippage=2.0,
                impact_cost=1.0,
                is_open=False
            )
        ]
        
        analyzer = PerformanceAnalyzer(initial_capital=100000)
        metrics = analyzer.calculate_metrics(trades)
        
        self.assertIsNotNone(metrics)


class TestEdgeCases(unittest.TestCase):
    """边界条件测试"""
    
    def test_empty_trades(self):
        """测试空交易列表"""
        from backtest.performance import PerformanceAnalyzer
        
        analyzer = PerformanceAnalyzer(initial_capital=100000)
        metrics = analyzer.calculate_metrics([])
        
        self.assertIsNotNone(metrics)
    
    def test_single_trade(self):
        """测试单笔交易"""
        from backtest.performance import PerformanceAnalyzer, Trade
        
        trades = [
            Trade(
                symbol='AAPL',
                entry_date=datetime.now() - timedelta(days=30),
                exit_date=datetime.now(),
                entry_price=150.0,
                exit_price=165.0,
                quantity=100,
                side='buy',
                pnl=1500.0,
                pnl_pct=0.10,
                commission=5.0,
                slippage=2.0,
                impact_cost=1.0,
                is_open=False
            )
        ]
        
        analyzer = PerformanceAnalyzer(initial_capital=100000)
        metrics = analyzer.calculate_metrics(trades)
        
        self.assertGreater(metrics.total_return, 0)
    
    def test_all_loss_trades(self):
        """测试全亏损交易"""
        from backtest.performance import PerformanceAnalyzer, Trade
        
        trades = [
            Trade(
                symbol='AAPL',
                entry_date=datetime.now() - timedelta(days=30),
                exit_date=datetime.now(),
                entry_price=150.0,
                exit_price=135.0,
                quantity=100,
                side='buy',
                pnl=-1500.0,
                pnl_pct=-0.10,
                commission=5.0,
                slippage=2.0,
                impact_cost=1.0,
                is_open=False
            )
        ]
        
        analyzer = PerformanceAnalyzer(initial_capital=100000)
        metrics = analyzer.calculate_metrics(trades)
        
        self.assertLess(metrics.total_return, 0)
    
    def test_zero_initial_capital(self):
        """测试零初始资本"""
        from backtest.performance import PerformanceAnalyzer
        
        analyzer = PerformanceAnalyzer(initial_capital=0)
        
        # 应该能处理除零错误
        metrics = analyzer.calculate_metrics([])
        
        self.assertIsNotNone(metrics)
    
    def test_very_large_trade(self):
        """测试超大额交易"""
        from engine import Order, OrderSide, OrderType
        
        order = Order(
            order_id='ORD001',
            symbol='AAPL',
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=1000000  # 100 万股
        )
        
        self.assertEqual(order.quantity, 1000000)
    
    def test_negative_price_protection(self):
        """测试负价格保护"""
        from engine import Bar
        
        # K 线价格不应该为负
        bar = Bar(
            symbol='AAPL',
            timestamp=datetime.now(),
            open=150.0,
            high=152.0,
            low=149.0,
            close=151.0,
            volume=1000000
        )
        
        self.assertGreater(bar.low, 0)
        self.assertGreater(bar.close, 0)


class TestConcurrentBacktest(unittest.TestCase):
    """测试并发回测"""
    
    @patch('batch_backtester.BacktestEngine')
    def test_run_multiple_backtests(self, mock_engine_class):
        """测试多个回测并行运行"""
        from batch_backtester import BatchBacktester, BacktestConfig
        
        mock_engine = MagicMock()
        mock_engine.run.return_value = {'metrics': {'total_return': 0.10}, 'trades': []}
        mock_engine_class.return_value = mock_engine
        
        configs = [
            BacktestConfig(symbol='AAPL', start_date='2024-01-01', end_date='2024-12-31'),
            BacktestConfig(symbol='GOOGL', start_date='2024-01-01', end_date='2024-12-31'),
            BacktestConfig(symbol='MSFT', start_date='2024-01-01', end_date='2024-12-31')
        ]
        
        batch = BatchBacktester(max_workers=2)
        results = batch.run_multiple(configs, mock_engine)
        
        self.assertEqual(len(results), 3)
    
    def test_progress_tracking(self):
        """测试进度追踪"""
        from batch_backtester import BatchBacktester, BacktestConfig, BacktestResult
        from datetime import datetime
        
        batch = BatchBacktester()
        
        # 模拟进度更新
        batch.progress = {'completed': 5, 'total': 10, 'current': 'AAPL'}
        
        self.assertEqual(batch.progress['completed'], 5)
        self.assertEqual(batch.progress['total'], 10)


if __name__ == '__main__':
    unittest.main()
