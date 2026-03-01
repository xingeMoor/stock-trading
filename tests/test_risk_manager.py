"""
风控层单元测试
测试模块：risk_manager.py, position_manager.py
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime, timedelta
from dataclasses import dataclass

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'risk'))


class TestPositionConfig(unittest.TestCase):
    """测试仓位配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        from position_manager import PositionConfig
        
        config = PositionConfig()
        
        self.assertEqual(config.max_position_pct, 0.25)
        self.assertEqual(config.max_total_exposure, 1.0)
        self.assertEqual(config.max_sector_exposure, 0.4)
        self.assertEqual(config.kelly_fraction, 0.25)
        self.assertEqual(config.max_positions, 20)
    
    def test_custom_config(self):
        """测试自定义配置"""
        from position_manager import PositionConfig
        
        config = PositionConfig(
            max_position_pct=0.30,
            max_total_exposure=0.80,
            kelly_fraction=0.50
        )
        
        self.assertEqual(config.max_position_pct, 0.30)
        self.assertEqual(config.max_total_exposure, 0.80)
        self.assertEqual(config.kelly_fraction, 0.50)


class TestPositionManager(unittest.TestCase):
    """测试仓位管理器"""
    
    def setUp(self):
        """测试前准备"""
        from position_manager import PositionConfig, PositionManager
        
        self.config = PositionConfig(
            max_position_pct=0.25,
            max_total_exposure=1.0,
            max_sector_exposure=0.4,
            kelly_fraction=0.25,
            min_position_pct=0.02,
            max_positions=10
        )
        self.pm = PositionManager(self.config)
    
    def test_init(self):
        """测试初始化"""
        from position_manager import PositionManager
        
        pm = PositionManager()
        
        self.assertIsNotNone(pm.config)
        self.assertEqual(len(pm.positions), 0)
    
    def test_update_portfolio_value(self):
        """测试更新组合价值"""
        self.pm.update_portfolio_value(1000000, 200000)
        
        self.assertEqual(self.pm.total_portfolio_value, 1000000)
        self.assertEqual(self.pm.cash_balance, 200000)
    
    def test_add_position(self):
        """测试添加持仓"""
        from position_manager import Position, PositionType
        
        position = Position(
            symbol='AAPL',
            quantity=100,
            avg_price=150.0,
            current_price=155.0,
            market_value=15500.0,
            weight=0.1,
            sector='科技',
            position_type=PositionType.LONG
        )
        
        self.pm.add_position(position)
        
        self.assertIn('AAPL', self.pm.positions)
        self.assertEqual(self.pm.positions['AAPL'].symbol, 'AAPL')
    
    def test_remove_position(self):
        """测试移除持仓"""
        from position_manager import Position, PositionType
        
        position = Position(
            symbol='AAPL',
            quantity=100,
            avg_price=150.0,
            current_price=155.0,
            market_value=15500.0,
            weight=0.1,
            sector='科技',
            position_type=PositionType.LONG
        )
        
        self.pm.add_position(position)
        self.pm.remove_position('AAPL')
        
        self.assertNotIn('AAPL', self.pm.positions)
    
    def test_calculate_kelly_fraction(self):
        """测试 Kelly 公式计算"""
        # 胜率 50%，盈亏比 2:1
        kelly = self.pm.calculate_kelly_fraction(
            win_rate=0.5,
            avg_win=0.20,
            avg_loss=0.10
        )
        
        # Kelly 公式：f* = (0.5 * 2 - 0.5) / 2 = 0.25
        # 调整后：0.25 * 0.25 = 0.0625
        self.assertAlmostEqual(kelly, 0.0625, places=3)
    
    def test_calculate_kelly_fraction_negative(self):
        """测试 Kelly 公式负期望"""
        # 胜率 30%，盈亏比 1:1
        kelly = self.pm.calculate_kelly_fraction(
            win_rate=0.3,
            avg_win=0.10,
            avg_loss=0.10
        )
        
        # Kelly 公式：f* = (0.3 * 1 - 0.7) / 1 = -0.4
        # 应该返回 0
        self.assertEqual(kelly, 0.0)
    
    def test_calculate_kelly_from_returns(self):
        """测试从历史收益率计算 Kelly"""
        returns = [0.05, 0.03, -0.02, 0.08, -0.01, 0.04, -0.03, 0.06, 0.02, -0.02,
                   0.07, 0.01, -0.04, 0.05, 0.03]
        
        kelly = self.pm.calculate_kelly_from_returns(returns)
        
        self.assertGreater(kelly, 0)
        self.assertLessEqual(kelly, self.pm.config.max_position_pct)
    
    def test_calculate_kelly_insufficient_data(self):
        """测试数据不足时的 Kelly 计算"""
        returns = [0.05, -0.02, 0.03]  # 太少数据
        
        kelly = self.pm.calculate_kelly_from_returns(returns)
        
        self.assertEqual(kelly, 0.0)
    
    def test_check_position_limit_exceeds_max(self):
        """测试仓位超过上限"""
        allowed, reason = self.pm.check_position_limit('AAPL', 0.30, '科技')
        
        self.assertFalse(allowed)
        self.assertIn('最大仓位', reason)
    
    def test_check_position_limit_below_min(self):
        """测试仓位低于下限"""
        allowed, reason = self.pm.check_position_limit('AAPL', 0.01, '科技')
        
        self.assertFalse(allowed)
        self.assertIn('最小仓位', reason)
    
    def test_check_position_limit_sector_exposure(self):
        """测试行业敞口限制"""
        from position_manager import Position, PositionType
        
        # 先添加一些科技行业持仓
        for i in range(3):
            position = Position(
                symbol=f'STOCK{i}',
                quantity=100,
                avg_price=100.0,
                current_price=100.0,
                market_value=10000.0,
                weight=0.15,
                sector='科技',
                position_type=PositionType.LONG
            )
            self.pm.add_position(position)
        
        self.pm.update_portfolio_value(100000, 50000)
        
        # 再添加科技行业会超过 40% 限制
        allowed, reason = self.pm.check_position_limit('NEW', 0.15, '科技')
        
        self.assertFalse(allowed)
        self.assertIn('行业', reason)
    
    def test_check_position_limit_max_positions(self):
        """测试最大持仓数量限制"""
        from position_manager import Position, PositionType
        
        # 添加 10 个持仓
        for i in range(10):
            position = Position(
                symbol=f'STOCK{i}',
                quantity=100,
                avg_price=100.0,
                current_price=100.0,
                market_value=5000.0,
                weight=0.05,
                sector=f'行业{i}',
                position_type=PositionType.LONG
            )
            self.pm.add_position(position)
        
        self.pm.update_portfolio_value(100000, 50000)
        
        # 添加新持仓会超过数量限制
        allowed, reason = self.pm.check_position_limit('NEW', 0.05, '新行业')
        
        self.assertFalse(allowed)
        self.assertIn('持仓数量', reason)
    
    def test_check_position_limit_valid(self):
        """测试有效仓位"""
        allowed, reason = self.pm.check_position_limit('AAPL', 0.10, '科技')
        
        self.assertTrue(allowed)
        self.assertEqual(reason, "通过检查")


class TestRiskConfig(unittest.TestCase):
    """测试风控配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        from risk_manager import RiskConfig
        
        config = RiskConfig()
        
        self.assertEqual(config.kelly_fraction, 0.25)
        self.assertEqual(config.max_position_pct, 0.25)
        self.assertEqual(config.fixed_stop_loss_pct, 0.08)
        self.assertEqual(config.max_drawdown_pct, 0.15)
    
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_from_yaml(self, mock_file):
        """测试从 YAML 加载配置"""
        from risk_manager import RiskConfig
        
        yaml_content = """
kelly:
  fraction: 0.5
  max_position_pct: 0.30
stop_loss:
  fixed_stop_loss_pct: 0.10
  fixed_take_profit_pct: 0.25
global:
  max_drawdown_pct: 0.20
  max_daily_loss_pct: 0.05
dynamic_adjustment:
  volatility:
    enabled: true
  market_regime:
    current: 'bull'
"""
        mock_file.return_value.read.return_value = yaml_content
        
        config = RiskConfig.from_yaml('test_config.yaml')
        
        self.assertEqual(config.kelly_fraction, 0.5)
        self.assertEqual(config.max_position_pct, 0.30)
        self.assertEqual(config.fixed_stop_loss_pct, 0.10)
        self.assertEqual(config.max_drawdown_pct, 0.20)


class TestRiskManager(unittest.TestCase):
    """测试风险管理器"""
    
    def setUp(self):
        """测试前准备"""
        from risk_manager import RiskConfig, RiskManager
        
        self.config = RiskConfig(
            kelly_fraction=0.25,
            max_position_pct=0.25,
            min_position_pct=0.02,
            max_positions=10,
            fixed_stop_loss_pct=0.08,
            fixed_take_profit_pct=0.20
        )
        self.rm = RiskManager(self.config)
        self.rm.initialize(1000000)
    
    def test_init(self):
        """测试初始化"""
        from risk_manager import RiskManager
        
        rm = RiskManager()
        
        self.assertIsNotNone(rm.config)
        self.assertIsNotNone(rm.position_manager)
        self.assertIsNotNone(rm.stop_loss_manager)
    
    def test_initialize(self):
        """测试初始化风控系统"""
        self.assertEqual(self.rm.initial_capital, 1000000)
        self.assertEqual(self.rm.peak_value, 1000000)
        self.assertEqual(self.rm.current_value, 1000000)
    
    def test_update_portfolio_value(self):
        """测试更新组合价值"""
        self.rm.update_portfolio_value(1100000, datetime.now())
        
        self.assertEqual(self.rm.current_value, 1100000)
        self.assertEqual(self.rm.peak_value, 1100000)
        self.assertEqual(self.rm.current_drawdown, 0.0)
    
    def test_update_portfolio_value_drawdown(self):
        """测试更新组合价值（回撤情况）"""
        # 先上涨
        self.rm.update_portfolio_value(1200000, datetime.now())
        
        # 再下跌
        self.rm.update_portfolio_value(1000000, datetime.now())
        
        self.assertEqual(self.rm.current_value, 1000000)
        self.assertEqual(self.rm.peak_value, 1200000)
        self.assertGreater(self.rm.current_drawdown, 0)
    
    def test_check_drawdown_normal(self):
        """测试回撤检查（正常）"""
        self.rm.update_portfolio_value(980000, datetime.now())
        
        level, pct = self.rm.check_drawdown_level()
        
        self.assertIn(level.value, ['normal', 'warning'])
    
    def test_check_drawdown_warning(self):
        """测试回撤检查（警告）"""
        self.rm.update_portfolio_value(920000, datetime.now())
        
        level, pct = self.rm.check_drawdown_level()
        
        self.assertEqual(level.value, 'warning')
    
    def test_check_drawdown_danger(self):
        """测试回撤检查（危险）"""
        self.rm.update_portfolio_value(880000, datetime.now())
        
        level, pct = self.rm.check_drawdown_level()
        
        self.assertEqual(level.value, 'danger')
    
    def test_check_drawdown_critical(self):
        """测试回撤检查（严重）"""
        self.rm.update_portfolio_value(800000, datetime.now())
        
        level, pct = self.rm.check_drawdown_level()
        
        self.assertEqual(level.value, 'critical')
    
    def test_pre_trade_check_pass(self):
        """测试交易前风控检查（通过）"""
        from risk_manager import TradeRequest, MarketType
        
        request = TradeRequest(
            symbol='AAPL',
            action='buy',
            quantity=100,
            price=150.0,
            market=MarketType.US_STOCK,
            sector='科技',
            signal_strength=0.7,
            win_rate=0.55,
            avg_win=0.15,
            avg_loss=0.08
        )
        
        result = self.rm.pre_trade_check(request)
        
        self.assertTrue(result.allowed)
    
    def test_pre_trade_check_reject(self):
        """测试交易前风控检查（拒绝）"""
        from risk_manager import TradeRequest, MarketType
        
        # 连续亏损后应该拒绝交易
        self.rm.consecutive_losses = 5
        
        request = TradeRequest(
            symbol='AAPL',
            action='buy',
            quantity=100,
            price=150.0,
            market=MarketType.US_STOCK,
            sector='科技',
            signal_strength=0.5,
            win_rate=0.45,
            avg_win=0.10,
            avg_loss=0.10
        )
        
        result = self.rm.pre_trade_check(request)
        
        self.assertFalse(result.allowed)
    
    def test_calculate_position_size(self):
        """测试仓位大小计算"""
        from risk_manager import MarketType
        
        size = self.rm.calculate_position_size(
            symbol='AAPL',
            price=150.0,
            win_rate=0.55,
            avg_win=0.15,
            avg_loss=0.08,
            sector='科技'
        )
        
        self.assertGreater(size, 0)
    
    def test_record_trade_win(self):
        """测试记录盈利交易"""
        self.rm.record_trade(
            symbol='AAPL',
            pnl=1500.0,
            pnl_pct=0.10,
            timestamp=datetime.now()
        )
        
        self.assertEqual(self.rm.consecutive_losses, 0)
        self.assertEqual(len(self.rm.trade_history), 1)
    
    def test_record_trade_loss(self):
        """测试记录亏损交易"""
        self.rm.record_trade(
            symbol='AAPL',
            pnl=-800.0,
            pnl_pct=-0.05,
            timestamp=datetime.now()
        )
        
        self.assertEqual(self.rm.consecutive_losses, 1)
    
    def test_record_trade_consecutive_losses(self):
        """测试连续亏损"""
        for i in range(5):
            self.rm.record_trade(
                symbol=f'STOCK{i}',
                pnl=-500.0,
                pnl_pct=-0.03,
                timestamp=datetime.now() + timedelta(hours=i)
            )
        
        self.assertEqual(self.rm.consecutive_losses, 5)
    
    def test_get_risk_level(self):
        """测试风险等级评估"""
        from risk_manager import RiskLevel
        
        level = self.rm.get_risk_level()
        
        self.assertIsInstance(level, RiskLevel)
    
    def test_get_risk_metrics(self):
        """测试风险指标"""
        metrics = self.rm.get_risk_metrics()
        
        self.assertIn('current_drawdown', metrics)
        self.assertIn('total_trades', metrics)
        self.assertIn('consecutive_losses', metrics)


class TestStopLossManager(unittest.TestCase):
    """测试止损管理器"""
    
    def setUp(self):
        """测试前准备"""
        from stop_loss import StopLossConfig, StopLossManager
        
        self.config = StopLossConfig(
            fixed_stop_loss_pct=0.08,
            fixed_take_profit_pct=0.20,
            trailing_stop_pct=0.10,
            max_holding_days=30
        )
        self.slm = StopLossManager(self.config)
    
    def test_init(self):
        """测试初始化"""
        from stop_loss import StopLossManager
        
        slm = StopLossManager()
        
        self.assertIsNotNone(slm.config)
    
    def test_check_stop_loss_triggered(self):
        """测试止损触发"""
        from stop_loss import StopLossType
        
        position = {
            'symbol': 'AAPL',
            'entry_price': 100.0,
            'quantity': 100,
            'entry_date': datetime.now() - timedelta(days=10)
        }
        
        should_stop, stop_type, reason = self.slm.check_stop_loss(position, 90.0)
        
        self.assertTrue(should_stop)
        self.assertEqual(stop_type, StopLossType.FIXED_STOP)
    
    def test_check_take_profit_triggered(self):
        """测试止盈触发"""
        from stop_loss import StopLossType
        
        position = {
            'symbol': 'AAPL',
            'entry_price': 100.0,
            'quantity': 100,
            'entry_date': datetime.now() - timedelta(days=10)
        }
        
        should_stop, stop_type, reason = self.slm.check_stop_loss(position, 125.0)
        
        self.assertTrue(should_stop)
        self.assertEqual(stop_type, StopLossType.FIXED_PROFIT)
    
    def test_check_trailing_stop_triggered(self):
        """测试移动止损触发"""
        from stop_loss import StopLossType
        
        position = {
            'symbol': 'AAPL',
            'entry_price': 100.0,
            'quantity': 100,
            'entry_date': datetime.now() - timedelta(days=10),
            'highest_price': 130.0  # 曾经涨到 130
        }
        
        # 从最高点回撤超过 10%
        should_stop, stop_type, reason = self.slm.check_stop_loss(position, 115.0)
        
        self.assertTrue(should_stop)
        self.assertEqual(stop_type, StopLossType.TRAILING)
    
    def test_check_max_holding_days(self):
        """测试最大持有天数"""
        from stop_loss import StopLossType
        
        position = {
            'symbol': 'AAPL',
            'entry_price': 100.0,
            'quantity': 100,
            'entry_date': datetime.now() - timedelta(days=35),  # 超过 30 天
            'highest_price': 100.0
        }
        
        should_stop, stop_type, reason = self.slm.check_stop_loss(position, 105.0)
        
        self.assertTrue(should_stop)
        self.assertEqual(stop_type, StopLossType.TIME_EXIT)
    
    def test_check_no_stop(self):
        """测试不需要止损"""
        position = {
            'symbol': 'AAPL',
            'entry_price': 100.0,
            'quantity': 100,
            'entry_date': datetime.now() - timedelta(days=10),
            'highest_price': 100.0
        }
        
        should_stop, stop_type, reason = self.slm.check_stop_loss(position, 98.0)
        
        self.assertFalse(should_stop)


class TestDrawdownControl(unittest.TestCase):
    """测试回撤控制"""
    
    def setUp(self):
        """测试前准备"""
        from drawdown_control import DrawdownController, DrawdownConfig
        
        self.config = DrawdownConfig(
            max_drawdown_pct=0.15,
            max_daily_loss_pct=0.03,
            warning_threshold=0.05,
            reduce_position_threshold=0.10
        )
        self.dc = DrawdownController(self.config)
        self.dc.initialize(1000000)
    
    def test_init(self):
        """测试初始化"""
        from drawdown_control import DrawdownController
        
        dc = DrawdownController()
        
        self.assertIsNotNone(dc.config)
    
    def test_update_value(self):
        """测试更新价值"""
        self.dc.update_value(950000, datetime.now())
        
        self.assertEqual(self.dc.current_value, 950000)
        self.assertEqual(self.dc.current_drawdown, 0.05)
    
    def test_get_position_limit_normal(self):
        """测试仓位限制（正常）"""
        limit = self.dc.get_position_limit()
        
        self.assertEqual(limit, 1.0)  # 100% 仓位
    
    def test_get_position_limit_warning(self):
        """测试仓位限制（警告）"""
        self.dc.update_value(940000, datetime.now())  # 6% 回撤
        
        limit = self.dc.get_position_limit()
        
        self.assertLess(limit, 1.0)
    
    def test_get_position_limit_danger(self):
        """测试仓位限制（危险）"""
        self.dc.update_value(880000, datetime.now())  # 12% 回撤
        
        limit = self.dc.get_position_limit()
        
        self.assertLess(limit, 0.5)
    
    def test_should_stop_trading(self):
        """测试是否应该停止交易"""
        self.dc.update_value(800000, datetime.now())  # 20% 回撤
        
        should_stop = self.dc.should_stop_trading()
        
        self.assertTrue(should_stop)


class TestRiskMetrics(unittest.TestCase):
    """测试风险指标计算"""
    
    def test_sharpe_ratio(self):
        """测试夏普比率计算"""
        from risk_metrics import RiskMetrics
        
        returns = [0.02, 0.01, -0.01, 0.03, -0.02, 0.01, 0.02, -0.01, 0.01, 0.02]
        
        sharpe = RiskMetrics.calculate_sharpe_ratio(returns, risk_free_rate=0.02)
        
        self.assertIsInstance(sharpe, float)
    
    def test_max_drawdown(self):
        """测试最大回撤计算"""
        from risk_metrics import RiskMetrics
        
        values = [100, 110, 120, 110, 100, 90, 100, 110]
        
        max_dd, details = RiskMetrics.calculate_max_drawdown(values)
        
        self.assertGreater(max_dd, 0)
        self.assertEqual(max_dd, 0.25)  # 从 120 跌到 90
    
    def test_var(self):
        """测试 VaR 计算"""
        from risk_metrics import RiskMetrics
        
        returns = [0.02, 0.01, -0.01, 0.03, -0.02, 0.01, 0.02, -0.01, 0.01, 0.02,
                   -0.05, -0.03, 0.01, 0.02, -0.01]
        
        var_95 = RiskMetrics.calculate_var(returns, confidence_level=0.95)
        
        self.assertIsInstance(var_95, float)
        self.assertLess(var_95, 0)


class TestEdgeCases(unittest.TestCase):
    """边界条件测试"""
    
    def test_zero_capital(self):
        """测试零资本"""
        from risk_manager import RiskManager
        
        rm = RiskManager()
        rm.initialize(0)
        
        self.assertEqual(rm.initial_capital, 0)
    
    def test_negative_returns(self):
        """测试负收益率"""
        from position_manager import PositionManager
        
        pm = PositionManager()
        returns = [-0.05, -0.03, -0.02, -0.04, -0.01]
        
        kelly = pm.calculate_kelly_from_returns(returns)
        
        self.assertEqual(kelly, 0.0)  # 负期望应该返回 0
    
    def test_all_wins(self):
        """测试全盈利"""
        from position_manager import PositionManager
        
        pm = PositionManager()
        returns = [0.05, 0.03, 0.02, 0.04, 0.01]
        
        kelly = pm.calculate_kelly_from_returns(returns)
        
        # 没有亏损数据应该返回 0
        self.assertEqual(kelly, 0.0)
    
    def test_division_by_zero(self):
        """测试除零保护"""
        from position_manager import PositionManager
        
        pm = PositionManager()
        
        kelly = pm.calculate_kelly_fraction(0.5, 0.1, 0)  # avg_loss=0
        
        self.assertEqual(kelly, 0.0)
    
    def test_extreme_drawdown(self):
        """测试极端回撤"""
        from risk_manager import RiskManager
        
        rm = RiskManager()
        rm.initialize(1000000)
        rm.update_portfolio_value(100000, datetime.now())  # 90% 回撤
        
        level, pct = rm.check_drawdown_level()
        
        self.assertEqual(level.value, 'critical')


if __name__ == '__main__':
    unittest.main()
